"""Apps running headless through nsh-testing: no window, no display."""

import logging
import pathlib
import runpy
import time

import pytest

import nsh
from nsh.testing import open

EXAMPLES = pathlib.Path(__file__).parent.parent / "examples"


def load_example(name):
    return runpy.run_path(str(EXAMPLES / f"{name}.py"))


def test_rust_hello():
    with open() as app:
        assert "Hello from Rust" in app.texts()


def test_counter_example():
    Counter = load_example("counter")["Counter"]
    with open(Counter) as app:
        assert app.shows("Count: 0")
        app.press("+1")
        app.press("id:inc")
        app.wait_for("Count: 2")
        app.press("−1")
        app.press("−1")
        app.press("−1")
        app.wait_for("Count: -1")
        assert "negative" in app.texts()


def test_poll_example():
    Poll = load_example("poll")["Poll"]
    with open(Poll) as app:
        assert app.shows("16 votes so far")
        assert app.texts().index("Python") < app.texts().index("Rust")
        for _ in range(6):
            app.press("role:button[Rust]")
        app.wait_for("22 votes so far")
        rows = app.texts()
        assert rows.index("Rust") < rows.index("Python")  # 9 votes beat 8


def test_monitor_example():
    Monitor = load_example("monitor")["Monitor"]
    with open(Monitor) as app:
        assert app.texts().count("40%") == 5
        for _ in range(50):  # the timer moves the load twice a second
            if app.texts().count("40%") < 5:
                break
            time.sleep(0.1)
        assert app.texts().count("40%") < 5
        assert any(t.startswith("Busiest: ") for t in app.texts())


def test_focus_example():
    Focus = load_example("focus")["Focus"]
    with open(lambda: Focus(minutes=1)) as app:
        assert app.shows("01:00")
        app.press("Start")
        app.wait_for("00:59")
        app.press("Pause")
        app.press("Reset")
        app.wait_for("01:00")


def test_tasks_example():
    Tasks = load_example("tasks")["Tasks"]
    with open(Tasks) as app:
        assert app.shows("2 left")
        app.type_text("id:new", "Water the plants\n")
        app.wait_for("Water the plants")
        app.wait_for("3 left")
        app.press("role:checkbox[Water the plants]")
        app.wait_for("2 left")


def test_stopwatch_example():
    App = load_example("stopwatch")["App"]
    with open(App) as app:
        assert app.shows("Tea") and app.shows("Eggs")
        app.press("Start >> nth=0")  # only the first one runs
        app.wait_for("00:01")
        assert app.texts().count("00:00") == 1
        app.press("Pause")
        app.press("Reset >> nth=0")
        app.wait_for("text:/^00:00$/ >> nth=1")


def test_counter_decorators_example():
    Counter = load_example("counter_decorators")["Counter"]
    with open(Counter) as app:
        app.press("id:inc")
        app.press("id:inc")
        app.wait_for("Count: 2")
        app.press("id:reset")
        app.wait_for("Count: 0")
        app.press("id:dec")
        app.wait_for("Count: -1")
        assert app.shows("negative")


def test_bindings_update_independently():
    renders = []

    def App():
        a, b = nsh.signal(0), nsh.signal(0)

        def show_a():
            renders.append("a")
            return f"a={a()}"

        return nsh.view(
            nsh.text(show_a),
            nsh.text(lambda: f"b={b()}"),
            nsh.button("bump b", on_press=lambda: b.update(lambda n: n + 1)),
        )

    with open(App) as app:
        app.press("bump b")
        app.wait_for("b=1")
        # Only the binding that read b ran again.
        assert renders == ["a"]


def test_callable_child_region():
    def App():
        items = nsh.signal(["x"])
        return nsh.view(
            lambda: [nsh.text(f"item {i}") for i in items()],
            nsh.button("add", on_press=lambda: items.mutate(lambda xs: xs.append("y"))),
        )

    with open(App) as app:
        app.press("add")
        app.wait_for("item y")
        assert app.texts()[:2] == ["item x", "item y"]


def test_handler_exception_is_logged_and_app_survives(caplog):
    def App():
        count = nsh.signal(0)

        def boom():
            raise ValueError("handler failed")

        return nsh.view(
            nsh.text(lambda: f"n={count()}"),
            nsh.button("boom", on_press=boom),
            nsh.button("inc", on_press=lambda: count.update(lambda n: n + 1)),
        )

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        app.press("boom")
        app.press("inc")
        app.wait_for("n=1")
    errors = [r for r in caplog.records if r.exc_info]
    assert len(errors) == 1
    assert isinstance(errors[0].exc_info[1], ValueError)


def test_root_exception_shows_error_page(caplog):
    def App():
        raise RuntimeError("no view")

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        assert app.shows("The app's root raised an exception")
    assert "no view" in caplog.text


def test_wait_for_timeout():
    with open(lambda: nsh.text("here")) as app:
        with pytest.raises(TimeoutError):
            app.wait_for("not here", timeout=0.2)


SHARED = nsh.signal(0)


def shared_app():
    return nsh.view(
        nsh.text(lambda: f"shared={SHARED()}"),
        nsh.button("inc", on_press=lambda: SHARED.update(lambda n: n + 1)),
    )


@pytest.mark.parametrize("run", [1, 2])
def test_module_level_signal_across_apps(run):
    # Each app has its own engine thread and reactive graph; the signal's
    # NSH trigger from the first must not leak into the second.
    with open(shared_app) as app:
        before = SHARED.peek()
        app.press("inc")
        app.wait_for(f"shared={before + 1}")


def test_decorators_and_computed_in_the_engine():
    def App():
        count = nsh.signal(0)

        @nsh.computed
        def parity():
            return "even" if count() % 2 == 0 else "odd"

        @count.updater
        def increment(n):
            return n + 1

        def add_two():
            count.value += 2

        return nsh.view(
            nsh.text(count.map(lambda n: f"n={n}")),
            nsh.text(parity),
            nsh.button("inc", on_press=increment),
            nsh.button("two", on_press=add_two),
            nsh.button("reset", on_press=count.setter(0)),
        )

    with open(App) as app:
        assert app.shows("n=0") and app.shows("even")
        app.press("inc")
        app.wait_for("n=1")
        assert app.shows("odd")
        app.press("two")
        app.wait_for("n=3")
        assert app.shows("odd")
        app.press("reset")
        app.wait_for("n=0")
        assert app.shows("even")


def test_failing_computed_recovers_when_its_source_changes(caplog):
    def App():
        n = nsh.signal(0)
        inverse = nsh.computed(lambda: f"inverse={1 / n()}")
        return nsh.view(nsh.text(inverse), nsh.button("one", on_press=n.setter(1)))

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        assert "ZeroDivisionError" in caplog.text
        app.press("one")
        app.wait_for("inverse=1.0")


def test_dataframe_example():
    pytest.importorskip("pandas")
    App = load_example("dataframe")["App"]

    def summary(app):
        return next(t for t in app.texts() if t.endswith(tuple("0123456789")) and "sales," in t)

    with open(App) as app:
        assert summary(app).startswith("8 sales,")
        app.press("Add a sale")
        app.press("Sort by units")  # handlers run in order, so this sees 9 rows
        assert summary(app).startswith("9 sales,")
        texts = app.texts()
        units = [
            int(texts[i + 2])
            for i, t in enumerate(texts)
            if t in {"North", "South", "East", "West"}
        ]
        assert units == sorted(units, reverse=True) and len(units) == 9


def test_form_example():
    Form = load_example("form")["Form"]
    with open(Form) as app:
        app.type_text("id:name", "Ada")
        app.wait_for("Hello, Ada")
        app.type_text("id:email", "ada@example.org")
        app.type_text("id:password", "s3cret")
        app.type_text("id:email", "\n")
        app.wait_for("Welcome, Ada! We'll write to ada@example.org.")
        assert app.value("id:name") == ""
        assert app.value("id:email") == ""
        assert app.value("id:password") == ""
        app.type_text("id:name", "Bo")
        app.press("id:send")  # no email: nothing is sent
        app.wait_for("Hello, Bo")
        assert app.shows("Welcome, Ada! We'll write to ada@example.org.")
