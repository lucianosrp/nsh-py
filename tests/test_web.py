"""`nsh.run(platform="web")`: the local server that hands the page the app."""

import sys
import threading
import urllib.error
import urllib.request

import pytest

import nsh
from nsh import _web


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A fake web build: the page and a wheel."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<p>page</p>")
    (site / "nsh_py-0.0.1-cp310-abi3-pyemscripten_2026_0_wasm32.whl").write_bytes(b"wheel")
    monkeypatch.setenv("NSH_WEB_SITE", str(site))
    return site


@pytest.fixture
def script(tmp_path):
    app = tmp_path / "myapp"
    app.mkdir()
    (app / "app.py").write_text("print('hi')\n")
    (tmp_path / "secret.txt").write_text("not served")
    return app / "app.py"


@pytest.fixture
def server(site, script):
    server = _web.make_server(script, _web.find_site(), port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def get(server, path):
    port = server.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return response.read().decode(), response.headers


def test_the_page_and_the_script_are_served(server, script):
    assert get(server, "/")[0] == "<p>page</p>"
    body, headers = get(server, "/app/app.py")
    assert body == "print('hi')\n"
    assert headers["Cache-Control"] == "no-store"  # refresh shows saved edits


def test_nothing_outside_the_scripts_folder_is_served(server):
    with pytest.raises(urllib.error.HTTPError) as err:
        get(server, "/app/../secret.txt")
    assert err.value.code == 404


def test_the_url_names_the_script(server, script):
    port = server.server_address[1]
    assert _web.app_url(server, script) == f"http://localhost:{port}/?app=app/app.py"


def test_a_missing_web_build_says_how_to_make_it(tmp_path, monkeypatch):
    monkeypatch.setenv("NSH_WEB_SITE", str(tmp_path))
    monkeypatch.setattr(_web, "__file__", str(tmp_path / "a" / "b" / "_web.py"))
    with pytest.raises(RuntimeError, match="web/pyodide/build.sh"):
        _web.find_site()


def test_an_unknown_platform_is_refused():
    with pytest.raises(ValueError, match="platform"):
        nsh.run(lambda: None, platform="gpui")


def test_web_and_reload_are_refused_together(site, monkeypatch):
    monkeypatch.setattr(_web, "in_browser", lambda: False)
    with pytest.raises(ValueError, match="reload"):
        nsh.run(lambda: None, platform="web", reload=True)


def test_web_serves_the_main_script(site, script, monkeypatch):
    served = []
    monkeypatch.setattr(_web, "serve", served.append)
    monkeypatch.setattr(_web, "in_browser", lambda: False)
    monkeypatch.setattr(sys.modules["__main__"], "__file__", str(script), raising=False)
    nsh.run(lambda: None, platform="web")
    assert served == [str(script)]


def test_nsh_platform_picks_the_platform(monkeypatch):
    monkeypatch.setenv("NSH_PLATFORM", "gpui")
    with pytest.raises(ValueError, match="gpui"):
        nsh.run(lambda: None)


def test_tui_runs_in_the_terminal(monkeypatch):
    ran = []
    monkeypatch.setattr(nsh._runtime._core, "run_tui", ran.append)
    monkeypatch.setenv("NSH_PLATFORM", "tui")
    root = object()
    nsh.run(root)
    assert ran == [root]


def test_the_browser_starts_without_our_terminal(monkeypatch):
    started = []
    monkeypatch.delenv("BROWSER", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(_web.shutil, "which", lambda name: "/usr/bin/xdg-open")
    monkeypatch.setattr(_web.subprocess, "Popen", lambda args, **kw: started.append((args, kw)))
    _web.open_browser("http://localhost:1/")
    [(args, kw)] = started
    assert args == ["/usr/bin/xdg-open", "http://localhost:1/"]
    assert kw["stdout"] is kw["stderr"] is _web.subprocess.DEVNULL
