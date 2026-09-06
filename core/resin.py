"""The resin economy - the binding constraint the whole product optimizes.

Original Resin regenerates on a wall-clock timer whether the account is logged
in or not, which makes it the one resource a planner cannot buy its way out of.
Every horizon estimate this repo produces bottoms out in the arithmetic here.

Constants, all named rather than inlined:

    ORIGINAL_RESIN_CAP          200   the natural regeneration ceiling
    RESIN_REGEN_MINUTES           8   one Original Resin per 8 minutes
    DAILY_RESIN_REGEN           180   24 * 60 / 8, derived not typed
    CONDENSED_RESIN_COST         40   Original Resin spent to craft one
    CONDENSED_RESIN_PAYOUT_MULTIPLIER  2   doubles a single domain payout
    FRAGILE_RESIN_GRANT          60   Original Resin granted on use

The overflow rule is the subtle one and it is modelled explicitly: a balance
ABOVE the cap is legal - Fragile Resin, and event rewards, can push past 200 -
and it is never clipped back down. It simply stops regenerating. Code that
writes `min(200, x)` unconditionally destroys a real balance, so `resin_at`
returns an above-cap `current` untouched.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.log_setup import get_logger

_log = get_logger(__name__)

# --- Verified economy constants -------------------------------------------
ORIGINAL_RESIN_CAP = 200
RESIN_REGEN_MINUTES = 8
RESIN_REGEN_SECONDS = RESIN_REGEN_MINUTES * 60
# Derived, not transcribed, so the two facts cannot drift apart.
DAILY_RESIN_REGEN = (24 * 60) // RESIN_REGEN_MINUTES  # 180

CONDENSED_RESIN_COST = 40
CONDENSED_RESIN_PAYOUT_MULTIPLIER = 2
FRAGILE_RESIN_GRANT = 60


def _as_utc(moment: datetime) -> datetime:
    """Attach UTC to a naive datetime, otherwise convert to UTC.

    A naive datetime is treated as ALREADY being UTC. Mixing naive and aware
    datetimes in a comparison raises TypeError, and this function exists so a
    caller passing `datetime.utcnow()` gets an answer rather than a traceback.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def daily_resin_budget() -> int:
    """Original Resin regenerated over a full 24 hours."""
    return DAILY_RESIN_REGEN


def resin_at(current: int, last_updated: datetime, now: datetime) -> int:
    """Return the resin balance at `now`, given `current` observed at `last_updated`.

    Regeneration is floor-quantized: partial intervals do not count, so 7
    minutes yields 0 and 8 minutes yields exactly 1.

    Two clamps, and only two:
      - the result is capped at ORIGINAL_RESIN_CAP when regeneration is what
        would have pushed it over;
      - an input already at or above the cap is returned UNCHANGED, because
        overflow from Fragile Resin persists and merely stops regenerating.

    A `now` earlier than `last_updated` yields no regeneration and is logged; it
    means the caller's clock or its stored timestamp is wrong, and inventing
    negative resin would be worse than standing still.
    """
    balance = max(0, int(current))
    if balance >= ORIGINAL_RESIN_CAP:
        return balance

    elapsed_seconds = (_as_utc(now) - _as_utc(last_updated)).total_seconds()
    if elapsed_seconds < 0:
        _log.warning("resin_at: now precedes last_updated by %.0fs, assuming no regeneration",
                     -elapsed_seconds)
        return balance
    regenerated = int(elapsed_seconds // RESIN_REGEN_SECONDS)
    return min(ORIGINAL_RESIN_CAP, balance + regenerated)


def time_to_reach(current: int, target: int) -> timedelta | None:
    """Time for regeneration alone to lift `current` to `target`.

    Returns `timedelta(0)` when the target is already met, and None when the
    target is above ORIGINAL_RESIN_CAP - regeneration stops at the cap, so no
    amount of waiting reaches it. None means "unreachable this way", not
    "error"; the caller's remaining levers are Fragile Resin and time-gated
    rewards.
    """
    balance = max(0, int(current))
    goal = int(target)
    if goal <= balance:
        return timedelta(0)
    if goal > ORIGINAL_RESIN_CAP:
        return None
    return timedelta(minutes=(goal - balance) * RESIN_REGEN_MINUTES)


def resin_available_over(days: int, current: int = 0, fragile_used: int = 0, condensed: int = 0) -> int:
    """Total Original Resin budget across a horizon of `days`.

    Terms:
      - `current`      resin in hand right now, including any overflow;
      - `days`         full days of regeneration at DAILY_RESIN_REGEN;
      - `fragile_used` Fragile Resin the plan intends to burn, 60 each;
      - `condensed`    Condensed Resin ALREADY CRAFTED and held. Each stores 40
                       Original Resin of value, so it is a credit here.

    Deliberately NOT modelled here:
      - crafting a NEW Condensed Resin out of this budget, which is value
        neutral - 40 out of the pool, 40 into an item;
      - the doubling. CONDENSED_RESIN_PAYOUT_MULTIPLIER doubles a domain's
        PAYOUT, it does not create resin, so it belongs to the planner's yield
        calculation and not to a resin budget.

    Assumes the account is drained often enough that regeneration is never lost
    to the cap. That makes this a planning UPPER BOUND, which is the honest
    reading: a player who logs in daily realises it, one who does not gets less.
    """
    horizon = max(0, int(days))
    if int(days) < 0:
        _log.warning("resin_available_over: negative horizon %d treated as 0", days)
    return (
        max(0, int(current))
        + horizon * DAILY_RESIN_REGEN
        + max(0, int(fragile_used)) * FRAGILE_RESIN_GRANT
        + max(0, int(condensed)) * CONDENSED_RESIN_COST
    )
