"""Defect N9: the responder answered a sibling note addressed to ANOTHER tree.

At 2026-10-18 12:35 the unattended responder sent
`2026-10-18-1235-from-RSC-ANSWER-to-SS-batched-1-answers.md`, "confirming" a
hold that only MAIN can run, in reply to
`2026-10-18-1230-from-SS-OPERATOR-REQUEST-to-MAIN-hold-SS-tree-writes-...md`.
The kit's `classify` has no addressee test (OPERATOR-REQUEST is not an exempt
class, so it went to TRIAGE), and neither `_inbox_triage` nor the legacy
`pending` asked who the note was addressed to.

The rule (`addressed_elsewhere`): a non-MAIN note whose filename carries the
addressee segment `-from-<SENDER>-[<CLASS>-]to-<CODE>-` naming a known fleet
code that is neither this tree, a broadcast (ALL, ALL-SIX), nor the sender
itself (`-to-SS-1700` from SS is a correction of its own note) is addressed
elsewhere - unless its header addresses this tree (`addresses_self`, a cc). It
gets a mechanical ledger ack, never a spawn and never a note.
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

#: Siblings sharing the root cause: another tree named as addressee.
ELSEWHERE = [
    N9_NAME,
    "2026-10-18-1231-from-SS-to-MAIN-FIXED-lane-locks.md",
    "2026-10-18-1232-from-SS-QUESTION-to-RC-what-is-your-count.md",
    "2026-10-18-1233-from-CS-ANSWER-to-LW-1030-the-leak.md",
    "2026-10-18-1234-from-RC-REQUEST-to-CS.md",
]

#: Legitimate neighbours that must stay answerable.
ADDRESSED = [
    "2026-10-18-1240-from-SS-QUESTION-to-RSC-your-count.md",
    "2026-10-18-1241-from-SS-REQUEST-to-RSC-FLEET-status.md",
    "2026-10-18-1242-from-SS-QUESTION-to-ALL-SIX-status.md",
    "2026-10-18-1243-from-SS-QUESTION-to-ALL-status.md",
    "2026-10-18-1244-from-SS-QUESTION-what-is-your-count.md",
    "2026-10-18-1245-from-SS-CORRECTION-to-SS-1700-a-wrong-refusal.md",
    "2026-09-20-1441-from-SS-OPERATOR-RULING-yes-to-six-abstention-withdrawn.md",
    "2026-09-07-1013-from-CS-ACTION-a-retraction-owed-to-LL-and-a-payload.md",
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


@pytest.mark.parametrize("name", ELSEWHERE)
def test_a_note_to_another_tree_is_addressed_elsewhere(rsp, name):
    assert rsp.addressed_elsewhere(name, N9_BODY.encode("ascii")) is True


@pytest.mark.parametrize("name", ADDRESSED)
def test_a_note_to_this_tree_or_everyone_is_not_addressed_elsewhere(rsp, name):
    assert rsp.addressed_elsewhere(name, b"# From SS - QUESTION\n\nwhy\n") is False


def test_a_header_cc_to_this_tree_overrides_the_filename(rsp):
    body = b"# From SS - OPERATOR REQUEST to MAIN\n\nCC: RSC, RC\nHOP: 1\n\n## Ask\n"
    assert rsp.addressed_elsewhere(N9_NAME, body) is False


def test_main_notes_are_left_to_their_own_provenance_rule(rsp):
    assert rsp.addressed_elsewhere("2026-10-18-1300-from-MAIN-ORDER-to-RC-widget.md", b"# x\n") is False


# ---------------------------------------------------------------- the triage lane


def test_n9_the_exact_incident_note_gets_no_spawn_and_no_reply(rsp, tmp_path, monkeypatch):
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.triage == [] and sessions.work == []
    assert _sent(tmp_path) == []
    row = _seen(rsp)[N9_NAME]
    assert row["action"] == fi.ACK and row["verdict"] == "not-addressed", row


@pytest.mark.parametrize("name", ELSEWHERE[1:] + ["2026-10-18-1235-from-SS-FIX-to-MAIN-your-gate.md"])
def test_sibling_shapes_and_work_classes_to_another_tree_get_no_reply(rsp, tmp_path, monkeypatch, name):
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


# ---------------------------------------------------------------- the legacy work lane


def test_pending_drops_a_note_to_another_tree_and_keeps_the_neighbours(rsp, tmp_path):
    inbox = tmp_path / "inbox"
    for n in ELSEWHERE + ADDRESSED:
        _note(inbox, n, "# From X - QUESTION\n\nwhy\n")
    got = {p.name for p in rsp.pending(inbox, rsp.OPTED_IN, set())}
    assert got.isdisjoint(ELSEWHERE), got
    # LL is retired; every other neighbour survives.
    assert got == {n for n in ADDRESSED if "-from-LL-" not in n}, got


def test_legacy_lane_never_replies_to_the_incident_note(rsp, tmp_path, monkeypatch):
    rsp.INBOX_TRIAGE = False
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    sessions = Sessions(rsp)
    _fire(rsp, tmp_path, monkeypatch, sessions)
    assert sessions.work == [] and _sent(tmp_path) == []


# ---------------------------------------------------------------- round 1 refutation
# Bias: when uncertain, do NOT skip. Answering wrongly is cheaper than silence.

#: The live note the round-1 adversary found silenced: RSC by its FULL NAME on
#: a `To:` field (folded), in a note named `-to-RC-1030-`.
LIVE_1930 = "2026-09-21-1930-from-SS-ANSWER-to-RC-1030-the-get-is-None-leak-reproduces.md"
LIVE_1930_HEAD = (
    b"# SS 1930 - ANSWER to RC 1030: the leak reproduces here.\n\n"
    b"From: SS\n"
    b"To: CS, LL, LW, Main, Resin Compute, RC\n"
    b"    and more\n"
    b"Date: 2026-09-21\n"
)


def test_r1_the_header_names_this_tree_by_its_full_name(rsp):
    assert rsp.addressed_elsewhere(LIVE_1930, LIVE_1930_HEAD) is False


@pytest.mark.parametrize("spelling", [b"Resin Compute", b"ResinCompute", b"resin compute", b"Resin-Compute"])
def test_r1_every_spelling_of_the_full_name_counts(rsp, spelling):
    head = b"# From SS - QUESTION\n\nTo: LW, " + spelling + b"\n"
    assert rsp.addressed_elsewhere("x-from-SS-to-LW-x.md", head) is False


def test_r1_a_folded_continuation_line_naming_the_code_counts(rsp):
    assert rsp.addressed_elsewhere("x-from-SS-to-LW-x.md", b"# n\nTo: LW,\n    RSC\n") is False


@pytest.mark.parametrize("name", [
    "2026-10-18-1300-from-SS-to-LW-and-RSC-x.md",
    "2026-10-18-1301-from-SS-ORDER-to-LW-RSC-x.md",
    "2026-10-18-1302-from-SS-to-EW-cc-RSC-x.md",
    "2026-10-18-1303-from-SS-QUESTION-to-LW-CC-RSC.md",
    "2026-10-18-1304-from-SS-QUESTION-to-LW-AND-ALL-SIX-x.md",
    "2026-10-18-1305-from-SS-QUESTION-to-LW-and-SS-x.md",
])
def test_r1_every_code_in_the_addressee_run_is_read(rsp, name):
    assert rsp.addressed_elsewhere(name, b"# n\n\nwhy\n") is False


@pytest.mark.parametrize("name", [
    "2026-10-18-1310-from-SS-to-LW-and-RC-x.md",
    "2026-10-18-1311-from-SS-ORDER-to-LW-CS-x.md",
    "2026-10-18-1312-from-SS-to-EW-cc-MAIN-x.md",
])
def test_r1_non_vacuity_a_run_of_only_other_trees_is_still_skipped(rsp, name):
    assert rsp.addressed_elsewhere(name, b"# n\n\nwhy\n") is True


def test_r1_a_mention_below_the_header_does_not_count(rsp):
    """Non-vacuity for the header rule: the body is not the header."""
    body = b"# From SS - REQUEST to MAIN\n\nHOP: 1\n\n## Ask\n\nRSC and Resin Compute need not act.\n"
    assert rsp.addressed_elsewhere(N9_NAME, body) is True


def test_r1_the_live_1930_note_stays_pending(rsp, tmp_path):
    _note(tmp_path / "inbox", LIVE_1930, LIVE_1930_HEAD.decode("ascii"))
    assert [p.name for p in rsp.pending(tmp_path / "inbox", rsp.OPTED_IN, set())] == [LIVE_1930]


def test_r1_the_legacy_filter_records_nothing_by_design(rsp, tmp_path):
    """Item 4: `pending` is a pure per-fire filter. Like its terminal and
    auto-reply skips it writes no record (triage off writes no seen ledger -
    pinned by the v8 legacy-switch arm); the triage lane is where the
    `not-addressed` ack is recorded."""
    _note(tmp_path / "inbox", N9_NAME, N9_BODY)
    assert rsp.pending(tmp_path / "inbox", rsp.OPTED_IN, set()) == []
    assert _seen(rsp) == {}
