"""Library tests for the "by when" question over a caller-supplied schedule.

The engine stays a pure function of its inputs: every window in the schedule
arrives from the caller, velocity arrives as a plain number of pulls per day
and `as_of` is an argument, never a clock read. The dates below are therefore
invented - year 2100, labels like "window-a" - and no window length here is a
fact about any real banner.

The curve the answer is read from is `markov.solve(...).absorbed_by_pull`, so
every probability below is cross-checked against `probability_of_success` at
the same pull count rather than against a figure typed in by hand.
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pytest

from agents.pity_engine.banners import banner_config
from agents.pity_engine.forecast import probability_of_success, pulls_needed_for_confidence
from agents.pity_engine.markov import solve
from agents.pity_engine.timeline import BannerWindow, ByWhenResult, WindowOutcome, by_when
from core.types import BannerKind, PityState

AS_OF = date(2100, 1, 1)
STATE = PityState()


def _plus(days: int, start: date = AS_OF) -> date:
    return date.fromordinal(start.toordinal() + days)


def _prob(pulls: int, state: PityState = STATE, banner: BannerKind = BannerKind.CHARACTER_EVENT) -> float:
    return probability_of_success(state, 1, pulls, banner=banner).probability


# ---------------------------------------------------------------------------
# Window validation
# ---------------------------------------------------------------------------


def test_a_window_whose_end_precedes_its_start_is_rejected() -> None:
    with pytest.raises(ValueError, match="end"):
        BannerWindow(start=date(2100, 1, 10), end=date(2100, 1, 9))


def test_a_one_day_window_is_legal_and_eligible_on_exactly_that_day() -> None:
    window = BannerWindow(start=date(2100, 1, 5), end=date(2100, 1, 5), label="window-a")
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=200, confidence=1.0)
    assert result.reachable is True
    assert result.by_date == date(2100, 1, 5)
    assert result.by_date_label == "window-a"
    assert len(result.windows) == 1
    assert result.windows[0].start == result.windows[0].end == date(2100, 1, 5)


def test_an_empty_schedule_has_no_answer() -> None:
    with pytest.raises(ValueError, match="schedule"):
        by_when(STATE, 1, [], as_of=AS_OF, pulls_on_hand=500)


def test_a_window_closed_before_as_of_is_rejected() -> None:
    stale = BannerWindow(start=date(2099, 12, 1), end=date(2099, 12, 31))
    live = BannerWindow(start=date(2100, 2, 1), end=date(2100, 2, 10))
    with pytest.raises(ValueError, match="as_of"):
        by_when(STATE, 1, [stale, live], as_of=AS_OF, pulls_on_hand=500)


def test_overlapping_windows_are_rejected_in_any_input_order() -> None:
    a = BannerWindow(start=date(2100, 1, 1), end=date(2100, 1, 10), label="window-a")
    b = BannerWindow(start=date(2100, 1, 10), end=date(2100, 1, 20), label="window-b")
    with pytest.raises(ValueError, match="overlap"):
        by_when(STATE, 1, [a, b], as_of=AS_OF, pulls_on_hand=500)
    with pytest.raises(ValueError, match="overlap"):
        by_when(STATE, 1, [b, a], as_of=AS_OF, pulls_on_hand=500)


def test_two_windows_with_equal_starts_overlap() -> None:
    a = BannerWindow(start=date(2100, 1, 1), end=date(2100, 1, 3))
    b = BannerWindow(start=date(2100, 1, 1), end=date(2100, 1, 9))
    with pytest.raises(ValueError, match="overlap"):
        by_when(STATE, 1, [a, b], as_of=AS_OF, pulls_on_hand=500)


def test_adjacent_windows_are_legal_and_come_back_sorted_by_start() -> None:
    a = BannerWindow(start=date(2100, 1, 1), end=date(2100, 1, 10), label="window-a")
    b = BannerWindow(start=date(2100, 1, 11), end=date(2100, 1, 20), label="window-b")
    result = by_when(STATE, 1, [b, a], as_of=AS_OF, pulls_on_hand=500)
    assert [w.label for w in result.windows] == ["window-a", "window-b"]
    assert all(isinstance(w, WindowOutcome) for w in result.windows)


# ---------------------------------------------------------------------------
# The inclusive end, and the day arithmetic around it
# ---------------------------------------------------------------------------


def test_the_end_date_is_inclusive() -> None:
    """One pull per day from zero: the 90 percent answer lands on day `needed`.

    The window ends on exactly that day. An exclusive end would make the last
    spendable day `needed - 1`, with one pull too few, and the schedule would
    read as unreachable.
    """
    needed = pulls_needed_for_confidence(STATE, 1, 0.9)
    window = BannerWindow(start=AS_OF, end=_plus(needed), label="window-a")
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=1.0, confidence=0.9)
    assert result.reachable is True
    assert result.by_date == window.end
    assert result.by_date_pulls_available == needed
    assert result.pulls_needed == needed
    assert result.pulls_short == 0


def test_a_window_one_day_shorter_misses_the_same_answer() -> None:
    """The control for the inclusive-end arm: the boundary is real on both sides."""
    needed = pulls_needed_for_confidence(STATE, 1, 0.9)
    window = BannerWindow(start=AS_OF, end=_plus(needed - 1), label="window-a")
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=1.0, confidence=0.9)
    assert result.reachable is False
    assert result.best_pulls_available == needed - 1
    assert result.pulls_short == 1


def test_a_window_straddling_as_of_is_eligible_from_as_of_not_from_its_start() -> None:
    window = BannerWindow(start=date(2100, 1, 1), end=date(2100, 1, 31), label="window-a")
    later = date(2100, 1, 15)
    needed = pulls_needed_for_confidence(STATE, 1, 0.9)
    result = by_when(STATE, 1, [window], as_of=later, pulls_on_hand=needed, confidence=0.9)
    assert result.by_date == later
    assert result.by_date_pulls_available == needed


def test_fractional_velocity_floors_to_whole_pulls_per_day() -> None:
    """Half a pull a day: day 1 holds floor(0.5) = 0 extra pulls, day 2 holds 1."""
    needed = pulls_needed_for_confidence(STATE, 1, 0.9)
    window = BannerWindow(start=AS_OF, end=_plus(10))
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=needed - 1, pulls_per_day=0.5)
    assert result.by_date == _plus(2)
    assert result.by_date_pulls_available == needed


@pytest.mark.parametrize(
    "rate, days, expected",
    [
        # 1.3 * 2 = 2.6: floor 2, round would say 3.
        (1.3, 2, 2),
        # 0.7 * 1 = 0.7: floor 0, round would say 1.
        (0.7, 1, 0),
        # 1.3 * 3 = 3.9: floor 3, round would say 4.
        (1.3, 3, 3),
    ],
)
def test_accrual_is_floored_not_rounded(rate: float, days: int, expected: int) -> None:
    """The wallet holds whole pulls; a fraction of a pull is not a pull.

    Each case sits where floor and round disagree, so the arm is about the
    rounding mode and not merely about integer arithmetic.
    """
    assert math.floor(rate * days) == expected
    assert round(rate * days) != expected, "fixture no longer separates floor from round"
    window = BannerWindow(start=AS_OF, end=_plus(days))
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=rate, confidence=0.0)
    assert result.windows[0].pulls_available_at_end == expected
    assert result.windows[0].probability_at_end == _prob(expected)


def test_a_window_ending_on_as_of_is_accepted_and_eligible_that_day() -> None:
    """R7 rejects only `end < as_of`. A window that closes ON as_of still has today."""
    closing_today = BannerWindow(start=date(2099, 12, 25), end=AS_OF, label="window-a")
    result = by_when(STATE, 1, [closing_today], as_of=AS_OF, pulls_on_hand=200, confidence=1.0)
    assert result.reachable is True
    assert result.by_date == AS_OF
    assert result.by_date_label == "window-a"
    assert result.windows[0].pulls_available_at_end == 200
    closed_yesterday = BannerWindow(start=date(2099, 12, 25), end=_plus(-1), label="window-a")
    with pytest.raises(ValueError, match="as_of"):
        by_when(STATE, 1, [closed_yesterday], as_of=AS_OF, pulls_on_hand=200, confidence=1.0)


def test_a_velocity_that_overflows_the_accrual_is_a_value_error() -> None:
    """`math.floor(inf)` raises OverflowError; the contract promises ValueError.

    A finite but enormous rate times a handful of days overflows to infinity.
    The library must name the input rather than leak the arithmetic's own
    exception class, which the HTTP layer would otherwise log as an unexpected
    failure rather than a bad request.
    """
    window = BannerWindow(start=AS_OF, end=_plus(3))
    with pytest.raises(ValueError, match="pulls_per_day"):
        by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=1e308)


# ---------------------------------------------------------------------------
# Pity and wallet persist across windows; gaps accrue but cannot be spent in
# ---------------------------------------------------------------------------


def test_pulls_accrue_through_a_gap_but_are_spendable_only_inside_a_window() -> None:
    """Confidence met in the gap resolves on the first day of the next window."""
    a = BannerWindow(start=AS_OF, end=_plus(9), label="window-a")
    b = BannerWindow(start=_plus(59), end=_plus(89), label="window-b")
    # The pulls this confidence needs are more than window-a ends with (9) and
    # fewer than window-b opens with (59), so the threshold is crossed inside
    # the gap and the answer is the first day of window-b.
    needed = pulls_needed_for_confidence(STATE, 1, 0.1)
    assert 9 < needed < 59, "the fixture no longer places the answer inside the gap"
    result = by_when(STATE, 1, [a, b], as_of=AS_OF, pulls_per_day=1.0, confidence=0.1)
    assert result.reachable is True
    assert result.by_date == b.start
    assert result.by_date_label == "window-b"
    assert result.by_date_pulls_available == 59
    assert result.by_date_probability == _prob(59)


def test_the_answer_can_land_mid_window_after_an_earlier_window_fell_short() -> None:
    a = BannerWindow(start=AS_OF, end=_plus(9), label="window-a")
    b = BannerWindow(start=_plus(59), end=_plus(89), label="window-b")
    needed = pulls_needed_for_confidence(STATE, 1, 0.5)
    assert 59 < needed <= 89, "the fixture no longer places the answer inside window-b"
    result = by_when(STATE, 1, [a, b], as_of=AS_OF, pulls_per_day=1.0, confidence=0.5)
    assert result.by_date == _plus(needed)
    assert result.by_date_label == "window-b"
    assert result.windows[0].pulls_available_at_end == 9
    assert result.windows[1].pulls_available_at_end == 89


# ---------------------------------------------------------------------------
# Unreachable is a result, never an error
# ---------------------------------------------------------------------------


def test_an_unreachable_schedule_is_a_result_with_reachable_false() -> None:
    window = BannerWindow(start=AS_OF, end=_plus(9), label="window-a")
    needed = pulls_needed_for_confidence(STATE, 1, 0.9)
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=1.0, confidence=0.9)
    assert isinstance(result, ByWhenResult)
    assert result.reachable is False
    assert result.by_date is None
    assert result.by_date_label is None
    assert result.by_date_pulls_available is None
    assert result.by_date_probability is None
    assert result.best_date == window.end
    assert result.best_label == "window-a"
    assert result.best_pulls_available == 9
    assert result.best_probability == _prob(9)
    assert result.pulls_needed == needed
    assert result.pulls_short == needed - 9


def test_best_date_is_the_earliest_eligible_day_attaining_the_maximum() -> None:
    """Once the curve saturates, later days add nothing - the FIRST such day wins.

    One pull a day over a long window: the wallet reaches the curve's last index
    on exactly day `horizon`, every later day reads the same saturated value,
    and best_date must be that first day, not the last day of the window. A
    `>=` tie-break would report the window's final day instead.
    """
    curve = solve(banner_config(BannerKind.CHARACTER_EVENT), STATE, 1, 0).absorbed_by_pull
    horizon = len(curve) - 1
    assert curve[horizon] > curve[horizon - 1], "the fixture needs a strictly rising last step"
    certain = pulls_needed_for_confidence(STATE, 1, 1.0)
    window = BannerWindow(start=AS_OF, end=_plus(364))
    assert (window.end - AS_OF).days > horizon, "the window must outlast the curve"
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_per_day=1.0, confidence=1.0)
    assert result.reachable is True
    assert result.by_date == _plus(certain)
    assert result.best_date == _plus(horizon)
    assert result.best_pulls_available == horizon
    assert result.best_probability == curve[horizon]


def test_a_flat_curve_breaks_the_tie_on_the_earliest_eligible_day() -> None:
    """Zero velocity: every eligible day has the same probability, the first wins.

    Two windows, nothing accruing, so P is flat across both. best_date is the
    first eligible day of the first window - not the last day of the last one -
    and by_date, where reachable, is that same first day.
    """
    a = BannerWindow(start=_plus(4), end=_plus(7), label="window-a")
    b = BannerWindow(start=_plus(14), end=_plus(19), label="window-b")
    short = by_when(STATE, 1, [b, a], as_of=AS_OF, pulls_on_hand=10, confidence=0.9)
    assert short.reachable is False
    assert short.best_date == a.start
    assert short.best_label == "window-a"
    assert short.best_pulls_available == 10
    assert short.best_probability == _prob(10)
    assert short.windows[0].probability_at_end == short.windows[1].probability_at_end
    plenty = by_when(STATE, 1, [b, a], as_of=AS_OF, pulls_on_hand=200, confidence=1.0)
    assert plenty.reachable is True
    assert plenty.by_date == a.start
    assert plenty.best_date == a.start


def test_a_wallet_past_the_horizon_reads_the_saturated_curve_without_error() -> None:
    window = BannerWindow(start=AS_OF, end=_plus(3))
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=1000, confidence=1.0)
    assert result.reachable is True
    assert result.by_date == AS_OF
    assert result.by_date_probability == pytest.approx(1.0, abs=1e-12)
    assert result.windows[0].probability_at_end == pytest.approx(1.0, abs=1e-12)


def test_zero_velocity_with_exactly_enough_on_hand_is_certain_on_day_one() -> None:
    certain = pulls_needed_for_confidence(STATE, 1, 1.0)
    window = BannerWindow(start=AS_OF, end=_plus(5))
    enough = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=certain, confidence=1.0)
    assert enough.reachable is True
    assert enough.by_date == AS_OF
    short = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=certain - 1, confidence=1.0)
    assert short.reachable is False
    assert short.pulls_short == 1
    assert short.best_pulls_available == certain - 1


# ---------------------------------------------------------------------------
# Scalar validation (R3) and the confidence range
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pulls_on_hand": -1},
        {"pulls_on_hand": True},
        {"pulls_on_hand": 1.5},
        {"pulls_per_day": -0.5},
        {"pulls_per_day": True},
        {"pulls_per_day": math.nan},
        {"pulls_per_day": math.inf},
        {"pulls_per_day": "fast"},
        {"confidence": 1.5},
        {"confidence": -0.1},
        {"confidence": math.nan},
        {"confidence": True},
    ],
)
def test_negative_bool_and_non_finite_scalars_are_rejected(kwargs: dict[str, object]) -> None:
    window = BannerWindow(start=AS_OF, end=_plus(5))
    with pytest.raises(ValueError):
        by_when(STATE, 1, [window], as_of=AS_OF, **kwargs)  # type: ignore[arg-type]


def test_target_count_validation_mirrors_the_forecaster() -> None:
    window = BannerWindow(start=AS_OF, end=_plus(5))
    with pytest.raises(ValueError, match="target_count"):
        by_when(STATE, 0, [window], as_of=AS_OF)
    with pytest.raises(ValueError, match="target_count"):
        by_when(STATE, True, [window], as_of=AS_OF)


def test_confidence_zero_needs_no_pulls_and_resolves_on_the_first_eligible_day() -> None:
    window = BannerWindow(start=_plus(3), end=_plus(6))
    result = by_when(STATE, 1, [window], as_of=AS_OF, confidence=0.0)
    assert result.pulls_needed == 0
    assert result.by_date == window.start
    assert result.by_date_pulls_available == 0


# ---------------------------------------------------------------------------
# The curve is the forecaster's curve, on every banner
# ---------------------------------------------------------------------------


def test_window_outcomes_match_the_public_forecaster_at_the_same_pull_count() -> None:
    a = BannerWindow(start=AS_OF, end=_plus(19), label="window-a")
    b = BannerWindow(start=_plus(40), end=_plus(70), label="window-b")
    result = by_when(STATE, 1, [a, b], as_of=AS_OF, pulls_on_hand=7, pulls_per_day=1.5)
    for outcome in result.windows:
        days = (outcome.end - AS_OF).days
        assert outcome.pulls_available_at_end == 7 + math.floor(1.5 * days)
        assert outcome.probability_at_end == _prob(outcome.pulls_available_at_end)


def test_the_banner_argument_selects_the_curve() -> None:
    state = PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=76, fate_points=1)
    window = BannerWindow(start=AS_OF, end=_plus(2))
    result = by_when(state, 1, [window], as_of=AS_OF, pulls_on_hand=1, confidence=1.0, banner=BannerKind.WEAPON_EVENT)
    assert result.reachable is True
    assert result.pulls_needed == 1
    assert result.by_date_probability == 1.0


def test_by_when_is_deterministic() -> None:
    state = PityState(pity_5star=30, consecutive_5050_losses=1)
    schedule = [
        BannerWindow(start=AS_OF, end=_plus(10), label="window-a"),
        BannerWindow(start=_plus(30), end=_plus(49), label="window-b"),
    ]
    first = by_when(state, 1, schedule, as_of=AS_OF, pulls_on_hand=12, pulls_per_day=0.7)
    second = by_when(state, 1, schedule, as_of=AS_OF, pulls_on_hand=12, pulls_per_day=0.7)
    assert first == second


def test_labels_are_opaque_and_echoed_verbatim() -> None:
    window = BannerWindow(start=AS_OF, end=_plus(2))
    assert window.label == ""
    result = by_when(STATE, 1, [window], as_of=AS_OF, pulls_on_hand=500, confidence=0.5)
    assert result.by_date_label == ""
    assert result.best_label == ""
    assert result.windows[0].label == ""


# ---------------------------------------------------------------------------
# Purity: no clock, no ledger
# ---------------------------------------------------------------------------

_FORBIDDEN_IN_ENGINE = ("core.ledger", "core.config", "core.domains", "today(", "datetime.now", "import time")


def _purity_offenders(source: str) -> list[str]:
    return [needle for needle in _FORBIDDEN_IN_ENGINE if needle in source]


def test_the_timeline_module_reads_no_clock_and_imports_no_ledger() -> None:
    source = (Path(__file__).resolve().parent.parent / "timeline.py").read_text(encoding="utf-8")
    assert _purity_offenders(source) == []


def test_the_purity_detector_fires_on_a_clock_read() -> None:
    assert _purity_offenders("as_of = date.today()\n") == ["today("]
    assert _purity_offenders("from core.ledger import estimate_velocity\n") == ["core.ledger"]
