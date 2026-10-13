"""Slice 0q - an attended outbound note must write its outbound-ledger row.

THE DEFECT (session 70, hand-off 0q). The kit's `OutboundCap` counts this
tree's daily notes from `ops/loop/control/outbound_notes.jsonl`. Its only
writers were the responder's two `cap.record` calls
(`tools/moon_sync_responder.py` `_send_batch` and `_record_work_reply`). An
ATTENDED session sent its notes by writing the files into MAIN's inbox and
its own by hand, so the ledger row was a remembered manual step. On
2026-10-12 it was skipped twice (the 0900 ANSWER and the 1258 INFORMATION
to MAIN): the ledger's last row stayed 2026-10-11 and the cap undercounted.

THE FIX. `tools/send_note.py send` is the attended send path: cap check,
deliver (never overwrite), re-hash every copy, THEN the row. `audit` finds
any own-sent note that still has no row, whatever path sent it, and prints
the exact rows to backfill.

Every arm runs under tmp_path; nothing here touches the live inbox or the
live ledger (the root conftest fences `outbound_notes.jsonl`).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "send_note.py"
LEDGER_REL = Path("ops/loop/control/outbound_notes.jsonl")

NOTE_0900 = "2026-10-12-0900-from-RSC-ANSWER-to-MAIN-1312-kit-v17-adopted-6f61e0d-OK-v17-expected.md"
NOTE_1258 = (
    "2026-10-12-1258-from-RSC-INFORMATION-to-MAIN-TEMP-1-scratchpad-numbers-FLEET_SUITE_SLOTS-1-observed.md"
)
BODY = "# From RSC - INFORMATION to MAIN: test\n\nHOP: 2\nTERMINAL no-reply.\n"


@pytest.fixture
def sn():
    spec = importlib.util.spec_from_file_location("send_note_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def world(tmp_path):
    """A fake fleet: this tree (own inbox, kit root) and MAIN's tree."""
    own = tmp_path / "rsc"
    main = tmp_path / "main"
    (own / "moon_sync_inbox").mkdir(parents=True)
    (main / "moon_sync_inbox").mkdir(parents=True)
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    return {
        "own": own,
        "own_inbox": own / "moon_sync_inbox",
        "main_inbox": main / "moon_sync_inbox",
        "roots": {"MAIN": main},
        "drafts": drafts,
        "ledger": own / LEDGER_REL,
    }


def _draft(world, name: str, body: str = BODY) -> Path:
    p = world["drafts"] / name
    p.write_bytes(body.encode("ascii"))
    return p


def _rows(world) -> list[dict]:
    path = world["ledger"]
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines() if line.strip()]


def _send(sn, world, draft: Path, clock=time.time):
    return sn.send(draft, roots=world["roots"], own_inbox=world["own_inbox"], ledger_root=world["own"], clock=clock)


def _seed_ledger(world, rows: list[dict]) -> None:
    world["ledger"].parent.mkdir(parents=True, exist_ok=True)
    world["ledger"].write_bytes("".join(json.dumps(r) + "\n" for r in rows).encode("ascii"))


# ---------------------------------------------------------------- the regression


def test_an_attended_send_writes_the_outbound_row(sn, world):
    """REGRESSION 0q: the 1258 INFORMATION note to MAIN, sent attended, must
    leave exactly one ledger row the kit's OutboundCap counts."""
    result = _send(sn, world, _draft(world, NOTE_1258))
    assert result["ok"], result
    rows = _rows(world)
    assert [r["note"] for r in rows] == [NOTE_1258]
    row = rows[0]
    assert (row["cls"], row["to"], row["parts"]) == ("INFORMATION", "MAIN", 1)
    assert row["day"] == time.strftime("%Y-%m-%d")
    assert result["row"] == row


def test_the_row_moves_the_kit_cap(sn, world, monkeypatch):
    """The point of the row: the kit's own `used()` sees the attended note."""
    kit = sn.inbox_kit
    before = kit.OutboundCap(world["own"]).used()
    assert _send(sn, world, _draft(world, NOTE_0900))["ok"]
    assert kit.OutboundCap(world["own"]).used() == before + 1


def test_send_delivers_byte_equal_copies_to_recipient_and_own_inbox(sn, world):
    draft = _draft(world, NOTE_0900)
    result = _send(sn, world, draft)
    want = hashlib.sha256(draft.read_bytes()).hexdigest()
    assert result["sha256"] == want
    assert (result["reached"], result["of"]) == (2, 2)
    for inbox in (world["main_inbox"], world["own_inbox"]):
        assert hashlib.sha256((inbox / NOTE_0900).read_bytes()).hexdigest() == want


# ---------------------------------------------------------------- the gates fire


def test_a_non_exempt_note_over_the_daily_cap_is_refused_and_not_delivered(sn, world):
    today = time.strftime("%Y-%m-%d")
    _seed_ledger(world, [{"ts": "x", "day": today, "note": f"n{i}.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}
                         for i in range(6)])
    result = _send(sn, world, _draft(world, NOTE_1258))
    assert not result["ok"]
    assert result["reason"] == "over-cap"
    assert not (world["main_inbox"] / NOTE_1258).exists()
    assert len(_rows(world)) == 6


def test_an_exempt_order_over_the_cap_is_still_sent_and_recorded(sn, world):
    today = time.strftime("%Y-%m-%d")
    _seed_ledger(world, [{"ts": "x", "day": today, "note": f"n{i}.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}
                         for i in range(6)])
    name = "2026-10-12-1300-from-RSC-ORDER-to-MAIN-x.md"
    result = _send(sn, world, _draft(world, name))
    assert result["ok"], result
    assert _rows(world)[-1]["note"] == name


def test_an_existing_recipient_copy_is_never_overwritten_and_no_row_is_written(sn, world):
    (world["main_inbox"] / NOTE_1258).write_bytes(b"older mail\n")
    result = _send(sn, world, _draft(world, NOTE_1258))
    assert not result["ok"]
    assert result["reason"] == "name-taken"
    assert (world["main_inbox"] / NOTE_1258).read_bytes() == b"older mail\n"
    # Refused before any write: no lone own copy for the audit to count.
    assert not (world["own_inbox"] / NOTE_1258).exists()
    assert _rows(world) == []
    assert sn.audit(world["own_inbox"], world["own"], roots=world["roots"]) == []


@pytest.mark.parametrize(
    "name, reason",
    [
        ("2026-10-12-1300-from-LW-ANSWER-to-MAIN-x.md", "bad-name"),
        ("2026-10-12-1300-from-RSC-auto-reply-to-x.md", "bad-name"),
        ("2026-10-12-1300-from-RSC-ANSWER-to-ZZ-x.md", "unknown-recipient"),
        ("2026-10-12-1300-from-RSC-ANSWER-to-LL-x.md", "retired-recipient"),
        ("2026-10-12-1300-from-RSC-ANSWER-to-RSC-x.md", "self-recipient"),
    ],
)
def test_a_note_the_tool_cannot_attribute_is_refused(sn, world, name, reason):
    # The roster HOLDS LL and RSC: the refusal is the responder's rule, not a
    # missing roster row.
    world["roots"]["LL"] = world["roots"]["MAIN"]
    world["roots"]["RSC"] = world["own"]
    result = _send(sn, world, _draft(world, name))
    assert (result["ok"], result["reason"]) == (False, reason)
    assert _rows(world) == []
    assert not any(world["main_inbox"].iterdir())


def test_the_retired_codes_are_the_responders_own(sn):
    assert "LL" in sn.responder.RETIRED
    assert sn.SELF_CODE == sn.responder.SELF_CODE == "RSC"


# ---------------------------------------------------------------- hyphenated classes (round 1, b)


@pytest.mark.parametrize(
    "cls",
    ["POLL-ANSWER", "CORRECTION-ACCEPTED", "NO-REPLY", "ANSWER", "INFORMATION", "REPORT", "ORDER"],
)
def test_hyphenated_and_plain_classes_parse_as_the_kit_classifies_them(sn, cls):
    name = f"2026-10-12-1300-from-RSC-{cls}-to-MAIN-x.md"
    assert sn.parse_name(name) == (sn.inbox_kit.note_class(name), "MAIN")
    assert sn.parse_name(name)[0] == cls


def test_a_hyphenated_exempt_class_is_exempt_by_the_kits_rule(sn, world):
    """FIX-ACK is not a kit ACK class, so the kit classes it FIX - exempt."""
    name = "2026-10-12-1300-from-RSC-FIX-ACK-to-MAIN-x.md"
    assert sn.parse_name(name) == ("FIX", "MAIN")
    today = time.strftime("%Y-%m-%d")
    _seed_ledger(world, [{"ts": "x", "day": today, "note": f"n{i}.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}
                         for i in range(6)])
    result = _send(sn, world, _draft(world, name))
    assert result["ok"], result
    assert _rows(world)[-1]["cls"] == "FIX"


def test_a_hyphenated_class_note_is_sent_and_audited(sn, world):
    name = "2026-10-12-1300-from-RSC-POLL-ANSWER-to-MAIN-x.md"
    _plant(world, name, time.time())
    assert [r["cls"] for r in sn.audit(world["own_inbox"], world["own"], roots=world["roots"])] == ["POLL-ANSWER"]


# ---------------------------------------------------------------- draft gate (round 1, d)


def test_the_responders_draft_gate_refuses_a_traceback_and_nothing_is_written(sn, world):
    body = BODY + "\nTraceback (most recent call last):\n  File x\n"
    result = _send(sn, world, _draft(world, NOTE_1258, body))
    assert (result["ok"], result["reason"]) == (False, "invalid-draft")
    assert result["reasons"]
    assert not any(world["main_inbox"].iterdir()) and not any(world["own_inbox"].iterdir())
    assert _rows(world) == []


def test_the_draft_gate_passes_an_ordinary_note_with_hashes(sn):
    """Neighbour guard: a real note carries sha256 hex and commit ids and has
    no responder tag; the gate must pass it."""
    text = BODY + "\nsha256 6daf69451a0de0d920d731d8eb8a22a3894133540e281bf6391cd8327ee0c2c6, commit 6f61e0d.\n"
    assert sn.draft_reasons(text) == []
    assert sn.responder.RESPONDER_TAG not in text


# ---------------------------------------------------------------- partial failure (round 1, a)


def _kill_on_call(monkeypatch, sn, n: int):
    real = sn.atomic_write_text
    calls = {"n": 0}

    def flaky(path, text):
        calls["n"] += 1
        if calls["n"] == n:
            raise KeyboardInterrupt("killed between copies")
        return real(path, text)

    monkeypatch.setattr(sn, "atomic_write_text", flaky)
    return real


def test_a_send_killed_between_the_copies_is_seen_by_the_audit_and_recovered_by_a_retry(sn, world, monkeypatch):
    draft = _draft(world, NOTE_0900)
    real = _kill_on_call(monkeypatch, sn, 2)
    with pytest.raises(KeyboardInterrupt):
        _send(sn, world, draft)
    monkeypatch.setattr(sn, "atomic_write_text", real)
    # The audit sees the interrupted send (the own copy landed first), but
    # proposes no row: the recipient never got it.
    seen = sn.audit(world["own_inbox"], world["own"], roots=world["roots"])
    assert [(r["note"], r.get("reason")) for r in seen] == [(NOTE_0900, "undelivered")]
    assert sn.backfill(world["own"], seen) == 0
    result = _send(sn, world, draft)
    assert result["ok"], result
    assert (result["reached"], result["of"]) == (2, 2)
    assert [r["note"] for r in _rows(world)] == [NOTE_0900]
    assert sn.audit(world["own_inbox"], world["own"], roots=world["roots"]) == []
    want = hashlib.sha256(draft.read_bytes()).hexdigest()
    assert hashlib.sha256((world["main_inbox"] / NOTE_0900).read_bytes()).hexdigest() == want


def test_a_send_killed_after_both_copies_is_recorded_once_by_a_retry(sn, world, monkeypatch):
    draft = _draft(world, NOTE_0900)

    def boom(self, *a, **k):
        raise KeyboardInterrupt("killed before the row")

    with monkeypatch.context() as m:
        m.setattr(sn.inbox_kit.OutboundCap, "record", boom)
        with pytest.raises(KeyboardInterrupt):
            _send(sn, world, draft)
    assert _rows(world) == []
    first = _send(sn, world, draft)
    assert (first["ok"], first["reason"]) == (True, "already-delivered")
    second = _send(sn, world, draft)
    assert (second["ok"], second["reason"]) == (True, "already-recorded")
    assert [r["note"] for r in _rows(world)] == [NOTE_0900]


def test_an_already_delivered_send_is_recorded_even_over_the_cap(sn, world):
    """A retry records a PAST send; the cap must not leave it uncounted."""
    draft = _draft(world, NOTE_1258)
    for inbox in (world["main_inbox"], world["own_inbox"]):
        (inbox / NOTE_1258).write_bytes(draft.read_bytes())
    today = time.strftime("%Y-%m-%d")
    _seed_ledger(world, [{"ts": "x", "day": today, "note": f"n{i}.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}
                         for i in range(6)])
    result = _send(sn, world, draft)
    assert (result["ok"], result["reason"]) == (True, "over-cap-recorded")
    assert _rows(world)[-1]["note"] == NOTE_1258


def test_a_fresh_send_that_loses_the_cap_race_says_over_cap_recorded(sn, world, monkeypatch):
    """P3: the forced row is kept (an undercount is the 0q defect) and is
    never silent: the result names it."""
    today = time.strftime("%Y-%m-%d")
    _seed_ledger(world, [{"ts": "x", "day": today, "note": f"n{i}.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}
                         for i in range(6)])
    # Another sender filled the cap between our allow() and our record().
    # The FIRST allow() (our pre-delivery check) passes; the kit's own
    # allow() inside record() then sees the full ledger and refuses.
    real_allow = sn.inbox_kit.OutboundCap.allow
    calls = {"n": 0}

    def racy_allow(self, cls):
        calls["n"] += 1
        return True if calls["n"] == 1 else real_allow(self, cls)

    monkeypatch.setattr(sn.inbox_kit.OutboundCap, "allow", racy_allow)
    result = _send(sn, world, _draft(world, NOTE_1258))
    assert (result["ok"], result["reason"]) == (True, "over-cap-recorded")
    assert result["row"]["note"] == NOTE_1258
    assert len(_rows(world)) == 7


def test_a_non_ascii_note_is_refused(sn, world):
    draft = world["drafts"] / NOTE_1258
    draft.write_bytes(b"caf\xc3\xa9\n")
    result = _send(sn, world, draft)
    assert (result["ok"], result["reason"]) == (False, "not-ascii")
    assert not (world["main_inbox"] / NOTE_1258).exists()


# ---------------------------------------------------------------- the audit


def _plant(world, name: str, epoch: float, body: str = BODY, recipient: bool = True) -> Path:
    """An own copy, and (by default) the recipient's byte-equal copy in MAIN."""
    p = world["own_inbox"] / name
    p.write_bytes(body.encode("ascii"))
    os.utime(p, (epoch, epoch))
    if recipient:
        (world["main_inbox"] / name).write_bytes(body.encode("ascii"))
    return p


def test_audit_reproduces_the_2026_10_12_gap_and_proposes_both_rows(sn, world):
    """The exact session-70 shape: the ledger's last row is 2026-10-11 and two
    own-sent notes of 2026-10-12 sit in the inbox with no row."""
    _seed_ledger(world, [{"ts": "2026-10-11T05:10:11-05:00", "day": "2026-10-11",
                          "note": "reply-to-x.md", "cls": "ANSWER", "to": "MAIN", "parts": 1}])
    t0900 = time.mktime((2026, 10, 12, 4, 13, 56, 0, 0, -1))
    t1258 = time.mktime((2026, 10, 12, 12, 58, 17, 0, 0, -1))
    _plant(world, NOTE_0900, t0900)
    _plant(world, NOTE_1258, t1258)
    missing = sn.audit(world["own_inbox"], world["own"], roots=world["roots"])
    assert [r["note"] for r in missing] == [NOTE_0900, NOTE_1258]
    assert [(r["cls"], r["to"], r["day"], r["parts"]) for r in missing] == [
        ("ANSWER", "MAIN", "2026-10-12", 1),
        ("INFORMATION", "MAIN", "2026-10-12", 1),
    ]
    assert missing[0]["ts"] == sn.inbox_kit._iso(t0900)


def test_audit_leaves_the_legitimate_neighbours_alone(sn, world):
    """Second guard of the sweep: recorded notes, responder auto-replies (the
    responder records them as `reply-to-...`), sibling notes and non-notes are
    never proposed."""
    recorded = "2026-10-10-1117-from-RSC-ANSWER-to-MAIN-x.md"
    _seed_ledger(world, [{"ts": "t", "day": "2026-10-10", "note": recorded, "cls": "ANSWER", "to": "MAIN",
                          "parts": 1}])
    for name in (recorded,
                 "2026-10-11-0505-from-RSC-auto-reply-to-2026-10-10-1230-from-MAIN-FIX-x.md",
                 "2026-10-11-0538-from-SS-ANSWER-to-MAIN-x.md",
                 "README.txt"):
        _plant(world, name, time.time())
    (world["own_inbox"] / "2026-10-12-0000-from-RSC-ANSWER-to-MAIN-dir.md").mkdir()
    assert sn.audit(world["own_inbox"], world["own"], roots=world["roots"]) == []


def test_audit_day_filter(sn, world):
    _plant(world, NOTE_0900, time.mktime((2026, 10, 12, 4, 13, 56, 0, 0, -1)))
    _plant(world, "2026-10-11-0100-from-RSC-ANSWER-to-MAIN-y.md", time.mktime((2026, 10, 11, 1, 0, 0, 0, 0, -1)))
    assert [r["note"] for r in sn.audit(world["own_inbox"], world["own"], roots=world["roots"], day="2026-10-12")] == [NOTE_0900]


def test_backfill_closes_the_gap_and_a_second_audit_is_clean(sn, world):
    _plant(world, NOTE_0900, time.mktime((2026, 10, 12, 4, 13, 56, 0, 0, -1)))
    _plant(world, NOTE_1258, time.mktime((2026, 10, 12, 12, 58, 17, 0, 0, -1)))
    missing = sn.audit(world["own_inbox"], world["own"], roots=world["roots"])
    assert sn.backfill(world["own"], missing) == 2
    assert [r["note"] for r in _rows(world)] == [NOTE_0900, NOTE_1258]
    assert sn.audit(world["own_inbox"], world["own"], roots=world["roots"]) == []
    # Idempotent: a second backfill of the same rows appends nothing.
    assert sn.backfill(world["own"], missing) == 0
    assert len(_rows(world)) == 2


def _roots_config(world) -> Path:
    cfg = world["own"] / "roots.json"
    cfg.write_bytes(json.dumps({"channel_codes": {k: str(v) for k, v in world["roots"].items()}}).encode("ascii"))
    return cfg


def test_cli_audit_exits_nonzero_while_a_row_is_missing(sn, world, capsys):
    _plant(world, NOTE_1258, time.time())
    argv = ["audit", "--inbox", str(world["own_inbox"]), "--ledger-root", str(world["own"]),
            "--roots", str(_roots_config(world))]
    assert sn.main(argv) == 1
    out = capsys.readouterr().out
    assert json.loads(out.strip().splitlines()[0])["note"] == NOTE_1258
    assert sn.backfill(world["own"], sn.audit(world["own_inbox"], world["own"], roots=world["roots"])) == 1
    assert sn.main(argv) == 0


def test_ledger_bytes_are_ascii_lf(sn, world):
    assert _send(sn, world, _draft(world, NOTE_1258))["ok"]
    raw = world["ledger"].read_bytes()
    raw.decode("ascii")
    assert b"\r" not in raw and raw.endswith(b"\n")


# ---------------------------------------------------------------- P1: audit checks the recipient copy


@pytest.mark.parametrize(
    "setup, reason",
    [("missing", "undelivered"), ("mismatch", "recipient-mismatch"), ("unknown", "unknown-recipient")],
)
def test_audit_proposes_no_row_unless_the_recipient_copy_hashes_equal(sn, world, setup, reason):
    """P1 (adjudicated B): an own copy alone is not a send. Own copy present,
    recipient copy missing / different / recipient unknown -> listed with a
    reason, and backfill appends 0."""
    name = NOTE_1258 if setup != "unknown" else "2026-10-12-1300-from-RSC-ANSWER-to-ZZ-x.md"
    _plant(world, name, time.time(), recipient=False)
    if setup == "mismatch":
        (world["main_inbox"] / name).write_bytes(b"other bytes\n")
    seen = sn.audit(world["own_inbox"], world["own"], roots=world["roots"])
    assert [(r["note"], r.get("reason")) for r in seen] == [(name, reason)]
    assert sn.backfill(world["own"], seen) == 0
    assert _rows(world) == []


def test_cli_audit_apply_appends_nothing_for_an_undelivered_own_copy(sn, world, capsys):
    """P1 regression via the CLI the merger runs: own copy present, recipient
    copy missing, `audit --apply` appends 0."""
    _plant(world, NOTE_1258, time.time(), recipient=False)
    argv = ["audit", "--apply", "--inbox", str(world["own_inbox"]), "--ledger-root", str(world["own"]),
            "--roots", str(_roots_config(world))]
    sn.main(argv)
    assert "appended 0" in capsys.readouterr().out
    assert _rows(world) == []


def test_audit_still_proposes_a_delivered_note(sn, world):
    """Neighbour guard for P1: own and recipient copies equal -> a row."""
    _plant(world, NOTE_1258, time.time())
    seen = sn.audit(world["own_inbox"], world["own"], roots=world["roots"])
    assert [r["note"] for r in seen] == [NOTE_1258] and "reason" not in seen[0]
    assert sn.backfill(world["own"], seen) == 1
