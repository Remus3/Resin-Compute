"""The ONLY place character and material identity lives.

Identity is DATA, not code: the tables are read from `data/fixtures/*.json`
rather than hardcoded as a Python dict, so correcting an id is a data edit and
never a code edit. That also keeps the license posture legible - the whole of
this repository's game-adjacent knowledge is two small hand-authored JSON files,
and `data/fixtures/README.md` says exactly what they are and why nothing bigger
is vendored.

Contents are limited to the ids independently verified in
`docs/SPEC_SCAFFOLD.md` section 5. Five characters, two boss materials, nothing
else. An id outside that set is UNKNOWN, and unknown resolves to a stable
placeholder - it never raises, and it never guesses a name. Guessing is how a
wrong id becomes a fact: `10000088` was proposed as Dehya (it is Charlotte) and
`10000080` as Lynette (it is Mika), and both would have looked plausible in a
UI forever.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.types import Element

#: Repository-relative fixture location. `ingest/` -> repo root -> data/fixtures.
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"

ROSTER_FILE = "seed_roster.json"
MATERIALS_FILE = "seed_materials.json"

#: Prefix for an id that is not in the verified seed set. Stable and greppable
#: on purpose: a placeholder that reads like a real name would hide the gap.
UNKNOWN_PREFIX = "unknown:"


class StaticDataError(RuntimeError):
    """A seed table is missing or malformed.

    Raised at LOAD time only. Lookups never raise - see `character_name`.
    """


@dataclass(frozen=True)
class CharacterIdentity:
    avatar_id: int
    name: str
    element: Element | None = None
    note: str = ""


@dataclass(frozen=True)
class MaterialIdentity:
    material_id: int
    name: str
    used_by: tuple[str, ...] = ()
    boss: str = ""
    region: str = ""


_roster_cache: dict[int, CharacterIdentity] | None = None
_materials_cache: dict[int, MaterialIdentity] | None = None


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StaticDataError(f"seed table is missing or unreadable: {path}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StaticDataError(f"seed table is not valid JSON: {path}") from exc
    if not isinstance(parsed, dict):
        raise StaticDataError(f"seed table must be a JSON object: {path}")
    return parsed


def _parse_element(raw: object) -> Element | None:
    """Elements are enum VALUES in the file. An unknown one is None, not a crash."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return Element(raw.strip().lower())
    except ValueError:
        return None


def load_roster(path: Path | None = None) -> dict[int, CharacterIdentity]:
    """Parse the seed roster table. Cached after the first successful read."""
    global _roster_cache
    if path is None and _roster_cache is not None:
        return _roster_cache

    source = path if path is not None else FIXTURES_DIR / ROSTER_FILE
    payload = _read_json(source)
    rows = payload.get("characters")
    if not isinstance(rows, list):
        raise StaticDataError(f"seed roster has no 'characters' list: {source}")

    table: dict[int, CharacterIdentity] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            avatar_id = int(row["avatar_id"])
        except (KeyError, TypeError, ValueError):
            continue
        table[avatar_id] = CharacterIdentity(
            avatar_id=avatar_id,
            name=str(row.get("name", "")),
            element=_parse_element(row.get("element")),
            note=str(row.get("note", "")),
        )

    if path is None:
        _roster_cache = table
    return table


def load_materials(path: Path | None = None) -> dict[int, MaterialIdentity]:
    """Parse the seed material table. Cached after the first successful read."""
    global _materials_cache
    if path is None and _materials_cache is not None:
        return _materials_cache

    source = path if path is not None else FIXTURES_DIR / MATERIALS_FILE
    payload = _read_json(source)
    rows = payload.get("materials")
    if not isinstance(rows, list):
        raise StaticDataError(f"seed material table has no 'materials' list: {source}")

    table: dict[int, MaterialIdentity] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            material_id = int(row["material_id"])
        except (KeyError, TypeError, ValueError):
            continue
        used_by = row.get("used_by")
        table[material_id] = MaterialIdentity(
            material_id=material_id,
            name=str(row.get("name", "")),
            used_by=tuple(str(x) for x in used_by) if isinstance(used_by, list) else (),
            boss=str(row.get("boss", "")),
            region=str(row.get("region", "")),
        )

    if path is None:
        _materials_cache = table
    return table


def reset_cache() -> None:
    """Drop the memoised tables. For tests and for a live fixture edit."""
    global _roster_cache, _materials_cache
    _roster_cache = None
    _materials_cache = None


# ---------------------------------------------------------------------------
# Lookups - these NEVER raise and NEVER invent a name
# ---------------------------------------------------------------------------


def character_name(avatar_id: int) -> str:
    """Display name for an avatarId.

    An id outside the verified seed set returns `unknown:<id>` - stable, greppable
    and obviously not a real name. It is deliberately NOT an exception: an
    unrecognised character in a live showcase is an expected gap in a five-entry
    seed table, not a failure, and the caller renders the placeholder while the
    bootstrap summary counts it.
    """
    entry = load_roster().get(int(avatar_id))
    return entry.name if entry is not None and entry.name else f"{UNKNOWN_PREFIX}{int(avatar_id)}"


def material_name(material_id: int) -> str:
    """Display name for a material id, with the same unknown-id contract."""
    entry = load_materials().get(int(material_id))
    return entry.name if entry is not None and entry.name else f"{UNKNOWN_PREFIX}{int(material_id)}"


def element_for(avatar_id: int) -> Element | None:
    """Element for an avatarId, or None when the id is unknown."""
    entry = load_roster().get(int(avatar_id))
    return entry.element if entry is not None else None


def material_for(material_id: int) -> MaterialIdentity | None:
    """Full material record, or None when the id is unknown."""
    return load_materials().get(int(material_id))


def is_known_character(avatar_id: int) -> bool:
    return int(avatar_id) in load_roster()


def is_known_material(material_id: int) -> bool:
    return int(material_id) in load_materials()


def is_unknown_name(name: str) -> bool:
    """True when a name is a placeholder rather than a resolved identity."""
    return name.startswith(UNKNOWN_PREFIX)


def known_avatar_ids() -> tuple[int, ...]:
    return tuple(sorted(load_roster()))


def known_material_ids() -> tuple[int, ...]:
    return tuple(sorted(load_materials()))


@dataclass(frozen=True)
class StaticIdentity:
    """Adapter satisfying `ingest.enka_mapper.IdentityLookup`.

    The mapper is pure and performs no I/O, so identity is injected as an object
    rather than imported by it. This is the production implementation of that
    seam; a test can pass any object with the same two methods.
    """

    def character_name(self, avatar_id: int) -> str:
        return character_name(avatar_id)

    def element_for(self, avatar_id: int) -> Element | None:
        return element_for(avatar_id)
