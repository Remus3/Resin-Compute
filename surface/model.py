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
from datetime import datetime, timedelta
from enum import StrEnum

from core import domains, resin
from core.log_setup import get_logger
from core.state_io import snapshot_age
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


#: A reading older than this is called stale. Chosen against the upstream
#: refresh cycle rather than arbitrarily: an Enka showcase refreshes on a ttl
#: measured in minutes, so anything past an hour is certainly not current.
STALE_AFTER = timedelta(hours=1)


def _humanise(age: timedelta) -> str:
    """Render an age the way a person reads it, coarsest useful unit first."""
    seconds = int(age.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes, _ = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


@dataclass(frozen=True)
class Dashboard:
    """Everything one render needs, and a summary of how much of it is live."""

    generated_at: datetime
    panels: tuple[Panel, ...] = ()
    source_age: timedelta | None = None

    @property
    def freshness(self) -> str:
        """How old the underlying reading is, in words.

        THE WHOLE REASON THIS IS ON THE BOARD RATHER THAN OPTIONAL. The dashboard
        renders a snapshot written by the headless lane, not a live query. A
        cached roster shown with no age is indistinguishable from a live one,
        which is exactly the confusion the live-state-first rule exists to
        prevent - and the confusion is silent, because a stale roster looks
        perfectly plausible.

        `None` is NOT zero. An account that has never synced has no reading, and
        saying "0s ago" would present an absence as a measurement.
        """
        if self.source_age is None:
            return "no reading yet"
        return f"synced {_humanise(self.source_age)} ago"

    @property
    def is_stale(self) -> bool:
        """True when the reading is old enough to distrust.

        A never-synced account is NOT stale - it is empty, which is a different
        problem and already visible in every panel saying so.
        """
        return self.source_age is not None and self.source_age > STALE_AFTER

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
    """Resin PROJECTED from the last recorded observation forward to `now`.

    THE DEFECT THIS SHAPE EXISTS TO PREVENT. This panel used to fold the ledger
    to a balance and render that number as the current resin, never touching the
    `now` it was handed. The same account therefore read identically at +0h, +4h
    and +12h while `core.resin.resin_at` answered 20, 50 and 110 for the same
    inputs. Resin regenerates on a wall clock whether anything reads it or not,
    so that was not a stale number - it was a wrong one, and it got wronger the
    longer the operator left the window open.

    The fix is to call `core.resin.resin_at`, which already models the floor
    quantization, the cap and the above-cap overflow rule. Nothing here re-derives
    any of that, and nothing here retypes a constant: a second copy of the cap or
    the regeneration interval would be a second source of truth free to drift out
    of step with the first in silence.

    WHY THE OBSERVATION MOMENT IS `last_synced_at`. The ledger entry carries its
    own `occurred_at`, but the ledger is an append-only log of DELTAS, and a fold
    of it is a balance as of the last event - not as of the last time anybody
    looked at the account. `last_synced_at` is the moment the snapshot was taken,
    which is the moment that balance was last known to be true.

    AND THE HONESTY CONSTRAINT, which is the larger half of this function.
    ADR-005's rule is that a panel never fakes a number. A projection is an
    ESTIMATE, not a measurement: the instant the operator spends resin the
    projection is high and this process cannot know. Regeneration only ever adds,
    so a projection is an UPPER BOUND on the truth and never a lower one. The
    panel therefore always says which of the two a number is, always shows the
    observation it was projected from, and always shows how old that observation
    is. A bare "137 / 200" with no provenance is the failure mode - it is
    indistinguishable from a reading taken a second ago.

    SIX STATES, and the reason for each:

    1. No observation time and no resin ever recorded. READY, and it claims NO
       balance. The regeneration rules are constants true of every account, so
       there is something true to say and no number to be wrong about. This is
       also the contract `tests/test_surface_model.py` pins - the resin panel is
       the smoke test that the surface is alive at all, and it is READY about the
       mechanism rather than about an account nobody has synced.
    2. A recorded balance with no observation time. PARTIAL. The number is real
       and undatable, and projecting it would mean inventing the elapsed time.
    3. An observation stamped AHEAD of `now`. PARTIAL. One of the two clocks is
       wrong. `resin_at` would decline to regenerate and hand back the observed
       value, which is the right arithmetic and the wrong thing to PRESENT: it
       would read as a confident present-tense measurement taken from a clock we
       have just caught disagreeing with itself.
    4. `now` exactly at the observation. READY, and the row says "observed"
       rather than "projected", because at zero elapsed it IS the measurement.
    5. A reading no older than STALE_AFTER. READY, projected, labelled.
    6. A reading older than that. PARTIAL, and the split inside it is the
       interesting one. Past `time_to_reach(observed, CAP)` the projection has
       SATURATED: `resin_at` answers the cap for an observation of 10 and for one
       of 190 alike, so the number stops being a function of anything the
       operator did and becomes a function of the constants alone. Printing it
       would render "200 / 200" - which reads as a measured, capped account - for
       an account nobody has looked at in days. So past saturation the panel
       presents NO present-tense number and shows only what was measured and
       when. That one branch has THREE honest explanations rather than one,
       because `time_to_reach` answers `timedelta(0)` at or above the cap and so
       the branch fires with no refill span elapsed: see the comment at the
       branch. Short of saturation the projection still carries information, so it
       is shown and named an upper bound, which is the `_plan_panel` precedent: a
       truthful PARTIAL that states its own limitation in the same breath as its
       content.
    """
    # Function-local, matching `_wishes_panel` and `_roster_panel`, and because
    # this builder is the only thing in the module that needs it.
    from datetime import UTC

    def _utc(moment: datetime) -> datetime:
        """A naive datetime is taken to be UTC, as `core.resin` and `core.state_io` both do.

        Mixing naive and aware datetimes in a subtraction raises, and a
        hand-edited state file can carry either.
        """
        return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)

    cap = resin.ORIGINAL_RESIN_CAP
    # NOT clamped to the cap. `core/resin.py` is explicit that an above-cap
    # balance is legal - Fragile Resin and event rewards push past 200 - and that
    # `min(200, x)` destroys a real balance the operator paid for.
    observed = max(0, account.ledger.balance_of(CurrencyKind.ORIGINAL_RESIN))
    ever_recorded = any(e.currency is CurrencyKind.ORIGINAL_RESIN for e in account.ledger.entries)
    observed_at = account.last_synced_at

    mechanism = [
        ("Regenerates", f"1 per {resin.RESIN_REGEN_MINUTES} minutes"),
        ("Daily budget", f"{resin.daily_resin_budget()}"),
    ]

    def _unknown(reason: str, waiting: str, seen_at: str) -> Panel:
        """A panel that states the measurement and refuses to state a present-tense one.

        THE VALUE CELL CARRIES A VALUE, NOT A SENTENCE. `surface/render.py`
        right-aligns every `dd`, so a reason long enough to wrap renders as prose
        with a ragged left edge - measured in Chromium, four lines at 360px and
        five at 620px and 900px, and the hardest thing on the board to read. The
        cell therefore carries the bare word and `reason` leads `waiting_on`,
        which is left-aligned prose the panel already has. Nothing is dropped:
        `reason` is a complete sentence and is placed, not deleted.
        """
        rows = [
            ("Resin now", "unknown"),
            ("Observed", f"{observed} / {cap} at {seen_at}" if ever_recorded else "nothing recorded"),
            *mechanism,
        ]
        return Panel(
            panel_id="resin",
            title="Resin",
            state=PanelState.PARTIAL,
            rows=tuple(rows),
            waiting_on=f"{reason} {waiting}",
        )

    # 1. Nothing observed, ever.
    if observed_at is None and not ever_recorded:
        return Panel(
            panel_id="resin",
            title="Resin",
            state=PanelState.READY,
            rows=tuple([("Resin", "not recorded yet"), *mechanism]),
            note=(
                "No resin observation has been recorded, so this panel states the regeneration "
                "rules and claims no balance. A sync gives it something to project from."
            ),
        )

    # 2. A balance nobody dated.
    if observed_at is None:
        return _unknown(
            "The reading carries no observation time.",
            "The ledger holds a resin balance but nothing recorded when it was seen, "
            "so there is no elapsed time to project across. Sync the account to date the reading.",
            "an unrecorded time",
        )

    seen_at = _utc(observed_at).strftime("%Y-%m-%d %H:%M UTC")
    elapsed = _utc(now) - _utc(observed_at)

    # 3. An observation from the future.
    if elapsed < timedelta(0):
        return _unknown(
            f"The reading is stamped {_humanise(-elapsed)} ahead of this clock.",
            "The recorded observation time is ahead of the dashboard clock, so one of the two "
            "is wrong and nothing can be projected across the gap. Re-sync to restamp the reading.",
            seen_at,
        )

    # 6b. The projection has saturated, so it no longer says anything about this
    # account. ONE branch, THREE honest readings of it, because `time_to_reach`
    # returns `timedelta(0)` for an observation at or above the cap: there, the
    # branch fires with NO refill span having elapsed at all. Saying the reading
    # is "longer than a full refill" of zero is true of every reading ever taken
    # and is therefore a statement about nothing - and the operator's own board
    # reads 200 / 200, so that was the common case rather than a corner. The
    # DECISION to withhold the projected number is correct in all three; only
    # the explanation differs.
    refill = resin.time_to_reach(observed, cap)
    if elapsed > STALE_AFTER and (refill is None or elapsed >= refill):
        age = _humanise(elapsed)
        if observed > cap:
            # Above-cap overflow is legal per `core/resin.py` and is never
            # clipped, so the Observed row still shows the real balance.
            reason = (
                f"The reading is {age} old and was {observed - cap} above the cap, "
                "which is a balance regeneration never adds to."
            )
            waiting = (
                "An above-cap balance is carried forward unchanged rather than clamped, so a "
                "projection would restate the observed number as though it had just been "
                "measured. Sync to get a real number."
            )
        elif observed == cap:
            reason = f"The reading is {age} old and was already at the cap, so no refill span had to elapse."
            waiting = (
                "Regeneration stops at the cap, so a projection would restate the observed "
                "number as though it had just been measured. Sync to get a real number."
            )
        else:
            reason = f"The reading is {age} old, longer than a full refill from that balance."
            waiting = (
                "A projection this far out reads as capped whatever was observed, so it would "
                "state the regeneration constants and nothing about this account. Sync to get a "
                "real number."
            )
        return _unknown(reason, waiting, seen_at)

    projected = resin.resin_at(observed, observed_at, now)
    stale = elapsed > STALE_AFTER
    if elapsed == timedelta(0):
        label = "Resin (observed)"
    elif stale:
        label = "Resin (projected upper bound)"
    else:
        label = "Resin (projected)"

    rows = [
        (label, f"{projected} / {cap}"),
        ("Observed", f"{observed} / {cap} at {seen_at}"),
        ("Observation age", _humanise(elapsed)),
    ]
    to_cap = resin.time_to_reach(projected, cap)
    if to_cap is None or to_cap == timedelta(0):
        rows.append(("Time to cap", "already at cap"))
    else:
        hours, remainder = divmod(int(to_cap.total_seconds()), 3600)
        rows.append(("Time to cap", f"{hours}h {remainder // 60:02d}m"))
    rows.extend(mechanism)

    if stale:
        return Panel(
            panel_id="resin",
            title="Resin",
            state=PanelState.PARTIAL,
            rows=tuple(rows),
            waiting_on=(
                f"The reading is {_humanise(elapsed)} old. Regeneration is projected forward from "
                "it, but any resin spent since is invisible here, so this is an upper bound and "
                "not a measurement."
            ),
        )
    return Panel(
        panel_id="resin",
        title="Resin",
        state=PanelState.READY,
        rows=tuple(rows),
        note=(
            ""
            if elapsed == timedelta(0)
            else "Projected forward by regeneration alone. Resin spent since the reading is not visible here."
        ),
    )


def _today_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """The game day, the domain rotation and the weekly reset.

    The game day is NOT the wall-clock day: the server rolls at 04:00, so between
    midnight and 04:00 the game day is still yesterday. Rendering the wall-clock
    date there would tell the operator their dailies had reset when they had not.
    """
    game_day = domains.current_game_day(now)
    weekday = game_day.weekday()
    # "slot 0", never a bare "0". `ROTATION_SLOTS` is (0, 1, 2), so a bare join
    # renders the string "0" on a day when slot 0 is the only one open - and
    # "Domain slots open: 0" is read by everybody as ZERO SLOTS OPEN, which is
    # the exact opposite of what it means. The empty case really does say "none"
    # two lines down, so the two readings collide on the same row. The Plan panel
    # already words its own rotation rows "slot 0"; this makes the board agree
    # with itself rather than state a thing and its negation in two cards.
    open_slots = [f"slot {slot}" for slot in domains.ROTATION_SLOTS if domains.is_available(slot, weekday)]
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

    THE ROTATION ROWS ARE NOT A STEP TOWARDS READY. A plan has two halves - HOW
    MUCH a goal needs, and WHEN the thing it needs can be farmed. Only the first
    half is behind the licence gate. The second is the three-day domain rotation
    in `core/domains.py`, which is pure schedule mechanics naming no domain and
    no material, and which docs/GOAL_SPEC_SEED_TEAM.md section 5.1 records as the
    roadmap's single biggest practical omission: a plan that ignores it sends the
    operator to spend resin on a day the domain is not dropping what they need.

    So the panel answers "what is farmable today, and how long until the rest"
    while still saying, in the same breath, that it cannot tell you how much of
    anything you need. Both halves of that are true at once, which is precisely
    the state PARTIAL exists to express. The rotation is derived by CALLING
    `domains.is_available` and `domains.next_available_day` rather than by
    reading the table - a copy of the weekday tuples here would be a second
    source of truth that could drift out of step with the first in silence.

    The weekday keys on `current_game_day`, not on the wall clock. Between
    midnight and 04:00 server time the game day is still yesterday, so a plan
    keyed on the calendar date would advertise the wrong rotation for four hours
    a day - and would do it most confidently in the small hours, which is when
    somebody is most likely to be burning the last of their resin.
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

    weekday = domains.current_game_day(now).weekday()
    open_slots = [slot for slot in domains.ROTATION_SLOTS if domains.is_available(slot, weekday)]

    rows = [
        ("Goal", "level 90, talents 8/8/8"),
        ("Steps in the graph", str(len(nodes))),
        ("Known material cost", "none - see below"),
        ("Farmable today", ", ".join(f"slot {slot}" for slot in open_slots) if open_slots else "none"),
    ]
    for slot in domains.ROTATION_SLOTS:
        if slot in open_slots:
            continue
        # Never more than six, because Sunday is in every slot's row. The bound
        # is a consequence of the table rather than a rule imposed here, so it
        # is asserted in the tests and not clamped in the code - a clamp would
        # hide a broken table instead of surfacing it.
        wait = domains.next_available_day(slot, weekday)
        rows.append((f"Slot {slot} opens in", f"{wait} day" if wait == 1 else f"{wait} days"))

    return Panel(
        panel_id="plan",
        title="Plan",
        state=PanelState.PARTIAL,
        rows=tuple(rows),
        waiting_on=waiting,
    )


def _teams_panel(account: AccountState, now: datetime, **_: object) -> Panel:
    """Who is on the roster and what element each one is. Nothing that ranks.

    WHAT IS HELD AND WHY, because the boundary is the entire design of this
    panel. ROADMAP's `## Later` holds the TEAM COMPOSITION SOLVER, and the reason
    it gives is that elemental REACTION MODELLING is a large piece of domain work
    that should not start before the resource layer is complete. That holds the
    modelling and the solver. Elemental IDENTITY is neither of those: it is
    already in this tree and already licence-clean, hand-authored into
    `data/fixtures/seed_roster.json` for the five verified avatarIds and read
    back by `ingest.static_data.element_for`.

    So this panel answers the identity question - who is here, what element are
    they, how do the elements fall out, and which of the verified five are absent
    - and refuses the composition question. It is PARTIAL rather than READY for
    exactly that reason: the half that would make this a real Teams answer is
    genuinely still held, and `waiting_on` keeps saying which half. Promoting it
    to READY would claim the held half had landed.

    THE ELEMENT COMES FROM `element_for`, NEVER FROM `MappedCharacter.element`.
    In production those are the same value - `ingest/enka_mapper.py` fills that
    field from this very lookup - so reading the field back would buy nothing and
    would cost the guarantee. The field is settable by any caller, so an id
    outside the verified seed set could arrive carrying an element nobody
    verified, and this panel would then present a guess as a fact. An unknown id
    says it is unknown instead, which is the contract `character_name` already
    keeps for names and for the same reason: `10000088` looked like a plausible
    Dehya id forever.

    NO COST FIGURE APPEARS HERE, and none is derived. docs/GOAL_SPEC_SEED_TEAM.md
    section 3 stamps the roadmap's cost figures UNVERIFIED and forbids them
    entering a calculation, so nothing on this panel touches one.
    """
    waiting = (
        "Elemental identity only. Reaction modelling, and the team composition "
        "solver built on top of it, stay held until the resource layer is "
        "complete - see ROADMAP. Nothing here ranks, scores or recommends."
    )
    if not account.roster:
        # Same reasoning as the Roster panel, and it is upstream's rather than
        # ours: Enka omits `avatarInfoList` entirely when the showcase is closed,
        # so an empty roster means "we were not shown one" far more often than it
        # means "this account owns nobody". A distribution over zero characters
        # would be a confident statement about an account nobody looked at.
        return Panel(
            panel_id="teams",
            title="Teams",
            state=PanelState.NOT_WIRED,
            waiting_on="No profile fetched yet, or the in-game showcase is closed. " + waiting,
        )

    from core.types import Element
    from ingest.static_data import character_name, element_for, known_avatar_ids

    rows: list[tuple[str, str]] = []
    counts: dict[Element, int] = {}
    unresolved = 0
    for character in account.roster:
        name = character.display_name or character_name(character.avatar_id)
        element = element_for(character.avatar_id)
        if element is None:
            unresolved += 1
            rows.append((name, "not in the verified seed set"))
            continue
        counts[element] = counts.get(element, 0) + 1
        rows.append((name, element.value))

    # Enum order, NOT count order. A distribution sorted by size reads as a
    # ranking of elements, and ranking is precisely the half of this panel that
    # is held. The order is a property of the enum rather than a choice made
    # here, so it cannot drift into an implied preference.
    spread = ", ".join(f"{element.value} x{counts[element]}" for element in Element if element in counts)
    rows.append(("Elements present", spread or "none resolved"))

    present = {character.avatar_id for character in account.roster}
    absent = [character_name(a) for a in known_avatar_ids() if a not in present]
    rows.append(("Verified seed characters absent", ", ".join(absent) if absent else "none"))

    note = ""
    if unresolved:
        note = f"{unresolved} character(s) are outside the verified seed set, so no element is claimed for them."
    return Panel(
        panel_id="teams",
        title="Teams",
        state=PanelState.PARTIAL,
        rows=tuple(rows),
        waiting_on=waiting,
        note=note,
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
    return Dashboard(
        generated_at=now,
        panels=tuple(panels),
        source_age=snapshot_age(account, now),
    )
