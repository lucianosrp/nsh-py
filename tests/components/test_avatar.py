"""The avatar component."""

import pytest

import nsh
from nsh.components.avatar import CLASS, INITIALS_CLASS, SIZES, initials
from nsh.testing import open


def test_initials():
    assert initials("Ada Lovelace") == "AL"
    assert initials("ada lovelace") == "AL"
    assert initials("Ada") == "A"
    assert initials("") == "?"
    assert initials("   ") == "?"
    assert initials("Ada  Lovelace") == "AL"


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_avatar_size_classes(size):
    el = nsh.avatar("Ada Lovelace", size=size)
    assert el.kind == "view"
    assert el.props["class_"].startswith(f"{CLASS} {SIZES[size]}")


def test_avatar_initials_props():
    el = nsh.avatar("Ada Lovelace", class_="w-80", test_id="avatar")
    assert el.kind == "view"
    assert el.props == {
        "class_": f"{CLASS} {SIZES['md']} w-80",
        "test_id": "avatar",
    }
    (child,) = el.children
    assert child.kind == "text"
    assert child.props["content"] == "AL"
    assert child.props["class_"] == INITIALS_CLASS


def test_avatar_image_props():
    el = nsh.avatar(
        "Ada Lovelace",
        src="examples/assets/dot.png",
        class_="w-16 h-16",
        test_id="avatar",
    )
    assert el.kind == "image"
    assert el.props == {
        "src": "examples/assets/dot.png",
        "alt": "Ada Lovelace",
        "class_": f"{CLASS} {SIZES['md']} w-16 h-16",
        "test_id": "avatar",
    }


def test_avatar_image_with_alt():
    el = nsh.avatar("Ada Lovelace", src="examples/assets/dot.png", alt="Ada")
    assert el.props["alt"] == "Ada"


def test_avatar_unknown_size():
    with pytest.raises(ValueError):
        nsh.avatar("Ada", size="xl")


def test_avatar_shows_initials():
    with open(lambda: nsh.avatar("Ada Lovelace")) as app:
        assert app.shows("AL")


def test_avatar_empty_shows_question_mark():
    with open(lambda: nsh.avatar("")) as app:
        assert app.shows("?")
