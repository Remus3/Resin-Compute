r"""A job that hangs on consecutive passes is QUARANTINED, durably.

WHY THIS EXISTS.

A LIVE pass that leaves a job abandoned ends the process holding its slot,
and `ops/supervisor.py` restarts the daemon. The supervisor resets its
backoff after `HEALTHY_UPTIME_SECONDS`, which is shorter than the runner's
`JOB_DEADLINE_SECONDS`, so a job that hangs on EVERY run would be rerun
forever - repeating its upstream fetch on every restart - and each restart's
pass summary would overwrite the record of the last abandonment.

So the runner keeps a per-job abandonment counter in the runtime directory,
written through `core/atomic_io.py`. A job abandoned on
`QUARANTINE_AFTER` consecutive passes is quarantined: later full passes SKIP
it, and every health record the runner writes carries a degraded flag naming
it, until the job completes once successfully - by asking for it explicitly
with `--job` - or the record is removed.

Every arm uses a tmp runtime dir and an EMPTIED job registry, so a full pass
runs only the fakes here, and calls `run_pass` directly, so no slot is taken
and no arm can reach the process exit.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from core import atomic_io as atomic_io_mod
from headless import jobs as jobs_mod
from headless import quarantine as quarantine_mod
from headless import runner as runner_mod
from ops import health as health_mod

HANGS = "quarantine_hangs"
OTHER = "quarantine_other"
CEILING = 10.0


@pytest.fixture(autouse=True)
def never_exit_this_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*args, **kwargs) -> None:
        raise AssertionError("the runner tried to os._exit the pytest process")

    monkeypatch.setattr(runner_mod, "_die_holding_slot", _refuse)


@pytest.fixture()
def only_fakes():
    snapshot = jobs_mod.registry_snapshot()
    jobs_mod.restore_registry({})
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def small_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_mod, "JOB_DEADLINE_SECONDS", 0.1)
    monkeypatch.setattr(runner_mod, "JOB_CANCEL_GRACE_SECONDS", 0.05)


@pytest.fixture()
def runtime(tmp_path: Path) -> Path:
    path = tmp_path / "runtime"
    path.mkdir()
    return path


class _Job:
    """A fake job whose behaviour each pass is set by `mode`."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.mode = "pass"
        self.calls = 0
        self.gates: list[threading.Event] = []
        self.workers: list[threading.Thread] = []

    def __call__(self, context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        self.calls += 1
        if self.mode == "hang":
            gate = threading.Event()
            self.gates.append(gate)
            self.workers.append(threading.current_thread())
            gate.wait(CEILING)
            return jobs_mod.passed(self.name, "late")
        if self.mode == "fail":
            return jobs_mod.failed(self.name, "ordinary failure")
        return jobs_mod.passed(self.name, "ok")

    def release(self) -> None:
        for gate in self.gates:
            gate.set()
        for worker in self.workers:
            worker.join(CEILING)


@pytest.fixture()
def fakes(only_fakes):
    made: list[_Job] = []

    def _make(name: str) -> _Job:
        job = _Job(name)
        jobs_mod.register(
            jobs_mod.JobSpec(
                name=name,
                description="quarantine probe",
                cadence=jobs_mod.CADENCE_ON_DEMAND,
                func=job,
            )
        )
        made.append(job)
        return job

    yield _make
    for job in made:
        job.release()
    assert runner_mod.abandoned_jobs() == []


def _pass(runtime: Path, job_names=None, dry_run: bool = False) -> runner_mod.PassResult:
    return runner_mod.run_pass(dry_run=dry_run, job_names=job_names, runtime_dir=str(runtime))


def _hang_once(job: _Job, runtime: Path) -> runner_mod.PassResult:
    job.mode = "hang"
    outcome = _pass(runtime)
    job.release()
    return outcome


def _health(runtime: Path) -> dict:
    return json.loads(health_mod.health_path(runtime).read_text(encoding="utf-8"))


def _record(runtime: Path) -> dict:
    return json.loads(quarantine_mod.record_path(str(runtime)).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def test_one_abandonment_is_counted_but_not_quarantined(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    assert _record(runtime)[HANGS]["consecutive"] == 1
    assert quarantine_mod.quarantined_jobs(str(runtime)) == []

    job.mode = "pass"
    calls = job.calls
    outcome = _pass(runtime)
    assert job.calls == calls + 1, "one abandonment must not quarantine"
    assert [r.status for r in outcome.results] == [jobs_mod.STATUS_PASS]


def test_two_consecutive_abandonments_quarantine_the_job(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    assert quarantine_mod.quarantined_jobs(str(runtime)) == [HANGS]

    job.mode = "pass"
    calls = job.calls
    outcome = _pass(runtime)
    assert job.calls == calls, "a quarantined job was started"
    (result,) = outcome.results
    assert result.status == jobs_mod.STATUS_SKIP
    assert "quarantined" in result.message
    assert "Traceback" not in result.message


def test_a_success_between_abandonments_resets_the_count(
    fakes, small_deadline, runtime: Path
) -> None:
    """Neighbour: abandonments must be CONSECUTIVE."""
    job = fakes(HANGS)
    _hang_once(job, runtime)
    job.mode = "pass"
    _pass(runtime)
    _hang_once(job, runtime)
    assert _record(runtime)[HANGS]["consecutive"] == 1
    assert quarantine_mod.quarantined_jobs(str(runtime)) == []


def test_an_ordinary_failure_between_abandonments_resets_the_count(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    job.mode = "fail"
    _pass(runtime)
    _hang_once(job, runtime)
    assert quarantine_mod.quarantined_jobs(str(runtime)) == []


def test_the_record_is_written_through_atomic_io(
    monkeypatch: pytest.MonkeyPatch, fakes, small_deadline, runtime: Path
) -> None:
    seen: list[Path] = []
    real = atomic_io_mod.atomic_write_json

    def _spy(path, obj):
        seen.append(Path(path))
        return real(path, obj)

    monkeypatch.setattr(atomic_io_mod, "atomic_write_json", _spy)
    job = fakes(HANGS)
    _hang_once(job, runtime)
    assert quarantine_mod.record_path(str(runtime)) in seen


def test_a_dry_run_writes_no_record(fakes, small_deadline, runtime: Path) -> None:
    job = fakes(HANGS)
    job.mode = "hang"
    _pass(runtime, dry_run=True)
    job.release()
    assert not quarantine_mod.record_path(str(runtime)).exists()


# ---------------------------------------------------------------------------
# The degraded flag in health
# ---------------------------------------------------------------------------


def test_health_carries_a_degraded_flag_that_survives_later_summaries(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    other = fakes(OTHER)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    job.mode = "pass"
    for _ in range(2):
        _pass(runtime)
        health = _health(runtime)
        assert health["degraded"] is True
        assert health["quarantined_jobs"] == [HANGS]
        assert HANGS in health["message"]
        assert "Traceback" not in health["message"]
    _pass(runtime, job_names=[OTHER])
    assert _health(runtime)["degraded"] is True, "an unrelated pass cleared the flag"
    assert other.calls >= 1


def test_a_healthy_tree_has_no_degraded_flag(fakes, small_deadline, runtime: Path) -> None:
    """Neighbour: the flag is not simply always on."""
    fakes(OTHER)
    _pass(runtime)
    health = _health(runtime)
    assert health.get("degraded") is False
    assert health.get("quarantined_jobs") == []


def test_the_shutdown_health_record_carries_the_flag_too(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    runner_mod._write_shutdown_health(str(runtime))
    assert _health(runtime)["quarantined_jobs"] == [HANGS]


# ---------------------------------------------------------------------------
# Leaving quarantine
# ---------------------------------------------------------------------------


def test_an_explicit_successful_run_lifts_the_quarantine(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    job.mode = "pass"
    outcome = _pass(runtime, job_names=[HANGS])
    assert [r.status for r in outcome.results] == [jobs_mod.STATUS_PASS]
    assert quarantine_mod.quarantined_jobs(str(runtime)) == []
    assert _health(runtime)["degraded"] is False

    calls = job.calls
    _pass(runtime)
    assert job.calls == calls + 1, "the job is back in the full pass"


def test_an_explicit_failing_run_keeps_the_quarantine(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    job.mode = "fail"
    _pass(runtime, job_names=[HANGS])
    assert quarantine_mod.quarantined_jobs(str(runtime)) == [HANGS]


def test_removing_the_record_lifts_the_quarantine(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    _hang_once(job, runtime)
    _hang_once(job, runtime)
    quarantine_mod.record_path(str(runtime)).unlink()
    job.mode = "pass"
    calls = job.calls
    _pass(runtime)
    assert job.calls == calls + 1


def test_a_corrupt_record_never_crashes_the_pass(
    fakes, small_deadline, runtime: Path
) -> None:
    job = fakes(HANGS)
    quarantine_mod.record_path(str(runtime)).write_bytes(b"{not json")
    outcome = _pass(runtime)
    assert job.calls == 1
    assert outcome.ok
