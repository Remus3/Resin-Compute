"""Guards for `core/walkprune.py`, the single owner of the never-walked names.

WHY THIS EXISTS. Three independent recursive walks in this tree prune against a
directory-name list. Until 2026-09-20 each held its OWN hand-maintained
frozenset - 9 names, 6 names and 8 names - and nothing tied them together. The
newest was missing `.claude`, which the oldest had carried for longer, and
`.claude/` in this checkout holds 834 files including nested worktree
checkouts. The missing name was the symptom; three untied lists was the defect.

THESE ARMS ARE AIMED AT THE TIE, NOT AT THE CONTENTS. An arm that re-asserts
the nine literals here passes forever while a call site quietly stops reading
them - the drift `core/ports.py` names as the failure its own guards exist to
catch. So each arm below resolves the constant THROUGH the importing module and
compares identity with the owner.
"""
from __future__ import annotations

import ast
import importlib.util
import subprocess
from pathlib import Path

import pytest

from core.walkprune import NEVER_WALKED_DIR_NAMES, is_pruned_dir_name
from tests.conftest import require_git_repository

ROOT = Path(__file__).resolve().parents[1]
WATCH_INBOX = ROOT / "scripts" / "watch_inbox.py"
REPO_SWEEP = ROOT / "core" / "repo_sweep.py"

#: EVERY tracked module that imports `core/walkprune.py`, and what each one is.
#:
#: THIS IS A REGISTER, AND THE ARM BELOW DERIVES THE LIVE SET RATHER THAN
#: TRUSTING IT. `test_every_prune_site_derives_from_the_one_owner` is a
#: HAND-LIST of deriving sites, and a hand-list cannot notice a FIFTH site
#: appearing - the same class of defect as a register satisfiable by a shrunk
#: population. So the hand-list is kept for the per-site identity assertions,
#: which have to name a module to make one, and it is BOUNDED by
#: `test_no_unregistered_module_imports_the_owner` below, which AST-parses
#: every tracked `.py` and requires the live importer set to equal these keys.
#:
#: MEASURED COST, on this host at this slice's base: 164 tracked `.py` files,
#: parsed in 0.77 s wall. That is why the derivation is adopted instead of
#: being declared too expensive and replaced by a bare floor.
#:
#: WHAT THE DERIVATION CANNOT SEE, stated rather than papered over. It catches
#: a new DIRECT importer of `core.walkprune`. It does NOT catch a fifth walk
#: that grows its own hand-maintained name list and imports nothing - that
#: module would never appear here. `tests/test_guard_worktree_blindness.py` is
#: the arm aimed at THAT population, and it enumerates root-walking guards
#: rather than importers.
WALKPRUNE_IMPORTERS = {
    "core/repo_sweep.py": "prune site: composes the owner names into a sweep predicate",
    "scripts/watch_inbox.py": "prune site: the inbox walk",
    "tools/first_run_capture.py": "prune site: the first-run capture walk",
    "tools/gate_mutation_runner.py": "prune site: the gate mutation walk, minus its cache targets",
    "tests/test_walkprune.py": "this guard",
}


def _load_script(path: Path, name: str):
    """`scripts/` is not an importable package, so load the hook by path."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_owner_set_is_populated_and_already_casefolded():
    """Non-vacuity for every arm below, plus the invariant the helper assumes.

    `is_pruned_dir_name` folds only the INCOMING name. A member stored with a
    capital in it could therefore never match anything, which is a dead entry
    that no behavioural arm would notice.
    """
    assert len(NEVER_WALKED_DIR_NAMES) >= 8, (
        f"the owner set is empty or near-empty, so every arm here is vacuous: "
        f"{sorted(NEVER_WALKED_DIR_NAMES)}"
    )
    unfolded = [n for n in NEVER_WALKED_DIR_NAMES if n != n.casefold()]
    assert unfolded == [], f"these members can never match an incoming name: {unfolded}"


def test_every_prune_site_derives_from_the_one_owner():
    """THE DIVERGENCE ARM. Red the moment a site grows its own list again.

    Identity against the owner, not equality against a literal. A site that
    re-declares the same nine names by hand passes an equality check and is
    exactly the state this module was created to end.

    FOUR SITES NOW, NOT THREE. `core/repo_sweep.py` joined on 2026-10-02 at
    e9cbc62 as the production owner of the repository-root sweep predicate,
    and it composes these names rather than restating them. Its assertion here
    is that it BINDS the owner object; the shape of the composition is pinned
    separately by `test_the_sweep_skip_set_is_derived_and_restates_no_owner_name`,
    because a module can keep the import alive and still hand-list beside it.

    THIS LIST IS NOT SELF-BOUNDING. It cannot notice a fifth site appearing,
    which is why `test_no_unregistered_module_imports_the_owner` derives the
    live importer set and holds this register to it.
    """
    from core import repo_sweep
    from tools import first_run_capture, gate_mutation_runner

    watch = _load_script(WATCH_INBOX, "walkprune_watch_inbox_under_test")

    assert repo_sweep.NEVER_WALKED_DIR_NAMES is NEVER_WALKED_DIR_NAMES, (
        "core/repo_sweep.py no longer binds the owner set at all, so its "
        "SWEEP_SKIP_DIRS is a second hand-maintained name list"
    )
    assert NEVER_WALKED_DIR_NAMES <= repo_sweep.SWEEP_SKIP_DIRS, (
        "core/repo_sweep.py's sweep set has stopped covering every owner name, "
        "so a directory this tree never walks is now walked by the root sweeps"
    )
    assert watch.PRUNED_DIR_NAMES is NEVER_WALKED_DIR_NAMES, (
        "scripts/watch_inbox.py stopped deriving its prune set from "
        "core/walkprune.py and is drifting on its own again"
    )
    assert first_run_capture._WALK_SKIP_DIRS is NEVER_WALKED_DIR_NAMES, (
        "tools/first_run_capture.py stopped deriving its prune set from "
        "core/walkprune.py and is drifting on its own again"
    )
    assert gate_mutation_runner._WALK_SKIP == NEVER_WALKED_DIR_NAMES - gate_mutation_runner._CACHE_DIRS, (
        "tools/gate_mutation_runner.py's prune set is no longer the owner set "
        "minus its own cache targets, so it is a fourth hand-maintained list"
    )


def test_the_one_divergent_site_diverges_only_by_its_own_cache_targets():
    """The single principled divergence, pinned so it cannot silently widen.

    `purge_caches` exists to DELETE `__pycache__` and `.pytest_cache`. Pruning
    them would stop it finding its own targets and reinstate the stale-bytecode
    defect its docstring records. Every OTHER name must still be shared, and
    this arm is what stops "gate needs a different set" becoming a licence to
    drop any name from it.
    """
    from tools import gate_mutation_runner

    missing = NEVER_WALKED_DIR_NAMES - gate_mutation_runner._WALK_SKIP

    assert missing == gate_mutation_runner._CACHE_DIRS, (
        f"gate_mutation_runner diverges from the owner set on names that are "
        f"NOT its cache targets: {sorted(missing - gate_mutation_runner._CACHE_DIRS)}"
    )
    assert gate_mutation_runner._CACHE_DIRS <= NEVER_WALKED_DIR_NAMES, (
        "a cache target is not in the owner set, so the subtraction is not the "
        "relationship it is written as"
    )


def test_the_catastrophic_names_are_all_present():
    """The four that are expensive rather than merely noisy.

    `.claude` is named outright because its absence from one of the three lists
    is the defect that created this module, and an arm that only checks the
    tie would go green again if all three dropped it together.
    """
    for name in (".git", ".claude", ".venv", "node_modules"):
        assert name in NEVER_WALKED_DIR_NAMES, f"{name} is not pruned anywhere"


@pytest.mark.parametrize("name", [".GIT", "__PYCACHE__", ".Venv", "Node_Modules", ".CLAUDE"])
def test_the_match_is_casefolded_because_this_platform_is(name):
    """NTFS preserves case on disk while comparing case-insensitively.

    So `.GIT/` IS `.git/` to every Windows API and to `open()`, and is a
    different string to a bare `in`. Measured 2026-09-20: a drop carrying
    `.GIT/` hashed identically with the case-sensitive prune live and with the
    prune removed entirely - it never fired.
    """
    assert is_pruned_dir_name(name), f"{name} escapes the prune on a case-insensitive filesystem"


@pytest.mark.parametrize(
    "name", ["pycache", "git", "venv-notes", "node_modules_readme", "claude", "gitignore"]
)
def test_the_survivors_the_casefold_must_not_swallow(name):
    """THE SURVIVOR ARM. A sweep that prunes everything scores 100 percent.

    Every name here is a legitimate directory that must still be walked. An
    adversary killed a substring mutant against this arm's sibling in
    `tests/test_watch_inbox_walk_pruning.py`, so it is doing real work: a
    casefold must not quietly widen into a substring or prefix match.
    """
    assert not is_pruned_dir_name(name), f"{name} was pruned as collateral"


def test_a_narrower_set_still_matches_through_the_same_fold():
    """The `names` parameter exists so a divergent caller keeps ONE match rule.

    Without it, `gate_mutation_runner` would compare its narrower set with a
    bare `in` and be case-sensitive again - the exact bug, reintroduced at the
    one site that was allowed to differ.
    """
    narrow = NEVER_WALKED_DIR_NAMES - frozenset({"__pycache__"})

    assert is_pruned_dir_name(".GIT", narrow)
    assert not is_pruned_dir_name("__PYCACHE__", narrow), (
        "the narrower set still pruned a name it deliberately excludes"
    )


# ---------------------------------------------------------------------------
# THE DERIVATION ITSELF. Not what the sets CONTAIN - whether one is COMPUTED
# from the other, which no comparison of values can answer.
# ---------------------------------------------------------------------------


def _assignment_value(module_path: Path, target: str) -> ast.expr:
    """The right-hand side of the LAST module-level assignment to `target`."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == target for t in node.targets)
    ]
    assert found, f"{module_path.name} has no module-level assignment to {target}"
    return found[-1]


def test_the_sweep_skip_set_is_derived_and_restates_no_owner_name():
    """THE ARM NO VALUE CHECK CAN REPLACE, and the one measured to be missing.

    `core/repo_sweep.py` builds `SWEEP_SKIP_DIRS` as the owner set unioned
    with two build-output names. Replacing that expression with a hand-written
    literal of the same eleven names and dropping the import produces a set
    that is VALUE-EQUAL to the derived one, so every behavioural arm in this
    tree answers identically. Measured on this slice's base: the whole `tests`
    suite stayed at 3162 passed, 4 skipped with that mutation live. The
    derivation was therefore unguarded, and a second hand-record that happens
    to agree today is the exact shape that has rotted repeatedly here.

    THIS IS A SYNTACTIC CLAIM AND IS WRITTEN AS ONE. It reads the assignment
    expression and asserts two things about it: the owner is REFERENCED by
    name, and no string literal in it is an owner name. It cannot see a
    derivation laundered through an alias assigned elsewhere in the module,
    and it is not trying to - the identity assertion in
    `test_every_prune_site_derives_from_the_one_owner` covers the binding, and
    this covers the composition.

    NO THIRD HAND-RECORD. The extras are never typed here. They are read off
    the source as literals and cross-checked against set arithmetic on the two
    live constants, so the two sides are derived independently and an arm that
    restated the eleven names - making the problem worse rather than better -
    is impossible to write in this shape.
    """
    from core.repo_sweep import SWEEP_SKIP_DIRS

    value = _assignment_value(REPO_SWEEP, "SWEEP_SKIP_DIRS")
    referenced = {node.id for node in ast.walk(value) if isinstance(node, ast.Name)}
    literals = {
        node.value
        for node in ast.walk(value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert "NEVER_WALKED_DIR_NAMES" in referenced, (
        f"core/repo_sweep.py builds SWEEP_SKIP_DIRS without referencing the owner set, "
        f"so it is a second hand-maintained list of directory names. It referenced: "
        f"{sorted(referenced)}"
    )
    restated = sorted(literals & NEVER_WALKED_DIR_NAMES)
    assert restated == [], (
        f"core/repo_sweep.py spells out owner names as literals beside the derivation, "
        f"so those names now live in two places and can drift apart: {restated}"
    )
    extras = set(SWEEP_SKIP_DIRS) - NEVER_WALKED_DIR_NAMES
    assert literals == extras, (
        f"the names written literally in the assignment are not the names the finished "
        f"set adds to the owner set. Literal in source: {sorted(literals)}; actually "
        f"added: {sorted(extras)}. One of the two is arriving from somewhere unaccounted for"
    )


def _tracked_python_files() -> list[str]:
    """Every tracked `.py`, as forward-slash paths relative to the repo root.

    `git ls-files` and never an `rglob`: an untracked scratch file or a nested
    worktree checkout must not be able to add a phantom importer to the
    derived set, and `tests/test_no_sibling_names.py` builds its corpus the
    same way for the same reason.
    """
    completed = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _imports_the_owner(relative_path: str) -> bool:
    """Whether this tracked module imports `core.walkprune` directly.

    AST rather than a text search, so a mention of the module name inside a
    docstring, a comment or a string literal - of which this tree has many,
    including several in this very file - cannot register as an import.
    """
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.walkprune":
            return True
        if isinstance(node, ast.Import) and any(a.name == "core.walkprune" for a in node.names):
            return True
    return False


def test_no_unregistered_module_imports_the_owner():
    """THE BOUND ON THE HAND-LIST, so a FIFTH site cannot appear unnoticed.

    `test_every_prune_site_derives_from_the_one_owner` names its sites by
    hand, because a per-site identity assertion has to name a module to make
    one. A hand-list of sites is satisfiable by a shrunk population: it goes
    green forever while a new walk is added beside it. This arm removes that
    by DERIVING the live importer set from the tree and requiring it to equal
    the register, in both directions - a new importer is an unregistered site,
    and a vanished importer is a stale register entry.

    THE COST WAS MEASURED, NOT ESTIMATED: 164 tracked `.py` parsed in 0.77 s
    on this host at this slice's base. Cheap enough that the alternative -
    keeping a bare hand-list and adding only a numeric floor - was rejected.
    A floor says how MANY sites there are and never which, so a site swapped
    for a different one passes it.

    WHAT IT DOES NOT COVER is in `WALKPRUNE_IMPORTERS`' own comment: a fifth
    walk that imports nothing and grows its own name list never appears in
    this set at all.
    """
    require_git_repository()

    tracked = _tracked_python_files()
    assert len(tracked) > 50, (
        f"git ls-files returned only {len(tracked)} python files, which is too few to be "
        f"this checkout - wrong cwd, or not a checkout, and this arm would pass vacuously"
    )

    live = {path for path in tracked if _imports_the_owner(path)}
    registered = set(WALKPRUNE_IMPORTERS)

    unregistered = sorted(live - registered)
    assert unregistered == [], (
        f"these modules import core/walkprune.py and are not in WALKPRUNE_IMPORTERS, so a "
        f"new prune site has appeared without anything checking that it derives its names "
        f"rather than hand-maintaining them: {unregistered}"
    )
    vanished = sorted(registered - live)
    assert vanished == [], (
        f"these modules are registered as importing core/walkprune.py and no longer do, so "
        f"either a site has gone back to a hand-maintained list or the register is stale "
        f"and is shrinking the population the identity arm covers: {vanished}"
    )
    assert len(registered) >= 5, (
        f"the register has shrunk below the five importers measured at e9cbc62, so the "
        f"identity arm above may be covering fewer sites than it did: {sorted(registered)}"
    )
