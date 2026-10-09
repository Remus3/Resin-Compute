"""The `plumbing` and `reads_docs` markers are applied centrally, and stay honest.

MAIN 2246 ORDER section 2, PERF-AUDIT items 2 and 3. Both markers come from
the module lists in `tests/_markers.py`, applied by
`pytest_collection_modifyitems` in `tests/conftest.py`, so no test module
carries a decorator and a module can be reclassified in one place.

  - `plumbing`: the module's subject lives under a plumbing root (tools/,
    headless/, scripts/, ops/, .githooks/, .github/, .claude/). CI and the
    pre-push hook run these only when such a root changes; the nightly
    schedule always runs them.
  - `reads_docs`: the module reads tracked .md content. The docs-guards
    workflow runs exactly these on a docs-only push.

THE OLD DOCS-LANE GREP SURVIVES AS A GUARD, not as the selector. Any module
whose text matches it must be either marked `reads_docs` or listed in
`DOCS_GREP_EXEMPT` (it mentions markdown only in prose). A new module that
mentions a .md path therefore reddens here until someone decides which it is.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests import _markers
from tests.conftest import is_slow, marker_for_module

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS = REPO_ROOT / "tests"

#: The docs-guards selection as it stood before the marker, transcribed from
#: its `grep -qE` line. Built by concatenation so this module's own source
#: does not match it.
DOCS_GREP = re.compile(r"\." + "md" + r"([^a-zA-Z0-9]|$)")


def _modules() -> list[str]:
    return sorted(f"tests/{p.name}" for p in TESTS.glob("test_*.py"))


def _grep_hits() -> set[str]:
    hits = set()
    for mod in _modules():
        text = (REPO_ROOT / mod).read_text(encoding="utf-8", errors="replace")
        if any(DOCS_GREP.search(line) for line in text.splitlines()):
            hits.add(mod)
    return hits


# ---------------------------------------------------------------------------
# Registry hygiene
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["PLUMBING", "READS_DOCS", "DOCS_GREP_EXEMPT"]
)
def test_every_listed_module_exists(name: str):
    listed = getattr(_markers, name)
    assert listed, f"{name} is empty, so the marker it feeds marks nothing"
    stale = sorted(m for m in listed if not (REPO_ROOT / m).is_file())
    assert not stale, f"{name} lists modules that are not on disk: {stale}"


def test_reads_docs_and_its_exemption_list_are_disjoint():
    both = sorted(_markers.READS_DOCS & _markers.DOCS_GREP_EXEMPT)
    assert not both, f"marked reads_docs AND exempt from it: {both}"


def test_every_listed_module_is_spelled_as_a_repo_path():
    for name in ("PLUMBING", "READS_DOCS", "DOCS_GREP_EXEMPT"):
        bad = sorted(
            m for m in getattr(_markers, name)
            if not re.fullmatch(r"tests/test_[a-z0-9_]+\.py", m)
        )
        assert not bad, f"{name} carries entries the hook cannot match: {bad}"


# ---------------------------------------------------------------------------
# The grep guard
# ---------------------------------------------------------------------------


def test_every_module_the_old_grep_selects_is_marked_or_exempt():
    unclassified = sorted(_grep_hits() - _markers.READS_DOCS - _markers.DOCS_GREP_EXEMPT)
    assert not unclassified, (
        "these modules mention a markdown path and are neither marked reads_docs nor "
        "listed in DOCS_GREP_EXEMPT in tests/_markers.py. Decide which: a module that "
        f"reads a tracked .md belongs in READS_DOCS. {unclassified}"
    )


def test_every_exemption_is_still_a_grep_hit():
    """An exemption for a module the grep no longer selects is dead weight."""
    stale = sorted(_markers.DOCS_GREP_EXEMPT - _grep_hits())
    assert not stale, f"DOCS_GREP_EXEMPT entries the grep no longer selects: {stale}"


def test_the_grep_guard_fires_on_an_unclassified_hit(tmp_path: Path):
    """Non-vacuity: the pattern selects a planted mention and spares a neighbour."""
    assert any(DOCS_GREP.search(ln) for ln in ['p = ROOT / "README' + '.md"'])
    assert not any(DOCS_GREP.search(ln) for ln in ["x = 'a.mdx'", "md = 1"])
    assert _grep_hits(), "non-vacuity: the real tree has grep hits to classify"


def test_the_marker_shrinks_the_docs_lane():
    """The point of item 3: the docs lane is no longer every grep hit."""
    assert len(_markers.READS_DOCS) < len(_grep_hits())


# ---------------------------------------------------------------------------
# Application: the conftest hook maps a module to its markers
# ---------------------------------------------------------------------------


def test_marker_for_module_reads_the_registry():
    plumbing = next(iter(sorted(_markers.PLUMBING)))
    docs = next(iter(sorted(_markers.READS_DOCS)))
    assert "plumbing" in marker_for_module(plumbing)
    assert "reads_docs" in marker_for_module(docs)
    assert marker_for_module("tests/test_core_resin.py") == ()


def test_this_session_applied_the_markers(request: pytest.FixtureRequest):
    """End to end over the real collection: this module carries neither."""
    names = {m.name for m in request.node.iter_markers()}
    assert "plumbing" not in names and "reads_docs" not in names


def test_a_plumbing_module_really_is_marked_at_collection(pytestconfig: pytest.Config):
    """The markers are declared in pytest.ini, so --strict-markers accepts them."""
    declared = "\n".join(pytestconfig.getini("markers"))
    for name in ("plumbing", "reads_docs", "slow"):
        assert re.search(rf"^{name}:", declared, re.M), f"{name} is not declared"


def test_every_slow_entry_names_a_test_that_exists():
    assert _markers.SLOW, "non-vacuity: `slow` was declared and used zero times before this"
    missing = []
    for nodeid in sorted(_markers.SLOW):
        module, _, name = nodeid.partition("::")
        path = REPO_ROOT / module
        if not name or not path.is_file():
            missing.append(nodeid)
            continue
        if not re.search(rf"^def {re.escape(name)}\(", path.read_text(encoding="utf-8"), re.M):
            missing.append(nodeid)
    assert not missing, f"SLOW names tests that are not defined: {missing}"


def test_is_slow_ignores_a_parametrize_suffix_and_spares_neighbours():
    nodeid = sorted(_markers.SLOW)[0]
    module, _, name = nodeid.partition("::")
    assert is_slow(module, name)
    assert is_slow(module, f"{name}[case-1]")
    assert not is_slow(module, f"{name}_and_more")
    assert not is_slow("tests/test_core_resin.py", name)


def test_the_product_suite_is_not_mostly_plumbing_by_accident():
    """A registry that swallowed the product modules would hide them from CI pushes."""
    product = {"tests/test_core_resin.py", "tests/test_engines_scheduler.py", "tests/test_ingest_mapper.py"}
    assert not product & _markers.PLUMBING
