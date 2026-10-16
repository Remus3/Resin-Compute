"""No tracked file may carry an absolute path into THIS machine's disk layout.

WHY (MAIN ORDERs 1901 PUBPATH and 1925 item f, slice P2). A tracked file goes
public with the repository. A drive-qualified path such as the repo root on
its real drive, its junction spelling on the other drive, the 8.3 short name
of either, or a user-profile directory, names one machine and resolves on no
other. Anything that needs the install root resolves it at RUN TIME
(`Path(__file__).resolve().parents[n]`, `$PSScriptRoot`, the parent of
`$MyInvocation.MyCommand.Path`); prose uses a placeholder such as
`<repo-root>`.

RELATION TO tests/test_machine_identity.py. That guard asks a narrower
question - does an absolute path name a real ACCOUNT - and owns the
placeholder-account allowlist. This guard asks the wider one - does any
drive-letter or drive-mount path appear at all - and reuses that guard's
enumeration (`_tracked_files`, which fails rather than returning an empty
corpus) and its `PLACEHOLDER_ACCOUNTS`, so the two cannot drift apart on what
counts as a fictional account.

WHAT IS EXEMPT, by FIRST PATH SEGMENT with a reason, never by wildcard:
Windows system roots that exist identically on every Windows install and name
nothing about this machine (`ProgramData`, `Program Files`, their 8.3 forms,
`Windows`), an elided path (`C:\\...`), an angle-bracket placeholder, a bare
`Users` directory with no account, and `Users\\<placeholder account>`. The
machine-wide slot bucket under ProgramData is a shared cross-repo contract
(`ops/loop/slots.py`, SHA-pinned, halt clause (b)), which is why that root has
to stay spellable.

THIS FILE BUILDS ITS OFFENDING STRINGS AT RUN TIME (drive letter, colon and
remainder held as separate literals), the shape test_machine_identity.py
records, so it is not on its own allowlist.
"""
from __future__ import annotations

import fnmatch
import functools
import re
from pathlib import Path

import pytest

from tests.test_machine_identity import PLACEHOLDER_ACCOUNTS, _tracked_files

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Files exempt from the sweep, by glob, each with a reason. Keep it short.
ALLOWLIST: dict[str, str] = {
    "ops/fleet_kit/*": (
        "MAIN's fleet kit, vendored byte-for-byte and pinned by "
        "ops/fleet_kit/MANIFEST.json. This tree may never edit it; a defect "
        "is reported to MAIN, so a kit-shipped path must not red this suite."
    ),
}

# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------

#: A drive-qualified path: `X:\`, `X:\\` (a Python literal), `X:/`. The
#: lookbehind keeps `https://` (the `s` before the colon is a letter that is
#: itself preceded by a letter) and `x[:2]` out. The lookahead drops an
#: escape sequence that merely LOOKS like a path - `a:` then backslash-n in a
#: YAML fixture string, `class C:` then backslash-n in a source fixture, with
#: one backslash or two - but not a real segment that starts with n, r or t.
_DRIVE = re.compile(
    r"(?<![A-Za-z0-9_])([A-Za-z]):(?!\\+[nrt](?![A-Za-z0-9_]))(?:\\\\|\\|/)+(?![\\/])(.*)"
)

#: The same drive re-spelled as a mount: `/e/...` (MSYS, Git Bash),
#: `/mnt/e/...` (WSL), `/cygdrive/e/...` (Cygwin). Lower-case drive only,
#: which is what every one of those shells emits.
_MOUNT = re.compile(
    r"(?<![A-Za-z0-9._~:/<>-])(?:/mnt|/cygdrive)?/([a-z])/(?=[A-Za-z0-9_.~$ <-])(.*)"
)

#: First-segment exemptions. Matched against the text right after the
#: separator, case-insensitively, and must end at a segment boundary.
SYSTEM_ROOTS: dict[str, str] = {
    r"ProgramData": "Windows system root, identical on every install.",
    r"Program Files(?: \(x86\))?": "Windows system root, identical on every install.",
    r"PROGRA~\d": "8.3 short name of a Program* system root.",
    r"Windows": "Windows system root, identical on every install.",
    r"\.\.\.": "An elided path: names no directory at all.",
    r"<[^>]*>": "Angle-bracket placeholder; illegal in a real Windows segment.",
    # Fictional fixture segments, by name. Each is a test or doc example that
    # needs a drive-shaped string to exercise Windows path handling.
    r"x|y": "One-letter stand-ins (tests/test_session_hooks.py, test_watch_inbox.py, tests/test_fleet_kit_v9_adoption.py, tools/moon_sync_responder.py).",
    r"nowhere": "A path that must not exist (tests/test_gate_mutation_runner.py).",
    r"fake": "A stubbed `which` result (tests/test_hook_interpreter.py).",
    r"checkout dir": "A space-bearing checkout stand-in (tests/test_moon_sync_responder.py, tests/test_machine_identity.py).",
    r"Genshin Impact": "A probed third-party game install folder in tools/wish_authkey.py _INSTALL_ROOTS; names the game's folder, not this machine.",
}

_BOUNDARY = r"(?=$|[\\/`'\"\s.,;:)\]}])"
_SYSTEM = re.compile(
    "(?:" + "|".join(SYSTEM_ROOTS) + ")" + _BOUNDARY, re.IGNORECASE
)
_USERS = re.compile(
    r"Users" + _BOUNDARY + r"(?:[\\/]+([^\s\\/`'\"]*))?",
    re.IGNORECASE,
)
_TRAILING = ".,;:!?)]}"


def _rest_is_exempt(rest: str) -> bool:
    if not rest or rest[0] in "`'\" \t)]}.,;":
        return True  # a bare drive root names no directory
    if _SYSTEM.match(rest):
        return True
    users = _USERS.match(rest)
    if users:
        account = (users.group(1) or "").rstrip(_TRAILING)
        return not account or account.lower() in PLACEHOLDER_ACCOUNTS
    return False


def machine_paths(line: str) -> list[str]:
    """Every non-exempt absolute machine path in `line`, as a short excerpt."""
    found: list[str] = []
    for pattern in (_DRIVE, _MOUNT):
        for match in pattern.finditer(line):
            if not _rest_is_exempt(match.group(2)):
                found.append(match.group(0)[:60])
    return found


def _allowlisted(name: str) -> bool:
    return any(fnmatch.fnmatch(name, glob) for glob in ALLOWLIST)


@functools.cache
def _sweep() -> tuple[tuple[str, ...], int]:
    offenders: list[str] = []
    scanned = 0
    for name in _tracked_files():
        if _allowlisted(name):
            continue
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            for hit in machine_paths(line):
                offenders.append(f"{name}:{lineno}: {hit}")
    return tuple(offenders), scanned


# ---------------------------------------------------------------------------
# Strings built at run time so this file never spells one contiguously
# ---------------------------------------------------------------------------

def _win(drive: str, sep: str, *parts: str) -> str:
    return drive + ":" + sep + sep.join(parts)


def _mnt(prefix: str, drive: str, *parts: str) -> str:
    return prefix + "/" + drive + "/" + "/".join(parts)


_ROOT_NAME = "Resin" + " Compute"

OFFENDERS: dict[str, str] = {
    "repo root, real drive": _win("E", "\\", _ROOT_NAME, ".githooks"),
    "repo root, junction drive": _win("C", "\\", _ROOT_NAME),
    "repo root, forward slash": _win("E", "/", _ROOT_NAME, "ops"),
    "repo root, python literal": "'" + _win("E", "\\\\", _ROOT_NAME) + "'",
    "repo root, 8.3 spelling": "`" + _win("C", "\\", "RESIN" + "C~1", "ops") + "`",
    "repo root, msys mount": _mnt("", "e", _ROOT_NAME),
    "repo root, wsl mount": _mnt("/mnt", "e", _ROOT_NAME),
    "user profile, real account": _win("C", "\\", "Users", "Admin" + "istrator"),
    "user profile, 8.3 account": _win("C", "/", "Users", "ADMINI" + "~1", "AppData"),
    "user profile, msys": _mnt("", "c", "Users", "Admin" + "istrator"),
    "other drive dir": _win("D", "\\", "dev", "ResinCompute"),
    "machine tool dir": "run " + _win("C", "\\", "Tools", "ops", "x.ps1"),
}

LEGITIMATE: dict[str, str] = {
    "slot bucket": _win("C", "\\", "ProgramData", "lw-loop", "slots"),
    "program files": "`" + _win("C", "\\", "Program Files", "Git") + "`",
    "8.3 programdata": _win("C", "\\", "PROGRA" + "~3", "x"),
    "elided": "`" + _win("C", "\\", "...", "ops", "runtime") + "`",
    "placeholder root": "<repo-root>\\.githooks",
    "drive placeholder": _win("C", "\\", "<clone-dir>"),
    "bare users dir": "29 `" + _win("C", "\\", "Users") + "`",
    "placeholder account": _win("C", "\\", "Users", "<account>", "x"),
    "fixture account": _win("C", "\\", "Users", "someoperator", "x"),
    "yaml escape": "jobs:\\n  a:\\n    steps:\\n",
    "class escape": "class C:\\n",
    "url": "https://example.com/e/x and http://a/b/c",
    "relative": "docs/e/x and ops/loop/control/progress",
    "runtime resolution": "Path(__file__).resolve().parents[1] / $PSScriptRoot",
    "bare drive root": "the root of `" + _win("E", "\\") + "`",
}


@pytest.mark.parametrize("label", sorted(OFFENDERS))
def test_the_predicate_flags_a_machine_path(label: str) -> None:
    assert machine_paths(OFFENDERS[label]), OFFENDERS[label]


@pytest.mark.parametrize("label", sorted(LEGITIMATE))
def test_the_predicate_spares_a_legitimate_neighbour(label: str) -> None:
    assert machine_paths(LEGITIMATE[label]) == [], LEGITIMATE[label]


def test_no_tracked_file_carries_an_absolute_machine_path() -> None:
    offenders, _ = _sweep()
    assert not offenders, (
        "absolute machine paths in tracked files - resolve at run time or "
        "use a placeholder such as <repo-root>:\n" + "\n".join(offenders)
    )


def test_the_sweep_reads_a_realistic_number_of_files() -> None:
    _, scanned = _sweep()
    assert scanned >= 155, scanned


@pytest.mark.parametrize("glob", sorted(ALLOWLIST))
def test_every_allowlist_entry_has_a_reason_and_a_target(glob: str) -> None:
    assert len(ALLOWLIST[glob]) > 40
    assert any(fnmatch.fnmatch(n, glob) for n in _tracked_files()), glob


def test_the_handoff_resolves_the_install_root_at_run_time() -> None:
    text = (REPO_ROOT / "RSC-NEXT-SESSION.txt").read_text(encoding="utf-8")
    assert not [m for line in text.splitlines() for m in machine_paths(line)]


def test_this_file_does_not_need_its_own_allowlist() -> None:
    assert not _allowlisted("tests/test_no_machine_paths.py")
    text = Path(__file__).read_text(encoding="utf-8")
    assert not [m for line in text.splitlines() for m in machine_paths(line)]
