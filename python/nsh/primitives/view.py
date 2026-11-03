"""`view`: a flexbox container. Rust: src/elements/view.rs."""

from __future__ import annotations

from nsh._element import Child, Element, Handler, StrProp, props

KIND = "view"


def view(
    *children: Child,
    class_: StrProp | None = None,
    on_press: Handler | None = None,
    test_id: str | None = None,
) -> Element:
    """A box holding `children`, laid out with flexbox (a column by default).

    `class_` takes Tailwind classes: `"p-4 gap-2 flex-row"`.
    """
    return Element(KIND, props(class_=class_, on_press=on_press, test_id=test_id), list(children))
