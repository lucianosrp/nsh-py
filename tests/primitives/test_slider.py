"""The slider primitive: nsh-base's Slider."""

import nsh
from nsh.primitives.slider import (
    INDICATOR_CLASS,
    RANGE_CLASS,
    THUMB_CLASS,
    TRACK_CLASS,
)
from nsh.testing import open


def test_slider_props():
    volume = nsh.signal(40.0)
    s = nsh.slider(volume, min=0, max=100, step=5, class_="w-64", test_id="vol")
    assert s.kind == "slider"
    assert s.props["value"] is volume
    assert s.props["on_change"] == volume.set
    assert s.props["min"] == 0
    assert s.props["max"] == 100
    assert s.props["step"] == 5
    assert s.props["track_class"] == TRACK_CLASS
    assert s.props["indicator_class"] == INDICATOR_CLASS
    assert s.props["range_class"] == RANGE_CLASS
    assert s.props["thumb_class"] == THUMB_CLASS
    assert s.props["class_"] == "w-64"
    assert s.props["test_id"] == "vol"
    assert s.children == []


def test_label_is_a_child():
    s = nsh.slider(50, label=lambda: "Halfway", test_id="mid")
    (label,) = s.children
    assert label.kind == "text"
    assert label.props["content"]() == "Halfway"


def test_signal_on_change_runs_after_set():
    seen = []
    volume = nsh.signal(10.0)
    s = nsh.slider(volume, on_change=seen.append)
    s.props["on_change"](25.0)
    assert volume() == 25.0
    assert seen == [25.0]


def test_bound_value_and_label_update():
    def App():
        volume = nsh.signal(40.0)
        return nsh.view(
            nsh.slider(
                volume,
                min=0,
                max=100,
                step=5,
                label=lambda: f"Volume {volume():.0f}",
                accessibility_label="Volume",
                test_id="vol",
            ),
            nsh.button("+5", on_press=volume.updater(lambda n: n + 5)),
            nsh.button("mute", on_press=volume.setter(0.0)),
        )

    with open(App) as app:
        assert app.shows("Volume 40")
        app.wait_for("id:vol")
        app.press("+5")
        app.wait_for("Volume 45")
        app.press("mute")
        app.wait_for("Volume 0")


def test_a_number_keeps_its_own_value():
    with open(
        lambda: nsh.view(
            nsh.slider(30, label="Level", test_id="level"),
            nsh.text("ready"),
        )
    ) as app:
        assert app.shows("Level")
        assert app.shows("ready")
        app.wait_for("id:level")


def test_value_that_raises_is_logged(caplog):
    def broken():
        raise ValueError("no volume")

    with open(lambda: nsh.view(nsh.slider(broken), nsh.text("still here"))) as app:
        assert app.shows("still here")
    assert "no volume" in caplog.text
