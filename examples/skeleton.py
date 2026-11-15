"""A poll that shows skeletons while a timer simulates loading results."""

import nsh


def Poll():
    results = nsh.signal(None)

    def load():
        results.set(None)
        nsh.set_timeout(
            2.0,
            results.set,
            [
                {"language": "Python", "votes": 8},
                {"language": "Both", "votes": 5},
                {"language": "Rust", "votes": 3},
            ],
        )

    def content():
        rows = results()
        if rows is None:
            return nsh.view(
                nsh.skeleton(class_="h-8 w-full"),
                nsh.skeleton(class_="h-4 w-48"),
                nsh.skeleton(class_="h-4 w-40"),
                nsh.skeleton(class_="h-4 w-32"),
                class_="gap-4 py-2",
                test_id="poll-loading",
            )
        return [
            nsh.table(rows),
            # This region disappears during loading; let the app own the timer.
            nsh.button("Reload", on_press=lambda: nsh.call_soon(load), class_="mt-2"),
        ]

    load()
    return nsh.view(
        nsh.card(
            content,
            title="Favourite language",
            description=lambda: (
                "Loading results…"
                if results() is None
                else f"{sum(row['votes'] for row in results())} votes so far"
            ),
            class_="w-96",
        ),
        class_="flex-1 items-center justify-center p-6 bg-background",
    )


if __name__ == "__main__":
    nsh.run(Poll, title="Skeleton · Poll", size=(480, 420))
