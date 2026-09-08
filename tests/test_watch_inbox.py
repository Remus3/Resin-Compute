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
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "watch_inbox.py"


@pytest.fixture()
def watch(tmp_path):
    """Load the script by path - `scripts/` is not an importable package.

    THE DEFAULTS ARE REDIRECTED INTO `tmp_path`, AND THAT IS LOAD-BEARING.
    Sibling-D measured the version of this fixture that does not: one arm
    omitted a keyword argument, the parameter fell back to the OPERATOR'S LIVE
    record, and every suite run for days wrote fixture names into real state. It
    was invisible while that record was write-only - the moment a new feature
    started READING it, the live report announced 24 withdrawn notes, 18 of them
    fixtures called `note-21.md`.

    This repo reproduced it on the first run of the withdrawal work: the live
    `ops/runtime/inbox_reported.json` came back holding `a.md`, `b.md` and
    `from-XX-verbatim/`. A test that can reach live state will reach it, so the
    fixture always injects a throwaway path rather than trusting every arm to
    pass one. `test_the_fixture_cannot_reach_live_runtime_state` pins it.

    EVERY `DEFAULT_*` PATH IS REDIRECTED, DISCOVERED RATHER THAN LISTED. This
    fixture named two of them by hand until the invocation log arrived as a
    third, at which point every arm below would have appended real lines to the
    operator's live record. That is not a hypothetical: the sibling fixture in
    `tests/test_moon_sync_responder.py` named three `DEFAULT_` paths, a fourth
    was added an hour later, and the suite immediately wrote five real lines
    into the live `ops/runtime/responder_invocations.log`. A hand-maintained
    list of things to isolate goes stale the moment somebody adds the next one,
    and it fails SILENTLY, because the arm that would have caught it was the
    same list.
    """
    spec = importlib.util.spec_from_file_location("watch_inbox_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def test_the_fixture_cannot_reach_live_runtime_state(watch, tmp_path):
    """An arm that omits a path argument must not land in `ops/runtime/`.

    A write-only state file is verified by nothing, which is why the pollution
    ran for days elsewhere before anything read it back.

    ENUMERATED, so a `DEFAULT_` constant added tomorrow is covered today rather
    than being discovered in the operator's live directory.
    """
    defaults = [
        n for n in dir(watch) if n.startswith("DEFAULT_") and isinstance(getattr(watch, n), Path)
    ]

    assert len(defaults) >= 4, f"the discovery found almost nothing, so this arm is vacuous: {defaults}"
    for name in defaults:
        assert tmp_path in getattr(watch, name).parents, (
            f"{name} escapes the test's own directory, so an arm that omits "
            "the flag writes into the operator's live record"
        )


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


# ---------------------------------------------------------------------------
# THE WALKER REPORTING A DELIVERABLE ZERO TIMES.
#
# Sibling-C enumerated four ways a subdirectory-walking watcher stays silent
# over a real payload, and Sibling-D reproduced two of them independently on a
# different tree. Three land on the walker in this file and are pinned below.
#
# THE JUNCTION IS THE EXPENSIVE ONE. `Path.is_symlink()` is FALSE for an NTFS
# junction, so `rglob` descends it. Sibling-D measured a ONE-FILE drop reported
# as 32 files; Sibling-A measured the same shape at 6. The count is the
# harmless half. A junction pointing at a large tree runs the walk past the
# hook's timeout, the hook is KILLED, and a killed hook surfaces nothing at all
# - a whole-channel outage from one link, and a junction is a thing an operator
# makes on purpose for ordinary reasons.
#
# THE RULE ADOPTED FROM SIBLING-C, VERBATIM: WHAT CANNOT BE DIGESTED IS FORCED
# INTO EVERY REPORT WITH ITS REASON, never keyed silently and never dropped.
# Silence is the defect; a named anomaly is the fix.
#
# THE CONSTRAINT ADOPTED FROM SIBLING-D: the digest FORMAT must not move for a
# drop of ordinary files, or the fix dumps the whole inbox back on the operator
# as unread and is worse than the bug. That is pinned first, below, because it
# is the arm that fails if someone "improves" the manifest later.
# ---------------------------------------------------------------------------


def _junction(link: Path, target: Path) -> bool:
    """Make an NTFS junction, or report that this box will not."""
    import subprocess

    try:
        done = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0 and link.exists()


def test_the_drop_digest_format_is_unchanged_for_a_drop_of_ordinary_files(watch, tmp_path):
    """The fix must not move a single existing key.

    Sibling-D's constraint, and this repo measured the cost it prevents at 88
    notes: a watcher that re-reports the whole inbox because its digest format
    moved is a worse artifact than the silence it fixes. The expected value is
    rebuilt here from the DOCUMENTED format rather than copied from the
    implementation, so this goes red if the format changes even when the
    implementation agrees with itself.
    """
    import hashlib

    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"a.py": "print(1)\n", "sub/b.txt": "two\n"})

    lines = []
    for rel, body in (("a.py", "print(1)\n"), ("sub/b.txt", "two\n")):
        lines.append(rel + chr(0) + hashlib.sha256(body.encode("ascii")).hexdigest())
    expected = hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()

    digest, count, _manifest, anomalies = watch._drop_manifest(drop)

    assert anomalies == (), "an ordinary drop reported an anomaly"
    assert count == 2
    assert digest == expected, (
        "the drop manifest format moved. Every seen key for every drop in every "
        "sibling's watermark just became stale, and the next report dumps the "
        "whole inbox back on the operator as unread"
    )


def test_a_junction_inside_a_drop_is_not_descended(watch, tmp_path):
    """A one-file drop must report ONE file, not the tree behind a junction."""
    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"only.py": "print(1)\n"})
    behind = tmp_path / "behind"
    (behind / "deep").mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (behind / "deep" / f"f{i}.py").write_bytes(b"x\n")
    if not _junction(drop / "link", behind):
        pytest.skip("this box will not create an NTFS junction")

    digest, count, _manifest, _anomalies = watch._drop_manifest(drop)

    assert count == 1, (
        f"the walk descended the junction and reported {count} files for a "
        "one-file drop. A junction over a large tree runs past the hook "
        "timeout, the hook is killed, and a killed hook surfaces nothing at all"
    )
    assert digest, "the drop still has to hash to something"


def test_a_junction_is_named_in_the_report_with_its_reason(watch, tmp_path, capsys):
    """Not descending it is half the fix. Silence about it is the other defect."""
    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"only.py": "print(1)\n"})
    behind = tmp_path / "behind"
    behind.mkdir()
    (behind / "f.py").write_bytes(b"x\n")
    if not _junction(drop / "link", behind):
        pytest.skip("this box will not create an NTFS junction")
    state = tmp_path / "runtime" / "seen.json"

    watch.main(["--dir", str(inbox), "--state", str(state), "--reported", str(tmp_path / "r.json")])
    out = capsys.readouterr().out

    assert "link" in out, "the junction was pruned silently, which is the defect"
    assert "reparse" in out.lower(), "the report does not say WHY the entry could not be digested"


def test_a_junction_moves_the_drop_digest_rather_than_vanishing(watch, tmp_path):
    """An entry that cannot be digested must MOVE the key, never drop out of it."""
    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"only.py": "print(1)\n"})
    before, _count, _m, _a = watch._drop_manifest(drop)
    behind = tmp_path / "behind"
    behind.mkdir()
    (behind / "f.py").write_bytes(b"x\n")
    if not _junction(drop / "link", behind):
        pytest.skip("this box will not create an NTFS junction")

    after, _count2, _m2, _a2 = watch._drop_manifest(drop)

    assert after != before, (
        "a junction appeared inside an acknowledged drop and the key did not "
        "move, so the drop reads as already read"
    )


#: How many files the budget arm below is allowed to create, as a LITERAL.
#: Never derived from the constant under test - see the arm's docstring.
_BUDGET_FIXTURE_FILES = 15


def test_the_shipped_entry_budget_is_a_bounded_number(watch):
    """The ceiling has to be small enough to bound a walk under a hook timeout.

    Asserted against a literal rather than against itself, so raising the
    constant to something that is not a ceiling goes RED here instead of being
    discovered by a walk that never finishes.
    """
    assert 0 < watch.MAX_DROP_ENTRIES <= 100_000, (
        "the entry budget is not a bound any more, so a junction over a large "
        "tree runs the walk past the hook timeout and the hook is killed"
    )


def test_a_drop_over_the_entry_budget_stops_and_says_so(watch, tmp_path, capsys, monkeypatch):
    """An unbounded walk under a hook with a timeout is the outage, not the count.

    THE BUDGET IS LOWERED TO MEET THE FIXTURE, NEVER THE FIXTURE RAISED TO MEET
    THE BUDGET. The first version of this arm sized its fixture as
    `MAX_DROP_ENTRIES + 5`, which reads as thorough and is a loaded gun: a
    mutation run against the constant set it to 10**9 and the arm began writing
    a billion files, reaching 492674 before it was killed. A fixture whose size
    is derived from the value under test is not a test of that value, it is an
    amplifier for whatever that value becomes. Sibling-C reported the same class
    from the other end - an adversary probing an unbounded read started a 400
    GiB sparse write on this box - and its rule is the one applied here: cap any
    fixture an adversary, or a mutation harness, is invited to create.
    """
    monkeypatch.setattr(watch, "MAX_DROP_ENTRIES", 5)
    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"a.py": "x\n"})
    for i in range(_BUDGET_FIXTURE_FILES):
        (drop / f"f{i}.txt").write_bytes(b"x\n")
    state = tmp_path / "runtime" / "seen.json"

    _digest, count, _m, _a = watch._drop_manifest(drop)
    watch.main(["--dir", str(inbox), "--state", str(state), "--reported", str(tmp_path / "r.json")])
    out = capsys.readouterr().out

    assert count <= 5, "the walk ran past its own budget"
    assert "budget" in out.lower(), "the walk stopped early and the report did not say so"


def test_an_entry_that_is_neither_a_file_nor_a_directory_is_reported(watch):
    """The both-false path, built DIRECTLY rather than through a filename trick.

    Sibling-C reached it with a trailing dot or space in a name; Sibling-D could
    not create such a name on its box at all. An arm that depends on the trick
    is a SKIP on one of the two, so the condition is constructed here instead.
    An `if is_dir() / elif is_file()` ladder with no `else` drops such an entry
    off the end of the loop under a confident exit 0.
    """

    class _Neither:
        name = "odd"

        def is_dir(self):
            return False

        def is_file(self):
            return False

    kind, reason = watch._classify(_Neither())

    assert kind == "anomaly", "a both-false entry was classified as something digestible"
    assert reason, "the anomaly carries no reason, so the report cannot say why"


def test_a_loose_top_level_file_is_a_first_class_entry(watch, tmp_path, capsys):
    """A deliverable that is not a note and not a drop.

    Measured on this channel 2026-09-07: Sibling-A delivered
    `REFERENCE-moon_sync_poller.py.txt` beside a note. A watcher globbing `*.md`
    at the top level is silent about it - it is not a note and it is not a
    directory, so it matches nothing. Sibling-C's rewritten walker caught the
    same real delivery three hours after its fix landed.
    """
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "REFERENCE-poller.py.txt").write_bytes(b"print(1)\n")
    state = tmp_path / "runtime" / "seen.json"

    unread = watch.unseen_entries(inbox, state)
    watch.main(["--dir", str(inbox), "--state", str(state), "--reported", str(tmp_path / "r.json")])
    out = capsys.readouterr().out

    assert [e.key for e in unread] == ["REFERENCE-poller.py.txt"], (
        "a loose top-level deliverable is invisible, which is the `*.md` glob "
        "reporting a real delivery zero times"
    )
    assert "REFERENCE-poller.py.txt" in out
    assert "print(1)" not in out, "the report leaked the loose file's content"


def test_a_loose_top_level_file_edited_in_place_re_surfaces(watch, tmp_path):
    """It is keyed on content like everything else, not merely listed once."""
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    loose = inbox / "REFERENCE-poller.py.txt"
    loose.write_bytes(b"print(1)\n")
    state = tmp_path / "runtime" / "seen.json"
    watch.mark_seen(inbox, state)
    assert not watch.unseen_entries(inbox, state), "the mark did not take"

    loose.write_bytes(b"print(2)\n")

    assert [e.key for e in watch.unseen_entries(inbox, state)] == ["REFERENCE-poller.py.txt"]


# ---------------------------------------------------------------------------
# THE WITHDRAWAL PROPERTY, AND THE HALF THAT IS EASY TO SHIP BROKEN.
#
# Sibling-A pulled 50 files from four inboxes in one night. Every arrival-keyed
# watcher on the box - all five of them - reported silence while an entire
# payload left the channel, and two senders then spent a night reasoning about
# bytes the receiver did not have. A drop that leaves the channel leaves no
# trace, so the watcher is the only thing that can say so.
#
# THE BASELINE IS `reported | seen`, NOT `seen` ALONE. Sibling-D's correction:
# the case that MOTIVATED the feature is notes LISTED at session start and
# pulled before anyone ran the acknowledge, and those live in the report record
# only. A seen-only baseline scores the motivating case as a non-event.
#
# THE HALF THAT SHIPS BROKEN. Sibling-D shipped this and found the defect
# twenty minutes later by running its own command against live mail: the
# acknowledge pruned the SEEN record and never touched the REPORT record, so a
# withdrawn name re-derived itself on every run and could never be cleared by
# anything. Every arm passed, because every arm asserted that a withdrawal
# REPORTS and none asserted that it STOPS. A report the reader cannot clear is
# a defect even when every line in it is TRUE - it trains the reader to skip
# the one section with no artifact left on disk to notice later.
#
# THE THIRD ARM IS THE ONE NOBODY ASKS FOR. The report record must never become
# a second acknowledgement path. It is written by a plain reporting run, so if
# it ever fed the unread decision, a session-start report would silently
# consume the operator's queue - which is the subagent-poisoning defect this
# tool separates `--mark` out to avoid, re-entering through the back door.
# ---------------------------------------------------------------------------


def test_a_withdrawal_is_reported_after_the_entry_was_shown(watch, tmp_path, capsys):
    """The motivating case: listed at session start, pulled before any acknowledge."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-07-from-RC-drop-note.md")
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args)
    capsys.readouterr()
    (inbox / "2026-09-07-from-RC-drop-note.md").unlink()
    watch.main(args)
    out = capsys.readouterr().out

    assert "withdrawn" in out.lower(), (
        "an entry that was SHOWN to the operator left the channel and the "
        "report went silent, which is the arrival-keyed defect"
    )
    assert "2026-09-07-from-RC-drop-note.md" in out


def test_a_withdrawn_drop_is_reported_by_name(watch, tmp_path, capsys):
    """Sibling-A's real incident was three whole payload directories."""
    import shutil

    inbox = tmp_path / "inbox"
    _drop(inbox, "from-RC-verbatim", {"tool.py": "print(1)\n"})
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args + ["--mark"])
    capsys.readouterr()
    shutil.rmtree(inbox / "from-RC-verbatim")
    watch.main(args)
    out = capsys.readouterr().out

    assert "from-RC-verbatim/" in out and "withdrawn" in out.lower()


def test_an_unacknowledged_withdrawal_survives_to_the_next_run(watch, tmp_path, capsys):
    """Reporting it exactly once puts it straight back into the watermark's class.

    A session cleared before anyone read the output loses it, and unlike every
    other inbox event there is no artifact left on disk to notice later.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args)
    (inbox / "a.md").unlink()
    watch.main(args)
    capsys.readouterr()
    watch.main(args)
    out = capsys.readouterr().out

    assert "a.md" in out, "the withdrawal was reported exactly once and then lost"


def test_an_acknowledged_withdrawal_stops_being_reported(watch, tmp_path, capsys):
    """The half Sibling-D shipped broken, found by report / acknowledge / report."""
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args)
    (inbox / "a.md").unlink()
    watch.main(args)
    capsys.readouterr()
    watch.main(args + ["--mark"])
    capsys.readouterr()
    watch.main(args)
    out = capsys.readouterr().out

    assert "a.md" not in out, (
        "an acknowledged withdrawal came back. A report the reader cannot clear "
        "is a defect even when every line in it is true"
    )
    assert "withdrawn" not in out.lower()


def test_the_report_record_is_never_a_second_acknowledgement_path(watch, tmp_path):
    """The pruning must not quietly consume unread mail.

    The report record is written by a PLAIN run. If it ever fed the unread
    decision, a session-start report would consume the operator's queue - the
    exact defect `--mark` is separated out to prevent, re-entering behind it.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args)
    watch.main(args)

    assert reported.is_file(), "the report record was never written, so this arm is vacuous"
    assert json.loads(reported.read_text())["reported"], "the record is empty, arm vacuous"
    assert [e.key for e in watch.unseen_entries(inbox, state)] == ["a.md"], (
        "a note went from unread to read without any --mark. Reporting "
        "acknowledged something"
    )


def test_an_edited_note_is_not_filed_as_a_withdrawal(watch, tmp_path, capsys):
    """Once keys carry a digest, an EDIT and a RETRACTION both move the key.

    Comparing raw keys files an edited note in two contradictory sections at
    once. The comparison is on the STABLE NAME: an edit keeps its name, a
    retraction loses it.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "first\n")
    state = tmp_path / "runtime" / "seen.json"
    reported = tmp_path / "runtime" / "reported.json"
    args = ["--dir", str(inbox), "--state", str(state), "--reported", str(reported)]

    watch.main(args + ["--mark"])
    capsys.readouterr()
    _note(inbox, "a.md", "corrected\n")
    watch.main(args)
    out = capsys.readouterr().out

    assert "unread" in out and "a.md" in out
    assert "withdrawn" not in out.lower(), (
        "an edited note was filed as a withdrawal as well as unread, in two "
        "contradictory sections of the same report"
    )


# ---------------------------------------------------------------------------
# THE INVOCATION LOG.
#
# WHY IT IS A REQUIREMENT AND NOT AN IMPROVEMENT. This watcher's only output is
# a report to a human, and a report to a human leaves nothing behind that says
# it ran. The SessionStart hook declared in `.claude/settings.json` - `python
# scripts/watch_inbox.py`, timeout 5 - could therefore fire on every cold
# session, or on none at all, and this tree would read exactly the same
# afterwards either way. So the honest status of "does the hook fire, and does
# it survive /clear" was never UNVERIFIED. It was UNMEASURABLE AS BUILT, which
# is a different and worse thing: no amount of care could have measured it.
#
# `tools/moon_sync_responder.py` reached that conclusion first, on Sibling-A's
# 1806 note, and its `log_invocation` is the shape copied here.
#
# THE WRAPPER IS THE DESIGN, and it is a measurement rather than a preference.
# The responder logged per exit path first, and four terminations - `window`,
# `budget`, `empty` and `disarmed` - each returned before ever reaching the
# logger, each with a passing arm asserting its termination as a RETURN VALUE.
# A gate tested as a pure predicate is not an enforced gate. Measured against
# the live scheduled task 2026-09-07 at 19:16: four fires, four bare `start`
# lines, no record of what any of them decided.
#
# So `main` here is a WRAPPER that writes the terminal line whatever the body
# returned, including when the body raised, and every arm below asserts the LOG
# rather than the return value. An arm on the logger's own return proves
# nothing about the paths that never call it.
#
# TWO LINES PER FIRE, a `start` and exactly one terminal. The `start` is not
# redundant here either: this hook is declared with a five second timeout and
# `MAX_DROP_ENTRIES` exists precisely because a walk can run past it. A fire
# killed mid-walk writes no terminal line at all, and the `start` is the only
# thing that can say it happened.
# ---------------------------------------------------------------------------


def _log_lines(watch) -> list[str]:
    """Every non-blank line currently in the invocation log."""
    path = Path(watch.DEFAULT_INVOCATIONS)
    if not path.is_file():
        return []
    return [ln for ln in path.read_text(encoding="ascii").splitlines() if ln.strip()]


def _terminals(watch) -> list[str]:
    """The TERMINAL dispositions only, in order. `start` phase lines are dropped.

    Split on the last field rather than on a position, so a line that grows a
    column later still grades on its disposition.
    """
    return [
        line.split("\t")[-1]
        for line in _log_lines(watch)
        if line.split("\t")[-1] != watch.PHASE_START
    ]


def _one_note_inbox(tmp_path: Path) -> Path:
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-07-1800-from-RC-hello.md")
    return inbox


def test_a_watcher_run_leaves_a_record_that_it_fired(watch, tmp_path):
    """Without this line a fire is indistinguishable on disk from no fire."""
    inbox = _one_note_inbox(tmp_path)

    watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json")])

    assert _log_lines(watch), (
        "the watcher ran and left no record, which is the state that makes "
        "hook survival UNMEASURABLE rather than merely unverified"
    )
    assert _terminals(watch) == [watch.TERMINAL_REPORTED], _log_lines(watch)


def test_the_absent_inbox_is_logged_as_a_disposition_of_its_own(watch, tmp_path):
    """A FRESH CLONE HAS NO CHANNEL AT ALL, and that is not the same fact as a
    quiet one.

    `moon_sync_inbox/` is gitignored (`.gitignore:115`), so a fresh clone
    receives zero files of it and the tool prints its no-inbox line and exits 0.
    That is a real terminal disposition of a real fire. Logging it as
    "nothing unread" would say the channel was checked and was quiet, when in
    fact there was no channel to check - and the two send a reader to completely
    different next steps.
    """
    state = tmp_path / "seen.json"

    watch.main(["--dir", str(tmp_path / "nope"), "--state", str(state)])
    absent = _terminals(watch)

    empty = tmp_path / "inbox"
    empty.mkdir()
    watch.main(["--dir", str(empty), "--state", str(state)])

    assert watch.TERMINAL_NO_INBOX != watch.TERMINAL_NOTHING_UNREAD, (
        "the two dispositions are the same string, so the log cannot tell a "
        "fresh clone with no channel from a channel with nothing in it"
    )
    assert absent == [watch.TERMINAL_NO_INBOX], _log_lines(watch)
    assert _terminals(watch) == [
        watch.TERMINAL_NO_INBOX,
        watch.TERMINAL_NOTHING_UNREAD,
    ], _log_lines(watch)


def _zero_argument_flags(watch) -> list[str]:
    """Every flag `main` declares that takes no value, read off the PARSER.

    DISCOVERED, NOT LISTED. A hand-maintained list of paths that remember to do
    something goes stale silently, and this suite's sibling has already been
    bitten by exactly that: the responder's isolation fixture named three
    `DEFAULT_` paths and the fourth arrived an hour later. So the matrix comes
    from the parser itself, which means a flag added tomorrow is graded today.

    `-h` is included deliberately. It exits through `SystemExit` rather than
    through the body, which is one of the exit paths a wrapper has to cover.
    """
    parser = watch._build_parser()
    return [a.option_strings[0] for a in parser._actions if a.option_strings and a.nargs == 0]


def test_every_exit_path_through_main_writes_exactly_one_terminal_line(watch, tmp_path):
    """The property, asserted without naming a single path.

    This is the arm the responder could not have had while its terminations
    were listed by hand. It does not care which flags exist or what they are
    called: whatever `main` declares, each invocation of it must leave the log
    exactly one line longer in terminal lines, and that line must be a declared
    disposition.
    """
    flags = _zero_argument_flags(watch)
    assert len(flags) >= 4, f"the discovery found almost nothing, so this arm is vacuous: {flags}"

    inbox = _one_note_inbox(tmp_path)
    base = [
        "--dir",
        str(inbox),
        "--state",
        str(tmp_path / "seen.json"),
        "--reported",
        str(tmp_path / "reported.json"),
    ]

    observed: list[str] = []
    for flag in [None, *flags]:
        argv = base if flag is None else [*base, flag]
        before = len(_terminals(watch))
        try:
            watch.main(argv)
        except SystemExit:
            # `-h` leaves through argparse. It is still a fire.
            pass
        after = _terminals(watch)

        assert len(after) == before + 1, (
            f"{argv} left {len(after) - before} terminal lines, not one. A fire "
            "with none is indistinguishable from one that never happened, and a "
            "fire with two is a log that cannot be counted"
        )
        assert after[-1] in watch.TERMINAL_DISPOSITIONS, (
            f"{argv} logged {after[-1]!r}, which is not a declared disposition"
        )
        observed.append(after[-1])

    assert len(set(observed)) >= 2, (
        f"every flag terminated identically ({observed}), so this arm would "
        "pass against a wrapper that logs one constant and reads nothing"
    )


def test_a_crash_inside_the_body_still_leaves_exactly_one_terminal_line(watch, tmp_path, monkeypatch):
    """A traceback out of a session-start hook surfaces NOTHING at all.

    The log says the fire happened and says it died, before the exception
    continues on its way. The exception is deliberately NOT swallowed: a
    watcher that hides its own failure is the defect one layer down.
    """
    inbox = _one_note_inbox(tmp_path)

    def boom(*_args, **_kwargs):
        raise RuntimeError("planted")

    monkeypatch.setattr(watch, "_entries", boom)

    with pytest.raises(RuntimeError):
        watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json")])

    assert _terminals(watch) == [watch.TERMINAL_CRASHED], _log_lines(watch)


def test_an_argv_the_parser_rejects_is_logged_rather_than_vanishing(watch, tmp_path):
    """argparse leaves through `SystemExit`, which is not an `Exception`.

    A wrapper guarding only `Exception` lets this exit path out untouched, and
    a hook mis-wired with a stale flag then fires, fails, and leaves nothing
    behind saying so - which reads afterwards exactly like a hook that is not
    wired at all.
    """
    with pytest.raises(SystemExit):
        watch.main(["--no-such-flag-exists"])

    assert _terminals(watch) == [watch.TERMINAL_ARGV_REJECTED], _log_lines(watch)


def test_the_declared_dispositions_are_discovered_rather_than_listed(watch):
    """A new `TERMINAL_` constant nobody added to the tuple fails HERE.

    The arm above grades every observed disposition against
    `TERMINAL_DISPOSITIONS`. That tuple is itself a hand-maintained list, so it
    is cross-checked against the module's own constants rather than trusted.
    """
    declared = {
        getattr(watch, name)
        for name in dir(watch)
        if name.startswith("TERMINAL_") and isinstance(getattr(watch, name), str)
    }

    assert len(declared) >= 5, f"the discovery found almost nothing, so this arm is vacuous: {declared}"
    assert declared == set(watch.TERMINAL_DISPOSITIONS), (
        "a terminal disposition constant exists that the declared tuple does "
        f"not carry, or the reverse: {declared ^ set(watch.TERMINAL_DISPOSITIONS)}"
    )
    assert watch.PHASE_START not in declared, (
        "`start` is an OPENING line, not a termination. Counting it as one "
        "makes a fire that died mid-walk read as a fire that finished"
    )


def test_the_line_records_which_entry_point_fired(watch, tmp_path):
    """`cli` is what the SessionStart hook produces; an in-process call is not.

    Without the entry point the log answers "something ran" and not "the hook
    ran", and the hook is the whole question.
    """
    inbox = _one_note_inbox(tmp_path)
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json")]

    watch.main(argv)
    watch.main(argv, source=watch.SOURCE_CLI)

    sources = [line.split("\t")[1] for line in _log_lines(watch)]

    assert watch.SOURCE_CLI in sources, sources
    assert len(set(sources)) == 2, (
        f"both fires recorded the same entry point ({sources}), so the column "
        "cannot separate a hook fire from an in-process call"
    )


def test_the_command_line_entry_point_declares_itself_as_such(watch):
    """Structural, and no longer the only thing standing here.

    ITS STATED REASON FOR BEING STRUCTURAL IS GONE, AND THE ARM IS KEPT ANYWAY.
    This docstring used to say that the end-to-end version "would run the
    script as a subprocess, which writes into the OPERATOR'S LIVE log - the
    exact pollution the fixture above exists to prevent". That was true and it
    is now fixed: `RESINCOMPUTE_RUNTIME_DIR` points a child somewhere
    disposable, so the arms under ISOLATION ACROSS A PROCESS BOUNDARY below DO
    launch the real script and DO read the label back off disk. Those arms are
    the guarantee.

    What this one still buys is a different fact, and it is cheap: that the
    guard names `SOURCE_CLI` as its FALLBACK. An end-to-end arm run with the
    variable unset proves the observed label is `cli`; only the source says
    that `cli` is what an unset variable resolves TO, rather than a value some
    ambient environment happened to supply.
    """
    source = SCRIPT.read_text(encoding="utf-8")

    assert "resolve_source(SOURCE_CLI)" in source, (
        "the `__main__` guard does not label its own entry point with the "
        "honest fallback, so a hook fire is recorded under some other source"
    )


#: Never derived from the constant under test - see the arm's docstring.
_INVOCATION_CAP_FIXTURE = 5
_INVOCATION_FIXTURE_FIRES = 12


def test_the_shipped_invocation_cap_is_a_bounded_number(watch):
    """Asserted against a literal, so a cap that stops being one goes red here."""
    assert 0 < watch.MAX_INVOCATION_LINES <= 100_000, (
        "the invocation log has no bound any more, so a hook that fires on "
        "every prompt grows a file nobody prunes"
    )


def test_the_invocation_log_is_capped_at_the_shipped_ceiling(watch, monkeypatch):
    """THE CAP IS LOWERED TO MEET THE FIXTURE, NEVER THE FIXTURE RAISED TO IT.

    A fixture sized `MAX_INVOCATION_LINES + 5` reads as thorough and is a
    loaded gun: this suite measured the same shape against `MAX_DROP_ENTRIES`,
    where a mutation set the constant to 10**9 and the arm wrote 492674 files
    before it was killed. A fixture whose size derives from the value under
    test is an amplifier for whatever that value becomes.
    """
    monkeypatch.setattr(watch, "MAX_INVOCATION_LINES", _INVOCATION_CAP_FIXTURE)

    for i in range(_INVOCATION_FIXTURE_FIRES):
        watch.log_invocation("test", f"d{i}")

    lines = _log_lines(watch)

    assert len(lines) == _INVOCATION_CAP_FIXTURE, (
        f"the log kept {len(lines)} lines under a cap of {_INVOCATION_CAP_FIXTURE}"
    )
    assert lines[-1].split("\t")[-1] == f"d{_INVOCATION_FIXTURE_FIRES - 1}", (
        f"the cap dropped the NEWEST line rather than the oldest: {lines}"
    )


def test_the_invocation_log_is_written_through_atomic_io(watch, tmp_path):
    """AN APPEND LOG STILL MUST NOT BE OBSERVABLE HALF-WRITTEN.

    `core/atomic_io.py` is the only sanctioned state-write path in this tree
    because readers poll mid-write, and a bare `open(path, "a")` is a real
    window: a reader can see a line without its newline, and the cap needs a
    rewrite rather than an append in any case.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert "atomic_write_text" in source, (
        "the invocation log is not written through core.atomic_io"
    )

    watch.log_invocation("test", watch.PHASE_START)
    log = Path(watch.DEFAULT_INVOCATIONS)

    assert log.is_file(), "no log was written"
    strays = [p.name for p in log.parent.iterdir() if p.name != log.name]
    assert strays == [], f"a temp file was left behind by the write: {strays}"


def test_each_logged_line_is_tab_separated_ascii_with_a_timestamp(watch, tmp_path):
    """The format is what a later reader parses, so it is pinned here.

    ASCII and LF are not house style in this file - `.gitattributes` pins
    `eol=lf` and `write_text` silently emits CRLF on Windows, so a log written
    through the wrong path carries bytes that no diff would show.
    """
    inbox = _one_note_inbox(tmp_path)
    watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json")])

    raw = Path(watch.DEFAULT_INVOCATIONS).read_bytes()
    raw.decode("ascii")

    assert b"\r\n" not in raw, "the log carries CRLF, which no diff in this tree would show"
    for line in _log_lines(watch):
        fields = line.split("\t")
        assert len(fields) == 3, f"expected timestamp, entry point and disposition: {line!r}"
        time.strptime(fields[0], "%Y-%m-%dT%H:%M:%S")
        assert fields[1], f"the entry point column is empty: {line!r}"
        assert fields[2], f"the disposition column is empty: {line!r}"


def test_an_unwritable_invocation_log_does_not_take_the_watcher_down(watch, tmp_path):
    """A crashed hook surfaces NOTHING at all, which is worse than a lost line.

    `ValueError` is in the guard because of a measurement, not out of caution:
    a path carrying a NUL byte raises `ValueError` out of `mkdir`, not
    `OSError`, so an `OSError`-only guard does not catch the case it was
    written for. `core/atomic_io.py` catches `OSError` alone, so the escape is
    real rather than hypothetical.
    """
    watch.DEFAULT_INVOCATIONS = tmp_path / "nope" / (chr(0) + "bad") / "x.log"

    assert watch.log_invocation("test", watch.PHASE_START) is False

    rc = watch.main(["--dir", str(tmp_path / "absent"), "--state", str(tmp_path / "seen.json")])

    assert rc == 0, "an unwritable log took the watcher down with it"


def test_the_invocation_log_never_carries_a_payload_byte(watch, tmp_path):
    """The log is a record of FIRES, not of contents. No note body reaches it."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-07-1800-from-RC-hello.md", _NOTE_MARKER + "\n")
    _drop(inbox, "from-XX-verbatim", {"tool.py": _DROP_MARKER + "\n"})

    watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--mark"])

    raw = Path(watch.DEFAULT_INVOCATIONS).read_text(encoding="ascii")

    for marker in (_NOTE_MARKER, _DROP_MARKER):
        assert marker not in raw, f"the invocation log carried {marker!r} out of a payload"


# ---------------------------------------------------------------------------
# ISOLATION ACROSS A PROCESS BOUNDARY
#
# THE FIXTURE AT THE TOP OF THIS FILE CANNOT ISOLATE A SUBPROCESS, AND IT IS
# COMPLETE. It redirects every `DEFAULT_` Path by enumeration rather than by a
# hand-written list, which is the fix for the failure it documents - and a
# monkeypatched module attribute lives in ONE interpreter. A test that launches
# `python scripts/watch_inbox.py` gets a fresh import with the real defaults,
# and every byte it writes lands in the operator's live `ops/runtime/`.
#
# MEASURED HERE, 2026-09-08, before this section existed. With the live log
# deleted first, `python -m pytest tests/test_session_hooks.py` passed 33 arms
# and left SIX REAL LINES in `ops/runtime/inbox_invocations.log`, all of them
# labelled `cli` - the same label a genuine SessionStart hook fire writes,
# because `__main__` passed `SOURCE_CLI` in both cases. The same run left two
# PLANTED fixture keys in the live `ops/runtime/inbox_reported.json`:
# `2026-09-07-1200-from-RC-planted.md` and `from-RC-verbatim/`. That is the
# fixture-pollution failure this file's own fixture docstring records - 24
# withdrawn notes, 18 of them called `note-21.md` - arriving through the one
# door the fixture cannot close.
#
# WHY IT IS NOT COSMETIC. The whole purpose of the invocation log is to make
# "does the SessionStart hook fire, and does it survive /clear" MEASURABLE for
# the first time. An operator reading the log after a suite run counts
# suite-manufactured lines as hook fires. An instrument its own test suite
# writes to, indistinguishably, is not evidence about the world.
#
# THE FIX IS THE ENVIRONMENT, because it is the only channel that crosses a
# process boundary:
#
#   RESINCOMPUTE_RUNTIME_DIR       where the runtime records go. NOT a new knob
#                                  - `ops/health.py` already defines it and
#                                  `headless/runner.py` already honours it, so
#                                  this tool joining them is one contract
#                                  rather than a second one beside it.
#   RESINCOMPUTE_INVOCATION_SOURCE who invoked this process. Absent, the label
#                                  stays the honest `cli`, so a missing
#                                  variable can never make a real fire look
#                                  like a test.
#
# EVERY ARM BELOW THAT MATTERS DRIVES THE REAL `python scripts/watch_inbox.py`
# PATH. A gate tested as a pure predicate is not an enforced gate: an arm on
# `resolve_source`'s return value would pass over a `__main__` guard that never
# calls it. The predicate arms are here as the non-vacuity half, never as the
# guarantee.
# ---------------------------------------------------------------------------


def _reimport(monkeypatch, env: dict[str, str | None]):
    """Import the script FRESH under `env`, bypassing the isolating fixture.

    The module resolves its runtime location from the ENVIRONMENT at import,
    because that is what a subprocess inherits, so an arm about that behaviour
    has to re-import rather than re-assign an attribute.
    """
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    spec = importlib.util.spec_from_file_location("watch_inbox_env_probe", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: A literal ceiling on a spawned run, never derived from anything under test.
#: A fixture sized from the value it measures is an amplifier - this file has
#: already measured one that wrote 492674 files.
_SPAWN_TIMEOUT_SECONDS = 60


def _spawn(argv: list[str], env_extra: dict[str, str | None]):
    """Run the REAL script in a REAL child process under `env_extra`.

    `sys.executable` rather than a bare `python`: this suite has measured a
    subprocess call that never ran at all and returned the reassuring shape of
    one that did.
    """
    import subprocess
    import sys

    env = dict(os.environ)
    for name, value in env_extra.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=_SPAWN_TIMEOUT_SECONDS,
    )


def _live_paths(monkeypatch, watch) -> dict[str, Path]:
    """Every `DEFAULT_` Path as an UNREDIRECTED import sees it - the real ones.

    Derived from the module rather than spelled out here. A hand-written copy
    of `ops/runtime/inbox_invocations.log` in this file would go stale silently
    the day the record is renamed, and the arm guarding the operator's live
    state would then be guarding a path nothing writes.
    """
    plain = _reimport(monkeypatch, {watch.ENV_RUNTIME_DIR: None})
    return {
        name: getattr(plain, name)
        for name in dir(plain)
        if name.startswith("DEFAULT_") and isinstance(getattr(plain, name), Path)
    }


def _snapshot(paths: dict[str, Path]) -> dict[str, bytes | None]:
    """The bytes of each path, or None where there is no file. Creates nothing."""
    return {name: (p.read_bytes() if p.is_file() else None) for name, p in paths.items()}


def _spawned_lines(redirected: Path, monkeypatch, watch) -> list[str]:
    """The invocation lines a spawned child left under `redirected`."""
    log = redirected / _live_paths(monkeypatch, watch)["DEFAULT_INVOCATIONS"].name
    assert log.is_file(), (
        f"the child wrote no log under {redirected}; either it ignored "
        f"{watch.ENV_RUNTIME_DIR} or it wrote into live state"
    )
    return [ln for ln in log.read_text(encoding="ascii").splitlines() if ln.strip()]


def test_the_runtime_override_is_the_variable_the_rest_of_the_tree_honours(watch):
    """ONE contract, not a second one beside it.

    `ops/health.py` defines `RESINCOMPUTE_RUNTIME_DIR` and `headless/runner.py`
    already honours it. A watcher that invented its own name would leave an
    operator with two variables to set and a suite with two to remember, and
    the one nobody set is the one that writes into live state.
    """
    from ops import health as health_mod

    assert watch.ENV_RUNTIME_DIR == health_mod.ENV_RUNTIME_DIR, (
        f"the watcher reads {watch.ENV_RUNTIME_DIR!r} while the rest of the tree "
        f"reads {health_mod.ENV_RUNTIME_DIR!r}; that is two contracts wearing one name"
    )


def test_every_runtime_record_follows_the_override_and_the_inbox_does_not(watch, monkeypatch, tmp_path):
    """DISCOVERED, NEVER LISTED, and stated in both directions.

    The set that MOVES is computed by diffing two imports rather than by naming
    the three records, so a runtime record added tomorrow that forgets the
    override lands in `stayed` and turns this red today. The set that STAYS is
    asserted exactly, because a redirect that swallowed the INBOX would isolate
    the suite by making the watcher read an empty channel - green, and blind.
    """
    redirected = tmp_path / "elsewhere"
    plain = _reimport(monkeypatch, {watch.ENV_RUNTIME_DIR: None})
    fresh = _reimport(monkeypatch, {watch.ENV_RUNTIME_DIR: str(redirected)})

    names = [
        n for n in dir(plain) if n.startswith("DEFAULT_") and isinstance(getattr(plain, n), Path)
    ]
    assert len(names) >= 4, f"the discovery found almost nothing, so this arm is vacuous: {names}"

    moved = [n for n in names if getattr(fresh, n) != getattr(plain, n)]
    stayed = [n for n in names if getattr(fresh, n) == getattr(plain, n)]

    assert stayed == ["DEFAULT_INBOX"], (
        "exactly one default is not runtime state - the INBOX, which is an "
        f"input and must never move with the override. Stayed: {stayed}"
    )
    assert len(moved) >= 3, moved
    for name in moved:
        assert getattr(fresh, name).parent == redirected, (
            f"{name} ignored {watch.ENV_RUNTIME_DIR} and stayed at "
            f"{getattr(fresh, name)}; a subprocess cannot be isolated any other way"
        )


def test_an_absent_source_variable_leaves_the_honest_label(watch, monkeypatch):
    """A MISSING VARIABLE MUST NEVER MAKE A REAL FIRE LOOK LIKE A TEST.

    The fallback is what a genuine hook writes, so the default has to be the
    truthful one and the override the deliberate act - the same shape as
    `--mark` being separate from reading.
    """
    monkeypatch.delenv(watch.ENV_INVOCATION_SOURCE, raising=False)
    assert watch.resolve_source(watch.SOURCE_CLI) == watch.SOURCE_CLI
    assert watch.resolve_source(watch.SOURCE_MAIN) == watch.SOURCE_MAIN


def test_a_named_source_variable_replaces_the_label(watch, monkeypatch):
    monkeypatch.setenv(watch.ENV_INVOCATION_SOURCE, watch.SOURCE_SUITE)
    assert watch.resolve_source(watch.SOURCE_CLI) == watch.SOURCE_SUITE


#: Labels the log must refuse, with the reason each one is here. Built with
#: `chr()` where a literal would put a control byte into this file's source.
_FORGED_LABELS = (
    ("suite" + chr(9) + "cli", "a tab forges the disposition column"),
    ("a" + chr(10) + "2026-01-01T00:00:00" + chr(9) + "cli", "a newline forges a whole line"),
    ("", "an empty label leaves the column blank"),
    ("   ", "whitespace leaves the column blank"),
    ("CLI", "an uppercase spelling is a second name for one entry point"),
    ("x" * 200, "an unbounded label is an unbounded line"),
    ("-leading", "a label must start with something nameable"),
)


@pytest.mark.parametrize("forged,why", _FORGED_LABELS)
def test_a_forged_source_label_falls_back_to_the_honest_one(watch, monkeypatch, forged, why):
    """The label is untrusted input written into a TAB-separated record."""
    monkeypatch.setenv(watch.ENV_INVOCATION_SOURCE, forged)
    assert watch.resolve_source(watch.SOURCE_CLI) == watch.SOURCE_CLI, why


@pytest.mark.parametrize("legitimate", ("suite", "cli", "cron", "ops-probe", "run_once", "v2.1"))
def test_a_legitimate_source_label_survives(watch, monkeypatch, legitimate):
    """THE SURVIVING-NEIGHBOUR HALF. A validator that rejected everything would
    satisfy every arm above while making the variable useless, and the log would
    then be back to one undifferentiated label.
    """
    monkeypatch.setenv(watch.ENV_INVOCATION_SOURCE, legitimate)
    assert watch.resolve_source(watch.SOURCE_CLI) == legitimate


def test_a_spawned_process_writes_where_the_environment_points_and_nowhere_else(
    watch, monkeypatch, tmp_path
):
    """THE ENFORCED-GATE ARM. The real script, a real child process.

    An arm on `resolve_source` or on a redirected module attribute proves
    nothing about `python scripts/watch_inbox.py`, which is what
    `.claude/settings.json` declares and what a test spawns.
    """
    live = _live_paths(monkeypatch, watch)
    before = _snapshot(live)
    redirected = tmp_path / "runtime"

    done = _spawn(
        ["--dir", str(tmp_path / "absent")],
        {watch.ENV_RUNTIME_DIR: str(redirected), watch.ENV_INVOCATION_SOURCE: watch.SOURCE_SUITE},
    )

    assert done.returncode == 0, f"stderr: {done.stderr[:400]!r}"
    assert _spawned_lines(redirected, monkeypatch, watch), (
        f"the child left no lines. stdout: {done.stdout[:200]!r}"
    )
    assert _snapshot(live) == before, (
        "a spawned run changed the operator's live runtime records although the "
        "environment pointed somewhere disposable"
    )


def test_a_spawned_process_labels_itself_from_the_environment(watch, monkeypatch, tmp_path):
    """A suite-manufactured line must be TELLABLE from a hook fire.

    Same argument as the entry-point column itself: without it the log answers
    "something ran" when the question is whether the HOOK ran.
    """
    redirected = tmp_path / "runtime"
    done = _spawn(
        ["--dir", str(tmp_path / "absent")],
        {watch.ENV_RUNTIME_DIR: str(redirected), watch.ENV_INVOCATION_SOURCE: watch.SOURCE_SUITE},
    )
    assert done.returncode == 0, f"stderr: {done.stderr[:400]!r}"

    lines = _spawned_lines(redirected, monkeypatch, watch)
    sources = {ln.split("\t")[1] for ln in lines}

    assert sources == {watch.SOURCE_SUITE}, (
        f"a spawned run labelled itself {sources}; a suite line reading "
        f"{watch.SOURCE_CLI!r} is indistinguishable from a real hook fire"
    )
    assert watch.SOURCE_SUITE != watch.SOURCE_CLI, (
        "the two labels are the same string, so the column separates nothing"
    )


def test_a_spawned_process_with_nothing_naming_it_still_says_cli(watch, monkeypatch, tmp_path):
    """THE HONEST-DEFAULT ARM, on the real path.

    A hook fires with no variable set, so this is the line the instrument is
    for. If the fallback ever became the test label the log would report every
    genuine session start as suite noise, and the measurement would invert.
    """
    redirected = tmp_path / "runtime"
    done = _spawn(
        ["--dir", str(tmp_path / "absent")],
        {watch.ENV_RUNTIME_DIR: str(redirected), watch.ENV_INVOCATION_SOURCE: None},
    )
    assert done.returncode == 0, f"stderr: {done.stderr[:400]!r}"

    lines = _spawned_lines(redirected, monkeypatch, watch)
    assert {ln.split("\t")[1] for ln in lines} == {watch.SOURCE_CLI}, lines


def test_a_forged_label_cannot_reach_a_spawned_log(watch, monkeypatch, tmp_path):
    """The validator on the real path, not on its own return value.

    A tab in the label would forge the disposition column, so a line claiming
    any outcome at all could be planted by setting one variable.
    """
    redirected = tmp_path / "runtime"
    done = _spawn(
        ["--dir", str(tmp_path / "absent")],
        {
            watch.ENV_RUNTIME_DIR: str(redirected),
            watch.ENV_INVOCATION_SOURCE: "suite" + chr(9) + watch.TERMINAL_MARKED,
        },
    )
    assert done.returncode == 0, f"stderr: {done.stderr[:400]!r}"

    lines = _spawned_lines(redirected, monkeypatch, watch)
    for line in lines:
        assert len(line.split("\t")) == 3, f"a forged label grew a column: {line!r}"
    assert {ln.split("\t")[1] for ln in lines} == {watch.SOURCE_CLI}, (
        f"a rejected label did not fall back to the honest one: {lines}"
    )
