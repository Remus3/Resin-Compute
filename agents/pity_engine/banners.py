"""Hazard tables and per-banner branch rules.

Every number in this module traces to `docs/SPEC_SCAFFOLD.md` section 3. Nothing
here is fitted, guessed or carried over from the original brief without the
spec's correction applied.

Two shapes live here:

1. A FIVE-STAR HAZARD TABLE is a tuple indexed by pity count, where `table[n]`
   is the probability that the n-th wish since the last 5-star pays out. Index 0
   is an unused placeholder so the index reads as the pity number rather than an
   offset. The table is built by ramping until the value clips at 1.0, so hard
   pity is COMPUTED from the curve rather than asserted alongside it. That is the
   whole reason section 3.3's defect is impossible to reintroduce here: an
   inconsistent (ramp, hard pity) pair cannot be expressed.

2. A RATE-UP BRANCH is `w(guarantee, losses) -> float`, the probability that a
   5-star, once it lands, is the thing the caller wanted. `losses` is the
   consecutive-50/50-loss counter and is only consulted on the Character Event
   banner, which is the only family Capturing Radiance touches.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.types import BannerKind

# ---------------------------------------------------------------------------
# Five-star curve parameters - SPEC 3.1 and 3.3
# ---------------------------------------------------------------------------

# Character Event Wish, Character Event Wish-2, Standard and Chronicled all
# share this curve (SPEC 3.1, 3.7).
FIVE_STAR_BASE_CHARACTER = 0.006
FIVE_STAR_ANCHOR_CHARACTER = 73
FIVE_STAR_INCREMENT_CHARACTER = 0.06

# Weapon Event Wish (SPEC 3.3). The increment is TUNABLE and deliberately not a
# literal buried in a table: the exact micro-curve is not pinned by public data,
# and 7.0 / 6.6 / 6.0 / 5.8 percent all overshoot the published 1.850%
# consolidated rate by more than the character banner's error margin.
FIVE_STAR_BASE_WEAPON = 0.007
FIVE_STAR_ANCHOR_WEAPON = 62
FIVE_STAR_INCREMENT_WEAPON_DEFAULT = 0.07

# A ramp that never clips would loop forever. This bound only exists so a bad
# tuning parameter raises instead of hanging; no real curve comes near it.
MAX_PITY_BOUND = 400

# ---------------------------------------------------------------------------
# Four-star curves - SPEC 3.5
# ---------------------------------------------------------------------------
#
# Written out as literals rather than derived from an increment, because section
# 3.5 states the three probabilities directly and does not state an increment.
# Inventing one to regenerate these values would be inventing a constant.

FOUR_STAR_TABLE_CHARACTER: tuple[float, ...] = (0.0,) + (0.051,) * 8 + (0.561, 1.0)
FOUR_STAR_TABLE_WEAPON: tuple[float, ...] = (0.0,) + (0.060,) * 7 + (0.660, 1.0)

# ---------------------------------------------------------------------------
# Rate-up branch constants - SPEC 3.2, 3.4, 3.7
# ---------------------------------------------------------------------------

# SOLVED, not observed. Capturing Radiance (version 5.0) replaced the flat 50/50
# on the Character Event banner. HoYoverse publishes a "consolidated probability
# of 55.000%" that a non-guaranteed 5-star is the promotional character, plus a
# hard cap: four consecutive 50/50 losses are impossible.
#
# 0.52106 is the per-roll win probability that makes the long-run rate over
# 50/50 ROLLS come out at 55.000% once the forced win at three losses is folded
# in. It is NOT itself 55%, and the naive substitutions are all wrong:
#
#   flat 0.50, no cap  -> 50.00%   pre-5.0 behaviour, what the brief specified
#   flat 0.55 + cap    -> 57.35%   overshoots the official 55.000%
#   (.5, .5, .5, 1.0)  -> 53.33%   undershoots
#
# `capturing_radiance_long_run_rate` below reproduces every one of those figures,
# and the test suite asserts all four so the constant can never be "simplified"
# back to 0.55 without a red test.
CAPTURING_RADIANCE_P = 0.52106

# You cannot lose a fourth 50/50 in a row, so the counter saturates at 3 and the
# roll taken while sitting at 3 is a forced win.
CAPTURING_RADIANCE_CAP = 3

# SPEC 3.4. 75% of weapon 5-stars are one of the TWO featured weapons, so the
# chance of any single chosen weapon is 0.75 / 2.
WEAPON_FEATURED_SINGLE_P = 0.375

# SPEC 3.7. Chronicled Wish designated-item chance.
CHRONICLED_DESIGNATED_P = 0.5


# ---------------------------------------------------------------------------
# Table construction
# ---------------------------------------------------------------------------


def build_five_star_table(
    base: float,
    anchor: int,
    increment: float,
    max_pity: int = MAX_PITY_BOUND,
) -> tuple[float, ...]:
    """Build a hazard table that ramps from `anchor + 1` and stops at the clip.

    `base` applies for pity 1..anchor. From `anchor + 1` the hazard is
    `base + increment * (n - anchor)`, clipped to 1.0. The table ENDS at the
    first index where the clip binds, because a pity counter can never advance
    past a hazard of 1.0. Hard pity is therefore an emergent property of the
    curve, never a separately-declared number that can drift out of agreement
    with it.
    """
    if not 0.0 < base < 1.0:
        raise ValueError("base hazard must lie strictly between 0 and 1")
    if anchor < 1:
        raise ValueError("anchor must be at least 1")
    if increment <= 0.0:
        raise ValueError("increment must be positive or the ramp never reaches hard pity")

    table: list[float] = [0.0]
    for n in range(1, max_pity + 1):
        raw = base if n <= anchor else base + increment * (n - anchor)
        if raw >= 1.0:
            table.append(1.0)
            return tuple(table)
        table.append(raw)
    raise ValueError(f"hazard ramp did not reach 1.0 within {max_pity} pulls")


def effective_hard_pity(table: tuple[float, ...]) -> int:
    """Return the first pity count whose hazard is 1.0.

    This is the answer to "what is hard pity", and it is derived rather than
    quoted. SPEC 3.3 exists because the brief quoted 80 for a curve that
    saturates at 77; asking the table settles it.
    """
    for n in range(1, len(table)):
        if table[n] >= 1.0:
            return n
    raise ValueError("hazard table never reaches 1.0 - it has no hard pity")


def character_five_star_table() -> tuple[float, ...]:
    """SPEC 3.1. Hard pity 90, P(89) = 0.966, unclipped P(90) would be 1.026."""
    return build_five_star_table(
        FIVE_STAR_BASE_CHARACTER,
        FIVE_STAR_ANCHOR_CHARACTER,
        FIVE_STAR_INCREMENT_CHARACTER,
    )


def weapon_five_star_table(increment: float = FIVE_STAR_INCREMENT_WEAPON_DEFAULT) -> tuple[float, ...]:
    """SPEC 3.3. At the 0.07 default this saturates at pity 77, not 79 or 80."""
    return build_five_star_table(
        FIVE_STAR_BASE_WEAPON,
        FIVE_STAR_ANCHOR_WEAPON,
        increment,
    )


CHARACTER_FIVE_STAR_TABLE: tuple[float, ...] = character_five_star_table()
WEAPON_FIVE_STAR_TABLE: tuple[float, ...] = weapon_five_star_table()


# ---------------------------------------------------------------------------
# Rate-up branches
# ---------------------------------------------------------------------------


def capturing_radiance_long_run_rate(
    win_probability: float = CAPTURING_RADIANCE_P,
    cap: int = CAPTURING_RADIANCE_CAP,
) -> float:
    """Long-run share of 50/50 ROLLS that are won, given the forced win at `cap`.

    The denominator is 50/50 rolls, not 5-stars. A guaranteed 5-star is not a
    50/50 roll at all, so it never enters this average - that distinction is
    exactly what makes 0.52106 come out at 55.000% rather than at something in
    the high sixties.

    Solve: E[rolls per win] with `q = 1 - p` is
    `p * (1 + 2q + 3q^2 + ...) + (cap + 1) * q^cap`, and the rate is its
    reciprocal. `cap = 0` degenerates to "every roll is forced", `cap` large
    degenerates to the uncapped flat rate `p`.
    """
    if not 0.0 < win_probability <= 1.0:
        raise ValueError("win probability must lie in (0, 1]")
    if cap < 0:
        raise ValueError("loss cap cannot be negative")

    expected_rolls = 0.0
    survival = 1.0
    for losses in range(cap + 1):
        win = 1.0 if losses == cap else win_probability
        expected_rolls += (losses + 1) * survival * win
        survival *= 1.0 - win
    return 1.0 / expected_rolls


def character_rate_up(guarantee: bool, losses: int = 0) -> float:
    """SPEC 3.2. Capturing Radiance applies to Character Event Wish only."""
    if guarantee:
        return 1.0
    if losses >= CAPTURING_RADIANCE_CAP:
        return 1.0
    return CAPTURING_RADIANCE_P


def weapon_rate_up(fate_point: bool, losses: int = 0) -> float:
    """SPEC 3.4. `fate_point` is the Epitomized Path counter, capped at 1.

    No Capturing Radiance here, so `losses` is accepted for a uniform branch
    signature and never consulted.
    """
    return 1.0 if fate_point else WEAPON_FEATURED_SINGLE_P


def chronicled_rate_up(guarantee: bool, losses: int = 0) -> float:
    """SPEC 3.7. Flat 50.000% designated item, miss guarantees the next."""
    return 1.0 if guarantee else CHRONICLED_DESIGNATED_P


def standard_rate_up(guarantee: bool = False, losses: int = 0) -> float:
    """SPEC 3.7. Wanderlust Invocation has no featured pool and no 50/50.

    Every 5-star is therefore a success by definition, which is why this returns
    1.0 unconditionally rather than modelling a branch that does not exist.
    """
    return 1.0


# ---------------------------------------------------------------------------
# Banner configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BannerConfig:
    """Everything the chain needs to know about one banner family.

    `rate_up` is stored as an instance attribute rather than a method so that a
    caller can substitute a branch rule (a re-tuned Capturing Radiance, say)
    without subclassing. Instance attributes are not bound as methods, so
    `config.rate_up(guarantee, losses)` passes exactly two arguments.
    """

    kind: BannerKind
    five_star: tuple[float, ...]
    four_star: tuple[float, ...]
    rate_up: Callable[[bool, int], float]
    capturing_radiance: bool = False
    label: str = ""

    @property
    def hard_pity(self) -> int:
        """First pity count whose 5-star hazard is 1.0."""
        return effective_hard_pity(self.five_star)

    @property
    def four_star_hard_pity(self) -> int:
        """First pity count whose 4-star hazard is 1.0."""
        return effective_hard_pity(self.four_star)


def banner_config(
    kind: BannerKind,
    weapon_increment: float = FIVE_STAR_INCREMENT_WEAPON_DEFAULT,
) -> BannerConfig:
    """Build the configuration for one banner family.

    `weapon_increment` is threaded through so a caller can explore the untuned
    weapon micro-curve (SPEC 3.3) without editing this module. It is ignored for
    every other family.
    """
    if kind is BannerKind.CHARACTER_EVENT:
        return BannerConfig(
            kind=kind,
            five_star=CHARACTER_FIVE_STAR_TABLE,
            four_star=FOUR_STAR_TABLE_CHARACTER,
            rate_up=character_rate_up,
            capturing_radiance=True,
            label="Character Event Wish",
        )
    if kind is BannerKind.WEAPON_EVENT:
        return BannerConfig(
            kind=kind,
            five_star=weapon_five_star_table(weapon_increment),
            four_star=FOUR_STAR_TABLE_WEAPON,
            rate_up=weapon_rate_up,
            capturing_radiance=False,
            label="Weapon Event Wish",
        )
    if kind is BannerKind.STANDARD:
        return BannerConfig(
            kind=kind,
            five_star=CHARACTER_FIVE_STAR_TABLE,
            four_star=FOUR_STAR_TABLE_CHARACTER,
            rate_up=standard_rate_up,
            capturing_radiance=False,
            label="Wanderlust Invocation",
        )
    if kind is BannerKind.CHRONICLED:
        # SPEC 3.7 pins the Chronicled 5-star curve ("same 74/90 curve") but 3.5
        # names only "character / standard" and "weapon banner" for the 4-star
        # step, so Chronicled is not stated there. It inherits the
        # character/standard 4-star table rather than getting an invented one.
        return BannerConfig(
            kind=kind,
            five_star=CHARACTER_FIVE_STAR_TABLE,
            four_star=FOUR_STAR_TABLE_CHARACTER,
            rate_up=chronicled_rate_up,
            capturing_radiance=False,
            label="Chronicled Wish",
        )
    raise ValueError(f"no banner configuration for {kind!r}")
