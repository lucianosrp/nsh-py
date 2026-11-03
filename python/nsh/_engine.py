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

from collections.abc import Callable
from typing import Any

from nsh import _core


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
