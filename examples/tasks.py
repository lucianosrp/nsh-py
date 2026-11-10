"""Tasks: type one and press Enter; tick it off; the count follows."""

import nsh


def Tasks():
    tasks = nsh.signal(
        [
            {"id": 1, "title": "Try nsh-py", "done": True},
            {"id": 2, "title": "Write a native app in Python", "done": False},
            {"id": 3, "title": "Show a friend", "done": False},
        ]
    )
    draft = nsh.signal("")

    def add(title):
        if title.strip():
            tasks.update(lambda ts: [*ts, {"id": len(ts) + 1, "title": title, "done": False}])
            draft.set("")

    def toggle(id, done):
        tasks.update(lambda ts: [{**t, "done": done} if t["id"] == id else t for t in ts])

    def row(task):
        return nsh.checkbox(
            task["title"],
            checked=task["done"],
            on_change=lambda done: toggle(task["id"], done),
        )

    return nsh.card(
        nsh.input(
            draft,
            placeholder="What needs doing?",
            on_submit=add,
            test_id="new",
            class_="rounded-md border border-input px-3 py-2",
        ),
        nsh.each(tasks, row, key=lambda t: t["id"]),
        title="Tasks",
        description=lambda: f"{sum(not t['done'] for t in tasks())} left",
        class_="m-6 w-96 gap-3",
    )


if __name__ == "__main__":
    nsh.run(Tasks, title="Tasks")
