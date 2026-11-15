"""The app and its window: `nsh.quit()` and `nsh.current_window()`.

    def App():
        window = nsh.current_window()    # while building the tree
        return nsh.view(
            nsh.button("Minimize", on_press=window.minimize),
            nsh.button("Quit", on_press=nsh.quit),
        )

Both are safe to call from any thread: from elsewhere the call is posted
to the app's thread and runs soon. With no app running they do nothing.
"""

from __future__ import annotations

from nsh import _core

Window = _core.Window
"""A handle on one of the app's windows: `close()`, `hide()`, `show()`,
`focus()`, `minimize()`, plus `id` and `is_main`. Get it from
`nsh.current_window()`."""


def quit() -> None:  # noqa: A001
    """Quit the app, as its Quit menu item does: every window closes and
    `nsh.run` returns. The app can't cancel it.

        nsh.button("Quit", on_press=nsh.quit)

    On Windows, NSH 0.5.1 ends the process when the app ends, so
    `nsh.run` doesn't return there (closing the window does the same).

    Safe from any thread. Does nothing when no app is running.
    """
    _core.quit()


def current_window() -> Window:
    """The window the app's tree is shown in.

    Call it while building the tree (in the root function or a
    component), keep the handle, and use it in handlers:

        def App():
            window = nsh.current_window()
            return nsh.button("Close", on_press=window.close)

    Closing the main window ends the app, as when the user closes it.
    Raises `RuntimeError` anywhere else (in a plain script, or a worker
    thread). The handle's methods work from any thread, and do nothing
    once the component that made it is gone.
    """
    return _core.current_window()
