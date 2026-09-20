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

import importlib.util
from pathlib import Path

import pytest

from core.walkprune import NEVER_WALKED_DIR_NAMES, is_pruned_dir_name

ROOT = Path(__file__).resolve().parents[1]
WATCH_INBOX = ROOT / "scripts" / "watch_inbox.py"


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
    """
    from tools import first_run_capture, gate_mutation_runner

    watch = _load_script(WATCH_INBOX, "walkprune_watch_inbox_under_test")

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
