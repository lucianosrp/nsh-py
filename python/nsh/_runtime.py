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
    reload: bool = False,
    platform: str | None = None,
) -> None:
    """Open a window showing `root` and run until it closes.

    `root` is a component (a function returning elements) or elements.
    Blocks the calling thread, which must be the main thread. Ctrl-C in
    the terminal closes the app and returns, as closing the window does:
    no `KeyboardInterrupt` traceback.

    `reload=True` redraws the window when you save the script (or a local
    module it imports), keeping the window open: for development. Signals
    keep their values across reloads. `python -m nsh.reload
    app.py` does the same without changing the script.

    `platform="web"` shows the app in your browser instead of a window:
    the browser runs the script with Pyodide. Save and refresh the page to
    see changes. It needs the web build of nsh-py (`web/README.md`). In
    the browser itself, `nsh.run` always runs there, so the same script
    works in both places. The default, `None` (or `"native"`), is this
    OS's own UI: GTK, AppKit or Win32.
    """
    import sys

    from nsh import _web

    if platform not in (None, *_web.PLATFORMS):
        raise ValueError(f"platform must be one of {_web.PLATFORMS!r} or None, not {platform!r}")
    if platform == "web" and not _web.in_browser():
        if reload:
            raise ValueError('reload=True doesn\'t work with platform="web": refresh the page')
        script = getattr(sys.modules["__main__"], "__file__", None)
        if script is None:
            raise RuntimeError('platform="web" needs the app to be run as a script file')
        _web.serve(script)
        return
    if reload:
        from nsh._reload import run_reloading

        script = getattr(sys.modules["__main__"], "__file__", None)
        if script is None:
            raise RuntimeError("reload=True needs the app to be run as a script file")
        run_reloading(script, root, title=title, size=size, app_id=app_id)
        return
    try:
        _core.run(root, title=title, size=size, app_id=app_id)
    except KeyboardInterrupt:
        stopped()


def stopped() -> None:
    """Ctrl-C closed the app. That's how a terminal app is stopped, not an error."""
    logger.debug("Ctrl-C: the app was closed")
