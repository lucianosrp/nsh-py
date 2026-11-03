"""Running apps: `nsh.run()` and what reports errors in app code."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nsh import _core

logger = logging.getLogger("nsh")


def report_exception(exc: BaseException) -> None:
    """Log an exception raised by app code (a handler, a binding, a view).

    The app keeps running: the failed handler does nothing, a failed
    binding shows an empty value. Called by the Rust side.
    """
    if not logging.getLogger().handlers and not logger.handlers:
        # No logging configured: still show the traceback.
        logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
    logger.error("Exception in app code", exc_info=(type(exc), exc, exc.__traceback__))


def run(
    root: Callable[[], Any] | Any = None,
    *,
    title: str = "nsh",
    size: tuple[int, int] = (480, 640),
    app_id: str = "dev.nsh_py.app",
) -> None:
    """Open a window showing `root` and run until it closes.

    `root` is a component (a function returning elements) or elements.
    Blocks the calling thread, which must be the main thread. Ctrl-C quits
    and raises `KeyboardInterrupt`.
    """
    _core.run(root, title=title, size=size, app_id=app_id)
