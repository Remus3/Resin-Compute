"""The single owner of "is this path OUR content", for every guard that walks the tree.

WHY THIS MODULE EXISTS AT ALL, AND WHY IT IS IN `core/` RATHER THAN `tests/`.

The predicate started life in `tests/test_guard_worktree_exclusion.py`, which is
where the four guards that first needed it could reach. That module's own
docstring already named `tests/conftest.py` as the home a follow-up slice should
move it to. Both of those are TEST locations, and the measurement that moved it
here is that `core/provenance.py` - PRODUCTION code, inside `mypy.ini`'s `files=`
roots - needs the same predicate. A production module importing from `tests/`
is a dependency inversion on its own, and here it is worse than a style
complaint: `tests/test_guard_worktree_exclusion.py` imports `pytest` at module
scope, so `core.provenance` would have acquired a hard runtime dependency on a
test framework. `import core.provenance` would then fail on any machine that
runs this tree without pytest installed. That is not a tidiness argument, it is
a breakage, and it is what decided the move.

WHY A NEW MODULE RATHER THAN A FEW MORE LINES IN `core/walkprune.py`.
`core/walkprune.py` is the single owner of the never-walked directory NAMES, and
it stays that. This module owns a different question - whether a PATH sits
inside content this working tree does not own - and it ANSWERS that question by
composing walkprune's name rule rather than by restating any of its names. The
`SWEEP_SKIP_DIRS` set below is derived arithmetic on `NEVER_WALKED_DIR_NAMES`,
in the same shape `tools/gate_mutation_runner.py::_WALK_SKIP` uses, so there is
still exactly one list of names in this tree and no second one to drift.

WHAT COUNTS AS "NOT THIS TREE'S OWN CONTENT". Two independent signals, both
required because neither covers the other:

  - a PRUNED or DOT-PREFIXED directory anywhere between the sweep root and the
    file. This tree's own worktrees live at `.claude/worktrees/`, one full copy
    per in-flight agent.
  - a directory carrying a `.git` ENTRY. A linked worktree's `.git` is a FILE
    holding a `gitdir:` pointer, not a directory, which is why the test is
    `.exists()` and not `.is_dir()`. This is the signal that catches a nested
    checkout that is NOT dot-prefixed, which a name filter alone would walk
    straight into. It is also the signal a `.git`-in-`path.parts` filter misses
    entirely, because a nested checkout's TRACKED CONTENT has no `.git` anywhere
    in its path.

WHAT IS DELIBERATELY NOT EXCLUDED. A plain, non-dot directory with no `.git`
entry is this repository's own content and is swept. That is what keeps
`tests/test_guard_worktree_blindness.py` honest: its vulnerability proof plants
a probe with NO `.git` marker and NO dot prefix and asserts a guard still goes
red on it.

THE OVER-EXCLUSION FAILURE MODE IS THE EXPENSIVE ONE. An exclusion that quietly
stops sweeping real content passes every "the bad thing is gone" arm while
destroying the guard it was meant to repair. Every caller below is therefore
paired in its tests with a NEIGHBOURS arm proving ordinary sibling content is
still swept, and the mutant that excludes everything reddens those arms and only
those arms.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.walkprune import NEVER_WALKED_DIR_NAMES, is_pruned_dir_name

#: Directory names a repository sweep must not descend into.
#:
#: DERIVED, not restated. `core/walkprune.py` owns the names; this adds the two
#: build-output directories that are not in that set because nothing else in
#: this tree walks into them, and matches the whole union through walkprune's
#: own casefolded comparison. On NTFS that fold is load-bearing rather than
#: tidy: `__PYCACHE__` and `.GIT` are the SAME directories as `__pycache__` and
#: `.git` to every Windows API and different strings to Python's `in`.
SWEEP_SKIP_DIRS = NEVER_WALKED_DIR_NAMES | frozenset({"build", "dist"})

#: What a linked git worktree puts at its own root: a FILE, not a directory,
#: holding a `gitdir:` pointer back to the superproject. Tested with
#: `.exists()` so both that file and an ordinary `.git` directory are caught.
GIT_MARKER = ".git"


def is_nested_checkout(directory: Path) -> bool:
    """Whether `directory` is the root of some OTHER checkout of some repository.

    A linked worktree carries a `.git` FILE; a clone carries a `.git`
    DIRECTORY. `.exists()` is the only test that sees both.
    """
    return (directory / GIT_MARKER).exists()


def is_foreign_dir_name(name: str) -> bool:
    """Whether a directory with this NAME is never part of a repository sweep.

    Dot-prefixed wholesale, because `.claude/worktrees/` holds full copies of
    this repository and a sweep that walked them would report on other agents'
    uncommitted work. Then the shared pruned-name table, through walkprune's
    casefold.
    """
    return name.startswith(".") or is_pruned_dir_name(name, SWEEP_SKIP_DIRS)


def excluded_from_repo_sweep(path: Path, root: Path) -> bool:
    """Is `path` inside something that is not this working tree's own content?

    Only ANCESTOR DIRECTORIES strictly between `root` and `path` are consulted.
    The leaf's own name never decides, so a tracked file legitimately named
    `.gitattributes` is swept, and `root` itself never decides, so a sweep whose
    root is itself a dot-directory - `.githooks/`, which
    `tests/test_line_endings.py` walks - does not exclude its entire corpus on
    the first step.

    A path that is not under `root` RAISES rather than returning False. Walking
    off the top would otherwise reach the filesystem root and quietly answer
    "not excluded" to a question this function could not answer at all.
    """
    current = path.parent
    while current != root:
        parent = current.parent
        if parent == current:
            raise ValueError(f"{path} is not inside {root}, so it cannot be swept from there")
        if is_foreign_dir_name(current.name):
            return True
        if is_nested_checkout(current):
            return True
        current = parent
    return False


def swept_files(root: Path, pattern: str = "*") -> list[Path]:
    """Every FILE under `root` matching `pattern` that this tree actually owns.

    The drop-in replacement for `sorted(root.rglob(pattern))` in a guard that
    walks a repository directory. Sorted, so a guard's offender list stays
    deterministic across machines and filesystems.
    """
    return sorted(
        path
        for path in root.rglob(pattern)
        if path.is_file() and not excluded_from_repo_sweep(path, root)
    )


def prune_walk_dirs(dirpath: str | os.PathLike[str], dirnames: list[str]) -> None:
    """The `os.walk` shape of the same predicate, pruning `dirnames` IN PLACE.

    `swept_files` filters AFTER `rglob` has already descended; an `os.walk`
    caller can refuse to descend in the first place, which is strictly better
    and is why both shapes live here instead of one caller growing its own
    second rule. Mutating the list in place rather than returning a new one is
    `os.walk`'s own documented contract for pruning - rebinding the name would
    be a silent no-op.

    The `.git`-marker test is applied to the CHILD directory, so a nested
    checkout is refused before a single one of its entries is read.
    """
    base = Path(dirpath)
    dirnames[:] = [
        name
        for name in dirnames
        if not is_foreign_dir_name(name) and not is_nested_checkout(base / name)
    ]
