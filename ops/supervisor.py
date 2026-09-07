"""The watchdog.

Inherited wholesale from Sibling-C's own supervisor module, minus the
parts that only make sense for a project with an Electron overlay. The three
behaviours that carry over verbatim, because each one was paid for:

1. **The supervisor is the SOLE lifecycle owner.** It spawns, stops and
   restarts the managed child. Nothing else may start it. Two processes each
   believing they own a PID is how a restart loop begins.
2. **`restart_trigger.txt` is the restart channel.** Any content. The
   supervisor polls for it, CLEARS it, and restarts the child within about five
   seconds. Clearing before the restart, not after, is deliberate: a trigger
   that survives its own restart re-fires forever.
3. **NEVER `Stop-Process`.** CLAUDE.md states this as a hard rule for the
   parent project - `Stop-Process` hangs the MCP pipe. On Windows the child is
   terminated with `taskkill /F /PID <pid>`. This is not a style preference and
   it is not portable-by-accident: the POSIX path below uses SIGTERM then
   SIGKILL, and the Windows path uses taskkill. Do not "simplify" the two into
   `Popen.terminate()` on Windows.

Also inherited: the child is launched with `pythonw.exe` on Windows so a
scheduled task does not flash a console window on every restart. `pythonw`
suppresses its OWN console, never a child's, which is why the launch flags
below also pass CREATE_NO_WINDOW.

    python -m ops.supervisor --dry-run

verifies the configuration and exits 0 without spawning anything.
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ops import health as health_mod

log = logging.getLogger("ops.supervisor")

#: `ops/supervisor.py` -> `ops/` -> repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: Inherited channel name and location: repo root, not the runtime dir, so an
#: operator can drop it with a single `echo restart > restart_trigger.txt` from
#: wherever they already are.
RESTART_TRIGGER = "restart_trigger.txt"

#: Polled once a second so the inherited "restarts within about 5s" promise
#: holds with margin.
DEFAULT_POLL_SECONDS = 1.0

#: Bounded exponential backoff. Bounded matters: an unbounded retry against a
#: child that cannot start is a busy loop that hides the real failure.
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_FACTOR = 2.0
BACKOFF_CAP_SECONDS = 60.0
DEFAULT_MAX_RESTARTS = 0  # 0 means unbounded

#: A child that survives this long is considered to have started successfully,
#: which resets the backoff. Without this a slow crash-loop keeps the backoff
#: pinned at its cap forever.
HEALTHY_UPTIME_SECONDS = 60.0

#: Windows process-creation flag. Passing creationflags on POSIX raises, so
#: every use is platform-guarded.
CREATE_NO_WINDOW = 0x08000000

DEFAULT_CHILD_ARGS = ("-m", "headless.runner", "--daemon")


def is_windows() -> bool:
    return os.name == "nt"


def default_child_python() -> str:
    """The interpreter used to launch the child.

    `pythonw.exe` on Windows, so a logon-triggered scheduled task does not
    flash a console window on boot and again on every restart. Falls back to
    the running interpreter when the sibling `pythonw.exe` is not on disk,
    which is the case for a Store or embedded install.
    """
    current = Path(sys.executable)
    if is_windows():
        candidate = current.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(current)


@dataclass
class SupervisorConfig:
    """Everything the supervisor needs, resolved once at startup."""

    repo_root: Path = REPO_ROOT
    python_exe: str = field(default_factory=default_child_python)
    child_args: tuple[str, ...] = DEFAULT_CHILD_ARGS
    poll_seconds: float = DEFAULT_POLL_SECONDS
    max_restarts: int = DEFAULT_MAX_RESTARTS
    runtime_dir: Path | None = None
    log_level: str = "INFO"

    @property
    def trigger_path(self) -> Path:
        return self.repo_root / RESTART_TRIGGER

    @property
    def health_file(self) -> Path:
        return health_mod.health_path(
            self.runtime_dir, filename=health_mod.SUPERVISOR_HEALTH_FILENAME
        )

    def command(self) -> list[str]:
        return [self.python_exe, *self.child_args]


# ---------------------------------------------------------------------------
# Configuration check
# ---------------------------------------------------------------------------


def verify_config(config: SupervisorConfig) -> list[str]:
    """Return a list of configuration problems. Empty means good to launch.

    This is what `--dry-run` reports. It checks the things that actually fail
    in the field - a missing interpreter, an unwritable runtime directory, a
    child module that is not importable - rather than asserting the config
    object merely has the right shape.
    """
    problems: list[str] = []

    if not Path(config.python_exe).exists():
        problems.append(f"interpreter not found: {config.python_exe}")

    if not config.repo_root.is_dir():
        problems.append(f"repo root is not a directory: {config.repo_root}")

    runtime = health_mod.runtime_dir(config.runtime_dir)
    try:
        runtime.mkdir(parents=True, exist_ok=True)
        probe = runtime / ".supervisor_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        log.warning("runtime dir probe failed at %s: %s", runtime, exc)
        problems.append(f"runtime directory is not writable: {runtime}")

    # The child is launched as `-m <module>`; confirm the module resolves
    # rather than discovering it at the first restart storm.
    if len(config.child_args) >= 2 and config.child_args[0] == "-m":
        module = config.child_args[1]
        import importlib.util

        try:
            if importlib.util.find_spec(module) is None:
                problems.append(f"child module not importable: {module}")
        except (ImportError, ValueError) as exc:
            log.warning("could not resolve child module %s: %s", module, exc)
            problems.append(f"child module not importable: {module}")

    return problems


# ---------------------------------------------------------------------------
# Child lifecycle
# ---------------------------------------------------------------------------


def spawn_child(config: SupervisorConfig) -> subprocess.Popen[bytes]:
    """Start the managed child. The supervisor is the only caller."""
    kwargs: dict[str, object] = {
        "cwd": str(config.repo_root),
        "stdin": subprocess.DEVNULL,
    }
    if is_windows():
        # pythonw suppresses its own console, never a child's, so the flag is
        # still required even when python_exe is pythonw.exe.
        kwargs["creationflags"] = CREATE_NO_WINDOW
    command = config.command()
    log.info("spawning child: %s", " ".join(command))
    return subprocess.Popen(command, **kwargs)  # type: ignore[arg-type]


def terminate_child(proc: subprocess.Popen[bytes], timeout: float = 10.0) -> None:
    """Stop the managed child.

    WINDOWS: `taskkill /F /PID <pid>`. NEVER `Stop-Process` - CLAUDE.md records
    it as a hard rule for the parent project because it hangs the MCP pipe.
    `Popen.terminate()` on Windows is `TerminateProcess`, which is not the
    inherited path either; the operator-facing, documented, and
    audit-trail-producing way to kill a process on this fleet is taskkill.

    POSIX: SIGTERM, wait, then SIGKILL. The child installs a SIGTERM handler
    and shuts down cleanly, so the escalation is the exception path.
    """
    if proc.poll() is not None:
        return

    pid = proc.pid
    if is_windows():
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                check=False,
                capture_output=True,
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("taskkill failed for pid %s: %s", pid, exc)
    else:
        try:
            proc.terminate()
        except OSError as exc:
            log.warning("terminate failed for pid %s: %s", pid, exc)

    try:
        proc.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        log.warning("child pid %s did not exit within %.1fs, escalating", pid, timeout)

    try:
        proc.kill()
        proc.wait(timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        log.error("could not force-kill child pid %s: %s", pid, exc)


def backoff_delay(consecutive_failures: int) -> float:
    """Bounded exponential backoff, in seconds."""
    if consecutive_failures <= 0:
        return 0.0
    delay = BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (consecutive_failures - 1))
    return min(delay, BACKOFF_CAP_SECONDS)


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


def clear_trigger(path: Path) -> bool:
    """Delete the restart trigger. True if one was present.

    Cleared BEFORE the restart, never after: a trigger that outlives the
    restart it caused re-fires on the next poll, forever.
    """
    try:
        if not path.exists():
            return False
        path.unlink()
        return True
    except OSError as exc:
        log.warning("could not clear the restart trigger at %s: %s", path, exc)
        return False


def write_heartbeat(
    config: SupervisorConfig,
    child_pid: int | None,
    alive: bool,
    message: str,
    restarts: int,
    started_at: str,
) -> None:
    """Write the supervisor heartbeat. Never raises."""
    try:
        health_mod.write_health(
            alive=alive,
            started_at=started_at,
            role="supervisor",
            message=message,
            engine_version_value=health_mod.engine_version(),
            extra={"child_pid": child_pid, "restarts": restarts},
            base=config.runtime_dir,
            filename=health_mod.SUPERVISOR_HEALTH_FILENAME,
        )
    except OSError:
        log.exception("could not write the supervisor heartbeat")


def supervise(config: SupervisorConfig, stop: threading.Event | None = None) -> int:
    """Own the child's lifecycle until asked to stop.

    Returns 0 on a clean stop, 1 when the restart budget was exhausted.
    """
    stop = stop or threading.Event()
    started_at = health_mod.utc_now_iso()
    consecutive_failures = 0
    restarts = 0

    proc = spawn_child(config)
    child_started = time.monotonic()
    write_heartbeat(config, proc.pid, True, "child started", restarts, started_at)

    try:
        while not stop.is_set():
            if stop.wait(config.poll_seconds):
                break

            if clear_trigger(config.trigger_path):
                log.info("restart trigger seen - restarting the child")
                terminate_child(proc)
                proc = spawn_child(config)
                child_started = time.monotonic()
                restarts += 1
                consecutive_failures = 0
                write_heartbeat(config, proc.pid, True, "restarted on trigger", restarts, started_at)
                continue

            code = proc.poll()
            if code is None:
                write_heartbeat(config, proc.pid, True, "child running", restarts, started_at)
                continue

            uptime = time.monotonic() - child_started
            if uptime >= HEALTHY_UPTIME_SECONDS:
                # It ran long enough to count as a real start, so this is a
                # fresh failure rather than a continuing crash loop.
                consecutive_failures = 0
            consecutive_failures += 1
            restarts += 1
            log.warning(
                "child exited with code %s after %.1fs (failure %d)",
                code,
                uptime,
                consecutive_failures,
            )

            if config.max_restarts and restarts > config.max_restarts:
                log.error("restart budget of %d exhausted, giving up", config.max_restarts)
                write_heartbeat(config, None, False, "restart budget exhausted", restarts, started_at)
                return 1

            delay = backoff_delay(consecutive_failures)
            write_heartbeat(
                config, None, False, f"child down, retrying in {delay:.0f}s", restarts, started_at
            )
            if delay and stop.wait(delay):
                break

            proc = spawn_child(config)
            child_started = time.monotonic()
            write_heartbeat(config, proc.pid, True, "child restarted", restarts, started_at)
    finally:
        terminate_child(proc)
        write_heartbeat(config, None, False, "supervisor stopped", restarts, started_at)

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ops.supervisor",
        description="ResinCompute supervisor. Owns the headless runner's lifecycle.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="verify the configuration and exit without spawning anything",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        metavar="SECONDS",
        help=f"restart-trigger poll interval (default {DEFAULT_POLL_SECONDS})",
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=DEFAULT_MAX_RESTARTS,
        metavar="N",
        help="give up after N restarts (0 means unbounded, the default)",
    )
    parser.add_argument(
        "--child",
        action="append",
        default=None,
        metavar="ARG",
        dest="child_args",
        help="override one argument of the child command (repeatable)",
    )
    parser.add_argument("--log-level", default="INFO", metavar="LEVEL")
    return parser


def _configure_logging(level: str) -> None:
    numeric = getattr(logging, str(level).upper(), logging.INFO)
    if not isinstance(numeric, int):
        numeric = logging.INFO
    logging.basicConfig(
        level=numeric,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    config = SupervisorConfig(
        poll_seconds=max(0.1, float(args.interval)),
        max_restarts=max(0, int(args.max_restarts)),
        child_args=tuple(args.child_args) if args.child_args else DEFAULT_CHILD_ARGS,
        log_level=args.log_level,
    )

    problems = verify_config(config)
    if args.dry_run:
        print("supervisor configuration check")
        print(f"  repo root      : {config.repo_root}")
        print(f"  interpreter    : {config.python_exe}")
        print(f"  child command  : {' '.join(config.command())}")
        print(f"  restart trigger: {config.trigger_path}")
        print(f"  health file    : {config.health_file}")
        print(f"  poll interval  : {config.poll_seconds}s")
        print(f"  max restarts   : {config.max_restarts or 'unbounded'}")
        if problems:
            print("  problems:")
            for problem in problems:
                print(f"    - {problem}")
            print("dry run complete - configuration has problems, nothing was spawned")
        else:
            print("dry run complete - configuration is valid, nothing was spawned")
        # A dry run reports; it does not adjudicate. Exit 0 either way so the
        # check can be wired into a boot script without gating it.
        return 0

    if problems:
        for problem in problems:
            log.error("configuration problem: %s", problem)
        return 1

    try:
        return supervise(config)
    except KeyboardInterrupt:
        log.info("interrupted - stopping")
        return 0
    except Exception:  # noqa: BLE001 - top-level guard, must never traceback
        log.exception("supervisor loop crashed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
