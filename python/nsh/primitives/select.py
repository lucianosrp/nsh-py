"""`select`: choose a string from a dropdown. Rust: src/elements/select.rs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from nsh._element import BoolProp, Element, StrProp, merge_class, props
from nsh._signals import Signal, signal
from nsh.primitives.text import text

KIND = "select"

TRIGGER_CLASS = (
    "flex-row items-center justify-between gap-2 min-w-40 h-9 px-3 rounded-md "
    "border border-input bg-background text-foreground focus:border-ring disabled:opacity-50"
)
POPUP_CLASS = "rounded-md border border-border bg-popover text-popover-foreground shadow-md"
LIST_CLASS = "p-1"
ITEM_CLASS = (
    "px-2 py-1.5 rounded-sm text-sm focus:bg-accent focus:text-accent-foreground "
    "selected:bg-accent selected:text-accent-foreground"
)


def select(
    value: StrProp | None = None,
    *,
    options: Sequence[str] | Callable[[], Sequence[str]],
    placeholder: StrProp = "Select…",
    on_change: Callable[[str], Any] | None = None,
    disabled: BoolProp | None = None,
    accessibility_label: StrProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """Choose one of `options`, a sequence of unique strings or a callable
    returning one (a signal, lambda or computed).

    A **signal** `value` is two-way: choosing sets it, then calls
    `on_change(value)`. A **callable** is controlled: choosing only calls
    `on_change`, and the app decides whether to update the value. A
    **string** (or `None`) is the initial value of a select that keeps its
    own selection. Choosing the current option again does not call the
    handler. Exceptions in handlers are logged and the app keeps running.

    The trigger shows `placeholder` while the value is `None` or absent
    from `options`; replacing the options never changes the value itself.
    `disabled` blocks interaction. Both accept values or callables.
    `class_` styles the trigger, after its defaults. `accessibility_label`
    gives the control a name for screen readers.

        size = nsh.signal("Medium")
        nsh.select(size, options=["Small", "Medium", "Large"],
                   accessibility_label="Size")
    """
    if not callable(value) or isinstance(value, Signal):
        own = value if isinstance(value, Signal) else signal(value)
        value = own
        if on_change is None:
            on_change = own.set
        else:
            callback = on_change

            def changed(chosen: str) -> None:
                own.set(chosen)
                callback(chosen)

            on_change = changed

    def label() -> str:
        chosen = value()
        items = options() if callable(options) else options
        if chosen is not None and chosen in items:
            return chosen
        return placeholder() if callable(placeholder) else placeholder

    return Element(
        KIND,
        props(
            value=value,
            options=options,
            placeholder=placeholder,
            on_change=on_change,
            disabled=disabled,
            accessibility_label=accessibility_label,
            class_=merge_class(TRIGGER_CLASS, class_),
            popup_class=POPUP_CLASS,
            list_class=LIST_CLASS,
            item_class=ITEM_CLASS,
            test_id=test_id,
        ),
        [text(label, class_="flex-1 text-sm"), text("▾", class_="text-muted-foreground")],
    )
