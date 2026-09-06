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
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from core import ports
from tests.conftest import require_git_repository

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


def _git(*args: str, stdin: str | None = None, ok: tuple[int, ...] = (0,)) -> str:
    """Run a git command at REPO_ROOT and return stdout.

    `cwd` is REPO_ROOT computed from `__file__`, never the process working
    directory: pytest can be invoked from anywhere and a relative git call would
    then answer about a different repository, or about none.
    """
    require_git_repository()
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # git absent from PATH
        raise RuntimeError(f"cannot ask git about tracked source: {exc}") from exc
    if completed.returncode not in ok:
        raise RuntimeError(f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}")
    return completed.stdout


@lru_cache(maxsize=1)
def _tracked_python_paths() -> tuple[Path, ...]:
    """Every `.py` file git TRACKS, asked of git rather than walked from disk.

    THE DEFECT THIS REPLACED. This helper was named `_tracked_python_files` and
    never consulted git. It was `REPO_ROOT.rglob("*.py")` behind an ad-hoc
    denylist of `__pycache__`, `.pytest_cache`, `node_modules` and `.git/`, which
    made it a test of PRESENCE ON DISK while its name, and the guard below,
    claim TRACKEDNESS. Anything gitignored that holds `.py` files was swept as
    if it were this project's source.

    The agent worktrees under `.claude/` were how it was noticed, but they are
    not the reason it matters. A stranger clones this repo, makes a `.venv/`,
    installs the dev requirements, and site-packages fills with third-party
    `.py` files carrying every integer under the sun. Their very first
    `python -m pytest tests` goes red on a port-hygiene guard for a reason that
    has nothing to do with them. Any guard that sweeps this tree is worth
    checking for the same confusion, and the question is always the same one:
    does the helper ask git, or does it ask the disk.

    Asking git is also what makes the old denylist unnecessary rather than
    merely redundant, and it is deliberately NOT kept: git tracks none of those
    four paths today, and if one ever did become tracked - a vendored
    `node_modules` module, a committed `__pycache__` - it would be real tracked
    source that this guard SHOULD sweep. Re-adding the filter would build a
    blind spot exactly where an accidental vendoring lands.

    `-z` because `core.quotePath` escapes non-ASCII paths in git's default
    output and would corrupt them on the way back.

    Raises rather than returning empty. A guard whose file list silently
    collapsed to nothing would pass forever, which is the failure mode
    `test_the_guard_is_not_vacuous` exists to deny.
    """
    listing = _git("ls-files", "-z")
    rels = [rel for rel in listing.split("\0") if rel.endswith(".py")]
    if not rels:
        raise RuntimeError("git ls-files reported no tracked .py files - the port sweep would scan nothing")
    # A path can be in the index and absent from disk - a file deleted but not
    # yet staged. Skipped, not failed: that is an ordinary transient working
    # tree state with nothing to do with port hygiene, and failing on it would
    # reintroduce the exact bug being fixed here - this guard going red for a
    # reason that is not its subject. A file that is not there carries no
    # literal to find, so skipping cannot hide an offender.
    return tuple(path for rel in rels if (path := REPO_ROOT / rel).is_file())


def _tracked_python_files() -> list[Path]:
    """The cached tuple as a fresh list, so no caller can mutate the cache."""
    return list(_tracked_python_paths())


def _gitignored(rel_paths: list[str]) -> set[str]:
    """The subset of `rel_paths` that git's ignore rules exclude.

    A DIFFERENT oracle from `git ls-files`, which is the point: it is what lets
    the regression arm below check the file list against something other than
    the command that produced it.

    `check-ignore` exits 0 when at least one path is ignored and 1 when none
    are, so 1 is the healthy answer here and only above that is an error.
    """
    if not rel_paths:
        return set()
    # -z changes the INPUT separator as well as the output one. Feeding
    # newline-separated paths makes git read the whole list as a single path
    # with embedded newlines, and the check silently collapses to one bogus
    # entry that still satisfies a naive assertion. Measured in
    # tests/test_line_endings.py against `check-attr`, same trap.
    out = _git("check-ignore", "--stdin", "-z", stdin="\0".join(rel_paths), ok=(0, 1))
    return {rel for rel in out.split("\0") if rel}


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

    Strengthened past a bare count: a non-empty list of the WRONG files would
    also clear `> 10`, so this pins that this project's own source is in it and
    that every path returned is really on disk.
    """
    files = _tracked_python_files()
    assert len(files) > 10
    rels = {path.relative_to(REPO_ROOT).as_posix() for path in files}
    assert "core/ports.py" in rels, "the sweep does not include the module it guards"
    assert "tests/test_ports.py" in rels
    assert "agents/pity_engine/__main__.py" in rels, "the sweep does not reach the engine that binds"
    assert all(path.is_file() for path in files), "the sweep lists paths that are not on disk"
    assert 8870 in _foreign_ports()
    assert 8860 in _foreign_ports()


def test_the_swept_file_list_is_git_derived_and_not_a_disk_walk():
    """The regression arm on the defect that `_tracked_python_paths` replaced.

    The old implementation walked the filesystem, so any gitignored directory
    holding `.py` files was swept as project source - a contributor's `.venv/`,
    an agent worktree under `.claude/`, a vendored `node_modules`. This asserts
    the property that failed then and holds now: NOTHING the guard scans is a
    path git ignores.

    Deliberately does not require a `.venv/` to exist. The arm has to hold in a
    fresh clone, so the check is on the file list itself rather than on ambient
    state that a clean checkout would not have.
    """
    rels = [path.relative_to(REPO_ROOT).as_posix() for path in _tracked_python_files()]

    # Non-vacuity, and it has to be built in rather than argued. An assertion
    # that merely found nothing would also be satisfied by a detector that had
    # stopped reporting anything at all, so it proves nothing on its own.
    # Feeding the real list PLUS one synthetic path of the shape a disk walk
    # would produce settles both halves in a single call: the detector is live,
    # and the real list contributes not one entry to it.
    canary = ".venv/Lib/site-packages/example/client.py"
    assert _gitignored(rels + [canary]) == {canary}, "the gitignore detector did not fire on a known-ignored path"


@pytest.mark.parametrize("port", sorted(ports.ALL))
def test_no_bound_port_is_a_foreign_port(port):
    assert port not in _foreign_ports()
