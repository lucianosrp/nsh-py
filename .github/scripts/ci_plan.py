#!/usr/bin/env python3
"""Decide how much of CI a change needs, and say why.

Prints ``mode=<docs|prebuilt|build>`` to $GITHUB_OUTPUT (stdout without it):

- ``docs``: a pull request that only touches docs (Markdown, ``docs/``,
  issue and PR templates). Nothing to build or test.
- ``prebuilt``: a pull request whose Rust is identical to the ``dev-core``
  release's (``tools/source_hash.py`` against its ``manifest.json``): a
  Python, examples or tests change. The tests run on the prebuilt core
  (``tools/fetch_core.py --require-match``), with no Rust build.
- ``build``: everything else, and whenever in doubt: Rust changes, CI or
  packaging changes, pushes to main, an unreachable or older ``dev-core``.

Jobs keep running in every mode and skip their steps instead, so the
required checks always report under their usual names.

Environment: ``GITHUB_EVENT_NAME``, ``GITHUB_BASE_REF``; optional
``NSH_DEV_CORE_URL`` (the release to compare with). Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from source_hash import source_hash  # noqa: E402

DEFAULT_URL = "https://github.com/lucianosrp/nsh-py/releases/download/dev-core"

DOCS = re.compile(
    r"(\.md$|^docs/|^LICENSE|^\.github/ISSUE_TEMPLATE/|^\.github/PULL_REQUEST_TEMPLATE\.md$)"
)
"""Files that change no code: a pull request of only these skips CI's work."""

ALWAYS_BUILD = re.compile(r"(^\.github/workflows/|^\.github/scripts/|^pyproject\.toml$)")
"""Files that change how the core is built or tested: always build."""


def changed_files(base_ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def prebuilt_hash(base_url: str) -> str | None:
    """The ``source_hash`` of the dev-core release, or None if unreachable."""
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/manifest.json", headers={"User-Agent": "nsh-py-ci"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")).get("source_hash")
    except (OSError, ValueError) as exc:
        print(f"Could not read the dev-core manifest: {exc}")
        return None


def plan(event: str, base_ref: str, base_url: str) -> tuple[str, str]:
    """(mode, reason)."""
    if event != "pull_request" or not base_ref:
        return "build", f"a {event or 'non-PR'} run: always the full build"
    files = changed_files(base_ref)
    print("Changed files:", *files, sep="\n  ")
    if files and all(DOCS.search(f) for f in files):
        return "docs", "only docs changed"
    forcing = [f for f in files if ALWAYS_BUILD.search(f)]
    if forcing:
        return "build", f"{forcing[0]} changes how the core is built or tested"
    remote = prebuilt_hash(base_url)
    if remote is None:
        return "build", "the dev-core release isn't readable"
    if remote != source_hash(REPO_ROOT):
        return "build", "the Rust differs from the dev-core release"
    return "prebuilt", "the Rust is identical to the dev-core release"


def main() -> int:
    try:
        mode, reason = plan(
            os.environ.get("GITHUB_EVENT_NAME", ""),
            os.environ.get("GITHUB_BASE_REF", ""),
            os.environ.get("NSH_DEV_CORE_URL", DEFAULT_URL),
        )
    except Exception as exc:  # never fail the plan: fall back to the full build
        mode, reason = "build", f"the plan failed ({exc})"
    line = f"CI mode: **{mode}** ({reason})."
    print(line)
    for var, text in (("GITHUB_OUTPUT", f"mode={mode}\n"), ("GITHUB_STEP_SUMMARY", line + "\n")):
        path = os.environ.get(var)
        if path:
            with open(path, "a", encoding="utf-8") as out:
                out.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
