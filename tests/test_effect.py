"""Effects and timers: inside an app (NSH effects, owned) and with no app (Python only)."""

import logging
import threading

import pytest

import nsh
from nsh.testing import open


def wait_until(condition, timeout=5.0):
    stop = threading.Event()
    for _ in range(int(timeout / 0.01)):
        if condition():
            return
        stop.wait(0.01)
    raise TimeoutError("condition never became true")


def run_in_thread(fn, *args):
    thread = threading.Thread(target=fn, args=args)
    thread.start()
    thread.join(5)
    assert not thread.is_alive()


# --- no app: Python only ----------------------------------------------------


def test_effect_with_no_app_runs_now_and_again():
    count = nsh.signal(0)
    seen = []

    @nsh.effect
    def log():
        seen.append(count())

    assert seen == [0]
    count.set(1)
    count.set(1)  # no change, no run
    count.update(lambda n: n + 1)
    assert seen == [0, 1, 2]
    assert isinstance(log, nsh.Effect) and not log.disposed


def test_effect_with_no_app_follows_computeds_and_dynamic_dependencies():
    flag = nsh.signal(True)
    a, b = nsh.signal("a"), nsh.signal("b")
    both = nsh.computed(lambda: a() + b())
    seen = []
    nsh.effect(lambda: seen.append(both() if flag() else "off"))
    assert seen == ["ab"]
    a.set("A")
    assert seen == ["ab", "Ab"]
    flag.set(False)
    a.set("x")  # no longer read
    assert seen == ["ab", "Ab", "off"]
    flag.set(True)
    assert seen[-1] == "xb"


def test_effect_with_no_app_dispose_stops_it():
    count = nsh.signal(0)
    seen = []
    handle = nsh.effect(lambda: seen.append(count()))
    count.set(1)
    handle.dispose()
    handle.dispose()  # twice is fine
    count.set(2)
    assert seen == [0, 1] and handle.disposed


def test_effect_with_no_app_is_kept_alive_without_a_reference():
    import gc

    count = nsh.signal(0)
    seen = []
    nsh.effect(lambda: seen.append(count()))
    gc.collect()
    count.set(1)
    assert seen == [0, 1]


def test_effect_exception_is_logged_and_the_effect_goes_on(caplog):
    count = nsh.signal(0)
    seen = []

    def flaky():
        n = count()
        if n == 1:
            raise ValueError("effect failed")
        seen.append(n)

    with caplog.at_level(logging.ERROR, logger="nsh"):
        nsh.effect(flaky)
        count.set(1)
        count.set(2)
    assert seen == [0, 2]
    assert "effect failed" in caplog.text


def test_effect_writing_what_it_reads_settles_or_stops(caplog):
    count = nsh.signal(0)
    nsh.effect(lambda: count.set(min(count() + 1, 3)))  # settles at 3
    assert count.peek() == 3

    runaway = nsh.signal(0)
    with caplog.at_level(logging.ERROR, logger="nsh"):
        handle = nsh.effect(lambda: runaway.set(runaway() + 1))  # never settles
    assert handle.disposed is False  # the Python-only part stopped itself
    assert "keeps changing" in caplog.text
    runaway.set(0)  # and is quiet now
    assert runaway.peek() == 0


def test_signal_write_from_a_thread_runs_python_only_effects_there():
    count = nsh.signal(0)
    seen = []
    nsh.effect(lambda: seen.append((count(), threading.get_ident())))
    run_in_thread(count.set, 1)
    assert [n for n, _ in seen] == [0, 1]
    assert seen[1][1] != threading.get_ident()  # ran on the writer's thread


# --- in an app: NSH effects -------------------------------------------------


def test_effect_in_a_component_runs_and_reruns():
    count = nsh.signal(0)
    seen = []

    def App():
        nsh.effect(lambda: seen.append(count()))
        return nsh.view(
            nsh.text(lambda: f"n={count()}"),
            nsh.button("+1", on_press=count.updater(lambda n: n + 1)),
        )

    with open(App) as app:
        assert seen == [0]
        app.press("+1")
        app.wait_for("n=1")
        wait_until(lambda: seen == [0, 1])
        run_in_thread(count.set, 5)  # from another thread too
        app.wait_for("n=5")
        wait_until(lambda: seen == [0, 1, 5])


def test_effect_in_an_app_reads_computeds_and_runs_on_the_engine():
    import nsh._core as core

    count = nsh.signal(1)
    double = nsh.computed(lambda: count() * 2)
    seen = []

    def App():
        nsh.effect(lambda: seen.append((double(), core.in_engine())))
        return nsh.text(lambda: f"n={count()}")

    with open(App) as app:
        count.set(2)
        app.wait_for("n=2")
        wait_until(lambda: len(seen) == 2)
    assert seen == [(2, True), (4, True)]


def test_effect_dispose_stops_it():
    count = nsh.signal(0)
    seen = []
    handles = []

    def App():
        handles.append(nsh.effect(lambda: seen.append(count())))
        return nsh.text(lambda: f"n={count()}")

    with open(App) as app:
        count.set(1)
        wait_until(lambda: seen == [0, 1])
        run_in_thread(handles[0].dispose)  # disposing from another thread
        count.set(2)
        app.wait_for("n=2")
        run_in_thread(count.set, 3)
        app.wait_for("n=3")
    assert seen == [0, 1]


def test_effect_dies_with_its_component():
    show = nsh.signal(True)
    count = nsh.signal(0)
    seen = []

    def Child():
        nsh.effect(lambda: seen.append(count()))
        return nsh.text("child")

    def App():
        return nsh.view(
            lambda: Child() if show() else nsh.text("no child"),
            nsh.text(lambda: f"n={count()}"),
        )

    with open(App) as app:
        app.wait_for("child")
        count.set(1)
        app.wait_for("n=1")
        wait_until(lambda: seen == [0, 1])
        show.set(False)
        app.wait_for("no child")
        count.set(2)
        app.wait_for("n=2")
        nsh.call_soon(lambda: None)
    assert seen == [0, 1]  # the region ran again: its effect went with it


def test_effect_made_from_a_thread_starts_on_the_engine():
    count = nsh.signal(0)
    seen = []
    handles = []

    def make():
        handles.append(nsh.effect(lambda: seen.append((count(), nsh._core.in_engine()))))

    with open(lambda: nsh.text(lambda: f"n={count()}")) as app:
        run_in_thread(make)
        wait_until(lambda: seen == [(0, True)])
        count.set(1)
        app.wait_for("n=1")
        wait_until(lambda: seen == [(0, True), (1, True)])
        handles[0].dispose()


def test_effect_disposed_before_it_started_never_runs():
    seen = []
    with open(lambda: nsh.text("up")) as app:
        handle = []

        def make():
            handle.append(nsh.effect(lambda: seen.append(1)))
            handle[0].dispose()

        run_in_thread(make)
        app.wait_for("up")
        nsh.call_soon(lambda: None)
    assert seen == []


def test_effect_exception_in_an_app_is_logged_and_it_keeps_running(caplog):
    count = nsh.signal(0)
    seen = []

    def flaky():
        n = count()
        if n == 1:
            raise ValueError("app effect failed")
        seen.append(n)

    def App():
        nsh.effect(flaky)
        return nsh.text(lambda: f"n={count()}")

    with caplog.at_level(logging.ERROR, logger="nsh"), open(App) as app:
        count.set(1)
        app.wait_for("n=1")
        count.set(2)
        app.wait_for("n=2")
        wait_until(lambda: seen == [0, 2])
    assert "app effect failed" in caplog.text


# --- timers -----------------------------------------------------------------


def test_timers_need_an_app():
    with pytest.raises(RuntimeError, match="running app"):
        nsh.set_timeout(0.01, print)
    with pytest.raises(RuntimeError, match="running app"):
        nsh.set_interval(0.01, print)


def test_timer_rejects_bad_seconds():
    with open(lambda: nsh.text("up")):
        for bad in (-1, float("nan"), float("inf")):
            with pytest.raises(ValueError):
                nsh.set_timeout(bad, print)


def test_set_timeout_fires_once_with_its_arguments():
    log = []

    def App():
        nsh.set_timeout(0.05, lambda *a: log.append(a), 1, "x")
        return nsh.text("up")

    with open(App) as app:
        wait_until(lambda: log)
        app.wait_for("up")
        threading.Event().wait(0.2)
    assert log == [(1, "x")]


def test_set_interval_updates_the_screen_until_cancelled():
    count = nsh.signal(0)
    timers = []

    def App():
        timers.append(nsh.set_interval(0.02, count.updater(lambda n: n + 1)))
        return nsh.text(lambda: f"ticks={count()}")

    with open(App) as app:
        wait_until(lambda: count.peek() >= 3)
        timers[0].cancel()
        assert timers[0].cancelled
        seen = count.peek()
        threading.Event().wait(0.2)
        assert count.peek() <= seen + 1  # at most one tick was already due
        app.wait_for(f"ticks={count.peek()}")


def test_timer_made_from_a_thread_and_cancelled_before_it_starts():
    log = []
    with open(lambda: nsh.text("up")) as app:
        timer = []

        def make():
            timer.append(nsh.set_interval(0.01, log.append, "tick"))
            timer[0].cancel()

        run_in_thread(make)
        app.wait_for("up")
        nsh.call_soon(lambda: None)
        threading.Event().wait(0.1)
    assert log == []


def test_set_interval_from_a_thread():
    log = []
    with open(lambda: nsh.text("up")) as app:
        timer = []
        run_in_thread(lambda: timer.append(nsh.set_interval(0.01, log.append, "tick")))
        wait_until(lambda: len(log) >= 2)
        timer[0].cancel()
        app.wait_for("up")


def test_timer_dies_with_its_component():
    show = nsh.signal(True)
    log = []

    def Child():
        nsh.set_interval(0.02, log.append, "tick")
        return nsh.text("child")

    def App():
        return nsh.view(lambda: Child() if show() else nsh.text("no child"))

    with open(App) as app:
        wait_until(lambda: len(log) >= 2)
        show.set(False)
        app.wait_for("no child")
        threading.Event().wait(0.1)
        seen = len(log)
        threading.Event().wait(0.2)
        assert len(log) == seen
