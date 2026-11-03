"""`card`: a bordered, padded surface with an optional title and description."""

from __future__ import annotations

from nsh._element import Child, Element, StrProp, merge_class
from nsh.primitives import text, view

CLASS = "rounded-xl border border-border bg-card p-6 gap-2"
"""The card's own classes; the caller's `class_` comes after and wins."""

TITLE_CLASS = "text-lg font-semibold text-card-foreground"
DESCRIPTION_CLASS = "text-sm text-muted-foreground"


def card(
    *children: Child,
    title: StrProp | None = None,
    description: StrProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A card: an optional `title` and `description`, then `children`.

    `title` and `description` take a string or a callable (a binding).
    `class_` adds Tailwind classes after the default look, so they win.

        nsh.card(
            nsh.button("Save"),
            title="Profile",
            description="Shown to other people.",
            class_="w-80",
        )
    """
    header: list[Child] = []
    if title is not None:
        header.append(text(title, class_=TITLE_CLASS))
    if description is not None:
        header.append(text(description, class_=DESCRIPTION_CLASS))
    return view(
        *header,
        *children,
        class_=merge_class(CLASS, class_),
        test_id=test_id,
    )
