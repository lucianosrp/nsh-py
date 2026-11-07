"""Primitives: elements the Rust side builds, one module per kind.

Each module here pairs with `src/elements/<kind>.rs` and declares its
`KIND`. Adding one needs Rust: see CONTRIBUTING.md ("Add a primitive").
`tests/test_kinds.py` checks this list matches the Rust one.
"""

from nsh.primitives.input import KIND as _INPUT
from nsh.primitives.input import input
from nsh.primitives.scroll import KIND as _SCROLL
from nsh.primitives.scroll import scroll
from nsh.primitives.text import KIND as _TEXT
from nsh.primitives.text import text
from nsh.primitives.view import KIND as _VIEW
from nsh.primitives.view import view

# Note: `nsh.primitives.view` is the function, not the module (the import
# above rebinds it); import a module's other names from the module itself:
# `from nsh.primitives.view import KIND`.
KINDS = frozenset({_INPUT, _SCROLL, _TEXT, _VIEW})
"""The element kinds the primitives build."""

__all__ = ["KINDS", "input", "scroll", "text", "view"]
