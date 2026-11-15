"""Select a size, replace its options, or update its signal from a button."""

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
            nsh.select(
                size,
                options=options,
                placeholder="Choose a size",
                disabled=disabled,
                accessibility_label="Size",
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
            nsh.switch("Disable select", checked=disabled),
            nsh.text("Unavailable", class_="text-sm font-semibold pt-2"),
            nsh.select("Standard", options=["Standard"], disabled=True),
            title="Select",
            description="Two-way signals and reactive options.",
            class_="w-full gap-3",
        ),
        class_="flex-1 justify-center p-6",
    )


if __name__ == "__main__":
    nsh.run(App, title="Select", size=(480, 520))
