"""Keyed lists: `nsh.each(items, render, key=...)`.

    todos = nsh.signal([{"id": 1, "title": "Milk"}])
    nsh.view(
        nsh.each(todos, lambda todo: nsh.text(todo["title"]), key=lambda todo: todo["id"]),
    )

A row per item, known by its key. When `items` changes, only rows of new
keys are rendered; rows whose key stays keep their elements (and the
signals `render` made for them), moving if the order changed; rows of
keys that went are disposed. A callable child (`lambda: [...]`) instead
makes every row again on every change.

`each` is not an element kind: like a callable child, it is a region of
its parent's children (NSH's `each`), so it takes no props of its own.
The Rust side is src/each.rs.

Maintainers own this module.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Each(Generic[T]):
    """A keyed list of rows, as `nsh.each` makes it: a child of a view."""

    __slots__ = ("items", "render", "key")

    def __init__(
        self,
        items: Callable[[], Iterable[T]] | Iterable[T],
        render: Callable[[T], Any],
        key: Callable[[T], Hashable] | None,
    ) -> None:
        self.items = items
        self.render = render
        self.key = key

    def __repr__(self) -> str:
        return f"each({self.items!r}, {self.render!r}, key={self.key!r})"


def each(
    items: Callable[[], Iterable[T]] | Iterable[T],
    render: Callable[[T], Any],
    *,
    key: Callable[[T], Hashable] | None = None,
) -> Each[T]:
    """A row per item of `items`, made by `render(item)`, known by `key(item)`.

    `items` is a signal, a computed or any callable returning an iterable
    (the list follows it), or a plain iterable (fixed). `render` returns a
    row's children, like a component: an element, a string, a list...

    Rows are matched by key, so a change only renders new keys::

        todos = nsh.signal([{"id": 1, "title": "Milk", "done": False}])
        nsh.each(todos, Todo, key=lambda todo: todo["id"])

    - `render` runs once per new key. A row whose key stays keeps its
      elements, and the signals `render` made for it, and moves with its
      item when the list is reordered. A removed key disposes its row.
    - An item that changes under the same key (a new object that isn't
      `==` the old one, such as `{**todo, "done": True}`) renders its row
      again, in place. An item changed in place (`todo["done"] = True`)
      is the same object, so its row doesn't change: replace the item, or
      keep what changes in a signal inside it.
    - `key` defaults to the item itself, which suits strings, numbers,
      tuples and frozen dataclasses (equal items are the same row). An
      unhashable item (a dict, a list) is then known by identity (`is`):
      fine while the list keeps the same objects, but a copy is a new row.
      Pass `key` for records, typically their id.
    - Keys follow dict rules (`hash` and `==`). Two items with the same
      key make two rows. A key that raises is logged, and its row is made
      again on every change.

    Exceptions in `items`, `key` or `render` are logged and the app keeps
    running: a failed `items` keeps the rows shown, a failed `render`
    shows nothing for that row.
    """
    if not callable(render):
        raise TypeError(f"each: render must be callable, not {type(render).__name__}")
    if key is not None and not callable(key):
        raise TypeError(f"each: key must be callable or None, not {type(key).__name__}")
    if not callable(items):
        items = tuple(items)  # fixed: read once, now (a generator too)
    return Each(items, render, key)
