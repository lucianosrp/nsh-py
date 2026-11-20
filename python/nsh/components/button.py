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

_BASE_CLASS = "flex-row items-center justify-center rounded-md"
_VARIANTS = {
    "default": ("bg-primary", "text-primary-foreground"),
    "secondary": ("bg-secondary hover:bg-secondary/80", "text-secondary-foreground"),
    "outline": ("border border-input bg-background hover:bg-accent", "text-foreground"),
    "ghost": ("hover:bg-accent", "text-foreground"),
    "destructive": ("bg-destructive hover:bg-destructive/90", "text-destructive-foreground"),
}
_SIZES = {
    "sm": "px-3 py-1.5",
    "md": "px-4 py-2",
    "lg": "px-8 py-3",
}


def button(
    label: StrProp,
    *,
    on_press: Handler | None = None,
    variant: str = "default",
    size: str = "md",
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A button showing `label`; `on_press` runs when it is pressed.

    `variant` is `"default"`, `"secondary"`, `"outline"`, `"ghost"`, or
    `"destructive"`. `size` is `"sm"`, `"md"`, or `"lg"`. `class_` adds
    Tailwind classes after the default look, so they win.

        nsh.button("Delete", variant="destructive", size="sm")

    Raises `ValueError` for an unknown variant or size.
    """
    if variant not in _VARIANTS:
        raise ValueError(f"Unknown button variant {variant!r}; choose from {', '.join(_VARIANTS)}")
    if size not in _SIZES:
        raise ValueError(f"Unknown button size {size!r}; choose from {', '.join(_SIZES)}")

    variant_class, label_color = _VARIANTS[variant]
    if variant == "default" and size == "md":
        button_class = CLASS
    else:
        button_class = " ".join(
            (
                _BASE_CLASS,
                _SIZES[size],
                variant_class,
                "hover:opacity-90 active:opacity-80 disabled:opacity-50",
            )
        )

    label_class = (
        LABEL_CLASS
        if variant == "default" and size == "md"
        else f"text-sm font-medium {label_color}"
    )
    return Element(
        VIEW,
        props(
            class_=merge_class(button_class, class_),
            on_press=on_press,
            role="button",
            test_id=test_id,
        ),
        [text(label, class_=label_class)],
    )
