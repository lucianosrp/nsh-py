"""Test apps without a window: `nsh.testing.open(App)`.

    from nsh.testing import open

    def test_counter():
        with open(Counter) as app:
            app.press("+1")
            app.wait_for("Count: 1")
            assert "Count: 1" in app.texts()

The app runs on NSH's engine thread with no display (nsh-testing's
headless driver), exactly as it would in a window. Selectors: a bare
string matches a test id, then a label, then a text; or be explicit with
`"id:inc"`, `"text:+1"`, `"text:/regex/i"`, `"role:button[Save]"`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh import _core


class App:
    """A running headless app. Use it as a context manager, or `close()`."""

    def __init__(self, root: Callable[[], Any] | Any = None, *, size: tuple[float, float] = (390, 844)):
        self._app = _core.Headless(root, size=size)

    def press(self, selector: str) -> None:
        """Press what `selector` finds, then wait for the app to settle."""
        self._app.press(selector)

    def wait_for(self, selector: str, timeout: float = 5.0) -> None:
        """Wait until `selector` shows; `TimeoutError` after `timeout` s."""
        self._app.wait_for(selector, timeout)

    def texts(self) -> list[str]:
        """The texts shown, in order."""
        return self._app.texts()

    def shows(self, text: str) -> bool:
        """Whether `text` shows."""
        return self._app.shows(text)

    def close(self) -> None:
        """Stop the app's engine."""
        self._app.close()

    def __enter__(self) -> App:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open(root: Callable[[], Any] | Any = None, **kwargs: Any) -> App:  # noqa: A001
    """Start `root` headless (as `nsh.run` takes it)."""
    return App(root, **kwargs)
