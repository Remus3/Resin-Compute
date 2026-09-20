"""The single owner of the directory names no recursive walk in this tree descends.

WHY THIS FILE EXISTS. Three independent walks were pruning against three
hand-maintained name lists that had to agree and were not tied together by
anything. Measured 2026-09-20, before this module:

    tools/first_run_capture.py   _WALK_SKIP_DIRS   9 names
    tools/gate_mutation_runner.py _WALK_SKIP       6 names
    scripts/watch_inbox.py       PRUNED_DIR_NAMES  8 names

The eight-name list was the newest and it was MISSING `.claude`, which the
nine-name list had carried for longer. `.claude/` in this checkout holds 834
files including nested worktree checkouts - exactly the catastrophic case
`.git` and `.venv` are in the list for. Three lists that must agree and are not
mechanically tied is the defect; the missing name was only its first symptom.
`tests/test_walkprune.py` goes red if any of the three sites stops deriving
from here.

THE PATTERN IS `core/ports.py`'s, deliberately. That module is the single owner
of every TCP port this repo binds, with a test pinning each constant against
the site that really uses it rather than re-asserting the literal. No existing
primitive home fitted this constant - `core/config.py` is env-derived
live-state-first configuration and holds no frozen name tables, and
`core/domains.py` is game rotation mechanics - so this follows the owner-module
precedent rather than being bolted onto a module that means something else.

THE MATCH IS CASEFOLDED, AND ON THIS PLATFORM THAT IS LOAD-BEARING RATHER THAN
TIDINESS. NTFS PRESERVES the case a directory was created with while COMPARING
case-insensitively, so `.GIT/` and `__PYCACHE__/` are the same directory as
`.git/` and `__pycache__/` to every Windows API and to `open()`, and are
different strings to Python's `in`. Measured on this host 2026-09-20: a drop
carrying `.GIT/` hashed to `d719fe35...` under a case-SENSITIVE prune and to
the identical `d719fe35...` with the prune removed entirely - the prune never
fired, and a sender shipping that name got its whole object store digested.

`str.casefold()` RATHER THAN `str.lower()`, and that is not interchangeable.
`lower()` leaves several non-ASCII forms unfolded, so a name that Windows
resolves to a pruned directory can still slip a `lower()` comparison. Every
name here is ASCII, so the two agree on this table today; the fold is what
keeps that true when somebody adds a name that is not.

THE MATCH IS AN EXACT NAME MATCH AND NEVER A SUBSTRING. `pycache/`, `git/`,
`venv-notes/` and `node_modules_readme/` are legitimate directory names that
must still be walked, and a substring or prefix match would eat all four while
passing every other arm.
"""
from __future__ import annotations

#: Directory names that are never payload and are never descended.
#:
#: Stored ALREADY CASEFOLDED so a caller cannot forget: match through
#: `is_pruned_dir_name`, never with a bare `name in NEVER_WALKED_DIR_NAMES`.
#:
#: WHY THESE NINE. They fall into two groups with different reasons, and the
#: distinction matters because only one group is cheap to get wrong.
#:
#: The CACHE AND ARTEFACT group - `__pycache__`, `.mypy_cache`,
#: `.pytest_cache`, `.ruff_cache` - is the common case. Measured in this repo's
#: main checkout 2026-09-20 with `find`: 14 `__pycache__` directories within
#: four levels, 149 `.pyc` files in total, and one each of the other three.
#: None of it is source and none of it is correspondence.
#:
#: The BLOW-UP group - `.git`, `.venv`, `venv`, `node_modules`, `.claude` - is
#: the rare case that is expensive rather than merely noisy. Each is routinely
#: tens of thousands of entries: a sibling's object store, a populated
#: virtualenv, `shell/node_modules` which exists in this checkout, and
#: `.claude/` at 834 files here because it contains nested worktrees.
#:
#: ON `.gitignore`, STATED PRECISELY BECAUSE A LOOSER VERSION OF THIS SENTENCE
#: WAS MEASURED FALSE. Seven of the nine are ignored by this tree's own
#: `.gitignore`, and TWO ARE NOT. Measured with `git check-ignore -v` on
#: 2026-09-20: `__pycache__` `.gitignore:53`, `.pytest_cache` `:56`,
#: `.mypy_cache` `:57`, `.ruff_cache` `:58`, `.venv` `:66`, `venv` `:67`,
#: `.claude` `:86`; `.git` and `node_modules` return NO match and are NOT
#: ignored. `.git` needs no rule because git never tracks its own directory,
#: and `node_modules` has none at all although `shell/node_modules` exists on
#: disk. So this set is NOT derived from `.gitignore` and must not be
#: described as if it were - the two lists overlap, they are not the same list,
#: and the two names that fall outside it are the two most expensive to walk.
NEVER_WALKED_DIR_NAMES = frozenset(
    {
        ".git",
        ".claude",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)


def is_pruned_dir_name(name: str, names: frozenset[str] = NEVER_WALKED_DIR_NAMES) -> bool:
    """Whether a DIRECTORY called `name` must not be descended.

    `names` is a parameter so a caller with a principled narrower set - see
    `tools/gate_mutation_runner.py`, which must not prune the very caches it
    exists to delete - derives that set from this one and still matches through
    the same fold, rather than growing a second comparison rule.

    THE CALLER MUST HAVE ALREADY ESTABLISHED THAT THIS IS A DIRECTORY. In a git
    worktree `.git` is a FILE, and a file by any of these names is ordinary
    payload that must be read normally.
    """
    return name.casefold() in names
