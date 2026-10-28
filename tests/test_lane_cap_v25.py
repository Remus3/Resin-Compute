"""Guard for this tree's FLEET-KIT v25 LANE-CAP adoption (MAIN 2136 ORDER of
2026-10-27, section 5 item 4).

This tree has no lane driver yet. Its "driver cap" is `core.config.LANE_CAP`
as the kit resolves it (`fleet_lanes.lane_cap(LANE_CAP)`), and its slot count
is the width `headless/runner.py` sizes the shared governor bucket with
(`runner._lane_width()`). Both must follow the live machine config:

  1. With FLEET_LANES_CONFIG naming a tmp file of
     {"governor_width": 5, "lane_cap_max": 5} both read 5; with the file
     missing both read 3. No hard-coded 3 is left on either path.
  2. When `fleet_lanes.should_yield` is True the runner does not start the
     pass (no slot taken, no job run) and never calls kill, terminate or
     send_signal on any process. A paired arm proves the same pass DOES run
     when should_yield is False, so the skip is not vacuous.

Every bucket here is under tmp_path; nothing reaches the machine-wide root
or the real machine config.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from core import config as core_config
from headless import jobs as jobs_mod
from headless import runner as runner_mod

lanes: Any = importlib.import_module("ops.fleet_kit.fleet_lanes")

PROBE_JOB = "lane_cap_v25_probe"


def _point_config_at(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setenv(lanes.CONFIG_ENV, str(path))


def _driver_cap_and_slots() -> tuple[int, int]:
    return lanes.lane_cap(core_config.LANE_CAP), runner_mod._lane_width()


def test_a_machine_config_of_five_moves_cap_and_slot_count_to_five(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "lanes.json"
    cfg.write_bytes(json.dumps({"governor_width": 5, "lane_cap_max": 5}).encode("ascii"))
    _point_config_at(monkeypatch, cfg)
    assert _driver_cap_and_slots() == (5, 5)


def test_a_missing_machine_config_reads_the_default_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _point_config_at(monkeypatch, tmp_path / "absent" / "lanes.json")
    assert _driver_cap_and_slots() == (3, 3)


def test_the_tree_default_width_equals_the_kit_default() -> None:
    """MAX_CONCURRENT_LANES is now the no-config default, so it must agree."""
    assert core_config.MAX_CONCURRENT_LANES == lanes.CONFIG_DEFAULTS["governor_width"]


# ---------------------------------------------------------------------------
# should_yield: skip the pass, never kill
# ---------------------------------------------------------------------------


@pytest.fixture()
def probe(tmp_path: Path):
    snapshot = jobs_mod.registry_snapshot()
    ran: list[int] = []

    def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        ran.append(1)
        return jobs_mod.passed(PROBE_JOB, "ran")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name=PROBE_JOB,
            description="records that the pass ran",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=_probe,
        )
    )
    yield ran
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def kills(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def _record(name: str):
        def _call(*args: object, **kwargs: object) -> None:
            seen.append(name)

        return _call

    monkeypatch.setattr(os, "kill", _record("os.kill"))
    monkeypatch.setattr(subprocess.Popen, "kill", _record("Popen.kill"))
    monkeypatch.setattr(subprocess.Popen, "terminate", _record("Popen.terminate"))
    monkeypatch.setattr(subprocess.Popen, "send_signal", _record("Popen.send_signal"))
    return seen


def _run_one_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, yield_: bool) -> dict:
    slot_root = tmp_path / "slots"
    slot_root.mkdir()
    asked: list[tuple[str, object]] = []

    def _should_yield(code: str, root: object = None, **_kw: object) -> bool:
        asked.append((code, root))
        return yield_

    holds: list[int] = []
    real_hold = runner_mod.slots_mod.hold

    def _hold(max_slots: int = 2, **kwargs: Any):
        holds.append(max_slots)
        return real_hold(max_slots, **kwargs)

    monkeypatch.setattr(lanes, "should_yield", _should_yield)
    monkeypatch.setattr(runner_mod.slots_mod, "hold", _hold)
    rc = runner_mod.run_daemon(
        uid=None,
        interval=1,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(tmp_path / "runtime"),
        max_passes=1,
        slot_root=slot_root,
    )
    return {"rc": rc, "asked": asked, "holds": holds, "slot_root": slot_root}


def test_should_yield_true_skips_the_pass_and_kills_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe: list[int], kills: list[str]
) -> None:
    out = _run_one_pass(tmp_path, monkeypatch, yield_=True)
    assert out["asked"] and out["asked"][0][0] == runner_mod.SLOT_REPO_LABEL
    assert Path(str(out["asked"][0][1])) == out["slot_root"]
    assert probe == [], "the pass ran although should_yield was True"
    assert out["holds"] == [], "a slot was taken although should_yield was True"
    assert kills == [], f"the runner signalled a process on yield: {kills}"
    assert out["rc"] == runner_mod.EXIT_JOB_FAILED, "a yielded cycle is a starved cycle"


def test_should_yield_false_runs_the_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe: list[int], kills: list[str]
) -> None:
    """Non-vacuity for the arm above: the same harness DOES run the pass."""
    out = _run_one_pass(tmp_path, monkeypatch, yield_=False)
    assert probe == [1]
    assert out["holds"] == [core_config.MAX_CONCURRENT_LANES]
    assert kills == []
    assert out["rc"] == runner_mod.EXIT_OK


def test_the_runner_source_names_no_kill_or_terminate() -> None:
    source = Path(runner_mod.__file__).read_text(encoding="ascii")
    for needle in (".kill(", ".terminate(", "send_signal(", "taskkill"):
        assert needle not in source, f"headless/runner.py calls {needle!r}"
