"""Tests for the objective DAG engine.

Every assertion here is about MECHANISM. Nothing asserts a material quantity or
a character name, because the engine under test does not know any.
"""
from __future__ import annotations

import math
import random

import pytest

from core.types import MaterialCost, ObjectiveKind, ObjectiveNode
from engines.objectives import (
    ASCENSION_LEVEL_CAPS,
    MAX_ASCENSION_PHASE,
    MAX_TALENT_LEVEL,
    MIN_TALENT_LEVEL,
    TALENT_MAX_ASCENSION,
    TALENT_MIN_ASCENSION,
    CyclicObjectiveError,
    DuplicateObjectiveError,
    NodeCost,
    UnknownDependencyError,
    UnknownObjectiveError,
    build_graph,
    character_ascension_id,
    character_level_id,
    critical_path,
    expand_character_goal,
    min_ascension_for_talent,
    required_ascension_for_level,
    talent_id,
    topological_order,
    unmet_prerequisites,
    weapon_level_id,
)

SUBJECT = 10000096
WEAPON = 11509


def node(node_id: str, *deps: str, resin: int = 0, mora: int = 0) -> ObjectiveNode:
    """Terse builder for a bare mechanism node."""
    return ObjectiveNode(
        node_id=node_id,
        kind=ObjectiveKind.CHARACTER_LEVEL,
        subject_id=SUBJECT,
        target_value=1,
        depends_on=tuple(deps),
        resin_cost=resin,
        mora_cost=mora,
    )


def diamond() -> tuple[ObjectiveNode, ...]:
    """a -> b, a -> c, b/c -> d, plus an unrelated island node 'x'."""
    return (
        node("a", resin=10, mora=100),
        node("b", "a", resin=20, mora=200),
        node("c", "a", resin=30, mora=300),
        node("d", "b", "c", resin=40, mora=400),
        node("x", resin=999, mora=999),
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_build_graph_rejects_dangling_dependency():
    nodes = (node("a"), node("b", "ghost"))
    with pytest.raises(UnknownDependencyError) as caught:
        build_graph(nodes)
    assert caught.value.node_id == "b"
    assert caught.value.missing_id == "ghost"
    assert "ghost" in str(caught.value)


def test_build_graph_rejects_duplicate_ids():
    with pytest.raises(DuplicateObjectiveError):
        build_graph((node("a"), node("a")))


def test_cycle_raises_and_message_names_every_cycle_member():
    nodes = (node("a", "c"), node("b", "a"), node("c", "b"), node("island"))
    with pytest.raises(CyclicObjectiveError) as caught:
        build_graph(nodes)

    message = str(caught.value)
    for member in ("a", "b", "c"):
        assert member in caught.value.cycle, f"{member} missing from reported cycle {caught.value.cycle}"
    # The path closes: the entry node is repeated at the end.
    assert caught.value.cycle[0] == caught.value.cycle[-1]
    assert "->" in message
    assert "island" not in caught.value.cycle
    # Not the useless generic message.
    assert message != "cycle detected"


def test_self_dependency_is_a_cycle_of_one():
    with pytest.raises(CyclicObjectiveError) as caught:
        build_graph((node("solo", "solo"),))
    assert caught.value.cycle == ("solo", "solo")


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_topological_order_respects_dependencies():
    order = topological_order(diamond())
    position = {node_id: idx for idx, node_id in enumerate(order)}
    assert position["a"] < position["b"]
    assert position["a"] < position["c"]
    assert position["b"] < position["d"]
    assert position["c"] < position["d"]


def test_topological_order_is_deterministic_across_shuffles():
    nodes = list(diamond())
    baseline = topological_order(nodes)
    rng = random.Random(20260906)
    for attempt in range(20):
        shuffled = nodes[:]
        rng.shuffle(shuffled)
        assert topological_order(shuffled) == baseline, f"order drifted on shuffle {attempt}"


def test_topological_order_breaks_ties_on_node_id():
    # Three roots with no edges at all: only the stable key can order them.
    order = topological_order((node("zulu"), node("alpha"), node("mike")))
    assert order == ("alpha", "mike", "zulu")


# ---------------------------------------------------------------------------
# Critical path
# ---------------------------------------------------------------------------


def test_critical_path_includes_transitive_deps_and_excludes_unrelated():
    path = critical_path(diamond(), "d")
    assert set(path.ordered_nodes) == {"a", "b", "c", "d"}
    assert "x" not in path.ordered_nodes
    assert path.goal_id == "d"
    assert path.ordered_nodes[0] == "a"
    assert path.ordered_nodes[-1] == "d"


def test_critical_path_sums_only_path_costs():
    path = critical_path(diamond(), "d")
    assert path.total_resin == 10 + 20 + 30 + 40
    assert path.total_mora == 100 + 200 + 300 + 400
    # The unrelated island's 999 is excluded from both totals.
    assert path.total_resin != 999 + 100


def test_critical_path_of_a_root_is_just_the_root():
    path = critical_path(diamond(), "a")
    assert path.ordered_nodes == ("a",)
    assert path.total_resin == 10


def test_critical_path_leaves_schedule_fields_empty():
    path = critical_path(diamond(), "d")
    assert path.tasks == ()
    assert path.estimated_days == 0
    assert path.blocked_on == ()


def test_critical_path_rejects_unknown_goal():
    with pytest.raises(UnknownObjectiveError):
        critical_path(diamond(), "nope")


# ---------------------------------------------------------------------------
# Unmet prerequisites
# ---------------------------------------------------------------------------


def test_unmet_prerequisites_with_nothing_done():
    assert unmet_prerequisites(diamond(), "d") == ("a", "b", "c")


def test_unmet_prerequisites_drops_completed_and_prunes_beneath_them():
    # 'b' done implies 'a' was done to get there, but 'c' still needs 'a'.
    assert unmet_prerequisites(diamond(), "d", completed={"b"}) == ("a", "c")
    # Both branches done: 'a' is unreachable from any outstanding node.
    assert unmet_prerequisites(diamond(), "d", completed={"b", "c"}) == ()


def test_unmet_prerequisites_never_reports_the_goal_itself():
    assert "d" not in unmet_prerequisites(diamond(), "d")
    assert unmet_prerequisites(diamond(), "a") == ()


# ---------------------------------------------------------------------------
# Gate arithmetic
# ---------------------------------------------------------------------------


def test_cap_table_is_the_pinned_one():
    assert ASCENSION_LEVEL_CAPS == (20, 40, 50, 60, 70, 80, 90)
    assert MAX_ASCENSION_PHASE == 6


@pytest.mark.parametrize(
    ("level", "phase"),
    [(1, 0), (20, 0), (21, 1), (40, 1), (41, 2), (50, 2), (60, 3), (70, 4), (80, 5), (90, 6)],
)
def test_required_ascension_for_level(level, phase):
    assert required_ascension_for_level(level) == phase


def test_required_ascension_rejects_out_of_range_levels():
    with pytest.raises(ValueError):
        required_ascension_for_level(0)
    with pytest.raises(ValueError):
        required_ascension_for_level(91)


def test_talent_gate_honours_both_pinned_points_and_stays_monotone():
    assert min_ascension_for_talent(1) == 0
    # Any level above 1 requires ascension.
    assert min_ascension_for_talent(2) >= 1
    # Level 10 requires ascension 6.
    assert min_ascension_for_talent(10) == 6
    gates = [min_ascension_for_talent(level) for level in range(1, 11)]
    assert gates == sorted(gates), f"gate table is not monotone: {gates}"
    assert max(gates) <= MAX_ASCENSION_PHASE


def test_talent_gate_rejects_out_of_range():
    with pytest.raises(ValueError):
        min_ascension_for_talent(0)
    with pytest.raises(ValueError):
        min_ascension_for_talent(11)


# ---------------------------------------------------------------------------
# expand_character_goal
# ---------------------------------------------------------------------------


def test_expand_character_goal_produces_an_acyclic_validated_graph():
    nodes = expand_character_goal(SUBJECT, 60, {1: 6, 2: 6, 3: 6}, weapon_subject_id=WEAPON, weapon_target_level=60)
    graph = build_graph(nodes)  # raises on a cycle or a dangling edge
    assert len(graph) == len(nodes)
    assert len(graph.order) == len(nodes)


def test_expand_character_goal_wires_level_cap_to_its_ascension_node():
    nodes = expand_character_goal(SUBJECT, 60)
    by_id = {n.node_id: n for n in nodes}
    level_60 = by_id[character_level_id(SUBJECT, 60)]
    assert character_ascension_id(SUBJECT, 3) in level_60.depends_on
    # Level 20 sits under phase 0, so it hangs off no ascension at all.
    assert by_id[character_level_id(SUBJECT, 20)].depends_on == ()


def test_expand_character_goal_wires_ascension_to_the_cap_below_it():
    nodes = expand_character_goal(SUBJECT, 60)
    by_id = {n.node_id: n for n in nodes}
    ascension_2 = by_id[character_ascension_id(SUBJECT, 2)]
    assert character_level_id(SUBJECT, 40) in ascension_2.depends_on


def test_talent_ten_transitively_depends_on_ascension_six():
    nodes = expand_character_goal(SUBJECT, 60, {1: 10})
    goal = talent_id(SUBJECT, 1, 10)
    blockers = unmet_prerequisites(nodes, goal)
    assert character_ascension_id(SUBJECT, 6) in blockers
    # And it is genuinely reachable through the path, not merely present.
    path = critical_path(nodes, goal)
    assert character_ascension_id(SUBJECT, 6) in path.ordered_nodes
    assert path.ordered_nodes[-1] == goal


def test_talent_chain_links_each_level_to_the_one_below():
    nodes = expand_character_goal(SUBJECT, 60, {1: 4})
    by_id = {n.node_id: n for n in nodes}
    assert talent_id(SUBJECT, 1, 3) in by_id[talent_id(SUBJECT, 1, 4)].depends_on
    # Talent level 1 is the baseline and emits no node.
    assert talent_id(SUBJECT, 1, 1) not in by_id


def test_a_talent_gate_deepens_the_ascension_chain_beyond_the_level_target():
    # Level 60 alone needs phase 3. A level 10 talent forces the chain to 6.
    nodes = expand_character_goal(SUBJECT, 60, {1: 10})
    ids = {n.node_id for n in nodes}
    for phase in range(1, 7):
        assert character_ascension_id(SUBJECT, phase) in ids, f"ascension {phase} missing"
    # Reaching phase 6 forces the character to level 80 on the way.
    assert character_level_id(SUBJECT, 80) in ids


def test_weapon_chain_is_independent_of_the_character_chain():
    nodes = expand_character_goal(SUBJECT, 60, weapon_subject_id=WEAPON, weapon_target_level=60)
    path = critical_path(nodes, weapon_level_id(WEAPON, 60))
    assert all(not node_id.startswith("char:") for node_id in path.ordered_nodes)
    assert weapon_level_id(WEAPON, 20) in path.ordered_nodes


def test_no_weapon_nodes_when_no_weapon_requested():
    nodes = expand_character_goal(SUBJECT, 60)
    assert all(not n.node_id.startswith("weapon:") for n in nodes)


def test_kinds_are_assigned_per_node_family():
    nodes = expand_character_goal(SUBJECT, 40, {1: 2}, weapon_subject_id=WEAPON, weapon_target_level=40)
    by_id = {n.node_id: n for n in nodes}
    assert by_id[character_level_id(SUBJECT, 40)].kind is ObjectiveKind.CHARACTER_LEVEL
    assert by_id[character_ascension_id(SUBJECT, 1)].kind is ObjectiveKind.CHARACTER_ASCENSION
    assert by_id[talent_id(SUBJECT, 1, 2)].kind is ObjectiveKind.TALENT_LEVEL
    assert by_id[weapon_level_id(WEAPON, 40)].kind is ObjectiveKind.WEAPON_LEVEL


def test_materials_default_to_empty_and_are_never_invented():
    nodes = expand_character_goal(SUBJECT, 60, {1: 6}, weapon_subject_id=WEAPON, weapon_target_level=60)
    assert all(n.materials == () for n in nodes)
    assert all(n.resin_cost == 0 for n in nodes)
    assert all(n.mora_cost == 0 for n in nodes)


def test_caller_supplied_costs_are_applied_by_node_id():
    target = character_ascension_id(SUBJECT, 1)
    cost = NodeCost(
        materials=(MaterialCost(material_id=113059, quantity=2, display_name="fixture material"),),
        mora_cost=20000,
        resin_cost=40,
        available_weekdays=(1, 4),
        weekly_capped=True,
        display_name="fixture ascension",
    )
    nodes = expand_character_goal(SUBJECT, 60, costs={target: cost})
    by_id = {n.node_id: n for n in nodes}
    assert by_id[target].materials[0].material_id == 113059
    assert by_id[target].mora_cost == 20000
    assert by_id[target].resin_cost == 40
    assert by_id[target].available_weekdays == (1, 4)
    assert by_id[target].weekly_capped is True
    assert by_id[target].display_name == "fixture ascension"
    # Untouched nodes stay at zero.
    assert by_id[character_level_id(SUBJECT, 20)].resin_cost == 0


def test_expansion_is_deterministic():
    first = expand_character_goal(SUBJECT, 60, {1: 6, 2: 6, 3: 6}, weapon_subject_id=WEAPON, weapon_target_level=60)
    second = expand_character_goal(SUBJECT, 60, {3: 6, 1: 6, 2: 6}, weapon_subject_id=WEAPON, weapon_target_level=60)
    assert [n.node_id for n in first] == [n.node_id for n in second]


def test_expand_rejects_a_nonsense_target_level():
    with pytest.raises(ValueError):
        expand_character_goal(SUBJECT, 0)


# ---------------------------------------------------------------------------
# Boundary arms - each pins a branch the tests above leave unproven.
# ---------------------------------------------------------------------------


# -- graph view helpers ------------------------------------------------------


def test_graph_membership_and_direct_edge_views():
    graph = build_graph(expand_character_goal(SUBJECT, 40))
    level_20 = character_level_id(SUBJECT, 20)
    level_40 = character_level_id(SUBJECT, 40)
    ascension_1 = character_ascension_id(SUBJECT, 1)

    assert level_20 in graph
    assert "nope" not in graph
    assert len(graph) == 3
    assert graph.dependencies_of(level_40) == (ascension_1, level_20)
    assert graph.dependencies_of(level_20) == ()
    assert graph.dependents_of(level_20) == (ascension_1, level_40)
    assert graph.dependents_of(level_40) == ()
    assert graph.transitive_dependents(level_20) == (ascension_1, level_40)
    assert graph.transitive_dependents(ascension_1) == (level_40,)


def test_graph_views_reject_unknown_ids():
    graph = build_graph(expand_character_goal(SUBJECT, 40))
    for view in (graph.dependencies_of, graph.dependents_of, graph.transitive_dependents):
        with pytest.raises(UnknownObjectiveError) as caught:
            view("nope")
        assert caught.value.goal_id == "nope"


def test_unmet_prerequisites_rejects_unknown_goal():
    with pytest.raises(UnknownObjectiveError):
        unmet_prerequisites(diamond(), "nope")


# -- gate arithmetic edges ---------------------------------------------------


def test_required_ascension_honours_a_custom_cap_table():
    caps = (10, 30)
    assert required_ascension_for_level(10, caps) == 0
    assert required_ascension_for_level(11, caps) == 1
    assert required_ascension_for_level(30, caps) == 1
    with pytest.raises(ValueError):
        required_ascension_for_level(31, caps)


def test_talent_gate_table_is_the_ceiling_interpolation_between_the_pinned_points():
    """Pins the FORMULA, not a sourced table.

    ROADMAP Known gaps: intermediate gates are interpolated, not sourced. This
    arm re-derives the expected table from the three pinned points and the
    stated rule - monotone ceiling interpolation - using float math.ceil, so
    it is an independent computation of the same definition rather than a
    transcription of the engine's integer trick. No per-level number here is
    presented as a game fact.
    """
    span = MAX_TALENT_LEVEL - MIN_TALENT_LEVEL
    derived = [0] + [
        max(TALENT_MIN_ASCENSION, min(TALENT_MAX_ASCENSION, math.ceil((level - MIN_TALENT_LEVEL) * TALENT_MAX_ASCENSION / span)))
        for level in range(MIN_TALENT_LEVEL + 1, MAX_TALENT_LEVEL + 1)
    ]
    actual = [min_ascension_for_talent(level) for level in range(MIN_TALENT_LEVEL, MAX_TALENT_LEVEL + 1)]

    assert actual == derived
    # The three pinned points, exactly.
    assert actual[0] == 0
    assert actual[1] == TALENT_MIN_ASCENSION == 1
    assert actual[-1] == TALENT_MAX_ASCENSION == 6
    # Monotone and never a repeat of level 1's zero above level 1.
    assert actual == sorted(actual)
    assert all(gate >= 1 for gate in actual[1:])


def test_talent_gate_endpoint_overrides_are_honoured():
    """Docstring: every caller may override the two endpoints."""
    # A longer talent scale keeps both pins and stays monotone.
    wide = [min_ascension_for_talent(level, max_talent_level=15) for level in range(1, 16)]
    assert wide[0] == 0
    assert wide[1] == TALENT_MIN_ASCENSION
    assert wide[-1] == TALENT_MAX_ASCENSION
    assert wide == sorted(wide)

    # A lower ceiling and a higher floor both bind.
    assert min_ascension_for_talent(MAX_TALENT_LEVEL, max_ascension=4) == 4
    assert min_ascension_for_talent(2, min_ascension=2) == 2

    # A one-level scale has only the baseline: level 1 is 0, level 2 is out of range.
    assert min_ascension_for_talent(1, max_talent_level=1) == 0
    with pytest.raises(ValueError):
        min_ascension_for_talent(2, max_talent_level=1)


# -- expand_character_goal: explicit talent_gate path -----------------------


def test_explicit_talent_gate_replaces_the_derived_one():
    """With a caller table saying level 2 needs no ascension, the talent node hangs free."""
    nodes = expand_character_goal(SUBJECT, 20, {1: 2}, talent_gate={2: 0})
    by_id = {n.node_id: n for n in nodes}
    assert set(by_id) == {character_level_id(SUBJECT, 20), talent_id(SUBJECT, 1, 2)}
    assert by_id[talent_id(SUBJECT, 1, 2)].depends_on == ()
    # The derived gate would have demanded ascension 1 here.
    assert min_ascension_for_talent(2) == 1


def test_explicit_talent_gate_missing_an_entry_is_rejected():
    with pytest.raises(ValueError) as caught:
        expand_character_goal(SUBJECT, 20, {1: 3}, talent_gate={2: 1})
    assert "talent level 3" in str(caught.value)


def test_intermediate_gate_deeper_than_the_chain_is_rejected_naming_the_depth():
    """The chain is sized by the TARGET level's gate; a deeper intermediate gate cannot be wired.

    This is NOT a monotonicity check - the code performs none. A non-monotone
    table whose intermediate gates all fit inside the chain, e.g. {2: 3, 3: 1}
    for a level 60 target, is accepted. Only an intermediate gate that exceeds
    the chain's depth is rejected, and the message names that depth.
    """
    with pytest.raises(ValueError) as caught:
        expand_character_goal(SUBJECT, 60, {1: 3}, talent_gate={2: 6, 3: 1})
    message = str(caught.value)
    assert "talent level 2" in message
    assert "chain only reaches 3" in message


# -- expand_character_goal: argument validation -----------------------------


def test_expand_rejects_a_talent_target_below_one():
    with pytest.raises(ValueError) as caught:
        expand_character_goal(SUBJECT, 60, {1: 0})
    assert "slot 1" in str(caught.value)


def test_expand_rejects_an_empty_cap_table():
    with pytest.raises(ValueError) as caught:
        expand_character_goal(SUBJECT, 60, level_caps=())
    assert "level_caps" in str(caught.value)


# -- expand_character_goal: level targets off the cap table -----------------


def test_non_cap_target_emits_a_trailing_level_node_on_its_phase():
    nodes = expand_character_goal(SUBJECT, 45)
    ids = [n.node_id for n in nodes]
    assert ids[-1] == character_level_id(SUBJECT, 45)
    by_id = {n.node_id: n for n in nodes}
    assert by_id[character_level_id(SUBJECT, 45)].depends_on == (
        character_ascension_id(SUBJECT, 2),
        character_level_id(SUBJECT, 40),
    )
    assert character_level_id(SUBJECT, 50) not in by_id
    build_graph(nodes)  # still acyclic and fully wired


def test_default_target_is_a_single_level_one_node():
    nodes = expand_character_goal(SUBJECT)
    assert [n.node_id for n in nodes] == [character_level_id(SUBJECT, 1)]
    assert nodes[0].depends_on == ()
    assert nodes[0].target_value == 1


def test_a_deepened_chain_subsumes_a_non_cap_level_target():
    """Level 55 needs phase 3; talent 10 forces phase 6 and level 80 on the way.

    The chain's final level is the deeper of the target and the last cap it
    reached, so the subsumed 55 emits no node of its own.
    """
    nodes = expand_character_goal(SUBJECT, 55, {1: 10})
    ids = {n.node_id for n in nodes}
    assert character_level_id(SUBJECT, 80) in ids
    assert character_level_id(SUBJECT, 55) not in ids
    assert character_ascension_id(SUBJECT, 6) in ids


def test_weapon_target_level_zero_emits_no_weapon_chain():
    nodes = expand_character_goal(SUBJECT, 20, weapon_subject_id=WEAPON, weapon_target_level=0)
    assert [n.node_id for n in nodes] == [character_level_id(SUBJECT, 20)]


def test_prefix_is_applied_to_every_node_id_and_edge():
    nodes = expand_character_goal(SUBJECT, 40, {1: 2}, weapon_subject_id=WEAPON, weapon_target_level=20, prefix="p/")
    assert nodes  # non-vacuous
    assert all(n.node_id.startswith("p/") for n in nodes)
    assert all(dep.startswith("p/") for n in nodes for dep in n.depends_on)
    assert character_level_id(SUBJECT, 40, "p/") in {n.node_id for n in nodes}
    build_graph(nodes)  # every prefixed edge resolves


def test_worked_example_decomposes_into_thirty_nodes_reaching_phase_four():
    """ROADMAP: level 60 with 6/6/6 and a weapon at 60 is exactly 30 nodes.

    The character chain reaches ascension phase 4 because the talent gate
    demands it, not because level 60 does.
    """
    nodes = expand_character_goal(SUBJECT, 60, {1: 6, 2: 6, 3: 6}, weapon_subject_id=WEAPON, weapon_target_level=60)
    ids = {n.node_id for n in nodes}
    assert len(nodes) == 30
    assert character_ascension_id(SUBJECT, 4) in ids
    assert character_ascension_id(SUBJECT, 5) not in ids
    assert required_ascension_for_level(60) == 3
    assert min_ascension_for_talent(6) == 4


# -- generated labels --------------------------------------------------------


def test_generated_labels_are_the_display_name_fallback():
    nodes = expand_character_goal(SUBJECT, 40, {1: 2}, weapon_subject_id=WEAPON, weapon_target_level=20)
    by_id = {n.node_id: n for n in nodes}
    assert by_id[character_level_id(SUBJECT, 20)].display_name == f"character {SUBJECT} to level 20"
    assert by_id[character_ascension_id(SUBJECT, 1)].display_name == f"character {SUBJECT} ascension phase 1"
    assert by_id[talent_id(SUBJECT, 1, 2)].display_name == f"character {SUBJECT} talent 1 to level 2"
    assert by_id[weapon_level_id(WEAPON, 20)].display_name == f"weapon {WEAPON} to level 20"
