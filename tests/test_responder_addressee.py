"""Defect N9: the responder answered a sibling note addressed to MAIN.

At 2026-10-18 12:35 the unattended responder sent
`2026-10-18-1235-from-RSC-ANSWER-to-SS-batched-1-answers.md`, "confirming" a
hold that only MAIN can run, in reply to
`2026-10-18-1230-from-SS-OPERATOR-REQUEST-to-MAIN-hold-SS-tree-writes-...md`.
The kit's `classify` has no addressee test (OPERATOR-REQUEST is not an exempt
class, so it went to TRIAGE), and neither `_inbox_triage` nor the legacy
`pending` asked who the note was addressed to.

THE RULE (adjudicator DECISION C, after two refute rounds): a sibling note is
skipped ONLY when its filename addressee run is exactly `[MAIN]` and no line
in its first `ADDRESSEE_WINDOW_CHARS` characters names RSC, this tree's full
name in any spacing or case, or ALL. Every other addressee shape is answered
exactly as before N9. BIAS: when uncertain, do not skip - a wrong answer is
cheaper than silencing mail addressed to this tree.

Header shapes below are HAND-MADE copies of the structural lines of live
channel notes (title, HOP, TERMINAL, Re line). No game data.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ops.fleet_kit import fleet_inbox as fi

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"

#: The exact live note of the incident, name and header shape.
N9_NAME = "2026-10-18-1230-from-SS-OPERATOR-REQUEST-to-MAIN-hold-SS-tree-writes-2026-10-19-0320-0545-RefQuietBench.md"
N9_BODY = (
    "# From SS - OPERATOR REQUEST to MAIN: one-time hold on fleet writes into SS, "
    "2026-10-19 03:20-05:45 local\n\nHOP: 1\nREPLY REQUESTED by 2026-10-19 03:00 local.\n\n"
    "## The request\n\nPlease confirm by reply before 2026-10-19 03:00 local.\n"
)

_ANSWER = "# From SS - ANSWER to MAIN: {t}\n\nHOP: 2\nTERMINAL no-reply.\n\n## Re {re}\n\nDone.\n"
_RE_SS = "2026-10-05-0230-from-MAIN-ORDER-to-SS-ROSTER-CHANGE"

#: The live SS -> MAIN notes a0902d8 skipped, each with a hand-made copy of its
#: real header shape. A Re line quoting a `-to-ALL-SIX-` MAIN note is in the
#: window and names ALL, so DECISION C answers those (see LIVE_ALL below).
LIVE_SKIPPED: dict[str, str] = {
    "2026-09-21-1100-from-SS-to-MAIN-FIXED-SS-now-publishes-both-per-repo-lane-locks.md":
        "# From SS - to MAIN (ACTION DONE), RC (INFORMATION ONLY): FIXED.\n\n"
        "Replies to: 2026-09-20-2200-from-MAIN-lane-widget-cannot-see-SS-lane\n\n"
        "## 1. YOUR RULING IS ACCEPTED AS WRITTEN\n\nFix owner SS.\n",
    "2026-09-21-1400-from-SS-to-MAIN-CONFIRMED-the-operator-said-yes.md":
        "# From SS - to MAIN (INFORMATION, closes your 2230 ACTION): CONFIRMED.\n\n"
        "Replies to: 2026-09-20-2230-from-MAIN-ACTION-who-MAIN-is\n\nSS 1330 told you.\n",
    "2026-10-05-0820-from-SS-ANSWER-to-MAIN-0300-scorecard-before-after-2p6-to-6p4.md":
        _ANSWER.format(t="0300 scorecard", re="2026-10-05-0300-from-MAIN-ORDER-to-SS-SUPPLY-CHAIN"),
    "2026-10-05-0841-from-SS-REPORT-to-MAIN-KIT-item-5-closing-line.md":
        "# From SS - REPORT to MAIN: kit item 5 closing line\n\nHOP: 1\n"
        "No reply needed: the next kit version is the answer.\n\n## The order\n",
    "2026-10-07-2215-from-SS-ANSWER-to-MAIN-2155-C-path-inventory.md":
        "# From SS - ANSWER to MAIN 2155: C: path inventory\n\n2026-10-07 22:15 local. "
        "Channel code SS.\nTO MAIN. One destination. ANSWER.\nHOP: 2\nTERMINAL no-reply.\n",
    "2026-10-08-2239-from-SS-ANSWER-to-MAIN-2031-kit-v12-vendored.md":
        "# From SS - ANSWER to MAIN 2031: kit v12 vendored\n\nChannel code SS.\n"
        "TO MAIN. One destination. ANSWER, the ONE answer 2031 asked for.\nHOP: 1\n",
    "2026-10-09-0025-from-SS-ANSWER-to-MAIN-2246-kit-v13-vendored.md":
        "# From SS - ANSWER to MAIN 2246: kit v13 vendored\n\nChannel code SS.\n"
        "TO MAIN. ANSWER to your ORDER of 2026-10-08 22:46.\nHOP: 2\n",
    "2026-10-09-0910-from-SS-ANSWER-to-MAIN-TEMP-1-LANDED-60f4d985.md":
        _ANSWER.format(t="1 TEMP-1 landed", re="2026-10-09-0805-from-MAIN-FIX-to-SS-TEMP-1-ONE-ANSWER.md"),
    "2026-10-09-1140-from-SS-ANSWER-to-MAIN-2246-s8-repo-review-DONE.md":
        "# From SS - ANSWER to MAIN 2246 section 8: REPO-REVIEW DONE\n\nChannel code SS.\n"
        "TO MAIN. ANSWER to your ORDER of 2026-10-08 22:46, section 8.\nHOP: 2\n",
    "2026-10-13-1830-from-SS-ANSWER-to-MAIN-TEMP-2-LANDED-e57aa46.md":
        "# From SS - ANSWER to MAIN: TEMP-2 landed\n\nHOP: 2\nTERMINAL no-reply.\n\n"
        "Re 2026-10-13-1645-from-MAIN-ORDER-to-SS-TEMP-2-ONE-ANSWER.md. Provenance passed.\n",
    "2026-10-15-1941-from-SS-ANSWER-to-MAIN-batched-1-answers.md":
        _ANSWER.format(t="1 batched answers", re="2026-10-15-1925-from-MAIN-ORDER-to-SS-PUBREPO-ONE-ANSWER.md"),
    N9_NAME: N9_BODY,
}

#: Live SS -> MAIN notes a0902d8 skipped that DECISION C answers: five quote a
#: `-to-ALL-SIX-` MAIN order on their Re line, and one lists RSC in a roster
#: line, inside the window. All six are ANSWER class, which the kit acks
#: anyway, so no reply is ever drafted for them.
LIVE_ALL: dict[str, str] = {
    "2026-10-05-0438-from-SS-ANSWER-to-MAIN-batched-3-answers-0230-roster-DONE.md":
        _ANSWER.format(t="3 batched answers", re=_RE_SS)
        + "- SS-NEXT-SESSION.txt item R - DONE: rewritten to MAIN plus RC CS LW SS RSC EW.\n",
    "2026-10-09-1045-from-SS-ANSWER-to-MAIN-0930-kit-v14-vendored.md":
        _ANSWER.format(t="kit v14", re="2026-10-09-0930-from-MAIN-ORDER-to-ALL-SIX-FLEET-KIT-v14-ONE-ANSWER"),
    "2026-10-09-2155-from-SS-ANSWER-to-MAIN-2055-kit-v15-vendored.md":
        _ANSWER.format(t="KIT v15", re="2026-10-09-2055-from-MAIN-ORDER-to-ALL-SIX-FLEET-KIT-v15-ONE-ANSWER.md"),
    "2026-10-11-0538-from-SS-ANSWER-to-MAIN-1230-1312-kit-v17-vendored.md":
        _ANSWER.format(t="2 batched answers", re="2026-10-10-1230-from-MAIN-FIX-to-ALL-SIX-FLEET-KIT-v16-ONE-ANSWER.md"),
    "2026-10-18-1010-from-SS-ANSWER-to-MAIN-KIT-v18-vendored.md":
        _ANSWER.format(t="1 FLEET-KIT v18 adopted", re="2026-10-17-1018-from-MAIN-ORDER-to-ALL-SIX-FLEET-KIT-v18.md"),
    "2026-10-18-1307-from-SS-ANSWER-to-MAIN-KIT-v19-NOT-ADOPTED.md":
        _ANSWER.format(t="v19 NOT ADOPTED", re="2026-10-18-1235-from-MAIN-ORDER-to-ALL-SIX-FLEET-KIT-v19.md"),
}

#: Shapes that are answered: every addressee run other than exactly [MAIN],
#: and names with no addressee run at all.
ANSWERED_NAMES = [
    "2026-10-18-1232-from-SS-QUESTION-to-RC-what-is-your-count.md",
    "2026-10-18-1233-from-CS-QUESTION-to-LW-1030-the-leak.md",
    "2026-10-18-1234-from-RC-REQUEST-to-CS.md",
    "2026-10-18-1240-from-SS-QUESTION-to-RSC-your-count.md",
    "2026-10-18-1241-from-SS-REQUEST-to-RSC-FLEET-status.md",
    "2026-10-18-1242-from-SS-QUESTION-to-ALL-SIX-status.md",
    "2026-10-18-1243-from-SS-QUESTION-to-ALL-status.md",
    "2026-10-18-1244-from-SS-QUESTION-what-is-your-count.md",
    "2026-10-18-1245-from-SS-CORRECTION-to-SS-1700-a-wrong-refusal.md",
    "2026-10-18-1246-from-SS-to-MAIN-and-RC-x.md",
    "2026-10-18-1247-from-SS-to-LW-and-RC-x.md",
    "2026-10-18-1248-from-SS-to-EW-cc-MAIN-x.md",
    "2026-10-18-1249-from-SS-to-MAIN-cc-RSC-x.md",
    "2026-09-20-1441-from-SS-OPERATOR-RULING-yes-to-six-abstention-withdrawn.md",
    "2026-09-07-1013-from-CS-ACTION-a-retraction-owed-to-MAIN-and-a-payload.md",
]

TO_LW = "2026-10-18-1300-from-SS-QUESTION-to-LW-x.md"

#: The round-2 adversary's shapes: this tree named AFTER a heading or rule.
ROUND2_HEADS = [
    b"# n\n\n---\n\n**To:** RSC\n",
    b"# n\n\n| Field | Value |\n|---|---|\n| To | RSC |\n",
    b"# n\n\nTo: ALL\n",
    b"# n\n\n## Addressing\n\nTo: LW, Resin Compute\n",
]


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("responder_addressee_under_test", MODULE)
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
    def __init__(self, rsp) -> None:
        self.rsp = rsp
        self.work: list[str] = []
        self.triage: list[str] = []

    def spawn(self, prompt, bounds):
        self.work.append(prompt)
        return self.rsp.RESPONDER_TAG + "\n\nConfirmed.\n"

    def triage_spawn(self, prompt, bounds, note_name):
        self.triage.append(note_name)
        return "VERDICT: ANSWER\nConfirmed. We will hold."


def _note(inbox: Path, name: str, body: str = "please measure your suite\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def _fire(rsp, tmp_path, monkeypatch, sessions):
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))
    roots = {}
    for code in ("SS", "RC", "CS", "LW"):
        (tmp_path / code.lower() / "moon_sync_inbox").mkdir(parents=True, exist_ok=True)
        roots[code] = tmp_path / code.lower()
    return rsp.run_once(
        inbox=tmp_path / "inbox",
        roots=roots,
        bounds=rsp.Bounds(armed=True),
        spawn=sessions.spawn,
        triage_spawn=sessions.triage_spawn,
    )


def _sent(tmp_path) -> list[Path]:
    out: list[Path] = []
    for code in ("ss", "rc", "cs", "lw"):
        d = tmp_path / code / "moon_sync_inbox"
        if d.is_dir():
            out += sorted(d.iterdir())
    return out


def _seen(rsp) -> dict[str, dict]:
    path = rsp._kit_root() / fi.SEEN_REL
    if not path.is_file():
        return {}
    return {r["note"]: r for r in (json.loads(x) for x in path.read_text(encoding="ascii").splitlines())}


# ---------------------------------------------------------------- the rule


@pytest.mark.parametrize("name", sorted(LIVE_SKIPPED))
def test_the_live_ss_to_main_notes_are_skipped(rsp, name):
    assert rsp.addressed_elsewhere(name, LIVE_SKIPPED[name].encode("ascii")) is True


@pytest.mark.parametrize("name", sorted(LIVE_ALL))
def test_a_live_note_quoting_an_all_six_order_in_the_window_is_answered(rsp, name):
    assert rsp.addressed_elsewhere(name, LIVE_ALL[name].encode("ascii")) is False


@pytest.mark.parametrize("name", ANSWERED_NAMES)
def test_every_other_addressee_shape_is_answered(rsp, name):
    assert rsp.addressed_elsewhere(name, b"# From SS - QUESTION\n\nwhy\n") is False


def test_c_a_note_to_another_sibling_only_is_answered_as_before_n9(rsp):
    """Behaviour change from b80aab2 / a0902d8: only `[MAIN]` is skipped."""
    assert rsp.addressed_elsewhere(TO_LW, b"# n\n\nwhy\n") is False


@pytest.mark.parametrize("head", ROUND2_HEADS)
def test_c_round2_shapes_under_a_to_lw_name_are_answered(rsp, head):
    assert rsp.addressed_elsewhere(TO_LW, head) is False


@pytest.mark.parametrize("head", ROUND2_HEADS)
def test_c_round2_shapes_under_a_to_main_name_are_answered(rsp, head):
    assert rsp.addressed_elsewhere(N9_NAME, head) is False


@pytest.mark.parametrize("mention", ["RSC", "rsc", "Resin Compute", "ResinCompute", "resin-compute", "ALL-SIX"])
def test_c_a_mention_at_char_2000_overrides_the_skip(rsp, mention):
    body = N9_BODY + "x" * (2000 - len(N9_BODY)) + "\n" + mention + " please note.\n"
    assert body.index(mention) >= 2000
    assert rsp.addressed_elsewhere(N9_NAME, body.encode("ascii")) is False


def test_c_non_vacuity_a_mention_past_the_window_does_not_override(rsp):
    body = N9_BODY + "x" * (rsp.ADDRESSEE_WINDOW_CHARS + 10) + "\nRSC\n"
    assert rsp.addressed_elsewhere(N9_NAME, body.encode("ascii")) is True


def test_c_the_window_reader_is_not_truncated_to_the_kit_head(rsp, tmp_path):
    body = N9_BODY + "x" * (2900 - len(N9_BODY)) + "\nRSC\n" + "y" * 1000
    path = _note(tmp_path / "inbox", N9_NAME, body)
    window = rsp._note_window(path)
    assert len(window) == rsp.ADDRESSEE_WINDOW_CHARS and "RSC" in window
    assert "RSC" not in rsp._note_head(path)  # the kit head would have missed it


def test_main_notes_are_left_to_their_own_provenance_rule(rsp):
    assert rsp.addressed_elsewhere("2026-10-18-1300-from-MAIN-ORDER-to-MAIN-x.md", b"# x\n") is False


# ---------------------------------------------------------------- the triage lane


def test_n9_the_exact_incident_note_gets_no_spawn_and_no_reply(rsp, tmp_path, monkeypatch):
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and sessions.work == []
    assert _sent(tmp_path) == []
    row = _seen(rsp)[N9_NAME]
    assert row["action"] == fi.ACK and row["verdict"] == "not-addressed", row


def test_a_work_class_note_to_main_gets_no_reply(rsp, tmp_path, monkeypatch):
    name = "2026-10-18-1235-from-SS-FIX-to-MAIN-your-gate.md"
    _note(tmp_path / "inbox", name)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and sessions.work == []
    assert _sent(tmp_path) == []
    assert _seen(rsp)[name]["verdict"] == "not-addressed"


def test_non_vacuity_the_same_shape_to_this_tree_is_still_answered(rsp, tmp_path, monkeypatch):
    name = N9_NAME.replace("-to-MAIN-", "-to-RSC-")
    _note(tmp_path / "inbox", name, N9_BODY.replace("to MAIN", "to RSC"))
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [name]
    assert len(_sent(tmp_path)) == 1


def test_c_a_question_to_another_sibling_is_triaged_again(rsp, tmp_path, monkeypatch):
    _note(tmp_path / "inbox", TO_LW, "# From SS - QUESTION\n\nwhy\n")
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [TO_LW]


# ---------------------------------------------------------------- the legacy work lane


def test_pending_drops_the_main_only_note_and_keeps_the_neighbours(rsp, tmp_path):
    inbox = tmp_path / "inbox"
    _note(inbox, N9_NAME, N9_BODY)
    for n in ANSWERED_NAMES:
        _note(inbox, n, "# From X - QUESTION\n\nwhy\n")
    got = {p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set())}
    assert N9_NAME not in got
    assert got == set(ANSWERED_NAMES), got


def test_legacy_lane_never_replies_to_the_incident_note(rsp, tmp_path, monkeypatch):
    rsp.INBOX_TRIAGE = False
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.work == [] and _sent(tmp_path) == []


def test_the_legacy_filter_records_nothing_by_design(rsp, tmp_path):
    """`pending` is a pure per-fire filter. Like its terminal and auto-reply
    skips it writes no record (triage off writes no seen ledger - pinned by the
    v8 legacy-switch arm); the triage lane records the `not-addressed` ack."""
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    assert rsp.pending(tmp_path / "inbox", rsp.OPTED_IN, set()) == []
    assert _seen(rsp) == {}
