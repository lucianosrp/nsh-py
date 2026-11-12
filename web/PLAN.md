# nsh-py on the web: plan

Synthesis of four research reports (toolchain, loader/packaging/UX,
size/startup/runtime, alternative architectures) on top of the spike in
`web/README.md`. Estimates are marked *(est)*; everything else was
measured or checked in source.

## Where we are

The spike (route A) works: the counter runs in the browser as **one Pyodide
side module** (PyO3 + NSH + nsh-platform-web), rendered by NSH's DOM
backend, Python handlers and bindings live. Its costs were: nightly Rust
with `-Zbuild-std`, a 12.8 MB module (4.6 MB wheel, 3.2 MB brotli), a
global `WebAssembly.instantiate` hook, a patched `nsh.js`, a one-line
nsh-core fix.

## Decision: route A, made stable; keep B3 as the long-term watch item

| Route | What | Verdict |
|---|---|---|
| **A** one side module (spike) | Same Rust as desktop, built for emscripten | **Go.** Its biggest risk (nightly) goes away on Pyodide 314. |
| B1 two modules, our IR on stable wasm32-unknown-unknown | Python in Pyodide, NSH in its own wasm, JS glue by handle | Fallback if A's toolchain breaks again. 15-20 days *(est)*. |
| **B3** Python drives NSH's JS (TSX) API through Pyodide's FFI | Pure-Python web wheel, no Rust for the web | **Watch.** Smallest and on NSH's *promised* stable surface (the JS API, not Rust), but needs NSH's browser host, which is only on NSH main. Spike it (2-3 days) once NSH releases it. |
| C server renders, browser mounts | Engine on the server, mount batches over WebSocket | **No.** Layout and text measurement are engine-side, using the browser's fonts. |
| D transpile Python to JS | | **No.** Not "write Python" any more. |

For the future Streamlit-style layer: send our Element IR (already plain
`kind/props/children`) over a WebSocket to a browser running NSH (A or B3),
not route C.

## Key findings

**Toolchain: stable is possible.**
- Pyodide now versions by Python: **314.0.7** = Python 3.14, emscripten
  **5.0.3**, ABI `pyemscripten_2026_0`.
- Its Rust pin is **stable 1.93.0** (main: 1.97.1); no custom sysroot.
- Rust 1.93 made wasm exceptions the emscripten default, and 1.98 made them
  unconditional.
- maturin ≥ 1.16 handles the tags and the toolchain.
- `pyodide xbuildenv search` hid 314 from us only because pyodide-build ran
  on Python 3.13; the host must be 3.14.
- PEP 783 (Pyodide wheels on PyPI) is accepted. Whether pypi.org accepts
  `pyemscripten_*` today is unconfirmed.

**Size: 12.8 MB → about 5 MB *(est)*.**

| Item | Size |
|---|---|
| nsh-base components we never use (editor, text_view, data_table, diff, dock, plot) | ~3.4 MB of code |
| `two-face` syntax grammars | 0.92 MB of incompressible data |

Both come in because `nsh_base::registry()` registers all 34 components
and nsh-platform-web forces the `highlight` feature. NSH's own Rust web
apps are 3.3 MB.

Levers, in order of payoff:
1. A minimal registry, which needs a patched or upstreamed
   nsh-platform-web feature.
2. `opt-level="s"`, fat LTO, `codegen-units=1`, `panic=abort` (web only),
   `-Zlocation-detail=none` or `--remap-path-prefix`. This also stops our
   local paths leaking into panic strings.
3. `wasm-opt -Oz`: −8% raw, no brotli gain.

**Startup** (measured in Node, local files):
- Pyodide boot ~1.1 s; wheel load and instantiate ~0.2 s; import 8 ms.
- On a real network the wheel download dominates. Options:
  - shrink the wheel;
  - fetch it in parallel with Pyodide;
  - `loadPackage(url)` instead of micropip;
  - immutable hashed URLs;
  - a stored-zip wheel served with brotli.
- Pyodide memory snapshots: not worth it in the browser (experimental,
  build-locked).

**Loader.**
- Emscripten's side-module loader has no hook for extra import modules,
  so for now the hook stays. It should be scoped: installed only around
  `import nsh._core`, behind a mutex, restored in `finally`.
- The clean fix is upstream: on emscripten, declare NSH's imports as
  `env` imports.
- One wasm instance is one engine, so it's one app per Pyodide, with an
  iframe per app on shared pages.

**One Python API for desktop and web.**
- Pyodide has no threads, `time.sleep` freezes the page, and `nsh.run`
  can't block.
- The fix also closes our known desktop gap:
  - an **engine-thread queue**, `post(fn)`, safe from any thread, drained
    by an NSH `spawn` task through `bridge::call`;
  - `Trigger.notify` and off-engine drops go through it;
  - plus `nsh.call_soon` and `nsh.spawn(coro)`;
  - `async def` handlers on a small `NshLoop`;
  - `nsh.fetch` over NSH's network stack, the same on both targets.

**Testing.**
- nsh-testing's `Headless` is off on wasm. Its `Screen`,
  `ApproxTextEngine` and `LocalEngine` are not, so a `headless_web.rs`
  twin can run **the same pytest suite under Pyodide in Node**.
- Plus one Playwright smoke test and a size gate in CI.

## Phases

**Phase 0: make it real (~2 days)**
1. Python 3.14 pyodide-build venv; Pyodide 314.0.7 xbuildenv and
   emscripten 5.0.3.
2. Stable Rust 1.97.1 (Pyodide's CI pin) via `RUSTUP_TOOLCHAIN`; no
   `-Zbuild-std`. Try `pyodide build .` first, then the maturin recipe.
3. Run the ABI checks on the output:
   - legacy EH (`try` present, no `try_table`);
   - no `invoke_*`, `emscripten_longjmp` or `__wasm_setjmp`;
   - a panic-to-exception test.
4. Size: minimal registry (patched nsh-platform-web), size profile. Measure.
5. Retest the page on Pyodide 314.

**Phase 1: MVP**
- `nsh-py.js` `mount(el, {code|url|files, packages})`: scoped hook,
  lock-file wheel install, error overlay, `restart()`.
- Engine-thread queue and async: lands on **main**, since it's needed on
  desktop too.
- `python -m nsh.web serve app.py` (reload) and `build app.py -o dist/`
  (static, works on GitHub Pages).
  - `nsh.platform`; `title` maps to `document.title`.
  - Bonus: Python-only sprint contributors can preview components without
    GTK or Rust, using a prebuilt wheel.
- CI: non-blocking web job (build, Node pytest, Playwright smoke, size gate).
- A GitHub Pages demo.

**Phase 2: upstream and polish** (filing is public; needs a go-ahead)
- File with NSH:
  1. the `libc` fix (issue text drafted in the toolchain report);
  2. `player.imports()` / `player.attach({exports, memory})` plus
     `embedded` and `dispose()` in nsh.js;
  3. `env` imports on emscripten;
  4. a lean-registry or feature switch in nsh-platform-web.
- Then drop the hook, the patched `nsh.js` and the patched crates.
- Publish `pyemscripten` wheels (TestPyPI first) and an npm/jsDelivr
  package for the loader.

**Phase 3: docs and playground**
- `<nsh-py-app>` live examples, and an editor playground like NSH's
  `?playground`.
- Share links, posters; a separate origin for user code.

**Watch:** when NSH releases its browser host, run the B3 spike (2-3 days):
- **Success:** bound text and class update without re-running the root,
  and a handler exception is logged.
- **Kill:** function-valued props aren't reactive through the bridge.

## Open questions

- Does the build work on emscripten 5.0.3 with stable Rust? (Phase 0
  answers this.)
- Does pypi.org accept `pyemscripten_*` wheels today?
- Is `Module` visible from EM_JS code in a side module? This decides
  whether a no-hook loader is possible before upstream lands.
- What are the 257 exported symbols (about 25 in the plain Rust build)?
  They may be blocking dead-code removal.
