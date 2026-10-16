"""The capture-store root resolves at the POINT OF USE, never at import.

Slice P2 round 1, refutation A. The three capture tools once baked in a
drive-qualified literal; the first replacement called `Path.home()` at import
and at argparse time, which raises with no user profile, follows a roaming UNC
home onto a share (about 15 GB of captures), and on Linux names an unwritable
`/rsc-first-run`. The helper in core/capture_root.py reads `SystemDrive` on
Windows and the temp dir elsewhere, and nothing calls `Path.home()`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CONSUMERS = (
    "tools/first_run_capture.py",
    "tools/screen_capture.py",
    "tools/capture_supervisor.py",
)


def test_the_helper_honours_system_drive_on_windows() -> None:
    from core.capture_root import default_capture_root

    got = default_capture_root(environ={"SystemDrive": "D:"}, platform="win32")
    assert PureWindowsPath(got) == PureWindowsPath("D:/") / "rsc-first-run"


def test_the_helper_defaults_to_c_without_system_drive() -> None:
    from core.capture_root import default_capture_root

    got = default_capture_root(environ={}, platform="win32")
    assert PureWindowsPath(got) == PureWindowsPath("C:/") / "rsc-first-run"


@pytest.mark.parametrize(
    ("raw", "drive"),
    [
        ("D:", "D:"),
        (" e: ", "e:"),
        ("D:\\", "D:"),
        ("D:/", "D:"),
        ("C", "C:"),
        ("/", "C:"),
        ("D:foo", "C:"),
        ("\\\\srv", "C:"),
        ("\\\\srv" + "\\share", "C:"),
        ("", "C:"),
        ("DD:", "C:"),
    ],
)
def test_the_helper_validates_system_drive(raw: str, drive: str) -> None:
    """Refute round 2 item 1: only a bare drive letter is accepted."""
    from core.capture_root import default_capture_root

    got = PureWindowsPath(default_capture_root(environ={"SystemDrive": raw}, platform="win32"))
    assert got == PureWindowsPath(drive + "/") / "rsc-first-run", (raw, got)
    assert got.is_absolute() and not str(got).startswith("\\\\"), got


def test_the_helper_uses_the_temp_dir_off_windows() -> None:
    from core.capture_root import default_capture_root

    got = default_capture_root(environ={}, platform="linux")
    assert got == Path(tempfile.gettempdir()) / "rsc-first-run"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_no_consumer_calls_path_home(rel: str) -> None:
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    assert "Path.home(" not in text, rel
    assert "default_capture_root" in text, rel


def _fallback_pil(root: Path) -> Path:
    """An empty PIL package, APPENDED to sys.path so a real Pillow still wins.

    tools/screen_capture.py hard-stops at import without Pillow, by design
    (its guarded-import block), and the runtime is stdlib-only, so CI has no
    Pillow. What this test pins is "no Path.home() at import", which has
    nothing to do with PIL: the stub lets that arm run where Pillow is absent
    instead of skipping the one consumer it exists for.
    """
    pkg = root / "PIL"
    pkg.mkdir()
    for name in ("__init__.py", "Image.py", "ImageGrab.py"):
        (pkg / name).write_bytes(b"")
    return root


def test_every_consumer_imports_with_no_user_profile(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in {"USERPROFILE", "HOME", "HOMEDRIVE", "HOMEPATH"}}
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); sys.path.append(sys.argv[2]);"
        "import tools.first_run_capture, tools.screen_capture, "
        "tools.capture_supervisor; print('ok')"
    )
    done = subprocess.run(
        [sys.executable, "-c", code, str(REPO_ROOT), str(_fallback_pil(tmp_path))],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
        check=False, timeout=60,
    )
    assert done.returncode == 0 and done.stdout.strip() == "ok", done.stderr[-800:]
