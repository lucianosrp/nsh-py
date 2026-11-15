"""`avatar`: a round avatar with initials, or a picture.

`nsh.avatar("Ada Lovelace")` shows a circle with "AL". Give it `src=` to
show `nsh.image` instead.
"""

from __future__ import annotations

from nsh._element import Element, StrProp, merge_class
from nsh.primitives import image, text, view
from nsh.primitives.image import Src

CLASS = "rounded-full bg-muted items-center justify-center overflow-hidden"
"""The avatar's own classes; the caller's `class_` comes after and wins."""

INITIALS_CLASS = "font-medium text-muted-foreground"
"""The initials' classes (centred by the avatar's `items-center justify-center`)."""

SIZES = {
    "sm": "h-8 w-8 text-xs",
    "md": "h-10 w-10 text-sm",
    "lg": "h-12 w-12 text-base",
}
"""The size classes: the box, then the initials' font size."""


def initials(name: str) -> str:
    """The initials for `name`: the first letter of the first and last
    word, upper case; one word → one letter; empty → "?"."""
    words = name.split()
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


def avatar(
    name: str,
    *,
    size: str = "md",
    src: Src | None = None,
    alt: StrProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A round avatar with initials, or a picture when `src` is given.

    `name` is the person's name: its initials show (`nsh.avatar("Ada
    Lovelace")` → "AL"), or `?` when empty. `size` is `"sm"`, `"md"` or
    `"lg"`. `src` shows `nsh.image` instead, with `alt` (default `name`)
    as the screen-reader label. `class_` adds Tailwind classes after the
    default look, so they win.

        nsh.avatar("Ada Lovelace")
        nsh.avatar("Ada Lovelace", size="lg", class_="border border-border")
        nsh.avatar("Ada Lovelace", src="examples/assets/dot.png")
    """
    if size not in SIZES:
        raise ValueError(f"unknown size {size!r}; use sm, md or lg")
    box = f"{CLASS} {SIZES[size]}"
    if src is not None:
        return image(
            src,
            alt=alt if alt is not None else name,
            class_=merge_class(box, class_),
            test_id=test_id,
        )
    return view(
        text(initials(name), class_=INITIALS_CLASS),
        class_=merge_class(box, class_),
        test_id=test_id,
    )
