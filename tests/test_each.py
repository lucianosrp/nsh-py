"""`nsh.each`: keyed lists render only the rows that came."""

import logging
import pathlib
import runpy

import pytest

import nsh
from nsh.testing import open

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"


def todo(id, title, done=False):
    return {"id": id, "title": title, "done": done}


def test_arguments_are_checked():
    with pytest.raises(TypeError, match="render must be callable"):
        nsh.each([1], "not callable")
    with pytest.raises(TypeError, match="key must be callable"):
        nsh.each([1], str, key="id")


def test_static_items_are_read_once():
    made = nsh.each((n for n in range(3)), lambda n: nsh.text(f"n{n}"))
    assert made.items == (0, 1, 2)
    with open(lambda: nsh.view(made)) as app:
        assert app.texts() == ["n0", "n1", "n2"]


def test_only_new_keys_render():
    renders = []

    def render(item):
        renders.append(item["id"])
        return nsh.text(item["title"])

    def App():
        items = nsh.signal([todo(1, "a"), todo(2, "b")])
        return nsh.view(
            nsh.each(items, render, key=lambda t: t["id"]),
            nsh.button("add", on_press=items.mutator(lambda xs: xs.append(todo(3, "c")))),
            nsh.button("prepend", on_press=lambda: items.update(lambda xs: [todo(0, "z"), *xs])),
        )

    with open(App) as app:
        assert app.texts()[:2] == ["a", "b"]
        app.press("add")
        app.wait_for("c")
        app.press("prepend")
        app.wait_for("z")
        assert app.texts()[:4] == ["z", "a", "b", "c"]
    assert renders == [1, 2, 3, 0]


def test_reorder_moves_rows_without_rendering():
    renders = []

    def render(word):
        renders.append(word)
        return nsh.text(word)

    def App():
        words = nsh.signal(["a", "b", "c"])  # default key: the item itself
        return nsh.view(
            nsh.each(words, render),
            nsh.button("reverse", on_press=lambda: words.update(lambda ws: ws[::-1])),
        )

    with open(App) as app:
        app.press("reverse")
        assert app.texts()[:3] == ["c", "b", "a"]
        app.press("reverse")
        assert app.texts()[:3] == ["a", "b", "c"]
    assert renders == ["a", "b", "c"]


def test_removed_keys_go():
    def App():
        items = nsh.signal([1, 2, 3])
        return nsh.view(
            nsh.each(items, lambda n: nsh.text(f"row {n}")),
            nsh.button(
                "drop 2", on_press=lambda: items.update(lambda xs: [x for x in xs if x != 2])
            ),
            nsh.button("clear", on_press=items.setter([])),
        )

    with open(App) as app:
        app.press("drop 2")
        assert [t for t in app.texts() if t.startswith("row")] == ["row 1", "row 3"]
        app.press("clear")
        assert not [t for t in app.texts() if t.startswith("row")]


def test_row_local_signal_survives_a_sibling_insert():
    def Row(item):
        clicks = nsh.signal(0)  # the row's own state
        return nsh.button(
            lambda: f"{item['title']}: {clicks()}",
            on_press=clicks.updater(lambda n: n + 1),
            test_id=f"row{item['id']}",
        )

    def App():
        items = nsh.signal([todo(1, "a"), todo(2, "b")])
        return nsh.view(
            nsh.each(items, Row, key=lambda t: t["id"]),
            nsh.button(
                "insert", on_press=lambda: items.update(lambda xs: [xs[0], todo(9, "new"), *xs[1:]])
            ),
        )

    with open(App) as app:
        app.press("id:row2")
        app.press("id:row2")
        app.wait_for("b: 2")
        app.press("insert")
        app.wait_for("new: 0")
        assert app.shows("b: 2")
        assert app.texts()[:3] == ["a: 0", "new: 0", "b: 2"]


def test_changed_item_under_a_key_renders_its_row_again():
    renders = []

    def render(item):
        renders.append(item["id"])
        return nsh.text(f"{item['title']} {'done' if item['done'] else 'open'}")

    def App():
        items = nsh.signal([todo(1, "a"), todo(2, "b")])

        def toggle_b():
            items.update(
                lambda xs: [{**x, "done": not x["done"]} if x["id"] == 2 else x for x in xs]
            )

        return nsh.view(
            nsh.each(items, render, key=lambda t: t["id"]),
            nsh.button("toggle", on_press=toggle_b),
        )

    with open(App) as app:
        app.press("toggle")
        app.wait_for("b done")
        assert app.texts()[:2] == ["a open", "b done"]
    # Item 1 is the same object, so its row stays as it was.
    assert renders == [1, 2, 2]


def test_reads_in_render_do_not_render_the_row_again():
    renders = []

    def App():
        n = nsh.signal(0)

        def render(item):
            renders.append(item)
            return nsh.text(f"{item} read {n()}")  # read once, as documented

        return nsh.view(
            nsh.each(["x"], render),
            nsh.button("inc", on_press=n.updater(lambda v: v + 1)),
        )

    with open(App) as app:
        app.press("inc")
        assert app.shows("x read 0")
    assert renders == ["x"]


def test_computed_items():
    def App():
        items = nsh.signal([todo(1, "a"), todo(2, "b", done=True)])
        open_items = nsh.computed(lambda: [t for t in items() if not t["done"]])
        return nsh.view(
            nsh.each(open_items, lambda t: nsh.text(t["title"]), key=lambda t: t["id"]),
            nsh.button(
                "finish a",
                on_press=lambda: items.update(lambda xs: [{**x, "done": True} for x in xs]),
            ),
        )

    with open(App) as app:
        assert app.shows("a") and not app.shows("b")
        app.press("finish a")
        assert not app.shows("a")


def test_unhashable_items_default_to_identity():
    a, b = todo(1, "a"), todo(2, "b")
    renders = []

    def render(item):
        renders.append(item["id"])
        return nsh.text(item["title"])

    def App():
        items = nsh.signal([a, b])
        return nsh.view(
            nsh.each(items, render),
            nsh.button("swap", on_press=lambda: items.set([b, a])),
        )

    with open(App) as app:
        app.press("swap")
        assert app.texts()[:2] == ["b", "a"]
    assert renders == [1, 2]


def test_exceptions_are_logged_and_the_app_survives(caplog):
    def render(n):
        if n == 3:
            raise ValueError("render failed")
        return nsh.text(f"row {n}")

    def key(n):
        if n == 4:
            raise KeyError("key failed")
        return n

    def App():
        items = nsh.signal([1, 2])
        broken = nsh.signal(False)

        def read():
            if broken():
                raise RuntimeError("items failed")
            return items()

        return nsh.view(
            nsh.each(read, render, key=key),
            nsh.button("add 3", on_press=lambda: items.update(lambda xs: [*xs, 3])),
            nsh.button("add 4", on_press=lambda: items.update(lambda xs: [*xs, 4])),
            nsh.button("break", on_press=broken.setter(True)),
            nsh.button("fix", on_press=broken.setter(False)),
            nsh.button("add 5", on_press=lambda: items.update(lambda xs: [*xs, 5])),
        )

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        app.press("add 3")  # render raises: the row shows nothing
        app.press("add 4")  # key raises: the row is made with a unique key
        app.wait_for("row 4")
        app.press("break")  # items raises: the rows stay
        assert app.shows("row 1") and app.shows("row 4")
        app.press("fix")
        app.press("add 5")
        app.wait_for("row 5")
        assert [t for t in app.texts() if t.startswith("row")] == [
            "row 1",
            "row 2",
            "row 4",
            "row 5",
        ]
    errors = [type(r.exc_info[1]) for r in caplog.records if r.exc_info]
    assert ValueError in errors and KeyError in errors and RuntimeError in errors


def test_unhashable_key_is_reported(caplog):
    with (
        caplog.at_level(logging.ERROR, logger="nsh"),
        open(
            lambda: nsh.view(nsh.each([1], lambda n: nsh.text(f"row {n}"), key=lambda n: [n]))
        ) as app,
    ):
        assert app.shows("row 1")
    assert "key must be hashable" in caplog.text


def test_todo_example():
    TodoApp = runpy.run_path(str(EXAMPLES / "todo.py"))["TodoApp"]
    with open(TodoApp) as app:
        assert app.shows("Buy milk")
        app.press("id:toggle-1")
        app.wait_for("✓ Buy milk")
        app.press("id:add")
        app.wait_for("Task 4")
        app.press("id:remove-2")
        assert not app.shows("Write docs")
        assert app.shows("2 of 3 left")
