#!/usr/bin/env python3
"""Run a script (an example) against the checkout's ``python/`` directory.

For the Python-only flow: after ``tools/fetch_core.py`` the compiled core
sits in ``python/nsh/``, but ``nsh`` is not installed, so a plain
``python examples/counter.py`` can't import it. This puts ``python/`` on
the import path and runs the script as ``__main__``. Same on every OS, and
no environment variables to set. Standard library only.

Usage:
    python tools/run.py examples/counter.py
    uv run --no-project python tools/run.py examples/counter.py
    uv run --no-project python tools/run.py --reload examples/counter.py   # redraw on save

If you build locally with ``uv run`` instead, you don't need this:
``uv run python examples/counter.py`` works as is.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent.parent / "python"


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    reload = argv[0] == "--reload"
    if reload:
        argv = argv[1:]
        if not argv:
            print("error: --reload needs a script", file=sys.stderr)
            return 2
    script = Path(argv[0]).resolve()
    if not script.is_file():
        print(f"error: {argv[0]} is not a file", file=sys.stderr)
        return 2
    # Like `python script.py`: the script's folder first, then ours.
    sys.path[:] = [str(script.parent), str(PYTHON_DIR)] + sys.path[1:]
    if reload:
        from nsh._reload import main as reload_main

        return reload_main([str(script), *argv[1:]])
    sys.argv = [str(script), *argv[1:]]
    runpy.run_path(str(script), run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
