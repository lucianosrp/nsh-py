#!/usr/bin/env python3
"""Setup checker for nsh-py sprint contributors.

Run this before (or at) a PyCon sprint to see what is missing and the
exact command to fix it. Standard library only; works on Python 3.10+
even when uv, Rust, and the compiled extension are not installed.

Usage:
    python tools/doctor.py
    uv run python tools/doctor.py

How to add a check:
    1. Write a small function that returns a Result (name, status, detail,
       optional hint). Raise on unexpected errors — run_checks() catches
       them and reports "couldn't check" instead of crashing.
    2. Append the function to COMMON_CHECKS, LINUX_CHECKS, MACOS_CHECKS,
       WINDOWS_CHECKS, or OPTIONAL_CHECKS at the bottom of this file.
    Status is OK ("[ok]"), FAIL ("[!!]", blocking), or WARN ("[--]").
    Doctor exits 1 if any FAIL is present, else 0. Warnings do not fail.
"""

from __future__ import annotations

import glob
import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLCHAIN_TOML = REPO_ROOT / "rust-toolchain.toml"
PYTHON_SRC = REPO_ROOT / "python"

OK = "ok"
FAIL = "fail"
WARN = "warn"

_TAG = {OK: "[ok]", FAIL: "[!!]", WARN: "[--]"}
_COLOR = {
    OK: "\033[32m",
    FAIL: "\033[31m",
    WARN: "\033[33m",
}
_RESET = "\033[0m"

_CHANNEL_RE = re.compile(
    r"""(?m)^\s*channel\s*=\s*["']([^"']+)["']"""
)
_OS_RELEASE_PATHS = ("/etc/os-release", "/usr/lib/os-release")

APT_HINT = "sudo apt install clang libclang-dev libgtk-4-dev pkg-config"
DNF_HINT = "sudo dnf install clang clang-devel gtk4-devel pkgconf-pkg-config"
PACMAN_HINT = "sudo pacman -S clang gtk4 pkgconf"
TOO_OLD_RELEASES = (
    "Ubuntu 22.04 and Debian 12 are too old "
    "(Ubuntu 24.04+, Debian 13, Fedora 40+, Arch work)."
)
UV_URL = "https://docs.astral.sh/uv/"
RUSTUP_URL = "https://rustup.rs"
GIT_URL = "https://git-scm.com/downloads"

CheckFn = Callable[[], "Result"]


@dataclass(frozen=True)
class Result:
    """Outcome of one check."""

    name: str
    status: str
    detail: str
    hint: str = ""


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no dependence on this machine)
# ---------------------------------------------------------------------------


def parse_version(text: str) -> tuple[int, ...]:
    """Return the first dotted numeric version in *text*.

    ``"glibc 2.39"`` -> ``(2, 39)``; ``"4.14.0"`` -> ``(4, 14, 0)``.
    """
    match = re.search(r"\d+(?:\.\d+)*", text)
    if not match:
        raise ValueError(f"no version number in {text!r}")
    return tuple(int(part) for part in match.group(0).split("."))


def version_at_least(got: Sequence[int], need: Sequence[int]) -> bool:
    """True if *got* is greater than or equal to *need*, padding with zeros."""
    n = max(len(got), len(need))
    left = tuple(got) + (0,) * (n - len(got))
    right = tuple(need) + (0,) * (n - len(need))
    return left >= right


def parse_toolchain_channel(text: str) -> str:
    """Read ``channel = "..."`` from a rust-toolchain.toml body.

    A regex is used instead of tomllib so this runs on Python 3.10.
    """
    match = _CHANNEL_RE.search(text)
    if not match:
        raise ValueError('no channel = "..." in rust-toolchain.toml')
    return match.group(1)


def toolchain_is_listed(channel: str, rustup_list_output: str) -> bool:
    """True if *channel* appears in ``rustup toolchain list`` output."""
    wanted = channel.strip()
    if not wanted:
        return False
    for raw in rustup_list_output.splitlines():
        line = raw.strip()
        if not line:
            continue
        name = line.split()[0]
        if name == wanted or name.startswith(wanted + "-"):
            return True
    return False


def parse_os_release(text: str) -> dict[str, str]:
    """Parse an os-release file into a dict of keys."""
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key] = value.strip().strip("\"'")
    return data


def is_too_old_distro(info: dict[str, str]) -> bool:
    """Ubuntu 22.04 and Debian 12 cannot satisfy glibc 2.39 / GTK 4.14."""
    distro_id = info.get("ID", "").lower().strip()
    version = info.get("VERSION_ID", "").strip()
    if distro_id == "ubuntu":
        return version == "22.04" or version.startswith("22.04.")
    if distro_id == "debian":
        return version == "12" or version.startswith("12.")
    return False


def old_distro_message(info: dict[str, str]) -> str | None:
    """Plain-language 'this release is too old' line, or None."""
    if not is_too_old_distro(info):
        return None
    pretty = info.get("PRETTY_NAME") or (
        f"{info.get('ID', 'this distro')} {info.get('VERSION_ID', '')}".strip()
    )
    return f"{pretty} is too old. {TOO_OLD_RELEASES}"


def distro_family(info: dict[str, str]) -> str:
    """Return ``apt``, ``dnf``, ``pacman``, or ``unknown``."""
    distro_id = info.get("ID", "").lower()
    like = info.get("ID_LIKE", "").lower().split()
    tokens = {distro_id, *like}
    if tokens & {"arch", "archlinux", "manjaro", "endeavouros", "cachyos"}:
        return "pacman"
    if tokens & {"fedora", "rhel", "centos", "rocky", "almalinux"}:
        return "dnf"
    if tokens & {"debian", "ubuntu", "linuxmint", "pop", "raspbian"}:
        return "apt"
    return "unknown"


def linux_install_hint(info: dict[str, str] | None = None) -> str:
    """Distro-family install command for clang, libclang, GTK 4, pkg-config."""
    family = distro_family(info if info is not None else read_os_release())
    if family == "apt":
        return APT_HINT
    if family == "dnf":
        return DNF_HINT
    if family == "pacman":
        return PACMAN_HINT
    return (
        f"Debian/Ubuntu: {APT_HINT}\n"
        f"Fedora: {DNF_HINT}\n"
        f"Arch: {PACMAN_HINT}"
    )


def summarize(results: Sequence[Result]) -> tuple[str, int]:
    """Return ``(summary_line, exit_code)``. Exit 1 if any result is FAIL."""
    n_fail = sum(1 for r in results if r.status == FAIL)
    n_warn = sum(1 for r in results if r.status == WARN)
    n = len(results)
    if n_fail == 0 and n_warn == 0:
        return f"All {n} checks passed.", 0
    if n_fail == 0:
        word = "warning" if n_warn == 1 else "warnings"
        return f"All required checks passed ({n_warn} {word}).", 0
    fail_word = "check" if n_fail == 1 else "checks"
    msg = f"{n_fail} blocking {fail_word} failed"
    if n_warn:
        word = "warning" if n_warn == 1 else "warnings"
        msg += f", {n_warn} {word}"
    return msg + ".", 1


def format_result(result: Result, color: bool = False) -> str:
    """One line plus an indented hint for failures and warnings."""
    tag = _TAG.get(result.status, "[--]")
    if color:
        tag = f"{_COLOR.get(result.status, '')}{tag}{_RESET}"
    lines = [f"{tag} {result.name}: {result.detail}"]
    if result.hint and result.status != OK:
        for hint_line in result.hint.splitlines():
            lines.append(f"     {hint_line}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Environment (I/O)
# ---------------------------------------------------------------------------


def use_color(stream=None) -> bool:
    """Color only on a TTY when NO_COLOR is unset."""
    if os.environ.get("NO_COLOR"):
        return False
    out = sys.stdout if stream is None else stream
    try:
        if not out.isatty():
            return False
    except Exception:
        return False
    if sys.platform == "win32":
        return _enable_windows_ansi()
    return True


def _enable_windows_ansi() -> bool:
    """Turn on VT processing on Windows 10+; skip color if that fails."""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004
        return bool(kernel32.SetConsoleMode(handle, mode.value | enable_vt))
    except Exception:
        return False


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        **kwargs,
    )


def _cmd_version(exe: str) -> str:
    try:
        proc = _run([exe, "--version"])
    except Exception:
        return exe
    text = (proc.stdout or proc.stderr or "").strip().splitlines()
    return text[0] if text else exe


def read_os_release() -> dict[str, str]:
    for path in _OS_RELEASE_PATHS:
        try:
            return parse_os_release(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except OSError:
            continue
    return {}


def _with_old_distro(hint: str) -> str:
    extra = old_distro_message(read_os_release())
    if extra:
        return extra + "\n" + hint
    return hint


def _rustup_hint() -> str:
    if sys.platform == "win32":
        path_note = (
            r"If you just installed it, open a new terminal so PATH includes "
            r"%USERPROFILE%\.cargo\bin"
        )
    else:
        path_note = (
            "If you just installed it, open a new terminal so PATH includes "
            "~/.cargo/bin"
        )
    return f"Install Rust from {RUSTUP_URL}\n{path_note}"


def _check_name(fn: Callable[..., object]) -> str:
    name = getattr(fn, "__name__", "check")
    if name.startswith("check_"):
        name = name[len("check_") :]
    return name.replace("_", " ")


def is_python_binary(path: str) -> bool:
    """True if *path* looks like a Python interpreter, not a wrapper binary."""
    name = path.replace("\\", "/").rstrip("/").split("/")[-1].lower()
    if name.endswith(".appimage"):
        return False
    stem = name[:-4] if name.endswith(".exe") else name
    return stem.startswith("python")


def pick_python_executable(candidates: Sequence[str | None]) -> str:
    """Choose a re-spawnable interpreter from *candidates*.

    Hosts that wrap Python (AppImage, some IDEs) put a non-Python path in
    ``sys.executable``. Prefer a ``python*`` binary so the optional
    ``import nsh`` subprocess can actually start.
    """
    paths = [c for c in candidates if c]
    for path in paths:
        if is_python_binary(path):
            return path
    return paths[0] if paths else "python3"


def python_for_subprocess() -> str:
    return pick_python_executable(
        [
            sys.executable,
            getattr(sys, "_base_executable", None),
            shutil.which("python3"),
            shutil.which("python"),
        ]
    )


# ---------------------------------------------------------------------------
# Checks — all OS
# ---------------------------------------------------------------------------


def check_python() -> Result:
    v = sys.version_info
    detail = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 10):
        return Result("Python", OK, f"{detail} (>= 3.10)")
    return Result(
        "Python",
        FAIL,
        f"{detail} is too old (need >= 3.10)",
        "Install Python 3.10 or newer from https://www.python.org/downloads/",
    )


def check_uv() -> Result:
    path = shutil.which("uv")
    if path:
        return Result("uv", OK, _cmd_version("uv"))
    return Result(
        "uv",
        WARN,
        "not found on PATH",
        f"Install uv: {UV_URL}  (optional, but the sprint uses it)",
    )


def check_git() -> Result:
    path = shutil.which("git")
    if path:
        return Result("git", OK, path)
    return Result(
        "git",
        FAIL,
        "not found on PATH",
        f"Install Git from {GIT_URL}",
    )


def check_rustup() -> Result:
    path = shutil.which("rustup")
    if path:
        return Result("rustup", OK, path)
    return Result("rustup", FAIL, "not found on PATH", _rustup_hint())


def check_cargo() -> Result:
    path = shutil.which("cargo")
    if path:
        return Result("cargo", OK, _cmd_version("cargo"))
    hint = _rustup_hint()
    if shutil.which("rustup"):
        hint = (
            "cargo should come with rustup. Is ~/.cargo/bin (or "
            r"%USERPROFILE%\.cargo\bin) on PATH?"
            "\n" + hint
        )
    return Result("cargo", FAIL, "not found on PATH", hint)


def check_rust_toolchain() -> Result:
    if not TOOLCHAIN_TOML.is_file():
        return Result(
            "Rust toolchain",
            WARN,
            f"{TOOLCHAIN_TOML.name} not found in the repo root",
        )
    channel = parse_toolchain_channel(
        TOOLCHAIN_TOML.read_text(encoding="utf-8")
    )
    rustup = shutil.which("rustup")
    if not rustup:
        return Result(
            "Rust toolchain",
            WARN,
            f"need {channel}, but rustup is missing so it could not be listed",
            f"Install rustup from {RUSTUP_URL}; it fetches {channel} on the "
            "first build (from rust-toolchain.toml).",
        )
    proc = _run(["rustup", "toolchain", "list"])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "rustup failed").strip().splitlines()
        last = err[-1] if err else "rustup toolchain list failed"
        return Result(
            "Rust toolchain",
            WARN,
            f"couldn't list toolchains (need {channel}): {last}",
            f"That's fine: rustup installs {channel} on the first build.",
        )
    if toolchain_is_listed(channel, proc.stdout):
        return Result("Rust toolchain", OK, f"{channel} is installed")
    return Result(
        "Rust toolchain",
        WARN,
        f"{channel} is not installed yet",
        f"That's fine: rustup installs {channel} on the first build "
        "(from rust-toolchain.toml).",
    )


def check_nsh_import() -> Result:
    """Optional: is the built extension importable from this checkout?"""
    env = os.environ.copy()
    pythonpath = str(PYTHON_SRC)
    existing = env.get("PYTHONPATH")
    if existing:
        pythonpath = pythonpath + os.pathsep + existing
    env["PYTHONPATH"] = pythonpath
    try:
        proc = subprocess.run(
            [
                python_for_subprocess(),
                "-c",
                "import nsh; print(getattr(nsh, '__version__', 'ok'))",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=env,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return Result(
            "nsh import",
            WARN,
            "import nsh timed out",
            "Run `uv run pytest -q tests` once to build the extension.",
        )
    if proc.returncode == 0:
        ver = (proc.stdout or "").strip().splitlines()
        extra = ver[-1] if ver else "ok"
        return Result("nsh import", OK, f"import nsh succeeded ({extra})")
    if proc.returncode < 0:
        detail = f"interpreter crashed (signal {-proc.returncode})"
    else:
        err = (proc.stderr or proc.stdout or "import failed").strip().splitlines()
        detail = err[-1] if err else "import failed"
    return Result(
        "nsh import",
        WARN,
        f"not importable yet ({detail})",
        "Run `uv run pytest -q tests` once to build the extension.",
    )


# ---------------------------------------------------------------------------
# Checks — Linux
# ---------------------------------------------------------------------------


def _glibc_version_string() -> str | None:
    raw = None
    try:
        raw = os.confstr("CS_GNU_LIBC_VERSION")
    except (ValueError, OSError, AttributeError):
        raw = None
    if raw:
        return raw
    try:
        lib, ver = platform.libc_ver()
    except Exception:
        return None
    if lib and ver:
        return f"{lib} {ver}"
    return None


def check_glibc() -> Result:
    raw = _glibc_version_string()
    if not raw:
        return Result(
            "glibc",
            FAIL,
            "GNU libc not detected",
            _with_old_distro(
                "Need glibc 2.39+ (Ubuntu 24.04+, Debian 13, Fedora 40+, Arch)."
            ),
        )
    got = parse_version(raw)
    shown = ".".join(str(p) for p in got)
    if version_at_least(got, (2, 39)):
        return Result("glibc", OK, f"{shown} (>= 2.39)")
    return Result(
        "glibc",
        FAIL,
        f"{shown} is too old (need >= 2.39)",
        _with_old_distro(
            "Need glibc 2.39+ (Ubuntu 24.04+, Debian 13, Fedora 40+, Arch)."
        ),
    )


def check_gtk4() -> Result:
    pkg = shutil.which("pkg-config")
    version_text = None
    if pkg:
        proc = _run(["pkg-config", "--modversion", "gtk4"])
        if proc.returncode == 0:
            version_text = (proc.stdout or "").strip()
    runtime = None
    try:
        from ctypes.util import find_library

        runtime = find_library("gtk-4")
    except Exception:
        runtime = None

    pkgs = linux_install_hint()
    if version_text:
        got = parse_version(version_text)
        if version_at_least(got, (4, 14)):
            return Result("GTK 4", OK, f"{version_text} (>= 4.14)")
        return Result(
            "GTK 4",
            FAIL,
            f"{version_text} is too old (need >= 4.14)",
            _with_old_distro(pkgs),
        )

    if runtime:
        missing = "pkg-config" if not pkg else "the GTK 4 -dev package"
        return Result(
            "GTK 4",
            FAIL,
            f"{missing} missing (runtime found at {runtime})",
            _with_old_distro(
                "The GTK 4 runtime is installed, but headers are not. "
                "Install the -dev package so pkg-config can find gtk4.\n"
                + pkgs
            ),
        )
    why = "pkg-config not found" if not pkg else "pkg-config did not find gtk4"
    return Result(
        "GTK 4",
        FAIL,
        f"not found ({why})",
        _with_old_distro(f"GTK 4.14+ is required.\n{pkgs}"),
    )


def check_clang() -> Result:
    path = shutil.which("clang")
    if path:
        return Result("clang", OK, path)
    return Result(
        "clang",
        FAIL,
        "not found on PATH",
        linux_install_hint(),
    )


def _find_libclang_linux() -> str | None:
    try:
        from ctypes.util import find_library

        found = find_library("clang")
        if found:
            return found
    except Exception:
        pass
    llvm_config = shutil.which("llvm-config")
    if llvm_config:
        try:
            proc = _run([llvm_config, "--libdir"])
        except Exception:
            proc = None
        if proc is not None and proc.returncode == 0:
            libdir = (proc.stdout or "").strip()
            matches = sorted(glob.glob(os.path.join(libdir, "libclang*.so*")))
            if matches:
                return matches[0]
    patterns = (
        "/usr/lib*/llvm-*/lib/libclang*.so*",
        "/usr/lib/x86_64-linux-gnu/libclang*.so*",
        "/usr/lib64/libclang*.so*",
        "/usr/lib/libclang*.so*",
    )
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


def check_libclang() -> Result:
    found = _find_libclang_linux()
    if found:
        return Result("libclang", OK, found)
    return Result(
        "libclang",
        FAIL,
        "not found",
        "Need libclang for bindgen.\n" + linux_install_hint(),
    )


# ---------------------------------------------------------------------------
# Checks — macOS
# ---------------------------------------------------------------------------


def check_macos_version() -> Result:
    ver = platform.mac_ver()[0]
    if not ver:
        return Result("macOS", WARN, "couldn't read the macOS version")
    got = parse_version(ver)
    if version_at_least(got, (14,)):
        return Result("macOS", OK, f"{ver} (>= 14)")
    return Result(
        "macOS",
        FAIL,
        f"{ver} is too old (need >= 14)",
        "nsh-py needs macOS 14 or newer.",
    )


def check_xcode_clt() -> Result:
    proc = _run(["xcode-select", "-p"])
    path = (proc.stdout or "").strip()
    if proc.returncode == 0 and path:
        return Result("Xcode Command Line Tools", OK, path)
    return Result(
        "Xcode Command Line Tools",
        FAIL,
        "not installed",
        "Run: xcode-select --install",
    )


# ---------------------------------------------------------------------------
# Checks — Windows
# ---------------------------------------------------------------------------


def check_windows_version() -> Result:
    win = sys.getwindowsversion()  # type: ignore[attr-defined]
    major, build = win.major, win.build
    detail = f"{major}.{win.minor} build {build}"
    if major > 10 or (major == 10 and build >= 17763):
        return Result("Windows", OK, f"{detail} (>= 10 build 17763 / 1809)")
    return Result(
        "Windows",
        FAIL,
        f"{detail} is too old (need 10 build 17763 / 1809+)",
        "nsh-py needs Windows 10 version 1809 or newer.",
    )


def _vswhere_path() -> Path:
    pf86 = os.environ.get("ProgramFiles(x86)")
    if not pf86:
        pf86 = os.environ.get("ProgramFiles", r"C:\Program Files")
    return (
        Path(pf86)
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe"
    )


def check_msvc() -> Result:
    vswhere = _vswhere_path()
    hint = (
        "Install Visual Studio Build Tools with the C++ workload: "
        "https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    )
    if not vswhere.is_file():
        return Result(
            "MSVC build tools",
            FAIL,
            f"vswhere.exe not found at {vswhere}",
            hint,
        )
    proc = _run(
        [
            str(vswhere),
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ]
    )
    paths = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if paths:
        return Result("MSVC build tools", OK, paths[0])
    return Result(
        "MSVC build tools",
        FAIL,
        "Visual C++ tools not installed",
        hint,
    )


def _windows_libclang_path() -> str | None:
    env = os.environ.get("LIBCLANG_PATH")
    if env:
        p = Path(env)
        if p.is_file():
            return str(p)
        for candidate in (p / "libclang.dll", p / "bin" / "libclang.dll"):
            if candidate.is_file():
                return str(candidate)
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    default = Path(program_files) / "LLVM" / "bin" / "libclang.dll"
    if default.is_file():
        return str(default)
    hardcoded = Path(r"C:\Program Files\LLVM\bin\libclang.dll")
    if hardcoded.is_file():
        return str(hardcoded)
    return None


def check_windows_libclang() -> Result:
    found = _windows_libclang_path()
    if found:
        return Result("libclang", OK, found)
    return Result(
        "libclang",
        FAIL,
        "not found",
        "Install LLVM: winget install LLVM.LLVM\n"
        r"Then set LIBCLANG_PATH to C:\Program Files\LLVM\bin",
    )


# ---------------------------------------------------------------------------
# Registry — append a function here to add a check
# ---------------------------------------------------------------------------


COMMON_CHECKS: list[CheckFn] = [
    check_python,
    check_uv,
    check_git,
    check_rustup,
    check_cargo,
    check_rust_toolchain,
]

LINUX_CHECKS: list[CheckFn] = [
    check_glibc,
    check_gtk4,
    check_clang,
    check_libclang,
]

MACOS_CHECKS: list[CheckFn] = [
    check_macos_version,
    check_xcode_clt,
]

WINDOWS_CHECKS: list[CheckFn] = [
    check_windows_version,
    check_msvc,
    check_windows_libclang,
]

OPTIONAL_CHECKS: list[CheckFn] = [
    check_nsh_import,
]


def all_checks(plat: str | None = None) -> list[CheckFn]:
    """Checks for *plat* (``sys.platform`` by default)."""
    system = sys.platform if plat is None else plat
    checks = list(COMMON_CHECKS)
    if system.startswith("linux"):
        checks.extend(LINUX_CHECKS)
    elif system == "darwin":
        checks.extend(MACOS_CHECKS)
    elif system == "win32":
        checks.extend(WINDOWS_CHECKS)
    checks.extend(OPTIONAL_CHECKS)
    return checks


def run_checks(check_fns: Sequence[CheckFn] | None = None) -> list[Result]:
    """Run each check, catching exceptions so doctor never crashes."""
    results: list[Result] = []
    fns = all_checks() if check_fns is None else check_fns
    for fn in fns:
        try:
            results.append(fn())
        except Exception as exc:
            results.append(
                Result(
                    _check_name(fn),
                    WARN,
                    f"couldn't check ({type(exc).__name__}: {exc})",
                )
            )
    return results


def main(argv: list[str] | None = None) -> int:
    del argv  # no flags; kept so tests can call main([])
    results = run_checks()
    color = use_color()
    for result in results:
        print(format_result(result, color=color))
    summary, code = summarize(results)
    print()
    print(summary)
    return code


if __name__ == "__main__":
    sys.exit(main())
