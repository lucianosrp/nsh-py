"""The scroll primitive."""

import nsh
from nsh.primitives.scroll import KIND
from nsh.testing import open


def test_scroll_props():
    el = nsh.scroll(nsh.text("a"), class_="flex-1", test_id="list")
    assert el.kind == KIND
    assert el.props == {"class_": "flex-1", "test_id": "list"}
    (child,) = el.children
    assert child.props["content"] == "a"


def test_scroll_horizontal_prop():
    el = nsh.scroll(horizontal=True, test_id="row")
    assert el.kind == KIND
    assert el.props == {"horizontal": True, "test_id": "row"}
    assert nsh.scroll().props == {}


def test_long_list_renders_in_a_small_viewport():
    def App():
        return nsh.view(
            nsh.scroll(
                *[nsh.text(f"Row {i}") for i in range(200)],
                class_="flex-1",
                test_id="list",
            ),
            class_="flex-1",
        )

    with open(App, size=(200, 240)) as app:
        assert app.shows("Row 0")
        assert app.shows("Row 199")
        app.scroll("id:list", 1000)
        assert app.shows("Row 199")


def test_pressing_a_far_row():
    def App():
        picked = nsh.signal("")
        return nsh.view(
            nsh.text(lambda: picked() or "none"),
            nsh.scroll(
                *[
                    nsh.button(
                        f"Row {i}",
                        on_press=lambda i=i: picked.set(f"picked {i}"),
                        test_id=f"row-{i}",
                    )
                    for i in range(200)
                ],
                class_="flex-1",
            ),
            class_="flex-1",
        )

    with open(App, size=(200, 240)) as app:
        app.press("id:row-199")
        app.wait_for("picked 199")


def test_horizontal_scroll_moves():
    def App():
        return nsh.view(
            nsh.scroll(
                *[nsh.text(f"Col {i}", class_="w-24 shrink-0") for i in range(40)],
                horizontal=True,
                class_="flex-row flex-1",
                test_id="row",
            ),
            class_="flex-1",
        )

    with open(App, size=(200, 80)) as app:
        assert app.shows("Col 0")
        assert app.shows("Col 39")
        app.scroll("id:row", 400)
