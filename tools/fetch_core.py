#!/usr/bin/env python3
"""Download the prebuilt nsh-py extension so you don't need Rust.

For Python-only contributors: CI keeps a rolling ``dev-core`` prerelease
with wheels built from ``main``. This tool picks the wheel for your OS and
CPU, pulls out the compiled extension (``nsh/_core.*``) and drops it into
``python/nsh/``. After that you run tests and examples straight from the
checkout, with no Rust, no LLVM and no GTK dev packages (see SPRINT.md).
Standard library only; works on Python 3.10+.

Usage:
    python tools/fetch_core.py              # fetch (skips if already current)
    python tools/fetch_core.py --dry-run    # show what would happen
    python tools/fetch_core.py --force      # fetch again, overwrite
    python tools/fetch_core.py --base-url URL

``--base-url`` (or the NSH_DEV_CORE_URL environment variable) replaces the
default release URL. It must serve ``manifest.json`` and the wheel files;
``file:///some/dir`` works too, handy for testing.

The manifest records the commit the core was built from and a hash of the
Rust sources (``tools/source_hash.py``). If your checkout's Rust differs,
the core may not match your checkout: rebase on main, or build locally with
``uv run``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "python" / "nsh"
MARKER = PACKAGE_DIR / ".dev-core"
"""Written after a fetch: the commit of the core in ``python/nsh``."""

DEFAULT_BASE_URL = "https://github.com/lucianosrp/nsh-py/releases/download/dev-core"
URL_ENV = "NSH_DEV_CORE_URL"
TIMEOUT = 30

CORE_MEMBER_RE = re.compile(r"^nsh/(_core[^/]*\.(?:so|pyd|dylib))$")
"""The compiled extension inside a wheel: ``nsh/_core.abi3.so``, ``nsh/_core.pyd``."""


class FetchError(Exception):
    """Something the user can act on; main() prints it and exits 1."""


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no network, no dependence on this machine)
# ---------------------------------------------------------------------------


def platform_key(system: str | None = None, machine: str | None = None) -> str:
    """The manifest key for an OS and CPU: ``linux-x86_64``, ``macos-arm64``...

    Arguments default to this machine (``platform.system()`` / ``.machine()``).
    """
    system = (platform.system() if system is None else system).lower()
    machine = (platform.machine() if machine is None else machine).lower()
    os_name = {"linux": "linux", "darwin": "macos", "windows": "windows"}.get(system)
    if os_name is None:
        raise FetchError(f"no prebuilt core for the operating system {system!r}")
    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, machine)
    if os_name == "linux" and arch == "arm64":
        arch = "aarch64"  # the spelling Linux users know
    return f"{os_name}-{arch}"


def parse_manifest(text: str) -> dict:
    """Parse and check ``manifest.json``: ``{commit, source_hash, wheels}``."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise FetchError(f"manifest.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FetchError("manifest.json should hold a JSON object")
    wheels = data.get("wheels")
    if not isinstance(wheels, dict) or not wheels:
        raise FetchError("manifest.json has no 'wheels' table")
    for key, name in wheels.items():
        if not isinstance(name, str) or not name.endswith(".whl") or "/" in name:
            raise FetchError(f"manifest.json: bad wheel entry for {key!r}: {name!r}")
    for field in ("commit", "source_hash"):
        if not isinstance(data.get(field), str) or not data[field]:
            raise FetchError(f"manifest.json has no {field!r}")
    return data


def pick_wheel(manifest: dict, key: str) -> str:
    """The wheel file name for *key*, or a FetchError that lists the choices."""
    wheels = manifest["wheels"]
    if key not in wheels:
        have = ", ".join(sorted(wheels)) or "none"
        raise FetchError(
            f"no prebuilt core for {key} (the release has: {have}). "
            "Build locally instead: `uv run pytest -q tests` (needs Rust, see SPRINT.md)."
        )
    return wheels[key]


def extract_core(wheel: Path, dest: Path) -> list[Path]:
    """Write the extension module(s) of *wheel* into *dest*; return the paths.

    Only ``nsh/_core.*`` is read out of the zip, nothing else, and only by
    base name, so a hostile archive can't write elsewhere.
    """
    written: list[Path] = []
    with zipfile.ZipFile(wheel) as zf:
        for info in zf.infolist():
            match = CORE_MEMBER_RE.match(info.filename)
            if not match:
                continue
            target = dest / match.group(1)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            if not sys.platform.startswith("win"):
                target.chmod(0o755)
            written.append(target)
    if not written:
        raise FetchError(f"{wheel.name} has no nsh/_core.* extension module")
    return written


def existing_cores(package_dir: Path) -> list[Path]:
    """Extension modules already in *package_dir* (a fetch or a local build)."""
    return sorted(p for p in package_dir.glob("_core*") if CORE_MEMBER_RE.match(f"nsh/{p.name}"))


def read_marker(path: Path = MARKER) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def _open(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "nsh-py-fetch-core"})
    try:
        return urllib.request.urlopen(request, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FetchError(
                f"{url} not found (404). The dev-core release may not exist yet "
                "(it is created after the first push to main), or --base-url is wrong."
            ) from exc
        raise FetchError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise FetchError(
            f"could not reach {url}: {reason}. Are you online? "
            "Without network you can still build locally: `uv run pytest -q tests`."
        ) from exc


def fetch_manifest(base_url: str) -> dict:
    with _open(f"{base_url}/manifest.json") as response:
        return parse_manifest(response.read().decode("utf-8"))


def download(url: str, path: Path) -> None:
    with _open(url) as response, open(path, "wb") as out:
        shutil.copyfileobj(response, out)


def load_source_hash() -> str:
    """tools/source_hash.py, loaded by path (tools/ is not a package)."""
    path = Path(__file__).resolve().parent / "source_hash.py"
    spec = importlib.util.spec_from_file_location("nsh_source_hash", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.source_hash(REPO_ROOT)


def run(base_url: str, force: bool, dry_run: bool, require_match: bool = False) -> int:
    base_url = base_url.rstrip("/")
    key = platform_key()
    print(f"Platform: {key}")
    print(f"Release:  {base_url}")
    manifest = fetch_manifest(base_url)
    wheel_name = pick_wheel(manifest, key)
    commit = manifest["commit"]
    short = commit[:10]
    print(f"Prebuilt core: {wheel_name} (built from commit {short})")

    present = existing_cores(PACKAGE_DIR)
    marker = read_marker()
    if present and marker == commit and not force:
        print(f"python/nsh/ already has the core from {short}. Nothing to do (--force to redo).")
        return 0
    if present:
        names = ", ".join(p.name for p in present)
        if marker:
            print(f"Replacing the fetched core in python/nsh/ ({names}, from {marker[:10]}).")
        else:
            print(f"Note: python/nsh/ has a core that is not from dev-core ({names}),")
            print("      probably a local build. It will be overwritten.")

    local_hash = load_source_hash()
    if local_hash == manifest["source_hash"]:
        print("Rust sources match the prebuilt core.")
    elif require_match:
        raise FetchError(
            f"your checkout's Rust differs from the prebuilt core (commit {short}), "
            "and --require-match was given."
        )
    else:
        print(
            f"\nWarning: your checkout's Rust differs from the prebuilt core (commit {short}).\n"
            "  The core may not match the Python code you have (missing functions, changed\n"
            "  behaviour). Rebase on main (`git pull --rebase origin main`) and fetch again,\n"
            "  or build locally instead (`uv run pytest -q tests`; needs Rust, see SPRINT.md).\n"
        )

    if dry_run:
        print(f"Dry run: would download {base_url}/{wheel_name} and write python/nsh/_core.*")
        return 0

    with tempfile.TemporaryDirectory(prefix="nsh-core-") as tmp:
        wheel = Path(tmp) / wheel_name
        print(f"Downloading {wheel_name} ...")
        download(f"{base_url}/{wheel_name}", wheel)
        for old in present:
            old.unlink()
        written = extract_core(wheel, PACKAGE_DIR)
    MARKER.write_text(commit + "\n", encoding="utf-8")
    for path in written:
        print(f"Wrote {path.relative_to(REPO_ROOT).as_posix()}")
    if key.startswith("linux-"):
        print(
            "Note: the Linux core needs the GTK 4.14+ runtime (no dev packages), "
            "Ubuntu 24.04+ / Debian 13 / Fedora 40+ / Arch."
        )
    print("Done. Run the tests: see 'Setup' in SPRINT.md.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download the prebuilt nsh-py extension into python/nsh/."
    )
    parser.add_argument("--force", action="store_true", help="fetch again even if current")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen")
    parser.add_argument(
        "--require-match",
        action="store_true",
        help="fail instead of warning when the checkout's Rust differs from the core (CI)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(URL_ENV, DEFAULT_BASE_URL),
        help=f"where manifest.json and the wheels are (env {URL_ENV})",
    )
    args = parser.parse_args(argv)
    try:
        return run(args.base_url, args.force, args.dry_run, args.require_match)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
