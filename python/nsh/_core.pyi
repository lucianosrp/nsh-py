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

def element_kinds() -> list[str]:
    """The element kinds this build knows (src/elements/mod.rs)."""

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
