"""FLEET-COMMON item 13 in the responder: the parent-owned checklist.

The rulings are recorded in CLAUDE.md ("Session checklist - FLEET-COMMON item 13
in this tree") and are NOT re-litigated here:

- (i) the kit spawn gets governor=None for EVERY note class;
- (ii) every fire writes the progress file `rsc-responder`; only a fire that
  reaches the kit spawn logs the ASCII checklist block, under `firedetail`;
- (iii) the parent owns the checklist and the brief forbids the child from
  printing one.

PROGRESS OWNERSHIP. A fire takes a non-blocking OS lock beside the responder's
run record before its first progress write and releases it after its terminal
write. Only the holder writes the progress file, so an idle fire that lands
while another fire is inside a 900 s spawn can never clobber that fire's
checklist. A busy lock is logged `kit-progress-busy` and the fire otherwise runs
unchanged: the lock never gates the fire itself.

Every arm redirects every `DEFAULT_` path under tmp_path, and the kit's root
follows them (`_kit_root`), so nothing here can write the live progress file.
No arm reaches the real `claude` or the proxy.
"""
from __future__ import annotations

import importlib.util
import json
import threading
import time
import types
from pathlib import Path

import pytest

from ops.fleet_kit import fleet_headless as kit

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"
BRIEF = ROOT / "tools" / "responder_brief.md"
LIVE_PROGRESS = ROOT / kit.PROGRESS_REL
ROW_IDS = ["R1", "R2", "R3", "R4"]
BOX = chr(0x2610)


def _conftest():
    import conftest

    return conftest


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("responder_checklist_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _progress_path(rsp) -> Path:
    return rsp._kit_root() / kit.PROGRESS_REL / (rsp.PROGRESS_TASK + ".json")


def _agree(rsp) -> None:
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )


def _armed(rsp, tmp_path, monkeypatch, spawn, name="2026-09-07-1900-from-RC-question.md"):
    """One armed fire on one note, with the session injected."""
    _agree(rsp)
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / name).write_bytes(b"please measure your suite\n")
    (tmp_path / "rc" / "moon_sync_inbox").mkdir(parents=True, exist_ok=True)
    return rsp.run_once(
        inbox=inbox, roots={"RC": tmp_path / "rc"}, bounds=rsp.Bounds(armed=True), spawn=spawn
    )


def _draft(rsp) -> str:
    return rsp.RESPONDER_TAG + "\n\nThe suite was measured.\n"


def _log_lines(rsp) -> list[list[str]]:
    try:
        text = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    except FileNotFoundError:
        return []
    return [line.split("\t") for line in text.splitlines()]


def _recording(monkeypatch) -> list[dict]:
    docs: list[dict] = []
    real = kit.write_progress

    def spy(root, task, pct, step, eta_s, status, clock=time.time, checklist=None):
        doc = real(root, task, pct, step, eta_s, status, clock=clock, checklist=checklist)
        docs.append(doc)
        return doc

    monkeypatch.setattr(kit, "write_progress", spy)
    return docs


def test_the_task_name_and_rows_are_the_ruled_ones(rsp):
    assert rsp.PROGRESS_TASK == "rsc-responder"
    assert [r[0] for r in rsp.CHECKLIST_ROWS] == ROW_IDS
    for _id, task in rsp.CHECKLIST_ROWS:
        task.encode("ascii")
        assert task.strip()


def test_every_fire_ends_with_a_done_progress_file_and_an_empty_checklist(rsp, tmp_path):
    live_before = (LIVE_PROGRESS / "rsc-responder.json").exists()
    result = rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    assert result["termination"] == "empty", result
    path = _progress_path(rsp)
    assert tmp_path in path.parents, f"the progress file escaped tmp: {path}"
    doc = json.loads(path.read_text(encoding="ascii"))
    assert set(doc) == {"task", "pct", "step", "eta_s", "status", "updated", "checklist"}, doc
    assert doc["task"] == "rsc-responder"
    assert doc["status"] == "done" and doc["pct"] == 100
    assert doc["checklist"] == []
    assert (LIVE_PROGRESS / "rsc-responder.json").exists() == live_before


def test_the_first_write_is_running_with_R1_to_R4_in_order_and_every_later_write_is_a_suffix(
    rsp, tmp_path, monkeypatch
):
    docs = _recording(monkeypatch)
    result = _armed(rsp, tmp_path, monkeypatch, lambda prompt, bounds: _draft(rsp))
    assert result["termination"] == "delivered", result
    mine = [d for d in docs if d["task"] == "rsc-responder"]
    assert len(mine) >= 3, mine
    assert mine[0]["status"] == "running"
    assert [r["id"] for r in mine[0]["checklist"]] == ROW_IDS
    for before, after in zip(mine, mine[1:]):
        b = [r["id"] for r in before["checklist"]]
        a = [r["id"] for r in after["checklist"]]
        assert a == b[len(b) - len(a):], (b, a)
    # The spawn was reached, so a write with exactly R3 and R4 left exists.
    assert any([r["id"] for r in d["checklist"]] == ["R3", "R4"] for d in mine), mine
    assert mine[-1]["status"] == "done" and mine[-1]["checklist"] == []


def test_a_concurrent_idle_fire_never_clobbers_a_spawning_fires_checklist(
    rsp, tmp_path, monkeypatch
):
    entered, release = threading.Event(), threading.Event()
    box: dict = {}

    def held_spawn(prompt, bounds):
        entered.set()
        assert release.wait(30), "the arm never released fire 1"
        return _draft(rsp)

    def fire_one():
        box["result"] = _armed(rsp, tmp_path, monkeypatch, held_spawn)

    worker = threading.Thread(target=fire_one, name="fire-1")
    worker.start()
    try:
        assert entered.wait(30), "fire 1 never reached its spawn"
        second = rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
        assert second["termination"] == "empty", second
        doc = json.loads(_progress_path(rsp).read_text(encoding="ascii"))
        assert doc["status"] == "running", doc
        ids = [r["id"] for r in doc["checklist"]]
        assert "R3" in ids and "R4" in ids, doc
        outcomes = [p[3] for p in _log_lines(rsp) if len(p) == 4]
        assert "fail-closed:kit-progress-busy" in outcomes, outcomes
    finally:
        release.set()
        worker.join(60)
    assert box["result"]["termination"] == "delivered", box
    doc = json.loads(_progress_path(rsp).read_text(encoding="ascii"))
    assert doc["status"] == "done" and doc["checklist"] == []


def _crash(*_a, **_k):
    raise RuntimeError("a crash inside the cycle")


def test_the_progress_lock_is_released_after_a_crash(rsp, tmp_path, monkeypatch):
    monkeypatch.setattr(rsp, "_run_once", _crash)
    with pytest.raises(RuntimeError):
        rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    fd = rsp._acquire_run_lock(rsp.progress_lock_path())
    assert fd is not None, "the progress lock survived the crash"
    rsp._release_run_lock(fd)


def test_a_crashing_fire_writes_failed_and_still_re_raises(rsp, tmp_path, monkeypatch):
    monkeypatch.setattr(rsp, "_run_once", _crash)
    with pytest.raises(RuntimeError, match="a crash inside the cycle"):
        rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    doc = json.loads(_progress_path(rsp).read_text(encoding="ascii"))
    assert doc["status"] == "failed", doc


@pytest.mark.parametrize("exc", [OSError, ValueError])
def test_a_failing_progress_write_never_ends_the_fire(rsp, tmp_path, monkeypatch, exc):
    def broken(*_a, **_k):
        raise exc("no progress for you")

    monkeypatch.setattr(kit, "write_progress", broken)
    result = rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    assert result["termination"] == "empty", result
    outcomes = [p[3] for p in _log_lines(rsp) if len(p) == 4]
    assert f"fail-closed:kit-progress-{exc.__name__}" in outcomes, outcomes
    assert outcomes[-1] == "empty", outcomes


class _Stop(Exception):
    pass


@pytest.mark.parametrize("cls", ["ORDER", "FIX", "RULING", "ANSWER", "QUESTION", "INFORMATION"])
def test_the_kit_spawn_gets_governor_none_for_every_note_class(rsp, tmp_path, monkeypatch, cls):
    from tests.test_headless_env import kit_route

    kit_route(rsp, monkeypatch, tmp_path)
    seen: dict = {}

    def fake_spawn(*args, **kwargs):
        seen.update(kwargs)
        raise kit.Refused("stop here")

    monkeypatch.setattr(kit, "spawn", fake_spawn)
    name = f"2026-10-05-0310-from-MAIN-{cls}-to-RSC-something.md"
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_headless("a prompt", rsp.Bounds(), note_name=name)
    assert "governor" in seen and seen["governor"] is None, seen
    assert seen.get("kind") == "inbox", seen
    assert seen.get("note") == name, seen


def test_the_responder_never_imports_ops_loop_slots(rsp):
    """By the LOADED module's namespace, not its source text.

    The plan named an AST walk; that reads the responder's source, which makes
    this file a shape grader that `tools/gate_mutation_runner.py` refuses
    unless it is declared there - a file outside this slice. So the property
    is checked on what the import actually bound: no module object from
    `ops.loop` and no callable defined there sits in the namespace.
    """
    bound = []
    for value in vars(rsp).values():
        if isinstance(value, types.ModuleType):
            bound.append(value.__name__)
        elif callable(value) and isinstance(getattr(value, "__module__", None), str):
            bound.append(value.__module__)
    assert not [n for n in bound if n.startswith("ops.loop")], sorted(set(bound))
    # Non-vacuity: the walk does see this module's real collaborators.
    assert "core.atomic_io" in bound and "ops.fleet_kit.fleet_headless" in bound


def test_a_spawning_fire_logs_an_ascii_firedetail_block(rsp, tmp_path, monkeypatch):
    result = _armed(rsp, tmp_path, monkeypatch, lambda prompt, bounds: _draft(rsp))
    assert result["termination"] == "delivered", result
    detail = [p[3] for p in _log_lines(rsp) if len(p) == 4 and p[1] == "firedetail"]
    block = [o.partition(":")[2] for o in detail if o.partition(":")[2].startswith(("Session ", "[ ]"))]
    assert block, detail
    assert block[0].startswith("Session ") and block[0].endswith(" checklist"), block
    assert block[-1] == "[ ] /done", block
    assert all(line.startswith("[ ] ") for line in block[1:]), block
    assert len(block) >= 3, block
    # The caller prefix rides on every line, so the conftest leak guard can read it.
    assert all(o.partition(":")[0] == "run_once" for o in detail), detail
    raw = rsp.DEFAULT_INVOCATIONS.read_bytes()
    raw.decode("ascii")
    assert BOX.encode("utf-8") not in raw


def test_an_idle_fire_logs_no_checklist_lines(rsp, tmp_path):
    rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    lines = _log_lines(rsp)
    assert [p[3] for p in lines] == ["start", "empty"], lines


def test_the_brief_forbids_a_checklist_in_the_draft():
    text = BRIEF.read_text(encoding="ascii")
    bullet = [line for line in text.splitlines() if "checklist" in line.lower()]
    assert bullet, "the brief says nothing about a checklist"
    assert any("never" in line.lower() for line in bullet), bullet


@pytest.mark.parametrize(
    "name",
    ["rsc-responder.json", "rsc-runner.json", "rsc-responder.json.1234.tmp", "rsc-runner.json.99.tmp"],
)
def test_the_conftest_fence_refuses_a_live_progress_write(runtime_fence_ledger, name):
    target = LIVE_PROGRESS / name
    existed = target.exists()
    with pytest.raises(_conftest().LiveRuntimeFenceError):
        open(target, "w").close()  # noqa: SIM115 - the open itself is the probe
    assert runtime_fence_ledger.acknowledge(1) == 1
    assert target.exists() == existed


def test_the_conftest_fence_leaves_a_neighbouring_progress_file_alone(runtime_fence_ledger):
    """Survival guard: the fence names two files, not the whole progress dir."""
    assert not _conftest()._is_live_progress_record(str(LIVE_PROGRESS / "lane-0.json"))
    assert not _conftest()._is_live_progress_record(str(LIVE_PROGRESS / "rsc-v8-slice-C.json"))
    assert _conftest()._is_live_progress_record(str(LIVE_PROGRESS / "rsc-responder.json"))
    assert runtime_fence_ledger.hits() == []
