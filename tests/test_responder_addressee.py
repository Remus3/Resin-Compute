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
