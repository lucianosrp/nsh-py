"""The card component."""

import nsh
from nsh.components.card import CLASS, DESCRIPTION_CLASS, TITLE_CLASS
from nsh.testing import open


def test_card_props():
    c = nsh.card(
        nsh.text("body"),
        title="Profile",
        description="Shown to others.",
        class_="w-80",
        test_id="profile",
    )
    assert c.kind == "view"
    assert c.props == {"class_": f"{CLASS} w-80", "test_id": "profile"}
    title, description, body = c.children
    assert (title.props["content"], title.props["class_"]) == ("Profile", TITLE_CLASS)
    assert (description.props["content"], description.props["class_"]) == (
        "Shown to others.",
        DESCRIPTION_CLASS,
    )
    assert body.props["content"] == "body"


def test_card_without_title_or_description():
    c = nsh.card(nsh.text("only a child"))
    assert c.props == {"class_": CLASS}
    assert [child.props["content"] for child in c.children] == ["only a child"]


def test_card_with_bound_class():
    c = nsh.card(class_=lambda: "bg-muted")
    assert callable(c.props["class_"])
    assert c.props["class_"]() == f"{CLASS} bg-muted"


def test_card_shows_title_and_children():
    with open(lambda: nsh.card(nsh.text("body"), title="Profile", description="Shown to others.")) as app:
        assert app.shows("Profile")
        assert app.shows("Shown to others.")
        assert app.shows("body")


def test_card_bound_title_updates():
    def App():
        name = nsh.signal("Ada")
        return nsh.card(
            nsh.button("Rename", on_press=lambda: name.set("Grace"), test_id="rename"),
            title=lambda: f"Hello, {name()}",
        )

    with open(App) as app:
        assert app.shows("Hello, Ada")
        app.press("id:rename")
        app.wait_for("Hello, Grace")
        assert not app.shows("Hello, Ada")
