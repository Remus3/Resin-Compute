"""Guards on the port registry.

Two different kinds of assertion live here and the difference is the whole point.

**Positive pins, against the LIVE definition site.** `assert ENGINE == 8790`
would pass forever while the server that actually binds quietly moved to
something else, so these import the module that really binds and compare it to
the registry. That is Riot Commander's refinement of Red Moon's pattern, and it
is the arm that catches drift rather than restating it.

**A negative guard, against foreign literals.** Red Moon proves disjointness
from the other side: no sibling project's port number may appear in tracked
source at all. This tree carries the sibling BLOCK ranges in `core/ports.py`
deliberately, so that one file is exempt by name - everything else is swept.

Nothing here scans a live socket. Clockspeed's registry records what that costs:
it chose a band by probing for a free listener, the owning project's GUI happened
to be closed, and the whole block reported clean while being someone else's.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core import ports

REPO_ROOT = Path(__file__).resolve().parent.parent

#: `core/ports.py` is the one file allowed to name a sibling's numbers, because
#: carrying the blocks is how this tree proves disjointness at all.
FOREIGN_LITERAL_EXEMPT = {"core/ports.py", "tests/test_ports.py"}


# ---------------------------------------------------------------------------
# The block itself
# ---------------------------------------------------------------------------


def test_the_block_is_the_one_the_registry_assigned():
    assert ports.RSC_BLOCK == range(8790, 8810)
    assert len(ports.RSC_BLOCK) == 20


def test_every_port_this_repo_binds_is_inside_its_own_block():
    """The defect that created this module, asserted directly.

    PityEngine shipped on 8870, which is inside Daemon Slayer's reserved
    8860-8879. Nothing was listening there so nothing broke and nothing warned.
    """
    assert ports.ALL
    for port in sorted(ports.ALL):
        assert ports.is_ours(port), f"port {port} is bound here but sits outside the ResinCompute block"
        assert ports.block_for(port) == "rsc"


def test_the_block_is_disjoint_from_every_sibling_block():
    ours = set(ports.RSC_BLOCK)
    for name, block in ports.BLOCKS.items():
        if name == "rsc":
            continue
        assert ours.isdisjoint(set(block)), f"the ResinCompute block overlaps {name}"


def test_every_declared_block_is_disjoint_from_every_other():
    """`block_for` returns the first match, so overlapping blocks would make its
    answer depend on dict iteration order rather than on the registry."""
    names = sorted(ports.BLOCKS)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            assert set(ports.BLOCKS[left]).isdisjoint(set(ports.BLOCKS[right])), f"{left} overlaps {right}"


def test_daemon_slayers_block_still_contains_the_port_this_project_abandoned():
    """A regression pin on the reason for the migration.

    If somebody ever proposes moving the engine back to 8870, this states in one
    line why that is not available.
    """
    assert 8870 in ports.DS_BLOCK
    assert ports.block_for(8870) == "ds"
    assert not ports.is_ours(8870)


def test_block_for_returns_none_outside_every_block():
    assert ports.block_for(80) is None
    assert ports.block_for(8880) is None


def test_next_free_stays_inside_the_block_and_skips_what_is_bound():
    candidate = ports.next_free()
    assert candidate in ports.RSC_BLOCK
    assert candidate not in ports.ALL


# ---------------------------------------------------------------------------
# Positive pins against the live definition sites
# ---------------------------------------------------------------------------


def test_the_engine_service_binds_the_registered_port():
    from agents.pity_engine.__main__ import DEFAULT_PORT

    assert DEFAULT_PORT == ports.ENGINE


def test_the_engine_client_default_matches_the_service():
    from core.config import DEFAULT_ENGINE_PORT

    assert DEFAULT_ENGINE_PORT == ports.ENGINE


def test_the_engine_binds_loopback_on_both_sides():
    from agents.pity_engine.__main__ import DEFAULT_HOST
    from core.config import DEFAULT_ENGINE_HOST

    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_ENGINE_HOST == "127.0.0.1"


# ---------------------------------------------------------------------------
# The negative guard - no foreign port literal in tracked source
# ---------------------------------------------------------------------------


def _tracked_python_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith((".git/", "__pycache__")) or "/__pycache__/" in rel:
            continue
        if ".pytest_cache" in rel or "/node_modules/" in rel:
            continue
        out.append(path)
    return out


def _foreign_ports() -> set[int]:
    foreign: set[int] = set()
    for name, block in ports.BLOCKS.items():
        if name == "rsc":
            continue
        foreign.update(block)
    return foreign


def test_no_sibling_port_literal_appears_in_tracked_python_source():
    """Red Moon's negative proof, applied here.

    An integer literal inside a sibling's block has no business in this tree.
    Parsing rather than grepping means a number inside a comment or a docstring
    does not trip it - prose about a sibling is fine, a live literal is not.
    """
    foreign = _foreign_ports()
    offenders: list[str] = []

    for path in _tracked_python_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in FOREIGN_LITERAL_EXEMPT:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):  # pragma: no cover - a broken file is another test's problem
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, int) and node.value in foreign:
                offenders.append(f"{rel}:{node.lineno} carries {node.value}")

    assert not offenders, "foreign port literals in tracked source: " + "; ".join(offenders)


def test_the_guard_is_not_vacuous():
    """Proof the sweep above would actually catch something.

    A guard that silently stopped finding files would pass forever. This asserts
    it looks at a real, populated set and that a known foreign number is in the
    set it tests against.
    """
    assert len(_tracked_python_files()) > 10
    assert 8870 in _foreign_ports()
    assert 8860 in _foreign_ports()


@pytest.mark.parametrize("port", sorted(ports.ALL))
def test_no_bound_port_is_a_foreign_port(port):
    assert port not in _foreign_ports()
