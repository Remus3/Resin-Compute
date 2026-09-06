"""Serialize `AccountState` to and from a snapshot file.

WHAT THIS IS FOR, AND THE RULE IT MUST NOT BREAK. The headless lane rebuilds
`AccountState` from the live upstream response on every pass and then throws it
away when the process exits. The dashboard is a separate process that starts
cold, so without a file on disk it has nothing to render and every panel honestly
reports having no data. This module is that file.

**It is a DISPLAY CACHE. It is never an input to reconciliation.** CLAUDE.md's
live-state-first rule says a stale cache must not be treated as truth, and the
way that rule survives the existence of a cache file is structural: nothing in
`headless/jobs.py` READS this back. `reconcile_state` derives from the current
response and only the current response; `persist_state` writes the result down
afterwards. The only reader is `surface/`, which renders it and says how old it
is. If a future job ever reads this file to seed a reconciliation, that is the
rule being broken, and it will not look like a bug - it will look like a cache
hit.

**STALENESS IS PART OF THE PAYLOAD, NOT AN AFTERTHOUGHT.** `snapshot_age` exists
so a consumer cannot render the snapshot without being able to say when it was
taken. A cached roster shown with no age reads exactly like a live one.

TOTALITY. `read_state` and `state_from_dict` NEVER raise. Every failure mode -
absent file, truncated write, malformed JSON, a schema version from the future, a
field of the wrong type, an enum value that no longer exists, a `PityState` whose
own `__post_init__` rejects it - returns None or degrades that one field. A
dashboard that will not open because a cache file was half-written is worse than
one that opens empty, and readers polling mid-write is a documented hazard in
this tree rather than a hypothetical.

Writes go through `core/atomic_io.py`, which is the only sanctioned state-write
path, for exactly that reason.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.atomic_io import atomic_write_json, read_json
from core.log_setup import get_logger
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

_log = get_logger(__name__)

__all__ = [
    "DEFAULT_STATE_FILENAME",
    "STATE_SCHEMA_VERSION",
    "read_state",
    "snapshot_age",
    "state_from_dict",
    "state_to_dict",
    "write_state",
]

#: Bumped whenever the shape below changes incompatibly. A reader that meets a
#: HIGHER version refuses rather than guessing - see `read_state`.
STATE_SCHEMA_VERSION = 1

DEFAULT_STATE_FILENAME = "account_state.json"


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def _encode_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _encode_artifact(artifact: MappedArtifact) -> dict[str, Any]:
    return {
        "item_id": artifact.item_id,
        "set_name_hash": artifact.set_name_hash,
        "rank_level": artifact.rank_level,
        "level": artifact.level,
        "main_stat_id": artifact.main_stat_id,
        "main_stat_value": artifact.main_stat_value,
        "substats": [[name, value] for name, value in artifact.substats],
        "equip_type": artifact.equip_type,
    }


def _encode_weapon(weapon: MappedWeapon | None) -> dict[str, Any] | None:
    if weapon is None:
        return None
    return {
        "item_id": weapon.item_id,
        "name_hash": weapon.name_hash,
        "level": weapon.level,
        "ascension": weapon.ascension,
        "refinement": weapon.refinement,
        "rank_level": weapon.rank_level,
    }


def _encode_character(character: MappedCharacter) -> dict[str, Any]:
    return {
        "avatar_id": character.avatar_id,
        "level": character.level,
        "ascension": character.ascension,
        "constellations": character.constellations,
        # JSON has no integer keys. These are written as strings deliberately and
        # converted back in `_decode_int_map`; the alternative is a silent
        # key-type change that misses every lookup.
        "talent_levels": {str(k): v for k, v in character.talent_levels.items()},
        "talent_levels_base": {str(k): v for k, v in character.talent_levels_base.items()},
        "friendship": character.friendship,
        "weapon": _encode_weapon(character.weapon),
        "artifacts": [_encode_artifact(a) for a in character.artifacts],
        "element": character.element.value if character.element is not None else None,
        "display_name": character.display_name,
    }


def state_to_dict(state: AccountState) -> dict[str, Any]:
    """Encode an account into a plain JSON-safe dict."""
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "uid": state.uid,
        "adventure_rank": state.adventure_rank,
        "world_level": state.world_level,
        "roster": [_encode_character(c) for c in state.roster],
        "ledger": [
            {
                "entry_id": e.entry_id,
                "occurred_at": _encode_datetime(e.occurred_at),
                "currency": e.currency.value,
                "delta": e.delta,
                "reason": e.reason,
                "source": e.source,
            }
            for e in state.ledger.entries
        ],
        "pity": {
            banner.value: {
                "pity_5star": p.pity_5star,
                "pity_4star": p.pity_4star,
                "has_guarantee": p.has_guarantee,
                "consecutive_5050_losses": p.consecutive_5050_losses,
                "fate_points": p.fate_points,
            }
            for banner, p in state.pity.items()
        },
        "velocity": {
            "primogems_per_day": state.velocity.primogems_per_day,
            "intertwined_fates_per_day": state.velocity.intertwined_fates_per_day,
            "resin_per_day": state.velocity.resin_per_day,
            "sampled_over_days": state.velocity.sampled_over_days,
        },
        "last_synced_at": _encode_datetime(state.last_synced_at),
        "last_reset_date": state.last_reset_date.isoformat() if state.last_reset_date else None,
    }


# ---------------------------------------------------------------------------
# Decoding - every helper below is total
# ---------------------------------------------------------------------------


def _as_int(value: Any, default: int = 0) -> int:
    # A bool is an int in Python and would decode `true` as 1. Rejected first.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return int(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _as_str(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_bool(value: Any, default: bool = False) -> bool:
    # Strictly by type. The string "false" is truthy, and coercing it would flip
    # a guarantee flag to the opposite of what the file says.
    return value if isinstance(value, bool) else default


def _decode_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _decode_int_map(value: Any) -> dict[int, int]:
    """Undo the string-key damage JSON does to an integer-keyed dict."""
    if not isinstance(value, dict):
        return {}
    out: dict[int, int] = {}
    for key, level in value.items():
        try:
            out[int(key)] = _as_int(level)
        except (TypeError, ValueError):
            continue
    return out


def _decode_artifact(raw: Any) -> MappedArtifact | None:
    if not isinstance(raw, dict):
        return None
    substats: list[tuple[str, float]] = []
    for pair in raw.get("substats", []) or []:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            substats.append((_as_str(pair[0]), _as_float(pair[1])))
    try:
        return MappedArtifact(
            item_id=_as_int(raw.get("item_id")),
            set_name_hash=_as_str(raw.get("set_name_hash")),
            rank_level=_as_int(raw.get("rank_level")),
            level=_as_int(raw.get("level")),
            main_stat_id=_as_str(raw.get("main_stat_id")),
            main_stat_value=_as_float(raw.get("main_stat_value")),
            substats=tuple(substats),
            equip_type=_as_str(raw.get("equip_type")),
        )
    except (TypeError, ValueError):
        return None


def _decode_weapon(raw: Any) -> MappedWeapon | None:
    if not isinstance(raw, dict):
        return None
    try:
        return MappedWeapon(
            item_id=_as_int(raw.get("item_id")),
            name_hash=_as_str(raw.get("name_hash")),
            level=_as_int(raw.get("level")),
            ascension=_as_int(raw.get("ascension")),
            refinement=_as_int(raw.get("refinement")),
            rank_level=_as_int(raw.get("rank_level")),
        )
    except (TypeError, ValueError):
        return None


def _decode_element(raw: Any) -> Element | None:
    if not isinstance(raw, str):
        return None
    try:
        return Element(raw)
    except ValueError:
        # A member removed or renamed since the file was written. None is the
        # honest answer; guessing a neighbouring element would be worse.
        return None


def _decode_character(raw: Any) -> MappedCharacter | None:
    if not isinstance(raw, dict):
        return None
    avatar_id = raw.get("avatar_id")
    if isinstance(avatar_id, bool) or not isinstance(avatar_id, (int, float)):
        # Without a usable id the entry cannot be identified at all, so it is
        # dropped rather than defaulted to 0 and rendered as a real character.
        return None
    artifacts = [a for a in (_decode_artifact(x) for x in raw.get("artifacts", []) or []) if a is not None]
    try:
        return MappedCharacter(
            avatar_id=int(avatar_id),
            level=_as_int(raw.get("level")),
            ascension=_as_int(raw.get("ascension")),
            constellations=_as_int(raw.get("constellations")),
            talent_levels=_decode_int_map(raw.get("talent_levels")),
            talent_levels_base=_decode_int_map(raw.get("talent_levels_base")),
            friendship=_as_int(raw.get("friendship")),
            weapon=_decode_weapon(raw.get("weapon")),
            artifacts=tuple(artifacts),
            element=_decode_element(raw.get("element")),
            display_name=_as_str(raw.get("display_name")),
        )
    except (TypeError, ValueError):
        return None


def _decode_entry(raw: Any) -> LedgerEntry | None:
    if not isinstance(raw, dict):
        return None
    try:
        currency = CurrencyKind(_as_str(raw.get("currency")))
    except ValueError:
        return None
    occurred_at = _decode_datetime(raw.get("occurred_at"))
    if occurred_at is None:
        return None
    try:
        # LedgerEntry.__post_init__ rejects a zero delta, which a corrupted or
        # hand-edited file can easily produce. That refusal is correct and must
        # not escape as an exception from a read.
        return LedgerEntry(
            entry_id=_as_str(raw.get("entry_id")),
            occurred_at=occurred_at,
            currency=currency,
            delta=_as_int(raw.get("delta")),
            reason=_as_str(raw.get("reason")),
            source=_as_str(raw.get("source"), "manual"),
        )
    except (TypeError, ValueError):
        return None


def _decode_pity(raw: Any) -> dict[BannerKind, PityState]:
    if not isinstance(raw, dict):
        return {}
    out: dict[BannerKind, PityState] = {}
    for key, value in raw.items():
        try:
            banner = BannerKind(key)
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        try:
            # PityState.__post_init__ enforces the Capturing Radiance cap and the
            # fate-point cap. A file violating either is DROPPED, not repaired:
            # clamping would present an invented counter as an observed one.
            out[banner] = PityState(
                banner=banner,
                pity_5star=_as_int(value.get("pity_5star")),
                pity_4star=_as_int(value.get("pity_4star")),
                has_guarantee=_as_bool(value.get("has_guarantee")),
                consecutive_5050_losses=_as_int(value.get("consecutive_5050_losses")),
                fate_points=_as_int(value.get("fate_points")),
            )
        except (TypeError, ValueError) as exc:
            _log.warning("dropping unusable pity state for %s: %s", key, exc)
    return out


def state_from_dict(payload: Any) -> AccountState | None:
    """Decode a snapshot. Returns None for anything unusable. NEVER raises."""
    if not isinstance(payload, dict):
        return None

    version = payload.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        return None
    if version > STATE_SCHEMA_VERSION:
        _log.error(
            "account snapshot is schema version %s but this build understands %s - refusing to guess",
            version,
            STATE_SCHEMA_VERSION,
        )
        return None

    state = AccountState(uid=_as_str(payload.get("uid")))
    state.adventure_rank = _as_int(payload.get("adventure_rank"))
    state.world_level = _as_int(payload.get("world_level"))

    roster = payload.get("roster")
    if isinstance(roster, list):
        state.roster = tuple(c for c in (_decode_character(x) for x in roster) if c is not None)

    ledger = payload.get("ledger")
    if isinstance(ledger, list):
        state.ledger.entries.extend(e for e in (_decode_entry(x) for x in ledger) if e is not None)

    state.pity = _decode_pity(payload.get("pity"))

    velocity = payload.get("velocity")
    if isinstance(velocity, dict):
        state.velocity = IncomeVelocity(
            primogems_per_day=_as_float(velocity.get("primogems_per_day")),
            intertwined_fates_per_day=_as_float(velocity.get("intertwined_fates_per_day")),
            resin_per_day=_as_int(velocity.get("resin_per_day"), 180),
            sampled_over_days=_as_int(velocity.get("sampled_over_days")),
        )

    state.last_synced_at = _decode_datetime(payload.get("last_synced_at"))

    raw_reset = payload.get("last_reset_date")
    if isinstance(raw_reset, str) and raw_reset:
        try:
            state.last_reset_date = datetime.fromisoformat(raw_reset).date()
        except ValueError:
            state.last_reset_date = None

    return state


# ---------------------------------------------------------------------------
# File IO
# ---------------------------------------------------------------------------


def write_state(path: str | Path, state: AccountState) -> bool:
    """Write a snapshot atomically. Returns True on success, never raises."""
    return atomic_write_json(path, state_to_dict(state))


def read_state(path: str | Path) -> AccountState | None:
    """Read a snapshot. Returns None for absent, malformed or future files."""
    return state_from_dict(read_json(path, default=None))


def snapshot_age(state: AccountState, now: datetime) -> timedelta | None:
    """How old the reading is, or None when the account was never synced.

    NONE IS NOT ZERO, and the distinction is the point. A snapshot with no sync
    time is not a fresh one, and a consumer that rendered it as age zero would be
    presenting an unknown as a measurement.

    Clamped at zero. A clock that moved backwards, or a file written by a machine
    whose clock is ahead, would otherwise produce a negative age that reads as a
    reading from the future.
    """
    synced = state.last_synced_at
    if synced is None:
        return None
    # Comparing naive to aware raises. A hand-edited file can carry either, so
    # the boundary normalises rather than propagating a TypeError upward.
    if synced.tzinfo is None:
        synced = synced.replace(tzinfo=UTC)
    reference = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    delta = reference - synced
    return delta if delta > timedelta(0) else timedelta(0)
