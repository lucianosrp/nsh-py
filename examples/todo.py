"""A to-do list: `nsh.each` keeps each row, so a change only touches its own.

There's no text input yet, so "Add" adds a numbered task.
"""

import itertools

import nsh


def TodoRow(todo, toggle, remove):
    """One task. Made once per id: it stays as other tasks come and go."""
    done = todo["done"]
    return nsh.view(
        nsh.text(
            ("✓ " if done else "") + todo["title"],
            class_="flex-1 " + ("text-muted-foreground line-through" if done else "text-foreground"),
            on_press=lambda: toggle(todo["id"]),
            test_id=f"toggle-{todo['id']}",
        ),
        nsh.button("Remove", on_press=lambda: remove(todo["id"]), test_id=f"remove-{todo['id']}"),
        class_="flex-row items-center gap-2",
    )


def TodoApp():
    todos = nsh.signal(
        [
            {"id": 1, "title": "Buy milk", "done": False},
            {"id": 2, "title": "Write docs", "done": False},
            {"id": 3, "title": "Ship it", "done": False},
        ]
    )
    ids = itertools.count(4)

    def add():
        n = next(ids)
        todos.update(lambda ts: [*ts, {"id": n, "title": f"Task {n}", "done": False}])

    def toggle(id):
        # A new dict for the toggled task: its row renders again, the others stay.
        todos.update(lambda ts: [{**t, "done": not t["done"]} if t["id"] == id else t for t in ts])

    def remove(id):
        todos.update(lambda ts: [t for t in ts if t["id"] != id])

    left = nsh.computed(lambda: sum(not t["done"] for t in todos()))

    return nsh.view(
        nsh.text("To do", class_="text-2xl font-bold text-foreground"),
        nsh.each(todos, lambda t: TodoRow(t, toggle, remove), key=lambda t: t["id"]),
        nsh.text(lambda: f"{left()} of {len(todos())} left", class_="text-sm text-muted-foreground"),
        nsh.button("Add", on_press=add, test_id="add"),
        class_="flex-1 gap-3 p-8",
    )


if __name__ == "__main__":
    nsh.run(TodoApp, title="To do")
