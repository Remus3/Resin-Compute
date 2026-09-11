"""Regression: an unreadable record must never be silently rewritten from empty.

WHAT THIS FILE WAS AND WHAT IT IS NOW. It began as a CHARACTERISATION pinning
`scripts/watch_inbox.py` as it stood: one undecodable byte in the invocation
log made the very next fire replace the whole file with a single line. The
operator ruled that all three sites be fixed rather than pinned, so the arms
that pinned the defect are INVERTED here and now pin the FIXED behaviour. The
control arms are unchanged, because a control that moves with the fix was never
a control.

THE ROOT CAUSE, ONE SENTENCE. A read that degrades to empty on decode failure,
spliced with new data and written back, converts unreadable history into
DELETED history.

THE THREE SITES, all in `scripts/watch_inbox.py`.

  1. `_log_tail` read the invocation log as strict ASCII and returned `[]` on
     failure; `log_invocation` does not append, it rebuilds the file from that
     tail plus one line and writes the result over the target. So one bad byte
     anywhere - newest line or oldest - made the very next fire replace the
     entire log. The live record held 664 lines on 2026-09-10, and it grows on every fire. Fixed
     by reading with `errors="replace"` and folding the replacement character
     down to ASCII `?`, so the readable lines survive and the rewrite is
     byte-stable across fires.
  2. `record_reported` unioned `read_reported(...)` with the new keys and wrote
     the result. Its docstring said "Union, never a rewrite", which was FALSE
     under a degraded read - the union started from nothing. Fixed by refusing
     the write.
  3. `prune_records` intersected `read_reported(...)` with what is present and
     wrote the result, so a degraded read wrote `"reported": []`. Fixed by
     refusing the write, which routes `--mark` to a refusal rather than to a
     silent erasure.

ABSENT AND UNREADABLE MUST NOT COLLAPSE INTO ONE PATH, and half the defect was
that they did: both produced an identical empty read and an identical one-line
outcome, so no arm could tell legitimately-empty history from destroyed
history. A log that does not exist has no history to lose and one line is the
CORRECT outcome. `test_absent_log_is_not_the_defect` separates them by
mechanism and `test_absent_and_unreadable_are_now_different_outcomes` separates
them by outcome; `test_an_absent_report_record_is_written_normally` pins the
same split for the report record.

THE CONTROL IS THE LOAD-BEARING HALF, kept from the original file and extended
to the two new sites. An arm that plants five lines, fires once and finds five
lines proves nothing on its own: a fixture that never wrote, or a tail that
returned its input unchanged, would produce the identical green.
`test_ascii_log_survives_a_fire`, `test_a_readable_report_record_is_updated`
and `test_a_readable_report_record_is_pruned` are the same fixtures and the
same calls with the corruption removed.

REACHABILITY, STATED HONESTLY. Every writer in this tree is ASCII-closed -
`_SOURCE_LABEL_SHAPE` rejects a non-ASCII source label and the dispositions are
module constants - so these sites are reachable by EXTERNAL corruption of a
runtime file, not by this tree's own writes. The arms below plant that
corruption directly. They demonstrate a real hazard on a real file; they do not
claim the defect fires today.

NO NON-ASCII LITERAL APPEARS IN THIS SOURCE. The bad byte is built with
`bytes([0xC3, 0xA9])` - the UTF-8 encoding of a lowercase e with an acute
accent - and the replacement character is written `chr(0xFFFD)`. Typing either
here would make this file violate the repo's own 7-bit rule and the pre-commit
glyph gate would reject it, which is a trap this tree has walked into before.
For the same reason every plant goes through `write_bytes`: `Path.write_text`
emits CRLF on Windows, `read_text` hides it, and `tests/` sits outside the
corpus of `tests/test_no_crlf_writers.py`, so nothing else here would catch a
byte sequence that was not the one intended.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "watch_inbox.py"

#: The UTF-8 encoding of a lowercase e with an acute accent, built from code
#: points so this source stays 7-bit. Any byte above 0x7F would do; this one is
#: an ordinary character a human could paste into a note by accident, which is
#: the realistic way the log acquires one.
BAD_BYTE = bytes([0xC3, 0xA9])

#: U+FFFD, named rather than typed. `errors="replace"` produces it and the fix
#: folds it away before anything is written back - see
#: `test_a_second_fire_does_not_grow_the_mangled_line` for why that matters.
REPLACEMENT = chr(0xFFFD)

#: Five plausible log lines. Small on purpose: `MAX_INVOCATION_LINES` is 2000,
#: so nothing here can be blamed on the cap, and
#: `test_the_cap_cannot_explain_the_line_counts` pins that rather than leaving
#: it to the reader.
PLANTED = [
    "2026-09-01T00:00:01\tcli\tup-to-date",
    "2026-09-02T00:00:02\tcli\tnew-notes",
    "2026-09-03T00:00:03\tmain\tup-to-date",
    "2026-09-04T00:00:04\tcli\tnew-notes",
    "2026-09-05T00:00:05\tcli\tup-to-date",
]

#: A record file this module cannot parse. Not a decode failure and not a JSON
#: failure alone - both routes are exercised, by this constant and by
#: `_ascii_payload() + BAD_BYTE`, because `read_json` returns its default for
#: BOTH and the fix must not care which one happened.
GARBAGE_RECORD = b"{ this is not json"


@pytest.fixture()
def watch(tmp_path):
    """Load `scripts/watch_inbox.py` by path with every `DEFAULT_` path redirected.

    `scripts/` is not an importable package, so the module is loaded from its
    file. The redirection is the same one `tests/test_watch_inbox.py` documents
    at length and for the same measured reason: the real
    `ops/runtime/inbox_invocations.log` is the operator's record, this module
    exercises a call that used to OVERWRITE that file with a single line, and
    an arm that reached it would perform the defect instead of testing it.

    The redirect is DISCOVERED from `dir(module)` rather than listed by name. A
    hand-kept list goes stale the moment somebody adds the next `DEFAULT_`
    constant, and it fails silently, because the arm that would catch it is the
    same list.
    """
    spec = importlib.util.spec_from_file_location("watch_inbox_log_discard", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _plant(module, payload: bytes) -> Path:
    """Write `payload` at the module's redirected log path, byte for byte."""
    target = module.DEFAULT_INVOCATIONS
    assert "isolated" in target.parts, (
        f"the fixture did not redirect DEFAULT_INVOCATIONS - refusing to write {target}"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def _ascii_payload() -> bytes:
    return ("\n".join(PLANTED) + "\n").encode("ascii")


def _lines(target: Path) -> list[str]:
    """Read the file back as UTF-8, which is what the module used to decline."""
    return [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def _plant_record(path: Path, payload: bytes) -> Path:
    """Write a report record byte for byte, under tmp_path only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _record_payload(keys: list[str]) -> bytes:
    return json.dumps({"version": 1, "reported": keys}).encode("ascii")


def _note(inbox: Path, name: str) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    target = inbox / name
    target.write_bytes(b"body\n")
    return target


def test_the_fixture_cannot_reach_the_live_invocation_log(watch):
    """The redirected path is under tmp, and it is not `ops/runtime/`.

    Non-vacuity for every log arm below: if this failed, each of them would be
    rewriting the operator's real record while reporting green.
    """
    target = watch.DEFAULT_INVOCATIONS
    live = ROOT / "ops" / "runtime" / "inbox_invocations.log"
    assert target.name == "inbox_invocations.log"
    assert "isolated" in target.parts
    assert "runtime" not in target.parts
    assert target != live
    assert not target.exists(), "nothing may have been written at the redirected path yet"


def test_one_undecodable_byte_no_longer_discards_the_log(watch):
    """Five readable lines plus one bad byte, one fire, and all five survive.

    THE INVERSION OF THE ORIGINAL ARM ONE, which asserted `len(survived) == 1`
    and that every planted line was gone. The bad byte is appended on its own
    line, the friendliest possible placement: every one of the five originals
    is complete, well-formed and ASCII. They now stay.
    """
    target = _plant(watch, _ascii_payload() + BAD_BYTE + b"\n")

    assert watch._log_tail()[: len(PLANTED)] == PLANTED, (
        "the decode failure must no longer empty the tail"
    )
    assert watch.log_invocation("main", "up-to-date") is True

    survived = _lines(target)
    assert survived[: len(PLANTED)] == PLANTED, (
        f"the originals must survive in order, got {survived}"
    )
    assert survived[-1].endswith("\tmain\tup-to-date")
    assert len(survived) == len(PLANTED) + 2, (
        f"five originals, the mangled line and the new line: got {survived}"
    )


def test_the_undecodable_bytes_are_mangled_to_ascii_not_dropped(watch):
    """The bad line is KEPT, with one ASCII `?` per undecodable byte.

    Preserving mangled bytes beats deleting readable ones - the precedent is
    `tools/moon_sync_responder.py`, which reads its own invocation log with
    `errors="replace"` and is immune to this defect by construction. Folding
    the replacement character down to `?` is this module's DEPARTURE from that
    precedent, and the next arm is the reason for it.
    """
    target = _plant(watch, b"2026-09-01T00:00:01\tcli\tcaf" + BAD_BYTE + b"\n")

    assert watch._log_tail() == ["2026-09-01T00:00:01\tcli\tcaf??"]
    assert watch.log_invocation("main", "up-to-date") is True

    survived = _lines(target)
    assert survived[0] == "2026-09-01T00:00:01\tcli\tcaf??", (
        f"the mangled line must be carried, not dropped: got {survived}"
    )
    assert REPLACEMENT not in target.read_text(encoding="utf-8"), (
        "the replacement character must not reach disk - see the next arm"
    )


def test_a_second_fire_does_not_grow_the_mangled_line(watch):
    """WHY ASCII `?` AND NOT THE REPLACEMENT CHARACTER. Otherwise the file explodes.

    `atomic_write_text` encodes UTF-8, so a retained U+FFFD would land as three
    bytes, be read back on the next fire as three replacement characters and be
    written back as nine. One bad character would pass a billion bytes inside
    twenty fires, which is a worse outcome than the defect being fixed. This
    arm fires three times and requires the mangled line to be identical each
    time.
    """
    _plant(watch, b"2026-09-01T00:00:01\tcli\tcaf" + BAD_BYTE + b"\n")
    target = watch.DEFAULT_INVOCATIONS

    seen = []
    for i in range(3):
        assert watch.log_invocation("main", f"fire-{i}") is True
        seen.append(_lines(target)[0])

    assert seen == [seen[0]] * 3, f"the mangled line drifted across fires: {seen}"
    assert seen[0] == "2026-09-01T00:00:01\tcli\tcaf??"


def test_a_bad_byte_in_the_oldest_line_no_longer_takes_the_newest(watch):
    """Position never mattered, and now neither position loses anything.

    THE INVERSION OF THE ORIGINAL ARM TWO, which required `len(survived) == 1`
    and that the newest planted line was gone. The cap drops the OLDEST lines
    and keeps the newest, because the question the log answers is about the
    recent end; this discard path kept nothing at all. The byte goes in line
    one and line five must come back with it.
    """
    corrupt_first = (
        b"2026-09-01T00:00:01\tcli\tcaf" + BAD_BYTE + b"\n"
        + ("\n".join(PLANTED[1:]) + "\n").encode("ascii")
    )
    target = _plant(watch, corrupt_first)

    assert watch.log_invocation("main", "new-notes") is True

    survived = _lines(target)
    assert PLANTED[4] in survived, "the NEWEST readable line must survive a bad byte in line one"
    assert survived[1:5] == PLANTED[1:], f"lines two through five must be intact, got {survived}"
    assert survived[0] == "2026-09-01T00:00:01\tcli\tcaf??"


def test_ascii_log_survives_a_fire(watch):
    """THE CONTROL. Same fixture, same call, no bad byte - nothing is lost.

    Unchanged from the characterisation, deliberately: without this arm the two
    above could pass because the path was wrong, the plant never landed, or the
    tail returned its input untouched. Here the same five lines come back in
    the same order with the new line appended and NO mangled line between them,
    which is what keeps `?` a statement about the bad bytes alone.
    """
    target = _plant(watch, _ascii_payload())

    assert watch._log_tail() == PLANTED
    assert watch.log_invocation("main", "up-to-date") is True

    survived = _lines(target)
    assert len(survived) == len(PLANTED) + 1, f"expected {len(PLANTED) + 1} lines, got {survived}"
    assert survived[: len(PLANTED)] == PLANTED, "the originals must survive in order"
    assert survived[-1].endswith("\tmain\tup-to-date")
    assert "?" not in "".join(survived), "a clean log must not acquire a mangle marker"


def test_absent_log_is_not_the_defect(watch):
    """A file that never existed ends at one line, by a legitimate route.

    A missing log has no history, so writing one line loses nothing. This arm
    exists so that a future change which merely stopped creating the file could
    not be mistaken for the fix.
    """
    target = watch.DEFAULT_INVOCATIONS
    assert not target.exists(), "the fixture must hand back a path with no file at it"

    assert watch._log_tail() == []
    assert watch.log_invocation("main", "up-to-date") is True

    assert len(_lines(target)) == 1
    assert watch._log_tail() != [], "the newly written line must now be readable"


def test_absent_and_unreadable_are_now_different_outcomes(watch, tmp_path):
    """The two states that used to collapse are separated by OUTCOME, not just mechanism.

    Both used to produce an identical one-line file, so no arm could tell
    legitimately-empty history from destroyed history. One fire against each,
    and the line counts must now differ.
    """
    absent_target = watch.DEFAULT_INVOCATIONS
    assert not absent_target.exists()
    assert watch.log_invocation("main", "up-to-date") is True
    absent_result = len(_lines(absent_target))

    watch.DEFAULT_INVOCATIONS = tmp_path / "isolated" / "second" / "inbox_invocations.log"
    corrupt_target = _plant(watch, _ascii_payload() + BAD_BYTE + b"\n")
    assert watch.log_invocation("main", "up-to-date") is True
    corrupt_result = len(_lines(corrupt_target))

    assert absent_result == 1, "an absent log still legitimately ends at one line"
    assert corrupt_result > absent_result, (
        f"unreadable history must not end where absent history ends:"
        f" {corrupt_result} vs {absent_result}"
    )


def test_the_tail_now_sees_the_lines_that_were_always_on_disk(watch):
    """`could not see anyway` was about the reader, and the reader is fixed.

    THE INVERSION OF THE ORIGINAL ARM, which asserted `_log_tail() == []` while
    reading the same five lines straight back out of the planted file as UTF-8.
    That gap was the whole argument: the history was readable the entire time,
    and only this module's choice of decoder hid it. Both readers now agree.
    """
    target = _plant(watch, _ascii_payload() + BAD_BYTE + b"\n")

    on_disk = _lines(target)
    assert on_disk[: len(PLANTED)] == PLANTED, "non-vacuity: the plant must have landed"

    assert watch._log_tail()[: len(PLANTED)] == PLANTED, (
        "the module's own reader must now recover what a UTF-8 reader always could"
    )


def test_the_cap_cannot_explain_the_line_counts(watch):
    """`MAX_INVOCATION_LINES` is 2000 and the plants are 5 lines long.

    Pinned rather than assumed: if a later change set the cap to 1, the arms
    above would be documenting the cap instead of the decode path. This arm
    goes red first and names the real cause.
    """
    assert watch.MAX_INVOCATION_LINES == 2000
    assert len(PLANTED) < watch.MAX_INVOCATION_LINES


# ---------------------------------------------------------------------------
# SITE 2: `record_reported`. Its docstring says "Union, never a rewrite", and
# that sentence was false under a degraded read - the union started from empty,
# so the write that followed was a total rewrite wearing a union's name. These
# arms had NO coverage at all before this slice.
# ---------------------------------------------------------------------------


def test_a_readable_report_record_is_updated(watch, tmp_path):
    """THE CONTROL FOR SITE 2. A parseable record still takes new keys.

    Without this arm the refusal arm below proves nothing: a `record_reported`
    that returned False unconditionally, or never wrote at all, would pass it.
    """
    reported = _plant_record(tmp_path / "rec" / "reported.json", _record_payload(["a.md"]))

    assert watch.record_reported(reported, ["b.md"]) is True

    payload = json.loads(reported.read_text(encoding="utf-8"))
    assert payload["reported"] == ["a.md", "b.md"], "the union must actually union"


def test_an_absent_report_record_is_written_normally(watch, tmp_path):
    """ABSENT IS NOT UNREADABLE, and only the second is refused.

    A record that does not exist yet has nothing to lose, so the first run must
    create it. Collapsing the two states is half the defect, so the split is
    pinned for this site as well as for the log.
    """
    reported = tmp_path / "rec-absent" / "reported.json"
    assert not reported.exists()

    assert watch.record_reported(reported, ["b.md"]) is True

    payload = json.loads(reported.read_text(encoding="utf-8"))
    assert payload["reported"] == ["b.md"]


def test_an_unreadable_report_record_is_not_overwritten(watch, tmp_path):
    """FAIL CLOSED. The bytes stay on disk and the write is refused.

    The precedent is `tools/moon_sync_responder.py`'s `refusals_usable`, whose
    docstring says FAIL CLOSED IS THE POINT, written for exactly this fail-open
    hazard. A record that cannot be read must not be replaced from empty; it
    must be left alone so it can be repaired.
    """
    reported = _plant_record(tmp_path / "rec" / "reported.json", GARBAGE_RECORD)

    assert watch.record_reported(reported, ["b.md"]) is False, "the write must be refused"
    assert reported.read_bytes() == GARBAGE_RECORD, "the unreadable bytes must be untouched"


def test_an_undecodable_report_record_is_not_overwritten(watch, tmp_path):
    """The OTHER route into the same degraded read, pinned separately.

    `read_json` returns its default for a decode failure AND for a JSON parse
    failure AND for a missing file. Two of those three must refuse and one must
    not, so both refusing routes are exercised rather than assumed equivalent.
    """
    payload = _record_payload(["a.md"]) + BAD_BYTE
    reported = _plant_record(tmp_path / "rec" / "reported.json", payload)

    assert watch.record_reported(reported, ["b.md"]) is False
    assert reported.read_bytes() == payload


def test_read_reported_still_degrades_to_empty_for_its_reading_callers(watch, tmp_path):
    """The READ keeps degrading, and that is deliberate rather than an oversight.

    `read_reported` feeds `withdrawn`, which only PRINTS. A degraded read there
    under-reports withdrawals and can never invent one, so it fails in the safe
    direction. Every WRITER goes through the refusing path instead. Pinning
    this stops a later reader from "finishing the fix" by making the reader
    raise, which would take the session-start hook down with it.
    """
    reported = _plant_record(tmp_path / "rec" / "reported.json", GARBAGE_RECORD)

    assert watch.read_reported(reported) == set()


# ---------------------------------------------------------------------------
# SITE 3: `prune_records`. A degraded read here intersected empty with what is
# present and wrote `"reported": []` - the acknowledge erasing the record it
# was meant to prune. Also uncovered before this slice.
# ---------------------------------------------------------------------------


def test_a_readable_report_record_is_pruned(watch, tmp_path):
    """THE CONTROL FOR SITE 3. A parseable record still loses withdrawn keys."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    reported = _plant_record(
        tmp_path / "rec" / "reported.json",
        _record_payload(["2026-09-06-1000-from-RC-first.md", "gone.md"]),
    )

    assert watch.prune_records(inbox, reported) is True

    payload = json.loads(reported.read_text(encoding="utf-8"))
    assert payload["reported"] == ["2026-09-06-1000-from-RC-first.md"], (
        "the present key must be kept and the withdrawn key dropped"
    )


def test_an_unreadable_report_record_is_not_pruned_to_empty(watch, tmp_path):
    """FAIL CLOSED, and the bytes are the assertion.

    The old path wrote `"reported": []` over a record it could not read, which
    is the acknowledge destroying exactly the history it exists to maintain.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    reported = _plant_record(tmp_path / "rec" / "reported.json", GARBAGE_RECORD)

    assert watch.prune_records(inbox, reported) is False
    assert reported.read_bytes() == GARBAGE_RECORD


def test_an_absent_report_record_prunes_to_an_empty_record(watch, tmp_path):
    """ABSENT IS NOT UNREADABLE at this site either.

    Nothing has ever been shown, so an empty record is the honest result and
    writing it is correct. This is the outcome the unreadable case USED to
    reach, which is why the two need separating by more than their result.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    reported = tmp_path / "rec-absent" / "reported.json"

    assert watch.prune_records(inbox, reported) is True

    payload = json.loads(reported.read_text(encoding="utf-8"))
    assert payload["reported"] == []


def test_the_acknowledge_refuses_rather_than_erasing_an_unreadable_record(
    watch, tmp_path, capsys
):
    """END TO END. `--mark` against an unreadable record refuses, and says so.

    THE WATERMARK MUST NOT MOVE EITHER. The old order ran `mark_seen` first and
    `prune_records` second, so a prune failure printed "it stays where it was"
    AFTER the watermark had already moved - a true-sounding line about a state
    that no longer held. The refusal is checked before either write now.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-09-06-1000-from-RC-first.md")
    state = tmp_path / "runtime" / "seen.json"
    reported = _plant_record(tmp_path / "rec" / "reported.json", GARBAGE_RECORD)

    code, disposition = watch._main(
        ["--dir", str(inbox), "--state", str(state), "--reported", str(reported), "--mark"]
    )

    assert code == 0, "a refusal is a degraded state, not a crash"
    assert disposition == watch.TERMINAL_MARK_FAILED
    assert not state.exists(), "the watermark must not have moved"
    assert reported.read_bytes() == GARBAGE_RECORD

    out = capsys.readouterr().out
    assert "could not read" in out, f"the refusal must be surfaced to the reader: {out!r}"
    for leak in ("Traceback", "JSONDecodeError", "Expecting value"):
        assert leak not in out, f"a raw error string reached the surface: {out!r}"


def test_this_source_file_is_seven_bit_ascii():
    """The bad byte and the replacement character are constructed, never typed.

    A regression test about a non-ASCII trap is the easiest file in the tree to
    write in violation of the tree's own 7-bit rule, and the pre-commit glyph
    gate would reject it at the commit rather than here.
    """
    raw = Path(__file__).resolve().read_bytes()
    offenders = [i for i, b in enumerate(raw) if b > 0x7F]
    assert offenders == [], f"non-ASCII bytes at offsets {offenders[:10]}"
