"""Ctrl-C closes the app quietly: `nsh.run` returns, with no traceback."""

import os
import sys

import pytest

import nsh
from nsh import _core, _reload


def interrupted(*args, **kwargs):
    raise KeyboardInterrupt


def test_ctrl_c_returns_from_run(monkeypatch):
    monkeypatch.setattr(_core, "run", interrupted)
    assert nsh.run(lambda: None) is None


def test_ctrl_c_returns_from_a_reloading_run(monkeypatch, tmp_path):
    script = tmp_path / "app.py"
    script.write_text("import nsh\n")
    monkeypatch.setattr(_core, "run", interrupted)
    stopped = []
    monkeypatch.setattr(_reload.Reloader, "stop", lambda self: stopped.append(True))
    _reload.run_reloading(script, lambda: None)
    assert stopped == [True]  # the watcher still stops


def test_other_errors_still_raise(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(_core, "run", broken)
    with pytest.raises(RuntimeError, match="boom"):
        nsh.run(lambda: None)


def test_ctrl_c_returns_from_a_web_run(monkeypatch, tmp_path):
    from nsh import _web

    monkeypatch.setattr(_web, "serve", interrupted)
    monkeypatch.setattr(_web, "in_browser", lambda: False)
    monkeypatch.setattr(
        sys.modules["__main__"], "__file__", str(tmp_path / "app.py"), raising=False
    )
    assert nsh.run(lambda: None, platform="web") is None


@pytest.mark.skipif(sys.platform == "win32", reason="Ctrl-C not wired on Windows yet")
@pytest.mark.skipif(
    sys.platform.startswith("linux")
    and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
    reason="no display",
)
@pytest.mark.gui
def test_ctrl_c_gui():
    import select
    import signal
    import subprocess

    script = """
import nsh
def App():
    nsh.set_timeout(0, lambda: print("READY", flush=True))
    return nsh.text("hi")
nsh.run(App)
"""
    # Import the same nsh as this process: conftest may have put the
    # checkout's python/ on sys.path (a fetched core, not installed).
    pkg_dir = os.path.dirname(os.path.dirname(nsh.__file__))
    pythonpath = os.pathsep.join(filter(None, [pkg_dir, os.environ.get("PYTHONPATH")]))
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": pythonpath},
    )
    try:
        assert select.select([proc.stdout], [], [], 15)[0], proc.stderr.read()
        assert proc.stdout.readline() == b"READY\n", proc.stderr.read()
        proc.send_signal(signal.SIGINT)
        _, err = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()

    assert proc.returncode == 0, err
