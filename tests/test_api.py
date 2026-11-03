"""The pure-Python API, without an engine (no display needed)."""

import logging

import nsh
from nsh import _runtime


def test_signal_outside_engine_is_a_plain_box():
    count = nsh.signal(1)
    assert count() == 1
    count.set(2)
    count.update(lambda n: n + 1)
    assert count() == 3
    assert count.peek() == 3


def test_signal_equal_write_keeps_old_value():
    a, b = [1], [1]
    s = nsh.signal(a)
    s.set(b)
    assert s() is a


def test_signal_mutate():
    items = nsh.signal([1])
    items.mutate(lambda xs: xs.append(2))
    assert items() == [1, 2]


def test_signal_with_odd_equality():
    class Weird:
        def __eq__(self, other):
            raise TypeError("no")

    s = nsh.signal(Weird())
    w = Weird()
    s.set(w)
    assert s() is w


def test_elements():
    tree = nsh.view(
        nsh.text("hi", class_="text-xl"),
        nsh.button("Go", on_press=lambda: None, class_="w-full", test_id="go"),
        class_="p-4",
    )
    assert tree.kind == "view"
    assert tree.props == {"class_": "p-4"}
    text, button = tree.children
    assert text.props == {"content": "hi", "class_": "text-xl"}
    assert button.props["role"] == "button"
    assert button.props["class_"].endswith(" w-full")
    assert button.props["test_id"] == "go"
    assert button.children[0].props["content"] == "Go"


def test_button_with_bound_class():
    b = nsh.button("Go", class_=lambda: "bg-destructive")
    assert callable(b.props["class_"])
    assert b.props["class_"]().endswith(" bg-destructive")


def test_report_exception_logs(caplog):
    try:
        raise ValueError("boom")
    except ValueError as e:
        err = e
    with caplog.at_level(logging.ERROR, logger="nsh"):
        _runtime.report_exception(err)
    assert "Exception in app code" in caplog.text
    assert caplog.records[0].exc_info[1] is err
