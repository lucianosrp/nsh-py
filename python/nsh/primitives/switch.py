"""`switch`: nsh-base's Switch. Rust: src/elements/switch.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import BoolProp, Child, Element, StrProp, props
from nsh.primitives import _toggle
from nsh.primitives.text import text

KIND = "switch"

TRACK_CLASS = (
    "h-5 w-9 rounded-full p-0.5 bg-input transition-colors checked:bg-primary disabled:opacity-50"
)
"""The track. `checked:` and `disabled:` follow the switch."""

THUMB_CLASS = "h-4 w-4 rounded-full bg-background transition-transform checked:translate-x-4"
"""The thumb, inside the track: `checked:` moves it to the end."""

LABEL_CLASS = "ml-2 text-sm"
"""The label, after the track (the switch lays them out in a row)."""


def switch(
    label: StrProp | None = None,
    *,
    checked: BoolProp | None = None,
    on_change: Callable[[bool], Any] | None = None,
    disabled: BoolProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A switch: an on / off setting that takes effect at once, then `label`.

    `checked` works as `nsh.checkbox`'s: a **signal** is two-way (a press
    sets it, then calls `on_change`), a **callable** is one-way and
    read-only (a press only calls `on_change`), and a **bool** (or
    nothing: off) is the first value of a switch that keeps its own value
    and toggles by itself (`on_change(value)` runs after each press).
    `disabled` (a bool or a callable) ignores presses and dims it.
    `class_` takes Tailwind classes for where it sits: they go on a view
    around it, as `nsh.checkbox`'s do.

        dark = nsh.signal(False)
        nsh.switch("Dark mode", checked=dark, test_id="dark")
    """
    _toggle.check_label("switch", label)
    value, handler = _toggle.state(checked, on_change)
    children: list[Child] = []
    if label is not None:
        children.append(text(label, class_=_toggle.label_class(LABEL_CLASS, disabled)))
    return Element(
        KIND,
        props(
            checked=value,
            disabled=disabled,
            on_change=handler,
            track_class=TRACK_CLASS,
            thumb_class=THUMB_CLASS,
            class_=class_,
            test_id=test_id,
        ),
        children,
    )
