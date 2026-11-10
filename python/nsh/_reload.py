"""Hot reload: redraw a running app when its source files change.

`nsh.run(App, reload=True)`, or `python -m nsh.reload app.py` with no
change to the app, keeps the window open while you edit. On save, the
script runs again (its `nsh.run` call only hands over the new root) and
the window's content is rebuilt from it. Local modules the script imports
are reloaded too. State made inside components starts over, as after a
restart, but the window, its size and its place stay.

If the new code raises, the old view stays up and the traceback is
logged, so a typo never closes the app.
"""

from __future__ import annotations

import logging
import runpy
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nsh import _engine
from nsh._signals import signal

logger = logging.getLogger("nsh")

POLL_SECONDS = 0.25
"""How often the watcher looks at the files' modification times."""


class _Captured(Exception):
    """Raised by the stand-in `nsh.run` to stop the script once it has
    handed over its root, so code after `nsh.run(...)` doesn't run twice."""

    def __init__(self, root: Any) -> None:
        super().__init__()
        self.root = root


class Reloader:
    """Runs `script` for its root, and runs it again on demand.

    `root()` is the component to hand to the window: a region that shows
    the latest root and is rebuilt by `reload()`. `watch()` starts a
    thread that calls `reload()` on the app thread when a file changes.
    """

    def __init__(self, script: str | Path, root: Any = None) -> None:
        self.script = Path(script).resolve()
        self._root = root
        self._version: Any = None  # made on the app thread, by root()
        self._mtimes: dict[Path, float] = {}
        self._stop = threading.Event()
        if self._root is None:
            self._root = self._run_script()
        self._mtimes = self._snapshot()

    def root(self) -> Callable[[], Any]:
        """The window's root: the latest one, made again on each reload."""

        def region() -> Any:
            self._version()  # read, so a reload re-makes this region
            root = self._root
            return root() if callable(root) else root

        def Reloading() -> Any:  # noqa: N802 (a component)
            self._version = signal(0)
            return region

        return Reloading

    def reload(self) -> bool:
        """Run the script again and show its new root. Returns whether it
        worked; on an error the old view stays and the error is logged."""
        self._forget_local_modules()
        try:
            root = self._run_script()
        except Exception:
            logger.exception("Reload of %s failed; keeping the old view", self.script.name)
            return False
        self._root = root
        if self._version is not None:
            self._version.update(lambda n: n + 1)
        logger.info("Reloaded %s", self.script.name)
        return True

    def watch(self) -> None:
        """Watch the files from a daemon thread; reload on a change."""
        threading.Thread(target=self._watch, name="nsh-reload", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _watch(self) -> None:
        while not self._stop.wait(POLL_SECONDS):
            now = self._snapshot()
            if now != self._mtimes:
                self._mtimes = now
                _engine.call_soon(self.reload)

    def _run_script(self) -> Any:
        """Run the script as `__main__` with `nsh.run` standing in, and
        return the root it passes to `nsh.run`."""
        import nsh

        def capture(root: Any = None, **_: Any) -> None:
            raise _Captured(root)

        real = nsh.run
        nsh.run = capture
        folder = str(self.script.parent)
        added = folder not in sys.path
        if added:
            sys.path.insert(0, folder)
        try:
            runpy.run_path(str(self.script), run_name="__main__")
        except _Captured as captured:
            return captured.root
        finally:
            nsh.run = real
            if added:
                sys.path.remove(folder)
        raise RuntimeError(f"{self.script.name} never called nsh.run(...)")

    def _local_modules(self) -> dict[str, Path]:
        """Imported modules whose file is in the script's folder (or below)."""
        folder = self.script.parent
        found = {}
        for name, module in list(sys.modules.items()):
            path = getattr(module, "__file__", None)
            if path and Path(path).resolve().is_relative_to(folder):
                found[name] = Path(path).resolve()
        return found

    def _forget_local_modules(self) -> None:
        for name in self._local_modules():
            sys.modules.pop(name, None)

    def _snapshot(self) -> dict[Path, float]:
        paths = {self.script, *self._local_modules().values()}
        times = {}
        for path in paths:
            try:
                times[path] = path.stat().st_mtime
            except OSError:
                times[path] = -1.0
        return times


def run_reloading(script: str | Path, root: Any = None, **options: Any) -> None:
    """Open the window for `script` and reload it whenever it changes."""
    from nsh import _core

    reloader = Reloader(script, root)
    reloader.watch()
    logger.info("Watching %s for changes", reloader.script.name)
    try:
        _core.run(reloader.root(), **options)
    finally:
        reloader.stop()


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: python -m nsh.reload app.py [args...]")
        return 0 if argv else 2
    script = Path(argv[0])
    if not script.is_file():
        print(f"error: {argv[0]} is not a file", file=sys.stderr)
        return 2
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s", level=logging.INFO)
    sys.argv = [str(script), *argv[1:]]
    # Run once for the root and the window options, then keep reloading.
    options: dict[str, Any] = {}
    import nsh

    def capture(root: Any = None, **kwargs: Any) -> None:
        options.update(kwargs)
        raise _Captured(root)

    real = nsh.run
    nsh.run = capture
    sys.path.insert(0, str(script.resolve().parent))
    try:
        runpy.run_path(str(script), run_name="__main__")
    except _Captured as captured:
        root = captured.root
    else:
        print(f"error: {script} never called nsh.run(...)", file=sys.stderr)
        return 2
    finally:
        nsh.run = real
    options.pop("reload", None)
    run_reloading(script, root, **options)
    return 0
