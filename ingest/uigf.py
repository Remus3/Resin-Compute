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
the last 5-star and since the last 4-star-or-above (rank_type "4" or "5": a
5-star also resets the 4-star counter, SPEC_SCAFFOLD 3.6), ordered by
(time, id). The GUARANTEE state - `has_guarantee`, `consecutive_5050_losses`
and the weapon `fate_points` - is NOT derived: deciding whether a past 5-star
was the featured item needs a banner schedule and item table this repository
does not hold and will not vendor. Those are CALLER INPUT, default zero/False.

Top-level keys other than `info` and `hk4e` (other games' sections, annotation
keys) are carried through untouched. Unknown keys inside an account or an item
are dropped on parse.

Command line
------------
`python -m ingest.uigf <path> --uid <uid> --banner <banner>
[--target-count N --pull-budget N]` prints the derived pity state as JSON, plus a
forecast when both of the bracketed arguments are given. It lives here and not in
`agents/pity_engine/` because ADR-005 says the engine "holds no account state and
reads no file", and because this module already imports the engine: `ingest`
depends on the engine, never the reverse. `tests/test_uigf_cli.py` pins both.
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import re
import sys
import time as _time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from agents.pity_engine import ENGINE_VERSION
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
_TIME_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
_TIME_FMT = "%Y-%m-%d %H:%M:%S"
# ASCII digits only, whole string: `^\d+$` with .match accepts a trailing
# newline and any Unicode Nd digit, and str.isdigit also accepts superscripts.
_DIGITS_RE = re.compile(r"[0-9]+")
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
    if digits and not _DIGITS_RE.fullmatch(value):
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
    if not _TIME_RE.fullmatch(stamp):
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
    if count is not None and not _DIGITS_RE.fullmatch(count):
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
    if (
        isinstance(uid, bool)
        or not isinstance(uid, (str, int))
        or not _DIGITS_RE.fullmatch(str(uid))
    ):
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
    except (ValueError, RecursionError) as exc:
        # Not JSONDecodeError: an integer past sys.get_int_max_str_digits raises
        # a bare ValueError from inside the decoder, deep nesting RecursionError.
        raise UigfError(f"document: not valid JSON ({exc.__class__.__name__})") from exc
    try:
        return parse_document(raw)
    except RecursionError as exc:
        # A deeply nested carried key decodes, then overflows copy.deepcopy.
        raise UigfError("document: nested too deeply") from exc


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
    # chronological. Ten wishes share one timestamp; the id breaks the tie,
    # numerically. Length then text is that order for ASCII digits without int(),
    # which raises a bare ValueError on an id past sys.get_int_max_str_digits.
    def tie_break(item: UigfItem) -> tuple[str, int, str]:
        significant = item.id.lstrip("0")
        return item.time, len(significant), significant

    return sorted(items, key=tie_break)


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
    rank_type "4" or "5" item (a 5-star also resets the 4-star counter). The guarantee fields are caller input (see the module
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
        # A 5-star also resets the 4-star counter (SPEC_SCAFFOLD 3.6: the
        # guarantee is "4-star or above every 10 wishes").
        pity_4 = 0 if item.rank_type in ("4", "5") else pity_4 + 1
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


# ---------------------------------------------------------------------------
# Command line: python -m ingest.uigf
# ---------------------------------------------------------------------------

_CLI_PROG = "python -m ingest.uigf"

#: `--banner` values. Keyed off BANNER_TO_UIGF, so a BannerKind with no UIGF
#: family can never be offered and then KeyError in `pity_state_from_uigf`.
_CLI_BANNERS: dict[str, BannerKind] = {kind.value: kind for kind in BANNER_TO_UIGF}

#: Compute bounds, not game rules. The engine caps neither argument and its solve
#: grows steeply with both: measured on the 3.14 host, target 7 took about 1.6 s
#: and target 100 did not finish in 88 s; target 7 with budget 5000 took 4.3 s
#: and with budget 1000000 did not finish in 60 s. Seven copies is C0 to C6.
_CLI_MAX_TARGET_COUNT = 7
_CLI_MAX_PULL_BUDGET = 5000

# Every failure prints one of these and nothing else. The UigfError text is for a
# caller of the library: it quotes file content and names parser fields, so here
# it goes to the log, never to the console (the raw-error hard rule).
_CLI_UNREADABLE = "that file could not be read - check the path"
_CLI_INVALID = "that file is not a valid UIGF v4 wish history"
_CLI_UNKNOWN_UID = "that file has no account with that uid"
_CLI_NO_RANK = "pity cannot be derived - a wish in that banner has no rank_type"
_CLI_PAST_HARD_PITY = (
    "that many wishes since the last 5-star is past hard pity for this banner - "
    "check the banner or export the complete history"
)
_CLI_NEEDS_BOTH = "--target-count and --pull-budget must be given together"
_CLI_NO_OUTPUT = "output could not be written"
_CLI_BAD_ARGUMENTS = "unrecognised command line argument - run with --help"
_CLI_INTERRUPTED = "interrupted"

#: The logger is named, not __name__: under `python -m` that is "__main__". The
#: command attaches no handler, because a console handler would break the
#: one-line stderr contract, so this reaches a host process that configured
#: logging and is otherwise dropped.
_LOGGER = logging.getLogger("ingest.uigf")


class _CliParser(argparse.ArgumentParser):
    """argparse whose failure is one line and never echoes a token back.

    The stock `error` prints a usage block and messages such as
    "unrecognized arguments: <whatever was typed>". Only the wording that carries
    no user input survives; everything else becomes the fixed message.
    """

    def error(self, message: str) -> NoReturn:
        name, _, detail = message.partition(": ")
        if message.startswith("the following arguments are required: "):
            text = message
        elif name.startswith("argument ") and detail.startswith(("must be ", "expected one argument")):
            text = f"{name.removeprefix('argument ')}: {detail}"
        else:
            text = _CLI_BAD_ARGUMENTS
        self.exit(2, f"{self.prog}: {text}\n")


def _bounded_int(low: int, high: int) -> Callable[[str], int]:
    """An argparse type: ASCII digits only, whole string, within [low, high].

    `int()` is not the check: it accepts every Unicode Nd digit, surrounding
    whitespace, a sign and underscores, and raises on a long enough digit string.
    """

    def convert(text: str) -> int:
        if _DIGITS_RE.fullmatch(text) and len(text) <= len(str(high)):
            value = int(text)
            if low <= value <= high:
                return value
        raise argparse.ArgumentTypeError(f"must be a whole number from {low} to {high} in ASCII digits")

    return convert


def _uid_arg(text: str) -> str:
    if _DIGITS_RE.fullmatch(text):
        return text
    raise argparse.ArgumentTypeError("must be a uid in ASCII digits")


def _banner_arg(text: str) -> BannerKind:
    if text in _CLI_BANNERS:
        return _CLI_BANNERS[text]
    raise argparse.ArgumentTypeError(f"must be one of {', '.join(sorted(_CLI_BANNERS))}")


def _cli_parser() -> _CliParser:
    parser = _CliParser(
        prog=_CLI_PROG,
        allow_abbrev=False,
        description=(
            "Load a UIGF v4 wish history and print the pity state it implies for one "
            "banner family as JSON, with a PityEngine forecast if asked. The guarantee "
            "state cannot be derived from the file, so it is caller input."
        ),
    )
    parser.add_argument("path", help="UIGF v4 JSON file")
    parser.add_argument("--uid", required=True, type=_uid_arg, help="account uid, exactly as the file spells it")
    parser.add_argument(
        "--banner", required=True, type=_banner_arg, help=f"one of {', '.join(sorted(_CLI_BANNERS))}"
    )
    parser.add_argument(
        "--target-count",
        type=_bounded_int(1, _CLI_MAX_TARGET_COUNT),
        help=f"copies wanted, 1 to {_CLI_MAX_TARGET_COUNT}; forecasts together with --pull-budget",
    )
    parser.add_argument(
        "--pull-budget",
        type=_bounded_int(0, _CLI_MAX_PULL_BUDGET),
        help=f"pulls to spend, 0 to {_CLI_MAX_PULL_BUDGET}; forecasts together with --target-count",
    )
    parser.add_argument("--has-guarantee", action="store_true", help="the next 5-star is guaranteed featured")
    parser.add_argument(
        "--consecutive-5050-losses",
        type=_bounded_int(0, 3),
        default=0,
        help="50/50 losses in a row, 0 to 3 (default 0)",
    )
    parser.add_argument(
        "--fate-points", type=_bounded_int(0, 1), default=0, help="weapon Epitomized Path points, 0 or 1 (default 0)"
    )
    return parser


def _cli_fail(message: str, exc: BaseException | None = None, *, code: int = 1) -> int:
    if exc is not None:
        _LOGGER.info("uigf command failed: %s", message, exc_info=exc)
    print(f"{_CLI_PROG}: {message}", file=sys.stderr)
    return code


def _cli_emit(text: str) -> int:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except OSError as exc:
        # Point the dead descriptor at devnull, or the interpreter's exit-time
        # flush of the same buffer prints its own "Exception ignored" block.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return _cli_fail(_CLI_NO_OUTPUT, exc)
    return 0


def _cli_run(args: argparse.Namespace) -> int:
    if (args.target_count is None) != (args.pull_budget is None):
        return _cli_fail(_CLI_NEEDS_BOTH, code=2)
    try:
        doc = read_uigf(args.path)
    except (ValueError, RecursionError, MemoryError) as exc:
        # UigfError is a ValueError. The bare one is a NUL in the path; a file
        # too large for memory has no ceiling here because the importer has none.
        unreadable = isinstance(exc.__cause__, OSError) or not isinstance(exc, UigfError)
        return _cli_fail(_CLI_UNREADABLE if unreadable else _CLI_INVALID, exc)
    try:
        account = _account(doc, args.uid)
    except UigfError as exc:
        return _cli_fail(_CLI_UNKNOWN_UID, exc)
    banner: BannerKind = args.banner
    try:
        state = pity_state_from_uigf(
            doc,
            args.uid,
            banner,
            has_guarantee=args.has_guarantee,
            consecutive_5050_losses=args.consecutive_5050_losses,
            fate_points=args.fate_points,
        )
    except UigfError as exc:
        return _cli_fail(_CLI_NO_RANK, exc)
    forecast: dict[str, Any] | None = None
    if args.target_count is not None:
        try:
            result = probability_of_success(state, args.target_count, args.pull_budget, banner=banner)
        except ValueError as exc:
            # Arguments are bounded above, so the one reachable refusal left in
            # the engine is a pity count at or past hard pity.
            return _cli_fail(_CLI_PAST_HARD_PITY, exc)
        forecast = {
            "probability": result.probability,
            "pull_budget": result.pull_budget,
            "target_count": result.target_count,
            "distribution": list(result.distribution),
            "expected_pulls": result.expected_pulls,
        }
    uigf_type = BANNER_TO_UIGF[banner]
    payload = {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "uid": args.uid,
        "banner": banner.value,
        "wishes_seen": sum(1 for item in account.items if item.uigf_gacha_type == uigf_type),
        "pity_5star": state.pity_5star,
        "pity_4star": state.pity_4star,
        "has_guarantee": state.has_guarantee,
        "consecutive_5050_losses": state.consecutive_5050_losses,
        "fate_points": state.fate_points,
        "forecast": forecast,
    }
    return _cli_emit(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    """Exit codes: 0 answered, 1 refused, 2 bad arguments (argparse's own number)."""
    args = _cli_parser().parse_args(argv)
    try:
        return _cli_run(args)
    except KeyboardInterrupt:
        return _cli_fail(_CLI_INTERRUPTED)


if __name__ == "__main__":
    raise SystemExit(main())
