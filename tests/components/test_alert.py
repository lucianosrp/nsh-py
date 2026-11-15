"""The alert component."""

import pytest

import nsh
from nsh.components.alert import (
    DEFAULT_CLASS,
    DESCRIPTION_CLASS,
    DESTRUCTIVE_CLASS,
    TITLE_CLASS,
)
from nsh.testing import open


def test_default_alert_props():
    alert = nsh.alert(
        "Saved",
        description="Your changes are live.",
        class_="w-80",
        test_id="saved",
    )
    assert alert.kind == "view"
    assert alert.props == {"class_": f"{DEFAULT_CLASS} w-80", "test_id": "saved"}

    title, description = alert.children
    assert (title.props["content"], title.props["class_"]) == ("Saved", TITLE_CLASS)
    assert (description.props["content"], description.props["class_"]) == (
        "Your changes are live.",
        DESCRIPTION_CLASS,
    )


def test_alert_without_description_or_children():
    alert = nsh.alert("Saved")
    (title,) = alert.children
    assert title.props["content"] == "Saved"


def test_destructive_alert_uses_its_variant_class():
    alert = nsh.alert(
        "Delete project?",
        description="This action cannot be undone.",
        variant="destructive",
    )
    assert alert.props["class_"] == DESTRUCTIVE_CLASS
    assert {"border-destructive/40", "bg-destructive/10", "text-destructive"} <= set(
        DESTRUCTIVE_CLASS.split()
    )


def test_alert_children_come_after_the_description():
    alert = nsh.alert(
        "Saved",
        nsh.button("Undo", test_id="undo"),
        description="Your changes are live.",
    )
    title, description, action = alert.children
    assert title.props["content"] == "Saved"
    assert description.props["content"] == "Your changes are live."
    assert action.props["test_id"] == "undo"


def test_alert_class_can_be_bound():
    alert = nsh.alert("Saved", class_=lambda: "w-80")
    assert callable(alert.props["class_"])
    assert alert.props["class_"]() == f"{DEFAULT_CLASS} w-80"


def test_unknown_alert_variant():
    with pytest.raises(ValueError, match="default.*destructive"):
        nsh.alert("Saved", variant="warning")


def test_alert_text_can_be_bound():
    def App():
        title = nsh.signal("Saved")
        description = nsh.signal("Your changes are live.")
        return nsh.view(
            nsh.alert(
                title,
                description=description,
                test_id="alert",
            ),
            nsh.button(
                "Rename",
                on_press=lambda: (
                    title.set("Stored"),
                    description.set("Everything is up to date."),
                ),
                test_id="rename",
            ),
        )

    with open(App) as app:
        assert app.shows("Saved")
        assert app.shows("Your changes are live.")
        app.press("id:rename")
        app.wait_for("Stored")
        app.wait_for("Everything is up to date.")


def test_alert_shows_title_description_and_action():
    presses = []

    def App():
        return nsh.alert(
            "Saved",
            nsh.button("Undo", on_press=lambda: presses.append(1), test_id="undo"),
            description="Your changes are live.",
        )

    with open(App) as app:
        assert app.texts() == ["Saved", "Your changes are live.", "Undo"]
        app.press("id:undo")
    assert presses == [1]
