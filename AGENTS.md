# nsh-py: notes for agents

The sprint guide (tracks, setup, workflow, PR checklist) is part of these notes:
@SPRINT.md

Python bindings for [Native Shell (NSH)](https://nsh.dev) by Longbridge: native UIs written in plain Python.
`pip install nsh-py`, then `import nsh`. (The PyPI name `nsh` is a placeholder upload, so we may ask for it under PEP 541 later.)

## Goal and constraints
- **Users:** Python developers who write simple, familiar Python and get native NSH UIs. The API should feel Pythonic, not like Rust.
- **PyCon sprint:** an in-person sprint where contributors use macOS, Windows and Linux. Most contributors know little Rust, so the pure-Python layer (styled components on `nsh/base`, Tailwind classes, docs, examples, tests) is where most sprint work happens.
- **Our own repo:** we don't fork NSH and don't depend on upstream changes. Exception: when we (the maintainers, not sprint contributors) hit a real NSH bug, we may file an issue or PR upstream. Sprint contributors never need to touch NSH; work around upstream bugs here and link the upstream issue. The web spike's nsh-core libc fix went upstream this way ([longbridge/nsh#896](https://github.com/longbridge/nsh/pull/896)).
- **Distribution:** prebuilt abi3 wheels for Python 3.10+, like Polars, so end users never compile anything.
- **Later: web.** `web/` runs apps in a browser (Pyodide + nsh-platform-web; the same app file as desktop). Needs NSH 0.5.0+ (it has our emscripten libc fix, [longbridge/nsh#896](https://github.com/longbridge/nsh/pull/896)) and uses a patched copy of NSH's `nsh.js` (one option, not filed upstream yet). Details in `web/README.md`. Not sprint scope.
- **Later:** a Streamlit-style layer is a separate future project. Keep the layers clean so it can sit on top.
- **Commits:** make atomic commits as work progresses.
- **Delegation:** parallel work can be split across Sonnet (Claude) and Grok agents.

## Architecture decision: "Path B"
Bind NSH's **public Rust app API** through PyO3. Don't write a script host next to `nsh-js`: that would need a fork of `nsh-engine`, which hard-wires QuickJS. Full reasoning: `docs/research/nsh-2026-11-03.md`.

- `platform::run_app(AppSource::Rust(Root::...), AppOptions{..})` runs on the **process main thread** (Python's main thread). Release the GIL (`py.detach`) before calling it.
- App code, signals and handlers run on the **"nsh-engine" thread**. The reactive graph panics anywhere else. Python callbacks run there through `Python::attach`.
- **Ctrl-C:** `Python::check_signals` does nothing off the main thread, so a timer on the GTK/AppKit/Win32 main loop has to attach and check signals.
- **Handlers:** `on_press(impl IntoListener)` closures must be `'static` but **not `Send`**, so they can hold `Py<PyAny>`. `Root::new(props: Fn() -> P + Send + Sync + 'static)` crosses threads, which is fine for `Py<PyAny>`.
- **Runtime trees:** `view()`, `text(content)`, `.child()`, `dynamic(|| ...)` (flow.rs:208), `when` and `each` all work at runtime, with no macros needed.
- **Reactive props:** `IntoReactive<T>` is implemented for any `Fn() -> U + 'static` where `U: Into<T>` (reactive.rs:1056). That's how Python lambdas become reactive bindings.
- **Tailwind strings:** `.app_class(impl IntoReactive<Option<SharedString>>)` (builder.rs:857) passes class strings to the core, which parses them natively. This backs `class_="p-4 gap-2"`.
- **`Component` trait** (element/component.rs:43): `type Props: Props; type Event: Event; fn view(props, cx: Scope<Event>) -> impl IntoElement`. `Root::of::<C>()` needs `C::Props: Default`.
- **Platform crates:** `nsh-platform-{linux,macos,windows}` expose the same names, and each only compiles on its own OS. Use them with `default-features = false`, which drops QuickJS.
- **Example to copy:** `examples/gallery-rs/native/src/main.rs` in the NSH repo shows `set_ui_sets(vec![nsh_base::registry(), ..])`, `Root::of::<App>().tokens(..).app_id(..)` and `run_app`.
- **Testing:** `nsh-testing` provides `Headless::start(EngineConfig::new(Root::of::<App>()))` with `.press("text:..")`, `.type_text("id:..", ..)` and `.wait_for(..)`. It needs no display.

## Pins and toolchain
- NSH crates are pinned to exactly `=0.5.0`. NSH's 0.x releases break the API (0.4.0 and 0.5.0 did), and the compatibility freeze hasn't started yet. Bump deliberately, one PR per bump, and read the release's "Migrating" notes first.
- ⚠ The crates.io crate named `nsh` is an unrelated shell. Depend on `nsh-core`, `nsh-base` and so on.
- Rust 1.99.1 is pinned in `rust-toolchain.toml`. This machine's `stable` rustup toolchain is broken (no `rustc`), so use the pinned one.
- PyO3 0.30: `Python::attach` / `py.detach` (the old names were `with_gil` / `allow_threads`).
- NSH source is in `~/.cargo/registry/src/index.crates.io-*/nsh-*-0.5.0/`. Read it there, since it matches our pin. A checkout of NSH `main` (newer) at `/tmp/nsh-src` belongs to another session, so read it only and never build there.

## Build
```sh
uv venv && uv pip install maturin pytest
source .venv/bin/activate && maturin develop      # about 65 s cold on Linux
python -c "import nsh; print(nsh.__version__)"
```
Or just `uv run python examples/counter.py` / `uv run pytest`: uv builds the extension itself and rebuilds when `src/**/*.rs`, `Cargo.*` or `pyproject.toml` change (`[tool.uv] cache-keys`). It builds the dev profile (`[tool.uv] config-settings`), so a Rust edit costs ~1-3 s; release (LTO) takes ~23 s incremental and is only for wheels (`maturin build --release`). Dev builds keep line tables only (deps none): the .so is ~110 MB instead of ~790 MB.
Linux needs GTK 4.14+, GStreamer 1.x (core + plugins-base: NSH 0.5.0's Linux backend links it) and glibc 2.39 or newer (Ubuntu 24.04+, Debian 13, Fedora 40+, Arch), plus clang/libclang. Ubuntu 22.04 and Debian 12 are too old.

## Where code goes
Behaviour in Rust, look and composition in Python: `python/nsh/components/` (Python only), `python/nsh/primitives/<kind>.py` ↔ `src/elements/<kind>.rs` (registered in `KINDS`), core = `_element/_signals/_runtime/testing` + `bridge/signal/app/headless`. Details: `docs/architecture.md`. Gotcha: `nsh.primitives.view` is the function (package re-export shadows the module); import module names from the module (`from nsh.primitives.view import KIND`).

## Python API direction (draft)
```python
import nsh

def Counter():
    count = nsh.signal(0)
    return nsh.view(
        nsh.text(lambda: f"Count: {count()}", class_="text-xl"),
        nsh.button("Increment", on_press=lambda: count.update(lambda n: n + 1)),
        class_="p-4 gap-2",
    )

nsh.run(Counter, title="Counter")
```
- The signal API follows reaktiv/Solid: `s()`, `.set()`, `.update()`, `computed`, `effect`.
- **Pitfall 1:** a value read without a lambda is read once and isn't reactive. Warn or lint for it.
- **Pitfall 2:** changing a list or dict in place doesn't notify subscribers. Provide reactive collections, or document the rule.
- **Decided:** the value lives in Python; each signal holds an NSH `Signal<()>` trigger so NSH's graph tracks dependencies (`docs/architecture.md`). Done: `.value`, `@nsh.computed` (cached in Python), `.map`, handler decorators `@count.updater` / `@items.mutator` and `count.setter(v)`; lambdas still work everywhere. Also done: the engine-thread queue (`nsh.call_soon`, writes from worker threads), `@nsh.effect`, `nsh.set_timeout` / `nsh.set_interval`: `docs/architecture.md`.

## Roadmap
1. ✅ Skeleton (maturin, PyO3, NSH pinned) and research briefs.
2. ✅ Spike: `nsh.run()` window + Ctrl-C (Linux), Python trees (view/text/button, `class_`, `on_press`), `nsh.signal` + counter, headless pytest via `nsh-testing` (`nsh.testing.open`). Signal design decided: see `docs/architecture.md`.
3. CI matrix written (`.github/workflows/ci.yml`) but never run (no remote yet). macOS/Windows builds unverified; Ctrl-C there not wired.
4. `CONTRIBUTING.md`, a `doctor.py` setup checker, and setup guides for each OS.
5. Before the sprint: Input and List bindings, reference styled components in Python, an issue list and a dry run on each OS.
6. ✅ Wheels (`.github/workflows/`, never run on GitHub yet): `release.yml` builds abi3 wheels (macOS arm64/x86_64, Windows x64, Linux x86_64 tagged `linux_x86_64`, needs system GTK 4.14+) plus an sdist on `v*` tags and publishes them to GitHub Releases only (no PyPI, experimental). Users run `uv pip install nsh-py --no-index --find-links https://github.com/lucianosrp/nsh-py/releases/expanded_assets/latest` (`latest` is a rolling prerelease). `dev-core.yml` keeps a rolling `dev-core` prerelease of `main` (wheels + `manifest.json` with the Rust `source_hash`); `tools/fetch_core.py` pulls its compiled core into `python/nsh/` so Python-only contributors need no Rust, and `tools/run.py` runs examples against the checkout.
