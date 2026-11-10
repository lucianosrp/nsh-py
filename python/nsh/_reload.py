"""Hot reload: redraw a running app when its source files change.

`nsh.run(App, reload=True)`, or `python -m nsh.reload app.py` with no
change to the app, keeps the window open while you edit. On save, the
script runs again (its `nsh.run` call only hands over the new root) and
the window's content is rebuilt from it. Local modules the script imports
are reloaded too. Signals keep their values (a running timer keeps
running), and the window, its size and its place stay.

If the new code raises, the old view stays up and the traceback is
logged, so a typo never closes the app.
"""

from __future__ import annotations

import logging
import runpy
import site
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from nsh import _engine, _signals
from nsh._signals import Signal, signal

logger = logging.getLogger("nsh")

POLL_SECONDS = 0.25
"""How often the watcher looks at the files' modification times."""


_INSTALLED = tuple(
    Path(p).resolve()
    for p in {
        sys.prefix,
        sys.base_prefix,
        sys.exec_prefix,
        *site.getsitepackages(),
        site.getusersitepackages(),
    }
)
"""Where the interpreter and installed packages live: never reloaded."""


def is_app_module(name: str, path: Path, folder: Path) -> bool:
    """Whether a module is the app's own code, to reload with the script.

    nsh itself never reloads, even when the app sits next to it (a script
    in a checkout of nsh-py): a second copy of its classes would make the
    window show elements as text. Nor does anything installed, such as a
    `.venv` inside the app's folder.
    """
    if name == "nsh" or name.startswith("nsh."):
        return False
    if not path.is_relative_to(folder):
        return False
    return not any(path.is_relative_to(p) for p in _INSTALLED) and "site-packages" not in path.parts


class _Captured(Exception):
    """Raised by the stand-in `nsh.run` to stop the script once it has
    handed over its root, so code after `nsh.run(...)` doesn't run twice."""

    def __init__(self, root: Any) -> None:
        super().__init__()
        self.root = root


class _Keeper:
    """Keeps signals' values across reloads, like React's Fast Refresh.

    While the script runs and the window's content renders, every
    `nsh.signal(...)` is recorded under its place in the code: the
    function that made it, which call of that function in this render,
    and which signal in that call. On a reload the values are saved, and
    the signal made at the same place by the new code starts from the
    saved value instead of its initial one. A value of a different type
    than the new initial one (you changed `0` to `""`) is dropped.
    """

    def __init__(self) -> None:
        self.live: dict[tuple[str, int, int], Signal[Any]] = {}
        self.saved: dict[tuple[str, int, int], Any] = {}
        self._previous: dict[tuple[str, int, int], Signal[Any]] = {}
        self._calls: dict[str, int] = {}
        self._frames: dict[str, tuple[Any, int]] = {}

    @contextmanager
    def recording(self) -> Iterator[None]:
        """Record (and restore) the signals made inside the block."""
        self._calls, self._frames = {}, {}
        _signals._signal_hook = self._make
        try:
            yield
        finally:
            _signals._signal_hook = None
            self._frames = {}  # don't keep the frames' locals alive

    def save(self) -> None:
        """Before a reload: remember the current signals' values."""
        self.saved = {key: s._value for key, s in self.live.items()}
        self._previous, self.live = self.live, {}

    def failed(self) -> None:
        """The reload failed: the old view, and its signals, stay."""
        self.live, self.saved = self._previous, {}

    def _make(self, value: Any, where: tuple[str, Any] | None = None) -> Signal[Any]:
        """`where` is (name, group) when the caller knows better than the
        stack: a class component's fields are keyed by its class, and
        grouped by its instance."""
        if where is None:
            frame = sys._getframe(2)  # the caller of nsh.signal
            code = frame.f_code
            name = f"{code.co_filename}:{getattr(code, 'co_qualname', code.co_name)}"
        else:
            name, frame = where
        last = self._frames.get(name)
        if last is not None and last[0] is frame:
            call, index = self._calls[name], last[1] + 1
        else:
            call, index = self._calls.get(name, -1) + 1, 0
            self._calls[name] = call
        self._frames[name] = (frame, index)
        key = (name, call, index)
        if key in self.saved:
            old = self.saved.pop(key)
            if value is None or type(old) is type(value):
                value = old
        made = Signal(value)
        self.live[key] = made
        return made


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
        self._keeper = _Keeper()
        if self._root is None:
            self._root = self._run_script()
        self._mtimes = self._snapshot()

    def root(self) -> Callable[[], Any]:
        """The window's root: the latest one, made again on each reload."""

        def region() -> Any:
            self._version()  # read, so a reload re-makes this region
            root = self._root
            with self._keeper.recording():
                return root() if callable(root) else root

        def Reloading() -> Any:  # noqa: N802 (a component)
            self._version = signal(0)
            return region

        return Reloading

    def reload(self) -> bool:
        """Run the script again and show its new root. Returns whether it
        worked; on an error the old view stays and the error is logged."""
        self._forget_local_modules()
        self._keeper.save()
        try:
            root = self._run_script()
        except Exception:
            self._keeper.failed()
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
            with self._keeper.recording():
                runpy.run_path(str(self.script), run_name="__main__")
        except _Captured as captured:
            return captured.root
        finally:
            nsh.run = real
            if added:
                sys.path.remove(folder)
        raise RuntimeError(f"{self.script.name} never called nsh.run(...)")

    def _local_modules(self) -> dict[str, Path]:
        """The app's own imported modules: their file is in the script's
        folder (or below), and they aren't nsh or an installed package."""
        folder = self.script.parent
        found = {}
        for name, module in list(sys.modules.items()):
            path = getattr(module, "__file__", None)
            if path and is_app_module(name, Path(path).resolve(), folder):
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
