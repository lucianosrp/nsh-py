"""Checkboxes, switches and progress bars, bound to signals."""

import nsh

TOPPINGS = ["Cheese", "Mushrooms", "Olives"]


def Toggles():
    picked = {name: nsh.signal(False) for name in TOPPINGS}
    wifi = nsh.signal(True)
    saved = nsh.signal(0)

    def picked_count():
        return sum(s() for s in picked.values())

    def pick_all(value):
        for s in picked.values():
            s.set(value)

    def save():
        saved.update(lambda n: min(n + 25, 100))

    return nsh.view(
        nsh.text("Toppings", class_="text-lg font-semibold"),
        # "All" is checked when every topping is, a dash when some are.
        nsh.checkbox(
            "All",
            checked=lambda: picked_count() == len(TOPPINGS),
            indeterminate=lambda: 0 < picked_count() < len(TOPPINGS),
            on_change=pick_all,
        ),
        *[nsh.checkbox(name, checked=s, class_="pl-6") for name, s in picked.items()],
        nsh.checkbox("Remember my order", checked=True),  # keeps its own value
        nsh.checkbox("Gift wrap (sold out)", disabled=True),
        nsh.text("Settings", class_="text-lg font-semibold pt-2"),
        nsh.switch("Wi-Fi", checked=wifi),
        nsh.text(
            lambda: "Connected" if wifi() else "Offline", class_="text-sm text-muted-foreground"
        ),
        nsh.switch("Airplane mode (managed)", disabled=True),
        nsh.text("Progress", class_="text-lg font-semibold pt-2"),
        nsh.progress(saved, lambda: f"Saved {saved()}%"),
        nsh.progress(lambda: picked_count(), "Toppings picked", max=len(TOPPINGS)),
        nsh.progress(indeterminate=wifi, label="Syncing…"),
        nsh.view(
            nsh.button("Save 25%", on_press=save),
            nsh.button("Reset", on_press=saved.setter(0)),
            class_="flex-row gap-2",
        ),
        class_="p-4 gap-3",
    )


if __name__ == "__main__":
    nsh.run(Toggles, title="Toggles")
