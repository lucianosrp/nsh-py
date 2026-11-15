"""Separators between stacked sections and side-by-side panes."""

import nsh


def App():
    return nsh.view(
        nsh.view(
            nsh.text("Account", class_="text-lg font-semibold"),
            nsh.text("Profile and privacy settings.", class_="text-sm text-muted-foreground"),
            nsh.separator(class_="my-5"),
            nsh.text("Appearance", class_="text-lg font-semibold"),
            nsh.text("Choose how the application looks.", class_="text-sm text-muted-foreground"),
            nsh.separator(class_="my-5"),
            nsh.view(
                nsh.view(
                    nsh.text("Editor"),
                    class_="flex-1 items-center justify-center",
                ),
                nsh.separator(vertical=True, class_="mx-4"),
                nsh.view(
                    nsh.text("Preview"),
                    class_="flex-1 items-center justify-center",
                ),
                class_="flex-row h-20 items-stretch",
            ),
            class_="w-96 gap-2 p-6 rounded-xl border border-border bg-card",
        ),
        class_="flex-1 items-center justify-center p-8 bg-background",
    )


if __name__ == "__main__":
    nsh.run(App, title="Separator")
