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
    if active != HOOKS_DIRNAME:
        # Verify rather than assume. A --system or --global hooksPath, or a
        # config include, can win over what was just written.
        print(
            f"core.hooksPath reads back as {active!r}, expected "
            f"{HOOKS_DIRNAME!r} - hooks are NOT installed.",
            file=sys.stderr,
        )
        return 1

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
