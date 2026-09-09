"""Project-goals QA: the docs must agree with the tree.

WHY THIS EXISTS, and it is not hypothetical. CLAUDE.md instructed every session
to read `docs/ARCHITECTURE.md` at startup. That file has never existed in this
repository. The instruction survived because nothing checked it, and every
session that followed it either silently skipped the file or wasted a step
looking for it.

A document is not a source of truth here - CLAUDE.md says so about test counts
already. This file extends the same discipline to the docs themselves: a pointer
that does not resolve, an ADR that is not indexed, or a "DONE" claim naming
something absent are all failures, not cosmetic drift.

DELIBERATELY NOT CHECKED: prose accuracy. No test can tell whether an ADR's
reasoning is sound. What it can tell is whether the things the prose POINTS AT
are really there, which is the class of error that actually accumulates.
"""
from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tests.test_guard_worktree_exclusion import swept_files

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"

#: Top-level directories a backticked path may start with. Anything else in
#: backticks is prose, a command or an identifier, not a repo path.
TREE_ROOTS = (
    "agents/",
    "core/",
    "data/",
    "docs/",
    "engines/",
    "headless/",
    "ingest/",
    "ops/",
    "scripts/",
    "shell/",
    "surface/",
    "tests/",
    "tools/",
)

#: Documents whose pointers must all resolve. These are the ones a session is
#: told to read, so a dead pointer in them costs real time.
#:
#: `.claude/commands/done.md` is here because it is the densest collection of
#: paths in the tree - it names the gates, the workflows, the hooks and the
#: hand-off - and it is read at the moment a session is wrapping up, which is
#: the worst possible time to discover a pointer went stale. It is not under
#: `docs/`, so the directory sweep below does not reach it.
GOVERNING_DOCS = (
    "CLAUDE.md",
    "README.md",
    "ROADMAP.md",
    ".claude/commands/done.md",
    # The three outward-facing root docs. They are the first thing a stranger
    # reads and they are the LEAST likely to be re-read by anyone here, so a
    # rotted path or a smuggled non-ASCII glyph would sit in them unnoticed.
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
)

#: File suffixes this tree actually contains. A backticked token whose last
#: segment carries a dot that is NOT one of these is a dotted symbol reference -
#: `module.function` - rather than a path, and must not be looked up on disk.
KNOWN_SUFFIXES = frozenset(
    {".py", ".md", ".json", ".js", ".toml", ".ini", ".txt", ".yml", ".yaml", ".xml", ".ps1", ".cmd", ".lnk", ".html"}
)

#: Paths that are legitimately absent from a clean checkout because something
#: CREATES them at run time. Each is exempt by name with a stated reason rather
#: than by a pattern, so the exemption cannot silently widen.
RUNTIME_ARTIFACTS = {
    # Written by ops/supervisor.py and headless/runner.py on the first pass.
    # Gitignored, and absent until something has actually run.
    "ops/runtime/health.json",
}


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _docs_markdown() -> list[Path]:
    """Every markdown file under `docs/` that THIS working tree owns.

    `swept_files` rather than a bare `rglob`: a nested checkout left inside
    `docs/` - a merged worktree, a stray extraction - is a second full copy of
    somebody else's documentation, and its pointers are not this tree's to
    resolve. Sweeping it makes these guards' colour a fact about that copy. See
    `tests/test_guard_worktree_exclusion.py` for the measurement and the proof.

    The non-emptiness assertion is here, at the single choke point every arm in
    this file walks through, rather than repeated six times: a corpus builder
    that silently stopped finding documents would let every pointer guard below
    pass forever, and zero out of zero is not a pass.
    """
    found = swept_files(REPO_ROOT / "docs", "*.md")
    assert found, "the docs/ sweep found no markdown at all - zero out of zero is not a pass"
    return found


def _governing_and_docs() -> list[Path]:
    """The governing documents plus the whole of `docs/`.

    `.claude/commands/done.md` is one of the governing documents and lives under
    a dot-directory, so it is named explicitly here and never reached by a
    sweep - which is also why the sweep's dot-directory exclusion cannot cost
    this file any coverage.
    """
    return [REPO_ROOT / d for d in GOVERNING_DOCS] + _docs_markdown()


def _backticked_paths(text: str) -> set[str]:
    """Every backticked token that looks like a path into this tree."""
    found: set[str] = set()
    for token in re.findall(r"`([^`\n]+)`", text):
        candidate = token.strip().rstrip(".,;:")
        if not candidate.startswith(TREE_ROOTS):
            continue
        # A glob or a wildcard is a pattern, not a path.
        if any(ch in candidate for ch in "*?[]<>"):
            continue
        # `engines/objectives.expand_character_goal` is a symbol, not a file.
        # Distinguished by suffix rather than by guessing at case or length.
        tail = candidate.rstrip("/").rsplit("/", 1)[-1]
        if "." in tail and not any(tail.endswith(suffix) for suffix in KNOWN_SUFFIXES):
            continue
        if candidate.rstrip("/") in RUNTIME_ARTIFACTS or candidate in RUNTIME_ARTIFACTS:
            continue
        found.add(candidate)
    return found


@functools.lru_cache(maxsize=1)
def _tracked_paths() -> tuple[frozenset[str], frozenset[str]]:
    """(files git stores, directories git stores something under).

    Shelled out ONCE and cached, never once per candidate path.

    `git ls-files` emits FILES ONLY - it never prints a directory - so a cited
    directory such as `docs/adr/` can never match its output literally, and a
    naive membership test against that output would call every directory in the
    docs untracked. The directory set is therefore DERIVED by walking each
    tracked file's parents, which is also the correct definition: git tracks a
    directory exactly when it tracks something under it.

    This reads the INDEX, not HEAD. A file that has been `git add`ed but not yet
    committed already appears. That is deliberate and is what keeps the arms
    below stable when several slices are merged and staged before the suite is
    run - newly created files that the merge has staged count as tracked.

    `cwd` is REPO_ROOT, computed from `__file__`, never the process working
    directory, because pytest can be invoked from anywhere. Inside a linked
    worktree this lists that worktree's own index, which is what we want.

    `-z` avoids core.quotePath escaping, which would otherwise mangle any path
    outside plain ASCII into a quoted form that stops matching the citation.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    files = frozenset(entry for entry in completed.stdout.split("\0") if entry)
    directories: set[str] = set()
    for entry in files:
        segments = entry.split("/")
        for depth in range(1, len(segments)):
            directories.add("/".join(segments[:depth]))
    return files, frozenset(directories)


def _is_tracked(candidate: str) -> bool:
    """Would a FRESH CLONE have this path? `.exists()` cannot answer that.

    GIT STORES NO EMPTY DIRECTORIES, so a directory can resolve on the machine
    that wrote the doc and be absent from every clone of it. That is not a
    hypothesis: the docs-guards CI job went red on the runner while this very
    file was green locally, because data/costs/ existed here and existed in no
    clone. Existence is a fact about one disk; trackedness is a fact about what
    everybody else receives, and only the second one is what a pointer promises.

    The trailing slash is stripped because the docs cite directories that way.
    """
    files, directories = _tracked_paths()
    normalised = candidate.rstrip("/")
    return normalised in files or normalised in directories


# ---------------------------------------------------------------------------
# Pointers resolve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", GOVERNING_DOCS)
def test_every_path_a_governing_doc_points_at_exists(doc: str):
    """The arm that would have caught docs/ARCHITECTURE.md on the day it landed."""
    missing = sorted(p for p in _backticked_paths(_read(doc)) if not (REPO_ROOT / p).exists())
    assert not missing, f"{doc} points at paths that do not exist: {missing}"


def test_every_path_the_docs_directory_points_at_exists():
    missing: list[str] = []
    for path in _docs_markdown():
        rel = path.relative_to(REPO_ROOT).as_posix()
        for candidate in _backticked_paths(path.read_text(encoding="utf-8")):
            if not (REPO_ROOT / candidate).exists():
                missing.append(f"{rel} -> {candidate}")
    assert not missing, "dead pointers in docs/: " + "; ".join(sorted(missing))


def test_the_pointer_sweep_is_not_vacuous():
    """A sweep that stopped recognising paths would pass forever."""
    found = _backticked_paths(_read("CLAUDE.md"))
    assert len(found) >= 5, f"only recognised {len(found)} paths in CLAUDE.md"
    assert "core/types.py" in found


def test_the_sweep_ignores_dotted_symbols_but_not_real_files():
    """The filter must be narrow. Dropping real paths would make it vacuous."""
    recognised = _backticked_paths(
        "`engines/objectives.expand_character_goal` `core/ports.py` `surface/` `agents/pity_engine/__main__.py`"
    )
    assert recognised == {"core/ports.py", "surface/", "agents/pity_engine/__main__.py"}


def test_every_runtime_artifact_exemption_is_still_referenced_somewhere():
    """An exemption for a path nobody mentions any more is dead weight, and dead
    exemptions are how an allowlist quietly stops describing reality."""
    corpus = "".join(
        path.read_text(encoding="utf-8")
        for path in _governing_and_docs()
    )
    for artifact in RUNTIME_ARTIFACTS:
        assert artifact in corpus, f"{artifact} is exempt but no longer referenced - drop the exemption"


# ---------------------------------------------------------------------------
# Pointers survive the clone
#
# The arms above ask whether a cited path is HERE. These ask whether it reaches
# ANYWHERE ELSE. Both are needed and neither implies the other: a path can be
# tracked and still be a broken pointer in some other sense, and a path can
# resolve perfectly on this disk while git stores nothing of it. The second case
# is the one that has actually cost this repository a red CI run.
#
# The exemption is not restated here. `_backticked_paths()` already drops
# RUNTIME_ARTIFACTS before any candidate reaches these arms, so the single
# by-name exemption with its stated reason is reused rather than duplicated -
# and it therefore cannot widen behind this file's back.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", GOVERNING_DOCS)
def test_every_path_a_governing_doc_points_at_is_tracked_by_git(doc: str):
    """Resolving on this machine is not the same as reaching a clone."""
    untracked = sorted(p for p in _backticked_paths(_read(doc)) if not _is_tracked(p))
    assert not untracked, f"{doc} points at paths git does not store, so a clone will not have them: {untracked}"


def test_every_path_the_docs_directory_points_at_is_tracked_by_git():
    untracked: list[str] = []
    for path in _docs_markdown():
        rel = path.relative_to(REPO_ROOT).as_posix()
        for candidate in _backticked_paths(path.read_text(encoding="utf-8")):
            if not _is_tracked(candidate):
                untracked.append(f"{rel} -> {candidate}")
    assert not untracked, "docs/ cites paths git does not store: " + "; ".join(sorted(untracked))


def test_the_trackedness_predicate_has_teeth():
    """Non-vacuity, proven against the PREDICATE and without touching the tree.

    There are no live violations, so the two sweeps above pass on sight and a
    predicate that had quietly stopped recognising anything would pass with
    them, forever. The honest way to show the guard bites is to hand it inputs
    whose answers are known independently - not to break the checkout to watch a
    test fail. This tree is shared with a merge and with sibling worktrees, and
    a test that mutates it is a test that can leave residue.

    Both directions are pinned, so neither a predicate stuck on True nor one
    stuck on False can survive this arm.
    """
    files, directories = _tracked_paths()
    assert len(files) > 50, f"git ls-files returned only {len(files)} entries - wrong cwd, or not a checkout"

    # TRUE for a tracked file, and for a tracked directory in the trailing-slash
    # form the docs actually use.
    assert _is_tracked("core/types.py")
    assert _is_tracked("docs/adr/")
    assert _is_tracked("docs/adr")

    # And this is exactly why the directory set has to be derived rather than
    # looked up: git ls-files lists files, so the directory is not in its output.
    assert "docs/adr" not in files, "git ls-files started emitting directories - the derivation may now be redundant"
    assert "docs/adr" in directories

    # FALSE for something that EXISTS on disk yet git stores nothing of. `.git`
    # is chosen because git structurally refuses to track it - it is the index,
    # not a thing in the index - so this case cannot be quietly cancelled later
    # by somebody committing the file. It is present in a plain checkout and in
    # a linked worktree alike, as a directory in the first and a pointer file in
    # the second, and `.exists()` is true for both.
    assert (REPO_ROOT / ".git").exists(), "no .git here, so this arm is not testing what it claims"
    assert not _is_tracked(".git")

    # FALSE for a plausible-looking path that is not there at all. Shaped so it
    # would clear every filter in _backticked_paths - under a tree root, with a
    # known suffix, no glob - which is what makes it a fair probe rather than a
    # token the parser would have discarded anyway.
    absent = "docs/no-such-doc-this-is-a-guard-sentinel.md"
    assert not (REPO_ROOT / absent).exists(), f"{absent} was created - pick another sentinel"
    assert not _is_tracked(absent)
    assert absent in _backticked_paths(f"see `{absent}` for details")


def test_the_trackedness_sweep_walked_a_real_corpus():
    """A parser that recognised nothing would make both sweeps above vacuous.

    So count what they actually walk. The floor is far below the corpus - it
    measured 140 citations across 16 documents when this arm was written - and
    is set low on purpose, because sibling slices add and reword citations
    constantly and this arm is here to catch a parser that found NOTHING, not to
    pin a number.
    """
    citations = 0
    for path in _governing_and_docs():
        citations += len(_backticked_paths(path.read_text(encoding="utf-8")))
    assert citations >= 80, f"the trackedness sweep only walked {citations} citations - the parser is broken"


# ---------------------------------------------------------------------------
# The ADR index is complete in both directions
# ---------------------------------------------------------------------------


def _adr_files() -> list[Path]:
    return sorted(ADR_DIR.glob("ADR-*.md"))


def test_every_adr_file_appears_in_the_index():
    index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
    missing = [p.name for p in _adr_files() if p.name not in index]
    assert not missing, f"ADRs exist but are not indexed: {missing}"


def test_every_adr_the_index_names_exists():
    index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
    named = set(re.findall(r"\(?(ADR-\d+-[a-z0-9-]+\.md)\)?", index))
    missing = sorted(name for name in named if not (ADR_DIR / name).exists())
    assert not missing, f"the index names ADRs that do not exist: {missing}"


def test_every_adr_referenced_anywhere_exists():
    """A citation of ADR-00N with no such ADR is a dangling argument."""
    numbers = {p.name.split("-")[1] for p in _adr_files()}
    dangling: list[str] = []
    for path in _governing_and_docs():
        text = path.read_text(encoding="utf-8")
        for number in set(re.findall(r"\bADR-(\d{3})\b", text)):
            if number not in numbers:
                dangling.append(f"{path.relative_to(REPO_ROOT).as_posix()} cites ADR-{number}")
    assert not dangling, "; ".join(sorted(set(dangling)))


def test_adr_numbers_are_unique_and_contiguous():
    """A duplicate or a gap means two decisions share a name, or one was lost."""
    numbers = sorted(int(p.name.split("-")[1]) for p in _adr_files())
    assert numbers == sorted(set(numbers)), f"duplicate ADR numbers: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"ADR numbering has a gap: {numbers}"


def test_every_adr_declares_a_status():
    for path in _adr_files():
        text = path.read_text(encoding="utf-8")
        assert re.search(r"\*\*Status:\*\*", text), f"{path.name} declares no status"


# ---------------------------------------------------------------------------
# ROADMAP claims
# ---------------------------------------------------------------------------


def test_roadmap_done_claims_name_something_that_exists():
    """A "DONE" beside a path that is not there is worse than no roadmap."""
    text = _read("ROADMAP.md")
    missing: list[str] = []
    for line in text.splitlines():
        if "DONE" not in line:
            continue
        for candidate in _backticked_paths(line):
            if not (REPO_ROOT / candidate).exists():
                missing.append(candidate)
    assert not missing, f"ROADMAP marks work DONE naming absent paths: {missing}"


#: Control bytes a text file may legitimately contain: tab, newline, carriage
#: return. Everything else below 0x09 is a control character with no business in
#: prose, and everything above 0x7E leaves 7-bit ASCII.
_ALLOWED_CONTROL = frozenset({0x09, 0x0A, 0x0D})


def test_the_docs_are_seven_bit_ascii():
    """Both ends of the range, and the lower end was a real blind spot.

    This originally tested `byte > 0x7E` only. A BEL character - 0x07, produced
    by a backslash-a escape in a non-raw Python string - was written into
    docs/LEDGER.md by the very entry describing that same bug in a test, and this
    guard said nothing. A check on one end of a range is a check with a
    documented hole in it.
    """
    offenders: list[str] = []
    for path in _governing_and_docs():
        raw = path.read_bytes()
        bad = sorted({b for b in raw if b > 0x7E or (b < 0x20 and b not in _ALLOWED_CONTROL)})
        if bad:
            offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()} {bad}")
    assert not offenders, f"non-ASCII or control bytes in docs: {offenders}"


def test_the_ascii_guard_catches_a_control_byte():
    """Non-vacuity, aimed at the hole that actually existed."""
    for byte in (0x07, 0x00, 0x1B):
        assert byte < 0x20 and byte not in _ALLOWED_CONTROL
    for byte in (0x09, 0x0A, 0x0D):
        assert byte in _ALLOWED_CONTROL
