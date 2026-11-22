"""Button variants and sizes."""

import nsh


def Buttons():
    return nsh.view(
        nsh.text("Variants", class_="text-lg font-semibold"),
        nsh.view(
            nsh.button("Default"),
            nsh.button("Secondary", variant="secondary"),
            nsh.button("Outline", variant="outline"),
            nsh.button("Ghost", variant="ghost"),
            nsh.button("Destructive", variant="destructive"),
            class_="flex-row flex-wrap gap-2",
        ),
        nsh.text("Sizes", class_="text-lg font-semibold pt-2"),
        nsh.view(
            nsh.button("Small", size="sm"),
            nsh.button("Medium"),
            nsh.button("Large", size="lg"),
            class_="flex-row items-center gap-2",
        ),
        class_="p-4 gap-3",
    )


if __name__ == "__main__":
    nsh.run(Buttons, title="Buttons")
