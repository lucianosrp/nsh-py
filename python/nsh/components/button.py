"""`button`: a pressable, styled view with a label."""

from __future__ import annotations

from nsh._element import Element, Handler, StrProp, merge_class, props
from nsh.primitives import text
from nsh.primitives.view import KIND as VIEW

CLASS = (
    "flex-row items-center justify-center px-4 py-2 rounded-md bg-primary "
    "hover:opacity-90 active:opacity-80 disabled:opacity-50"
)
"""The button's own classes; the caller's `class_` comes after and wins."""

LABEL_CLASS = "text-sm font-medium text-primary-foreground"


def button(
    label: StrProp,
    *,
    on_press: Handler | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A button showing `label`; `on_press` runs when it is pressed.

    `class_` adds Tailwind classes after the default look, so they win.
    """
    return Element(
        VIEW,
        props(
            class_=merge_class(CLASS, class_),
            on_press=on_press,
            role="button",
            test_id=test_id,
        ),
        [text(label, class_=LABEL_CLASS)],
    )
