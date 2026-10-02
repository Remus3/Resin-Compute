"""Point git at the TRACKED hooks in .githooks/.

FIRST ACTION IN ANY FRESH CLONE:
    python scripts/install_hooks.py

WHY THIS IS NOT OPTIONAL
------------------------
`core.hooksPath` is LOCAL git config. It is not cloned. So a fresh clone of
this repo runs ZERO hooks until someone sets it, which defeats the tracked
.githooks/ directory entirely - the gate is absent and nothing says so.

WHY THIS SCRIPT MUST NEVER WRITE A HOOK FILE
--------------------------------------------
Sibling-C's installer used to write `.git/hooks/pre-commit` containing
only one of its steps, overwriting whatever was there. `.git/hooks/` is not
version controlled, so that clobbered the tracked hooks and nothing pointed the
two at each other. Measured consequence, found 2026-07-26: the tracked and
active pre-commit hooks had FULLY DIVERGED and three tracked guards had
silently stopped running, with both generated artifacts drifted by the time it
surfaced. The commit-msg pair had split the same way - the trailer strip lived
only in the untracked copy, the subject validation only in the tracked one, so
exactly one of the two ran depending on which file won.

Setting `core.hooksPath` is therefore the whole job. Every hook body belongs in
.githooks/, under version control, where a fresh clone and a second machine
both get it. Do not reintroduce a hook-writing installer.

IDEMPOTENT: running it twice changes nothing the second time.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIRNAME = ".githooks"


def _names_hooks_dir(active: str, hooks_dir: Path) -> bool:
    """True when `active` NAMES `hooks_dir`, whatever SPELLING git handed back.

    THE DEFECT THIS CLOSES, measured in this tree rather than reasoned about.
    The readback below used to be `active != HOOKS_DIRNAME` - a comparison of
    two STRINGS where the subject is a PATH. One path has many spellings and
    all but one of them made the installer report `hooks are NOT installed`
    about a clone whose hooks were installed and firing.

    Reproduced end to end against a throwaway repo wired exactly as a fresh
    clone. `git config extensions.worktreeConfig true` plus
    `git config --worktree core.hooksPath '.githooks/'` - one trailing
    separator, and the WORKTREE scope outranks the --local scope this script
    writes, which is not exotic here because this repo runs its agents in
    linked worktrees. The installer exited 1 with
    `core.hooksPath reads back as '.githooks/', expected '.githooks' - hooks
    are NOT installed.` while a real `git commit` of a line carrying U+2014
    was REFUSED by the gate, HEAD did not move, and `precommit_gate BLOCKED`
    was on stderr. The hooks were installed. The string said otherwise.
    `'./.githooks'` reproduces it identically.

    On Windows the spelling space is wider still and every member of it is a
    real way a person or a tool writes this value: a case difference, a
    backslash separator, an 8.3 short name, a junction, and an absolute
    spelling of the same directory. `Path.resolve()` collapses all of them
    for a path that EXISTS, and `os.path.normcase` is the backstop for the
    case-insensitive half; on POSIX `normcase` is the identity, so nothing
    here makes the comparison looser on Linux than it has to be.

    WHAT THIS DOES NOT DO, so it is not over-read: it does not accept a
    DIFFERENT directory. A readback naming some other path still resolves to
    some other path and still fails, and
    `test_a_hooks_path_naming_a_different_directory_is_still_refused` is the
    non-vacuity arm that holds that open.

    Relative values are resolved against REPO_ROOT because that is what git
    does with them: `core.hooksPath` is "relative to the directory where the
    hooks are run", which is the top level of the working tree.
    """
    if not active:
        return False
    candidate = Path(active)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        resolved = candidate.resolve()
        want = hooks_dir.resolve()
    except OSError:
        # An unresolvable path is not a match. Fail CLOSED: the caller prints
        # "hooks are NOT installed" and exits 1, which is the safe answer when
        # the question could not be settled.
        return False
    if resolved == want:
        return True
    return os.path.normcase(str(resolved)) == os.path.normcase(str(want))


def _git(*args: str, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=capture,
        text=True,
        check=False,
    )


def _ensure_executable(hooks_dir: Path) -> list[str]:
    """chmod +x every hook in the working tree. Returns what changed.

    A hook that is not executable is not an error git reports - git simply
    declines to run it and says nothing, so the entire commit-time gate goes
    missing while CI stays green. Sibling-C shipped all five of its hooks
    mode 100644 for a while and found out the day a banned glyph committed
    straight through the hole.

    No-op on Windows, where the filesystem has no exec bit and git records the
    mode from the index instead.
    """
    changed: list[str] = []
    if os.name == "nt":
        return changed
    for hook in sorted(p for p in hooks_dir.iterdir() if p.is_file()):
        mode = hook.stat().st_mode
        want = mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if mode != want:
            hook.chmod(want)
            changed.append(hook.name)
    return changed


def _index_mode_problems() -> list[str]:
    """Tracked hooks whose INDEX mode is not 100755.

    The working-tree bit above is what makes the hook run HERE; the index mode
    is what makes it run for everyone else. They are different facts and this
    checks the second one. Silent (returns empty) when the hooks are not
    tracked yet, which is the normal state of a scaffold before its first
    commit.
    """
    listing = _git("ls-files", "-s", f"{HOOKS_DIRNAME}/")
    if listing.returncode != 0 or not listing.stdout.strip():
        return []
    bad: list[str] = []
    for line in listing.stdout.splitlines():
        if not line.strip():
            continue
        # Format is: <mode> <object> <stage><TAB><path>. chr(9) rather than a
        # tab escape because a backslash is illegal inside an f-string
        # expression on the pinned Python 3.11.
        mode, _, rest = line.partition(" ")
        if mode != "100755":
            bad.append(f"{rest.split(chr(9))[-1]}  (mode {mode})")
    return bad


def main() -> int:
    hooks_dir = REPO_ROOT / HOOKS_DIRNAME
    if not (REPO_ROOT / ".git").exists():
        print(f"Not a git repository: {REPO_ROOT}", file=sys.stderr)
        return 1
    if not hooks_dir.is_dir():
        print(f"Missing tracked hooks directory: {hooks_dir}", file=sys.stderr)
        return 1

    # Relative on purpose. An absolute path breaks the moment the repo is
    # cloned to a different location, which is precisely the portability the
    # tracked-hooks layout exists to provide.
    setter = _git("config", "core.hooksPath", HOOKS_DIRNAME)
    if setter.returncode != 0:
        print(
            f"git config core.hooksPath failed: {setter.stderr.strip()}",
            file=sys.stderr,
        )
        return 1

    active = _git("config", "core.hooksPath").stdout.strip()
    if not _names_hooks_dir(active, hooks_dir):
        # Verify rather than assume. A --system, --global or --worktree
        # hooksPath, or a config include, can win over what was just written.
        # RESOLVED rather than string-compared - see _names_hooks_dir for the
        # measurement that forced that.
        print(
            f"core.hooksPath reads back as {active!r}, which does not resolve "
            f"to {hooks_dir} - hooks are NOT installed.",
            file=sys.stderr,
        )
        return 1
    if active != HOOKS_DIRNAME:
        # Not a failure. A different SPELLING of the same directory is a
        # working installation, and saying so is better than silence: it tells
        # the reader that something outranked the --local value this script
        # just wrote, which is the one fact they would otherwise have to go
        # looking for.
        print(
            f"note: core.hooksPath reads back as {active!r} rather than the "
            f"{HOOKS_DIRNAME!r} just written - a higher-precedence scope "
            f"(--worktree, --global, --system or an include) is supplying it. "
            f"It resolves to the same directory, so the hooks ARE active."
        )

    chmodded = _ensure_executable(hooks_dir)
    hooks = sorted(p.name for p in hooks_dir.iterdir() if p.is_file())

    print(f"core.hooksPath = {active}")
    for name in hooks:
        print(f"  active: {name}")
    if chmodded:
        print(f"  chmod +x applied to: {', '.join(chmodded)}")

    bad = _index_mode_problems()
    if bad:
        print(
            "\nThese tracked hooks are not mode 100755. Git silently REFUSES to\n"
            "run a non-executable hook, so the gate would be absent for every\n"
            "other clone:",
            file=sys.stderr,
        )
        for entry in bad:
            print(f"  {entry}", file=sys.stderr)
        print(
            "Fix with: git update-index --chmod=+x .githooks/<hook>",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nOK - {len(hooks)} hook(s) installed from {HOOKS_DIRNAME}/. "
        "Any .git/hooks/ copies are now inert; git consults core.hooksPath."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
