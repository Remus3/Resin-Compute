r"""An operator HALT sentinel disarms the live headless lane before any slot.

WHAT THIS GUARDS.

`headless/runner.py` holds a MACHINE-WIDE lane slot around every live pass.
An operator who needs that lane to stop - without killing a process and
without editing a scheduled task - drops a file named `HALT` into the runtime
directory. The runner then:

  1. takes NO slot and runs NO pass, on every live pass, daemon or `--once`;
  2. reports a halted `--once` as `EXIT_JOB_FAILED` - a pass that did not run
     is never reported as success, the same rule a `SlotTimeout` follows;
  3. stops a daemon at the NEXT pass when the file appears mid-run, and exits
     `EXIT_OK` - the sentinel is checked on every iteration, not at launch;
  4. NEVER deletes the file. A disarm the runner clears itself is a disarm
     that fails to stop the first hold after a restart;
  5. ignores it on a dry run, which takes no slot and writes nothing anyway.

The neighbour arm proves the gate is not simply closed: with no sentinel the
pass runs and the slot is acquired and released.

THE LIVE BUCKET IS OFF LIMITS. Every call here passes `slot_root` under
`tmp_path` and `runtime_dir` under `tmp_path`; the AST guard at the top of the
module enforces the first by parsing this file.
"""
from __future__ import annotations

import ast
import contextlib
import os
from pathlib import Path

import pytest

from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

PROBE_JOB = "halt_probe"
SENTINEL = "HALT"


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


class _Spy:
    """Counts calls to a wrapped callable while delegating to it."""

    def __init__(self, target):
        self.target = target
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.target(*args, **kwargs)


@pytest.fixture()
def spies(monkeypatch: pytest.MonkeyPatch):
    hold_spy = _Spy(slots_mod.hold)
    pass_spy = _Spy(runner_mod.run_pass)
    monkeypatch.setattr(slots_mod, "hold", hold_spy)
    monkeypatch.setattr(runner_mod, "run_pass", pass_spy)
    # The daemon sleeps one interval between passes; the arms here are about
    # the sentinel, not the clock, so the wait returns at once (no shutdown).
    monkeypatch.setattr(runner_mod._ShutdownFlag, "wait", lambda self, seconds: False)
    return hold_spy, pass_spy


def _locks(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("*.lock"))


def _register_probe(seen: list[int], root: Path, plant: Path | None = None) -> None:
    """A job recording the on-disk lock count; optionally plants a sentinel."""

    def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        seen.append(len(_locks(root)))
        if plant is not None:
            plant.write_text("stop\n", encoding="utf-8")
        return jobs_mod.passed(PROBE_JOB, "recorded")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name=PROBE_JOB,
            description="records the on-disk lock count",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=_probe,
        )
    )


def _plant(runtime: Path) -> Path:
    path = runtime / SENTINEL
    path.write_text("operator disarm\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 0. Guards on this module itself
# ---------------------------------------------------------------------------


def test_no_arm_here_can_reach_the_live_bucket() -> None:
    """Every run_daemon / run_once call in this file names its own bucket."""
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
        assert "slot_root" in names, (
            f"call at line {node.lineno} omits slot_root and would acquire against "
            f"{slots_mod.DEFAULT_ROOT}, the machine-wide bucket"
        )
        assert "runtime_dir" in names, (
            f"call at line {node.lineno} omits runtime_dir and would read the real "
            "ops/runtime sentinel"
        )


def test_the_guard_above_would_notice_a_missing_slot_root() -> None:
    """Non-vacuity: the detector fires on a call that omits the keyword."""
    tree = ast.parse("runner_mod.run_once(uid=None, runtime_dir='x')\n")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert "slot_root" not in {kw.arg for kw in call.keywords}


# ---------------------------------------------------------------------------
# 1. The constant and where the file lives
# ---------------------------------------------------------------------------


def test_sentinel_name_is_halt() -> None:
    assert runner_mod.HALT_SENTINEL_NAME == SENTINEL


def test_sentinel_lives_in_the_explicit_runtime_dir(runtime: Path) -> None:
    assert runner_mod.halt_sentinel_path(str(runtime)) == runtime / SENTINEL


def test_sentinel_defaults_to_the_health_runtime_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no runtime_dir it follows the same resolution the health file uses."""
    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(tmp_path / "envrt"))
    assert runner_mod.halt_sentinel_path(None) == health_mod.runtime_dir() / SENTINEL
    assert runner_mod.halt_sentinel_path(None) == tmp_path / "envrt" / SENTINEL


# ---------------------------------------------------------------------------
# 2. --once
# ---------------------------------------------------------------------------


def test_once_halted_takes_no_slot_runs_nothing_and_fails(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    hold_spy, pass_spy = spies
    seen: list[int] = []
    _register_probe(seen, slot_root)
    sentinel = _plant(runtime)

    code = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_JOB_FAILED
    assert hold_spy.calls == 0, "a halted pass must not even attempt a slot"
    assert pass_spy.calls == 0, "a halted pass must not run"
    assert seen == []
    assert list(slot_root.iterdir()) == [], "nothing may be created in the bucket"
    assert sentinel.exists(), "the runner must never delete the operator's sentinel"


def test_once_without_sentinel_runs_and_holds_a_slot(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    """Neighbour: the gate is not simply closed."""
    hold_spy, pass_spy = spies
    seen: list[int] = []
    _register_probe(seen, slot_root)

    code = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert hold_spy.calls == 1
    assert pass_spy.calls == 1
    assert seen == [1], "exactly one lock was held while the pass ran"
    assert _locks(slot_root) == [], "and it was released afterwards"


def test_dry_run_ignores_the_sentinel(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    hold_spy, pass_spy = spies
    seen: list[int] = []
    _register_probe(seen, slot_root)
    sentinel = _plant(runtime)

    code = runner_mod.run_once(
        uid=None,
        dry_run=True,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert pass_spy.calls == 1, "a dry run computes and logs regardless of HALT"
    assert hold_spy.calls == 0, "a dry run never takes a slot"
    assert seen == [0]
    assert sentinel.exists()


def test_unreadable_sentinel_state_fails_closed(
    monkeypatch: pytest.MonkeyPatch, clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    """If the sentinel cannot be checked, the lane stays disarmed.

    The fault is injected at `os.stat` itself, for the sentinel path only, and
    the REAL path object is used. A fake path object would hide the defect this
    arm exists for: `Path.exists()` swallows OSError on 3.14 (and some Windows
    errors on 3.11) and answers False, which would RUN the pass.
    """
    hold_spy, pass_spy = spies
    _register_probe([], slot_root)
    sentinel = runtime / SENTINEL
    real_stat = os.stat

    def _stat(path, *args, **kwargs):
        try:
            hit = Path(os.fspath(path)) == sentinel
        except TypeError:
            hit = False
        if hit:
            raise PermissionError(13, "Access is denied", str(sentinel))
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", _stat)
    code = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        slot_root=slot_root,
        slot_timeout=1,
    )
    assert code == runner_mod.EXIT_JOB_FAILED
    assert hold_spy.calls == 0
    assert pass_spy.calls == 0


def test_absent_runtime_dir_is_not_halted(
    clean_registry, spies, slot_root: Path, tmp_path: Path
) -> None:
    """Neighbour of fail-closed: a MISSING sentinel (or parent) is not a halt."""
    hold_spy, pass_spy = spies
    _register_probe([], slot_root)
    code = runner_mod.run_once(
        uid=None,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(tmp_path / "no-such-runtime"),
        slot_root=slot_root,
        slot_timeout=1,
    )
    assert code == runner_mod.EXIT_OK
    assert pass_spy.calls == 1
    assert hold_spy.calls == 1


# ---------------------------------------------------------------------------
# 3. Daemon
# ---------------------------------------------------------------------------


def test_daemon_halted_at_launch_runs_nothing_and_exits_ok(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    hold_spy, pass_spy = spies
    _register_probe([], slot_root)
    sentinel = _plant(runtime)

    code = runner_mod.run_daemon(
        uid=None,
        interval=1,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        max_passes=5,
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert hold_spy.calls == 0
    assert pass_spy.calls == 0
    assert list(slot_root.iterdir()) == []
    assert sentinel.exists()


def test_daemon_stops_at_the_next_pass_when_halt_appears_mid_run(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    """The sentinel is re-checked every iteration, not only at launch."""
    hold_spy, pass_spy = spies
    seen: list[int] = []
    sentinel = runtime / SENTINEL
    _register_probe(seen, slot_root, plant=sentinel)

    code = runner_mod.run_daemon(
        uid=None,
        interval=1,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        max_passes=5,
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert pass_spy.calls == 1, "pass 1 ran and planted HALT; pass 2 must not run"
    assert hold_spy.calls == 1
    assert seen == [1]
    assert _locks(slot_root) == []
    assert sentinel.exists()


def test_daemon_without_sentinel_runs_every_pass(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    """Neighbour: with no sentinel the daemon runs to max_passes."""
    hold_spy, pass_spy = spies
    seen: list[int] = []
    _register_probe(seen, slot_root)

    code = runner_mod.run_daemon(
        uid=None,
        interval=1,
        dry_run=False,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        max_passes=3,
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert pass_spy.calls == 3
    assert hold_spy.calls == 3
    assert seen == [1, 1, 1]


def test_daemon_dry_run_ignores_the_sentinel(
    clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    hold_spy, pass_spy = spies
    _register_probe([], slot_root)
    _plant(runtime)

    code = runner_mod.run_daemon(
        uid=None,
        interval=1,
        dry_run=True,
        job_names=[PROBE_JOB],
        runtime_dir=str(runtime),
        max_passes=2,
        slot_root=slot_root,
        slot_timeout=1,
    )

    assert code == runner_mod.EXIT_OK
    assert pass_spy.calls == 2
    assert hold_spy.calls == 0


def test_halt_log_line_is_friendly(
    caplog: pytest.LogCaptureFixture, clean_registry, spies, slot_root: Path, runtime: Path
) -> None:
    _register_probe([], slot_root)
    _plant(runtime)
    with caplog.at_level("INFO", logger="headless.runner"), contextlib.suppress(SystemExit):
        runner_mod.run_once(
            uid=None,
            dry_run=False,
            job_names=[PROBE_JOB],
            runtime_dir=str(runtime),
            slot_root=slot_root,
            slot_timeout=1,
        )
    assert any("halted by operator sentinel" in r.getMessage() for r in caplog.records)
    assert not any("Traceback" in r.getMessage() for r in caplog.records)
