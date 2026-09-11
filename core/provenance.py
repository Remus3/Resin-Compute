"""Row-scoped provenance - the receipt every value entering `data/` carries.

WHAT THIS MODULE IS, in one sentence: a value in `data/` must name the artefact
it was read from, that artefact's sha256, and HOW it was read, and this module
is what makes those three things checkable rather than aspirational.

WHY IT IS ROW-SCOPED AND NOT DOCUMENT-SCOPED. A row torn out of a file still
carries its own receipt. A header block at the top of a table describes the
table on the day it was written and describes nothing at all about the row a
consumer actually read.

THREE MEASURED EPISODES ARE THE REASON, and each one is a rule below.

1. INDEPENDENCE MUST BE COMPUTABLE. One account fact was described as "read
   four ways". Two of those four were pixel reads of ONE crop, so the honest
   count was three. `witness_key` keys a read on the artefact it came from -
   its `parent_sha256` where there is one - so two reads of one crop collapse
   into one witness by arithmetic, with no author having to remember to say so.
2. AN OCR ROW AND AN EYE ROW ARE DIFFERENT EVIDENCE. Tesseract returned a
   confident ZERO on a splash reading "Obtained New Character" with the text
   plainly on screen, in a stylised font over a full-screen effect.
   `EvidenceClass` and the `ocr_only` flag on `witness_report` exist so a
   consumer knows a zero came only from machines BEFORE it reads that zero as
   an absence.
3. NOT FOUND AT 1 FPS IS NOT NOT PRESENT. A negative is a claim about a SEARCH.
   `validate_row` REFUSES a `NOT_FOUND` record with no `SamplingRef`, rather
   than warning about it, because a warning nobody reads is not a rule.
4. A DIGEST NOBODY CAN RECOMPUTE IS A NUMBER, NOT A RECEIPT. For one release
   the only check on `sha256` was the FORMAT regex `_SHA256`, which answers
   "does this look like a digest" and cannot answer "is this the digest OF
   THOSE BYTES". A wrong digest that is still 64 lowercase hex characters
   passed it and always would have. `verify_source` RECOMPUTES with `hashlib`
   and compares, and it can do so because a locator is a path relative to a
   capture root - enforced by `_check_locator`, not hoped - and that root is a
   real directory the capture tools own and pass in. The root stays a
   PARAMETER: naming one machine's path in this tree is the leak this schema
   exists to avoid. `DigestVerdict` keeps ABSENT separate from MATCH and from
   MISMATCH so a verify cannot pass on an artefact that is not there, and
   `parent_sha256` reports UNLOCATABLE because it carries no locator of its own
   - it is a join key onto a parent that appears elsewhere as a source in its
   own right.

THE PYTHON CONVENTION, restated here because this module is a contract and the
convention is what keeps it one: a required field added to any dataclass below
is appended at the END with a default. A mid-class required field breaks every
existing positional construction and its tests. Every defaulted field below is
last in its class for that reason.

WRITING. `write_rows` builds the whole file body and hands it to
`core.atomic_io.atomic_write_text` ONCE. An append-mode open is banned outright
and `tests/test_provenance.py` asserts this file contains none: a reader
polling mid-append sees a torn last line, which is exactly the failure
`core/atomic_io.py` exists to prevent. An append here is therefore a whole-file
rewrite, which is O(n) per row and correct at this scale.

ACCOUNT SAFETY. `FORBIDDEN_KEY_TOKENS` refuses a payload key, a payload string
value or a locator naming an account field. The check is a case-insensitive
SUBSTRING match and is deliberately over-broad: a false refusal costs a rename,
a false accept costs an account leak into a public repository. Its stated limit
is that a bare account NUMBER sitting in a payload value is not detectable
here - no numeric shape distinguishes one from a level or an item id - so that
remains a human rule, enforced by `tests/test_machine_identity.py` over the
tracked tree.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from core.atomic_io import atomic_write_text

#: Bumped only by a deliberate migration. Nothing yet defines what a bump
#: obliges a reader to do; that is recorded as open rather than invented, and
#: `validate_row` refuses a version it does not know so the question cannot be
#: skipped silently.
PROVENANCE_SCHEMA_VERSION = 1

#: Account field names that must never reach `data/`. Named rather than
#: pattern-matched, so the list cannot widen or narrow behind anyone's back.
FORBIDDEN_KEY_TOKENS: tuple[str, ...] = (
    "uid",
    "authkey",
    "authkey_ver",
    "account_id",
    "nickname",
    "token",
    "session_key",
)

#: A digest is 64 lowercase hex characters. Uppercase is refused rather than
#: normalised: two spellings of one digest is two join keys, and the whole
#: point of the field is that it joins.
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

#: ISO-8601 with a trailing Z. A timestamp with no zone is a timestamp about
#: nowhere, and this tree records UTC.
_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")

#: A locator names a path RELATIVE to a capture root that is named outside this
#: tree. A drive letter, a leading separator or an MSYS mount spelling all name
#: one machine.
_DRIVE = re.compile(r"^[A-Za-z]:")


class ProvenanceError(ValueError):
    """A row or a receipt does not satisfy the contract.

    Per the hard rule, no raw error string reaches a user-facing surface. A
    future `surface/` panel renders "provenance incomplete" and logs this
    message. That is a constraint on the consumer; this module raises plainly
    because its callers are code, not people.
    """


class ReadMethod(StrEnum):
    """HOW a value was read. Seven members, pinned by a test.

    `HUMAN_EYE` and `VISION_MODEL` are separate because their failure modes
    differ: a model confabulates plausibly, an eye misreads. `OCR` is separate
    from both because of the measured zero described in the module docstring.
    """

    GAME_BYTES = "game_bytes"
    GAME_API = "game_api"
    HUMAN_EYE = "human_eye"
    VISION_MODEL = "vision_model"
    OCR = "ocr"
    OPERATOR_STATEMENT = "operator_statement"
    DERIVED = "derived"


class EvidenceClass(StrEnum):
    """What KIND of evidence a read method produces."""

    GAME_AUTHORED = "game_authored"
    HUMAN_READ = "human_read"
    MACHINE_READ = "machine_read"
    TESTIMONY = "testimony"
    NONE = "none"


#: TOTAL over `ReadMethod`, and `check_evidence_class_totality` proves it is,
#: counting what it checked before it reports what it found. A read method with
#: no class would otherwise classify as nothing and quietly stop being graded.
EVIDENCE_CLASS: Mapping[ReadMethod, EvidenceClass] = MappingProxyType(
    {
        ReadMethod.GAME_BYTES: EvidenceClass.GAME_AUTHORED,
        ReadMethod.GAME_API: EvidenceClass.GAME_AUTHORED,
        ReadMethod.HUMAN_EYE: EvidenceClass.HUMAN_READ,
        ReadMethod.VISION_MODEL: EvidenceClass.HUMAN_READ,
        ReadMethod.OCR: EvidenceClass.MACHINE_READ,
        ReadMethod.OPERATOR_STATEMENT: EvidenceClass.TESTIMONY,
        ReadMethod.DERIVED: EvidenceClass.NONE,
    }
)


def evidence_class(method: ReadMethod) -> EvidenceClass:
    """The evidence class of `method`. Raises `KeyError` on an unclassed one,
    which is the loud failure the totality check exists to prevent reaching."""
    return EVIDENCE_CLASS[method]


class SourceKind(StrEnum):
    """WHAT was read."""

    FILE = "file"
    FRAME = "frame"
    CROP = "crop"
    VIDEO_SEGMENT = "video_segment"
    HTTP_RESPONSE = "http_response"
    TESTIMONY = "testimony"


class ObservationStatus(StrEnum):
    """What the read established.

    `MEASURED_ZERO` and `NOT_FOUND` are deliberately distinct, and conflating
    them is how a sampled sweep gets read as a fact. A surface that ANSWERED
    and answered none is a measured zero. A sweep that found nothing is a claim
    about the sweep.
    """

    VERIFIED = "verified"
    MEASURED_ZERO = "measured_zero"
    NOT_FOUND = "not_found"
    UNVERIFIED = "unverified"
    RETRACTED = "retracted"


@dataclass(frozen=True)
class SourceRef:
    """The artefact a read came out of.

    `parent_sha256` is the load-bearing field. It is what makes two pixel reads
    of one crop computably ONE fact rather than assertedly one: both cite the
    same parent frame, so both produce the same witness key.

    `witness_group` is the manual escape for the known limit. Two DIFFERENT
    frames of one unchanged screen have different digests and would count
    twice. Perceptual similarity is a judgement and a guard that guessed at it
    would be wrong in both directions, so the schema does not guess - an author
    collapses them by naming a group, and `witness_report` still reports the
    shape so the decision stays visible.
    """

    kind: SourceKind
    locator: str
    sha256: str
    captured_utc: str
    bytes_len: int = 0
    parent_sha256: str = ""
    offset_s: float = 0.0
    witness_group: str = ""


@dataclass(frozen=True)
class SamplingRef:
    """The corpus a read swept, and how much of it was actually looked at.

    `population_count == 0` means UNKNOWN and is allowed. It is not silently
    accepted: `coverage_notes` stamps it `coverage_unknown`, because a row
    asserting absence over an uncounted population is not the same row as one
    asserting it over a counted one.
    """

    corpus: str
    native_rate_hz: float
    examined_rate_hz: float
    examined_count: int
    population_count: int
    window_start_utc: str
    window_end_utc: str


@dataclass(frozen=True)
class ProvenanceRecord:
    """ONE receipt. A row carries a tuple of these and never fewer than one."""

    record_id: str
    claim: str
    read_method: ReadMethod
    source: SourceRef
    observed_utc: str
    status: ObservationStatus
    reader: str
    game_version: str = ""
    sampling: tuple[SamplingRef, ...] = ()
    derived_from: tuple[str, ...] = ()
    retracted_by: str = ""
    reconfirmed_utc: str = ""
    reconfirmed_game_version: str = ""
    note: str = ""


@dataclass(frozen=True)
class DataRow:
    """The thing that lands in `data/`. One row, one line, one receipt set.

    NEVER HASHABLE, deliberately. `payload` is a Mapping, so a generated hash
    would raise from inside the set operation that built it, at a call site
    with nothing to do with provenance. `__hash__` raises here instead, where
    the message can say why. Equality still works, which is all the consumers
    need.

    `source` is a RENDERED summary and is never hand-written. `data/costs/`
    promises a `source` field on every row and the parked cost-loader suite
    asserts it is truthy; `render_source` DERIVES it from the receipts so the
    two can never disagree, and `validate_row` refuses a hand-written one that
    contradicts them.
    """

    row_id: str
    table: str
    key: str
    payload: Mapping[str, Any]
    provenance: tuple[ProvenanceRecord, ...]
    schema_version: int = PROVENANCE_SCHEMA_VERSION
    source: str = ""

    def __hash__(self) -> int:
        raise TypeError(
            "DataRow is not hashable: payload is a Mapping, and a set of rows "
            "would fail from inside whatever built the set. Compare rows or key "
            "them by row_id."
        )


@dataclass(frozen=True)
class WitnessReport:
    """The shape of the support behind a claim, not just its size.

    `ocr_only` is the flag the confident-zero episode earns. Three OCR
    witnesses over three distinct frames really are three witnesses - and they
    are also three MACHINE_READ witnesses, which is what a consumer needs
    before it reads a zero as an absence. The count alone was never the answer.
    """

    witnesses: int
    keys: tuple[str, ...]
    class_counts: Mapping[EvidenceClass, int]
    single_class: bool
    ocr_only: bool


# ---------------------------------------------------------------------------
# Independence
# ---------------------------------------------------------------------------


def witness_key(record: ProvenanceRecord) -> str | None:
    """The identity of the thing that WITNESSED this claim, or None.

    None means "not a witness at all", and there are exactly two such cases. A
    `DERIVED` record read nothing, so it cannot corroborate its own inputs. A
    retracted record was withdrawn, and a withdrawn reading that still counted
    towards support would make retraction cosmetic.
    """
    if record.read_method is ReadMethod.DERIVED:
        return None
    if record.status is ObservationStatus.RETRACTED or record.retracted_by:
        return None
    source = record.source
    if source.witness_group:
        return "group:" + source.witness_group
    if source.kind is SourceKind.TESTIMONY:
        return "testimony:" + source.locator
    if source.parent_sha256:
        return "artefact:" + source.parent_sha256
    return "artefact:" + source.sha256


def independent_witnesses(records: Iterable[ProvenanceRecord]) -> int:
    """How many DISTINCT artefacts stand behind these records.

    Two pixel reads of one crop share a parent frame, so the set collapses and
    the answer is 1. Add the game's own bytes and it is 2 - pixels and bytes
    agreeing IS corroboration, and two pixel reads agreeing is not.
    """
    keys = {witness_key(record) for record in records}
    keys.discard(None)
    return len(keys)


def witness_report(records: Iterable[ProvenanceRecord]) -> WitnessReport:
    """`independent_witnesses` plus the SHAPE of what is behind the count.

    A witness is classed by the FIRST record citing it, in the order given, so
    the report is deterministic when one artefact was read two ways.
    """
    ordered: list[str] = []
    classes: dict[str, EvidenceClass] = {}
    for record in records:
        key = witness_key(record)
        if key is None or key in classes:
            continue
        ordered.append(key)
        classes[key] = evidence_class(record.read_method)

    counts: dict[EvidenceClass, int] = {}
    for cls in classes.values():
        counts[cls] = counts.get(cls, 0) + 1

    return WitnessReport(
        witnesses=len(ordered),
        keys=tuple(ordered),
        class_counts=MappingProxyType(counts),
        single_class=len(counts) == 1,
        ocr_only=bool(counts) and set(counts) == {EvidenceClass.MACHINE_READ},
    )


def supporting_records(
    rows: Iterable[DataRow | ProvenanceRecord], claim: str
) -> tuple[ProvenanceRecord, ...]:
    """Every non-retracted record supporting `claim`, in file order.

    This is the direct answer to the trial-character episode. Two numbers
    merely consistent with a hypothesis were ONE record with ONE witness at
    `UNVERIFIED`; operator testimony then retracted it, and the support set
    goes EMPTY rather than the claim keeping numbers that never were evidence.

    Accepts rows or bare records so a caller holding either can ask.
    """
    found: list[ProvenanceRecord] = []
    for item in rows:
        records = (item,) if isinstance(item, ProvenanceRecord) else item.provenance
        for record in records:
            if record.claim != claim:
                continue
            if record.status is ObservationStatus.RETRACTED or record.retracted_by:
                continue
            found.append(record)
    return tuple(found)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def coverage_ratio(sampling: SamplingRef) -> float:
    """Examined rate over native rate. One frame in fifteen reports 1/15.

    A native rate of zero cannot be divided by and cannot describe a corpus, so
    it reports 0.0 rather than raising - `validate_row` is what refuses it, and
    a report helper that raised would make the refusal harder to describe.
    """
    if sampling.native_rate_hz <= 0.0:
        return 0.0
    return sampling.examined_rate_hz / sampling.native_rate_hz


def coverage_notes(record: ProvenanceRecord) -> tuple[str, ...]:
    """Machine-readable stamps about how thin this record's coverage is.

    STAMPED, NOT REFUSED. An absence over an unknown population is a legitimate
    thing to record - it is what the operator actually had - but it must not
    read like an absence over a counted one.
    """
    notes: list[str] = []
    for sampling in record.sampling:
        if sampling.population_count == 0:
            notes.append(f"coverage_unknown: {sampling.corpus} population was not counted")
        ratio = coverage_ratio(sampling)
        if ratio < 1.0:
            notes.append(f"partial_coverage: {sampling.corpus} examined at {ratio:.6f} of native rate")
    return tuple(notes)


def is_absence_claim(record: ProvenanceRecord) -> bool:
    """True only for `NOT_FOUND`. A measured zero is not an absence claim."""
    return record.status is ObservationStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _refuse(message: str) -> None:
    raise ProvenanceError(message)


def _forbidden_token(text: str) -> str | None:
    lowered = text.lower()
    for token in FORBIDDEN_KEY_TOKENS:
        if token in lowered:
            return token
    return None


def _check_locator(locator: str, where: str) -> None:
    if not locator:
        _refuse(f"{where}: locator is empty; a receipt must name what was read")
    if _DRIVE.match(locator):
        _refuse(f"{where}: locator names a drive, so it names one machine: {locator!r}")
    if locator.startswith(("/", "\\")):
        _refuse(f"{where}: locator is absolute; it must be relative to a named capture root: {locator!r}")
    if "\\" in locator:
        _refuse(f"{where}: locator uses a backslash separator; write it with forward slashes: {locator!r}")
    if ".." in locator.split("/"):
        _refuse(f"{where}: locator escapes its capture root: {locator!r}")
    token = _forbidden_token(locator)
    if token is not None:
        _refuse(f"{where}: locator names the account field {token!r}, which must never reach data/")


def _check_timestamp(value: str, where: str) -> None:
    if not _ISO_Z.match(value):
        _refuse(f"{where}: {value!r} is not ISO-8601 UTC with a trailing Z")


def _check_sampling(sampling: SamplingRef, where: str) -> None:
    if not sampling.corpus:
        _refuse(f"{where}: sampling names no corpus")
    if sampling.native_rate_hz <= 0.0:
        _refuse(f"{where}: native_rate_hz must be positive, got {sampling.native_rate_hz}")
    if sampling.examined_rate_hz <= 0.0:
        _refuse(f"{where}: examined_rate_hz must be positive, got {sampling.examined_rate_hz}")
    if sampling.examined_rate_hz > sampling.native_rate_hz:
        _refuse(
            f"{where}: examined_rate_hz {sampling.examined_rate_hz} exceeds native_rate_hz "
            f"{sampling.native_rate_hz}; nobody examines frames that do not exist"
        )
    if sampling.examined_count < 0 or sampling.population_count < 0:
        _refuse(f"{where}: sampling counts cannot be negative")
    if sampling.population_count and sampling.examined_count > sampling.population_count:
        _refuse(
            f"{where}: examined {sampling.examined_count} of a population of "
            f"{sampling.population_count}"
        )
    _check_timestamp(sampling.window_start_utc, f"{where}.window_start_utc")
    _check_timestamp(sampling.window_end_utc, f"{where}.window_end_utc")


#: Source kinds where sampling is FORBIDDEN. One artefact was read in full, so
#: a fabricated rate of 1.0 is noise that makes a real rate harder to trust.
_NO_SAMPLING = frozenset({SourceKind.FILE, SourceKind.HTTP_RESPONSE, SourceKind.TESTIMONY})


def validate_record(record: ProvenanceRecord) -> None:
    """Refuse a receipt that does not carry what a reader would need.

    A NOTE ON THE OCR-SWEEP RULE, stated rather than quietly dropped. The
    design says an OCR record that came from a SWEEP must carry a sampling
    rate. "Came from a sweep" is not decidable from the record itself - the
    same method reads one named still and a whole recording - so it is covered
    here by the two rules that ARE decidable: a `NOT_FOUND` status and a
    `VIDEO_SEGMENT` source both require sampling, and every real OCR sweep in
    the measured corpus carries at least one of them. Reading one named still
    is not sampling, and is left optional.
    """
    where = f"record {record.record_id or '<unnamed>'}"
    if not record.record_id:
        _refuse("a provenance record carries no record_id")
    if not record.claim:
        _refuse(f"{where}: claim is empty; a receipt must say what it supports")
    if not record.reader:
        _refuse(f"{where}: reader is empty; who or what performed the read is part of the receipt")
    _check_timestamp(record.observed_utc, f"{where}.observed_utc")

    source = record.source
    _check_locator(source.locator, where)
    _check_timestamp(source.captured_utc, f"{where}.source.captured_utc")
    if source.kind is SourceKind.TESTIMONY:
        if source.sha256:
            _refuse(
                f"{where}: a testimony source carries a digest. No bytes exist, so a "
                "digest there is theatre"
            )
    elif not _SHA256.match(source.sha256):
        _refuse(
            f"{where}: sha256 {source.sha256!r} is not 64 lowercase hex characters, so no "
            "reader can re-derive which bytes were read"
        )
    if source.parent_sha256 and not _SHA256.match(source.parent_sha256):
        _refuse(f"{where}: parent_sha256 {source.parent_sha256!r} is not 64 lowercase hex characters")
    if source.bytes_len < 0:
        _refuse(f"{where}: bytes_len is negative")
    if source.offset_s < 0.0:
        _refuse(f"{where}: offset_s is negative")

    if record.read_method is ReadMethod.DERIVED and not record.derived_from:
        _refuse(
            f"{where}: a DERIVED record names no derived_from inputs. A derivation that "
            "names no inputs is an assertion wearing a receipt"
        )
    if record.read_method is ReadMethod.OPERATOR_STATEMENT and source.kind is not SourceKind.TESTIMONY:
        _refuse(f"{where}: an OPERATOR_STATEMENT must cite a TESTIMONY source, not {source.kind}")

    if record.status is ObservationStatus.RETRACTED and not record.retracted_by:
        _refuse(f"{where}: status is RETRACTED but retracted_by names no retraction")
    if record.retracted_by and record.status is not ObservationStatus.RETRACTED:
        _refuse(f"{where}: retracted_by is set but status is {record.status}, not RETRACTED")

    if record.status is ObservationStatus.NOT_FOUND and not record.sampling:
        _refuse(
            f"{where}: a NOT_FOUND record carries no sampling. A negative is a claim about a "
            "SEARCH, and a search with no stated rate is unreportable - not found at 1 fps is "
            "not not present"
        )
    if source.kind is SourceKind.VIDEO_SEGMENT and not record.sampling:
        _refuse(
            f"{where}: a VIDEO_SEGMENT source carries no sampling. A segment is a corpus, not "
            "an artefact, and naming one is naming a haystack"
        )
    if record.sampling and source.kind in _NO_SAMPLING:
        _refuse(
            f"{where}: sampling is forbidden on a {source.kind} source. One artefact was read in "
            "full, and a fabricated rate makes a real one harder to trust"
        )
    for index, sampling in enumerate(record.sampling):
        _check_sampling(sampling, f"{where}.sampling[{index}]")


def validate_row(row: DataRow) -> None:
    """Refuse a row that cannot be audited. Raises `ProvenanceError`."""
    where = f"row {row.row_id or '<unnamed>'}"
    if not row.row_id:
        _refuse("a data row carries no row_id")
    if not row.table:
        _refuse(f"{where}: table is empty")
    if not row.key:
        _refuse(f"{where}: key is empty")
    if row.schema_version != PROVENANCE_SCHEMA_VERSION:
        _refuse(
            f"{where}: schema_version {row.schema_version} is not "
            f"{PROVENANCE_SCHEMA_VERSION}; a reader cannot know what the difference obliges it to do"
        )
    if not row.provenance:
        _refuse(
            f"{where}: provenance is empty. A value with no receipt cannot be audited later, "
            "which is the entire reason this schema exists"
        )

    for key, value in row.payload.items():
        token = _forbidden_token(str(key))
        if token is not None:
            _refuse(f"{where}: payload key {key!r} names the account field {token!r}, which must never reach data/")
        if isinstance(value, str):
            token = _forbidden_token(value)
            if token is not None:
                _refuse(
                    f"{where}: payload value under {key!r} names the account field {token!r}, "
                    "which must never reach data/"
                )

    for record in row.provenance:
        validate_record(record)

    if row.source and row.source != render_source(row):
        _refuse(
            f"{where}: source was hand-written and contradicts the receipts. It is DERIVED - "
            "leave it empty and write_rows fills it in"
        )


def render_source(row: DataRow) -> str:
    """The `source` summary, DERIVED from the receipts so it cannot disagree.

    `data/costs/README.md` promises every row carries a `source` field. This is
    that field, and it is a function of the provenance tuple rather than a
    second place for a human to state an origin.
    """
    live = [record for record in row.provenance if witness_key(record) is not None]
    report = witness_report(live)
    parts = [
        f"{record.read_method.value}:{record.source.kind.value}:{_short(record.source)}"
        for record in live
    ]
    if not parts:
        return f"{report.witnesses} independent witness(es): none - every receipt is retracted or derived"
    suffix = " [ocr_only]" if report.ocr_only else ""
    return f"{report.witnesses} independent witness(es): " + "; ".join(parts) + suffix


def _short(source: SourceRef) -> str:
    digest = source.parent_sha256 or source.sha256
    return digest[:8] if digest else source.locator


# ---------------------------------------------------------------------------
# Recompute-and-compare. A DIGEST NOBODY CAN RECOMPUTE IS A NUMBER.
# ---------------------------------------------------------------------------


class DigestVerdict(StrEnum):
    """What a recompute established about ONE declared digest.

    FIVE members, and the last three exist so that "the bytes were never
    compared" can never be spelled the same way as "the bytes agreed".

    - `MATCH` - the artefact was located, hashed, and the digests are equal.
    - `MISMATCH` - located and hashed, and the digests differ. This is the
      verdict the format check could never reach: a wrong digest that is still
      64 lowercase hex characters passes `_SHA256` and always would have.
    - `ABSENT` - the locator resolved under the capture root and no readable
      bytes are there. ITS OWN CLASS, deliberately. A verify that returned
      `MATCH` on a missing artefact would be one more degrade-to-empty site.
    - `NO_DIGEST` - the receipt declares none. A `TESTIMONY` source has no
      bytes, so there is nothing to recompute and nothing to pass.
    - `UNLOCATABLE` - a digest with no path to its bytes. This is what
      `parent_sha256` always is when read from the child alone; see
      `verify_record`.
    """

    MATCH = "match"
    MISMATCH = "mismatch"
    ABSENT = "absent"
    NO_DIGEST = "no_digest"
    UNLOCATABLE = "unlocatable"


#: Verdicts where the bytes question was actually ASKED. `check_digests` uses
#: this as its denominator: counting a digest nobody could reach as "checked"
#: inflates the denominator, which is the same defect as zero out of zero
#: reading as a pass.
VERIFIABLE_VERDICTS: frozenset[DigestVerdict] = frozenset(
    {DigestVerdict.MATCH, DigestVerdict.MISMATCH, DigestVerdict.ABSENT}
)


@dataclass(frozen=True)
class DigestCheck:
    """The result of comparing ONE declared digest against real bytes.

    `computed` is empty whenever nothing was hashed, so an empty `computed`
    beside a `MATCH` would be a contradiction rather than a default. Fields
    after `declared` carry defaults and are last, per the convention stated in
    the module docstring.
    """

    verdict: DigestVerdict
    field: str
    locator: str
    declared: str
    computed: str = ""
    path: str = ""
    detail: str = ""


#: Read size for hashing. A frame or a video segment is far larger than a row,
#: so the file is streamed rather than materialised.
_HASH_CHUNK = 1 << 20


def sha256_bytes(data: bytes) -> str:
    """The sha256 of `data`, 64 lowercase hex characters."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    """The sha256 of a file's BYTES, read in binary mode.

    BINARY IS THE WHOLE POINT and is not an implementation detail. A text-mode
    read on Windows collapses CRLF to LF, so the same file would hash
    differently from the bytes on disk and every comparison would become a
    statement about the host. `.gitattributes` pins `eol=lf` in this tree and
    hides the difference from every diff, which is precisely why the hash must
    not go through a decoder.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(_HASH_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def resolve_source(source: SourceRef, capture_root: str | os.PathLike[str]) -> Path:
    """Where `source.locator` points, under `capture_root`. Raises on a bad one.

    THE JOIN IS ONLY SAFE BECAUSE THE LOCATOR WAS ALREADY CONSTRAINED, so this
    re-runs `_check_locator` rather than trusting that a caller validated first.
    A locator naming a drive, an absolute path or a `..` segment is refused
    here, not silently hashed from somewhere outside the root.
    """
    _check_locator(source.locator, f"source {source.locator!r}")
    return Path(capture_root) / source.locator


def verify_source(source: SourceRef, capture_root: str | os.PathLike[str]) -> DigestCheck:
    """RECOMPUTE `source.sha256` from the bytes and compare. Never a shape check.

    WHY RECOMPUTE-AND-COMPARE AND NOT A RENAME TO ADVISORY. The artefact IS
    reachable from here: a locator is a path relative to a capture root - that
    is enforced, not hoped, by `_check_locator` refusing a drive letter, an
    absolute path and a `..` segment - and the root is a real directory on disk
    that the capture tools own and pass in. The root is not hardcoded here
    because naming one machine's path in this tree is the leak this schema
    exists to avoid; it is a parameter for that reason and for no other.

    A `TESTIMONY` source carrying a digest is REFUSED rather than graded. No
    bytes exist, so a digest there is theatre, and `validate_record` already
    says so.
    """
    if source.kind is SourceKind.TESTIMONY and source.sha256:
        _refuse(
            f"source {source.locator!r}: a testimony source carries a digest. No bytes exist, "
            "so there is nothing to recompute it against"
        )
    if not source.sha256:
        return DigestCheck(
            verdict=DigestVerdict.NO_DIGEST,
            field="sha256",
            locator=source.locator,
            declared="",
            detail=f"a {source.kind.value} source declares no digest",
        )

    path = resolve_source(source, capture_root)
    if not path.is_file():
        return DigestCheck(
            verdict=DigestVerdict.ABSENT,
            field="sha256",
            locator=source.locator,
            declared=source.sha256,
            path=str(path),
            detail="no readable artefact at that locator under the capture root",
        )
    try:
        computed = sha256_file(path)
    except OSError as exc:
        return DigestCheck(
            verdict=DigestVerdict.ABSENT,
            field="sha256",
            locator=source.locator,
            declared=source.sha256,
            path=str(path),
            detail=f"the artefact could not be read: {exc}",
        )

    verdict = DigestVerdict.MATCH if computed == source.sha256 else DigestVerdict.MISMATCH
    return DigestCheck(
        verdict=verdict,
        field="sha256",
        locator=source.locator,
        declared=source.sha256,
        computed=computed,
        path=str(path),
    )


def verify_record(
    record: ProvenanceRecord, capture_root: str | os.PathLike[str]
) -> tuple[DigestCheck, ...]:
    """One check for `sha256`, and one for `parent_sha256` where it is set.

    `parent_sha256` IS ALWAYS `UNLOCATABLE` FROM HERE, and that is a fact about
    the schema rather than a gap in this function. The field carries no locator
    of its own: it is a JOIN KEY onto a parent artefact that appears elsewhere
    as a `SourceRef` in its own right, with its own locator and its own digest.
    Verifying it therefore means locating that parent record, which is the
    caller's corpus and not this record. Reporting it as `UNLOCATABLE` says so
    out loud instead of letting an unverified digest sit next to a verified one
    looking the same.
    """
    checks = [verify_source(record.source, capture_root)]
    if record.source.parent_sha256:
        checks.append(
            DigestCheck(
                verdict=DigestVerdict.UNLOCATABLE,
                field="parent_sha256",
                locator=record.source.locator,
                declared=record.source.parent_sha256,
                detail=(
                    "parent_sha256 carries no locator of its own; verify it where the parent "
                    "artefact appears as a source in its own right"
                ),
            )
        )
    return tuple(checks)


def verify_row(row: DataRow, capture_root: str | os.PathLike[str]) -> tuple[DigestCheck, ...]:
    """Every digest check for every receipt on `row`, in receipt order."""
    checks: list[DigestCheck] = []
    for record in row.provenance:
        checks.extend(verify_record(record, capture_root))
    return tuple(checks)


def digest_counts(checks: Iterable[DigestCheck]) -> Mapping[DigestVerdict, int]:
    """How many checks landed on each verdict. TOTAL over what it was given.

    This is what makes the UNVERIFIABLE population countable rather than
    invisible. `check_digests` reports offenders and a verifiable denominator;
    a caller that wants to know how many digests nobody could reach asks here.
    """
    counts: dict[DigestVerdict, int] = {verdict: 0 for verdict in DigestVerdict}
    for check in checks:
        counts[check.verdict] += 1
    return MappingProxyType(counts)


def check_digests(
    rows: Iterable[DataRow], capture_root: str | os.PathLike[str]
) -> tuple[int, list[str]]:
    """`(checked, offenders)` over declared digests, per the house convention.

    `checked` counts only the digests whose bytes question was actually asked -
    `VERIFIABLE_VERDICTS`. A `NO_DIGEST` or `UNLOCATABLE` check is not in the
    denominator, because a corpus of nothing but those would otherwise report a
    large checked count and an empty offender list, which reads as a pass over
    digests nobody compared. Call `digest_counts` for that population.
    """
    checked = 0
    offenders: list[str] = []
    for row in rows:
        for check in verify_row(row, capture_root):
            if check.verdict in VERIFIABLE_VERDICTS:
                checked += 1
            if check.verdict is DigestVerdict.MISMATCH:
                offenders.append(
                    f"{row.row_id or '<unnamed>'}: {check.field} mismatch at {check.locator}: "
                    f"declared {check.declared}, recomputed {check.computed}"
                )
            elif check.verdict is DigestVerdict.ABSENT:
                offenders.append(
                    f"{row.row_id or '<unnamed>'}: {check.field} absent at {check.locator}: "
                    f"{check.detail}"
                )
    return checked, offenders


# ---------------------------------------------------------------------------
# Checkers. EVERY ONE returns (checked, offenders), and every caller asserts
# the checked count BEFORE the offender list. Zero out of zero is not a pass.
# ---------------------------------------------------------------------------


def check_evidence_class_totality() -> tuple[int, list[str]]:
    """Is `EVIDENCE_CLASS` total over `ReadMethod`?"""
    offenders = [method.name for method in ReadMethod if method not in EVIDENCE_CLASS]
    return len(list(ReadMethod)), offenders


def check_rows(rows: Iterable[DataRow]) -> tuple[int, list[str]]:
    """Validate rows in memory, reporting rather than raising."""
    checked = 0
    offenders: list[str] = []
    for row in rows:
        checked += 1
        try:
            validate_row(row)
        except ProvenanceError as exc:
            offenders.append(f"{row.row_id or '<unnamed>'}: {exc}")
    return checked, offenders


def sweep_data_dir(root: str | os.PathLike[str]) -> tuple[int, list[str]]:
    """Validate every provenance row under `root`, one JSONL line at a time.

    `data/fixtures/` is SKIPPED. It is hand-authored fixture material, not
    observation, and grading it would be either vacuous or wrong.

    A missing root reports (0, []). That zero is honest and the caller is
    expected to assert it: an empty corpus passing in silence is the exact
    defect the checked-count rule exists for.
    """
    base = Path(root)
    checked = 0
    offenders: list[str] = []
    if not base.is_dir():
        return checked, offenders
    for path in sorted(base.rglob("*.jsonl")):
        relative = path.relative_to(base)
        if "fixtures" in relative.parts:
            continue
        name = relative.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            offenders.append(f"{name}: unreadable: {exc}")
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            checked += 1
            try:
                validate_row(row_from_dict(json.loads(line)))
            except (ProvenanceError, json.JSONDecodeError, TypeError) as exc:
                offenders.append(f"{name}:{lineno}: {exc}")
    return checked, offenders


# ---------------------------------------------------------------------------
# Serialization and IO
# ---------------------------------------------------------------------------


def _sampling_to_dict(sampling: SamplingRef) -> dict[str, Any]:
    return {
        "corpus": sampling.corpus,
        "native_rate_hz": sampling.native_rate_hz,
        "examined_rate_hz": sampling.examined_rate_hz,
        "examined_count": sampling.examined_count,
        "population_count": sampling.population_count,
        "window_start_utc": sampling.window_start_utc,
        "window_end_utc": sampling.window_end_utc,
    }


def _source_to_dict(source: SourceRef) -> dict[str, Any]:
    return {
        "kind": source.kind.value,
        "locator": source.locator,
        "sha256": source.sha256,
        "captured_utc": source.captured_utc,
        "bytes_len": source.bytes_len,
        "parent_sha256": source.parent_sha256,
        "offset_s": source.offset_s,
        "witness_group": source.witness_group,
    }


def _record_to_dict(record: ProvenanceRecord) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "claim": record.claim,
        "read_method": record.read_method.value,
        "source": _source_to_dict(record.source),
        "observed_utc": record.observed_utc,
        "status": record.status.value,
        "reader": record.reader,
        "game_version": record.game_version,
        "sampling": [_sampling_to_dict(item) for item in record.sampling],
        "derived_from": list(record.derived_from),
        "retracted_by": record.retracted_by,
        "reconfirmed_utc": record.reconfirmed_utc,
        "reconfirmed_game_version": record.reconfirmed_game_version,
        "note": record.note,
    }


def row_to_dict(row: DataRow) -> dict[str, Any]:
    """A plain JSON-ready mapping. Enums become their string values."""
    return {
        "row_id": row.row_id,
        "table": row.table,
        "key": row.key,
        "payload": dict(row.payload),
        "provenance": [_record_to_dict(record) for record in row.provenance],
        "schema_version": row.schema_version,
        "source": row.source,
    }


def _require_mapping(obj: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise ProvenanceError(f"{where}: expected an object, got {type(obj).__name__}")
    return obj


def _sampling_from_dict(obj: Any, where: str) -> SamplingRef:
    data = _require_mapping(obj, where)
    try:
        return SamplingRef(
            corpus=str(data["corpus"]),
            native_rate_hz=float(data["native_rate_hz"]),
            examined_rate_hz=float(data["examined_rate_hz"]),
            examined_count=int(data["examined_count"]),
            population_count=int(data["population_count"]),
            window_start_utc=str(data["window_start_utc"]),
            window_end_utc=str(data["window_end_utc"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProvenanceError(f"{where}: malformed sampling reference: {exc}") from exc


def _source_from_dict(obj: Any, where: str) -> SourceRef:
    data = _require_mapping(obj, where)
    try:
        return SourceRef(
            kind=SourceKind(data["kind"]),
            locator=str(data["locator"]),
            sha256=str(data["sha256"]),
            captured_utc=str(data["captured_utc"]),
            bytes_len=int(data.get("bytes_len", 0)),
            parent_sha256=str(data.get("parent_sha256", "")),
            offset_s=float(data.get("offset_s", 0.0)),
            witness_group=str(data.get("witness_group", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProvenanceError(f"{where}: malformed source reference: {exc}") from exc


def _record_from_dict(obj: Any, where: str) -> ProvenanceRecord:
    data = _require_mapping(obj, where)
    try:
        return ProvenanceRecord(
            record_id=str(data["record_id"]),
            claim=str(data["claim"]),
            read_method=ReadMethod(data["read_method"]),
            source=_source_from_dict(data["source"], f"{where}.source"),
            observed_utc=str(data["observed_utc"]),
            status=ObservationStatus(data["status"]),
            reader=str(data["reader"]),
            game_version=str(data.get("game_version", "")),
            sampling=tuple(
                _sampling_from_dict(item, f"{where}.sampling[{index}]")
                for index, item in enumerate(data.get("sampling", ()))
            ),
            derived_from=tuple(str(item) for item in data.get("derived_from", ())),
            retracted_by=str(data.get("retracted_by", "")),
            reconfirmed_utc=str(data.get("reconfirmed_utc", "")),
            reconfirmed_game_version=str(data.get("reconfirmed_game_version", "")),
            note=str(data.get("note", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProvenanceError(f"{where}: malformed provenance record: {exc}") from exc


def row_from_dict(obj: Any) -> DataRow:
    """Rebuild a row from its serialized form.

    A row with an EMPTY provenance list is rebuilt rather than rejected here.
    Refusal belongs to `validate_row`, so a sweep can count the row as CHECKED
    and then report it, instead of losing it before it was ever graded.
    """
    data = _require_mapping(obj, "row")
    try:
        payload = _require_mapping(data["payload"], "row.payload")
        return DataRow(
            row_id=str(data["row_id"]),
            table=str(data["table"]),
            key=str(data["key"]),
            payload=dict(payload),
            provenance=tuple(
                _record_from_dict(item, f"row.provenance[{index}]")
                for index, item in enumerate(data.get("provenance", ()))
            ),
            schema_version=int(data.get("schema_version", PROVENANCE_SCHEMA_VERSION)),
            source=str(data.get("source", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProvenanceError(f"malformed data row: {exc}") from exc


def read_rows(path: str | os.PathLike[str]) -> tuple[DataRow, ...]:
    """Every row in a JSONL file, in file order. Raises on a malformed line."""
    text = Path(path).read_text(encoding="utf-8")
    rows: list[DataRow] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProvenanceError(f"line {lineno} is not JSON: {exc}") from exc
        rows.append(row_from_dict(parsed))
    return tuple(rows)


def write_rows(path: str | os.PathLike[str], rows: Sequence[DataRow] | Iterable[DataRow]) -> bool:
    """Validate, then write the WHOLE file in one atomic call. Returns its bool.

    Validation happens BEFORE any IO, so an invalid row cannot half-land. The
    body is built as one string and handed to `atomic_write_text` once: an
    append-mode open would let a polling reader see a torn last line, which is
    the failure `core/atomic_io.py` exists to prevent. Appending a row is
    therefore `read_rows` then `write_rows`, which is O(n) and correct at this
    scale.

    `source` is filled in from the receipts for any row that left it empty, so
    the rendered summary and the receipts cannot drift apart on disk.
    """
    materialised = list(rows)
    for row in materialised:
        validate_row(row)
    finalised = [row if row.source else replace(row, source=render_source(row)) for row in materialised]
    body = "".join(
        json.dumps(row_to_dict(row), sort_keys=True, ensure_ascii=True) + "\n" for row in finalised
    )
    return atomic_write_text(path, body)
