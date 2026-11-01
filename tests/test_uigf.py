"""UIGF v4 import and export (MAIN ORDER item RSC-UIGF-IO).

The fixture `data/fixtures/uigf_v4_sample.json` is INVENTED and hand-authored:
placeholder uid, ids, names and times. Its expected pity figures are derived by
hand in the comments below, from the fixture rows, not from the module.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agents.pity_engine.forecast import probability_of_success
from core.types import BannerKind, PityState
from ingest.uigf import (
    UIGF_VERSION,
    UigfDocument,
    UigfError,
    UigfItem,
    build_document,
    dumps,
    export_document,
    forecast_from_uigf,
    parse_document,
    pity_state_from_uigf,
    read_uigf,
    write_uigf,
)

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "uigf_v4_sample.json"


def _raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _doc() -> UigfDocument:
    return parse_document(_raw())


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def test_fixture_declares_itself_invented():
    raw = _raw()
    assert raw["_invented"] is True
    assert raw["_vendored"] is False


def test_parse_yields_typed_records():
    doc = _doc()
    assert doc.info.version == "v4.0"
    assert doc.info.export_app == "TestExporter"
    assert len(doc.hk4e) == 1
    account = doc.hk4e[0]
    assert account.uid == "000000001"
    assert account.timezone == 8
    assert len(account.items) == 14
    assert all(isinstance(item, UigfItem) for item in account.items)
    five = [item for item in account.items if item.rank_type == "5"]
    assert {item.name for item in five} == {"Test Item A", "Test Item D"}


# ---------------------------------------------------------------------------
# Round trip - the acceptance criterion
# ---------------------------------------------------------------------------


def test_round_trip_parse_export_parse_is_identical():
    first = _doc()
    exported = export_document(first)
    second = parse_document(exported)
    assert second == first
    # And the exported dict re-exports byte-identically.
    assert dumps(second) == dumps(first)


def test_round_trip_preserves_every_hk4e_field_of_the_source():
    raw = _raw()
    exported = export_document(parse_document(raw))
    assert exported["info"] == raw["info"]
    assert exported["hk4e"] == raw["hk4e"]


def test_round_trip_through_a_file(tmp_path):
    target = tmp_path / "out.json"
    assert write_uigf(target, _doc()) is True
    assert read_uigf(target) == _doc()
    assert b"\r\n" not in target.read_bytes()


def test_build_document_exports_rsc_records_as_v4():
    items = _doc().hk4e[0].items
    doc = build_document("000000002", items, timezone=8, lang="en-us", export_timestamp=1)
    out = export_document(doc)
    assert out["info"]["version"] == UIGF_VERSION == "v4.0"
    assert out["info"]["export_app"] == "ResinCompute"
    assert out["hk4e"][0]["uid"] == "000000002"
    assert parse_document(json.loads(dumps(doc))) == doc


# ---------------------------------------------------------------------------
# Validation - each guard with a firing arm
# ---------------------------------------------------------------------------


def _mutated(path: tuple, value) -> dict:
    raw = copy.deepcopy(_raw())
    node = raw
    for key in path[:-1]:
        node = node[key]
    if value is _DELETE:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return raw


_DELETE = object()
_ITEM0 = ("hk4e", 0, "list", 0)


@pytest.mark.parametrize(
    "path,value,needle",
    [
        (("info", "version"), "v3.0", "version"),
        (("info",), _DELETE, "info"),
        (("hk4e",), {}, "hk4e"),
        (("hk4e", 0, "uid"), _DELETE, "uid"),
        ((*_ITEM0, "uigf_gacha_type"), "999", "uigf_gacha_type"),
        ((*_ITEM0, "gacha_type"), "302", "gacha_type"),
        ((*_ITEM0, "id"), _DELETE, "id"),
        ((*_ITEM0, "id"), "abc", "id"),
        ((*_ITEM0, "item_id"), 90000003, "item_id"),
        ((*_ITEM0, "rank_type"), "6", "rank_type"),
        ((*_ITEM0, "time"), "2026/01/02 10:00", "time"),
        ((*_ITEM0, "count"), "x", "count"),
    ],
)
def test_validation_rejects_malformed_input(path, value, needle):
    with pytest.raises(UigfError, match=needle):
        parse_document(_mutated(path, value))


def test_validation_rejects_duplicate_ids():
    raw = _raw()
    raw["hk4e"][0]["list"][1]["id"] = raw["hk4e"][0]["list"][0]["id"]
    with pytest.raises(UigfError, match="duplicate"):
        parse_document(raw)


def test_validation_accepts_400_under_301_and_optional_fields_absent():
    """The neighbours a strict validator must leave standing."""
    raw = _raw()
    assert any(row["gacha_type"] == "400" for row in raw["hk4e"][0]["list"])
    for key in ("name", "item_type", "count"):
        del raw["hk4e"][0]["list"][0][key]
    doc = parse_document(raw)
    assert doc.hk4e[0].items[0].name is None
    assert "name" not in export_document(doc)["hk4e"][0]["list"][0]


def test_uigf_error_is_a_value_error():
    assert issubclass(UigfError, ValueError)


# ---------------------------------------------------------------------------
# Starting pity
# ---------------------------------------------------------------------------
# Character (301 incl. 400), chronological by (time, id):
#   001 r3, 002 r4, 003 r3, 004 r5, 005 r3, 006 r4, 007 r3, 008 r3
#   since last 5-star (004): 005..008 -> 4; since last 4-star (006): 007, 008 -> 2
# Weapon (302): three r3 -> 3 and 3. Standard (200): r5 then r3 -> 1, and no
#   4-star at all -> 2. Chronicled (500): no rows -> 0 and 0.


@pytest.mark.parametrize(
    "banner,p5,p4",
    [
        (BannerKind.CHARACTER_EVENT, 4, 2),
        (BannerKind.WEAPON_EVENT, 3, 3),
        (BannerKind.STANDARD, 1, 2),
        (BannerKind.CHRONICLED, 0, 0),
    ],
)
def test_pity_derived_per_banner(banner, p5, p4):
    state = pity_state_from_uigf(_doc(), "000000001", banner)
    assert state == PityState(banner=banner, pity_5star=p5, pity_4star=p4)


def test_pity_ignores_file_order():
    """The fixture lists the character rows newest-first; reversing must not matter."""
    raw = _raw()
    raw["hk4e"][0]["list"].reverse()
    state = pity_state_from_uigf(parse_document(raw), "000000001", BannerKind.CHARACTER_EVENT)
    assert (state.pity_5star, state.pity_4star) == (4, 2)


def test_guarantee_state_is_caller_input():
    state = pity_state_from_uigf(
        _doc(),
        "000000001",
        BannerKind.CHARACTER_EVENT,
        has_guarantee=True,
        consecutive_5050_losses=2,
    )
    assert state.has_guarantee is True
    assert state.consecutive_5050_losses == 2
    assert state.pity_5star == 4


def test_pity_needs_rank_type():
    raw = _raw()
    del raw["hk4e"][0]["list"][0]["rank_type"]
    with pytest.raises(UigfError, match="rank_type"):
        pity_state_from_uigf(parse_document(raw), "000000001", BannerKind.CHARACTER_EVENT)


def test_pity_unknown_uid_raises():
    with pytest.raises(UigfError, match="uid"):
        pity_state_from_uigf(_doc(), "999", BannerKind.CHARACTER_EVENT)


# ---------------------------------------------------------------------------
# Forecaster wiring
# ---------------------------------------------------------------------------


def test_forecast_from_uigf_matches_engine_on_seeded_state():
    got = forecast_from_uigf(_doc(), "000000001", BannerKind.CHARACTER_EVENT, 1, 80)
    want = probability_of_success(
        PityState(banner=BannerKind.CHARACTER_EVENT, pity_5star=4, pity_4star=2),
        1,
        80,
        banner=BannerKind.CHARACTER_EVENT,
    )
    assert got == want


def test_forecast_seeding_changes_the_answer():
    """Non-vacuity: a seeded pity must differ from a fresh-account forecast.

    The budget reaches soft pity: below it the hazard is flat, so a budget
    that stays in the flat region gives the same probability for pity 0 and 3.
    """
    seeded = forecast_from_uigf(_doc(), "000000001", BannerKind.WEAPON_EVENT, 1, 70)
    fresh = probability_of_success(
        PityState(banner=BannerKind.WEAPON_EVENT), 1, 70, banner=BannerKind.WEAPON_EVENT
    )
    assert seeded.probability > fresh.probability
    assert seeded.expected_pulls < fresh.expected_pulls
