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

Exit codes:
  0  the pass completed; no job failed, or it was a dry run
  1  at least one job FAILed in a non-dry run
  2  usage error - an unknown --job name, or argparse rejected the arguments

Inherited from Riot Commander's headless lane: a run summary lands in
`ops/runtime/health.json` (CLAUDE.md "Where to find current state"), and the
daemon shuts down cleanly on a signal rather than being killed mid-write.
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from headless import jobs as jobs_mod
from ops import health as health_mod

log = logging.getLogger("headless.runner")

#: Environment fallback for the account uid, so a scheduled task does not have
#: to bake the uid into its command line.
ENV_UID = "RESINCOMPUTE_UID"

DEFAULT_INTERVAL_SECONDS = 300

EXIT_OK = 0
EXIT_JOB_FAILED = 1
EXIT_USAGE = 2


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
        return (
            f"pass complete - {counts[jobs_mod.STATUS_PASS]} pass, "
            f"{counts[jobs_mod.STATUS_FAIL]} fail, "
            f"{counts[jobs_mod.STATUS_SKIP]} skip"
        )


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

    for spec in specs:
        result = jobs_mod.run_job(spec, context)
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


def run_daemon(
    uid: str | None,
    interval: int,
    dry_run: bool,
    job_names: Sequence[str] | None,
    runtime_dir: str | None,
    max_passes: int | None = None,
) -> int:
    """Run passes on an interval until a signal arrives.

    `max_passes` is a test and operations affordance: it bounds the loop so a
    supervised run can be exercised without relying on a signal being
    deliverable in the harness.
    """
    flag = _ShutdownFlag()
    installed = install_signal_handlers(flag)
    log.info(
        "daemon start - interval %ds, signal handlers: %s",
        interval,
        ", ".join(installed) if installed else "none available",
    )

    passes = 0
    last_ok = True
    while not flag.requested:
        outcome = run_pass(
            uid=uid,
            dry_run=dry_run,
            job_names=job_names,
            runtime_dir=runtime_dir,
        )
        last_ok = outcome.ok
        passes += 1
        if max_passes is not None and passes >= max_passes:
            log.info("daemon reached max_passes=%d, stopping", max_passes)
            break
        if flag.wait(max(1, int(interval))):
            break

    log.info("daemon stopped after %d pass(es)", passes)
    if not dry_run:
        _write_shutdown_health(runtime_dir)
    if dry_run:
        return EXIT_OK
    return EXIT_OK if last_ok else EXIT_JOB_FAILED


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
    # rather than sitting there doing nothing.
    outcome = run_pass(
        uid=uid,
        dry_run=args.dry_run,
        job_names=args.job_names,
        runtime_dir=runtime_dir,
    )

    # A dry run never fails the exit code on a job outcome: it computed and
    # logged, which is all it promised to do.
    if args.dry_run:
        return EXIT_OK
    return EXIT_OK if outcome.ok else EXIT_JOB_FAILED


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
