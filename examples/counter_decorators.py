"""The counter again, with named functions and decorators instead of lambdas.

Both styles work, and you can mix them: see examples/counter.py.
"""

import nsh


def Counter():
    count = nsh.signal(0)

    @nsh.computed
    def label():
        return f"Count: {count()}"

    @nsh.computed
    def sign():
        return "negative" if count() < 0 else "zero or more"

    @nsh.computed
    def sign_class():
        return "text-destructive" if count() < 0 else "text-muted-foreground"

    @count.updater
    def decrement(n):
        return n - 1

    @count.updater
    def increment(n):
        return n + 1

    return nsh.view(
        nsh.text(label, class_="text-4xl font-bold text-foreground"),
        nsh.text(sign, class_=sign_class),
        nsh.view(
            nsh.button("−1", on_press=decrement, test_id="dec"),
            nsh.button("+1", on_press=increment, test_id="inc"),
            nsh.button("Reset", on_press=count.setter(0), test_id="reset"),
            class_="flex-row gap-2",
        ),
        class_="flex-1 items-center justify-center gap-4 p-8",
    )


if __name__ == "__main__":
    nsh.run(Counter, title="Counter")
