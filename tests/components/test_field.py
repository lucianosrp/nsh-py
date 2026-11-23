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
            nsh.input(email, test_id="email"),
            help="We never share it.",
            error=error,
        )

    with open(App) as app:
        assert app.shows("Email")
        assert app.shows("We never share it.")
        assert not app.shows(message)

        app.type_text("id:email", "ada")
        app.wait_for(message)

        app.type_text("id:email", "@example.org")
        assert app.value("id:email") == "ada@example.org"
        assert not app.shows(message)
