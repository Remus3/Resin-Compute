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

from core import headless_env as he

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
def routed(rsp, monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _n: str(ROOT / "fake-claude-shim.cmd"))
    monkeypatch.setattr(rsp, "_headless_gate", lambda: he.Decision(True, {"PATH": "x"}, ""))


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
