"""The checkbox primitive: nsh-base's Checkbox."""

import pytest

import nsh
from nsh.primitives.checkbox import CHECK, DASH, INDICATOR_CLASS, LABEL_CLASS
from nsh.testing import open


def test_checkbox_props():
    agree = nsh.signal(False)
    c = nsh.checkbox("I agree", checked=agree, class_="p-2", test_id="agree")
    assert c.kind == "checkbox"
    assert c.props["checked"] is agree
    assert c.props["on_change"] == agree.set  # a press sets the signal
    assert c.props["class_"] == "p-2"  # on a view around it (see props::with_class)
    assert c.props["indicator_class"] == INDICATOR_CLASS
    assert c.props["test_id"] == "agree"
    (label,) = c.children
    assert label.props["content"] == "I agree"
    assert nsh.checkbox().children == []
    # A disabled checkbox dims its label (fixed, or bound to `disabled`).
    assert nsh.checkbox(label="x", disabled=True).children[0].props["class_"].endswith("opacity-50")
    locked = nsh.signal(False)
    dimmed = nsh.checkbox(label="x", disabled=locked).children[0].props["class_"]
    assert "opacity-50" not in dimmed()
    locked.set(True)
    assert dimmed().endswith(f"{LABEL_CLASS} opacity-50")

    def log(value):
        pass

    # A callable is one-way and read-only.
    assert "on_change" not in nsh.checkbox(checked=lambda: agree()).props
    assert nsh.checkbox(checked=lambda: agree(), on_change=log).props["on_change"] is log
    # A bool is the first value of the checkbox's own signal.
    own = nsh.checkbox(checked=True).props
    assert isinstance(own["checked"], nsh.Signal) and own["checked"]() is True


def test_pressing_toggles_the_signal():
    def App():
        agree = nsh.signal(False)
        return nsh.view(
            nsh.checkbox("I agree", checked=agree, test_id="agree"),
            nsh.text(lambda: f"agree={agree()}"),
        )

    with open(App) as app:
        assert app.shows("agree=False") and not app.shows(CHECK)
        app.press("id:agree")
        app.wait_for("agree=True")
        assert app.shows(CHECK)  # the mark shows
        app.press("text:I agree")  # the label is part of the checkbox
        app.wait_for("agree=False")
        assert not app.shows(CHECK)
        app.press("role:checkbox[I agree]")
        app.wait_for("agree=True")


def test_signal_writes_show_in_the_box():
    def App():
        agree = nsh.signal(False)
        return nsh.view(
            nsh.checkbox("I agree", checked=agree),
            nsh.button("check", on_press=agree.setter(True)),
        )

    with open(App) as app:
        assert not app.shows(CHECK)
        app.press("check")
        app.wait_for(CHECK)


def test_a_bool_toggles_by_itself_and_reports():
    seen = []

    def App():
        return nsh.checkbox("Remember me", checked=True, on_change=seen.append, test_id="remember")

    with open(App) as app:
        assert app.shows(CHECK)
        app.press("id:remember")
        assert seen == [False]
        assert not app.shows(CHECK)
        app.press("id:remember")
        app.wait_for(CHECK)
        assert seen == [False, True]


def test_a_callable_is_one_way():
    asked = []

    def App():
        agree = nsh.signal(False)
        return nsh.view(
            nsh.checkbox("Shown", checked=lambda: agree(), on_change=asked.append, test_id="shown"),
            nsh.button("check", on_press=agree.setter(True)),
        )

    with open(App) as app:
        app.press("id:shown")
        assert asked == [True]
        assert not app.shows(CHECK)  # the value didn't change
        app.press("check")
        app.wait_for(CHECK)
        app.press("id:shown")
        assert asked == [True, False]
        assert app.shows(CHECK)


def test_indeterminate_shows_a_dash_and_asks_for_checked():
    def App():
        picked = nsh.signal(False)
        some = nsh.signal(True)

        return nsh.view(
            nsh.checkbox(
                "All",
                checked=picked,
                indeterminate=some,
                on_change=lambda _: some.set(False),
                test_id="all",
            ),
            nsh.text(lambda: f"all={picked()}"),
        )

    with open(App) as app:
        assert app.shows(DASH) and not app.shows(CHECK)
        app.press("id:all")
        app.wait_for("all=True")
        assert app.shows(CHECK) and not app.shows(DASH)


def test_disabled_ignores_presses():
    def App():
        agree = nsh.signal(False)
        locked = nsh.signal(True)
        return nsh.view(
            nsh.checkbox("I agree", checked=agree, disabled=locked, test_id="agree"),
            nsh.button("unlock", on_press=locked.setter(False)),
            nsh.text(lambda: f"agree={agree()}"),
        )

    with open(App) as app:
        with pytest.raises(RuntimeError, match="disabled"):
            app.press("id:agree")
        assert app.shows("agree=False")
        app.press("unlock")
        app.press("id:agree")
        app.wait_for("agree=True")


def test_failing_on_change_is_logged(caplog):
    def boom(value):
        raise ValueError("nope")

    with open(lambda: nsh.checkbox("x", on_change=boom, test_id="x")) as app:
        app.press("id:x")
        assert app.shows(CHECK)  # its own value was set before on_change ran
    assert "nope" in caplog.text


def test_class_and_test_id_work_together():
    # `class_` wraps the checkbox in a view; `test_id` still finds the
    # checkbox itself, and a bound class_ stays bound.
    def App():
        agree = nsh.signal(False)
        return nsh.view(
            nsh.checkbox(
                "I agree", checked=agree, class_=lambda: "pl-6" if agree() else "", test_id="agree"
            ),
            nsh.text(lambda: f"agree={agree()}"),
        )

    with open(App) as app:
        app.press("id:agree")
        app.wait_for("agree=True")
        app.press("id:agree")
        app.wait_for("agree=False")


def test_a_signal_is_set_before_on_change_runs():
    seen = []

    def App():
        agree = nsh.signal(False)
        return nsh.checkbox(
            "I agree", checked=agree, on_change=lambda v: seen.append((v, agree())), test_id="agree"
        )

    with open(App) as app:
        app.press("id:agree")
        app.wait_for(CHECK)
    assert seen == [(True, True)]  # on_change sees the new value


@pytest.mark.parametrize("value", [True, nsh.signal(False)])
def test_the_value_first_raises(value):
    with pytest.raises(TypeError, match="label first"):
        nsh.checkbox(value)
    with pytest.raises(TypeError, match="label first"):
        nsh.switch(value)
