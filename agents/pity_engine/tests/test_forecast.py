"""Public API tests - SPEC 3.8.

`probability_of_success` is the function the original brief got wrong twice: it
omitted the pull budget entirely, and it invited a binomial on 1.6%. Both are
guarded here.
"""
from __future__ import annotations

import pytest

from agents.pity_engine import ENGINE_VERSION
from agents.pity_engine.banners import CAPTURING_RADIANCE_P
from agents.pity_engine.forecast import probability_of_success, pulls_needed_for_confidence
from core.types import BannerKind, ForecastResult, PityState


def test_engine_version_is_the_single_source_of_truth() -> None:
    assert ENGINE_VERSION == "0.1.0"


def test_zero_budget_cannot_succeed() -> None:
    """No pulls, no copies. The trivial anchor of the whole curve."""
    result = probability_of_success(PityState(), target_count=1, pull_budget=0)
    assert result.probability == 0.0
    assert result.distribution == (1.0, 0.0)


def test_result_is_a_populated_forecast_result() -> None:
    result = probability_of_success(PityState(pity_5star=80), target_count=1, pull_budget=10)
    assert isinstance(result, ForecastResult)
    assert result.pull_budget == 10
    assert result.target_count == 1
    assert result.banner is BannerKind.CHARACTER_EVENT
    assert 0.0 < result.probability < 1.0
    assert len(result.distribution) == 2
    assert sum(result.distribution) == pytest.approx(1.0, abs=1e-9)
    assert result.expected_pulls is not None
    assert result.expected_pulls > 0.0


def test_distribution_sums_to_one() -> None:
    for budget in (0, 1, 45, 90, 150):
        result = probability_of_success(PityState(), target_count=2, pull_budget=budget)
        assert sum(result.distribution) == pytest.approx(1.0, abs=1e-9)
        assert len(result.distribution) == 3


def test_probability_is_monotone_non_decreasing_in_pull_budget() -> None:
    """More pulls can never hurt. The single strongest sanity property here."""
    previous = -1.0
    for budget in (0, 1, 10, 45, 74, 90, 120, 180):
        current = probability_of_success(PityState(), target_count=1, pull_budget=budget).probability
        assert current >= previous - 1e-15, f"probability fell at budget {budget}"
        previous = current
    assert previous == pytest.approx(1.0, abs=1e-12)


def test_guaranteed_at_pity_89_with_one_pull_is_certain() -> None:
    state = PityState(pity_5star=89, has_guarantee=True)
    assert probability_of_success(state, target_count=1, pull_budget=1).probability == 1.0


def test_forecast_is_not_a_binomial_on_the_consolidated_rate() -> None:
    """SPEC 3.8's headline refutation, made falsifiable.

    A binomial on 1.6% would give the same answer for any pity, and would put
    90 pulls at `1 - 0.984 ** 90` = 0.766. The real chain is pity-sensitive: 90
    pulls guarantee a 5-star, so the answer at high pity is far higher and the
    answer from zero pity is set by the 50/50, not by a per-wish coin.
    """
    binomial = 1.0 - (1.0 - 0.016) ** 90
    fresh = probability_of_success(PityState(), target_count=1, pull_budget=90).probability
    deep = probability_of_success(PityState(pity_5star=80), target_count=1, pull_budget=90).probability
    assert fresh != pytest.approx(binomial, abs=1e-3)
    assert deep > fresh
    # Same budget, same target, different pity: a binomial cannot express this.
    assert deep - fresh > 0.1


def test_banner_argument_selects_the_curve() -> None:
    state = PityState(pity_5star=76)
    weapon = probability_of_success(state, 1, 1, banner=BannerKind.WEAPON_EVENT)
    character = probability_of_success(state, 1, 1, banner=BannerKind.CHARACTER_EVENT)
    # Pity 76 is hard pity on the weapon curve and only mid-ramp on the
    # character curve, so the same state answers very differently.
    assert weapon.probability == pytest.approx(0.375, abs=1e-12)
    assert character.probability == pytest.approx(0.246 * CAPTURING_RADIANCE_P, abs=1e-12)
    assert weapon.probability > character.probability
    assert weapon.banner is BannerKind.WEAPON_EVENT


def test_weapon_fate_point_certainty_through_the_public_api() -> None:
    state = PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=76, fate_points=1)
    result = probability_of_success(state, 1, 1, banner=BannerKind.WEAPON_EVENT)
    assert result.probability == 1.0
    assert result.expected_pulls == pytest.approx(1.0, abs=1e-12)


def test_expected_pulls_matches_the_hand_solved_value() -> None:
    """E[pulls to a first rate-up copy] from a fresh character banner state.

    E[wishes per 5-star] is 62.297 (SPEC 3.1) and E[5-stars per rate-up copy] is
    `2 - CAPTURING_RADIANCE_P` from a clean slate, so Wald gives roughly 92.1
    pulls. This is the number a binomial on 1.6% would put at 62.3.
    """
    result = probability_of_success(PityState(), target_count=1, pull_budget=0)
    assert result.expected_pulls == pytest.approx(92.1, abs=1.0)


def test_more_copies_cost_more_pulls() -> None:
    one = probability_of_success(PityState(), 1, 0).expected_pulls
    two = probability_of_success(PityState(), 2, 0).expected_pulls
    assert one is not None and two is not None
    assert two > one


def test_validation_rejects_a_question_with_no_answer() -> None:
    with pytest.raises(ValueError, match="target_count"):
        probability_of_success(PityState(), target_count=0, pull_budget=10)
    with pytest.raises(ValueError, match="target_count"):
        probability_of_success(PityState(), target_count=-3, pull_budget=10)
    with pytest.raises(ValueError, match="pull_budget"):
        probability_of_success(PityState(), target_count=1, pull_budget=-1)
    with pytest.raises(ValueError, match="target_count"):
        probability_of_success(PityState(), target_count=1.5, pull_budget=10)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="pull_budget"):
        probability_of_success(PityState(), target_count=1, pull_budget=True)


def test_pulls_needed_for_confidence_is_the_inverse() -> None:
    state = PityState()
    needed = pulls_needed_for_confidence(state, 1, 0.9)
    assert needed > 0
    assert probability_of_success(state, 1, needed).probability >= 0.9
    assert probability_of_success(state, 1, needed - 1).probability < 0.9


def test_pulls_needed_for_confidence_edges() -> None:
    state = PityState()
    assert pulls_needed_for_confidence(state, 1, 0.0) == 0
    # Certainty is finite because hard pity bounds the worst case at two
    # 5-stars per copy.
    certain = pulls_needed_for_confidence(state, 1, 1.0)
    assert 0 < certain <= 180
    assert probability_of_success(state, 1, certain).probability == pytest.approx(1.0, abs=1e-12)
    # Higher confidence never costs fewer pulls.
    assert pulls_needed_for_confidence(state, 1, 0.5) <= pulls_needed_for_confidence(state, 1, 0.95)


def test_pulls_needed_for_confidence_validation() -> None:
    with pytest.raises(ValueError, match="confidence"):
        pulls_needed_for_confidence(PityState(), 1, 1.5)
    with pytest.raises(ValueError, match="confidence"):
        pulls_needed_for_confidence(PityState(), 1, -0.1)
    with pytest.raises(ValueError, match="target_count"):
        pulls_needed_for_confidence(PityState(), 0, 0.5)


def test_forecast_is_deterministic() -> None:
    args = (PityState(pity_5star=30, consecutive_5050_losses=1), 1, 60)
    assert probability_of_success(*args) == probability_of_success(*args)
