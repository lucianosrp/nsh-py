"""The view and text primitives."""

import nsh
from nsh.testing import open


def test_view_props_and_children():
    tree = nsh.view(nsh.text("hi", class_="text-xl"), class_="p-4", test_id="root")
    assert tree.kind == "view"
    assert tree.props == {"class_": "p-4", "test_id": "root"}
    (child,) = tree.children
    assert child.kind == "text"
    assert child.props == {"content": "hi", "class_": "text-xl"}


def test_text_binding():
    count = nsh.signal(0)

    def App():
        return nsh.view(
            nsh.text(lambda: f"n={count()}"),
            nsh.text(count),  # a signal is a callable: bound too
            nsh.view("tap", on_press=lambda: count.update(lambda n: n + 1), test_id="tap"),
        )

    with open(App) as app:
        app.press("id:tap")
        app.wait_for("n=1")
        assert "1" in app.texts()
