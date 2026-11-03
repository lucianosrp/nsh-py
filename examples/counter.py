"""The counter: a signal, a bound text and two buttons."""

import nsh


def Counter():
    count = nsh.signal(0)
    return nsh.view(
        nsh.text(lambda: f"Count: {count()}", class_="text-4xl font-bold text-foreground"),
        nsh.text(
            lambda: "negative" if count() < 0 else "zero or more",
            class_=lambda: "text-destructive" if count() < 0 else "text-muted-foreground",
        ),
        nsh.view(
            nsh.button("−1", on_press=lambda: count.update(lambda n: n - 1), test_id="dec"),
            nsh.button("+1", on_press=lambda: count.update(lambda n: n + 1), test_id="inc"),
            class_="flex-row gap-2",
        ),
        class_="flex-1 items-center justify-center gap-4 p-8",
    )


if __name__ == "__main__":
    nsh.run(Counter, title="Counter")
