"""Tests for tools/source_hash.py, tools/fetch_core.py and tools/run.py.

Pure helpers only: no network, and nothing here depends on this machine.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"nsh_{name}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


source_hash = _load("source_hash")
fetch_core = _load("fetch_core")


# --- source_hash -----------------------------------------------------------


def _make_tree(root: Path) -> None:
    (root / "src" / "elements").mkdir(parents=True)
    (root / "src" / "lib.rs").write_bytes(b"fn a() {}\n")
    (root / "src" / "elements" / "view.rs").write_bytes(b"fn b() {}\n")
    (root / "Cargo.toml").write_bytes(b"[package]\n")
    (root / "Cargo.lock").write_bytes(b"# lock\n")
    (root / "rust-toolchain.toml").write_bytes(b'channel = "1"\n')


def test_source_files_are_sorted_posix_paths(tmp_path):
    _make_tree(tmp_path)
    assert source_hash.source_files(tmp_path) == [
        "Cargo.lock",
        "Cargo.toml",
        "rust-toolchain.toml",
        "src/elements/view.rs",
        "src/lib.rs",
    ]


def test_source_hash_is_stable_and_a_sha256(tmp_path):
    _make_tree(tmp_path)
    first = source_hash.source_hash(tmp_path)
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert source_hash.source_hash(tmp_path) == first


def test_source_hash_changes_with_content_and_path(tmp_path):
    _make_tree(tmp_path)
    before = source_hash.source_hash(tmp_path)
    (tmp_path / "src" / "lib.rs").write_bytes(b"fn a() { 1; }\n")
    assert source_hash.source_hash(tmp_path) != before


def test_source_hash_ignores_crlf(tmp_path):
    _make_tree(tmp_path)
    lf = source_hash.source_hash(tmp_path)
    for path in (tmp_path / "src" / "lib.rs", tmp_path / "Cargo.toml"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert source_hash.source_hash(tmp_path) == lf


def test_source_hash_ignores_unrelated_files(tmp_path):
    _make_tree(tmp_path)
    before = source_hash.source_hash(tmp_path)
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "x.py").write_text("print(1)")
    (tmp_path / "README.md").write_text("hi")
    (tmp_path / "src" / "notes.txt").write_text("not rust")
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "z.rs").write_text("fn z() {}")
    assert source_hash.source_hash(tmp_path) == before


def test_source_hash_of_this_repo_runs_as_a_script():
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "source_hash.py")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == source_hash.source_hash(ROOT)


# --- fetch_core: platform key ---------------------------------------------


@pytest.mark.parametrize(
    ("system", "machine", "key"),
    [
        ("Linux", "x86_64", "linux-x86_64"),
        ("Linux", "aarch64", "linux-aarch64"),
        ("Darwin", "arm64", "macos-arm64"),
        ("Darwin", "x86_64", "macos-x86_64"),
        ("Windows", "AMD64", "windows-x86_64"),
    ],
)
def test_platform_key(system, machine, key):
    assert fetch_core.platform_key(system, machine) == key


def test_platform_key_rejects_unknown_os():
    with pytest.raises(fetch_core.FetchError):
        fetch_core.platform_key("FreeBSD", "amd64")


# --- fetch_core: manifest --------------------------------------------------

MANIFEST = {
    "commit": "0123456789abcdef",
    "source_hash": "f" * 64,
    "wheels": {
        "linux-x86_64": "nsh_py-0.0.1-cp310-abi3-linux_x86_64.whl",
        "macos-arm64": "nsh_py-0.0.1-cp310-abi3-macosx_11_0_arm64.whl",
    },
}


def test_parse_manifest_roundtrip():
    assert fetch_core.parse_manifest(json.dumps(MANIFEST)) == MANIFEST


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({**MANIFEST, "wheels": {}}),
        json.dumps({**MANIFEST, "wheels": {"linux-x86_64": "../evil.whl"}}),
        json.dumps({**MANIFEST, "wheels": {"linux-x86_64": "a.tar.gz"}}),
        json.dumps({k: v for k, v in MANIFEST.items() if k != "commit"}),
        json.dumps({k: v for k, v in MANIFEST.items() if k != "source_hash"}),
    ],
)
def test_parse_manifest_rejects_bad_input(text):
    with pytest.raises(fetch_core.FetchError):
        fetch_core.parse_manifest(text)


def test_pick_wheel():
    assert fetch_core.pick_wheel(MANIFEST, "macos-arm64").endswith("macosx_11_0_arm64.whl")


def test_pick_wheel_lists_what_exists_when_missing():
    with pytest.raises(fetch_core.FetchError, match="linux-x86_64, macos-arm64"):
        fetch_core.pick_wheel(MANIFEST, "windows-x86_64")


# --- fetch_core: extraction ------------------------------------------------


def _fake_wheel(path: Path, core_name: str = "nsh/_core.abi3.so") -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("nsh/__init__.py", "SHOULD NOT BE EXTRACTED")
        zf.writestr(core_name, b"\x7fELF fake core")
        zf.writestr("nsh/primitives/view.py", "nope")
        zf.writestr("../evil/_core.so", b"nope")
        zf.writestr("nsh_py-0.0.1.dist-info/METADATA", "Name: nsh-py")
    return path


def test_extract_core_writes_only_the_extension(tmp_path):
    wheel = _fake_wheel(tmp_path / "w.whl")
    dest = tmp_path / "pkg"
    dest.mkdir()
    written = fetch_core.extract_core(wheel, dest)
    assert [p.name for p in written] == ["_core.abi3.so"]
    assert (dest / "_core.abi3.so").read_bytes() == b"\x7fELF fake core"
    assert [p.name for p in dest.iterdir()] == ["_core.abi3.so"]
    assert not (tmp_path / "evil").exists()


def test_extract_core_handles_windows_pyd(tmp_path):
    wheel = _fake_wheel(tmp_path / "w.whl", core_name="nsh/_core.pyd")
    dest = tmp_path / "pkg"
    dest.mkdir()
    (written,) = fetch_core.extract_core(wheel, dest)
    assert written.name == "_core.pyd"


def test_extract_core_errors_when_there_is_no_extension(tmp_path):
    wheel = tmp_path / "empty.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("nsh/__init__.py", "")
    with pytest.raises(fetch_core.FetchError, match="no nsh/_core"):
        fetch_core.extract_core(wheel, tmp_path)


def test_existing_cores_sees_extensions_only(tmp_path):
    for name in ("_core.abi3.so", "_core.pyd", "_core.pyi", "_element.py", "other.so"):
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in fetch_core.existing_cores(tmp_path)] == [
        "_core.abi3.so",
        "_core.pyd",
    ]


def test_read_marker(tmp_path):
    marker = tmp_path / ".dev-core"
    assert fetch_core.read_marker(marker) is None
    marker.write_text("abc123\n")
    assert fetch_core.read_marker(marker) == "abc123"


# --- run.py ----------------------------------------------------------------


def test_run_py_puts_python_dir_on_the_path(tmp_path):
    script = tmp_path / "probe.py"
    script.write_text("import sys; print(__name__); print(sys.argv[1:]); print(sys.path[1])")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run.py"), str(script), "a", "b"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert out[0] == "__main__"
    assert out[1] == "['a', 'b']"
    assert out[2] == str(ROOT / "python")
