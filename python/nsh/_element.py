"""The element: what components return, and what the Rust side builds.

An element is a plain Python object: a `kind` (a primitive the Rust side
knows, see `nsh.primitives`), a `props` dict and `children`. A callable
where a value goes is a binding, called again when the signals it reads
change:

    nsh.text(lambda: f"Count: {count()}")

A callable child is a region, made again the same way.

Maintainers own this module; contributions go in `nsh.primitives`
(Python + Rust) and `nsh.components` (Python only).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from nsh._each import Each

Child = Union["Element", str, None, Callable[[], Any], list, tuple, "Each[Any]"]
"""A child: an element, a string (a text), None, a list, a callable, or `nsh.each`."""

StrProp = str | Callable[[], Any]
"""A string, or a callable returning one (a binding)."""

BoolProp = Union[bool, Callable[[], Any]]
"""A bool, or a callable returning one (a binding)."""

Handler = Callable[[], Any]
"""An event handler. Exceptions it raises are logged; the app keeps running."""


class Element:
    """One element of a UI tree."""

    __slots__ = ("kind", "props", "children")

    def __init__(self, kind: str, props: dict[str, Any], children: list[Any]) -> None:
        self.kind = kind
        self.props = props
        self.children = children

    def __repr__(self) -> str:
        return f"Element({self.kind!r}, {self.props!r}, {self.children!r})"


def props(**values: Any) -> dict[str, Any]:
    """A props dict without the props left at `None`."""
    return {k: v for k, v in values.items() if v is not None}


def merge_class(base: str, extra: StrProp | None) -> StrProp:
    """`base` classes then the caller's `extra` ones (which win), keeping a
    callable `extra` bound."""
    if extra is None:
        return base
    if callable(extra):
        return lambda: f"{base} {extra()}"
    return f"{base} {extra}"
