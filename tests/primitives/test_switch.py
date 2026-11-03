"""The switch primitive: nsh-base's Switch."""

import pytest

import nsh
from nsh.primitives.switch import THUMB_CLASS, TRACK_CLASS
from nsh.testing import open


def test_switch_props():
    dark = nsh.signal(False)
    s = nsh.switch(dark, "Dark mode", class_=lambda: "p-2", test_id="dark")
    assert s.kind == "switch"
    assert s.props["checked"] is dark
    assert s.props["on_change"] == dark.set
    assert s.props["track_class"] == TRACK_CLASS
    assert s.props["thumb_class"] == THUMB_CLASS
    assert s.props["class_"]() == "p-2"  # a bound class_ stays bound
    (label,) = s.children
    assert label.props["content"] == "Dark mode"


def test_pressing_toggles_the_signal():
    def App():
        dark = nsh.signal(False)
        return nsh.view(
            nsh.switch(dark, "Dark mode", test_id="dark"),
            nsh.text(lambda: "on" if dark() else "off"),
            nsh.button("reset", on_press=dark.setter(False)),
        )

    with open(App) as app:
        assert app.shows("off")
        app.press("id:dark")
        app.wait_for("on")
        app.press("role:switch[Dark mode]")
        app.wait_for("off")
        app.press("text:Dark mode")
        app.wait_for("on")
        app.press("reset")  # a write shows, and the next press turns it on again
        app.wait_for("off")
        app.press("id:dark")
        app.wait_for("on")


def test_a_bool_toggles_by_itself():
    seen = []
    with open(lambda: nsh.switch(True, on_change=seen.append, test_id="wifi")) as app:
        app.press("id:wifi")
        app.press("id:wifi")
        app.press("id:wifi")
    assert seen == [False, True, False]


def test_disabled_ignores_presses():
    seen = []
    with open(lambda: nsh.switch(False, "Wi-Fi", on_change=seen.append, disabled=True, test_id="wifi")) as app:
        with pytest.raises(RuntimeError, match="disabled"):
            app.press("id:wifi")
        with pytest.raises(RuntimeError, match="disabled"):
            app.press("text:Wi-Fi")
    assert seen == []
