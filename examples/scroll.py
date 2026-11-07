"""A long list that scrolls."""

import nsh


def App():
    return nsh.view(
        nsh.text("200 rows", class_="text-lg font-semibold px-4 py-3 text-foreground"),
        nsh.scroll(
            *[
                nsh.text(
                    f"Row {i}",
                    class_="px-4 py-2 border-b border-border text-foreground",
                )
                for i in range(200)
            ],
            class_="flex-1",
        ),
        class_="flex-1",
    )


if __name__ == "__main__":
    nsh.run(App, title="Scroll")
