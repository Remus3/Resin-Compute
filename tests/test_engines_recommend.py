"""Tests for the recommendation solver.

No roster, tier list or meta ranking appears in this file, because none appears
in the module under test. Every candidate here is constructed by the test, which
is exactly how a caller supplies them.
"""
from __future__ import annotations

import random

import pytest

from core.types import (
    AccountState,
    Element,
    MappedCharacter,
    ObjectiveKind,
    ObjectiveNode,
    Recommendation,
)
from engines.recommend import (
    WEIGHT_COVERAGE_GAP,
    WEIGHT_NEAR_COMPLETION,
    WEIGHT_UNBLOCKS,
    WEIGHT_VALUE_PER_RESIN,
    Candidate,
    coverage_gaps,
    recommend,
    score_candidate,
)


def character(avatar_id: int, element: Element | None) -> MappedCharacter:
    return MappedCharacter(
        avatar_id=avatar_id,
        level=90,
        ascension=6,
        constellations=0,
        element=element,
    )


def account(*elements: Element | None, goals: tuple[ObjectiveNode, ...] = ()) -> AccountState:
    roster = tuple(character(700 + idx, element) for idx, element in enumerate(elements))
    return AccountState(uid="900000001", roster=roster, goals=goals)


def node(node_id: str, *deps: str) -> ObjectiveNode:
    return ObjectiveNode(
        node_id=node_id,
        kind=ObjectiveKind.CHARACTER_ASCENSION,
        subject_id=1,
        target_value=1,
        depends_on=tuple(deps),
    )


def diamond() -> tuple[ObjectiveNode, ...]:
    """root gates two branches which gate a join, plus one isolated leaf."""
    return (node("root"), node("left", "root"), node("right", "root"), node("join", "left", "right"), node("leaf"))


def candidate(subject_id: int, **kwargs) -> Candidate:
    base = {"subject_id": subject_id, "kind": ObjectiveKind.CHARACTER_ASCENSION}
    base.update(kwargs)
    return Candidate(**base)


# ---------------------------------------------------------------------------
# Coverage gaps
# ---------------------------------------------------------------------------


def test_coverage_gaps_returns_exactly_the_missing_elements():
    state = account(Element.PYRO, Element.HYDRO, Element.ANEMO)
    assert coverage_gaps(state) == (Element.ELECTRO, Element.DENDRO, Element.CRYO, Element.GEO)


def test_coverage_gaps_is_empty_for_a_complete_roster():
    assert coverage_gaps(account(*list(Element))) == ()


def test_coverage_gaps_on_an_empty_roster_is_every_element():
    assert coverage_gaps(account()) == tuple(Element)


def test_coverage_gaps_ignores_characters_with_an_unknown_element():
    # An unmapped element is missing information, not evidence of absence, so
    # it must not silently cover anything.
    state = account(Element.PYRO, None)
    gaps = coverage_gaps(state)
    assert Element.PYRO not in gaps
    assert len(gaps) == len(Element) - 1


def test_coverage_gaps_order_is_the_enum_order_not_set_order():
    for _ in range(5):
        assert coverage_gaps(account(Element.GEO)) == tuple(e for e in Element if e is not Element.GEO)


def test_duplicate_elements_on_the_roster_do_not_change_the_gaps():
    assert coverage_gaps(account(Element.PYRO, Element.PYRO)) == coverage_gaps(account(Element.PYRO))


# ---------------------------------------------------------------------------
# Axes
# ---------------------------------------------------------------------------


def test_filling_an_element_gap_outranks_an_otherwise_identical_candidate():
    state = account(Element.PYRO)  # everything but pyro is missing
    covered = candidate(1, element=Element.PYRO, account_value=10.0, resin_cost=20)
    gap_filler = candidate(2, element=Element.CRYO, account_value=10.0, resin_cost=20)
    ranked = recommend(state, [covered, gap_filler])
    assert ranked[0].subject_id == 2
    assert ranked[0].score - ranked[1].score == pytest.approx(WEIGHT_COVERAGE_GAP)


def test_value_per_resin_axis_prefers_the_cheaper_route_to_the_same_value():
    state = account(*list(Element))  # no gaps, so only efficiency can move it
    cheap = candidate(1, account_value=100.0, resin_cost=10)
    dear = candidate(2, account_value=100.0, resin_cost=100)
    ranked = recommend(state, [dear, cheap])
    assert ranked[0].subject_id == 1
    assert ranked[0].score == pytest.approx(WEIGHT_VALUE_PER_RESIN)


def test_the_unblocks_axis_counts_transitive_dependents_from_the_dag():
    state = account(*list(Element), goals=diamond())
    root = candidate(1, node_id="root")
    isolated = candidate(2, node_id="leaf")
    ranked = recommend(state, [isolated, root])
    assert ranked[0].subject_id == 1
    # root gates left, right and join - three downstream goals.
    assert "unblocks 3 downstream goals" in ranked[0].rationale
    assert ranked[0].score == pytest.approx(WEIGHT_UNBLOCKS)


def test_a_candidate_with_no_node_id_simply_scores_zero_on_the_dag_axis():
    state = account(*list(Element), goals=diamond())
    ranked = recommend(state, [candidate(1)])
    assert ranked[0].score == pytest.approx(0.0)


def test_near_completion_axis_prefers_the_nearly_finished_goal():
    state = account(*list(Element))
    ranked = recommend(state, [candidate(1, progress=0.1), candidate(2, progress=0.9)])
    assert ranked[0].subject_id == 2
    assert ranked[0].score == pytest.approx(WEIGHT_NEAR_COMPLETION * 0.9)
    assert "90 percent complete" in ranked[0].rationale


def test_progress_outside_zero_to_one_is_clamped():
    state = account(*list(Element))
    ranked = recommend(state, [candidate(1, progress=5.0), candidate(2, progress=-3.0)])
    scores = {rec.subject_id: rec.score for rec in ranked}
    assert scores[1] == pytest.approx(WEIGHT_NEAR_COMPLETION)
    assert scores[2] == pytest.approx(0.0)


def test_score_candidate_exposes_every_axis_by_name():
    state = account(Element.PYRO)
    total, axes = score_candidate(
        candidate(1, element=Element.CRYO, account_value=10.0, resin_cost=10, progress=0.5),
        coverage_gaps(state),
        None,
        1.0,
        0.0,
    )
    assert {axis.name for axis in axes} == {
        "coverage_gap",
        "value_per_resin",
        "unblocks",
        "near_completion",
    }
    assert total == pytest.approx(sum(axis.points for axis in axes))


# ---------------------------------------------------------------------------
# Rationale
# ---------------------------------------------------------------------------


def test_every_recommendation_carries_a_non_empty_rationale():
    state = account(Element.PYRO, Element.GEO, goals=diamond())
    pool = [
        candidate(1, element=Element.CRYO, account_value=50.0, resin_cost=20, node_id="root", progress=0.4),
        candidate(2, element=Element.PYRO, account_value=5.0, resin_cost=60, node_id="leaf"),
        candidate(3),
        candidate(4, progress=1.0, display_name="fixture goal"),
    ]
    ranked = recommend(state, pool, limit=len(pool))
    assert len(ranked) == len(pool)
    for rec in ranked:
        assert isinstance(rec, Recommendation)
        assert rec.rationale.strip(), f"empty rationale for {rec.subject_id}"
        assert len(rec.rationale) > 20


def test_rationale_names_only_the_axes_that_actually_fired():
    state = account(Element.PYRO)
    only_progress = candidate(1, element=Element.PYRO, progress=0.5)
    rationale = recommend(state, [only_progress])[0].rationale
    assert "50 percent complete" in rationale
    assert "cannot field" not in rationale
    assert "unblocks 0" not in rationale


def test_a_candidate_that_fires_nothing_still_explains_itself_specifically():
    state = account(*list(Element))
    rationale = recommend(state, [candidate(1)])[0].rationale
    assert rationale.strip()
    assert "no element gap" in rationale
    assert "no recorded progress" in rationale


def test_rationale_uses_the_display_name_when_one_is_supplied():
    state = account(*list(Element))
    ranked = recommend(state, [candidate(1, progress=0.5, display_name="fixture goal")])
    assert ranked[0].rationale.startswith("fixture goal ")


# ---------------------------------------------------------------------------
# Determinism and limit
# ---------------------------------------------------------------------------


def test_tied_scores_break_on_a_stable_key():
    state = account(*list(Element))
    tied = [candidate(subject_id) for subject_id in (500, 100, 300, 200, 400)]
    ranked = recommend(state, tied, limit=len(tied))
    assert [rec.score for rec in ranked] == [0.0] * len(tied)
    assert [rec.subject_id for rec in ranked] == [100, 200, 300, 400, 500]


def test_ranking_is_identical_across_shuffled_input():
    state = account(Element.PYRO, Element.HYDRO, goals=diamond())
    pool = [
        candidate(10, element=Element.CRYO, account_value=30.0, resin_cost=20, node_id="root"),
        candidate(20, element=Element.PYRO, account_value=30.0, resin_cost=20, node_id="left"),
        candidate(30, progress=0.5, node_id="leaf"),
        candidate(40),
        candidate(50, account_value=1.0, resin_cost=1),
    ]
    baseline = recommend(state, pool, limit=len(pool))
    rng = random.Random(20260906)
    for attempt in range(20):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        run = recommend(state, shuffled, limit=len(pool))
        assert [rec.subject_id for rec in run] == [rec.subject_id for rec in baseline], f"drift on shuffle {attempt}"
        assert [rec.rationale for rec in run] == [rec.rationale for rec in baseline]


def test_identical_candidates_differing_only_in_id_come_back_in_id_order():
    state = account(*list(Element))
    pair = [candidate(9, progress=0.5), candidate(2, progress=0.5)]
    assert [rec.subject_id for rec in recommend(state, pair)] == [2, 9]
    assert [rec.subject_id for rec in recommend(state, list(reversed(pair)))] == [2, 9]


def test_limit_is_respected():
    state = account(Element.PYRO)
    pool = [candidate(i, progress=i / 10.0) for i in range(1, 8)]
    assert len(recommend(state, pool, limit=3)) == 3
    assert len(recommend(state, pool)) == 5  # documented default
    assert len(recommend(state, pool, limit=99)) == len(pool)
    assert recommend(state, pool, limit=0) == ()


def test_limit_keeps_the_highest_scoring_candidates():
    state = account(*list(Element))
    pool = [candidate(i, progress=i / 10.0) for i in range(1, 8)]
    top = recommend(state, pool, limit=2)
    assert [rec.subject_id for rec in top] == [7, 6]


def test_an_empty_candidate_pool_is_an_empty_result():
    assert recommend(account(Element.PYRO), []) == ()


def test_a_negative_limit_is_rejected():
    with pytest.raises(ValueError):
        recommend(account(Element.PYRO), [candidate(1)], limit=-1)


def test_nodes_argument_overrides_the_account_goals():
    state = account(*list(Element), goals=())
    ranked = recommend(state, [candidate(1, node_id="root")], nodes=diamond())
    assert ranked[0].score == pytest.approx(WEIGHT_UNBLOCKS)
    assert "unblocks 3 downstream goals" in ranked[0].rationale


def test_recommendation_carries_the_candidate_metadata_through():
    state = account(Element.PYRO)
    ranked = recommend(
        state,
        [candidate(77, kind=ObjectiveKind.ACQUIRE_CHARACTER, estimated_days=12, display_name="fixture")],
    )
    assert ranked[0].subject_id == 77
    assert ranked[0].kind is ObjectiveKind.ACQUIRE_CHARACTER
    assert ranked[0].estimated_days == 12
    assert ranked[0].display_name == "fixture"
