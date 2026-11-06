"""Type stubs for the Rust extension (src/). Keep in step with src/lib.rs."""

from collections.abc import Callable
from typing import Any

__version__: str

def run(
    root: Callable[[], Any] | Any = None,
    *,
    title: str = "nsh",
    size: tuple[int, int] = (480, 640),
    app_id: str = "dev.nsh_py.app",
) -> None:
    """Run the app until its window closes (src/app.rs)."""

def in_engine() -> bool:
    """Whether Python code running now was called by the engine."""

def notify_all(triggers: list[Trigger]) -> None:
    """Notify triggers together, so what reads several runs once (src/signal.rs)."""

def element_kinds() -> list[str]:
    """The element kinds this build knows (src/elements/mod.rs)."""

def call_soon(func: Callable[..., Any], args: tuple[Any, ...] = ()) -> None:
    """Run `func(*args)` on the engine thread, soon; right away with no app (src/queue.rs)."""

def app_active() -> bool:
    """Whether an app is starting or running: posted jobs will run (src/queue.rs)."""

class Effect:
    """An NSH effect running a Python function (src/schedule.rs). Engine thread only."""

    def __init__(self, func: Callable[[], Any]) -> None: ...
    def dispose(self) -> None: ...

class Timer:
    """A timer, started with `arm()` on the engine thread (src/schedule.rs)."""

    def __init__(
        self, func: Callable[..., Any], args: tuple[Any, ...], seconds: float, repeat: bool
    ) -> None: ...
    def arm(self) -> None: ...
    def cancel(self) -> None: ...
    @property
    def cancelled(self) -> bool: ...

class Trigger:
    """The NSH signal behind a Python signal (src/signal.rs)."""

    def __init__(self) -> None: ...
    def track(self) -> None: ...
    def notify(self) -> bool: ...

class Headless:
    """A headless app for tests (src/headless.rs); use nsh.testing."""

    def __init__(
        self, root: Callable[[], Any] | Any = None, *, size: tuple[float, float] = (390.0, 844.0)
    ) -> None: ...
    def press(self, selector: str) -> None: ...
    def wait_for(self, selector: str, timeout: float = 5.0) -> None: ...
    def texts(self) -> list[str]: ...
    def shows(self, text: str) -> bool: ...
    def close(self) -> None: ...
