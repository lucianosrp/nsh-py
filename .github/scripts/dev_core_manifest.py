#!/usr/bin/env python3
"""Collect the wheels of a build into one folder and write manifest.json.

    dev_core_manifest.py WHEELS_DIR OUT_DIR

WHEELS_DIR holds one folder per platform, named ``wheels-<key>`` (what
actions/download-artifact makes without merge-multiple), each with a wheel.
OUT_DIR gets every wheel plus manifest.json:

    {"commit": ..., "source_hash": ..., "wheels": {"<key>": "<file>"}}

``commit`` comes from $GITHUB_SHA, ``source_hash`` from tools/source_hash.py
(the same function tools/fetch_core.py uses to compare). Standard library.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from source_hash import source_hash  # noqa: E402


def build_manifest(wheels_dir: Path, out_dir: Path, commit: str, digest: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    wheels: dict[str, str] = {}
    for folder in sorted(wheels_dir.glob("wheels-*")):
        found = sorted(folder.glob("*.whl"))
        if len(found) != 1:
            raise SystemExit(f"{folder}: expected exactly one wheel, found {len(found)}")
        wheels[folder.name.removeprefix("wheels-")] = found[0].name
        shutil.copy2(found[0], out_dir / found[0].name)
    if not wheels:
        raise SystemExit(f"no wheels-* folders in {wheels_dir}")
    manifest = {"commit": commit, "source_hash": digest, "wheels": wheels}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    manifest = build_manifest(
        Path(argv[0]), Path(argv[1]), os.environ["GITHUB_SHA"], source_hash(REPO_ROOT)
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
