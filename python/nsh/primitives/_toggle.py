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

    - a signal: two-way, pressing sets it (`on_change`, if given, runs
      instead, as `nsh.input` does);
    - a callable: one-way, pressing only calls `on_change`;
    - a bool (or `None`, off): the first value of a signal of the toggle's
      own, so it still toggles; `on_change` runs after it is set.
    """
    if isinstance(checked, Signal):
        return checked, on_change if on_change is not None else checked.set
    if callable(checked):
        return checked, on_change
    own = signal(bool(checked))
    if on_change is None:
        return own, own.set

    def changed(value: bool) -> None:
        own.set(value)
        on_change(value)

    return own, changed


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
