"""Running apps: `nsh.run()` and what reports errors in app code."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nsh import _core

logger = logging.getLogger("nsh")

PLATFORMS = ("native", "web", "tui")
"""What `nsh.run(platform=...)` accepts (`None` means native)."""


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
    works in both places.

    `platform="tui"` draws the app in the terminal it runs in, with the
    keyboard and the mouse; Ctrl-C or Ctrl-Q quits. The default, `None`
    (or `"native"`), is this OS's own UI: GTK, AppKit or Win32.

    With no `platform`, the `NSH_PLATFORM` environment variable picks one,
    so any script runs anywhere unchanged: `NSH_PLATFORM=tui python app.py`.
    """
    import os
    import sys

    from nsh import _web

    if platform is None:
        platform = os.environ.get("NSH_PLATFORM") or None

    if platform not in (None, *PLATFORMS):
        raise ValueError(f"platform must be one of {PLATFORMS!r} or None, not {platform!r}")
    if reload and platform in ("web", "tui"):
        raise ValueError(f"reload=True doesn't work with platform={platform!r} yet")
    if platform == "web" and not _web.in_browser():
        script = getattr(sys.modules["__main__"], "__file__", None)
        if script is None:
            raise RuntimeError('platform="web" needs the app to be run as a script file')
        try:
            _web.serve(script)
        except KeyboardInterrupt:
            stopped()  # Ctrl-C stops the server, as it closes a window
        return
    if platform == "tui" and not _web.in_browser():
        _core.run_tui(root)
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
