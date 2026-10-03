"""The uniform fleet budget and the loop-damping floors, MAIN 0845.

The operator's order, relayed by MAIN and SHA-256 verified against MAIN's
outbox: every tree carries the same five budget knobs at ten times the only
existing figure. What does NOT change is loop damping that is not a number -
never spawn on your own notes, never spawn on a note marked TERMINAL or
no-reply - and a ten-times hop budget makes those floors matter more.

Every figure is read from the module, never typed here, so the arm moves with
the constant and a regression to an old literal still fails on behaviour.
Every arm runs in tmp directories through the `DEFAULT_*` redirect fixture.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from core import headless_env as he

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("moon_sync_responder_budget", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def test_every_default_path_is_isolated(rsp, tmp_path):
    defaults = [n for n in dir(rsp) if n.startswith("DEFAULT_") and isinstance(getattr(rsp, n), Path)]
    assert "DEFAULT_RUNS" in defaults, "the run record is not a redirected default"
    for name in defaults:
        assert tmp_path in getattr(rsp, name).parents, name


def _note(inbox: Path, name: str, body: str = "please measure your suite\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


# ---------------------------------------------------------------------------
# The knobs.
# ---------------------------------------------------------------------------


def test_the_hop_budget_default_is_the_named_constant(rsp):
    """The scheduled task passes no --max-hops, so this default governs."""
    assert rsp.Bounds().max_hops == rsp.MAX_HOPS


def test_the_retracted_0845_knobs_are_absent(rsp):
    """MAIN 0855 retracted turns-per-run and spawns-per-tick: nothing added."""
    assert "--max-turns" not in rsp.SPAWN_COMMAND, rsp.SPAWN_COMMAND
    assert not hasattr(rsp, "MAX_TURNS_PER_RUN")
    assert not hasattr(rsp, "SPAWNS_PER_TICK")


def test_the_spawn_argv_pins_the_permission_floor(rsp):
    """Measured live: user-scope settings run bypassPermissions, and the child
    saw write-capable tools and MCP servers. The argv must pin the floor."""
    argv = list(rsp.SPAWN_COMMAND)

    def value_of(flag: str) -> str:
        assert argv.count(flag) == 1, (flag, argv)
        return argv[argv.index(flag) + 1]

    assert value_of("--permission-mode") == "dontAsk"
    assert "--strict-mcp-config" in argv
    assert value_of("--tools") == "Read,Grep,Glob,Bash"
    assert value_of("--allowed-tools") == (
        "Read,Grep,Glob,Bash(python -m pytest:*),Bash(git log:*),Bash(git status:*)"
    )
    assert not any("bypassPermissions" in a for a in argv), argv
    assert not any("dangerously" in a.lower() for a in argv), argv


def test_run_reservations_stop_at_the_daily_cap(rsp):
    now = 1_000_000.0
    oks = [rsp.reserve_run(rsp.DEFAULT_RUNS, now + i)[0] for i in range(rsp.MAX_RUNS_PER_DAY)]
    assert all(oks), "a run under the cap was refused"

    ok, why = rsp.reserve_run(rsp.DEFAULT_RUNS, now + rsp.MAX_RUNS_PER_DAY)

    assert ok is False and why == rsp.RUN_BUDGET_REASON
    rows = json.loads(rsp.DEFAULT_RUNS.read_text())["runs"]
    assert len(rows) == rsp.MAX_RUNS_PER_DAY, "a refused run still wrote a row"


def test_runs_older_than_the_window_age_out(rsp):
    now = 1_000_000.0
    for i in range(rsp.MAX_RUNS_PER_DAY):
        assert rsp.reserve_run(rsp.DEFAULT_RUNS, now + i)[0]

    later = now + rsp.RUNS_WINDOW_SECONDS + rsp.MAX_RUNS_PER_DAY + 1

    assert rsp.reserve_run(rsp.DEFAULT_RUNS, later) == (True, "")
    assert json.loads(rsp.DEFAULT_RUNS.read_text())["runs"] == [later]


@pytest.mark.parametrize("poison", [b"{not json", b'{"runs": "x"}', b'{"runs": [1, "two"]}'])
def test_a_corrupt_run_record_fails_closed_and_is_not_overwritten(rsp, poison):
    rsp.DEFAULT_RUNS.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_RUNS.write_bytes(poison)

    ok, why = rsp.reserve_run(rsp.DEFAULT_RUNS, 1_000_000.0)

    assert ok is False and why == rsp.RUN_RECORD_REASON
    assert rsp.DEFAULT_RUNS.read_bytes() == poison


def _seed(rsp, rows) -> None:
    rsp.DEFAULT_RUNS.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_RUNS.write_text(json.dumps({"version": 1, "runs": rows}))


def test_future_stamped_rows_count_and_are_never_discarded(rsp):
    """Lifetime probe fut.py: rows written while the clock ran fast still bind."""
    now = 1_000_000.0
    future = [now + 2 * rsp.RUNS_WINDOW_SECONDS] * rsp.MAX_RUNS_PER_DAY
    _seed(rsp, future)

    ok, why = rsp.reserve_run(rsp.DEFAULT_RUNS, now)

    assert ok is False and why == rsp.RUN_BUDGET_REASON, (ok, why)
    assert json.loads(rsp.DEFAULT_RUNS.read_text())["runs"] == future


def test_a_future_row_survives_a_successful_reservation(rsp):
    now = 1_000_000.0
    _seed(rsp, [now + 3600.0])

    assert rsp.reserve_run(rsp.DEFAULT_RUNS, now) == (True, "")
    assert json.loads(rsp.DEFAULT_RUNS.read_text())["runs"] == [now + 3600.0, now]


@pytest.mark.parametrize(("age_offset", "counts"), [(0.0, False), (-1.0, True)])
def test_the_window_edge_is_exact(rsp, age_offset, counts):
    """A row exactly one window old has expired; one second younger counts."""
    now = 1_000_000.0
    stamp = now - rsp.RUNS_WINDOW_SECONDS - age_offset
    _seed(rsp, [stamp] * rsp.MAX_RUNS_PER_DAY)

    ok, _ = rsp.reserve_run(rsp.DEFAULT_RUNS, now)

    assert ok is (not counts), (stamp, ok)


def _hold(rsp):
    """Take the run lock on a handle of our own, as another process would."""
    handle = rsp._acquire_run_lock(rsp.run_lock_path(rsp.DEFAULT_RUNS))
    assert handle is not None, "the arm could not take the lock it needs to hold"
    return handle


def test_a_held_lock_starts_nothing_and_leaves_the_record_alone(rsp):
    _seed(rsp, [])
    handle = _hold(rsp)
    try:
        ok, why = rsp.reserve_run(rsp.DEFAULT_RUNS, 1_000_000.0)
    finally:
        rsp._release_run_lock(handle)

    assert ok is False and why == rsp.RUN_LOCK_REASON, (ok, why)
    assert json.loads(rsp.DEFAULT_RUNS.read_text())["runs"] == []


def test_a_holder_that_dies_frees_the_lock_at_once(rsp):
    """A closed handle - what the OS does for a dead process - frees the lock."""
    import os

    _seed(rsp, [])
    handle = _hold(rsp)
    os.close(handle)  # no unlock call: the holder simply "dies"

    assert rsp.reserve_run(rsp.DEFAULT_RUNS, 1_000_000.0) == (True, "")


def test_no_stale_timeout_path_is_left_and_the_lock_file_is_never_unlinked(rsp):
    """An old lock FILE with no OS lock on it blocks nothing; nothing deletes it."""
    import os

    assert not hasattr(rsp, "RUN_LOCK_STALE_SECONDS")
    assert not hasattr(rsp, "_take_run_lock")
    _seed(rsp, [])
    lock = rsp.run_lock_path(rsp.DEFAULT_RUNS)
    lock.write_text("left by a dead process\n")
    os.utime(lock, (1.0, 1.0))

    assert rsp.reserve_run(rsp.DEFAULT_RUNS, 1_000_000.0) == (True, "")
    assert lock.exists(), "the lock file was unlinked"


_CONTENDER = r"""
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("rsp_contender", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
runs, now, tries = Path(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
out = [m.reserve_run(runs, now) for _ in range(tries)]
print(json.dumps([[ok, why] for ok, why in out]))
"""


def test_real_processes_contending_never_exceed_the_cap(rsp, tmp_path):
    """Several interpreters reserve against one record at once."""
    import sys

    now = 1_000_000.0
    room = 5
    _seed(rsp, [now - 10.0] * (rsp.MAX_RUNS_PER_DAY - room))
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", _CONTENDER, str(MODULE), str(rsp.DEFAULT_RUNS), str(now), "40"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(tmp_path),
        )
        for _ in range(4)
    ]
    results = []
    for proc in procs:
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err
        results.extend(json.loads(out.strip().splitlines()[-1]))

    oks = sum(1 for ok, _ in results if ok)
    rows = json.loads(rsp.DEFAULT_RUNS.read_text())["runs"]
    whys = {why for ok, why in results if not ok}
    assert 1 <= oks <= room, (oks, whys)
    assert len(rows) == rsp.MAX_RUNS_PER_DAY - room + oks <= rsp.MAX_RUNS_PER_DAY, (len(rows), oks)
    assert whys <= {rsp.RUN_BUDGET_REASON, rsp.RUN_LOCK_REASON}, whys


def test_a_busy_lock_ends_the_spawn_with_its_own_outcome(rsp, routed):
    _seed(rsp, [])
    handle = _hold(rsp)
    try:
        with pytest.raises(rsp.RunLockBusy) as caught:
            rsp._spawn_headless("a prompt", rsp.Bounds())
    finally:
        rsp._release_run_lock(handle)

    assert routed.calls == 0
    assert caught.value.termination == "run-locked" and "run-locked" in rsp.TERMINATIONS


def test_a_busy_lock_fire_terminates_run_locked(rsp, tmp_path):
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "a.md", "expires": 9_999_999_999})
    )
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-0900-from-RC-q.md")
    (tmp_path / "rc" / "moon_sync_inbox").mkdir(parents=True)

    def spawn(prompt, bounds):
        raise rsp.RunLockBusy(rsp.RUN_LOCK_REASON)

    result = rsp.run_once(
        inbox=inbox, roots={"RC": tmp_path / "rc"}, bounds=rsp.Bounds(armed=True), spawn=spawn
    )

    assert result["termination"] == "run-locked", result


class _Run:
    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="draft", stderr="")


@pytest.fixture()
def routed(rsp, monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _n: str(ROOT / "fake-claude-shim.cmd"))
    monkeypatch.setattr(rsp, "_headless_gate", lambda: he.Decision(True, {"PATH": "x"}, ""))
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    return run


def test_a_spawn_reserves_one_run_and_the_full_budget_starts_none(rsp, routed):
    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "draft"
    assert routed.calls == 1
    assert len(json.loads(rsp.DEFAULT_RUNS.read_text())["runs"]) == 1

    import time

    stamp = time.time()
    rsp.DEFAULT_RUNS.write_text(
        json.dumps({"version": 1, "runs": [stamp] * rsp.MAX_RUNS_PER_DAY})
    )
    with pytest.raises(rsp.RunBudgetSpent):
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert routed.calls == 1, "a session started with the run budget spent"


def test_a_spent_run_budget_ends_the_fire_as_run_budget(rsp, tmp_path, monkeypatch):
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "a.md", "expires": 9_999_999_999})
    )
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-0900-from-RC-q.md")
    rc = tmp_path / "rc"
    (rc / "moon_sync_inbox").mkdir(parents=True)

    def spawn(prompt, bounds):
        raise rsp.RunBudgetSpent(rsp.RUN_BUDGET_REASON)

    result = rsp.run_once(inbox=inbox, roots={"RC": rc}, bounds=rsp.Bounds(armed=True), spawn=spawn)

    assert result["termination"] == "run-budget", result
    assert "run-budget" in rsp.TERMINATIONS
    assert list((rc / "moon_sync_inbox").iterdir()) == []
    assert not list(rsp.DEFAULT_STAGING.glob("held/*")), "a run-budget fire held a file"


# ---------------------------------------------------------------------------
# Loop damping. Both floors, and the neighbours that must survive them.
# ---------------------------------------------------------------------------


def test_own_notes_are_never_queued_by_name_or_by_tag(rsp, tmp_path):
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-0900-from-RSC-our-own.md")
    _note(inbox, "2026-10-03-0901-from-RC-carries-our-tag.md", rsp.RESPONDER_TAG + "\nbody\n")
    kept = _note(inbox, "2026-10-03-0902-from-RC-question.md")

    queued = rsp.pending(inbox, rsp.OPTED_IN, set())

    assert queued == [kept], [p.name for p in queued]


@pytest.mark.parametrize(
    "name",
    [
        "2026-10-03-0708-from-LW-RESPONDER-ACK-x-TERMINAL-no-reply.md",
        "2026-10-03-0708-from-LW-ack-x-terminal-no-reply-wanted.md",
        "2026-10-03-0708-from-LW-ack-x-TERMINAL.md",
    ],
)
def test_a_note_named_terminal_or_no_reply_is_never_queued(rsp, tmp_path, name):
    inbox = tmp_path / "inbox"
    _note(inbox, name)
    kept = _note(inbox, "2026-10-03-0709-from-LW-question.md")

    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]


@pytest.mark.parametrize(
    "body",
    [
        "# From LW - ACK: read. TERMINAL, no reply wanted.\n",
        "CLASS     ACK + A1 measurement. TERMINAL - nothing is asked of anyone.\n",
        "body\nreply: none\n",
    ],
)
def test_a_body_declaring_terminal_is_never_queued(rsp, tmp_path, body):
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-0708-from-LW-ack.md", body)

    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # MAIN 0845's own prose DISCUSSES the rule and asks for a reply.
        (
            "2026-10-03-0845-from-MAIN-ORDER-ALL-one-UNIFORM-budget.md",
            "- Loop damping: never spawn on a note marked TERMINAL or no-reply.\n"
            "answered: n/a - a reply IS requested\n",
        ),
        ("2026-10-03-0830-from-MAIN-reply-with-the-sha256.md", "Reply with the sha256.\n"),
        ("2026-10-03-0900-from-RC-terminals-and-replies.md", "the terminal line of a fire\n"),
    ],
)
def test_legitimate_neighbours_survive_the_terminal_rule(rsp, tmp_path, name, body):
    """Non-vacuity in the other direction: a sweep that ate these has failed."""
    inbox = tmp_path / "inbox"
    kept = _note(inbox, name, body)

    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]
