"""A Kanban board: one list per column; ← → moves a card between them."""

import itertools

import nsh

TO_DO, DOING, DONE = "To do", "Doing", "Done"
COLUMNS = [TO_DO, DOING, DONE]


def Ticket(card, move_left, move_right):
    """One ticket. Made once per id: it stays as it moves between columns."""
    return nsh.card(
        nsh.view(
            nsh.button("←", on_press=move_left, class_="px-2 py-1", test_id=f"left-{card['id']}"),
            nsh.button("→", on_press=move_right, class_="px-2 py-1", test_id=f"right-{card['id']}"),
            class_="flex-row gap-1",
        ),
        title=card["title"],
        class_="p-3 gap-2",
        test_id=f"card-{card['id']}",
    )


def Column(name, cards, move):
    i = COLUMNS.index(name)
    left = COLUMNS[i - 1] if i > 0 else None
    right = COLUMNS[i + 1] if i < len(COLUMNS) - 1 else None

    def row(card):
        return Ticket(
            card,
            move_left=(lambda: move(card["id"], name, left)) if left else None,
            move_right=(lambda: move(card["id"], name, right)) if right else None,
        )

    return nsh.card(
        nsh.each(cards, row, key=lambda c: c["id"]),
        title=name,
        description=lambda: f"{len(cards())} cards",
        class_="flex-1 gap-2 min-w-56",
        test_id=f"column-{name}",
    )


def Kanban():
    columns = {
        TO_DO: nsh.signal([{"id": 1, "title": "Buy milk"}]),
        DOING: nsh.signal([{"id": 2, "title": "Write docs"}]),
        DONE: nsh.signal([{"id": 3, "title": "Ship it"}]),
    }
    ids = itertools.count(4)

    def add():
        n = next(ids)
        columns[TO_DO].update(lambda cs: [*cs, {"id": n, "title": f"Card {n}"}])

    def move(id, src, dst):
        card = next(c for c in columns[src]() if c["id"] == id)
        columns[src].update(lambda cs: [c for c in cs if c["id"] != id])
        columns[dst].update(lambda cs: [*cs, card])

    return nsh.view(
        nsh.text("Kanban", class_="text-2xl font-bold text-foreground"),
        nsh.view(
            *[Column(name, columns[name], move) for name in COLUMNS],
            class_="flex-1 flex-row gap-4 items-start",
        ),
        nsh.button("Add", on_press=add, test_id="add"),
        class_="flex-1 gap-4 p-6",
    )


if __name__ == "__main__":
    nsh.run(Kanban, title="Kanban", size=(900, 560))
