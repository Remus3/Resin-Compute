"""Tests for the resolution-path scheduler.

The scheduler earns its existence only if it beats the naive resin quotient, so
the central assertions here are comparative: the SAME path with and without a
gate, and the gated answer must be strictly worse. A test that only asserted
"returns some tasks" would pass against a scheduler that ignored every gate.
"""
from __future__ import annotations

import pytest

from core.types import ObjectiveKind, ObjectiveNode, ResolutionPath, TaskCadence
from engines.scheduler import (
    MAX_SCHEDULE_ITERATIONS,
    WEEKLY_WINDOW_DAYS,
    UnknownScheduleNodeError,
    estimated_days,
    naive_days,
    plan,
    schedule,
    solve,
)

SUBJECT = 10000096

# A weekday set no calendar can satisfy - 0..6 are the only real weekdays.
# Used to force the unreachable branch without relying on a resin argument.
IMPOSSIBLE_WEEKDAYS = (9,)


def node(
    node_id: str,
    *,
    resin: int = 0,
    weekdays: tuple[int, ...] = (),
    weekly: bool = False,
    name: str = "",
) -> ObjectiveNode:
    return ObjectiveNode(
        node_id=node_id,
        kind=ObjectiveKind.CHARACTER_ASCENSION,
        subject_id=SUBJECT,
        target_value=1,
        resin_cost=resin,
        available_weekdays=weekdays,
        weekly_capped=weekly,
        display_name=name,
    )


def path_over(nodes: tuple[ObjectiveNode, ...]) -> ResolutionPath:
    return ResolutionPath(
        goal_id=nodes[-1].node_id,
        ordered_nodes=tuple(n.node_id for n in nodes),
        total_resin=sum(n.resin_cost for n in nodes),
        total_mora=sum(n.mora_cost for n in nodes),
    )


# ---------------------------------------------------------------------------
# Weekday rotation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("start_weekday", list(range(7)))
def test_a_node_gated_to_tuesday_and_friday_is_never_placed_on_a_monday(start_weekday):
    nodes = (node("domain", resin=20, weekdays=(1, 4)),)
    tasks = schedule(path_over(nodes), nodes, start_weekday=start_weekday, resin_on_hand=200)
    assert len(tasks) == 1
    weekday = (start_weekday + tasks[0].earliest_day) % 7
    assert weekday in (1, 4), f"placed on weekday {weekday} from start {start_weekday}"
    assert weekday != 0


def test_weekday_gate_placement_is_the_first_open_day():
    nodes = (node("domain", resin=20, weekdays=(1, 4)),)
    # Starting Monday (0), the first open day is Tuesday, one day out.
    tasks = schedule(path_over(nodes), nodes, start_weekday=0, resin_on_hand=200)
    assert tasks[0].earliest_day == 1
    # Starting Wednesday (2), the first open day is Friday, two days out.
    tasks = schedule(path_over(nodes), nodes, start_weekday=2, resin_on_hand=200)
    assert tasks[0].earliest_day == 2


def test_an_ungated_node_goes_out_on_day_zero_when_resin_is_banked():
    nodes = (node("anyday", resin=20),)
    tasks = schedule(path_over(nodes), nodes, resin_on_hand=200)
    assert tasks[0].earliest_day == 0


# ---------------------------------------------------------------------------
# The property that justifies the module
# ---------------------------------------------------------------------------


def test_estimated_days_exceeds_the_naive_quotient_when_a_weekday_gate_binds():
    # Resin is deliberately NOT the binding constraint: one node, one day's
    # worth of resin, already banked. Only the gate can move the answer.
    gated = (node("thursday_only", resin=180, weekdays=(4,)),)
    ungated = (node("thursday_only", resin=180),)
    gated_path = path_over(gated)

    naive = naive_days(gated_path, resin_per_day=180)
    assert naive == 1

    control = estimated_days(path_over(ungated), ungated, resin_per_day=180, start_weekday=0, resin_on_hand=180)
    gated_answer = estimated_days(gated_path, gated, resin_per_day=180, start_weekday=0, resin_on_hand=180)

    assert control == naive, "without a gate the scheduler must match the naive bound"
    assert gated_answer > naive, f"gate did not bind: {gated_answer} vs naive {naive}"
    assert gated_answer == 5  # Monday start, first Thursday is day 4, so 5 days


def test_estimated_days_exceeds_the_naive_quotient_when_a_weekly_lockout_binds():
    weekly = (
        node("boss_a", resin=90, weekly=True),
        node("boss_b", resin=90, weekly=True),
    )
    unlocked = (node("boss_a", resin=90), node("boss_b", resin=90))
    weekly_path = path_over(weekly)

    naive = naive_days(weekly_path, resin_per_day=180)
    assert naive == 1

    control = estimated_days(path_over(unlocked), unlocked, resin_per_day=180, resin_on_hand=180)
    answer = estimated_days(weekly_path, weekly, resin_per_day=180, resin_on_hand=180)

    assert control == naive
    assert answer > naive, f"weekly lockout did not bind: {answer} vs naive {naive}"
    assert answer == WEEKLY_WINDOW_DAYS + 1


def test_resin_accrual_alone_pushes_past_day_zero():
    nodes = (node("costly", resin=100), node("costlier", resin=100))
    tasks = schedule(path_over(nodes), nodes, resin_per_day=180, resin_on_hand=0)
    # Day 0 has nothing banked; day 1 has 180, enough for one; the second waits.
    assert [task.earliest_day for task in tasks] == [1, 2]


# ---------------------------------------------------------------------------
# Weekly lockout
# ---------------------------------------------------------------------------


def test_weekly_capped_nodes_are_at_most_one_per_seven_days():
    nodes = (
        node("boss_a", weekly=True),
        node("boss_b", weekly=True),
        node("boss_c", weekly=True),
    )
    tasks = schedule(path_over(nodes), nodes, resin_on_hand=1000)
    days = [task.earliest_day for task in tasks]
    assert days == [0, 7, 14]
    for earlier, later in zip(days, days[1:]):
        assert later - earlier >= WEEKLY_WINDOW_DAYS
    # Any 7-day window holds at most one of them.
    for window_start in range(0, 21):
        in_window = [day for day in days if window_start <= day < window_start + WEEKLY_WINDOW_DAYS]
        assert len(in_window) <= 1, f"window starting {window_start} holds {in_window}"


def test_the_weekly_slot_budget_is_a_knob_not_an_assumption():
    nodes = (node("boss_a", weekly=True), node("boss_b", weekly=True), node("boss_c", weekly=True))
    tasks = schedule(path_over(nodes), nodes, resin_on_hand=1000, weekly_slots_per_window=3)
    assert [task.earliest_day for task in tasks] == [0, 0, 0]


def test_uncapped_nodes_are_unaffected_by_the_weekly_window():
    nodes = (node("a"), node("b"), node("c"))
    tasks = schedule(path_over(nodes), nodes)
    assert [task.earliest_day for task in tasks] == [0, 0, 0]


# ---------------------------------------------------------------------------
# Unreachable, bounded
# ---------------------------------------------------------------------------


def test_an_unsatisfiable_gate_terminates_and_reports_blocked_on():
    nodes = (node("never_opens", resin=20, weekdays=IMPOSSIBLE_WEEKDAYS), node("after_it", resin=20))
    resolved = plan(path_over(nodes), nodes, horizon_days=30, resin_on_hand=1000)
    assert resolved.tasks == ()
    assert resolved.blocked_on == ("never_opens", "after_it")
    assert resolved.estimated_days == 30


def test_a_weekly_chain_that_overruns_the_horizon_blocks_the_tail():
    nodes = (
        node("boss_a", weekly=True),
        node("boss_b", weekly=True),
        node("boss_c", weekly=True),
    )
    resolved = plan(path_over(nodes), nodes, horizon_days=5, resin_on_hand=1000)
    assert [task.node_id for task in resolved.tasks] == ["boss_a"]
    assert resolved.blocked_on == ("boss_b", "boss_c")


def test_the_search_is_hard_bounded():
    nodes = (node("never_opens", weekdays=IMPOSSIBLE_WEEKDAYS),)
    outcome = solve(path_over(nodes), nodes, horizon_days=365)
    assert outcome.blocked_on == ("never_opens",)
    assert outcome.exhausted is False
    # One probe per day of the horizon, and never more than the hard ceiling.
    assert outcome.iterations <= 366
    assert outcome.iterations <= MAX_SCHEDULE_ITERATIONS


def test_zero_regeneration_with_unaffordable_cost_blocks_rather_than_spins():
    nodes = (node("unaffordable", resin=500),)
    outcome = solve(path_over(nodes), nodes, resin_per_day=0, resin_on_hand=10, horizon_days=365)
    assert outcome.blocked_on == ("unaffordable",)
    # It gave up on the first probe instead of walking the whole horizon.
    assert outcome.iterations == 1


# ---------------------------------------------------------------------------
# Task shape and argument validation
# ---------------------------------------------------------------------------


def test_task_fields_are_populated():
    nodes = (node("ascend", resin=20, name="fixture ascension"),)
    task = schedule(path_over(nodes), nodes, resin_on_hand=100)[0]
    assert task.node_id == "ascend"
    assert task.task_id == "task:ascend:d0"
    assert task.resin_cost == 20
    assert task.description == "fixture ascension"
    assert task.earliest_day == 0


def test_cadence_reflects_the_node_shape():
    nodes = (node("weekly_one", resin=30, weekly=True), node("daily_one", resin=20), node("free_one"))
    tasks = {task.node_id: task for task in schedule(path_over(nodes), nodes, resin_on_hand=1000)}
    assert tasks["weekly_one"].cadence is TaskCadence.WEEKLY
    assert tasks["daily_one"].cadence is TaskCadence.DAILY
    assert tasks["free_one"].cadence is TaskCadence.ON_DEMAND


def test_scheduling_preserves_path_order():
    nodes = tuple(node(f"n{i}", resin=90) for i in range(5))
    tasks = schedule(path_over(nodes), nodes, resin_on_hand=1000)
    assert [task.node_id for task in tasks] == [n.node_id for n in nodes]
    days = [task.earliest_day for task in tasks]
    assert days == sorted(days)


def test_plan_fills_the_schedule_fields_and_leaves_the_dag_fields_alone():
    nodes = (node("a", resin=20), node("b", resin=20))
    original = path_over(nodes)
    resolved = plan(original, nodes, resin_on_hand=100)
    assert resolved.goal_id == original.goal_id
    assert resolved.ordered_nodes == original.ordered_nodes
    assert resolved.total_resin == original.total_resin
    assert len(resolved.tasks) == 2
    assert resolved.estimated_days == 1
    assert resolved.blocked_on == ()
    # The input path is frozen and untouched.
    assert original.tasks == ()


def test_an_empty_path_is_a_zero_day_plan():
    empty = ResolutionPath(goal_id="none")
    assert schedule(empty, ()) == ()
    assert estimated_days(empty, ()) == 0
    assert naive_days(empty) == 0


def test_a_path_referencing_an_unknown_node_raises():
    with pytest.raises(UnknownScheduleNodeError):
        schedule(ResolutionPath(goal_id="ghost", ordered_nodes=("ghost",)), ())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"resin_per_day": -1},
        {"resin_on_hand": -1},
        {"horizon_days": -1},
        {"weekly_slots_per_window": 0},
        {"start_weekday": 7},
        {"start_weekday": -1},
    ],
)
def test_invalid_arguments_are_rejected(kwargs):
    nodes = (node("a"),)
    with pytest.raises(ValueError):
        schedule(path_over(nodes), nodes, **kwargs)


def test_naive_days_requires_positive_regeneration():
    nodes = (node("a", resin=10),)
    with pytest.raises(ValueError):
        naive_days(path_over(nodes), resin_per_day=0)


def test_nodes_may_be_supplied_as_a_mapping():
    nodes = (node("a", resin=20),)
    as_map = {n.node_id: n for n in nodes}
    assert schedule(path_over(nodes), as_map, resin_on_hand=100)[0].node_id == "a"
