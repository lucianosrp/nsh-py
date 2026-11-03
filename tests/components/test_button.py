"""The button component."""

import nsh
from nsh.components.button import CLASS
from nsh.testing import open


def test_button_props():
    b = nsh.button("Go", on_press=lambda: None, class_="w-full", test_id="go")
    assert b.kind == "view"
    assert b.props["role"] == "button"
    assert b.props["class_"] == f"{CLASS} w-full"
    assert b.props["test_id"] == "go"
    assert b.children[0].props["content"] == "Go"


def test_button_with_bound_class():
    b = nsh.button("Go", class_=lambda: "bg-destructive")
    assert callable(b.props["class_"])
    assert b.props["class_"]().endswith(" bg-destructive")


def test_button_press():
    presses = []
    with open(lambda: nsh.button("Go", on_press=lambda: presses.append(1))) as app:
        app.press("Go")
        app.press("role:button[Go]")
    assert presses == [1, 1]
