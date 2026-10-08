r"""The runner's live pass writes its FLEET-COMMON item-13 checklist.

Item 13 d: a headless fire writes its task list into its item-12 progress file
as "checklist": [{"id", "task", "state", "eta_s"}], REMAINING tasks only. In
this tree the runner's progress task is `rsc-runner` (CLAUDE.md, "Session
checklist - FLEET-COMMON item 13 in this tree"), written through the kit's
`write_progress`. Each arm below pins one property:

  - a live pass writes a remaining-only checklist, and ends `done`;
  - a failed or overrun job ends the progress `failed`;
  - a dry run writes no progress file - it writes nothing at all;
  - a progress write that fails never fails the pass;
  - the progress root is the repo root ONLY for the default runtime; any
    redirected runtime puts it under `<runtime>/kit_root`, mirroring the
    responder's `_kit_root`, so no arm can reach the live progress directory;
  - the pass log carries the block, rendered ASCII (`[ ]` for the box).

ISOLATION. Every arm sets RESINCOMPUTE_RUNTIME_DIR to a tmp directory, passes
an explicit `runtime_dir` under tmp, and passes `slot_root` under tmp, so no
arm takes a slot in the machine-wide bucket or writes the live
`ops/loop/control/`. `test_every_runner_call_here_names_its_slot_root` parses
this module to keep that true.
"""
from __future__ import annotations

import ast
import importlib
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")
checklist_kit: Any = importlib.import_module("ops.fleet_kit.fleet_checklist")

JOB_A = "cl_probe_a"
JOB_B = "cl_probe_b"


@pytest.fixture()
def clean_registry():
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "runtime"
    path.mkdir()
    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(path))
    return path


@pytest.fixture()
def slot_root(tmp_path: Path) -> Path:
    root = tmp_path / "slots"
    root.mkdir()
    assert root != slots_mod.DEFAULT_ROOT
    return root


def _progress_path(runtime: Path) -> Path:
    return runtime / "kit_root" / kit.PROGRESS_REL / (runner_mod.PROGRESS_TASK + ".json")


def _read_progress(runtime: Path) -> dict:
    return json.loads(_progress_path(runtime).read_text(encoding="ascii"))


def _register(name: str, func) -> None:
    jobs_mod.register(
        jobs_mod.JobSpec(
            name=name,
            description="checklist probe",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=func,
        )
    )


def _ok(name: str):
    def _job(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed(name, "ok")

    return _job


def _once(runtime: Path, slot_root: Path, jobs: list[str], dry_run: bool = False) -> int:
    return runner_mod.run_once(
        uid=None,
        dry_run=dry_run,
        job_names=jobs,
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=5.0,
    )


# ---------------------------------------------------------------------------
# Isolation guard
# ---------------------------------------------------------------------------


def test_every_runner_call_here_names_its_slot_root() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("run_daemon", "run_once")
    ]
    assert calls, "no runner call found, so this guard proves nothing"
    for node in calls:
        names = {kw.arg for kw in node.keywords}
        assert "slot_root" in names and "runtime_dir" in names, node.lineno


# ---------------------------------------------------------------------------
# The checklist
# ---------------------------------------------------------------------------


def test_a_live_pass_writes_a_remaining_only_checklist(
    clean_registry, runtime: Path, slot_root: Path
) -> None:
    mid: list[dict] = []
    _register(JOB_A, _ok(JOB_A))

    def _probe_b(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        mid.append(_read_progress(runtime))
        return jobs_mod.passed(JOB_B, "ok")

    _register(JOB_B, _probe_b)

    rc = _once(runtime, slot_root, [JOB_A, JOB_B])

    assert rc == runner_mod.EXIT_OK
    assert len(mid) == 1
    seen = mid[0]
    assert seen["task"] == "rsc-runner"
    assert seen["status"] == "running"
    rows = seen["checklist"]
    assert [r["task"] for r in rows] == [f"Run job {JOB_B}"], (
        f"mid-pass the checklist must hold the REMAINING job only, got {rows}"
    )
    assert rows[0]["state"] == "running"
    assert set(rows[0]) == {"id", "task", "state", "eta_s"}

    final = _read_progress(runtime)
    assert final["status"] == "done"
    assert final["pct"] == 100
    assert final["checklist"] == []
    assert set(final) >= {"task", "pct", "step", "eta_s", "status", "updated"}
    raw = _progress_path(runtime).read_bytes()
    assert raw.isascii() and b"\r" not in raw


def test_a_failed_or_overrun_job_ends_the_progress_failed(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fails(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.failed(JOB_A, "planted failure")

    _register(JOB_A, _fails)
    rc = _once(runtime, slot_root, [JOB_A])
    assert rc == runner_mod.EXIT_JOB_FAILED
    assert _read_progress(runtime)["status"] == "failed"

    # Overrun: a job that waits past a tiny deadline, then stops on cancel.
    _progress_path(runtime).unlink()
    monkeypatch.setattr(runner_mod, "JOB_DEADLINE_SECONDS", 0.2)
    monkeypatch.setattr(runner_mod, "JOB_CANCEL_GRACE_SECONDS", 5)

    def _slow(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        context.cancel.wait(10)
        return jobs_mod.passed(JOB_B, "late")

    _register(JOB_B, _slow)
    rc = _once(runtime, slot_root, [JOB_B])
    assert rc == runner_mod.EXIT_JOB_FAILED
    assert _read_progress(runtime)["status"] == "failed"


def test_a_pass_that_raises_ends_the_progress_failed(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run_pass` absorbs a failing job, so the PASS itself is made to raise."""
    _register(JOB_A, _ok(JOB_A))

    def _explode(**kwargs):
        raise RuntimeError("planted pass failure")

    monkeypatch.setattr(runner_mod, "run_pass", _explode)
    with pytest.raises(RuntimeError):
        _once(runtime, slot_root, [JOB_A])
    final = _read_progress(runtime)
    assert final["status"] == "failed"
    assert "planted" not in final["step"], "a raw error string reached the progress file"


def test_a_dry_run_writes_no_progress_file(
    clean_registry, runtime: Path, slot_root: Path
) -> None:
    _register(JOB_A, _ok(JOB_A))
    rc = _once(runtime, slot_root, [JOB_A], dry_run=True)
    assert rc == runner_mod.EXIT_OK
    assert not (runtime / "kit_root").exists()
    assert list(runtime.iterdir()) == [], "a dry run wrote into the runtime dir"


def test_a_halted_pass_writes_no_progress_file(
    clean_registry, runtime: Path, slot_root: Path
) -> None:
    _register(JOB_A, _ok(JOB_A))
    (runtime / runner_mod.HALT_SENTINEL_NAME).write_text("stop\n", encoding="ascii")
    rc = _once(runtime, slot_root, [JOB_A])
    assert rc == runner_mod.EXIT_JOB_FAILED
    assert not (runtime / "kit_root").exists()


def test_a_failing_progress_write_never_fails_a_pass(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _broken(*args, **kwargs):
        calls.append(kwargs.get("status") or args[5])
        raise OSError("planted: disk full")

    monkeypatch.setattr(kit, "write_progress", _broken)
    ran: list[str] = []

    def _job(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        ran.append(JOB_A)
        return jobs_mod.passed(JOB_A, "ok")

    _register(JOB_A, _job)
    rc = _once(runtime, slot_root, [JOB_A])
    assert rc == runner_mod.EXIT_OK
    assert ran == [JOB_A]
    assert calls, "non-vacuity: the broken writer was never reached"
    assert not _progress_path(runtime).exists()


def test_the_root_is_the_repo_root_only_for_the_default_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pure path computation; nothing is written by any branch here."""
    repo = Path(health_mod.REPO_ROOT)
    default_runtime = repo / "ops" / "runtime"

    monkeypatch.delenv(health_mod.ENV_RUNTIME_DIR, raising=False)
    assert runner_mod.kit_root(None) == repo
    assert runner_mod.kit_root(str(default_runtime)) == repo

    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(tmp_path / "rt"))
    assert runner_mod.kit_root(None) == tmp_path / "rt" / "kit_root"
    assert runner_mod.kit_root(str(tmp_path / "x")) == tmp_path / "x" / "kit_root"
    assert not (tmp_path / "rt").exists() and not (tmp_path / "x").exists()


def test_the_pass_log_carries_an_ascii_session_block(
    clean_registry, runtime: Path, slot_root: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _register(JOB_A, _ok(JOB_A))
    _register(JOB_B, _ok(JOB_B))
    with caplog.at_level(logging.INFO, logger="headless.runner"):
        rc = _once(runtime, slot_root, [JOB_A, JOB_B])
    assert rc == runner_mod.EXIT_OK
    lines = [r.getMessage() for r in caplog.records if r.name == "headless.runner"]
    assert "Session 1 checklist" in lines
    head = lines.index("Session 1 checklist")
    assert lines[head + 1 : head + 4] == [
        f"[ ] J1: Run job {JOB_A}",
        f"[ ] J2: Run job {JOB_B}",
        "[ ] /done",
    ]
    assert all(line.isascii() for line in lines), "a log line carries a non-ASCII byte"
    assert checklist_kit.BOX not in "\n".join(lines)


# ---------------------------------------------------------------------------
# The terminal write survives a reader, and leaves no tmp behind
# ---------------------------------------------------------------------------
#
# The kit's `fleet_headless._atomic_write` (a recorded kit defect, reported to
# MAIN, never patched here) has no retry and never removes its tmp. On Windows
# a reader holding the progress file open makes `replace` raise
# PermissionError, so without a retry the file stays "running" and
# `rsc-runner.json.<pid>.tmp` is orphaned for good - its name is not an
# `atomic_io` temp, so `sweep_orphan_temps` never reaches it.


def _kit_tmp(runtime: Path, pid: int) -> Path:
    progress = _progress_path(runtime)
    return progress.with_name(f"{progress.name}.{pid}.tmp")


def _leftover_tmps(runtime: Path) -> list[str]:
    folder = _progress_path(runtime).parent
    if not folder.exists():
        return []
    return sorted(p.name for p in folder.iterdir() if p.name.endswith(".tmp"))


def test_a_reader_holding_the_file_on_the_final_write_still_ends_done(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A REAL open handle on the target during the terminal write.

    On Windows the first terminal attempt is refused while the handle is open
    (asserted, so the arm is not vacuous there); the handle closes shortly
    after, and the bounded retry must then land "done" with no tmp left.
    """
    real = kit.write_progress
    state: dict[str, Any] = {"held": None, "timer": None, "refused": 0}

    # Kit v10 (MAIN 0839 ORDER s2) retries `replace` INSIDE `_atomic_write`, so
    # a held reader may never surface as an OSError from `write_progress`.
    # Contention is therefore counted where it happens, at `Path.replace`,
    # whichever layer - the kit's retry or the runner's - absorbs it.
    real_replace = Path.replace

    def _counting_replace(self, target):
        try:
            return real_replace(self, target)
        except PermissionError:
            state["refused"] += 1
            raise

    monkeypatch.setattr(Path, "replace", _counting_replace)

    def _wrapped(root, task, **kwargs):
        path = Path(root) / kit.PROGRESS_REL / (task + ".json")
        if kwargs.get("status") == "done" and state["held"] is None:
            state["held"] = open(path, "rb")  # noqa: SIM115 - closed by the timer
            state["timer"] = threading.Timer(0.05, state["held"].close)
            state["timer"].start()
        return real(root, task, **kwargs)

    monkeypatch.setattr(kit, "write_progress", _wrapped)
    _register(JOB_A, _ok(JOB_A))
    try:
        rc = _once(runtime, slot_root, [JOB_A])
    finally:
        if state["timer"] is not None:
            state["timer"].join(5)
        if state["held"] is not None:
            state["held"].close()

    assert rc == runner_mod.EXIT_OK
    assert state["held"] is not None, "non-vacuity: the terminal write was never reached"
    if sys.platform == "win32":
        assert state["refused"] >= 1, (
            "non-vacuity: the held reader never refused a write, so this arm "
            "measured no contention"
        )
    assert _read_progress(runtime)["status"] == "done"
    assert _leftover_tmps(runtime) == []


def test_a_refused_terminal_write_is_retried_on_every_platform(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same contention, simulated: deterministic on POSIX too.

    The fake leaves the kit's own tmp behind on each refusal, as the real
    `_atomic_write` does when `replace` raises.
    """
    real = kit.write_progress
    refusals = {"left": 3}

    def _flaky(root, task, **kwargs):
        if kwargs.get("status") == "done" and refusals["left"] > 0:
            refusals["left"] -= 1
            _kit_tmp(runtime, os.getpid()).write_bytes(b"{}")
            raise PermissionError(13, "planted: file in use")
        return real(root, task, **kwargs)

    monkeypatch.setattr(kit, "write_progress", _flaky)
    monkeypatch.setattr(runner_mod, "PROGRESS_RETRY_SLEEP_SECONDS", 0.001)
    _register(JOB_A, _ok(JOB_A))
    rc = _once(runtime, slot_root, [JOB_A])
    assert rc == runner_mod.EXIT_OK
    assert refusals["left"] == 0, "non-vacuity: the refusals were never consumed"
    assert _read_progress(runtime)["status"] == "done"
    assert _leftover_tmps(runtime) == []


def test_an_exhausted_retry_removes_only_this_processes_tmp(
    clean_registry, runtime: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every terminal attempt refused: the pass still succeeds, this process's
    tmp is removed, and ANOTHER process's tmp - possibly a write in flight -
    survives untouched."""
    real = kit.write_progress
    attempts = {"n": 0}

    def _always_refused(root, task, **kwargs):
        if kwargs.get("status") == "done":
            attempts["n"] += 1
            _kit_tmp(runtime, os.getpid()).write_bytes(b"{}")
            raise PermissionError(13, "planted: file in use")
        return real(root, task, **kwargs)

    monkeypatch.setattr(kit, "write_progress", _always_refused)
    monkeypatch.setattr(runner_mod, "PROGRESS_RETRY_SLEEP_SECONDS", 0.001)
    _register(JOB_A, _ok(JOB_A))

    def _plant_neighbour(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        _kit_tmp(runtime, os.getpid() + 1).write_bytes(b"{}")
        return jobs_mod.passed(JOB_B, "ok")

    _register(JOB_B, _plant_neighbour)
    rc = _once(runtime, slot_root, [JOB_A, JOB_B])
    assert rc == runner_mod.EXIT_OK
    assert attempts["n"] == runner_mod.PROGRESS_RETRIES
    assert _leftover_tmps(runtime) == [_kit_tmp(runtime, os.getpid() + 1).name], (
        "only this process's own tmp may be removed"
    )
