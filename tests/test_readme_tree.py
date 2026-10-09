"""The repository trees must describe the repository that ships.

TWO TREES, one parser (MAIN 2246 ORDER s3 item 4). `README.md` carries the
short form - top-level folders plus the four entry points - and
`docs/OVERVIEW.md` carries the per-file tree that used to sit in the README.
Every arm below runs against both, so moving a line between them can never
take it out from under the guard.

WHY THIS EXISTS, and it is measured rather than hypothetical. The tree in
README.md is a FENCED BLOCK, so `tests/test_docs_consistency.py` never sees it -
that sweep reads backticked tokens, and nothing inside a fence is backticked.
The block therefore drifted with no guard on it at all: it named
`agents/pity_engine/pity.py`, which has never existed in this repository, and it
omitted `surface/` and `shell/` entirely, so a stranger reading it never learned
the dashboard or the Electron companion were there.

EXISTENCE IS THE WRONG TEST, and this repository already paid for that lesson.
Every path check in `tests/test_docs_consistency.py` calls `.exists()`, which is
true for a directory git does not store. Git stores no empty directories, so a
path can resolve on the machine that authored it and be absent in every clone -
which is exactly how `docs-guards` went red on the CI runner while the same
test was green locally. The arms below therefore assert TRACKEDNESS, via
`git ls-files`, and a directory counts as tracked only if git tracks something
underneath it.

THIS GUARD IS ONE-DIRECTIONAL, AND DELIBERATELY SO. It asserts that every path
NAMED IN A TREE exists and is tracked. It does NOT assert the converse - that
every tracked file appears in the tree - because the converse couples this test
to every unrelated addition anywhere in the repository. A session that adds an
ADR, a test module or a fixture would turn this file red through no fault of its
own, and a guard that fails for reasons outside its subject is a guard people
learn to ignore. The single bounded exception is stated at
`test_every_top_level_directory_is_named`, with its own reasoning.

DELIBERATELY NOT CHECKED: the description column. The parser reads the first
token on a line and discards the rest, so rewording a description is free. This
guards PATHS, not prose.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The heading each tree lives under. The block is found by heading rather than
#: by position, so reordering a document does not break this.
TREE_HEADING = "## Repository tree"

#: The documents carrying a tree: the minimum number of paths the parser must
#: recover from each (the non-vacuity floor), and paths each must contain.
TREE_DOCS: dict[str, tuple[int, tuple[str, ...]]] = {
    "README.md": (
        20,
        (
            "agents/pity_engine/__main__.py",
            "headless/runner.py",
            "ops/supervisor.py",
            "surface/__main__.py",
            "shell/",
            "tests/",
        ),
    ),
    "docs/OVERVIEW.md": (40, ("core/types.py", "surface/", "shell/", "tests/", "README.md")),
}

_DOCS = sorted(TREE_DOCS)

#: The root marker. A placeholder, not a directory name: a checkout can live
#: anywhere under any name, and the repository slug appears once, in the README
#: Quickstart. The block once rooted itself at `resin-compute/`, which was
#: neither the repository nor any real checkout.
TREE_ROOT = "<checkout>/"

#: One path segment. Leading dot allowed - `.githooks/`, `.gitignore` and
#: `.claude/` are all real entries.
_SEG = r"\.?[A-Za-z0-9_][A-Za-z0-9_.-]*"

#: A tree entry: one or more segments, optionally trailing-slashed for a
#: directory. Multi-segment entries are not an edge case - a tree collapses a
#: single-child chain as `agents/pity_engine/` or `.github/workflows/` rather
#: than spending two lines on it. Matching only ONE segment here is not a
#: harmless narrowing: the collapsed line is skipped, the stack keeps whatever
#: directory came before it, and every child silently reattaches to the wrong
#: parent. That produced a first run of this file blaming `core/pity.py` for a
#: file the tree had filed under `agents/pity_engine/`.
_SEGMENT = re.compile(rf"{_SEG}(?:/{_SEG})*/?")


# ---------------------------------------------------------------------------
# Reading a tree out of a document
# ---------------------------------------------------------------------------


def _doc(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _tree_block(doc: str) -> str:
    """The raw text inside the fence under the Repository tree heading."""
    _, heading, after = _doc(doc).partition(TREE_HEADING)
    assert heading, f"{doc} has no {TREE_HEADING!r} section"
    _, opened, rest = after.partition("```")
    assert opened, f"the {doc} Repository tree section opens no fence"
    # Drop the remainder of the opening fence line, which may carry a language
    # tag. Left in place, a tag like `text` parses as a path and fails absurdly.
    rest = rest.split("\n", 1)[1] if "\n" in rest else ""
    block, closed, _ = rest.partition("```")
    assert closed, f"the {doc} Repository tree fence is never closed"
    return block


def _tree_paths(doc: str) -> list[str]:
    """Repo-relative paths named by the tree, rebuilt from its indentation.

    Directories keep their trailing slash so the trackedness predicate can tell
    them apart from files. A line whose first token does not look like a path
    segment is skipped rather than rejected: descriptions are free text, and a
    parser that hard-failed on prose would be a parser nobody could edit around.
    Silent over-skipping is caught by the non-vacuity arm below, not here.
    """
    stack: list[tuple[int, str]] = []
    found: list[str] = []
    for raw in _tree_block(doc).splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        token = raw.strip().split()[0]
        if not _SEGMENT.fullmatch(token):
            continue
        if indent == 0:
            # The root marker names the checkout directory, not a path inside
            # the repository. It is asserted separately and never resolved.
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        prefix = "".join(f"{name}/" for _, name in stack)
        if token.endswith("/"):
            stack.append((indent, token.rstrip("/")))
            found.append(f"{prefix}{token}")
        else:
            found.append(f"{prefix}{token}")
    return found


# ---------------------------------------------------------------------------
# Trackedness, which is a stronger claim than existence
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _tracked() -> frozenset[str]:
    """Every path git actually stores, as `git ls-files` reports it."""
    require_git_repository()
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(line.strip() for line in result.stdout.splitlines() if line.strip())


def _is_tracked(path: str) -> bool:
    """A file is tracked if git lists it. A directory is tracked if git lists
    anything underneath it - an EMPTY DIRECTORY IS NOT IN THE REPOSITORY, so a
    directory that resolves locally can still be absent from every clone."""
    bare = path.rstrip("/")
    if path.endswith("/"):
        prefix = f"{bare}/"
        return any(entry.startswith(prefix) for entry in _tracked())
    return bare in _tracked()


# ---------------------------------------------------------------------------
# The forward arms - everything a tree names is really there
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", _DOCS)
def test_the_tree_roots_itself_at_the_placeholder(doc: str):
    """`resin-compute/` was neither the repo name nor any real checkout."""
    first = next(line.strip() for line in _tree_block(doc).splitlines() if line.strip())
    assert first.split()[0] == TREE_ROOT, f"{doc} tree roots itself at {first.split()[0]!r}"


@pytest.mark.parametrize("doc", _DOCS)
def test_every_path_the_tree_names_exists(doc: str):
    missing = sorted(p for p in _tree_paths(doc) if not (REPO_ROOT / p).exists())
    assert not missing, f"the {doc} tree names paths that do not exist: {missing}"


@pytest.mark.parametrize("doc", _DOCS)
def test_every_path_the_tree_names_is_tracked_by_git(doc: str):
    """The arm that existence cannot provide. A path present only on the machine
    that wrote it is a path every clone is missing."""
    untracked = sorted(p for p in _tree_paths(doc) if not _is_tracked(p))
    assert not untracked, f"the {doc} tree names paths git does not store: {untracked}"


# ---------------------------------------------------------------------------
# The one bounded completeness arm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", _DOCS)
def test_every_top_level_directory_is_named(doc: str):
    """Bounded on purpose, and the bound is the point.

    The reported defect was whole limbs missing - `surface/`, `shell/` and
    `.claude/` were absent, so the dashboard and the Electron companion were
    invisible to a reader. Catching that needs some completeness check, and a
    full converse is refused above for good reason.

    Top-level directories are the narrowest cut that catches it. There are a
    handful, a new one is an architectural event rather than routine churn, and
    adding a file to a directory that is already named - an ADR, a test module,
    a fixture - does not touch this set. So this arm stays quiet during ordinary
    work and speaks only when a limb appears or disappears.
    """
    tracked_dirs = {entry.split("/", 1)[0] for entry in _tracked() if "/" in entry}
    named = {p.rstrip("/").split("/", 1)[0] for p in _tree_paths(doc)}
    missing = sorted(tracked_dirs - named)
    assert not missing, f"top-level directories absent from the {doc} tree: {missing}"


# ---------------------------------------------------------------------------
# Non-vacuity, proven at the predicate level and without mutating the tree
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", _DOCS)
def test_the_parser_actually_finds_the_tree(doc: str):
    """A parser that quietly stopped recognising lines would pass every arm
    above forever. This is the arm that notices."""
    floor, expected_paths = TREE_DOCS[doc]
    paths = _tree_paths(doc)
    assert len(paths) >= floor, f"only parsed {len(paths)} paths out of the {doc} tree"
    for expected in expected_paths:
        assert expected in paths, f"the parser did not recover {expected!r} from {doc}"


def test_the_parser_discards_the_description_column():
    """Proof that rewording a description cannot break this file."""
    paths = _tree_paths("docs/OVERVIEW.md")
    assert "README.md" in paths
    # The word "the" opens README.md's own description in the OVERVIEW block.
    # If the parser read past the first token it would surface here as a path.
    assert not any(p.endswith("/the") or p == "the" for p in paths)
    # README entry lines open their description with `ENTRY:`; a parser reading
    # past the first token would reattach it as a child path.
    assert not any("ENTRY" in p for p in _tree_paths("README.md"))


def test_the_readme_tree_is_the_short_form():
    """Item 4 of the order: the README tree stays short. The per-file listing
    lives in docs/OVERVIEW.md and must be the larger of the two."""
    short, full = _tree_paths("README.md"), _tree_paths("docs/OVERVIEW.md")
    assert len(short) < 30, f"the README tree has grown back to {len(short)} paths"
    assert len(full) > len(short)


def test_trackedness_is_stricter_than_existence():
    """The whole reason this file exists rather than reusing `.exists()`.

    `.git` is present in every checkout and tracked in none, so it separates the
    two predicates without touching the working tree. Nothing here writes,
    deletes or renames anything - a guard that mutates the repository to prove
    itself is a guard that can break a suite running beside it.
    """
    dot_git = REPO_ROOT / ".git"
    if not dot_git.exists():
        pytest.skip("not a git checkout")
    assert not _is_tracked(".git"), "`git ls-files` should never list .git"
    assert not _is_tracked(".git/"), "a directory git does not store is not tracked"


def test_the_trackedness_predicate_answers_both_ways():
    """A predicate stuck on True makes every arm above vacuous, and one stuck on
    False would fail them loudly. Both directions are pinned."""
    assert _is_tracked("core/types.py")
    assert _is_tracked("core/")
    assert _is_tracked("docs/adr/")
    # Never existed, never tracked. This is the file CLAUDE.md told every
    # session to read for months, which is what started the docs-guard work.
    assert not _is_tracked("docs/ARCHITECTURE.md")
    # Exists as a directory in a working checkout, stored by git as nothing.
    assert not _is_tracked("ops/runtime/health.json")


def test_the_tracked_listing_is_not_empty():
    """If `git ls-files` returned nothing, every trackedness arm would invert."""
    assert len(_tracked()) >= 50, f"git lists only {len(_tracked())} files"
