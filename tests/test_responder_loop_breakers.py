"""Loop breakers and limit detection for the widened responder audience.

Refutation of c695ad1, four findings. The ones covered here:

  F2  usage-limit wording the first detector missed, and `overloaded` which is
      a failure but NOT a usage limit.
  F3  one agreement record arms every participant, by ruling - the operator's
      2026-10-02 directive stands in for per-pair agreement - but the record must
      still exist and be unexpired.
  F4a a note that is itself a responder-authored auto-reply, from any tree, is
      never auto-answered.
  F4b an outbound cap: at most `MAX_REPLIES_PER_SENDER` replies per sender per
      rolling 24h, counted from this tree's own durable record.

Every arm drives the real module with the spawn intercepted; nothing launches a
session and nothing writes outside `tmp_path`.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import time
from pathlib import Path

import pytest

from tests.test_headless_env import kit_route

ROOT = Path(__file__).resolve().parents[1]
RESPONDER_PATH = ROOT / "tools" / "moon_sync_responder.py"


def _load(tmp_path: Path, label: str):
    spec = importlib.util.spec_from_file_location(f"responder_loop_{label}", RESPONDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / label / name.lower() / value.name)
    return module


@pytest.fixture()
def rsp(tmp_path):
    return _load(tmp_path, "self")


def _agree(rsp, who="RC", expires=9_999_999_999):
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_bytes(
        json.dumps({"confirmed_by": who, "note": "agreed.md", "expires": expires}).encode("ascii")
    )


def _note(inbox: Path, name: str, body: str = "please measure your suite\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def _trust(rsp, monkeypatch):
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))


def _drafter(rsp):
    def spawn(prompt, bounds):
        return rsp.RESPONDER_TAG + "\nmeasured: nothing further to report.\n"

    return spawn


# ---------------------------------------------------------------------------
# F2 - usage-limit wording
# ---------------------------------------------------------------------------


class _Run:
    def __init__(self, stdout, returncode=1):
        self.calls = 0
        self._out = (stdout, returncode)

    def __call__(self, *args, **kwargs):
        self.calls += 1
        out, rc = self._out
        return subprocess.CompletedProcess(args=args[0], returncode=rc, stdout=out, stderr="")


@pytest.fixture()
def routed(rsp, monkeypatch, tmp_path):
    """Routed through the fleet kit with a loopback stub URL and an injected dial."""
    kit_route(rsp, monkeypatch, tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        "You've HIT YOUR LIMIT for today",
        "Your limit will reset at 3pm",
        "Usage resets at 5pm (UTC)",
        "You are out of extra usage",
        '{"type":"error","error":{"type":"usage_limit"}}',
        '{"type":"error","error":{"type":"rate_limit_error"}}',
    ],
)
def test_each_usage_limit_phrase_is_detected(rsp, routed, monkeypatch, text):
    monkeypatch.setattr(subprocess, "run", _Run(text))
    with pytest.raises(rsp.UsageLimited):
        rsp._spawn_headless("a prompt", rsp.Bounds())


def test_overloaded_is_a_failure_and_not_a_usage_limit(rsp, routed, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _Run('{"error":{"type":"overloaded_error"}} Overloaded'))
    try:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    except rsp.UsageLimited:  # pragma: no cover - reaching this is the failure
        pytest.fail("overloaded was treated as a usage limit, which would park the responder")
    except rsp.SpawnFailed:
        pass


# ---------------------------------------------------------------------------
# F3 - one agreement arms the whole audience, but the floor stays
# ---------------------------------------------------------------------------


def _armed(rsp, inbox, roots):
    return rsp.run_once(inbox=inbox, roots=roots, bounds=rsp.Bounds(armed=True), spawn=_drafter(rsp))


def test_one_agreement_record_arms_a_note_from_any_participant(rsp, tmp_path, monkeypatch):
    _agree(rsp, who="RC")
    _trust(rsp, monkeypatch)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["termination"] == "delivered", result


def test_an_expired_agreement_still_holds_every_sender(rsp, tmp_path, monkeypatch):
    _agree(rsp, expires=time.time() - 1)
    _trust(rsp, monkeypatch)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["termination"] == "unconfirmed", result


def test_a_missing_agreement_still_holds_every_sender(rsp, tmp_path, monkeypatch):
    _trust(rsp, monkeypatch)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-MAIN-question.md")
    result = _armed(rsp, inbox, {"MAIN": tmp_path / "main"})
    assert result["termination"] == "unconfirmed", result


# ---------------------------------------------------------------------------
# F4a - never auto-answer an auto-reply
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, body",
    [
        ("2026-10-02-1000-from-SS-question.md", "[SS-RESPONDER] This note was written by an unattended responder.\nhi\n"),
        ("2026-10-02-1000-from-LW-question.md", "hello\n\n[LW-RESPONDER] tagged lower down\n"),
        ("2026-10-02-1000-from-CS-question.md", "This reply was written by a headless responder.\n"),
        ("2026-10-02-1000-from-MAIN-auto-reply-to-something.md", "an untagged body\n"),
    ],
)
def test_an_auto_reply_from_any_tree_is_never_pending(rsp, tmp_path, name, body):
    inbox = tmp_path / "inbox"
    _note(inbox, name, body)
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


def test_a_human_note_beside_them_is_still_pending(rsp, tmp_path):
    """Survival guard: the auto-reply filter did not delete human traffic."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md", "[SS-RESPONDER] auto\n")
    human = _note(inbox, "2026-10-02-1001-from-SS-question.md", "a responder reading this is fine\n")
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [human]


def test_the_auto_reply_detector_names_what_it_matches(rsp):
    assert rsp.is_auto_reply("x-auto-reply-to-y.md", "")
    assert rsp.is_auto_reply("n.md", rsp.RESPONDER_TAG)
    assert not rsp.is_auto_reply("n.md", "please answer the RESPONDER question\n")


# ---------------------------------------------------------------------------
# F4b - outbound cap per sender per rolling 24h
# ---------------------------------------------------------------------------


def test_at_most_n_replies_per_sender_per_day(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    inbox = tmp_path / "inbox"
    for i in range(rsp.MAX_REPLIES_PER_SENDER + 2):
        _note(inbox, f"2026-10-02-10{i:02d}-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    results = [_armed(rsp, inbox, {"SS": tmp_path / "ss"}) for _ in range(rsp.MAX_REPLIES_PER_SENDER + 2)]
    delivered = [r for r in results if r["delivered"]]
    assert rsp.MAX_REPLIES_PER_SENDER == 3
    assert len(delivered) == 3, [r["termination"] for r in results]
    assert results[-1]["termination"] == "empty", results[-1]
    record = json.loads(rsp.DEFAULT_OUTBOUND.read_text(encoding="ascii"))
    assert len(record["replies"]) == 3


def test_the_cap_is_per_sender(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    now = time.time()
    for _ in range(3):
        rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now, True)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    _note(inbox, "2026-10-02-1001-from-LW-question.md")
    (tmp_path / "lw" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss", "LW": tmp_path / "lw"})
    assert result["note"] == "2026-10-02-1001-from-LW-question.md", result


def test_the_cap_window_rolls(rsp):
    now = 2_000_000.0
    for _ in range(3):
        rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now - 90_000, True)
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now) == set()
    for _ in range(3):
        rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now - 10, True)
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now) == {"SS"}


def test_an_undelivered_reply_is_not_counted(rsp):
    rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", 1.0, False)
    assert not rsp.DEFAULT_OUTBOUND.exists() or json.loads(
        rsp.DEFAULT_OUTBOUND.read_text(encoding="ascii")
    )["replies"] == []


# ---------------------------------------------------------------------------
# A simulated two-responder exchange terminates.
# ---------------------------------------------------------------------------


def test_two_responders_answering_each_other_terminate(tmp_path, monkeypatch):
    a = _load(tmp_path, "a")
    b = _load(tmp_path, "b")
    # B is a sibling tree running the same responder under its own codename.
    monkeypatch.setattr(b, "SELF_CODE", "RC")
    monkeypatch.setattr(b, "RESPONDER_TAG", "[RC-RESPONDER] This note was written by an unattended responder.")
    monkeypatch.setattr(b, "OPTED_IN", ("RSC",))
    root_a, root_b = tmp_path / "root_a", tmp_path / "root_b"
    inbox_a, inbox_b = root_a / "moon_sync_inbox", root_b / "moon_sync_inbox"
    inbox_a.mkdir(parents=True)
    inbox_b.mkdir(parents=True)
    for mod in (a, b):
        _agree(mod)
        _trust(mod, monkeypatch)
    # One human question starts it, from B's side into A's inbox.
    _note(inbox_a, "2026-10-02-0900-from-RC-question.md")

    deliveries = 0
    for _ in range(20):
        ra = a.run_once(inbox=inbox_a, roots={"RC": root_b}, bounds=a.Bounds(armed=True), spawn=_drafter(a))
        rb = b.run_once(inbox=inbox_b, roots={"RSC": root_a}, bounds=b.Bounds(armed=True), spawn=_drafter(b))
        deliveries += int(ra["delivered"]) + int(rb["delivered"])
    assert deliveries == 1, f"the exchange did not terminate after one reply: {deliveries}"


# ---------------------------------------------------------------------------
# Second refutation (6f11963). Every one of these FAILS CLOSED.
# ---------------------------------------------------------------------------

BOM = chr(0xFEFF)
RC_TAG_LINE = "[RC-RESPONDER] This note was written by an unattended responder."


def test_r1_a_bom_before_a_sibling_tag_is_still_an_auto_reply(rsp, tmp_path):
    """Tag ONLY, no declaration sentence, so the tag matcher alone must fire."""
    body = BOM + "[RC-RESPONDER]\nmeasured: nothing further.\n"
    assert rsp.is_auto_reply("n.md", RC_TAG_LINE)
    assert rsp.is_auto_reply("2026-10-02-1000-from-RC-question.md", body)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "2026-10-02-1000-from-RC-question.md").write_bytes(body.encode("utf-8"))
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


def test_r1_read_text_strips_a_leading_bom(rsp, tmp_path):
    path = tmp_path / "n.md"
    path.write_bytes((BOM + "hello\n").encode("utf-8"))
    assert rsp._read_text(path) == "hello\n"


def test_r2_an_empty_or_unreadable_note_is_skipped(rsp, tmp_path):
    assert rsp.is_auto_reply("2026-10-02-1000-from-SS-question.md", "")
    assert rsp.is_auto_reply("2026-10-02-1000-from-SS-question.md", " \n\t\n")
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md", "")
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


def _outbound_corrupt(rsp):
    rsp.DEFAULT_OUTBOUND.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_OUTBOUND.write_bytes(b"{not json")


def test_r3_a_corrupt_outbound_record_caps_every_sender(rsp):
    _outbound_corrupt(rsp)
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, time.time()) >= set(rsp.OPTED_IN)


def test_r3_a_malformed_row_is_a_corrupt_record(rsp):
    rsp.DEFAULT_OUTBOUND.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_OUTBOUND.write_bytes(b'{"version": 1, "replies": [{"to": 5}]}')
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, time.time()) >= set(rsp.OPTED_IN)


def test_r3_a_missing_outbound_record_is_zero_rows(rsp):
    assert not rsp.DEFAULT_OUTBOUND.exists()
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, time.time()) == set()


def test_r3_a_corrupt_record_sends_nothing(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    _outbound_corrupt(rsp)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["delivered"] is False, result
    assert list((tmp_path / "ss" / "moon_sync_inbox").iterdir()) == []


def test_r3_a_failed_reserve_sends_nothing(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    monkeypatch.setattr(rsp, "record_outbound", lambda *a, **k: False)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["delivered"] is False, result
    assert list((tmp_path / "ss" / "moon_sync_inbox").iterdir()) == []
    log = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    assert "fail-closed" in log, log


def test_r3_the_row_is_reserved_before_the_delivery(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    reserved_at_delivery = []
    real_deliver = rsp.deliver

    def deliver(*a, **k):
        reserved_at_delivery.append(rsp.DEFAULT_OUTBOUND.exists())
        return real_deliver(*a, **k)

    monkeypatch.setattr(rsp, "deliver", deliver)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["delivered"] is True, result
    assert reserved_at_delivery and reserved_at_delivery[0] is True, "delivered before reserving"


def test_r4_a_corrupt_backoff_record_is_an_active_backoff(rsp):
    rsp.DEFAULT_BACKOFF.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_BACKOFF.write_bytes(b"garbage")
    assert rsp.backoff_active(rsp.DEFAULT_BACKOFF, time.time()) is True
    rsp.DEFAULT_BACKOFF.write_bytes(b'{"until": "soon"}')
    assert rsp.backoff_active(rsp.DEFAULT_BACKOFF, time.time()) is True


def test_r4_a_missing_or_expired_backoff_record_is_inactive(rsp):
    assert rsp.backoff_active(rsp.DEFAULT_BACKOFF, time.time()) is False
    rsp.DEFAULT_BACKOFF.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_BACKOFF.write_bytes(b'{"until": 1.0}')
    assert rsp.backoff_active(rsp.DEFAULT_BACKOFF, time.time()) is False


def test_r4_a_failed_backoff_write_still_ends_as_usage_backoff(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    monkeypatch.setattr(rsp, "record_backoff", lambda *a, **k: False)

    def limited(prompt, bounds):
        raise rsp.UsageLimited(None)

    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    result = rsp.run_once(
        inbox=inbox, roots={"SS": tmp_path / "ss"}, bounds=rsp.Bounds(armed=True), spawn=limited
    )
    assert result["termination"] == "usage-backoff", result
    log = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    assert "fail-closed" in log, log


@pytest.mark.parametrize("bad", [b"NaN", b"Infinity", b"-Infinity", b"true", b"false"])
def test_n1_a_non_finite_or_bool_until_is_an_active_backoff(rsp, bad):
    rsp.DEFAULT_BACKOFF.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_BACKOFF.write_bytes(b'{"until": ' + bad + b"}")
    assert rsp.backoff_active(rsp.DEFAULT_BACKOFF, time.time()) is True
    log = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    assert "fail-closed" in log, log


@pytest.mark.parametrize("bad", [b"NaN", b"Infinity", b"-Infinity", b"true", b'"1"'])
def test_n2_a_non_finite_or_bool_row_corrupts_the_whole_record(rsp, bad):
    now = time.time()
    good = json.dumps({"to": "SS", "at": now}).encode("ascii")
    doc = b'{"version": 1, "replies": [' + good + b', {"to": "LW", "at": ' + bad + b"}]}"
    rsp.DEFAULT_OUTBOUND.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_OUTBOUND.write_bytes(doc)
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now) >= set(rsp.OPTED_IN)
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now, True) is False
    assert rsp.DEFAULT_OUTBOUND.read_bytes() == doc, "a corrupt record was rewritten"


@pytest.mark.parametrize("encoding, bom", [("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff")])
def test_n3_a_utf16_reply_is_still_an_auto_reply(rsp, tmp_path, encoding, bom):
    body = "[RC-RESPONDER]\nmeasured: nothing further.\n"
    path = tmp_path / "2026-10-02-1000-from-RC-question.md"
    path.write_bytes(bom + body.encode(encoding))
    assert rsp._read_text(path) == body
    assert rsp.is_auto_reply(path.name, rsp._read_text(path))


def test_n3_a_utf8_bom_is_decoded(rsp, tmp_path):
    path = tmp_path / "n.md"
    path.write_bytes(b"\xef\xbb\xbf" + b"[RC-RESPONDER]\n")
    assert rsp._read_text(path) == "[RC-RESPONDER]\n"


def test_n3_undecodable_bytes_read_as_unreadable_and_are_skipped(rsp, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    path = inbox / "2026-10-02-1000-from-SS-question.md"
    path.write_bytes(b"please \xff\xfe\xfd answer\n")
    assert rsp._read_text(path) == ""
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


def test_n4_the_reservation_rechecks_the_cap_before_writing(rsp):
    """A second pass that read the cap BEFORE the first reserved must not exceed it."""
    now = time.time()
    for _ in range(rsp.MAX_REPLIES_PER_SENDER):
        assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now, True)
    before = rsp.DEFAULT_OUTBOUND.read_bytes()
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "SS", now, True) is False
    assert rsp.DEFAULT_OUTBOUND.read_bytes() == before
    # Non-vacuity: another sender still reserves.
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, "LW", now, True) is True


def test_n5_a_failed_reservation_terminates_as_reserve_failed(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    monkeypatch.setattr(rsp, "record_outbound", lambda *a, **k: False)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    result = _armed(rsp, inbox, {"SS": tmp_path / "ss"})
    assert result["termination"] == "reserve-failed", result
    assert "reserve-failed" in rsp.TERMINATIONS
    assert "2026-10-02-1000-from-SS-question.md" in rsp._answered(rsp.DEFAULT_ANSWERED)
    log = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    assert "note-dropped" in log, log


def test_n5_a_good_reservation_still_terminates_as_delivered(rsp, tmp_path, monkeypatch):
    """Survival guard for the termination helper."""
    _agree(rsp)
    _trust(rsp, monkeypatch)
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    (tmp_path / "ss" / "moon_sync_inbox").mkdir(parents=True)
    assert _armed(rsp, inbox, {"SS": tmp_path / "ss"})["termination"] == "delivered"


_RSC_TAGGED = "[RSC-RESPONDER] auto\nmeasured.\n"


@pytest.mark.parametrize(
    "raw",
    [
        _RSC_TAGGED.encode("utf-16-le"),
        _RSC_TAGGED.encode("utf-16-be"),
        b"\xff\xfe\x00\x00" + _RSC_TAGGED.encode("utf-32-le"),
        b"\x00\x00\xfe\xff" + _RSC_TAGGED.encode("utf-32-be"),
        _RSC_TAGGED.encode("utf-32-le"),
    ],
    ids=["utf16le-nobom", "utf16be-nobom", "utf32le-bom", "utf32be-bom", "utf32le-nobom"],
)
def test_f1_wide_encodings_read_as_unreadable_and_are_never_answered(rsp, tmp_path, raw):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    path = inbox / "2026-10-02-1000-from-SS-question.md"
    path.write_bytes(raw)
    text = rsp._read_text(path)
    assert chr(0) not in text
    assert text == "", f"read as {text!r}"
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []


def test_f1_a_plain_note_still_reads(rsp, tmp_path):
    """Survival guard: the NUL rule did not empty ordinary ASCII mail."""
    path = tmp_path / "n.md"
    path.write_bytes(b"please measure\n")
    assert rsp._read_text(path) == "please measure\n"


def test_f2_a_huge_int_row_caps_every_sender_without_crashing(rsp):
    now = time.time()
    rsp.DEFAULT_OUTBOUND.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_OUTBOUND.write_bytes(
        b'{"version": 1, "replies": [{"to": "SS", "at": 1' + b"0" * 400 + b"}]}"
    )
    assert rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now) >= set(rsp.OPTED_IN)


def test_f2_a_huge_int_backoff_is_usage_backoff_not_spawn_failed(rsp, tmp_path, monkeypatch):
    _agree(rsp)
    _trust(rsp, monkeypatch)
    kit_route(rsp, monkeypatch, tmp_path)
    run = _Run("ok", returncode=0)
    monkeypatch.setattr(subprocess, "run", run)
    rsp.DEFAULT_BACKOFF.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_BACKOFF.write_bytes(b'{"until": 1' + b"0" * 400 + b"}")
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-02-1000-from-SS-question.md")
    result = rsp.run_once(inbox=inbox, roots={"SS": tmp_path / "ss"}, bounds=rsp.Bounds(armed=True))
    assert result["termination"] == "usage-backoff", result
    assert run.calls == 0
    assert "fail-closed" in rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")


def test_r5_a_limit_phrase_on_a_clean_long_exit_still_backs_off(rsp, routed, monkeypatch):
    text = rsp.RESPONDER_TAG + "\n" + "x" * 2000 + "\nYou've hit your limit\n"
    monkeypatch.setattr(subprocess, "run", _Run(text, returncode=0))
    with pytest.raises(rsp.UsageLimited):
        rsp._spawn_headless("a prompt", rsp.Bounds())


# ---------------------------------------------------------------------------
# Inbound ORDER / FIX / RULING pass the local per-sender reply hold (FLEET-COMMON
# 14 hard constraint: no note waits on a human). Not 14c, which is outbound.
# ---------------------------------------------------------------------------


def _main_at_cap(rsp, now: float) -> None:
    for i in range(rsp.MAX_REPLIES_PER_SENDER):
        assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, rsp.MAIN_CODE, now - 60 * (i + 1), True)


def test_cap_exempt_a_capped_sender_still_has_its_order_picked(rsp, tmp_path):
    """A MAIN ORDER is never held behind the per-sender reply cap."""
    now = time.time()
    _main_at_cap(rsp, now)
    capped = rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now)
    assert rsp.MAIN_CODE in capped
    inbox = tmp_path / "inbox"
    order = _note(inbox, "2026-10-07-1000-from-MAIN-ORDER-to-RSC-adopt-v9.md")
    answer = _note(inbox, "2026-10-07-1001-from-MAIN-ANSWER-to-RSC-re-question.md")
    picked = [p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set(), capped=capped)]
    assert order.name in picked, picked
    # Non-vacuity: the cap still holds a non-exempt class from the same sender.
    assert answer.name not in picked, picked
    # And without the cap the ANSWER is eligible, so the exclusion is the cap's.
    assert answer.name in [p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set())]


@pytest.mark.parametrize("cls", ["ORDER", "FIX", "RULING"])
def test_cap_exempt_every_exempt_class_passes_the_cap(rsp, tmp_path, cls):
    now = time.time()
    _main_at_cap(rsp, now)
    inbox = tmp_path / "inbox"
    note = _note(inbox, f"2026-10-07-1000-from-MAIN-{cls}-to-RSC-x.md")
    capped = rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now)
    assert note.name in [p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set(), capped=capped)]


def test_cap_exempt_reservation_passes_an_order_and_refuses_an_answer_at_cap(rsp):
    now = time.time()
    _main_at_cap(rsp, now)
    before = rsp.DEFAULT_OUTBOUND.read_bytes()
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, rsp.MAIN_CODE, now, True) is False
    assert rsp.DEFAULT_OUTBOUND.read_bytes() == before
    assert rsp.record_outbound(rsp.DEFAULT_OUTBOUND, rsp.MAIN_CODE, now, True, exempt=True) is True


def test_cap_exempt_reserve_targets_reads_the_class_from_the_note_name(rsp, tmp_path):
    now = time.time()
    _main_at_cap(rsp, now)
    inbox = tmp_path / "inbox"
    dest = tmp_path / "main"
    order = _note(inbox, "2026-10-07-1000-from-MAIN-ORDER-to-RSC-x.md")
    answer = _note(inbox, "2026-10-07-1001-from-MAIN-ANSWER-to-RSC-y.md")
    targets, own, reasons = rsp._reserve_targets(rsp.DEFAULT_OUTBOUND, answer, [dest], inbox, now)
    assert (targets, own, reasons) == ([], [], [rsp.OUTBOUND_UNRESERVED_REASON])
    targets, own, reasons = rsp._reserve_targets(rsp.DEFAULT_OUTBOUND, order, [dest], inbox, now)
    assert targets == [dest / "moon_sync_inbox"] and own == [inbox] and reasons == []


#: Adversary on 4cdef6f: the case-blind sender reader sees MAIN at `from-main-`
#: while the kit's upper-case class reader skips it and finds `ORDER` later on.
SPLIT_PARSE = "2026-10-07-1000-from-main-ANSWER-from-LW-ORDER-y.md"


def test_cap_exempt_split_parse_name_stays_held_in_pending(rsp, tmp_path):
    now = time.time()
    _main_at_cap(rsp, now)
    inbox = tmp_path / "inbox"
    note = _note(inbox, SPLIT_PARSE)
    assert rsp.sender_of(note.name) == rsp.MAIN_CODE
    capped = rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now)
    assert note.name not in [p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set(), capped=capped)]
    # Non-vacuity: uncapped it is eligible, so the exclusion is the cap's.
    assert note.name in [p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set())]


def test_cap_exempt_split_parse_name_stays_held_in_reserve_targets(rsp, tmp_path):
    now = time.time()
    _main_at_cap(rsp, now)
    inbox = tmp_path / "inbox"
    note = _note(inbox, SPLIT_PARSE)
    before = rsp.DEFAULT_OUTBOUND.read_bytes()
    targets, own, reasons = rsp._reserve_targets(rsp.DEFAULT_OUTBOUND, note, [tmp_path / "m"], inbox, now)
    assert (targets, own, reasons) == ([], [], [rsp.OUTBOUND_UNRESERVED_REASON])
    assert rsp.DEFAULT_OUTBOUND.read_bytes() == before


def test_cap_exempt_class_is_read_at_the_sender_the_cap_counts(rsp):
    assert rsp._cap_exempt(SPLIT_PARSE) is False
    assert rsp._cap_exempt("2026-10-07-1000-from-main-ORDER-to-RSC-x.md") is True
    assert rsp._cap_exempt("2026-10-07-1000-from-MAIN-FIX-to-RSC-x.md") is True
    assert rsp._cap_exempt("2026-10-07-1000-from-MAIN-ANSWER-ORDER-x.md") is False
    assert rsp._cap_exempt("no-sender-ORDER.md") is False
