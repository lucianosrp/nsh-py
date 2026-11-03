"""The image primitive."""

from pathlib import Path

import pytest

import nsh
from nsh.primitives.image import FITS, KIND
from nsh.testing import open

DOT = Path(__file__).resolve().parents[2] / "examples" / "assets" / "dot.png"


def test_image_props():
    el = nsh.image(DOT, alt="A blue square", fit="contain", class_="w-32 h-32", test_id="dot")
    assert el.kind == KIND
    assert el.children == []
    assert el.props["src"] is DOT
    assert el.props["alt"] == "A blue square"
    assert el.props["fit"] == "contain"
    assert el.props["class_"] == "w-32 h-32"
    assert el.props["test_id"] == "dot"
    assert nsh.image("logo.png").props == {"src": "logo.png"}
    assert nsh.image("https://example.com/dot.png").props["src"] == "https://example.com/dot.png"
    assert FITS >= {"contain", "cover", "fill", "none", "scale-down"}


def test_unknown_fit_raises():
    with pytest.raises(ValueError, match="unknown fit 'stretchy'"):
        nsh.image(DOT, fit="stretchy")


def test_image_builds_from_path_and_bytes():
    png = DOT.read_bytes()

    def App():
        return nsh.view(
            nsh.image(DOT, alt="from path", class_="w-8 h-8", test_id="path"),
            nsh.image(png, alt="from bytes", fit="contain", class_="w-8 h-8", test_id="bytes"),
            nsh.text("shown"),
        )

    with open(App) as app:
        assert app.shows("shown")


def test_image_src_binding():
    png = DOT.read_bytes()

    def App():
        use_bytes = nsh.signal(False)
        return nsh.view(
            nsh.image(
                lambda: png if use_bytes() else DOT,
                fit="cover",
                class_="w-8 h-8",
                test_id="pic",
            ),
            nsh.button("swap", on_press=use_bytes.setter(True), test_id="swap"),
            nsh.text(lambda: "bytes" if use_bytes() else "path"),
        )

    with open(App) as app:
        assert app.shows("path")
        app.press("id:swap")
        app.wait_for("bytes")


def test_bound_fit():
    def App():
        mode = nsh.signal("contain")
        return nsh.view(
            nsh.image(DOT, fit=mode, class_="w-8 h-8", test_id="pic"),
            nsh.button("cover", on_press=mode.setter("cover"), test_id="cover"),
            nsh.text(mode),
        )

    with open(App) as app:
        assert app.shows("contain")
        app.press("id:cover")
        app.wait_for("cover")


def test_unknown_fit_on_the_element_is_reported(caplog):
    with open(lambda: nsh.Element("image", {"src": str(DOT), "fit": "nope"}, [])) as app:
        assert app.shows("The app's root raised an exception")
    assert "unknown fit" in caplog.text
