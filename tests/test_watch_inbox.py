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
assume somebody else took it. Sibling-C's charter names the rule directly:
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
import os
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

    Sibling-C measured this on 2026-09-07: Sibling-A re-dated four notes
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
    """The self-heal, kept deliberately at Sibling-C's request.

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
    assert sorted(payload["seen"]) == ["2026-09-06-1500-from-RC-first.md"], (
        "the watermark kept a key that no longer exists - it is merging "
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


# ---------------------------------------------------------------------------
# THE FOUR MEASURED HOLES. All five repos on this cross-repo channel built the
# same watcher and every one printed a confident "nothing new" over a real
# payload. Measured in a fixture inbox against the shipped functions:
#
#   PASS  a brand new note is unread
#   PASS  marking clears it
#   FAIL  a note corrected IN PLACE, same filename, does not resurface
#   FAIL  a 2-file subdirectory drop does not surface at all
#   FAIL  an edited subdirectory payload does not surface
#   FAIL  a file swapped inside a drop, count equal, does not surface
#
# Root cause, both halves: `_notes()` globbed `*.md` at the top level only and
# a DIRECTORY has no `.md` suffix, and the watermark keyed on `p.name` alone.
#
# EVERY ARM BELOW ASSERTS THE EXAMINED COUNT BEFORE THE UNREAD LIST. A watcher
# that matches nothing reports "unread: none" and looks clean - zero out of
# zero rendered as a clean bill of health - so `watch.survey()` returns the
# PAIR and the count is asserted first. `assert unread == []` on its own is the
# trap; `assert checked == 3 and unread == []` is the fix.
# ---------------------------------------------------------------------------


def _drop(inbox: Path, name: str, files: dict[str, str]) -> Path:
    """A subdirectory payload, the shape `from-RC-verbatim/` arrived in."""
    drop = inbox / name
    drop.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        target = drop / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("ascii"))
    return drop


# --- (1) a note corrected in place -----------------------------------------


def test_a_note_corrected_in_place_re_surfaces_as_unread(watch, tmp_path):
    """Not hypothetical. Notes under a CORRECTION heading have already shipped
    on this channel, reusing the filename they are correcting.
    """
    inbox = tmp_path / "inbox"
    note = _note(inbox, "2026-09-07-1000-from-RC-note.md", "original claim\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    # ARM THE CHECK EXPLICITLY. A happy-path test that never establishes its
    # precondition can pass while asserting nothing.
    assert watch.unseen_notes(inbox, state) == [], (
        "precondition failed: the note must start ACKNOWLEDGED or the arm below "
        "would pass for the wrong reason"
    )

    note.write_bytes(b"CORRECTION: that claim was wrong\n")

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries and would pass vacuously"
    assert [entry.key for entry in unread] == ["2026-09-07-1000-from-RC-note.md"], (
        "a note edited in place did not resurface; the watermark is keyed on the "
        "filename alone, so a correction reads as already read"
    )


def test_an_unchanged_note_stays_acknowledged(watch, tmp_path):
    """The surviving-neighbour half. Without a positive control a watcher that
    resurfaced EVERYTHING would satisfy the arm above while being useless.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-07-1000-from-RC-note.md", "original claim\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert unread == [], f"an untouched note resurfaced: {[e.key for e in unread]}"


# --- (2) a subdirectory drop ------------------------------------------------


def test_a_subdirectory_drop_is_reported_as_a_first_class_entry(watch, tmp_path):
    """`moon_sync_inbox/from-RC-verbatim/` held 48 real files - hooks, guards,
    tools, tests - while the notes beside it only described them. The watcher
    saw none of it: a directory has no `.md` suffix.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    _drop(inbox, "from-RC-verbatim", {"tools/gate.py": "a\n", "tests/test_gate.py": "b\n"})
    state = tmp_path / "runtime" / "seen.json"

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries; the drop is invisible"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]
    assert unread[0].kind == "drop"
    assert unread[0].files == 2


def test_an_empty_subdirectory_is_still_reported(watch, tmp_path):
    """The fleet's standing one-line test: put an empty directory in the inbox
    and see whether the next report mentions it. A drop is an entry because of
    its NAME, never because it has content to hash.
    """
    inbox = tmp_path / "inbox"
    (inbox / "from-LW-empty").mkdir(parents=True)
    state = tmp_path / "runtime" / "seen.json"

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries; an empty drop vanished"
    assert [entry.key for entry in unread] == ["from-LW-empty/"]
    assert unread[0].files == 0


def test_an_unchanged_drop_stays_acknowledged(watch, tmp_path):
    """Positive control for the three drop arms. A gate that refuses everything
    passes every refusal test.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    _drop(inbox, "from-RC-verbatim", {"a.txt": "alpha\n", "b.txt": "beta\n"})
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert unread == [], f"an untouched drop resurfaced: {[e.key for e in unread]}"


# --- (3) an edited payload inside a drop ------------------------------------


def test_an_edited_file_inside_a_drop_re_surfaces_the_drop(watch, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(inbox, "from-RC-verbatim", {"a.txt": "alpha\n", "b.txt": "beta\n"})
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert watch.unseen_entries(inbox, state) == [], "precondition: the drop must start read"

    (drop / "a.txt").write_bytes(b"alpha CORRECTED\n")

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]


def test_a_file_added_to_a_drop_re_surfaces_it(watch, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(inbox, "from-RC-verbatim", {"a.txt": "alpha\n"})
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert watch.unseen_entries(inbox, state) == [], "precondition: the drop must start read"

    (drop / "b.txt").write_bytes(b"beta\n")

    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]


# --- (4) a swap, where the FILE COUNT does not move -------------------------


def test_two_files_swapping_contents_inside_a_drop_re_surfaces_it(watch, tmp_path):
    """FILE COUNT is REFUTED as a key and this arm is why.

    A sender who REPLACES a file leaves the count equal, so a count-keyed drop
    reads as already acknowledged. The manifest digest carries the drop-relative
    POSIX path on every line, so the same multiset of file hashes under a
    different pairing is a different digest.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(inbox, "from-RC-verbatim", {"a.txt": "alpha\n", "b.txt": "beta\n"})
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    before = len(list(drop.rglob("*")))
    assert watch.unseen_entries(inbox, state) == [], "precondition: the drop must start read"

    (drop / "a.txt").write_bytes(b"beta\n")
    (drop / "b.txt").write_bytes(b"alpha\n")

    assert len(list(drop.rglob("*"))) == before, (
        "the swap changed the file count, so this arm would pass under a "
        "count-keyed watcher and prove nothing"
    )
    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]


def test_the_drop_digest_is_not_the_senders_manifest(watch, tmp_path):
    """A DIGEST OF THE SENDER'S `MANIFEST.sha256` IS REFUTED as a key.

    Sibling-C measured it: a payload edited without regenerating its
    manifest keys IDENTICAL - same manifest, completely different contents,
    same key, silently unread. Keying on a sender's manifest means trusting the
    sender remembered to rebuild it, which is exactly the assumption a watcher
    exists to remove. It is shipped as human context; it is never the key.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(
        inbox,
        "from-RC-verbatim",
        {"a.txt": "alpha\n", "MANIFEST.sha256": "deadbeef  a.txt\n"},
    )
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    manifest_before = (drop / "MANIFEST.sha256").read_bytes()
    assert watch.unseen_entries(inbox, state) == [], "precondition: the drop must start read"

    (drop / "a.txt").write_bytes(b"alpha CORRECTED, manifest left stale\n")

    assert (drop / "MANIFEST.sha256").read_bytes() == manifest_before, (
        "the manifest moved, so this arm would pass under a manifest-keyed "
        "watcher and prove nothing"
    )
    checked, unread = watch.survey(inbox, state)
    assert checked == 1, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]
    assert unread[0].manifest is True, "the manifest is human context and must be surfaced"


# --- the digest primitives --------------------------------------------------


def test_a_readable_file_digest_is_a_plain_sha256(watch, tmp_path):
    import hashlib

    path = tmp_path / "a.txt"
    path.write_bytes(b"alpha\n")
    assert watch._file_digest(path) == hashlib.sha256(b"alpha\n").hexdigest()


def test_an_unreadable_file_contributes_its_exception_class(watch, tmp_path):
    """It must MOVE the digest rather than vanish from it.

    A file that silently drops out of the manifest is a payload the watcher
    reports as unchanged while it is not, which is the failure this whole slice
    is about.
    """
    digest = watch._file_digest(tmp_path / "absent.txt")
    assert "FileNotFoundError" in digest, digest
    assert digest != watch._file_digest(tmp_path)


def test_the_manifest_digest_is_stable_across_two_reads(watch, tmp_path):
    """Non-vacuity for every drop arm above. If the digest were unstable each
    of them would pass for the wrong reason - everything would always resurface.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(inbox, "d", {"a.txt": "alpha\n", "nested/b.txt": "beta\n"})
    first = watch._drop_manifest(drop)
    assert first == watch._drop_manifest(drop)
    assert len(first[0]) == 64, f"not a sha256 hexdigest: {first[0]!r}"
    assert first[1] == 2


# --- backward compatibility with the shipped name-only watermark ------------


def test_a_legacy_name_only_watermark_still_counts_its_notes_as_read(watch, tmp_path):
    """THE MIGRATION. The live watermark on this machine holds
    `{"seen": [<name string>, ...]}` with 80-odd plain strings. A version bump
    that treated every existing entry as unseen would dump the whole inbox back
    on the operator as unread, which is worse than the bug it fixes.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "old-a.md", "a\n")
    _note(inbox, "old-b.md", "b\n")
    state = tmp_path / "runtime" / "seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(json.dumps({"seen": ["old-a.md", "old-b.md"]}).encode("ascii"))

    checked, unread = watch.survey(inbox, state)
    assert checked == 2, f"the survey examined {checked} entries"
    assert unread == [], (
        "the legacy name-only watermark was discarded, so every already-answered "
        f"note came back as unread: {[e.key for e in unread]}"
    )


def test_a_legacy_watermark_still_surfaces_a_name_it_never_listed(watch, tmp_path):
    """The surviving-neighbour half of the migration. A reader that accepted a
    legacy blob by treating EVERYTHING as read would pass the arm above.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "old-a.md", "a\n")
    _note(inbox, "brand-new.md", "n\n")
    state = tmp_path / "runtime" / "seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(json.dumps({"seen": ["old-a.md"]}).encode("ascii"))

    checked, unread = watch.survey(inbox, state)
    assert checked == 2, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["brand-new.md"]


def test_a_legacy_watermark_surfaces_a_drop_it_could_not_have_recorded(watch, tmp_path):
    """A name-only watermark never held a directory, because the old walker
    could not see one. Every drop is therefore genuinely unread, and reporting
    it is the FIX rather than a regression.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "old-a.md", "a\n")
    _drop(inbox, "from-RC-verbatim", {"a.txt": "alpha\n"})
    state = tmp_path / "runtime" / "seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(json.dumps({"seen": ["old-a.md"]}).encode("ascii"))

    checked, unread = watch.survey(inbox, state)
    assert checked == 2, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-RC-verbatim/"]


def test_marking_upgrades_a_legacy_watermark_to_the_keyed_shape(watch, tmp_path):
    inbox = tmp_path / "inbox"
    _note(inbox, "old-a.md", "a\n")
    state = tmp_path / "runtime" / "seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(json.dumps({"seen": ["old-a.md"]}).encode("ascii"))

    watch.mark_seen(inbox, state)

    payload = json.loads(state.read_text(encoding="utf-8"))
    assert isinstance(payload["seen"], dict), f"still the legacy shape: {payload}"
    assert sorted(payload["seen"]) == ["old-a.md"]
    assert len(payload["seen"]["old-a.md"]) == 64


# --- the quiet rendering the UserPromptSubmit hook depends on ---------------


def test_quiet_when_empty_prints_nothing_when_nothing_is_unread(watch, tmp_path, capsys):
    """A hook that speaks on every prompt trains the reader to skip it."""
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "a\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    rc = watch.main(["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"])

    assert rc == 0
    assert capsys.readouterr().out == ""


def test_quiet_when_empty_still_speaks_when_a_note_is_unread(watch, tmp_path, capsys):
    """The positive control. Silence is only meaningful if speech is possible."""
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "a\n")
    state = tmp_path / "runtime" / "seen.json"

    rc = watch.main(["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "unread: 1" in out
    assert "a.md" in out


def test_quiet_when_empty_says_nothing_about_an_absent_inbox(watch, tmp_path, capsys):
    rc = watch.main(
        ["--dir", str(tmp_path / "absent"), "--state", str(tmp_path / "s.json"),
         "--quiet-when-empty"]
    )
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_reporting_never_advances_the_watermark(watch, tmp_path):
    """READING IS NOT ACKNOWLEDGING, at the level the hook exercises it.

    This is what stops a subagent's session start marking the operator's queue
    read, and it is asserted on the BYTES rather than on the report.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "a\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    before = state.read_bytes()

    _note(inbox, "b.md", "b\n")
    watch.main(["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"])
    watch.main(["--dir", str(inbox), "--state", str(state)])
    watch.main(["--dir", str(inbox), "--state", str(state), "--all"])

    assert state.read_bytes() == before, "a reporting run moved the watermark"


def test_reporting_is_idempotent_and_does_not_even_touch_the_state_file(
    watch, tmp_path
):
    """Property 6, and BYTES-EQUAL IS NOT THE SAME CLAIM AS DID-NOT-WRITE.

    Sibling-D measured this from the far side on 2026-09-07 and it is their
    finding, not ours. Acknowledgement as a SIDE EFFECT of reporting means
    anything that can report can silently consume - including a probe whose only
    purpose was to check that the watcher runs. LL ran their four hook commands
    verbatim to confirm the paths still resolved after an edit, and the
    `SessionStart` one ate three genuinely unread notes into the seen set. The
    next check then honestly reported nothing new.

    This tree separates reporting from acknowledging, and did from the first
    version, but for a weaker stated reason - that an inflated watermark is worse
    than none. LL's statement of the rule is the better one and this arm exists
    because of it.

    The arm above asserts the BYTES. That is not enough on its own: an atomic
    write producing identical content still moves the modification time, so a
    watcher that rewrote the file every run would pass it. LL named the two as
    different facts and only one of them is the one you want. Both are asserted
    here, plus the idempotence of the report itself.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "a\n")
    _drop(inbox, "from-XX-verbatim", {"tool.py": "print(1)\n"})
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)

    _note(inbox, "b.md", "b\n")
    first_checked, first_unread = watch.survey(inbox, state)
    assert first_checked > 0, "nothing was checked, so this arm is vacuous"
    assert first_unread, (
        "nothing is unread, so an acknowledging watcher would have nothing to "
        "consume and this arm could not detect one"
    )

    before_bytes = state.read_bytes()
    before_mtime = state.stat().st_mtime_ns

    second_checked, second_unread = watch.survey(inbox, state)

    assert (second_checked, [e.key for e in second_unread]) == (
        first_checked,
        [e.key for e in first_unread],
    ), "two reporting runs disagreed, so reporting consumed something"
    assert state.read_bytes() == before_bytes, "a reporting run rewrote the watermark"
    assert state.stat().st_mtime_ns == before_mtime, (
        "the watermark's bytes are unchanged but it was written again. Identical "
        "content is not the same fact as no write, and a watcher that rewrites "
        "on every report is one refactor away from rewriting something different"
    )


#: Markers planted in payload bodies, assembled with `chr()` so this module does
#: not itself carry an instruction-shaped sentence for some other scanner to
#: find, and so the markers cannot collide with ordinary report text.
_NOTE_MARKER = "ZQ" + chr(45) + "NOTEBODY" + chr(45) + "MARKER"
_DROP_MARKER = "ZQ" + chr(45) + "DROPFILE" + chr(45) + "MARKER"
_MANIFEST_MARKER = "ZQ" + chr(45) + "MANIFEST" + chr(45) + "MARKER"


@pytest.mark.parametrize("mode", [[], ["--all"], ["--quiet-when-empty"]])
def test_the_report_never_carries_a_payload_byte(watch, tmp_path, capsys, mode):
    """The watcher's stdout is a PRIVILEGED surface. Names go in it, bytes do not.

    Everything this prints at `SessionStart` and `UserPromptSubmit` is injected
    into a session's context with the harness's own authority, and it lands
    there before any judgement is applied to it. A report that echoed a note's
    body, a file inside a drop, or an excerpt of either would let an imperative
    sentence sitting in a sibling repository's file - or in anything a sibling
    forwarded from somewhere else - arrive in one of our sessions wearing this
    watcher's voice. Names, counts and digests carry the information without
    carrying the payload.

    Credited to Sibling-D, relayed by Sibling-A on 2026-09-07.

    The ARMING assertion comes first and is the load-bearing half: a watcher
    that crashed and printed nothing would satisfy the no-payload assertion
    perfectly.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-07-0000-from-XX-topic.md", f"# heading\n\n{_NOTE_MARKER}\n")
    _drop(
        inbox,
        "from-XX-verbatim",
        {
            "tool.py": f"# {_DROP_MARKER}\n",
            "MANIFEST.sha256": f"{_MANIFEST_MARKER}  tool.py\n",
        },
    )
    state = tmp_path / "runtime" / "seen.json"

    watch.main(["--dir", str(inbox), "--state", str(state), *mode])
    out = capsys.readouterr().out

    assert "2026-09-07-0000-from-XX-topic.md" in out, (
        "the note name is absent, so the watcher reported nothing and the "
        "no-payload assertions below would pass for the wrong reason"
    )
    assert "from-XX-verbatim" in out, (
        "the drop name is absent, so this arm is not exercising a drop at all"
    )

    for label, marker in (
        ("a note body", _NOTE_MARKER),
        ("a file inside a drop", _DROP_MARKER),
        ("a sender's manifest", _MANIFEST_MARKER),
    ):
        assert marker not in out, (
            f"the report echoed {label} into stdout. That surface is injected "
            "into a session with the harness's authority before any judgement "
            "is applied, so a payload byte reaching it is an injection route. "
            "Report names, counts and digests instead."
        )
# ---------------------------------------------------------------------------
# METADATA-KEY MUTANTS, AND THE ARM SHAPE THAT KILLS THEM
#
# Sibling-A ran a read-only adversary over their own shipped watcher on
# 2026-09-07 and measured three mutants surviving it green. Their watcher and
# this one were both rebuilt on a `(name, digest)` key in the same round, so the
# weakness was a hypothesis here until it was measured. It reproduced. Measured
# in this worktree, against the arms above, before any of the arms below existed:
#
#   the note key computed from `st_mtime_ns` instead of the content   SURVIVED
#   the drop manifest line carrying `st_size` instead of the content  SURVIVED
#   a 16-character preview of a payload appended to the report        SURVIVED
#
# The two literal forms - `_file_digest` itself returning `str(st_mtime_ns)` or
# `str(st_size)` - were killed, but only by `test_a_readable_file_digest_is_a_
# plain_sha256` and by the 64-character length assertion in
# `test_marking_upgrades_a_legacy_watermark_to_the_keyed_shape`. Those are SHAPE
# arms. Hashing the metadata instead of returning it raw restores the shape and
# walks straight past them, and moving the substitution to the entry-key site or
# to the manifest line walks past them without even that much effort. A shape
# arm on a primitive is not a behavioural arm on the key.
#
# THE ROOT CAUSE IS THE SAME ONE IN ALL THREE CASES, and it is a property of the
# ARMS rather than of the module: an arm that varies content varies mtime, size
# and content AT ONCE, so it pins none of them individually. `write_bytes` of a
# longer corrected sentence moves all three, and every metadata key moves with
# it, so the arm passes under a watcher that never looked at a byte.
#
# TO PIN THE CONTENT LEG, HOLD EVERYTHING ELSE CONSTANT:
#
#   edit IN PLACE at CONSTANT BYTE LENGTH, and RESTORE THE MTIME.
#
# That is not a contrived shape. `cp -p`, `rsync -t`, `tar -p` and every restore
# from an archive preserve the modification time, and a policy value flipping
# from one meaning to another at identical length is the ordinary case, not the
# adversarial one.
#
# The mtime restore is itself armed rather than assumed. `os.utime` is pushed to
# a DIFFERENT time first and the difference asserted, so the arm proves the
# filesystem honours a timestamp write before it relies on one; a fast
# edit-and-rewrite that happened to land on the same coarse tick would otherwise
# make the control unarmed and the arm pass for the wrong reason. NTFS stores
# 100ns ticks and round-trips `st_mtime_ns` exactly, so the restore is asserted
# for EQUALITY rather than for nearness - if that ever stops holding this goes
# red and says so, which is the honest failure.
# ---------------------------------------------------------------------------


def _restore_mtime_provably(path: Path, mtime_ns: int, atime_ns: int) -> None:
    """Put `path` back to an exact mtime, having PROVED the write takes effect.

    WITHOUT A POSITIVE CONTROL, A CLEAN RESULT AND AN UNARMED CHECK LOOK
    IDENTICAL. If `os.utime` were silently ignored - a read-only mount, a
    filesystem without timestamp writes - the caller's arm would still pass,
    but it would be passing because the mtime never moved rather than because
    the watcher read the content. So the timestamp is pushed somewhere else
    first and the move asserted, and only then restored.
    """
    os.utime(path, ns=(atime_ns, mtime_ns + 10**9))
    assert path.stat().st_mtime_ns != mtime_ns, (
        "os.utime did not move the modification time, so the restore below "
        "would be a no-op and this arm could not tell a content key from a "
        "timestamp key"
    )
    os.utime(path, ns=(atime_ns, mtime_ns))
    assert path.stat().st_mtime_ns == mtime_ns, (
        "the modification time did not restore EXACTLY. This filesystem cannot "
        "round-trip st_mtime_ns, so the timestamp leg is not held constant and "
        "the arm below would prove nothing"
    )


def test_a_note_edited_at_constant_length_with_the_mtime_restored_re_surfaces(
    watch, tmp_path
):
    """THE CONTENT LEG, PINNED ALONE. Kills a watcher keyed on `st_mtime_ns`.

    The arm above it - `test_a_note_corrected_in_place_re_surfaces_as_unread` -
    edits the file and lets the modification time move with the edit, so it
    cannot distinguish a content key from a timestamp key. Measured: a watcher
    keying notes on `sha256(st_mtime_ns)` passed the entire file.

    Here the byte length is identical and the modification time is put back, so
    the ONLY thing that moved is the content. A watcher that reports this note
    as still read is reading metadata.

    Real-world miss this closes: a sibling corrects a note and copies it across
    with `cp -p`, or restores it from an archive. The timestamp comes back with
    the file and the correction is silently already-read.
    """
    inbox = tmp_path / "inbox"
    edited = _note(inbox, "2026-09-07-1000-from-xx-corrected.md", "verdict: allow\n")
    neighbour = _note(inbox, "2026-09-07-1100-from-xx-untouched.md", "verdict: allow\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert watch.unseen_entries(inbox, state) == [], (
        "precondition failed: both notes must start ACKNOWLEDGED or the arm "
        "below would pass for the wrong reason"
    )

    before = edited.stat()
    before_bytes = edited.read_bytes()
    neighbour_before = neighbour.stat()

    # SAME NUMBER OF BYTES. `allow` and `block` are both five characters, which
    # is the ordinary case rather than a contrived one: a policy value flipping
    # meaning at identical length is exactly what mutant 2 below is about too.
    edited.write_bytes(b"verdict: block\n")
    _restore_mtime_provably(edited, before.st_mtime_ns, before.st_atime_ns)

    after = edited.stat()
    assert after.st_size == before.st_size, (
        f"the edit changed the byte length {before.st_size} -> {after.st_size}, "
        "so SIZE moved too and this arm cannot pin the content leg"
    )
    assert edited.read_bytes() != before_bytes, (
        "the bytes did not actually change, so there is nothing for a "
        "content-keyed watcher to notice"
    )
    assert after.st_mtime_ns == before.st_mtime_ns, (
        "the modification time moved, so this arm would pass under an "
        "mtime-keyed watcher and prove nothing"
    )
    assert neighbour.stat().st_mtime_ns == neighbour_before.st_mtime_ns, (
        "the untouched neighbour's timestamp moved, so the survivor half of "
        "this sweep is not a control"
    )

    checked, unread = watch.survey(inbox, state)
    assert checked == 2, f"the survey examined {checked} entries and would pass vacuously"
    assert [entry.key for entry in unread] == [
        "2026-09-07-1000-from-xx-corrected.md"
    ], (
        "a note edited in place at constant byte length, with its modification "
        "time restored, did not resurface. The watermark is keyed on metadata "
        "rather than on content, so a correction arriving through cp -p, rsync "
        "or an archive restore reads as already answered"
    )


def test_a_drop_payload_edited_at_constant_length_and_mtime_re_surfaces_it(
    watch, tmp_path
):
    """THE SAME PIN, INSIDE A DROP. Kills a manifest keyed on size or on mtime.

    `test_an_edited_file_inside_a_drop_re_surfaces_the_drop` varies content and
    size together - `alpha` becomes `alpha CORRECTED` - so a manifest line
    carrying `st_size` in place of the file's digest passes it. Measured: it did,
    with the whole file green.

    Real-world miss this closes: a payload file going from a value meaning allow
    to one meaning deny at identical length. The file count is equal, the drop's
    total byte size is equal, every timestamp is equal, and the meaning is
    inverted.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(
        inbox,
        "from-XX-verbatim",
        {"policy.txt": "verdict: allow\n", "notes.txt": "unchanged\n"},
    )
    _note(inbox, "2026-09-07-1100-from-xx-untouched.md", "body\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert watch.unseen_entries(inbox, state) == [], (
        "precondition: the drop and the note must start read"
    )

    target = drop / "policy.txt"
    before = target.stat()
    before_bytes = target.read_bytes()
    before_files = sorted(p for p in drop.rglob("*") if p.is_file())
    before_total = sum(p.stat().st_size for p in before_files)

    target.write_bytes(b"verdict: block\n")
    _restore_mtime_provably(target, before.st_mtime_ns, before.st_atime_ns)

    after_files = sorted(p for p in drop.rglob("*") if p.is_file())
    assert after_files == before_files, (
        "the file listing moved, so this arm would pass under a count-keyed or "
        "name-keyed watcher and prove nothing"
    )
    assert sum(p.stat().st_size for p in after_files) == before_total, (
        "the drop's total byte size moved, so this arm would pass under a "
        "size-keyed manifest and prove nothing"
    )
    assert target.stat().st_size == before.st_size, (
        "the edited file's own size moved, which is the same defeat one level "
        "down"
    )
    assert target.stat().st_mtime_ns == before.st_mtime_ns, (
        "the edited file's modification time moved, so this arm would pass "
        "under an mtime-keyed manifest"
    )
    assert target.read_bytes() != before_bytes, (
        "the bytes did not actually change, so there is nothing to notice"
    )

    checked, unread = watch.survey(inbox, state)
    assert checked == 2, f"the survey examined {checked} entries"
    assert [entry.key for entry in unread] == ["from-XX-verbatim/"], (
        "a payload file edited at constant length, with its modification time "
        "restored, did not resurface the drop. The manifest is built from file "
        "metadata rather than from file bytes, so allow becoming deny at equal "
        "length is reported as already read"
    )


def test_the_drop_manifest_moves_when_only_the_bytes_move(watch, tmp_path):
    """The primitive under the arm above, pinned directly and both ways.

    `_drop_manifest` must move when the bytes move at constant size and constant
    timestamp, and must NOT move when nothing moves at all. The second half is
    the survivor guard: a manifest that returned a fresh value on every call
    would satisfy the first half while being useless, and would silently turn
    every drop arm in this file into a tautology.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    drop = _drop(inbox, "d", {"policy.txt": "verdict: allow\n"})
    target = drop / "policy.txt"

    first = watch._drop_manifest(drop)
    assert first == watch._drop_manifest(drop), (
        "the manifest is unstable across two reads of an untouched drop, so "
        "every drop arm in this file would pass for the wrong reason"
    )

    before = target.stat()
    target.write_bytes(b"verdict: block\n")
    _restore_mtime_provably(target, before.st_mtime_ns, before.st_atime_ns)
    second = watch._drop_manifest(drop)

    assert target.stat().st_size == before.st_size
    assert target.stat().st_mtime_ns == before.st_mtime_ns
    assert second[1] == first[1] == 1, "the file count moved and must not have"
    assert second[0] != first[0], (
        "the manifest digest did not move although the bytes did. Size and "
        "modification time were both held constant, so the manifest is built "
        "from metadata"
    )


def test_the_note_digest_moves_when_only_the_bytes_move(watch, tmp_path):
    """The same pin on `_file_digest`, held to behaviour rather than to shape.

    `test_a_readable_file_digest_is_a_plain_sha256` pins the exact value and is
    the stronger arm where it applies, but it is a WHITE-BOX arm on one
    primitive: a watcher can leave `_file_digest` untouched and key the entry on
    metadata at the call site, which is precisely the mutant that survived. This
    arm asks the question the watermark actually asks.
    """
    inbox = tmp_path / "inbox"
    note = _note(inbox, "a.md", "verdict: allow\n")

    before = note.stat()
    first = watch._file_digest(note)
    assert first == watch._file_digest(note), "the digest is unstable across two reads"

    note.write_bytes(b"verdict: block\n")
    _restore_mtime_provably(note, before.st_mtime_ns, before.st_atime_ns)

    assert note.stat().st_size == before.st_size
    assert note.stat().st_mtime_ns == before.st_mtime_ns
    assert watch._file_digest(note) != first, (
        "the file digest did not move although the bytes did, with size and "
        "modification time both held constant"
    )


# ---------------------------------------------------------------------------
# THE NO-PAYLOAD PROPERTY, ASSERTED OVER EVERY WINDOW RATHER THAN OVER ONE
# STRING.
#
# `test_the_report_never_carries_a_payload_byte` above asserts that one exact
# marker is ABSENT from the report. AN ABSENCE ASSERTION ON ONE EXACT STRING IS
# DEFEATED BY TRUNCATION. Measured here on 2026-09-07: a mutant appending a
# 16-character preview of a note body and of the first file in a drop passed the
# whole file, because the planted markers are 18 characters long. The preview
# leaked real payload bytes into the report and every arm stayed green.
#
# A leak is a leak at any length, so the assertion has to be over EVERY
# CONTIGUOUS WINDOW of the payload rather than over the payload entire. The
# markers below are drawn from an alphabet chosen so that no window of them can
# collide with the report's own legitimate vocabulary - names, counts, `recv`,
# `sent`, `file`, `files`, and `MANIFEST.sha256 present, not used as the key`.
# The letters of MANIFEST are excluded, the entry names planted here are
# lowercase, and a run of four characters from this alphabet cannot occur in any
# of it.
#
# Assembled with `chr()` and joined so this module does not carry an
# instruction-shaped sentence for some other scanner in this repo to find, which
# is the convention the markers above already follow.
# ---------------------------------------------------------------------------

#: Uppercase only, and disjoint from the letters of `MANIFEST`.
_WINDOW_NOTE_MARKER = "ZQBKVWDGHJLOPQRUXYZCDGKW"
_WINDOW_DROP_MARKER = "QZKBWVGDJHLPOQURXZYWKGDC"

#: Below this the window is short enough that ordinary report text could carry
#: it by coincidence, which would make the sweep a false-positive generator
#: rather than a guard. Four is well under the 16 the measured mutant leaked.
_MIN_LEAK_WINDOW = 4


def _payload_window_sweep(report: str, payload: str) -> tuple[int, list[str]]:
    """(windows checked, windows found in the report).

    RETURNS THE PAIR, like `watch.survey`. A sweep that checked nothing reports
    an empty offender list and reads exactly like a clean one - zero out of zero
    as a clean bill of health - so the caller asserts the checked count first.
    """
    checked = 0
    offenders: list[str] = []
    for size in range(_MIN_LEAK_WINDOW, len(payload) + 1):
        for start in range(len(payload) - size + 1):
            window = payload[start:start + size]
            checked += 1
            if window in report:
                offenders.append(window)
    return checked, offenders


def test_the_payload_window_sweep_actually_fires():
    """NON-VACUITY FOR THE SWEEP ITSELF, and it is the load-bearing arm.

    The two arms below assert that a sweep found nothing. That claim is worth
    nothing unless the sweep can find something, so it is pointed at a
    fabricated report carrying a 16-character preview - the exact mutation
    measured surviving this file - and must report offenders.
    """
    clean = "unread: 1\n  [recv] 2026-09-07-0000-from-xx-topic.md\n"
    checked, offenders = _payload_window_sweep(clean, _WINDOW_NOTE_MARKER)
    assert checked > 0, "the sweep examined no windows at all"
    assert offenders == [], (
        f"the sweep fired on a report with no payload in it: {offenders[:4]}. "
        "The marker alphabet collides with the report's own vocabulary and the "
        "arms below would be false positives rather than guards"
    )

    truncated = clean + "  " + _WINDOW_NOTE_MARKER[:16]
    checked, offenders = _payload_window_sweep(truncated, _WINDOW_NOTE_MARKER)
    assert checked > 0, "the sweep examined no windows at all"
    assert offenders, (
        "the sweep did not fire on a report carrying a 16-character preview of "
        "the payload. That is the mutation measured surviving this file, so a "
        "sweep blind to it is not a guard"
    )
    assert _WINDOW_NOTE_MARKER[:16] in offenders


@pytest.mark.parametrize("mode", [[], ["--all"], ["--quiet-when-empty"]])
def test_the_report_leaks_no_window_of_a_payload(watch, tmp_path, capsys, mode):
    """The privileged-surface property, hardened against truncation.

    Everything this prints at `SessionStart` and `UserPromptSubmit` is injected
    into a session's context with the harness's own authority, before any
    judgement is applied to it. A sixteen-character fragment of a sibling's file
    is still a sibling's bytes arriving in this voice, and an imperative sentence
    does not need to be complete to be read as one.

    The ARMING assertions come first: a watcher that crashed and printed nothing
    would satisfy every absence assertion below perfectly.
    """
    inbox = tmp_path / "inbox"
    _note(
        inbox,
        "2026-09-07-0000-from-xx-topic.md",
        f"# heading\n\n{_WINDOW_NOTE_MARKER}\n",
    )
    _drop(
        inbox,
        "from-XX-verbatim",
        {
            "tool.py": f"# {_WINDOW_DROP_MARKER}\n",
            "MANIFEST.sha256": f"{_WINDOW_DROP_MARKER}  tool.py\n",
        },
    )
    state = tmp_path / "runtime" / "seen.json"

    watch.main(["--dir", str(inbox), "--state", str(state), *mode])
    out = capsys.readouterr().out

    assert "2026-09-07-0000-from-xx-topic.md" in out, (
        "the note name is absent, so the watcher reported nothing and every "
        "absence assertion below would pass for the wrong reason"
    )
    assert "from-XX-verbatim" in out, (
        "the drop name is absent, so this arm is not exercising a drop at all"
    )

    for label, marker in (
        ("a note body", _WINDOW_NOTE_MARKER),
        ("a file inside a drop", _WINDOW_DROP_MARKER),
    ):
        checked, offenders = _payload_window_sweep(out, marker)
        assert checked > 0, f"no windows of {label} were examined; the sweep is vacuous"
        assert offenders == [], (
            f"the report echoed {len(offenders)} window(s) of {label} into "
            f"stdout, the longest being {max(offenders, key=len)!r}. That "
            "surface is injected into a session with the harness's authority "
            "before any judgement is applied, so a payload byte reaching it is "
            "an injection route - and a truncated fragment is still a payload "
            "byte. Report names, counts and digests instead"
        )
