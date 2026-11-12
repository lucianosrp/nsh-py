"""A store dashboard: a sidebar, a header, KPI cards, a live orders table.

Orders keep arriving while "Live orders" is on; the search box filters
the table, and the cards and goals follow the orders. Runs anywhere:

    uv run python examples/dashboard.py                    # a window
    NSH_PLATFORM=web uv run python examples/dashboard.py   # the browser
    NSH_PLATFORM=tui uv run python examples/dashboard.py   # the terminal
"""

import itertools
import random

import nsh

CUSTOMERS = [
    "Ada Lovelace",
    "Alan Turing",
    "Grace Hopper",
    "Linus Torvalds",
    "Guido van Rossum",
    "Margaret Hamilton",
    "Ken Thompson",
    "Barbara Liskov",
    "Dennis Ritchie",
]
PRODUCTS = {
    "Keyboard": 89.0,
    "Monitor": 249.0,
    "Headphones": 129.0,
    "Desk lamp": 39.0,
    "Webcam": 69.0,
    "Chair": 319.0,
}
STATUSES = ["Paid", "Paid", "Paid", "Pending", "Refunded"]
NAV = ["Overview", "Orders", "Customers", "Products", "Settings"]
REVENUE_GOAL = 6000.0
ORDERS_GOAL = 40

ids = itertools.count(1042)


def new_order() -> dict:
    product = random.choice(list(PRODUCTS))
    qty = random.choice([1, 1, 1, 2, 3])
    return {
        "order": f"#{next(ids)}",
        "customer": random.choice(CUSTOMERS),
        "product": product,
        "qty": qty,
        "status": random.choice(STATUSES),
        "total": PRODUCTS[product] * qty,
    }


def Sidebar(page):
    def item(name):
        return nsh.view(
            nsh.text(
                name,
                class_=lambda: (
                    "text-sm font-medium "
                    + ("text-primary-foreground" if page() == name else "text-muted-foreground")
                ),
            ),
            on_press=lambda: page.set(name),
            class_=lambda: (
                "px-3 py-2 rounded-md " + ("bg-primary" if page() == name else "hover:bg-muted")
            ),
        )

    return nsh.view(
        nsh.view(
            nsh.view(class_="w-8 h-8 rounded-lg bg-primary"),
            nsh.text("Orbit", class_="text-lg font-bold text-foreground"),
            class_="flex-row items-center gap-2 px-3 pb-6",
        ),
        *[item(name) for name in NAV],
        nsh.view(class_="flex-1"),
        nsh.text("nsh-py demo store", class_="text-xs text-muted-foreground px-3"),
        class_="w-56 p-4 gap-1 border-r border-border bg-card",
    )


def Kpi(label, value, note):
    return nsh.card(
        nsh.text(label, class_="text-sm text-muted-foreground"),
        nsh.text(value, class_="text-2xl font-bold text-card-foreground"),
        nsh.text(note, class_="text-xs text-muted-foreground"),
        class_="flex-1 gap-1 p-5",
    )


def App():
    page = nsh.signal("Overview")
    orders = nsh.signal([new_order() for _ in range(12)])
    query = nsh.signal("")
    live = nsh.signal(True)
    paid_only = nsh.signal(False)

    @nsh.computed
    def paid():
        return [o for o in orders() if o["status"] == "Paid"]

    @nsh.computed
    def revenue():
        return sum(o["total"] for o in paid())

    @nsh.computed
    def shown():
        q = query().strip().lower()
        rows = paid() if paid_only() else orders()
        rows = [o for o in rows if not q or q in o["customer"].lower() or q in o["product"].lower()]
        return list(reversed(rows))

    def add_order():
        orders.set([*orders(), new_order()])

    def tick():
        if live():
            add_order()

    nsh.set_interval(2, tick)

    header = nsh.view(
        nsh.view(
            nsh.text(page, class_="text-2xl font-bold text-foreground"),
            nsh.text(
                "Your store at a glance, updated live.", class_="text-sm text-muted-foreground"
            ),
            class_="flex-1 gap-1",
        ),
        nsh.input(
            query,
            placeholder="Search orders…",
            class_="w-64 border border-border rounded-md px-3 py-2 text-foreground",
        ),
        nsh.button("New order", on_press=add_order),
        class_="flex-row items-center gap-3 px-8 py-6 border-b border-border",
    )

    kpis = nsh.view(
        Kpi("Revenue", lambda: f"${revenue():,.0f}", lambda: f"{len(paid())} paid orders"),
        Kpi("Orders", lambda: f"{len(orders())}", "since this morning"),
        Kpi(
            "Average order", lambda: f"${revenue() / max(len(paid()), 1):,.2f}", "paid orders only"
        ),
        Kpi(
            "Refunds", lambda: f"{sum(o['status'] == 'Refunded' for o in orders())}", "this session"
        ),
        class_="flex-row gap-4",
    )

    recent = nsh.card(
        nsh.table(
            shown,
            columns=["order", "customer", "product", "qty", "status", "total"],
            format={"total": "${:,.2f}"},
            widths={"order": "w-20", "qty": "w-12", "status": "w-24", "total": "w-24"},
            max_rows=10,
        ),
        title="Recent orders",
        description=lambda: f"{len(shown())} orders match",
        class_="flex-1",
    )

    side = nsh.view(
        nsh.card(
            nsh.progress(
                lambda: min(revenue(), REVENUE_GOAL),
                max=REVENUE_GOAL,
                label=lambda: f"Revenue ${revenue():,.0f} of ${REVENUE_GOAL:,.0f}",
            ),
            nsh.progress(
                lambda: min(len(orders()), ORDERS_GOAL),
                max=ORDERS_GOAL,
                label=lambda: f"Orders {len(orders())} of {ORDERS_GOAL}",
            ),
            title="Today's goals",
            class_="gap-4",
        ),
        nsh.card(
            nsh.switch("Live orders", checked=live),
            nsh.switch("Paid orders only", checked=paid_only),
            title="Settings",
            class_="gap-3",
        ),
        class_="w-80 gap-4",
    )

    main = nsh.scroll(
        nsh.view(
            kpis,
            nsh.view(recent, side, class_="flex-row gap-4 items-start"),
            class_="p-8 gap-6",
        ),
        class_="flex-1",
    )

    return nsh.view(
        Sidebar(page),
        nsh.view(header, main, class_="flex-1"),
        class_="flex-1 flex-row bg-background",
    )


if __name__ == "__main__":
    nsh.run(App, title="Orbit", size=(1280, 800))
