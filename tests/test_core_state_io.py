"""Tests for account state serialization.

WHAT THIS IS AND, MORE IMPORTANTLY, WHAT IT IS NOT. The snapshot written here is
a DISPLAY cache so the dashboard has something to render on a cold start. It is
never an input to reconciliation. CLAUDE.md's live-state-first rule is explicit
that a stale cache must not be treated as truth, and the way that rule survives
the existence of a cache file is that `read_state` is only ever called by the
surface, never by `reconcile_state`.

So the assertions below are of three kinds:

1. **Round trip.** Every nested type has to survive, including the two that JSON
   quietly damages: integer dict keys become strings, and enums become bare
   strings that have to be mapped back.
2. **Totality.** A missing, truncated, malformed or future-schema file returns
   None rather than raising. A dashboard that will not open because a cache file
   was half-written is worse than one that opens empty.
3. **Staleness is legible.** A snapshot that carries no age is indistinguishable
   from a live reading, which is exactly the confusion live-state-first exists to
   prevent.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.state_io import (
    STATE_SCHEMA_VERSION,
    read_state,
    snapshot_age,
    state_from_dict,
    state_to_dict,
    write_state,
)
from core.types import (
    AccountState,
    BannerKind,
    CurrencyKind,
    Element,
    IncomeVelocity,
    LedgerEntry,
    MappedArtifact,
    MappedCharacter,
    MappedWeapon,
    PityState,
)

NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)


def populated() -> AccountState:
    """An account exercising every nested type at once."""
    state = AccountState(uid="618285856", adventure_rank=58, world_level=7)
    state.ledger.entries.append(
        LedgerEntry(
            entry_id="e1",
            occurred_at=NOW,
            currency=CurrencyKind.ORIGINAL_RESIN,
            delta=137,
            reason="observed",
            source="manual",
        )
    )
    state.ledger.entries.append(
        LedgerEntry(entry_id="e2", occurred_at=NOW, currency=CurrencyKind.MORA, delta=-4000, reason="spend")
    )
    state.pity = {
        BannerKind.CHARACTER_EVENT: PityState(
            banner=BannerKind.CHARACTER_EVENT,
            pity_5star=61,
            pity_4star=3,
            has_guarantee=True,
            consecutive_5050_losses=2,
        ),
        BannerKind.WEAPON_EVENT: PityState(banner=BannerKind.WEAPON_EVENT, pity_5star=12, fate_points=1),
    }
    state.roster = (
        MappedCharacter(
            avatar_id=10000096,
            level=80,
            ascension=5,
            constellations=0,
            talent_levels={100: 9, 101: 9, 102: 9},
            talent_levels_base={100: 6, 101: 6, 102: 6},
            friendship=8,
            weapon=MappedWeapon(
                item_id=99990001, name_hash="SYNTHETIC_W", level=90, ascension=6, refinement=5, rank_level=5
            ),
            artifacts=(
                MappedArtifact(
                    item_id=99990002,
                    set_name_hash="SYNTHETIC_SET",
                    rank_level=5,
                    level=20,
                    main_stat_id="SYNTHETIC_MAIN",
                    main_stat_value=46.6,
                    substats=(("SYNTHETIC_SUB", 5.8), ("SYNTHETIC_SUB2", 11.7)),
                    equip_type="EQUIP_BRACER",
                ),
            ),
            element=Element.PYRO,
            display_name="Arlecchino",
        ),
    )
    state.velocity = IncomeVelocity(
        primogems_per_day=60.0, intertwined_fates_per_day=0.4, resin_per_day=180, sampled_over_days=30
    )
    state.last_synced_at = NOW
    return state


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_a_populated_state_survives_a_round_trip():
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    original = populated()
    assert restored.uid == original.uid
    assert restored.adventure_rank == original.adventure_rank
    assert restored.world_level == original.world_level
    assert restored.last_synced_at == original.last_synced_at


def test_an_empty_state_survives_a_round_trip():
    """The fresh-account case, which is the one that will actually run first."""
    restored = state_from_dict(state_to_dict(AccountState(uid="")))
    assert restored is not None
    assert restored.uid == ""
    assert restored.roster == ()
    assert restored.pity == {}


def test_the_ledger_round_trips_with_its_currencies_intact():
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    assert len(restored.ledger.entries) == 2
    assert restored.ledger.balance_of(CurrencyKind.ORIGINAL_RESIN) == 137
    assert restored.ledger.balance_of(CurrencyKind.MORA) == -4000
    assert all(isinstance(e.currency, CurrencyKind) for e in restored.ledger.entries)
    assert all(isinstance(e.occurred_at, datetime) for e in restored.ledger.entries)


def test_pity_keys_come_back_as_enum_members_not_strings():
    """JSON has no enum. A dict keyed by the string 'character_event' would miss
    every lookup done with `BannerKind.CHARACTER_EVENT`, silently and forever."""
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    assert set(restored.pity) == {BannerKind.CHARACTER_EVENT, BannerKind.WEAPON_EVENT}
    for banner, pity in restored.pity.items():
        assert isinstance(banner, BannerKind)
        assert isinstance(pity.banner, BannerKind)
    assert restored.pity[BannerKind.CHARACTER_EVENT].consecutive_5050_losses == 2
    assert restored.pity[BannerKind.CHARACTER_EVENT].has_guarantee is True
    assert restored.pity[BannerKind.WEAPON_EVENT].fate_points == 1


def test_talent_level_keys_come_back_as_integers():
    """The other thing JSON damages: an int dict key is written as a string."""
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    talents = restored.roster[0].talent_levels
    assert talents == {100: 9, 101: 9, 102: 9}
    assert all(isinstance(key, int) for key in talents)
    assert restored.roster[0].talent_levels_base == {100: 6, 101: 6, 102: 6}


def test_the_roster_round_trips_with_its_weapon_and_artifacts():
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    character = restored.roster[0]
    assert character.avatar_id == 10000096
    assert character.element is Element.PYRO
    assert character.weapon is not None
    assert character.weapon.refinement == 5
    assert len(character.artifacts) == 1
    assert character.artifacts[0].substats == (("SYNTHETIC_SUB", 5.8), ("SYNTHETIC_SUB2", 11.7))


def test_a_character_with_no_weapon_round_trips_as_none():
    state = AccountState(uid="1")
    state.roster = (MappedCharacter(avatar_id=10000032, level=1, ascension=0, constellations=0),)
    restored = state_from_dict(state_to_dict(state))
    assert restored is not None
    assert restored.roster[0].weapon is None


def test_velocity_round_trips():
    restored = state_from_dict(state_to_dict(populated()))
    assert restored is not None
    assert restored.velocity.primogems_per_day == 60.0
    assert restored.velocity.sampled_over_days == 30


def test_the_payload_is_json_serializable_and_ascii():
    payload = json.dumps(state_to_dict(populated()), ensure_ascii=True)
    assert payload.isascii()
    assert json.loads(payload)["schema_version"] == STATE_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Totality - a bad file degrades, never raises
# ---------------------------------------------------------------------------


def test_reading_an_absent_file_returns_none_rather_than_raising(tmp_path):
    assert read_state(tmp_path / "nope.json") is None


def test_reading_malformed_json_returns_none(tmp_path):
    target = tmp_path / "account_state.json"
    target.write_text("{not json", encoding="utf-8")
    assert read_state(target) is None


def test_reading_a_truncated_payload_returns_none(tmp_path):
    """Readers poll mid-write elsewhere in this tree; assume it happens here."""
    target = tmp_path / "account_state.json"
    target.write_text('{"schema_version": 1, "uid": "6182', encoding="utf-8")
    assert read_state(target) is None


def test_a_future_schema_version_is_refused_rather_than_guessed(tmp_path):
    """Guessing at a format from the future is how a wrong number gets rendered."""
    target = tmp_path / "account_state.json"
    target.write_text(json.dumps({"schema_version": STATE_SCHEMA_VERSION + 99, "uid": "x"}), encoding="utf-8")
    assert read_state(target) is None


def test_a_payload_that_is_not_an_object_returns_none():
    for bad in [None, [], "text", 42, True]:
        assert state_from_dict(bad) is None


def test_a_garbled_nested_field_degrades_that_field_and_not_the_state():
    """One bad roster entry must not cost the whole snapshot.

    The alternative is a dashboard that renders nothing because a single
    artifact substat was the wrong type.
    """
    payload = state_to_dict(populated())
    payload["roster"].append({"avatar_id": "not an int"})
    payload["ledger"].append({"entry_id": "bad", "delta": "not an int"})
    restored = state_from_dict(payload)
    assert restored is not None
    assert restored.uid == "618285856"
    assert len(restored.roster) == 1
    assert len(restored.ledger.entries) == 2


def test_an_unknown_enum_value_degrades_rather_than_raising():
    payload = state_to_dict(populated())
    payload["pity"]["not_a_real_banner"] = {"pity_5star": 5}
    payload["roster"][0]["element"] = "not_a_real_element"
    restored = state_from_dict(payload)
    assert restored is not None
    assert set(restored.pity) == {BannerKind.CHARACTER_EVENT, BannerKind.WEAPON_EVENT}
    assert restored.roster[0].element is None


def test_a_pity_state_violating_its_own_invariants_is_dropped_not_raised():
    """PityState.__post_init__ rejects a 5050 streak above 3. A hand-edited or
    corrupted file must not turn that into an unhandled exception at startup."""
    payload = state_to_dict(populated())
    payload["pity"]["standard"] = {"pity_5star": 1, "consecutive_5050_losses": 99}
    restored = state_from_dict(payload)
    assert restored is not None
    assert BannerKind.STANDARD not in restored.pity


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def test_writing_then_reading_returns_an_equivalent_state(tmp_path):
    target = tmp_path / "nested" / "account_state.json"
    assert write_state(target, populated()) is True
    assert target.is_file()
    restored = read_state(target)
    assert restored is not None
    assert restored.uid == "618285856"
    assert restored.pity[BannerKind.CHARACTER_EVENT].pity_5star == 61


def test_writing_leaves_no_temp_file_behind(tmp_path):
    """Atomic write via core/atomic_io.py - the sibling temp must be renamed away."""
    target = tmp_path / "account_state.json"
    assert write_state(target, populated()) is True
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "account_state.json"]
    assert leftovers == []


def test_the_written_file_is_ascii_on_disk(tmp_path):
    target = tmp_path / "account_state.json"
    write_state(target, populated())
    assert target.read_text(encoding="utf-8").isascii()


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def test_snapshot_age_reports_how_old_the_reading_is():
    state = populated()
    age = snapshot_age(state, now=NOW + timedelta(hours=3))
    assert age == timedelta(hours=3)


def test_snapshot_age_is_none_when_the_state_was_never_synced():
    """None is not zero. A snapshot with no sync time is not a fresh one."""
    assert snapshot_age(AccountState(uid="x"), now=NOW) is None


def test_snapshot_age_never_goes_negative():
    """A clock that moved backwards, or a file written by another machine."""
    age = snapshot_age(populated(), now=NOW - timedelta(hours=5))
    assert age == timedelta(0)


def test_a_naive_last_synced_at_is_treated_as_utc_rather_than_crashing():
    """Comparing naive and aware datetimes raises. A hand-edited file can carry
    either, so the boundary normalises instead of propagating a TypeError."""
    state = populated()
    state.last_synced_at = datetime(2026, 9, 6, 19, 30)
    age = snapshot_age(state, now=NOW + timedelta(hours=1))
    assert age == timedelta(hours=1)
