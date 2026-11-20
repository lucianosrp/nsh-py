"""`alert`: an inline callout with a title, optional description and actions."""

from __future__ import annotations

from nsh._element import Child, Element, Prop, merge_class
from nsh.primitives import text, view

BASE_CLASS = "rounded-xl border border-border bg-muted p-6 gap-2 text-foreground"
"""The classes shared by every alert variant."""

DEFAULT_CLASS = BASE_CLASS
"""The default alert classes."""

DESTRUCTIVE_CLASS = f"{BASE_CLASS} border-destructive/40 bg-destructive/10 text-destructive"
"""The destructive alert classes: a subtle tinted surface and red text."""

TITLE_CLASS = "text-lg font-semibold"
DESCRIPTION_CLASS = "text-sm"

VARIANT_CLASSES = {"default": DEFAULT_CLASS, "destructive": DESTRUCTIVE_CLASS}
"""The supported variants and their complete root classes."""


def alert(
    title: Prop[str],
    *children: Child,
    description: Prop[str] | None = None,
    variant: str = "default",
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """An alert showing `title`, an optional `description`, then `children`.

    `title` and `description` take a string or a callable (a binding).
    `variant` is `"default"` or `"destructive"`.
    `class_` adds Tailwind classes after the default look, so they win.

        nsh.alert(
            "Saved",
            nsh.button("Undo"),
            description="Your changes are live.",
            class_="w-80",
        )
    """
    try:
        alert_class = VARIANT_CLASSES[variant]
    except KeyError:
        raise ValueError(
            f"unknown alert variant {variant!r}; use 'default' or 'destructive'"
        ) from None

    content: list[Child] = [text(title, class_=TITLE_CLASS)]
    if description is not None:
        content.append(text(description, class_=DESCRIPTION_CLASS))
    content.extend(children)

    return view(
        *content,
        class_=merge_class(alert_class, class_),
        test_id=test_id,
    )
