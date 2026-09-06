"""Tests for core.ledger.

The load-bearing properties here are the event-sourced ones: a balance is a fold
over a log with a timestamp cutoff, income velocity ignores spends, and the
primogem-to-wish conversion is integer division at a fixed rate. Each is
asserted against a computed quantity, never against a restatement of the
implementation.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.ledger import (
    PRIMOGEMS_PER_FATE,
    STARDUST_PER_3STAR,
    STARGLITTER_PER_4STAR,
    STARGLITTER_PER_5STAR,
    apply_wish_batch,
    balance_at,
    estimate_velocity,
    fate_currency_for,
    project_balance,
    pulls_affordable,
    record,
)
from core.types import BannerKind, CurrencyKind, CurrencyLedger, IncomeVelocity

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _ledger() -> CurrencyLedger:
    return CurrencyLedger()


# --- record ---------------------------------------------------------------


def test_record_appends_and_returns_the_entry():
    ledger = _ledger()
    entry = record(ledger, CurrencyKind.PRIMOGEM, 1600, "abyss clear", "manual", T0)
    assert ledger.entries == [entry]
    assert entry.delta == 1600
    assert entry.currency is CurrencyKind.PRIMOGEM
    assert entry.occurred_at == T0
    assert entry.entry_id


def test_record_generates_distinct_ids():
    ledger = _ledger()
    first = record(ledger, CurrencyKind.PRIMOGEM, 60, "daily", "manual", T0)
    second = record(ledger, CurrencyKind.PRIMOGEM, 60, "daily", "manual", T0)
    assert first.entry_id != second.entry_id


def test_record_stamps_aware_utc_by_default():
    ledger = _ledger()
    entry = record(ledger, CurrencyKind.MORA, 20000, "domain run")
    assert entry.occurred_at.tzinfo is not None
    assert entry.occurred_at.utcoffset() == timedelta(0)


def test_record_normalizes_a_naive_timestamp_to_utc():
    ledger = _ledger()
    entry = record(ledger, CurrencyKind.PRIMOGEM, 60, "daily", "manual", datetime(2026, 1, 1, 12, 0))
    assert entry.occurred_at == T0


def test_record_refuses_a_zero_delta():
    ledger = _ledger()
    with pytest.raises(ValueError):
        record(ledger, CurrencyKind.PRIMOGEM, 0, "nothing happened")
    assert ledger.entries == []


# --- balance_at -----------------------------------------------------------


def test_balance_at_respects_the_timestamp_cutoff():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 100, "day 1", "manual", T0)
    record(ledger, CurrencyKind.PRIMOGEM, 200, "day 2", "manual", T0 + timedelta(days=1))
    record(ledger, CurrencyKind.PRIMOGEM, 400, "day 3", "manual", T0 + timedelta(days=2))

    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0 - timedelta(seconds=1)) == 0
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0) == 100
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0 + timedelta(days=1)) == 300
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0 + timedelta(days=10)) == 700
    # The fold at "now" must agree with the ledger's own whole-log balance.
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0 + timedelta(days=10)) == ledger.balance_of(
        CurrencyKind.PRIMOGEM
    )


def test_balance_at_folds_spends_and_ignores_other_currencies():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 1600, "income", "manual", T0)
    record(ledger, CurrencyKind.PRIMOGEM, -960, "spend", "manual", T0 + timedelta(hours=1))
    record(ledger, CurrencyKind.MORA, 500000, "unrelated", "manual", T0 + timedelta(hours=2))
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, T0 + timedelta(days=1)) == 640
    assert balance_at(ledger, CurrencyKind.MORA, T0 + timedelta(days=1)) == 500000


def test_balance_at_accepts_a_naive_cutoff():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 100, "day 1", "manual", T0)
    assert balance_at(ledger, CurrencyKind.PRIMOGEM, datetime(2026, 1, 1, 12, 0)) == 100


# --- apply_wish_batch -----------------------------------------------------


def test_fate_currency_mapping_per_banner_family():
    assert fate_currency_for(BannerKind.CHARACTER_EVENT) is CurrencyKind.INTERTWINED_FATE
    assert fate_currency_for(BannerKind.WEAPON_EVENT) is CurrencyKind.INTERTWINED_FATE
    assert fate_currency_for(BannerKind.CHRONICLED) is CurrencyKind.INTERTWINED_FATE
    assert fate_currency_for(BannerKind.STANDARD) is CurrencyKind.ACQUAINT_FATE


@pytest.mark.parametrize(
    ("banner", "debited", "untouched"),
    [
        (BannerKind.CHARACTER_EVENT, CurrencyKind.INTERTWINED_FATE, CurrencyKind.ACQUAINT_FATE),
        (BannerKind.WEAPON_EVENT, CurrencyKind.INTERTWINED_FATE, CurrencyKind.ACQUAINT_FATE),
        (BannerKind.CHRONICLED, CurrencyKind.INTERTWINED_FATE, CurrencyKind.ACQUAINT_FATE),
        (BannerKind.STANDARD, CurrencyKind.ACQUAINT_FATE, CurrencyKind.INTERTWINED_FATE),
    ],
)
def test_apply_wish_batch_debits_the_right_currency(banner, debited, untouched):
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 50, "seed", "manual", T0)
    record(ledger, CurrencyKind.ACQUAINT_FATE, 50, "seed", "manual", T0)

    result = apply_wish_batch(ledger, banner, 10)
    assert result.fate_currency is debited
    assert result.fates_spent == 10
    assert ledger.balance_of(debited) == 40
    assert ledger.balance_of(untouched) == 50


def test_apply_wish_batch_credits_the_standard_conversion_rates():
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 10, "seed", "manual", T0)
    rarities = [3, 3, 3, 3, 3, 3, 3, 3, 4, 5]

    result = apply_wish_batch(ledger, BannerKind.CHARACTER_EVENT, 10, rarities)
    assert result.stardust_gained == 8 * STARDUST_PER_3STAR == 120
    assert result.starglitter_gained == STARGLITTER_PER_4STAR + STARGLITTER_PER_5STAR == 12
    assert ledger.balance_of(CurrencyKind.STARDUST) == 120
    assert ledger.balance_of(CurrencyKind.STARGLITTER) == 12
    assert ledger.balance_of(CurrencyKind.INTERTWINED_FATE) == 0


def test_apply_wish_batch_without_rarities_claims_only_the_floor_yield():
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 10, "seed", "manual", T0)
    result = apply_wish_batch(ledger, BannerKind.CHARACTER_EVENT, 10)
    assert result.stardust_gained == 10 * STARDUST_PER_3STAR
    assert result.starglitter_gained == 0
    assert ledger.balance_of(CurrencyKind.STARGLITTER) == 0


def test_apply_wish_batch_records_an_overdraft_rather_than_refusing():
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 3, "seed", "manual", T0)
    result = apply_wish_batch(ledger, BannerKind.CHARACTER_EVENT, 10)
    assert result.fates_spent == 10
    assert ledger.balance_of(CurrencyKind.INTERTWINED_FATE) == -7


def test_apply_wish_batch_ignores_a_non_positive_count():
    ledger = _ledger()
    result = apply_wish_batch(ledger, BannerKind.CHARACTER_EVENT, 0)
    assert result.fates_spent == 0
    assert result.entries == ()
    assert ledger.entries == []


# --- estimate_velocity ----------------------------------------------------


def test_estimate_velocity_on_an_empty_ledger_is_zero_and_does_not_raise():
    velocity = estimate_velocity(_ledger(), 30)
    assert velocity.primogems_per_day == 0.0
    assert velocity.intertwined_fates_per_day == 0.0
    assert velocity.sampled_over_days == 0
    assert velocity.resin_per_day == 180


def test_estimate_velocity_uses_only_positive_entries():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 1800, "income", "manual", T0)
    record(ledger, CurrencyKind.PRIMOGEM, -1600, "ten pulls", "manual", T0 + timedelta(hours=1))
    velocity = estimate_velocity(ledger, 30, T0 + timedelta(days=1))
    # 1800 income over a 30 day window. The spend must not drag it negative.
    assert velocity.primogems_per_day == pytest.approx(60.0)
    assert velocity.sampled_over_days == 30


def test_estimate_velocity_excludes_entries_outside_the_window():
    ledger = _ledger()
    now = T0 + timedelta(days=60)
    record(ledger, CurrencyKind.PRIMOGEM, 9000, "ancient", "manual", T0)
    record(ledger, CurrencyKind.PRIMOGEM, 900, "recent", "manual", now - timedelta(days=5))
    velocity = estimate_velocity(ledger, 30, now)
    assert velocity.primogems_per_day == pytest.approx(30.0)


def test_estimate_velocity_counts_fates_separately():
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 14, "battle pass", "manual", T0)
    velocity = estimate_velocity(ledger, 14, T0 + timedelta(days=1))
    assert velocity.intertwined_fates_per_day == pytest.approx(1.0)
    assert velocity.primogems_per_day == 0.0


def test_estimate_velocity_rejects_a_non_positive_window_without_dividing_by_zero():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 100, "income", "manual", T0)
    velocity = estimate_velocity(ledger, 0, T0)
    assert velocity.primogems_per_day == 0.0
    assert velocity.sampled_over_days == 0


# --- pulls_affordable -----------------------------------------------------


@pytest.mark.parametrize(
    ("primogems", "expected"),
    [(0, 0), (1, 0), (159, 0), (160, 1), (161, 1), (319, 1), (320, 2), (16000, 100)],
)
def test_pulls_affordable_is_integer_division_at_160(primogems, expected):
    ledger = _ledger()
    if primogems:
        record(ledger, CurrencyKind.PRIMOGEM, primogems, "seed", "manual", T0)
    assert PRIMOGEMS_PER_FATE == 160
    assert pulls_affordable(ledger) == expected


def test_pulls_affordable_adds_held_fates():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 320, "seed", "manual", T0)
    record(ledger, CurrencyKind.INTERTWINED_FATE, 3, "seed", "manual", T0)
    record(ledger, CurrencyKind.ACQUAINT_FATE, 7, "seed", "manual", T0)
    # Character banner sees primogems plus intertwined fates only.
    assert pulls_affordable(ledger, BannerKind.CHARACTER_EVENT) == 5
    # Standard banner sees primogems plus acquaint fates only.
    assert pulls_affordable(ledger, BannerKind.STANDARD) == 9


def test_pulls_affordable_floors_a_negative_balance_at_zero():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, -500, "bad entry", "manual", T0)
    assert pulls_affordable(ledger) == 0


# --- project_balance ------------------------------------------------------


def test_project_balance_rolls_forward_at_the_modelled_rate():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 1000, "seed", "manual", T0)
    velocity = IncomeVelocity(primogems_per_day=60.0, intertwined_fates_per_day=0.5)
    assert project_balance(ledger, velocity, 10) == 1600
    assert project_balance(ledger, velocity, 0) == 1000


def test_project_balance_floors_a_fractional_projection():
    ledger = _ledger()
    record(ledger, CurrencyKind.INTERTWINED_FATE, 2, "seed", "manual", T0)
    velocity = IncomeVelocity(primogems_per_day=0.0, intertwined_fates_per_day=0.5)
    assert project_balance(ledger, velocity, 3, CurrencyKind.INTERTWINED_FATE) == 3


def test_project_balance_leaves_an_unmodelled_currency_flat():
    ledger = _ledger()
    record(ledger, CurrencyKind.ORIGINAL_RESIN, 120, "seed", "manual", T0)
    velocity = IncomeVelocity(primogems_per_day=60.0, resin_per_day=180)
    # Resin caps at 200, so it is deliberately not projected linearly here.
    assert project_balance(ledger, velocity, 30, CurrencyKind.ORIGINAL_RESIN) == 120


def test_project_balance_treats_a_negative_horizon_as_zero():
    ledger = _ledger()
    record(ledger, CurrencyKind.PRIMOGEM, 1000, "seed", "manual", T0)
    velocity = IncomeVelocity(primogems_per_day=60.0)
    assert project_balance(ledger, velocity, -5) == 1000


def test_ledger_functions_do_not_share_global_state():
    first, second = _ledger(), _ledger()
    record(first, CurrencyKind.PRIMOGEM, 100, "only first", "manual", T0)
    assert second.entries == []
    assert second.balance_of(CurrencyKind.PRIMOGEM) == 0
