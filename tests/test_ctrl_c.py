"""Ctrl-C closes the app quietly: `nsh.run` returns, with no traceback."""

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
    import sys

    from nsh import _web

    monkeypatch.setattr(_web, "serve", interrupted)
    monkeypatch.setattr(_web, "in_browser", lambda: False)
    monkeypatch.setattr(
        sys.modules["__main__"], "__file__", str(tmp_path / "app.py"), raising=False
    )
    assert nsh.run(lambda: None, platform="web") is None
