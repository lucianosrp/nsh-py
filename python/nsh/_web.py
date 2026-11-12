"""`nsh.run(App, platform="web")`: show the app in a browser instead.

The browser runs the app itself: Pyodide runs the script again, with the
web build of nsh-py, and NSH's web backend draws it as HTML. This module
is the desktop side: a small local server that hands the page the
script, and a browser tab pointed at it.

The page and the web build of nsh-py come from `web/pyodide/site` in a
checkout (`sh web/pyodide/build.sh` builds them), or from the folder in
`NSH_WEB_SITE`. Releases don't ship a web build yet.
"""

from __future__ import annotations

import functools
import http.server
import logging
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

logger = logging.getLogger("nsh")

APP_PREFIX = "/app/"
"""Where the page finds the script's folder."""


def in_browser() -> bool:
    """True when this Python is Pyodide, in a browser."""
    return sys.platform == "emscripten"


def find_site() -> Path:
    """The folder with the page and the web build of nsh-py.

    Raises `RuntimeError` saying how to build it if there is none.
    """
    env = os.environ.get("NSH_WEB_SITE")
    candidates = [Path(env)] if env else []
    # A checkout: python/nsh/_web.py -> the repo root.
    candidates.append(Path(__file__).resolve().parents[2] / "web" / "pyodide" / "site")
    for site in candidates:
        if (site / "index.html").is_file() and any(site.glob("nsh_py-*pyemscripten*.whl")):
            return site
    raise RuntimeError(
        'platform="web" needs the web build of nsh-py, and none was found in '
        + ", ".join(str(c) for c in candidates)
        + ". In a checkout, build it with `sh web/pyodide/build.sh` (see web/README.md), "
        "or point NSH_WEB_SITE at a folder that has it."
    )


class _Handler(http.server.SimpleHTTPRequestHandler):
    """The page from `site`, and `/app/...` from the script's folder."""

    def __init__(self, *args, site: Path, app_dir: Path, **kwargs) -> None:
        self.site = site
        self.app_dir = app_dir
        super().__init__(*args, directory=str(site), **kwargs)

    def translate_path(self, path: str) -> str:
        path = unquote(urlsplit(path).path)
        if path.startswith(APP_PREFIX):
            root = self.app_dir.resolve()
            target = (root / path[len(APP_PREFIX) :]).resolve()
            # Nothing outside the script's folder.
            if target != root and root not in target.parents:
                return str(root / "not-served" / "not-served")
            return str(target)
        return super().translate_path(path)

    def end_headers(self) -> None:
        # A browser refresh picks up the saved script.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        logger.debug("web: " + format, *args)


def make_server(script: Path, site: Path, port: int = 8766) -> http.server.ThreadingHTTPServer:
    """A server on localhost for `script`'s folder and the page in `site`.

    Takes `port`, or any free port if it's in use.
    """
    handler = functools.partial(_Handler, site=site, app_dir=script.parent)
    try:
        return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError:
        return http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)


def app_url(server: http.server.HTTPServer, script: Path) -> str:
    """The page's address, showing `script`."""
    port = server.server_address[1]
    return f"http://localhost:{port}/?app={quote(APP_PREFIX[1:] + script.name)}"


def open_browser(url: str) -> None:
    """Open `url` in the default browser, keeping its messages out of the terminal.

    `webbrowser.open` starts the browser with our stdout and stderr, so
    whatever it logs (Chrome's "Opening in existing browser session" and
    its errors) lands under the app's own output. `BROWSER`, when set,
    still goes through `webbrowser`, as it would anywhere else.
    """
    if os.environ.get("BROWSER"):
        webbrowser.open(url)
        return
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
        return
    opener = "open" if sys.platform == "darwin" else shutil.which("xdg-open")
    if opener is None:
        webbrowser.open(url)
        return
    subprocess.Popen(
        [opener, url],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # not stopped by Ctrl-C in our terminal
    )


def serve(script: str | os.PathLike[str], *, port: int = 8766, browser: bool = True) -> None:
    """Serve `script` to the browser and open it there; block until Ctrl-C.

    Ctrl-C stops the server and raises `KeyboardInterrupt`, which
    `nsh.run` turns into a quiet return, as for a window.
    """
    script = Path(script).resolve()
    server = make_server(script, find_site(), port)
    url = app_url(server, script)
    print(f"nsh: {script.name} is at {url} (Ctrl-C to stop)", file=sys.stderr)
    if browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
