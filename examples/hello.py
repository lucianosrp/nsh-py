"""A Python-defined tree: views, texts and a button calling Python."""

import nsh

presses = 0


def on_press():
    global presses
    presses += 1
    print(f"pressed {presses} time(s)")


def broken():
    raise RuntimeError("this handler fails, and the app keeps running")


def App():
    return nsh.view(
        nsh.text("Hello from Python", class_="text-3xl font-bold text-foreground"),
        nsh.text("Each press prints to the terminal.", class_="text-muted-foreground"),
        nsh.view(
            nsh.button("Press me", on_press=on_press),
            nsh.button("Raise", on_press=broken, class_="bg-destructive"),
            class_="flex-row gap-2",
        ),
        class_="flex-1 items-center justify-center gap-4 p-8",
    )


if __name__ == "__main__":
    nsh.run(App, title="Hello from Python")
