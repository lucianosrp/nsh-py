# nsh-py sprint guide

Welcome! nsh-py lets you write native desktop UIs in plain Python, on top
of [Native Shell (NSH)](https://nsh.dev). This page gets you from zero to a
merged PR during the sprint. For how the code is organised, read
[docs/architecture.md](docs/architecture.md). For step-by-step recipes,
read [CONTRIBUTING.md](CONTRIBUTING.md).

> Date, venue and mentors: TBD.

## What we're building

```python
import nsh

def Counter():
    count = nsh.signal(0)
    return nsh.view(
        nsh.text(lambda: f"Count: {count()}", class_="text-xl"),
        nsh.button("+1", on_press=lambda: count.update(lambda n: n + 1)),
        class_="p-4 gap-2",
    )

nsh.run(Counter, title="Counter")
```

This already works on Linux: windows, Tailwind classes, buttons, signals
and headless tests. The sprint grows the set of components and gets
macOS and Windows to the same level.

## Pick your track

| Track | You need | Typical tasks | Issue label |
|---|---|---|---|
| **Python only** | Python | Styled components (card, badge, alert…), examples, docs, tests | `python-only`, `good-first-issue` |
| **Python + Rust** | Python, some Rust | New primitives (input, scroll, image, lists), new props and events | `python+rust` |
| **Platforms** | macOS or Windows machine | Make it build and run there, Ctrl-C, wheels | `platform` |

You don't need to know Rust for the first track. The rule of thumb:
**behaviour goes in Rust, look and composition go in Python.**

## Setup (do this before the sprint if you can)

Pick the path for your track. Both end with tests passing and a window opening.

### Python-only track: no Rust, no LLVM, no GTK dev packages

CI keeps a prebuilt core of `main` (the compiled extension) on the `dev-core`
release. You download it once and run everything straight from the checkout.

1. Install [uv](https://docs.astral.sh/uv/) and Git. On Linux you also need the GTK 4
   *runtime* (GTK 4.14+, Ubuntu 24.04+, Debian 13, Fedora 40+, Arch; on Ubuntu
   `sudo apt install libgtk-4-1`). macOS needs 14+ and Windows 10 1809+.
2. Clone the repo, then fetch the core and check it works:
   ```sh
   uv run --no-project python tools/fetch_core.py                   # downloads python/nsh/_core.*
   uv run --no-project --with pytest pytest -q tests                # headless tests
   uv run --no-project python tools/run.py examples/counter.py      # opens a window
   ```
   `tools/run.py` runs a script with `python/` on the import path (`nsh` isn't
   installed in this flow). `--no-project` stops uv from building the Rust extension.
3. If you branch from an old `main`, or someone changed Rust, `fetch_core.py` warns that your
   Rust differs from the prebuilt core. Rebase on `main` and fetch again (`--force` fetches
   even when the core looks current). If you need your own Rust, use the other path.

Python-only work stays in `python/nsh/components/`, `examples/` and `tests/`. Editing
`src/*.rs` needs the Rust path.

### Python + Rust and Platforms tracks: build the extension yourself

1. Install [uv](https://docs.astral.sh/uv/) and Git.
2. Install the platform requirements:
   - **Linux:** GTK 4.14+ and glibc 2.39+ (Ubuntu 24.04+, Debian 13, Fedora 40+, Arch),
     plus `clang` and the GTK dev package: `sudo apt install clang libclang-dev libgtk-4-dev`.
     Ubuntu 22.04 and Debian 12 are too old.
   - **macOS:** macOS 14+ and the Xcode Command Line Tools (`xcode-select --install`).
   - **Windows:** Windows 10 1809+, Visual Studio Build Tools (C++ workload), and LLVM
     (`winget install LLVM.LLVM`).
3. Install Rust from [rustup.rs](https://rustup.rs). The repo pins the version in
   `rust-toolchain.toml`, and rustup fetches it the first time you build.
4. Clone the repo and check it works:
   ```sh
   uv run pytest -q tests            # first run builds the extension (a few minutes)
   uv run python examples/counter.py # opens a window
   ```

`tools/doctor.py` checks this path's requirements. Don't mix the two paths in one checkout
without a reason: a fetched core in `python/nsh/` is overwritten by `uv run`'s build, and
`fetch_core.py` overwrites a local build (it tells you).

## Workflow

1. Pick an issue with your track's label and comment that you're on it.
2. Branch: `git switch -c <short-topic>`.
3. Make the change in the right place. To start from a template, run
   `uv run --no-project python tools/new.py component <name>` (or
   `... primitive <name>`): it writes the files below and adds the exports.
   - **Component (Python only):** `python/nsh/components/<name>.py`, export it in
     `components/__init__.py` and `nsh/__init__.py`, and test it in
     `tests/components/test_<name>.py`.
   - **Primitive (Python + Rust):** `src/elements/<kind>.rs` plus one line in `KINDS`
     (`src/elements/mod.rs`), then `python/nsh/primitives/<kind>.py` and
     `tests/primitives/test_<kind>.py`.
4. Test it:
   ```sh
   uv run pytest -q tests                  # headless: no window needed
   uv run python examples/<example>.py     # look at it for real
   uvx ruff@0.15.12 check --fix . && uvx ruff@0.15.12 format .   # Python lint + format
   cargo fmt && cargo clippy -- -D warnings  # if you touched Rust
   ```
5. Open a PR with a screenshot if it changes what you see.

## Tests

Tests run headless: the app runs for real, without a window.

```python
from nsh.testing import open

def test_card_shows_title():
    with open(lambda: nsh.card("Hello")) as app:
        assert app.shows("Hello")
        app.press("id:close")     # or press("Close"), press("role:button[Close]")
        app.wait_for("Closed")
```

## PR checklist

- [ ] `uv run pytest -q tests` passes.
- [ ] `ruff check` and `ruff format --check` pass (CI runs them).
- [ ] New components or primitives have a test, and a docstring with an example.
- [ ] Public names are exported from `nsh/__init__.py`.
- [ ] Rust changes pass `cargo fmt` and `cargo clippy -- -D warnings`.
- [ ] One topic per PR, and commits that each make sense on their own.

## Ground rules

- Be kind. Ask early: mentors would rather unblock you in five minutes than
  find out after an hour.
- Don't bump the NSH version pins (`=0.3.0`) in a sprint PR. Bumps are
  deliberate, one PR each.
- Never add the crates.io crate called `nsh`: it's an unrelated shell. NSH's
  crates are `nsh-core`, `nsh-base` and so on.
- Rust code calls Python only through `bridge::call`, and touches NSH only on
  the engine thread. If you're unsure, ask a maintainer.
- Using an AI coding agent is fine. Point it at `AGENTS.md`, and review
  what it writes before you push.
