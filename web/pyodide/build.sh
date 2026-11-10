#!/bin/sh
# Build nsh-py as a Pyodide wheel and copy the examples next to
# the page.
#
# Pyodide 314.0.7 (Python 3.14, emscripten 5.0.3) and stable Rust: the
# toolchain pinned in rust-toolchain.toml, with its emscripten target.
#
# One-time setup (all user-level, outside the repo):
#   uv venv -p 3.14 ~/.cache/nshpy-web/pyb314 && uv pip install -p ~/.cache/nshpy-web/pyb314/bin/python pyodide-build
#   ~/.cache/nshpy-web/pyb314/bin/pyodide xbuildenv install 314.0.7
#   ~/.cache/nshpy-web/pyb314/bin/pyodide xbuildenv install-emscripten
#   rustup target add wasm32-unknown-emscripten   # in the repo: the pinned toolchain
#
# Needs an NSH release with longbridge/nsh#896 (nsh-core's libc on
# emscripten): 0.4.0 doesn't build for the web. See web/README.md.
set -e
cd "$(dirname "$0")/../.."
if grep -q '^nsh-core = "=0.4.0"' Cargo.toml; then
  echo "nsh-core 0.4.0 doesn't build for emscripten (longbridge/nsh#896 is unreleased): see web/README.md." >&2
  exit 1
fi
. "$(ls -d ~/.cache/pyodide-build/.pyodide-xbuildenv-*/314.0.7/emsdk | head -1)/emsdk_env.sh" >/dev/null 2>&1
CARGO_TARGET_DIR="$HOME/.cache/nshpy-web/target314" \
PYO3_CROSS_PYTHON_VERSION=3.14 \
MATURIN_PYEMSCRIPTEN_PLATFORM_VERSION=2026_0 \
RUSTFLAGS="-C link-arg=-sSIDE_MODULE=2" \
  uvx maturin build --release --target wasm32-unknown-emscripten -i python3.14 -o web/pyodide/site
# The page runs these with ?app=examples/<name>.py.
rm -rf web/pyodide/site/examples && cp -r examples web/pyodide/site/examples
echo "Serve with: python3 -m http.server -d web/pyodide/site 8766, then open /?app=examples/poll.py"
