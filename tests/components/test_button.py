"""The button component."""

import pytest

import nsh
from nsh.components.button import CLASS
from nsh.testing import open


def test_button_props():
    b = nsh.button("Go", on_press=lambda: None, class_="w-full", test_id="go")
    assert b.kind == "view"
    assert b.props["role"] == "button"
    assert b.props["class_"] == f"{CLASS} w-full"
    assert b.props["test_id"] == "go"
    assert b.children[0].props["content"] == "Go"


@pytest.mark.parametrize(
    ("variant", "surface_class", "label_class"),
    [
        ("default", "bg-primary", "text-primary-foreground"),
        ("secondary", "bg-secondary", "text-secondary-foreground"),
        ("outline", "border-input", "text-foreground"),
        ("ghost", "hover:bg-accent", "text-foreground"),
        ("destructive", "bg-destructive", "text-destructive-foreground"),
    ],
)
def test_button_variants(variant, surface_class, label_class):
    b = nsh.button("Go", variant=variant)
    assert surface_class in b.props["class_"].split()
    assert label_class in b.children[0].props["class_"].split()


@pytest.mark.parametrize(
    ("size", "size_class"),
    [("sm", "px-3"), ("md", "px-4"), ("lg", "px-8")],
)
def test_button_sizes(size, size_class):
    b = nsh.button("Go", size=size)
    assert size_class in b.props["class_"].split()


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("variant", "warning", "default.*destructive"),
        ("size", "xl", "sm.*lg"),
    ],
)
def test_unknown_button_options(option, value, message):
    with pytest.raises(ValueError, match=message):
        nsh.button("Go", **{option: value})


def test_button_with_bound_class():
    b = nsh.button("Go", class_=lambda: "bg-destructive")
    assert callable(b.props["class_"])
    assert b.props["class_"]().endswith(" bg-destructive")


def test_button_class_comes_after_variant():
    b = nsh.button("Go", variant="secondary", class_="bg-primary")
    assert b.props["class_"].endswith(" bg-primary")


def test_button_press():
    presses = []
    with open(lambda: nsh.button("Go", on_press=lambda: presses.append(1))) as app:
        app.press("Go")
        app.press("role:button[Go]")
    assert presses == [1, 1]
