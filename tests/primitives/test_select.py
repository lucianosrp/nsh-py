"""The select primitive: a dropdown backed by nsh-base's Select."""

import logging

import pytest

import nsh
from nsh.testing import open


def test_select_updates_the_signal_and_follows_signal_writes():
    seen = []

    def App():
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.select(
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
        app.press("id:size")
        app.wait_for("role:option[Large]")
        app.press("role:option[Large]")
        app.wait_for("Size: Large")
        assert app.shows("Large")
        assert not app.shows("Medium")  # the menu closed
        app.press("Reset")
        app.wait_for("Size: Small")
        assert app.shows("Small")
    assert seen == [("Large", "Large")]


@pytest.mark.parametrize("initial", [None, "Medium"])
def test_static_value_keeps_its_own_selection(initial):
    seen = []
    with open(
        lambda: nsh.select(
            initial,
            options=("Small", "Medium", "Large"),
            on_change=seen.append,
            test_id="size",
        )
    ) as app:
        assert app.shows("Select…" if initial is None else initial)
        app.press("id:size")
        app.press("role:option[Large]")
        assert app.shows("Large")
        app.press("id:size")
        app.press("role:option[Large]")  # choosing the same value only closes
        assert not app.shows("Medium")
        app.press("id:size")
        app.press("role:option[Small]")
        assert app.shows("Small")
    assert seen == ["Large", "Small"]


def test_static_value_without_a_callback_still_updates():
    with open(lambda: nsh.select(options=["Small", "Large"], test_id="size")) as app:
        app.press("id:size")
        app.press("role:option[Large]")
        assert app.shows("Large")
        assert not app.shows("Select…")


@pytest.mark.parametrize("binding", ["signal", "lambda", "computed"])
def test_options_can_change_while_the_menu_is_open(binding):
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
            nsh.select(size, options=bound, on_change=seen.append, test_id="size"),
            nsh.text(lambda: f"Size: {size()}"),
            nsh.button("Replace", on_press=options.setter(["Red", "Blue"])),
            nsh.button("Empty", on_press=options.setter([])),
            nsh.button("Restore", on_press=options.setter(["Medium", "Blue"])),
        )

    with open(App) as app:
        app.press("id:size")
        app.press("Replace")
        app.wait_for("role:option[Blue]")
        assert not app.shows("Large")
        assert app.shows("Select…")
        assert app.shows("Size: Medium")  # removal doesn't rewrite the signal
        app.press("role:option[Blue]")
        app.wait_for("Size: Blue")
        app.press("Empty")
        app.wait_for("Select…")
        assert app.shows("Size: Blue")
        app.press("id:size")  # an empty menu can still be opened and closed
        app.press("id:size")
        app.press("Restore")
        app.wait_for("text:Blue")
        assert not app.shows("Select…")
    assert seen == ["Blue"]


def test_callable_value_leaves_updates_to_the_app():
    seen = []

    def App():
        size = nsh.signal("Medium")
        return nsh.view(
            nsh.select(
                lambda: size(),
                options=["Small", "Medium", "Large"],
                on_change=seen.append,
                test_id="size",
            ),
            nsh.button("Reset", on_press=size.setter("Small")),
        )

    with open(App) as app:
        app.press("id:size")
        app.press("role:option[Large]")
        assert app.shows("Medium")
        assert not app.shows("Large")
        app.press("Reset")
        app.wait_for("Small")
    assert seen == ["Large"]


def test_callback_can_transform_the_selection():
    def App():
        size = nsh.signal("Medium")
        return nsh.select(
            size,
            options=["Small", "Medium", "Large"],
            on_change=lambda _: size.set("Small"),
            test_id="size",
        )

    with open(App) as app:
        app.press("id:size")
        app.press("role:option[Large]")
        app.wait_for("Small")
        assert not app.shows("Large")


def test_nullable_signal_and_reactive_placeholder():
    def App():
        size = nsh.signal(None)
        placeholder = nsh.signal("Pick a size")

        def clear():
            size.set(None)
            placeholder.set("Choose again")

        return nsh.view(
            nsh.select(size, options=["Small", "Large"], placeholder=placeholder, test_id="size"),
            nsh.button("Clear", on_press=clear),
        )

    with open(App) as app:
        assert app.shows("Pick a size")
        app.press("id:size")
        app.press("role:option[Large]")
        assert app.shows("Large")
        app.press("Clear")
        app.wait_for("Choose again")
        assert not app.shows("Large")


def test_disabled_select_blocks_interaction_until_enabled():
    seen = []

    def App():
        disabled = nsh.signal(True)
        return nsh.view(
            nsh.select(
                "Small",
                options=["Small", "Large"],
                on_change=seen.append,
                disabled=disabled,
                accessibility_label="Size",
                class_=lambda: "w-64",
                test_id="size",
            ),
            nsh.button("Enable", on_press=disabled.setter(False)),
        )

    with open(App) as app:
        with pytest.raises(RuntimeError, match="disabled"):
            app.press("id:size")
        assert not app.shows("Large")
        app.press("Enable")
        app.press("role:combobox[Size]")
        app.press("role:option[Large]")
        assert app.shows("Large")
    assert seen == ["Large"]


def test_handler_exception_is_logged_after_the_signal_updates(caplog):
    def boom(value):
        raise ValueError("select callback failed")

    def App():
        size = nsh.signal("Small")
        return nsh.view(
            nsh.select(size, options=["Small", "Large"], on_change=boom, test_id="size"),
            nsh.text(lambda: f"Size: {size()}"),
        )

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        app.press("id:size")
        app.press("role:option[Large]")
        app.wait_for("Size: Large")
        app.press("id:size")
        app.press("role:option[Small]")
        app.wait_for("Size: Small")
    assert "select callback failed" in caplog.text
