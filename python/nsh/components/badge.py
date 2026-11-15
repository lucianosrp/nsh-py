"""`badge`: a compact rounded label for statuses and counts."""

from __future__ import annotations

from nsh._element import Element, StrProp, merge_class
from nsh.primitives import text, view

CLASS = "self-start flex-row items-center rounded-full border px-2.5 py-0.5"
"""The badge's own classes; the caller's `class_` comes after and wins."""

LABEL_CLASS = "text-xs font-semibold"

_VARIANTS = {
    "default": ("border-transparent bg-primary", "text-primary-foreground"),
    "secondary": ("border-transparent bg-secondary", "text-secondary-foreground"),
    "outline": ("border-border", "text-foreground"),
    "destructive": ("border-transparent bg-destructive", "text-destructive-foreground"),
}


def badge(
    label: StrProp,
    *,
    variant: str = "default",
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A compact label for a status or count.

    `variant` is `"default"`, `"secondary"`, `"outline"`, or `"destructive"`.
    `label` takes a string or a callable (a binding). `class_` adds Tailwind
    classes after the default look, so they win; it can also be a binding.

        nsh.badge("Paid", variant="secondary")
        nsh.badge(lambda: f"{unread()} unread", class_="rounded-md")

    Raises `ValueError` for an unknown variant.
    """
    if variant not in _VARIANTS:
        raise ValueError(f"Unknown badge variant {variant!r}; choose from {', '.join(_VARIANTS)}")
    surface_class, label_class = _VARIANTS[variant]
    return view(
        text(label, class_=f"{LABEL_CLASS} {label_class}"),
        class_=merge_class(f"{CLASS} {surface_class}", class_),
        test_id=test_id,
    )
