#!/usr/bin/env python3
"""Scaffold a new component or primitive.

Usage:
    uv run --no-project python tools/new.py component avatar
    uv run --no-project python tools/new.py primitive slider

A component (Python only) writes:
    python/nsh/components/avatar.py
    tests/components/test_avatar.py
and adds the exports to python/nsh/components/__init__.py and
python/nsh/__init__.py.

A primitive (Python + Rust) writes:
    python/nsh/primitives/slider.py
    tests/primitives/test_slider.py
    src/elements/slider.rs
and adds it to `KINDS` in src/elements/mod.rs and in
python/nsh/primitives/__init__.py, and exports it from python/nsh/__init__.py.

It never overwrites a file: if anything it would write already exists, it
stops before changing anything. Standard library only, and the same on
macOS, Windows and Linux.
"""

from __future__ import annotations

import argparse
import builtins
import keyword
import re
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINE_LENGTH = 100

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# Words Rust won't accept as a module name (the primitive's `src/elements/<name>.rs`).
RUST_KEYWORDS = frozenset(
    "as async await break const continue crate dyn else enum extern false fn for if impl in "
    "let loop match mod move mut pub ref return self static struct super trait true type "
    "unsafe use where while abstract become box do final macro override priv try typeof "
    "unsized virtual yield".split()
)

# --- templates -------------------------------------------------------------

COMPONENT_PY = '''\
"""`{name}`: TODO one line about what it looks like."""

from __future__ import annotations

from nsh._element import Child, Element, StrProp, merge_class
from nsh.primitives import view

CLASS = "rounded-md border border-border bg-card p-2 gap-2"
"""The {name}'s own classes; the caller's `class_` comes after and wins."""


def {name}(
    *children: Child,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A {name}: TODO what it shows, then `children`.

    `class_` adds Tailwind classes after the default look, so they win.

        nsh.{name}(nsh.text("Hello"), class_="w-80")
    """
    return view(
        *children,
        class_=merge_class(CLASS, class_),
        test_id=test_id,
    )
'''

COMPONENT_TEST = '''\
"""The {name} component."""

import nsh
from nsh.components.{name} import CLASS
from nsh.testing import open


def test_{name}_props():
    el = nsh.{name}(nsh.text("hi"), class_="w-80", test_id="{name}")
    assert el.kind == "view"
    assert el.props == {{"class_": f"{{CLASS}} w-80", "test_id": "{name}"}}
    (child,) = el.children
    assert child.props["content"] == "hi"


def test_{name}_shows_its_children():
    with open(lambda: nsh.{name}(nsh.text("Hello"))) as app:
        assert app.shows("Hello")
'''

PRIMITIVE_PY = '''\
"""`{name}`: TODO one line. Rust: src/elements/{name}.rs."""

from __future__ import annotations

from nsh._element import Child, Element, Handler, StrProp, props

KIND = "{name}"


def {name}(
    *children: Child,
    class_: StrProp | None = None,
    on_press: Handler | None = None,
    test_id: str | None = None,
) -> Element:
    """A {name}: TODO what it is and what the arguments mean.

    `class_` takes Tailwind classes: `"p-4 gap-2"`.

        nsh.{name}(class_="p-4")
    """
    return Element(KIND, props(class_=class_, on_press=on_press, test_id=test_id), list(children))
'''

PRIMITIVE_RS = """\
//! `{name}`: TODO one line (`nsh.{name}`). Props: `class_`, `on_press`, `test_id`.

use nsh_core::prelude::*;
use pyo3::{{prelude::*, types::PyDict}};

use crate::{{props, tree}};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {{
    // TODO: this is a plain `view` so the new kind builds and the tests pass.
    // Swap it for the NSH builder you want to wrap. NSH's source matches our
    // pin: ~/.cargo/registry/src/index.crates.io-*/nsh-core-0.5.0/src/element/host.rs
    let mut el = props::common(view(), props)?;
    for child in tree::children(py, children)? {{
        el = el.child(child);
    }}
    Ok(el.into_element())
}}
"""

PRIMITIVE_TEST = '''\
"""The {name} primitive."""

import nsh
from nsh.testing import open


def test_{name}_props():
    el = nsh.{name}(nsh.text("hi"), class_="p-4", test_id="{name}")
    assert el.kind == "{name}"
    assert el.props == {{"class_": "p-4", "test_id": "{name}"}}
    (child,) = el.children
    assert child.kind == "text"


def test_{name}_builds_and_shows_its_children():
    with open(lambda: nsh.{name}(nsh.text("Hello"))) as app:
        assert app.shows("Hello")
'''


# --- small helpers ---------------------------------------------------------


class ScaffoldError(Exception):
    """A problem to show the user (not a bug in this script)."""


def _sort_key(name: str) -> tuple[int, str]:
    """Constants first, then Classes, then the rest (what ruff's isort does)."""
    if name.isupper() and len(name) > 1:
        return (0, name)
    if name[:1].isupper():
        return (1, name)
    return (2, name)


def _render_list(items: list[str], open_: str, close: str, multiline: bool, prefix: str) -> str:
    """`prefix` + `open_` + the quoted/plain items + `close`, one line if it fits."""
    one = f"{prefix}{open_}{', '.join(items)}{close}"
    if not multiline and len(one) <= LINE_LENGTH:
        return one
    body = "".join(f"    {item},\n" for item in items)
    return f"{prefix}{open_}\n{body}{close}"


def _quote(name: str) -> str:
    return f'"{name}"'


def add_to_all(text: str, name: str) -> str:
    """Add `name` to the `__all__` list, before the first entry that sorts after it."""
    m = re.search(r"^__all__ = \[(.*?)\]", text, re.S | re.M)
    if not m:
        raise ScaffoldError("can't find `__all__ = [...]` to add the export to")
    items = re.findall(r'"([^"]+)"', m.group(1))
    if name in items:
        raise ScaffoldError(f"`{name}` is already in __all__")
    at = next((i for i, it in enumerate(items) if _sort_key(it) > _sort_key(name)), len(items))
    items.insert(at, name)
    multiline = "\n" in m.group(1)
    new = _render_list([_quote(i) for i in items], "[", "]", multiline, "__all__ = ")
    return text[: m.start()] + new + text[m.end() :]


def add_to_import(text: str, module: str, name: str) -> str:
    """Add `name` to the `from <module> import ...` statement."""
    pattern = re.compile(rf"^from {re.escape(module)} import (\([^)]*\)|[^\n(]+)$", re.M)
    m = pattern.search(text)
    if not m:
        raise ScaffoldError(f"can't find `from {module} import ...` to add `{name}` to")
    names = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", m.group(1))
    if name in names:
        raise ScaffoldError(f"`{name}` is already imported from {module}")
    names = sorted([*names, name], key=_sort_key)
    new = _render_list(names, "(", ")", "\n" in m.group(1), f"from {module} import ")
    if "\n" not in new:  # fits on one line: no parentheses
        new = f"from {module} import {', '.join(names)}"
    return text[: m.start()] + new + text[m.end() :]


# --- the edits ---------------------------------------------------------------


def edit_components_init(text: str, name: str) -> str:
    line = f"from nsh.components.{name} import {name}\n"
    imports = list(re.finditer(r"^from nsh\.components\.(\w+) import \w+\n", text, re.M))
    if not imports:
        raise ScaffoldError("can't find the component imports in components/__init__.py")
    after = next((m for m in imports if m.group(1) > name), None)
    at = after.start() if after else imports[-1].end()
    text = text[:at] + line + text[at:]
    return add_to_all(text, name)


def edit_nsh_init(text: str, name: str, package: str) -> str:
    text = add_to_import(text, f"nsh.{package}", name)
    return add_to_all(text, name)


def edit_primitives_init(text: str, name: str) -> str:
    const = f"_{name.upper()}"
    block = (
        f"from nsh.primitives.{name} import KIND as {const}\n"
        f"from nsh.primitives.{name} import {name}\n"
    )
    pairs = list(
        re.finditer(
            r"^from nsh\.primitives\.(\w+) import KIND as \w+\n"
            r"from nsh\.primitives\.\1 import \w+\n",
            text,
            re.M,
        )
    )
    if not pairs:
        raise ScaffoldError("can't find the primitive imports in primitives/__init__.py")
    after = next((m for m in pairs if m.group(1) > name), None)
    at = after.start() if after else pairs[-1].end()
    text = text[:at] + block + text[at:]

    m = re.search(r"^KINDS = frozenset\(\{(.*?)\}\)", text, re.S | re.M)
    if not m:
        raise ScaffoldError("can't find `KINDS = frozenset({...})` in primitives/__init__.py")
    consts = sorted({*re.findall(r"_\w+", m.group(1)), const})
    new = _render_list(consts, "{", "})", "\n" in m.group(1), "KINDS = frozenset(")
    text = text[: m.start()] + new + text[m.end() :]
    return add_to_all(text, name)


def edit_mod_rs(text: str, name: str) -> str:
    mods = list(re.finditer(r"^mod (\w+);\n", text, re.M))
    if not mods:
        raise ScaffoldError("can't find the `mod x;` lines in src/elements/mod.rs")
    after = next((m for m in mods if m.group(1) > name), None)
    at = after.start() if after else mods[-1].end()
    text = text[:at] + f"mod {name};\n" + text[at:]

    entries = list(re.finditer(r'^    \("(\w+)", \w+::build\),\n', text, re.M))
    if not entries:
        raise ScaffoldError("can't find the `KINDS` entries in src/elements/mod.rs")
    after = next((m for m in entries if m.group(1) > name), None)
    at = after.start() if after else entries[-1].end()
    return text[:at] + f'    ("{name}", {name}::build),\n' + text[at:]


# --- validation and orchestration -------------------------------------------


def check_name(kind: str, name: str, root: Path) -> None:
    if not NAME_RE.match(name):
        raise ScaffoldError(
            f"`{name}` is not a good name: use lowercase snake_case "
            "(letters, digits and single underscores, starting with a letter), like `avatar`"
        )
    if keyword.iskeyword(name) or keyword.issoftkeyword(name) or hasattr(builtins, name):
        raise ScaffoldError(
            f"`{name}` is a Python keyword or builtin: pick another name, for example `{name}_view`"
        )
    if kind == "primitive" and name in RUST_KEYWORDS:
        raise ScaffoldError(f"`{name}` is a Rust keyword: pick another name")
    if name == "testing" or name.startswith("_"):
        raise ScaffoldError(f"`{name}` is reserved: pick another name")
    init = (root / "python" / "nsh" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r"^__all__ = \[(.*?)\]", init, re.S | re.M)
    if m and name in re.findall(r'"([^"]+)"', m.group(1)):
        raise ScaffoldError(f"`nsh.{name}` already exists")


def plan(kind: str, name: str, root: Path) -> tuple[dict[Path, str], dict[Path, str]]:
    """(new files, edited files) as path -> content, without writing anything."""
    check_name(kind, name, root)
    py = root / "python" / "nsh"
    fmt = {"name": name}
    new: dict[Path, str] = {}
    edited: dict[Path, Callable[[str], str]] = {}

    if kind == "component":
        new[py / "components" / f"{name}.py"] = COMPONENT_PY.format(**fmt)
        new[root / "tests" / "components" / f"test_{name}.py"] = COMPONENT_TEST.format(**fmt)
        edited[py / "components" / "__init__.py"] = lambda t: edit_components_init(t, name)
        edited[py / "__init__.py"] = lambda t: edit_nsh_init(t, name, "components")
    else:
        new[py / "primitives" / f"{name}.py"] = PRIMITIVE_PY.format(**fmt)
        new[root / "tests" / "primitives" / f"test_{name}.py"] = PRIMITIVE_TEST.format(**fmt)
        new[root / "src" / "elements" / f"{name}.rs"] = PRIMITIVE_RS.format(**fmt)
        edited[py / "primitives" / "__init__.py"] = lambda t: edit_primitives_init(t, name)
        edited[py / "__init__.py"] = lambda t: edit_nsh_init(t, name, "primitives")
        edited[root / "src" / "elements" / "mod.rs"] = lambda t: edit_mod_rs(t, name)

    for path in new:
        if path.exists():
            raise ScaffoldError(f"{path.relative_to(root)} already exists: not overwriting it")
    changed: dict[Path, str] = {}
    for path, edit in edited.items():
        if not path.is_file():
            raise ScaffoldError(f"{path.relative_to(root)} is missing: is this the repo root?")
        changed[path] = edit(path.read_text(encoding="utf-8"))
    return new, changed


def scaffold(kind: str, name: str, root: Path = ROOT) -> list[Path]:
    """Write the new files and edits. Returns the paths touched. Nothing is
    written when anything is wrong."""
    new, changed = plan(kind, name, root)
    for path, content in new.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    for path, content in changed.items():
        path.write_text(content, encoding="utf-8", newline="\n")
    return [*new, *changed]


def next_steps(kind: str, name: str) -> str:
    if kind == "component":
        return (
            f"Next:\n"
            f"  1. Fill in python/nsh/components/{name}.py (TODOs, classes, docstring).\n"
            f"  2. Extend tests/components/test_{name}.py.\n"
            f"  3. uv run pytest -q tests\n"
            f"  4. Look at it: add examples/{name}.py and run it with uv run python.\n"
            f"  5. Open a PR with a screenshot (SPRINT.md has the checklist)."
        )
    return (
        f"Next:\n"
        f"  1. In src/elements/{name}.rs, replace the placeholder `view()` with the NSH builder.\n"
        f"  2. Give python/nsh/primitives/{name}.py its real props; read them in the Rust.\n"
        f"  3. Extend tests/primitives/test_{name}.py.\n"
        f"  4. uv run pytest -q tests  (this rebuilds the extension)\n"
        f"  5. cargo fmt && cargo clippy -- -D warnings\n"
        f"  6. Add examples/{name}.py, then open a PR (SPRINT.md has the checklist)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="new.py", description="Scaffold a new nsh component or primitive."
    )
    parser.add_argument("kind", choices=["component", "primitive"])
    parser.add_argument("name", help="snake_case name, like `avatar`")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        touched = scaffold(args.kind, args.name, args.root.resolve())
    except ScaffoldError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    root = args.root.resolve()
    print("Created or updated:")
    for path in touched:
        print(f"  {path.relative_to(root).as_posix()}")
    print()
    print(next_steps(args.kind, args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
