"""Pure mapping from a raw upstream profile payload to the internal contract.

No I/O whatsoever lives here: every function takes a dict and returns dataclasses
from `core.types`. Identity lookup (display name, element) is injected as an
optional `IdentityLookup`, so the mapper stays a pure function even though names
come from a file on disk.

This module is where the VERIFIED upstream traps are absorbed, once, at the
boundary. Every consumer downstream is entitled to assume they are already dealt
with. Each trap is commented at the site that handles it and has a dedicated
regression test in `tests/test_ingest_mapper.py`.

The traps, all verified in `docs/SPEC_SCAFFOLD.md` section 5:

1. `avatarInfoList` is ABSENT ENTIRELY when the showcase is closed. Not `[]`.
2. `talentIdList` KEY IS MISSING at C0. `len(avatar["talentIdList"])` raises.
3. `skillLevelMap` EXCLUDES constellation-granted +3 levels. They live in
   `proudSkillExtraLevelMap`, which the upstream docs table omits.
4. `affixMap` is at `equipList[].weapon.affixMap` - NOT top level, NOT under
   `flat` - and its range is 0..4, so presented refinement is that PLUS ONE.
5. The wire key is `avatarId`. The docs table misprints it as `avatarID`.
6. `propMap` types are 1001 XP, 1002 Ascension, 4001 Level, and `ival` is
   documented as "Ignore it" - read `val`.
7. `flat.itemType` is exactly "ITEM_RELIQUARY" or "ITEM_WEAPON".
8. Artifact substats are `flat.reliquarySubstats` as [{appendPropId, propValue}].
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from core.types import (
    Element,
    EnkaMappedProfile,
    EquipItemType,
    MappedArtifact,
    MappedCharacter,
    MappedWeapon,
)

# --- propMap types (trap 6) ------------------------------------------------
PROP_XP = 1001
PROP_ASCENSION = 1002
PROP_LEVEL = 4001

# --- affixMap range (trap 4) ----------------------------------------------
AFFIX_MIN = 0
AFFIX_MAX = 4
REFINEMENT_MIN = AFFIX_MIN + 1
REFINEMENT_MAX = AFFIX_MAX + 1

#: The wire key. Trap 5: the upstream docs TABLE misprints this as `avatarID`,
#: with a capital D. That misprint is deliberately absent from this module - a
#: reader that falls back to it would silently accept a payload shape that does
#: not exist and mask a real parse failure.
AVATAR_ID_KEY = "avatarId"


class IdentityLookup(Protocol):
    """Minimal shape the mapper needs from an identity table.

    Injected rather than imported so this module performs no I/O and so a caller
    can supply a different table (a test stub, a future live source) without
    touching the mapper. `ingest.static_data.StaticIdentity` satisfies it.
    """

    def character_name(self, avatar_id: int) -> str: ...

    def element_for(self, avatar_id: int) -> Element | None: ...


# ---------------------------------------------------------------------------
# Small coercions - upstream sends numbers as strings in several places
# ---------------------------------------------------------------------------


def _as_int(value: object, default: int = 0) -> int:
    # Narrow before converting rather than suppressing the type error. The
    # upstream payload is untyped JSON, so `value` really is `object`, and a
    # bare `int(value)` is a call-overload error that a `type: ignore` would
    # only hide. JSON admits str, int, float, bool, None, list and dict; the
    # first three convert, bool converts because it subclasses int, and the
    # rest fall through to the default exactly as the old TypeError path did.
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def read_prop(prop_map: dict | None, prop_type: int, default: int = 0) -> int:
    """Read one `propMap` entry.

    TRAP 6: an entry is `{type, ival, val}` and the upstream docs say of `ival`
    "Ignore it". `val` is the real number. A reader that takes `ival` reports 0
    for every level, which is why the test fixture makes the two disagree.

    Keys arrive as strings on the wire; an int key is accepted too so a caller
    that already normalised the map is not punished.
    """
    if not isinstance(prop_map, dict):
        return default
    entry = prop_map.get(str(prop_type))
    if entry is None:
        entry = prop_map.get(prop_type)
    if not isinstance(entry, dict):
        return default
    raw = entry.get("val")
    if raw is None or raw == "":
        return default
    return _as_int(raw, default)


def refinement_from_affix_map(affix_map: dict | None) -> int:
    """Convert `weapon.affixMap` into the PRESENTED refinement rank.

    TRAP 4: `affixMap` lives at `equipList[].weapon.affixMap`. It is neither top
    level nor under `flat`, which is where the original brief put it. Its
    documented value range is 0..4, i.e. R1..R5 minus one, so the presented rank
    is the value PLUS ONE.

    The conversion happens exactly here, once, at the boundary. `MappedWeapon`
    stores the presented 1..5 rank, so no downstream consumer ever has to
    remember the offset - and no consumer can apply it twice.

    An absent or unreadable map means an unrefined weapon, which presents as R1.
    """
    if not isinstance(affix_map, dict) or not affix_map:
        return REFINEMENT_MIN
    values = [_as_int(v, -1) for v in affix_map.values()]
    values = [v for v in values if v >= 0]
    if not values:
        return REFINEMENT_MIN
    presented = max(values) + 1
    return max(REFINEMENT_MIN, min(REFINEMENT_MAX, presented))


# ---------------------------------------------------------------------------
# Talent levels (trap 3)
# ---------------------------------------------------------------------------


def fold_talent_levels(
    avatar: dict,
    skill_group_map: dict[int, int] | None = None,
    positional_fallback: bool = False,
) -> tuple[dict[int, int], dict[int, int], dict[int, int]]:
    """Return (effective_levels, base_levels, unresolved_bonuses).

    TRAP 3: `skillLevelMap` does NOT include constellation-granted +3 talent
    levels. Those live in `proudSkillExtraLevelMap`, a real field the upstream
    docs table omits entirely. A talent reader that ignores it is wrong for
    every C3+ character, and wrong in the direction that matters - it
    under-reports the talent a player has actually invested in.

    Resolution order, most trustworthy first:

    1. An explicit `skill_group_map` (proudSkillGroupId -> skillId) supplied by
       the caller. This is the only exact answer for a live payload, because the
       bonus map is keyed by proudSkillGroupId and resolving it needs the
       character's skill depot.
    2. A direct key hit - the bonus key is already a skillId present in
       `skillLevelMap`.
    3. `positional_fallback`, DEFAULT-OFF: pair the sorted bonus keys with the
       sorted skill keys when the two maps are the same length. This is an
       approximation that is only correct when every talent received a bonus, so
       it is opt-in rather than a silent guess.

    Anything still unresolved is RETURNED rather than guessed at or dropped
    silently. This repository vendors no skill-depot data (see
    `data/fixtures/README.md`), so inventing a numeric relation between
    proudSkillGroupId and skillId would be scaffolding on an assumption. The
    honest answer is "these bonuses exist and I could not place them".
    """
    raw_base = avatar.get("skillLevelMap") or {}
    base: dict[int, int] = {}
    if isinstance(raw_base, dict):
        for key, value in raw_base.items():
            base[_as_int(key)] = _as_int(value)

    effective = dict(base)
    unresolved: dict[int, int] = {}

    raw_extra = avatar.get("proudSkillExtraLevelMap") or {}
    if not isinstance(raw_extra, dict) or not raw_extra:
        return effective, base, unresolved

    pending: dict[int, int] = {}
    for key, value in raw_extra.items():
        group_id = _as_int(key)
        bonus = _as_int(value)
        if bonus == 0:
            continue
        target: int | None = None
        if skill_group_map and group_id in skill_group_map:
            target = skill_group_map[group_id]
        elif group_id in effective:
            target = group_id
        if target is not None and target in effective:
            effective[target] += bonus
        else:
            pending[group_id] = bonus

    if pending and positional_fallback and len(pending) == len(base) and base:
        # Opt-in approximation. Correct only when every talent got a bonus.
        for group_id, target in zip(sorted(pending), sorted(base)):
            effective[target] += pending[group_id]
        pending = {}

    unresolved.update(pending)
    return effective, base, unresolved


# ---------------------------------------------------------------------------
# Equipment (traps 4, 7, 8)
# ---------------------------------------------------------------------------


def map_weapon(equip: dict) -> MappedWeapon:
    """Map one `equipList` entry whose `flat.itemType` is ITEM_WEAPON."""
    weapon = equip.get("weapon") or {}
    flat = equip.get("flat") or {}
    return MappedWeapon(
        item_id=_as_int(equip.get("itemId")),
        name_hash=str(flat.get("nameTextHashMap", "")),
        level=_as_int(weapon.get("level"), 1),
        ascension=_as_int(weapon.get("promoteLevel")),
        # TRAP 4 handled once, here. Stored value is the PRESENTED 1..5 rank.
        refinement=refinement_from_affix_map(weapon.get("affixMap")),
        rank_level=_as_int(flat.get("rankLevel")),
    )


def map_artifact(equip: dict) -> MappedArtifact:
    """Map one `equipList` entry whose `flat.itemType` is ITEM_RELIQUARY.

    TRAP 8: substats are `flat.reliquarySubstats`, a list of
    `{appendPropId, propValue}`. They are under `flat`, alongside the mainstat -
    not under `reliquary`, which carries only the raw id lists.

    `level` is carried through verbatim. No off-by-one adjustment is applied
    because SPEC section 5 does not verify one, and a silent unverified
    conversion here would be indistinguishable from a bug downstream.
    """
    reliquary = equip.get("reliquary") or {}
    flat = equip.get("flat") or {}
    main = flat.get("reliquaryMainstat") or {}
    raw_subs = flat.get("reliquarySubstats") or []

    substats: list[tuple[str, float]] = []
    if isinstance(raw_subs, list):
        for sub in raw_subs:
            if not isinstance(sub, dict):
                continue
            substats.append((str(sub.get("appendPropId", "")), _as_float(sub.get("propValue"))))

    return MappedArtifact(
        item_id=_as_int(equip.get("itemId")),
        set_name_hash=str(flat.get("setNameTextHashMap", "")),
        rank_level=_as_int(flat.get("rankLevel")),
        level=_as_int(reliquary.get("level")),
        main_stat_id=str(main.get("mainPropId", "")),
        main_stat_value=_as_float(main.get("statValue")),
        substats=tuple(substats),
        equip_type=str(flat.get("equipType", "")),
    )


def split_equipment(equip_list: object) -> tuple[MappedWeapon | None, tuple[MappedArtifact, ...]]:
    """Partition `equipList` by `flat.itemType`.

    TRAP 7: the two values are EXACTLY "ITEM_RELIQUARY" and "ITEM_WEAPON", which
    is why `EquipItemType` in `core.types` mirrors them verbatim. The comparison
    is against the enum values rather than string literals typed here, so there
    is one spelling of each in the tree.

    An entry with an unrecognised itemType is skipped rather than guessed at by
    inspecting which sub-object is present.
    """
    weapon: MappedWeapon | None = None
    artifacts: list[MappedArtifact] = []
    if not isinstance(equip_list, list):
        return None, ()
    for equip in equip_list:
        if not isinstance(equip, dict):
            continue
        item_type = (equip.get("flat") or {}).get("itemType")
        if item_type == EquipItemType.WEAPON.value:
            weapon = map_weapon(equip)
        elif item_type == EquipItemType.RELIQUARY.value:
            artifacts.append(map_artifact(equip))
    return weapon, tuple(artifacts)


# ---------------------------------------------------------------------------
# Characters and profile
# ---------------------------------------------------------------------------


def map_character(
    avatar: dict,
    identity: IdentityLookup | None = None,
    skill_group_map: dict[int, int] | None = None,
    positional_fallback: bool = False,
) -> MappedCharacter:
    """Map one `avatarInfoList` entry."""
    # TRAP 5: `avatarId`. The docs table's `avatarID` is not read, on purpose.
    avatar_id = _as_int(avatar.get(AVATAR_ID_KEY))

    prop_map = avatar.get("propMap")
    level = read_prop(prop_map, PROP_LEVEL)
    ascension = read_prop(prop_map, PROP_ASCENSION)

    # TRAP 2: the `talentIdList` KEY IS ABSENT at C0 - it is not an empty list.
    # `len(avatar["talentIdList"])` raises KeyError on every unconstellated
    # character, which is the single most common crash in a naive reader.
    talent_ids = avatar.get("talentIdList", [])
    constellations = len(talent_ids) if isinstance(talent_ids, list) else 0

    effective, base, _unresolved = fold_talent_levels(
        avatar,
        skill_group_map=skill_group_map,
        positional_fallback=positional_fallback,
    )

    weapon, artifacts = split_equipment(avatar.get("equipList"))

    fetter = avatar.get("fetterInfo") or {}
    friendship = _as_int(fetter.get("expLevel")) if isinstance(fetter, dict) else 0

    display_name = ""
    element: Element | None = None
    if identity is not None:
        display_name = identity.character_name(avatar_id)
        element = identity.element_for(avatar_id)

    return MappedCharacter(
        avatar_id=avatar_id,
        level=level,
        ascension=ascension,
        constellations=constellations,
        talent_levels=effective,
        talent_levels_base=base,
        friendship=friendship,
        weapon=weapon,
        artifacts=artifacts,
        element=element,
        display_name=display_name,
    )


def map_profile(
    payload: dict,
    uid: str | None = None,
    fetched_at: datetime | None = None,
    identity: IdentityLookup | None = None,
    skill_group_map: dict[int, int] | None = None,
    positional_fallback: bool = False,
) -> EnkaMappedProfile:
    """Map a whole upstream response into the internal profile contract.

    TRAP 1: `avatarInfoList` is ABSENT ENTIRELY when the showcase is closed or
    empty - upstream does not send `[]`. Key PRESENCE is therefore the signal,
    and a closed showcase is a normal state that yields `showcase_open=False`
    plus an empty roster. It is not an error and must not raise: a player is
    perfectly entitled to keep their showcase shut.
    """
    player = payload.get("playerInfo") or {}
    if not isinstance(player, dict):
        player = {}

    showcase_open = "avatarInfoList" in payload
    raw_avatars = payload.get("avatarInfoList") or []
    characters: list[MappedCharacter] = []
    if isinstance(raw_avatars, list):
        for avatar in raw_avatars:
            if isinstance(avatar, dict):
                characters.append(
                    map_character(
                        avatar,
                        identity=identity,
                        skill_group_map=skill_group_map,
                        positional_fallback=positional_fallback,
                    )
                )

    resolved_uid = str(uid if uid is not None else payload.get("uid", ""))

    return EnkaMappedProfile(
        uid=resolved_uid,
        nickname=str(player.get("nickname", "")),
        signature=str(player.get("signature", "")),
        world_level=_as_int(player.get("worldLevel")),
        adventure_rank=_as_int(player.get("level")),
        achievements=_as_int(player.get("finishAchievementNum")),
        abyss_floor=_as_int(player.get("towerFloorIndex")),
        abyss_chamber=_as_int(player.get("towerLevelIndex")),
        characters=tuple(characters),
        ttl_seconds=_as_int(payload.get("ttl"), 60),
        fetched_at=fetched_at,
        showcase_open=showcase_open,
    )
