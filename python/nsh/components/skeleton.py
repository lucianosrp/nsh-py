"""`skeleton`: a pulsing placeholder while content loads."""

from __future__ import annotations

from nsh._element import Element, Prop, merge_class
from nsh.primitives import view

CLASS = "rounded-md bg-muted animate-pulse"


def skeleton(
    *,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """A rounded, muted placeholder that pulses while content loads.

    Set its size and shape with `class_`, a string or a callable binding.
    These classes come after the defaults, so they win; use `animate-none`
    for a still placeholder. Replace the skeleton when the content arrives.

        nsh.skeleton(class_="h-4 w-48")
        nsh.skeleton(class_="h-12 w-12 rounded-full")
    """
    return view(class_=merge_class(CLASS, class_), test_id=test_id)
