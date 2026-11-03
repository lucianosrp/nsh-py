"""Which `nsh` the tests import.

The checkout's `python/nsh` is used when it holds a compiled core: a local
build (`uv run`, `maturin develop`) or one fetched by `tools/fetch_core.py`
for Python-only work (`uv run --no-project --with pytest pytest -q tests`).
Otherwise, as in CI, which installs a built wheel, the installed package is
used: putting a checkout without `_core` first would hide it.
"""

import pathlib
import sys

PYTHON_SRC = pathlib.Path(__file__).resolve().parent.parent / "python"

# The compiled extension only (`_core.abi3.so`, `_core.pyd`, ...), not the
# `_core.pyi` stub that's always there.
HAS_CORE = any(p.suffix in {".so", ".pyd"} for p in (PYTHON_SRC / "nsh").glob("_core*"))

if HAS_CORE and str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))
