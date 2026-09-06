"""Absorbing-chain tests - SPEC 3.8.

These cover the DP itself: conservation of probability, absorption, the
guarantee and Fate Point bits, and the one deliberate deviation from the spec's
literal recurrence (documented at the top of `markov.py`).
"""
from __future__ import annotations

import pytest

from agents.pity_engine.banners import banner_config
from agents.pity_engine.markov import (
    consolidated_rate,
    expected_wishes_per_five_star,
    pull_distribution,
    solve,
)
from core.types import BannerKind, PityState

CHARACTER = banner_config(BannerKind.CHARACTER_EVENT)
WEAPON = banner_config(BannerKind.WEAPON_EVENT)
STANDARD = banner_config(BannerKind.STANDARD)
CHRONICLED = banner_config(BannerKind.CHRONICLED)


def test_distribution_is_a_probability_mass_function() -> None:
    solution = solve(CHARACTER, PityState(), 2, 100)
    assert len(solution.distribution) == 3
    assert sum(solution.distribution) == pytest.approx(1.0, abs=1e-9)
    assert all(mass >= 0.0 for mass in solution.distribution)
    # The absorbing bucket and the headline probability are the same number.
    assert solution.distribution[2] == solution.probability


def test_pull_distribution_sums_to_one_and_cannot_pay_out_at_zero() -> None:
    mass = pull_distribution(CHARACTER, PityState())
    assert mass[0] == 0.0
    assert sum(mass) == pytest.approx(1.0, abs=1e-9)
    assert all(m >= 0.0 for m in mass)
    # A first rate-up copy needs at most two full pity cycles.
    assert len(mass) - 1 <= 2 * CHARACTER.hard_pity


def test_pull_distribution_respects_max_pulls() -> None:
    mass = pull_distribution(CHARACTER, PityState(), max_pulls=90)
    assert len(mass) == 91
    # 90 pulls from zero pity guarantees a 5-star but not a rate-up win, so the
    # truncated head sums to strictly less than one.
    assert 0.0 < sum(mass) < 1.0
    with pytest.raises(ValueError):
        pull_distribution(CHARACTER, PityState(), max_pulls=-1)


def test_guaranteed_five_star_at_hard_pity_minus_one_is_certain() -> None:
    """Pity 89 plus a guarantee means the very next pull is the rate-up."""
    solution = solve(CHARACTER, PityState(pity_5star=89, has_guarantee=True), 1, 1)
    assert solution.probability == 1.0
    assert solution.expected_pulls == pytest.approx(1.0, abs=1e-12)


def test_capturing_radiance_forced_win_at_three_losses() -> None:
    """SPEC 3.2's hard cap, exercised through the chain rather than the branch.

    No guarantee flag is set here. The certainty comes purely from sitting at
    three consecutive 50/50 losses, which is the state the brief's flat 50/50
    model cannot represent at all.
    """
    state = PityState(pity_5star=89, has_guarantee=False, consecutive_5050_losses=3)
    assert solve(CHARACTER, state, 1, 1).probability == 1.0
    # One loss short of the cap it is emphatically not certain.
    near = PityState(pity_5star=89, has_guarantee=False, consecutive_5050_losses=2)
    assert solve(CHARACTER, near, 1, 1).probability < 0.6


def test_weapon_fate_point_makes_the_next_five_star_the_chosen_weapon() -> None:
    """SPEC 3.4. One Fate Point is the Epitomized Path cap since version 5.0."""
    at_hard_pity = PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=76, fate_points=1)
    assert solve(WEAPON, at_hard_pity, 1, 1).probability == 1.0

    # From zero pity the first 5-star arrives within 77 pulls, and with a Fate
    # Point banked it is certainly the charted weapon.
    fresh = PityState(banner=BannerKind.WEAPON_EVENT, fate_points=1)
    assert solve(WEAPON, fresh, 1, WEAPON.hard_pity).probability == pytest.approx(1.0, abs=1e-12)

    # Without the Fate Point, one 5-star taken at hard pity is the chosen weapon
    # exactly 37.5% of the time.
    without = PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=76, fate_points=0)
    assert solve(WEAPON, without, 1, 1).probability == pytest.approx(0.375, abs=1e-12)


def test_weapon_banner_ignores_the_character_guarantee_field() -> None:
    """The chain's single guarantee bit is the Fate Point on the weapon banner.

    SPEC 3.8 carries one bit and SPEC 3.4 already folds the weapon banner's
    featured-vs-off-banner guarantee into the flat 0.375, so honouring
    `has_guarantee` here as well would double-count it.
    """
    flagged = PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=76, has_guarantee=True)
    assert solve(WEAPON, flagged, 1, 1).probability == pytest.approx(0.375, abs=1e-12)


def test_standard_banner_has_no_rate_up_branch() -> None:
    """SPEC 3.7: every Wanderlust 5-star is a success, so hard pity is the answer."""
    assert solve(STANDARD, PityState(banner=BannerKind.STANDARD), 1, 90).probability == pytest.approx(1.0, abs=1e-12)
    assert solve(STANDARD, PityState(banner=BannerKind.STANDARD), 1, 89).probability < 1.0


def test_chronicled_is_a_flat_fifty_fifty_with_a_guarantee() -> None:
    """SPEC 3.7: 50.000% designated, and no Capturing Radiance."""
    # One 5-star, taken at hard pity so the budget cannot fit a second, is the
    # designated item exactly half the time.
    state = PityState(banner=BannerKind.CHRONICLED, pity_5star=89)
    assert solve(CHRONICLED, state, 1, 1).probability == pytest.approx(0.5, abs=1e-12)
    guaranteed = PityState(banner=BannerKind.CHRONICLED, pity_5star=89, has_guarantee=True)
    assert solve(CHRONICLED, guaranteed, 1, 1).probability == 1.0


def test_absorption_is_exact_within_two_pity_cycles() -> None:
    """Why `expected_pulls` is closed rather than truncated.

    Any 5-star either pays out or sets the guarantee bit that makes the next one
    pay out, so two full pity cycles per copy absorb the entire mass.
    """
    solution = solve(CHARACTER, PityState(), 1, 2 * CHARACTER.hard_pity)
    assert solution.probability == pytest.approx(1.0, abs=1e-12)
    assert solution.absorbed_by_pull[-1] == pytest.approx(1.0, abs=1e-12)
    assert 0.0 < solution.expected_pulls < 2 * CHARACTER.hard_pity


def test_absorbed_curve_is_monotone_and_starts_at_zero() -> None:
    curve = solve(CHARACTER, PityState(), 1, 0).absorbed_by_pull
    assert curve[0] == 0.0
    assert all(curve[i] <= curve[i + 1] + 1e-15 for i in range(len(curve) - 1))
    assert curve[-1] == pytest.approx(1.0, abs=1e-12)


def test_solve_rejects_impossible_states() -> None:
    with pytest.raises(ValueError, match="hard pity"):
        solve(CHARACTER, PityState(pity_5star=90), 1, 10)
    with pytest.raises(ValueError, match="target_count"):
        solve(CHARACTER, PityState(), 0, 10)
    with pytest.raises(ValueError, match="pull_budget"):
        solve(CHARACTER, PityState(), 1, -1)
    # Weapon hard pity is 77, so pity 78 is unreachable there even though it is
    # a perfectly ordinary character-banner state.
    with pytest.raises(ValueError, match="hard pity"):
        solve(WEAPON, PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=78), 1, 10)
    assert solve(CHARACTER, PityState(pity_5star=78), 1, 10).probability > 0.0


def test_radiance_carry_beats_the_spec_literal_recurrence() -> None:
    """SPEC 3.8.1 - the corrected win branch, measured where the cap bites.

    The spec's original win branch `f[min(k+1,N), 0, 0, 0]` resets the 50/50
    loss counter on EVERY win, guaranteed wins included. A guaranteed 5-star is
    not a contested roll, so under that literal reading `r` alternates 0, 1, 0,
    1 and the forced win at three losses is unreachable dead code.

    The test MUST start at `consecutive_5050_losses = 2`. On this banner each
    loss is immediately redeemed by a guaranteed win, so the streak can only
    climb one step per copy obtained - from a fresh state the cap cannot bite
    before absorption and the two policies are equal to within float noise. A
    strict inequality from a default start state is therefore decided by the
    last bit rather than by the model, and empirically that noise points the
    WRONG way. Magnitudes below are measured, not predicted.
    """
    banked = PityState(consecutive_5050_losses=2)
    carried = solve(CHARACTER, banked, 2, 200, carry_radiance_through_guarantee=True)
    literal = solve(CHARACTER, banked, 2, 200, carry_radiance_through_guarantee=False)

    # Measured: +9.2385e-02 probability, -1.4290e+01 expected pulls.
    assert carried.probability - literal.probability == pytest.approx(0.092385, abs=1e-5)
    assert literal.expected_pulls - carried.expected_pulls == pytest.approx(14.290, abs=1e-2)

    # Control, and the reason the community simplification survives in the wild:
    # from a fresh state the cap never gets the chance to fire, so the literal
    # reading is indistinguishable rather than merely close.
    fresh = PityState()
    fresh_carried = solve(CHARACTER, fresh, 2, 200, carry_radiance_through_guarantee=True)
    fresh_literal = solve(CHARACTER, fresh, 2, 200, carry_radiance_through_guarantee=False)
    assert fresh_carried.probability == pytest.approx(fresh_literal.probability, abs=1e-12)

    # Both remain valid distributions - the correction changes the answer, not
    # the conservation of probability.
    for solution in (carried, literal, fresh_carried, fresh_literal):
        assert sum(solution.distribution) == pytest.approx(1.0, abs=1e-9)


def test_consolidated_rate_and_expected_wishes_reject_an_empty_table() -> None:
    with pytest.raises(ValueError):
        expected_wishes_per_five_star((0.0,))
    with pytest.raises(ValueError):
        consolidated_rate(())


def test_solver_is_deterministic() -> None:
    """Pure function: identical arguments, identical floats, every time."""
    first = solve(CHARACTER, PityState(pity_5star=40), 1, 60)
    second = solve(CHARACTER, PityState(pity_5star=40), 1, 60)
    assert first == second
