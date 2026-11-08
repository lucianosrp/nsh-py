"""The progress primitive: nsh-base's Progress."""

import pytest

import nsh
from nsh.primitives.progress import INDETERMINATE_CLASS, INDICATOR_CLASS, TRACK_CLASS
from nsh.testing import open


def test_progress_props():
    p = nsh.progress(40, "40%", class_="w-64", test_id="upload")
    assert p.kind == "progress"
    assert p.props == {
        "value": 40,
        "max": 100,
        "track_class": TRACK_CLASS,
        "indicator_class": INDICATOR_CLASS,
        "class_": "w-64",
        "test_id": "upload",
    }
    (label,) = p.children
    assert label.props["content"] == "40%"
    assert nsh.progress(0.5, max=1.0).props["max"] == 1.0
    assert (
        nsh.progress(indeterminate=True).props["indicator_class"]
        == f"{INDICATOR_CLASS} {INDETERMINATE_CLASS}"
    )
    busy = nsh.signal(False)
    bound = nsh.progress(indeterminate=busy).props["indicator_class"]
    assert bound() == INDICATOR_CLASS
    busy.set(True)
    assert bound() == f"{INDICATOR_CLASS} {INDETERMINATE_CLASS}"


@pytest.mark.parametrize("bad", [0, -1, float("nan")])
def test_max_must_be_positive(bad):
    with pytest.raises(ValueError, match="positive"):
        nsh.progress(1, max=bad)


def test_bound_value_and_label_update():
    def App():
        done = nsh.signal(0.25)
        return nsh.view(
            nsh.progress(done, lambda: f"{done():.0%}", max=1.0, test_id="bar"),
            nsh.button("more", on_press=done.updater(lambda d: d + 0.5)),
            nsh.button("way more", on_press=done.setter(7.0)),  # held to max
        )

    with open(App) as app:
        assert app.shows("25%")
        app.wait_for("id:bar")
        app.press("more")
        app.wait_for("75%")
        app.press("way more")
        app.wait_for("700%")  # the label is yours; nsh-base holds the bar to full


def test_value_that_raises_is_logged(caplog):
    def broken():
        raise ValueError("no progress")

    with open(lambda: nsh.view(nsh.progress(broken), nsh.text("still here"))) as app:
        assert app.shows("still here")
    assert "no progress" in caplog.text
