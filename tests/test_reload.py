"""Hot reload: the window shows the script's new root after a change."""

import builtins
import json
import logging
import os
import sys
import textwrap
import time
from pathlib import Path

import pytest

import nsh
from nsh._reload import Reloader, is_app_module
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


def test_nsh_and_installed_packages_never_reload(tmp_path):
    # A script in a checkout of nsh-py has nsh under its folder, and a
    # project's .venv sits under it too: neither is the app's own code.
    nsh_file = tmp_path / "python" / "nsh" / "_element.py"
    assert not is_app_module("nsh._element", nsh_file, tmp_path)
    assert not is_app_module("nsh", tmp_path / "python" / "nsh" / "__init__.py", tmp_path)
    venv_file = (
        tmp_path / ".venv" / "lib" / "python3.14" / "site-packages" / "numpy" / "__init__.py"
    )
    assert not is_app_module("numpy", venv_file, tmp_path)
    assert is_app_module("greeting", tmp_path / "greeting.py", tmp_path)
    assert is_app_module("ui.cards", tmp_path / "ui" / "cards.py", tmp_path)
    assert not is_app_module("json", Path(json.__file__).resolve(), tmp_path)


def test_reload_next_to_nsh_keeps_drawing_elements(tmp_path):
    # The bug this guards: reloading nsh too made a second Element class,
    # and the window showed the elements' repr instead of drawing them.
    script = tmp_path / "app.py"
    write(script, "v1")
    reloader = Reloader(script)
    element_class = nsh.Element
    with open(reloader.root()) as app:
        app.wait_for("Hello v1 0")
        write(script, "v2")
        nsh.call_soon(reloader.reload)
        app.wait_for("Hello v2 0")
        assert not any(t.startswith("Element(") for t in app.texts())
    assert sys.modules["nsh"].Element is element_class
    # A script in the checkout's root has nsh under its folder.
    reloader.script = Path(nsh.__file__).resolve().parents[2] / "app.py"
    assert not any(n == "nsh" or n.startswith("nsh.") for n in reloader._local_modules())
