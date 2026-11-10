"""Class components: annotated attributes are signals, `view()` runs once."""

from typing import ClassVar

import pytest

import nsh
from nsh.testing import open


class Counter(nsh.Component):
    count: int = 0
    step: int = 1
    LABEL = "Count"  # unannotated: a plain constant

    def bump(self):
        self.count += self.step

    def view(self):
        return nsh.view(
            nsh.text(lambda: f"{self.LABEL}: {self.count}"),
            nsh.button("+", on_press=self.bump),
        )


def test_assigning_a_field_redraws():
    with open(Counter) as app:
        app.wait_for("Count: 0")
        app.press("+")
        app.press("+")
        app.wait_for("Count: 2")


def test_props_set_the_starting_values():
    with open(lambda: Counter(count=10, step=5)) as app:
        app.press("+")
        app.wait_for("Count: 15")


def test_a_signal_prop_is_shared_with_the_caller():
    def Parent():
        total = nsh.signal(0)
        return nsh.view(
            Counter(count=total),
            nsh.text(lambda: f"Parent sees {total()}"),
        )

    with open(Parent) as app:
        app.press("+")
        app.wait_for("Parent sees 1")


def test_each_instance_has_its_own_state():
    class Todo(nsh.Component):
        items: list = []  # copied per instance

        def view(self):
            def add():
                self.items = [*self.items, "x"]

            return nsh.view(
                nsh.text(lambda: f"{len(self.items)} items"), nsh.button("add", on_press=add)
            )

    with open(lambda: nsh.view(Todo(), Todo())) as app:
        app.press("add >> nth=0")
        app.wait_for("1 items")
        assert app.shows("0 items")


def test_signals_gives_a_fields_signal_to_a_widget():
    class Task(nsh.Component):
        done: bool = False

        def view(self):
            return nsh.view(
                nsh.checkbox("Done", checked=self.signals.done),
                nsh.text(lambda: "yes" if self.done else "no"),
            )

    with open(Task) as app:
        app.wait_for("no")
        app.press("Done")
        app.wait_for("yes")


def test_setup_runs_before_view_and_properties_are_live():
    class Doubler(nsh.Component):
        n: int = 2
        seen: ClassVar[list] = []

        def setup(self):
            self.seen.append("setup")

        @property
        def double(self):
            return self.n * 2

        def view(self):
            self.seen.append("view")
            return nsh.view(
                nsh.text(lambda: f"double {self.double}"),
                nsh.button("inc", on_press=lambda: setattr(self, "n", self.n + 1)),
            )

    with open(Doubler) as app:
        app.press("inc")
        app.wait_for("double 6")
    assert Doubler.seen == ["setup", "view"]


def test_fields_are_inherited():
    class Big(Counter):
        step: int = 100

    with open(Big) as app:
        app.press("+")
        app.wait_for("Count: 100")


def test_a_missing_or_unknown_prop_raises():
    class Named(nsh.Component):
        name: str

        def view(self):
            return nsh.text(self.name)

    with pytest.raises(TypeError, match="missing keyword argument: 'name'"):
        Named()
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        Named(name="a", colour="red")
    assert Named(name="a") is not None


def test_view_must_be_defined():
    class Empty(nsh.Component):
        pass

    with pytest.raises(NotImplementedError):
        Empty()
