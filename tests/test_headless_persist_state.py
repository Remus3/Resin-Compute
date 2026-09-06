"""Tests for the persist_state job.

THE JOB EXISTS TO CLOSE ONE GAP: `reconcile_state` rebuilds the account from the
live response every pass and the process then exits, so the dashboard - a
separate process starting cold - had nothing to render.

THE RULE IT MUST NOT BREAK is live-state-first. The snapshot is written and never
read back by the headless lane. The last test in this file asserts that
structurally rather than trusting the docstring, because "nothing reads this"
is exactly the kind of claim that quietly stops being true.
"""
from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

from core.state_io import read_state
from core.types import AccountState, BannerKind, MappedCharacter, PityState
from headless.jobs import JobContext, get_job, persist_state

REPO_ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)


def _state() -> AccountState:
    state = AccountState(uid="618285856", adventure_rank=58, world_level=7)
    state.roster = (
        MappedCharacter(avatar_id=10000096, level=80, ascension=5, constellations=0, display_name="Arlecchino"),
    )
    state.pity = {BannerKind.CHARACTER_EVENT: PityState(pity_5star=61, has_guarantee=True)}
    state.last_synced_at = NOW
    return state


def _context(tmp_path: Path, **kwargs) -> JobContext:
    options = {"state_path": str(tmp_path / "account_state.json")}
    options.update(kwargs.pop("options", {}))
    return JobContext(uid="618285856", options=options, **kwargs)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_the_job_is_registered_and_depends_on_reconciliation():
    spec = get_job("persist_state")
    assert spec is not None
    assert "reconcile_state" in spec.depends_on


def test_the_job_runs_after_reconcile_state_in_the_ordered_pass():
    from headless.jobs import ordered_jobs

    names = [spec.name for spec in ordered_jobs()]
    assert "persist_state" in names
    assert names.index("reconcile_state") < names.index("persist_state")


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------


def test_it_writes_a_snapshot_the_reader_can_load(tmp_path):
    context = _context(tmp_path)
    context.state = _state()

    result = persist_state(context)

    assert result.ok, result.message
    restored = read_state(tmp_path / "account_state.json")
    assert restored is not None
    assert restored.uid == "618285856"
    assert restored.roster[0].display_name == "Arlecchino"
    assert restored.pity[BannerKind.CHARACTER_EVENT].pity_5star == 61


def test_a_dry_run_writes_nothing(tmp_path):
    """The CI smoke test runs --once --dry-run. It must not touch the tree."""
    context = _context(tmp_path, dry_run=True)
    context.state = _state()

    result = persist_state(context)

    assert result.skipped
    assert not (tmp_path / "account_state.json").exists()


def test_no_reconciled_state_skips_rather_than_writing_an_empty_one(tmp_path):
    """Overwriting a good snapshot with an empty one because a fetch failed is
    strictly worse than leaving yesterday's reading in place and saying so."""
    context = _context(tmp_path)
    context.state = None

    result = persist_state(context)

    assert result.skipped
    assert not (tmp_path / "account_state.json").exists()


def test_an_existing_snapshot_survives_a_pass_that_produced_no_state(tmp_path):
    target = tmp_path / "account_state.json"
    good = _context(tmp_path)
    good.state = _state()
    persist_state(good)
    before = target.read_text(encoding="utf-8")

    empty = _context(tmp_path)
    empty.state = None
    persist_state(empty)

    assert target.read_text(encoding="utf-8") == before


def test_an_unwritable_destination_fails_the_job_without_raising(tmp_path):
    # A directory where the file should be. The write cannot succeed and must
    # come back as a failed JobResult, not an exception that aborts the pass.
    blocked = tmp_path / "account_state.json"
    blocked.mkdir()
    context = _context(tmp_path)
    context.state = _state()

    result = persist_state(context)

    assert result.failed
    assert "Traceback" not in result.message


def test_the_snapshot_lands_in_the_data_dir_when_no_override_is_given(tmp_path, monkeypatch):
    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path))
    context = JobContext(uid="618285856")
    context.state = _state()

    result = persist_state(context)

    assert result.ok, result.message
    assert (tmp_path / "account_state.json").is_file()


def test_the_result_message_names_no_absolute_path(tmp_path):
    """A path under the user profile carries the Windows account name."""
    context = _context(tmp_path)
    context.state = _state()

    result = persist_state(context)

    assert ":\\" not in result.message
    assert "Users" not in result.message


# ---------------------------------------------------------------------------
# The live-state-first guard
# ---------------------------------------------------------------------------


def test_the_headless_lane_never_reads_the_snapshot_back():
    """Structural, not documentary.

    The snapshot is a DISPLAY cache. The moment a job reads it to seed a
    reconciliation, live-state-first is broken - and it would not look like a
    bug, it would look like a cache hit. So the import is asserted absent.
    """
    tree = ast.parse((REPO_ROOT / "headless" / "jobs.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.state_io":
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "read_state":
                imported.append("read_state")
            if isinstance(func, ast.Attribute) and func.attr == "read_state":
                imported.append("read_state")

    assert "read_state" not in imported, "headless/jobs.py reads the snapshot back - see core/state_io.py"


def test_the_guard_is_not_vacuous():
    """It must be looking at a file that really does use state_io at all."""
    text = (REPO_ROOT / "headless" / "jobs.py").read_text(encoding="utf-8")
    assert "state_io" in text
    assert "write_state" in text
