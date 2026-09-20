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
        and node.func.attr == "run_daemon"
    ]
    assert calls, "this guard found no run_daemon call to check, so it proves nothing"
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
