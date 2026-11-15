"""The skeleton component and its loading example."""

import pathlib
import runpy

import pytest

import nsh
from nsh.testing import open


def test_skeleton_defaults():
    placeholder = nsh.skeleton(test_id="placeholder")
    assert placeholder.kind == "view"
    assert placeholder.props == {
        "class_": "rounded-md bg-muted animate-pulse",
        "test_id": "placeholder",
    }
    assert placeholder.children == []


def test_skeleton_custom_classes():
    placeholder = nsh.skeleton(class_="h-4 w-48 rounded-full animate-none")
    assert placeholder.props["class_"] == (
        "rounded-md bg-muted animate-pulse h-4 w-48 rounded-full animate-none"
    )


def test_skeleton_callable_class_is_not_read_early():
    size = "h-4 w-48"
    reads = []

    def classes():
        reads.append(size)
        return size

    placeholder = nsh.skeleton(class_=classes)
    assert reads == []
    binding = placeholder.props["class_"]
    assert callable(binding)
    assert binding() == "rounded-md bg-muted animate-pulse h-4 w-48"
    size = "h-8 w-64"
    assert binding() == "rounded-md bg-muted animate-pulse h-8 w-64"


def test_loading_example_replaces_skeletons_and_can_reload():
    example = pathlib.Path(__file__).resolve().parents[2] / "examples" / "skeleton.py"
    Poll = runpy.run_path(str(example))["Poll"]

    with open(Poll) as app:
        for cycle in range(2):
            app.wait_for("id:poll-loading")
            assert app.shows("Loading results…")
            assert not app.shows("Python")
            app.wait_for("16 votes so far")
            assert app.shows("Python")
            assert app.shows("Rust")
            assert app.shows("Both")
            with pytest.raises(TimeoutError):
                app.wait_for("id:poll-loading", timeout=0.05)
            if cycle == 0:
                app.press("Reload")
