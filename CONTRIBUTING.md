# Contributing to nsh-py

This page gets you from a fresh clone to a merged PR: setup, the workflow,
two walkthroughs and the PR checklist.
[docs/architecture.md](docs/architecture.md) explains how the pieces fit.

## Setup

Pick the path for what you'll change. Both end with tests passing and a
window opening.

### Python only: no Rust, no LLVM, no GTK dev packages

CI keeps a prebuilt core of `main` (the compiled extension) on the `dev-core`
release. You download it once and run everything straight from the checkout.

1. Install [uv](https://docs.astral.sh/uv/) and Git. On Linux you also need the GTK 4 and GStreamer
   *runtime* (GTK 4.14+, Ubuntu 24.04+, Debian 13, Fedora 40+, Arch; on Ubuntu
   `sudo apt install libgtk-4-1 libgstreamer1.0-0 libgstreamer-plugins-base1.0-0`). macOS needs 14+ and Windows 10 1809+.
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

### Python + Rust, or platform work: build the extension yourself

1. Install [uv](https://docs.astral.sh/uv/) and Git.
2. Install the platform requirements:
   - **Linux:** GTK 4.14+ and glibc 2.39+ (Ubuntu 24.04+, Debian 13, Fedora 40+, Arch),
     plus `clang` and the GTK and GStreamer dev packages: `sudo apt install clang libclang-dev libgtk-4-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev`.
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

1. Pick an issue and comment that you're on it. The labels say what it needs:
   `python-only` (and `good-first-issue`), `python+rust`, or `platform`
   (a macOS or Windows machine).
2. Branch: `git switch -c <short-topic>`.
3. Make the change in the right place. `tools/new.py` writes a starting
   point for a component or a primitive (the walkthroughs below).
4. Test, lint and look at it (the commands are just below).
5. Open a PR with a screenshot if it changes what you see, and go through
   the [PR checklist](#pr-checklist).

## Orientation

**The rule: behaviour goes in Rust, look and composition go in Python.**
A button that opens a dialog needs Rust. A button with rounded corners and
the primary colour is Python.

Components live in `python/nsh/components/` (most contributions).
Primitives live in `python/nsh/primitives/<kind>.py` and pair with
`src/elements/<kind>.rs`. Tests are in `tests/components/` and
`tests/primitives/`, examples in `examples/`.

A component builds a tree out of primitives (`view`, `text`) and Tailwind
classes. A primitive is an element kind the Rust side knows how to build.
`docs/architecture.md` has the full layout and the threading model.

The commands you'll use (the same on macOS, Windows and Linux):

```sh
uv run pytest -q tests                    # headless: no window needed
uv run python examples/counter.py         # open a window
uvx ruff@0.15.12 check --fix . && uvx ruff@0.15.12 format .   # lint and format the Python
cargo fmt && cargo clippy -- -D warnings  # only if you touched Rust
uv run --no-project python tools/new.py component avatar   # start a new component
```

CI runs the same two `ruff` commands (without `--fix`), so run them before
you push. Optional: `.pre-commit-config.yaml` runs them (and `cargo fmt`)
on every commit: `uv tool install pre-commit && pre-commit install`.

`uv run` builds the Rust extension by itself the first time (a few
minutes), and again whenever `src/**/*.rs`, `Cargo.*` or `pyproject.toml`
change. It uses the dev profile, so a Rust edit costs about 1–3 seconds.
You never run `maturin` by hand.

**No Rust installed?** If you only touch Python, skip the build: fetch the
prebuilt core once with `uv run --no-project python tools/fetch_core.py`, then
run `uv run --no-project --with pytest pytest -q tests` and
`uv run --no-project python tools/run.py examples/counter.py`. [Setup](#setup)
has the details and says when the core is out of date.

## Walkthrough A: add a component (Python only)

**Quick start:** `uv run --no-project python tools/new.py component avatar`
writes `python/nsh/components/avatar.py` and `tests/components/test_avatar.py`,
and adds the exports (steps 1 to 3 below). It never overwrites a file. Then
fill in the TODOs. The steps below show what it writes.

We'll add `card`, a bordered surface with an optional title and
description. The finished code is in the repo (`python/nsh/components/card.py`,
`tests/components/test_card.py`, `examples/card.py`). For your own
component, replace `card` with its name.

### 1. Write `python/nsh/components/card.py`

```python
"""`card`: a bordered, padded surface with an optional title and description."""

from __future__ import annotations

from nsh._element import Child, Element, Prop, merge_class
from nsh.primitives import text, view

CLASS = "rounded-xl border border-border bg-card p-6 gap-2"
"""The card's own classes; the caller's `class_` comes after and wins."""

TITLE_CLASS = "text-lg font-semibold text-card-foreground"
DESCRIPTION_CLASS = "text-sm text-muted-foreground"


def card(
    *children: Child,
    title: Prop[str] | None = None,
    description: Prop[str] | None = None,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """A card: an optional `title` and `description`, then `children`.

    `title` and `description` take a string or a callable (a binding).
    `class_` adds Tailwind classes after the default look, so they win.

        nsh.card(
            nsh.button("Save"),
            title="Profile",
            description="Shown to other people.",
            class_="w-80",
        )
    """
    header: list[Child] = []
    if title is not None:
        header.append(text(title, class_=TITLE_CLASS))
    if description is not None:
        header.append(text(description, class_=DESCRIPTION_CLASS))
    return view(
        *header,
        *children,
        class_=merge_class(CLASS, class_),
        test_id=test_id,
    )
```

What to notice:

- A component is a plain function returning an `Element`, built from the
  `view` and `text` primitives. The classes live in module constants, so
  tests can import them.
- `merge_class(CLASS, class_)` puts the caller's classes after ours, so
  `class_="w-80"` wins. It keeps a callable `class_` bound.
- `title` and `description` are `Prop[str]`: a string, or a callable that
  `text` binds. `title=lambda: f"Hello, {name()}"` updates by itself.
- `props(...)` (`nsh._element`) drops props left at `None`. `view` already
  does that, so `card` doesn't need it; use it to build an `Element`
  directly, as `button` does.

### 2. Export it

(`tools/new.py` does this for you.) In `python/nsh/components/__init__.py`, add
`from nsh.components.card import card` and `"card"` to `__all__`. In
`python/nsh/__init__.py`, change the import to
`from nsh.components import button, card` and add `"card"` to `__all__`
(kept sorted).

### 3. Write `tests/components/test_card.py`

Test the props first (instant, no app), then run it for real:

```python
import nsh
from nsh.components.card import CLASS
from nsh.testing import open


def test_card_props():
    c = nsh.card(title="Profile", class_="w-80", test_id="profile")
    assert c.kind == "view"
    assert c.props == {"class_": f"{CLASS} w-80", "test_id": "profile"}
    (title,) = c.children
    assert title.props["content"] == "Profile"


def test_card_bound_title_updates():
    def App():
        name = nsh.signal("Ada")
        return nsh.card(
            nsh.button("Rename", on_press=lambda: name.set("Grace"), test_id="rename"),
            title=lambda: f"Hello, {name()}",
        )

    with open(App) as app:
        assert app.shows("Hello, Ada")
        app.press("id:rename")
        app.wait_for("Hello, Grace")
        assert not app.shows("Hello, Ada")
```

Create the signal *inside* `App`: the app builds it when it starts. The
real file has a few more tests (no title, a bound `class_`).

### 4. Add an example and run everything

`examples/card.py` shows a card with a bound title and a button. Keep
examples small: one idea each.

```sh
uv run pytest -q tests
uv run python examples/card.py
```

Then open a PR with a screenshot (see the [PR checklist](#pr-checklist)).

## Walkthrough B: add a primitive (Python + Rust)

**Quick start:** `uv run python tools/new.py primitive slider` writes
`src/elements/slider.rs`, `python/nsh/primitives/slider.py` and
`tests/primitives/test_slider.py`, and registers the kind (steps 2 and 4
below). The Rust builds a plain `view` for now: replace it with the NSH
builder you want to wrap (step 1). It never overwrites a file.

A primitive is a new element kind. We'll use `input`, a text field. The
finished code is in the repo (`src/elements/input.rs`,
`python/nsh/primitives/input.py`, `tests/primitives/test_input.py`,
`examples/form.py`); the snippets below are simplified (the real `input`
also takes `disabled`, and a signal as `value`). To check a call against
NSH's source, which matches our pin:
`~/.cargo/registry/src/index.crates.io-*/nsh-core-0.7.0/src/element/host.rs`
(`pub fn input`, `impl Input`; on Windows, `%USERPROFILE%\.cargo\registry\src\`).
Binding an nsh-base component (a checkbox, tabs, a dialog) works a little
differently: see "Binding nsh-base components" in `docs/architecture.md`,
and copy `src/elements/checkbox.rs`.

NSH's `Input` has `.value(text)` (controlled), `.default_value(text)`,
`.placeholder(text)`, `.on_change(|text: &str| ..)` and `.on_submit(..)`.
It is `Interactive` and `Accessible`, so `props::common` (`class_`,
`on_press`, `role`, `test_id`) works on it. The `kind` string and the
`props` dict are the whole contract: Python writes them, `build` reads them.

### 1. The Rust builder: `src/elements/input.rs`

```rust
//! `input`: a text field (`nsh.input`). Props: `value`, `placeholder`
//! (a string or a callable), `on_change` and `on_submit` (called with the text).

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{bridge, props};

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = props::common(input(), props)?;
    if let Some(v) = props::get(props, "value")? {
        // `.value()` wants `IntoReactive<String>`, `props::string` gives a
        // `Reactive<SharedString>`: you may need a small conversion.
        el = el.value(props::string(&v)?);
    }
    if let Some(p) = props::get(props, "placeholder")? {
        el = el.placeholder(props::string(&p)?);
    }
    if let Some(h) = props::get(props, "on_change")? {
        el = el.on_change(with_text(h.unbind()));
    }
    if let Some(h) = props::get(props, "on_submit")? {
        el = el.on_submit(with_text(h.unbind()));
    }
    Ok(el.into_element())
}

/// A listener calling the Python `handler` with the text. It must be
/// `'static` but not `Send`, so it can hold the `Py<PyAny>`.
fn with_text(handler: Py<PyAny>) -> impl Fn(&str) + 'static {
    move |text: &str| {
        let text = text.to_owned();
        bridge::call(|py| handler.call1(py, (text,)).map(drop));
    }
}
```

`view.rs` and `text.rs` next to it are the smallest real examples.

### 2. Register it in `KINDS`

In `src/elements/mod.rs`, add `mod input;` and one entry. The name is the
`kind` string Python uses:

```rust
const KINDS: &[(&str, Build)] = &[
    ("input", input::build),
    ("text", text::build),
    ("view", view::build),
];
```

### 3. The Python primitive: `python/nsh/primitives/input.py`

```python
"""`input`: a text field. Rust: src/elements/input.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import Element, Prop, props

KIND = "input"


def input(  # noqa: A001
    *,
    value: Prop[str] | None = None,
    placeholder: Prop[str] | None = None,
    on_change: Callable[[str], Any] | None = None,
    on_submit: Callable[[str], Any] | None = None,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """A text field: `nsh.input(value=name, on_change=name.set)`."""
    return Element(
        KIND,
        props(value=value, placeholder=placeholder, on_change=on_change,
              on_submit=on_submit, class_=class_, test_id=test_id),
        [],
    )
```

### 4. Add it to `primitives.KINDS` and export it

In `python/nsh/primitives/__init__.py`, import `KIND as _INPUT` and `input`,
add `_INPUT` to `KINDS` and `"input"` to `__all__`. Then export `input` from
`python/nsh/__init__.py`. `tests/test_kinds.py` fails if the Python and
Rust lists of kinds differ, which catches a forgotten step 2 or 4.

### 5. Test it: `tests/primitives/test_input.py`

```python
import nsh
from nsh.testing import open


def test_input_is_controlled():
    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(value=name, on_change=name.set, test_id="name"),
            nsh.text(lambda: f"Hello, {name()}"),
        )

    with open(App) as app:
        app.type_text("id:name", "Ada")
        app.wait_for("Hello, Ada")
```

`type_text` is in `nsh.testing.App` (a method next to `press` in
`src/headless.rs`, and a thin one in `python/nsh/testing.py`): a `"\n"` in
the text is the Enter key, and `app.value("id:name")` reads what an input
holds. If your primitive needs another nsh-testing driver call, add it the
same way in the same PR.

### 6. Build and check

`uv run pytest -q tests` rebuilds the extension (a Rust compile error shows
up in its output). Then `cargo fmt && cargo clippy -- -D warnings`.

## Conventions

- **Docstrings.** Every public function gets one: a line, what the
  arguments mean, then a short example indented as in `card` above.
- **Tailwind via `class_`.** Style with class strings (`"p-4 gap-2
  flex-row"`); NSH parses them natively. Every styled element takes `class_`,
  a string or a callable (bound).
- **`merge_class` so the caller wins.** Your classes first, then theirs:
  `class_=merge_class(CLASS, class_)`. In NSH, a utility later in the
  class string wins over an earlier one that sets the same property (it's
  designed for exactly this, with no `tailwind-merge`; see the top of
  `src/tailwind/mod.rs` in `nsh-core`). Variants (`hover:`, `dark:`) apply
  after plain utilities.
- **`test_id` on interactive parts.** Give buttons, inputs and anything
  pressable a `test_id` parameter and pass it through, so tests can say
  `app.press("id:save")` instead of depending on a label that may change.
- **Theme tokens, not fixed colours.** Light and dark mode and custom
  themes only work if colours come from the theme. Prefer `bg-primary` to
  `bg-blue-500`, and check your component in a window before the PR.

The default theme (`src/default-theme.json` in the `nsh-base` crate, the
shadcn/ui set) defines these tokens. Use them as `bg-<token>`,
`text-<token>` or `border-<token>`:

- `background`, `foreground`: the page and its text
- `card`, `card-foreground`; `popover`, `popover-foreground`
- `primary`, `primary-foreground`: the main action (the button)
- `secondary`, `secondary-foreground`: a quieter action
- `muted`, `muted-foreground`: quiet surfaces and secondary text
- `accent`, `accent-foreground`: hover and selected states
- `destructive`: errors, delete
- `border`, `input`, `ring`: borders, field borders, the focus ring
- `chart-1` to `chart-5`, and `sidebar`, `sidebar-foreground`,
  `sidebar-primary`, `sidebar-primary-foreground`, `sidebar-accent`,
  `sidebar-accent-foreground`, `sidebar-border`, `sidebar-ring`

**Gotcha: `nsh.components.button` is the function, not the module.** The
package re-exports it (`from nsh.components.button import button`), which
rebinds the name `button` on the package. `nsh.primitives.view` and the
others work the same way. To reach a module's other names, import them from
the module itself:

```python
from nsh.components.button import CLASS        # works
from nsh.primitives.view import KIND           # works
import nsh.components.button as b; b.CLASS     # fails: b is the function
```

## Rules for Rust code

You only need these if you change `src/`. If you're unsure, ask a
maintainer.

- **Call Python only through `bridge::call`.** It attaches to Python and
  logs an exception instead of crashing: a failed handler does nothing, a
  failed binding shows an empty string.
- **Touch NSH only on the engine thread.** Builders, handlers and bindings
  already run there. NSH's reactive graph panics anywhere else.
- **Never hold the GIL while waiting on the engine.** Wrap blocking calls
  in `py.detach(|| ...)`. The engine needs the GIL to run your Python
  callbacks; if you hold it and wait, both sides wait forever.
- **Don't bump the NSH pins** (`=0.7.0`) in a feature PR. Bumps are
  deliberate, one PR each.
- **Never depend on the crates.io crate called `nsh`.** It's an unrelated
  shell. NSH's crates are `nsh-core`, `nsh-base` and so on.
- Rust 1.99.1 is pinned in `rust-toolchain.toml`; rustup fetches it for you.

## Writing tests

Tests run the app for real on NSH's engine thread, with no window, so they
work on any machine and in CI.

```python
import nsh
from nsh.testing import open


def test_counter():
    def App():
        count = nsh.signal(0)
        return nsh.view(
            nsh.text(lambda: f"Count: {count()}"),
            nsh.button("+1", on_press=lambda: count.update(lambda n: n + 1), test_id="inc"),
        )

    with open(App) as app:
        app.press("id:inc")
        app.wait_for("Count: 1")
        assert "Count: 1" in app.texts()
```

`open(root)` takes what `nsh.run` takes: a function returning an element.
Use it as a context manager so the engine stops at the end.

- `app.press(selector)`: press what the selector finds, then wait for the
  app to settle.
- `app.wait_for(selector, timeout=5.0)`: wait until the selector shows;
  raises `TimeoutError`. Use it after a press whose effect isn't immediate.
- `app.texts()`: the texts shown, in order.
- `app.shows(text)`: whether that text shows right now.

**Selectors:**

- `"id:inc"`: the element with `test_id="inc"`. Prefer this for presses.
- `"text:+1"`: an element showing that text. `"text:/regex/i"` is a regex.
- `"role:button[Save]"`: a button labelled "Save".
- `"Save"`: a bare string tries a test id, then a label, then a text.

A good component test has two parts: one on the props (`el.kind`,
`el.props`, `el.children`: no app, instant) and one with `open(...)` that
checks what shows and what a press does. See `tests/components/`.

## PR checklist

- [ ] `uv run pytest -q tests` passes.
- [ ] `ruff check` and `ruff format --check` pass (CI runs them).
- [ ] New components or primitives have a test, and a docstring with an example.
- [ ] Public names are exported from `nsh/__init__.py`.
- [ ] Rust changes pass `cargo fmt` and `cargo clippy -- -D warnings`.
- [ ] One topic per PR, and commits that each make sense on their own.

## Ground rules

- Be kind, and ask early: a maintainer would rather unblock you in five
  minutes than find out after an hour.
- Using an AI coding agent is fine. Point it at `AGENTS.md`, and review
  what it writes before you push.
