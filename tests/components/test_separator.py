"""The separator component."""

import nsh
from nsh.components.separator import HORIZONTAL_CLASS, VERTICAL_CLASS
from nsh.testing import open


def test_horizontal_separator_props():
    separator = nsh.separator(test_id="rule")
    assert separator.kind == "view"
    assert separator.props == {"class_": HORIZONTAL_CLASS, "test_id": "rule"}
    assert separator.children == []


def test_vertical_separator_props():
    separator = nsh.separator(vertical=True)
    assert separator.kind == "view"
    assert separator.props == {"class_": VERTICAL_CLASS}
    assert separator.children == []


def test_separator_class_options():
    separator = nsh.separator(class_="my-4")
    assert separator.props["class_"] == f"{HORIZONTAL_CLASS} my-4"

    separator = nsh.separator(vertical=True, class_=lambda: "bg-muted")
    assert callable(separator.props["class_"])
    assert separator.props["class_"]() == f"{VERTICAL_CLASS} bg-muted"


def test_separator_between_texts():
    def App():
        return nsh.view(
            nsh.text("Above"),
            nsh.separator(test_id="rule"),
            nsh.text("Below"),
        )

    with open(App) as app:
        assert app.texts() == ["Above", "Below"]
        app.wait_for("id:rule")
