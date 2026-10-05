"""Guards for this tree's adoption of the kit's lane layer (`fleet_lanes.py`).

The ruling recorded in CLAUDE.md ("Session checklist - FLEET-COMMON item 13
in this tree") fixes the lane contract for a FUTURE lane driver: `run_lane`
with cap=`core.config.LANE_CAP`, cwd = the claim's worktree,
`spawn(governor='queued')`, progress `lane-<i>.json` under the MAIN checkout.
No lane driver exists yet, so these arms pin the parts that can be pinned
now, and none of them creates a lane lock or a worktree:

  1. CAP BOUNDS. LANE_CAP is accepted by the kit's own `lane_cap()` unchanged,
     and fits both the kit's per-repo maximum and the governor width.
  2. NO LANE-LOCK WRITER OUTSIDE THE KIT. The lane locks under
     `ops/loop/control/lanes/` are the kit's on-disk protocol; a second writer
     spelling that path itself would bypass its mutex and its ABA guard. The
     detector runs over the tracked `.py` corpus, fires on the kit itself (a
     checked count above zero) and on a planted positive.
  3. THE LANE WORKTREE IS OUTSIDE THE ROOT AND IS NOT CREATED by computing it.
  4. NO MODULE BOTH HOLDS A SLOT AND SPAWNS. The kit's rule is one governor
     slot per executor call, taken by `spawn(governor=...)` OR by an existing
     `slots.hold()`, never both - nesting two in one lane deadlocks three
     lanes against a width of three.

The corpus is `git ls-files`, never an rglob: a leftover linked worktree
under the root would otherwise be scanned as a second copy of the tree.
"""
from __future__ import annotations

import importlib
import re
import subprocess
from pathlib import Path
from typing import Any

from core.config import LANE_CAP, MAX_CONCURRENT_LANES
from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Loaded by importlib and typed Any, as every caller of the vendored kit in
#: this tree does: the kit is outside the mypy roots and is never edited here.
lanes: Any = importlib.import_module("ops.fleet_kit.fleet_lanes")

KIT_DIR = "ops/fleet_kit/"

#: The lane-lock directory spelled as a path, either separator, or the kit's
#: own constant name. Built from pieces so this module's source does not match
#: its own detector.
_LANE_LOCK_PATH = re.compile(
    "control" + r"[/\\]+" + "lanes" + r"\b" + "|" + r"\b" + "LANES" + "_REL" + r"\b"
)

_SLOT_HOLD = re.compile(r"\bslots(?:_mod)?\s*\.\s*hold\s*\(")
_KIT_SPAWN = re.compile(r"\b(?:kit|fleet_headless)\s*\.\s*spawn\s*\(")


def _tracked_py() -> list[str]:
    require_git_repository()
    out = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _read(rel: str) -> str | None:
    try:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def lane_lock_writers(sources: dict[str, str]) -> tuple[list[str], list[str]]:
    """(kit files that spell the lane-lock path, non-kit files that do)."""
    kit_hits: list[str] = []
    offenders: list[str] = []
    for rel, text in sources.items():
        if not _LANE_LOCK_PATH.search(text):
            continue
        (kit_hits if rel.startswith(KIT_DIR) else offenders).append(rel)
    return kit_hits, offenders


def hold_and_spawn(sources: dict[str, str]) -> tuple[list[str], list[str]]:
    """(runtime modules that hold a slot, those that ALSO spawn).

    Runtime modules only: the kit itself and the tests are excluded, because
    the kit's docstrings name both calls and a test may drive either.
    """
    holders: list[str] = []
    both: list[str] = []
    for rel, text in sources.items():
        if rel.startswith(KIT_DIR) or rel.startswith("tests/") or rel == "conftest.py":
            continue
        if _SLOT_HOLD.search(text):
            holders.append(rel)
            if _KIT_SPAWN.search(text):
                both.append(rel)
    return holders, both


def _corpus() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in _tracked_py():
        if rel == "tests/test_fleet_lanes_adoption.py":
            continue
        text = _read(rel)
        if text is not None:
            out[rel] = text
    return out


# ---------------------------------------------------------------------------
# 1. Cap bounds
# ---------------------------------------------------------------------------


def test_the_lane_cap_is_within_the_kit_bounds() -> None:
    assert 1 <= LANE_CAP <= lanes.LANE_CAP_MAX
    assert LANE_CAP <= lanes.GOVERNOR_WIDTH
    assert LANE_CAP <= MAX_CONCURRENT_LANES
    assert lanes.lane_cap(LANE_CAP) == LANE_CAP, (
        "the kit clamps LANE_CAP, so a lane driver passing it would run fewer "
        "lanes than this tree declares"
    )


def test_the_kit_bounds_check_fires_on_an_out_of_range_cap() -> None:
    """Non-vacuity: `lane_cap` is a real bound, not an identity."""
    for bad in (0, lanes.LANE_CAP_MAX + 1):
        try:
            lanes.lane_cap(bad)
        except ValueError:
            continue
        raise AssertionError(f"lane_cap({bad}) was accepted")


# ---------------------------------------------------------------------------
# 2. No lane-lock writer outside the kit
# ---------------------------------------------------------------------------


def test_no_lane_lock_writer_outside_the_kit() -> None:
    sources = _corpus()
    assert len(sources) > 50, f"only {len(sources)} tracked .py files read - vacuous corpus"
    kit_hits, offenders = lane_lock_writers(sources)
    assert len(kit_hits) > 0, (
        "the detector found the lane-lock path in NO kit file, so a clean result "
        "below says nothing about the corpus"
    )
    assert "ops/fleet_kit/fleet_lanes.py" in kit_hits
    assert not offenders, (
        f"these tracked modules spell the kit's lane-lock path themselves: {offenders}. "
        "Lane locks are written only through fleet_lanes (run_lane / try_acquire_lane)."
    )


def test_the_lane_lock_detector_fires_on_a_planted_writer() -> None:
    planted = {
        "headless/planted_a.py": 'p = root / "ops/loop/control/lanes" / "0.lock"\n',
        "headless/planted_b.py": 'p = root / "ops\\\\loop\\\\control\\\\lanes"\n',
        "headless/planted_c.py": "from ops.fleet_kit.fleet_lanes import LANES_REL\n",
        "headless/clean.py": 'p = root / "ops/loop/control/progress"\n',
    }
    _, offenders = lane_lock_writers(planted)
    assert sorted(offenders) == [
        "headless/planted_a.py",
        "headless/planted_b.py",
        "headless/planted_c.py",
    ]


# ---------------------------------------------------------------------------
# 3. Worktree path: outside the root, not created
# ---------------------------------------------------------------------------


def test_the_lane_worktree_is_outside_a_repo_root_and_not_created(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(LANE_CAP):
        path = Path(lanes.worktree_path(repo, "RSC", index))
        assert not path.resolve().is_relative_to(repo.resolve()), path
        assert path.resolve().is_relative_to(tmp_path.resolve()), path
        assert path.name == f"lane-{index}"
        assert not path.exists(), f"computing a lane worktree path created {path}"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["repo"], (
        "computing lane worktree paths wrote beside the repo"
    )


def test_this_trees_lane_worktree_is_outside_its_root() -> None:
    """Pure computation against the real root: no directory is created."""
    path = Path(lanes.worktree_path(REPO_ROOT, "RSC", 0))
    main = Path(lanes.main_tree(REPO_ROOT))
    existed = path.exists()
    assert not path.resolve().is_relative_to(main.resolve()), path
    assert not path.resolve().is_relative_to(REPO_ROOT.resolve()), path
    assert path.exists() == existed, "computing the path changed the filesystem"


# ---------------------------------------------------------------------------
# 4. No module both holds a slot and spawns
# ---------------------------------------------------------------------------


def test_no_runtime_module_both_holds_a_slot_and_spawns() -> None:
    holders, both = hold_and_spawn(_corpus())
    assert "headless/runner.py" in holders, (
        "the detector no longer sees the runner's slots.hold, so a clean result "
        "says nothing"
    )
    assert not both, (
        f"{both} hold a slots.hold() AND call the kit's spawn. One governor slot per "
        "executor call: spawn(governor=...) OR slots.hold(), never both."
    )


def test_the_hold_and_spawn_detector_fires_on_a_planted_module() -> None:
    planted = {
        "headless/planted.py": (
            "with slots_mod.hold(max_slots=3):\n    kit.spawn(note, governor=None)\n"
        ),
        "headless/hold_only.py": "with slots.hold(max_slots=3):\n    pass\n",
        "tests/test_x.py": "with slots.hold():\n    kit.spawn(x)\n",
    }
    holders, both = hold_and_spawn(planted)
    assert sorted(holders) == ["headless/hold_only.py", "headless/planted.py"]
    assert both == ["headless/planted.py"]
