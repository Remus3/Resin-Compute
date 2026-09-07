"""The exclusion the four blind root-walking guards were missing, and its proof.

WHAT THIS FIXES. `tests/test_guard_worktree_blindness.py` measured, against all
39 `test_*.py` modules in this directory, that exactly four of them recurse a
directory tree anchored at the repository root while carrying no skip list of
any kind - not a dot-directory filter, not even the conventional
`__pycache__`/`.git` denylist:

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
modules import `swept_files()` from here, and
`test_all_four_repaired_guards_share_one_predicate_object` below pins that they
share ONE function object rather than four look-alikes.

WHY THIS MODULE AND NOT `tests/conftest.py`. `conftest.py` is the natural home
and is where a follow-up slice should move it. It was outside this slice's
declared write-list, and editing a file off the write-list is the exact thing
that makes parallel slices collide, so the helper lives here for now. Nothing
about the helper depends on the module it sits in.

NO CIRCULAR IMPORT. This module imports the four guard modules INSIDE test
bodies, never at module scope, so the four can import `swept_files` from here at
module scope without a cycle.

WHAT COUNTS AS "NOT THIS TREE'S OWN CONTENT". Two independent signals, both
required because neither covers the other:

  - a DOT-DIRECTORY anywhere between the sweep root and the file. This tree's
    own worktrees live at `.claude/worktrees/`, one full copy per in-flight
    agent, and `tests/test_loop_concurrency.py::_SWEEP_SKIP_DIRS` already
    excludes dot-directories wholesale for exactly that reason. That is the
    shape this slice was told to copy, and it is copied rather than reinvented.
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
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
GITHOOKS_DIR = REPO_ROOT / ".githooks"

#: Directory names a repository sweep must not descend into, on top of the
#: dot-directory rule. Copied from `tests/test_loop_concurrency.py`'s
#: `_SWEEP_SKIP_DIRS`, which is the one root-walking guard in this directory
#: that already carried an exclusion when this slice was written.
SWEEP_SKIP_DIRS = frozenset({"__pycache__", "node_modules", "venv", "build", "dist"})

#: What a linked git worktree puts at its own root: a FILE, not a directory,
#: holding a `gitdir:` pointer back to the superproject. Tested with
#: `.exists()` so both that file and an ordinary `.git` directory are caught.
GIT_MARKER = ".git"

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
# The predicate the four repaired guards share
# ---------------------------------------------------------------------------


def excluded_from_repo_sweep(path: Path, root: Path) -> bool:
    """Is `path` inside something that is not this working tree's own content?

    Only ANCESTOR DIRECTORIES strictly between `root` and `path` are consulted.
    The leaf's own name never decides, so a tracked file legitimately named
    `.gitattributes` is swept, and `root` itself never decides, so a sweep whose
    root is itself a dot-directory - `.githooks/`, which
    `tests/test_line_endings.py` walks - does not exclude its entire corpus on
    the first step.
    """
    current = path.parent
    while current != root:
        parent = current.parent
        if parent == current:
            raise ValueError(f"{path} is not inside {root}, so it cannot be swept from there")
        if current.name.startswith(".") or current.name in SWEEP_SKIP_DIRS:
            return True
        if (current / GIT_MARKER).exists():
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


# ---------------------------------------------------------------------------
# Probe planting
# ---------------------------------------------------------------------------


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
    created: list[Path] = []

    def _plant(parent: Path, *, nested_checkout: bool, files: dict[str, bytes]) -> Path:
        probe_dir = parent / f"{_PROBE_PREFIX}{uuid.uuid4().hex}"
        probe_dir.mkdir(parents=True)
        created.append(probe_dir)
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
        return probe_dir

    try:
        yield _plant
    finally:
        for probe_dir in created:
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
