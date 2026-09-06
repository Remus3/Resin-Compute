"""Hazard-curve characterization tests.

Every assertion here is a boundary value from `docs/SPEC_SCAFFOLD.md` section 3.
Two of them are regression guards for defects in the ORIGINAL brief rather than
ordinary coverage, and are labelled as such:

- `test_weapon_curve_saturates_at_pity_77` guards SPEC 3.3.
- `test_capturing_radiance_*` guard SPEC 3.2.
"""
from __future__ import annotations

import pytest

from agents.pity_engine.banners import (
    CAPTURING_RADIANCE_CAP,
    CAPTURING_RADIANCE_P,
    CHARACTER_FIVE_STAR_TABLE,
    CHRONICLED_DESIGNATED_P,
    FIVE_STAR_ANCHOR_CHARACTER,
    FIVE_STAR_ANCHOR_WEAPON,
    FIVE_STAR_BASE_CHARACTER,
    FIVE_STAR_BASE_WEAPON,
    FIVE_STAR_INCREMENT_CHARACTER,
    FIVE_STAR_INCREMENT_WEAPON_DEFAULT,
    FOUR_STAR_TABLE_CHARACTER,
    FOUR_STAR_TABLE_WEAPON,
    WEAPON_FEATURED_SINGLE_P,
    banner_config,
    build_five_star_table,
    capturing_radiance_long_run_rate,
    character_rate_up,
    chronicled_rate_up,
    effective_hard_pity,
    standard_rate_up,
    weapon_five_star_table,
    weapon_rate_up,
)
from agents.pity_engine.markov import consolidated_rate, expected_wishes_per_five_star
from core.types import BannerKind

# ---------------------------------------------------------------------------
# SPEC 3.1 - Character Event Wish five-star curve
# ---------------------------------------------------------------------------


def test_character_table_boundary_pulls() -> None:
    table = CHARACTER_FIVE_STAR_TABLE
    assert table[1] == pytest.approx(0.006, abs=1e-12)
    assert table[73] == pytest.approx(0.006, abs=1e-12)
    # First ramp step: 0.006 + 0.06 * (74 - 73).
    assert table[74] == pytest.approx(0.066, abs=1e-12)
    assert table[89] == pytest.approx(0.966, abs=1e-12)
    assert table[90] == 1.0
    assert effective_hard_pity(table) == 90
    # The table STOPS at hard pity. Pity 91 is not a state that can exist.
    assert len(table) - 1 == 90


def test_character_p89_is_exactly_point_966() -> None:
    """The brief's "roughly 96.6%" is exact, not approximate."""
    assert abs(CHARACTER_FIVE_STAR_TABLE[89] - 0.966) < 1e-12


def test_character_hard_pity_is_a_clip_not_an_evaluation() -> None:
    """SPEC 3.1: the unclipped formula gives 1.026 at pity 90."""
    unclipped = FIVE_STAR_BASE_CHARACTER + FIVE_STAR_INCREMENT_CHARACTER * (90 - FIVE_STAR_ANCHOR_CHARACTER)
    assert unclipped == pytest.approx(1.026, abs=1e-12)
    assert unclipped > 1.0
    assert CHARACTER_FIVE_STAR_TABLE[90] == 1.0


def test_consolidated_rate_self_check() -> None:
    """The table's own self-check.

    HoYoverse publishes a consolidated 5-star probability of 1.600% for the
    Character Event Wish. This table computes 1.6052%. That 0.005pp agreement is
    the evidence the curve is transcribed correctly - a mis-typed hazard moves
    this aggregate far more than it moves any single entry.
    """
    rate_percent = 100.0 * consolidated_rate(CHARACTER_FIVE_STAR_TABLE)
    assert round(rate_percent, 4) == 1.6052


def test_expected_wishes_per_five_star() -> None:
    """SPEC 3.8: 1.600% is 1 / E, with E = 62.297 wishes. Never a Bernoulli p."""
    assert round(expected_wishes_per_five_star(CHARACTER_FIVE_STAR_TABLE), 3) == 62.297


def test_consolidated_rate_is_the_reciprocal_of_expected_wishes() -> None:
    table = CHARACTER_FIVE_STAR_TABLE
    assert consolidated_rate(table) == pytest.approx(1.0 / expected_wishes_per_five_star(table), rel=1e-15)


# ---------------------------------------------------------------------------
# SPEC 3.3 - THE SATURATION TEST, regression guard for the brief's defect
# ---------------------------------------------------------------------------


def test_weapon_curve_saturates_at_pity_77() -> None:
    """REGRESSION GUARD for the original brief's arithmetically impossible curve.

    The brief specified "increasing 7% per pull up to pull 79" with hard pity at
    80. With `P_n = 0.007 + 0.07 * (n - 62)`:

        P(76) = 0.987
        P(77) = 1.057   <- exceeds 1.0

    A 7% ramp from pull 63 SATURATES AT PULL 77, three pulls before the stated
    hard pity, so the briefed curve cannot reach pull 79 and pity 78..80 is
    unreachable under it. The brief's numbers are not merely imprecise, they
    describe a curve that does not exist. This test fails the moment anyone
    re-introduces a hand-written hard pity of 79 or 80 next to a 7% ramp.
    """
    table = weapon_five_star_table()

    assert table[62] == pytest.approx(FIVE_STAR_BASE_WEAPON, abs=1e-12)
    assert table[63] == pytest.approx(0.077, abs=1e-12)
    assert table[76] == pytest.approx(0.987, abs=1e-12)

    unclipped_77 = FIVE_STAR_BASE_WEAPON + FIVE_STAR_INCREMENT_WEAPON_DEFAULT * (77 - FIVE_STAR_ANCHOR_WEAPON)
    assert unclipped_77 == pytest.approx(1.057, abs=1e-12)
    assert unclipped_77 > 1.0

    assert table[77] == 1.0
    assert effective_hard_pity(table) == 77
    assert len(table) - 1 == 77, "pity 78, 79 and 80 are unreachable under the 0.07 increment"


def test_weapon_increment_is_tunable_and_moves_hard_pity() -> None:
    """SPEC 3.3: the increment is a parameter because the micro-curve is unpinned.

    Incidentally, this is where the brief's "up to pull 79" came from: a 79 hard
    pity is consistent with a ~6% ramp, never with the 7% the brief also stated.
    """
    assert effective_hard_pity(weapon_five_star_table(0.06)) == 79
    assert effective_hard_pity(weapon_five_star_table(FIVE_STAR_INCREMENT_WEAPON_DEFAULT)) == 77
    assert effective_hard_pity(weapon_five_star_table(0.10)) == 72
    # The config factory threads the tuning parameter through unchanged.
    assert banner_config(BannerKind.WEAPON_EVENT, weapon_increment=0.06).hard_pity == 79


def test_build_five_star_table_rejects_nonsense() -> None:
    with pytest.raises(ValueError):
        build_five_star_table(0.0, 73, 0.06)
    with pytest.raises(ValueError):
        build_five_star_table(1.0, 73, 0.06)
    with pytest.raises(ValueError):
        build_five_star_table(0.006, 0, 0.06)
    with pytest.raises(ValueError):
        build_five_star_table(0.006, 73, 0.0)
    with pytest.raises(ValueError):
        # A ramp too shallow to clip inside the bound raises rather than hanging.
        build_five_star_table(0.006, 73, 1e-9, max_pity=50)


def test_effective_hard_pity_rejects_a_table_with_no_clip() -> None:
    with pytest.raises(ValueError):
        effective_hard_pity((0.0, 0.1, 0.2))


# ---------------------------------------------------------------------------
# SPEC 3.2 - Capturing Radiance, regression guard for the flat 50/50
# ---------------------------------------------------------------------------


def test_capturing_radiance_solves_to_the_published_55_percent() -> None:
    """REGRESSION GUARD for the brief's flat 50/50, obsolete since version 5.0.

    `CAPTURING_RADIANCE_P` is SOLVED, not observed: it is the per-roll win
    probability that, once the forced win at three consecutive losses is folded
    in, makes the long-run share of WON 50/50 rolls equal the official
    consolidated 55.000%.
    """
    rate = capturing_radiance_long_run_rate(CAPTURING_RADIANCE_P, CAPTURING_RADIANCE_CAP)
    assert round(rate, 4) == 0.55
    assert abs(rate - 0.55) < 1e-5


def test_flat_55_percent_with_the_cap_overshoots() -> None:
    """Why the naive value is wrong.

    Reading "55.000%" off the FAQ and using it as the per-roll probability
    double-counts the cap: the forced win at three losses adds its own wins on
    top, and the long-run rate lands at 57.35% instead of the published 55.000%.
    """
    rate = capturing_radiance_long_run_rate(0.55, CAPTURING_RADIANCE_CAP)
    assert round(rate, 4) == 0.5735
    assert rate > 0.55


def test_flat_50_percent_with_the_cap_undershoots() -> None:
    """The (.5, .5, .5, 1.0) reading lands at 53.33%, short of 55.000%."""
    assert round(capturing_radiance_long_run_rate(0.5, CAPTURING_RADIANCE_CAP), 4) == 0.5333


def test_uncapped_flat_50_percent_is_the_pre_5_0_behaviour() -> None:
    """Without the cap the model degenerates to exactly the briefed 50/50."""
    assert capturing_radiance_long_run_rate(0.5, cap=200) == pytest.approx(0.5, abs=1e-12)


def test_capturing_radiance_cap_edges() -> None:
    # cap 0 means every roll is forced, so the rate is 1.0.
    assert capturing_radiance_long_run_rate(0.5, cap=0) == pytest.approx(1.0, abs=1e-12)
    with pytest.raises(ValueError):
        capturing_radiance_long_run_rate(0.0)
    with pytest.raises(ValueError):
        capturing_radiance_long_run_rate(0.5, cap=-1)


# ---------------------------------------------------------------------------
# SPEC 3.5 - four-star curves
# ---------------------------------------------------------------------------


def test_four_star_character_table() -> None:
    table = FOUR_STAR_TABLE_CHARACTER
    assert table[1] == pytest.approx(0.051, abs=1e-12)
    assert table[8] == pytest.approx(0.051, abs=1e-12)
    assert table[9] == pytest.approx(0.561, abs=1e-12)
    assert table[10] == 1.0
    assert effective_hard_pity(table) == 10


def test_four_star_weapon_table_differs() -> None:
    table = FOUR_STAR_TABLE_WEAPON
    assert table[1] == pytest.approx(0.060, abs=1e-12)
    assert table[7] == pytest.approx(0.060, abs=1e-12)
    assert table[8] == pytest.approx(0.660, abs=1e-12)
    assert table[9] == 1.0
    assert effective_hard_pity(table) == 9
    assert effective_hard_pity(FOUR_STAR_TABLE_CHARACTER) != effective_hard_pity(table)


# ---------------------------------------------------------------------------
# SPEC 3.2 / 3.4 / 3.7 - rate-up branch rules
# ---------------------------------------------------------------------------


def test_character_rate_up_branch() -> None:
    assert character_rate_up(True, 0) == 1.0
    assert character_rate_up(True, 3) == 1.0
    assert character_rate_up(False, 0) == CAPTURING_RADIANCE_P
    assert character_rate_up(False, 2) == CAPTURING_RADIANCE_P
    # The hard cap: a fourth consecutive 50/50 loss is impossible.
    assert character_rate_up(False, 3) == 1.0


def test_weapon_rate_up_branch() -> None:
    """SPEC 3.4: 75% featured over two weapons is 0.375 for the chosen one."""
    assert weapon_rate_up(False) == WEAPON_FEATURED_SINGLE_P
    assert weapon_rate_up(False) == pytest.approx(0.75 / 2.0, abs=1e-12)
    assert weapon_rate_up(True) == 1.0
    # No Capturing Radiance on the weapon banner: the loss counter is inert.
    assert weapon_rate_up(False, 3) == WEAPON_FEATURED_SINGLE_P


def test_chronicled_and_standard_branches() -> None:
    assert chronicled_rate_up(False) == CHRONICLED_DESIGNATED_P
    assert chronicled_rate_up(True) == 1.0
    # No Capturing Radiance outside the Character Event banner.
    assert chronicled_rate_up(False, 3) == CHRONICLED_DESIGNATED_P
    # Standard has no featured pool at all, so every 5-star is a success.
    assert standard_rate_up(False) == 1.0
    assert standard_rate_up(True) == 1.0


def test_banner_config_flags_capturing_radiance_only_on_character_event() -> None:
    assert banner_config(BannerKind.CHARACTER_EVENT).capturing_radiance is True
    for kind in (BannerKind.WEAPON_EVENT, BannerKind.STANDARD, BannerKind.CHRONICLED):
        assert banner_config(kind).capturing_radiance is False


def test_banner_config_five_star_curves() -> None:
    """SPEC 3.7: standard and chronicled share the character 74/90 curve."""
    assert banner_config(BannerKind.STANDARD).hard_pity == 90
    assert banner_config(BannerKind.CHRONICLED).hard_pity == 90
    assert banner_config(BannerKind.CHARACTER_EVENT).hard_pity == 90
    assert banner_config(BannerKind.WEAPON_EVENT).hard_pity == 77
    assert banner_config(BannerKind.WEAPON_EVENT).four_star_hard_pity == 9
    assert banner_config(BannerKind.CHARACTER_EVENT).four_star_hard_pity == 10
