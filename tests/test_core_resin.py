"""Tests for core.resin.

Resin is the binding constraint, so its arithmetic is pinned exactly rather than
approximately: 1 per 8 minutes, 180 per day, cap 200, and an above-cap balance
that is never clipped down. The overflow case is the one a naive `min(200, x)`
gets wrong, so it is asserted directly.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.resin import (
    CONDENSED_RESIN_COST,
    CONDENSED_RESIN_PAYOUT_MULTIPLIER,
    DAILY_RESIN_REGEN,
    FRAGILE_RESIN_GRANT,
    ORIGINAL_RESIN_CAP,
    RESIN_REGEN_MINUTES,
    daily_resin_budget,
    resin_at,
    resin_available_over,
    time_to_reach,
)

T0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


# --- constants ------------------------------------------------------------


def test_constants_match_the_verified_economy():
    assert ORIGINAL_RESIN_CAP == 200
    assert RESIN_REGEN_MINUTES == 8
    assert CONDENSED_RESIN_COST == 40
    assert CONDENSED_RESIN_PAYOUT_MULTIPLIER == 2
    assert FRAGILE_RESIN_GRANT == 60


def test_daily_regen_is_derived_from_the_eight_minute_rate():
    assert DAILY_RESIN_REGEN == 180
    assert DAILY_RESIN_REGEN == (24 * 60) // RESIN_REGEN_MINUTES
    assert daily_resin_budget() == 180


# --- resin_at -------------------------------------------------------------


def test_exactly_180_regenerate_in_24_hours():
    assert resin_at(0, T0, T0 + timedelta(hours=24)) == 180


def test_eight_minutes_yields_one_and_seven_minutes_yields_zero():
    assert resin_at(0, T0, T0 + timedelta(minutes=7)) == 0
    assert resin_at(0, T0, T0 + timedelta(minutes=8)) == 1
    assert resin_at(0, T0, T0 + timedelta(minutes=15)) == 1
    assert resin_at(0, T0, T0 + timedelta(minutes=16)) == 2
    # Seconds inside an interval never round up.
    assert resin_at(0, T0, T0 + timedelta(minutes=7, seconds=59)) == 0


def test_the_cap_binds():
    # 190 plus a full day of regeneration would be 370 uncapped.
    assert resin_at(190, T0, T0 + timedelta(hours=24)) == ORIGINAL_RESIN_CAP
    # Landing exactly on the cap is still the cap.
    assert resin_at(180, T0, T0 + timedelta(minutes=8 * 20)) == 200


def test_an_above_cap_balance_is_not_clipped_and_does_not_regenerate():
    # 260 is reachable with Fragile Resin. It must survive untouched.
    assert resin_at(260, T0, T0 + timedelta(hours=24)) == 260
    assert resin_at(260, T0, T0 + timedelta(days=7)) == 260
    # A balance sitting exactly at the cap also stays put.
    assert resin_at(200, T0, T0 + timedelta(hours=24)) == 200


def test_a_clock_that_runs_backwards_yields_no_regeneration():
    assert resin_at(50, T0, T0 - timedelta(hours=5)) == 50


def test_a_naive_timestamp_is_accepted_as_utc():
    assert resin_at(0, datetime(2026, 1, 1, 0, 0), T0 + timedelta(hours=24)) == 180


# --- time_to_reach --------------------------------------------------------


def test_time_to_reach_is_eight_minutes_per_point():
    assert time_to_reach(0, 60) == timedelta(minutes=480)
    assert time_to_reach(140, 200) == timedelta(minutes=480)
    assert time_to_reach(0, ORIGINAL_RESIN_CAP) == timedelta(minutes=1600)


def test_time_to_reach_is_zero_when_already_met():
    assert time_to_reach(200, 200) == timedelta(0)
    assert time_to_reach(120, 40) == timedelta(0)
    # Overflow already covers a below-cap target.
    assert time_to_reach(260, 200) == timedelta(0)


def test_time_to_reach_is_none_above_the_cap():
    # Regeneration stops at 200, so 201 and up are unreachable by waiting.
    assert time_to_reach(0, 201) is None
    assert time_to_reach(199, 240) is None


def test_time_to_reach_agrees_with_resin_at():
    waited = time_to_reach(0, 90)
    assert waited is not None
    assert resin_at(0, T0, T0 + waited) == 90


# --- resin_available_over -------------------------------------------------


def test_resin_available_over_sums_every_source():
    # 100 held, 7 days of regeneration, 2 fragile, 3 condensed in inventory.
    expected = 100 + 7 * 180 + 2 * 60 + 3 * 40
    assert resin_available_over(7, 100, 2, 3) == expected == 1600


def test_resin_available_over_defaults_to_regeneration_only():
    assert resin_available_over(30) == 30 * DAILY_RESIN_REGEN == 5400
    assert resin_available_over(0) == 0


def test_resin_available_over_floors_negative_inputs():
    assert resin_available_over(-5, -10, -1, -2) == 0
