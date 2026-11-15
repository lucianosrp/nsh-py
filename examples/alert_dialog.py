"""A native alert dialog with cancel and destructive actions.

Mirrors https://nsh.dev/elements/alert-dialog/.
"""

import nsh


def App():
    answer = nsh.signal("–")

    def confirm():
        nsh.alert_dialog(
            "Delete the photo?",
            description="This cannot be undone.",
            actions=[
                {"id": "cancel", "label": "Cancel", "role": "cancel"},
                {"id": "delete", "label": "Delete", "role": "destructive"},
            ],
            on_result=lambda action: answer.set("deleted" if action == "delete" else "kept"),
        )

    return nsh.view(
        nsh.button(
            "Delete…",
            on_press=confirm,
            class_="rounded-lg bg-destructive px-4 py-3 font-semibold",
            test_id="ask",
        ),
        nsh.text(answer),
        class_="flex-1 gap-3 p-4 pt-12 bg-background",
    )


if __name__ == "__main__":
    nsh.run(App, title="Alert Dialog")
