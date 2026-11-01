"""The one-line forecast card at the top of the dashboard (RSC-FORECAST-GLANCE).

It mirrors the README banner: current pity, guarantee state, and the chance of
the featured 5-star within N wishes - "pity 74, no guarantee, 30 wishes gives a
59.0 percent chance of the featured 5-star". Every number comes from the
PityEngine forecast; nothing here re-derives a gacha constant. The expected
chance is computed by calling the engine, so the test pins the wiring, and the
README's own 59.0 figure pins that the wiring is the same query the banner shows.
"""
from __future__ import annotations

import json
from dataclasses import fields
from datetime import UTC, datetime

import pytest

from agents.pity_engine.forecast import probability_of_success
from core.types import AccountState, BannerKind, PityState
from surface import model as model_mod
from surface.model import GLANCE_WISHES, Dashboard, ForecastGlance, build_dashboard
from surface.render import render_html, render_json

NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)

GLANCE_FIELDS = ("available", "banner", "pity", "guarantee", "wishes", "chance", "text")


def _account(pity: dict | None = None) -> AccountState:
    state = AccountState(uid="000000000")
    if pity is not None:
        state.pity = pity
    return state


def _banner_state() -> AccountState:
    return _account({BannerKind.CHARACTER_EVENT: PityState(pity_5star=74, has_guarantee=False)})


def test_the_glance_field_set_is_pinned():
    assert tuple(f.name for f in fields(ForecastGlance)) == GLANCE_FIELDS
    assert GLANCE_WISHES == 30


def test_the_glance_renders_from_the_engine_output():
    board = build_dashboard(_banner_state(), now=NOW)
    glance = board.glance
    assert glance is not None and glance.available
    expected = probability_of_success(
        PityState(pity_5star=74, has_guarantee=False),
        target_count=1,
        pull_budget=GLANCE_WISHES,
        banner=BannerKind.CHARACTER_EVENT,
    )
    assert glance.banner == "Character Event"
    assert glance.pity == "74"
    assert glance.guarantee == "no guarantee"
    assert glance.wishes == "30"
    assert glance.chance == f"{expected.probability * 100:.1f}%"
    assert glance.chance == "59.0%"  # the README banner's own figure
    assert glance.text == "Pity 74, no guarantee, 30 wishes gives a 59.0% chance of the featured 5-star"


def test_the_guarantee_state_is_carried():
    state = _account({BannerKind.CHARACTER_EVENT: PityState(pity_5star=10, has_guarantee=True)})
    glance = build_dashboard(state, now=NOW).glance
    assert glance is not None and glance.guarantee == "guaranteed"
    assert "guaranteed" in glance.text


def test_the_glance_is_the_first_row_of_the_page():
    page = render_html(build_dashboard(_banner_state(), now=NOW))
    glance_at = page.index('class="glance')
    assert glance_at < page.index("<header>")
    assert glance_at < page.index('<div class="grid">')
    assert "Pity 74, no guarantee, 30 wishes gives a 59.0% chance of the featured 5-star" in page


def test_the_glance_is_in_the_json_payload():
    payload = json.loads(render_json(build_dashboard(_banner_state(), now=NOW)))
    assert tuple(payload["glance"]) == tuple(sorted(GLANCE_FIELDS))
    assert payload["glance"]["chance"] == "59.0%"


def test_no_pity_degrades_to_friendly_text_and_no_number():
    glance = build_dashboard(_account(), now=NOW).glance
    assert glance is not None and not glance.available
    assert glance.pity == glance.chance == glance.wishes == ""
    assert glance.text
    assert not any(ch.isdigit() for ch in glance.text)


def test_an_engine_failure_degrades_and_logs_the_raw_error(monkeypatch):
    secret = "RAW-ENGINE-ERR-xyz"

    def boom(*_a, **_k):
        raise RuntimeError(secret)

    logged: list[str] = []

    class _Recorder:
        def error(self, fmt, *args):
            logged.append(fmt % args)

    monkeypatch.setattr(model_mod, "_glance_forecast", boom)
    monkeypatch.setattr(model_mod, "_log", _Recorder())
    board = build_dashboard(_banner_state(), now=NOW)
    glance = board.glance
    assert glance is not None and not glance.available
    assert glance.chance == ""
    page = render_html(board)
    assert secret not in page and secret not in render_json(board)
    assert glance.text in page
    assert any(secret in line for line in logged)
    # The panels survive the glance failing.
    assert board.panel("wishes").rows


def test_a_board_without_a_glance_still_renders_a_friendly_top_row():
    board = Dashboard(generated_at=NOW)
    page = render_html(board)
    assert page.index('class="glance') < page.index("<header>")
    assert "Forecast unavailable" in page
    assert json.loads(render_json(board))["glance"] is None


@pytest.mark.parametrize("pity", [0, 89])
def test_the_glance_chance_tracks_the_engine_at_the_edges(pity):
    state = _account({BannerKind.CHARACTER_EVENT: PityState(pity_5star=pity)})
    glance = build_dashboard(state, now=NOW).glance
    expected = probability_of_success(PityState(pity_5star=pity), 1, GLANCE_WISHES, BannerKind.CHARACTER_EVENT)
    assert glance is not None and glance.chance == f"{expected.probability * 100:.1f}%"
