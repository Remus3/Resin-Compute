#!/usr/bin/env python3
"""Create or converge the desktop shortcut that opens the companion window.

IDEMPOTENT BY DESIGN, and that is a deliberate divergence from the sibling
project this pattern came from. Sibling-A's equivalent REFUSES when a shortcut
of the same name is already there and requires `--force`, on the reasoning that
the operator may have pinned or renamed it. That is defensible. It is also not
idempotent: running it twice is an error the second time, so it cannot be put in
a bootstrap script or run on a schedule.

This one converges instead:

    absent            -> create it,  exit 0
    present, correct  -> change NOTHING, say so, exit 0
    present, differs  -> rewrite it, say so, exit 0
    present, differs, --no-clobber -> refuse, exit 4

The comparison is what makes that safe. It reads the existing shortcut back and
compares target, arguments and working directory, so a correct shortcut is never
rewritten - which matters because rewriting drops a pin the operator made.

WHY A `.lnk` POINTED STRAIGHT AT electron.exe. The obvious launchers all flash a
console: a terminal invocation leaves one open for the window's lifetime, a
`.cmd` wrapper spawns a console host that appears for a moment, and a `.vbs`
wrapper avoids the flash by adding a scripting host nobody asked for. A `.lnk`
aimed at a GUI-subsystem image has none of those problems.

THE RUNTIME IS USUALLY ABSENT AFTER `npm install`, AND THAT IS THE COMMON CASE
rather than an exotic one. The pinned Electron package ships no scripts block, so
no postinstall, and fetches its platform binary lazily on the first
`require("electron")`. An operator who has run only `npm install` therefore has
no `electron.exe`, and a shortcut written anyway would be a broken icon with no
diagnosis attached. This refuses instead, and names the remedy.

WHY THIS SHELLS OUT. Nothing in the standard library writes a `.lnk`, and
`requirements.txt` is empty as a recorded decision. Adding pywin32 to write one
file is not a trade this project makes, so PowerShell - present on every Windows
install - drives the `WScript.Shell` COM object.

POWERSHELL IS NEVER INVOKED THROUGH A SHELL. Through Git Bash, MSYS path
conversion rewrites arguments before the tool sees them. Every call below passes
a list argv with `shell=False`, which is immune. `tests/test_make_shortcut.py`
pins the absence of the other spelling twice, once against the parsed call and
once against the raw source text.

PRIVACY IS THE SHARP EDGE OF THIS SCRIPT. The Desktop sits under the user
profile, so its path CONTAINS THE WINDOWS ACCOUNT NAME:

  - NO MESSAGE EVER NAMES A DIRECTORY. Every refusal is fixed text naming a
    remedy, and the lines that are not fixed name the shortcut FILE and never
    where it sits.
  - POWERSHELL'S OWN ERROR TEXT IS NEVER ECHOED. A failed `CreateShortcut` names
    the `.lnk` path it could not write. A tool's error text is not a channel this
    script can make safe, so it is not opened.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SHELL_DIR = REPO_ROOT / "shell"
ELECTRON_RELATIVE = Path("node_modules") / "electron" / "dist" / "electron.exe"

DEFAULT_SHORTCUT_NAME = "ResinCompute"
SHORTCUT_SUFFIX = ".lnk"
SHORTCUT_ARGUMENTS = "."
SHORTCUT_DESCRIPTION = "ResinCompute companion window"

# Exit codes. A caller scripting this reads these, so they are a contract.
EXIT_OK = 0
EXIT_RUNTIME_MISSING = 1
EXIT_NO_POWERSHELL = 3
EXIT_REFUSED = 4
EXIT_WRITE_FAILED = 5

RUNTIME_MISSING = (
    "The Electron runtime is not installed, so there is nothing for a shortcut "
    "to point at. Install it with: npm install --prefix shell"
)
NO_POWERSHELL = (
    "No PowerShell was found on PATH, and it is what writes the shortcut file. "
    "Install Windows PowerShell or PowerShell 7, then run this again."
)
WRITE_FAILED = (
    "The shortcut could not be written. Check that the desktop exists and is "
    "writable, then run this again."
)
REFUSED_EXISTS = (
    "A shortcut of that name is already there and points somewhere else. "
    "Re-run without --no-clobber to replace it."
)
CREATED = "Created the shortcut"
UPDATED = "Updated the shortcut"
UNCHANGED = "Already correct, nothing to do"

_POWERSHELL_NAMES = ("powershell.exe", "pwsh.exe", "powershell", "pwsh")


class Action(Enum):
    """What one run decided to do."""

    CREATE = "create"
    UPDATE = "update"
    UNCHANGED = "unchanged"
    REFUSE = "refuse"


class ShortcutState(NamedTuple):
    """The three fields that decide whether a shortcut is the one we want.

    Icon and description are deliberately NOT compared. Both are cosmetic, and
    including them would make the script rewrite a working shortcut whenever a
    label was reworded - which is exactly the churn idempotence is meant to
    prevent.
    """

    target: str
    arguments: str
    working_dir: str


def _normalize_path(value: str) -> str:
    """Fold a Windows path for comparison.

    Case-insensitive and trailing-separator-insensitive, because the COM object
    may hand back a path it was not literally given. Treating either difference
    as real would rewrite a correct shortcut on every run.
    """
    return value.strip().rstrip("\\/").casefold()


def matches(observed: ShortcutState, desired: ShortcutState) -> bool:
    """Is this shortcut the one we would have written?

    THE ONE COMPARISON, used by `decide` and by the renamed-twin scan alike. Two
    copies of this rule would drift and then disagree about whether a shortcut
    needs rewriting, which is the worst possible outcome for an idempotent tool.
    """
    return (
        _normalize_path(observed.target) == _normalize_path(desired.target)
        and observed.arguments.strip() == desired.arguments.strip()
        and _normalize_path(observed.working_dir) == _normalize_path(desired.working_dir)
    )


def decide(
    observed: ShortcutState | None,
    desired: ShortcutState,
    no_clobber: bool = False,
) -> Action:
    """Compare observed against desired and return the action to take.

    Pure. This is the whole of the idempotence logic and it is why the module is
    testable without touching a desktop.
    """
    if observed is None:
        return Action.CREATE

    if matches(observed, desired):
        return Action.UNCHANGED
    if no_clobber:
        return Action.REFUSE
    return Action.UPDATE


def ps_quote(value: str) -> str:
    """Wrap a string as a PowerShell single-quoted literal.

    Inside single quotes nothing is special except the quote itself, which is
    escaped by DOUBLING it. A backslash escape is a shell habit and is wrong
    here; a Windows path's backslashes must stay literal.
    """
    return "'" + value.replace("'", "''") + "'"


def powershell_argv(powershell: str, script: str) -> list[str]:
    """Build the argv. A LIST, never a command string."""
    return [
        powershell,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


def create_script(desired: ShortcutState, link_path: str) -> str:
    """PowerShell that writes the shortcut. Single quotes throughout."""
    return (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + ps_quote(link_path) + ");"
        " $s.TargetPath = " + ps_quote(desired.target) + ";"
        " $s.Arguments = " + ps_quote(desired.arguments) + ";"
        " $s.WorkingDirectory = " + ps_quote(desired.working_dir) + ";"
        " $s.Description = " + ps_quote(SHORTCUT_DESCRIPTION) + ";"
        " $s.IconLocation = " + ps_quote(desired.target) + ";"
        " $s.Save()"
    )


def read_script(link_path: str) -> str:
    """PowerShell that prints the existing shortcut's three fields, one per line.

    Reading it back is what makes the script idempotent rather than merely safe:
    without this, a correct shortcut and a wrong one are indistinguishable.
    """
    return (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + ps_quote(link_path) + ");"
        " Write-Output $s.TargetPath; Write-Output $s.Arguments;"
        " Write-Output $s.WorkingDirectory"
    )


def shortcut_file_name(raw: str | None) -> str:
    """Normalise `--name` into a bare file name.

    A NAME, NEVER A LOCATION. Without the separator check, `--name
    ..\\..\\startup\\x` would write outside the desktop entirely.
    """
    if raw is None:
        return DEFAULT_SHORTCUT_NAME + SHORTCUT_SUFFIX
    candidate = raw.strip()
    if not candidate or candidate in {".", ".."}:
        raise ValueError("the shortcut name is empty")
    if "/" in candidate or "\\" in candidate or os.pathsep in candidate:
        raise ValueError("the shortcut name is a file name, not a path")
    if not candidate.lower().endswith(SHORTCUT_SUFFIX):
        candidate += SHORTCUT_SUFFIX
    return candidate


def electron_path() -> Path:
    return SHELL_DIR / ELECTRON_RELATIVE


def desired_state() -> ShortcutState:
    return ShortcutState(
        target=str(electron_path()),
        arguments=SHORTCUT_ARGUMENTS,
        working_dir=str(SHELL_DIR),
    )


def desktop_dir(explicit: str | None = None) -> Path:
    """Where the shortcut goes.

    `USERPROFILE` rather than a registry read: this project has no Windows-only
    dependency and the registry route needs `winreg`, which does not exist on
    the machines the suite also runs on.
    """
    if explicit:
        return Path(explicit)
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return Path(profile) / "Desktop"


def _resolve_powershell() -> str | None:
    """Find PowerShell on PATH by NAME.

    Never an absolute path: a machine-specific path in a tracked file is exactly
    what the privacy rule forbids.
    """
    from shutil import which

    for name in _POWERSHELL_NAMES:
        found = which(name)
        if found:
            return name
    return None


def _run(powershell: str, script: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - argv is a list and shell is False
        powershell_argv(powershell, script),
        capture_output=True,
        shell=False,
        check=False,
        timeout=60,
    )


def observe(powershell: str, link_path: Path) -> ShortcutState | None:
    """Read an existing shortcut, or None when there is not one.

    PowerShell's own stderr is NEVER echoed - a failed CreateShortcut names the
    path it could not read, and a path carries the account name. A failure here
    is reported as "no readable shortcut", which drives a create, which then
    fails loudly if the real problem was permissions.
    """
    if not link_path.exists():
        return None
    completed = _run(powershell, read_script(str(link_path)))
    if completed.returncode != 0:
        return None
    lines = completed.stdout.decode("utf-8", errors="replace").splitlines()
    while len(lines) < 3:
        lines.append("")
    return ShortcutState(target=lines[0].strip(), arguments=lines[1].strip(), working_dir=lines[2].strip())


def find_renamed_twin(powershell: str, destination: Path, desired: ShortcutState, skip: Path) -> Path | None:
    """A shortcut to the same target under a DIFFERENT name, or None.

    WHY THIS EXISTS, and it was measured rather than imagined. The operator
    renamed the shortcut this script created to match their own convention. The
    exact-name lookup then found nothing, and without this scan the next run
    would have created a second shortcut beside the first - which is precisely
    the failure Sibling-A's refuse-unless-force default was guarding against.

    Idempotence converges on a STATE - a working shortcut to this app exists -
    not on one particular filename.
    """
    try:
        candidates = sorted(destination.glob("*.lnk"))
    except OSError:
        return None
    for candidate in candidates:
        if candidate == skip:
            continue
        observed = observe(powershell, candidate)
        if observed is not None and matches(observed, desired):
            return candidate
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/make_shortcut.py",
        description="Create or converge the ResinCompute desktop shortcut. Safe to run repeatedly.",
    )
    parser.add_argument("--name", default=None, help="shortcut file name, without a path")
    parser.add_argument("--desktop-dir", default=None, help="override the destination directory")
    parser.add_argument(
        "--no-clobber",
        action="store_true",
        help="refuse if a shortcut of that name points somewhere else, instead of updating it",
    )
    parser.add_argument("--dry-run", action="store_true", help="say what would happen and write nothing")
    args = parser.parse_args(argv)

    try:
        file_name = shortcut_file_name(args.name)
    except ValueError as exc:
        print(f"Refused: {exc}")
        return EXIT_REFUSED

    # Decided before any tool is resolved, so a machine with no PowerShell still
    # learns its real problem rather than being told about PowerShell.
    if not electron_path().is_file():
        print(RUNTIME_MISSING)
        return EXIT_RUNTIME_MISSING

    powershell = _resolve_powershell()
    if powershell is None:
        print(NO_POWERSHELL)
        return EXIT_NO_POWERSHELL

    destination = desktop_dir(args.desktop_dir)
    if not destination.is_dir():
        print(WRITE_FAILED)
        return EXIT_WRITE_FAILED

    link_path = destination / file_name
    desired = desired_state()
    observed = observe(powershell, link_path)

    # Before creating anything, check whether a correct shortcut is already
    # there under a name the operator chose. Creating a duplicate beside it is
    # not idempotent, it is litter.
    if observed is None:
        twin = find_renamed_twin(powershell, destination, desired, skip=link_path)
        if twin is not None:
            print(f"{UNCHANGED}: already present as {twin.name}")
            return EXIT_OK

    action = decide(observed, desired, no_clobber=args.no_clobber)

    if action is Action.UNCHANGED:
        print(f"{UNCHANGED}: {file_name}")
        return EXIT_OK
    if action is Action.REFUSE:
        print(REFUSED_EXISTS)
        return EXIT_REFUSED

    if args.dry_run:
        verb = CREATED if action is Action.CREATE else UPDATED
        print(f"Would have done this: {verb}: {file_name}")
        return EXIT_OK

    completed = _run(powershell, create_script(desired, str(link_path)))
    if completed.returncode != 0:
        # PowerShell's stderr is deliberately not rendered. See the header.
        print(WRITE_FAILED)
        return EXIT_WRITE_FAILED

    print(f"{CREATED if action is Action.CREATE else UPDATED}: {file_name}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
