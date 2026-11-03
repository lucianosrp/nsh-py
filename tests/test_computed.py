"""Ergonomics: .value, handler decorators, computed (no display needed)."""

import pytest

import nsh


def test_value_property_reads_and_writes():
    count = nsh.signal(1)
    assert count.value == 1
    count.value = 5
    assert count() == 5
    count.value += 1
    assert count.peek() == 6


def test_setter_updater_mutator_make_handlers():
    count = nsh.signal(0)
    items = nsh.signal([])

    @count.updater
    def increment(n):
        """Add one."""
        return n + 1

    @items.mutator
    def add_item(xs):
        xs.append("x")

    reset = count.setter(0)

    increment()
    increment()
    assert count() == 2
    assert increment.__name__ == "increment" and increment.__doc__ == "Add one."
    add_item()
    assert items() == ["x"]
    reset()
    assert count() == 0


def test_computed_is_cached_until_a_source_changes():
    count = nsh.signal(2)
    runs = []

    @nsh.computed
    def double():
        runs.append(1)
        return count() * 2

    assert double() == 4 and double.value == 4 and double.peek() == 4
    assert len(runs) == 1
    count.set(2)  # equal write: nothing changes
    assert double() == 4 and len(runs) == 1
    count.set(3)
    assert double() == 6 and len(runs) == 2


def test_computed_chains_and_follows_new_sources():
    flag = nsh.signal(True)
    a = nsh.signal("a")
    b = nsh.signal("b")
    pick = nsh.computed(lambda: a() if flag() else b())
    loud = pick.map(str.upper)

    assert loud() == "A"
    b.set("bb")  # not read yet: no recompute needed
    assert loud() == "A"
    flag.set(False)
    assert loud() == "BB"
    a.set("aa")  # no longer read
    assert pick._value == "bb"
    b.set("c")
    assert loud() == "C"


def test_computed_cannot_be_set():
    c = nsh.computed(lambda: 1)
    with pytest.raises(AttributeError):
        c.value = 2


def test_computed_reading_itself_raises():
    holder = []
    c = nsh.computed(lambda: holder[0]())
    holder.append(c)
    with pytest.raises(RuntimeError, match="reads itself"):
        c()


def test_computed_error_retries_on_next_read():
    s = nsh.signal(0)
    c = nsh.computed(lambda: 1 // s())
    with pytest.raises(ZeroDivisionError):
        c()
    s.set(1)
    assert c() == 1
