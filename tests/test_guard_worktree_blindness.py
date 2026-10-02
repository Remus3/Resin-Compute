"""Regression proof for a sibling's inbox finding on nested worktrees blinding guards.

Source: the 2026-09-07-0710 note in `moon_sync_inbox/` from Sibling-C,
section 5 (2026-09-07T07:10). Codenames resolve only in the gitignored
`ops/moon_sync_repos.json`. After merging a worktree agent's branch, that
sibling left the merged worktree on disk inside the repo, and two
guards that `rglob` from the repo root scanned the second full copy of the
tree and went red on content that was not theirs. It measured 10 of 15
root-walking guards in its own `tests/` with no worktree exclusion, and only
2 of those 10 actually fired that night because only 2 happened to match
content in the duplicate - the other 8 were latent, waiting for the day their
particular content showed up inside a stray worktree.

WHAT COUNTS AS "ROOT-WALKING", which is the only part of the original census
that has not rotted and is therefore the only part restated. A module is
root-walking when it recurses a directory tree - `Path.rglob`, `os.walk`, a
`**` glob, or a *recursive* `Path.iterdir` loop - from a path anchored at
`REPO_ROOT`. `ast.walk` does not count: it walks a parsed syntax tree, never
the filesystem. `tmp_path.rglob()` does not count: `tmp_path` is pytest's own
throwaway directory outside the repository and cannot contain a worktree. A
corpus built from `git ls-files` is walked by GIT rather than by this process
and is immune by construction - this tree already made that exact fix once,
for `mypy.ini`'s scope guard in commit b55825e, because mypy walks the
filesystem while git does not.

THE CENSUS THAT USED TO SIT HERE IS GONE, AND THAT IS THE REPAIR RATHER THAN
AN OMISSION. This docstring carried a three-row table - so many guards
excluded, so many not excluded, so many modules examined, with the three
figures footed to a total. Every one of those numbers was wrong by the time
anyone read it again:

  - the four guards the table listed as carrying no skip list "of any kind"
    were REPAIRED. All four now import one shared `swept_files()` from
    `tests/test_guard_worktree_exclusion.py`, and that module's
    `test_all_four_repaired_guards_share_one_predicate_object` pins the
    binding by OBJECT IDENTITY, so a module growing its own look-alike helper
    goes red rather than drifting quietly. The table went on describing the
    defect for weeks after the defect was closed.
  - the module count had moved by more than a factor of two.
  - nothing anywhere asserted any of the three numbers, so none of them could
    go red when it rotted. A figure in a docstring is unguarded by
    construction.

WHY THE REMEDY IS TO DROP THE NUMBERS RATHER THAN REFRESH THEM, which is a
DECISION and the thing a later reader must not quietly reverse by helpfully
typing a fresh count back in. Restating a census buys exactly one edit's worth
of accuracy and then begins rotting again on the next commit, and this tree
has the receipts: a sibling guard module's figures were corrected and rotted a
second time, and the judgement reached there - drop the count, do not restate
it - is the judgement applied here. This tree also records, as an expensive
finding, a slice dispatched against a defect the ledger had already recorded
as closed; a stale present-tense table is precisely the artifact that causes
that. A count that no assertion reads is not documentation, it is a
time-delayed false statement.

WHAT REPLACES IT. The structural facts, which do not rot, plus a RECIPE for
re-deriving any figure a reader actually needs:

  - the exclusion predicate and its two signals live in
    `tests/test_guard_worktree_exclusion.py::excluded_from_repo_sweep`, and
    the drop-in sweep helper beside it is `swept_files()`. That module's own
    arms are where the repair is proved, per guard, with a matched
    neighbours-survive partner.
  - to re-derive the walker population, do not grep for `rglob`: a textual
    sweep cannot tell a repo-anchored root from a `tmp_path` one, and it is
    blind to a module that reaches a walk through a helper defined elsewhere -
    which is now the common case, since the four repaired guards own no walk
    token at all. Wrap `Path.rglob`, `Path.glob`, `Path.walk`, `Path.iterdir`,
    `os.walk`, `os.scandir`, `os.listdir`, `glob.glob` and `glob.iglob`, run
    `python -m pytest tests`, record for each call both the resolved root and
    EVERY repo module on the stack, then keep the calls whose root is under
    `REPO_ROOT` and not under the temp directory. Attributing such a call to
    only the innermost frame is the trap: it credits the walk to whichever
    module defines the helper and reports the real callers as clean.
  - that instrument has its own blind spot, and it is the opposite one - a
    walk on a code path the suite never executes is invisible to it. Neither
    method is sufficient alone, which is the reason for naming both.

A DATED READING, stamped as a reading and not as a constant. Measured
2026-10-02 at b8f2932 by the runtime method above, over `python -m pytest
tests`: exactly one module under `tests/` recursed from the TRUE repository
root while carrying no `.git`-marker exclusion, and it was
`tests/test_responder_task_argv.py::_repo_python_files`. It was repaired in
the same slice that rewrote this docstring and now binds the same shared
`swept_files()` the other four do. This paragraph is a snapshot of one run on
one day; re-run the recipe before citing it, and do not treat its absence of
other names as a statement about code that run did not execute.

THE HONEST CAVEAT ON THE FOUR REPAIRED GUARDS, kept because it is still true
and still load-bearing. This repo's own worktrees live at `.claude/worktrees/`,
a SIBLING of `data/` and `docs/`, never a descendant of either. So those four
guards could not have reproduced the sibling's exact scenario - a merged
worktree agent's branch left on disk and scanned as a duplicate checkout -
unless a worktree were created inside `data/` or `docs/`, which is not this
repo's convention. That never made them safe: with no exclusion logic at all,
ANY nested directory dropped into their scanned subtree was swept as this
repository's own content. The repair addressed that broader, true property,
and the tests below probe it directly rather than asserting the narrower
worktree-specific claim this tree's own history does not support.

PART B PROOF STRATEGY. Two tests below each plant a real nested directory
under the repo root (never committed, always removed) and call the SHIPPED
guard function - unmodified, imported directly, not reimplemented - both
before and after planting.

`test_licence_posture_bulk_dump_guard_still_sweeps_an_unmarked_nested_directory`
WAS this file's vulnerability proof and IS NOW THE REPAIR'S NEIGHBOURS-SURVIVE
ARM. The test body did not change; what it means did. Its probe carries NO
`.git` marker and NO dot prefix, so under the repaired `swept_files()` it is
still, deliberately, this repository's own content - and the guard still goes
red on it. Before the repair that redness was the defect. After the repair it
is the boundary: it proves the exclusion did not buy its cleanliness by
excluding everything, which is the failure mode this tree's two-guards rule
for any sweep exists to catch. The arm was RENAMED rather than deleted,
because the old name - "is blind to a nested checkout" - asserts something the
probe cannot show: an unmarked directory is not a checkout, and after the
repair a real `.git`-marked checkout is NOT swept. A test name is an
assertion that no runner checks, so a name outrunning its evidence is the same
defect as an assert message doing it.

WHERE THE CHECKOUT CASE IS ACTUALLY PROVED, since this module no longer claims
to: `tests/test_guard_worktree_exclusion.py` plants `.git`-marked probes
against each repaired guard and carries the matched outside-the-checkout
partner for every one of them.

`test_lane_declarations_excludes_a_nested_dot_directory_probe` is the CONTRAST
arm, and its name is accurate in a way the sentence that used to describe it
was not. It proves `_lane_declarations` excludes a DOT-PREFIXED probe, which
is the only thing the probe can show. The older wording called that guard "the
one guard already excluding nested directories", and that is broader than the
evidence: measured 2026-10-02 at b8f2932 by planting a NON-dot directory
carrying a `.git` file at the repository root, `_lane_declarations` walked
straight into it and surfaced its `config_nested.json`. Its filter is
dot-prefix plus `_SWEEP_SKIP_DIRS` and carries no `.git`-marker test, so it
covers `.claude/worktrees/` by name and a non-dot checkout not at all. The arm
below is still worth having - it proves the dot-directory half of the fix
pattern genuinely holds rather than being assumed from reading the source -
but it is a statement about dot-directories and must not be read as a clean
bill for that guard.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from tests import test_licence_posture, test_loop_concurrency
from tests.test_guard_worktree_exclusion import swept_files

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

#: One byte past the ceiling `test_licence_posture.py`'s
#: `test_no_data_file_is_large_enough_to_be_a_bulk_dump` pins as a local
#: variable (`limit = 64 * 1024`). Copied as a literal rather than imported
#: because the guard does not expose that number as a module constant - it is
#: local to the test function - so this pins the SAME number the guard pins
#: and will fail loudly, rather than silently stop proving anything, if that
#: number ever changes without a matching update here.
OVERSIZE_BYTES = 64 * 1024 + 1

_PROBE_PREFIX = "wt_probe_"


@pytest.fixture
def worktree_probe_factory() -> Callable[..., Path]:
    """Yields a callable that plants one nested probe directory per call and
    guarantees every one of them is removed afterward, regardless of how the
    test that used it exits.

    WHY A FACTORY RATHER THAN A SINGLE FIXED FIXTURE. Both tests below need to
    call a real guard function TWICE - once before the probe exists (proving
    the guard is clean on this tree today, so a later failure is caused by the
    probe rather than by unrelated drift) and once after. That before/after
    shape only works if planting happens inside the test body, not in fixture
    setup, so the fixture hands back a planting function instead of an
    already-planted path.

    CLEANUP IS UNCONDITIONAL. The teardown after `yield` runs during pytest
    fixture finalization, which fires even when the test body raises - the
    same guarantee a plain `try/finally` gives, extended to cover every probe
    a single test plants. Each removal is verified with an explicit
    `assert not probe_dir.exists()`: a leftover probe directory inside `data/`
    or the repo root would itself become exactly the kind of stray nested
    content this file is about, and a second run of this suite - or any of
    the guards this file exercises - would then trip on residue from a first
    run that failed midway.

    NAMED TO NEVER COLLIDE. Every probe carries a fresh `uuid4().hex` suffix,
    so two probes from the same test, two concurrent test runs, and a probe
    racing an actual worktree merge cannot land on the same path.
    """
    created: list[Path] = []

    def _plant(parent: Path, *, dotdir: bool, files: dict[str, bytes]) -> Path:
        stem = f"{_PROBE_PREFIX}{uuid.uuid4().hex}"
        name = f".{stem}" if dotdir else stem
        probe_dir = parent / name
        probe_dir.mkdir(parents=True)
        for rel_path, content in files.items():
            target = probe_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        created.append(probe_dir)
        return probe_dir

    try:
        yield _plant
    finally:
        for probe_dir in created:
            if probe_dir.exists():
                # Deepest paths first, so a directory is always empty by the
                # time its own rmdir() runs.
                for path in sorted(
                    probe_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True
                ):
                    if path.is_dir() and not path.is_symlink():
                        path.rmdir()
                    else:
                        path.unlink()
                probe_dir.rmdir()
            assert not probe_dir.exists(), (
                f"cleanup left {probe_dir} behind - a stray probe directory "
                "inside the repository is exactly the defect this test is "
                "about, and this suite must never be the thing that leaves it"
            )


def test_licence_posture_bulk_dump_guard_still_sweeps_an_unmarked_nested_directory(
    worktree_probe_factory: Callable[..., Path],
) -> None:
    """THE REPAIR'S NEIGHBOURS-SURVIVE ARM, and the positive control that makes
    it mean something, in the same test.

    HISTORY, because the body is unchanged and only the meaning moved. This
    was written as a vulnerability proof: the guard carried no skip list, so a
    nested directory was swept as this repository's own content. The guard has
    since been repaired and now sweeps through the shared
    `tests/test_guard_worktree_exclusion.py::swept_files`.

    WHAT IT PROVES NOW. The probe planted here has NO `.git` marker and NO dot
    prefix, and the repaired predicate deliberately treats such a directory as
    this tree's own content. So the guard must STILL go red on it. An
    exclusion that scored a perfect result on the checkout case by excluding
    every nested directory would fail right here, which is the second of the
    two guards this tree requires of any sweep - one that the bad thing is
    gone, one that the legitimate neighbours survived.

    `tests/test_licence_posture.py::test_no_data_file_is_large_enough_to_be_a_bulk_dump`
    sweeps `data/` for any file over 64 KiB, on the theory that a vendored
    dataset arrives as a big file rather than announced. This plants an
    oversized file inside `wt_probe_<uuid>/nested_checkout/data/` - a path
    SHAPED like a nested checkout's own data folder but carrying none of the
    markers that make a directory one - and calls the REAL guard function,
    unmodified and imported directly, before and after.

    BEFORE: the guard must pass on the tree as it stands, or a failure after
    planting would prove nothing about the plant - it could be pre-existing
    drift this test happened to catch by coincidence.

    AFTER: the guard must fail, and specifically on the message this guard
    emits, not some other assertion in the same function.

    The checked-count assertion below is the tree's own standing rule (see
    `tests/test_mypy_scope.py`, "Zero out of zero reads as a pass"), applied
    to THIS probe: before trusting the guard's verdict, this proves the probe
    file is actually inside the corpus the guard walks, so a pass could not be
    explained by the probe having landed somewhere the sweep never reaches.

    THE CORPUS IS THE GUARD'S OWN, NOT A NAIVE RGLOB. This assertion used to
    be written against `DATA_DIR.rglob("*")`, which was the same thing as the
    guard's corpus only while the guard had no exclusion. It is not the same
    thing now. A membership proof against a corpus the guard does not use
    would keep passing if `swept_files` ever started dropping this probe, and
    would then be asserting the opposite of what it says.
    """
    # BEFORE: the shipped guard, called for real, is clean on this tree today.
    test_licence_posture.test_no_data_file_is_large_enough_to_be_a_bulk_dump()

    probe_dir = worktree_probe_factory(
        DATA_DIR,
        dotdir=False,
        files={"nested_checkout/data/oversized_dump.bin": b"\x00" * OVERSIZE_BYTES},
    )
    planted = probe_dir / "nested_checkout" / "data" / "oversized_dump.bin"

    # Checked count, asserted before the offender check, every time.
    scanned = swept_files(DATA_DIR)
    checked = len(scanned)
    assert checked > 0, "the sweep of data/ found nothing to check - zero out of zero is not a pass"
    assert planted in scanned, (
        f"the planted probe at {planted} is not inside the corpus the repaired "
        "guard actually sweeps, so this test would prove nothing about whether "
        "an unmarked nested directory still survives the exclusion"
    )
    assert planted.stat().st_size > 64 * 1024, "the planted file is not actually oversized"

    # AFTER: the identical guard function, called again with nothing else
    # changed, now fails - and fails on ITS OWN message, not a stray one.
    with pytest.raises(AssertionError, match=r"suspiciously large files under data/"):
        test_licence_posture.test_no_data_file_is_large_enough_to_be_a_bulk_dump()


def test_lane_declarations_excludes_a_nested_dot_directory_probe(
    worktree_probe_factory: Callable[..., Path],
) -> None:
    """CONTRAST ARM: the one guard this tree measured as already excluding
    nested directories, proved to still do so - not assumed from reading its
    source, exercised against a real planted probe shaped the same way as the
    vulnerability proof above.

    `tests/test_loop_concurrency.py::_lane_declarations` walks `config*.json`
    files under a root and reports any `max_concurrent_lanes` value that
    disagrees with the three-repo agreement. Its docstring at the skip-list
    definition names `.claude/worktrees/` as the reason dot-directories are
    excluded wholesale. This plants a dot-prefixed probe directory
    (`.` + `wt_probe_<uuid>`, the same shape a worktree checkout takes) at the
    REPO ROOT - where `_lane_declarations` is actually called from, via
    `ROOT` in `test_every_json_config_declaring_a_lane_count_declares_the_agreed_one` -
    holding a `config_probe.json` that declares a lane count disagreeing with
    `EXPECTED_LANES`.

    POSITIVE CONTROL FIRST: `_lane_declarations` is called pointed DIRECTLY at
    the probe directory. If that found nothing, the probe itself would be
    malformed - wrong filename pattern, wrong JSON shape - and the exclusion
    test below would prove nothing, because a scanner that never finds the
    file when aimed straight at it cannot demonstrate that aiming it elsewhere
    excludes the file on purpose rather than by accident.

    REAL USAGE SECOND: the identical function, called the way the shipped
    guard actually calls it - from the repository root - must not surface the
    probe's declaration at all, proving the dot-directory filter holds against
    a probe realistic enough to have just passed the positive control.
    """
    wrong_value = test_loop_concurrency.EXPECTED_LANES + 1
    probe_dir = worktree_probe_factory(
        REPO_ROOT,
        dotdir=True,
        files={
            "config_probe.json": json.dumps({"max_concurrent_lanes": wrong_value}).encode(
                "utf-8"
            )
        },
    )

    # POSITIVE CONTROL: checked count, asserted before the offender check.
    direct = test_loop_concurrency._lane_declarations(probe_dir)
    checked = len(direct)
    assert checked > 0, (
        "the probe's own config_probe.json was not found even when the scanner "
        "was pointed straight at the probe directory - the probe is malformed "
        "and proves nothing about exclusion"
    )
    assert direct.get("config_probe.json") == wrong_value, (
        f"the guard read {direct.get('config_probe.json')!r} back from the probe's own "
        f"config_probe.json; expected the planted disagreeing value {wrong_value!r}"
    )

    # REAL USAGE: the same scanner, run the way the shipped guard runs it,
    # must not have descended into the dot-directory at all.
    found_from_root = test_loop_concurrency._lane_declarations(REPO_ROOT)
    leaked = [name for name in found_from_root if probe_dir.name in name]
    assert not leaked, (
        f"the dot-directory exclusion in _lane_declarations did not hold: {leaked} "
        f"leaked from a probe that the positive control proved was readable"
    )
