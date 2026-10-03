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
           elapsed, and records the rest as SKIP; the last job started
           before that is itself bounded by `JOB_DEADLINE_SECONDS` plus
           `JOB_CANCEL_GRACE_SECONDS`;
  - drain: `slots.RELEASE_ATTEMPTS * slots.RELEASE_BACKOFF`.

Every figure is read from a module attribute - no literal here - so a change
to either side of the inequality re-runs the arithmetic.

THE PER-JOB DEADLINE. Each job runs on a worker thread and the pass waits
for it at most `JOB_DEADLINE_SECONDS`. A job still running then is recorded
FAIL, its context's `cancel` event is set, the pass waits a short grace for it
to notice, and the pass ends - so the slot is released on time. A Python thread
cannot be killed, so a job that ignores `cancel` keeps running as an ABANDONED
daemon thread. On a DRY run that is the end of it: no further job in that pass
starts, and no slot is involved. On a LIVE pass the invariant is that NO SLOT
OF THIS PROCESS IS RELEASED WHILE A JOB OF THIS PROCESS IS STILL RUNNING, so
the runner writes a health record saying so and ends the PROCESS with
`EXIT_JOB_ABANDONED`, inside the hold, without releasing it. Process death
kills the abandoned thread; the lock is left with a dead pid for the reap path
in `ops/loop/slots.py`. The arms in section 4 measure each of those, and the
live arms run the runner in a CHILD interpreter, never in this one.
"""
from __future__ import annotations

import ast
import contextlib
import json
import os
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pytest

from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

JOB_A = "budget_first"
JOB_B = "budget_second"


@pytest.fixture(autouse=True)
def never_exit_this_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_die_holding_slot` ends the process with `os._exit`. In THIS process it
    raises instead, so a regression that reaches it fails one arm rather than
    killing the whole pytest run. The real exit is measured in a child below."""

    def _refuse(*args, **kwargs) -> None:
        raise AssertionError("the runner tried to os._exit the pytest process")

    monkeypatch.setattr(runner_mod, "_die_holding_slot", _refuse)


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
    run = (
        runner_mod.PASS_DEADLINE_SECONDS
        + runner_mod.JOB_DEADLINE_SECONDS
        + runner_mod.JOB_CANCEL_GRACE_SECONDS
    )
    return wait + run + drain


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
    assert runner_mod.JOB_DEADLINE_SECONDS > 0
    assert runner_mod.JOB_CANCEL_GRACE_SECONDS > 0


def test_the_budget_detector_fires_on_an_over_budget_job_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity for the per-job term: it is actually inside the sum."""
    monkeypatch.setattr(runner_mod, "JOB_DEADLINE_SECONDS", slots_mod.DEFAULT_STALE_AFTER)
    assert not _worst_lock_age() < slots_mod.DEFAULT_STALE_AFTER


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


# ---------------------------------------------------------------------------
# 4. The per-job deadline
# ---------------------------------------------------------------------------
#
# Each fake job blocks on a `threading.Event` the TEST owns, with its own
# ceiling, so a red arm can never leave a thread running past the test: the
# `release` fixture sets every event and joins every worker on teardown.

HUNG = "budget_hung"
AFTER = "budget_after"
SMALL_DEADLINE = 0.2
SMALL_GRACE = 0.2
#: A ceiling on how long any fake job may block, well past the deadline.
FAKE_CEILING = 10.0


@pytest.fixture()
def small_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_mod, "JOB_DEADLINE_SECONDS", SMALL_DEADLINE)
    monkeypatch.setattr(runner_mod, "JOB_CANCEL_GRACE_SECONDS", SMALL_GRACE)


@pytest.fixture()
def release():
    """Events the fake jobs block on, and the worker threads they ran on."""
    events: list[threading.Event] = []
    workers: list[threading.Thread] = []
    yield events, workers
    for event in events:
        event.set()
    for worker in workers:
        worker.join(FAKE_CEILING)
    assert runner_mod.abandoned_jobs() == [], "a fake job outlived its test"


def _register_hung(
    release, *, cooperative: bool, late: list[str] | None = None
) -> threading.Event:
    events, workers = release
    gate = threading.Event()
    events.append(gate)

    def _hung(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        workers.append(threading.current_thread())
        if cooperative:
            context.cancel.wait(FAKE_CEILING)
        else:
            gate.wait(FAKE_CEILING)
        if late is not None:
            late.append("returned")
        return jobs_mod.passed(HUNG, "a late success that must never be recorded")

    _register(HUNG, _hung)
    return gate


def _register_after(ran: list[str]) -> None:
    def _after(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        ran.append(AFTER)
        return jobs_mod.passed(AFTER, "ok")

    _register(AFTER, _after, depends_on=(HUNG,))


def test_a_hung_job_is_failed_within_its_deadline(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    gate = _register_hung(release, cooperative=False)
    start = time.monotonic()
    outcome = runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    elapsed = time.monotonic() - start

    assert elapsed < SMALL_DEADLINE + SMALL_GRACE + 2.0, "the pass waited on the hung job"
    (result,) = outcome.results
    assert result.status == jobs_mod.STATUS_FAIL, "a hung job is never a success"
    assert "deadline" in result.message
    assert "Traceback" not in result.message
    assert not outcome.ok
    gate.set()


def test_a_hung_job_stops_the_rest_of_the_pass(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    """The hung job may still be mutating the shared context, so nothing after it runs."""
    gate = _register_hung(release, cooperative=False)
    ran: list[str] = []
    _register_after(ran)
    outcome = runner_mod.run_pass(
        dry_run=True, job_names=[HUNG, AFTER], runtime_dir=str(runtime)
    )
    by_name = {r.name: r for r in outcome.results}
    assert ran == []
    assert by_name[HUNG].status == jobs_mod.STATUS_FAIL
    assert by_name[AFTER].status == jobs_mod.STATUS_SKIP
    assert "Traceback" not in by_name[AFTER].message
    gate.set()


def test_a_late_return_is_never_recorded(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    late: list[str] = []
    gate = _register_hung(release, cooperative=False, late=late)
    outcome = runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    gate.set()
    for worker in release[1]:
        worker.join(FAKE_CEILING)
    assert late == ["returned"], "fixture: the job did come back, late"
    assert [r.status for r in outcome.results] == [jobs_mod.STATUS_FAIL]


def test_a_cooperative_job_is_cancelled_and_leaks_no_thread(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    _register_hung(release, cooperative=True)
    outcome = runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    assert [r.status for r in outcome.results] == [jobs_mod.STATUS_FAIL]
    (worker,) = release[1]
    assert not worker.is_alive(), "the cancel event did not reach the job"
    assert runner_mod.abandoned_jobs() == []


def test_the_grace_period_lets_a_cooperative_job_finish_cleaning_up(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    """Kills a no-grace mutant: without the grace wait, cleanup is cut off.

    The job notices `cancel` and then needs a short, bounded moment - well
    inside the grace - to finish. With the grace wait the pass returns only
    after it has; without it the pass returns at once and the job is
    misrecorded as abandoned.
    """
    events, workers = release
    cleaned: list[str] = []

    def _tidy(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        workers.append(threading.current_thread())
        context.cancel.wait(FAKE_CEILING)
        time.sleep(SMALL_GRACE / 4)
        cleaned.append("done")
        return jobs_mod.passed(HUNG, "late")

    _register(HUNG, _tidy)
    outcome = runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    (result,) = outcome.results
    assert cleaned == ["done"], "the pass returned before the job's grace ran out"
    assert result.status == jobs_mod.STATUS_FAIL
    assert result.details["abandoned"] is False
    assert runner_mod.abandoned_jobs() == []


def test_an_uncooperative_job_is_tracked_until_it_ends(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    """A thread cannot be killed; it is a DAEMON thread and it is tracked."""
    gate = _register_hung(release, cooperative=False)
    runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    (worker,) = release[1]
    assert worker.is_alive()
    assert worker.daemon, "an abandoned job must never block interpreter exit"
    assert runner_mod.abandoned_jobs() == [HUNG]
    gate.set()
    worker.join(FAKE_CEILING)
    assert runner_mod.abandoned_jobs() == []


def test_a_fast_job_is_unaffected_by_the_deadline(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    """Neighbour: a job inside its deadline passes and leaves nothing behind."""
    _register(JOB_A, _probe)
    outcome = runner_mod.run_pass(dry_run=True, job_names=[JOB_A], runtime_dir=str(runtime))
    assert [r.status for r in outcome.results] == [jobs_mod.STATUS_PASS]
    assert outcome.ok
    assert runner_mod.abandoned_jobs() == []


def test_a_job_that_raises_on_its_worker_is_still_failed(
    clean_registry, small_deadline, release, runtime: Path
) -> None:
    def _boom(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        raise RuntimeError("raw upstream text that must not surface")

    _register(JOB_A, _boom)
    outcome = runner_mod.run_pass(dry_run=True, job_names=[JOB_A], runtime_dir=str(runtime))
    (result,) = outcome.results
    assert result.status == jobs_mod.STATUS_FAIL
    assert "raw upstream" not in result.message


def test_no_live_pass_takes_a_slot_while_a_job_is_abandoned(
    clean_registry, small_deadline, release, fake_hold, slot_root: Path, runtime: Path
) -> None:
    """The fence before the hold. A DRY pass abandons the job here, because a
    LIVE pass that abandons one ends the process and must not run in pytest."""
    gate = _register_hung(release, cooperative=False)
    _register(JOB_A, _probe)
    runner_mod.run_pass(dry_run=True, job_names=[HUNG], runtime_dir=str(runtime))
    assert runner_mod.abandoned_jobs() == [HUNG]

    blocked = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[JOB_A],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )
    assert blocked == runner_mod.EXIT_JOB_FAILED
    assert fake_hold == [], "a slot was taken while abandoned work was still running"

    gate.set()
    release[1][0].join(FAKE_CEILING)
    resumed = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[JOB_A],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )
    assert resumed == runner_mod.EXIT_OK, "neighbour: the lane resumes once the job ends"
    assert len(fake_hold) == 1


# ---------------------------------------------------------------------------
# 5. A LIVE pass with an abandoned job: the process dies holding its slot
# ---------------------------------------------------------------------------
#
# Every arm here runs the runner in a CHILD interpreter launched by
# `sys.executable`, because the behaviour under test is `os._exit`. The child
# gets a tmp runtime dir and a tmp slot root; it can never reach the live
# bucket. After `run_once` returns the child stays alive for CHILD_LINGER
# seconds, the way a daemon would carry on to its next interval - so a runner
# that released the slot and carried on is caught red-handed.

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILD_LINGER = 3.0
#: When the zombie job writes its late state, measured from the job's start.
LATE_WRITE_AT = 1.2

_CHILD = r"""
import sys, time
from pathlib import Path
repo, work = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, repo)
from headless import jobs as jobs_mod
from headless import runner as runner_mod

beat = work / "heartbeat"
late = work / "late_state"
started = work / "started"

def _zombie(context):
    t0 = time.monotonic()
    started.write_text("1", encoding="utf-8")
    while time.monotonic() - t0 < 10.0:
        with beat.open("a", encoding="utf-8") as fh:
            fh.write(".")
        if time.monotonic() - t0 >= float(sys.argv[3]) and not late.exists():
            late.write_text("stale state from an abandoned job", encoding="utf-8")
        time.sleep(0.02)
    return jobs_mod.passed("zombie", "late")

jobs_mod.register(jobs_mod.JobSpec(
    name="zombie", description="ignores cancel",
    cadence=jobs_mod.CADENCE_ON_DEMAND, func=_zombie))
runner_mod.JOB_DEADLINE_SECONDS = 0.2
runner_mod.JOB_CANCEL_GRACE_SECONDS = 0.1
code = runner_mod.run_once(
    uid=None, dry_run=False, job_names=["zombie"],
    runtime_dir=str(work / "runtime"), slot_root=str(work / "slots"), slot_timeout=5)
time.sleep(float(sys.argv[4]))
sys.exit(90 + code)
"""


def _spawn_child(work: Path) -> subprocess.Popen[bytes]:
    (work / "runtime").mkdir()
    (work / "slots").mkdir()
    env = dict(os.environ)
    env["RESINCOMPUTE_RUNTIME_DIR"] = str(work / "runtime")
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            _CHILD,
            str(REPO_ROOT),
            str(work),
            str(LATE_WRITE_AT),
            str(CHILD_LINGER),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for(predicate, ceiling: float = 20.0) -> bool:
    end = time.monotonic() + ceiling
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _try_second_holder(root: Path) -> bool:
    """One non-blocking attempt at the 1-of-1 slot, as another process would."""
    try:
        with slots_mod.hold(
            max_slots=1, repo="second-holder", root=root, timeout=0, backoff=0, jitter=0
        ):
            return True
    except slots_mod.SlotTimeout:
        return False


def _beats(work: Path) -> int:
    try:
        return (work / "heartbeat").stat().st_size
    except FileNotFoundError:
        return 0


def test_a_second_holder_never_acquires_while_the_zombie_lives(tmp_path: Path) -> None:
    """The adversary's probe shape, against a REAL hold under a tmp root.

    Liveness is judged by `slots.pid_alive` - the reaper's OWN predicate - and
    by the zombie's heartbeat, never by `Popen.poll()`. `poll()` can lag the
    exit code the reaper reads, so a poll-judged arm flaked 5 in 25 against a
    correct runner. `poll()` is still CALLED each turn, only to reap the child
    on POSIX, where an unreaped zombie pid reads as alive.
    """
    work = tmp_path / "work"
    work.mkdir()
    child = _spawn_child(work)
    try:
        assert _wait_for(lambda: (work / "started").exists()), "the zombie never started"
        refused_while_alive = 0
        acquired_alive: bool | None = None
        end = time.monotonic() + 20.0
        while time.monotonic() < end:
            child.poll()
            alive = slots_mod.pid_alive(child.pid)
            if _try_second_holder(work / "slots"):
                acquired_alive = slots_mod.pid_alive(child.pid)
                break
            if alive:
                refused_while_alive += 1
            time.sleep(0.02)
        assert acquired_alive is not None, "the slot never came free"
        assert refused_while_alive > 0, "non-vacuity: the slot was never contended"
        assert acquired_alive is False, "a second holder got the slot while the zombie ran"
        settled = _beats(work)
        time.sleep(0.3)
        assert _beats(work) == settled, "the zombie kept running after the slot was taken"
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(30)
    assert child.returncode == runner_mod.EXIT_JOB_ABANDONED


def test_the_process_dies_holding_its_slot_and_the_late_write_never_lands(
    tmp_path: Path,
) -> None:
    """The late-write race is closed by construction: the writer is dead."""
    work = tmp_path / "work"
    work.mkdir()
    child = _spawn_child(work)
    try:
        assert _wait_for(lambda: (work / "started").exists()), "the zombie never started"
        job_started = time.monotonic()
        child.wait(30)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(30)
    assert child.returncode == runner_mod.EXIT_JOB_ABANDONED
    assert child.returncode != 259, "STILL_ACTIVE would make a dead pid read as alive"
    assert time.monotonic() - job_started < LATE_WRITE_AT, "the child outlived the late write"

    # The slot was NOT released: the lock is still there, naming the dead pid.
    lock = work / "slots" / "0.lock"
    record = json.loads(lock.read_text(encoding="utf-8"))
    assert record["pid"] == child.pid
    assert not slots_mod.pid_alive(child.pid)

    # Wait past the moment the zombie would have written its stale state.
    remaining = LATE_WRITE_AT + 0.5 - (time.monotonic() - job_started)
    if remaining > 0:
        time.sleep(remaining)
    assert not (work / "late_state").exists(), "an abandoned job wrote after its process ended"

    # The health record says what happened, in friendly text.
    health = json.loads(
        health_mod.health_path(work / "runtime").read_text(encoding="utf-8")
    )
    assert health["alive"] is False
    assert health["last_pass_ok"] is False
    assert "overran" in health["message"]
    assert "Traceback" not in json.dumps(health)
    assert health["abandoned_jobs"] == ["zombie"]

    # The abandonment was counted BEFORE the process ended, so the restart
    # the supervisor makes can see it.
    record = json.loads((work / "runtime" / "job_abandonments.json").read_text(encoding="utf-8"))
    assert record["zombie"]["consecutive"] == 1

    # The dead-pid reap path frees the lock promptly for the next holder.
    t0 = time.monotonic()
    assert _try_second_holder(work / "slots"), "a dead-pid lock was not reaped"
    assert time.monotonic() - t0 < 2.0


def test_the_job_deadline_is_read_at_call_time() -> None:
    """The fixtures above patch the module attribute; a bound copy would ignore them."""
    source = Path(runner_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defaults = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.arguments)
        for default in [*node.defaults, *node.kw_defaults]
        if isinstance(default, ast.Name) and default.id == "JOB_DEADLINE_SECONDS"
    ]
    assert defaults == [], "JOB_DEADLINE_SECONDS bound as a default argument"
