"""UIGF v4 wish-history import and export (MAIN ORDER item RSC-UIGF-IO).

UIGF (Uniformed Interchangeable GachaLog Format) is a public open standard
published by UIGF-org. This module implements the v4 hk4e section from that
published format, with the stdlib `json` module only. It vendors NO game data:
no item table, no banner schedule, no name list. See docs/LICENSE_NOTES.md -
protocol and format facts are re-implementable; data payloads are not.

Shape handled::

    {"info": {"export_timestamp", "export_app", "export_app_version",
              "version": "v4.0"},
     "hk4e": [{"uid", "timezone", "lang",
               "list": [{"uigf_gacha_type", "gacha_type", "item_id", "count",
                         "time", "name", "item_type", "rank_type", "id"}]}]}

Numeric item fields are STRINGS on the wire and stay strings here, so an export
reproduces the source bytes' values exactly. `uigf_gacha_type` is one of
100, 200, 301, 302, 500; the 301 family also carries in-game `gacha_type` 400
(Character Event Wish-2, which shares the 301 pity counter).

Pity seeding
------------
`pity_state_from_uigf` derives, per banner family, the count of wishes since
the last 5-star and since the last 4-star (rank_type exactly "4"), ordered by
(time, id). The GUARANTEE state - `has_guarantee`, `consecutive_5050_losses`
and the weapon `fate_points` - is NOT derived: deciding whether a past 5-star
was the featured item needs a banner schedule and item table this repository
does not hold and will not vendor. Those are CALLER INPUT, default zero/False.

Top-level keys other than `info` and `hk4e` (other games' sections, annotation
keys) are carried through untouched. Unknown keys inside an account or an item
are dropped on parse.
"""
from __future__ import annotations

import copy
import json
import os
import re
import time as _time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.pity_engine.forecast import probability_of_success
from core.atomic_io import atomic_write_text
from core.types import BannerKind, ForecastResult, PityState

UIGF_VERSION = "v4.0"
EXPORT_APP = "ResinCompute"
EXPORT_APP_VERSION = "1"

#: uigf_gacha_type -> the in-game gacha_type values it may carry.
UIGF_GACHA_TYPES: dict[str, frozenset[str]] = {
    "100": frozenset({"100"}),
    "200": frozenset({"200"}),
    "301": frozenset({"301", "400"}),
    "302": frozenset({"302"}),
    "500": frozenset({"500"}),
}

#: Banner family -> uigf_gacha_type. Novice (100) has no BannerKind.
BANNER_TO_UIGF: dict[BannerKind, str] = {
    BannerKind.CHARACTER_EVENT: "301",
    BannerKind.WEAPON_EVENT: "302",
    BannerKind.STANDARD: "200",
    BannerKind.CHRONICLED: "500",
}

_RANKS = frozenset({"3", "4", "5"})
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
_TIME_FMT = "%Y-%m-%d %H:%M:%S"
_DIGITS_RE = re.compile(r"^\d+$")
_OPTIONAL_ITEM_FIELDS = ("count", "name", "item_type", "rank_type")
_ITEM_ORDER = (
    "uigf_gacha_type", "gacha_type", "item_id", "count", "time",
    "name", "item_type", "rank_type", "id",
)


class UigfError(ValueError):
    """A UIGF document that is malformed or cannot answer the question asked."""


@dataclass(frozen=True)
class UigfItem:
    uigf_gacha_type: str
    gacha_type: str
    item_id: str
    time: str
    id: str
    count: str | None = None
    name: str | None = None
    item_type: str | None = None
    rank_type: str | None = None


@dataclass(frozen=True)
class UigfAccount:
    uid: str | int
    timezone: int
    items: tuple[UigfItem, ...]
    lang: str | None = None


@dataclass(frozen=True)
class UigfInfo:
    export_timestamp: str | int
    export_app: str
    export_app_version: str
    version: str = UIGF_VERSION


@dataclass(frozen=True)
class UigfDocument:
    info: UigfInfo
    hk4e: tuple[UigfAccount, ...]
    #: Top-level keys other than info/hk4e, carried through verbatim, in order.
    extra: tuple[tuple[str, Any], ...] = field(default=())


# ---------------------------------------------------------------------------
# Parse and validate
# ---------------------------------------------------------------------------


def _require(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise UigfError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _str_field(mapping: Mapping[str, Any], key: str, where: str, *, digits: bool = False) -> str:
    value = _require(mapping, key, where)
    if not isinstance(value, str):
        raise UigfError(f"{where}: field {key!r} must be a string, got {type(value).__name__}")
    if digits and not _DIGITS_RE.match(value):
        raise UigfError(f"{where}: field {key!r} must be a numeric string")
    return value


def _parse_item(raw: Any, where: str) -> UigfItem:
    if not isinstance(raw, Mapping):
        raise UigfError(f"{where}: item must be an object")
    uigf_type = _str_field(raw, "uigf_gacha_type", where)
    if uigf_type not in UIGF_GACHA_TYPES:
        raise UigfError(f"{where}: unknown uigf_gacha_type {uigf_type!r}")
    gacha_type = _str_field(raw, "gacha_type", where)
    if gacha_type not in UIGF_GACHA_TYPES[uigf_type]:
        raise UigfError(
            f"{where}: gacha_type {gacha_type!r} does not belong to uigf_gacha_type {uigf_type!r}"
        )
    item_id = _str_field(raw, "item_id", where, digits=True)
    item_uid = _str_field(raw, "id", where, digits=True)
    stamp = _str_field(raw, "time", where)
    if not _TIME_RE.match(stamp):
        raise UigfError(f"{where}: time must be 'YYYY-MM-DD HH:MM:SS'")
    try:
        datetime.strptime(stamp, _TIME_FMT)
    except ValueError as exc:
        raise UigfError(f"{where}: time is not a valid date-time") from exc
    optional: dict[str, str | None] = {}
    for key in _OPTIONAL_ITEM_FIELDS:
        if key not in raw:
            optional[key] = None
            continue
        value = raw[key]
        if not isinstance(value, str):
            raise UigfError(f"{where}: field {key!r} must be a string")
        optional[key] = value
    count = optional["count"]
    if count is not None and not _DIGITS_RE.match(count):
        raise UigfError(f"{where}: field 'count' must be a numeric string")
    rank = optional["rank_type"]
    if rank is not None and rank not in _RANKS:
        raise UigfError(f"{where}: rank_type {rank!r} is not one of 3, 4, 5")
    return UigfItem(
        uigf_gacha_type=uigf_type,
        gacha_type=gacha_type,
        item_id=item_id,
        time=stamp,
        id=item_uid,
        count=count,
        name=optional["name"],
        item_type=optional["item_type"],
        rank_type=rank,
    )


def _parse_account(raw: Any, where: str) -> UigfAccount:
    if not isinstance(raw, Mapping):
        raise UigfError(f"{where}: account must be an object")
    uid = _require(raw, "uid", where)
    if isinstance(uid, bool) or not isinstance(uid, (str, int)) or not str(uid).isdigit():
        raise UigfError(f"{where}: uid must be a numeric string or integer")
    timezone = _require(raw, "timezone", where)
    if isinstance(timezone, bool) or not isinstance(timezone, int):
        raise UigfError(f"{where}: timezone must be an integer")
    lang = raw.get("lang")
    if lang is not None and not isinstance(lang, str):
        raise UigfError(f"{where}: lang must be a string")
    rows = _require(raw, "list", where)
    if not isinstance(rows, list):
        raise UigfError(f"{where}: list must be an array")
    items = tuple(_parse_item(row, f"{where}.list[{i}]") for i, row in enumerate(rows))
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            raise UigfError(f"{where}: duplicate wish id {item.id}")
        seen.add(item.id)
    return UigfAccount(uid=uid, timezone=timezone, items=items, lang=lang)


def parse_document(raw: Any) -> UigfDocument:
    """Validate a decoded UIGF v4 JSON object and return typed records.

    Raises `UigfError` (a `ValueError`) naming the offending field.
    """
    if not isinstance(raw, Mapping):
        raise UigfError("document: top level must be an object")
    info_raw = _require(raw, "info", "document")
    if not isinstance(info_raw, Mapping):
        raise UigfError("info: must be an object")
    version = _str_field(info_raw, "version", "info")
    if not version.startswith("v4."):
        raise UigfError(f"info: unsupported version {version!r}; this reader handles v4.x")
    stamp = _require(info_raw, "export_timestamp", "info")
    if isinstance(stamp, bool) or not isinstance(stamp, (str, int)):
        raise UigfError("info: export_timestamp must be an integer or string")
    info = UigfInfo(
        export_timestamp=stamp,
        export_app=_str_field(info_raw, "export_app", "info"),
        export_app_version=_str_field(info_raw, "export_app_version", "info"),
        version=version,
    )
    accounts_raw = raw.get("hk4e", [])
    if not isinstance(accounts_raw, list):
        raise UigfError("hk4e: must be an array")
    accounts = tuple(_parse_account(acc, f"hk4e[{i}]") for i, acc in enumerate(accounts_raw))
    extra = tuple(
        (key, copy.deepcopy(value)) for key, value in raw.items() if key not in ("info", "hk4e")
    )
    return UigfDocument(info=info, hk4e=accounts, extra=extra)


def loads(text: str) -> UigfDocument:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UigfError(f"document: not valid JSON ({exc.msg})") from exc
    return parse_document(raw)


def read_uigf(path: str | os.PathLike[str]) -> UigfDocument:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UigfError(f"document: cannot read file ({exc.__class__.__name__})") from exc
    return loads(text)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _export_item(item: UigfItem) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in _ITEM_ORDER:
        value = getattr(item, key)
        if value is not None:
            out[key] = value
    return out


def export_document(doc: UigfDocument) -> dict[str, Any]:
    """Typed records -> a UIGF v4 JSON-ready dict (the inverse of `parse_document`)."""
    out: dict[str, Any] = {key: copy.deepcopy(value) for key, value in doc.extra}
    out["info"] = {
        "export_timestamp": doc.info.export_timestamp,
        "export_app": doc.info.export_app,
        "export_app_version": doc.info.export_app_version,
        "version": doc.info.version,
    }
    accounts = []
    for account in doc.hk4e:
        entry: dict[str, Any] = {"uid": account.uid, "timezone": account.timezone}
        if account.lang is not None:
            entry["lang"] = account.lang
        entry["list"] = [_export_item(item) for item in account.items]
        accounts.append(entry)
    out["hk4e"] = accounts
    return out


def dumps(doc: UigfDocument) -> str:
    return json.dumps(export_document(doc), indent=2, ensure_ascii=True) + "\n"


def write_uigf(path: str | os.PathLike[str], doc: UigfDocument) -> bool:
    """Atomic write through core/atomic_io. Returns True on success."""
    return atomic_write_text(path, dumps(doc))


def build_document(
    uid: str | int,
    items: Iterable[UigfItem],
    *,
    timezone: int,
    lang: str | None = None,
    export_timestamp: str | int | None = None,
    export_app: str = EXPORT_APP,
    export_app_version: str = EXPORT_APP_VERSION,
) -> UigfDocument:
    """Wrap RSC-held wish records as a single-account UIGF v4 document.

    The result is validated by a parse of its own export, so a malformed record
    fails here rather than in the importing tool.
    """
    stamp = int(_time.time()) if export_timestamp is None else export_timestamp
    doc = UigfDocument(
        info=UigfInfo(
            export_timestamp=stamp,
            export_app=export_app,
            export_app_version=export_app_version,
            version=UIGF_VERSION,
        ),
        hk4e=(UigfAccount(uid=uid, timezone=timezone, items=tuple(items), lang=lang),),
    )
    return parse_document(export_document(doc))


# ---------------------------------------------------------------------------
# Pity seeding and the forecaster
# ---------------------------------------------------------------------------


def _account(doc: UigfDocument, uid: str | int) -> UigfAccount:
    for account in doc.hk4e:
        if str(account.uid) == str(uid):
            return account
    raise UigfError(f"no hk4e account with uid {uid!r} in this document")


def _chronological(items: Iterable[UigfItem]) -> list[UigfItem]:
    # Times share one account timezone and are zero-padded, so a string sort is
    # chronological. Ten wishes share one timestamp; the id breaks the tie.
    return sorted(items, key=lambda item: (item.time, int(item.id)))


def pity_state_from_uigf(
    doc: UigfDocument,
    uid: str | int,
    banner: BannerKind,
    *,
    has_guarantee: bool = False,
    consecutive_5050_losses: int = 0,
    fate_points: int = 0,
) -> PityState:
    """Starting `PityState` for one banner family, seeded from wish history.

    `pity_5star` / `pity_4star` are the wishes since the last rank_type "5" /
    rank_type "4" item. The guarantee fields are caller input (see the module
    docstring for why they cannot be derived from a UIGF file alone).
    """
    account = _account(doc, uid)
    uigf_type = BANNER_TO_UIGF[banner]
    rows = _chronological(item for item in account.items if item.uigf_gacha_type == uigf_type)
    for item in rows:
        if item.rank_type is None:
            raise UigfError(
                f"wish id {item.id} has no rank_type; pity cannot be derived without it"
            )
    pity_5 = 0
    pity_4 = 0
    for item in rows:
        pity_5 = 0 if item.rank_type == "5" else pity_5 + 1
        pity_4 = 0 if item.rank_type == "4" else pity_4 + 1
    return PityState(
        banner=banner,
        pity_5star=pity_5,
        pity_4star=pity_4,
        has_guarantee=has_guarantee,
        consecutive_5050_losses=consecutive_5050_losses,
        fate_points=fate_points,
    )


def forecast_from_uigf(
    doc: UigfDocument,
    uid: str | int,
    banner: BannerKind,
    target_count: int,
    pull_budget: int,
    *,
    has_guarantee: bool = False,
    consecutive_5050_losses: int = 0,
    fate_points: int = 0,
    weapon_increment: float | None = None,
) -> ForecastResult:
    """PityEngine forecast whose starting pity is seeded from a UIGF file."""
    state = pity_state_from_uigf(
        doc,
        uid,
        banner,
        has_guarantee=has_guarantee,
        consecutive_5050_losses=consecutive_5050_losses,
        fate_points=fate_points,
    )
    return probability_of_success(
        state,
        target_count,
        pull_budget,
        banner=banner,
        weapon_increment=weapon_increment,
    )
