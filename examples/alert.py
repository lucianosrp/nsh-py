"""Default and destructive alerts with action buttons."""

import nsh


def App():
    return nsh.view(
        nsh.card(
            title="Project settings",
            description="Manage who can access this project.",
            class_="w-96",
        ),
        nsh.alert(
            "Saved",
            description="Your changes are live.",
            class_="w-96",
        ),
        nsh.alert(
            "Delete project?",
            nsh.button(
                "Delete",
                on_press=lambda: print("Delete pressed"),
                class_="bg-destructive",
            ),
            description="This action cannot be undone.",
            variant="destructive",
            class_="w-96",
        ),
        class_="flex-1 items-center justify-center gap-4 p-8 bg-background",
    )


if __name__ == "__main__":
    nsh.run(App, title="Alert")
