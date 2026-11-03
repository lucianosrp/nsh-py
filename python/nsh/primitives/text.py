"""`text`: a text block. Rust: src/elements/text.rs."""

from __future__ import annotations

from nsh._element import Element, Handler, StrProp, props

KIND = "text"


def text(
    content: StrProp,
    *,
    class_: StrProp | None = None,
    on_press: Handler | None = None,
    test_id: str | None = None,
) -> Element:
    """A text. Pass a callable to bind it: `text(lambda: f"{count()}")`."""
    return Element(
        KIND,
        props(content=content, class_=class_, on_press=on_press, test_id=test_id),
        [],
    )
