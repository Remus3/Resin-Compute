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

WHAT THIS TREE MEASURED, independently, against every `test_*.py` under
`tests/` (39 modules; `conftest.py` and `__init__.py` are not test modules and
carry no filesystem walk of their own; `tests/_parked/test_engines_costs.py.parked`
is not collected - it does not end in `.py`). A module counts as "root-walking"
when it recurses a directory tree - `Path.rglob`, `os.walk`, or a *recursive*
`Path.iterdir` loop - starting from a path anchored at `REPO_ROOT`
(`Path(__file__).resolve().parent.parent` or `.parents[1]`, the convention
every module in this directory uses). `ast.walk` does not count - it walks a
parsed syntax tree, never the filesystem, and several guards here use it to
inspect one already-read source file. `tmp_path.iterdir()` / `tmp_path.rglob()`
do not count either - `tmp_path` is pytest's own throwaway directory outside
the repository and cannot contain a worktree. A corpus built from
`git ls-files` is walked by GIT, not by this process, and is immune by
construction - this tree already made that exact fix once, for `mypy.ini`'s
scope guard in commit b55825e, because mypy walks the filesystem while git
does not.

    root-walking-and-excluded:      1   tests/test_loop_concurrency.py,
                                         `_lane_declarations()`, `os.walk(ROOT)`
                                         with an explicit dot-directory and
                                         `_SWEEP_SKIP_DIRS` filter, documented
                                         at the definition as covering
                                         `.claude/worktrees/` by name.
    root-walking-and-NOT-excluded:  4   tests/test_docs_consistency.py
                                         (`(REPO_ROOT / "docs").rglob("*.md")`,
                                         four call sites, same pattern),
                                         tests/test_goal_spec.py
                                         (`DATA_DIR.rglob("*")`),
                                         tests/test_licence_posture.py
                                         (`(REPO_ROOT / "data").rglob(...)`,
                                         four call sites), tests/test_line_endings.py
                                         (`(REPO_ROOT / ".githooks").iterdir()`,
                                         one level, no recursion needed to be
                                         exposed since `.githooks/` holds no
                                         subdirectories today). None of the
                                         four carries a skip list of any kind -
                                         not a dot-directory filter, not even
                                         the conventional `__pycache__`/`.git`
                                         denylist.
    not-root-walking:              34   everything else - `tmp_path`-scoped
                                         iterdir/rglob (test_bootstrap.py,
                                         test_core_atomic_io.py,
                                         test_core_state_io.py,
                                         test_headless_jobs.py,
                                         test_headless_runner.py,
                                         test_ops_health.py,
                                         test_publish_next_session.py,
                                         test_watch_inbox.py - the last of
                                         these rglobs a fixture-built `drop`
                                         directory under `tmp_path`, not the
                                         repository), `ast.walk` over a parsed
                                         tree rather than a directory
                                         (test_headless_persist_state.py,
                                         test_make_shortcut.py, test_ports.py,
                                         test_session_hooks.py), and every
                                         guard whose corpus is `git ls-files`
                                         (test_ports.py's own Python sweep and
                                         test_machine_identity.py both moved to
                                         this on purpose; test_ports.py's
                                         `test_the_swept_file_list_is_git_derived_and_not_a_disk_walk`
                                         is that repo's own regression arm on
                                         the identical defect class this file
                                         is about), plus every remaining module
                                         with no filesystem walk at all.
                                    ---
                                    39  test_*.py modules examined

    1 + 4 + 34 = 39.

THE HONEST CAVEAT ON THAT FRAMING, stated rather than smoothed over. This
repo's own worktrees live at `.claude/worktrees/`, a SIBLING of `data/` and
`docs/`, never a descendant of either. So the four NOT-excluded guards above
cannot reproduce the sibling's exact scenario - "a merged worktree agent's branch left
on disk got scanned as a duplicate checkout" - unless a worktree, or literally
anything else, were ever created inside `data/` or `docs/`, which is not this
repo's convention and has never happened per `git worktree list` at the time
of writing (one worktree: the primary checkout itself). That does not make
these four guards safe. They have no exclusion logic of any kind, so ANY
nested directory dropped into their scanned subtree - a worktree, a stray
extraction, an editor's backup folder, anything - is swept as if it were this
repository's own tracked content. This test file proves that broader, true
property directly with a real nested probe, rather than asserting the
narrower worktree-specific claim that this tree's own history does not
support.

PART B PROOF STRATEGY. Two tests below each plant a real nested directory
under the repo root (never committed, always removed) and call the SHIPPED
guard function - unmodified, imported directly, not reimplemented - both
before and after planting. `test_licence_posture_bulk_dump_guard_is_blind_to_a_nested_checkout`
is the POSITIVE CONTROL AND THE VULNERABILITY PROOF in one: the guard passes
on the clean tree, then fails once the planted file exists, proving both that
the planted content is well-formed (it really does trip the guard when the
guard is pointed at it) and that the guard cannot tell "my own data/" from "a
nested checkout's data/ that happens to be lying around" - the sibling's defect,
reproduced against a real guard in this tree rather than a hypothetical one.
`test_lane_declarations_excludes_a_nested_dot_directory_probe` is the CONTRAST
arm: the one guard this tree measured as already excluding nested
directories, proved to still do so against the identical style of probe, so
this file is not merely finding defects but also proving the fix pattern
already present in `test_loop_concurrency.py` actually works.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from tests import test_licence_posture, test_loop_concurrency

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


def test_licence_posture_bulk_dump_guard_is_blind_to_a_nested_checkout(
    worktree_probe_factory: Callable[..., Path],
) -> None:
    """VULNERABILITY PROOF, and the positive control that makes it mean
    something, in the same test.

    `tests/test_licence_posture.py::test_no_data_file_is_large_enough_to_be_a_bulk_dump`
    rglobs `data/` for any file over 64 KiB, on the theory that a vendored
    dataset arrives as a big file rather than announced. It carries no skip
    list at all. This plants an oversized file inside a directory shaped like
    a nested checkout's own `data/` folder (`_wt_probe_<uuid>/nested_checkout/data/`)
    and calls the REAL guard function, unmodified and imported directly,
    before and after.

    BEFORE: the guard must pass on the tree as it stands, or a failure after
    planting would prove nothing about the plant - it could be pre-existing
    drift this test happened to catch by coincidence.

    AFTER: the guard must fail, and specifically on the message this guard
    emits, not some other assertion in the same function.

    The checked-count assertion below is the tree's own standing rule (see
    `tests/test_mypy_scope.py`, "Zero out of zero reads as a pass"), applied
    to THIS probe: before trusting the guard's verdict, this proves the probe
    file is actually inside the corpus a naive full sweep of `data/` would
    walk over, so a pass could not be explained by the probe having landed
    somewhere the sweep never reaches.
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
    scanned = [p for p in DATA_DIR.rglob("*") if p.is_file()]
    checked = len(scanned)
    assert checked > 0, "the sweep of data/ found nothing to check - zero out of zero is not a pass"
    assert planted in scanned, (
        f"the planted probe at {planted} is not inside data/'s own recursive "
        "sweep, so this test would prove nothing about the guard's blindness"
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
