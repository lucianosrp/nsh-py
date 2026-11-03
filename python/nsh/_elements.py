"""Elements: what components return.

An element is a plain Python object (`kind`, `props`, `children`). The Rust
side turns it into NSH elements when the app runs. A callable where a value
goes is a binding, called again when the signals it reads change:

    nsh.text(lambda: f"Count: {count()}")

A callable child is a region, made again the same way.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Union

Child = Union["Element", str, None, Callable[[], Any], list, tuple]
"""A child: an element, a string (a text), None, a list, or a callable."""

StrProp = Union[str, Callable[[], Any]]
"""A string, or a callable returning one (a binding)."""


class Element:
    """One element of a UI tree."""

    __slots__ = ("kind", "props", "children")

    def __init__(self, kind: str, props: dict[str, Any], children: list[Any]) -> None:
        self.kind = kind
        self.props = props
        self.children = children

    def __repr__(self) -> str:
        return f"Element({self.kind!r}, {self.props!r}, {self.children!r})"


def _props(**props: Any) -> dict[str, Any]:
    return {k: v for k, v in props.items() if v is not None}


def view(
    *children: Child,
    class_: StrProp | None = None,
    on_press: Callable[[], Any] | None = None,
    test_id: str | None = None,
) -> Element:
    """A box holding `children`, laid out with flexbox (a column by default).

    `class_` takes Tailwind classes: `"p-4 gap-2 flex-row"`.
    """
    return Element("view", _props(class_=class_, on_press=on_press, test_id=test_id), list(children))


def text(
    content: StrProp,
    *,
    class_: StrProp | None = None,
    on_press: Callable[[], Any] | None = None,
    test_id: str | None = None,
) -> Element:
    """A text. Pass a callable to bind it: `text(lambda: f"{count()}")`."""
    return Element(
        "text",
        _props(content=content, class_=class_, on_press=on_press, test_id=test_id),
        [],
    )


BUTTON_CLASS = (
    "flex-row items-center justify-center px-4 py-2 rounded-md bg-primary "
    "hover:opacity-90 active:opacity-80 disabled:opacity-50"
)
BUTTON_LABEL_CLASS = "text-sm font-medium text-primary-foreground"


def _join(base: str, extra: StrProp | None) -> StrProp:
    if extra is None:
        return base
    if callable(extra):
        return lambda: f"{base} {extra()}"
    return f"{base} {extra}"


def button(
    label: StrProp,
    *,
    on_press: Callable[[], Any] | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A button showing `label`; `on_press` runs when it is pressed.

    `class_` adds Tailwind classes after the default look, so they win.
    """
    return Element(
        "view",
        _props(
            class_=_join(BUTTON_CLASS, class_),
            on_press=on_press,
            role="button",
            test_id=test_id,
        ),
        [text(label, class_=BUTTON_LABEL_CLASS)],
    )
