"""`separator`: A horizontal or vertical separator line"""

from __future__ import annotations

from nsh._element import Element, StrProp, merge_class
from nsh.primitives import view

HORIZONTAL_CLASS = "h-px w-full bg-border"
"""A horizontal separator spans its container and is one pixel high."""

VERTICAL_CLASS = "w-px h-full bg-border"
"""A vertical separator spans its container and is one pixel wide."""


def separator(
    *,
    vertical: bool = False,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A separator: A horizontal line, or a vertical one when `vertical` is true.

    `class_` adds Tailwind classes after the default look, so they win.

        nsh.view(
            nsh.text("Above"),
            nsh.separator(),
            nsh.text("Below"),
        )
    """
    base_class = VERTICAL_CLASS if vertical else HORIZONTAL_CLASS
    return view(
        class_=merge_class(base_class, class_),
        test_id=test_id,
    )
