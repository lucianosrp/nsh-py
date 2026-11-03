"""Tests for tools/new.py (the component and primitive scaffolder).

They run on a temporary copy of the files the tool edits: nothing in the
real tree changes, and no extension is needed.
"""

from __future__ import annotations

import ast
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("nsh_new", ROOT / "tools" / "new.py")
assert _spec is not None and _spec.loader is not None
new = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = new
_spec.loader.exec_module(new)

EDITED = [
    "python/nsh/__init__.py",
    "python/nsh/components/__init__.py",
    "python/nsh/primitives/__init__.py",
    "src/elements/mod.rs",
]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel in EDITED:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest)
    return tmp_path


def read(repo: Path, rel: str) -> str:
    return (repo / rel).read_text(encoding="utf-8")


def all_of(source: str) -> list[str]:
    """The `__all__` list of a module's source."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "__all__":  # type: ignore[attr-defined]
            return ast.literal_eval(node.value)
    raise AssertionError("no __all__")


def test_component_writes_files_and_exports(repo):
    touched = new.scaffold("component", "badge", repo)
    assert {p.relative_to(repo).as_posix() for p in touched} == {
        "python/nsh/components/badge.py",
        "tests/components/test_badge.py",
        "python/nsh/components/__init__.py",
        "python/nsh/__init__.py",
    }
    comp = read(repo, "python/nsh/components/__init__.py")
    assert "from nsh.components.badge import badge\n" in comp
    # Imports stay in alphabetical order, and so does __all__.
    assert comp.index("badge import") < comp.index("button import")
    assert all_of(comp) == sorted(all_of(comp))
    top = read(repo, "python/nsh/__init__.py")
    assert "from nsh.components import badge, button, card, table\n" in top
    names = all_of(top)
    assert names.index("badge") == names.index("__version__") + 1
    assert names.index("badge") < names.index("button")


def test_generated_python_is_valid_and_has_a_docstring_example(repo):
    new.scaffold("component", "badge", repo)
    for rel in ("python/nsh/components/badge.py", "tests/components/test_badge.py"):
        ast.parse(read(repo, rel))
    source = read(repo, "python/nsh/components/badge.py")
    assert "def badge(" in source
    assert 'nsh.badge(nsh.text("Hello")' in source


def test_primitive_writes_files_and_registers_the_kind(repo):
    touched = new.scaffold("primitive", "image", repo)
    assert {p.relative_to(repo).as_posix() for p in touched} == {
        "python/nsh/primitives/image.py",
        "tests/primitives/test_image.py",
        "src/elements/image.rs",
        "python/nsh/primitives/__init__.py",
        "python/nsh/__init__.py",
        "src/elements/mod.rs",
    }
    prims = read(repo, "python/nsh/primitives/__init__.py")
    assert "from nsh.primitives.image import KIND as _IMAGE\n" in prims
    assert "from nsh.primitives.image import image\n" in prims
    assert "KINDS = frozenset({_IMAGE, _INPUT, _SCROLL, _TEXT, _VIEW})" in prims
    assert all_of(prims) == sorted(all_of(prims), key=lambda n: (not n.isupper(), n))
    mod = read(repo, "src/elements/mod.rs")
    assert "mod image;\nmod input;\n" in mod
    assert '    ("image", image::build),\n    ("input", input::build),\n' in mod
    assert "from nsh.primitives import image, input, scroll, text, view\n" in read(
        repo, "python/nsh/__init__.py"
    )
    for rel in ("python/nsh/primitives/image.py", "tests/primitives/test_image.py"):
        ast.parse(read(repo, rel))
    assert "pub(super) fn build(" in read(repo, "src/elements/image.rs")


def test_names_sort_to_the_end_too(repo):
    new.scaffold("component", "zebra", repo)
    new.scaffold("primitive", "zoom", repo)
    comp = read(repo, "python/nsh/components/__init__.py")
    assert comp.rindex("zebra") > comp.index("table")
    assert all_of(comp)[-1] == "zebra"
    mod = read(repo, "src/elements/mod.rs")
    assert mod.index("mod zoom;") > mod.index("mod view;")
    assert mod.index('("zoom", zoom::build)') > mod.index('("view", view::build)')


def test_two_scaffolds_in_a_row(repo):
    new.scaffold("component", "badge", repo)
    new.scaffold("component", "alert", repo)
    assert all_of(read(repo, "python/nsh/components/__init__.py")) == [
        "alert",
        "badge",
        "button",
        "card",
        "table",
    ]


def test_it_never_overwrites(repo):
    new.scaffold("component", "badge", repo)
    before = {rel: read(repo, rel) for rel in EDITED}
    # The component's file exists: refuse, and change nothing else.
    with pytest.raises(new.ScaffoldError, match="already exists"):
        new.scaffold("component", "badge", repo)
    (repo / "tests" / "components" / "test_alert.py").write_text("keep me", encoding="utf-8")
    with pytest.raises(new.ScaffoldError, match="not overwriting"):
        new.scaffold("component", "alert", repo)
    assert read(repo, "tests/components/test_alert.py") == "keep me"
    assert not (repo / "python" / "nsh" / "components" / "alert.py").exists()
    assert {rel: read(repo, rel) for rel in EDITED} == before


def test_existing_public_names_are_refused(repo):
    for name in ("card", "view", "signal", "run"):
        with pytest.raises(new.ScaffoldError, match="already exists"):
            new.scaffold("component", name, repo)


@pytest.mark.parametrize(
    "name", ["Badge", "my-badge", "2fast", "_private", "a__b", "badge_", "", "bad name"]
)
def test_bad_names_are_refused(repo, name):
    with pytest.raises(new.ScaffoldError, match="not a good name"):
        new.scaffold("component", name, repo)


@pytest.mark.parametrize("name", ["class", "list", "type", "print", "match"])
def test_python_keywords_and_builtins_are_refused(repo, name):
    with pytest.raises(new.ScaffoldError, match="keyword or builtin"):
        new.scaffold("component", name, repo)


def test_rust_keywords_are_refused_for_primitives_only(repo):
    with pytest.raises(new.ScaffoldError, match="Rust keyword"):
        new.scaffold("primitive", "impl", repo)
    new.scaffold("component", "impl", repo)  # fine in Python


def test_main_prints_next_steps_and_exit_codes(repo, capsys):
    assert new.main(["component", "badge", "--root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "python/nsh/components/badge.py" in out
    assert "Next:" in out
    assert new.main(["component", "badge", "--root", str(repo)]) == 1
    assert "error:" in capsys.readouterr().err
