r"""A held slot's lock can never grow old enough to be reaped as stale.

WHY THIS EXISTS.

`ops/loop/slots.hold()` stamps the lock payload's `ts` BEFORE it starts
waiting, so the age a reaper sees on a live lock is

    wait + run + release drain

and `slots.DEFAULT_STALE_AFTER` must exceed that sum, or another carrier's
`reap()` unlinks a lock this process still holds and the bucket over-admits.
The runner bounds each term:

  - wait:  every slot wait is clamped to `MAX_SLOT_WAIT_SECONDS`, including a
           daemon started with an enormous `--interval`;
  - run:   `run_pass` stops STARTING jobs once `PASS_DEADLINE_SECONDS` has
           elapsed, and records the rest as SKIP;
  - drain: `slots.RELEASE_ATTEMPTS * slots.RELEASE_BACKOFF`.

Every figure is read from a module attribute - no literal here - so a change
to either side of the inequality re-runs the arithmetic.

KNOWN RESIDUAL, stated rather than hidden: one job that never returns is still
unbounded, because the deadline is checked between jobs. A hard cap needs a
subprocess. No arm here claims otherwise.
"""
from __future__ import annotations

import ast
import contextlib
import types
from pathlib import Path

import pytest

from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops.loop import slots as slots_mod

JOB_A = "budget_first"
JOB_B = "budget_second"


@pytest.fixture()
def clean_registry():
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def slot_root(tmp_path: Path) -> Path:
    root = tmp_path / "slots"
    root.mkdir()
    assert root != slots_mod.DEFAULT_ROOT
    return root


@pytest.fixture()
def runtime(tmp_path: Path) -> Path:
    path = tmp_path / "runtime"
    path.mkdir()
    return path


@pytest.fixture()
def fake_hold(monkeypatch: pytest.MonkeyPatch) -> list[float | None]:
    """Replace hold() with a diskless recorder of the timeout it was given."""
    seen: list[float | None] = []

    @contextlib.contextmanager
    def _hold(*args, **kwargs):
        seen.append(kwargs.get("timeout"))
        yield Path("fake.lock")

    monkeypatch.setattr(slots_mod, "hold", _hold)
    return seen


def _register(name: str, func, depends_on: tuple[str, ...] = ()) -> None:
    jobs_mod.register(
        jobs_mod.JobSpec(
            name=name,
            description="budget probe",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=func,
            depends_on=depends_on,
        )
    )


# ---------------------------------------------------------------------------
# 0. Guard on this module itself
# ---------------------------------------------------------------------------


def test_no_arm_here_can_reach_the_live_bucket() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("run_daemon", "run_once")
    ]
    assert any(n.func.attr == "run_daemon" for n in calls), "no run_daemon call checked"
    assert any(n.func.attr == "run_once" for n in calls), "no run_once call checked"
    for node in calls:
        names = {kw.arg for kw in node.keywords}
        assert "slot_root" in names, f"call at line {node.lineno} omits slot_root"
        assert "runtime_dir" in names, f"call at line {node.lineno} omits runtime_dir"


def test_the_guard_above_would_notice_a_missing_slot_root() -> None:
    tree = ast.parse("runner_mod.run_daemon(uid=None, runtime_dir='x')\n")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert "slot_root" not in {kw.arg for kw in call.keywords}


# ---------------------------------------------------------------------------
# 1. The arithmetic
# ---------------------------------------------------------------------------


def _worst_lock_age() -> float:
    wait = max(runner_mod.ONCE_SLOT_TIMEOUT_SECONDS, runner_mod.MAX_SLOT_WAIT_SECONDS)
    drain = slots_mod.RELEASE_ATTEMPTS * slots_mod.RELEASE_BACKOFF
    return wait + runner_mod.PASS_DEADLINE_SECONDS + drain


def test_worst_case_lock_age_is_below_the_stale_threshold() -> None:
    assert _worst_lock_age() < slots_mod.DEFAULT_STALE_AFTER, (
        "a held lock can age past slots.DEFAULT_STALE_AFTER and be reaped as stale "
        "by another carrier while this process still holds it"
    )


def test_the_budget_detector_fires_on_an_over_budget_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity: a deadline as long as the stale threshold breaks the sum."""
    monkeypatch.setattr(runner_mod, "PASS_DEADLINE_SECONDS", slots_mod.DEFAULT_STALE_AFTER)
    assert not _worst_lock_age() < slots_mod.DEFAULT_STALE_AFTER


def test_once_timeout_does_not_exceed_the_wait_cap() -> None:
    assert runner_mod.ONCE_SLOT_TIMEOUT_SECONDS <= runner_mod.MAX_SLOT_WAIT_SECONDS


def test_budget_constants_are_positive() -> None:
    assert runner_mod.MAX_SLOT_WAIT_SECONDS > 0
    assert runner_mod.PASS_DEADLINE_SECONDS > 0


# ---------------------------------------------------------------------------
# 2. The wait clamp
# ---------------------------------------------------------------------------


def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
    return jobs_mod.passed(JOB_A, "ok")


def test_daemon_with_a_huge_interval_waits_at_most_the_cap(
    clean_registry, fake_hold, slot_root: Path, runtime: Path
) -> None:
    _register(JOB_A, _probe)
    code = runner_mod.run_daemon(
        uid=None,
        interval=20000,
        dry_run=False,
        job_names=[JOB_A],
        runtime_dir=str(runtime),
        max_passes=1,
        slot_root=slot_root,
    )
    assert code == runner_mod.EXIT_OK
    assert len(fake_hold) == 1
    assert fake_hold[0] is not None
    assert fake_hold[0] <= runner_mod.MAX_SLOT_WAIT_SECONDS


def test_daemon_with_a_short_interval_keeps_its_interval_as_the_wait(
    clean_registry, fake_hold, slot_root: Path, runtime: Path
) -> None:
    """Neighbour: the clamp only bites above the cap."""
    _register(JOB_A, _probe)
    runner_mod.run_daemon(
        uid=None,
        interval=20,
        dry_run=False,
        job_names=[JOB_A],
        runtime_dir=str(runtime),
        max_passes=1,
        slot_root=slot_root,
    )
    assert fake_hold == [20.0]


def test_explicit_oversized_slot_timeout_is_clamped_too(
    clean_registry, fake_hold, slot_root: Path, runtime: Path
) -> None:
    _register(JOB_A, _probe)
    runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[JOB_A],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=10**6,
    )
    assert len(fake_hold) == 1
    assert fake_hold[0] is not None
    assert fake_hold[0] <= runner_mod.MAX_SLOT_WAIT_SECONDS


# ---------------------------------------------------------------------------
# 3. The pass deadline
# ---------------------------------------------------------------------------


def _two_jobs(clock: list[float], ran: list[str], advance_to: float) -> None:
    def _first(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        ran.append(JOB_A)
        clock[0] = advance_to
        return jobs_mod.passed(JOB_A, "ok")

    def _second(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        ran.append(JOB_B)
        return jobs_mod.passed(JOB_B, "ok")

    _register(JOB_A, _first)
    _register(JOB_B, _second, depends_on=(JOB_A,))


def _pin_monotonic(monkeypatch: pytest.MonkeyPatch, clock: list[float]) -> None:
    """Give the runner a `time` whose ONLY usable clock is the fake monotonic.

    Replacing the runner's own `time` binding rather than the global module
    keeps logging and pytest on the real clocks. Reading `time.time` from the
    runner raises, so a wall-clock deadline is a RED, not a silent pass; and a
    clock bound at import (`_clock = time.monotonic`) never sees the fake, so
    the deadline is never reached and the arm below is RED for that too.
    """

    def _wall_clock_forbidden() -> float:
        raise AssertionError("the pass deadline must read time.monotonic, not time.time")

    fake = types.SimpleNamespace(monotonic=lambda: clock[0], time=_wall_clock_forbidden)
    monkeypatch.setattr(runner_mod, "time", fake)


def test_run_pass_past_the_deadline_starts_no_further_jobs(
    monkeypatch: pytest.MonkeyPatch, clean_registry, runtime: Path
) -> None:
    clock = [1000.0]
    ran: list[str] = []
    _pin_monotonic(monkeypatch, clock)
    _two_jobs(clock, ran, advance_to=1000.0 + runner_mod.PASS_DEADLINE_SECONDS + 1)

    outcome = runner_mod.run_pass(
        dry_run=True, job_names=[JOB_A, JOB_B], runtime_dir=str(runtime)
    )

    assert ran == [JOB_A], "the second job must not be started past the deadline"
    by_name = {r.name: r for r in outcome.results}
    assert by_name[JOB_A].status == jobs_mod.STATUS_PASS
    assert by_name[JOB_B].status == jobs_mod.STATUS_SKIP
    assert "deadline" in by_name[JOB_B].message
    assert "Traceback" not in by_name[JOB_B].message


def test_run_pass_within_the_deadline_runs_every_job(
    monkeypatch: pytest.MonkeyPatch, clean_registry, runtime: Path
) -> None:
    """Neighbour: just inside the deadline both jobs run."""
    clock = [1000.0]
    ran: list[str] = []
    _pin_monotonic(monkeypatch, clock)
    _two_jobs(clock, ran, advance_to=1000.0 + runner_mod.PASS_DEADLINE_SECONDS - 1)

    outcome = runner_mod.run_pass(
        dry_run=True, job_names=[JOB_A, JOB_B], runtime_dir=str(runtime)
    )

    assert ran == [JOB_A, JOB_B]
    assert all(r.status == jobs_mod.STATUS_PASS for r in outcome.results)
    assert "deadline reached" not in outcome.summary_line()


def test_deadline_skipped_pass_says_so_in_the_summary(
    monkeypatch: pytest.MonkeyPatch, clean_registry, runtime: Path
) -> None:
    """A pass cut short by the deadline must not read as a plain green summary."""
    clock = [1000.0]
    ran: list[str] = []
    _pin_monotonic(monkeypatch, clock)
    _two_jobs(clock, ran, advance_to=1000.0 + runner_mod.PASS_DEADLINE_SECONDS + 1)

    outcome = runner_mod.run_pass(
        dry_run=True, job_names=[JOB_A, JOB_B], runtime_dir=str(runtime)
    )

    assert "deadline reached: 1 jobs not started" in outcome.summary_line()
    assert outcome.ok, "a deadline skip is not a failure - the exit code stays 0"


def test_deadline_skipped_live_once_still_exits_ok(
    monkeypatch: pytest.MonkeyPatch, clean_registry, fake_hold, slot_root: Path, runtime: Path
) -> None:
    clock = [1000.0]
    ran: list[str] = []
    _pin_monotonic(monkeypatch, clock)
    _two_jobs(clock, ran, advance_to=1000.0 + runner_mod.PASS_DEADLINE_SECONDS + 1)
    code = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[JOB_A, JOB_B],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )
    assert code == runner_mod.EXIT_OK
    assert ran == [JOB_A]
