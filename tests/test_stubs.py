"""python/nsh/_core.pyi must list what the Rust extension exports."""

import ast
import pathlib

from nsh import _core

STUB = pathlib.Path(__file__).parent.parent / "python" / "nsh" / "_core.pyi"


def test_core_stub_matches_extension():
    tree = ast.parse(STUB.read_text())
    stubbed = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    stubbed |= {t.id for n in tree.body if isinstance(n, ast.AnnAssign) for t in [n.target]}
    exported = {n for n in dir(_core) if not n.startswith("_")} | {"__version__"}
    assert exported - stubbed == set(), "add these to python/nsh/_core.pyi"
    assert stubbed - exported == set(), "remove these from python/nsh/_core.pyi"
