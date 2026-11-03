"""Signals: values that UIs follow.

    count = nsh.signal(0)
    count()                          # read (subscribes the running binding)
    count.set(1)                     # write: what read it runs again
    count.update(lambda n: n + 1)    # write from the current value

A read subscribes only inside a binding: a lambda passed where a value goes
(`nsh.text(lambda: f"{count()}")`) or a callable child. A value read
outside one is read once: `nsh.text(f"{count()}")` never changes.

The value lives in Python. Each signal holds an NSH signal (a "trigger")
that NSH's reactive graph tracks, so only the bindings that read it run
again. See docs/architecture.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from nsh import _core

T = TypeVar("T")

logger = logging.getLogger("nsh")


def _same(old: Any, new: Any) -> bool:
    if old is new:
        return True
    try:
        return bool(old == new)
    except Exception:  # arrays and the like compare element-wise or raise
        return False


class Signal(Generic[T]):
    """A value that bindings follow. Make one with `nsh.signal(value)`."""

    __slots__ = ("_value", "_trigger", "__weakref__")

    def __init__(self, value: T) -> None:
        self._value = value
        self._trigger: _core.Trigger | None = None

    def __call__(self) -> T:
        """The value, subscribing the running binding."""
        if _core.in_engine():
            if self._trigger is None:
                self._trigger = _core.Trigger()
            self._trigger.track()
        return self._value

    def peek(self) -> T:
        """The value, without subscribing anything."""
        return self._value

    def set(self, value: T) -> None:
        """Write `value`. Bindings that read the signal run again, unless
        the new value equals the old one (`==`)."""
        if _same(self._value, value):
            return
        self._value = value
        self._notify()

    def update(self, fn: Callable[[T], T]) -> None:
        """Write `fn(value)`: `count.update(lambda n: n + 1)`."""
        self.set(fn(self._value))

    def mutate(self, fn: Callable[[T], Any]) -> None:
        """Change the value in place, then notify (always).

        Lists and dicts changed in place are the same object, so `set`
        can't see the change: `items.mutate(lambda xs: xs.append(4))`.
        """
        fn(self._value)
        self._notify()

    def _notify(self) -> None:
        trigger = self._trigger
        if trigger is not None and not trigger.notify():
            logger.warning(
                "Signal written outside the app's thread: the UI won't update. "
                "Write signals from handlers (on_press, ...) for now."
            )

    def __repr__(self) -> str:
        return f"signal({self._value!r})"


def signal(value: T) -> Signal[T]:
    """A new signal holding `value`."""
    return Signal(value)
