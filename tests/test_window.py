"""nsh.quit() and nsh.current_window()."""

import threading

import pytest

import nsh
from nsh.testing import open


def window_app(seen):
    def App():
        window = nsh.current_window()
        seen.append(window)
        return nsh.view(
            nsh.button("Hide", on_press=window.hide),
            nsh.button("Show", on_press=window.show),
            nsh.button("Minimize", on_press=window.minimize),
            nsh.button("Focus", on_press=window.focus),
            nsh.button("Close", on_press=window.close),
            nsh.button("Quit", on_press=nsh.quit),
        )

    return App


def wait_until(condition, timeout=5.0):
    stop = threading.Event()
    for _ in range(int(timeout / 0.01)):
        if condition():
            return
        stop.wait(0.01)
    raise TimeoutError("condition never became true")


def test_current_window_is_the_main_window():
    seen = []
    with open(window_app(seen), desktop=True) as app:
        app.wait_for("Hide")
        (window,) = seen
        assert window.id == "main"
        assert window.is_main
        assert repr(window) == '<nsh window "main">'
        assert app.window().visible


def test_window_methods_reach_the_platform():
    # A hidden window takes no presses: the test thread brings it back
    # through the handle, which posts the call to the app's thread.
    seen = []
    with open(window_app(seen), desktop=True) as app:
        app.wait_for("Hide")
        (window,) = seen
        app.press("Minimize")
        assert app.window().minimized
        window.show()
        wait_until(lambda: app.window().visible)
        assert not app.window().minimized
        app.press("Hide")
        assert not app.window().visible
        window.focus()
        wait_until(lambda: app.window().visible and app.window().focused)
        app.press("Close")
        assert not app.window().visible  # the main window closing ends a real app


def test_window_methods_work_from_another_thread():
    seen = []
    with open(window_app(seen), desktop=True) as app:
        app.wait_for("Hide")
        worker = threading.Thread(target=seen[0].hide)
        worker.start()
        worker.join(5)
        wait_until(lambda: not app.window().visible)


def test_quit_from_a_handler_does_not_raise():
    # The headless driver has no app to end: the Quit only has to get there.
    with open(window_app([]), desktop=True) as app:
        app.press("Quit")
        assert app.shows("Hide")


def test_current_window_outside_the_app_raises():
    with pytest.raises(RuntimeError, match="builds its tree"):
        nsh.current_window()


def test_quit_without_an_app_does_nothing():
    nsh.quit()
