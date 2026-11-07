"""A pandas DataFrame in a window: sort it, add rows, watch the totals follow.

Needs pandas (`uv run --with pandas python examples/dataframe.py` if the
project environment doesn't have it).
"""

import random

import pandas as pd

import nsh

rng = random.Random(7)


def new_sale() -> dict:
    return {
        "region": rng.choice(["North", "South", "East", "West"]),
        "product": rng.choice(["Widget", "Gadget", "Gizmo"]),
        "units": rng.randint(1, 50),
        "price": round(rng.uniform(5, 40), 2),
    }


def with_revenue(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(revenue=df["units"] * df["price"])


def App():
    sales = nsh.signal(with_revenue(pd.DataFrame([new_sale() for _ in range(8)])))

    @nsh.computed
    def summary():
        df = sales()
        return f"{len(df)} sales, {df['units'].sum()} units, revenue ${df['revenue'].sum():,.2f}"

    @sales.updater
    def add_sale(df):
        return with_revenue(pd.concat([df, pd.DataFrame([new_sale()])], ignore_index=True))

    def sort_by(column):
        @sales.updater
        def sort(df):
            return df.sort_values(column, ascending=False).reset_index(drop=True)

        return sort

    return nsh.view(
        nsh.text("Sales", class_="text-xl font-semibold text-foreground"),
        nsh.text(summary, class_="text-muted-foreground"),
        nsh.view(
            nsh.button("Sort by revenue", on_press=sort_by("revenue")),
            nsh.button("Sort by units", on_press=sort_by("units")),
            nsh.button("Add a sale", on_press=add_sale),
            class_="flex-row gap-2",
        ),
        # `sales` is a signal, so the table is made again when it changes.
        # The scroll lets it grow past the window.
        nsh.scroll(
            nsh.table(sales, format={"price": "${:.2f}", "revenue": "${:,.2f}"}),
            class_="flex-1",
        ),
        class_="flex-1 p-6 gap-4",
    )


if __name__ == "__main__":
    nsh.run(App, title="DataFrame")
