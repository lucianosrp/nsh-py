#!/usr/bin/env python3
"""Hash of the Rust sources that decide what the compiled extension does.

CI stores this next to the prebuilt core (the ``dev-core`` release's
``manifest.json``) and ``tools/fetch_core.py`` compares it with the hash of
your checkout, so you know when your Rust differs from the prebuilt one.
Standard library only; works on Python 3.10+.

Usage:
    python tools/source_hash.py            # prints the sha256 hex digest
    python tools/source_hash.py --files    # also lists the hashed files

What is hashed: ``src/**/*.rs``, ``Cargo.toml``, ``Cargo.lock`` and
``rust-toolchain.toml``, sorted by relative path (POSIX separators). For
each file: the path, a NUL byte, then the file bytes with CRLF turned into
LF, so a Windows checkout with autocrlf gives the same digest.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TOP_LEVEL_FILES = ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")
"""Files at the repository root that change the build."""


def source_files(root: Path = REPO_ROOT) -> list[str]:
    """Relative POSIX paths of the files that are hashed, sorted."""
    found = [p.relative_to(root).as_posix() for p in (root / "src").rglob("*.rs")]
    found += [name for name in TOP_LEVEL_FILES if (root / name).is_file()]
    return sorted(found)


def source_hash(root: Path = REPO_ROOT) -> str:
    """The sha256 hex digest over :func:`source_files` (see module doc)."""
    digest = hashlib.sha256()
    for rel in source_files(root):
        data = (root / rel).read_bytes().replace(b"\r\n", b"\n")
        digest.update(rel.encode("utf-8") + b"\0" + data)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--files" in args:
        for rel in source_files():
            print(rel, file=sys.stderr)
    print(source_hash())
    return 0


if __name__ == "__main__":
    sys.exit(main())
