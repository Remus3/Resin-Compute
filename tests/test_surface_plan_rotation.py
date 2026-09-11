"""The Plan panel must answer what is farmable TODAY.

WHY THIS FILE EXISTS. The Plan panel is PARTIAL and stays PARTIAL: every
material cost behind the objective DAG is empty because ADR-002's licence gate
means no cost table exists in this tree, and ADR-005's contract is what stops a
finish date being reported off an empty cost table. None of that is moving.

What IS available, licence-clean and verified, is the three-day domain rotation
already implemented in `core/domains.py`. docs/GOAL_SPEC_SEED_TEAM.md section
5.1 records its absence from the roadmap as the single biggest practical
omission: follow a plan that ignores it and you spend resin on a day the domain
is not dropping what you need.

HOW THESE ARMS AVOID AGREEING WITH THEMSELVES. Not one assertion below retypes
the rotation table. Every expectation is computed by calling
`core.domains.is_available` and `core.domains.next_available_day`, so a wrong
table in the module cannot be matched by a wrong table in the test. The weekday
itself comes from `core.domains.current_game_day`, which is the same 04:00
boundary the panel keys on rather than the wall clock.

The licence arm - state stays PARTIAL, the cost text stays present - is not
decoration. Without it a later session could add these rows, notice the panel
now says something useful, and quietly promote it to READY. That is precisely
the failure ADR-005 exists to prevent.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core import domains
from core.types import AccountState, MappedCharacter
from surface.model import Panel, PanelState, build_dashboard

# A full week of consecutive dates, so every weekday is exercised and no arm
# depends on which day of the week the suite happens to run. 19:30 sits well
# clear of the 04:00 game-day boundary in both directions, so the game day and
# the calendar date agree and a reader can check these by eye. The arms still
# derive the weekday through `current_game_day` rather than assuming that.
WEEK = tuple(datetime(2026, 9, day, 19, 30, tzinfo=UTC) for day in range(7, 14))
MONDAY_NOW, TUESDAY_NOW = WEEK[0], WEEK[1]
SUNDAY_NOW = WEEK[6]

OPEN_LABEL = "Farmable today"
WAIT_SUFFIX = "opens in"


def _account() -> AccountState:
    """An account with exactly enough roster for the panel to reach PARTIAL.

    With an empty roster the Plan panel is NOT_WIRED, and a NOT_WIRED panel may
    carry no rows at all - so a rotation arm run against an empty account would
    be asserting about a panel that is not the one under test.
    """
    state = AccountState(uid="000000000")
    state.roster = (
        MappedCharacter(
            avatar_id=10000096,
            level=60,
            ascension=3,
            constellations=0,
            display_name="Arlecchino",
        ),
    )
    return state


def _plan_panel(now: datetime) -> Panel:
    return build_dashboard(_account(), now=now).panel("plan")


def _rows(now: datetime) -> dict[str, str]:
    return dict(_plan_panel(now).rows)


def _game_weekday(now: datetime) -> int:
    return domains.current_game_day(now).weekday()


def _open_slots(now: datetime) -> set[str]:
    """The slot tokens the panel says are farmable, as an exact-token set.

    Split rather than substring-matched: `"slot 0" in "slot 0, slot 2"` is true
    for the wrong reason as well as the right one, and a substring arm would
    survive a renderer that emitted every slot on every day.
    """
    value = _rows(now)[OPEN_LABEL]
    if value.strip().lower() == "none":
        return set()
    return {token.strip() for token in value.split(",") if token.strip()}


def _wait_label(slot: int) -> str:
    return f"Slot {slot} {WAIT_SUFFIX}"


# ---------------------------------------------------------------------------
# Arm 1 - availability tracks the rotation, on every weekday and every slot
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("now", WEEK, ids=lambda n: n.date().isoformat())
@pytest.mark.parametrize("slot", domains.ROTATION_SLOTS)
def test_a_slot_reads_open_exactly_when_core_domains_says_it_is(now: datetime, slot: int) -> None:
    """21 cases: 7 consecutive days by 3 slots, the whole rotation surface.

    The expectation is `domains.is_available`'s answer, never a literal. If the
    panel and the module disagree on any one of the 21 the arm fails, and it
    cannot pass by both being wrong in the same way.
    """
    expected = domains.is_available(slot, _game_weekday(now))
    assert (f"slot {slot}" in _open_slots(now)) is expected


@pytest.mark.parametrize("now", WEEK, ids=lambda n: n.date().isoformat())
@pytest.mark.parametrize("slot", domains.ROTATION_SLOTS)
def test_an_unavailable_slot_carries_the_wait_core_domains_computes(now: datetime, slot: int) -> None:
    """A closed slot must say how long until it opens, and say the true number.

    "Not today" alone is not actionable - the whole point of surfacing the
    rotation is that the operator can see whether to wait one day or three.
    """
    weekday = _game_weekday(now)
    rows = _rows(now)
    label = _wait_label(slot)
    if domains.is_available(slot, weekday):
        assert label not in rows, "an open slot must not also advertise a wait"
        return
    expected = domains.next_available_day(slot, weekday)
    assert expected >= 1, "a slot that is not available today cannot open in zero days"
    assert label in rows
    assert rows[label].split()[0] == str(expected)


# ---------------------------------------------------------------------------
# Arm 2 - the Sunday property, which bounds every wait the panel can print
# ---------------------------------------------------------------------------


def test_sunday_opens_every_slot_so_the_panel_prints_no_wait_at_all() -> None:
    """Sunday is in every slot's row, which is why no slot is ever far out."""
    weekday = _game_weekday(SUNDAY_NOW)
    assert all(domains.is_available(slot, weekday) for slot in domains.ROTATION_SLOTS)
    rows = _rows(SUNDAY_NOW)
    assert _open_slots(SUNDAY_NOW) == {f"slot {slot}" for slot in domains.ROTATION_SLOTS}
    assert not [label for label in rows if label.endswith(WAIT_SUFFIX)]


@pytest.mark.parametrize("now", WEEK, ids=lambda n: n.date().isoformat())
def test_no_wait_the_panel_prints_can_ever_exceed_six_days(now: datetime) -> None:
    """The bound is a consequence of Sunday, not a separate rule.

    Sunday appears in all three rows, so from any weekday some qualifying day is
    at most six away. A printed wait of seven or more would mean the panel had
    stopped deriving from the table.
    """
    weekday = _game_weekday(now)
    rows = _rows(now)
    printed = [int(value.split()[0]) for label, value in rows.items() if label.endswith(WAIT_SUFFIX)]
    assert all(1 <= days <= 6 for days in printed), printed
    assert printed == [
        domains.next_available_day(slot, weekday)
        for slot in domains.ROTATION_SLOTS
        if not domains.is_available(slot, weekday)
    ]


# ---------------------------------------------------------------------------
# Arm 3 - the licence guard. Adding capability must not move the gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("now", WEEK, ids=lambda n: n.date().isoformat())
def test_the_panel_stays_partial_and_keeps_naming_the_empty_cost_table(now: datetime) -> None:
    """Rotation rows are a capability, not a closing of ADR-002's gate.

    The rotation says WHEN a domain drops. It says nothing about HOW MUCH of
    anything a goal needs, so the cost table is exactly as absent as it was and
    the panel must go on saying so.
    """
    panel = _plan_panel(now)
    assert panel.state is PanelState.PARTIAL
    assert "cost" in panel.waiting_on.lower()
    assert "ADR-002" in panel.waiting_on


@pytest.mark.parametrize("now", WEEK, ids=lambda n: n.date().isoformat())
def test_no_rotation_row_smuggles_in_a_material_or_mora_figure(now: datetime) -> None:
    """The only integers these rows may carry are a slot id and a day count.

    A cost figure reaching this panel is the failure the gate exists to stop,
    and it would arrive looking exactly like a helpful extra row.
    """
    rows = _rows(now)
    rotation = {k: v for k, v in rows.items() if k == OPEN_LABEL or k.endswith(WAIT_SUFFIX)}
    assert rotation, "the panel carries no rotation rows to check"
    for value in rotation.values():
        for token in value.replace(",", " ").split():
            if token.isdigit():
                assert int(token) <= 6, f"unexpected magnitude in a rotation row: {value}"


# ---------------------------------------------------------------------------
# Arm 4 - the control. Without this, arms 1-3 could pass against a static panel.
# ---------------------------------------------------------------------------


def test_the_rotation_rows_actually_change_between_two_different_weekdays() -> None:
    """Proof the panel reads `now` at all.

    The disagreement between the two dates is asserted through
    `domains.is_available` FIRST, so the control cannot silently become vacuous
    if the rotation table is ever changed underneath it.
    """
    monday, tuesday = _game_weekday(MONDAY_NOW), _game_weekday(TUESDAY_NOW)
    assert monday != tuesday
    assert any(
        domains.is_available(slot, monday) != domains.is_available(slot, tuesday)
        for slot in domains.ROTATION_SLOTS
    ), "the control dates must differ in the rotation, or it measures nothing"
    assert _plan_panel(MONDAY_NOW).rows != _plan_panel(TUESDAY_NOW).rows
    assert _open_slots(MONDAY_NOW) != _open_slots(TUESDAY_NOW)


def test_the_pre_existing_plan_rows_are_untouched_by_the_rotation_rows() -> None:
    """The survival half of the sweep.

    A change that scored full marks on every arm above by replacing the panel's
    rows outright would have deleted the DAG rows this panel already carried.
    """
    rows = _rows(MONDAY_NOW)
    assert "Goal" in rows
    assert "Steps in the graph" in rows
    assert int(rows["Steps in the graph"]) > 0
