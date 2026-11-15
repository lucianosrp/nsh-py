"""Tabs: a section list bound to a signal, each with its own panel."""

import nsh


def overview():
    return nsh.view(
        nsh.text("Visitors, sign-ups and conversion this week.", class_="text-foreground"),
        nsh.text("12.4k visitors · 380 sign-ups", class_="text-sm text-muted-foreground"),
        class_="gap-2",
    )


def orders():
    return nsh.view(
        nsh.text("Shipments on the way and recent deliveries.", class_="text-foreground"),
        nsh.text("18 open · 4 out for delivery", class_="text-sm text-muted-foreground"),
        class_="gap-2",
    )


def billing():
    return nsh.view(
        nsh.text("Invoices, plans and payment methods.", class_="text-foreground"),
        nsh.text("Next invoice on the 1st", class_="text-sm text-muted-foreground"),
        class_="gap-2",
    )


PANELS = {
    "Overview": overview,
    "Orders": orders,
    "Billing": billing,
}


def App():
    page = nsh.signal("Overview")

    def section(label: str):
        return nsh.tab(
            label,
            selected=lambda: page() == label,
            on_press=page.setter(label),
        )

    return nsh.view(
        nsh.text("Account", class_="text-xl font-semibold text-foreground"),
        nsh.tabs(*[section(label) for label in PANELS]),
        lambda: PANELS[page()](),
        nsh.text(
            lambda: f"Selected: {page()}",
            class_="text-sm text-muted-foreground",
        ),
        class_="p-6 gap-4 w-96",
    )


if __name__ == "__main__":
    nsh.run(App, title="Tabs")
