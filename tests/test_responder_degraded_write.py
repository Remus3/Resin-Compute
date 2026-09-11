"""A degraded READ written BACK deletes the history it could not read.

FOUR SITES IN `tools/moon_sync_responder.py`, ONE ROOT CAUSE AND ONE EXTRA.

`core/atomic_io.read_json` returns its default for a missing file, for an
undecodable one and for corrupt JSON alike. Every caller here therefore saw one
empty list for three different facts, and two of those callers spliced that
empty with new data and wrote the result over the target. Degrading a READ to
empty is defensive. Splicing that empty with new data and writing it BACK
converts unreadable history into DELETED history, which is a different act, and
both callers returned True while doing it.

  - `record_cycle`     a one-row document written over however many rows of
                       M1-M6 measurement were on disk. Each row carries five
                       distinct numbers for a cycle that cannot be re-run.
  - `_remember_answered`  every note ever answered erased, after which the next
                       cycle re-answers all of them - the 288-a-day defect the
                       refusal record exists to close, re-entering through the
                       answered record.

The precedent is commit b3ff9fe, which fixed exactly this shape in
`scripts/watch_inbox.py`: a helper that splits ABSENT from UNREADABLE, a writer
that refuses and leaves the bytes byte-identical, and a reader that goes on
degrading to empty deliberately with an arm pinning the split. These arms follow
that cure rather than inventing a second one.

THE THIRD SITE IS AN ENCODING MISMATCH, NOT A DEGRADED READ.
`_trim_invocations` reads `encoding="ascii", errors="replace"` and
`atomic_write_text` encodes UTF-8, so one undecodable byte is read as one
U+FFFD, written back as three bytes, read back as three replacement characters
and written back as nine. Threefold growth per fire, on the function whose only
job is to hold the file under a byte cap - and it fires every time once the file
is over that cap, which is exactly when the growth compounds. Latent, because
the cap is high and no ledger on this machine has reached it.

THE FOURTH IS THE CAP ITSELF, AND ITS REPAIR IS AUTHORISED SEPARATELY
(2026-09-11). `rows = rows[-MAX_METRICS_ROWS:]` wrote the overflow NOWHERE: the
oldest evidence in the trial was destroyed by the arrival of the 501st row, with
nothing said about it anywhere. The authorised repair is a BOUNDED rotate - the
dropped rows go beside the live ledger, the archive is itself capped, and the
live file is replaced LAST so no failure path can leave it short. An unbounded
archive was NOT authorised and would reproduce the quadratic-bytes defect the
cap exists to close.

WHAT THIS FILE DELIBERATELY DOES NOT TOUCH, named so the omissions are choices:

  - `refusals_usable` does not fail closed on corrupt CONTENT, by an explicit
    judgement in its own docstring, and whether that should be harmonised with
    the two writers here is an OPERATOR DECISION that is outstanding. Silently
    harmonising it would settle a question that has not been put.
  - The other four trim sites in the responder and `scripts/watch_inbox.py` are
    NOT rotated. The invocation-log trim was examined on 2026-09-10 and ruled
    correct as it stands, its lines not being evidence rows; the arms here touch
    that function's DECODING only, never its trim policy, and
    `tests/test_responder_invocation_trim.py` still pins that the discarded
    lines go nowhere.

EVERY SIZE IS COMPUTED FROM THE MODULE'S OWN CONSTANTS. Retyping a cap here
would make an arm agree with a number this file invented rather than with the
module, and the arm would then stay green through a constant change that broke
the caller. `test_the_byte_cap_is_read_from_the_module_and_is_not_retyped_here`
keeps that honest.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"

#: U+FFFD, built rather than typed. A test that enforces a 7-bit ASCII tree by
#: typing the banned glyph into itself violates the rule it is checking, and
#: `tools/precommit_gate.py` rejects the literal in any authored file here.
REPLACEMENT = chr(0xFFFD)

#: The UTF-8 encoding of U+FFFD. The growth this file measures is a BYTE fact,
#: so the assertion is made against bytes on disk rather than against decoded
#: text, which would hide the three-for-one expansion entirely.
REPLACEMENT_BYTES = REPLACEMENT.encode("utf-8")

#: One byte no UTF-8 decoder can take and no ASCII decoder can take. This is the
#: whole input to three of the arms below: the defect needs exactly one.
BAD_BYTE = b"\xff"


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_*` path redirected under `tmp_path`.

    The same DISCOVERED redirection `tests/test_responder_invocation_trim.py`
    uses, and for the reason recorded there: a hand-written list of the paths one
    file happens to care about goes stale the moment someone adds the next
    default, and it fails SILENTLY. The specific stake here is
    `DEFAULT_INVOCATIONS`, which `_trim_invocations` reads off the module by name
    at call time - an un-redirected run would overwrite the operator's live
    invocation ledger with this file's filler, which is the very damage these
    arms describe.
    """
    spec = importlib.util.spec_from_file_location("moon_sync_responder_degraded", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)

    assert tmp_path in module.DEFAULT_INVOCATIONS.parents, (
        "the invocation ledger still points at live runtime state; the arms below "
        "would then be driving the operator's real evidence file"
    )
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_unreadable(path: Path, payload: dict) -> bytes:
    """Write `payload` as JSON and then make it UNDECODABLE with one byte.

    THE READABLE PREFIX IS LOAD BEARING. A file of pure garbage would support
    "the write was refused" and nothing else. This one plainly CONTAINS the
    history - the note names are in the bytes and can be asserted on - so the
    byte-identical assertion says the history SURVIVED rather than merely that
    the file was not replaced by something of the same length.

    `core/atomic_io.read_json` reads `encoding="utf-8"` strictly, so one 0xFF
    raises `UnicodeDecodeError`, which it logs and answers with its default.
    That is the exact production path, not a stand-in for it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload).encode("ascii") + BAD_BYTE
    path.write_bytes(raw)
    return raw


def _rows(count: int, prefix: str = "old") -> list[dict]:
    """`count` metrics rows that name their own ordinal.

    Filler made of one repeated value can only support a COUNT assertion, so a
    rotate that archived the NEWEST rows and kept the oldest would pass against
    it. Each row names its position, making survival and departure checkable by
    identity.
    """
    return [{"note": f"{prefix}{i:05d}.md", "hops": 0} for i in range(count)]


def _line(index: int, width: int) -> str:
    """One invocation-log line of exactly `width` characters, carrying its ordinal."""
    stem = f"2026-01-01T00:00:00\tseq{index:08d}\t-\tstart"
    assert len(stem) <= width, (stem, width)
    return stem.ljust(width)


def _over_bytes_under_lines(rsp) -> tuple[int, int]:
    """A (count, width) that is over the BYTE cap and under the LINE cap.

    BOTH SIDES MATTER AND FOR OPPOSITE REASONS. Over the byte cap is what makes
    the trim fire at all. Under the LINE cap is what makes it fire AGAIN on the
    file it just wrote - it keeps every line, so the rewrite leaves the file
    still over the byte cap, so the next fire fires too. That is the only
    configuration in which the threefold growth compounds, and a fixture over
    both caps at once could not exhibit it: the trim would drop to the line cap
    on the first fire and then stop firing.
    """
    width = 200
    count = (rsp.MAX_INVOCATION_BYTES // width) + 50
    assert count < rsp.MAX_INVOCATION_LINES, (count, rsp.MAX_INVOCATION_LINES)
    assert count * (width + 1) > rsp.MAX_INVOCATION_BYTES, count
    return count, width


# --------------------------------------------------------------------------
# ITEM A - `record_cycle`
# --------------------------------------------------------------------------


def test_an_unreadable_metrics_ledger_is_refused_and_left_byte_identical(rsp, tmp_path):
    """The evidence rows stay on disk and the caller is told the write did not land.

    Falsified by the pre-fix code twice over: `read_json` answered with its
    default, the row list restarted from empty, and a ONE-ROW document was
    written over the ledger while True came back.
    """
    metrics = tmp_path / "responder_metrics.json"
    _seed_unreadable(metrics, {"version": 1, "cycles": _rows(3)})
    before = _sha256(metrics)

    landed = rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    )

    assert landed is False, "an unreadable ledger was rewritten and reported as recorded"
    assert _sha256(metrics) == before, "the bytes moved, so the refusal was not a refusal"
    raw = metrics.read_bytes()
    assert b"old00000.md" in raw and b"old00002.md" in raw, (
        "the rows this ledger held are gone, which is the defect itself"
    )
    assert b"new.md" not in raw, "the new row was spliced into a record that was refused"


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("a list document", b"[1, 2, 3]"),
        ("a dict with no cycles list", b'{"version": 1}'),
        ("a dict whose cycles is not a list", b'{"version": 1, "cycles": "nope"}'),
        ("an empty file", b""),
        ("plain garbage", b"{not json at all"),
    ],
)
def test_every_unusable_metrics_shape_is_refused_rather_than_replaced(
    rsp, tmp_path, label, body
):
    """PRESENT-BUT-UNUSABLE is one state however it got that way.

    An empty file is in this table on purpose. Every writer of this record goes
    through `atomic_write_json`, which replaces the target in one step and can
    never leave a zero-byte file, so a zero-byte ledger is external corruption
    and refusing it is correct. Deleting the file is the repair that makes it
    ABSENT again, which the arm below shows still records normally.
    """
    metrics = tmp_path / "responder_metrics.json"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_bytes(body)
    before = _sha256(metrics)

    landed = rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    )

    assert landed is False, f"{label} was replaced and reported as recorded"
    assert _sha256(metrics) == before, f"{label} lost its bytes to a refused write"


def test_an_absent_metrics_ledger_still_records_the_row(rsp, tmp_path):
    """THE NEIGHBOUR THAT HAD TO SURVIVE. Absent is legitimately empty history.

    A sweep needs two guards, and this is the second: a fix that refused every
    empty read would score full marks on the arm above by breaking the first
    cycle of every trial that has ever run.
    """
    metrics = tmp_path / "absent" / "responder_metrics.json"
    assert not metrics.exists()

    landed = rsp.record_cycle(
        metrics, "first.md", 2, 0.0, 1.0, 1.0, ["A5"], True, [], "delivered"
    )

    assert landed is True, "the first cycle of a trial could not record itself"
    rows = json.loads(metrics.read_text(encoding="utf-8"))["cycles"]
    assert [r["note"] for r in rows] == ["first.md"], rows
    assert rows[0]["cycle_seconds"] == 1.0 and rows[0]["delivered"] is True, rows[0]


def test_a_readable_metrics_ledger_still_appends_rather_than_replacing(rsp, tmp_path):
    """The second neighbour: the ordinary path is untouched and still APPENDS."""
    metrics = tmp_path / "responder_metrics.json"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(json.dumps({"version": 1, "cycles": _rows(3)}), encoding="utf-8")

    assert rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    ) is True

    notes = [r["note"] for r in json.loads(metrics.read_text(encoding="utf-8"))["cycles"]]
    assert notes == ["old00000.md", "old00001.md", "old00002.md", "new.md"], notes


# --------------------------------------------------------------------------
# ITEM B - `_remember_answered`, and the reading half that must NOT change
# --------------------------------------------------------------------------


def test_a_replaceable_answered_record_is_OVERWRITTEN_so_the_record_heals(rsp, tmp_path):
    """THE ANSWERED RECORD DOES NOT FAIL CLOSED HERE, AND THAT IS AN ADJUDICATED
    REVERSAL OF WHAT THIS ARM ASSERTED WHEN IT WAS FIRST WRITTEN.

    The first version of this arm read the metrics cure across onto the answered
    record: refuse the write, leave the bytes, return False. The arithmetic goes
    the other way, and it was not checked.

    `_remember_answered` IS THE ONLY THING THAT HEALS THIS RECORD. Refuse the
    write on a replaceable poisoning and the record never becomes readable
    again, so `_answered` degrades to empty on EVERY later cycle, `pending`
    reports the same note unanswered on every later cycle, and `_run_once`
    answers it again on every later cycle. `deliver` never overwrites an
    existing name and `_reply_name` stamps to the minute, so those replies
    ACCUMULATE as distinct files in a repository this one does not own. That is
    one delivery PER CYCLE FOREVER - the 288-a-day shape - in exchange for
    avoiding ONE duplicate.

    Overwriting instead costs exactly one duplicate reply per note that the
    unreadable record had been holding, once, and then the record is readable
    and the suppression works again. Bounded beats unbounded.

    THE PRECEDENT IS IN THIS MODULE AND NOT IN THE METRICS LEDGER. A metrics row
    is IRREPLACEABLE EVIDENCE of a cycle that cannot be re-run, so refusing to
    overwrite it is right. An answered name is a SUPPRESSION KEY whose only job
    is to stop a second delivery, and a suppression key that cannot be rewritten
    has stopped suppressing. `refusals_usable` already splits the two classes
    for the refusal record on exactly this reasoning.
    """
    record = tmp_path / "responder_answered.json"
    _seed_unreadable(record, {"version": 1, "answered": ["a.md", "b.md", "c.md"]})

    landed = rsp._remember_answered(record, "d.md")

    assert landed is True, (
        "a replaceable answered record was refused, so nothing will ever repair "
        "it and every later cycle re-answers the same note"
    )
    assert rsp._answered(record) == {"d.md"}, (
        "the record did not heal itself, so the suppression is dead from here on"
    )
    assert json.loads(record.read_text(encoding="utf-8"))["answered"] == ["d.md"]


@pytest.mark.parametrize(
    "poison",
    ["{not json", "", "[]", '{"answered": "not a list"}'],
    ids=["corrupt", "empty", "wrong-top-type", "wrong-rows-type"],
)
def test_every_replaceable_answered_shape_is_overwritten_rather_than_refused(
    rsp, tmp_path, poison
):
    """THE SWEEP. One measured poisoning is never the only one of its class.

    The same four shapes `refusals_usable`'s own non-vacuity arm uses, because
    the classification being mirrored is that function's and a split proved on
    one shape is a split proved on nothing.
    """
    record = tmp_path / "responder_answered.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(poison, encoding="utf-8")

    assert rsp._remember_answered(record, "d.md") is True, poison
    assert rsp._answered(record) == {"d.md"}, poison


@pytest.mark.parametrize(
    "shape",
    ["dir-at-path", "file-at-parent"],
)
def test_a_structurally_unusable_answered_record_is_refused_and_nothing_is_written(
    rsp, tmp_path, shape
):
    """THE OTHER HALF OF THE SPLIT, and the half where refusing is right.

    In both shapes `atomic_write_json` CANNOT LAND, so overwriting is not on
    offer: the record stays unreadable whatever the writer returns. Returning
    True there would tell `_run_once` the delivery was suppressed when it was
    not, which is the one lie that makes the duplicate loop silent.

    Falsified by a `_remember_answered` that reports success off
    `atomic_write_json`'s own return without asking whether the target is even a
    file, and by any version that fails closed on the replaceable shapes above
    while leaving these two open.
    """
    record = tmp_path / "structural" / "responder_answered.json"
    if shape == "dir-at-path":
        record.mkdir(parents=True)
        (record / "keep.txt").write_text("not empty, so replace cannot win", encoding="ascii")
    else:
        record.parent.parent.mkdir(parents=True, exist_ok=True)
        record.parent.write_text("i am a file where a directory is expected", encoding="ascii")

    usable, why = rsp.answered_usable(record)
    assert usable is False, f"{shape} was called usable"
    assert why and "answered record" in why, why
    assert rsp._remember_answered(record, "d.md") is False, (
        f"{shape} reported a recorded answer that is not on disk anywhere"
    )


def test_the_answered_usable_reason_never_carries_a_raw_error_string(rsp, tmp_path):
    """`CLAUDE.md` forbids a raw API or error string on a user-facing surface.

    These reasons are printed by the responder and reach `result["reasons"]`,
    which `record_cycle` writes into the metrics ledger. `_listed_record`'s
    docstring states the same rule for the same records. At most a class NAME,
    and never `str(exc)` - a filesystem error message on Windows carries the
    absolute path, which is the account-shaped path `validate_draft` refuses to
    let out of this repo.
    """
    record = tmp_path / "structural" / "responder_answered.json"
    record.mkdir(parents=True)

    for path in (record, tmp_path / "absent" / "responder_answered.json"):
        _usable, why = rsp.answered_usable(path)
        assert str(tmp_path) not in why, f"the reason leaked a filesystem path: {why}"
        assert "Error" not in why or why.endswith(")"), why
        assert "\n" not in why and "\t" not in why, why


def test_an_absent_answered_record_still_records_the_first_name(rsp, tmp_path):
    """THE NEIGHBOUR THAT HAD TO SURVIVE on the answered record too."""
    record = tmp_path / "absent" / "responder_answered.json"
    assert not record.exists()

    assert rsp._remember_answered(record, "first.md") is True
    assert rsp._answered(record) == {"first.md"}


def test_a_readable_answered_record_is_a_union_and_not_a_rewrite(rsp, tmp_path):
    """The ordinary path: prior names survive, which is what `union` has to mean."""
    record = tmp_path / "responder_answered.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"version": 1, "answered": ["a.md", "b.md"]}), encoding="utf-8")

    assert rsp._remember_answered(record, "c.md") is True
    assert rsp._answered(record) == {"a.md", "b.md", "c.md"}


def test_the_reading_path_still_degrades_to_empty_for_its_reading_caller(rsp, tmp_path):
    """`_answered` DELIBERATELY still answers empty on an unreadable record.

    THIS ARM IS GREEN ON BOTH SIDES OF THE FIX AND IS STILL THE POINT. Its job
    is to pin the SPLIT, so that a later reader cannot "finish the fix" by
    tightening the wrong half. Making this function raise would take an
    unattended cycle down on a corrupt runtime file and surface nothing at all.

    THE BOUND IS THE WRITER OVERWRITING, NOT THE WRITER REFUSING, and the first
    version of this docstring had that exactly backwards. A degraded read here
    makes an already-answered note look eligible, and what makes that cost ONE
    duplicate rather than one per cycle forever is that `_remember_answered`
    then REWRITES the record so the very next read succeeds. The arm above
    carries the arithmetic.

    The structural classes are not bounded by anything the writer can do, so
    they are stopped one level up - `_run_once` declines the cycle. That is the
    arm named `test_a_structurally_unreadable_answered_record_answers_nothing`.

    Falsified by: any change that makes the reader raise, or that makes it
    report names it could not read.
    """
    record = tmp_path / "responder_answered.json"
    _seed_unreadable(record, {"version": 1, "answered": ["a.md", "b.md"]})

    assert rsp._answered(record) == set(), (
        "the reading half changed behaviour, which is out of scope here and is "
        "under a separate decision"
    )

    inbox = tmp_path / "moon_sync_inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    # `pending` is the real consumer, and it must still run rather than raise.
    assert rsp.pending(inbox, rsp.OPTED_IN, rsp._answered(record)) == []


# --------------------------------------------------------------------------
# ITEM C - `_trim_invocations`, the encoding mismatch
# --------------------------------------------------------------------------


def test_three_fires_over_an_undecodable_byte_do_not_grow_the_ledger(rsp):
    """BYTE STABILITY ACROSS REPEATED FIRES. One bad byte tripled per fire.

    Read as ascii/replace the byte arrives as one U+FFFD; written by
    `atomic_write_text` as UTF-8 it leaves as three bytes; read back it is three
    replacement characters and leaves as nine. Falsified by the pre-fix code on
    the second fire, which is why one fire is not enough to see it - a single
    call cannot tell a stable rewrite from the first step of a compounding one.
    """
    count, width = _over_bytes_under_lines(rsp)
    body = "\n".join(_line(i, width) for i in range(count))
    rsp.DEFAULT_INVOCATIONS.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_INVOCATIONS.write_bytes(body.encode("ascii") + BAD_BYTE)

    sizes = []
    for _ in range(3):
        rsp._trim_invocations()
        sizes.append(rsp.DEFAULT_INVOCATIONS.stat().st_size)

    assert sizes[0] == sizes[1] == sizes[2], (
        f"the ledger grew across fires: {sizes} - one undecodable byte is being "
        "re-expanded threefold every time the trim runs"
    )
    raw = rsp.DEFAULT_INVOCATIONS.read_bytes()
    assert REPLACEMENT_BYTES not in raw, (
        "a replacement character survived the write, so the next fire triples it"
    )
    assert b"?" in raw, "the undecodable byte was dropped rather than folded to ASCII"


def test_the_fold_does_not_destroy_the_lines_around_the_bad_byte(rsp):
    """THE SURVIVAL GUARD. A fold that deleted the mangled line would pass above.

    The arm above is satisfied by any function that makes the file stop growing,
    including one that throws the whole line away. This one pins the legitimate
    neighbours: every line the fixture wrote is still there afterwards, and the
    count is unchanged.
    """
    count, width = _over_bytes_under_lines(rsp)
    body = "\n".join(_line(i, width) for i in range(count))
    rsp.DEFAULT_INVOCATIONS.parent.mkdir(parents=True, exist_ok=True)
    # The bad byte goes INSIDE a middle line, not at the end of the file, so the
    # damage is to a line that has neighbours on both sides.
    raw = body.encode("ascii")
    cut = raw.index(b"seq00000010")
    rsp.DEFAULT_INVOCATIONS.write_bytes(raw[:cut] + BAD_BYTE + raw[cut:])

    rsp._trim_invocations()

    text = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == count, (len(lines), count)
    assert "seq00000009" in text and "seq00000011" in text, (
        "the neighbours of the mangled line were destroyed by the fold"
    )
    assert "seq00000010" in text, "the mangled line itself was discarded rather than folded"


def test_a_clean_ledger_under_both_caps_is_still_left_alone(rsp):
    """The fold must not turn the `stat` guard into a read. Nothing fires here."""
    rsp.DEFAULT_INVOCATIONS.parent.mkdir(parents=True, exist_ok=True)
    # No trailing newline, which the trim's own join can never produce - so "was
    # this file rewritten at all" has a byte-level yes-or-no answer.
    rsp.DEFAULT_INVOCATIONS.write_bytes(b"2026-01-01T00:00:00\tcli\t-\tstart")
    before = _sha256(rsp.DEFAULT_INVOCATIONS)

    rsp._trim_invocations()

    assert _sha256(rsp.DEFAULT_INVOCATIONS) == before


# --------------------------------------------------------------------------
# ITEM D - the bounded rotate
# --------------------------------------------------------------------------


def _seed_live(rsp, metrics: Path, count: int, prefix: str = "old") -> None:
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(
        json.dumps({"version": 1, "cycles": _rows(count, prefix)}), encoding="utf-8"
    )


def _all_text_under(root: Path) -> str:
    """Every readable byte anywhere under `root`, concatenated.

    Borrowed from `tests/test_responder_invocation_trim.py`, which uses it for
    the opposite verdict. It asks whether a dropped row went ANYWHERE, not merely
    whether it left the live ledger - and that distinction is the whole finding,
    because asserting only the second cannot tell a rotate from a trim.
    """
    chunks = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            chunks.append(path.read_text(encoding="ascii", errors="replace"))
    return "\n".join(chunks)


def test_the_dropped_row_still_exists_somewhere_under_the_ledger_directory(rsp, tmp_path):
    """THE BEHAVIOUR-ONLY ARM FOR THE CAP. It names no new symbol at all.

    Deliberately separate from the arms below, which reach for `_rotation_path`
    and therefore go red on the pre-fix code with an `AttributeError` - red for
    the right defect but by the absence of an API rather than by a measurement.
    This one asks only the question the defect is about: after the cap fires, is
    the dropped row anywhere on disk? Pre-fix the answer was no, and the arm
    would stay red against any repair that dropped the row under a different
    name than the one below expects.
    """
    cap = rsp.MAX_METRICS_ROWS
    ledgers = tmp_path / "ledgers"
    metrics = ledgers / "responder_metrics.json"
    _seed_live(rsp, metrics, cap)

    assert rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    ) is True

    live = json.loads(metrics.read_text(encoding="utf-8"))["cycles"]
    assert [r["note"] for r in live][0] == "old00001.md", (
        "the cap did not fire, so this arm is measuring nothing"
    )
    assert "old00000.md" in _all_text_under(ledgers), (
        "the row the cap dropped is nowhere on disk - the oldest evidence in the "
        "trial was destroyed by the arrival of one row"
    )


def test_rows_beyond_the_cap_are_recoverable_from_the_rotation_file(rsp, tmp_path):
    """The overflow goes SOMEWHERE. Falsified by the pre-fix bare slice.

    Pre-fix, `rows = rows[-MAX_METRICS_ROWS:]` wrote the dropped rows nowhere and
    said nothing, so the oldest evidence in the trial left the tree at the 501st
    row. Asserting only that the live ledger no longer holds them cannot tell a
    rotate from a trim, and telling those apart is the whole point.
    """
    cap = rsp.MAX_METRICS_ROWS
    metrics = tmp_path / "responder_metrics.json"
    _seed_live(rsp, metrics, cap)

    for i in range(3):
        assert rsp.record_cycle(
            metrics, f"new{i}.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
        ) is True

    live = json.loads(metrics.read_text(encoding="utf-8"))["cycles"]
    assert len(live) == cap, len(live)
    assert [r["note"] for r in live[-3:]] == ["new0.md", "new1.md", "new2.md"], live[-3:]

    rotation = rsp._rotation_path(metrics)
    assert rotation.is_file(), (
        f"nothing was archived at {rotation.name}; the cap is still a bare drop"
    )
    archived = [r["note"] for r in json.loads(rotation.read_text(encoding="utf-8"))["cycles"]]
    assert archived == ["old00000.md", "old00001.md", "old00002.md"], archived


def test_the_rotation_file_is_bounded_at_the_same_cap(rsp, tmp_path):
    """BOUNDED IS THE AUTHORISED SHAPE. An unbounded archive was not authorised.

    The whole document is re-serialized on every write, so an archive that grew
    forever would reproduce the quadratic-bytes defect the cap exists to close.
    The archive therefore carries the NEWEST overflow rows up to `cap` and drops
    beyond it, holding total on-disk rows at `2 * cap` for any number of cycles.
    """
    cap = rsp.MAX_METRICS_ROWS
    metrics = tmp_path / "responder_metrics.json"
    _seed_live(rsp, metrics, cap)
    rotation = rsp._rotation_path(metrics)
    rotation.write_text(
        json.dumps({"version": 1, "cycles": _rows(cap, "arc")}), encoding="utf-8"
    )

    assert rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    ) is True

    archived = [r["note"] for r in json.loads(rotation.read_text(encoding="utf-8"))["cycles"]]
    assert len(archived) == cap, (
        f"the archive holds {len(archived)} rows against a cap of {cap}; it is unbounded"
    )
    assert archived[0] == "arc00001.md", archived[0]
    assert archived[-1] == "old00000.md", (
        "the row that just fell off the live ledger did not reach the archive"
    )


def test_a_failing_rotate_leaves_the_live_ledger_complete_not_short(rsp, tmp_path):
    """A FAILED ROTATE MUST NOT SILENTLY BECOME A TRIM.

    The rotation path is made a DIRECTORY, so `read_json` cannot read it and the
    archive is refused rather than replaced. The refusal has to propagate BEFORE
    the live ledger is touched, because a caller told True about rows that went
    nowhere is worse off than one told nothing at all.

    Falsified by the pre-fix code, which trimmed unconditionally and returned
    True, and by any rotate ordered live-file-first.
    """
    cap = rsp.MAX_METRICS_ROWS
    metrics = tmp_path / "responder_metrics.json"
    _seed_live(rsp, metrics, cap + 5)
    before = _sha256(metrics)
    rsp._rotation_path(metrics).mkdir(parents=True, exist_ok=True)

    landed = rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    )

    assert landed is False, "a rotate that could not archive anything reported success"
    assert _sha256(metrics) == before, (
        "the live ledger was rewritten after the rotate failed, so the failed "
        "rotate became a trim"
    )
    live = json.loads(metrics.read_text(encoding="utf-8"))["cycles"]
    assert len(live) == cap + 5, (
        f"the live ledger is short: {len(live)} rows where {cap + 5} were on disk"
    )


def test_an_unreadable_rotation_file_is_refused_rather_than_replaced(rsp, tmp_path):
    """The archive gets the same ABSENT-versus-UNREADABLE split as the live file."""
    cap = rsp.MAX_METRICS_ROWS
    metrics = tmp_path / "responder_metrics.json"
    _seed_live(rsp, metrics, cap)
    rotation = rsp._rotation_path(metrics)
    _seed_unreadable(rotation, {"version": 1, "cycles": _rows(2, "arc")})
    before = _sha256(rotation)

    assert rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    ) is False
    assert _sha256(rotation) == before
    assert b"arc00000.md" in rotation.read_bytes()


def test_a_ledger_under_the_cap_creates_no_rotation_file(rsp, tmp_path):
    """THE SURVIVAL GUARD FOR THE ROTATE. It fires at the cap and not before.

    A rotate that wrote an archive on every cycle would satisfy every arm above
    and would double the bytes written per tick for a trial that never reaches
    the cap - which, measured 2026-09-08 at 100 cycles, is every trial so far.
    """
    metrics = tmp_path / "responder_metrics.json"
    _seed_live(rsp, metrics, rsp.MAX_METRICS_ROWS - 1)

    assert rsp.record_cycle(
        metrics, "new.md", 0, 0.0, 1.0, 1.0, [], False, ["r"], "refused"
    ) is True

    assert not rsp._rotation_path(metrics).exists(), (
        "an archive was written by a cycle that dropped nothing"
    )
    assert len(json.loads(metrics.read_text(encoding="utf-8"))["cycles"]) == rsp.MAX_METRICS_ROWS


# --------------------------------------------------------------------------
# The arm that keeps the fixtures honest
# --------------------------------------------------------------------------


def test_the_byte_cap_is_read_from_the_module_and_is_not_retyped_here(rsp):
    """No cap's digits appear in this file's own source.

    A fixture sized from a retyped literal agrees with a number this file
    invented rather than with the module, and it would stay green through a
    constant change that broke the caller. The match is WORD-ANCHORED rather
    than a substring test, because a three-digit cap is a substring of half the
    round numbers a fixture might legitimately use.
    """
    source = Path(__file__).read_text(encoding="ascii")
    for name in ("MAX_INVOCATION_BYTES", "MAX_INVOCATION_LINES", "MAX_METRICS_ROWS"):
        digits = str(getattr(rsp, name))
        assert re.search(rf"(?<![\w_]){re.escape(digits)}(?![\w_])", source) is None, (
            f"{name} is spelled as {digits} in this file instead of being read "
            f"from the module"
        )


# --------------------------------------------------------------------------
# ITEM E - THE MULTI-CYCLE ARM. NO TRACKED ARM ANYWHERE DROVE MORE THAN ONE
# CYCLE OVER A POISONED ANSWERED RECORD, AND A SINGLE-CYCLE ARM STRUCTURALLY
# CANNOT SEE THIS DEFECT.
#
# Every multi-cycle `_drive` arm in `tests/test_moon_sync_responder.py` targets
# `DEFAULT_REFUSALS`. The answered record had unit-level arms on its writer and
# nothing at all on the CYCLE, so the question "how many replies does a poisoned
# answered record put in somebody else's inbox" had never been asked of a real
# `run_once`. One cycle answers a note once whatever the record says. The defect
# is entirely in what cycle TWO does, which is why these arms drive three.
#
# Both arms count FILES IN THE DESTINATION INBOX. A gate proved as a pure
# predicate is not an enforced gate, and this module's own suite records being
# bitten by that three times.
# --------------------------------------------------------------------------

#: A wall-clock minute apart is not enough: three cycles in one test run land in
#: the same real minute. Stepping the INJECTED clock keeps the arms honest about
#: ordering without pretending the reply NAME moved - see `_unique_reply_names`.
CYCLE_STEP_SECONDS = 60.0

#: A start epoch well clear of the ones the sibling suite uses, so a shared
#: `tmp_path` collision would be visible rather than coincidental.
CYCLE_EPOCH = 90_000.0


def _agree(rsp) -> None:
    """Record the counterparty's agreement, as the operator would.

    Written EXPLICITLY by the arms rather than by the fixture, which is the
    convention `tests/test_moon_sync_responder.py` records: a fixture that
    pre-agreed would make the arms pass whether or not the gate existed.
    """
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999}),
        encoding="ascii",
    )


def _answer_bed(rsp, tmp_path):
    """An agreed, armed setup with ONE note that will pass the output gate.

    The mirror of `_refusal_bed` in the sibling suite, pointed the other way: its
    draft is refused on purpose, this one is DELIVERED on purpose, because the
    answered record is only ever written on the delivered branch.
    """
    _agree(rsp)
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "2026-09-10-1900-from-RC-question.md").write_bytes(
        b"please measure your suite\n"
    )
    far_inbox = tmp_path / "rc" / "moon_sync_inbox"
    far_inbox.mkdir(parents=True, exist_ok=True)
    return inbox, far_inbox


def _unique_reply_names(rsp, monkeypatch) -> None:
    """Make each cycle's reply name distinct, and the reason is load bearing.

    `_reply_name` stamps `time.strftime("%Y-%m-%d-%H%M")` off the WALL CLOCK,
    never off the injected `now`, so three cycles inside one test run ask
    `deliver` to write the SAME filename. `deliver` refuses to overwrite, so the
    second and third replies silently do not land and the destination inbox
    holds one file whether the responder decided to answer once or three times.

    A file count taken without this patch is therefore an arm that CANNOT FAIL -
    green on both sides of the defect it was written to catch, which is this
    tree's most-measured failure mode. Production cycles are five minutes apart
    and the names DO differ, so the patch restores the production observation
    rather than inventing one. Nothing under test is touched: the count being
    measured is how many times the responder DECIDES to answer.

    THE NAME KEEPS THE REAL `from-<SELF_CODE>-` PREFIX, AND THAT IS NOT
    COSMETIC. `deliver` writes our own copy back into the LOCAL inbox, so a
    reply whose filename parses to an OPTED-IN sender becomes eligible responder
    input and the next cycle answers the reply. Measured while writing these
    arms with a bare `reply-N-to-<stem>` name: cycle two delivered
    `reply-2-to-reply-1-to-...`, a responder answering itself. `_reply_name`
    stamps `from-RSC-` AHEAD of the quoted stem for exactly this reason and
    `_SENDER` takes the first match, so the patch has to keep that ordering or
    it measures a loop it invented rather than the one under test.
    """
    seen: list[str] = []

    def _named(note):
        seen.append(note.name)
        return f"c{len(seen)}-from-{rsp.SELF_CODE}-auto-reply-to-{note.stem[:40]}.md"

    monkeypatch.setattr(rsp, "_reply_name", _named)


def _drive_answers(rsp, tmp_path, inbox, n):
    """`n` armed cycles whose draft PASSES the gate. `n` is always a literal."""
    draft = rsp.RESPONDER_TAG + "\n\nmeasured, and here are the numbers.\n"
    return [
        rsp.run_once(
            inbox=inbox,
            roots={"RC": tmp_path / "rc"},
            bounds=rsp.Bounds(armed=True),
            spawn=lambda *a, **k: draft,
            now=CYCLE_EPOCH + CYCLE_STEP_SECONDS * i,
        )
        for i in range(n)
    ]


def _delivered_files(far_inbox: Path) -> list[str]:
    return sorted(p.name for p in far_inbox.iterdir())


@pytest.mark.parametrize(
    "poison",
    ["{not json", "", "[]", '{"answered": "not a list"}'],
    ids=["corrupt", "empty", "wrong-top-type", "wrong-rows-type"],
)
def test_a_replaceable_answered_record_still_answers_and_self_heals(
    rsp, tmp_path, monkeypatch, poison
):
    """THREE CYCLES, ONE DELIVERY. The record repairs itself on the first one.

    This is the arm that was missing, and the one that fails against a writer
    that refuses a replaceable record. Against such a writer the record never
    becomes readable, `_answered` stays empty, `pending` keeps reporting the same
    note, and every cycle delivers again: THREE deliveries here and one per tick
    forever in production, into a repository this one does not own.

    It is also the non-vacuity arm for the structural one below. A responder that
    simply stopped answering whenever its answered record was scrambled would
    pass that arm and fail this one, and stopping is exactly what the
    counterparty complained about in the first place.
    """
    inbox, far_inbox = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)
    rsp.DEFAULT_ANSWERED.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_ANSWERED.write_text(poison, encoding="utf-8")

    results = _drive_answers(rsp, tmp_path, inbox, 3)

    landed = _delivered_files(far_inbox)
    assert len(landed) == 1, (
        f"a replaceable answered record delivered {len(landed)} replies into a "
        f"sibling's inbox: {landed}. One per cycle, forever, is the shape"
    )
    assert results[0]["delivered"] is True, results[0]
    assert results[0]["termination"] == "delivered", results[0]
    assert [r["termination"] for r in results[1:]] == ["empty", "empty"], (
        "the note was still eligible after being answered, so the answered "
        "record did not heal"
    )
    assert rsp._answered(rsp.DEFAULT_ANSWERED) == {"2026-09-10-1900-from-RC-question.md"}


def test_a_structurally_unreadable_answered_record_answers_nothing(
    rsp, tmp_path, monkeypatch
):
    """THREE CYCLES, ZERO DELIVERIES, because no write can ever repair this.

    A non-empty DIRECTORY at the record path - the same plausible botched-restore
    state the refusal record's arm uses, and non-empty so `Path.replace` cannot
    quietly win. Here overwriting is not on offer: `atomic_write_json` cannot
    land, so the record stays unreadable however many times the writer tries.
    The bound the replaceable case relies on does not exist, and the reader's
    degrade-to-empty therefore hands `pending` the same note every cycle
    forever.

    So the READER fails closed for this class only: the cycle declines to answer
    at all and says why. Zero files in the far inbox is the load-bearing
    assertion - this repo's own mess is its own problem, the other repo's is not.

    Measured against the pre-change bytes: 3 cycles, 3 deliveries, terminating
    `delivered` every time with nothing surfaced anywhere.
    """
    inbox, far_inbox = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)
    rsp.DEFAULT_ANSWERED.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_ANSWERED.mkdir()
    (rsp.DEFAULT_ANSWERED / "keep.txt").write_text(
        "not empty, so replace cannot win", encoding="ascii"
    )

    results = _drive_answers(rsp, tmp_path, inbox, 3)

    assert _delivered_files(far_inbox) == [], (
        f"an unrecordable answer delivered {len(_delivered_files(far_inbox))} "
        "replies into a sibling's inbox. A reply that cannot be recorded is a "
        "reply that will be sent again on every cycle forever"
    )
    assert len(results) == 3, "a cycle raised instead of returning"
    assert all(r["delivered"] is False for r in results), results
    assert all(r["termination"] == rsp.TERMINATION_UNANSWERABLE for r in results), (
        [r["termination"] for r in results]
    )
    assert rsp.TERMINATION_UNANSWERABLE in rsp.TERMINATIONS
    assert rsp.TERMINATION_UNANSWERABLE != "unrecordable", (
        "the answered-record refusal is wearing the refusal record's termination, "
        "so an operator reading the log cannot tell which record is broken"
    )
    assert all(r["reasons"] for r in results), (
        "the cycle declined and said nothing about why"
    )


def test_the_declined_cycle_reaches_the_invocation_log_with_its_own_reason(
    rsp, tmp_path, monkeypatch
):
    """A gate that returns early must still be VISIBLE, or it is a silent stop.

    Four terminations in this module were once proven by arms asserting a return
    value and none of them reached the log. `run_once` writes the terminal line
    whatever the body did, so the assertion is on the FILE.
    """
    inbox, _far = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)
    rsp.DEFAULT_ANSWERED.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_ANSWERED.mkdir()

    result = _drive_answers(rsp, tmp_path, inbox, 1)[0]

    lines = [ln for ln in rsp.DEFAULT_INVOCATIONS.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "a declined cycle left no record at all"
    assert lines[-1].split("\t")[-1] == result["termination"], (
        f"log ends on {lines[-1]!r} but the cycle terminated {result['termination']!r}"
    )


def test_an_absent_answered_record_answers_normally_on_a_cold_start(
    rsp, tmp_path, monkeypatch
):
    """ABSENT IS NOT AN ERROR, AND THIS IS THE STATE THE MACHINE IS IN NOW.

    `ops/runtime/responder_answered.json` does not exist on disk in this repo -
    measured 2026-09-10 - so a cold start is the ORDINARY case and not an edge.
    A reader gate that treated absent as unusable would decline every cycle
    forever and the channel would never open at all, which is a worse failure
    than the one the gate is for and it would look identical in the log.

    This is the neighbour the sweep had to leave alive, and without it the
    structural arm above passes on a responder that answers nothing ever.
    """
    inbox, far_inbox = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)
    assert not rsp.DEFAULT_ANSWERED.exists()

    results = _drive_answers(rsp, tmp_path, inbox, 2)

    assert len(_delivered_files(far_inbox)) == 1, _delivered_files(far_inbox)
    assert results[0]["termination"] == "delivered", results[0]
    assert results[1]["termination"] == "empty", results[1]
    assert rsp._answered(rsp.DEFAULT_ANSWERED) == {"2026-09-10-1900-from-RC-question.md"}


def test_a_failed_answered_write_is_reported_rather_than_discarded(
    rsp, tmp_path, monkeypatch
):
    """THE RETURN VALUE WAS THROWN AWAY AT THE CALL SITE, AND THAT IS WHY THE
    DUPLICATE LOOP WOULD HAVE BEEN SILENT.

    `_run_once` called `_remember_answered(DEFAULT_ANSWERED, note.name)` as a
    bare statement. A False reached neither `result`, nor `record_cycle`'s
    reasons column, nor the invocation log, so a responder re-answering one note
    every five minutes produced a log of perfectly ordinary `delivered` lines.

    THE FAILURE IS INJECTED AT THE CALL SITE DELIBERATELY. Every structural way
    to make the write fail for real is now stopped by the reader gate one level
    up, which is the point of that gate; what remains is a race - the record
    replaced between the gate and the write - and no arm can schedule that. So
    this arm asks the one question it can answer honestly: does the call site
    OBSERVE the return. The real-write behaviour is pinned by the arms above.
    """
    inbox, far_inbox = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)
    monkeypatch.setattr(rsp, "_remember_answered", lambda *a, **k: False)

    result = _drive_answers(rsp, tmp_path, inbox, 1)[0]

    assert len(_delivered_files(far_inbox)) == 1, "the reply did not go out at all"
    assert result["delivered"] is True, result
    assert rsp.ANSWERED_NOT_RECORDED in result["reasons"], (
        f"a delivered-but-unrecorded reply reported {result['reasons']!r}; the "
        "next cycle will answer the same note again and nothing says so"
    )

    rows = json.loads(rsp.DEFAULT_METRICS.read_text(encoding="utf-8"))["cycles"]
    assert rows, "no metrics row was written for the delivered cycle"
    assert rsp.ANSWERED_NOT_RECORDED in rows[-1]["reasons"], (
        f"the cycle row hid it: {rows[-1]}"
    )


def test_a_recorded_answer_adds_no_reason_at_all(rsp, tmp_path, monkeypatch):
    """THE NON-VACUITY ARM FOR THE ONE ABOVE.

    A call site that appended that reason unconditionally would pass the arm
    above and would put a permanent false alarm in every delivered cycle's row.
    """
    inbox, _far = _answer_bed(rsp, tmp_path)
    _unique_reply_names(rsp, monkeypatch)

    result = _drive_answers(rsp, tmp_path, inbox, 1)[0]

    assert result["delivered"] is True, result
    assert result["reasons"] == [], result["reasons"]
    rows = json.loads(rsp.DEFAULT_METRICS.read_text(encoding="utf-8"))["cycles"]
    assert rows[-1]["reasons"] == [], rows[-1]
