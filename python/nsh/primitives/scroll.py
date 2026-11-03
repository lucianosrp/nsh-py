"""`scroll`: a scroll view. Rust: src/elements/scroll.rs."""

from __future__ import annotations

from nsh._element import Child, Element, Handler, StrProp, props

KIND = "scroll"


def scroll(
    *children: Child,
    horizontal: bool = False,
    class_: StrProp | None = None,
    on_press: Handler | None = None,
    test_id: str | None = None,
) -> Element:
    """A box whose `children` scroll when they are taller (or, with
    `horizontal=True`, wider) than it.

    Give it a size (`class_="flex-1"` or `"h-64"`) so the content has
    somewhere to overflow. NSH has no `overflow-y-auto` on `view`; this is
    the scroll view.

        nsh.scroll(
            *[nsh.text(f"Row {i}") for i in range(200)],
            class_="flex-1",
        )
    """
    return Element(
        KIND,
        props(
            horizontal=True if horizontal else None,
            class_=class_,
            on_press=on_press,
            test_id=test_id,
        ),
        list(children),
    )
