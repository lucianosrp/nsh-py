"""A picture from a file, from bytes, and with a bound size."""

from pathlib import Path

import nsh

DOT = Path(__file__).parent / "assets" / "dot.png"


def App():
    big = nsh.signal(False)
    png = DOT.read_bytes()
    return nsh.view(
        nsh.text("nsh.image", class_="text-lg font-semibold text-foreground"),
        nsh.image(DOT, alt="A blue square from a file", fit="contain", class_="w-32 h-32"),
        nsh.image(png, alt="The same square from bytes", fit="cover", class_="w-16 h-16"),
        nsh.button(
            lambda: "Shrink" if big() else "Grow",
            on_press=lambda: big.update(lambda v: not v),
            test_id="toggle",
        ),
        nsh.image(
            DOT,
            alt="Grows when you press",
            class_=lambda: "w-48 h-48" if big() else "w-16 h-16",
            fit="contain",
        ),
        class_="p-4 gap-3 items-center",
    )


if __name__ == "__main__":
    nsh.run(App, title="Image")
