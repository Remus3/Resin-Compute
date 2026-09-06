"""Tests for core.domains.

The rotation table is asserted against a hand-written expectation matrix rather
than against a re-derivation from the module's own data - a test that recomputes
the answer the same way the code does proves nothing.

Calendar facts used below are pinned with an explicit `weekday()` assertion so a
miscounted date fails loudly instead of quietly shifting every expectation.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from core.domains import (
    DAILY_RESET_HOUR,
    ROTATION_SLOT_WEEKDAYS,
    ROTATION_SLOTS,
    SUNDAY,
    WEEKLY_RESET_WEEKDAY,
    current_game_day,
    is_available,
    next_available_day,
    weekly_boss_reset,
    weekly_resets_between,
)

# 2026-01-05 is a Monday. Pinned by assertion in the tests that use it.
MONDAY_2026_01_05 = date(2026, 1, 5)

# Hand-written expectation: days to wait, indexed by weekday 0..6 (Mon..Sun).
#   slot 0 runs Mon / Thu / Sun
#   slot 1 runs Tue / Fri / Sun
#   slot 2 runs Wed / Sat / Sun
EXPECTED_WAIT = {
    0: [0, 2, 1, 0, 2, 1, 0],
    1: [1, 0, 2, 1, 0, 1, 0],
    2: [2, 1, 0, 2, 1, 0, 0],
}

# Hand-written availability matrix, same layout.
EXPECTED_AVAILABLE = {
    0: [True, False, False, True, False, False, True],
    1: [False, True, False, False, True, False, True],
    2: [False, False, True, False, False, True, True],
}


# --- rotation table -------------------------------------------------------


def test_the_rotation_has_exactly_three_slots():
    assert ROTATION_SLOTS == (0, 1, 2)
    assert sorted(ROTATION_SLOT_WEEKDAYS) == [0, 1, 2]
    assert SUNDAY == 6
    assert WEEKLY_RESET_WEEKDAY == 0
    assert DAILY_RESET_HOUR == 4


def test_sunday_is_available_for_every_rotation_slot():
    for slot in ROTATION_SLOTS:
        assert is_available(slot, SUNDAY) is True


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_availability_matches_the_expected_matrix(slot):
    observed = [is_available(slot, weekday) for weekday in range(7)]
    assert observed == EXPECTED_AVAILABLE[slot]
    # Every slot is farmable exactly three days a week.
    assert sum(observed) == 3


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_next_available_day_matches_the_expected_matrix(slot):
    observed = [next_available_day(slot, weekday) for weekday in range(7)]
    assert observed == EXPECTED_WAIT[slot]


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_next_available_day_is_zero_exactly_when_available(slot):
    for weekday in range(7):
        wait = next_available_day(slot, weekday)
        assert (wait == 0) is is_available(slot, weekday)
        assert 0 <= wait <= 6
        # Waiting that many days really does land on an available weekday.
        assert is_available(slot, (weekday + wait) % 7) is True


def test_every_weekday_serves_at_least_one_slot():
    for weekday in range(7):
        assert any(is_available(slot, weekday) for slot in ROTATION_SLOTS)


def test_an_unknown_slot_degrades_instead_of_raising():
    assert is_available(9, SUNDAY) is False
    assert next_available_day(9, 0) == 0


def test_weekday_input_is_normalized():
    # 7 is Monday again; -1 is Sunday.
    assert is_available(0, 7) is is_available(0, 0)
    assert is_available(0, -1) is True


# --- daily reset ----------------------------------------------------------


def test_current_game_day_boundary_is_0400_not_midnight():
    assert current_game_day(datetime(2026, 1, 5, 3, 59)) == date(2026, 1, 4)
    assert current_game_day(datetime(2026, 1, 5, 4, 0)) == date(2026, 1, 5)
    assert current_game_day(datetime(2026, 1, 5, 23, 59)) == date(2026, 1, 5)
    assert current_game_day(datetime(2026, 1, 5, 0, 0)) == date(2026, 1, 4)


def test_current_game_day_honours_a_custom_reset_hour():
    assert current_game_day(datetime(2026, 1, 5, 4, 30), reset_hour=5) == date(2026, 1, 4)
    assert current_game_day(datetime(2026, 1, 5, 5, 30), reset_hour=5) == date(2026, 1, 5)


def test_current_game_day_converts_into_the_server_timezone():
    server = timezone(timedelta(hours=8))
    # 2026-01-04 20:30 UTC is 2026-01-05 04:30 on a UTC+8 server, so the game
    # day has already rolled over there while it is still the 4th in UTC.
    moment = datetime(2026, 1, 4, 20, 30, tzinfo=UTC)
    assert current_game_day(moment, tz=server) == date(2026, 1, 5)
    assert current_game_day(moment, tz=UTC) == date(2026, 1, 4)


# --- weekly reset ---------------------------------------------------------


def test_the_pinned_calendar_fact():
    assert MONDAY_2026_01_05.weekday() == 0


def test_weekly_boss_reset_returns_the_next_monday_0400():
    assert MONDAY_2026_01_05.weekday() == 0
    # Sunday evening rolls to the very next morning.
    assert weekly_boss_reset(datetime(2026, 1, 4, 23, 0, tzinfo=UTC)) == datetime(
        2026, 1, 5, 4, 0, tzinfo=UTC
    )
    # Monday at 03:59 has not reset yet.
    assert weekly_boss_reset(datetime(2026, 1, 5, 3, 59, tzinfo=UTC)) == datetime(
        2026, 1, 5, 4, 0, tzinfo=UTC
    )
    # Monday at 04:00 exactly has just reset, so the NEXT one is a week out.
    assert weekly_boss_reset(datetime(2026, 1, 5, 4, 0, tzinfo=UTC)) == datetime(
        2026, 1, 12, 4, 0, tzinfo=UTC
    )


def test_weekly_resets_between_counts_a_monday_boundary_once():
    assert MONDAY_2026_01_05.weekday() == 0
    start = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    assert weekly_resets_between(start, datetime(2026, 1, 5, 3, 59, tzinfo=UTC)) == 0
    assert weekly_resets_between(start, datetime(2026, 1, 5, 4, 0, tzinfo=UTC)) == 1
    assert weekly_resets_between(start, datetime(2026, 1, 11, 23, 59, tzinfo=UTC)) == 1


def test_weekly_resets_between_is_half_open_on_the_start():
    reset = datetime(2026, 1, 5, 4, 0, tzinfo=UTC)
    # A reset landing exactly on `start` is already consumed, so only the next
    # Monday counts here.
    assert weekly_resets_between(reset, reset + timedelta(days=7)) == 1
    # Consecutive windows therefore tile without double counting.
    first = weekly_resets_between(reset, reset + timedelta(days=7))
    second = weekly_resets_between(reset + timedelta(days=7), reset + timedelta(days=14))
    assert first + second == weekly_resets_between(reset, reset + timedelta(days=14)) == 2


def test_weekly_resets_between_over_a_multi_week_window():
    start = datetime(2026, 1, 5, 3, 59, tzinfo=UTC)
    # Resets at Jan 5, 12, 19 and 26. Feb 2 04:00 falls just outside.
    assert weekly_resets_between(start, start + timedelta(days=28)) == 4
    assert weekly_resets_between(start, start + timedelta(days=28, minutes=1)) == 5
    assert weekly_resets_between(start, start + timedelta(days=365)) == 53


def test_weekly_resets_between_returns_zero_for_an_empty_or_inverted_window():
    moment = datetime(2026, 1, 7, 12, 0, tzinfo=UTC)
    assert weekly_resets_between(moment, moment) == 0
    assert weekly_resets_between(moment, moment - timedelta(days=30)) == 0


def test_weekly_resets_between_uses_the_supplied_server_timezone():
    server = timezone(timedelta(hours=8))
    # 2026-01-04 19:00 UTC is 2026-01-05 03:00 server time, so the Monday 04:00
    # server reset is one hour away and falls inside a two hour window.
    start = datetime(2026, 1, 4, 19, 0, tzinfo=UTC)
    end = start + timedelta(hours=2)
    assert weekly_resets_between(start, end, tz=server) == 1
    # The same window against a UTC server contains no reset at all.
    assert weekly_resets_between(start, end, tz=UTC) == 0


def test_weekly_resets_between_accepts_naive_datetimes_as_server_local():
    assert weekly_resets_between(datetime(2026, 1, 5, 0, 0), datetime(2026, 1, 5, 5, 0)) == 1
