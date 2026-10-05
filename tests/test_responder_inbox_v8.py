"""FLEET-COMMON item 14 (kit v8, MAIN 0310 ORDER) in the responder.

RULE 1 - ONE HANDLER. This tree has no lane loop that fires unattended: the only
registered unattended tick is the responder's own scheduled task (PT5M), and
`headless/runner.py` never reads the channel inbox. So the responder stays the
ONE inbox handler and triage folds into ITS tick. The arm below pins the half of
that which lives in the tree; the scheduled-task half is a host fact recorded in
the module docstring of `_inbox_triage`.

RULE 2 - TRIAGE FIRST, on every armed fire, before the work lane:
  skip / ack -> one seen-ledger line and a `firedetail` line; no note, no spawn;
  work       -> ORDER / FIX / RULING, the existing provenance + reply path;
  triage     -> ONE sonnet/low/bare spawn (`fleet_inbox.TRIAGE_SPAWN`), kind
                "triage"; NOREPLY / ACK are marked seen, ANSWER bodies go out in
                ONE batched note per destination.
RULE 3 - `OutboundCap.allow` before any note, `.record` after.
RULE 4 - every outbound note carries `HOP: <n>`; never answer an answer.
RULE 5 - every spawn has a non-empty note label and a kind.

LEDGERS. `responder_answered.json` stays AUTHORITATIVE for "a reply went out";
the kit's seen ledger records the triage disposition and is reconciled from the
answered record on every fire, so the two never disagree about an answered note.

HARD CONSTRAINT. Handling stays automatic: a failed or refused triage spawn
leaves the note UNSEEN, so the next fire retries it with nobody prompting.

Every arm injects both sessions; no arm reaches `claude` or the proxy. The
conftest sets RESINCOMPUTE_RESPONDER_TRIAGE=0 for the legacy arms, so every arm
here opts in explicitly with `rsp.INBOX_TRIAGE = True`.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

from ops.fleet_kit import fleet_headless as kit
from ops.fleet_kit import fleet_inbox as fi

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("responder_inbox_v8_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    module.INBOX_TRIAGE = True
    return module


class Sessions:
    """Both injected sessions, counted."""

    def __init__(self, rsp, verdicts: dict[str, str] | None = None, raises=None) -> None:
        self.rsp = rsp
        self.verdicts = verdicts or {}
        self.raises = raises
        self.work: list[str] = []
        self.triage: list[str] = []

    def spawn(self, prompt, bounds):
        self.work.append(prompt)
        return self.rsp.RESPONDER_TAG + "\n\nThe suite was measured.\n"

    def triage_spawn(self, prompt, bounds, note_name):
        self.triage.append(note_name)
        if self.raises is not None:
            raise self.raises
        return self.verdicts.get(note_name, "VERDICT: ACK")


def _agree(rsp) -> None:
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )


def _note(inbox: Path, name: str, body: str = "please measure your suite\n", age: float = 0.0) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    if age:
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
    return path


def _fire(rsp, tmp_path, monkeypatch, sessions, bounds=None):
    _agree(rsp)
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))
    (tmp_path / "rc" / "moon_sync_inbox").mkdir(parents=True, exist_ok=True)
    return rsp.run_once(
        inbox=tmp_path / "inbox",
        roots={"RC": tmp_path / "rc"},
        bounds=bounds or rsp.Bounds(armed=True),
        spawn=sessions.spawn,
        triage_spawn=sessions.triage_spawn,
    )


def _seen(rsp) -> list[dict]:
    path = rsp._kit_root() / fi.SEEN_REL
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines()]


def _outbound(rsp) -> list[dict]:
    path = rsp._kit_root() / fi.OUTBOUND_REL
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines()]


def _sent(tmp_path) -> list[Path]:
    return sorted((tmp_path / "rc" / "moon_sync_inbox").iterdir())


def _detail(rsp) -> list[str]:
    try:
        text = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    except FileNotFoundError:
        return []
    return [p[3] for p in (ln.split("\t") for ln in text.splitlines()) if len(p) == 4 and p[1] == "firedetail"]


# ---------------------------------------------------------------- rule 1


def test_rule1_the_runner_lane_never_reads_the_channel_inbox(rsp):
    """The responder is the ONE handler: no second reader exists in the runner."""
    runner = (ROOT / "headless" / "runner.py").read_text(encoding="utf-8")
    assert "moon_sync_inbox" not in runner
    assert "fleet_inbox" not in runner
    # Non-vacuity: the responder IS a reader of that inbox (by its bound
    # default, not its source text - see the checklist file on shape graders).
    assert rsp.DEFAULT_INBOX.name == "moon_sync_inbox"


def test_the_scheduled_task_still_runs_the_responder_armed():
    """Handling stays automatic: the task definition is unchanged by this slice."""
    xml = (ROOT / "ops" / "ResinCompute-Responder.xml").read_text(encoding="utf-8")
    assert "tools/moon_sync_responder.py --arm" in xml
    assert "<Interval>PT5M</Interval>" in xml


# ---------------------------------------------------------------- engagement


def test_the_switch_reads_the_attribute_first_then_the_environment(rsp, monkeypatch):
    rsp.INBOX_TRIAGE = None
    monkeypatch.delenv(rsp.ENV_TRIAGE, raising=False)
    assert rsp._triage_engaged() is True, "production default must be ON"
    monkeypatch.setenv(rsp.ENV_TRIAGE, "0")
    assert rsp._triage_engaged() is False
    rsp.INBOX_TRIAGE = True
    assert rsp._triage_engaged() is True


def test_the_conftest_turns_triage_off_for_the_legacy_arms():
    triage_off = os.environ.get("RESINCOMPUTE_RESPONDER_TRIAGE") == "0"
    assert triage_off, "RESINCOMPUTE_RESPONDER_TRIAGE is not set to off by the root conftest"


# ---------------------------------------------------------------- rule 2


def test_skip_and_ack_are_a_ledger_line_with_no_note_and_no_spawn(rsp, tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    names = [
        "2026-10-05-0100-from-RSC-ANSWER-to-RC-ours.md",
        "2026-10-05-0101-from-RC-INFORMATION-TERMINAL-no-reply.md",
        "2026-10-05-0102-from-RC-ACK-thanks.md",
        "2026-10-05-0103-from-RC-ANSWER-to-RSC-your-question.md",
    ]
    for n in names:
        _note(inbox, n)
    _note(inbox, "2026-10-05-0104-from-RC-QUESTION-third-hop.md", "# From RC - QUESTION\n\nHOP: 2\n\nwhy\n")
    sessions = Sessions(rsp)
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "empty", result
    assert sessions.work == [] and sessions.triage == []
    assert _sent(tmp_path) == []
    rows = {r["note"]: r for r in _seen(rsp)}
    assert set(rows) == {*names, "2026-10-05-0104-from-RC-QUESTION-third-hop.md"}, rows
    assert rows[names[0]]["action"] == "skip"
    assert rows[names[3]]["action"] == "ack"
    assert rows["2026-10-05-0104-from-RC-QUESTION-third-hop.md"]["action"] == "ack"
    detail = _detail(rsp)
    assert any(d.startswith("run_once:triage-skip") for d in detail), detail
    assert any(d.startswith("run_once:triage-ack") for d in detail), detail
    assert _outbound(rsp) == []


def test_a_work_note_takes_the_existing_reply_path_with_a_hop_line(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-0200-from-RC-FIX-your-gate.md"
    _note(tmp_path / "inbox", name)
    sessions = Sessions(rsp)
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "delivered", result
    assert len(sessions.work) == 1 and sessions.triage == []
    sent = _sent(tmp_path)
    assert len(sent) == 1
    body = sent[0].read_text(encoding="ascii")
    assert "\nHOP: 2\n" in body, body
    assert body.startswith(rsp.RESPONDER_TAG)
    out = _outbound(rsp)
    assert [(r["cls"], r["to"]) for r in out] == [("FIX", "RC")], out
    # The next fire reconciles the seen ledger from the answered record.
    again = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert again["termination"] == "empty", again
    assert len(sessions.work) == 1
    assert [r["note"] for r in _seen(rsp) if r["note"] == name], _seen(rsp)


def test_an_unclassified_note_gets_one_triage_spawn_and_never_the_work_lane(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-0300-from-RC-QUESTION-what-is-your-count.md"
    _note(tmp_path / "inbox", name)
    sessions = Sessions(rsp, {name: "VERDICT: NOREPLY"})
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "empty", result
    assert sessions.triage == [name] and sessions.work == []
    assert _sent(tmp_path) == []
    rows = [r for r in _seen(rsp) if r["note"] == name]
    assert len(rows) == 1 and rows[0]["verdict"] == "NOREPLY", rows
    # Seen means seen: the next fire spends nothing on it.
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [name]


def test_two_answers_to_one_destination_go_out_as_one_batched_note(rsp, tmp_path, monkeypatch):
    a = "2026-10-05-0400-from-RC-QUESTION-first.md"
    b = "2026-10-05-0401-from-RC-QUESTION-second.md"
    _note(tmp_path / "inbox", a)
    _note(tmp_path / "inbox", b)
    sessions = Sessions(rsp, {a: "VERDICT: ANSWER\nThe count is 3.", b: "VERDICT: ANSWER\nNo, never."})
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sorted(sessions.triage) == [a, b] and sessions.work == []
    sent = _sent(tmp_path)
    assert len(sent) == 1, sent
    body = sent[0].read_text(encoding="ascii")
    assert "-from-RSC-ANSWER-to-RC-batched-2-answers" in sent[0].name
    assert "HOP: 2" in body and rsp.RESPONDER_TAG in body
    assert f"## Re {a}" in body and f"## Re {b}" in body
    assert "The count is 3." in body and "No, never." in body
    out = _outbound(rsp)
    assert len(out) == 1 and out[0]["cls"] == "ANSWER" and out[0]["parts"] == 2, out
    answered = json.loads(rsp.DEFAULT_ANSWERED.read_text(encoding="utf-8"))["answered"]
    assert a in answered and b in answered
    verdicts = {r["note"]: r["verdict"] for r in _seen(rsp)}
    assert verdicts[a] == verdicts[b] == "ANSWER"


def test_a_triage_answer_that_fails_the_draft_gate_is_held_not_sent(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-0450-from-RC-QUESTION-leaky.md"
    _note(tmp_path / "inbox", name)
    leak = "VERDICT: ANSWER\nTraceback (most recent call last):\n  boom"
    sessions = Sessions(rsp, {name: leak})
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert _sent(tmp_path) == []
    assert _outbound(rsp) == []
    held = list((rsp.DEFAULT_STAGING / "held").iterdir())
    assert len(held) == 1, held
    rows = [r for r in _seen(rsp) if r["note"] == name]
    assert rows and rows[0]["verdict"] == "ANSWER-refused", rows


def test_a_failed_triage_spawn_leaves_the_note_unseen_for_the_next_fire(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-0500-from-RC-QUESTION-retry-me.md"
    _note(tmp_path / "inbox", name)
    sessions = Sessions(rsp, raises=rsp.SpawnFailed("the session returned no usable result"))
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [name]
    assert [r for r in _seen(rsp) if r["note"] == name] == []
    sessions.raises = None
    sessions.verdicts = {name: "VERDICT: ACK"}
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [name, name], "the next fire did not retry automatically"
    assert [r["verdict"] for r in _seen(rsp) if r["note"] == name] == ["ACK"]


def test_triage_spawns_are_bounded_per_fire(rsp, tmp_path, monkeypatch):
    names = [f"2026-10-05-06{i:02d}-from-RC-QUESTION-n{i}.md" for i in range(rsp.TRIAGE_PER_FIRE + 2)]
    for n in names:
        _note(tmp_path / "inbox", n)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert len(sessions.triage) == rsp.TRIAGE_PER_FIRE
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sorted(sessions.triage) == sorted(names)


def test_the_backlog_is_marked_seen_without_a_spawn(rsp, tmp_path, monkeypatch):
    old = "2026-09-01-0100-from-RC-QUESTION-ancient.md"
    done = "2026-10-05-0700-from-RC-QUESTION-already-answered.md"
    _note(tmp_path / "inbox", old, age=10 * 86400)
    _note(tmp_path / "inbox", done)
    rsp.DEFAULT_ANSWERED.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_ANSWERED.write_text(json.dumps({"version": 1, "answered": [done]}))
    sessions = Sessions(rsp)
    bounds = rsp.Bounds(armed=True, window_opens=time.time() - 86400, window_closes=time.time() + 86400)
    _fire(rsp, tmp_path, monkeypatch, sessions, bounds=bounds)
    assert sessions.triage == [] and sessions.work == []
    verdicts = {r["note"]: r["verdict"] for r in _seen(rsp)}
    assert verdicts == {old: "before-window", done: "answered"}, verdicts


def test_an_auto_reply_from_a_sibling_is_never_triaged(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-0800-from-RC-auto-reply-to-our-note.md"
    _note(tmp_path / "inbox", name, "[RC-RESPONDER] This note was written by an unattended responder.\nhi\n")
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and sessions.work == []
    assert [r["verdict"] for r in _seen(rsp) if r["note"] == name] == ["auto-reply"]


def test_a_sibling_bounce_file_is_never_triaged(rsp, tmp_path, monkeypatch):
    """A bounce is a `.txt` that is NOT a note (`BOUNCE_SUFFIX`); the kit's scan
    lists `.txt` too, so this tree keeps its bounce-war breaker in front of it."""
    name = "2026-10-05-0850-from-RC-bounce-our-reply.txt"
    _note(tmp_path / "inbox", name, "RC RESPONDER BOUNCE\n")
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and sessions.work == []
    assert [r["verdict"] for r in _seen(rsp) if r["note"] == name] == ["not-a-note"]


def test_a_disarmed_or_halted_fire_triages_nothing_and_writes_no_ledger(rsp, tmp_path, monkeypatch):
    _note(tmp_path / "inbox", "2026-10-05-0900-from-RC-QUESTION-q.md")
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions, bounds=rsp.Bounds())
    assert sessions.triage == [] and _seen(rsp) == []
    rsp.halt_sentinel().parent.mkdir(parents=True, exist_ok=True)
    rsp.halt_sentinel().write_bytes(b"")
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "halted"
    assert sessions.triage == [] and _seen(rsp) == []


def test_the_legacy_switch_off_keeps_the_old_single_note_path(rsp, tmp_path, monkeypatch):
    """Survival guard: with triage off, a QUESTION still reaches the work lane."""
    rsp.INBOX_TRIAGE = False
    _note(tmp_path / "inbox", "2026-10-05-1000-from-RC-QUESTION-legacy.md")
    sessions = Sessions(rsp)
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "delivered", result
    assert sessions.triage == [] and len(sessions.work) == 1
    assert _seen(rsp) == []


# ---------------------------------------------------------------- rule 3


def _fill_cap(rsp, n=fi.OUTBOUND_CAP):
    path = rsp._kit_root() / fi.OUTBOUND_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    day = dt.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
    rows = [{"ts": "x", "day": day, "note": f"n{i}.md", "cls": "ANSWER", "to": "RC", "parts": 1} for i in range(n)]
    path.write_bytes("".join(json.dumps(r) + "\n" for r in rows).encode("ascii"))


def test_at_the_daily_cap_triage_waits_for_tomorrow_and_spends_nothing(rsp, tmp_path, monkeypatch):
    name = "2026-10-05-1100-from-RC-QUESTION-capped.md"
    _note(tmp_path / "inbox", name)
    _fill_cap(rsp)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and _sent(tmp_path) == []
    assert [r for r in _seen(rsp) if r["note"] == name] == [], "a capped note must stay unseen"


def test_a_work_note_is_exempt_from_the_daily_cap(rsp, tmp_path, monkeypatch):
    _note(tmp_path / "inbox", "2026-10-05-1200-from-RC-RULING-do-it.md")
    _fill_cap(rsp)
    sessions = Sessions(rsp)
    result = _fire(rsp, tmp_path, monkeypatch, sessions)
    assert result["termination"] == "delivered", result
    assert len(_sent(tmp_path)) == 1


# ---------------------------------------------------------------- rule 4


def test_the_reply_hop_is_the_incoming_hop_plus_one(rsp, tmp_path):
    assert rsp._reply_hop(_note(tmp_path, "2026-10-05-from-RC-FIX-a.md")) == 2
    path = _note(tmp_path, "2026-10-05-from-RC-FIX-b.md", "# From RC - FIX\n\nHOP: 3\n")
    assert rsp._reply_hop(path) == 4


def test_an_exhausted_draft_gets_no_hop_line(rsp):
    bounds = rsp.Bounds()
    assert rsp._hop_stamp(rsp.RESPONDER_TAG + "\n", 2, bounds) == rsp.RESPONDER_TAG + "\n"
    stamped = rsp._hop_stamp(rsp.RESPONDER_TAG + "\n\nbody\n", 2, bounds)
    assert stamped.endswith("\nHOP: 2\n") and fi.hop(stamped) == 2
    assert rsp._hop_stamp(rsp.RESPONDER_TAG + "\n\nbody\n", None, bounds) == rsp.RESPONDER_TAG + "\n\nbody\n"


# ---------------------------------------------------------------- rule 5


@pytest.mark.parametrize("note_name", ["", "2026-10-05-from-RC-QUESTION-x.md"])
def test_every_spawn_carries_a_label_and_a_kind(rsp, tmp_path, monkeypatch, note_name):
    from tests.test_headless_env import kit_route

    kit_route(rsp, monkeypatch, tmp_path)
    seen: dict = {}

    def fake_spawn(*args, **kwargs):
        seen.update(kwargs)
        raise kit.Refused("stop here")

    monkeypatch.setattr(kit, "spawn", fake_spawn)
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_headless("a prompt", rsp.Bounds(), note_name=note_name)
    assert seen["note"], seen
    assert seen["kind"] == "inbox"
    seen.clear()
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_triage("a prompt", rsp.Bounds(), note_name)
    assert seen["note"] and seen["kind"] == "triage", seen
    assert seen["model"] == fi.TRIAGE_SPAWN["model"]
    assert seen["effort"] == fi.TRIAGE_SPAWN["effort"]
    assert seen["bare"] is fi.TRIAGE_SPAWN["bare"]
    assert seen["timeout"] == fi.TRIAGE_SPAWN["timeout"]
    assert seen["governor"] is None
    assert seen["rules_file"] is None


# ---------------------------------------------------------------- live fence


@pytest.mark.parametrize("name", ["inbox_seen.jsonl", "outbound_notes.jsonl", "inbox_seen.jsonl.42.tmp"])
def test_the_conftest_fence_refuses_a_live_v8_ledger_write(runtime_fence_ledger, name):
    import conftest

    target = ROOT / "ops" / "loop" / "control" / name
    existed = target.exists()
    with pytest.raises(conftest.LiveRuntimeFenceError):
        open(target, "a").close()  # noqa: SIM115 - the open itself is the probe
    assert runtime_fence_ledger.acknowledge(1) == 1
    assert target.exists() == existed


def test_the_v8_ledger_fence_leaves_the_status_file_alone():
    """Survival guard: inbox_status.json is out of the fence's scope (ruled)."""
    import conftest

    control = ROOT / "ops" / "loop" / "control"
    assert not conftest._is_live_progress_record(str(control / "inbox_status.json"))
    assert not conftest._is_live_progress_record(str(control / "headless_usage.jsonl"))
    assert conftest._is_live_progress_record(str(control / "inbox_seen.jsonl"))
