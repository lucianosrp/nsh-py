"""Hot reload: the window shows the script's new root after a change."""

import builtins
import logging
import os
import sys
import textwrap
import time

import pytest

import nsh
from nsh._reload import Reloader
from nsh.testing import open

APP = """
import nsh
from greeting import WORD

def App():
    count = nsh.signal(0)
    return nsh.view(
        nsh.text(lambda: f"{WORD} LABEL {count()}"),
        nsh.button("+1", on_press=lambda: count.update(lambda n: n + 1)),
    )

if __name__ == "__main__":
    nsh.run(App, reload=True)
    raise SystemExit("after run")  # never reached: run hands over the root
"""


@pytest.fixture(autouse=True)
def fresh_greeting():
    # Each test's app imports its own greeting.py: drop the last one.
    sys.modules.pop("greeting", None)
    yield
    sys.modules.pop("greeting", None)


def write(path, label, word="Hello"):
    path.write_text(textwrap.dedent(APP.replace("LABEL", label)))
    (path.parent / "greeting.py").write_text(f"WORD = {word!r}\n")
    # Make each write a new modification time, even on coarse clocks.
    os.utime(path, ns=(0, os.stat(path).st_mtime_ns + 1_000_000_000))


def test_reload_shows_the_new_code(tmp_path):
    script = tmp_path / "app.py"
    write(script, "v1")
    reloader = Reloader(script)
    with open(reloader.root()) as app:
        app.wait_for("Hello v1 0")
        app.press("+1")
        app.wait_for("Hello v1 1")
        write(script, "v2", word="Hi")  # the script and a module it imports
        nsh.call_soon(reloader.reload)
        app.wait_for("Hi v2 0")  # new code; state made in components starts over
        assert not app.shows("Hello v1 1")


def test_a_broken_edit_keeps_the_old_view(tmp_path, caplog):
    script = tmp_path / "app.py"
    write(script, "v1")
    reloader = Reloader(script)
    with open(reloader.root()) as app:
        app.wait_for("Hello v1 0")
        script.write_text("def App(:\n")  # a syntax error
        assert reloader.reload() is False
        assert app.shows("Hello v1 0")
    assert "Reload of app.py failed" in caplog.text


def test_the_watcher_notices_a_save(tmp_path):
    script = tmp_path / "app.py"
    write(script, "v1")
    reloader = Reloader(script)
    with open(reloader.root()) as app:
        app.wait_for("Hello v1 0")
        reloader.watch()
        try:
            write(script, "v3")
            app.wait_for("Hello v3 0", timeout=5)
        finally:
            reloader.stop()


def test_a_script_without_run_raises(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("import nsh\n")
    with pytest.raises(RuntimeError, match="never called nsh.run"):
        Reloader(script)


logging.getLogger("nsh").setLevel(logging.INFO)


def test_reload_stops_the_old_components_timers(tmp_path):
    ticks = []
    source = """
import nsh
def App():
    nsh.set_interval(0.05, lambda: TICKS.append("VER"))
    return nsh.text("VER")
nsh.run(App)
"""
    script = tmp_path / "app.py"
    script.write_text(source.replace("VER", "v1"))
    # The script reads TICKS from builtins, so both versions share it.
    builtins.TICKS = ticks
    try:
        reloader = Reloader(script)
        with open(reloader.root()) as app:
            app.wait_for("v1")
            script.write_text(source.replace("VER", "v2"))
            nsh.call_soon(reloader.reload)
            app.wait_for("v2")
            before = ticks.count("v1")
            time.sleep(0.4)
            assert ticks.count("v1") == before  # the old timer ended with its component
            assert ticks.count("v2") > 0
    finally:
        del builtins.TICKS
