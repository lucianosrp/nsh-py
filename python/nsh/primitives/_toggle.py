"""What checkbox and switch share: the value a toggle shows and sets."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import BoolProp, StrProp
from nsh._signals import Signal, signal


def state(
    checked: BoolProp | None, on_change: Callable[[bool], Any] | None
) -> tuple[Callable[[], Any], Callable[[bool], Any] | None]:
    """The toggle's value (a callable the toggle binds) and its press
    handler, from what the caller passed:

    - a signal: two-way, a press sets it, then calls `on_change`;
    - a callable: one-way and read-only, a press only calls `on_change`;
    - a bool (or `None`, off): the first value of a signal of the toggle's
      own, so it still toggles; a press sets it, then calls `on_change`.
    """
    if callable(checked) and not isinstance(checked, Signal):
        return checked, on_change
    own = checked if isinstance(checked, Signal) else signal(bool(checked))
    if on_change is None:
        return own, own.set

    def changed(value: bool) -> None:
        own.set(value)
        on_change(value)

    return own, changed


def check_label(name: str, label: object) -> None:
    """Raise when `label` looks like the value: the label comes first and
    the value is `checked=` (`nsh.checkbox("I agree", checked=agree)`)."""
    if isinstance(label, bool) or (isinstance(label, Signal) and isinstance(label.value, bool)):
        raise TypeError(
            f"nsh.{name}() takes the label first; pass the value as checked=, "
            f'as in nsh.{name}("I agree", checked=agree)'
        )


def reader(value: BoolProp | None) -> Callable[[], bool]:
    """`value` as a function to read in a binding."""
    if callable(value):
        return lambda: bool(value())
    fixed = bool(value)
    return lambda: fixed


def label_class(base: str, disabled: BoolProp | None) -> StrProp:
    """`base`, dimmed while `disabled`: the label's own `disabled:` can't
    follow the toggle (only its parts' do)."""
    if callable(disabled):
        return lambda: f"{base} {DIMMED}" if disabled() else base
    return f"{base} {DIMMED}" if disabled else base


DIMMED = "opacity-50"
"""How a disabled toggle's label looks."""
