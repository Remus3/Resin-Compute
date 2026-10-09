"""Artifact scoring - a weighted substat sum over caller-supplied tables.

The model is STATED in `docs/adr/ADR-012-artifact-scoring-model.md` before it
is built here, and this module carries NO number of its own. Every weight,
every per-roll magnitude and every tolerance arrives from the caller; the only
numerals in this file are zero and one, and a test walks the AST to keep it
so. `docs/SPEC_SCAFFOLD.md` verifies the SHAPE of a substat - an opaque stat
id and a value - and nothing else about artifacts, so any table shipped here
would be invented.

THE MODEL, restated from the ADR's Decision section for the reader of the code:

- A substat contributes `weight * value` when its id is a KEY of `weights`,
  including a key whose weight is zero. A stat whose id is absent is not
  scored and is returned in `unweighted`, so a typo in a weight table is
  visible rather than silently worth nothing. Weight keys matching no carried
  stat are ignored: a priority legitimately covers stats a piece lacks.
- The score is a left fold from zero over the substats IN CARRIED ORDER with
  plain binary addition - no rounding, no compensated summation - so a second
  implementation of this paragraph produces bit-identical floats.
- The main stat is excluded unless `include_main_stat` is set. Then it is
  looked up in the same `weights`, its contribution is added LAST, and it is
  reported apart in `main_stat`; if it has no weight its id is appended to
  `unweighted` after the substats. It is never roll-counted.
- Roll counting is an OPTIONAL layer that exists only when `magnitudes` is
  given: `rolls = floor((value + tolerance) / magnitude)`, with the raw
  `quotient = value / magnitude` returned so a caller may round differently.
  A stat with no magnitude is returned in `unresolved`. A quotient that
  overflows to infinity is refused with ValueError naming the stat, never
  left to `floor`. Upstream values may be display-rounded and the SPEC is
  silent on it, so the count is an estimate; the caller owns `tolerance`,
  which defaults to zero.
- Ranking is a sort: score descending, then every `MappedArtifact` field in
  declaration order. A non-finite score or a NaN in any float field is refused
  by name, because NaN is unordered and would let input order leak. The key
  compares by Python ordering, so two rows that differ only in the sign of a
  zero compare equal and keep input order; with that one stated exception a
  shuffled input yields an identical ranking, and no one field is privileged
  as "the" identity - in the fixture the item id is a type id that every piece
  of one kind shares.

Stat ids are the opaque strings `ingest/enka_mapper.py` carried. This module
names none of them.
"""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from core.types import MappedArtifact

__all__ = [
    "ArtifactScore",
    "RollCount",
    "WeightedStat",
    "rank_artifacts",
    "score_artifact",
]


@dataclass(frozen=True)
class WeightedStat:
    """One scored stat. `contribution` is `weight * value` and nothing more."""

    stat_id: str
    value: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class RollCount:
    """One substat measured against a caller-supplied per-roll magnitude.

    `quotient` is the raw `value / magnitude`. `rolls` is
    `floor((value + tolerance) / magnitude)`. Both estimate how many times the
    stat rolled, and the caller who supplied the magnitude owns the reading.
    """

    stat_id: str
    value: float
    magnitude: float
    quotient: float
    rolls: int


@dataclass(frozen=True)
class ArtifactScore:
    """The result of scoring one artifact.

    Carries the artifact itself rather than a bare id, so a caller never has
    to join rows back by an id that is not unique.
    """

    artifact: MappedArtifact
    score: float
    weighted: tuple[WeightedStat, ...]
    unweighted: tuple[str, ...]
    rolls: tuple[RollCount, ...] = ()
    unresolved: tuple[str, ...] = ()
    main_stat: WeightedStat | None = None


def _require_finite_weights(weights: Mapping[str, float]) -> None:
    for stat_id, weight in weights.items():
        if not math.isfinite(weight):
            raise ValueError(f"weight for stat {stat_id!r} is not finite: {weight!r}")


def _require_usable_magnitudes(magnitudes: Mapping[str, float]) -> None:
    for stat_id, magnitude in magnitudes.items():
        if not math.isfinite(magnitude) or magnitude <= 0.0:
            raise ValueError(f"magnitude for stat {stat_id!r} must be finite and positive: {magnitude!r}")


def _require_finite_tolerance(tolerance: float) -> None:
    if not math.isfinite(tolerance):
        raise ValueError(f"tolerance is not finite: {tolerance!r}")


def _weigh(stat_id: str, value: float, weights: Mapping[str, float]) -> WeightedStat | None:
    """Membership decides: a key with weight zero is weighted, an absent key is not."""
    if stat_id not in weights:
        return None
    weight = weights[stat_id]
    return WeightedStat(stat_id=stat_id, value=value, weight=weight, contribution=weight * value)


def _count_rolls(
    artifact: MappedArtifact, magnitudes: Mapping[str, float], tolerance: float
) -> tuple[tuple[RollCount, ...], tuple[str, ...]]:
    rolls: list[RollCount] = []
    unresolved: list[str] = []
    for stat_id, value in artifact.substats:
        if not math.isfinite(value):
            raise ValueError(f"carried value for stat {stat_id!r} is not finite: {value!r}")
        if stat_id not in magnitudes:
            unresolved.append(stat_id)
            continue
        magnitude = magnitudes[stat_id]
        quotient = value / magnitude
        shifted = (value + tolerance) / magnitude
        if not math.isfinite(quotient) or not math.isfinite(shifted):
            raise ValueError(f"roll quotient for stat {stat_id!r} is not finite: {value!r} over {magnitude!r}")
        rolls.append(
            RollCount(
                stat_id=stat_id,
                value=value,
                magnitude=magnitude,
                quotient=quotient,
                rolls=math.floor(shifted),
            )
        )
    return tuple(rolls), tuple(unresolved)


def score_artifact(
    artifact: MappedArtifact,
    weights: Mapping[str, float],
    *,
    magnitudes: Mapping[str, float] | None = None,
    tolerance: float = 0.0,
    include_main_stat: bool = False,
) -> ArtifactScore:
    """Score one artifact against caller-supplied `weights`.

    `weights` is required and has no default: a silent empty table would make
    every artifact score a plausible zero. Raises ValueError, naming the stat
    id or argument, for a non-finite weight, a non-finite or non-positive
    magnitude, a non-finite tolerance, or a non-finite carried value when
    `magnitudes` is supplied. Carried values are otherwise taken as-is; this
    engine does not police the mapper.
    """
    _require_finite_weights(weights)
    _require_finite_tolerance(tolerance)
    if magnitudes is not None:
        _require_usable_magnitudes(magnitudes)

    score = 0.0
    weighted: list[WeightedStat] = []
    unweighted: list[str] = []
    for stat_id, value in artifact.substats:
        entry = _weigh(stat_id, value, weights)
        if entry is None:
            unweighted.append(stat_id)
            continue
        weighted.append(entry)
        score = score + entry.contribution

    main_stat: WeightedStat | None = None
    if include_main_stat:
        main_stat = _weigh(artifact.main_stat_id, artifact.main_stat_value, weights)
        if main_stat is None:
            unweighted.append(artifact.main_stat_id)
        else:
            score = score + main_stat.contribution

    rolls: tuple[RollCount, ...] = ()
    unresolved: tuple[str, ...] = ()
    if magnitudes is not None:
        rolls, unresolved = _count_rolls(artifact, magnitudes, tolerance)

    return ArtifactScore(
        artifact=artifact,
        score=score,
        weighted=tuple(weighted),
        unweighted=tuple(unweighted),
        rolls=rolls,
        unresolved=unresolved,
        main_stat=main_stat,
    )


def _require_orderable(artifact: MappedArtifact) -> None:
    """NaN is unordered under Python, so a NaN anywhere in the sort key would
    make the ranking depend on input order. Refuse it by name."""
    if math.isnan(artifact.main_stat_value):
        raise ValueError(f"artifact {artifact.item_id!r} field main_stat_value is NaN and cannot be ordered")
    for stat_id, value in artifact.substats:
        if math.isnan(value):
            raise ValueError(f"artifact {artifact.item_id!r} substat {stat_id!r} value is NaN and cannot be ordered")


def _rank_key(scored: ArtifactScore) -> tuple[object, ...]:
    """Score descending, then every MappedArtifact field in declaration order."""
    return (-scored.score,) + dataclasses.astuple(scored.artifact)


def rank_artifacts(
    artifacts: Sequence[MappedArtifact],
    weights: Mapping[str, float],
    *,
    magnitudes: Mapping[str, float] | None = None,
    tolerance: float = 0.0,
    include_main_stat: bool = False,
) -> tuple[ArtifactScore, ...]:
    """Score every artifact and sort: score descending, then the full field tuple.

    Refused with ValueError, in input order: a non-finite score, then a NaN in
    `main_stat_value` or in any substat value - NaN is unordered and would make
    the result depend on input order. Rows differing only in the sign of a zero
    compare equal under Python ordering and keep input order; otherwise
    field-identical artifacts yield identical rows, so their mutual order is
    unobservable. Empty input returns an empty tuple.
    """
    scored = [
        score_artifact(
            artifact,
            weights,
            magnitudes=magnitudes,
            tolerance=tolerance,
            include_main_stat=include_main_stat,
        )
        for artifact in artifacts
    ]
    for row in scored:
        if not math.isfinite(row.score):
            raise ValueError(f"artifact {row.artifact.item_id!r} scored a non-finite value: {row.score!r}")
        _require_orderable(row.artifact)
    return tuple(sorted(scored, key=_rank_key))
