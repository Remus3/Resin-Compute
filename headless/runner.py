"""The headless lane entrypoint.

    python -m headless.runner --once --dry-run

is the CI smoke test, and it must exit 0 on a tree where only this slice has
been built, with no network access and no arguments beyond those two. Every
design choice below serves that:

  - No sibling package is imported at module scope. Optional dependencies are
    imported inside the job that needs them, so an absent slice degrades ONE
    job to SKIP instead of breaking import of the runner.
  - A dry run writes NOTHING. Not the health file, not a log file, not a lock
    file. Logging goes to stderr only. "Compute and log, write nothing" is the
    literal contract, and a log FILE is a write.
  - No job can abort the pass. Every job is executed through
    `headless.jobs.run_job`, which absorbs anything the job leaks and reports
    it as FAIL. One broken job costs one line of the summary.

Daemon mode is governed. This tree's daemon loop is one participant in a
MACHINE-WIDE concurrency bucket shared with sibling repositories through the
vendored `ops/loop/slots.py`, so each LIVE pass runs inside a held slot and a
`SlotTimeout` is a failed cycle rather than permission to run unslotted. The
slot is held around the pass and nothing else, per that module's own contract,
and a dry run takes none: a slot is a lock file, and a dry run writes none.

Exit codes:
  0  the pass completed; no job failed, or it was a dry run
  1  at least one job FAILed in a non-dry run, or a live --once pass did not
     run at all - no slot came free, or the operator's HALT sentinel is present
  2  usage error - an unknown --job name, or argparse rejected the arguments

Inherited from Sibling-C's headless lane: a run summary lands in
`ops/runtime/health.json` (CLAUDE.md "Where to find current state"), and the
daemon shuts down cleanly on a signal rather than being killed mid-write.
"""
from __future__ import annotations

import argparse
import contextlib
import logging
import os
import signal
import sys
import threading
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from headless import jobs as jobs_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

log = logging.getLogger("headless.runner")

#: Environment fallback for the account uid, so a scheduled task does not have
#: to bake the uid into its command line.
ENV_UID = "RESINCOMPUTE_UID"

DEFAULT_INTERVAL_SECONDS = 300

#: The `repo` field written into a slot lockfile. It is a FREE-FORM HUMAN LABEL:
#: nothing in the vendored governor branches on it, and carriers spell it
#: differently on purpose - a sibling's measurement, reported rather than
#: re-measured here, has four carriers writing their full checkout root path and
#: one writing a short code. Its only job is telling a maintainer who is
#: grepping a stuck bucket which tree is holding a lane.
#:
#: "resin-compute" rather than the short code "rsc", for two reasons.
#: It is already the spelling every existing call site in this tree uses
#: (`tests/test_loop_concurrency.py`), so adopting it leaves ONE spelling in the
#: tree instead of adding a second. And a three-letter code is also this
#: repository's opaque cross-repo CODENAME, which would put a fleet codename
#: into a machine-wide artifact that other trees read - exactly the roster leak
#: `tests/test_no_sibling_names.py` exists to prevent.
#:
#: This is the single definition. Runtime code must not spell it inline.
SLOT_REPO_LABEL = "resin-compute"

EXIT_OK = 0
EXIT_JOB_FAILED = 1
EXIT_USAGE = 2
#: A LIVE pass left a job running past its deadline, so the process exited
#: without releasing its slot. Never 259: that is Windows STILL_ACTIVE, and
#: `slots.pid_alive` would read the dead process as alive.
EXIT_JOB_ABANDONED = 3

#: The operator's durable disarm. A file with this name in the runtime
#: directory (the `runtime_dir` argument, else the directory the health file
#: resolves to) stops every LIVE pass before it takes a slot. The runner NEVER
#: deletes it: a stop file cleared at launch fails to stop the first hold after
#: a restart, so removing it is the operator's act alone. A dry run ignores it.
HALT_SENTINEL_NAME = "HALT"

# Lock-age budget. `slots.hold()` stamps the lock's `ts` BEFORE it waits, so
# the age another carrier's reaper sees on a lock this process still holds is
#
#     slot wait + pass run + release drain
#
# and `slots.DEFAULT_STALE_AFTER` must exceed that sum, or a live lock is reaped
# as stale and the bucket over-admits. Each term is bounded here, and
# `tests/test_headless_runner_lock_budget.py` re-runs the arithmetic from these
# attributes. The pass deadline is checked BETWEEN jobs; the job running when it
# passes is itself bounded by JOB_DEADLINE_SECONDS plus JOB_CANCEL_GRACE_SECONDS,
# so the run term is the sum of the three.
#
# HOW A JOB IS BOUNDED, and why a thread and not a subprocess. Jobs share one
# in-process JobContext - `state` is threaded from job to job, and test fakes
# are registered as closures - so a subprocess would need every context and
# every job to pickle, which none of them do. Each job therefore runs on a
# daemon worker thread and the pass waits for it at most the deadline. A job
# still running then is FAILED, `context.cancel` is set, and the pass waits a
# short grace for it to notice. A Python thread cannot be killed, so a job that
# ignores `cancel` keeps running, ABANDONED, and no further job in that pass
# starts (it may still be mutating the shared context). On a LIVE pass the
# invariant is: NO SLOT OF THIS PROCESS IS RELEASED WHILE A JOB OF THIS
# PROCESS IS STILL RUNNING. So the process ends inside the hold, slot still
# held - see `_die_holding_slot` - which kills the abandoned job and leaves a
# dead-pid lock for `slots.is_stale` to reclaim. A dry run holds no slot, so
# there the job just stays abandoned on its daemon thread, and a later LIVE
# pass in the same process refuses to take a slot until it ends.

#: Ceiling on any slot wait, daemon or one-shot, whatever `--interval` says.
MAX_SLOT_WAIT_SECONDS = 300

#: Once a pass has run this long, it starts no further jobs; the rest are
#: recorded as SKIP and run on the next pass.
PASS_DEADLINE_SECONDS = 3600

#: The longest one job may run before it is recorded FAIL and the pass moves on.
JOB_DEADLINE_SECONDS = 900

#: After a job overruns and its `cancel` event is set, how long the pass waits
#: for it to return before abandoning it.
JOB_CANCEL_GRACE_SECONDS = 5


# ---------------------------------------------------------------------------
# Pass result
# ---------------------------------------------------------------------------


@dataclass
class PassResult:
    """Outcome of one reconciliation pass."""

    started_at: str
    finished_at: str = ""
    dry_run: bool = False
    uid: str | None = None
    results: list[jobs_mod.JobResult] = field(default_factory=list)
    #: Jobs not started because the pass ran past PASS_DEADLINE_SECONDS.
    #: Appended last with a default, per the tree's dataclass convention.
    deadline_skipped: int = 0
    #: Jobs recorded FAIL because they overran JOB_DEADLINE_SECONDS.
    overran: int = 0

    @property
    def failed(self) -> list[jobs_mod.JobResult]:
        return [r for r in self.results if r.failed]

    @property
    def ok(self) -> bool:
        return not self.failed

    def counts(self) -> dict[str, int]:
        out = {jobs_mod.STATUS_PASS: 0, jobs_mod.STATUS_FAIL: 0, jobs_mod.STATUS_SKIP: 0}
        for result in self.results:
            out[result.status] = out.get(result.status, 0) + 1
        return out

    def summary_line(self) -> str:
        counts = self.counts()
        line = (
            f"pass complete - {counts[jobs_mod.STATUS_PASS]} pass, "
            f"{counts[jobs_mod.STATUS_FAIL]} fail, "
            f"{counts[jobs_mod.STATUS_SKIP]} skip"
        )
        # A deadline cut is not a failure (the exit code stays 0), but it must
        # not read as a plain green pass either.
        if self.deadline_skipped:
            line += f"; deadline reached: {self.deadline_skipped} jobs not started"
        if self.overran:
            line += f"; {self.overran} job overran its deadline and was failed"
        return line


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging(level: str, dry_run: bool) -> None:
    """Install a stderr log handler.

    `core.log_setup` is the tree's sanctioned logger and is preferred when it
    is present, but it is NEVER called during a dry run: it owns the log file,
    and a dry run that creates `logs/` has already broken the "write nothing"
    contract. The stderr-only fallback below is used in that case, and it is
    also what runs while `core.log_setup` is still an unbuilt sibling slice.
    """
    numeric = getattr(logging, str(level).upper(), logging.INFO)
    if not isinstance(numeric, int):
        numeric = logging.INFO

    if not dry_run and _configure_via_core_log_setup(numeric):
        return

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(numeric)


def _configure_via_core_log_setup(numeric: int) -> bool:
    """Install the tree's sanctioned logging, returning True when it took.

    `core.log_setup` exposes `get_logger(name)`, verified by inspection rather
    than assumed - it is idempotent and attaches a console handler plus the
    daily `logs/YYYY-MM-DD.log` file handler. Calling it for the ROOT logger
    name means every module in the pass propagates into those handlers, rather
    than only the one logger this module happens to hold.

    `configure` / `setup_logging` are probed first so a later rename of the
    entrypoint does not silently drop this lane back to stderr.

    Returns False on any shortfall - absent slice, unexpected entrypoint shape,
    or handlers that did not actually attach - so the caller installs the
    stderr fallback. A logging setup that half-worked is worse than one that
    plainly did not.
    """
    try:
        from core import log_setup as core_log_setup
    except ImportError:
        return False

    for entrypoint in ("configure", "setup_logging"):
        candidate = getattr(core_log_setup, entrypoint, None)
        if callable(candidate):
            try:
                candidate(level=numeric)
            except TypeError:
                continue
            logging.getLogger().setLevel(numeric)
            return True

    get_logger = getattr(core_log_setup, "get_logger", None)
    if not callable(get_logger):
        return False
    try:
        root = get_logger("")
    except (TypeError, ValueError, OSError):
        log.debug("core.log_setup.get_logger did not accept the root name")
        return False
    if not getattr(root, "handlers", None):
        return False
    root.setLevel(numeric)
    return True


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def select_jobs(names: Sequence[str] | None) -> list[jobs_mod.JobSpec]:
    """Resolve the requested job names to specs, in registry order.

    With no names, the whole registry runs in dependency order. With names, ONLY
    those jobs run: `--job` means "instead of the full pass", so dependencies
    are deliberately NOT pulled in. Running an unrequested job because something
    else asked for it would make `--job` unusable for the case it exists for,
    which is re-running one job in isolation.

    Raises `KeyError` on an unknown name so the caller can render a friendly
    usage error rather than a traceback.
    """
    ordered = jobs_mod.ordered_jobs()
    if not names:
        return ordered
    wanted = list(names)
    known = {spec.name for spec in ordered}
    unknown = [n for n in wanted if n not in known]
    if unknown:
        raise KeyError(", ".join(unknown))
    return [spec for spec in ordered if spec.name in set(wanted)]


#: Jobs that overran, ignored `cancel`, and are still running. Keyed by the
#: Thread OBJECT, never by `ident` - idents are reused once a thread ends, so
#: an ident-keyed record can name a thread that is not the job's.
_abandoned_lock = threading.Lock()
_abandoned: list[tuple[str, threading.Thread]] = []


def abandoned_jobs() -> list[str]:
    """Names of overrun jobs whose worker thread is STILL alive, oldest first.

    Ended workers are pruned on every call, so the list never grows past the
    jobs that are actually still running.
    """
    with _abandoned_lock:
        _abandoned[:] = [(name, worker) for name, worker in _abandoned if worker.is_alive()]
        return [name for name, _ in _abandoned]


def _run_job_bounded(
    spec: jobs_mod.JobSpec, context: jobs_mod.JobContext
) -> tuple[jobs_mod.JobResult, bool]:
    """Run one job on a worker thread, waiting at most JOB_DEADLINE_SECONDS.

    Returns `(result, overran)`. A job that overruns is ALWAYS a FAIL - a late
    success is discarded, never recorded. See the budget note at the constants
    for why this is a thread and what the residual is.

    Both constants are read at call time, so a test can inject a small one.
    """
    limit = float(JOB_DEADLINE_SECONDS)
    grace = float(JOB_CANCEL_GRACE_SECONDS)
    box: list[jobs_mod.JobResult] = []

    def _work() -> None:
        # run_job absorbs every Exception into a FAIL; a BaseException ends
        # the thread with `box` empty, which is handled below.
        box.append(jobs_mod.run_job(spec, context))

    worker = threading.Thread(target=_work, name=f"headless-job-{spec.name}", daemon=True)
    start = time.monotonic()
    worker.start()
    worker.join(limit)
    if not worker.is_alive():
        if box:
            return box[0], False
        log.error("job %s ended without a result", spec.name)
        return (
            jobs_mod.failed(spec.name, "job ended without a result - see the log"),
            False,
        )

    context.cancel.set()
    worker.join(grace)
    elapsed = time.monotonic() - start
    abandoned = worker.is_alive()
    if abandoned:
        with _abandoned_lock:
            _abandoned.append((spec.name, worker))
    log.error(
        "job %s overran its %gs deadline (%.1fs) and was recorded FAIL; %s",
        spec.name,
        limit,
        elapsed,
        "it ignored cancel and is still running, abandoned"
        if abandoned
        else "it stopped after cancel",
    )
    result = jobs_mod.JobResult(
        name=spec.name,
        status=jobs_mod.STATUS_FAIL,
        message=(
            f"did not finish within its {limit:g}s deadline - recorded as failed"
        ),
        duration_ms=elapsed * 1000.0,
        details={"deadline_seconds": limit, "abandoned": abandoned},
    )
    return result, True


def run_pass(
    uid: str | None = None,
    dry_run: bool = False,
    job_names: Sequence[str] | None = None,
    runtime_dir: str | None = None,
    options: dict[str, Any] | None = None,
    write_summary: bool = True,
) -> PassResult:
    """Run one reconciliation pass.

    Never raises on a job failure. The only exception that escapes is a
    `KeyError` from `select_jobs` for an unknown job name, which is a usage
    error the caller reports before any job runs.
    """
    started_at = _utc_now_iso()
    specs = select_jobs(job_names)
    context = jobs_mod.JobContext(
        uid=uid,
        dry_run=dry_run,
        runtime_dir=runtime_dir,
        started_at=started_at,
        options=dict(options or {}),
    )
    outcome = PassResult(started_at=started_at, dry_run=dry_run, uid=uid)

    mode = "dry run" if dry_run else "live"
    log.info("pass start (%s) - %d job(s), uid=%s", mode, len(specs), uid or "unset")

    # Monotonic, never `time.time`: a wall-clock step must not end a pass early
    # or extend it. Looked up at call time, not bound at import.
    deadline = float(PASS_DEADLINE_SECONDS)
    pass_start = time.monotonic()
    for spec in specs:
        elapsed = time.monotonic() - pass_start
        if outcome.overran:
            # A job overran and may still be running, mutating the shared
            # context. Nothing after it may read that context, so the rest of
            # the pass is not started. SKIP, not FAIL: the overrun job already
            # carries the failure.
            result = jobs_mod.skipped(
                spec.name,
                "not started - an earlier job overran its deadline; "
                "it will run on the next pass",
            )
        elif elapsed > deadline:
            # Checked BEFORE a job starts, never during one: a running job is
            # not interrupted, which is the residual named at the budget
            # constants. The remaining jobs are a SKIP, not a FAIL - they did
            # not go wrong, they were not reached.
            result = jobs_mod.skipped(
                spec.name,
                f"not started - the pass ran past its {int(deadline)}s deadline; "
                "it will run on the next pass",
                deadline_seconds=int(deadline),
            )
            outcome.deadline_skipped += 1
        else:
            result, overran = _run_job_bounded(spec, context)
            if overran:
                outcome.overran += 1
        context.results[spec.name] = result
        outcome.results.append(result)
        log.info("%-6s %-16s %s", result.status, result.name, result.message)

    outcome.finished_at = _utc_now_iso()
    log.info("%s", outcome.summary_line())

    # A dry run writes NOTHING, so the summary is skipped entirely rather than
    # written to a scratch location.
    if write_summary and not dry_run:
        _write_summary(outcome, runtime_dir)

    return outcome


def _write_summary(outcome: PassResult, runtime_dir: str | None) -> None:
    """Persist the pass summary to the health file. Never raises."""
    try:
        health_mod.write_health(
            alive=True,
            started_at=outcome.started_at,
            last_pass_at=outcome.finished_at,
            last_pass_ok=outcome.ok,
            jobs=[r.as_dict() for r in outcome.results],
            engine_version_value=health_mod.engine_version(),
            role="headless-runner",
            uid=outcome.uid,
            message=outcome.summary_line(),
            base=Path(runtime_dir) if runtime_dir else None,
        )
    except OSError:
        # Losing the health write must not fail an otherwise good pass. The
        # raw error goes to the log, never to a user-facing surface.
        log.exception("could not write the pass summary to the health file")


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


class _ShutdownFlag:
    """Cooperative stop signal shared by the signal handlers and the loop."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request(self, reason: str) -> None:
        if not self._event.is_set():
            log.info("shutdown requested (%s)", reason)
        self._event.set()

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    def wait(self, seconds: float) -> bool:
        """Sleep, waking early on shutdown. Returns True if shutdown was asked for."""
        return self._event.wait(timeout=seconds)


def install_signal_handlers(flag: _ShutdownFlag) -> list[str]:
    """Install clean-shutdown handlers, tolerating a platform that lacks them.

    SIGTERM does not exist on Windows in the POSIX sense, and `signal.signal`
    also raises ValueError when called off the main thread (which is exactly
    what happens when a test drives the daemon from a worker). Both are
    degradations, not errors: the daemon then relies on the loop's own exit
    conditions. Returns the signal names actually installed so the caller can
    log what it got rather than what it hoped for.
    """
    installed: list[str] = []
    for signame in ("SIGTERM", "SIGINT", "SIGBREAK"):
        signum = getattr(signal, signame, None)
        if signum is None:
            continue
        try:
            signal.signal(signum, lambda _s, _f, _n=signame: flag.request(_n))
        except (ValueError, OSError, RuntimeError) as exc:
            log.debug("could not install a handler for %s: %s", signame, exc)
            continue
        installed.append(signame)
    return installed


def _lane_width() -> int:
    """The cross-repo ceiling on concurrent executor calls.

    Imported HERE rather than at module scope, for the reason in this module's
    docstring: a sibling slice must not be able to break `--once --dry-run`.
    There is deliberately NO fallback value. `slots.hold`'s signature default of
    2 and `Config.max_concurrent_lanes` are different numbers that do not govern
    this bucket, and inventing a width is worse than failing loudly - every
    participant must read the SAME number or the bucket bounds nothing.
    """
    from core.config import MAX_CONCURRENT_LANES

    return MAX_CONCURRENT_LANES


class _Halted:
    """The type of `HALTED`: a pass that did not run because of the sentinel.

    Distinct from None (a starved pass) so the daemon can stop on one and
    retry on the other, and falsy so no caller can read it as a PassResult.
    """

    _instance: _Halted | None = None

    def __new__(cls) -> _Halted:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "HALTED"


HALTED = _Halted()


def halt_sentinel_path(runtime_dir: str | None) -> Path:
    """Where the operator's HALT file lives: the same directory as the health file."""
    return health_mod.runtime_dir(Path(runtime_dir) if runtime_dir else None) / HALT_SENTINEL_NAME


def _halt_requested(runtime_dir: str | None, cycle: int) -> bool:
    """True when the operator's sentinel is present. Fails CLOSED.

    If the sentinel's presence cannot be determined, the lane stays disarmed:
    a stop control that silently reads as "go" when it cannot be read is not a
    stop control. The raw error goes to the debug log, never to a surface.

    `os.lstat` directly, NEVER `Path.exists()`: on 3.14 `exists()` swallows
    every OSError and answers False, and on 3.11 it still swallows some Windows
    errors (WinError 123), so an unreadable sentinel would read as absent and
    the pass would RUN. Only "there is no entry" - FileNotFoundError, or
    NotADirectoryError when a parent is not a directory - means not halted.

    `lstat`, never `stat`: `stat` follows a symlink, so a HALT link whose
    target is missing raises FileNotFoundError there and would read as "go".
    Any directory entry named HALT - a file, a directory, a dangling or live
    link - is the operator's stop. What it points at is not consulted.
    """
    path = halt_sentinel_path(runtime_dir)
    try:
        os.lstat(path)
        present = True
    except (FileNotFoundError, NotADirectoryError):
        present = False
    except OSError:
        log.warning(
            "cycle %d halted - could not check for the operator sentinel %s, so the "
            "pass did NOT run (a stop control that cannot be read stays stopped)",
            cycle,
            path,
        )
        log.debug("sentinel check failed", exc_info=True)
        return True
    if present:
        log.warning(
            "cycle %d halted by operator sentinel %s - no slot taken, the pass did "
            "NOT run. Remove the file to resume; the runner never removes it.",
            cycle,
            path,
        )
    return present


def _die_holding_slot(outcome: PassResult, runtime_dir: str | None, cycle: int) -> None:
    """End the PROCESS, slot still held, because a job of this pass is abandoned.

    THE INVARIANT: no slot of this process is released while a job of this
    process is still running. A thread cannot be killed and a process can, so
    the process goes. That kills the abandoned job - it can write nothing
    after this point, which closes the late-write race by construction - and
    leaves the lock with a dead pid, which `slots.is_stale` reclaims on the
    next `hold()` by any carrier. `os._exit`, never `sys.exit`: SystemExit
    would unwind through the hold's `finally` and RELEASE the slot while the
    job still ran. Under the supervisor the daemon is restarted on this exit.

    RESIDUAL, accepted: the abandoned thread dies wherever it is, so a temp
    file it was writing through `core/atomic_io.py` can be left behind. The
    target itself is never torn - a temp only becomes the target by an atomic
    `replace` - and nothing in this tree sweeps orphaned temps; their names
    carry pid and a random suffix, so they never collide with a later write.
    """
    names = abandoned_jobs()
    log.critical(
        "cycle %d: %d job(s) overran their deadline and are still running (%s). The "
        "runner is exiting with code %d WITHOUT releasing its lane slot, so that no "
        "work of this process runs outside a held slot; the lock is reclaimed once "
        "this process is gone.",
        cycle,
        len(names),
        ", ".join(names),
        EXIT_JOB_ABANDONED,
    )
    try:
        health_mod.write_health(
            alive=False,
            started_at=outcome.started_at,
            last_pass_at=outcome.finished_at,
            last_pass_ok=False,
            jobs=[r.as_dict() for r in outcome.results],
            engine_version_value=health_mod.engine_version(),
            role="headless-runner",
            uid=outcome.uid,
            message=(
                "a job overran its deadline and could not be stopped, so the runner "
                "exited to stop it; it restarts under its supervisor"
            ),
            extra={"abandoned_jobs": names, "exit_code": EXIT_JOB_ABANDONED},
            base=Path(runtime_dir) if runtime_dir else None,
        )
    except Exception:  # noqa: BLE001 - nothing may stop the exit below
        log.exception("could not write the abandonment record to the health file")
    for handler in logging.getLogger().handlers + log.handlers:
        with contextlib.suppress(Exception):
            handler.flush()
    os._exit(EXIT_JOB_ABANDONED)


def _run_governed_pass(
    uid: str | None,
    dry_run: bool,
    job_names: Sequence[str] | None,
    runtime_dir: str | None,
    run_id: str,
    cycle: int,
    slot_root: str | Path | None,
    slot_timeout: float,
) -> PassResult | _Halted | None:
    """Run one pass while holding one machine-wide lane slot.

    Returns `HALTED` when the operator's HALT sentinel is present: no slot is
    taken and the pass does not run. Checked on every call, immediately before
    the hold, so a daemon stops at the next pass after the file appears.

    The slot wait is clamped to `MAX_SLOT_WAIT_SECONDS` here, the one place
    every caller passes through, so no caller can push a lock's age past the
    budget recorded at that constant.

    Returns None when no slot came free inside the timeout. That is a FAILED
    cycle: the pass does not run, and the caller must never read it as
    permission to proceed unslotted. The bucket exists because the participating
    repositories share one rate-limit pool, so a cycle that ran anyway would
    defeat the governor for every carrier at once, silently.

    The slot wraps the pass and NOTHING else - not the lane-width read, not the
    signal handlers, not the shutdown health write. That is the vendored
    module's own contract: "HELD ONLY AROUND THE EXECUTOR CALL, never around git
    or the adjudicator, so a long merge in one repo cannot starve the other."

    A dry run takes no slot. This module promises a dry run writes nothing -
    "not the health file, not a log file, not a lock file" - and a slot IS a
    lock file. It also reaches no rate-limited resource, so it is not work the
    bucket exists to bound.
    """
    if dry_run:
        return run_pass(
            uid=uid, dry_run=True, job_names=job_names, runtime_dir=runtime_dir
        )

    # Read OUTSIDE the critical section: config loading is setup, not executor
    # work, and holding a shared lane while doing it starves the other carriers.
    max_slots = _lane_width()
    root = Path(slot_root) if slot_root is not None else None
    slot_timeout = min(float(slot_timeout), float(MAX_SLOT_WAIT_SECONDS))

    if _halt_requested(runtime_dir, cycle):
        return HALTED

    # An abandoned job from an earlier pass is executor work still running
    # outside any slot. Taking a new slot now would let the two overlap, so
    # the cycle FAILS, exactly like a starved one, until that job ends.
    still_running = abandoned_jobs()
    if still_running:
        log.error(
            "cycle %d failed - %d overrun job(s) from an earlier pass still running "
            "(%s). The pass did NOT run and took no slot.",
            cycle,
            len(still_running),
            ", ".join(still_running),
        )
        return None

    try:
        with slots_mod.hold(
            max_slots=max_slots,
            repo=SLOT_REPO_LABEL,
            run_id=run_id,
            cycle=cycle,
            root=root,
            timeout=slot_timeout,
            log=lambda message: log.info("%s", message),
        ):
            outcome = run_pass(
                uid=uid, dry_run=False, job_names=job_names, runtime_dir=runtime_dir
            )
            if abandoned_jobs():
                # INSIDE the hold, on purpose: this never returns, so the
                # hold's `finally` never runs and the slot is NOT released.
                _die_holding_slot(outcome, runtime_dir, cycle)
            return outcome
    except slots_mod.SlotTimeout:
        # Never swallowed into a success path, and never surfaced raw. The
        # operator gets a cause; the exception text goes to the debug log.
        log.error(
            "cycle %d failed - no lane slot free within %ss (%d lanes). The pass did "
            "NOT run: a busy bucket is a failed cycle, never permission to run "
            "unslotted.",
            cycle,
            slot_timeout,
            max_slots,
        )
        log.debug("slot acquisition timed out", exc_info=True)
        return None


def run_daemon(
    uid: str | None,
    interval: int,
    dry_run: bool,
    job_names: Sequence[str] | None,
    runtime_dir: str | None,
    max_passes: int | None = None,
    slot_root: str | Path | None = None,
    slot_timeout: float | None = None,
) -> int:
    """Run passes on an interval until a signal arrives.

    `max_passes` is a test and operations affordance: it bounds the loop so a
    supervised run can be exercised without relying on a signal being
    deliverable in the harness.

    `slot_root` and `slot_timeout` are APPENDED with defaults, per the tree's
    convention. `slot_root` defaults to the vendored governor's machine-wide
    bucket and is overridden only by tests, which must never touch that bucket:
    sibling repositories hold lanes in it live. `slot_timeout` defaults to one
    interval - waiting longer than that means the pass is already late, so the
    cycle fails and the next tick tries again rather than the loop piling up -
    and never more than `MAX_SLOT_WAIT_SECONDS`, because `--interval` is
    unbounded and the slot wait counts toward a held lock's age.

    The operator's HALT sentinel is checked on EVERY pass. When it is present
    the loop stops and the daemon exits `EXIT_OK`: a halt is an operator's
    clean stop, not a failure of this process.
    """
    flag = _ShutdownFlag()
    installed = install_signal_handlers(flag)
    log.info(
        "daemon start - interval %ds, signal handlers: %s",
        interval,
        ", ".join(installed) if installed else "none available",
    )

    run_id = uuid.uuid4().hex[:12]
    timeout = (
        float(min(max(1, int(interval)), MAX_SLOT_WAIT_SECONDS))
        if slot_timeout is None
        else float(slot_timeout)
    )

    passes = 0
    last_ok = True
    halted = False
    while not flag.requested:
        passes += 1
        outcome = _run_governed_pass(
            uid=uid,
            dry_run=dry_run,
            job_names=job_names,
            runtime_dir=runtime_dir,
            run_id=run_id,
            cycle=passes,
            slot_root=slot_root,
            slot_timeout=timeout,
        )
        if outcome is HALTED:
            halted = True
            log.info("daemon halted by operator sentinel at cycle %d, stopping", passes)
            break
        # A starved cycle has no PassResult at all, and it is a FAILURE. This is
        # the one place a None could be mistaken for "nothing went wrong".
        last_ok = outcome is not None and outcome.ok
        if max_passes is not None and passes >= max_passes:
            log.info("daemon reached max_passes=%d, stopping", max_passes)
            break
        if flag.wait(max(1, int(interval))):
            break

    log.info("daemon stopped after %d pass(es)", passes)
    if not dry_run:
        _write_shutdown_health(runtime_dir)
    if dry_run or halted:
        return EXIT_OK
    return EXIT_OK if last_ok else EXIT_JOB_FAILED


#: How long a live `--once` pass waits for a lane slot before it fails. A daemon
#: waits one interval because its next tick retries; a one-shot has no next
#: tick of its own, so it waits one DEFAULT interval - the cadence a scheduled
#: one-shot stands in for - and then fails with EXIT_JOB_FAILED.
ONCE_SLOT_TIMEOUT_SECONDS = DEFAULT_INTERVAL_SECONDS


def run_once(
    uid: str | None,
    dry_run: bool,
    job_names: Sequence[str] | None,
    runtime_dir: str | None,
    slot_root: str | Path | None = None,
    slot_timeout: float | None = None,
) -> int:
    """Run ONE pass, governed exactly as a daemon pass is, and return an exit code.

    A live `--once` pass reaches the same rate-limited resource a daemon pass
    does, so it holds one machine-wide lane slot through `_run_governed_pass`
    rather than calling `run_pass` bare. A dry run takes no slot - the same
    helper owns that rule for both modes, so they cannot drift apart.

    A `SlotTimeout` is a FAILED pass: the pass does not run and the exit code is
    `EXIT_JOB_FAILED`, never `EXIT_OK`. A pass that raises propagates, and the
    slot is released by the vendored `hold()`'s own finally.

    `slot_root` defaults to the vendored governor's machine-wide bucket and is
    overridden only by tests, which must never touch that bucket.
    """
    timeout = (
        float(ONCE_SLOT_TIMEOUT_SECONDS) if slot_timeout is None else float(slot_timeout)
    )
    outcome = _run_governed_pass(
        uid=uid,
        dry_run=dry_run,
        job_names=job_names,
        runtime_dir=runtime_dir,
        run_id=uuid.uuid4().hex[:12],
        cycle=1,
        slot_root=slot_root,
        slot_timeout=timeout,
    )
    # A dry run never fails the exit code on a job outcome: it computed and
    # logged, which is all it promised to do. It also never starves, because
    # it takes no slot, so `outcome` is never None here on the dry path.
    if dry_run:
        return EXIT_OK
    # None is a starved pass and HALTED is a pass the operator's sentinel
    # stopped. Both are a pass that did NOT run, so both are EXIT_JOB_FAILED -
    # never read as "no news". `isinstance` rather than truthiness, so neither
    # sentinel can be mistaken for a result.
    if not isinstance(outcome, PassResult):
        return EXIT_JOB_FAILED
    return EXIT_OK if outcome.ok else EXIT_JOB_FAILED


def _write_shutdown_health(runtime_dir: str | None) -> None:
    """Mark the health file not-alive on a clean exit. Never raises."""
    try:
        health_mod.write_health(
            alive=False,
            role="headless-runner",
            message="stopped cleanly",
            base=Path(runtime_dir) if runtime_dir else None,
        )
    except OSError:
        log.exception("could not write the shutdown health record")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="headless.runner",
        description="ResinCompute headless reconciliation runner. No UI, no prompts.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="run one reconciliation pass and exit")
    mode.add_argument("--daemon", action="store_true", help="run continuously on an interval")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        metavar="N",
        help=f"seconds between passes in daemon mode (default {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and log, write nothing",
    )
    parser.add_argument(
        "--job",
        action="append",
        default=None,
        metavar="NAME",
        dest="job_names",
        help="run one named job instead of the full pass (repeatable)",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="print the registered jobs and exit",
    )
    parser.add_argument("--uid", default=None, help="account uid to reconcile")
    parser.add_argument(
        "--log-level",
        default="INFO",
        metavar="LEVEL",
        help="DEBUG, INFO, WARNING, ERROR or CRITICAL (default INFO)",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=None,
        metavar="N",
        help="stop the daemon after N passes (testing and bounded runs)",
    )
    return parser


def _print_job_listing(stream: Any = None) -> None:
    out = stream or sys.stdout
    specs = jobs_mod.ordered_jobs()
    print(f"{len(specs)} registered job(s), in dependency order:", file=out)
    for index, spec in enumerate(specs, start=1):
        deps = ", ".join(spec.depends_on) if spec.depends_on else "-"
        print(f"  {index}. {spec.name}", file=out)
        print(f"       cadence: {spec.cadence}", file=out)
        print(f"       depends: {deps}", file=out)
        if spec.description:
            print(f"       {spec.description}", file=out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level, args.dry_run)

    if args.list_jobs:
        _print_job_listing()
        return EXIT_OK

    # Validate the job names BEFORE any work starts, so an unknown name costs
    # nothing and the message names the valid options.
    try:
        select_jobs(args.job_names)
    except KeyError as exc:
        known = ", ".join(jobs_mod.job_names()) or "none registered"
        print(
            f"error: unknown job name(s): {exc.args[0]}\n"
            f"       known jobs: {known}\n"
            f"       run --list-jobs for details",
            file=sys.stderr,
        )
        return EXIT_USAGE

    uid = args.uid or os.environ.get(ENV_UID) or None
    runtime_dir = os.environ.get(health_mod.ENV_RUNTIME_DIR) or None

    if args.daemon:
        return run_daemon(
            uid=uid,
            interval=args.interval,
            dry_run=args.dry_run,
            job_names=args.job_names,
            runtime_dir=runtime_dir,
            max_passes=args.max_passes,
        )

    # `--once` is the default shape: a bare invocation runs a single pass
    # rather than sitting there doing nothing. It is governed by the same lane
    # slot as a daemon pass; see `run_once`.
    return run_once(
        uid=uid,
        dry_run=args.dry_run,
        job_names=args.job_names,
        runtime_dir=runtime_dir,
    )


def _entrypoint() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        # Ctrl-C outside the daemon loop. Not an error, and never a traceback
        # on a user-facing surface.
        print("interrupted", file=sys.stderr)
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(_entrypoint())
