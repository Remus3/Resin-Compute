"""The two CI workflows must COVER every push between them, with no hole.

`ci.yml` carries `paths-ignore: ['**/*.md']` and `docs-guards.yml` carries the
matching `paths: ['**/*.md']`. That pairing is what makes a docs-only push cheap
without making it unverified: `ci` declines it and `docs-guards` picks it up.

THE FAILURE THIS GUARDS IS A COVERAGE HOLE, NOT A RED BUILD. Add a second entry
to `ci.yml`'s `paths-ignore` - say `'docs/**'` - and forget the matching `paths`
entry in `docs-guards.yml`, and pushes touching that path fire NEITHER workflow.
Nothing goes red. Nothing warns. The tree simply stops being checked for a whole
class of file, and the only evidence is an absence of runs that nobody is
looking for.

`ci.yml` already carries a COMMENT instructing the author to add the matching
entry in the same commit. An instruction is not a guard: it is read only by
someone who already opened the right file. Riot Commander enforces this
mechanically in CI (its "docs-guard complement is wired" step); this tree had
the comment and no enforcement until now.

Parsed with a line scanner rather than a YAML library because this repository is
stdlib-only at runtime and PyYAML is not a dependency. The scan is deliberately
narrow - it reads the two `on:` trigger blocks and nothing else.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

CI = WORKFLOWS / "ci.yml"
DOCS_GUARDS = WORKFLOWS / "docs-guards.yml"


def _trigger_patterns(path: Path, key: str) -> set[str]:
    """Every glob listed under `key:` inside the workflow's `on:` block.

    Stops at the first line that is neither a list item nor a comment nor
    blank, so a `paths-ignore:` under `push:` and another under
    `pull_request:` are both collected while the rest of the file is ignored.
    """
    found: set[str] = set()
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, raw in enumerate(lines):
        if raw.strip() != f"{key}:":
            continue
        for follower in lines[index + 1:]:
            stripped = follower.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith("- "):
                break
            found.add(stripped[2:].strip().strip("'\""))
    return found


def test_both_workflow_files_exist():
    """The complement is meaningless if one half has been renamed away."""
    assert CI.is_file(), f"{CI} is missing"
    assert DOCS_GUARDS.is_file(), f"{DOCS_GUARDS} is missing"


def test_the_parser_actually_recovers_the_known_pairing():
    """Non-vacuity. A parser that silently found nothing would pass everything
    below it forever, which is the same class of bug the pairing itself guards."""
    ignored = _trigger_patterns(CI, "paths-ignore")
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    assert "**/*.md" in ignored, f"ci.yml paths-ignore parsed as {ignored}"
    assert "**/*.md" in covered, f"docs-guards.yml paths parsed as {covered}"


def test_every_path_ci_ignores_is_covered_by_docs_guards():
    """THE GUARD. A pattern in neither workflow is a class of file nobody checks."""
    ignored = _trigger_patterns(CI, "paths-ignore")
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    uncovered = sorted(ignored - covered)
    assert not uncovered, (
        f"ci.yml declines {uncovered} and docs-guards.yml does not pick them up, so a "
        f"push touching those paths fires NEITHER workflow and is never checked. This "
        f"does not go red on its own - it goes SILENT. Add the matching entry to "
        f"{DOCS_GUARDS.name}'s `paths:` in the same commit, as ci.yml's own comment says."
    )


@pytest.mark.parametrize("mechanism", ["docs-guards.yml", "precommit_gate.py"])
def test_docs_guards_reruns_itself_when_its_own_mechanism_changes(mechanism: str):
    """An edit to the checker must re-run the checker.

    Otherwise a change that breaks the banned-glyph engine lands green, because
    the only workflow that exercises it was not triggered by the file that
    changed it.
    """
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    assert any(mechanism in pattern for pattern in covered), (
        f"docs-guards.yml does not re-run itself when {mechanism} changes; "
        f"its paths are {sorted(covered)}"
    )


def test_ci_still_ignores_markdown_so_the_complement_is_load_bearing():
    """If ci.yml stopped ignoring .md this whole file would be guarding nothing.

    Stated as its own arm so that the day someone deletes the `paths-ignore`,
    this fails loudly and points at the four tests above rather than leaving
    them quietly tautological.
    """
    assert "**/*.md" in _trigger_patterns(CI, "paths-ignore"), (
        "ci.yml no longer ignores markdown. That may be correct, but the "
        "ci/docs-guards complement this module guards no longer exists - "
        "re-read whether docs-guards.yml is still needed at all."
    )


def test_the_scanner_ignores_keys_outside_the_trigger_block():
    """The `paths` word appears in prose and in step bodies; only triggers count."""
    assert not any(
        pattern.startswith("name:") or pattern.endswith(":")
        for pattern in _trigger_patterns(DOCS_GUARDS, "paths")
    )
