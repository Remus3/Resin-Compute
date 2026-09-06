"""Domain rotation and reset schedule - pure mechanics, no content.

Talent and weapon material domains run a three-day rotation: one material set
on Monday and Thursday, a second on Tuesday and Friday, a third on Wednesday and
Saturday, and ALL sets on Sunday. That schedule is the whole of this module.

This module names NO domain and NO material. It is keyed by an abstract
`rotation_slot` (0, 1 or 2) so the schedule can be unit tested without a content
table, and so the data slice owns the mapping from a real domain to a slot. A
proper noun appearing here would also violate the trademark posture in
docs/SPEC_SCAFFOLD.md section 0.

Weekdays are Python's: Monday is 0 through Sunday is 6, matching
`datetime.date.weekday()`. Using that convention rather than a bespoke one means
a caller never has to remember a conversion.

Reset times are 04:00 SERVER time - daily for commissions and domains, weekly on
Monday for Trounce Domains. Server time is region dependent (the Asia, Europe
and America servers each reset on their own offset), so the timezone is a
PARAMETER on every function that needs one, never a hardcoded constant. The
default is UTC purely so a caller that has not decided yet gets deterministic
behaviour; it is not a claim about any region.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, tzinfo

from core.log_setup import get_logger

_log = get_logger(__name__)

# Python weekday convention: Monday is 0.
MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)

DAYS_PER_WEEK = 7
ROTATION_CYCLE_DAYS = 3
ROTATION_SLOTS = (0, 1, 2)

# The rotation, as data. Sunday appears in every row because every set is
# available then; `is_available` therefore needs no Sunday special case beyond
# what this table already states.
ROTATION_SLOT_WEEKDAYS: dict[int, tuple[int, ...]] = {
    0: (MONDAY, THURSDAY, SUNDAY),
    1: (TUESDAY, FRIDAY, SUNDAY),
    2: (WEDNESDAY, SATURDAY, SUNDAY),
}

# 04:00 server time, both resets.
DAILY_RESET_HOUR = 4
WEEKLY_RESET_WEEKDAY = MONDAY


def _normalize_weekday(weekday: int) -> int:
    """Fold any integer onto 0..6. Keeps `day + n` arithmetic caller-side safe."""
    return int(weekday) % DAYS_PER_WEEK


def _as_server_time(moment: datetime, tz: tzinfo) -> datetime:
    """Interpret `moment` in server time.

    A naive datetime is assumed to ALREADY be server-local, which is the common
    case for a value read off a schedule. An aware one is converted.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def is_available(rotation_slot: int, weekday: int) -> bool:
    """True when `rotation_slot`'s material set is farmable on `weekday`.

    Sunday is always True for every slot. An unknown slot returns False and is
    logged rather than raising: a bad slot is a data defect upstream, and the
    safe answer for a scheduler is "cannot farm it today".
    """
    days = ROTATION_SLOT_WEEKDAYS.get(int(rotation_slot))
    if days is None:
        _log.warning("is_available: unknown rotation slot %r, treating as unavailable", rotation_slot)
        return False
    return _normalize_weekday(weekday) in days


def next_available_day(rotation_slot: int, from_weekday: int) -> int:
    """Days to wait until `rotation_slot` is farmable, 0 if it is today.

    Always in 0..6, because Sunday is in every slot's row so no slot can ever be
    more than six days out. An unknown slot returns 0 after logging - the
    scheduler will get False from `is_available` anyway, and returning a
    fictitious wait would corrupt a horizon estimate.
    """
    days = ROTATION_SLOT_WEEKDAYS.get(int(rotation_slot))
    if days is None:
        _log.warning("next_available_day: unknown rotation slot %r", rotation_slot)
        return 0
    start = _normalize_weekday(from_weekday)
    return min((day - start) % DAYS_PER_WEEK for day in days)


def current_game_day(now: datetime, reset_hour: int = DAILY_RESET_HOUR, tz: tzinfo | None = None) -> date:
    """The game day `now` belongs to.

    The day boundary is 04:00 server time, not midnight, so 03:59 still belongs
    to the previous calendar date. This is what a daily-commission or
    domain-availability check must key on.

    `tz` converts an aware `now` into server time first. A naive `now` is taken
    to be server-local already.
    """
    hour = int(reset_hour)
    if not 0 <= hour <= 23:
        _log.warning("current_game_day: reset_hour %r out of range, using %d", reset_hour, DAILY_RESET_HOUR)
        hour = DAILY_RESET_HOUR
    local = now if tz is None else _as_server_time(now, tz)
    if local.hour < hour:
        return (local - timedelta(days=1)).date()
    return local.date()


def weekly_boss_reset(
    now: datetime,
    tz: tzinfo = UTC,
    reset_hour: int = DAILY_RESET_HOUR,
) -> datetime:
    """The next weekly boss reset strictly AFTER `now`.

    Trounce Domain entries refresh Monday at 04:00 server time. `tz` is the
    server offset and is a parameter for the region reason stated in the module
    docstring.
    """
    local = _as_server_time(now, tz)
    anchor = local.replace(hour=int(reset_hour), minute=0, second=0, microsecond=0)
    anchor -= timedelta(days=(anchor.weekday() - WEEKLY_RESET_WEEKDAY) % DAYS_PER_WEEK)
    while anchor <= local:
        anchor += timedelta(days=DAYS_PER_WEEK)
    return anchor


def weekly_resets_between(
    start: datetime,
    end: datetime,
    tz: tzinfo = UTC,
    reset_hour: int = DAILY_RESET_HOUR,
) -> int:
    """Count Monday 04:00 resets in the half-open window (start, end].

    Half-open on purpose: a reset landing exactly on `start` has already been
    consumed by whatever produced that timestamp, while one landing exactly on
    `end` is available within the window. That makes consecutive windows tile
    without double counting a boundary reset.

    Returns 0 for an empty or inverted window. Timezone-naive inputs are taken
    to be server-local.
    """
    first = weekly_boss_reset(start, tz=tz, reset_hour=reset_hour)
    finish = _as_server_time(end, tz)
    if finish < first:
        return 0
    # Fixed-offset server zones have no DST, so a whole number of 7-day spans is
    # exact arithmetic rather than an approximation.
    span_weeks = int((finish - first).total_seconds() // (DAYS_PER_WEEK * 24 * 3600))
    return span_weeks + 1
