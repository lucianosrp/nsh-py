"""The input primitive: a text field."""

import logging

import pytest

import nsh
from nsh.testing import open


def test_input_props():
    name = nsh.signal("")
    two_way = nsh.input(name, placeholder="Your name", class_="w-64", test_id="name")
    assert two_way.kind == "input"
    assert two_way.children == []
    assert two_way.props["value"] is name
    assert two_way.props["on_change"] == name.set  # typing sets the signal
    assert two_way.props["placeholder"] == "Your name"
    assert two_way.props["class_"] == "w-64"
    assert two_way.props["test_id"] == "name"
    # Props left at None are dropped.
    assert set(nsh.input().props) == set()
    extra = nsh.input("x", readonly=True, masked=True, max_length=8, multiline=True)
    assert extra.props["readonly"] is True
    assert extra.props["masked"] is True
    assert extra.props["max_length"] == 8
    assert extra.props["multiline"] is True

    def log(text):
        pass

    # With a signal, on_change runs after the set; a lambda or a string stays one-way.
    assert nsh.input(name, on_change=log).props["on_change"] is not log
    assert "on_change" not in nsh.input(lambda: name()).props
    assert "on_change" not in nsh.input("first").props


def test_typing_sets_the_signal_and_bound_text_follows():
    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(name, placeholder="Your name", test_id="name"),
            nsh.text(lambda: f"Hello, {name()}"),
        )

    with open(App) as app:
        assert app.value("id:name") == ""
        app.type_text("id:name", "Ada")
        app.wait_for("Hello, Ada")
        app.type_text("id:name", " L")
        app.wait_for("Hello, Ada L")
        assert app.value("id:name") == "Ada L"
        # By placeholder, while empty, as nsh-testing's selectors allow.
    with open(App) as app:
        app.type_text("text:Your name", "Bo")
        app.wait_for("Hello, Bo")


def test_signal_writes_show_in_the_field():
    def App():
        name = nsh.signal("Ada")
        return nsh.view(
            nsh.input(name, test_id="name"),
            nsh.button("clear", on_press=name.setter("")),
            nsh.button("grace", on_press=name.setter("Grace")),
        )

    with open(App) as app:
        assert app.value("id:name") == "Ada"
        app.press("grace")
        app.wait_for("text:Grace")
        assert app.value("id:name") == "Grace"
        app.press("clear")
        app.type_text("id:name", "x")
        assert app.value("id:name") == "x"


def test_callable_value_is_one_way():
    def App():
        name = nsh.signal("Ada")
        return nsh.view(
            nsh.input(lambda: name().upper(), test_id="shout"),
            nsh.button("rename", on_press=name.setter("grace")),
        )

    with open(App) as app:
        assert app.value("id:shout") == "ADA"
        app.press("rename")
        app.wait_for("text:GRACE")
        assert app.value("id:shout") == "GRACE"


def test_none_value_is_empty():
    with open(lambda: nsh.input(lambda: None, test_id="n")) as app:
        assert app.value("id:n") == ""


def test_string_value_is_the_first_text():
    seen = []

    def App():
        return nsh.input("Ada", on_change=seen.append, test_id="name")

    with open(App) as app:
        assert app.value("id:name") == "Ada"
        app.type_text("id:name", "!")
        assert app.value("id:name") == "Ada!"
    assert seen == ["Ada!"]


def test_a_signal_is_set_before_on_change_runs():
    seen = []

    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(name, on_change=lambda t: seen.append((t, name())), test_id="name"),
            nsh.text(lambda: f"signal={name()!r}"),
        )

    with open(App) as app:
        app.type_text("id:name", "Hi")
        app.wait_for("signal='Hi'")
    assert seen == [("H", "H"), ("Hi", "Hi")]  # on_change sees the new value


def test_on_change_can_transform_what_is_typed():
    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(name, on_change=lambda t: name.set(t.upper()), test_id="name"),
            nsh.text(lambda: f"name={name()}"),
        )

    with open(App) as app:
        app.type_text("id:name", "ab")
        app.wait_for("name=AB")
        assert app.value("id:name") == "AB"


def test_on_submit_gets_the_text_on_enter():
    submitted = []

    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(name, on_submit=submitted.append, test_id="name"),
            nsh.text(lambda: f"name={name()}"),
        )

    with open(App) as app:
        app.type_text("id:name", "Ada")
        assert submitted == []
        app.type_text("id:name", "\n")
        assert submitted == ["Ada"]
        app.wait_for("name=Ada")


def test_submit_can_clear_the_field():
    def App():
        name = nsh.signal("")
        sent = nsh.signal("")

        def submit(text):
            sent.set(text)
            name.set("")

        return nsh.view(
            nsh.input(name, on_submit=submit, test_id="name"),
            nsh.text(lambda: f"sent={sent()}"),
        )

    with open(App) as app:
        app.type_text("id:name", "Ada\n")
        app.wait_for("sent=Ada")
        assert app.value("id:name") == ""


def test_disabled_input_is_not_editable():
    def App():
        locked = nsh.signal(True)
        return nsh.view(
            nsh.input("x", disabled=locked, test_id="name"),
            nsh.button("unlock", on_press=locked.setter(False)),
        )

    with open(App) as app:
        with pytest.raises(RuntimeError, match="not editable"):
            app.type_text("id:name", "y")
        assert app.value("id:name") == "x"
        app.press("unlock")
        app.type_text("id:name", "y")
        assert app.value("id:name") == "xy"


def test_type_text_into_no_input_raises():
    with open(lambda: nsh.text("no input here")) as app:
        with pytest.raises(RuntimeError, match="no input matches"):
            app.type_text("id:nope", "x")
        assert app.value("id:nope") is None


@pytest.mark.parametrize("handler", ["on_change", "on_submit"])
def test_handler_exceptions_are_logged_and_the_app_survives(handler, caplog):
    def boom(text):
        raise ValueError(f"{handler} failed")

    def App():
        count = nsh.signal(0)
        return nsh.view(
            nsh.input(test_id="f", **{handler: boom}),
            nsh.text(lambda: f"n={count()}"),
            nsh.button("inc", on_press=count.updater(lambda n: n + 1)),
        )

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        app.type_text("id:f", "a\n")
        app.press("inc")
        app.wait_for("n=1")
        app.type_text("id:f", "b")
        assert app.value("id:f") == "ab"
    errors = [r for r in caplog.records if r.exc_info]
    assert errors
    assert all(isinstance(r.exc_info[1], ValueError) for r in errors)
    assert f"{handler} failed" in caplog.text


def test_readonly_input_is_not_editable():
    def App():
        locked = nsh.signal(True)
        return nsh.view(
            nsh.input("Ada", readonly=locked, test_id="name"),
            nsh.button("unlock", on_press=locked.setter(False)),
        )

    with open(App) as app:
        assert app.value("id:name") == "Ada"
        with pytest.raises(RuntimeError, match="not editable"):
            app.type_text("id:name", "y")
        assert app.value("id:name") == "Ada"
        app.press("unlock")
        app.type_text("id:name", "!")
        assert app.value("id:name") == "Ada!"


def test_masked_input_holds_the_real_text():
    def App():
        secret = nsh.signal("")
        return nsh.view(
            nsh.input(secret, masked=True, test_id="pw"),
            nsh.text(lambda: f"len={len(secret())}"),
        )

    with open(App) as app:
        app.type_text("id:pw", "s3cret")
        app.wait_for("len=6")
        assert app.value("id:pw") == "s3cret"


def test_max_length_clips_what_is_typed():
    def App():
        name = nsh.signal("")
        return nsh.view(
            nsh.input(name, max_length=5, test_id="name"),
            nsh.text(lambda: f"name={name()}"),
        )

    with open(App) as app:
        app.type_text("id:name", "Ada Lovelace")
        app.wait_for("name=Ada L")
        assert app.value("id:name") == "Ada L"


def test_multiline_return_inserts_a_line():
    submitted = []

    def App():
        note = nsh.signal("")
        return nsh.view(
            nsh.input(note, multiline=True, on_submit=submitted.append, test_id="note"),
            nsh.text(lambda: note().replace("\n", "/")),
        )

    with open(App) as app:
        app.type_text("id:note", "a\nb")
        app.wait_for("a/b")
        assert app.value("id:note") == "a\nb"
        assert submitted == []


def test_input_can_be_styled_with_a_bound_class():
    def App():
        invalid = nsh.signal(True)
        return nsh.input(
            test_id="f",
            class_=lambda: "border-destructive" if invalid() else "border-input",
        )

    with open(App) as app:
        app.type_text("id:f", "ok")
        assert app.value("id:f") == "ok"
