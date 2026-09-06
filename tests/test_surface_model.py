"""Tests for the dashboard model.

The model is PURE: it takes an account snapshot and a clock and returns panels.
No socket, no file, no `datetime.now()`. That is what lets the interesting
assertions below exist at all - a panel's readiness is a decision, and a decision
that can only be observed by looking at a running window is a decision nobody
grades.

THE CENTRAL INVARIANT, and the reason this file is longer than the module:
a panel that is not READY must say what it is waiting on and must not carry a
number. ADR-005 states why - rendering "0 resin required" for a plan built on an
empty cost table is not a neutral placeholder, it is a confident wrong answer.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.types import (
    AccountState,
    BannerKind,
    Element,
    MappedCharacter,
    PityState,
)
from surface.model import (
    PANEL_IDS,
    Dashboard,
    Panel,
    PanelState,
    build_dashboard,
)

NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)


def account(**kwargs) -> AccountState:
    state = AccountState(uid="000000000")
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_build_dashboard_returns_every_declared_panel_in_a_stable_order():
    board = build_dashboard(account(), now=NOW)
    assert isinstance(board, Dashboard)
    assert tuple(p.panel_id for p in board.panels) == PANEL_IDS


def test_the_model_is_pure_and_takes_its_clock_as_an_argument():
    """Two calls with the same clock produce the same board.

    A model that reached for `datetime.now()` would be untestable at the edges
    that matter - the daily reset boundary and the weekly one.
    """
    first = build_dashboard(account(), now=NOW)
    second = build_dashboard(account(), now=NOW)
    assert first == second


def test_every_panel_has_a_title_and_a_declared_state():
    board = build_dashboard(account(), now=NOW)
    for panel in board.panels:
        assert panel.title
        assert isinstance(panel.state, PanelState)


# ---------------------------------------------------------------------------
# The central invariant
# ---------------------------------------------------------------------------


def test_a_panel_that_is_not_ready_names_what_it_is_waiting_on():
    board = build_dashboard(account(), now=NOW)
    for panel in board.panels:
        if panel.state is PanelState.READY:
            continue
        assert panel.waiting_on, f"panel {panel.panel_id} is {panel.state} but names nothing it needs"


def test_a_not_wired_panel_carries_no_rows_at_all():
    """The strongest form of the invariant.

    A row is a label and a value, and a value on an unwired panel is a number
    with nothing behind it. There is no such thing as a harmless placeholder
    zero on a planning tool.
    """
    board = build_dashboard(account(), now=NOW)
    for panel in board.panels:
        if panel.state is PanelState.NOT_WIRED:
            assert panel.rows == (), f"panel {panel.panel_id} is not wired but carries rows"


def test_panel_rejects_a_non_ready_state_with_no_waiting_on():
    """Enforced in the type, not only in the builders.

    A future panel added by somebody who did not read this file still cannot
    ship a silent gap.
    """
    with pytest.raises(ValueError):
        Panel(panel_id="x", title="X", state=PanelState.NOT_WIRED)


def test_panel_rejects_rows_on_a_not_wired_panel():
    with pytest.raises(ValueError):
        Panel(
            panel_id="x",
            title="X",
            state=PanelState.NOT_WIRED,
            waiting_on="something",
            rows=(("a", "0"),),
        )


def test_a_ready_panel_needs_no_waiting_on():
    panel = Panel(panel_id="x", title="X", state=PanelState.READY, rows=(("a", "1"),))
    assert panel.waiting_on == ""


# ---------------------------------------------------------------------------
# Individual panels
# ---------------------------------------------------------------------------


def test_the_resin_panel_is_ready_with_no_account_data_at_all():
    """Resin is pure arithmetic on a clock, so it always has something true to say.

    It is the one panel that does not depend on a profile fetch, which makes it
    the honest smoke test that the whole surface is alive.
    """
    board = build_dashboard(account(), now=NOW)
    panel = board.panel("resin")
    assert panel.state is PanelState.READY
    assert panel.rows


def test_the_today_panel_reports_the_game_day_not_the_wall_clock_day():
    """04:00 server reset. At 02:00 the game day is still yesterday."""
    before_reset = datetime(2026, 9, 6, 2, 0, tzinfo=UTC)
    board = build_dashboard(account(), now=before_reset)
    values = dict(board.panel("today").rows)
    assert "2026-09-05" in " ".join(values.values())


def test_the_wishes_panel_is_not_wired_without_pity_state():
    board = build_dashboard(account(), now=NOW)
    panel = board.panel("wishes")
    assert panel.state is PanelState.NOT_WIRED
    assert panel.rows == ()


def test_the_wishes_panel_becomes_ready_once_pity_is_known():
    state = account()
    state.pity = {BannerKind.CHARACTER_EVENT: PityState(pity_5star=74, has_guarantee=False)}
    board = build_dashboard(state, now=NOW)
    panel = board.panel("wishes")
    assert panel.state is PanelState.READY
    assert panel.rows


def test_the_wishes_panel_reports_a_real_forecast_not_a_placeholder():
    """Pity 89, one pull, character banner - a number only the real engine gives.

    The next wish is number 90, so a 5-star is CERTAIN. The featured character is
    not: the roll is a contested 50/50, and SPEC section 3.2 pins the per-roll
    rate-up probability at 0.52106 since Capturing Radiance shipped in version
    5.0. So the answer is 52.1%, and a surface rendering a placeholder or
    confusing "a 5-star" with "the character" cannot produce that digit string.

    This assertion was originally written expecting 96 or 100 - the probability
    of ANY 5-star - which is the exact confusion the constant guards against.
    """
    state = account()
    state.pity = {BannerKind.CHARACTER_EVENT: PityState(pity_5star=89)}
    board = build_dashboard(state, now=NOW, pull_budget=1)
    joined = " ".join(v for _, v in board.panel("wishes").rows)
    assert "52.1%" in joined


def test_the_roster_panel_is_not_wired_with_an_empty_roster():
    board = build_dashboard(account(), now=NOW)
    assert board.panel("roster").state is PanelState.NOT_WIRED


def test_the_roster_panel_lists_characters_when_present():
    state = account()
    state.roster = (
        MappedCharacter(
            avatar_id=10000096,
            level=60,
            ascension=3,
            constellations=0,
            element=Element.PYRO,
            display_name="Arlecchino",
        ),
    )
    board = build_dashboard(state, now=NOW)
    panel = board.panel("roster")
    assert panel.state is PanelState.READY
    assert any("Arlecchino" in label for label, _ in panel.rows)


def test_the_plan_panel_is_partial_and_says_the_cost_table_is_missing():
    """The honest state of the planner today.

    The DAG is correct and the costs are empty, so the panel is PARTIAL rather
    than READY, and it names the gate. ROADMAP and ADR-002 carry the same fact;
    this is the version the operator actually sees.
    """
    state = account()
    state.roster = (
        MappedCharacter(avatar_id=10000096, level=60, ascension=3, constellations=0, display_name="Arlecchino"),
    )
    board = build_dashboard(state, now=NOW)
    panel = board.panel("plan")
    assert panel.state is PanelState.PARTIAL
    assert "cost" in panel.waiting_on.lower()


def test_the_teams_panel_is_not_wired_and_says_so():
    board = build_dashboard(account(), now=NOW)
    panel = board.panel("teams")
    assert panel.state is PanelState.NOT_WIRED
    assert panel.waiting_on


# ---------------------------------------------------------------------------
# Aggregate reporting - this is what makes progress visible
# ---------------------------------------------------------------------------


def test_the_board_summarises_how_much_of_itself_is_live():
    board = build_dashboard(account(), now=NOW)
    assert board.ready_count + board.partial_count + board.not_wired_count == len(board.panels)
    assert 0.0 <= board.readiness <= 1.0


def test_readiness_rises_as_data_arrives():
    """The number the operator watches while features land."""
    empty = build_dashboard(account(), now=NOW)
    state = account()
    state.pity = {BannerKind.CHARACTER_EVENT: PityState(pity_5star=10)}
    state.roster = (MappedCharacter(avatar_id=10000032, level=90, ascension=6, constellations=0),)
    fuller = build_dashboard(state, now=NOW)
    assert fuller.readiness > empty.readiness


def test_panel_lookup_raises_for_an_unknown_id():
    board = build_dashboard(account(), now=NOW)
    with pytest.raises(KeyError):
        board.panel("no_such_panel")


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------


def test_a_panel_builder_that_raises_degrades_that_panel_and_not_the_board():
    """Hard rule: never surface a raw error string, and never take the page down.

    One panel failing must not blank the other five, and the failure text the
    operator sees must not be an exception repr.
    """
    state = account()
    state.pity = {BannerKind.CHARACTER_EVENT: "not a PityState"}  # type: ignore[dict-item]
    board = build_dashboard(state, now=NOW)
    assert len(board.panels) == len(PANEL_IDS)
    panel = board.panel("wishes")
    assert panel.state is not PanelState.READY
    assert "Traceback" not in panel.waiting_on
    assert "AttributeError" not in panel.waiting_on


# ---------------------------------------------------------------------------
# Freshness - a snapshot rendered without its age reads as a live reading
# ---------------------------------------------------------------------------


def test_a_board_built_from_a_never_synced_account_says_so():
    """NONE IS NOT ZERO. 'no reading yet' and 'synced 0 seconds ago' are
    different facts, and only one of them is true for a fresh account."""
    board = build_dashboard(account(), now=NOW)
    assert board.source_age is None
    assert "no reading" in board.freshness.lower()


def test_a_board_reports_how_old_its_reading_is():
    from datetime import timedelta

    state = account()
    state.last_synced_at = NOW - timedelta(hours=3, minutes=12)
    board = build_dashboard(state, now=NOW)
    assert board.source_age == timedelta(hours=3, minutes=12)
    assert "3h" in board.freshness


def test_a_recent_reading_reads_as_minutes_not_a_bare_timestamp():
    from datetime import timedelta

    state = account()
    state.last_synced_at = NOW - timedelta(minutes=7)
    board = build_dashboard(state, now=NOW)
    assert "7m" in board.freshness


def test_freshness_never_reports_a_negative_age():
    """A clock that moved backwards, or a snapshot written by another machine."""
    from datetime import timedelta

    state = account()
    state.last_synced_at = NOW + timedelta(hours=5)
    board = build_dashboard(state, now=NOW)
    assert board.source_age == timedelta(0)


def test_a_stale_reading_is_flagged_as_stale():
    from datetime import timedelta

    state = account()
    state.last_synced_at = NOW - timedelta(days=2)
    board = build_dashboard(state, now=NOW)
    assert board.is_stale
    assert not build_dashboard(account(), now=NOW).is_stale


def test_a_fresh_reading_is_not_flagged_as_stale():
    from datetime import timedelta

    state = account()
    state.last_synced_at = NOW - timedelta(minutes=2)
    board = build_dashboard(state, now=NOW)
    assert not board.is_stale
