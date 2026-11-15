"""Badge variants, a reactive unread count, and custom classes."""

import nsh


def App():
    unread = nsh.signal(3)
    return nsh.view(
        nsh.card(
            nsh.view(
                nsh.badge("Default"),
                nsh.badge("Secondary", variant="secondary"),
                nsh.badge("Outline", variant="outline"),
                nsh.badge("Destructive", variant="destructive"),
                class_="flex-row items-center gap-2",
            ),
            nsh.view(
                nsh.badge(
                    lambda: f"{unread()} unread",
                    variant="secondary",
                    class_="self-center",
                    test_id="unread",
                ),
                nsh.button(
                    "Read one",
                    on_press=unread.updater(lambda n: max(0, n - 1)),
                    test_id="read",
                ),
                class_="flex-row items-center gap-3",
            ),
            nsh.badge("Custom outline", variant="outline", class_="rounded-md border-primary px-4"),
            title="Badges",
            description="Variants, a reactive count, and custom classes.",
            class_="w-full gap-4",
        ),
        class_="flex-1 justify-center p-6",
    )


if __name__ == "__main__":
    nsh.run(App, title="Badges", size=(600, 360))
