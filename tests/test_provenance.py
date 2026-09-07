"""The row-scoped provenance contract - written FAILING FIRST.

WHAT THIS FILE IS FOR, stated once so nobody has to reconstruct it.

Every value that lands in `data/` must carry the artefact it was read from,
that artefact's sha256, and HOW it was read. Three episodes in the 2026-09-07
capture session are the reason, and each one has an arm below:

1. A single account fact was described as "read four ways". Two of those four
   were pixel reads of ONE crop. Two reads of one source are ONE fact, and the
   count has to be ARITHMETIC rather than an author remembering to say so.
2. Tesseract returned a confident ZERO on a splash reading "Obtained New
   Character" with the text plainly on screen. An OCR row and an eye row are
   different evidence classes, and a consumer is entitled to know that a zero
   came only from machines before it reads that zero as an absence.
3. A character was recorded as a trial character on two numbers merely
   "consistent with" the hypothesis, and operator testimony later refuted it.
   Two consistent numbers are not two facts.

THE CHECKED-COUNT RULE. Every checker returns `(checked, offenders)` and every
test here asserts the CHECKED COUNT before it looks at the offender list. Zero
out of zero reads as a pass, and this tree already refuses that -
`tests/test_guard_worktree_blindness.py` and `tests/test_mypy_scope.py` both
make the same move.

ACCOUNT SAFETY. No account value appears anywhere in this file. Every digest is
a repeated hex character, every locator is invented, and the forbidden-key arms
name FIELD NAMES only. The real capture store lives outside the tree on
purpose.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.provenance import (
    EVIDENCE_CLASS,
    PROVENANCE_SCHEMA_VERSION,
    DataRow,
    EvidenceClass,
    ObservationStatus,
    ProvenanceError,
    ProvenanceRecord,
    ReadMethod,
    SamplingRef,
    SourceKind,
    SourceRef,
    check_evidence_class_totality,
    check_rows,
    coverage_notes,
    coverage_ratio,
    evidence_class,
    independent_witnesses,
    is_absence_claim,
    read_rows,
    render_source,
    supporting_records,
    sweep_data_dir,
    validate_row,
    witness_key,
    witness_report,
    write_rows,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "core" / "provenance.py"

#: Digests are 64 lowercase hex characters. Repeated characters keep them
#: obviously invented while staying legal, so no arm below can be mistaken for
#: a real artefact digest.
SHA_FRAME = "a" * 64
SHA_CROP = "b" * 64
SHA_CROP_TWO = "c" * 64
SHA_UID_FILE = "d" * 64
SHA_DIR_NAME = "e" * 64
SHA_FRAME_TWO = "f" * 64
SHA_FRAME_THREE = "0" * 63 + "1"

WHEN = "2026-09-07T10:00:25Z"


# ---------------------------------------------------------------------------
# Builders. Every arm below constructs from these so that a change to a shared
# default cannot make one arm quietly stop testing what it says it tests.
# ---------------------------------------------------------------------------


def _source(
    kind: SourceKind = SourceKind.CROP,
    locator: str = "evidence/detail_crop.png",
    sha256: str = SHA_CROP,
    **kwargs: object,
) -> SourceRef:
    return SourceRef(kind=kind, locator=locator, sha256=sha256, captured_utc=WHEN, **kwargs)  # type: ignore[arg-type]


def _record(
    record_id: str = "rec-1",
    claim: str = "the detail pane reads level 20",
    read_method: ReadMethod = ReadMethod.HUMAN_EYE,
    source: SourceRef | None = None,
    status: ObservationStatus = ObservationStatus.VERIFIED,
    reader: str = "human",
    **kwargs: object,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        record_id=record_id,
        claim=claim,
        read_method=read_method,
        source=_source() if source is None else source,
        observed_utc=WHEN,
        status=status,
        reader=reader,
        **kwargs,  # type: ignore[arg-type]
    )


def _row(*records: ProvenanceRecord, **kwargs: object) -> DataRow:
    payload = kwargs.pop("payload", {"level": 20})
    return DataRow(
        row_id=kwargs.pop("row_id", "row-1"),  # type: ignore[arg-type]
        table=kwargs.pop("table", "roster"),  # type: ignore[arg-type]
        key=kwargs.pop("key", "slot-1"),  # type: ignore[arg-type]
        payload=payload,  # type: ignore[arg-type]
        provenance=records or (_record(),),
        **kwargs,  # type: ignore[arg-type]
    )


def _vision_read_of_the_crop() -> ProvenanceRecord:
    return _record(
        record_id="vision",
        read_method=ReadMethod.VISION_MODEL,
        reader="vision-model",
        source=_source(parent_sha256=SHA_FRAME),
    )


def _ocr_read_of_the_same_crop() -> ProvenanceRecord:
    return _record(
        record_id="ocr",
        read_method=ReadMethod.OCR,
        reader="pytesseract psm7",
        source=_source(parent_sha256=SHA_FRAME),
    )


def _game_written_file() -> ProvenanceRecord:
    return _record(
        record_id="game-file",
        read_method=ReadMethod.GAME_BYTES,
        reader="filesystem",
        source=_source(kind=SourceKind.FILE, locator="game/info.txt", sha256=SHA_UID_FILE),
    )


def _noelle_sampling() -> tuple[SamplingRef, ...]:
    """The measured shape of the gap: one frame in fifteen was examined."""
    return (
        SamplingRef(
            corpus="video frames",
            native_rate_hz=15.0,
            examined_rate_hz=1.0,
            examined_count=1384,
            population_count=0,
            window_start_utc="2026-09-07T09:20:44Z",
            window_end_utc="2026-09-07T09:42:59Z",
        ),
        SamplingRef(
            corpus="screenshots",
            native_rate_hz=0.25,
            examined_rate_hz=0.25,
            examined_count=1328,
            population_count=1328,
            window_start_utc="2026-09-07T09:20:44Z",
            window_end_utc="2026-09-07T09:42:59Z",
        ),
    )


def _not_found_record(**kwargs: object) -> ProvenanceRecord:
    defaults: dict[str, object] = {
        "record_id": "gap",
        "claim": "the roster gained no character in this window",
        "read_method": ReadMethod.OCR,
        "reader": "pytesseract psm7",
        "source": _source(kind=SourceKind.VIDEO_SEGMENT, locator="recordings/session.mkv", sha256=SHA_FRAME),
        "status": ObservationStatus.NOT_FOUND,
        "sampling": _noelle_sampling(),
    }
    defaults.update(kwargs)
    return _record(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1-6: shape and refusal
# ---------------------------------------------------------------------------


def test_a_row_with_no_provenance_is_refused():
    """A value with no receipt is the whole thing this schema exists to stop."""
    row = DataRow(row_id="row-1", table="roster", key="slot-1", payload={"level": 20}, provenance=())
    with pytest.raises(ProvenanceError) as caught:
        validate_row(row)
    assert "provenance" in str(caught.value), (
        f"the refusal must name the field a reader has to fix: {caught.value}"
    )


@pytest.mark.parametrize(
    ("label", "digest"),
    [
        ("uppercase hex", "A" * 64),
        ("a 40-character sha1", "a" * 40),
        ("empty on a non-testimony source", ""),
        ("not hex at all", "z" * 64),
        ("65 characters", "a" * 65),
    ],
)
def test_a_digest_that_is_not_64_lowercase_hex_is_refused(label: str, digest: str):
    """The digest is what makes two reads of one artefact computably one fact.

    A digest in a shape nothing produces is a digest nobody can re-derive, so
    the field would be decoration.
    """
    with pytest.raises(ProvenanceError):
        validate_row(_row(_record(source=_source(sha256=digest))))


def test_a_testimony_source_must_not_carry_a_digest():
    """Testimony has no bytes. A digest there is theatre."""
    testimony = _record(
        read_method=ReadMethod.OPERATOR_STATEMENT,
        reader="operator",
        source=_source(kind=SourceKind.TESTIMONY, locator="operator/statement", sha256=SHA_FRAME),
    )
    with pytest.raises(ProvenanceError):
        validate_row(_row(testimony))


def test_an_operator_statement_must_use_a_testimony_source():
    """The other direction of the same rule, and it is not implied by it."""
    mislabelled = _record(
        read_method=ReadMethod.OPERATOR_STATEMENT,
        reader="operator",
        source=_source(kind=SourceKind.FILE, locator="game/info.txt", sha256=SHA_UID_FILE),
    )
    with pytest.raises(ProvenanceError):
        validate_row(_row(mislabelled))


def test_a_testimony_record_with_no_digest_is_accepted():
    """ARM TWO. The rule above must not have deleted the legitimate case."""
    testimony = _record(
        read_method=ReadMethod.OPERATOR_STATEMENT,
        reader="operator",
        source=_source(kind=SourceKind.TESTIMONY, locator="operator/statement", sha256=""),
    )
    validate_row(_row(testimony))


def test_the_read_method_enum_has_exactly_the_declared_members():
    """Widening the enum becomes a deliberate edit rather than a drive-by."""
    assert {member.name for member in ReadMethod} == {
        "GAME_BYTES",
        "GAME_API",
        "HUMAN_EYE",
        "VISION_MODEL",
        "OCR",
        "OPERATOR_STATEMENT",
        "DERIVED",
    }
    assert {member.value for member in ReadMethod} == {
        "game_bytes",
        "game_api",
        "human_eye",
        "vision_model",
        "ocr",
        "operator_statement",
        "derived",
    }


def test_every_read_method_has_an_evidence_class():
    """CHECKED COUNT FIRST. A mapping that had stopped covering the enum would
    otherwise pass with an empty offender list forever."""
    checked, offenders = check_evidence_class_totality()
    assert checked == len(ReadMethod), (
        f"the totality check examined {checked} of {len(ReadMethod)} read methods; "
        "zero out of zero is not a pass"
    )
    assert not offenders, f"read methods with no evidence class: {offenders}"
    assert evidence_class(ReadMethod.OCR) is EvidenceClass.MACHINE_READ
    assert evidence_class(ReadMethod.GAME_BYTES) is EvidenceClass.GAME_AUTHORED
    assert evidence_class(ReadMethod.DERIVED) is EvidenceClass.NONE


def test_the_evidence_class_mapping_is_not_mutable():
    """A shared mapping a consumer can edit is not a contract."""
    with pytest.raises(TypeError):
        EVIDENCE_CLASS[ReadMethod.OCR] = EvidenceClass.GAME_AUTHORED  # type: ignore[index]


def test_a_data_row_is_never_hashable():
    """`payload` is a Mapping, so a set of rows would be a silent surprise."""
    with pytest.raises(TypeError):
        hash(_row())
    assert _row() == _row(), "equality is what the consumers need, and it must survive"


# ---------------------------------------------------------------------------
# 7-15: independence. This is the core of the schema.
# ---------------------------------------------------------------------------


def test_two_pixel_reads_of_one_crop_count_as_one_witness():
    """The episode this schema exists for. Both reads cite the SAME crop."""
    records = (_vision_read_of_the_crop(), _ocr_read_of_the_same_crop())
    assert independent_witnesses(records) == 1, (
        "two reads of one artefact are one fact; the count must be arithmetic, "
        "not an author remembering to say so"
    )


def test_the_games_own_bytes_are_a_second_witness():
    """Pixels and bytes agreeing IS corroboration. Two pixel reads are not."""
    pixels = (_vision_read_of_the_crop(), _ocr_read_of_the_same_crop())
    assert independent_witnesses(pixels + (_game_written_file(),)) == 2
    directory_name = _record(
        record_id="game-dir",
        read_method=ReadMethod.GAME_BYTES,
        reader="filesystem",
        source=_source(kind=SourceKind.FILE, locator="game/BeyondLocal", sha256=SHA_DIR_NAME),
    )
    assert independent_witnesses(pixels + (_game_written_file(), directory_name)) == 3


def test_two_crops_of_one_frame_are_still_one_witness():
    """The frame is the witness, not the rectangle cut out of it."""
    left = _record(record_id="left", source=_source(sha256=SHA_CROP, parent_sha256=SHA_FRAME))
    right = _record(record_id="right", source=_source(sha256=SHA_CROP_TWO, parent_sha256=SHA_FRAME))
    assert independent_witnesses((left, right)) == 1


def test_a_witness_group_collapses_two_frames_of_one_unchanged_screen():
    """The KNOWN LIMIT and its manual escape.

    Two different frames of one unchanged screen have different digests and
    would otherwise count twice. Perceptual similarity is a judgement, so the
    schema does not guess - it lets an author collapse them by name.
    """
    first = _record(
        record_id="frame-1",
        source=_source(kind=SourceKind.FRAME, locator="frames/a.png", sha256=SHA_FRAME_TWO, witness_group="roster-screen"),
    )
    second = _record(
        record_id="frame-2",
        source=_source(kind=SourceKind.FRAME, locator="frames/b.png", sha256=SHA_FRAME_THREE, witness_group="roster-screen"),
    )
    assert independent_witnesses((first, second)) == 1
    assert witness_key(first) == witness_key(second)


def test_two_frames_without_a_witness_group_count_twice():
    """ARM TWO for the collapse above. The escape must not be the default."""
    first = _record(record_id="frame-1", source=_source(kind=SourceKind.FRAME, locator="frames/a.png", sha256=SHA_FRAME_TWO))
    second = _record(record_id="frame-2", source=_source(kind=SourceKind.FRAME, locator="frames/b.png", sha256=SHA_FRAME_THREE))
    assert independent_witnesses((first, second)) == 2


def test_a_derived_record_is_never_a_witness():
    """A computation read nothing. It cannot corroborate its own inputs."""
    derived = _record(
        record_id="derived",
        read_method=ReadMethod.DERIVED,
        reader="core.provenance",
        source=_source(kind=SourceKind.TESTIMONY, locator="derived/from-prefix", sha256=""),
        derived_from=("game-file",),
        status=ObservationStatus.UNVERIFIED,
    )
    assert witness_key(derived) is None
    assert independent_witnesses((_game_written_file(), derived)) == 1


def test_a_derived_record_with_no_supporting_records_is_refused():
    """A derivation that names no inputs is an assertion wearing a receipt."""
    orphan = _record(
        record_id="derived",
        read_method=ReadMethod.DERIVED,
        reader="core.provenance",
        source=_source(kind=SourceKind.TESTIMONY, locator="derived/from-prefix", sha256=""),
        status=ObservationStatus.UNVERIFIED,
    )
    with pytest.raises(ProvenanceError) as caught:
        validate_row(_row(orphan))
    assert "derived_from" in str(caught.value)


def test_a_retracted_record_is_neither_a_witness_nor_support():
    """The trial-character episode, in arithmetic.

    One record, one witness, status UNVERIFIED - then testimony refutes it. The
    support set goes EMPTY, which is the honest answer, rather than the claim
    keeping the two numbers that never were two facts.
    """
    claim = "the character arrived as a trial character"
    retracted = _record(
        record_id="inference",
        claim=claim,
        status=ObservationStatus.RETRACTED,
        retracted_by="testimony",
        source=_source(parent_sha256=SHA_FRAME),
    )
    assert witness_key(retracted) is None
    assert independent_witnesses((retracted,)) == 0
    assert supporting_records((_row(retracted),), claim) == ()


def test_three_ocr_witnesses_are_reported_as_ocr_only():
    """The count alone was never the answer.

    Three distinct frames read by tesseract really are three witnesses. They
    are also three MACHINE_READ witnesses, and the consumer reading a zero as
    an absence is entitled to know that before it does.
    """
    records = tuple(
        _record(
            record_id=f"ocr-{n}",
            read_method=ReadMethod.OCR,
            reader="pytesseract psm7",
            source=_source(kind=SourceKind.FRAME, locator=f"frames/{n}.png", sha256=str(n) * 64),
        )
        for n in (1, 2, 3)
    )
    report = witness_report(records)
    assert report.witnesses == 3
    assert report.ocr_only is True
    assert report.single_class is True
    assert report.class_counts[EvidenceClass.MACHINE_READ] == 3
    assert len(report.keys) == 3


def test_a_mixed_report_is_not_ocr_only():
    """ARM TWO. The flag must distinguish, not simply always fire."""
    report = witness_report((_ocr_read_of_the_same_crop(), _game_written_file()))
    assert report.witnesses == 2
    assert report.ocr_only is False
    assert report.single_class is False


def test_supporting_records_are_enumerable_and_counted_first():
    """CHECKED COUNT FIRST, then the ids."""
    claim = "the detail pane reads level 20"
    vision = _vision_read_of_the_crop()
    game = _record(record_id="game-file", claim=claim, read_method=ReadMethod.GAME_BYTES, reader="filesystem",
                   source=_source(kind=SourceKind.FILE, locator="game/info.txt", sha256=SHA_UID_FILE))
    other = _record(record_id="unrelated", claim="a different claim entirely")
    found = supporting_records((_row(vision, game, other),), claim)
    assert len(found) == 2, f"expected two supporting records, got {len(found)}"
    assert [record.record_id for record in found] == ["vision", "game-file"], "file order must survive"


# ---------------------------------------------------------------------------
# 16-20: sampling. NOT FOUND AT 1 FPS IS NOT NOT PRESENT.
# ---------------------------------------------------------------------------


def test_a_not_found_row_without_a_sampling_rate_is_refused():
    """A negative is a claim about a SEARCH, and a search with no stated rate
    is unreportable. A refusal, not a warning nobody reads."""
    with pytest.raises(ProvenanceError) as caught:
        validate_row(_row(_not_found_record(sampling=())))
    assert "sampling" in str(caught.value)


def test_a_not_found_row_states_both_the_native_and_the_examined_rate():
    """The Noelle shape validates, and its own arithmetic contradicts anyone
    reading it as "she was not acquired in this window"."""
    record = _not_found_record()
    validate_row(_row(record))
    video = record.sampling[0]
    assert video.corpus == "video frames"
    assert coverage_ratio(video) == pytest.approx(1.0 / 15.0, abs=1e-9)
    assert coverage_ratio(record.sampling[1]) == pytest.approx(1.0, abs=1e-9)


def test_an_examined_rate_above_the_native_rate_is_refused():
    """Nobody examines frames that do not exist."""
    impossible = SamplingRef(
        corpus="video frames",
        native_rate_hz=15.0,
        examined_rate_hz=30.0,
        examined_count=10,
        population_count=0,
        window_start_utc="2026-09-07T09:20:44Z",
        window_end_utc="2026-09-07T09:42:59Z",
    )
    with pytest.raises(ProvenanceError):
        validate_row(_row(_not_found_record(sampling=(impossible,))))


def test_sampling_is_forbidden_on_a_single_file_read():
    """One artefact was read in full. A fabricated rate of 1.0 here is noise
    that makes a real rate harder to trust."""
    with pytest.raises(ProvenanceError):
        validate_row(_row(_record(
            record_id="game-file",
            read_method=ReadMethod.GAME_BYTES,
            reader="filesystem",
            source=_source(kind=SourceKind.FILE, locator="game/info.txt", sha256=SHA_UID_FILE),
            sampling=_noelle_sampling()[:1],
        )))


def test_a_measured_zero_is_not_a_not_found():
    """A surface that ANSWERED and answered none is not a sweep that found
    nothing, and only the second one is a claim about a search."""
    answered = _record(
        record_id="api",
        claim="the wish history holds no records",
        read_method=ReadMethod.GAME_API,
        reader="urllib",
        source=_source(kind=SourceKind.HTTP_RESPONSE, locator="responses/gacha_log.json", sha256=SHA_FRAME),
        status=ObservationStatus.MEASURED_ZERO,
    )
    validate_row(_row(answered))
    assert is_absence_claim(answered) is False
    assert is_absence_claim(_not_found_record()) is True


def test_an_absence_over_an_unknown_population_is_stamped_not_swallowed():
    """`population_count == 0` is allowed and is REPORTED, because a row
    asserting absence over an unknown population is not the same row as one
    asserting it over a counted one."""
    notes = coverage_notes(_not_found_record())
    assert any("coverage_unknown" in note for note in notes), notes
    assert any("video frames" in note for note in notes), notes


# ---------------------------------------------------------------------------
# 21-25: writing. Through core/atomic_io.py and nothing else.
# ---------------------------------------------------------------------------


def test_rows_are_written_through_atomic_io(tmp_path, monkeypatch):
    """One call, with the WHOLE body. A per-row call is a torn file waiting to
    be read by a poller."""
    calls: list[tuple[str, str]] = []

    def _recorder(path, text):  # type: ignore[no-untyped-def]
        calls.append((str(path), text))
        return True

    monkeypatch.setattr("core.provenance.atomic_write_text", _recorder)
    target = tmp_path / "roster.jsonl"
    assert write_rows(target, [_row(), _row(row_id="row-2")]) is True
    assert len(calls) == 1, f"atomic_write_text was called {len(calls)} times, not once"
    assert calls[0][1].count("\n") == 2, "the whole body must arrive in one call"


def test_the_module_never_opens_a_file_for_append():
    """Cheap, and it is the rule that actually matters.

    An append-mode open is banned outright: a reader polling mid-append sees a
    torn last line, which is exactly the failure core/atomic_io.py exists to
    prevent.
    """
    source = MODULE_PATH.read_text(encoding="utf-8")
    for call in re.findall(r"open\s*\([^)]*\)", source):
        assert not re.search(r"""["'][rwbtx+]*a[rwbtx+]*["']""", call), (
            f"core/provenance.py opens a file for append: {call}"
        )
    assert "atomic_write_text" in source, "the module must write through the sanctioned path"


def test_the_append_detector_fires_on_a_planted_call():
    """NON-VACUITY for the arm above. A detector never observed to fire and an
    absent defect look identical."""
    planted = 'with open(path, "a", encoding="utf-8") as handle:'
    hits = [
        call
        for call in re.findall(r"open\s*\([^)]*\)", planted)
        if re.search(r"""["'][rwbtx+]*a[rwbtx+]*["']""", call)
    ]
    assert hits, "the append detector does not recognise an append-mode open"


def test_a_failed_write_leaves_the_previous_file_intact(tmp_path, monkeypatch):
    target = tmp_path / "roster.jsonl"
    assert write_rows(target, [_row()]) is True
    before = target.read_bytes()

    monkeypatch.setattr("core.provenance.atomic_write_text", lambda path, text: False)
    assert write_rows(target, [_row(row_id="row-2")]) is False
    assert target.read_bytes() == before, "a failed write must not disturb the target"


def test_a_row_that_does_not_validate_is_never_written(tmp_path):
    """Validation happens BEFORE any IO, so a bad row cannot half-land."""
    target = tmp_path / "roster.jsonl"
    bad = DataRow(row_id="row-1", table="roster", key="slot-1", payload={"level": 20}, provenance=())
    with pytest.raises(ProvenanceError):
        write_rows(target, [_row(), bad])
    assert not target.exists(), "the target was created despite an invalid row"


def test_every_written_line_is_ascii_and_a_single_json_object(tmp_path):
    """One row, one line, one receipt set. A row torn out of the file still
    carries its receipt, which is the whole difference between row-scoped and
    document-scoped provenance."""
    target = tmp_path / "roster.jsonl"
    payload = {"display_name": "Fran" + chr(0xE7) + "ois", "level": 20}
    assert write_rows(target, [_row(payload=payload), _row(row_id="row-2")]) is True
    raw = target.read_bytes()
    assert raw.isascii(), "a non-ASCII byte reached the file; ensure_ascii is not doing its job"
    terminators = raw.count(b"\n")
    assert terminators == 2, f"expected one line terminator per row, got {terminators}"
    lines = target.read_text(encoding="ascii").splitlines()
    assert len(lines) == 2
    for line in lines:
        assert isinstance(json.loads(line), dict), "each line must be one complete JSON object"
    recovered = read_rows(target)
    assert len(recovered) == 2
    assert recovered[0].payload["display_name"] == payload["display_name"]


def test_the_written_file_carries_no_crlf(tmp_path):
    """EXPECTED RED until the atomic-writer slice lands.

    `.gitattributes` declares `* text=auto eol=lf`, which covers `.jsonl`, and
    tests/test_line_endings.py fails any tracked file that declares eol=lf and
    carries CRLF on disk. `Path.write_text` opens with `newline=None`, so on
    Windows every newline becomes CRLF and `git diff` shows nothing because the
    index normalises it. This arm is the one that catches that, and it is
    deliberately written before the fix so it goes red first.
    """
    target = tmp_path / "roster.jsonl"
    assert write_rows(target, [_row(), _row(row_id="row-2")]) is True
    raw = target.read_bytes()
    assert b"\r\n" not in raw, "the written file carries CRLF; the atomic writer is translating newlines"
    assert b"\r" not in raw


def test_the_rendered_source_is_derived_and_never_contradicts_the_receipts(tmp_path):
    """`data/costs/README.md` promises a `source` field on every row. It is
    DERIVED so the two can never disagree."""
    row = _row(_vision_read_of_the_crop(), _game_written_file())
    rendered = render_source(row)
    assert rendered, "the derived source summary is empty"
    assert "2 independent witness" in rendered, rendered
    target = tmp_path / "roster.jsonl"
    assert write_rows(target, [row]) is True
    assert read_rows(target)[0].source == rendered

    with pytest.raises(ProvenanceError):
        validate_row(_row(_vision_read_of_the_crop(), source="read it somewhere"))


# ---------------------------------------------------------------------------
# 26-28: the sweep, and the zero-out-of-zero guard
# ---------------------------------------------------------------------------


def _plant(root: Path, relative: str, rows: list[dict[str, object]]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8", newline="\n")


def _valid_row_dict() -> dict[str, object]:
    row = _row(_game_written_file())
    from core.provenance import row_to_dict

    return row_to_dict(row)


def test_the_sweep_reports_checked_before_offenders_on_a_planted_corpus(tmp_path):
    """THE NON-VACUITY PROOF, and it does not depend on the real tree holding
    any rows. One good file, one file whose row has no receipt."""
    good = _valid_row_dict()
    bad = dict(good)
    bad["row_id"] = "row-bad"
    bad["provenance"] = []
    _plant(tmp_path, "roster/good.jsonl", [good])
    _plant(tmp_path, "roster/bad.jsonl", [bad])

    checked, offenders = sweep_data_dir(tmp_path)
    assert checked == 2, f"the sweep examined {checked} rows, not 2 - zero out of zero is not a pass"
    assert len(offenders) == 1, f"expected exactly one offender, got {offenders}"
    assert "bad.jsonl" in offenders[0], offenders


def test_the_real_data_directory_reports_zero_checked_today_and_that_is_not_a_pass():
    """ZERO CHECKED, ASSERTED EXPLICITLY.

    `data/` holds no observation rows yet, so this sweep grades nothing and a
    green result here proves NOTHING about the checker. The proof lives in
    test_the_sweep_reports_checked_before_offenders_on_a_planted_corpus.

    When the first real row lands, this is the test whoever lands it must
    deliberately update - which is the point of asserting the zero rather than
    letting an empty corpus pass in silence.
    """
    checked, offenders = sweep_data_dir(REPO_ROOT / "data")
    assert checked == 0, (
        f"data/ now holds {checked} provenance rows. Update this test deliberately: "
        "raise the expected count and say in the message what landed."
    )
    assert not offenders


def test_the_sweep_skips_the_hand_authored_fixtures(tmp_path):
    """`data/fixtures/` is hand-authored fixture material, not observation.
    Grading it would be either vacuous or wrong."""
    _plant(tmp_path, "fixtures/seed.jsonl", [{"row_id": "nope", "provenance": []}])
    checked, offenders = sweep_data_dir(tmp_path)
    assert checked == 0, f"the sweep counted fixture rows: {checked}"
    assert not offenders

    _plant(tmp_path, "roster/good.jsonl", [_valid_row_dict()])
    checked, offenders = sweep_data_dir(tmp_path)
    assert checked == 1, "ARM TWO: the skip went too wide and dropped a real row file"
    assert not offenders


def test_check_rows_counts_before_it_complains():
    """The same contract, on the in-memory checker."""
    good = _row(_game_written_file())
    bad = DataRow(row_id="row-bad", table="roster", key="slot-2", payload={}, provenance=())
    checked, offenders = check_rows([good, bad])
    assert checked == 2, f"check_rows examined {checked} rows, not 2"
    assert len(offenders) == 1, offenders
    assert "row-bad" in offenders[0]


# ---------------------------------------------------------------------------
# 29-30: account safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    ["uid", "authkey", "authkey_ver", "account_id", "nickname", "token", "session_key"],
)
def test_a_row_carrying_a_forbidden_key_is_refused(forbidden: str):
    """PLANTED CONTROL, ASSERTED TO FIRE.

    A clean result and an unarmed check look identical, which is the same
    discipline docs/LEDGER.md records for the UID sweep. Every field name is
    named here rather than any value: the capture store lives outside the tree
    on purpose and nothing from it may ever reach `data/`.
    """
    with pytest.raises(ProvenanceError) as caught:
        validate_row(_row(payload={forbidden: "redacted"}))
    assert forbidden in str(caught.value)

    with pytest.raises(ProvenanceError):
        validate_row(_row(_record(source=_source(locator=f"evidence/{forbidden}_crop.png"))))


def test_a_legitimate_payload_key_survives_the_forbidden_sweep():
    """ARM TWO. A sweep scores one hundred percent on arm one by refusing
    everything, and this is what stops that being an acceptable answer."""
    validate_row(_row(payload={"level": 20, "friendship": 1, "element": "pyro", "rarity": 5}))


@pytest.mark.parametrize(
    ("label", "locator"),
    [
        ("a windows drive", "C:" + chr(92) + "evidence" + chr(92) + "frame.png"),
        ("a posix absolute path", "/var/captures/frame.png"),
        ("an msys mount spelling", "/c/captures/frame.png"),
        ("a unc share", chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "frame.png"),
        ("a parent escape", "../outside/frame.png"),
        ("empty", ""),
    ],
)
def test_a_locator_must_be_relative_and_must_not_name_a_drive(label: str, locator: str):
    """Keeps tests/test_machine_identity.py from ever having to catch a
    provenance row. A locator is relative to a NAMED capture root, and the root
    is named outside the tree."""
    with pytest.raises(ProvenanceError):
        validate_row(_row(_record(source=_source(locator=locator))))


def test_a_relative_locator_survives():
    """ARM TWO for the locator rule."""
    validate_row(_row(_record(source=_source(locator="evidence/roster_screen.png"))))


# ---------------------------------------------------------------------------
# Housekeeping the tree already expects of every file
# ---------------------------------------------------------------------------


def test_the_module_and_this_file_are_seven_bit_ascii():
    for path in (MODULE_PATH, Path(__file__).resolve()):
        raw = path.read_bytes()
        bad = sorted({byte for byte in raw if byte > 0x7E or (byte < 0x20 and byte not in (0x09, 0x0A, 0x0D))})
        assert bad == [], f"{path.name} carries non-ASCII or control bytes {bad}"


def test_the_schema_version_is_recorded_on_every_row():
    assert PROVENANCE_SCHEMA_VERSION == 1
    assert _row().schema_version == PROVENANCE_SCHEMA_VERSION
    with pytest.raises(ProvenanceError):
        validate_row(_row(schema_version=PROVENANCE_SCHEMA_VERSION + 1))
