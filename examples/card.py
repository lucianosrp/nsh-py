"""A card with a bound title, a description and a button."""

import nsh


def App():
    clicks = nsh.signal(0)
    return nsh.view(
        nsh.card(
            nsh.button("Press", on_press=lambda: clicks.update(lambda n: n + 1), test_id="press"),
            title=lambda: f"Pressed {clicks()} times",
            description="The title is a lambda, so it follows the signal.",
            class_="w-80",
        ),
        class_="flex-1 items-center justify-center p-8",
    )


if __name__ == "__main__":
    nsh.run(App, title="Card")
