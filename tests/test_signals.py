"""Signals without an engine: plain boxes (no display needed)."""

import nsh


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
