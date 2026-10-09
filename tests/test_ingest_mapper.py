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
from ingest.enka_client import DEFAULT_TTL_SECONDS
from ingest.enka_mapper import (
    REFINEMENT_MAX,
    REFINEMENT_MIN,
    fold_talent_levels,
    map_artifact,
    map_character,
    map_profile,
    map_weapon,
    read_prop,
    refinement_from_affix_map,
    split_equipment,
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


# ---------------------------------------------------------------------------
# Boundary arms - each pins a branch the trap tests above leave unproven.
# Inputs are hand-authored dicts; the only ids are the fixture's 9xxxxxxx
# placeholders and the verified avatarIds already named at the top of this file.
# ---------------------------------------------------------------------------


# -- trap 4 edges: refinement_from_affix_map -------------------------------


def test_affix_map_values_outside_the_documented_range_stay_inside_the_presented_rank():
    """`MappedWeapon.refinement` stores the PRESENTED rank 1..5 (core/types.py).

    The documented input range is 0..4. What an out-of-range value maps to is
    NOT documented, so this arm pins only the field contract - whatever comes
    back is still a presentable rank - and not the specific clamp value.
    """
    for out_of_range in (9, 5, -3):
        presented = refinement_from_affix_map({"190000001": out_of_range})
        assert REFINEMENT_MIN <= presented <= REFINEMENT_MAX, f"affixMap {out_of_range} -> {presented}"
    assert (REFINEMENT_MIN, REFINEMENT_MAX) == (1, 5)


def test_unreadable_affix_map_values_present_as_r1():
    """Docstring: an absent or UNREADABLE map means an unrefined weapon, R1.

    Where the R1 comes from: an unreadable value coerces to -1 and the result is
    then clamped to REFINEMENT_MIN at enka_mapper.py:143. The `v >= 0` filter at
    :139-141 is dead in effect - deleting it changes no output, because the
    clamp catches the same cases - so this arm grades the clamp and the
    non-dict branch at :136-137, not the filter.
    """
    assert refinement_from_affix_map({"190000001": "abc"}) == 1
    assert refinement_from_affix_map({"190000001": None}) == 1
    # A truthy non-dict is as unreadable as a missing one.
    assert refinement_from_affix_map("4") == 1  # type: ignore[arg-type]


def test_affix_map_string_coded_value_is_coerced_like_every_other_wire_number():
    """Upstream sends numbers as strings in several places (mapper coercions)."""
    assert refinement_from_affix_map({"190000001": "2"}) == 3


# -- equipment edges: map_weapon / map_artifact / split_equipment ----------


def test_weapon_entry_without_a_weapon_object_still_maps_as_a_weapon_at_r1():
    """`flat.itemType` says weapon, so it IS one, even with no `weapon` sub-object.

    Absent `affixMap` presents as R1 by the documented rule. The level and
    ascension a missing `weapon` object falls to are NOT asserted: no document
    states them, and the module's weapon default (enka_mapper.py:234, level 1)
    disagrees with its character default (read_prop, 0). Which is right is an
    adjudicator's call, not a pin.
    """
    weapon = map_weapon(
        {
            "itemId": 90000001,
            "flat": {
                "itemType": EquipItemType.WEAPON.value,
                "nameTextHashMap": "SYNTHETIC_WEAPON_NAME_A",
                "rankLevel": 4,
            },
        }
    )
    assert weapon.item_id == 90000001
    assert weapon.name_hash == "SYNTHETIC_WEAPON_NAME_A"
    assert weapon.rank_level == 4
    assert weapon.refinement == 1


def test_artifact_level_and_item_id_are_carried_verbatim(payload):
    """Docstring: `level` is carried through VERBATIM, no off-by-one applied."""
    profile = map_profile(payload)
    artifact = _character(profile, ARLECCHINO).artifacts[0]
    raw = next(
        e for a in payload["avatarInfoList"] if a["avatarId"] == ARLECCHINO for e in a["equipList"] if "reliquary" in e
    )
    assert raw["reliquary"]["level"] == 21  # guard the guard: the fixture still carries it
    assert artifact.level == 21
    assert artifact.item_id == 90000002


def test_artifact_substats_skip_non_dict_entries_and_coerce_string_values():
    entry = {
        "itemId": 90000002,
        "flat": {
            "itemType": EquipItemType.RELIQUARY.value,
            "reliquarySubstats": [1, {"appendPropId": "SYNTHETIC_PROP_X", "propValue": "2.5"}],
        },
    }
    assert map_artifact(entry).substats == (("SYNTHETIC_PROP_X", 2.5),)

    entry["flat"]["reliquarySubstats"] = "x"
    assert map_artifact(entry).substats == ()


def test_split_equipment_skips_non_dict_entries_and_entries_without_flat():
    """No `flat` means no `itemType`, and an unrecognised itemType is skipped."""
    assert split_equipment(["x", 1, {"itemId": 1}]) == (None, ())
    assert split_equipment("x") == (None, ())
    assert split_equipment(None) == (None, ())


def test_empty_equip_list_yields_no_weapon_and_no_artifacts(payload):
    bennett = next(a for a in payload["avatarInfoList"] if a["avatarId"] == BENNETT)
    assert bennett["equipList"] == []  # guard the guard
    mapped = map_character(bennett)
    assert mapped.weapon is None
    assert mapped.artifacts == ()


# -- trap 1 edge: avatarInfoList present but empty, or malformed ----------


def test_present_but_empty_avatar_info_list_counts_as_an_open_showcase():
    """Key PRESENCE is the documented signal, so [] is open-with-nobody-in-it."""
    profile = map_profile({"avatarInfoList": []})
    assert profile.showcase_open is True
    assert profile.characters == ()


def test_malformed_avatar_info_list_entries_are_skipped_not_fatal():
    """SPEC section 5 says upstream never sends these shapes; the mapper still must not raise.

    What `showcase_open` reads for a non-list value is deliberately NOT asserted:
    it is a non-occurring input and no document assigns it a meaning.
    """
    profile = map_profile({"avatarInfoList": [1, None, {"avatarId": BENNETT}]})
    assert [c.avatar_id for c in profile.characters] == [BENNETT]

    profile = map_profile({"avatarInfoList": "x"})
    assert profile.characters == ()


# -- profile header edges --------------------------------------------------


def test_player_info_that_is_not_a_dict_maps_to_a_blank_header():
    profile = map_profile({"playerInfo": "x"})
    assert profile.nickname == ""
    assert profile.adventure_rank == 0
    assert profile.world_level == 0


def test_uid_argument_overrides_the_payload_uid():
    assert map_profile({"uid": "000000000"}, uid="000000001").uid == "000000001"
    assert map_profile({"uid": "000000000"}).uid == "000000000"
    assert map_profile({}).uid == ""


def test_ttl_absent_or_unreadable_defaults_to_the_client_fallback():
    """A drift guard across three literal 60s, not a shared constant.

    The mapper does not reference DEFAULT_TTL_SECONDS: enka_mapper.py:407 is a
    literal 60, enka_client.py:99 another, core/types.py:309 a third. No
    document says they must agree; this arm exists so that if one moves the
    others are noticed.
    """
    assert map_profile({}).ttl_seconds == DEFAULT_TTL_SECONDS
    assert map_profile({"ttl": "x"}).ttl_seconds == DEFAULT_TTL_SECONDS
    assert map_profile({"ttl": "120"}).ttl_seconds == 120


# -- trap 2 edge: talentIdList that is not a list ---------------------------


def test_talent_id_list_that_is_not_a_list_counts_as_c0():
    assert map_character({"avatarId": BENNETT, "talentIdList": "abc"}).constellations == 0
    assert map_character({"avatarId": BENNETT, "talentIdList": {"a": 1}}).constellations == 0


def test_missing_fetter_info_and_prop_map_default_to_zero():
    mapped = map_character({"avatarId": BENNETT})
    assert mapped.friendship == 0
    assert mapped.level == 0
    assert mapped.ascension == 0
    assert mapped.talent_levels == {}

    mapped = map_character({"avatarId": BENNETT, "fetterInfo": "x", "propMap": "y"})
    assert (mapped.friendship, mapped.level, mapped.ascension) == (0, 0, 0)


# -- trap 3 edges: the fold's resolution order ------------------------------


def test_skill_group_map_is_threaded_through_map_profile():
    """The live-shaped resolution must reach map_profile callers, not just fold callers."""
    payload = {
        "avatarInfoList": [
            {
                "avatarId": ARLECCHINO,
                "skillLevelMap": {"9000101": 9},
                "proudSkillExtraLevelMap": {"7777": 3},
            }
        ]
    }
    with_map = map_profile(payload, skill_group_map={7777: 9000101}).characters[0]
    assert with_map.talent_levels == {9000101: 12}
    assert with_map.talent_levels_base == {9000101: 9}

    without_map = map_profile(payload).characters[0]
    assert without_map.talent_levels == without_map.talent_levels_base == {9000101: 9}


def test_positional_fallback_cannot_place_three_base_talents_against_two_bonus_keys():
    """Three base talents, two bonus keys: the lengths differ, so even opt-in does not guess.

    This says nothing about which constellation produces this shape; the
    fixture's own C3 carries one bonus key. The subject is the length rule at
    enka_mapper.py:172-173.
    """
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9, "9000103": 9},
        "proudSkillExtraLevelMap": {"7777": 3, "7778": 3},
    }
    effective, base, unresolved = fold_talent_levels(avatar, positional_fallback=True)
    assert unresolved == {7777: 3, 7778: 3}
    assert effective == base


def test_positional_fallback_never_double_bonuses_a_directly_hit_skill():
    """Docstring contract: the positional pairing fires only when the two MAPS are the
    same length. Three bonus keys against two talents is not that, even after a direct
    hit shrinks the pending set to two. The directly hit skill is bonused once and the
    two unplaceable bonuses are RETURNED, never laundered onto the remaining talents."""
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9},
        "proudSkillExtraLevelMap": {"9000101": 3, "7777": 3, "7778": 3},
    }
    effective, base, unresolved = fold_talent_levels(avatar, positional_fallback=True)
    assert effective == {9000101: 12, 9000102: 9}
    assert base == {9000101: 9, 9000102: 9}
    assert unresolved == {7777: 3, 7778: 3}


def test_positional_fallback_never_fires_after_an_explicit_map_placement():
    """Sibling of the direct-hit case: an explicit skill_group_map placement is also a
    placement, so the positional branch must stay shut for the remainder."""
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9, "9000102": 9},
        "proudSkillExtraLevelMap": {"5555": 3, "7777": 3, "7778": 3},
    }
    effective, base, unresolved = fold_talent_levels(
        avatar, skill_group_map={5555: 9000101}, positional_fallback=True
    )
    assert effective == {9000101: 12, 9000102: 9}
    assert base == {9000101: 9, 9000102: 9}
    assert unresolved == {7777: 3, 7778: 3}


def test_zero_bonus_entries_are_neither_folded_nor_reported():
    """An EXPLICIT zero bonus is skipped at enka_mapper.py:200-201.

    Pinned because a zero adds nothing to fold and nothing to report. The same
    branch also swallows an UNREADABLE bonus value ("abc", None coerce to 0),
    which SPEC 5.1 says should be RETURNED as unresolved rather than dropped.
    That contradiction is filed for an adjudicator and is NOT asserted here;
    a fix that tells unreadable from zero keeps this arm green.
    """
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9},
        "proudSkillExtraLevelMap": {"9000101": 0, "7777": 0},
    }
    effective, base, unresolved = fold_talent_levels(avatar)
    assert effective == base == {9000101: 9}
    assert unresolved == {}


def test_explicit_map_to_a_skill_absent_from_base_stays_unresolved():
    """A caller-supplied mapping onto a skill the payload does not carry is not invented."""
    avatar = {
        "avatarId": ARLECCHINO,
        "skillLevelMap": {"9000101": 9},
        "proudSkillExtraLevelMap": {"7777": 3},
    }
    effective, base, unresolved = fold_talent_levels(avatar, skill_group_map={7777: 9000199})
    assert unresolved == {7777: 3}
    assert effective == base == {9000101: 9}


# -- trap 6 edges: read_prop key and value shapes ---------------------------


def test_read_prop_accepts_int_keys_and_rejects_blank_or_malformed_entries():
    """Docstring: keys arrive as strings on the wire; an int key is accepted too."""
    assert read_prop({4001: {"val": "5"}}, 4001) == 5
    assert read_prop({"4001": {"val": ""}}, 4001, default=-1) == -1
    assert read_prop({"4001": {"val": None}}, 4001, default=-1) == -1
    assert read_prop({"4001": {"val": "abc"}}, 4001, default=-1) == -1
    assert read_prop({"4001": "x"}, 4001, default=-1) == -1
    # ival alone is "Ignore it" - with no val there is nothing to read.
    assert read_prop({"4001": {"ival": "3"}}, 4001, default=-1) == -1
