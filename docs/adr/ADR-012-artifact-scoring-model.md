# ADR-012: Artifact scoring is a weighted substat sum over caller-supplied tables; no number ships

**Status:** Proposed, 2026-10-04 (adjudicated; operator confirmation pending)
**Closes:** the "stated scoring model before implementation" requirement of
the Artifact scoring row under `## Next` in `ROADMAP.md`

Disambiguation: `ops/loop/winmutex.py:10` cites an "ADR-012" that belongs to
the tree which publishes that shared, byte-pinned file. It is not this record,
and that file is not touched by this decision.

## Context

`MappedArtifact` (`core/types.py:229-239`) carries each substat as an opaque
stat id and a value, in wire order, exactly as `ingest/enka_mapper.py::map_artifact`
reads them from `flat.reliquarySubstats` (the read is
`ingest/enka_mapper.py:256`; each pair is carried through at
`ingest/enka_mapper.py:263`), and the main stat as `main_stat_id` and
`main_stat_value`. `ROADMAP.md` has said since the type landed that nothing
scores a substat roll and that the model must be stated before it is built.

What the SPEC verifies about artifacts is the shape and nothing else:
`docs/SPEC_SCAFFOLD.md:353` lists `reliquaryMainstat` and `reliquarySubstats`
under `flat`, and `docs/SPEC_SCAFFOLD.md:355` gives `reliquarySubstats` as
`[{appendPropId, propValue}]`. It states NO per-roll magnitude, NO stat-weight
table, NO prop-id vocabulary, NO substat count per rarity and NO main-stat
scaling. A grep of the SPEC for "roll" and "magnitude" hits only the gacha
section. The SPEC's acceptance list requires that every external field and id
a slice relies on appears in the SPEC and that nothing is invented, and
`docs/adr/ADR-002-data-posture.md` forbids vendoring game data. Together they
leave exactly one honest model: every table is supplied by the caller, and
the engine ships no number.

The one artifact any test here can see is in
`data/fixtures/enka_sample_profile.json:159-172`, a hand-authored fixture that
carries a file-level synthetic flag and labels its ids and name hashes as
deliberately unrealistic placeholders. It makes no claim about its stat
VALUES, and neither does this record: whether any of them coincides with a
value in the game is unverified and unverifiable here (see the common-mode
risk below), and they appear in this record and in the tests only as
arithmetic inputs to the weighted sum.

## Criteria, in priority order

1. **No invented or searched number.** The module's numerals are zero and one
   and nothing else, in either integer or float spelling.
2. **Pure and typed.** A deterministic function over `MappedArtifact` with no
   I/O, no change to `core/types.py`, and result dataclasses defined in the
   engine module, as `engines/recommend.py` does.
3. **Opaque ids, generic names.** Stat ids stay the strings the mapper carried;
   no real upstream prop id appears; identifiers are generic English (artifact,
   substat, roll, score, weight) per the trademark posture in
   `docs/SPEC_SCAFFOLD.md` and `docs/LICENSE_NOTES.md`.
4. **Statable to reproducibility.** A second implementer following the Decision
   section alone produces byte-identical outputs.
5. **Answers the roadmap row.** Ranks pieces for a stated priority, and counts
   rolls when the caller supplies magnitudes.
6. **Lands cleanly.** Status honest about operator confirmation; header in the
   shape of `docs/adr/ADR-011-main-provenance.md`; the docs guards hold; the
   backticked `engines/artifact_score.py` exists in the same commit as this file.

## Decision

The model is a **weighted substat sum**, implemented in `engines/artifact_score.py`
and exported from `engines/__init__.py`, with roll counting as an optional
layer and ranking as a sort. The rules below are the whole model; a second
implementer following this section produces byte-identical outputs.

1. `weights: Mapping[str, float]` is REQUIRED and has no default. A silent
   empty default would make every artifact score a plausible zero, the
   anti-pattern `docs/adr/ADR-005-companion-shell.md` names.
2. Membership decides weighting. A stat whose id is a key of `weights` is
   WEIGHTED, including a key whose weight is zero, and contributes
   `weight * value`. A stat whose id is absent is listed in `unweighted`.
   Zero and missing differ.
3. Weight keys matching no carried stat contribute nothing and are not
   listed: a priority legitimately covers stats a piece lacks. They are still
   VALIDATED - rule 7 checks every key of `weights` and every key of
   `magnitudes` before any scoring, matched or not, so a non-finite weight or
   a non-positive magnitude on an absent stat still raises. `unweighted` makes
   a typo in a carried stat's id visible.
4. Summation is a left fold from the float `0.0` over the substats in CARRIED
   order with plain binary addition. Not `math.fsum`, not sorted, not rounded
   anywhere; the result is a float even when nothing was weighted.
5. The main stat is excluded by default (`include_main_stat=False`). When
   included it is looked up in the same `weights`, its contribution
   `weight * main_stat_value` is added LAST after every substat, and it is
   reported apart in `main_stat`, never in `weighted`; if its id has no weight,
   `main_stat` is `None` and the id is appended to `unweighted` after the
   substats. It is never roll-counted. When excluded, `main_stat` is `None`
   and the id appears in no result field.
6. Rolls exist only when `magnitudes` is not `None`. For each substat in
   carried order: a present magnitude yields
   `RollCount(stat_id, value, magnitude, quotient=value / magnitude,
   rolls=floor((value + tolerance) / magnitude))`; an absent one appends the
   id to `unresolved`. Both `value / magnitude` and
   `(value + tolerance) / magnitude` must be finite: if either overflows to
   infinity, rule 7 raises `ValueError` naming the stat id rather than letting
   `floor` raise `OverflowError`. With `magnitudes=None`, `rolls` and
   `unresolved` are both empty.
7. Validation raises `ValueError` naming the offending stat id or argument,
   and the checks run in THIS order. Before any scoring: every key of
   `weights` must be finite; then `tolerance` must be finite - checked even
   when `magnitudes` is `None`; then, when `magnitudes` is supplied, every
   key of it must be finite and positive. After the sum and the main stat
   have been folded, while rolls are counted in carried order: each carried
   substat value must be finite and each quotient of rule 6 must be finite.
   The fold itself raises nothing, so a multi-fault input names the first
   offender in that order, in every implementation. Carried values are
   otherwise taken as-is; the engine does not police the mapper.
8. `tolerance: float = 0.0` is keyword-only, in STAT units, added to the value
   before the division. Its default is zero, so no hidden number. The
   `quotient` excludes it.
9. A duplicate stat id in `substats` is scored and listed once per carried
   entry, so `unweighted` and `unresolved` may repeat an id.
10. `rank_artifacts` scores every artifact in input order (rule 7 errors
    propagate), then refuses with `ValueError` a row whose score is not
    finite or whose `main_stat_value` or any substat value is NaN, naming
    the field or the stat id - NaN is unordered under Python and would make
    the sort depend on input order. The refusal order is fixed so the name
    is deterministic on a multi-fault list: rows are checked in input order,
    and within a row the score check runs first, then `main_stat_value`, then
    the substats in carried order; the first fault found is the one named.
    It then sorts by
    `(-score,)` followed by `dataclasses.astuple(artifact)` ascending: score
    descending, then every `MappedArtifact` field in declaration order
    (`item_id`, `set_name_hash`, `rank_level`, `level`, `main_stat_id`,
    `main_stat_value`, `substats`, `equip_type`). The key compares by
    Python's ordering, and `-0.0 == 0.0`, so two rows that differ only in the
    sign of a zero compare equal and keep their input order (the sort is
    stable); that is the one stated exception. Otherwise field-identical
    artifacts yield identical rows, so their mutual order is unobservable, and
    a shuffled input yields an identical ranking. Empty input returns an empty
    tuple. There is no limit argument.
11. Result rows carry the `artifact` itself, not a bare item id, because the
    item id is not unique (see Evidence).
12. The public names are exported through `engines/__init__.py`, as the
    recommendation solver's are.

Signatures, as implemented:

    @dataclass(frozen=True)
    class WeightedStat: stat_id: str; value: float; weight: float; contribution: float

    @dataclass(frozen=True)
    class RollCount: stat_id: str; value: float; magnitude: float; quotient: float; rolls: int

    @dataclass(frozen=True)
    class ArtifactScore:
        artifact: MappedArtifact
        score: float
        weighted: tuple[WeightedStat, ...]
        unweighted: tuple[str, ...]
        rolls: tuple[RollCount, ...] = ()
        unresolved: tuple[str, ...] = ()
        main_stat: WeightedStat | None = None

    def score_artifact(artifact, weights, *, magnitudes=None, tolerance=0.0,
                       include_main_stat=False) -> ArtifactScore
    def rank_artifacts(artifacts, weights, *, magnitudes=None, tolerance=0.0,
                       include_main_stat=False) -> tuple[ArtifactScore, ...]

The module may spell only the numerals zero and one, may import only
`__future__` (annotations), `collections.abc`, `dataclasses`, `math` and
`core.types`, and may contain no string literal shaped like an upstream prop
id. `tests/test_engines_artifact_score.py` walks the module's AST to enforce
all three, each arm paired with a mutant that proves the detector fires. The
NaN and overflow refusals above use `math.isnan` and `math.isfinite`, so they
add no numeral.

## Rejected alternatives

- **Roll counting as THE model.** Best argument: it alone answers the roadmap
  phrase "scores a substat roll" literally. Lost because it yields nothing
  without caller magnitudes that nothing in this tree can verify, and it
  rests on an assumption about upstream display rounding that the SPEC does
  not settle and that probing the live endpoint, which is forbidden here,
  could not settle either. It is a layer over the sum, not a primitive.
- **A normalized relative rank.** Best argument: parity with `_normalize` in
  `engines/recommend.py`. Lost because the score order already delivers the
  ranking; a figure relative to one call is exactly what that module's own
  header warns is not comparable across calls; and a caller can divide by the
  top score itself. `rank_artifacts` is a sort and nothing more.
- **Appending a field to `MappedArtifact`.** No model needs one, and a field
  would drag in the `core/state_io.py` codec and its tests for no gain.
- **A default weight table of any kind**, including the stat priorities in
  `docs/GOAL_SPEC_SEED_TEAM.md` section 3.4. Those are recorded there as
  unverified and not actionable, and a default table is a shipped number.
- **Normalising `-0.0` to `0.0` in the rank key, or adding the sign of zero
  to it.** Either would add a rule for a case no mapper output has produced,
  and the first would still leave the two rows tied. Stating the Python
  ordering and the input-order consequence is the smaller claim.

## Evidence, measured 2026-10-04

- A grep of `docs/SPEC_SCAFFOLD.md` for "roll" and "magnitude" hits only the
  gacha section; the SPEC carries no artifact numeral at all.
- The fixture artifact maps to two substats with values 7.8 and 9.9 under the
  fixture's placeholder ids, and a main stat of 4780.0 under its placeholder
  main-stat id. The fixture does not characterise these values and this
  record does not either; they are arithmetic inputs here and nothing more.
- Acceptance of the weighted sum, through the real mapper: `{}` scores 0.0
  with both ids unweighted; the first placeholder id at 1.0 scores 7.8; both
  at 1.0 score 17.7, and `0.0 + 7.8 + 9.9 == 17.7` is True under IEEE double
  precision, so `==` is the assertion given rule 4; `include_main_stat=True`
  with the main-stat placeholder id at 1.0 scores 4780.0; an empty
  `magnitudes` mapping lists both ids unresolved. No magnitude is paired with
  any fixture id anywhere in the tests.
- Roll counting is exercised on a hand-built artifact with opaque ids: a
  value of 5.9 against a magnitude of 2.0, where 2.0 is an arbitrary test
  magnitude chosen for nothing but the arithmetic, gives quotient 2.95
  (`5.9 / 2.0 == 2.95` under IEEE double precision) and rolls 2, which also
  tells floor from round; with a tolerance of 0.1 the rolls become 3 and the
  quotient stays 2.95.
- `itemId` in the fixture is a TYPE id: the one artifact and the two weapons
  carry consecutive placeholder ids of one shape, and `docs/SPEC_SCAFFOLD.md`
  gives `equipList` as `{itemId, ...}` with no instance id. Two pieces of one
  kind share it, so `(item_id, equip_type)` is not a total order and a stable
  sort keyed on it would leak input order. Hence rule 10.
- Every numeral in this record is a date, an ADR number, a line number, a
  rule, criterion or section number, zero, one, a value copied from the
  fixture, or a test-chosen value. The record asserts nothing about whether
  any of them coincides with a value in the game: that cannot be checked from
  this tree, and no such check was attempted.

## Known common-mode risk

Every candidate, the reader and this record share one input: the
`(appendPropId, propValue)` encoding at `ingest/enka_mapper.py:263` and the
SPEC's silence about everything beyond it. Weights are keyed by opaque
upstream ids that only the hand-authored SYNTHETIC_* ids ever exercise here,
so the arithmetic is tested and id stability and `propValue` rounding are
not, and cannot be from this tree. The same limit covers the fixture's stat
values: nothing here can say whether they resemble live ones. The residual is
settled only by an operator-observed live artifact compared against a
caller-held table, never by vendoring one.

## Consequences

- No default table ships. `docs/GOAL_SPEC_SEED_TEAM.md` section 3.4 stays
  unverified input: it is NOT a default weight table and NEVER a test
  expectation.
- Weights and magnitudes arrive from the caller or not at all. A caller with
  no table gets `unweighted` and `unresolved` lists, not a guess.
- No panel renders a score yet; this is an engine with tests and no surface.
- `README.md`, `docs/OVERVIEW.md` and `docs/GOAL_SPEC_SEED_TEAM.md` each
  say nothing scores a substat; those rows are stale once this lands and are
  to be moved to partial ("engine only, no table, no panel") in the same
  merge.

## What flips this to Accepted

Operator confirmation of this record, or a MAIN note verified as CLAUDE.md
requires. The flip edits the Status line here and the Status column of the
row in `docs/adr/README.md`, and nothing else.

## What would reverse this

- A SPEC-verified roll table. A superseding ADR would then add a sanctioned
  table as a named, cited constant, not a quiet default.
- A measured need for set-bonus scoring, which `set_name_hash` cannot express
  today because it is a hash and not a set identity.
- A demonstrated case where the carried order is not the wire order, which
  would make rule 4 a statement about the mapper rather than about the engine.
- A mapper output carrying `-0.0`, which would make the signed-zero exception
  of rule 10 a live case rather than a stated edge.
