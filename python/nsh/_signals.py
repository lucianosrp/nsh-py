"""Signals: values that UIs follow.

    count = nsh.signal(0)
    count()                          # read (subscribes the running binding)
    count.value                      # the same read, as a property
    count.set(1)                     # write: what read it runs again
    count.value = 1                  # the same write
    count.value += 1                 # read, then write
    count.update(lambda n: n + 1)    # write from the current value

    @nsh.computed                    # a derived value, cached
    def label():
        return f"Count: {count()}"

    @count.updater                   # a handler: on_press=increment
    def increment(n):
        return n + 1

Every style works everywhere: pick lambdas, named functions or decorators.

A read subscribes only inside a binding: a callable passed where a value
goes (`nsh.text(lambda: f"{count()}")`, `nsh.text(label)`) or a callable
child. A value read outside one is read once: `nsh.text(f"{count()}")` and
`nsh.text(count.value)` never change.

The value lives in Python. Each signal holds an NSH signal (a "trigger")
that NSH's reactive graph tracks, so only the bindings that read it run
again. A computed also remembers which signals it read, so it recomputes
only when one of them changes. See docs/architecture.md.
"""

from __future__ import annotations

import functools
import threading
import weakref
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from nsh import _core

T = TypeVar("T")
U = TypeVar("U")

_local = threading.local()


def _collecting() -> list[set[_Source[Any]]]:
    """The sources read by each computed being computed now (innermost last)."""
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = _local.stack = []
    return stack


def _same(old: Any, new: Any) -> bool:
    if old is new:
        return True
    try:
        return bool(old == new)
    except Exception:  # arrays and the like compare element-wise or raise
        return False


class _Source(Generic[T]):
    """What signals and computeds share: a trigger and the computeds that read it."""

    __slots__ = ("_trigger", "_dependents", "__weakref__")

    def __init__(self) -> None:
        self._trigger: _core.Trigger | None = None
        self._dependents: weakref.WeakSet[Computed[Any]] = weakref.WeakSet()

    def __call__(self) -> T:  # pragma: no cover - overridden
        raise NotImplementedError

    @property
    def value(self) -> T:
        """The value, subscribing the running binding (same as calling it)."""
        return self()

    def map(self, fn: Callable[[T], U]) -> Computed[U]:
        """A computed of `fn(value)`: `nsh.text(count.map(lambda n: f"{n} items"))`."""
        return Computed(lambda: fn(self()))

    def _track(self) -> None:
        stack = _collecting()
        if stack:
            stack[-1].add(self)
        if _core.in_engine():
            if self._trigger is None:
                self._trigger = _core.Trigger()
            self._trigger.track()

    def _changed(self) -> None:
        """Tell everything that read this: computeds first, then NSH.

        NSH's graph and the computeds belong to the app's thread. From
        another thread, while an app runs, the notify is posted there
        (`nsh.call_soon`): the value is already stored, and the UI follows
        soon. With no app there is nothing to post to: it runs right here.
        """
        if _core.in_engine() or not _core.app_active():
            self._notify()
        else:
            _core.call_soon(self._notify)

    def _notify(self) -> None:
        stale: list[_Source[Any]] = [self]
        for dependent in list(self._dependents):
            dependent._mark_stale(stale)
        # Together: a binding that read a computed and its signal runs once.
        _core.notify_all([s._trigger for s in stale if s._trigger is not None])
        for source in stale:
            observer = getattr(source, "_observer", None)
            if observer is not None:
                observer()


class Signal(_Source[T]):
    """A value that bindings follow. Make one with `nsh.signal(value)`."""

    __slots__ = ("_value", "_lock")

    def __init__(self, value: T) -> None:
        super().__init__()
        self._value = value
        # Writes from several threads (a worker and the app) must not lose
        # updates: `update` reads, computes and stores under it.
        self._lock = threading.RLock()

    def __call__(self) -> T:
        """The value, subscribing the running binding."""
        self._track()
        return self._value

    @property
    def value(self) -> T:
        """The value. Reading subscribes the running binding; assigning is `set`."""
        return self()

    @value.setter
    def value(self, value: T) -> None:
        self.set(value)

    def peek(self) -> T:
        """The value, without subscribing anything."""
        return self._value

    def set(self, value: T) -> None:
        """Write `value`. Bindings that read the signal run again, unless
        the new value equals the old one (`==`).

        Safe from any thread: the value is stored at once, and what reads
        the signal follows on the app's thread, soon."""
        with self._lock:
            if _same(self._value, value):
                return
            self._value = value
        self._changed()

    def update(self, fn: Callable[[T], T]) -> None:
        """Write `fn(value)`: `count.update(lambda n: n + 1)`.

        Atomic against other writers, on any thread: no update is lost."""
        with self._lock:
            new = fn(self._value)
            if _same(self._value, new):
                return
            self._value = new
        self._changed()

    def mutate(self, fn: Callable[[T], Any]) -> None:
        """Change the value in place, then notify (always).

        Lists and dicts changed in place are the same object, so `set`
        can't see the change: `items.mutate(lambda xs: xs.append(4))`.
        """
        with self._lock:
            fn(self._value)
        self._changed()

    # Handlers: each returns a function that takes no arguments, for on_press.

    def setter(self, value: T) -> Callable[[], None]:
        """A handler that sets `value`: `on_press=count.setter(0)`."""

        def handler() -> None:
            self.set(value)

        return handler

    def updater(self, fn: Callable[[T], T]) -> Callable[[], None]:
        """A handler that runs `update(fn)`. Use it as a decorator::

        @count.updater
        def increment(n):
            return n + 1

        nsh.button("+1", on_press=increment)
        """

        def handler() -> None:
            self.update(fn)

        return functools.wraps(fn)(handler)

    def mutator(self, fn: Callable[[T], Any]) -> Callable[[], None]:
        """A handler that runs `mutate(fn)`. Use it as a decorator::

        @items.mutator
        def add_item(xs):
            xs.append("new")
        """

        def handler() -> None:
            self.mutate(fn)

        return functools.wraps(fn)(handler)

    def __repr__(self) -> str:
        return f"signal({self._value!r})"


_STALE = object()


class Computed(_Source[T]):
    """A value derived from signals, cached until one of them changes.

    Make one with `nsh.computed(fn)`, or `@nsh.computed` on a function
    that takes no arguments. Read it like a signal: `label()` or
    `label.value`. It can't be set.
    """

    __slots__ = ("_fn", "_value", "_sources", "_computing", "_dirty", "_name", "_observer")

    def __init__(self, fn: Callable[[], T]) -> None:
        super().__init__()
        self._fn = fn
        self._value: Any = _STALE
        self._sources: set[_Source[Any]] = set()
        self._computing = False
        self._dirty = True  # marked stale since the last compute attempt
        self._name = getattr(fn, "__name__", "computed")
        # Called after a source changed and this was marked stale (the
        # effects with no app, nsh/_effects.py).
        self._observer: Callable[[], None] | None = None

    def __call__(self) -> T:
        """The value (computed now if a source changed), subscribing the running binding."""
        self._track()
        return self.peek()

    def peek(self) -> T:
        """The value, without subscribing anything."""
        if self._value is _STALE:
            self._compute()
        return self._value

    def _compute(self) -> None:
        if self._computing:
            raise RuntimeError(f"computed {self._name!r} reads itself")
        self._dirty = False  # a change from now on must tell readers, even if this raises
        for source in self._sources:
            source._dependents.discard(self)
        read = self._new_reads()
        stack = _collecting()
        stack.append(read)
        self._computing = True
        try:
            value = self._fn()
        finally:
            self._computing = False
            stack.pop()
            self._sources = read
            for source in read:
                source._dependents.add(self)
        self._value = value

    def _new_reads(self) -> set[_Source[Any]]:
        """Where a compute records the sources it reads."""
        return set()

    def _mark_stale(self, stale: list[_Source[Any]]) -> None:
        if self._dirty:
            return  # already stale: its readers were told
        self._dirty = True
        self._value = _STALE
        stale.append(self)
        for dependent in list(self._dependents):
            dependent._mark_stale(stale)

    def __repr__(self) -> str:
        shown = "<not computed>" if self._value is _STALE else repr(self._value)
        return f"computed({self._name}: {shown})"


_signal_hook: Callable[..., Signal[Any]] | None = None
"""Set by hot reload (`nsh._reload`) while it renders, to keep signals'
values across reloads. `None` otherwise."""


def signal(value: T) -> Signal[T]:
    """A new signal holding `value`."""
    if _signal_hook is not None:
        return _signal_hook(value)
    return Signal(value)


def computed(fn: Callable[[], T]) -> Computed[T]:
    """A cached value derived from signals. Use it as a decorator::

        @nsh.computed
        def total():
            return sum(prices())

        nsh.text(lambda: f"Total: {total()}")

    or inline: `nsh.computed(lambda: count() * 2)`.
    """
    return Computed(fn)
