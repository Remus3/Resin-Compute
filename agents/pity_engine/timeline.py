"""Answer "by when" over a CALLER-SUPPLIED banner schedule.

`forecast.probability_of_success` answers "given N pulls". This module answers
"by what date", and it does so without learning anything the forecaster does
not already know: the caller supplies every window on which the wanted thing is
pullable, the pulls already in hand, a velocity in pulls per day and the date
the question is asked from. The engine vendors no calendar, imports no ledger
and reads no clock - `as_of` is an argument, exactly as `pull_budget` is one.

The model, stated once
----------------------
Pulls accrue continuously from `as_of` at `pulls_per_day`, floored to whole
pulls per day, so on day `d` the wallet holds

    B(d) = pulls_on_hand + floor(pulls_per_day * (d - as_of).days)

A pull is spendable only on an ELIGIBLE day: a day inside some window of the
schedule that is not before `as_of`. Every window in the schedule is a window
of the target; labels are opaque and carry no semantics. Pity and the wallet
persist across windows (SPEC 3.6), so pulls that accrue in a gap between two
windows are spent on the first day of the next one, and the probability of
having the target by day `d` is the forecaster's own cumulative curve read at
the wallet:

    P(d) = F[min(B(d), len(F) - 1)]       F = solve(...).absorbed_by_pull

`by_date` is the earliest eligible day with `P(d) >= confidence -
_CONFIDENCE_EPS`, which is the same day as the earliest eligible day with
`B(d) >= pulls_needed_for_confidence(...)` because `F` is monotone and that
function is its inverse. When no eligible day qualifies the answer is a RESULT
with `reachable=False`, never an error: the `best_*` fields then carry the
earliest eligible day attaining the maximum probability the schedule allows,
and `pulls_short` says how many pulls the wallet was short on that day.

Window semantics
----------------
- Both ends are INCLUSIVE; `start == end` is a one-day window.
- Two windows overlap when, after sorting by start, `b.start <= a.end`;
  adjacent windows (`b.start == a.end + 1 day`) are legal; equal starts are an
  overlap. Input order is free - the engine sorts.
- A window whose `end` is before `as_of` is rejected: the schedule carries
  only windows not yet closed. A window straddling `as_of` is eligible from
  `as_of`.
- An empty schedule is rejected: a question with no window has no answer,
  mirroring `target_count < 1`.

Pure and deterministic, like the rest of the engine. The result types live
here rather than in `core/types.py` on the precedent of `ChainSolution`; they
move only when a second consumer outside the engine needs the type.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from core.types import BannerKind, PityState

from .banners import BannerConfig, banner_config
from .forecast import _CONFIDENCE_EPS, pulls_needed_for_confidence
from .markov import solve


@dataclass(frozen=True)
class BannerWindow:
    """One run of days on which the wanted thing is pullable. Inclusive ends."""

    start: date
    end: date
    label: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise ValueError("a banner window needs a start date and an end date")
        if not isinstance(self.label, str):
            raise ValueError("a banner window label must be a string")
        if self.end.toordinal() < self.start.toordinal():
            raise ValueError("a banner window cannot end before it starts")


@dataclass(frozen=True)
class WindowOutcome:
    """The wallet and the cumulative probability on the LAST day of one window."""

    start: date
    end: date
    label: str
    pulls_available_at_end: int
    probability_at_end: float


@dataclass(frozen=True)
class ByWhenResult:
    """The answer. `by_date_*` are None exactly when `reachable` is False.

    `best_*` are never None: validation guarantees at least one eligible day,
    so there is always an earliest day attaining the maximum probability.
    `pulls_short` is 0 when reachable and otherwise the gap between the pulls
    needed for `confidence` and the wallet on `best_date`.
    """

    reachable: bool
    by_date: date | None
    by_date_label: str | None
    by_date_pulls_available: int | None
    by_date_probability: float | None
    best_date: date
    best_label: str
    best_pulls_available: int
    best_probability: float
    pulls_needed: int
    pulls_short: int
    windows: tuple[WindowOutcome, ...]


def _config_for(banner: BannerKind, weapon_increment: float | None) -> BannerConfig:
    if weapon_increment is None:
        return banner_config(banner)
    return banner_config(banner, weapon_increment=weapon_increment)


def _require_count(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
    return value


def _require_rate(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    rate = float(value)
    if not math.isfinite(rate):
        raise ValueError(f"{name} must be a finite number")
    if rate < 0.0:
        raise ValueError(f"{name} cannot be negative")
    return rate


def _sorted_schedule(schedule: Sequence[BannerWindow], as_of: date) -> list[BannerWindow]:
    windows = list(schedule)
    if not windows:
        raise ValueError("schedule is empty - a question with no window has no answer")
    for window in windows:
        if not isinstance(window, BannerWindow):
            raise ValueError("schedule entries must be banner windows")
        if window.end.toordinal() < as_of.toordinal():
            raise ValueError("a window that closed before as_of does not belong in the schedule")
    windows.sort(key=lambda w: w.start.toordinal())
    for earlier, later in zip(windows, windows[1:]):
        if later.start.toordinal() <= earlier.end.toordinal():
            raise ValueError("schedule windows overlap - two windows cannot share a day")
    return windows


def by_when(
    state: PityState,
    target_count: int,
    schedule: Sequence[BannerWindow],
    as_of: date,
    pulls_on_hand: int = 0,
    pulls_per_day: float = 0.0,
    confidence: float = 0.9,
    banner: BannerKind = BannerKind.CHARACTER_EVENT,
    weapon_increment: float | None = None,
    carry_radiance_through_guarantee: bool = True,
) -> ByWhenResult:
    """Earliest schedule day on which `confidence` of `target_count` copies is reached.

    See the module docstring for the model. Raises `ValueError` on a question
    with no answer: an empty or overlapping schedule, a window already closed
    at `as_of`, a negative or non-integer wallet, a negative or non-finite
    velocity, or a confidence outside [0, 1]. An unreachable schedule is NOT
    an error - it is a result with `reachable=False`.
    """
    if isinstance(target_count, bool) or not isinstance(target_count, int):
        raise ValueError("target_count must be an integer number of copies")
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be a number")
    on_hand = _require_count(pulls_on_hand, "pulls_on_hand")
    rate = _require_rate(pulls_per_day, "pulls_per_day")
    windows = _sorted_schedule(schedule, as_of)

    # target_count < 1 and the confidence range are rejected here, by the same
    # code the forecaster uses, so the two answer the same question identically.
    pulls_needed = pulls_needed_for_confidence(
        state,
        target_count,
        confidence,
        banner=banner,
        weapon_increment=weapon_increment,
        carry_radiance_through_guarantee=carry_radiance_through_guarantee,
    )
    config = _config_for(banner, weapon_increment)
    curve = solve(
        config,
        state,
        target_count,
        0,
        carry_radiance_through_guarantee=carry_radiance_through_guarantee,
    ).absorbed_by_pull
    last = len(curve) - 1
    threshold = confidence - _CONFIDENCE_EPS
    origin = as_of.toordinal()

    def wallet(ordinal: int) -> int:
        accrued = rate * (ordinal - origin)
        # A finite rate times a finite day count can still overflow to inf, and
        # math.floor(inf) raises OverflowError - which is not the ValueError
        # this function promises. Say which input did it.
        if not math.isfinite(accrued):
            raise ValueError("pulls_per_day is too large to accrue over this schedule")
        return on_hand + math.floor(accrued)

    def probability(ordinal: int) -> float:
        return curve[min(wallet(ordinal), last)]

    by_ordinal: int | None = None
    by_label: str | None = None
    best_ordinal: int | None = None
    best_label = ""
    best_probability = -1.0
    outcomes: list[WindowOutcome] = []
    for window in windows:
        first = max(window.start.toordinal(), origin)
        for ordinal in range(first, window.end.toordinal() + 1):
            p = probability(ordinal)
            if by_ordinal is None and p >= threshold:
                by_ordinal = ordinal
                by_label = window.label
            if p > best_probability:
                best_probability = p
                best_ordinal = ordinal
                best_label = window.label
        end_ordinal = window.end.toordinal()
        outcomes.append(
            WindowOutcome(
                start=window.start,
                end=window.end,
                label=window.label,
                pulls_available_at_end=wallet(end_ordinal),
                probability_at_end=probability(end_ordinal),
            )
        )

    # Validation above guarantees at least one eligible day, so this holds; it
    # is stated rather than assumed so the type checker sees a plain int.
    if best_ordinal is None:
        raise ValueError("schedule carries no eligible day on or after as_of")
    best_pulls = wallet(best_ordinal)

    if by_ordinal is None:
        return ByWhenResult(
            reachable=False,
            by_date=None,
            by_date_label=None,
            by_date_pulls_available=None,
            by_date_probability=None,
            best_date=date.fromordinal(best_ordinal),
            best_label=best_label,
            best_pulls_available=best_pulls,
            best_probability=best_probability,
            pulls_needed=pulls_needed,
            pulls_short=max(0, pulls_needed - best_pulls),
            windows=tuple(outcomes),
        )
    return ByWhenResult(
        reachable=True,
        by_date=date.fromordinal(by_ordinal),
        by_date_label=by_label,
        by_date_pulls_available=wallet(by_ordinal),
        by_date_probability=probability(by_ordinal),
        best_date=date.fromordinal(best_ordinal),
        best_label=best_label,
        best_pulls_available=best_pulls,
        best_probability=best_probability,
        pulls_needed=pulls_needed,
        pulls_short=0,
        windows=tuple(outcomes),
    )
