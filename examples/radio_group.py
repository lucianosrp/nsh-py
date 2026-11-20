"""Radio group: pick one option, replace the list, or clear the signal."""

import nsh


def App():
    size = nsh.signal("Medium")
    options = nsh.signal(["Small", "Medium", "Large"])
    disabled = nsh.signal(False)

    def reset():
        options.set(["Small", "Medium", "Large"])
        size.set("Medium")

    return nsh.view(
        nsh.card(
            nsh.text("Size", class_="text-sm font-semibold"),
            nsh.radio_group(
                size,
                options=options,
                disabled=disabled,
                test_id="size",
            ),
            nsh.text(lambda: f"Selected: {size() or 'None'}", class_="text-sm"),
            nsh.view(
                nsh.button("Choose Large", on_press=size.setter("Large")),
                nsh.button("Clear", on_press=size.setter(None)),
                nsh.button("Reset", on_press=reset),
                class_="flex-row gap-2",
            ),
            nsh.button("Use numeric sizes", on_press=options.setter(["36", "38", "40", "42"])),
            nsh.switch("Disable radios", checked=disabled),
            nsh.text("In a row", class_="text-sm font-semibold pt-2"),
            nsh.radio_group(
                "Standard",
                options=["Standard", "Express"],
                class_="flex-row gap-4",
                disabled=True,
            ),
            title="Radio group",
            description="Two-way signals and reactive options.",
            class_="w-full gap-3",
        ),
        class_="flex-1 justify-center p-6",
    )


if __name__ == "__main__":
    nsh.run(App, title="Radio group", size=(480, 560))
