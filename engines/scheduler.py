"""Resolution-path scheduler - turns an ordered path into dated tasks.

Three constraints bind, and they bind independently. A plan that models only
the first is the naive resin quotient, and it is always optimistic:

1. **Resin generation.** Resin accrues at `resin_per_day` and is spent by
   tasks. A node cannot run before enough has accumulated.
2. **Weekday rotation.** A node with a non-empty `available_weekdays` runs only
   on those weekdays. A node whose domain opens Tuesday and Friday cannot be
   run on a Monday no matter how much resin is banked.
3. **Weekly lockout.** A `weekly_capped` node consumes a weekly slot, and a new
   one cannot be taken until the window has rolled.

STATED ASSUMPTIONS:

- **Day 0 is the start day** and its weekday is `start_weekday`. Weekday
  numbering is Python's: Monday is 0, Sunday is 6.
- **Resin available on day d is** `resin_on_hand + resin_per_day * d - spent`.
  Accrual is modelled per whole day; this scheduler does not model the resin
  cap, because a cap only ever makes the schedule LONGER and a planner that
  reports an optimistic date is worse than one that omits a refinement.
- **The weekly cap is enforced two ways** - per node, and as a global slot
  budget of `weekly_slots_per_window` per rolling 7-day window. The per-node
  half is the literal contract. The global half is what actually binds, since a
  path executes each node once, and it is tunable rather than assumed: raise it
  to disable.
- **Ordering follows the path.** `ResolutionPath.ordered_nodes` is already
  topological, so scheduling in that order and never moving the cursor
  backwards satisfies every dependency by construction.
- **Unreachable is a result, not a hang.** Every search is bounded twice, by
  `horizon_days` and by a hard iteration ceiling, and a node that fits neither
  lands in `blocked_on`.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

from core.types import ObjectiveNode, ResolutionPath, ScheduledTask, TaskCadence

__all__ = [
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_RESIN_PER_DAY",
    "MAX_SCHEDULE_ITERATIONS",
    "WEEKLY_WINDOW_DAYS",
    "ScheduleOutcome",
    "UnknownScheduleNodeError",
    "estimated_days",
    "naive_days",
    "plan",
    "schedule",
    "solve",
]

#: Full daily resin regeneration, matching `IncomeVelocity.resin_per_day`.
DEFAULT_RESIN_PER_DAY: int = 180

#: How far ahead a plan is allowed to look before declaring a node blocked.
DEFAULT_HORIZON_DAYS: int = 365

#: Length of the rolling weekly-lockout window, in days.
WEEKLY_WINDOW_DAYS: int = 7

#: Absolute ceiling on day-probe iterations for one call. This exists so a
#: pathological input terminates even if the horizon arithmetic is wrong.
MAX_SCHEDULE_ITERATIONS: int = 1_000_000

DAYS_PER_WEEK: int = 7


class UnknownScheduleNodeError(KeyError):
    """The path references a node id absent from the supplied node set."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"path references unknown node id: {node_id}")


@dataclass(frozen=True)
class ScheduleOutcome:
    """Everything one scheduling run produced.

    Kept separate from `ResolutionPath` so the three public entry points can
    share one solve without any of them recomputing it.
    """

    tasks: tuple[ScheduledTask, ...] = ()
    blocked_on: tuple[str, ...] = ()
    horizon: int = 0
    iterations: int = 0
    exhausted: bool = False


def _as_index(nodes: Iterable[ObjectiveNode] | Mapping[str, ObjectiveNode]) -> dict[str, ObjectiveNode]:
    if isinstance(nodes, Mapping):
        return dict(nodes)
    return {node.node_id: node for node in nodes}


def _cadence_of(node: ObjectiveNode) -> TaskCadence:
    """Classify a node for display.

    A weekly-capped node is WEEKLY. A node that burns resin is DAILY farmable
    work. Anything left costs no resin and is not gated, so it is ON_DEMAND -
    the crafting or spending step at the end of a chain.
    """
    if node.weekly_capped:
        return TaskCadence.WEEKLY
    if node.resin_cost > 0:
        return TaskCadence.DAILY
    return TaskCadence.ON_DEMAND


def _weekday_of(day: int, start_weekday: int) -> int:
    return (start_weekday + day) % DAYS_PER_WEEK


def solve(
    path: ResolutionPath,
    nodes: Iterable[ObjectiveNode] | Mapping[str, ObjectiveNode],
    resin_per_day: int = DEFAULT_RESIN_PER_DAY,
    start_weekday: int = 0,
    resin_on_hand: int = 0,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    weekly_slots_per_window: int = 1,
) -> ScheduleOutcome:
    """The one solve behind `schedule`, `estimated_days` and `plan`.

    Public because it is the only view that exposes `iterations` and
    `exhausted`, which is how a caller - or a test - proves the search really
    is bounded rather than trusting that it is.
    """
    if resin_per_day < 0:
        raise ValueError(f"resin_per_day cannot be negative, got {resin_per_day}")
    if resin_on_hand < 0:
        raise ValueError(f"resin_on_hand cannot be negative, got {resin_on_hand}")
    if horizon_days < 0:
        raise ValueError(f"horizon_days cannot be negative, got {horizon_days}")
    if weekly_slots_per_window < 1:
        raise ValueError(f"weekly_slots_per_window must be at least 1, got {weekly_slots_per_window}")
    if not 0 <= start_weekday < DAYS_PER_WEEK:
        raise ValueError(f"start_weekday must be 0..6, got {start_weekday}")

    index = _as_index(nodes)

    tasks: list[ScheduledTask] = []
    blocked: list[str] = []
    spent = 0
    cursor = 0
    weekly_days: list[int] = []
    per_node_days: dict[str, int] = {}
    iterations = 0
    exhausted = False

    # Two independent bounds. The horizon bounds each search; this bounds the
    # whole call, so a bad horizon still cannot spin forever.
    ceiling = min(
        MAX_SCHEDULE_ITERATIONS,
        (horizon_days + 1) * (len(path.ordered_nodes) + 1) + DAYS_PER_WEEK,
    )

    for position, node_id in enumerate(path.ordered_nodes):
        node = index.get(node_id)
        if node is None:
            raise UnknownScheduleNodeError(node_id)

        placed_day: int | None = None
        day = cursor
        while day <= horizon_days:
            iterations += 1
            if iterations > ceiling:
                exhausted = True
                break

            if node.available_weekdays and _weekday_of(day, start_weekday) not in node.available_weekdays:
                day += 1
                continue

            available = resin_on_hand + resin_per_day * day - spent
            if node.resin_cost > available:
                if resin_per_day == 0:
                    break
                day += 1
                continue

            if node.weekly_capped:
                previous = per_node_days.get(node_id)
                if previous is not None and day - previous < WEEKLY_WINDOW_DAYS:
                    day += 1
                    continue
                in_window = sum(1 for taken in weekly_days if day - taken < WEEKLY_WINDOW_DAYS)
                if in_window >= weekly_slots_per_window:
                    day += 1
                    continue

            placed_day = day
            break

        if placed_day is None:
            # Unreachable inside the budget. Everything still unplaced is
            # reported rather than retried - the path is ordered, so a node the
            # planner could not place blocks the tail behind it.
            blocked.extend(path.ordered_nodes[position:])
            break

        spent += node.resin_cost
        cursor = placed_day
        per_node_days[node_id] = placed_day
        if node.weekly_capped:
            weekly_days.append(placed_day)

        tasks.append(
            ScheduledTask(
                task_id=f"task:{node_id}:d{placed_day}",
                node_id=node_id,
                cadence=_cadence_of(node),
                resin_cost=node.resin_cost,
                earliest_day=placed_day,
                description=node.display_name or node_id,
            )
        )

    if blocked:
        horizon = horizon_days
    elif tasks:
        horizon = max(task.earliest_day for task in tasks) + 1
    else:
        horizon = 0

    return ScheduleOutcome(
        tasks=tuple(tasks),
        blocked_on=tuple(dict.fromkeys(blocked)),
        horizon=horizon,
        iterations=iterations,
        exhausted=exhausted,
    )


def schedule(
    path: ResolutionPath,
    nodes: Iterable[ObjectiveNode] | Mapping[str, ObjectiveNode],
    resin_per_day: int = DEFAULT_RESIN_PER_DAY,
    start_weekday: int = 0,
    resin_on_hand: int = 0,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    weekly_slots_per_window: int = 1,
) -> tuple[ScheduledTask, ...]:
    """Place every node of `path` on a day, earliest-first.

    `earliest_day` is a 0-based offset from the start day, and it respects all
    three constraints - so a node gated to Tuesday and Friday is never returned
    on a Monday even when resin is banked and its dependencies are done.

    Nodes that do not fit inside `horizon_days` are simply absent from the
    result. Call `plan` instead when the caller needs to know WHICH ones.
    """
    return solve(
        path,
        nodes,
        resin_per_day=resin_per_day,
        start_weekday=start_weekday,
        resin_on_hand=resin_on_hand,
        horizon_days=horizon_days,
        weekly_slots_per_window=weekly_slots_per_window,
    ).tasks


def estimated_days(
    path: ResolutionPath,
    nodes: Iterable[ObjectiveNode] | Mapping[str, ObjectiveNode],
    resin_per_day: int = DEFAULT_RESIN_PER_DAY,
    start_weekday: int = 0,
    resin_on_hand: int = 0,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    weekly_slots_per_window: int = 1,
) -> int:
    """Days needed to finish the path, gates included.

    This is GREATER than `naive_days` whenever a weekday gate or a weekly
    lockout binds, which is the entire reason the scheduler exists. When part
    of the path could not be placed the answer is the full horizon, since the
    budget was spent without finishing.
    """
    return solve(
        path,
        nodes,
        resin_per_day=resin_per_day,
        start_weekday=start_weekday,
        resin_on_hand=resin_on_hand,
        horizon_days=horizon_days,
        weekly_slots_per_window=weekly_slots_per_window,
    ).horizon


def naive_days(path: ResolutionPath, resin_per_day: int = DEFAULT_RESIN_PER_DAY) -> int:
    """The resin-only lower bound - `ceil(total_resin / resin_per_day)`.

    Exposed so callers and tests compare against the SAME definition the
    scheduler is claimed to beat, rather than an ad hoc one.
    """
    if resin_per_day <= 0:
        raise ValueError(f"resin_per_day must be positive, got {resin_per_day}")
    if path.total_resin <= 0:
        return 0
    return -(-path.total_resin // resin_per_day)


def plan(
    path: ResolutionPath,
    nodes: Iterable[ObjectiveNode] | Mapping[str, ObjectiveNode],
    resin_per_day: int = DEFAULT_RESIN_PER_DAY,
    start_weekday: int = 0,
    resin_on_hand: int = 0,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    weekly_slots_per_window: int = 1,
) -> ResolutionPath:
    """Return the path with `tasks`, `estimated_days` and `blocked_on` filled.

    This is the entry point that answers the unreachable case honestly: a node
    that cannot be placed inside the horizon lands in `blocked_on` together
    with the tail it holds up, and the call returns instead of looping.
    """
    outcome = solve(
        path,
        nodes,
        resin_per_day=resin_per_day,
        start_weekday=start_weekday,
        resin_on_hand=resin_on_hand,
        horizon_days=horizon_days,
        weekly_slots_per_window=weekly_slots_per_window,
    )
    return replace(
        path,
        tasks=outcome.tasks,
        estimated_days=outcome.horizon,
        blocked_on=outcome.blocked_on,
    )
