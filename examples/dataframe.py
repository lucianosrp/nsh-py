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

    def sort_by(column):
        sales.update(lambda df: df.sort_values(column, ascending=False).reset_index(drop=True))

    def add_row():
        sales.update(lambda df: with_revenue(pd.concat([df, pd.DataFrame([new_sale()])], ignore_index=True)))

    return nsh.view(
        nsh.text("Sales", class_="text-xl font-semibold text-foreground"),
        nsh.text(
            lambda: (
                f"{len(sales())} sales, {sales()['units'].sum()} units, "
                f"revenue ${sales()['revenue'].sum():,.2f}"
            ),
            class_="text-muted-foreground",
        ),
        nsh.view(
            nsh.button("Sort by revenue", on_press=lambda: sort_by("revenue")),
            nsh.button("Sort by units", on_press=lambda: sort_by("units")),
            nsh.button("Add a sale", on_press=add_row),
            class_="flex-row gap-2",
        ),
        # `sales` is a signal, so the table is made again when it changes.
        nsh.table(sales, max_rows=12, format={"price": "${:.2f}", "revenue": "${:,.2f}"}),
        class_="p-6 gap-4",
    )


if __name__ == "__main__":
    nsh.run(App, title="DataFrame")
