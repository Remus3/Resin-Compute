"""Where the first-run capture store lives, resolved at the point of use.

The store holds account-bearing bytes (UIDs, registry tokens) and must sit
OUTSIDE this repository. It is resolved when a tool actually needs it, never
at import: no drive letter is baked into a tracked file, and nothing here calls
`Path.home()`, which raises with no user profile and on a roaming profile
resolves to a network share.

Windows: the system drive's root (`SystemDrive`, default `C:`) plus
`rsc-first-run`. Elsewhere: the platform temp dir plus `rsc-first-run`.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath

CAPTURE_DIR_NAME = "rsc-first-run"


def default_capture_root(
    environ: Mapping[str, str] | None = None, platform: str | None = None
) -> Path:
    """The default capture root for this host. Pure apart from its inputs."""
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    if plat == "win32":
        drive = (env.get("SystemDrive") or "C:").rstrip("\\/")
        win = PureWindowsPath(drive + "\\") / CAPTURE_DIR_NAME
        return Path(str(win))
    return Path(tempfile.gettempdir()) / CAPTURE_DIR_NAME
