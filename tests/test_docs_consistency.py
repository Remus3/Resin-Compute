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


# ---------------------------------------------------------------------------
# Line-number citations - the `path:NNN` form
#
# WHY THIS SECTION EXISTS, and it is measured rather than hypothetical.
# `_backticked_paths()` above SILENTLY DROPS every `path:NNN` token. Trace it
# with `tools/precommit_gate.py:398`: `tail` becomes `precommit_gate.py:398`,
# which contains a dot and ends with NO entry in KNOWN_SUFFIXES, so the function
# hits its `continue`. The token never reaches the existence check or the
# trackedness check. So the guard whose entire job is policing citations in the
# docs was BLIND to the citation form that carries a line number, and CLAUDE.md
# carried two wrong line numbers - 398 for a real 414, and 86 for a real 117 -
# with every arm in this file green.
#
# WHY A SIBLING EXTRACTOR RATHER THAN EXTENDING `_backticked_paths()`. The
# choice is STRUCTURAL, not a risk dodge. That function returns a set of bare
# path strings and its six callers - lines 211, 219, 227, 234, 270 and 278 -
# all feed each element straight into `(REPO_ROOT / p).exists()` or
# `_is_tracked(p)`. Returning the raw `path:NNN` token would break all six,
# because no such path is on disk. Stripping the `:NNN` before returning would
# keep them working but DISCARDS the line number, which is the one datum the
# arms below exist to check. A sibling extractor is the only shape that can
# carry both.
#
# MEASURED, so that the structural argument is not doing the work alone: the
# strip-and-extend variant was evaluated over every tracked `.md` in this tree
# and found 82 line-number citations naming 27 distinct files, all 27 of which
# exist on disk AND are tracked by git. So extending would NOT have reddened any
# existing arm today. It was rejected for losing the line number, not for
# breaking a neighbour.
# ---------------------------------------------------------------------------


#: Suffix alternation built FROM KNOWN_SUFFIXES rather than retyped, so the two
#: extractors cannot drift about what counts as a file.
_SUFFIX_ALTERNATION = "|".join(sorted(re.escape(suffix.lstrip(".")) for suffix in KNOWN_SUFFIXES))

#: A backticked citation of the form `path/to/file.py:123` or `...:123-456`.
#: Anchored at the start and deliberately indifferent to what follows the line
#: number: docs/LEDGER.md cites
#: `tests/test_task_liveness.py:836: AssertionError, assert "LIVE" in out`,
#: which is a real citation with a pasted failure line glued to it.
_LINE_CITATION = re.compile(
    r"^((?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.(?:" + _SUFFIX_ALTERNATION + r")):(\d+)(?:-(\d+))?"
)

#: The three guard corpus-builders CLAUDE.md cites by line in its
#: cross-repo-inbox section. Every one of the three makes the SAME claim: that
#: the cited line is where that guard builds its corpus from `git ls-files`.
#: Listed by path only - the line numbers are read out of the document, which is
#: what lets a wrong one fail here.
CORPUS_BUILDER_CITATIONS = (
    "tools/precommit_gate.py",
    "tests/test_no_sibling_names.py",
    "tests/test_docs_consistency.py",
)

#: The token the cited line must actually contain. The claim in CLAUDE.md is
#: about `git ls-files`, and that is the substring an out-of-range check can
#: never stand in for: 398 and 414 are both inside a 700-line file.
_CORPUS_BUILDER_TOKEN = "ls-files"


def _tracked_markdown() -> list[str]:
    """Every markdown file git stores, as repo-relative posix paths.

    Derived from the SAME cached `git ls-files` the trackedness predicate uses,
    so the corpus and the predicate cannot disagree, and a nested foreign
    checkout cannot contribute - git does not store another repository's files.
    """
    files, _ = _tracked_paths()
    found = sorted(name for name in files if name.endswith(".md"))
    assert found, "git stores no markdown at all - zero out of zero is not a pass"
    return found


def _backticked_line_citations(text: str) -> list[tuple[str, int, int]]:
    """Every backticked `path:NNN` citation, as (path, first line, last line).

    A list rather than a set: the same citation appearing twice in one document
    is two claims, and both are worth resolving. A bare `path` with no line
    number is NOT returned - that form is `_backticked_paths()`'s business.
    """
    found: list[tuple[str, int, int]] = []
    for token in re.findall(r"`([^`\n]+)`", text):
        match = _LINE_CITATION.match(token.strip())
        if match is None:
            continue
        first = int(match.group(2))
        last = int(match.group(3)) if match.group(3) else first
        found.append((match.group(1), first, last))
    return found


def test_every_line_number_citation_resolves():
    """ARM 1, generic: the cited file exists, is tracked, and HAS that line."""
    failures: list[str] = []
    for doc in _tracked_markdown():
        for path, first, last in _backticked_line_citations(_read(doc)):
            target = REPO_ROOT / path
            if not target.exists():
                failures.append(f"{doc} -> {path}:{first} names a file that does not exist")
                continue
            if not _is_tracked(path):
                failures.append(f"{doc} -> {path}:{first} names a file git does not store")
                continue
            total = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
            if first < 1 or last > total:
                failures.append(f"{doc} -> {path}:{first}-{last} is outside that file's {total} lines")
    assert not failures, "line-number citations that do not resolve: " + "; ".join(sorted(failures))


def test_the_line_citation_sweep_walked_a_real_corpus():
    """A parser that recognised no citation would make the arm above vacuous.

    The floor is far below the corpus - 82 citations when this arm was written -
    and is set low on purpose, because the docs gain and lose citations
    constantly and this arm exists to catch a parser that found NOTHING.
    """
    citations = sum(len(_backticked_line_citations(_read(doc))) for doc in _tracked_markdown())
    assert citations >= 40, f"the line-citation sweep only walked {citations} citations - the parser is broken"


def test_the_line_citation_parser_is_narrow_and_not_blind():
    """Both directions, so neither a parser stuck on None nor one that swallows
    ordinary paths can survive. The last probe is the LEDGER's real shape: a
    citation with a pasted failure line glued onto it."""
    recognised = _backticked_line_citations(
        "`tools/precommit_gate.py:414` `ops/loop/winmutex.py:37-38` "
        "`core/types.py` `engines/objectives.expand_character_goal` "
        '`tests/test_task_liveness.py:836: AssertionError, assert "LIVE" in out`'
    )
    assert recognised == [
        ("tools/precommit_gate.py", 414, 414),
        ("ops/loop/winmutex.py", 37, 38),
        ("tests/test_task_liveness.py", 836, 836),
    ], recognised


def test_the_corpus_builder_citations_land_on_an_ls_files_line():
    """ARM 2, semantic: the cited line must really be the `git ls-files` call.

    This is the arm with teeth. An out-of-range check cannot tell 398 from 414 -
    both are inside a 700-line file - so only reading the cited line and looking
    for what the prose claims is there can fail on the real defect.
    """
    cited = {
        path: (first, last)
        for path, first, last in _backticked_line_citations(_read("CLAUDE.md"))
        if path in CORPUS_BUILDER_CITATIONS
    }
    absent = [path for path in CORPUS_BUILDER_CITATIONS if path not in cited]
    assert not absent, (
        f"CLAUDE.md no longer cites a line in {absent}, so this arm is not measuring what it claims - "
        "either restore the citation or retire it from CORPUS_BUILDER_CITATIONS"
    )

    wrong: list[str] = []
    for path, (first, last) in sorted(cited.items()):
        lines = (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
        if first < 1 or last > len(lines):
            wrong.append(f"CLAUDE.md cites {path}:{first} but that file has only {len(lines)} lines")
            continue
        window = lines[first - 1 : last]
        if not any(_CORPUS_BUILDER_TOKEN in line for line in window):
            wrong.append(
                f"CLAUDE.md cites {path}:{first} as the {_CORPUS_BUILDER_TOKEN} corpus builder, "
                f"but line {first} reads {lines[first - 1].strip()!r}"
            )
    assert not wrong, "; ".join(wrong)


def test_the_corpus_builder_arm_can_fail():
    """Non-vacuity for ARM 2, without mutating the tree.

    The arm above passes on sight once the numbers are right, and an arm that
    cannot fail is not a gate. So the CHECK is re-run here against a known-wrong
    number and a known-right one, proving the comparison discriminates. 398 is
    the exact number CLAUDE.md carried while claiming to point at the glyph
    gate's corpus builder; 414 is where that call really is.
    """
    lines = (REPO_ROOT / "tools/precommit_gate.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) > 414, "precommit_gate.py shrank below 414 lines - re-measure before trusting this arm"
    assert _CORPUS_BUILDER_TOKEN in lines[413], f"line 414 no longer reads as the corpus builder: {lines[413]!r}"
    assert _CORPUS_BUILDER_TOKEN not in lines[397], (
        f"line 398 now also contains {_CORPUS_BUILDER_TOKEN!r} - this arm can no longer tell the two apart"
    )
