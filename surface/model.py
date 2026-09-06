"""The dashboard model - pure, and the only place a panel's readiness is decided.

WHAT THIS IS. `build_dashboard` turns an `AccountState` and a clock into a tuple
of panels ready for rendering. It performs NO I/O: no socket, no file, no
`datetime.now()`. The clock is an argument, which is what makes the daily-reset
boundary testable at all.

THE RULE THIS MODULE EXISTS TO ENFORCE, from ADR-005:

    A panel that is not READY must say what it is waiting on, and must not
    carry a number.

That is stronger than it sounds and it is enforced in `Panel.__post_init__`
rather than only in the builders, so a panel added later by somebody who has not
read this docstring still cannot ship a silent gap.

WHY IT MATTERS HERE SPECIFICALLY. This repository's planner decomposes a goal
into a correct DAG whose material costs are all empty, because the licence gate
in ADR-002 means no cost table exists yet. A dashboard that rendered that as
"0 resin required" would not be showing a neutral placeholder - it would be
stating, confidently and in the operator's own UI, a number that is wrong. The
same distinction `engines/objectives.py` draws between a cost of zero and a cost
that is unknown is drawn here between a value and an absence.

EVERY PANEL IS BUILT INSIDE A GUARD. A builder that raises degrades its own panel
to `PARTIAL` with fixed text and leaves the other panels alone, per the hard rule
that a raw error string never reaches a user-facing surface. The raw exception is
logged.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from core import domains, resin
from core.log_setup import get_logger
from core.types import AccountState, CurrencyKind

_log = get_logger(__name__)

__all__ = [
    "PANEL_IDS",
    "Dashboard",
    "Panel",
    "PanelState",
    "build_dashboard",
]


class PanelState(StrEnum):
    """How much of a panel is real.

    Three states rather than two, because "some of this is true" is the honest
    description of most of this tree right now and collapsing it into either
    READY or NOT_WIRED would lose the distinction the operator most needs.
    """

    READY = "ready"
    PARTIAL = "partial"
    NOT_WIRED = "not_wired"


@dataclass(frozen=True)
class Panel:
    """One card on the dashboard.

    `rows` are (label, value) pairs, already rendered as strings. Formatting
    happens here rather than in the renderer so that the renderer stays a pure
    function of text and cannot introduce a number of its own.
    """

    panel_id: str
    title: str
    state: PanelState
    rows: tuple[tuple[str, str], ...] = ()
    waiting_on: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.state is not PanelState.READY and not self.waiting_on:
            raise ValueError(f"panel {self.panel_id} is {self.state.value} but names nothing it is waiting on")
        if self.state is PanelState.NOT_WIRED and self.rows:
            raise ValueError(f"panel {self.panel_id} is not wired but carries {len(self.rows)} rows")


@dataclass(frozen=True)
class Dashboard:
    """Everything one render needs, and a summary of how much of it is live."""

    generated_at: datetime
    panels: tuple[Panel, ...] = ()

    def panel(self, panel_id: str) -> Panel:
        for panel in self.panels:
            if panel.panel_id == panel_id:
                return panel
        raise KeyError(panel_id)

    @property
    def ready_count(self) -> int:
        return sum(1 for p in self.panels if p.state is PanelState.READY)

    @property
    def partial_count(self) -> int:
        return sum(1 for p in self.panels if p.state is PanelState.PARTIAL)

    @property
    def not_wired_count(self) -> int:
        return sum(1 for p in self.panels if p.state is PanelState.NOT_WIRED)

    @property
    def readiness(self) -> float:
        """Fraction of the board that is live, counting PARTIAL as a half.

        This is the number the operator watches while features land, which is the
        whole reason ADR-005 puts the shell before the features. A partial panel
        counts for half rather than for nothing because a correct DAG with no
        costs really is halfway there.
        """
        if not self.panels:
            return 0.0
        score = self.ready_count + 0.5 * self.partial_count
        return score / len(self.panels)


# ---------------------------------------------------------------------------
# Panel builders - one per card, each pure
# ---------------------------------------------------------------------------


def _resin_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """Resin state. Always has something true to say.

    This is the only panel that needs no profile fetch and no account data, which
    makes it the honest smoke test that the surface is alive at all.
    """
    ledger_resin = account.ledger.balance_of(CurrencyKind.ORIGINAL_RESIN)
    current = max(0, min(ledger_resin, resin.ORIGINAL_RESIN_CAP))
    to_cap = resin.time_to_reach(current, resin.ORIGINAL_RESIN_CAP)

    rows = [
        ("Resin", f"{current} / {resin.ORIGINAL_RESIN_CAP}"),
        ("Regenerates", f"1 per {resin.RESIN_REGEN_MINUTES} minutes"),
        ("Daily budget", f"{resin.daily_resin_budget()}"),
    ]
    if to_cap is None:
        rows.append(("Time to cap", "already at cap"))
    else:
        hours, remainder = divmod(int(to_cap.total_seconds()), 3600)
        rows.append(("Time to cap", f"{hours}h {remainder // 60:02d}m"))

    note = ""
    if ledger_resin == 0:
        note = "No resin events on the ledger yet, so this reads as empty rather than as measured."
    return Panel(panel_id="resin", title="Resin", state=PanelState.READY, rows=tuple(rows), note=note)


def _today_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """The game day, the domain rotation and the weekly reset.

    The game day is NOT the wall-clock day: the server rolls at 04:00, so between
    midnight and 04:00 the game day is still yesterday. Rendering the wall-clock
    date there would tell the operator their dailies had reset when they had not.
    """
    game_day = domains.current_game_day(now)
    weekday = game_day.weekday()
    open_slots = [str(slot) for slot in domains.ROTATION_SLOTS if domains.is_available(slot, weekday)]
    weekday_name = _WEEKDAY_NAMES[weekday]

    rows = [
        ("Game day", f"{game_day.isoformat()} ({weekday_name})"),
        ("Domain slots open", ", ".join(open_slots) if open_slots else "none"),
        ("Daily reset", f"{domains.DAILY_RESET_HOUR:02d}:00 server time"),
        ("Weekly reset", _WEEKDAY_NAMES[domains.WEEKLY_RESET_WEEKDAY]),
    ]
    return Panel(panel_id="today", title="Today", state=PanelState.READY, rows=tuple(rows))


def _wishes_panel(account: AccountState, now: datetime, pull_budget: int = 90, **_: object) -> Panel:
    """Pity state and a real forecast from PityEngine.

    NOT_WIRED rather than a zeroed card when no pity is known, because a pity
    counter of 0 is a real and meaningful state - a fresh banner - and is not the
    same as never having told the tool anything.
    """
    if not account.pity:
        return Panel(
            panel_id="wishes",
            title="Wishes",
            state=PanelState.NOT_WIRED,
            waiting_on="No pity state recorded. Wish history is not importable from the public profile API.",
        )

    from agents.pity_engine.forecast import probability_of_success

    rows: list[tuple[str, str]] = []
    for banner in sorted(account.pity, key=lambda b: b.value):
        state = account.pity[banner]
        result = probability_of_success(state, target_count=1, pull_budget=pull_budget, banner=banner)
        label = banner.value.replace("_", " ").title()
        guarantee = " (guaranteed)" if state.has_guarantee else ""
        rows.append((f"{label} pity", f"{state.pity_5star}{guarantee}"))
        rows.append((f"{label} in {pull_budget} pulls", f"{result.probability * 100:.1f}%"))
        if result.expected_pulls is not None:
            rows.append((f"{label} expected pulls", f"{result.expected_pulls:.1f}"))

    return Panel(panel_id="wishes", title="Wishes", state=PanelState.READY, rows=tuple(rows))


def _roster_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """Characters from the last profile fetch.

    Empty is NOT_WIRED rather than READY-with-nothing, because the upstream omits
    `avatarInfoList` entirely when the showcase is closed - so an empty roster
    most often means "we were not shown one", not "you own no characters".
    """
    if not account.roster:
        return Panel(
            panel_id="roster",
            title="Roster",
            state=PanelState.NOT_WIRED,
            waiting_on="No profile fetched yet, or the in-game showcase is closed.",
        )

    from ingest.static_data import character_name, is_unknown_name

    rows: list[tuple[str, str]] = []
    unknown = 0
    for character in account.roster:
        name = character.display_name or character_name(character.avatar_id)
        if is_unknown_name(name):
            unknown += 1
        detail = f"level {character.level}, ascension {character.ascension}, C{character.constellations}"
        rows.append((name, detail))

    note = ""
    if unknown:
        note = f"{unknown} character(s) are outside the verified seed set and show as a placeholder id."
    return Panel(
        panel_id="roster",
        title="Roster",
        state=PanelState.READY,
        rows=tuple(rows),
        note=note,
    )


def _plan_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """What the planner can and cannot answer today.

    PARTIAL, always, and deliberately. The DAG is correct and complete as
    mechanism; every material cost behind it is empty because ADR-002's licence
    gate means no cost table exists. Reporting a finish date off that would be
    the exact failure ADR-005 built this panel's contract to prevent.
    """
    waiting = (
        "The objective DAG is correct but every material cost is empty. "
        "A first-party cost table is the gate - see ADR-002 and ROADMAP."
    )
    if not account.roster:
        return Panel(
            panel_id="plan",
            title="Plan",
            state=PanelState.NOT_WIRED,
            waiting_on="No roster to plan against yet. " + waiting,
        )

    from engines.objectives import expand_character_goal

    subject = account.roster[0]
    nodes = expand_character_goal(subject.avatar_id, target_level=90, talent_targets={1: 8, 2: 8, 3: 8})
    rows = [
        ("Goal", "level 90, talents 8/8/8"),
        ("Steps in the graph", str(len(nodes))),
        ("Known material cost", "none - see below"),
    ]
    return Panel(
        panel_id="plan",
        title="Plan",
        state=PanelState.PARTIAL,
        rows=tuple(rows),
        waiting_on=waiting,
    )


def _teams_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """Team composition for an event. Not started.

    Named on the board from day one on purpose: ADR-005 puts the shell before the
    features so that arrival is visible, and a feature that is not yet on the
    board cannot be watched arriving.
    """
    return Panel(
        panel_id="teams",
        title="Teams",
        state=PanelState.NOT_WIRED,
        waiting_on=(
            "Team composition needs elemental reaction modelling, which ROADMAP "
            "holds until the resource layer is complete."
        ),
    )


_BUILDERS: tuple[tuple[str, Callable[..., Panel]], ...] = (
    ("resin", _resin_panel),
    ("today", _today_panel),
    ("wishes", _wishes_panel),
    ("roster", _roster_panel),
    ("plan", _plan_panel),
    ("teams", _teams_panel),
)

PANEL_IDS: tuple[str, ...] = tuple(panel_id for panel_id, _ in _BUILDERS)

_TITLES = {
    "resin": "Resin",
    "today": "Today",
    "wishes": "Wishes",
    "roster": "Roster",
    "plan": "Plan",
    "teams": "Teams",
}

_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_DEGRADED = "This panel could not be built from the current state. The details are in the log."


def build_dashboard(
    account: AccountState,
    now: datetime,
    pull_budget: int = 90,
) -> Dashboard:
    """Build every panel. Pure, total, and never raises.

    EVERY BUILDER RUNS INSIDE A GUARD. One panel failing must not blank the other
    five - a dashboard that goes white because a roster entry was malformed is
    worse than one that shows five good cards and one that says it could not be
    built. The raw exception goes to the log; the operator sees fixed text.

    The blind except is deliberate and is the same call `headless/runner.py` and
    `ops/supervisor.py` make at their own boundaries: a builder is effectively
    third-party code from this function's point of view, and the set of things it
    might raise is not enumerable.
    """
    panels: list[Panel] = []
    for panel_id, builder in _BUILDERS:
        try:
            panels.append(builder(account, now, pull_budget=pull_budget))
        except Exception as exc:  # noqa: BLE001 - a panel must never take the board down
            _log.error(
                "dashboard panel %s failed: %s: %s",
                panel_id,
                exc.__class__.__name__,
                exc,
            )
            panels.append(
                Panel(
                    panel_id=panel_id,
                    title=_TITLES.get(panel_id, panel_id.title()),
                    state=PanelState.PARTIAL,
                    waiting_on=_DEGRADED,
                )
            )
    return Dashboard(generated_at=now, panels=tuple(panels))
