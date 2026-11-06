"""Reaching the app: `call_soon`, `effect`, `set_timeout`, `set_interval`.

    nsh.call_soon(fn, *args)         # run fn(*args) on the app's thread, soon
    nsh.call_soon(count.set, 5)      # from a worker thread: the UI follows

    @nsh.effect                      # now, and again when count changes
    def log():
        print("count is", count())

    log.dispose()                    # stop it

    tick = nsh.set_interval(1.0, count.updater(lambda n: n + 1))
    tick.cancel()

NSH's reactive graph belongs to one thread, the app's ("nsh-engine"). All
of these are safe to call from any thread: what must run on the app's
thread is posted there and runs soon, in the order posted. Code the app
calls (handlers, bindings, effects, timers) already runs on that thread.
See docs/architecture.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nsh import _core
from nsh._runtime import report_exception
from nsh._signals import Computed, _Source

logger = logging.getLogger("nsh")

Timer = _core.Timer
"""A timer made by `set_timeout` or `set_interval`. `cancel()` stops it."""


def call_soon(fn: Callable[..., Any], *args: Any) -> None:
    """Run `fn(*args)` on the app's thread, soon. Safe from any thread.

    It runs after what is running now and after the calls posted before
    it, in order, even when called from the app's own thread (a handler
    that calls `call_soon` finishes first). An exception is logged and the
    app keeps running.

    With no app running (before `nsh.run`, or in a plain script) there is
    no app thread to wait for: `fn(*args)` runs right away, here, and an
    exception is logged. While an app is starting, the call waits for it.
    A call still waiting when the app ends is dropped.
    """
    _core.call_soon(fn, args)


class Effect:
    """A function that runs now and again when the signals it reads change.

    Make one with `nsh.effect`. `dispose()` stops it.
    """

    __slots__ = ("_fn", "_disposed", "_core", "_py", "__weakref__")

    def __init__(self, fn: Callable[[], Any]) -> None:
        self._fn = fn
        self._disposed = False
        self._core: _core.Effect | None = None
        self._py: _PyEffect | None = None
        if _core.in_engine():
            self._start_in_app()
        elif _core.app_active():
            _core.call_soon(self._start_in_app, ())
        else:
            self._py = _PyEffect(fn)
            self._py.run()

    def _start_in_app(self) -> None:
        # On the app's thread. An NSH effect owned by whatever is running:
        # the component that made it, or the app's root for a posted one.
        if not self._disposed:
            self._core = _core.Effect(self._fn)

    @property
    def disposed(self) -> bool:
        """Whether `dispose()` was called."""
        return self._disposed

    def dispose(self) -> None:
        """Stop the effect: it never runs again. Safe from any thread."""
        self._disposed = True
        if self._core is not None:
            self._core.dispose()
        if self._py is not None:
            self._py.dispose()

    def __repr__(self) -> str:
        name = getattr(self._fn, "__name__", "effect")
        return f"effect({name}{', disposed' if self._disposed else ''})"


# Python-only effects nobody keeps a reference to still run until disposed.
_alive: set[_PyEffect] = set()


class _Reads(set):  # type: ignore[type-arg]
    """The sources an effect read, subscribing as it reads: a write the effect
    makes to something it read earlier in the same run must run it again."""

    def __init__(self, effect: _PyEffect) -> None:
        super().__init__()
        self._effect = effect

    def add(self, source: Any) -> None:
        super().add(source)
        source._dependents.add(self._effect)


class _PyEffect(Computed[None]):
    """An effect with no app: a computed that runs again when it's stale.

    It tracks what it reads like a computed does (`nsh/_signals.py`), and
    a write marks it stale and runs it, on the writing thread, after every
    computed downstream of the write is marked.
    """

    __slots__ = ("_running", "_again", "_dead")

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__(fn)
        self._running = False
        self._again = False
        self._dead = False
        self._observer = self.run
        _alive.add(self)

    def _new_reads(self) -> set[_Source[Any]]:
        return _Reads(self)

    def run(self) -> None:
        if self._dead:
            return
        if self._running:  # marked stale by its own writes: once more after
            self._again = True
            return
        self._running = True
        try:
            for _ in range(100):
                self._again = False
                try:
                    self._compute()
                except Exception as exc:
                    report_exception(exc)
                if not self._again or self._dead:
                    break
            else:
                logger.error("effect %r keeps changing what it reads: stopped", self._name)
                self.dispose()
        finally:
            self._running = False

    def dispose(self) -> None:
        self._dead = True
        self._observer = None
        for source in self._sources:
            source._dependents.discard(self)
        self._sources = set()
        _alive.discard(self)


def effect(fn: Callable[[], Any]) -> Effect:
    """Run `fn` now, and again whenever the signals it reads change.
    Use it as a decorator::

        @nsh.effect
        def log():
            print("count is", count())

    Returns a handle: `log.dispose()` stops it.

    Made inside the app (in a component, a handler, a posted call), it is
    owned by what made it: a component's effect ends with the component.
    It runs on the app's thread, after the bindings of a change are up to
    date. From another thread it is made on the app's thread soon, so its
    first run isn't immediate. Made before the app starts, or with no app
    at all, it runs right here and again on whatever thread writes a signal
    it read, until disposed; it isn't tied to a component.

    An exception in `fn` is logged and the effect stays subscribed to what
    it read before raising.
    """
    return Effect(fn)


def set_timeout(seconds: float, fn: Callable[..., Any], *args: Any) -> Timer:
    """Run `fn(*args)` once on the app's thread, after `seconds`.

    Returns a handle: `cancel()` stops it, from any thread. Made inside
    the app, it is owned by what made it (a component's timers end with
    it); from another thread it is made on the app's thread soon, and
    `seconds` count from then. Needs a running app: `RuntimeError` otherwise.
    """
    return _timer(seconds, fn, args, repeat=False)


def set_interval(seconds: float, fn: Callable[..., Any], *args: Any) -> Timer:
    """Run `fn(*args)` on the app's thread every `seconds` until cancelled.

    Same rules as `set_timeout`. Late wake-ups don't pile up calls, and an
    interval is never shorter than a millisecond.
    """
    return _timer(seconds, fn, args, repeat=True)


def _timer(seconds: float, fn: Callable[..., Any], args: tuple[Any, ...], *, repeat: bool) -> Timer:
    timer = _core.Timer(fn, args, seconds, repeat)
    if _core.in_engine():
        timer.arm()
    elif _core.app_active():
        _core.call_soon(timer.arm, ())
    else:
        raise RuntimeError(
            "timers need a running app: make them in a component or a handler, "
            "or from a thread once nsh.run() has started"
        )
    return timer
