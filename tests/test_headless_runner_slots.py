r"""The headless daemon holds a machine-wide lane slot around each pass.

WHAT THIS GUARDS, AND WHY IT IS NOT A DUPLICATE OF test_loop_concurrency.py.

`tests/test_loop_concurrency.py` guards the VENDORED governor - that this tree's
copy of `ops/loop/slots.py` is byte-identical to every other carrier's, and that
the protocol inside it behaves. It says nothing about whether this repository
ever acquires. Until this module existed, it did not: the only callers of
`hold()` here were that file's own tests.

This module guards the ACQUIRER. `headless/runner.py`'s daemon mode is this
tree's one real repeated executor - `run_daemon` runs `run_pass` on an interval
until a signal arrives - and each of those passes now runs inside a held slot.

FOUR PROPERTIES, each with its own arm below:

  1. a live daemon pass ACQUIRES a slot and RELEASES it;
  2. the slot is released even when the pass RAISES, because the release lives
     in the vendored `hold()`'s finally and not in a happy path;
  3. a `SlotTimeout` is a FAILED cycle - the pass does not run, the exit code is
     `EXIT_JOB_FAILED`, and the holders are left undisturbed. Never permission
     to proceed unslotted;
  4. the hold wraps the PASS and nothing else. Signal-handler installation and
     the shutdown health write both happen with zero locks on disk, which is
     the vendored docstring's "HELD ONLY AROUND THE EXECUTOR CALL".

THE LIVE BUCKET IS OFF LIMITS TO EVERY TEST HERE.

`slots.DEFAULT_ROOT` is a MACHINE-WIDE directory under `C:\ProgramData` that
sibling repositories hold against for real, right now. A test that acquired
there would consume a lane from a live loop in another tree and could, on a
timeout arm, plant locks into it. Every arm below therefore drives `run_daemon`
with an explicit `slot_root` under `tmp_path`, and
`test_no_arm_here_can_reach_the_live_bucket` enforces that by PARSING THIS
MODULE rather than by asking the arms nicely - a future edit that drops the
keyword from one call is a RED here, not a silent escape into ProgramData.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core import config as core_config
from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

PROBE_JOB = "slot_probe"


@pytest.fixture()
def clean_registry():
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def slot_root(tmp_path: Path) -> Path:
    """A private bucket. Never `slots.DEFAULT_ROOT` - see the module docstring."""
    root = tmp_path / "slots"
    root.mkdir()
    assert root != slots_mod.DEFAULT_ROOT
    return root


def _locks(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("*.lock"))


def _write_lock(root: Path, index: int, pid: int) -> Path:
    """Plant a lock held by a LIVE pid with a FRESH timestamp.

    Both arms of `is_stale` are defeated on purpose, so the reaper cannot
    rescue a caller and the timeout path is the only way out.
    """
    path = root / f"{index}.lock"
    path.write_text(
        json.dumps({"pid": pid, "repo": "planted", "run_id": "planted",
                    "cycle": 0, "ts": time.time()}),
        encoding="utf-8",
    )
    return path


def _register_probe(seen: list[int], root: Path) -> None:
    """Register a job that records how many locks were on disk while it ran."""

    def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        seen.append(len(_locks(root)))
        return jobs_mod.passed(PROBE_JOB, "recorded")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name=PROBE_JOB,
            description="records the on-disk lock count",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=_probe,
        )
    )


def _daemon_kwargs(tmp_path: Path, slot_root: Path) -> dict:
    return {
        "uid": None,
        "interval": 1,
        "dry_run": False,
        "job_names": [PROBE_JOB],
        "runtime_dir": str(tmp_path / "runtime"),
        "max_passes": 1,
        "slot_root": slot_root,
    }


# ---------------------------------------------------------------------------
# 0. The live bucket is unreachable from this module
# ---------------------------------------------------------------------------


def test_no_arm_here_can_reach_the_live_bucket() -> None:
    """Every `run_daemon` call in this file must name its own bucket.

    Parsed, not grepped: a keyword argument is a syntactic fact and `ast` reads
    it exactly, where a substring search over the file would be satisfied by the
    word appearing anywhere at all - including inside this docstring.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("run_daemon", "run_once")
    ]
    assert calls, "this guard found no run_daemon call to check, so it proves nothing"
    assert any(n.func.attr == "run_once" for n in calls), (
        "this guard found no run_once call to check, so its run_once half proves nothing"
    )
    # `kw.arg is None` is `**mapping`. Those calls all unpack `_daemon_kwargs`,
    # which is checked directly below rather than being taken on trust.
    for node in calls:
        names = {kw.arg for kw in node.keywords}
        assert "slot_root" in names or None in names, (
            f"run_daemon at line {node.lineno} does not pass slot_root. Without it the "
            f"daemon acquires against {slots_mod.DEFAULT_ROOT}, a MACHINE-WIDE bucket "
            "sibling repositories hold against live. No test may touch it."
        )
    built = _daemon_kwargs(Path("no-such-tmp"), Path("no-such-bucket"))
    assert built["slot_root"] == Path("no-such-bucket"), (
        "the shared kwargs builder stopped setting slot_root, so every `**` call site "
        "above would fall back to the live bucket"
    )
    built_once = _once_kwargs(Path("no-such-tmp"), Path("no-such-bucket"))
    assert built_once["slot_root"] == Path("no-such-bucket"), (
        "the --once kwargs builder stopped setting slot_root, so every `**` run_once "
        "call site above would fall back to the live bucket"
    )


def test_the_guard_above_would_notice_a_missing_slot_root() -> None:
    """Non-vacuity: the detector fires on a call that omits the keyword."""
    tree = ast.parse("runner_mod.run_daemon(uid=None, interval=1)\n")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert "slot_root" not in {kw.arg for kw in call.keywords}


# ---------------------------------------------------------------------------
# 1. Acquire and release
# ---------------------------------------------------------------------------


def test_a_live_daemon_pass_acquires_and_releases_a_slot(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    seen: list[int] = []
    _register_probe(seen, slot_root)

    assert _locks(slot_root) == [], "the bucket was not empty before the daemon ran"
    rc = runner_mod.run_daemon(**_daemon_kwargs(tmp_path, slot_root))

    assert rc == runner_mod.EXIT_OK
    assert seen == [1], (
        f"the pass ran with {seen} lock(s) on disk. Exactly one slot must be HELD "
        "while the pass runs."
    )
    assert _locks(slot_root) == [], "the slot was not released when the pass finished"


def test_the_hold_is_configured_from_the_governing_constants(
    clean_registry, tmp_path: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`max_slots` is the cross-repo ceiling, and the repo label has one spelling.

    `slots.hold`'s own signature default is 2 and `Config` carries a separate
    `max_concurrent_lanes`. Neither of those governs: the value that bounds the
    shared bucket is `core.config.MAX_CONCURRENT_LANES`, and this arm fails if
    the runner ever passes anything else.
    """
    recorded: list[dict] = []
    real_hold = slots_mod.hold

    def _recording_hold(max_slots=2, **kwargs):
        recorded.append({"max_slots": max_slots, **kwargs})
        return real_hold(max_slots, **kwargs)

    monkeypatch.setattr(runner_mod.slots_mod, "hold", _recording_hold)
    _register_probe([], slot_root)

    runner_mod.run_daemon(**_daemon_kwargs(tmp_path, slot_root))

    assert len(recorded) == 1, f"expected exactly one hold for one pass, got {recorded}"
    call = recorded[0]
    assert call["max_slots"] == core_config.MAX_CONCURRENT_LANES
    assert core_config.MAX_CONCURRENT_LANES != 2, (
        "the governing constant now equals `slots.hold`'s signature default, so the "
        "assertion above can no longer tell the two apart. Re-arm this guard."
    )
    assert call["repo"] == runner_mod.SLOT_REPO_LABEL
    assert Path(call["root"]) == slot_root
    assert call["cycle"] == 1, "the cycle number must identify WHICH pass holds the slot"
    assert call["run_id"], "a blank run_id makes a stuck bucket unattributable"


def test_the_repo_label_has_exactly_one_spelling() -> None:
    """A free-form human label, so its only value is being greppable."""
    assert runner_mod.SLOT_REPO_LABEL == "resin-compute"


# ---------------------------------------------------------------------------
# 2. Release on the raising path
# ---------------------------------------------------------------------------


def test_the_slot_is_released_when_the_pass_raises(
    clean_registry, tmp_path: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The release belongs to `hold()`'s finally, not to a happy path.

    `run_pass` absorbs a failing JOB, so a job that raises cannot reach this
    path at all - the pass itself has to blow up. `run_pass` is replaced
    wholesale to produce that.
    """

    def _explode(**kwargs):
        raise RuntimeError("raw upstream detail 0xdeadbeef")

    monkeypatch.setattr(runner_mod, "run_pass", _explode)
    _register_probe([], slot_root)

    with pytest.raises(RuntimeError):
        runner_mod.run_daemon(**_daemon_kwargs(tmp_path, slot_root))

    assert _locks(slot_root) == [], (
        "a pass that raised left its lock behind. A leaked lock carries a LIVE pid "
        "and a fresh ts, so neither arm of is_stale fires and the lane is lost for "
        "the rest of the run."
    )


# ---------------------------------------------------------------------------
# 3. A timeout is a failed cycle
# ---------------------------------------------------------------------------


def test_a_slot_timeout_is_a_failed_pass_and_never_a_success(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    seen: list[int] = []
    _register_probe(seen, slot_root)
    planted = [
        _write_lock(slot_root, i, os.getpid())
        for i in range(core_config.MAX_CONCURRENT_LANES)
    ]

    kwargs = _daemon_kwargs(tmp_path, slot_root)
    kwargs["slot_timeout"] = 0.0
    rc = runner_mod.run_daemon(**kwargs)

    assert seen == [], "the pass RAN without a slot. A timeout is never permission."
    assert rc == runner_mod.EXIT_JOB_FAILED, (
        f"a starved cycle exited {rc}. A SlotTimeout must never be swallowed into a "
        "success path."
    )
    assert all(p.exists() for p in planted), "a timed-out caller disturbed the holders"


def test_a_starved_cycle_says_so_without_leaking_the_raw_error(
    clean_registry, tmp_path: Path, slot_root: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _register_probe([], slot_root)
    for i in range(core_config.MAX_CONCURRENT_LANES):
        _write_lock(slot_root, i, os.getpid())

    kwargs = _daemon_kwargs(tmp_path, slot_root)
    kwargs["slot_timeout"] = 0.0
    with caplog.at_level("ERROR", logger="headless.runner"):
        runner_mod.run_daemon(**kwargs)

    assert any("slot" in r.message.lower() for r in caplog.records), (
        "a starved cycle logged nothing about the slot, so an operator reading the "
        "log sees a failed pass with no cause"
    )


def test_the_health_file_records_the_starved_cycle_as_not_alive(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    """The shutdown write still happens - a starved cycle is not a crash."""
    _register_probe([], slot_root)
    for i in range(core_config.MAX_CONCURRENT_LANES):
        _write_lock(slot_root, i, os.getpid())

    kwargs = _daemon_kwargs(tmp_path, slot_root)
    kwargs["slot_timeout"] = 0.0
    runner_mod.run_daemon(**kwargs)

    payload = health_mod.read_health(base=tmp_path / "runtime")
    assert payload["alive"] is False


# ---------------------------------------------------------------------------
# 4. The hold wraps the pass and nothing else
# ---------------------------------------------------------------------------


def test_the_hold_does_not_wrap_the_setup_kept_outside_it(
    clean_registry, tmp_path: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """"HELD ONLY AROUND THE EXECUTOR CALL" - the vendored docstring.

    Signal-handler installation and the shutdown health write are both outside
    the critical section, so each must observe an EMPTY bucket. The pass itself
    must observe exactly one lock. Recording all three into one ordered list
    makes the boundary a sequence rather than three unrelated booleans.
    """
    timeline: list[tuple[str, int]] = []
    real_install = runner_mod.install_signal_handlers
    real_shutdown = runner_mod._write_shutdown_health

    def _install(flag):
        timeline.append(("install_signal_handlers", len(_locks(slot_root))))
        return real_install(flag)

    def _shutdown(runtime_dir):
        timeline.append(("shutdown_health", len(_locks(slot_root))))
        return real_shutdown(runtime_dir)

    monkeypatch.setattr(runner_mod, "install_signal_handlers", _install)
    monkeypatch.setattr(runner_mod, "_write_shutdown_health", _shutdown)

    def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        timeline.append(("pass", len(_locks(slot_root))))
        return jobs_mod.passed(PROBE_JOB, "recorded")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name=PROBE_JOB, description="x",
            cadence=jobs_mod.CADENCE_ON_DEMAND, func=_probe,
        )
    )

    runner_mod.run_daemon(**_daemon_kwargs(tmp_path, slot_root))

    assert timeline == [
        ("install_signal_handlers", 0),
        ("pass", 1),
        ("shutdown_health", 0),
    ], f"the hold boundary is wrong: {timeline}"


# ---------------------------------------------------------------------------
# 5. A dry run still writes nothing - not even a lock file
# ---------------------------------------------------------------------------


def test_a_dry_run_acquires_no_slot(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    """`headless/runner.py`'s docstring: "Not the health file, not a log file,
    not a lock file." A slot IS a lock file, so a dry run must not take one.

    This is not a loophole in the governor. A dry run executes no job that
    reaches the rate-limited resource the bucket exists to bound, and the CI
    smoke test `--once --dry-run` must stay write-free on any machine,
    including one with no `C:\\ProgramData\\lw-loop` at all.
    """
    seen: list[int] = []
    _register_probe(seen, slot_root)

    kwargs = _daemon_kwargs(tmp_path, slot_root)
    kwargs["dry_run"] = True
    rc = runner_mod.run_daemon(**kwargs)

    assert rc == runner_mod.EXIT_OK
    assert seen == [0], f"a dry run held a lock: {seen}"
    assert _locks(slot_root) == []


# ---------------------------------------------------------------------------
# 6. A live --once pass is governed exactly as a daemon pass is
# ---------------------------------------------------------------------------
#
# `--once` is a pass too, and it reaches the same rate-limited resource a daemon
# pass does. Before `run_once` existed, `main` called `run_pass` directly on the
# `--once` path, so a scheduled one-shot ran UNSLOTTED beside a governed daemon.
# Every arm below names its own `slot_root`, enforced by the AST guard in
# section 0, which reads `run_once` calls as well as `run_daemon` calls.


def _once_kwargs(tmp_path: Path, slot_root: Path) -> dict:
    return {
        "uid": None,
        "dry_run": False,
        "job_names": [PROBE_JOB],
        "runtime_dir": str(tmp_path / "runtime"),
        "slot_root": slot_root,
    }


def test_a_live_once_pass_acquires_and_releases_a_slot(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    seen: list[int] = []
    _register_probe(seen, slot_root)

    assert _locks(slot_root) == [], "the bucket was not empty before the pass ran"
    rc = runner_mod.run_once(**_once_kwargs(tmp_path, slot_root))

    assert rc == runner_mod.EXIT_OK
    assert seen == [1], (
        f"the --once pass ran with {seen} lock(s) on disk. Exactly one slot must be "
        "HELD while the pass runs, as it is for a daemon pass."
    )
    assert _locks(slot_root) == [], "the slot was not released when the pass finished"


def test_a_slot_timeout_under_once_is_a_failed_pass_and_never_a_success(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    seen: list[int] = []
    _register_probe(seen, slot_root)
    planted = [
        _write_lock(slot_root, i, os.getpid())
        for i in range(core_config.MAX_CONCURRENT_LANES)
    ]

    kwargs = _once_kwargs(tmp_path, slot_root)
    kwargs["slot_timeout"] = 0.0
    rc = runner_mod.run_once(**kwargs)

    assert seen == [], "the --once pass RAN without a slot. A timeout is never permission."
    assert rc == runner_mod.EXIT_JOB_FAILED, (
        f"a starved --once pass exited {rc}. A SlotTimeout must never be swallowed "
        "into a success path."
    )
    assert rc != runner_mod.EXIT_OK
    assert all(p.exists() for p in planted), "a timed-out caller disturbed the holders"


def test_the_once_slot_is_released_when_the_pass_raises(
    clean_registry, tmp_path: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    held: list[int] = []

    def _explode(**kwargs):
        held.append(len(_locks(slot_root)))
        raise RuntimeError("raw upstream detail 0xdeadbeef")

    monkeypatch.setattr(runner_mod, "run_pass", _explode)
    _register_probe([], slot_root)

    with pytest.raises(RuntimeError):
        runner_mod.run_once(**_once_kwargs(tmp_path, slot_root))

    assert held == [1], f"the raising pass was not running inside a held slot: {held}"
    assert _locks(slot_root) == [], "a --once pass that raised left its lock behind"


def test_a_dry_once_pass_acquires_no_slot(
    clean_registry, tmp_path: Path, slot_root: Path
) -> None:
    seen: list[int] = []
    _register_probe(seen, slot_root)

    kwargs = _once_kwargs(tmp_path, slot_root)
    kwargs["dry_run"] = True
    rc = runner_mod.run_once(**kwargs)

    assert rc == runner_mod.EXIT_OK
    assert seen == [0], f"a dry --once pass held a lock: {seen}"
    assert _locks(slot_root) == []


def test_the_once_hold_is_configured_from_the_governing_constants(
    clean_registry, tmp_path: Path, slot_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded: list[dict] = []
    real_hold = slots_mod.hold

    def _recording_hold(max_slots=2, **kwargs):
        recorded.append({"max_slots": max_slots, **kwargs})
        return real_hold(max_slots, **kwargs)

    monkeypatch.setattr(runner_mod.slots_mod, "hold", _recording_hold)
    _register_probe([], slot_root)

    runner_mod.run_once(**_once_kwargs(tmp_path, slot_root))

    assert len(recorded) == 1, f"expected exactly one hold for one pass, got {recorded}"
    call = recorded[0]
    assert call["max_slots"] == core_config.MAX_CONCURRENT_LANES
    assert call["repo"] == runner_mod.SLOT_REPO_LABEL
    assert Path(call["root"]) == slot_root
    assert call["cycle"] == 1
    assert call["run_id"], "a blank run_id makes a stuck bucket unattributable"
    assert call["timeout"] == float(runner_mod.ONCE_SLOT_TIMEOUT_SECONDS)


# ---------------------------------------------------------------------------
# 7. The BEHAVIOURAL fence: an in-process arm that reaches the bucket dies fast
# ---------------------------------------------------------------------------
#
# The AST guards above read SHAPES, and a shape matcher cannot support "no arm
# reaches the live bucket": changing an in-process `main(["--once", "--dry-run"])`
# to `main(["--once"])` defeats every one of them. The root conftest therefore
# installs a `sys.addaudithook` fence. EXACTLY WHAT IT FENCES: an audit event in
# `conftest._FENCED_EVENTS`, raised in THIS interpreter, whose path argument
# normalises (normpath, normcase, cwd-joined when relative) to the real
# `slots.DEFAULT_ROOT` or a path under it. WHAT IT DOES NOT FENCE: alias
# spellings of the bucket (`\\?\C:\...`, `\\.\C:\...`, the 8.3 short name
# `PROGRA~3`, a trailing dot or space, `\\localhost\C$\...`, junctions, symlinks,
# `subst` drives); child processes; native IO that emits no path event, such as
# `sqlite3` and `ctypes` `CreateFileW`; events outside the table; reads with no
# event such as `os.stat`; and `dir_fd`-relative calls. The conftest block
# carries the full list. These arms prove the fence fires on the canonical
# spelling and that it lets neutral paths through - nothing more.
#
# `sys.audit(...)` raises a SYNTHETIC event: every installed hook sees it and no
# IO happens at all. That is how an arm checks the fence without ever touching
# the bucket, and why the live arm below refuses to run if the check fails.

FENCE_ERROR = "SlotBucketFenceError"


def _fence_trips(path: Path) -> bool:
    """True when a synthetic mkdir event on `path` is refused. Performs no IO."""
    try:
        sys.audit("os.mkdir", str(path), 0o777, -1)
    except BaseException as exc:  # the fence error is deliberately not an Exception
        if type(exc).__name__ == FENCE_ERROR:
            return True
        raise
    return False


def test_the_fence_trips_on_a_synthetic_event_inside_the_real_bucket(
    slot_fence_ledger,
) -> None:
    bucket = slots_mod.DEFAULT_ROOT
    assert _fence_trips(bucket), f"no audit hook refused a mkdir of {bucket}"
    assert _fence_trips(bucket / "0.lock"), "the fence missed a path INSIDE the bucket"
    assert len(slot_fence_ledger.hits()) == 2, "the fence raised but did not RECORD"
    slot_fence_ledger.acknowledge(2)


def test_the_fence_lets_neutral_paths_through(tmp_path: Path) -> None:
    """The neighbours survive: only the bucket and paths under it are refused."""
    bucket = slots_mod.DEFAULT_ROOT
    assert not _fence_trips(tmp_path)
    assert not _fence_trips(Path(str(bucket) + "_neighbour")), (
        "a sibling directory whose NAME starts with the bucket's was refused - "
        "the fence is matching a string prefix, not a path"
    )
    assert not _fence_trips(bucket.parent), "the bucket's PARENT was refused"
    # Real IO on a neutral path, through every fenced event family.
    probe = tmp_path / "neutral"
    probe.mkdir()
    (probe / "f.txt").write_text("x", encoding="utf-8")
    (probe / "f.txt").replace(probe / "g.txt")
    assert [p.name for p in probe.iterdir()] == ["g.txt"]
    (probe / "g.txt").unlink()
    probe.rmdir()


def test_a_live_in_process_once_without_a_slot_root_fails_fast_through_the_fence(
    clean_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, slot_fence_ledger
) -> None:
    """The adversary's counter-example, driven on purpose.

    `main(["--once"])` in-process names NO slot root, so it heads for the real
    machine-wide bucket. It must die at the first path event there - before any
    lock is created - rather than hold a sibling's lane or wait out the
    300-second one-shot timeout. The timeout is cut to zero as well, so even an
    unfenced run returns quickly instead of hanging.
    """
    if not _fence_trips(slots_mod.DEFAULT_ROOT):
        pytest.fail(
            "the audit-hook fence is not installed, so driving a live pass here would "
            f"acquire in {slots_mod.DEFAULT_ROOT}. Refusing to run it."
        )
    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(tmp_path / "runtime"))
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "1")
    monkeypatch.setattr(runner_mod, "ONCE_SLOT_TIMEOUT_SECONDS", 0.0)
    monkeypatch.setattr(runner_mod, "configure_logging", lambda level, dry_run: None)
    ran: list[int] = []
    _register_probe(ran, tmp_path)

    started = time.monotonic()
    with pytest.raises(BaseException) as info:
        runner_mod.main(["--once", "--job", PROBE_JOB])
    elapsed = time.monotonic() - started

    assert type(info.value).__name__ == FENCE_ERROR, (
        f"the live pass ended with {type(info.value).__name__}, not the fence"
    )
    assert ran == [], "the pass RAN - the fence fired after the work, not before it"
    assert elapsed < 5.0, f"the fence took {elapsed:.1f}s to fire; it must be immediate"
    # Two hits: the precondition's synthetic probe, then the runner's mkdir.
    assert len(slot_fence_ledger.hits()) == 2, slot_fence_ledger.hits()
    slot_fence_ledger.acknowledge(2)


# ---------------------------------------------------------------------------
# 8. Every fence hit is LOUD, whichever thread it lands on
# ---------------------------------------------------------------------------
#
# An exception raised inside a `threading.Thread` does not fail the test that
# started it - pytest only warns. So the fence also RECORDS every hit, an autouse
# fixture in the root conftest fails the test during whose run a hit landed
# unless the test acknowledged it, and `pytest_sessionfinish` fails the run for
# any hit never attributed to a test at all - EXCEPT under pytest-xdist, where a
# worker's session-finish result never reaches the controller's exit status.
# `acknowledge(expected)` may be called only from the main thread, and it COUNTS
# the hits carrying the main thread's ident - it does not identify which hits.
# Main-thread-only matters because a worker's ident is reused once the worker
# exits, so a later worker could count a dead one's hit as its own; the main
# thread's ident cannot be reused while the session runs. These arms drive an INNER pytest
# over a temp copy of the root conftest, because the property under test is that
# a run goes red - which an arm in this suite cannot show without being red.
# Every hit below is a SYNTHETIC `sys.audit` event: no IO reaches the bucket.

REPO_ROOT = Path(__file__).resolve().parents[1]

_INNER_THREAD_HIT = '''
import sys, threading
from ops.loop import slots

def test_thread_hit():
    t = threading.Thread(
        target=lambda: sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)
    )
    t.start()
    t.join()
'''

_INNER_THREAD_NEUTRAL = '''
import sys, threading

def test_thread_neutral(tmp_path):
    t = threading.Thread(
        target=lambda: sys.audit("os.mkdir", str(tmp_path / "x"), 0o777, -1)
    )
    t.start()
    t.join()
'''

_INNER_UNATTRIBUTED_HIT = '''
import sys
from ops.loop import slots

try:
    sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)
except BaseException:
    pass

def test_nothing():
    pass
'''


# A deliberate hit on the main thread PLUS a real hit from another thread. The
# test acknowledges ITS OWN hit only. The `inspect` branch lets this body run
# under both ledger APIs - the old no-argument `acknowledge()` and the counted
# one - so a red against the old API is about the hidden hit and never about a
# signature mismatch.
_INNER_OTHER_THREAD_HIDDEN = '''
import inspect, sys, threading
from ops.loop import slots

def _hit():
    sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)

def test_other_thread_hit_is_not_hidden(slot_fence_ledger):
    t = threading.Thread(target=_hit)
    t.start()
    t.join()
    try:
        _hit()
    except BaseException:
        pass
    ack = slot_fence_ledger.acknowledge
    ack(1) if inspect.signature(ack).parameters else ack()
'''

_INNER_OWN_HIT_ACKNOWLEDGED = '''
import sys
from ops.loop import slots

def test_own_hit(slot_fence_ledger):
    try:
        sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)
    except BaseException:
        pass
    slot_fence_ledger.acknowledge(1)
'''

# A WORKER thread hits the bucket and then acknowledges its own hit. Thread
# idents are reused once a thread exits, so a worker's acknowledge could clear a
# dead thread's hit that happened to carry the same ident. Only the main thread,
# which outlives every other, may acknowledge.
_INNER_WORKER_ACKNOWLEDGES = '''
import sys, threading
from ops.loop import slots

def test_worker_acknowledges(slot_fence_ledger):
    def _work():
        try:
            sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)
        except BaseException:
            pass
        slot_fence_ledger.acknowledge(1)

    t = threading.Thread(target=_work)
    t.start()
    t.join()
'''

_INNER_WRONG_COUNT = '''
import sys
from ops.loop import slots

def test_wrong_count(slot_fence_ledger):
    try:
        sys.audit("os.mkdir", str(slots.DEFAULT_ROOT), 0o777, -1)
    except BaseException:
        pass
    slot_fence_ledger.acknowledge(2)
'''


def _run_inner_pytest(tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    inner = tmp_path / "inner"
    inner.mkdir()
    shutil.copyfile(REPO_ROOT / "conftest.py", inner / "conftest.py")
    (inner / "test_inner.py").write_text(body, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
         "--rootdir", str(inner), str(inner / "test_inner.py")],
        cwd=str(inner),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_fence_hit_inside_a_thread_fails_the_test(tmp_path: Path) -> None:
    proc = _run_inner_pytest(tmp_path, _INNER_THREAD_HIT)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        "a fence hit inside a thread left the run GREEN - pytest only warned. "
        f"output:\n{out[-2000:]}"
    )
    assert "slot bucket" in out.lower(), out[-2000:]


def test_a_neutral_event_inside_a_thread_leaves_the_run_green(tmp_path: Path) -> None:
    """The control: the inner harness itself is green when nothing is fenced."""
    proc = _run_inner_pytest(tmp_path, _INNER_THREAD_NEUTRAL)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def test_acknowledging_cannot_hide_another_threads_hit(tmp_path: Path) -> None:
    proc = _run_inner_pytest(tmp_path, _INNER_OTHER_THREAD_HIDDEN)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        "acknowledge() swallowed a hit from ANOTHER thread, so a leftover thread's "
        f"real hit was hidden. output:\n{out[-2000:]}"
    )
    assert "not acknowledged" in out, out[-2000:]


def test_acknowledging_exactly_the_own_thread_hits_is_green(tmp_path: Path) -> None:
    """The control: one own-thread hit, acknowledged as one, passes."""
    proc = _run_inner_pytest(tmp_path, _INNER_OWN_HIT_ACKNOWLEDGED)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def test_acknowledging_from_a_worker_thread_fails(tmp_path: Path) -> None:
    proc = _run_inner_pytest(tmp_path, _INNER_WORKER_ACKNOWLEDGES)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        "a WORKER thread acknowledged a fence hit and the run stayed green. A "
        f"reused thread ident could clear a dead thread's hit. output:\n{out[-2000:]}"
    )
    assert "main thread" in out, out[-2000:]


def test_acknowledging_the_wrong_count_fails(tmp_path: Path) -> None:
    proc = _run_inner_pytest(tmp_path, _INNER_WRONG_COUNT)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"a miscounted acknowledge passed:\n{out[-2000:]}"
    assert "expected 2" in out, out[-2000:]


def test_a_fence_hit_outside_any_test_fails_the_session(tmp_path: Path) -> None:
    proc = _run_inner_pytest(tmp_path, _INNER_UNATTRIBUTED_HIT)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        "a swallowed fence hit during collection left the run GREEN. "
        f"output:\n{out[-2000:]}"
    )
    assert "never attributed" in out, out[-2000:]


def test_main_routes_the_once_path_through_run_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI `--once` path must reach the governed helper, not `run_pass`.

    Both are replaced, so this arm touches no bucket at all: it asserts the
    ROUTE, and the arms above assert what the route does.
    """
    routed: list[dict] = []

    def _fake_once(**kwargs):
        routed.append(kwargs)
        return runner_mod.EXIT_JOB_FAILED

    def _ungoverned(**kwargs):
        raise AssertionError("main called run_pass directly on the --once path")

    monkeypatch.setattr(runner_mod, "run_once", _fake_once)
    monkeypatch.setattr(runner_mod, "run_pass", _ungoverned)

    rc = runner_mod.main(["--once", "--job", "emit_health"])

    assert len(routed) == 1
    assert routed[0]["dry_run"] is False
    assert rc == runner_mod.EXIT_JOB_FAILED, "main did not return run_once's exit code"
