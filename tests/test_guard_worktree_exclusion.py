"""The exclusion the blind root-walking guards were missing, and its proof.

WHAT THIS FIXES. `tests/test_guard_worktree_blindness.py` measured, over every
`test_*.py` module in this directory, that four of them recurse a directory tree
anchored at the repository root while carrying no skip list of any kind - not a
dot-directory filter, not even the conventional `__pycache__`/`.git` denylist:

NO MODULE COUNT IS QUOTED HERE ANY MORE, DELIBERATELY. This paragraph used to
say "all 39 `test_*.py` modules". That figure was correct when written and was
measured at 95 on 2026-10-02 at commit 83d8b1a - it had rotted by a factor of
more than two while the sentence around it stayed true. Restating it buys one
edit of accuracy and then rots again, so the count is dropped rather than
refreshed: the claim this docstring needs is "every module in this directory",
which is what the measurement actually ranged over and which does not decay.
Re-derive with `git ls-files -- 'tests/test_*.py' | wc -l` if a number is
wanted.

    tests/test_docs_consistency.py   six `(REPO_ROOT / "docs").rglob("*.md")` sites
    tests/test_goal_spec.py          `DATA_DIR.rglob("*")` in `_data_files()`
    tests/test_licence_posture.py    four `(REPO_ROOT / "data").rglob(...)` sites
    tests/test_line_endings.py       `(REPO_ROOT / ".githooks").iterdir()`

The failure mode, from Sibling-C's inbox note of 2026-09-07: after merging
a worktree agent's branch, the merged worktree is left on disk INSIDE the
repository, and a guard that walks from the repository root then scans a SECOND
FULL COPY of the tree and goes red on content that is not its own. The colour of
the suite becomes a fact about whatever some unrelated agent happened to leave
lying around.

WHY A SHARED PREDICATE RATHER THAN FOUR COPIES. Four hand-maintained skip lists
are four chances to drift, and the drift is invisible - a skip list that has
quietly stopped covering a case still passes every test the guard has. All four
modules reach `swept_files()` through this module, and
`test_all_four_repaired_guards_share_one_predicate_object` below pins that they
share ONE function object rather than four look-alikes.

WHERE THE PREDICATE ACTUALLY LIVES NOW: `core/repo_sweep.py`. It used to be
defined in this file, and the paragraph here used to name `tests/conftest.py`
as the home a follow-up slice should move it to. Both of those are TEST
locations and both are now wrong, for a reason that was measured rather than
argued: `core/provenance.py` is PRODUCTION code that needs the same predicate,
this module imports `pytest` at module scope, and a production module importing
from here would have given `core.provenance` a hard runtime dependency on a
test framework. `import core.provenance` would then fail wherever this tree runs
without pytest. The names are RE-EXPORTED below, so every module that already
did `from tests.test_guard_worktree_exclusion import swept_files` keeps working
unchanged and keeps binding the SAME function object the identity arms pin.

NO CIRCULAR IMPORT. This module imports the guard modules INSIDE test bodies,
never at module scope, so they can import `swept_files` from here at module
scope without a cycle. `core/repo_sweep.py` imports nothing from `tests/`.

WHAT COUNTS AS "NOT THIS TREE'S OWN CONTENT". Two independent signals, both
required because neither covers the other:

  - a PRUNED or DOT-PREFIXED directory anywhere between the sweep root and the
    file. This tree's own worktrees live at `.claude/worktrees/`, one full copy
    per in-flight agent. The name table is `core/walkprune.py`'s, matched
    through its casefold, rather than a second hand-maintained list.
  - a directory carrying a `.git` ENTRY. A linked worktree's `.git` is a FILE
    holding a `gitdir:` pointer, not a directory, which is why the test is
    `.exists()` and not `.is_dir()` - `tests/conftest.py` records that same trap
    for `git rev-parse --git-dir`. This is the signal that catches a nested
    checkout that is NOT dot-prefixed, which a dot-directory filter alone would
    walk straight into.

WHAT IS DELIBERATELY NOT EXCLUDED. A plain, non-dot directory with no `.git`
entry is this repository's own content and is swept. That matters: it is what
keeps `tests/test_guard_worktree_blindness.py` honest. That module's
vulnerability proof plants `data/wt_probe_<uuid>/nested_checkout/data/` with NO
`.git` marker and NO dot prefix, and asserts the licence guard goes red on it.
It still does. This slice repairs the guards against real nested checkouts
without weakening the file that proves a naive sweep is naive.

THE SWEEP-NEEDS-TWO-GUARDS RULE, applied to this slice. Every repaired guard
below gets a matched pair: one arm proving the nested checkout is no longer
swept, and one arm proving that the IDENTICAL offending content, planted OUTSIDE
the nested checkout, still makes the guard fire. An exclusion that scored 100
percent on the first arm by excluding everything would fail the second, and the
checked-count assertion in every arm - asserted BEFORE the offender list, per
this tree's standing "zero out of zero reads as a pass" rule - catches the
degenerate case where the sweep silently found nothing at all.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest

from core.repo_sweep import (
    GIT_MARKER,
    SWEEP_SKIP_DIRS,
    excluded_from_repo_sweep,
    is_foreign_dir_name,
    is_nested_checkout,
    prune_walk_dirs,
    swept_files,
)

#: RE-EXPORTED, NOT REDEFINED. Six test modules already import `swept_files`
#: from this module by name; binding it here means none of their import lines
#: changed when the predicate moved to `core/repo_sweep.py`, and - because this
#: is the same function object, not a wrapper - the identity arms that pin them
#: all to ONE predicate still pin them to one predicate.
__all__ = [
    "GIT_MARKER",
    "SWEEP_SKIP_DIRS",
    "excluded_from_repo_sweep",
    "is_foreign_dir_name",
    "is_nested_checkout",
    "prune_walk_dirs",
    "swept_files",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
GITHOOKS_DIR = REPO_ROOT / ".githooks"

#: One byte past the ceiling `tests/test_licence_posture.py`'s bulk-dump guard
#: pins as a function-local variable (`limit = 64 * 1024`). Copied as a literal
#: for the same reason `tests/test_guard_worktree_blindness.py` copies it: the
#: guard does not expose the number as a module constant, so this pins the same
#: number and fails loudly if the guard's number ever moves.
OVERSIZE_BYTES = 64 * 1024 + 1

#: A figure `tests/test_goal_spec.py::UNSOURCED_FIGURES` denies entry to `data/`.
UNSOURCED_FIGURE = "430000"

#: A citation shaped like a real repo path - it starts with a `TREE_ROOTS`
#: prefix and ends in a `KNOWN_SUFFIXES` suffix, so
#: `tests/test_docs_consistency.py::_backticked_paths` recognises it - naming
#: something that does not and will not exist.
DEAD_POINTER = "docs/probe_absent_directory/probe_absent_pointer.md"

_PROBE_PREFIX = "wt_probe_"


# ---------------------------------------------------------------------------
# Probe planting
# ---------------------------------------------------------------------------


@contextmanager
def planted_tree(parent: Path, *, nested_checkout: bool, files: dict[str, bytes]) -> Iterator[Path]:
    """Plant ONE probe directory in the real tree, and remove it unconditionally.

    EXPORTED, and that is the point of it being a plain context manager rather
    than a fixture. Three more guards outside this module - in
    `tests/test_git_subprocess_census.py`, `tests/test_loop_concurrency.py` and
    `tests/test_provenance.py` - need to plant exactly this shape, and a
    `@pytest.fixture` cannot be imported into another test module and used: it
    would have to be re-registered through a `conftest.py` or copied. Copying
    is what produced the duplicated skip lists this whole module exists to end,
    so the mechanism is shared instead. `probe_factory` below is now a thin
    multi-plant wrapper over this, so there is ONE planting rule and ONE
    cleanup rule rather than two that must agree.

    CLEANUP IS UNCONDITIONAL and VERIFIED. The `finally` runs even when the
    body raises, and the removal is followed by an explicit
    `assert not probe_dir.exists()`: a probe left behind inside `data/`,
    `docs/`, `tools/` or `.githooks/` would itself be exactly the stray nested
    content this module is about, and would poison every later run.

    NAMED TO NEVER COLLIDE. A fresh `uuid4().hex` per probe, so two probes in
    one test, two concurrent runs, and a probe racing a real worktree merge
    cannot land on the same path.
    """
    probe_dir = parent / f"{_PROBE_PREFIX}{uuid.uuid4().hex}"
    probe_dir.mkdir(parents=True)
    try:
        if nested_checkout:
            # A linked worktree's root carries a `.git` FILE holding a pointer,
            # not a `.git` directory. Written with a relative gitdir on purpose:
            # an absolute one would be a machine-identity leak, which
            # `tests/test_machine_identity.py` forbids and would catch.
            (probe_dir / GIT_MARKER).write_bytes(b"gitdir: ../../.git/worktrees/probe\n")
        for rel_path, content in files.items():
            target = probe_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        yield probe_dir
    finally:
        if probe_dir.exists():
            # Deepest first, so every directory is empty by its own rmdir().
            for path in sorted(probe_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if path.is_dir() and not path.is_symlink():
                    path.rmdir()
                else:
                    path.unlink()
            probe_dir.rmdir()
        assert not probe_dir.exists(), (
            f"cleanup left {probe_dir} behind - a stray probe directory inside the "
            "repository is exactly the defect this module is about, and this suite "
            "must never be the thing that leaves one"
        )


def assert_probe_is_in_range(planted: Path, root: Path, pattern: str) -> None:
    """POSITIVE CONTROL, exported for the three guards repaired outside this file.

    See `_assert_probe_is_in_range` below, which is this function; the private
    spelling is kept because this module's own arms already call it by that
    name and renaming them would be churn in a file other slices read.
    """
    _assert_probe_is_in_range(planted, root, pattern)


@pytest.fixture
def probe_factory() -> Iterator[Callable[..., Path]]:
    """Plants probe directories in the real tree and removes every one of them.

    WHY THE REAL TREE AND NOT `tmp_path`. The guards under test are hard-wired
    to `REPO_ROOT`; there is no seam to point them somewhere else, and inventing
    one would mean testing a reimplementation rather than the shipped guard.
    `tests/test_guard_worktree_blindness.py` made the same call for the same
    reason, and this fixture is deliberately the same shape as that file's.

    CLEANUP IS UNCONDITIONAL and VERIFIED. Teardown after `yield` runs even when
    the test body raises, and each removal is followed by an explicit
    `assert not probe_dir.exists()`: a probe left behind inside `data/`, `docs/`
    or `.githooks/` would itself be exactly the stray nested content this module
    is about, and would poison every later run.

    NAMED TO NEVER COLLIDE. A fresh `uuid4().hex` per probe, so two probes in
    one test, two concurrent runs, and a probe racing a real worktree merge
    cannot land on the same path.
    """
    with ExitStack() as stack:

        def _plant(parent: Path, *, nested_checkout: bool, files: dict[str, bytes]) -> Path:
            return stack.enter_context(
                planted_tree(parent, nested_checkout=nested_checkout, files=files)
            )

        yield _plant


def _assert_probe_is_in_range(planted: Path, root: Path, pattern: str) -> None:
    """POSITIVE CONTROL: the planted file really is inside an unexcluded sweep.

    Without this, "the guard stayed green" and "the guard was aimed at an empty
    corpus" look identical, and a broken plant would read as a passing fix. The
    naive `rglob` here is the very sweep the four guards used before this slice,
    so a hit proves the old code WOULD have walked over this file.
    """
    naive = [path for path in root.rglob(pattern) if path.is_file()]
    assert len(naive) > 0, f"the naive sweep of {root} found nothing - zero out of zero is not a pass"
    assert planted in naive, (
        f"the planted probe at {planted} is not in an unfiltered sweep of {root}, so "
        "nothing below would prove anything about the exclusion"
    )


# ---------------------------------------------------------------------------
# tests/test_licence_posture.py - the bulk-dump sweep of data/
# ---------------------------------------------------------------------------


def test_licence_bulk_dump_guard_ignores_a_nested_checkout(probe_factory: Callable[..., Path]) -> None:
    from tests import test_licence_posture

    probe_dir = probe_factory(
        DATA_DIR,
        nested_checkout=True,
        files={"data/oversized_dump.bin": b"\x00" * OVERSIZE_BYTES},
    )
    planted = probe_dir / "data" / "oversized_dump.bin"
    _assert_probe_is_in_range(planted, DATA_DIR, "*")

    checked = swept_files(DATA_DIR)
    assert len(checked) > 0, "the repaired sweep of data/ found nothing - zero out of zero is not a pass"
    assert planted not in checked, "the nested checkout's oversized file is still being swept"

    test_licence_posture.test_no_data_file_is_large_enough_to_be_a_bulk_dump()


def test_licence_bulk_dump_guard_still_fires_outside_a_nested_checkout(
    probe_factory: Callable[..., Path],
) -> None:
    """SURVIVAL ARM: identical bytes, no `.git` marker, and the guard must bite."""
    from tests import test_licence_posture

    probe_dir = probe_factory(
        DATA_DIR,
        nested_checkout=False,
        files={"data/oversized_dump.bin": b"\x00" * OVERSIZE_BYTES},
    )
    planted = probe_dir / "data" / "oversized_dump.bin"

    checked = swept_files(DATA_DIR)
    assert len(checked) > 0, "the repaired sweep of data/ found nothing - zero out of zero is not a pass"
    assert planted in checked, "an ordinary directory under data/ must still be swept"

    with pytest.raises(AssertionError, match=r"suspiciously large files under data/"):
        test_licence_posture.test_no_data_file_is_large_enough_to_be_a_bulk_dump()


# ---------------------------------------------------------------------------
# tests/test_goal_spec.py - the unsourced-figure sweep of data/
# ---------------------------------------------------------------------------


def test_goal_spec_figure_guard_ignores_a_nested_checkout(probe_factory: Callable[..., Path]) -> None:
    from tests import test_goal_spec

    probe_dir = probe_factory(
        DATA_DIR,
        nested_checkout=True,
        files={"data/costs.json": b'{"mora": ' + UNSOURCED_FIGURE.encode("ascii") + b"}\n"},
    )
    planted = probe_dir / "data" / "costs.json"
    _assert_probe_is_in_range(planted, DATA_DIR, "*")

    checked = test_goal_spec._data_files()
    assert len(checked) > 0, "the repaired sweep of data/ found nothing - zero out of zero is not a pass"
    assert planted not in checked, "the nested checkout's cost file is still being swept"

    test_goal_spec.test_the_data_directory_carries_no_unsourced_cost_figure()


def test_goal_spec_figure_guard_still_fires_outside_a_nested_checkout(
    probe_factory: Callable[..., Path],
) -> None:
    """SURVIVAL ARM: identical bytes, no `.git` marker, and the guard must bite."""
    from tests import test_goal_spec

    probe_dir = probe_factory(
        DATA_DIR,
        nested_checkout=False,
        files={"data/costs.json": b'{"mora": ' + UNSOURCED_FIGURE.encode("ascii") + b"}\n"},
    )
    planted = probe_dir / "data" / "costs.json"

    checked = test_goal_spec._data_files()
    assert len(checked) > 0, "the repaired sweep of data/ found nothing - zero out of zero is not a pass"
    assert planted in checked, "an ordinary directory under data/ must still be swept"

    with pytest.raises(AssertionError, match=r"unsourced cost figures reached data/"):
        test_goal_spec.test_the_data_directory_carries_no_unsourced_cost_figure()


# ---------------------------------------------------------------------------
# tests/test_docs_consistency.py - the pointer sweep of docs/
# ---------------------------------------------------------------------------


def test_docs_pointer_guard_ignores_a_nested_checkout(probe_factory: Callable[..., Path]) -> None:
    from tests import test_docs_consistency

    probe_dir = probe_factory(
        DOCS_DIR,
        nested_checkout=True,
        files={"docs/probe.md": f"A dead pointer: `{DEAD_POINTER}`\n".encode("ascii")},
    )
    planted = probe_dir / "docs" / "probe.md"
    _assert_probe_is_in_range(planted, DOCS_DIR, "*.md")

    checked = test_docs_consistency._docs_markdown()
    assert len(checked) > 0, "the repaired sweep of docs/ found nothing - zero out of zero is not a pass"
    assert planted not in checked, "the nested checkout's markdown is still being swept"

    test_docs_consistency.test_every_path_the_docs_directory_points_at_exists()


def test_docs_pointer_guard_still_fires_outside_a_nested_checkout(
    probe_factory: Callable[..., Path],
) -> None:
    """SURVIVAL ARM: identical bytes, no `.git` marker, and the guard must bite."""
    from tests import test_docs_consistency

    probe_dir = probe_factory(
        DOCS_DIR,
        nested_checkout=False,
        files={"docs/probe.md": f"A dead pointer: `{DEAD_POINTER}`\n".encode("ascii")},
    )
    planted = probe_dir / "docs" / "probe.md"

    checked = test_docs_consistency._docs_markdown()
    assert len(checked) > 0, "the repaired sweep of docs/ found nothing - zero out of zero is not a pass"
    assert planted in checked, "an ordinary directory under docs/ must still be swept"

    with pytest.raises(AssertionError, match=r"dead pointers in docs/"):
        test_docs_consistency.test_every_path_the_docs_directory_points_at_exists()


# ---------------------------------------------------------------------------
# tests/test_line_endings.py - the CRLF sweep of .githooks/
# ---------------------------------------------------------------------------


def test_githooks_crlf_guard_ignores_a_nested_checkout(probe_factory: Callable[..., Path]) -> None:
    from tests import test_line_endings

    probe_dir = probe_factory(
        GITHOOKS_DIR,
        nested_checkout=True,
        files={".githooks/pre-commit": b"#!/bin/sh\r\nexit 0\r\n"},
    )
    planted = probe_dir / ".githooks" / "pre-commit"
    _assert_probe_is_in_range(planted, GITHOOKS_DIR, "*")

    checked = test_line_endings._githook_files()
    assert len(checked) > 0, "the repaired sweep of .githooks/ found nothing - zero out of zero is not a pass"
    assert planted not in checked, "the nested checkout's CRLF hook is still being swept"

    test_line_endings.test_the_githooks_shims_are_lf_because_a_crlf_shebang_breaks_them()


def test_githooks_crlf_guard_still_fires_outside_a_nested_checkout(
    probe_factory: Callable[..., Path],
) -> None:
    """SURVIVAL ARM, and the arm that proves the sweep got DEEPER, not just narrower.

    Before this slice `tests/test_line_endings.py` called
    `(REPO_ROOT / ".githooks").iterdir()` - one level, no recursion - so a CRLF
    file one directory down was invisible to it and this arm was RED. A shim that
    sources a helper out of a subdirectory would have carried the silent
    broken-shebang defect that guard exists to catch. The repair recurses AND
    excludes; this arm holds the recursion honest, and the arm above holds the
    exclusion honest.
    """
    from tests import test_line_endings

    probe_dir = probe_factory(
        GITHOOKS_DIR,
        nested_checkout=False,
        files={"lib/common.sh": b"#!/bin/sh\r\ntrue\r\n"},
    )
    planted = probe_dir / "lib" / "common.sh"

    checked = test_line_endings._githook_files()
    assert len(checked) > 0, "the repaired sweep of .githooks/ found nothing - zero out of zero is not a pass"
    assert planted in checked, "an ordinary subdirectory of .githooks/ must still be swept"

    with pytest.raises(AssertionError, match=r"has CRLF"):
        test_line_endings.test_the_githooks_shims_are_lf_because_a_crlf_shebang_breaks_them()


# ---------------------------------------------------------------------------
# The predicate itself, and the anti-drift arm
# ---------------------------------------------------------------------------


def test_the_predicate_excludes_both_signals_and_nothing_else(tmp_path: Path) -> None:
    """Aimed at the predicate, in `tmp_path`, touching no real tree.

    Four cases, because three of them are the ways an over-eager exclusion goes
    wrong: it must not exclude the sweep root itself, must not exclude on the
    leaf's own name, and must not exclude an ordinary nested directory.
    """
    root = tmp_path / "sweep_root"
    (root / "ordinary").mkdir(parents=True)
    (root / "ordinary" / "kept.md").write_bytes(b"kept\n")
    (root / ".dotdir").mkdir()
    (root / ".dotdir" / "dropped.md").write_bytes(b"dropped\n")
    (root / "checkout").mkdir()
    (root / "checkout" / GIT_MARKER).write_bytes(b"gitdir: elsewhere\n")
    (root / "checkout" / "dropped.md").write_bytes(b"dropped\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "dropped.md").write_bytes(b"dropped\n")
    (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")

    kept = swept_files(root, "*")
    assert len(kept) > 0, "the predicate dropped everything - zero out of zero is not a pass"
    assert root / "ordinary" / "kept.md" in kept, "an ordinary nested directory must be swept"
    assert root / ".gitattributes" in kept, "the leaf's own name must never decide exclusion"
    for dropped in (
        root / ".dotdir" / "dropped.md",
        root / "checkout" / "dropped.md",
        root / "__pycache__" / "dropped.md",
    ):
        assert dropped not in kept, f"{dropped} should have been excluded"

    # A checkout marked by a `.git` DIRECTORY rather than a worktree's `.git`
    # file must be excluded too - `.exists()` covers both, `.is_file()` would not.
    directory_marked = tmp_path / "dir_marked"
    (directory_marked / "checkout" / GIT_MARKER).mkdir(parents=True)
    (directory_marked / "checkout" / "dropped.md").write_bytes(b"dropped\n")
    assert swept_files(directory_marked, "*.md") == []


def test_a_path_outside_the_sweep_root_is_rejected_rather_than_silently_kept(tmp_path: Path) -> None:
    """The loop walks parents until it reaches `root`. A path that is not under
    `root` would otherwise walk to the filesystem root and return False, quietly
    reporting "not excluded" about a question it could not answer."""
    root = tmp_path / "sweep_root"
    root.mkdir()
    stray = tmp_path / "elsewhere" / "file.md"
    stray.parent.mkdir()
    stray.write_bytes(b"stray\n")
    with pytest.raises(ValueError, match=r"is not inside"):
        excluded_from_repo_sweep(stray, root)


def test_all_four_repaired_guards_share_one_predicate_object() -> None:
    """Four copies of a skip list are four chances to drift apart invisibly.

    Identity, not equality: a module that grew its own look-alike helper would
    still satisfy an equality check on the results while diverging on the next
    case nobody thought to test.
    """
    from tests import (
        test_docs_consistency,
        test_goal_spec,
        test_licence_posture,
        test_line_endings,
    )

    modules = (test_docs_consistency, test_goal_spec, test_licence_posture, test_line_endings)
    assert len(modules) == 4, "the blindness measurement named four guards; this arm must cover all four"
    for module in modules:
        assert module.swept_files is swept_files, (
            f"{module.__name__} does not use the shared sweep helper, so its exclusion "
            "can drift away from the other three without anything going red"
        )


# ---------------------------------------------------------------------------
# THE OVER-EXCLUSION AXIS. The name rule is EXACT, and the specimens that
# prove it are DERIVED rather than typed.
# ---------------------------------------------------------------------------
#
# WHY THESE ARMS EXIST, AND WHAT THE ARM ABOVE CANNOT SEE.
# `test_the_predicate_excludes_both_signals_and_nothing_else` builds its
# fixture from LITERAL skip names - `.dotdir`, `__pycache__`, a real `.git`
# marker. Every one of those is excluded under the shipped rule AND under a
# widened one, so that arm pins the predicate's ANSWERS on names it already
# knows and cannot see the match RULE widen underneath it. Measured on this
# slice's base: replacing the exact-name match in `core/repo_sweep.py` with a
# `startswith` over `SWEEP_SKIP_DIRS` left the whole `tests` suite at its
# baseline of 3162 passed, 4 skipped. Silent - and an over-exclusion that
# silently stops sweeping real content passes every bad-thing-is-gone arm in
# this file while destroying the four guards they exist to protect.
#
# WHY THE TREE ITSELF CANNOT SUPPLY THE SPECIMENS. No tracked directory name
# in this checkout has a skip name as a STRICT PREFIX, and none contains the
# `.git` marker string without a leading dot. So a sweep of real names is
# vacuous on exactly the axis that went silent, and the specimens have to be
# MANUFACTURED from the skip table instead of observed. That is the governing
# finding here: a safe list admitted on reasoning is a hole with a comment
# over it, because every POSITIVE specimen gets measured and no NEGATIVE one
# does.

#: Suffixes that turn a skip name into a DIFFERENT, legitimate directory name.
#: Chosen so the GENERATED set contains the five specimens an adversary named
#: against this predicate, rather than those five being typed in as the set.
_EXTENDING_SUFFIXES = ("er", "ribution", "lab", "-notes", "_readme", "s", "2")

#: Wrappers that bury a skip name in the MIDDLE of a name, so the specimen set
#: discriminates a substring rule and not only a prefix one. Applied to the
#: dotted spelling as well, which is how `legacy_.git` - a name that contains
#: the whole `.git` string yet does not start with a dot - enters the set.
_BURYING_WRAPPERS = ("legacy_{}", "{}_archive", "vendor_{}_snapshot")

#: The five an adversary named against this predicate. This is NOT the
#: specimen set - it is a PIN ON THE GENERATOR. A future edit that narrowed
#: `_EXTENDING_SUFFIXES` would quietly shrink the population the arm below
#: measures, which is the shrunk-population failure this tree has already
#: recorded; naming these five makes that edit go red instead.
_ADVERSARY_NAMED_SPECIMENS = (
    "builder",
    "distribution",
    "venv-notes",
    "node_modules_readme",
    "gitlab",
)


def _names_that_merely_resemble_a_skip_name() -> list[str]:
    """Directory names that RESEMBLE a skip name and must still be swept.

    Generated from `SWEEP_SKIP_DIRS` itself, so the population grows the day a
    name is added to the owner table and cannot be left behind by a reader who
    forgets to extend a hand-written list.

    Two spellings of every skip name feed the generator - the name as stored
    and the name with its leading dots stripped - because a dot-prefixed skip
    name extended into `.gitlab` is STILL legitimately excluded by this
    predicate's dot rule and would be a false specimen. The dot-stripped
    `gitlab` is the real one.

    Anything that comes out dot-prefixed, or that lands back on a skip name,
    is filtered out: both are excluded on their own account and neither says
    anything about the width of the match.
    """
    candidates: set[str] = set()
    for skip in SWEEP_SKIP_DIRS:
        bare = skip.lstrip(".")
        if not bare:
            continue
        for suffix in _EXTENDING_SUFFIXES:
            candidates.add(bare + suffix)
            candidates.add(skip + suffix)
        for wrapper in _BURYING_WRAPPERS:
            candidates.add(wrapper.format(bare))
            candidates.add(wrapper.format(skip))
    return sorted(
        name
        for name in candidates
        if not name.startswith(".") and name.casefold() not in SWEEP_SKIP_DIRS
    )


def test_the_foreign_name_rule_is_exact_and_never_a_prefix_or_a_substring() -> None:
    """THE SURVIVOR ARM for `core/repo_sweep.py`'s own layer.

    `core/walkprune.py`'s docstring already warns that a substring or prefix
    match would eat `pycache`, `git`, `venv-notes` and `node_modules_readme`
    while passing every other arm, and `tests/test_walkprune.py` carries a
    survivor arm at THAT layer. `is_foreign_dir_name` is a SECOND match rule
    composed on top of it - a dot test ORed with the table - and until this arm
    the new layer had no survivor arm of its own.

    The three discrimination checks below are the non-vacuity: they prove the
    generated population really does separate the shipped rule from each
    widened one. Without them an empty or badly chosen specimen set would
    score a perfect pass while testing nothing.
    """
    specimens = _names_that_merely_resemble_a_skip_name()

    assert len(specimens) >= 50, (
        f"the generator produced only {len(specimens)} specimens, too few to cover the "
        f"skip table - this arm has been quietly emptied: {specimens}"
    )
    missing = [name for name in _ADVERSARY_NAMED_SPECIMENS if name not in specimens]
    assert missing == [], (
        f"the generator no longer produces the specimens an adversary named against "
        f"this predicate, so its population has shrunk out from under this arm: {missing}"
    )

    killed_by_a_prefix_rule = [
        name for name in specimens if any(name.startswith(skip) for skip in SWEEP_SKIP_DIRS)
    ]
    assert killed_by_a_prefix_rule, (
        "no specimen starts with a skip name, so this arm could not tell an exact "
        "match from a startswith match and is vacuous on the axis it exists for"
    )
    killed_by_a_substring_rule = [
        name for name in specimens if any(skip in name for skip in SWEEP_SKIP_DIRS)
    ]
    assert killed_by_a_substring_rule, (
        "no specimen contains a skip name, so this arm could not tell an exact match "
        "from a substring match"
    )
    killed_by_a_dot_stripped_prefix_rule = [
        name
        for name in specimens
        if any(name.startswith(skip.lstrip(".")) for skip in SWEEP_SKIP_DIRS)
    ]
    assert killed_by_a_dot_stripped_prefix_rule, (
        "no specimen starts with a DOT-STRIPPED skip name, so a rule that folded "
        "`.git` to `git` before matching would pass this arm unnoticed"
    )

    swallowed = sorted(name for name in specimens if is_foreign_dir_name(name))
    assert swallowed == [], (
        f"{len(swallowed)} legitimate directory names were excluded as collateral, so the "
        f"name match has widened past an exact match and every guard that walks through "
        f"it has silently stopped sweeping real content: {swallowed}"
    )


def test_no_derived_specimen_names_real_content_in_this_checkout() -> None:
    """The specimens are MANUFACTURED, and this is what says so out loud.

    A specimen that happened to name a directory this tree really owns would
    make the arm above a statement about today's checkout rather than about
    the match rule, and would start failing for a reason that has nothing to
    do with the predicate. It would also mean the planted-probe arms earlier
    in this file could collide with it.
    """
    specimens = _names_that_merely_resemble_a_skip_name()
    assert specimens, "the generator is empty, so this control checks nothing"

    colliding = sorted(name for name in specimens if (REPO_ROOT / name).exists())
    assert colliding == [], (
        f"these generated specimens name real entries at the repository root, so the arm "
        f"above is coupled to this checkout rather than to the rule: {colliding}"
    )


def test_the_foreign_name_rule_still_catches_every_name_it_owns() -> None:
    """THE PAIRED POSITIVE ARM.

    A survivor arm on its own is satisfied by a predicate that excludes
    NOTHING, which is the opposite over-correction and would reinstate the
    worktree blindness this whole module repaired. A sweep needs both guards
    or neither is worth anything.

    The uppercase pass is the NTFS fold: `.GIT` and `__PYCACHE__` are the same
    directories as `.git` and `__pycache__` to every Windows API and different
    strings to Python's `in`.
    """
    assert len(SWEEP_SKIP_DIRS) >= 10, (
        f"the skip table is near-empty, so this arm is vacuous: {sorted(SWEEP_SKIP_DIRS)}"
    )
    escaped = sorted(
        name
        for skip in SWEEP_SKIP_DIRS
        for name in (skip, skip.upper())
        if not is_foreign_dir_name(name)
    )
    assert escaped == [], f"these names the predicate owns were not excluded: {escaped}"
