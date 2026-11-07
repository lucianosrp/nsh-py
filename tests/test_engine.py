"""The engine-thread queue: call_soon, and signals written from other threads."""

import gc
import logging
import threading

import nsh
from nsh import _core
from nsh.testing import open


def wait_until(condition, timeout=5.0):
    """Poll `condition` (for work that isn't on screen)."""
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


def test_signal_set_from_a_thread_updates_the_screen(caplog):
    count = nsh.signal(0)

    def App():
        return nsh.text(lambda: f"Count: {count()}")

    with caplog.at_level(logging.WARNING, logger="nsh"), open(App) as app:
        app.wait_for("Count: 0")
        run_in_thread(count.set, 7)
        assert count.peek() == 7  # stored at once
        app.wait_for("Count: 7")
    assert caplog.records == []  # the old "wrote outside the app's thread" warning is gone


def test_every_write_style_works_from_a_thread():
    items = nsh.signal(["a"])
    count = nsh.signal(0)
    label = nsh.computed(lambda: f"{count()} / {len(items())}")

    def App():
        return nsh.view(
            nsh.text(lambda: f"items={','.join(items())}"),
            nsh.text(label),
        )

    def writes():
        count.update(lambda n: n + 2)
        items.mutate(lambda xs: xs.append("b"))

    with open(App) as app:
        run_in_thread(writes)
        app.wait_for("items=a,b")
        app.wait_for("2 / 2")  # the computed saw both changes


def test_concurrent_updates_lose_nothing():
    count = nsh.signal(0)

    def App():
        return nsh.view(
            nsh.text(lambda: f"n={count()}"),
            nsh.button("+1", on_press=count.updater(lambda n: n + 1)),
        )

    def bump():
        for _ in range(200):
            count.update(lambda n: n + 1)

    with open(App) as app:
        threads = [threading.Thread(target=bump) for _ in range(4)]
        for t in threads:
            t.start()
        for _ in range(10):
            app.press("+1")  # the app's own thread writes too
        for t in threads:
            t.join()
        app.wait_for("n=810")


def test_call_soon_runs_on_the_engine_thread():
    seen = []
    engine = []

    def App():
        engine.append(threading.get_ident())  # the root runs on the engine's thread
        return nsh.text("app")

    def where():
        seen.append((threading.get_ident(), _core.in_engine()))

    with open(App) as app:
        run_in_thread(nsh.call_soon, where)
        nsh.call_soon(where)  # from the test's thread: also off the engine
        wait_until(lambda: len(seen) == 2)
        app.wait_for("app")
    assert engine[0] != threading.get_ident()
    assert seen == [(engine[0], True)] * 2


def test_call_soon_passes_arguments_and_keeps_order():
    log = []
    with open(lambda: nsh.text("done")) as app:
        for i in range(5):
            nsh.call_soon(log.append, i)
        nsh.call_soon(lambda a, b: log.append(a + b), "x", "y")
        wait_until(lambda: len(log) == 6)
        app.wait_for("done")
    assert log == [0, 1, 2, 3, 4, "xy"]


def test_call_soon_from_the_engine_defers_until_the_handler_ends():
    log = []

    def App():
        def handler():
            nsh.call_soon(log.append, "soon")
            log.append("handler end")

        return nsh.view(nsh.button("go", on_press=handler), nsh.text(lambda: f"log={len(log)}"))

    with open(App) as app:
        app.press("go")
        wait_until(lambda: len(log) == 2)
    assert log == ["handler end", "soon"]


def test_call_soon_can_write_signals_and_post_more():
    count = nsh.signal(0)

    def again():
        count.update(lambda n: n + 1)
        if count.peek() < 3:
            nsh.call_soon(again)

    with open(lambda: nsh.text(lambda: f"n={count()}")) as app:
        run_in_thread(nsh.call_soon, again)
        app.wait_for("n=3")


def test_call_soon_exception_is_logged_and_later_calls_run(caplog):
    log = []

    def boom():
        raise ValueError("call_soon failed")

    with caplog.at_level(logging.ERROR, logger="nsh"), open(lambda: nsh.text("up")) as app:
        nsh.call_soon(boom)
        nsh.call_soon(log.append, "after")
        wait_until(lambda: log)
        app.wait_for("up")
    assert log == ["after"]
    errors = [r for r in caplog.records if r.exc_info]
    assert len(errors) == 1 and isinstance(errors[0].exc_info[1], ValueError)


def test_call_soon_with_no_app_runs_right_away(caplog):
    log = []
    nsh.call_soon(log.append, 1)
    assert log == [1]
    with caplog.at_level(logging.ERROR, logger="nsh"):
        nsh.call_soon(lambda: 1 / 0)  # logged, not raised
    assert "ZeroDivisionError" in caplog.text


def test_signals_work_again_after_an_app_closes(caplog):
    count = nsh.signal(0)
    with open(lambda: nsh.text(lambda: f"n={count()}")) as app:
        count.set(1)
        app.wait_for("n=1")
    # The engine is gone: a write is a plain write, quietly.
    with caplog.at_level(logging.WARNING, logger="nsh"):
        run_in_thread(count.set, 2)
        count.set(3)
    assert count.peek() == 3 and caplog.records == []
    # And a new app picks the same signal up again.
    with open(lambda: nsh.text(lambda: f"n={count()}")) as app:
        run_in_thread(count.set, 4)
        app.wait_for("n=4")


def test_signal_dropped_from_another_thread_while_the_app_runs():
    # The trigger lives in the engine's graph: dropping the signal here
    # (not the engine's thread) posts its disposal there.
    keep = {}

    def App():
        keep["s"] = nsh.signal(1)
        return nsh.view(
            nsh.text(lambda: f"s={keep['s']() if 's' in keep else 'gone'}"),
            nsh.text("alive"),
        )

    with open(App) as app:
        app.wait_for("s=1")
        sig = keep.pop("s")
        del sig
        gc.collect()
        done = []
        nsh.call_soon(done.append, 1)  # the queue runs on, after the disposal
        wait_until(lambda: done)
        app.wait_for("alive")


def test_binding_reading_a_computed_and_its_signal_runs_once_per_write():
    count = nsh.signal(0)
    double = nsh.computed(lambda: count() * 2)
    runs = []

    def show():
        runs.append(1)
        return f"{count()}/{double()}"

    with open(lambda: nsh.text(show)) as app:
        assert len(runs) == 1
        run_in_thread(count.set, 1)
        app.wait_for("1/2")
        assert len(runs) == 2
