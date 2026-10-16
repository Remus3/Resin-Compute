"""No tracked file may carry an absolute path into THIS machine's disk layout.

WHY (MAIN ORDERs 1901 PUBPATH and 1925 item f, slice P2). A tracked file goes
public with the repository. A drive-qualified path such as the repo root on
its real drive, its junction spelling on the other drive, the 8.3 short name
of either, a user-profile or home directory, or a UNC share, names one machine
and resolves on no other. Anything that needs the install root resolves it at
RUN TIME (`Path(__file__).resolve().parents[n]`, `$PSScriptRoot`, the parent
of `$MyInvocation.MyCommand.Path`); prose uses a placeholder such as
`<repo-root>`.

SHAPES CAUGHT. A drive path in any separator form (backslash, doubled
backslash as in a Python literal, forward slash), whatever precedes the drive
letter except another letter; a drive mount `/c/`, `/C/`, `//c/`,
`/mnt/c/`, `/cygdrive/c/` in either case; `/home/<account>/` and
`/Users/<account>/`; a UNC share (two backslashes or two slashes, a host, a
share); and the repo
name after a drive in a drive-relative or percent-encoded spelling.

EXEMPTIONS - the complete list, each with its reason:

1. A bare drive root followed by nothing path-like. Names no directory.
2. An angle-bracket placeholder segment (`<repo-root>`, `<drive>`): angle
   brackets are illegal in a real Windows path segment.
3. An elided path, a first segment of exactly three dots: names no directory.
4. A path that stays inside a Windows system root - first segment exactly
   `ProgramData`, `Program Files`, `Program Files (x86)`, `PROGRA~1` to
   `PROGRA~3` or `Windows`, never a dotted neighbour such as `Windows.old` -
   and carries no user segment and no repo-name segment. Identical on every
   Windows install. The machine-wide slot bucket under ProgramData is a shared
   cross-repo contract (`ops/loop/slots.py`, SHA-pinned, halt clause (b)).
5. A bare `Users` directory with no account, or `Users` plus an account named
   in `PLACEHOLDER_ACCOUNTS` of tests/test_machine_identity.py (`x`,
   `<account>`, `someoperator`), and the same accounts under `/home/` and
   `/Users/`.
6. `FAKE_PATHS` below, matched as WHOLE paths (separators normalised), never
   by first segment: invented fixture paths that must be drive-shaped to
   exercise Windows path handling, plus the game-install probe in
   tools/wish_authkey.py.
7. `FAKE_UNC_HOSTS` below: invented share hosts in UNC fixtures.
8. Files matching `ALLOWLIST` (the vendored fleet kit only).

KNOWN GAPS, stated rather than hidden: a percent-encoded or drive-relative
path is caught only when it names the repo; a binary file (one holding a NUL
byte) is not swept, and an arm below pins that every such file is an image.

RELATION TO tests/test_machine_identity.py. That guard asks the narrower
question - does a path name a real ACCOUNT - and owns the placeholder-account
list. This guard reuses its enumeration (`_tracked_files`, which fails rather
than returning an empty corpus) and its `PLACEHOLDER_ACCOUNTS`.

THIS FILE BUILDS ITS OFFENDING STRINGS AT RUN TIME, so it is not allowlisted.
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

#: Whole fake paths, separators normalised to `/`. Exemption 6.
FAKE_PATHS: dict[str, str] = {
    "C:/x": "one-letter stand-in (test_moon_sync_responder, test_session_hooks, "
            "tools/moon_sync_responder.py, a ledger archive line)",
    "C:/y": "paired stand-in (tests/test_watch_inbox.py)",
    "C:/x/y.txt": "raw-error fixture (tests/test_session_hooks.py)",
    "D:/x/pytools/watch.py": "planted absolute hook path (tests/test_session_hooks.py)",
    "E:/x/fleet_done.py": "planted hook command (tests/test_fleet_kit_v9_adoption.py)",
    "C:/nowhere": "a path that must not exist (tests/test_gate_mutation_runner.py)",
    "C:/fake/git.exe": "stubbed `which` result (tests/test_hook_interpreter.py)",
    "C:/checkout dir": "space-bearing checkout stand-in (test_moon_sync_responder, "
                       "test_machine_identity, tools/moon_sync_responder.py)",
    "/c/x/frame.png": "msys-mount locator fixture (tests/test_provenance.py)",
    "D:/Genshin Impact/Genshin Impact game": (
        "a probed third-party game install folder in tools/wish_authkey.py "
        "_INSTALL_ROOTS; names the game's own folder, not this machine"
    ),
}

#: Invented UNC hosts. Exemption 7.
FAKE_UNC_HOSTS: dict[str, str] = {
    "server": "UNC locator fixture (tests/test_provenance.py)",
    "fileserver": "planted UNC hook path (tests/test_session_hooks.py)",
    "localhost": "loopback admin-share alias of a drive (conftest.py, "
                 "tests/test_headless_runner*.py); names no machine",
}

# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------

#: A character that continues a path. Used to tell an escape sequence that
#: merely LOOKS like a path (`a:` then backslash-n, followed by a space or a
#: quote) from a real segment that starts with n, r or t.
_PATH_CHAR = r"[A-Za-z0-9_\\/.~-]"

_DRIVE = re.compile(
    r"(?<![A-Za-z])([A-Za-z]):"
    r"(?!\\+[nrt](?!" + _PATH_CHAR + r"))"
    r"(?:\\\\|\\|/)+(?![\\/])(.*)"
)

_MOUNT = re.compile(
    r"(?<![A-Za-z0-9._~:<>/\\-])(?:/mnt|/cygdrive)?/{1,2}([A-Za-z])/"
    r"(?=[A-Za-z0-9_.~$ <-])(.*)",
    re.IGNORECASE,
)

_POSIX_HOME = re.compile(
    r"(?<![A-Za-z0-9._~:/<>\\-])/(?:home|Users)/([^\s\\/`'\"]+)", re.IGNORECASE
)

#: Two backslashes, host, ONE backslash (prose), or four, host, two (a Python
#: literal). Two-then-two is an escaped single-backslash path in source, such
#: as an environment-variable path, and is not a share.
_HOST = r"([A-Za-z0-9][A-Za-z0-9._$-]*)"
_UNC = re.compile(
    r"(?<![\\A-Za-z0-9])\\{2}" + _HOST + r"\\(?![\\\s])"
    r"|(?<![\\A-Za-z0-9])\\{4}" + _HOST + r"\\{2}(?![\\\s])"
    r"|(?<![:/A-Za-z0-9\\])//([A-Za-z0-9][A-Za-z0-9.-]*)/[^\s/`'\"]"
)

_REPO_NAME = re.compile(
    r"(?<![A-Za-z])[A-Za-z](?::|%3A)(?:[\\/]|%5C|%2F)*resin[ _-]?compute",
    re.IGNORECASE,
)

_FORBIDDEN_SEGMENT = re.compile(
    r"(?:^|[\\/])(?:users|documents and settings|resin[ _-]?compute|resinc~\d|"
    r"rc-worktrees)(?:$|[\\/])",
    re.IGNORECASE,
)

_SYSTEM_ROOT = re.compile(
    r"(?:ProgramData|Program Files(?: \(x86\))?|PROGRA~[1-3]|Windows)"
    r"(?=$|[\\/`'\" ,;:)\]}]|\.(?:$|\s))",
    re.IGNORECASE,
)

_TOKEN_END = re.compile(r"[`'\"<>|*?)\],;]")
_TRAILING = ".,;:!?)]}"


def _token(rest: str) -> str:
    """The path text after the drive separator, up to the first delimiter."""
    end = _TOKEN_END.search(rest)
    return rest[: end.start()] if end else rest


def _segments(token: str) -> list[str]:
    return [s for s in re.split(r"[\\/]+", token) if s]


def _is_fake(prefix: str, rest: str) -> bool:
    norm = prefix + re.sub(r"[\\/]+", "/", rest)
    for fake in FAKE_PATHS:
        if norm.lower().startswith(fake.lower()):
            after = norm[len(fake):len(fake) + 1]
            if not after or not re.match(_PATH_CHAR, after):
                return True
    return False


def _rest_is_exempt(prefix: str, rest: str) -> bool:
    if not rest or rest[0] in "`'\" \t)]},;":
        return True  # 1: a bare drive root names no directory
    if _is_fake(prefix, rest):
        return True  # 6
    token = _token(rest)
    if rest.startswith("<"):
        return not _FORBIDDEN_SEGMENT.search(rest[rest.find(">") + 1:].split(" ")[0])
    if token.startswith("...") and (len(token) == 3 or token[3] in "\\/"):
        return not _FORBIDDEN_SEGMENT.search(token)  # 3
    if _SYSTEM_ROOT.match(rest):
        return not _FORBIDDEN_SEGMENT.search(token)  # 4
    segs = _segments(token.split(" ")[0]) if token else []
    if segs and segs[0].lower() in ("users", "documents and settings"):
        account = segs[1].rstrip(_TRAILING) if len(segs) > 1 else ""
        return not account or account.lower() in PLACEHOLDER_ACCOUNTS  # 5
    return False


def machine_paths(line: str) -> list[str]:
    """Every non-exempt absolute machine path in `line`, as a short excerpt."""
    found: list[str] = []
    for match in _DRIVE.finditer(line):
        if not _rest_is_exempt(match.group(1) + ":/", match.group(2)):
            found.append(match.group(0)[:60])
    for match in _MOUNT.finditer(line):
        if not _rest_is_exempt("/" + match.group(1).lower() + "/", match.group(2)):
            found.append(match.group(0)[:60])
    for match in _POSIX_HOME.finditer(line):
        account = match.group(1).rstrip(_TRAILING)
        if account.lower() not in PLACEHOLDER_ACCOUNTS and not account.startswith("<"):
            found.append(match.group(0)[:60])
    for match in _UNC.finditer(line):
        host = match.group(1) or match.group(2) or match.group(3)
        if host.lower() not in FAKE_UNC_HOSTS:
            found.append(match.group(0)[:60])
    for match in _REPO_NAME.finditer(line):
        found.append(match.group(0)[:60])
    return found


def _allowlisted(name: str) -> bool:
    return any(fnmatch.fnmatch(name, glob) for glob in ALLOWLIST)


@functools.cache
def _sweep() -> tuple[tuple[str, ...], int, tuple[str, ...]]:
    """(offenders, files scanned, binary files not scanned)."""
    offenders: list[str] = []
    binary: list[str] = []
    scanned = 0
    for name in _tracked_files():
        if _allowlisted(name):
            continue
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\x00" in data:
            binary.append(name)
            continue
        text = data.decode("utf-8", errors="replace")
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            for hit in machine_paths(line):
                offenders.append(f"{name}:{lineno}: {hit}")
    return tuple(offenders), scanned, tuple(binary)


# ---------------------------------------------------------------------------
# Strings built at run time so this file never spells one contiguously
# ---------------------------------------------------------------------------

B = "\\"


def _win(drive: str, sep: str, *parts: str) -> str:
    return drive + ":" + sep + sep.join(parts)


def _mnt(prefix: str, drive: str, *parts: str) -> str:
    return prefix + "/" + drive + "/" + "/".join(parts)


_ROOT_NAME = "Resin" + " Compute"
_ACCT = "Admin" + "istrator"

OFFENDERS: dict[str, str] = {
    "repo root, real drive": _win("E", B, _ROOT_NAME, ".githooks"),
    "repo root, junction drive": _win("C", B, _ROOT_NAME),
    "repo root, forward slash": _win("E", "/", _ROOT_NAME, "ops"),
    "repo root, python literal": "'" + _win("E", B + B, _ROOT_NAME) + "'",
    "repo root, 8.3 spelling": "`" + _win("C", B, "RESIN" + "C~1", "ops") + "`",
    "repo root, msys mount": _mnt("", "e", _ROOT_NAME),
    "repo root, msys upper": _mnt("", "E", _ROOT_NAME, "ops"),
    "repo root, msys double slash": "/" + _mnt("", "e", _ROOT_NAME),
    "repo root, wsl mount": _mnt("/mnt", "e", _ROOT_NAME),
    "repo root, underscore prefix": "x_" + _win("E", B, _ROOT_NAME),
    "repo root, digit prefix": "9" + _win("E", B, _ROOT_NAME),
    "repo root, drive relative": "E:" + _ROOT_NAME,
    "repo root, percent encoded": "E%3A%5C" + _ROOT_NAME,
    "repo root, file url": "file:///E:/" + _ROOT_NAME.replace(" ", "%20"),
    "escape lookalike r then seg": _win("E", B, "r", _ROOT_NAME),
    "escape lookalike t then seg": _win("E", B, "t", "x"),
    "user profile, real account": _win("C", B, "Users", _ACCT),
    "user profile, 8.3 account": _win("C", "/", "Users", "ADMINI" + "~1", "AppData"),
    "user profile, public": _win("C", B, "Users", "Public", "x"),
    "user profile, msys": _mnt("", "c", "Users", _ACCT),
    "user profile, msys upper": _mnt("", "C", "Users", _ACCT, "x"),
    "posix home": "/home/" + "moon" + "beam/x",
    "mac users": "/Users/" + "moon" + "beam/x",
    "unc host backslash": B + B + "DESKTOP-AB12CD" + B + "share" + B + "x",
    "unc host python literal": B * 4 + "DESKTOP-AB12CD" + B * 2 + "share",
    "unc host forward slash": " /" + "/DESKTOP-AB12CD/share/x",
    "windows dot neighbour": _win("E", B, "Windows.old", _ROOT_NAME),
    "programdata holding the repo": _win("C", B, "ProgramData", _ROOT_NAME, "x"),
    "program files holding a user": _win("C", B, "Program Files", "Users", _ACCT),
    "fake prefix extended": _win("E", B, "x", _ROOT_NAME),
    "fake game folder extended": _win("E", B, "Genshin Impact", "Users", _ACCT),
    "other drive dir": _win("D", B, "dev", "ResinCompute"),
    "machine tool dir": "run " + _win("C", B, "Tools", "ops", "x.ps1"),
    "temp dir": _win("C", B, "Temp", "x"),
    "8.3 documents": _win("C", B, "DOCUME" + "~1", "x"),
    "elided then repo": "`" + _win("C", B, "...", _ROOT_NAME) + "`",
}

LEGITIMATE: dict[str, str] = {
    "slot bucket": _win("C", B, "ProgramData", "lw-loop", "slots"),
    "program files": "`" + _win("C", B, "Program Files", "Git") + "`",
    "program files gh": '"' + _win("C", "/", "Program Files", "GitHub CLI", "gh.exe") + '"',
    "8.3 programdata": _win("C", B, "PROGRA" + "~3", "x"),
    "elided": "`" + _win("C", B, "...", "ops", "runtime") + "`",
    "placeholder root": "<repo-root>" + B + ".githooks",
    "drive placeholder": "<drive>:/rsc-wt-atomic",
    "drive placeholder segment": _win("C", B, "<clone-dir>"),
    "bare users dir": "29 `" + _win("C", B, "Users") + "`",
    "placeholder account": _win("C", B, "Users", "<account>", "x"),
    "fixture account": _win("C", B, "Users", "someoperator", "x"),
    "fixture account posix": "/home/someoperator/x",
    "fake whole path": '"' + _win("C", "/", "checkout dir") + '"',
    "fake whole path python": "'" + _win("C", B * 2, "x", "y.txt") + "'",
    "fake game folder": '"' + _win("D", "/", "Genshin Impact", "Genshin Impact game") + '",',
    "fake unc": B * 2 + "server" + B + "share" + B + "frame.png",
    "device prefix": B * 2 + "?" + B + "C:" + B + "...",
    "yaml escape": "jobs:\\n  a:\\n    steps:\\n",
    "class escape": "class C:\\n",
    "trailing escape": "E:\\t",
    "url": "https://example.com/e/x and http://a/b/c",
    "relative": "docs/e/x and ops/loop/control/progress and N/A/x",
    "runtime resolution": "Path(__file__).resolve().parents[1] / $PSScriptRoot",
    "bare drive root": "the root of `" + _win("E", B) + "`",
}


@pytest.mark.parametrize("label", sorted(OFFENDERS))
def test_the_predicate_flags_a_machine_path(label: str) -> None:
    assert machine_paths(OFFENDERS[label]), OFFENDERS[label]


@pytest.mark.parametrize("label", sorted(LEGITIMATE))
def test_the_predicate_spares_a_legitimate_neighbour(label: str) -> None:
    assert machine_paths(LEGITIMATE[label]) == [], LEGITIMATE[label]


def test_no_tracked_file_carries_an_absolute_machine_path() -> None:
    offenders, _, _ = _sweep()
    assert not offenders, (
        "absolute machine paths in tracked files - resolve at run time or "
        "use a placeholder such as <repo-root>:\n" + "\n".join(offenders)
    )


def test_the_sweep_reads_a_realistic_number_of_files() -> None:
    _, scanned, _ = _sweep()
    assert scanned >= 155, scanned


def test_only_images_escape_the_sweep_as_binary() -> None:
    _, _, binary = _sweep()
    images = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp")
    assert all(name.lower().endswith(images) for name in binary), binary


def test_a_non_utf8_file_is_decoded_not_skipped(tmp_path: Path) -> None:
    raw = ("note " + _win("E", B, _ROOT_NAME) + " \xe9").encode("latin-1")
    text = raw.decode("utf-8", errors="replace")
    assert b"\x00" not in raw
    assert machine_paths(text)


@pytest.mark.parametrize("glob", sorted(ALLOWLIST))
def test_every_allowlist_entry_has_a_reason_and_a_target(glob: str) -> None:
    assert len(ALLOWLIST[glob]) > 40
    assert any(fnmatch.fnmatch(n, glob) for n in _tracked_files()), glob


@pytest.mark.parametrize(
    "table", [FAKE_PATHS, FAKE_UNC_HOSTS], ids=["fake_paths", "fake_unc_hosts"]
)
def test_every_fake_entry_has_a_reason(table: dict[str, str]) -> None:
    assert all(len(reason) > 20 for reason in table.values()), table


def test_the_handoff_resolves_the_install_root_at_run_time() -> None:
    text = (REPO_ROOT / "RSC-NEXT-SESSION.txt").read_text(encoding="utf-8")
    assert not [m for line in text.splitlines() for m in machine_paths(line)]


def test_this_file_does_not_need_its_own_allowlist() -> None:
    assert not _allowlisted("tests/test_no_machine_paths.py")
    text = Path(__file__).read_text(encoding="utf-8")
    assert not [m for line in text.splitlines() for m in machine_paths(line)]
