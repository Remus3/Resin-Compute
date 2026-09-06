"""Objective DAG engine - mechanism only, no game data.

This module answers four questions about a set of goal nodes:

1. Is the goal set well formed - does every dependency id resolve, and is the
   graph acyclic (`build_graph`)?
2. In what order may the nodes be executed (`topological_order`)?
3. What does ONE goal actually cost, transitively (`critical_path`)?
4. Given what is already done, what still blocks it (`unmet_prerequisites`)?

Plus one decomposition helper, `expand_character_goal`, which turns a
high-level intent such as "character to level 60, talents 6/6/6, weapon at 60"
into the node set with the real dependency edges wired.

STATED ASSUMPTIONS - read before extending:

- **No material quantities are invented here.** `MaterialCost`, mora, resin,
  weekday gates and weekly caps all arrive from the caller as a `NodeCost`
  mapping whose documented default is EMPTY. Real costs are data and are owned
  by the ingest slice, not by this engine.
- **The level cap table is pinned by the spec:** ascension phases 0..6 unlock
  level caps 20/40/50/60/70/80/90 - see `ASCENSION_LEVEL_CAPS`.
- **The talent gate is only partly pinned.** The contract fixes exactly two
  points: any talent level above 1 requires ascension, and talent level 10
  requires ascension 6. The levels in between are NOT pinned by any verified
  source available to this slice, so `min_ascension_for_talent` derives them by
  a monotone ceiling interpolation between those two fixed points and every
  caller may override the two endpoints. It is deliberately a formula rather
  than a hand-written table so that no unverified per-level number is smuggled
  in as if it were fact.
- **Weapon level caps default to the same table as characters** and are
  overridable through the `level_caps` parameter for the same reason.
"""
from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from core.types import MaterialCost, ObjectiveKind, ObjectiveNode, ResolutionPath

__all__ = [
    "ASCENSION_LEVEL_CAPS",
    "MAX_ASCENSION_PHASE",
    "MAX_TALENT_LEVEL",
    "MIN_TALENT_LEVEL",
    "TALENT_MAX_ASCENSION",
    "TALENT_MIN_ASCENSION",
    "CyclicObjectiveError",
    "DuplicateObjectiveError",
    "NodeCost",
    "ObjectiveGraph",
    "ObjectiveGraphError",
    "UnknownDependencyError",
    "UnknownObjectiveError",
    "build_graph",
    "character_ascension_id",
    "character_level_id",
    "critical_path",
    "expand_character_goal",
    "min_ascension_for_talent",
    "required_ascension_for_level",
    "talent_id",
    "topological_order",
    "unmet_prerequisites",
    "weapon_ascension_id",
    "weapon_level_id",
]

# ---------------------------------------------------------------------------
# Pinned constants
# ---------------------------------------------------------------------------

#: Level cap unlocked by each ascension phase. Index IS the phase, so phase 0
#: caps the subject at 20 and phase 6 caps it at 90. Pinned by the contract.
ASCENSION_LEVEL_CAPS: tuple[int, ...] = (20, 40, 50, 60, 70, 80, 90)

#: Highest ascension phase, derived from the cap table so the two cannot drift.
MAX_ASCENSION_PHASE: int = len(ASCENSION_LEVEL_CAPS) - 1

MIN_TALENT_LEVEL: int = 1
MAX_TALENT_LEVEL: int = 10

#: Talent levels above `MIN_TALENT_LEVEL` require at least this ascension.
TALENT_MIN_ASCENSION: int = 1
#: Talent level `MAX_TALENT_LEVEL` requires this ascension.
TALENT_MAX_ASCENSION: int = 6


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ObjectiveGraphError(ValueError):
    """Base class for every malformed-graph condition."""


class DuplicateObjectiveError(ObjectiveGraphError):
    """Two nodes in one set share a node_id."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"duplicate objective id: {node_id}")


class UnknownDependencyError(ObjectiveGraphError):
    """A node depends on an id that is not present in the node set."""

    def __init__(self, node_id: str, missing_id: str) -> None:
        self.node_id = node_id
        self.missing_id = missing_id
        super().__init__(f"objective {node_id} depends on unknown id {missing_id}")


class UnknownObjectiveError(ObjectiveGraphError):
    """A goal id was requested that is not present in the node set."""

    def __init__(self, goal_id: str) -> None:
        self.goal_id = goal_id
        super().__init__(f"unknown objective id: {goal_id}")


class CyclicObjectiveError(ObjectiveGraphError):
    """The dependency graph contains a cycle.

    The message names the ACTUAL members of the cycle in traversal order, with
    the entry node repeated at the end so the loop closes visibly. A bare
    "cycle detected" is useless to whoever has to fix the data.
    """

    def __init__(self, cycle: Sequence[str]) -> None:
        self.cycle: tuple[str, ...] = tuple(cycle)
        if self.cycle:
            body = " -> ".join(self.cycle)
        else:
            body = "<empty>"
        super().__init__(f"cyclic objective dependency: {body}")


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObjectiveGraph:
    """A validated, acyclic view over one objective node set.

    `dependents` is the reversed edge set. It is materialized here because the
    recommendation engine scores a goal partly on how many other goals it
    unblocks, and recomputing that per candidate would be quadratic.
    """

    nodes: dict[str, ObjectiveNode]
    dependents: dict[str, tuple[str, ...]]
    order: tuple[str, ...]

    def __contains__(self, node_id: object) -> bool:
        return node_id in self.nodes

    def __len__(self) -> int:
        return len(self.nodes)

    def dependencies_of(self, node_id: str) -> tuple[str, ...]:
        """Direct dependencies of one node, deduplicated and sorted."""
        if node_id not in self.nodes:
            raise UnknownObjectiveError(node_id)
        return tuple(sorted(set(self.nodes[node_id].depends_on)))

    def dependents_of(self, node_id: str) -> tuple[str, ...]:
        """Direct dependents of one node, sorted."""
        if node_id not in self.nodes:
            raise UnknownObjectiveError(node_id)
        return self.dependents.get(node_id, ())

    def transitive_dependents(self, node_id: str) -> tuple[str, ...]:
        """Every node that is blocked, directly or indirectly, by this one."""
        if node_id not in self.nodes:
            raise UnknownObjectiveError(node_id)
        seen: set[str] = set()
        stack = list(self.dependents.get(node_id, ()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.dependents.get(current, ()))
        return tuple(sorted(seen))


def _index(nodes: Iterable[ObjectiveNode]) -> dict[str, ObjectiveNode]:
    """Index a node iterable by id, rejecting duplicates."""
    index: dict[str, ObjectiveNode] = {}
    for node in nodes:
        if node.node_id in index:
            raise DuplicateObjectiveError(node.node_id)
        index[node.node_id] = node
    return index


def _validate_dependencies(index: Mapping[str, ObjectiveNode]) -> None:
    """Assert every dependency id resolves inside the same node set."""
    for node_id in sorted(index):
        for dep in index[node_id].depends_on:
            if dep not in index:
                raise UnknownDependencyError(node_id, dep)


def _reverse_edges(index: Mapping[str, ObjectiveNode]) -> dict[str, tuple[str, ...]]:
    collected: dict[str, list[str]] = {node_id: [] for node_id in index}
    for node_id in sorted(index):
        for dep in sorted(set(index[node_id].depends_on)):
            collected[dep].append(node_id)
    return {node_id: tuple(sorted(children)) for node_id, children in collected.items()}


def _find_cycle(index: Mapping[str, ObjectiveNode]) -> tuple[str, ...]:
    """Return one concrete cycle as a path, entry node repeated at the end.

    Iterative depth-first search with a three-colour marking. Roots and edges
    are both walked in sorted order, so the cycle reported for a given input is
    always the same one - a nondeterministic error message is nearly as bad as
    no message.
    """
    white, grey, black = 0, 1, 2
    colour: dict[str, int] = dict.fromkeys(index, white)

    for root in sorted(index):
        if colour[root] != white:
            continue
        colour[root] = grey
        path: list[str] = [root]
        stack: list[tuple[str, Iterable[str]]] = [(root, iter(sorted(set(index[root].depends_on))))]
        while stack:
            node_id, edges = stack[-1]
            advanced = False
            for dep in edges:
                state = colour.get(dep, white)
                if state == grey:
                    start = path.index(dep)
                    return tuple(path[start:]) + (dep,)
                if state == white:
                    colour[dep] = grey
                    path.append(dep)
                    stack.append((dep, iter(sorted(set(index[dep].depends_on)))))
                    advanced = True
                    break
            if not advanced:
                colour[node_id] = black
                path.pop()
                stack.pop()
    return ()


def topological_order(nodes: Iterable[ObjectiveNode]) -> tuple[str, ...]:
    """Return a DETERMINISTIC topological order of the node ids.

    Kahn's algorithm over a min-heap of ready ids. The heap is the whole point:
    a plain list or set makes the order depend on insertion or hash order, so
    the same input would produce different plans on different runs. Ties break
    on node_id, which is stable across processes.

    Raises `CyclicObjectiveError` naming the cycle, `UnknownDependencyError`
    for a dangling edge and `DuplicateObjectiveError` for a repeated id.
    """
    index = _index(nodes)
    _validate_dependencies(index)

    indegree = {node_id: len(set(node.depends_on)) for node_id, node in index.items()}
    dependents = _reverse_edges(index)

    ready = [node_id for node_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        node_id = heapq.heappop(ready)
        order.append(node_id)
        for child in dependents.get(node_id, ()):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)

    if len(order) != len(index):
        raise CyclicObjectiveError(_find_cycle(index))
    return tuple(order)


def build_graph(nodes: Iterable[ObjectiveNode]) -> ObjectiveGraph:
    """Validate a node set and return the graph view over it.

    Validation is total: duplicate ids, dangling `depends_on` ids and cycles
    are all rejected here, so every consumer downstream may assume the graph is
    well formed.
    """
    materialized = tuple(nodes)
    index = _index(materialized)
    order = topological_order(materialized)
    return ObjectiveGraph(nodes=index, dependents=_reverse_edges(index), order=order)


def _closure(index: Mapping[str, ObjectiveNode], goal_id: str, stop_at: frozenset[str] = frozenset()) -> set[str]:
    """Transitive dependency closure of one goal, including the goal itself.

    Traversal is pruned at any id in `stop_at`: a completed prerequisite means
    its own prerequisites were necessarily satisfied to complete it, so walking
    beneath it would report already-satisfied work as outstanding.
    """
    seen: set[str] = set()
    stack = [goal_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in stop_at:
            continue
        stack.extend(index[current].depends_on)
    return seen


def critical_path(nodes: Iterable[ObjectiveNode], goal_id: str) -> ResolutionPath:
    """Resolve ONE goal into its transitive prerequisite path.

    The result carries the goal plus every node it transitively depends on, in
    topological order, with resin and mora summed over exactly those nodes.
    Unrelated nodes in the input set are excluded - this is a path, not a plan
    for the whole account.

    `tasks`, `estimated_days` and `blocked_on` are deliberately left at their
    defaults; those are the scheduler's output, not the DAG's.
    """
    graph = build_graph(nodes)
    if goal_id not in graph.nodes:
        raise UnknownObjectiveError(goal_id)

    closure = _closure(graph.nodes, goal_id)
    ordered = tuple(node_id for node_id in graph.order if node_id in closure)
    total_resin = sum(graph.nodes[node_id].resin_cost for node_id in ordered)
    total_mora = sum(graph.nodes[node_id].mora_cost for node_id in ordered)

    return ResolutionPath(
        goal_id=goal_id,
        ordered_nodes=ordered,
        total_resin=total_resin,
        total_mora=total_mora,
    )


def unmet_prerequisites(
    nodes: Iterable[ObjectiveNode],
    goal_id: str,
    completed: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return what still blocks `goal_id`, in topological order.

    The goal itself is never reported: a goal does not block itself. A
    prerequisite already present in `completed` is dropped AND its own subtree
    is pruned, because a node cannot have been completed without its own
    dependencies having been satisfied first.
    """
    graph = build_graph(nodes)
    if goal_id not in graph.nodes:
        raise UnknownObjectiveError(goal_id)

    done = frozenset(completed)
    closure = _closure(graph.nodes, goal_id, stop_at=done)
    return tuple(
        node_id
        for node_id in graph.order
        if node_id in closure and node_id != goal_id and node_id not in done
    )


# ---------------------------------------------------------------------------
# Gate arithmetic
# ---------------------------------------------------------------------------


def required_ascension_for_level(level: int, level_caps: Sequence[int] = ASCENSION_LEVEL_CAPS) -> int:
    """Lowest ascension phase whose cap admits `level`.

    Level 20 sits at phase 0 because phase 0 already caps at 20; level 21
    requires phase 1. Raises for a level outside 1..max cap.
    """
    if level < 1:
        raise ValueError(f"level must be at least 1, got {level}")
    for phase, cap in enumerate(level_caps):
        if level <= cap:
            return phase
    raise ValueError(f"level {level} exceeds the highest cap {level_caps[-1]}")


def min_ascension_for_talent(
    level: int,
    min_ascension: int = TALENT_MIN_ASCENSION,
    max_ascension: int = TALENT_MAX_ASCENSION,
    max_talent_level: int = MAX_TALENT_LEVEL,
) -> int:
    """Ascension phase a talent level requires.

    Two points are pinned by the contract and are honoured exactly:
    `MIN_TALENT_LEVEL` needs no ascension, any level above it needs at least
    `min_ascension`, and `max_talent_level` needs `max_ascension`.

    Everything between those points is a monotone ceiling interpolation, NOT a
    transcribed table, precisely so no unverified per-level number is presented
    as fact. A caller holding the real table should not call this at all - pass
    an explicit gate through `expand_character_goal`.
    """
    if level < MIN_TALENT_LEVEL:
        raise ValueError(f"talent level must be at least {MIN_TALENT_LEVEL}, got {level}")
    if level > max_talent_level:
        raise ValueError(f"talent level {level} exceeds the maximum {max_talent_level}")
    if level == MIN_TALENT_LEVEL:
        return 0
    span = max_talent_level - MIN_TALENT_LEVEL
    steps = level - MIN_TALENT_LEVEL
    gate = -(-steps * max_ascension // span)  # integer ceiling division
    return max(min_ascension, min(max_ascension, gate))


# ---------------------------------------------------------------------------
# Node id vocabulary
# ---------------------------------------------------------------------------


def character_ascension_id(subject_id: int, phase: int, prefix: str = "") -> str:
    return f"{prefix}char:{subject_id}:ascension:{phase}"


def character_level_id(subject_id: int, level: int, prefix: str = "") -> str:
    return f"{prefix}char:{subject_id}:level:{level}"


def talent_id(subject_id: int, slot: int, level: int, prefix: str = "") -> str:
    return f"{prefix}char:{subject_id}:talent:{slot}:{level}"


def weapon_ascension_id(subject_id: int, phase: int, prefix: str = "") -> str:
    return f"{prefix}weapon:{subject_id}:ascension:{phase}"


def weapon_level_id(subject_id: int, level: int, prefix: str = "") -> str:
    return f"{prefix}weapon:{subject_id}:level:{level}"


# ---------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeCost:
    """Caller-supplied cost and gating for ONE generated node.

    Every field defaults to nothing. This engine never fills these in: material
    ids, quantities, mora, resin and domain rotation days are all DATA, owned by
    the ingest slice, and inventing them here would be inventing game facts.
    """

    materials: tuple[MaterialCost, ...] = ()
    mora_cost: int = 0
    resin_cost: int = 0
    available_weekdays: tuple[int, ...] = ()
    weekly_capped: bool = False
    display_name: str = ""


_NO_COSTS: dict[str, NodeCost] = {}


@dataclass
class _Builder:
    """Accumulates generated nodes while keeping ids unique."""

    costs: Mapping[str, NodeCost]
    emitted: dict[str, ObjectiveNode] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def add(
        self,
        node_id: str,
        kind: ObjectiveKind,
        subject_id: int,
        target_value: int,
        depends_on: Sequence[str],
        fallback_name: str,
    ) -> str:
        if node_id in self.emitted:
            return node_id
        cost = self.costs.get(node_id, NodeCost())
        self.emitted[node_id] = ObjectiveNode(
            node_id=node_id,
            kind=kind,
            subject_id=subject_id,
            target_value=target_value,
            depends_on=tuple(dict.fromkeys(depends_on)),
            materials=cost.materials,
            mora_cost=cost.mora_cost,
            resin_cost=cost.resin_cost,
            available_weekdays=cost.available_weekdays,
            weekly_capped=cost.weekly_capped,
            display_name=cost.display_name or fallback_name,
        )
        self.order.append(node_id)
        return node_id

    def result(self) -> tuple[ObjectiveNode, ...]:
        return tuple(self.emitted[node_id] for node_id in self.order)


def _build_chain(
    builder: _Builder,
    subject_id: int,
    target_level: int,
    phases: int,
    level_caps: Sequence[int],
    prefix: str,
    level_kind: ObjectiveKind,
    ascension_kind: ObjectiveKind,
    level_id_fn: Callable[[int, int, str], str],
    ascension_id_fn: Callable[[int, int, str], str],
    label: str,
) -> dict[int, str]:
    """Emit one alternating level / ascension chain and return its ascensions.

    The chain alternates because the two constraints point in opposite
    directions: a level cap is unlocked BY an ascension, and an ascension is
    unlocked BY sitting at the previous cap. That yields
    L20 -> A1 -> L40 -> A2 -> ... rather than a fan-out, and it is why the
    returned map is needed - talent nodes hang off specific phases in it.

    `phases` may exceed what `target_level` alone requires, because a talent
    gate can force a deeper ascension chain than the requested level does.
    """
    ascension_nodes: dict[int, str] = {}
    previous_level = ""

    for phase in range(phases):
        cap = level_caps[phase]
        level_deps: list[str] = []
        if phase >= 1:
            level_deps.append(ascension_nodes[phase])
        if previous_level:
            level_deps.append(previous_level)
        previous_level = builder.add(
            level_id_fn(subject_id, cap, prefix),
            level_kind,
            subject_id,
            cap,
            level_deps,
            f"{label} {subject_id} to level {cap}",
        )

        step = phase + 1
        ascension_deps: list[str] = []
        if step - 1 >= 1:
            ascension_deps.append(ascension_nodes[step - 1])
        ascension_deps.append(previous_level)
        ascension_nodes[step] = builder.add(
            ascension_id_fn(subject_id, step, prefix),
            ascension_kind,
            subject_id,
            step,
            ascension_deps,
            f"{label} {subject_id} ascension phase {step}",
        )

    final_level = target_level
    if phases >= 1:
        final_level = max(final_level, level_caps[phases - 1])
    already_emitted = phases >= 1 and final_level == level_caps[phases - 1]
    if not already_emitted:
        level_deps = []
        if phases >= 1:
            level_deps.append(ascension_nodes[phases])
        if previous_level:
            level_deps.append(previous_level)
        builder.add(
            level_id_fn(subject_id, final_level, prefix),
            level_kind,
            subject_id,
            final_level,
            level_deps,
            f"{label} {subject_id} to level {final_level}",
        )

    return ascension_nodes


def expand_character_goal(
    subject_id: int,
    target_level: int = 1,
    talent_targets: Mapping[int, int] | None = None,
    weapon_subject_id: int | None = None,
    weapon_target_level: int = 0,
    costs: Mapping[str, NodeCost] | None = None,
    level_caps: Sequence[int] = ASCENSION_LEVEL_CAPS,
    talent_gate: Mapping[int, int] | None = None,
    prefix: str = "",
) -> tuple[ObjectiveNode, ...]:
    """Decompose a high-level build goal into a wired ObjectiveNode set.

    Example intent - "character to level 60 with 6/6/6 talents and weapon at
    60" - becomes `expand_character_goal(id, 60, {1: 6, 2: 6, 3: 6},
    weapon_subject_id=wid, weapon_target_level=60)`.

    Edges wired, all four of them real:

    - a character level milestone depends on the ascension phase that unlocks
      its cap,
    - an ascension phase depends on the level milestone immediately below it,
      since a subject must be AT the cap to ascend, which is what makes the
      chain alternate rather than fan out,
    - a talent level depends on the ascension phase that unlocks it and on the
      talent level below it in the same slot,
    - a weapon level milestone depends on its own weapon ascension node, on an
      independent chain.

    `talent_gate` optionally replaces the derived gate with a real
    level-to-ascension table. `costs` supplies materials, mora, resin, weekday
    rotation and weekly caps per node id; its default is EMPTY and this
    function never invents any of them.
    """
    if target_level < 1:
        raise ValueError(f"target_level must be at least 1, got {target_level}")
    if not level_caps:
        raise ValueError("level_caps must not be empty")

    targets = dict(talent_targets or {})
    for slot, level in targets.items():
        if level < MIN_TALENT_LEVEL:
            raise ValueError(f"talent slot {slot} target {level} is below {MIN_TALENT_LEVEL}")

    def gate_for(level: int) -> int:
        if talent_gate is not None:
            if level not in talent_gate:
                raise ValueError(f"talent_gate has no entry for talent level {level}")
            return talent_gate[level]
        return min_ascension_for_talent(level)

    max_phase = len(level_caps) - 1
    phases = required_ascension_for_level(target_level, level_caps)
    for level in targets.values():
        phases = max(phases, gate_for(level))
    phases = min(phases, max_phase)

    builder = _Builder(costs=costs if costs is not None else _NO_COSTS)

    ascension_nodes = _build_chain(
        builder,
        subject_id,
        target_level,
        phases,
        level_caps,
        prefix,
        ObjectiveKind.CHARACTER_LEVEL,
        ObjectiveKind.CHARACTER_ASCENSION,
        character_level_id,
        character_ascension_id,
        "character",
    )

    # Talent chains, one per slot, each hanging off its unlocking ascension.
    for slot in sorted(targets):
        previous_talent_node = ""
        for level in range(MIN_TALENT_LEVEL + 1, targets[slot] + 1):
            gate = min(gate_for(level), max_phase)
            deps: list[str] = []
            if gate >= 1:
                if gate not in ascension_nodes:
                    raise ValueError(
                        f"talent level {level} needs ascension {gate} but the chain only reaches {phases}"
                    )
                deps.append(ascension_nodes[gate])
            if previous_talent_node:
                deps.append(previous_talent_node)
            previous_talent_node = builder.add(
                talent_id(subject_id, slot, level, prefix),
                ObjectiveKind.TALENT_LEVEL,
                subject_id,
                level,
                deps,
                f"character {subject_id} talent {slot} to level {level}",
            )

    # Weapon chain, independent of the character chain.
    if weapon_subject_id is not None and weapon_target_level >= 1:
        _build_chain(
            builder,
            weapon_subject_id,
            weapon_target_level,
            required_ascension_for_level(weapon_target_level, level_caps),
            level_caps,
            prefix,
            ObjectiveKind.WEAPON_LEVEL,
            ObjectiveKind.WEAPON_ASCENSION,
            weapon_level_id,
            weapon_ascension_id,
            "weapon",
        )

    return builder.result()
