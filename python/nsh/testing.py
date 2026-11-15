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
Text that starts with a lowercase word and a colon (`"b: 2"`,
`"total: 3"`) reads as a prefix, so write `"text:b: 2"`. `"Total: 3"`
is fine as it is.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

from nsh import _core


class WindowState(NamedTuple):
    """What the platform reports of a window (`App.window`)."""

    visible: bool
    minimized: bool
    focused: bool


class App:
    """A running headless app. Use it as a context manager, or `close()`."""

    def __init__(
        self,
        root: Callable[[], Any] | Any = None,
        *,
        size: tuple[float, float] = (390, 844),
        desktop: bool = False,
    ):
        self._app = _core.Headless(root, size=size, desktop=desktop)

    def press(self, selector: str) -> None:
        """Press what `selector` finds, then wait for the app to settle."""
        self._app.press(selector)

    def type_text(self, selector: str, text: str) -> None:
        """Type `text` at the end of the input `selector` finds, key by key,
        then wait for the app to settle. A `"\\n"` is the Enter key (it
        submits)."""
        self._app.type_text(selector, text)

    def value(self, selector: str) -> str | None:
        """The text the input `selector` finds holds (`None`: no such input)."""
        return self._app.value(selector)

    def wait_for(self, selector: str, timeout: float = 5.0) -> None:
        """Wait until `selector` shows; `TimeoutError` after `timeout` s."""
        self._app.wait_for(selector, timeout)

    def texts(self) -> list[str]:
        """The texts shown, in order."""
        return self._app.texts()

    def shows(self, text: str) -> bool:
        """Whether `text` shows. Plain text, not a selector: no prefixes."""
        return self._app.shows(text)

    def scroll(self, selector: str, distance: float) -> None:
        """Scroll the scroll view `selector` names by `distance` points
        along its axis (negative: back), then wait for the app to settle."""
        self._app.scroll(selector, distance)

    def dispatch(self, test_id: str, event: str, **data: float | bool | str) -> None:
        """Deliver `event` to the view `test_id` (bare or `"id:..."`), as the
        platform would, then wait for the app to settle. For what nothing
        headless does on its own, such as a video loading. `event` and the
        `data` fields are NSH's protocol names:

            app.dispatch("player", "onLoad", duration=5.0, width=640, height=360)
            app.dispatch("player", "onProgress", currentTime=1.5, duration=5.0)
        """
        self._app.dispatch(test_id, event, data)

    def seeks(self, test_id: str) -> list[float]:
        """The seconds of the seeks sent to the video `test_id`, in order."""
        return self._app.seeks(test_id)

    def window(self, window_id: str = "main") -> WindowState | None:
        """What the platform reports of window `window_id` (`"main"`): visible,
        minimized, focused. `None` while it isn't open. Needs an app
        opened with `desktop=True` (a phone has no windows)."""
        state = self._app.window_state(window_id)
        return None if state is None else WindowState(*state)

    def close(self) -> None:
        """Stop the app's engine."""
        self._app.close()

    def __enter__(self) -> App:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open(root: Callable[[], Any] | Any = None, **kwargs: Any) -> App:  # noqa: A001
    """Start `root` headless (as `nsh.run` takes it). `size=(w, h)` sets
    the viewport; `desktop=True` runs it as a desktop app, with a main
    window (`App.window`)."""
    return App(root, **kwargs)
