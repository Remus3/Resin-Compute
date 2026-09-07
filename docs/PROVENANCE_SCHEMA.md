# Row-scoped provenance - the receipt every value in data/ carries

**Status: the contract. Implemented in `core/provenance.py`, held by
`tests/test_provenance.py`.**

A value that lands under `data/` must name three things: the artefact it was
read from, that artefact's sha256, and HOW it was read. This document is the
prose a stranger can apply; the dataclasses and `validate_row` are the contract
itself, and the tests are what hold it.

**Row-scoped, not document-scoped.** A row torn out of a file still carries its
own receipt. A header block at the top of a table describes the table on the day
it was written, and describes nothing at all about the row a consumer actually
read.

---

## 1. Why the third field exists

The schema would be worthless without the third field - HOW it was read. Four
things measured on 2026-09-07 are why.

1. **Independence must be COMPUTABLE, not asserted.** One account fact was
   described as read four ways. Two of those four were pixel reads of ONE crop,
   so the honest count was three. Two reads of one source are one fact, and no
   schema should depend on an author remembering to say so.
2. **An OCR row and an eye row are different evidence.** Tesseract returned a
   confident ZERO on a splash reading "Obtained New Character" with the text
   plainly on screen, in a stylised font over a full-screen effect. A machine
   read that says nothing is there is not the same claim as a person saying it.
3. **Not found at 1 fps is not not present.** A row from a sampled corpus
   without its sampling rate is unreportable. A negative is a claim about a
   SEARCH.
4. **Two consistent numbers are not evidence.** A character was recorded as a
   trial character on two numbers merely consistent with the hypothesis.
   Operator testimony later refuted it. Testimony therefore has to be
   recordable, or the refutation has nowhere to live.

---

## 2. The names

Everything lives in `core/provenance.py`. Nothing is added to `core/types.py`:
that file is the merge surface, and a brand-new contract with no consumers has
no business landing there. It becomes a consumer later, if ever, by a separate
deliberate change.

| Name | What it is |
|---|---|
| `ReadMethod` | HOW it was read. Seven members, pinned by a test |
| `EvidenceClass` | What KIND of evidence a method produces. Five members |
| `EVIDENCE_CLASS` | Frozen mapping, TOTAL over `ReadMethod` |
| `SourceKind` | WHAT was read - file, frame, crop, video segment, response, testimony |
| `SourceRef` | The artefact: locator, sha256, capture time, parent digest |
| `SamplingRef` | The corpus swept, its native rate and the rate examined |
| `ObservationStatus` | What the read established |
| `ProvenanceRecord` | ONE receipt |
| `DataRow` | The thing that lands under `data/`. Carries a non-empty tuple of receipts |
| `ProvenanceError` | Raised by `validate_row` |

### The read methods

`game_bytes` (a file the game itself wrote), `game_api` (a documented endpoint
answered), `human_eye` (a person read pixels), `vision_model` (a model read
pixels), `ocr` (tesseract or equivalent), `operator_statement` (a person said
it; no bytes exist), `derived` (computed from other records; read nothing).

`human_eye` and `vision_model` are separate because their failure modes differ:
a model confabulates plausibly, an eye misreads. `ocr` is separate from both
because of the confident zero.

### The statuses

`verified`, `measured_zero`, `not_found`, `unverified`, `retracted`.

`measured_zero` and `not_found` are deliberately distinct, and conflating them
is how a sampled sweep gets read as a fact. A surface that ANSWERED and answered
none is a measured zero. A sweep that found nothing is a claim about the sweep.

---

## 3. On-disk shape

One row envelope per line, JSON Lines, under a per-table directory inside
`data/`. Cost tables land under `data/costs/` once real numbers exist; the file
names are not fixed here and are deliberately not cited as paths, because a
pointer to a file nobody has written yet is a dead pointer.

Every line is one complete row serialized with sorted keys, ASCII-escaped, no
indent. One row, one line, one receipt set.

**Writing goes through `core/atomic_io.py` and nothing else.** `write_rows`
validates every row BEFORE any IO, builds the whole body as one string, and
calls the atomic writer ONCE. An append-mode open is banned outright, and a test
reads the module source to assert there is none: a reader polling mid-append sees
a torn last line, which is exactly the failure the atomic writer exists to
prevent. Appending a row is therefore read-then-rewrite, which is O(n) per row
and correct at this scale.

**Line endings.** `.gitattributes` declares eol=lf and
`tests/test_line_endings.py` fails any tracked file that declares it and carries
CRLF on disk. A row file written on Windows through a writer that translates
newlines turns the suite red while `git diff` shows nothing, because the index
normalises it. `tests/test_provenance.py` carries the arm that reads the written
BYTES back and asserts no CRLF pair is present.

`data/fixtures/` is out of scope and unchanged. It is hand-authored fixture
material, not observation, and the sweep skips it.

---

## 4. How independence is computed

For a receipt, the witness key is:

- a `derived` record: **no key**. A computation read nothing, so it cannot
  corroborate its own inputs.
- a retracted record: **no key**. A withdrawn reading that still counted towards
  support would make retraction cosmetic.
- a source with a `witness_group`: the group name.
- a testimony source: the locator. No bytes exist to digest.
- a source with a `parent_sha256`: the PARENT digest.
- otherwise: the source's own digest.

The count is the number of distinct keys.

**Worked, and this is the whole point.** A vision read and a tesseract read of
one crop share both the crop digest and the parent frame digest. Their keys are
equal, the set collapses, the count is 1. Add the game's own file: a different
digest, no parent, so a second key and a second witness. Add the game-created
directory name: a third. Pixels and bytes agreeing IS corroboration; two pixel
reads agreeing is not.

**The known limit, stated rather than papered over.** Two DIFFERENT frames of
one unchanged screen have different digests and count as two, which overcounts.
Perceptual similarity is a judgement and a guard that guessed at it would be
wrong in both directions, so the schema does not guess. An author collapses them
by hand with a named `witness_group`, and `witness_report` still reports the
shape - how many witnesses, of which evidence classes, and whether every one of
them is a machine read.

`ocr_only` is the flag the confident zero earns. Three OCR witnesses over three
distinct frames are still three OCR witnesses, and a consumer is entitled to
know that before it reads a zero as an absence.

`supporting_records(rows, claim)` returns every non-retracted receipt behind a
claim, in file order. When the only receipt is retracted, the support set is
EMPTY - which is the honest answer, and is what the two-consistent-numbers
episode needed.

---

## 5. Sampling - required, forbidden, optional

| Case | Sampling |
|---|---|
| status is `not_found` | **REQUIRED**, no exception |
| source is a video segment | **REQUIRED**. A segment is a corpus, not an artefact |
| source is a file, an HTTP response or testimony | **FORBIDDEN**. One artefact was read in full |
| source is a frame or a crop | **OPTIONAL** |

A `SamplingRef` names the corpus, the rate the corpus EXISTS at, the rate that
was actually examined, the counts, and the window. `examined_rate_hz` may not
exceed `native_rate_hz`: nobody examines frames that do not exist.

`population_count` of zero means UNKNOWN. It is allowed and it is STAMPED -
`coverage_notes` returns `coverage_unknown` for it - because a row asserting
absence over an uncounted population is not the same row as one asserting it
over a counted one.

Reading one named still is not sampling. FINDING a still by sweeping a corpus
is: the 4-second screenshot lane missed a screen entirely that the 15 fps
recording caught, and that lane's 0.25 Hz IS the reason it missed. Recording the
rate is the whole value of the field.

**The one design rule that is not mechanically decidable**, stated so nobody
assumes it is enforced: "an OCR record that came from a SWEEP must carry a rate"
cannot be decided from the record, because the same method reads one named still
and a whole recording. It is covered by the two rules that ARE decidable - a
`not_found` status and a video-segment source both require sampling - and every
OCR sweep in the measured corpus carries at least one of them.

---

## 6. The checked-count rule

**Every checker returns `(checked, offenders)`, and every caller asserts the
CHECKED COUNT before it looks at the offender list.** Zero out of zero reads as
a pass, and a checker never observed to fire is indistinguishable from a clean
tree.

- `check_evidence_class_totality()` - checked equals the number of read methods.
- `check_rows(rows)` - checked equals the number of rows examined.
- `sweep_data_dir(root)` - checked equals the number of JSONL lines examined,
  with `data/fixtures/` skipped.

Today `sweep_data_dir` over the real `data/` returns **zero checked**, and the
test asserts that zero EXPLICITLY and says in its own message that a pass there
proves nothing. The proof lives in the planted-corpus arm next to it, which
builds one valid row file and one whose row has no receipt. When the first real
row lands, the zero-checked test is the one whoever lands it must deliberately
update.

Every refusal arm is paired with an arm proving the legitimate neighbour
survives. A sweep that scores one hundred percent by refusing everything has
failed.

---

## 7. Account safety

**No account value may ever enter `data/`.** The capture store lives outside the
tree deliberately.

`validate_row` refuses a payload key, a payload string value or a locator naming
any of these fields: uid, authkey, authkey_ver, account_id, nickname, token,
session_key. The match is a case-insensitive substring and is deliberately
over-broad: a false refusal costs a rename, a false accept costs a leak into a
public repository.

A locator must be RELATIVE to a capture root named outside this tree. An
absolute path, a drive letter, a UNC share, an MSYS mount spelling and a parent
escape are each refused, which keeps `tests/test_machine_identity.py` from ever
having to catch a provenance row.

**The stated limit:** a bare account NUMBER sitting in a payload value is not
detectable here. No numeric shape distinguishes one from a level or an item id.
That remains a human rule, enforced over the tracked tree by
`tests/test_machine_identity.py`.

---

## 8. Open, and recorded rather than invented

- `PROVENANCE_SCHEMA_VERSION` starts at 1. Nothing yet defines what a bump
  obliges a reader to do, so `validate_row` refuses a version it does not know
  rather than guessing.
- A measured zero has a FRESHNESS - the wish-history endpoint lags - which is a
  different axis from a sampling rate and is not modelled. A freshness field
  would be the honest addition, appended at the end with a default.
- JSONL conflicts with the parked cost-loader suite, which writes a single
  nested JSON document. Zero rows exist, so nothing migrates, but whoever
  unparks that file must revise its loader arms.
- No signature, HMAC or attestation. A sha256 proves WHICH BYTES were read. It
  does not prove who read them, and a key would imply a trust model this project
  does not have and cannot honour on one machine.
- No numeric confidence score. `reader` stays a free string and `EvidenceClass`
  carries the part that is real; a float would imply a calibration nobody
  measured.

---

## 9. Where to look

- `core/provenance.py` - the contract.
- `tests/test_provenance.py` - what holds it, written failing-first.
- `data/README.md` - what may enter the directory.
- `data/costs/README.md` - the `source` field promise, and where it now comes
  from.
- `docs/GOAL_SPEC_SEED_TEAM.md` section 3.1 - unchanged. This schema describes
  HOW a first-hand number carries its receipt; it does not widen what counts as
  one.
- `docs/LICENSE_NOTES.md` - unchanged. The data posture is not relaxed here.
