"""Operations over the event-sourced CurrencyLedger.

`CurrencyLedger` (core/types.py) is an append-only log of `LedgerEntry`, not a
balance map. Every number this module produces is DERIVED by folding that log.
That is what makes `balance_at` possible at all: a balance map can only answer
"now", while a fold answers "as of any instant", which is what a forecast, a
reconciliation against an external snapshot, and an audit of a suspicious spend
all need.

Every function is pure with respect to global state. The only mutation is the
append performed by `record` and `apply_wish_batch`, and it happens on the
ledger the caller passed in. There is no module-level ledger, no cache and no
singleton.

Timestamps are normalized to aware UTC on the way in and on every comparison, so
a caller mixing naive and aware datetimes gets an answer instead of a TypeError.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import NamedTuple
from uuid import uuid4

from core.log_setup import get_logger
from core.resin import DAILY_RESIN_REGEN
from core.types import BannerKind, CurrencyKind, CurrencyLedger, IncomeVelocity, LedgerEntry

_log = get_logger(__name__)

# --- Standard conversion rates --------------------------------------------
# These are the game's fixed wish-yield conversion rates. Every wish returns an
# item of one of three rarities, and each rarity converts to a fixed amount of
# the two "masterless" currencies.
STARDUST_PER_3STAR = 15
STARGLITTER_PER_4STAR = 2
STARGLITTER_PER_5STAR = 10

# 160 primogems buys one fate, either kind. This is the only primogem-to-wish
# conversion there is.
PRIMOGEMS_PER_FATE = 160

# Which fate a banner family consumes. Character Event, Weapon Event and
# Chronicled all spend Intertwined Fate; only the Standard banner (Wanderlust
# Invocation) spends Acquaint Fate.
FATE_CURRENCY_BY_BANNER: dict[BannerKind, CurrencyKind] = {
    BannerKind.CHARACTER_EVENT: CurrencyKind.INTERTWINED_FATE,
    BannerKind.WEAPON_EVENT: CurrencyKind.INTERTWINED_FATE,
    BannerKind.CHRONICLED: CurrencyKind.INTERTWINED_FATE,
    BannerKind.STANDARD: CurrencyKind.ACQUAINT_FATE,
}

# Rarity of a wish result, used by apply_wish_batch.
RARITY_THREE_STAR = 3
RARITY_FOUR_STAR = 4
RARITY_FIVE_STAR = 5


class WishBatchResult(NamedTuple):
    """What one call to `apply_wish_batch` did to the ledger.

    Declared here rather than in core/types.py because it is an operation
    result local to this module, and core/types.py is read-only to slices.
    """

    fate_currency: CurrencyKind
    fates_spent: int
    stardust_gained: int
    starglitter_gained: int
    entries: tuple[LedgerEntry, ...]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(moment: datetime) -> datetime:
    """Treat a naive datetime as UTC, convert an aware one to UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def fate_currency_for(banner: BannerKind) -> CurrencyKind:
    """The fate currency a banner family spends.

    An unrecognised banner degrades to Intertwined Fate, which is the currency
    for three of the four families, and logs. Raising here would take down a
    caller over a data defect it cannot fix mid-flight.
    """
    currency = FATE_CURRENCY_BY_BANNER.get(banner)
    if currency is None:
        _log.warning("fate_currency_for: unknown banner %r, assuming intertwined fate", banner)
        return CurrencyKind.INTERTWINED_FATE
    return currency


def record(
    ledger: CurrencyLedger,
    currency: CurrencyKind,
    delta: int,
    reason: str,
    source: str = "manual",
    occurred_at: datetime | None = None,
) -> LedgerEntry:
    """Append one signed economic event and return it.

    `delta` is signed: income positive, spend negative. A zero delta is rejected
    by the type contract itself (it carries no information), and it is rejected
    here first so the message names this function rather than a dataclass
    `__post_init__` two frames down.

    `occurred_at` defaults to now and exists so a backfill can state when an
    event actually happened. It is normalized to aware UTC.
    """
    if int(delta) == 0:
        raise ValueError("record: a zero delta carries no information, refusing to append")
    entry = LedgerEntry(
        entry_id=uuid4().hex,
        occurred_at=_as_utc(occurred_at) if occurred_at is not None else _utc_now(),
        currency=currency,
        delta=int(delta),
        reason=reason,
        source=source,
    )
    ledger.entries.append(entry)
    return entry


def balance_at(ledger: CurrencyLedger, currency: CurrencyKind, when: datetime) -> int:
    """Balance of `currency` as of `when`, folding only entries at or before it.

    This is the function that makes the ledger event-sourced rather than a
    balance map: entries after the cutoff are invisible, so the same log answers
    "what did I hold last Tuesday" and "what do I hold now" without a snapshot.

    The window is inclusive of `when`, matching the intuition that an event
    stamped exactly at the cutoff has already happened.
    """
    cutoff = _as_utc(when)
    return sum(
        entry.delta
        for entry in ledger.entries
        if entry.currency is currency and _as_utc(entry.occurred_at) <= cutoff
    )


def apply_wish_batch(
    ledger: CurrencyLedger,
    banner: BannerKind,
    count: int,
    rarities: Sequence[int] | None = None,
    source: str = "wish",
    occurred_at: datetime | None = None,
) -> WishBatchResult:
    """Debit `count` fates for `banner` and credit the resulting yields.

    The correct fate is chosen from the banner family, so a Standard-banner
    batch can never silently drain Intertwined Fate.

    `rarities` is the observed result of each wish, one of 3, 4 or 5 per pull.
    It is optional because the required call shape is `(ledger, banner, count)`.
    When it is omitted every wish is counted as a 3-star, which is the FLOOR of
    the yield rather than an invented distribution - the resulting stardust is a
    lower bound and no starglitter is claimed that was not observed. A caller
    that knows what it pulled passes them.

    Spending more fates than the ledger holds is logged as a warning and still
    recorded. The ledger's job is to state what happened; refusing to record an
    event that already occurred would put it out of sync with reality.
    """
    fate = fate_currency_for(banner)
    pulls = int(count)
    if pulls <= 0:
        _log.warning("apply_wish_batch: non-positive count %r, nothing recorded", count)
        return WishBatchResult(fate, 0, 0, 0, ())

    observed: list[int] = list(rarities) if rarities is not None else [RARITY_THREE_STAR] * pulls
    if len(observed) != pulls:
        _log.warning(
            "apply_wish_batch: %d rarities supplied for %d pulls, padding or truncating to match",
            len(observed), pulls,
        )
        observed = (observed + [RARITY_THREE_STAR] * pulls)[:pulls]

    held = ledger.balance_of(fate)
    if held < pulls:
        _log.warning(
            "apply_wish_batch: %d %s held against %d pulls, recording an overdraft",
            held, fate.value, pulls,
        )

    stardust = sum(STARDUST_PER_3STAR for r in observed if r == RARITY_THREE_STAR)
    starglitter = sum(
        STARGLITTER_PER_4STAR if r == RARITY_FOUR_STAR else STARGLITTER_PER_5STAR
        for r in observed
        if r in (RARITY_FOUR_STAR, RARITY_FIVE_STAR)
    )

    entries = [record(ledger, fate, -pulls, f"{pulls} wishes on {banner.value}", source, occurred_at)]
    if stardust:
        entries.append(
            record(ledger, CurrencyKind.STARDUST, stardust, f"3-star yield from {pulls} wishes",
                   source, occurred_at)
        )
    if starglitter:
        entries.append(
            record(ledger, CurrencyKind.STARGLITTER, starglitter, f"4/5-star yield from {pulls} wishes",
                   source, occurred_at)
        )
    return WishBatchResult(fate, pulls, stardust, starglitter, tuple(entries))


def estimate_velocity(
    ledger: CurrencyLedger,
    window_days: int = 30,
    now: datetime | None = None,
) -> IncomeVelocity:
    """Income per day, derived ONLY from observed positive entries in the window.

    Spends are excluded deliberately. Velocity answers "how fast does income
    arrive", and folding a 1600-primogem wish spend into it would report a
    negative income rate for an account that is earning normally.

    An empty ledger, or a window containing no income, returns a zero velocity
    with `sampled_over_days = 0` and never divides by zero. Zero samples is
    honestly reported rather than dressed up as a measured zero rate.

    `resin_per_day` is not estimated from the log - it is the wall-clock
    constant DAILY_RESIN_REGEN, since resin arrives on a timer regardless of what
    the account does.
    """
    days = int(window_days)
    if days <= 0:
        _log.warning("estimate_velocity: window_days %r must be positive, returning zero velocity", window_days)
        return IncomeVelocity(0.0, 0.0, DAILY_RESIN_REGEN, 0)

    end = _as_utc(now) if now is not None else _utc_now()
    start = end - timedelta(days=days)

    primogems = 0
    fates = 0
    samples = 0
    for entry in ledger.entries:
        if entry.delta <= 0:
            continue
        moment = _as_utc(entry.occurred_at)
        if moment < start or moment > end:
            continue
        samples += 1
        if entry.currency is CurrencyKind.PRIMOGEM:
            primogems += entry.delta
        elif entry.currency is CurrencyKind.INTERTWINED_FATE:
            fates += entry.delta

    if samples == 0:
        return IncomeVelocity(0.0, 0.0, DAILY_RESIN_REGEN, 0)
    return IncomeVelocity(primogems / days, fates / days, DAILY_RESIN_REGEN, days)


def pulls_affordable(ledger: CurrencyLedger, banner: BannerKind = BannerKind.CHARACTER_EVENT) -> int:
    """Total wishes the wallet can currently pay for on `banner`.

    Primogems convert at PRIMOGEMS_PER_FATE with integer division - a remainder
    buys nothing, so 159 primogems is 0 wishes and 320 is exactly 2. Fates
    already held are added on top.

    A negative folded balance (only reachable from a mis-entered ledger) is
    floored at zero rather than subtracting phantom wishes.
    """
    primogems = max(0, ledger.balance_of(CurrencyKind.PRIMOGEM))
    fates = max(0, ledger.balance_of(fate_currency_for(banner)))
    return primogems // PRIMOGEMS_PER_FATE + fates


def project_balance(
    ledger: CurrencyLedger,
    velocity: IncomeVelocity,
    days_ahead: int,
    currency: CurrencyKind = CurrencyKind.PRIMOGEM,
) -> int:
    """Roll the current balance of `currency` forward by `days_ahead`.

    Linear in the modelled rate and floored to a whole unit, because a fraction
    of a primogem is not a thing you can hold.

    Only the two currencies the velocity model actually measures grow:
    PRIMOGEM and INTERTWINED_FATE. Anything else is returned at its current
    balance. Original Resin is excluded ON PURPOSE - it caps at 200, so a linear
    projection of it is wrong by construction; `core.resin.resin_available_over`
    is the right tool for a resin horizon.
    """
    horizon = int(days_ahead)
    if horizon < 0:
        _log.warning("project_balance: negative horizon %d treated as 0", horizon)
        horizon = 0

    current = ledger.balance_of(currency)
    if currency is CurrencyKind.PRIMOGEM:
        rate = velocity.primogems_per_day
    elif currency is CurrencyKind.INTERTWINED_FATE:
        rate = velocity.intertwined_fates_per_day
    else:
        return current
    return current + int(math.floor(rate * horizon))
