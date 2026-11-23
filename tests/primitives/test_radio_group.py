"""The radio_group primitive: nsh-base's RadioGroup of Radios."""

import logging

import pytest

import nsh
from nsh.primitives.radio_group import GROUP_CLASS, RADIO_CLASS
from nsh.testing import open


def test_radio_group_props():
    size = nsh.signal("Medium")
    g = nsh.radio_group(
        size,
        options=["Small", "Medium", "Large"],
        class_="flex-row",
        test_id="size",
    )
    assert g.kind == "radio_group"
    assert g.props["value"] is size
    assert g.props["on_change"] == size.set
    assert g.props["options"] == ["Small", "Medium", "Large"]
    assert g.props["radio_class"] == RADIO_CLASS
    assert g.props["class_"] == f"{GROUP_CLASS} flex-row"
    assert g.props["test_id"] == "size"
    assert g.children == []


def test_radio_group_updates_the_signal_and_follows_signal_writes():
    seen = []

    def App():
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.radio_group(
                size,
                options=["Small", "Medium", "Large"],
                on_change=lambda value: seen.append((value, size())),
                test_id="size",
            ),
            nsh.text(lambda: f"Size: {size()}"),
            nsh.button("Reset", on_press=size.setter("Small")),
        )

    with open(App) as app:
        assert app.shows("Medium")
        app.wait_for("id:size")
        app.press("role:radio[Large]")
        app.wait_for("Size: Large")
        app.press("Reset")
        app.wait_for("Size: Small")
    assert seen == [("Large", "Large")]


@pytest.mark.parametrize("initial", [None, "Medium"])
def test_static_value_keeps_its_own_selection(initial):
    seen = []
    with open(
        lambda: nsh.radio_group(
            initial,
            options=("Small", "Medium", "Large"),
            on_change=seen.append,
            test_id="size",
        )
    ) as app:
        app.wait_for("id:size")
        app.press("role:radio[Large]")
        app.wait_for("role:radio[Large]")
        app.press("role:radio[Large]")  # already checked: reports nothing
        app.press("role:radio[Small]")
    assert seen == ["Large", "Small"]


def test_static_value_without_a_callback_still_updates():
    with open(
        lambda: nsh.view(
            nsh.radio_group(options=["Small", "Large"], test_id="size"),
            nsh.text("ready"),
        )
    ) as app:
        app.wait_for("ready")
        app.press("role:radio[Large]")
        # The group keeps its own value; pressing another option still works.
        app.press("role:radio[Small]")


@pytest.mark.parametrize("binding", ["signal", "lambda", "computed"])
def test_options_can_change(binding):
    seen = []

    def App():
        options = nsh.signal(["Small", "Medium", "Large"])
        bound = options
        if binding == "lambda":

            def bound():
                return options()

        elif binding == "computed":
            bound = nsh.computed(lambda: options())
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.radio_group(size, options=bound, on_change=seen.append, test_id="size"),
            nsh.text(lambda: f"Size: {size()}"),
            nsh.button("Replace", on_press=options.setter(["Red", "Blue"])),
            nsh.button("Empty", on_press=options.setter([])),
            nsh.button("Restore", on_press=options.setter(["Medium", "Blue"])),
        )

    with open(App) as app:
        app.press("Replace")
        app.wait_for("role:radio[Blue]")
        assert not app.shows("Large")
        assert app.shows("Size: Medium")  # removal doesn't rewrite the signal
        app.press("role:radio[Blue]")
        app.wait_for("Size: Blue")
        app.press("Empty")
        assert app.shows("Size: Blue")  # value stays; empty group has no radios
        assert not app.shows("Blue")
        app.press("Restore")
        app.wait_for("text:Blue")
        assert app.shows("Medium")
    assert seen == ["Blue"]


def test_callable_value_leaves_updates_to_the_app():
    seen = []

    def App():
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.radio_group(
                lambda: size(),
                options=["Small", "Medium", "Large"],
                on_change=seen.append,
                test_id="size",
            ),
            nsh.text(lambda: f"Size: {size()}"),
            nsh.button("Reset", on_press=size.setter("Small")),
        )

    with open(App) as app:
        app.press("role:radio[Large]")
        assert app.shows("Size: Medium")  # the app did not follow
        app.press("Reset")
        app.wait_for("Size: Small")
    assert seen == ["Large"]


def test_callback_can_transform_the_selection():
    def App():
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.radio_group(
                size,
                options=["Small", "Medium", "Large"],
                on_change=lambda _: size.set("Small"),
                test_id="size",
            ),
            nsh.text(lambda: f"Size: {size()}"),
        )

    with open(App) as app:
        app.press("role:radio[Large]")
        app.wait_for("Size: Small")


def test_nullable_signal_clears_the_selection():
    def App():
        size = nsh.signal(None)
        return nsh.view(
            nsh.radio_group(size, options=["Small", "Large"], test_id="size"),
            nsh.text(lambda: f"Size: {size() or 'None'}"),
            nsh.button("Clear", on_press=size.setter(None)),
        )

    with open(App) as app:
        assert app.shows("Size: None")
        app.press("role:radio[Large]")
        app.wait_for("Size: Large")
        app.press("Clear")
        app.wait_for("Size: None")


def test_disabled_radio_group_blocks_interaction_until_enabled():
    seen = []

    def App():
        disabled = nsh.signal(True)
        return nsh.view(
            nsh.radio_group(
                "Small",
                options=["Small", "Large"],
                on_change=seen.append,
                disabled=disabled,
                test_id="size",
            ),
            nsh.button("Enable", on_press=disabled.setter(False)),
        )

    with open(App) as app:
        with pytest.raises(RuntimeError, match="disabled"):
            app.press("role:radio[Large]")
        app.press("Enable")
        app.press("role:radio[Large]")
    assert seen == ["Large"]


def test_handler_exception_is_logged_after_the_signal_updates(caplog):
    def boom(value):
        raise ValueError("radio_group callback failed")

    def App():
        size = nsh.signal("Small")
        return nsh.view(
            nsh.radio_group(size, options=["Small", "Large"], on_change=boom, test_id="size"),
            nsh.text(lambda: f"Size: {size()}"),
        )

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        app.press("role:radio[Large]")
        app.wait_for("Size: Large")
        app.press("role:radio[Small]")
        app.wait_for("Size: Small")
    assert "radio_group callback failed" in caplog.text
