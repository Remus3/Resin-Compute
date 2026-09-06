"""Recommendation solver - "what should I build next", scored transparently.

Every axis is a named weight constant, every axis contributes a sentence to the
rationale, and the rationale is assembled from the axes that ACTUALLY fired. A
recommender that cannot say why it recommended something is a tier list with
extra steps, and this module refuses to be one.

STATED ASSUMPTIONS:

- **No roster, tier list or meta ranking lives here.** Candidates arrive from
  the caller. This module knows how to COMPARE candidates; it does not know
  which characters exist, and it must not learn.
- **`account_value` is caller-supplied and unitless.** It is whatever the
  caller means by immediate account value - abyss clears, domain throughput,
  overworld comfort. The engine only divides it by resin and normalizes.
- **Normalization is relative to the candidate set**, so a score is a ranking
  within one call and is not comparable across calls with different candidates.
  The rationale quotes the RAW numbers for exactly that reason.
- **Ties break on a stable key**, `(subject_id, kind, node_id)`, so a shuffled
  candidate list yields an identical ranking.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from core.types import AccountState, Element, ObjectiveKind, ObjectiveNode, Recommendation
from engines.objectives import ObjectiveGraph, build_graph

__all__ = [
    "WEIGHT_COVERAGE_GAP",
    "WEIGHT_NEAR_COMPLETION",
    "WEIGHT_UNBLOCKS",
    "WEIGHT_VALUE_PER_RESIN",
    "Candidate",
    "ScoredAxis",
    "coverage_gaps",
    "recommend",
    "score_candidate",
]

# ---------------------------------------------------------------------------
# Weights - the whole scoring model, in four numbers
# ---------------------------------------------------------------------------

#: Filling a missing element on the roster. Weighted highest because an element
#: the account cannot field at all is a capability gap, not a marginal upgrade.
WEIGHT_COVERAGE_GAP: float = 40.0

#: Immediate account value per unit of resin spent. The efficiency axis.
WEIGHT_VALUE_PER_RESIN: float = 25.0

#: How many other goals this one unblocks, from the DAG. A prerequisite that
#: gates six downstream nodes is worth more than an isolated leaf.
WEIGHT_UNBLOCKS: float = 20.0

#: How close the goal already is to done. Finishing beats starting.
WEIGHT_NEAR_COMPLETION: float = 15.0


@dataclass(frozen=True)
class Candidate:
    """One thing the caller is considering doing.

    Every field is caller-supplied. `node_id` ties the candidate to a node in
    the account's goal DAG so the unblocks axis can count dependents; leave it
    empty and that axis simply scores zero rather than guessing.
    """

    subject_id: int
    kind: ObjectiveKind
    element: Element | None = None
    account_value: float = 0.0
    resin_cost: int = 0
    progress: float = 0.0
    node_id: str = ""
    estimated_days: int = 0
    display_name: str = ""


@dataclass(frozen=True)
class ScoredAxis:
    """One axis' contribution to one candidate's score.

    `raw` is the measured quantity, `normalized` is that quantity mapped to
    0.0..1.0 across the candidate set, and `note` is the clause this axis
    contributes to the rationale when it fires.
    """

    name: str
    weight: float
    raw: float
    normalized: float
    note: str

    @property
    def points(self) -> float:
        return self.weight * self.normalized

    @property
    def fired(self) -> bool:
        return self.normalized > 0.0


def coverage_gaps(account: AccountState) -> tuple[Element, ...]:
    """Elements the roster cannot field at all.

    Returned in `Element` declaration order, not set order, so the result is
    deterministic. A roster entry whose element is unknown contributes nothing
    rather than being guessed at - an unmapped element is missing information,
    not evidence of absence.
    """
    covered = {character.element for character in account.roster if character.element is not None}
    return tuple(element for element in Element if element not in covered)


def _normalize(value: float, peak: float) -> float:
    """Map a raw value onto 0.0..1.0 against the set maximum."""
    if peak <= 0.0:
        return 0.0
    return max(0.0, min(1.0, value / peak))


def _percent(value: float) -> int:
    return int(round(value * 100))


def _unblocked_count(graph: ObjectiveGraph | None, node_id: str) -> int:
    if graph is None or not node_id or node_id not in graph:
        return 0
    return len(graph.transitive_dependents(node_id))


def score_candidate(
    candidate: Candidate,
    gaps: Sequence[Element],
    graph: ObjectiveGraph | None,
    peak_value_per_resin: float,
    peak_unblocked: float,
) -> tuple[float, tuple[ScoredAxis, ...]]:
    """Score ONE candidate and return its axes alongside the total.

    Exposed rather than kept private so a caller - or a test - can inspect why
    a candidate placed where it did without re-deriving the arithmetic.
    """
    axes: list[ScoredAxis] = []

    fills_gap = candidate.element is not None and candidate.element in gaps
    element_name = candidate.element.value if candidate.element is not None else "unknown"
    axes.append(
        ScoredAxis(
            name="coverage_gap",
            weight=WEIGHT_COVERAGE_GAP,
            raw=1.0 if fills_gap else 0.0,
            normalized=1.0 if fills_gap else 0.0,
            note=f"covers {element_name}, which the roster cannot field at all",
        )
    )

    per_resin = candidate.account_value / max(candidate.resin_cost, 1)
    axes.append(
        ScoredAxis(
            name="value_per_resin",
            weight=WEIGHT_VALUE_PER_RESIN,
            raw=per_resin,
            normalized=_normalize(per_resin, peak_value_per_resin),
            note=f"returns {per_resin:.2f} account value per resin",
        )
    )

    unblocked = _unblocked_count(graph, candidate.node_id)
    plural = "goal" if unblocked == 1 else "goals"
    axes.append(
        ScoredAxis(
            name="unblocks",
            weight=WEIGHT_UNBLOCKS,
            raw=float(unblocked),
            normalized=_normalize(float(unblocked), peak_unblocked),
            note=f"unblocks {unblocked} downstream {plural}",
        )
    )

    progress = max(0.0, min(1.0, candidate.progress))
    axes.append(
        ScoredAxis(
            name="near_completion",
            weight=WEIGHT_NEAR_COMPLETION,
            raw=progress,
            normalized=progress,
            note=f"already {_percent(progress)} percent complete",
        )
    )

    total = sum(axis.points for axis in axes)
    return total, tuple(axes)


def _rationale(candidate: Candidate, axes: Sequence[ScoredAxis]) -> str:
    """Build a human sentence from the axes that fired.

    Never empty and never generic: when nothing fires, the sentence says which
    four things were checked and found absent, which is itself actionable - it
    tells the reader the candidate was not filtered out silently.
    """
    label = candidate.display_name or f"{candidate.kind.value} {candidate.subject_id}"
    fired = [axis for axis in axes if axis.fired]
    if not fired:
        return (
            f"{label} scores nothing on any axis: it fills no element gap, "
            f"unblocks no other goal, has no recorded progress and returns no "
            f"value per resin"
        )
    ranked = sorted(fired, key=lambda axis: (-axis.points, axis.name))
    return f"{label} " + "; ".join(axis.note for axis in ranked)


def recommend(
    account: AccountState,
    candidates: Iterable[Candidate],
    limit: int = 5,
    nodes: Iterable[ObjectiveNode] | None = None,
) -> tuple[Recommendation, ...]:
    """Rank `candidates` for this account and return the top `limit`.

    `nodes` supplies the goal DAG used by the unblocks axis and defaults to
    `account.goals`. Sorting is by descending score then by the stable key
    `(subject_id, kind, node_id)`, so an equal-scoring pair always comes back in
    the same order regardless of input order.
    """
    if limit < 0:
        raise ValueError(f"limit cannot be negative, got {limit}")

    pool = tuple(candidates)
    if not pool:
        return ()

    source = tuple(nodes) if nodes is not None else tuple(account.goals)
    graph = build_graph(source) if source else None
    gaps = coverage_gaps(account)

    peak_value_per_resin = max(
        (candidate.account_value / max(candidate.resin_cost, 1) for candidate in pool),
        default=0.0,
    )
    peak_unblocked = float(
        max((_unblocked_count(graph, candidate.node_id) for candidate in pool), default=0)
    )

    scored: list[tuple[float, Candidate, tuple[ScoredAxis, ...]]] = []
    for candidate in pool:
        total, axes = score_candidate(
            candidate,
            gaps,
            graph,
            peak_value_per_resin,
            peak_unblocked,
        )
        scored.append((total, candidate, axes))

    scored.sort(key=lambda row: (-row[0], row[1].subject_id, row[1].kind.value, row[1].node_id))

    return tuple(
        Recommendation(
            subject_id=candidate.subject_id,
            kind=candidate.kind,
            score=total,
            rationale=_rationale(candidate, axes),
            estimated_days=candidate.estimated_days,
            display_name=candidate.display_name,
        )
        for total, candidate, axes in scored[:limit]
    )
