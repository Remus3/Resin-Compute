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
import os
import subprocess
from pathlib import Path

import pytest

from tests.test_headless_env import kit_route

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
    assert "--max-turns" not in rsp.SPAWN_FLOOR, rsp.SPAWN_FLOOR
    assert not hasattr(rsp, "MAX_TURNS_PER_RUN")
    assert not hasattr(rsp, "SPAWNS_PER_TICK")


def test_the_spawn_argv_pins_the_permission_floor(rsp):
    """Measured live: user-scope settings run bypassPermissions, and the child
    saw write-capable tools and MCP servers. The argv must pin the floor. The
    fleet kit's argv carries no --permission-mode (kit gap 2), so the floor is
    the `extra=` tuple; `tests/test_headless_env.py` grades the argv the
    kit actually built from it."""
    argv = list(rsp.SPAWN_FLOOR)

    def value_of(flag: str) -> str:
        assert argv.count(flag) == 1, (flag, argv)
        return argv[argv.index(flag) + 1]

    assert value_of("--permission-mode") == "dontAsk"
    assert "--strict-mcp-config" in argv
    # NO BASH (adversary C2): `git log --output=<file>` then pytest importing
    # it was code execution under dontAsk.
    assert value_of("--tools") == "Read,Grep,Glob"
    assert value_of("--allowed-tools") == "Read,Grep,Glob"
    assert not any("bypassPermissions" in a for a in argv), argv
    assert not any("dangerously" in a.lower() for a in argv), argv


# ---------------------------------------------------------------------------
# The run budget is the KIT'S (session 63, adjudicated ruling 0f, DECISION C).
# The responder-local run ledger is retired: kit v10's `RunBudget` holds an
# OS byte-range lock that a dead holder frees at once and never unlinks, and
# `kit.spawn` counts every start under it, so a second responder counter
# only drifted (it counted before `kit.spawn`, so a failed spawn cost a
# responder run and no kit run). The per-sender outbound ledger and the hop
# budget STAY: the kit's OutboundCap is per tree, not per sender.
# ---------------------------------------------------------------------------

#: Every name the ruling removes. A name that comes back is a second counter.
RETIRED_RUN_LEDGER_NAMES = (
    "MAX_RUNS_PER_DAY", "RUNS_WINDOW_SECONDS", "RUN_BUDGET_REASON",
    "RUN_RECORD_REASON", "RUN_LOCK_REASON", "_run_rows", "run_lock_path",
    "_acquire_run_lock", "_release_run_lock", "reserve_run", "RunLockBusy",
    "CAP_RUNS", "_binding_run_budget", "RunBudgetSpent",
)

#: What the ruling KEEPS. The non-vacuity half of the sweep above: a removal
#: that took these with it would pass the first arm and break the lane.
KEPT_NAMES = (
    "DEFAULT_RUNS", "halt_sentinel", "_kit_root", "progress_lock_path",
    "MAX_REPLIES_PER_SENDER", "senders_at_cap", "record_outbound", "MAX_HOPS",
    "HaltedBeforeSpawn", "KitRunBudgetSpent", "KitBudgetUnreadable", "KitBudgetLockBusy",
)


def test_the_responder_run_ledger_is_retired(rsp):
    left = [n for n in RETIRED_RUN_LEDGER_NAMES if hasattr(rsp, n)]
    assert left == [], f"the retired responder run ledger is back: {left}"
    assert "run-budget" not in rsp.TERMINATIONS, "a termination nothing can produce"


def test_the_ruling_keeps_the_loop_breakers_and_the_derived_paths(rsp):
    missing = [n for n in KEPT_NAMES if not hasattr(rsp, n)]
    assert missing == [], f"the shrink removed a kept name: {missing}"
    assert rsp.halt_sentinel().parent == rsp.DEFAULT_RUNS.parent
    assert rsp.progress_lock_path().parent == rsp.DEFAULT_RUNS.parent


def test_the_pre_spawn_refusals_survive_the_reparenting(rsp):
    """HaltedBeforeSpawn and the kit refusals keep ONE handler at the spawn site."""
    for cls, termination in (
        (rsp.HaltedBeforeSpawn, "halted"),
        (rsp.KitRunBudgetSpent, "kit-run-budget"),
        (rsp.KitBudgetUnreadable, "usage-backoff"),
        (rsp.KitBudgetLockBusy, "run-locked"),
    ):
        assert issubclass(cls, rsp.NoSessionStarted) and issubclass(cls, rsp.SpawnFailed), cls
        assert cls.termination == termination and termination in rsp.TERMINATIONS, cls


def _seed_legacy_runs(rsp, stamps) -> None:
    """A responder run record as the retired ledger wrote it."""
    rsp.DEFAULT_RUNS.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_RUNS.write_text(json.dumps({"version": 1, "runs": list(stamps)}))


def _kit_starts(rsp) -> list[float]:
    from ops.fleet_kit import fleet_headless as kit

    path = rsp._kit_root() / kit.BUDGET_REL
    return json.loads(path.read_text())["starts"] if path.exists() else []


def test_a_full_legacy_run_record_no_longer_refuses_a_spawn(rsp, routed):
    """ITEM-14 MINOR (1), the retry bound: what bounds a MAIN note retried every
    fire is the KIT'S 120, so a full legacy responder record binds nothing and
    is never read, written or deleted."""
    import time

    _seed_legacy_runs(rsp, [time.time() - 60.0] * 120)
    before = rsp.DEFAULT_RUNS.read_bytes()

    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "draft"
    assert routed.calls == 1, "a full legacy record still refused the session"
    assert len(_kit_starts(rsp)) == 1, "the kit did not count the start"
    assert rsp.DEFAULT_RUNS.read_bytes() == before, "the retired record was written"


def test_a_spawn_counts_one_kit_start_and_a_full_kit_budget_starts_none(rsp, routed):
    from ops.fleet_kit import fleet_headless as kit

    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "draft"
    assert routed.calls == 1 and len(_kit_starts(rsp)) == 1

    import time

    path = rsp._kit_root() / kit.BUDGET_REL
    path.write_text(json.dumps({"starts": [time.time() - 60.0] * kit.RUNS_CAP}))
    with pytest.raises(rsp.KitRunBudgetSpent):
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert routed.calls == 1, "a session started with the kit budget spent"
    assert not rsp.DEFAULT_RUNS.exists(), "a spawn wrote the retired responder record"


def test_the_kits_budget_lock_busy_ends_the_spawn_as_run_locked(rsp, routed, monkeypatch):
    from ops.fleet_kit import fleet_headless as kit

    def refuse(*_a, **_k):
        raise kit.Refused("budget lock busy")

    monkeypatch.setattr(kit, "spawn", refuse)
    with pytest.raises(rsp.KitBudgetLockBusy) as caught:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert caught.value.termination == "run-locked"
    assert not isinstance(caught.value, rsp.KitRunBudgetSpent), "a busy lock is not a spent budget"


def test_a_busy_kit_lock_fire_terminates_run_locked(rsp, tmp_path):
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "a.md", "expires": 9_999_999_999})
    )
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-0900-from-RC-q.md")
    rc = tmp_path / "rc"
    (rc / "moon_sync_inbox").mkdir(parents=True)

    def spawn(prompt, bounds):
        raise rsp.KitBudgetLockBusy("budget lock busy")

    result = rsp.run_once(inbox=inbox, roots={"RC": rc}, bounds=rsp.Bounds(armed=True), spawn=spawn)

    assert result["termination"] == "run-locked", result
    assert list((rc / "moon_sync_inbox").iterdir()) == []
    assert not list(rsp.DEFAULT_STAGING.glob("held/*")), "a refused fire held a file"


# ---------------------------------------------------------------------------
# The OS-held lock. No longer a run-ledger lock: it guards the progress lock
# and, since ITEM-14 MINOR (4), the per-sender outbound record.
# ---------------------------------------------------------------------------


def _hold(rsp, lock: Path) -> int:
    """Take the lock on a handle of our own, as another process would."""
    lock.parent.mkdir(parents=True, exist_ok=True)
    handle = rsp._acquire_os_lock(lock)
    assert handle is not None, "the arm could not take the lock it needs to hold"
    return handle


def test_a_holder_that_dies_frees_the_lock_at_once(rsp):
    """A closed handle - what the OS does for a dead process - frees the lock."""
    lock = rsp.outbound_lock_path(rsp.DEFAULT_OUTBOUND)
    handle = _hold(rsp, lock)
    assert rsp._acquire_os_lock(lock) is None, "non-vacuity: a held lock was taken twice"
    os.close(handle)  # no unlock call: the holder simply "dies"

    again = rsp._acquire_os_lock(lock)
    assert again is not None, "a dead holder's lock was not freed"
    rsp._release_os_lock(again)


def test_no_stale_timeout_path_is_left_and_the_lock_file_is_never_unlinked(rsp):
    """An old lock FILE with no OS lock on it blocks nothing; nothing deletes it."""
    assert not hasattr(rsp, "RUN_LOCK_STALE_SECONDS")
    assert not hasattr(rsp, "_take_run_lock")
    lock = rsp.outbound_lock_path(rsp.DEFAULT_OUTBOUND)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("left by a dead process\n")
    os.utime(lock, (1.0, 1.0))

    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "RC", 1_000_000.0, True) is True
    assert lock.exists(), "the lock file was unlinked"


def test_a_held_outbound_lock_reserves_nothing_and_releases_nothing(rsp, monkeypatch):
    """ITEM-14 MINOR (4): both read-modify-writes run under the lock, and a
    lock that cannot be taken leaves the record alone - the safe side."""
    monkeypatch.setattr(rsp, "OUTBOUND_LOCK_WAIT_SECONDS", 0.0)
    now = 1_000_000.0
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "RC", now, True) is True
    before = rsp.DEFAULT_OUTBOUND.read_bytes()
    handle = _hold(rsp, rsp.outbound_lock_path(rsp.DEFAULT_OUTBOUND))
    try:
        assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "RC", now + 1, True) is False
        assert rsp._release_outbound(rsp.DEFAULT_OUTBOUND, "RC", now) is False
    finally:
        rsp._release_os_lock(handle)
    assert rsp.DEFAULT_OUTBOUND.read_bytes() == before, "a write landed without the lock"
    log = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    assert "fail-closed:outbound-lock-busy" in log, log
    # Neighbour: with the lock free again, the release lands.
    assert rsp._release_outbound(rsp.DEFAULT_OUTBOUND, "RC", now) is True


_CONTENDER = r"""
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("rsp_contender", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
record, now, tries = Path(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
out = [m.record_outbound(record, "RC", now + i / 1000.0, True, exempt=True) for i in range(tries)]
print(json.dumps(out))
"""


@pytest.fixture()
def fake_repo(tmp_path) -> Path:
    """A throwaway repo root holding a byte copy of the responder and its imports.

    A child interpreter cannot see the `rsp` fixture's redirects: it loads the
    module afresh, and every `DEFAULT_*` record then resolves from
    `RESINCOMPUTE_RUNTIME_DIR` or, unset, from `<repo root>/ops/runtime`.
    Measured 2026-10-03: launched from the MAIN checkout with the variable unset,
    a contention arm appended 103 `fail-closed:run-lock-busy` lines to the LIVE
    invocation log. Children therefore load THIS copy, so even a child that
    loses its environment lands in `tmp_path` and never in the real tree.
    """
    import shutil

    fake = tmp_path / "fakerepo"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "core", fake / "core", ignore=ignore)
    (fake / "ops").mkdir()
    for name in ("__init__.py", "health.py"):
        shutil.copyfile(ROOT / "ops" / name, fake / "ops" / name)
    shutil.copytree(ROOT / "ops" / "fleet_kit", fake / "ops" / "fleet_kit", ignore=ignore)
    (fake / "tools").mkdir()
    shutil.copyfile(MODULE, fake / "tools" / MODULE.name)
    return fake


def _contend(fake: Path, record: Path, now: float, tries: int, cwd: Path) -> subprocess.Popen:
    """One contender interpreter against `record`, loading the fake repo's copy.

    The child's runtime is pinned EXPLICITLY to `cwd / "child-runtime"`: set,
    never inherited, so an operator's exported value cannot steer it either.
    """
    import sys

    env = dict(os.environ)
    env[_runtime_env_name()] = str(cwd / "child-runtime")
    return subprocess.Popen(
        [sys.executable, "-c", _CONTENDER, str(fake / "tools" / MODULE.name), str(record), str(now), str(tries)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd),
        env=env,
    )


def _runtime_env_name() -> str:
    """The variable's name, read from its one definition and never spelled here."""
    from ops.health import ENV_RUNTIME_DIR

    return ENV_RUNTIME_DIR


def _responder_records(runtime: Path) -> list[str]:
    if not runtime.is_dir():
        return []
    return sorted(p.name for p in runtime.iterdir() if p.name.lstrip(".").startswith("responder"))


def test_real_processes_reserving_outbound_rows_lose_none(rsp, tmp_path, fake_repo):
    """ITEM-14 MINOR (4). Several interpreters reserve against ONE outbound
    record at once. Every reservation that reported True must be a row: an
    unlocked read-modify-write loses the rows a concurrent writer landed."""
    record = rsp.DEFAULT_OUTBOUND
    record.parent.mkdir(parents=True, exist_ok=True)
    now = 1_000_000.0
    procs = [_contend(fake_repo, record, now, 25, tmp_path) for _ in range(4)]
    results: list[bool] = []
    for proc in procs:
        out, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err
        results.extend(json.loads(out.strip().splitlines()[-1]))

    oks = sum(1 for ok in results if ok)
    rows = json.loads(record.read_text())["replies"]
    assert oks > 0, "non-vacuity: no contender reserved anything"
    assert len(rows) == oks, f"{oks} reservations reported landed, {len(rows)} rows survived"
    assert _responder_records(fake_repo / "ops" / "runtime") == [], "a contender wrote the default runtime"


class _Run:
    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stderr="",
            stdout=json.dumps(
                {"type": "result", "subtype": "success", "is_error": False, "result": "draft"}
            ),
        )


@pytest.fixture()
def routed(rsp, monkeypatch, tmp_path):
    kit_route(rsp, monkeypatch, tmp_path)
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    return run


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
        # The BODY discusses a terminal line and must survive. The NAME avoids
        # the substring: the fleet kit's name rule damps `terminals` too, a
        # recorded over-damp pinned in `tests/test_headless_env.py`.
        ("2026-10-03-0900-from-RC-fire-lines-and-replies.md", "the terminal line of a fire\n"),
    ],
)
def test_legitimate_neighbours_survive_the_terminal_rule(rsp, tmp_path, name, body):
    """Non-vacuity in the other direction: a sweep that ate these has failed."""
    inbox = tmp_path / "inbox"
    kept = _note(inbox, name, body)

    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]


# ---------------------------------------------------------------------------
# The live-runtime guard in the root conftest. Two halves, because a leak has
# two routes: an in-process write (an audit-hook FENCE refuses it before it
# lands) and a child process, which no hook of ours can see (a per-test
# size-and-mtime DRIFT check catches it after the fact).
# ---------------------------------------------------------------------------


def _root_conftest():
    import conftest

    return conftest


def _write_flags() -> int:
    import os

    return os.O_WRONLY | os.O_CREAT | os.O_TRUNC


def _live(name: str) -> Path:
    """The LIVE record, never the redirect: the kit v12 test guard
    (tests/conftest.py) sets RESINCOMPUTE_RUNTIME_DIR to tmp_path for every
    test, while the fence resolved the live directory once at import."""
    from ops.health import runtime_dir

    return runtime_dir(Path(_root_conftest().__file__).resolve().parent / "ops" / "runtime") / name


def test_the_fence_refuses_an_in_process_write_to_a_live_record(runtime_fence_ledger):
    """Non-vacuity: a SYNTHETIC audit event, so a broken fence pollutes nothing."""
    import sys

    target = _live("responder_runs.json")
    with pytest.raises(_root_conftest().LiveRuntimeFenceError):
        sys.audit("open", str(target), "w", _write_flags())

    assert runtime_fence_ledger.acknowledge(1) == 1


@pytest.mark.parametrize(
    ("event", "args"),
    [
        ("os.rename", ("{tmp}/x", "{live}/responder_invocations.log", -1, -1)),
        ("os.remove", ("{live}/responder_runs.json.lock", -1)),
        ("open", ("{live}/.responder_runs.json.123.abcd1234.tmp", "w", 0)),
        # The HOST's O_CREAT, never a literal: 0x100 is O_CREAT on Windows but
        # O_NOCTTY on Linux, where it is no write at all (CI run 37131711357).
        ("open", ("{live}/responder/held/n.md", None, os.O_CREAT)),
    ],
)
def test_the_fence_covers_every_write_route(runtime_fence_ledger, tmp_path, event, args):
    import sys

    live = _live("x").parent
    real = tuple(a.format(tmp=tmp_path, live=live) if isinstance(a, str) else a for a in args)
    with pytest.raises(_root_conftest().LiveRuntimeFenceError):
        sys.audit(event, *real)

    assert runtime_fence_ledger.acknowledge(1) == 1


@pytest.mark.parametrize(
    "where",
    ["read-live-record", "write-tmp-namesake", "write-live-health", "write-live-sibling-name"],
)
def test_legitimate_neighbours_pass_the_fence(runtime_fence_ledger, tmp_path, where):
    """The other direction: a fence that refused these would break honest arms."""
    import os
    import sys

    path, flags = {
        "read-live-record": (_live("responder_runs.json"), os.O_RDONLY),
        "write-tmp-namesake": (tmp_path / "responder_runs.json", _write_flags()),
        "write-live-health": (_live("health.json"), _write_flags()),
        "write-live-sibling-name": (_live("not_responder_runs.json"), _write_flags()),
    }[where]

    sys.audit("open", str(path), None, flags)

    assert runtime_fence_ledger.hits() == []


def test_the_fence_covers_every_runtime_default_of_the_responder(monkeypatch):
    """Completeness, derived and not listed: a fresh, UNREDIRECTED load."""
    from ops.health import ENV_RUNTIME_DIR, runtime_dir

    monkeypatch.delenv(ENV_RUNTIME_DIR, raising=False)
    spec = importlib.util.spec_from_file_location("moon_sync_responder_fenced", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    live = runtime_dir()
    defaults = {
        n: getattr(module, n)
        for n in dir(module)
        if n.startswith("DEFAULT_") and isinstance(getattr(module, n), Path)
    }
    under = {n for n, p in defaults.items() if live in p.parents}

    assert {"DEFAULT_RUNS", "DEFAULT_INVOCATIONS"} <= under, sorted(under)
    assert set(defaults) - under, "non-vacuity: every default sits in the runtime dir"
    fenced = _root_conftest()._is_live_responder_record
    unfenced = [n for n, p in defaults.items() if not fenced(p)]
    assert unfenced == [], unfenced
    assert fenced(module.outbound_lock_path(module.DEFAULT_OUTBOUND))
    assert fenced(module.progress_lock_path())
    assert fenced(module.DEFAULT_INBOX / "2026-10-03-0900-from-RC-q.md")


def test_the_only_excusing_source_is_the_tasks_own_label(rsp):
    """Pinned to the module's constant, so a relabelled task cannot go unexcused
    silently - nor an extra label slip into the excuse set."""
    assert _root_conftest()._LIVE_FIRE_SOURCES == (rsp.SOURCE_SCHEDULED_TASK,)


_FIRE_LOG = (
    "2026-10-03T09:20:21\tfailclosed\t-\tfail-closed:run-lock-busy\n"
    "2026-10-03T09:21:01\tscheduledtask\t-\tstart\n"
    "2026-10-03T09:21:28\tscheduledtask\tn.md\tdelivered\n"
    "2026-10-03T09:26:01\tscheduledtask\t-\tstart\n"
)


def _at(stamp: str) -> float:
    import time

    return time.mktime(time.strptime(stamp, "%Y-%m-%dT%H:%M:%S"))


def test_fire_windows_come_only_from_live_start_lines():
    now = _at("2026-10-03T09:26:30")
    windows = _root_conftest()._live_fire_windows(_FIRE_LOG, now)

    assert windows == [
        (_at("2026-10-03T09:21:01"), _at("2026-10-03T09:21:28")),
        (_at("2026-10-03T09:26:01"), now),
    ], windows


@pytest.mark.parametrize(
    ("t0", "t1", "excused"),
    [
        ("2026-10-03T09:20:20", "2026-10-03T09:20:22", False),  # the measured leak
        ("2026-10-03T09:21:02", "2026-10-03T09:21:04", True),  # a live reserve
        ("2026-10-03T09:23:39", "2026-10-03T09:24:00", False),  # between fires
        ("2026-10-03T09:26:10", "2026-10-03T09:26:11", True),  # a fire still open
    ],
)
def test_drift_is_excused_only_inside_a_live_fire(t0, t1, excused):
    before = {"responder_runs.json": (10, 1)}
    after = {"responder_runs.json": (20, 2)}
    now = _at("2026-10-03T09:26:30")

    verdict = _root_conftest()._runtime_drift(before, after, _at(t0), _at(t1), _FIRE_LOG, now)

    assert (verdict is None) is excused, verdict


@pytest.mark.parametrize("source", ["cli", "run_once", "cliprobe", "suite"])
def test_a_leaking_child_cannot_excuse_itself_with_its_own_start_line(source):
    """REFUTED 2026-10-03 by the adversary: a child running a full cycle against
    the live runtime writes its OWN `start` line and closing line, and any
    source but `scheduledtask` used to open an excuse window around itself."""
    log = (
        f"2026-10-03T10:00:00\t{source}\t-\tstart\n"
        f"2026-10-03T10:00:01\t{source}\t-\tempty\n"
    )
    t0, t1, now = _at("2026-10-03T09:59:59"), _at("2026-10-03T10:00:02"), _at("2026-10-03T10:00:03")
    conf = _root_conftest()

    assert conf._live_fire_windows(log, now) == []
    assert conf._runtime_drift({}, {"responder_invocations.log": (90, 1)}, t0, t1, log, now) is not None


def test_an_unclosed_scheduled_start_excuses_at_most_its_cap():
    log = "2026-10-03T10:00:00\tscheduledtask\t-\tstart\n"
    start = _at("2026-10-03T10:00:00")
    conf = _root_conftest()

    assert conf._live_fire_windows(log, start + 3600) == [(start, start + conf._FIRE_OPEN_CAP_SECONDS)]
    late = conf._runtime_drift({}, {"responder_runs.json": (1, 1)}, start + 600, start + 601, log, start + 3600)
    assert late is not None, "a crashed fire excused a change ten minutes later"


def test_no_drift_is_never_a_finding():
    snap = {"responder_runs.json": (10, 1)}
    assert _root_conftest()._runtime_drift(snap, dict(snap), 0.0, 1.0, "", 2.0) is None


def test_a_created_record_is_drift():
    """The lock file was CREATED by the measured leak; absence-to-presence counts."""
    verdict = _root_conftest()._runtime_drift(
        {}, {"responder_runs.json.lock": (0, 5)}, 0.0, 1.0, "", 2.0
    )
    assert verdict is not None and "responder_runs.json.lock" in verdict


# ---------------------------------------------------------------------------
# S3 (c): an 8.3 SHORT spelling of a fenced path is the same path to the kernel.
# Measured on this host 2026-10-03: `C:\RESINC~1\...\ops\runtime\responder_runs.json`
# and the 8.3 spelling of the home directory's `.claude.json` both read as NOT
# live before the fix.
# ---------------------------------------------------------------------------


def _short_spelling(path: Path) -> str:
    """The 8.3 spelling of an EXISTING `path`, or skip with the reason."""
    if os.name != "nt":
        pytest.skip("8.3 short names are a Windows filesystem feature; this host is not Windows")
    import ctypes

    buf = ctypes.create_unicode_buffer(32768)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 32768)
    if not n or n >= 32768:
        pytest.skip(f"GetShortPathNameW gave no short spelling for {path} on this host")
    if "~" not in buf.value:
        pytest.skip(f"8.3 names are disabled for {path} on this volume, so no short spelling exists")
    return buf.value


def test_a_short_spelling_of_the_live_runtime_is_fenced():
    conf = _root_conftest()
    root = Path(conf.__file__).resolve().parent
    short = _short_spelling(root)
    target = os.path.join(short, "ops", "runtime", "responder_runs.json")
    assert conf._is_live_responder_record(os.path.join(root, "ops", "runtime", "responder_runs.json"))
    assert conf._is_live_responder_record(target), target


def test_a_short_spelling_of_the_user_scope_config_is_fenced():
    conf = _root_conftest()
    short = _short_spelling(Path.home())
    target = os.path.join(short, ".claude.json")
    assert conf._is_live_responder_record(target), target


def test_a_short_spelling_of_a_tmp_path_is_still_not_live(tmp_path):
    """The neighbour: expanding short names must not make everything live."""
    conf = _root_conftest()
    (tmp_path / "responder_runs.json").write_text("{}")
    short = _short_spelling(tmp_path)
    assert not conf._is_live_responder_record(os.path.join(short, "responder_runs.json"))
    assert os.path.normcase(conf._expand_short_names(short)) == os.path.normcase(str(tmp_path))


def test_a_short_spelling_of_the_slot_bucket_is_fenced():
    conf = _root_conftest()
    bucket = Path(conf._SLOT_BUCKET_RAW)
    existing = next((p for p in [bucket, *bucket.parents] if p.exists()), None)
    if existing is None or existing == Path(existing.anchor):
        pytest.skip("no existing parent of the slot bucket carries a short spelling here")
    short = _short_spelling(existing)
    spelled = os.path.join(short, os.path.relpath(bucket, existing), "lane.lock")
    assert conf._under_slot_bucket(spelled), spelled


def test_short_name_expansion_is_identity_off_windows(monkeypatch):
    """Linux CI: no kernel32, so the helper hands back its input unchanged."""
    conf = _root_conftest()
    monkeypatch.setattr(conf, "_GET_LONG_PATH", None)
    assert conf._expand_short_names("/tmp/LONGNA~1/x") == "/tmp/LONGNA~1/x"


# ---------------------------------------------------------------------------
# S3 (d): a change inside a scheduled fire is attributed by CONTENT. A
# test-shaped record is a leak even while the live task is running.
# ---------------------------------------------------------------------------

_OPEN_FIRE = "2026-10-03T11:00:00\tscheduledtask\t-\tstart\n"


@pytest.mark.parametrize("source", ["cli", "run_once", "suite", "cliprobe"])
def test_a_test_shaped_log_line_is_a_leak_inside_a_fire(source):
    t0, t1, now = _at("2026-10-03T11:00:05"), _at("2026-10-03T11:00:06"), _at("2026-10-03T11:00:07")
    appended = f"2026-10-03T11:00:05\t{source}\t-\tstart\n"
    verdict = _root_conftest()._runtime_drift(
        {"responder_invocations.log": (10, 1)}, {"responder_invocations.log": (60, 2)},
        t0, t1, _OPEN_FIRE, now, appended,
    )
    assert verdict is not None and source in verdict, verdict


@pytest.mark.parametrize("source", ["scheduledtask", "failclosed"])
def test_a_live_writers_log_line_inside_a_fire_is_still_excused(source):
    """The neighbour: the task's own lines, and its fail-closed lines, are live."""
    t0, t1, now = _at("2026-10-03T11:00:05"), _at("2026-10-03T11:00:06"), _at("2026-10-03T11:00:07")
    appended = f"2026-10-03T11:00:05\t{source}\t-\tbudget\n"
    verdict = _root_conftest()._runtime_drift(
        {"responder_invocations.log": (10, 1)}, {"responder_invocations.log": (60, 2)},
        t0, t1, _OPEN_FIRE, now, appended,
    )
    assert verdict is None, verdict


def test_a_record_carrying_a_test_path_is_a_leak_inside_a_fire(tmp_path):
    t0, t1, now = _at("2026-10-03T11:00:05"), _at("2026-10-03T11:00:06"), _at("2026-10-03T11:00:07")
    conf = _root_conftest()
    leaked = json.dumps({"rows": [{"dest": str(tmp_path / "rc" / "moon_sync_inbox")}]})
    clean = json.dumps({"rows": [{"note": "2026-10-03-1100-from-RC-q.md"}]})
    markers = conf._test_markers(str(tmp_path.parent))
    args = ({"responder_outbound.json": (1, 1)}, {"responder_outbound.json": (2, 2)}, t0, t1, _OPEN_FIRE, now)

    verdict = conf._runtime_drift(*args, "", {"responder_outbound.json": ("{}", leaked)}, markers)
    assert verdict is not None and "responder_outbound.json" in verdict, verdict
    assert conf._runtime_drift(*args, "", {"responder_outbound.json": ("{}", clean)}, markers) is None
    # A marker already present BEFORE the test is history, not this test's leak.
    assert conf._runtime_drift(*args, "", {"responder_outbound.json": (leaked, leaked)}, markers) is None


def _log_lines(n: int, start: int = 0) -> list[str]:
    """`n` invocation-log lines, every tenth a `run_once` one, like pd.py's."""
    return [
        f"2026-10-0{1 + i % 2}T10:00:{i % 60:02d}\t"
        f"{'run_once' if i % 10 == 0 else 'scheduledtask'}\t-\tstart\n"
        for i in range(start, start + n)
    ]


def test_a_pure_trim_of_the_log_adds_no_lines():
    """REFUTED on 46c2b3e (probe pd.py): `_trim_invocations` keeps the last
    2000 lines, so the file SHRINKS, and reading it from offset 0 blamed its old
    `run_once` lines on the running test. Lines are compared, not offsets."""
    conf = _root_conftest()
    before = "".join(_log_lines(6000))
    after = "".join(_log_lines(6000)[-2000:])
    assert conf._new_log_lines(before, after) == ""
    assert conf._test_shaped(conf._new_log_lines(before, after), {}, ()) == []


def test_a_trim_plus_an_append_yields_exactly_the_appended_lines():
    conf = _root_conftest()
    history = _log_lines(6000)
    live = "2026-10-03T14:00:00\tscheduledtask\t-\tstart\n"
    leak = "2026-10-03T14:00:01\tcli\t-\tstart\n"
    before = "".join(history)
    after = "".join(history[-2000:] + [live, leak])
    new = conf._new_log_lines(before, after)
    assert new == live + leak, new
    found = conf._test_shaped(new, {}, ())
    assert len(found) == 1 and "'cli'" in found[0], found


def test_a_pure_append_and_an_identical_repeat_line_are_both_seen():
    """An appended line that repeats one already in the log is still NEW."""
    conf = _root_conftest()
    history = _log_lines(50)
    repeat = history[-1]
    assert conf._new_log_lines("".join(history), "".join(history + [repeat])) == repeat
    assert conf._new_log_lines("", "".join(history)) == "".join(history)
    assert conf._new_log_lines("".join(history), "") == ""


def test_a_rewrite_with_no_overlap_is_all_new():
    conf = _root_conftest()
    assert conf._new_log_lines("".join(_log_lines(5)), "rotated\n") == "rotated\n"


def test_the_drift_check_reads_the_log_past_any_size_cap(tmp_path):
    """Refuted on 6f9dda2: a 1 MB read cap blinded the content check on a log
    already past 1 MB. The whole log is read, so an append past 1 MB is seen."""
    conf = _root_conftest()
    log = tmp_path / "responder_invocations.log"
    big = b"2026-10-03T09:00:00\tscheduledtask\t-\tbudget\n" * 40000  # ~1.7 MB
    log.write_bytes(big)
    assert log.stat().st_size > (1 << 20), "non-vacuity: the log must be past the old cap"
    before = conf._read_log_text(log)
    with log.open("ab") as handle:
        handle.write(b"2026-10-03T11:00:05\tcli\t-\tstart\n")
    new = conf._new_log_lines(before, conf._read_log_text(log))
    assert new == "2026-10-03T11:00:05\tcli\t-\tstart\n"
    assert conf._read_log_text(tmp_path / "absent.log") == ""


def test_the_temp_marker_is_the_pytest_basetemp_not_the_system_temp(request):
    import tempfile

    conf = _root_conftest()
    roots = conf._session_temp_roots(request)
    assert roots == (str(request.config._tmp_path_factory.getbasetemp()),), roots
    markers = conf._test_markers(*roots)
    system = os.path.normcase(tempfile.gettempdir()).lower()
    assert system not in markers and "pytest-of-" not in markers, markers


def test_an_unclosed_fire_excuses_only_its_measured_duration():
    """176 closed fires in the live log on 2026-10-03 ran at most 104 s. The
    start line carries no pid (`log_invocation` writes stamp, source, note,
    outcome), so liveness cannot be read from it and the cap stays."""
    conf = _root_conftest()
    assert 104.0 < conf._FIRE_OPEN_CAP_SECONDS < 300.0, conf._FIRE_OPEN_CAP_SECONDS
