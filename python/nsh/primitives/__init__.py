"""Primitives: elements the Rust side builds, one module per kind.

Each module here pairs with `src/elements/<kind>.rs` and declares its
`KIND`. Adding one needs Rust: see CONTRIBUTING.md ("Add a primitive").
`tests/test_kinds.py` checks this list matches the Rust one.
"""

from nsh.primitives.checkbox import KIND as _CHECKBOX
from nsh.primitives.checkbox import checkbox
from nsh.primitives.image import KIND as _IMAGE
from nsh.primitives.image import image
from nsh.primitives.input import KIND as _INPUT
from nsh.primitives.input import input
from nsh.primitives.progress import KIND as _PROGRESS
from nsh.primitives.progress import progress
from nsh.primitives.scroll import KIND as _SCROLL
from nsh.primitives.scroll import scroll
from nsh.primitives.select import KIND as _SELECT
from nsh.primitives.select import select
from nsh.primitives.slider import KIND as _SLIDER
from nsh.primitives.slider import slider
from nsh.primitives.switch import KIND as _SWITCH
from nsh.primitives.switch import switch
from nsh.primitives.tab import KIND as _TAB
from nsh.primitives.tab import tab
from nsh.primitives.tabs import KIND as _TABS
from nsh.primitives.tabs import tabs
from nsh.primitives.text import KIND as _TEXT
from nsh.primitives.text import text
from nsh.primitives.video import KIND as _VIDEO
from nsh.primitives.video import video
from nsh.primitives.view import KIND as _VIEW
from nsh.primitives.view import view

# Note: `nsh.primitives.view` is the function, not the module (the import
# above rebinds it); import a module's other names from the module itself:
# `from nsh.primitives.view import KIND`.
KINDS = frozenset(
    {
        _CHECKBOX,
        _IMAGE,
        _INPUT,
        _PROGRESS,
        _SCROLL,
        _SELECT,
        _SLIDER,
        _SWITCH,
        _TAB,
        _TABS,
        _TEXT,
        _VIDEO,
        _VIEW,
    }
)
"""The element kinds the primitives build."""

__all__ = [
    "KINDS",
    "checkbox",
    "image",
    "input",
    "progress",
    "scroll",
    "select",
    "slider",
    "switch",
    "tab",
    "tabs",
    "text",
    "video",
    "view",
]
