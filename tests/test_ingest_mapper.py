"""Regression tests for the verified Enka payload traps.

One test per trap in `docs/SPEC_SCAFFOLD.md` section 5. These are regression
tests in the strict sense: each one FAILS against the naive implementation the
trap describes, so deleting the guard in `ingest/enka_mapper.py` turns the test
red rather than leaving it quietly passing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.types import Element, EquipItemType
from ingest.enka_mapper import (
    fold_talent_levels,
    map_character,
    map_profile,
    read_prop,
    refinement_from_affix_map,
)
from ingest.static_data import StaticIdentity

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "enka_sample_profile.json"

BENNETT = 10000032
ARLECCHINO = 10000096
NOELLE = 10000034


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _character(profile, avatar_id: int):
    for character in profile.characters:
        if character.avatar_id == avatar_id:
            return character
    raise AssertionError(f"avatar {avatar_id} missing from the mapped profile")


# ---------------------------------------------------------------------------
# TRAP 1 - avatarInfoList is ABSENT when the showcase is closed, not []
# ---------------------------------------------------------------------------


def test_closed_showcase_yields_empty_roster_and_does_not_raise():
    closed = {"uid": "000000000", "ttl": 60, "playerInfo": {"nickname": "Closed", "level": 55}}
    assert "avatarInfoList" not in closed  # the whole point of the trap

    profile = map_profile(closed)

    assert profile.showcase_open is False
    assert profile.characters == ()
    # A closed showcase is a normal state, so the rest of the profile still maps.
    assert profile.nickname == "Closed"
    assert profile.adventure_rank == 55


def test_open_showcase_is_detected_by_key_presence(payload):
    profile = map_profile(payload)
    assert profile.showcase_open is True
    assert len(profile.characters) == 3


# ---------------------------------------------------------------------------
# TRAP 2 - talentIdList KEY IS MISSING at C0 (the most important test here)
# ---------------------------------------------------------------------------


def test_fixture_actually_omits_talent_id_list_at_c0(payload):
    """Guard the guard: if the fixture ever grows the key, trap 2 stops being tested."""
    bennett = next(a for a in payload["avatarInfoList"] if a["avatarId"] == BENNETT)
    assert "talentIdList" not in bennett
    with pytest.raises(KeyError):
        len(bennett["talentIdList"])  # exactly what a naive reader does


def test_c0_character_maps_without_keyerror(payload):
    bennett = next(a for a in payload["avatarInfoList"] if a["avatarId"] == BENNETT)

    # The assertion is that this call does NOT raise. pytest fails the test on
    # any exception, and the KeyError above proves the raw payload would.
    mapped = map_character(bennett)

    assert mapped.constellations == 0
    assert mapped.avatar_id == BENNETT


def test_constellation_count_is_talent_id_list_length(payload):
    profile = map_profile(payload)
    assert _character(profile, ARLECCHINO).constellations == 3
    assert _character(profile, NOELLE).constellations == 1
    assert _character(profile, BENNETT).constellations == 0


# ---------------------------------------------------------------------------
# TRAP 3 - skillLevelMap EXCLUDES constellation-granted +3 levels
# ---------------------------------------------------------------------------


def test_constellation_talent_bonus_is_folded_into_effective_level(payload):
    profile = map_profile(payload)
    arlecchino = _character(profile, ARLECCHINO)

    bonused = 9000102  # carries a +3 in proudSkillExtraLevelMap
    assert arlecchino.talent_levels_base[bonused] == 9
    assert arlecchino.talent_levels[bonused] == 12
    # The headline assertion: effective EXCEEDS base for a constellated character.
    assert arlecchino.talent_levels[bonused] > arlecchino.talent_levels_base[bonused]

    # Untouched talents must not drift.
    for skill_id in (9000101, 9000103):
        assert arlecchino.talent_levels[skill_id] == arlecchino.talent_levels_base[skill_id] == 9


def test_unconstellated_character_has_effective_equal_to_base(payload):
    profile = map_profile(payload)
    bennett = _character(profile, BENNETT)
    assert bennett.talent_levels == bennett.talent_levels_base
    assert set(bennett.talent_levels.values()) == {6}


def test_explicit_skill_group_map_resolves_a_live_shaped_bonus():
    """Live payloads key the bonus map by proudSkillGroupId, not skillId."""
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9},
        "proudSkillExtraLevelMap": {"7777": 3},
    }
    effective, base, unresolved = fold_talent_levels(avatar, skill_group_map={7777: 9000102})
    assert effective[9000102] == 12
    assert base[9000102] == 9
    assert unresolved == {}


def test_unresolvable_bonus_is_reported_not_guessed():
    """No skill-depot data is vendored, so an unplaceable bonus is surfaced."""
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9, "9000103": 9},
        "proudSkillExtraLevelMap": {"7777": 3},
    }
    effective, base, unresolved = fold_talent_levels(avatar)
    assert unresolved == {7777: 3}
    assert effective == base  # nothing was invented


def test_positional_fallback_is_default_off():
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9},
        "proudSkillExtraLevelMap": {"7777": 3, "7778": 3},
    }
    off_effective, off_base, off_unresolved = fold_talent_levels(avatar)
    assert off_effective == off_base
    assert off_unresolved == {7777: 3, 7778: 3}

    on_effective, _base, on_unresolved = fold_talent_levels(avatar, positional_fallback=True)
    assert on_unresolved == {}
    assert on_effective == {9000101: 12, 9000102: 12}


# ---------------------------------------------------------------------------
# TRAP 4 - affixMap lives on the weapon, range 0..4, presented rank is +1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("affix_value", "presented"),
    [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
)
def test_affix_map_value_maps_to_presented_refinement(affix_value, presented):
    assert refinement_from_affix_map({"190000001": affix_value}) == presented


def test_absent_affix_map_presents_as_r1():
    assert refinement_from_affix_map(None) == 1
    assert refinement_from_affix_map({}) == 1


def test_refinement_read_end_to_end_from_the_weapon_object(payload):
    profile = map_profile(payload)
    # affixMap 4 -> R5
    assert _character(profile, ARLECCHINO).weapon.refinement == 5
    # affixMap 0 -> R1
    assert _character(profile, NOELLE).weapon.refinement == 1


def test_affix_map_is_not_read_from_flat_or_top_level():
    """The brief put affixMap at the top level and under flat. Both are decoys."""
    avatar = {
        "avatarId": ARLECCHINO,
        "affixMap": {"1": 4},  # decoy: not where it lives
        "equipList": [
            {
                "itemId": 90000001,
                "weapon": {"level": 90, "promoteLevel": 6},  # no affixMap here
                "flat": {
                    "itemType": EquipItemType.WEAPON.value,
                    "nameTextHashMap": "SYNTHETIC_WEAPON_NAME_A",
                    "rankLevel": 5,
                    "affixMap": {"1": 4},  # decoy: not where it lives either
                },
            }
        ],
    }
    mapped = map_character(avatar)
    # Reading either decoy would yield R5. The real location is empty, so R1.
    assert mapped.weapon is not None
    assert mapped.weapon.refinement == 1


# ---------------------------------------------------------------------------
# TRAP 5 - the wire key is avatarId, not the docs-table misprint avatarID
# ---------------------------------------------------------------------------


def test_wire_key_is_avatar_id_lowercase_d(payload):
    for avatar in payload["avatarInfoList"]:
        assert "avatarId" in avatar
        assert "avatarID" not in avatar


def test_docs_table_misprint_is_not_accepted():
    mapped = map_character({"avatarID": ARLECCHINO})
    # Silently accepting the misprint would mask a genuinely malformed payload.
    assert mapped.avatar_id == 0


# ---------------------------------------------------------------------------
# TRAP 6 - propMap 1001 XP / 1002 Ascension / 4001 Level, and ival is "ignore it"
# ---------------------------------------------------------------------------


def test_prop_map_reads_val_not_ival(payload):
    profile = map_profile(payload)
    bennett = _character(profile, BENNETT)
    # ival is 0 for every entry in the fixture, val is the real number. A reader
    # that took ival would report level 0 and ascension 0 here.
    assert bennett.level == 80
    assert bennett.ascension == 5
    assert _character(profile, ARLECCHINO).level == 90
    assert _character(profile, NOELLE).level == 70


def test_prop_map_types_are_the_documented_ones():
    prop_map = {
        "1001": {"type": 1001, "ival": "0", "val": "8967"},
        "1002": {"type": 1002, "ival": "0", "val": "6"},
        "4001": {"type": 4001, "ival": "0", "val": "90"},
    }
    assert read_prop(prop_map, 1001) == 8967  # XP
    assert read_prop(prop_map, 1002) == 6  # Ascension
    assert read_prop(prop_map, 4001) == 90  # Level
    assert read_prop(prop_map, 9999, default=-1) == -1
    assert read_prop(None, 4001, default=-1) == -1


# ---------------------------------------------------------------------------
# TRAP 7 - flat.itemType is exactly ITEM_RELIQUARY or ITEM_WEAPON
# ---------------------------------------------------------------------------


def test_item_type_values_match_the_enum(payload):
    types = {e["flat"]["itemType"] for a in payload["avatarInfoList"] for e in a.get("equipList", [])}
    assert types <= {EquipItemType.WEAPON.value, EquipItemType.RELIQUARY.value}
    assert EquipItemType.WEAPON.value == "ITEM_WEAPON"
    assert EquipItemType.RELIQUARY.value == "ITEM_RELIQUARY"


def test_unknown_item_type_is_skipped_not_guessed():
    avatar = {
        "avatarId": ARLECCHINO,
        "equipList": [
            {"itemId": 1, "weapon": {"affixMap": {"1": 4}}, "flat": {"itemType": "ITEM_SOMETHING_ELSE"}},
        ],
    }
    mapped = map_character(avatar)
    assert mapped.weapon is None
    assert mapped.artifacts == ()


# ---------------------------------------------------------------------------
# TRAP 8 - artifact substats are flat.reliquarySubstats [{appendPropId, propValue}]
# ---------------------------------------------------------------------------


def test_artifact_substats_are_read_from_flat(payload):
    profile = map_profile(payload)
    artifacts = _character(profile, ARLECCHINO).artifacts
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.substats == (
        ("SYNTHETIC_PROP_CRIT_RATE", 7.8),
        ("SYNTHETIC_PROP_ATTACK_PERCENT", 9.9),
    )
    assert artifact.main_stat_id == "SYNTHETIC_PROP_HP"
    assert artifact.main_stat_value == pytest.approx(4780.0)
    assert artifact.set_name_hash == "SYNTHETIC_SET_NAME_A"
    assert artifact.equip_type == "EQUIP_BRACER"
    assert artifact.rank_level == 5


# ---------------------------------------------------------------------------
# Profile-level mapping and identity injection
# ---------------------------------------------------------------------------


def test_profile_header_fields(payload):
    profile = map_profile(payload)
    assert profile.uid == "000000000"
    assert profile.nickname == "SyntheticTraveler"
    assert profile.world_level == 8
    assert profile.adventure_rank == 60
    assert profile.achievements == 123
    assert profile.abyss_floor == 12
    assert profile.abyss_chamber == 3
    assert profile.ttl_seconds == 60


def test_identity_injection_fills_names_and_elements(payload):
    profile = map_profile(payload, identity=StaticIdentity())
    assert _character(profile, ARLECCHINO).display_name == "Arlecchino"
    assert _character(profile, ARLECCHINO).element is Element.PYRO
    assert _character(profile, NOELLE).element is Element.GEO


def test_mapper_is_pure_without_identity(payload):
    """No identity injected means no names invented."""
    profile = map_profile(payload)
    assert all(c.display_name == "" for c in profile.characters)
    assert all(c.element is None for c in profile.characters)


def test_weapon_fields_round_out(payload):
    profile = map_profile(payload)
    weapon = _character(profile, ARLECCHINO).weapon
    assert weapon.item_id == 90000001
    assert weapon.level == 90
    assert weapon.ascension == 6
    assert weapon.rank_level == 5
    assert weapon.name_hash == "SYNTHETIC_WEAPON_NAME_A"


def test_friendship_comes_from_fetter_info(payload):
    profile = map_profile(payload)
    assert _character(profile, ARLECCHINO).friendship == 10
    assert _character(profile, BENNETT).friendship == 8
