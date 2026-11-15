"""The app's window: minimize it, close it, or quit the app."""

import nsh


def App():
    window = nsh.current_window()  # while building the tree; handlers keep it
    return nsh.view(
        nsh.text("Window controls", class_="text-2xl font-bold"),
        nsh.view(
            nsh.button("Minimize", on_press=window.minimize),
            nsh.button("Close window", on_press=window.close),
            nsh.button("Quit", on_press=nsh.quit),
            class_="flex-row gap-2",
        ),
        class_="flex-1 items-center justify-center gap-4 p-8",
    )


if __name__ == "__main__":
    nsh.run(App, title="Window")
