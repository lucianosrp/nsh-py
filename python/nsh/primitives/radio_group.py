"""`radio_group`: nsh-base's RadioGroup. Rust: src/elements/radio_group.rs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from nsh._element import BoolProp, Element, StrProp, merge_class, props
from nsh._signals import Signal, signal

KIND = "radio_group"

GROUP_CLASS = "flex-col gap-2"
"""The group: a column of radios by default (`flex-row` for a row)."""

RADIO_CLASS = "group flex-row items-center gap-2 disabled:opacity-50"
"""One radio: `group` so the indicator's `group-checked:` follows it."""

INDICATOR_CLASS = (
    "size-4 rounded-full border border-primary items-center justify-center "
    "group-checked:border-primary"
)
"""The outer circle."""

DOT_CLASS = "size-2 rounded-full bg-primary opacity-0 group-checked:opacity-100"
"""The filled dot, shown while checked."""

LABEL_CLASS = "text-sm"
"""The option's label, after the circle."""


def radio_group(
    value: StrProp | None = None,
    *,
    options: Sequence[str] | Callable[[], Sequence[str]],
    on_change: Callable[[str], Any] | None = None,
    disabled: BoolProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """Choose one of `options`, a sequence of unique strings or a callable
    returning one (a signal, lambda or computed).

    A **signal** `value` is two-way: choosing sets it, then calls
    `on_change(value)`. A **callable** is controlled: choosing only calls
    `on_change`, and the app decides whether to update the value. A
    **string** (or `None`) is the initial value of a group that keeps its
    own selection. Choosing the current option again does nothing. A radio
    cannot clear itself; write `None` to the signal to clear. Exceptions in
    handlers are logged and the app keeps running.

    `disabled` greys every radio out and blocks presses. Both it and
    `value` accept a value or a callable. `class_` styles the group, after
    its defaults (later utilities win: `"flex-row gap-4"` lays them out in
    a row).

        size = nsh.signal("Medium")
        nsh.radio_group(size, options=["Small", "Medium", "Large"])
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

    return Element(
        KIND,
        props(
            value=value,
            options=options,
            on_change=on_change,
            disabled=disabled,
            radio_class=RADIO_CLASS,
            indicator_class=INDICATOR_CLASS,
            dot_class=DOT_CLASS,
            label_class=LABEL_CLASS,
            class_=merge_class(GROUP_CLASS, class_),
            test_id=test_id,
        ),
        [],
    )
