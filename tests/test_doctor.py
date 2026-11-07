"""Tests for tools/doctor.py: pure helpers, no dependence on this machine."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_doctor():
    path = ROOT / "tools" / "doctor.py"
    spec = importlib.util.spec_from_file_location("nsh_doctor", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


doctor = _load_doctor()


def test_parse_version():
    assert doctor.parse_version("3.13.5") == (3, 13, 5)
    assert doctor.parse_version("glibc 2.39") == (2, 39)
    assert doctor.parse_version("4.14") == (4, 14)
    assert doctor.parse_version("  14.2.1 (a) ") == (14, 2, 1)
    assert doctor.parse_version("4.24.1") == (4, 24, 1)
    assert doctor.parse_version("2") == (2,)


def test_parse_version_rejects_garbage():
    with pytest.raises(ValueError):
        doctor.parse_version("no numbers here")


def test_version_at_least():
    assert doctor.version_at_least((3, 10), (3, 10))
    assert doctor.version_at_least((3, 11, 0), (3, 10))
    assert not doctor.version_at_least((3, 9, 18), (3, 10))
    assert doctor.version_at_least((4, 14, 0), (4, 14))
    assert not doctor.version_at_least((4, 13, 9), (4, 14))
    assert doctor.version_at_least((2, 39), (2, 39))
    assert not doctor.version_at_least((2, 38), (2, 39))
    assert doctor.version_at_least((14,), (14, 0))
    assert doctor.version_at_least((14, 0, 1), (14,))
    assert not doctor.version_at_least((13, 6, 9), (14,))


def test_parse_toolchain_channel():
    text = '[toolchain]\nchannel = "1.99.1"\ncomponents = ["clippy", "rustfmt"]\n'
    assert doctor.parse_toolchain_channel(text) == "1.99.1"
    assert doctor.parse_toolchain_channel("channel = 'nightly'") == "nightly"
    commented = '[toolchain]\n# pin\nchannel = "1.99.1"  # keep\n'
    assert doctor.parse_toolchain_channel(commented) == "1.99.1"


def test_parse_toolchain_channel_missing():
    with pytest.raises(ValueError):
        doctor.parse_toolchain_channel("[toolchain]\ncomponents = []\n")


def test_toolchain_is_listed():
    listing = (
        "stable-x86_64-unknown-linux-gnu (default)\n"
        "1.99.1-x86_64-unknown-linux-gnu (active)\n"
        "nightly-x86_64-unknown-linux-gnu\n"
    )
    assert doctor.toolchain_is_listed("1.99.1", listing)
    assert not doctor.toolchain_is_listed("1.80.0", listing)
    assert doctor.toolchain_is_listed("stable", listing)
    assert doctor.toolchain_is_listed("1.99.1", "1.99.1 (default)\n")
    assert not doctor.toolchain_is_listed("1.99", listing)
    assert not doctor.toolchain_is_listed("1.9", listing)
    assert not doctor.toolchain_is_listed("1.99.1", "")


def test_parse_os_release():
    text = (
        "# comment\n"
        "\n"
        "ID=ubuntu\n"
        'VERSION_ID="22.04"\n'
        "ID_LIKE=debian\n"
        'PRETTY_NAME="Ubuntu 22.04.5 LTS"\n'
    )
    info = doctor.parse_os_release(text)
    assert info["ID"] == "ubuntu"
    assert info["VERSION_ID"] == "22.04"
    assert info["ID_LIKE"] == "debian"
    assert info["PRETTY_NAME"] == "Ubuntu 22.04.5 LTS"


def test_is_too_old_distro():
    assert doctor.is_too_old_distro({"ID": "ubuntu", "VERSION_ID": "22.04"})
    assert doctor.is_too_old_distro({"ID": "debian", "VERSION_ID": "12"})
    assert doctor.is_too_old_distro({"ID": "debian", "VERSION_ID": "12.1"})
    assert not doctor.is_too_old_distro({"ID": "ubuntu", "VERSION_ID": "24.04"})
    assert not doctor.is_too_old_distro({"ID": "arch"})
    assert not doctor.is_too_old_distro({"ID": "fedora", "VERSION_ID": "40"})
    assert not doctor.is_too_old_distro({"ID": "debian", "VERSION_ID": "13"})


def test_old_distro_message():
    msg = doctor.old_distro_message(
        {"ID": "ubuntu", "VERSION_ID": "22.04", "PRETTY_NAME": "Ubuntu 22.04.5 LTS"}
    )
    assert msg is not None
    assert "Ubuntu 22.04.5 LTS is too old" in msg
    assert "Debian 12" in msg
    assert doctor.old_distro_message({"ID": "arch"}) is None


def test_distro_family_and_install_hint():
    assert doctor.distro_family({"ID": "ubuntu"}) == "apt"
    assert doctor.distro_family({"ID": "debian"}) == "apt"
    assert doctor.distro_family({"ID": "linuxmint", "ID_LIKE": "ubuntu debian"}) == "apt"
    assert doctor.distro_family({"ID": "fedora"}) == "dnf"
    assert doctor.distro_family({"ID": "arch"}) == "pacman"
    assert doctor.linux_install_hint({"ID": "ubuntu"}) == doctor.APT_HINT
    assert doctor.linux_install_hint({"ID": "fedora"}) == doctor.DNF_HINT
    assert doctor.linux_install_hint({"ID": "arch"}) == doctor.PACMAN_HINT
    unknown = doctor.linux_install_hint({"ID": "void"})
    assert doctor.APT_HINT in unknown
    assert doctor.DNF_HINT in unknown
    assert doctor.PACMAN_HINT in unknown


def test_summarize_all_ok():
    results = [
        doctor.Result("a", doctor.OK, "yes"),
        doctor.Result("b", doctor.OK, "yes"),
    ]
    msg, code = doctor.summarize(results)
    assert code == 0
    assert msg == "All 2 checks passed."


def test_summarize_warnings_only():
    results = [
        doctor.Result("a", doctor.OK, "yes"),
        doctor.Result("b", doctor.WARN, "uv missing", "install uv"),
    ]
    msg, code = doctor.summarize(results)
    assert code == 0
    assert msg == "All required checks passed (1 warning)."


def test_summarize_blocking():
    results = [
        doctor.Result("a", doctor.FAIL, "no", "fix it"),
        doctor.Result("b", doctor.WARN, "eh"),
        doctor.Result("c", doctor.OK, "yes"),
    ]
    msg, code = doctor.summarize(results)
    assert code == 1
    assert msg == "1 blocking check failed, 1 warning."


def test_summarize_two_blocking_two_warnings():
    results = [
        doctor.Result("a", doctor.FAIL, "no"),
        doctor.Result("b", doctor.FAIL, "no"),
        doctor.Result("c", doctor.WARN, "eh"),
        doctor.Result("d", doctor.WARN, "eh"),
    ]
    msg, code = doctor.summarize(results)
    assert code == 1
    assert msg == "2 blocking checks failed, 2 warnings."


def test_format_result_tags_and_hint_indent():
    ok = doctor.format_result(doctor.Result("Python", doctor.OK, "3.12.0 (>= 3.10)"), color=False)
    assert ok == "[ok] Python: 3.12.0 (>= 3.10)"
    fail = doctor.format_result(
        doctor.Result("git", doctor.FAIL, "not found on PATH", "Install Git"),
        color=False,
    )
    assert fail.startswith("[!!] git: not found on PATH")
    assert "\n     Install Git" in fail
    warn = doctor.format_result(
        doctor.Result("uv", doctor.WARN, "not found on PATH", "Install uv"),
        color=False,
    )
    assert warn.startswith("[--] uv:")
    assert "\n     Install uv" in warn
    colored = doctor.format_result(doctor.Result("x", doctor.OK, "yes"), color=True)
    assert "\033[" in colored
    plain = doctor.format_result(doctor.Result("x", doctor.FAIL, "no", "hint"), color=False)
    assert "\033[" not in plain


def test_pick_python_executable():
    assert doctor.is_python_binary("/usr/bin/python3")
    assert doctor.is_python_binary("/usr/bin/python3.13")
    assert doctor.is_python_binary(r"C:\Python313\python.exe")
    assert not doctor.is_python_binary("/home/me/T3-Code-0.1.6-x86_64.AppImage")
    assert not doctor.is_python_binary("/usr/bin/rustup")
    assert (
        doctor.pick_python_executable(
            [
                "/tmp/T3-Code.AppImage",
                "/usr/bin/python3",
            ]
        )
        == "/usr/bin/python3"
    )
    assert doctor.pick_python_executable(["/usr/bin/python3.12"]) == ("/usr/bin/python3.12")
    assert doctor.pick_python_executable([None, ""]) == "python3"


def test_run_checks_swallows_exceptions():
    def boom():
        raise RuntimeError("nope")

    def ok():
        return doctor.Result("fine", doctor.OK, "yes")

    results = doctor.run_checks([boom, ok])
    assert results[0].status == doctor.WARN
    assert "couldn't check" in results[0].detail
    assert "RuntimeError" in results[0].detail
    assert results[1] == doctor.Result("fine", doctor.OK, "yes")


def test_all_checks_lists_per_os():
    linux = doctor.all_checks("linux")
    darwin = doctor.all_checks("darwin")
    win = doctor.all_checks("win32")
    assert doctor.check_python in linux
    assert doctor.check_glibc in linux
    assert doctor.check_gtk4 in linux
    assert doctor.check_macos_version not in linux
    assert doctor.check_macos_version in darwin
    assert doctor.check_xcode_clt in darwin
    assert doctor.check_glibc not in darwin
    assert doctor.check_windows_version in win
    assert doctor.check_msvc in win
    assert doctor.check_windows_libclang in win
    assert doctor.check_nsh_import in linux
    assert doctor.check_nsh_import in darwin
    assert doctor.check_nsh_import in win
    assert doctor.check_nsh_import is linux[-1]


def test_doctor_smoke_exits_and_summarizes():
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "doctor.py")],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode in (0, 1), proc.stderr
    out = proc.stdout
    assert out.strip(), "doctor produced no stdout"
    assert re.search(r"\[ok\]|\[!!\]|\[--\]", out)
    last = out.strip().splitlines()[-1]
    assert re.search(r"passed|failed|warning", last, re.I)
