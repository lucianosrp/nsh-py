# The same counter as examples/counter.py, running in the browser.
import nsh


def Counter():
    count = nsh.signal(0)
    return nsh.view(
        nsh.text("Python in the browser", class_="text-sm text-muted-foreground"),
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
        class_="flex-1 items-center justify-center gap-4 p-8 bg-background",
    )


nsh.run(Counter, title="Counter")
