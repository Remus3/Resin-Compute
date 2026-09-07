"""Guards for `scripts/watch_inbox.py`, the cross-repo inbox watermark tool.

WHY THIS EXISTS. `moon_sync_inbox/` is the channel the sibling projects on this
box use to hand each other bytes, digests and refutations. It is GITIGNORED on
purpose - a note is correspondence, not source - which means a cold session
inherits no record of what it has already read. During the 2026-09-06 session a
live watcher was armed inside the session itself; that watcher dies with the
session, so the next one starts blind and the notes that arrived overnight look
identical to the notes answered hours ago.

The failure that motivates it is not "a note is missed". It is a note being
answered TWICE, or a sibling's question sitting unanswered while three agents
assume somebody else took it. Riot Commander's charter names the rule directly:
silence is not agreement.

WHAT THE TOOL MUST NOT DO, and each of these has an arm below:

- It must not crash when `moon_sync_inbox/` is absent. A fresh clone has no
  inbox, and a tool that traceback-exits in a clean checkout is a tool nobody
  runs twice.
- It must not surface a raw exception string. `CLAUDE.md` forbids it on any
  user-facing surface; a corrupt watermark degrades to "everything is new",
  which is the safe direction - it re-reports rather than silently swallowing.
- It must not mark notes as seen just by looking at them. Reading is not
  acknowledging, so `--mark` is a separate, explicit act.
- It must not write its state anywhere but the runtime directory, and it must
  go through `core/atomic_io.py`, which is the only sanctioned state-write path
  in this tree because readers poll mid-write.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "watch_inbox.py"


@pytest.fixture()
def watch():
    """Load the script by path - `scripts/` is not an importable package."""
    spec = importlib.util.spec_from_file_location("watch_inbox_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _note(inbox: Path, name: str, body: str = "body\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def test_the_script_exists_and_is_tracked():
    """Absence must be RED. Every arm below is downstream of this file."""
    assert SCRIPT.is_file(), f"{SCRIPT} is missing"


def test_an_absent_inbox_is_a_friendly_line_and_not_a_crash(watch, tmp_path):
    """A fresh clone has no `moon_sync_inbox/`. That is normal, not an error."""
    state = tmp_path / "runtime" / "seen.json"
    rc = watch.main(["--dir", str(tmp_path / "nope"), "--state", str(state)])
    assert rc == 0


def test_every_note_is_new_before_anything_is_marked(watch, tmp_path):
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    _note(inbox, "2026-09-06-1100-from-LW-second.md")
    state = tmp_path / "runtime" / "seen.json"

    new = watch.unseen_notes(inbox, state)

    assert sorted(p.name for p in new) == [
        "2026-09-06-1000-from-RC-first.md",
        "2026-09-06-1100-from-LW-second.md",
    ]


def test_marking_is_a_separate_act_from_reading(watch, tmp_path):
    """Listing must NOT acknowledge. Reading a note is not answering it."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"

    watch.unseen_notes(inbox, state)
    assert watch.unseen_notes(inbox, state), "listing silently marked the note as seen"

    watch.mark_seen(inbox, state)
    assert watch.unseen_notes(inbox, state) == []


def test_a_note_arriving_after_the_mark_is_new_again(watch, tmp_path):
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    _note(inbox, "2026-09-06-1200-from-LW-third.md")

    assert [p.name for p in watch.unseen_notes(inbox, state)] == [
        "2026-09-06-1200-from-LW-third.md"
    ]


def test_a_corrupt_watermark_degrades_toward_re_reporting(watch, tmp_path):
    """The safe direction. Re-reporting a note costs a read; dropping one costs
    an unanswered sibling."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(b"{ this is not json")

    assert [p.name for p in watch.unseen_notes(inbox, state)] == [
        "2026-09-06-1000-from-RC-first.md"
    ]


def test_outbound_notes_are_labelled_rather_than_hidden(watch, tmp_path):
    """This repo's own sent notes live in the same directory.

    Hiding them would be wrong - a cold session wants to know what THIS repo
    said as well as what arrived - so they are labelled by direction instead.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-inbound.md")
    _note(inbox, "2026-09-06-1100-from-RSC-outbound.md")
    state = tmp_path / "runtime" / "seen.json"

    new = watch.unseen_notes(inbox, state)
    assert len(new) == 2, "an outbound note vanished instead of being labelled"
    assert watch.direction("2026-09-06-1100-from-RSC-outbound.md") == "sent"
    assert watch.direction("2026-09-06-1000-from-RC-inbound.md") == "recv"


def test_a_renamed_note_re_surfaces_as_unread(watch, tmp_path):
    """The accepted cost of keying on names, pinned so nobody "fixes" it blind.

    Riot Commander measured this on 2026-09-07: Clockspeed re-dated four notes
    and every seen-name watcher on the box reported four unread notes that had
    already been answered. The alternative - keying on a content hash - trades
    it for a strictly worse failure, where an EDITED note reads as already seen.
    A false "new mail" costs a glance; a missed correction costs more.
    """
    inbox = tmp_path / "inbox"
    original = _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert watch.unseen_notes(inbox, state) == []

    original.rename(inbox / "2026-09-06-1500-from-RC-first.md")

    assert [p.name for p in watch.unseen_notes(inbox, state)] == [
        "2026-09-06-1500-from-RC-first.md"
    ], "a rename must re-surface, and this arm exists so that stays a CHOICE"


def test_the_seen_set_does_not_accumulate_renamed_notes(watch, tmp_path):
    """The self-heal, kept deliberately at Riot Commander's request.

    `mark_seen` rewrites the set from the CURRENT listing rather than merging
    into the old one, so a name that no longer exists drops out. Merging would
    grow the watermark by one dead entry per rename, forever.
    """
    inbox = tmp_path / "inbox"
    original = _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    original.rename(inbox / "2026-09-06-1500-from-RC-first.md")
    watch.mark_seen(inbox, state)

    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["seen"] == ["2026-09-06-1500-from-RC-first.md"], (
        "the watermark kept a name that no longer exists - it is merging "
        "instead of rewriting, and will grow by one dead entry per rename"
    )


def test_the_state_file_is_written_through_atomic_io(watch, tmp_path):
    """`core/atomic_io.py` is the only sanctioned state-write path in this tree.

    Structural, not documentary: the module must actually reference it. A
    hand-rolled `open(...).write(...)` is the thing this arm exists to catch,
    because a reader polling mid-write sees a truncated file.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert "atomic_write_json" in source, (
        "watch_inbox.py must persist its watermark through core.atomic_io, "
        "not with a bare write - readers poll mid-write"
    )
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    assert state.is_file(), "mark_seen did not create the watermark"
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert "seen" in payload


def test_the_report_never_prints_a_raw_exception_string(watch, tmp_path, capsys):
    """CLAUDE.md: never surface a raw API or error string on a user surface."""
    state = tmp_path / "runtime" / "seen.json"
    rc = watch.main(["--dir", str(tmp_path / "absent"), "--state", str(state)])
    out = capsys.readouterr().out

    assert rc == 0
    for leak in ("Traceback", "FileNotFoundError", "OSError", "Errno"):
        assert leak not in out, f"the report leaked {leak!r} to the user surface"
