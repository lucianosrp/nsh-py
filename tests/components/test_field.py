"""The field component."""

import nsh
from nsh.testing import open


def test_field_shows_and_clears_bound_error():
    message = "Enter a valid email address."

    def App():
        email = nsh.signal("")

        def error():
            value = email()
            return message if value and "@" not in value else None

        return nsh.field(
            "Email",
            nsh.input(email, placeholder="you@example.org"),
            help="We never share it.",
            error=error,
        )

    with open(App) as app:
        assert app.shows("Email")
        assert app.shows("We never share it.")
        assert not app.shows(message)

        app.type_text("label:Email", "ada")
        app.wait_for(message)

        app.type_text("label:Email", "@example.org")
        assert app.value("label:Email") == "ada@example.org"
        assert not app.shows(message)


def test_field_updates_the_input_name_when_its_label_changes():
    def App():
        label = nsh.signal("Name")
        return nsh.view(
            nsh.field(label, nsh.input()),
            nsh.button("Rename", on_press=lambda: label.set("Full name")),
        )

    with open(App) as app:
        app.type_text("label:Name", "Ada")
        app.press("Rename")
        assert app.value("label:Name") is None
        assert app.value("label:Full name") == "Ada"


def test_field_preserves_an_explicit_input_name():
    with open(lambda: nsh.field("Name", nsh.input(accessibility_label="Full name"))) as app:
        assert app.shows("Name")
        assert app.value("label:Name") is None
        assert app.value("label:Full name") == ""
