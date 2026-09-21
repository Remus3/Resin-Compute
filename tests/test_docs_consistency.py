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
    {".py", ".md", ".json", ".js", ".toml", ".ini", ".txt", ".yml", ".yaml", ".xml", ".ps1", ".cmd", ".lnk", ".html", ".sh", ".parked"}  # noqa: E501
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


# ---------------------------------------------------------------------------
# Bare path citations in non-markdown prose
# ---------------------------------------------------------------------------
#
# LIMITS OF THE BARE CITATION RULE - READ THIS BEFORE TRUSTING THE ARMS BELOW.
#
# This belongs in the module docstring and is not there for a mechanical
# reason: CLAUDE.md cites `tests/test_docs_consistency.py:171` by LINE NUMBER,
# `test_the_corpus_builder_citations_land_on_an_ls_files_line` resolves that
# citation, and adding a single line anywhere above the `git ls-files` call
# moves it and reds the suite. Measured while writing this section - a 9-line
# docstring addition put the call on 180 and turned that arm red. So the text
# lives here, below the pinned line, and CLAUDE.md is not this slice's to edit.
#
# The arms below are STRICTLY WEAKER than the markdown arms above. A bare
# citation passes when git STORES the path or git IGNORES it. That is all. They
# promise NOTHING about:
#
#   - EXISTENCE inside an ignored namespace. `ops/runtime/` is gitignored
#     whole, so `ops/runtime/a_file_deleted_last_year.json` is accepted
#     unconditionally and forever - measured accounted True, measured absent
#     from disk. The hand-off already cites two ignored runtime artifacts, and
#     both will expire silently rather than reporting.
#   - LINE RANGE. The markdown arms resolve `path:NNN` against the target's
#     real length. There is no bare equivalent; a line number in plain text is
#     prose, and nothing here reads one.
#   - The shapes the extractor cannot see, listed on `BARE_PATH_SUFFIXES`.
#
# The ignored half is a deliberate trade, not an oversight. It is the only rule
# that does not decay when the hand-off is regenerated, which happens every
# session. Tightening it means resolving ignored paths on disk, and a disk check
# is a fact about ONE MACHINE - which is the precise mistake `_is_tracked()`
# exists to avoid, and which once turned the docs-guards CI job red.
#
# WHY TWO SUFFIXES WERE ADDED to `KNOWN_SUFFIXES` above. A sweep of the index
# found `.sh` and `.parked` TRACKED and absent from that list, which made a
# citation to either decay in silence - the token read as a dotted symbol and
# was never looked up. `scripts/hook_python.sh` is the one shell script, and
# `.parked` is the suffix on `tests/_parked/test_engines_costs.py.parked`,
# whose absence additionally TRUNCATED that path to `...py`. Both were measured
# against every arm in this file before being added. Still absent, and stated
# as a known hole: tracked files with no suffix at all - `.githooks/commit-msg`,
# `LICENSE`, `NOTICE` - and dot-name files - `.gitignore`, `.gitattributes`,
# `ops/runtime/.gitkeep`.
#
# WHY A SECOND EXTRACTOR EXISTS. Everything above is BACKTICK-KEYED, and the
# corpus above is SUFFIX-KEYED to `.md`. Between them those two facts left a
# tracked, session-critical document guarded by nothing:
# `RSC-NEXT-SESSION.txt` is generated by `tools/publish_next_session.py` as
# PLAIN TEXT and contains ZERO backtick characters, so widening
# `_tracked_markdown()` to take `.txt` would have added a corpus file and not
# one citation - an arm that cannot fail. Measured in this tree 2026-09-20:
# grep counts 0 backtick characters in the whole hand-off.
#
# So the paths in it are BARE, and they need their own extractor and their own
# rule. The file extractor is deliberately weaker than the markdown one: a bare
# token is matched on suffix alone, with no leading `TREE_ROOTS` gate, because
# the hand-off legitimately names root-level files - `CLAUDE.md`, `mypy.ini`,
# `pytest.ini` - that no tree root covers. The DIRECTORY extractor is the
# mirror image and keeps the gate, because a directory citation has no suffix
# to key on and only the gate keeps it from matching ordinary prose.

#: The hand-off, named rather than matched. `_tracked_non_markdown_prose()`
#: asserts this document is IN its corpus, because the corpus is suffix-keyed
#: and a suffix-keyed corpus loses its subject silently: renaming this file to
#: `.text` would empty the sweep of the one document it exists for while the
#: two requirements files kept every arm green. That failure mode is recorded
#: in this tree already - a suffix rename empties suffix-keyed guards - and the
#: name assertion is the only thing that reds on it.
HANDOFF_DOCUMENT = "RSC-NEXT-SESSION.txt"

#: Suffixes of tracked prose files that are NOT markdown and therefore carry no
#: backticks for the extractors above to key on. `.txt` is the whole list today
#: because git stores exactly three of them - the hand-off and the two
#: requirements files - and all three are prose that cites paths.
NON_MARKDOWN_PROSE_SUFFIXES = (".txt",)

#: What the bare extractor matches on, DERIVED from `KNOWN_SUFFIXES` so the two
#: cannot drift apart.
#:
#: NOT COVERED, deliberately, and stated here rather than left to be discovered:
#: tracked files with NO distinguishing suffix - `.githooks/commit-msg`,
#: `LICENSE`, `NOTICE` - and tracked DOT-NAME files - `.gitignore`,
#: `.gitattributes`, `ops/runtime/.gitkeep`. Matching those needs a list of
#: literal names, not a shape rule, and a name-keyed list decays the moment the
#: hand-off is rewritten - which is the exact failure this section was built to
#: avoid. A citation to one of them is therefore unguarded, and that is a known
#: hole rather than an oversight.
BARE_PATH_SUFFIXES = frozenset(KNOWN_SUFFIXES)

#: A bare path-shaped token, with two lookaheads that are both load-bearing:
#:
#:   `(?![A-Za-z0-9_-])`   stops `.py` matching the head of `.pyc`, and `.js`
#:                         the head of `.json` before the alternation has
#:                         reached the longer branch.
#:   `(?!\.[A-Za-z0-9_])`  stops `tests/_parked/test_engines_costs.py.parked`
#:                         being TRUNCATED to `...py` and then reported as a
#:                         file git does not store. `.parked` is in
#:                         `KNOWN_SUFFIXES`, so the full token matches instead.
#:
#: The leading `\.?` is the third. Without it `.claude/commands/done.md` - one
#: of this module's own `GOVERNING_DOCS` - extracts as `claude/commands/done.md`
#: and reds the suite for a citation that is perfectly valid. Measured: the
#: hand-off is REGENERATED EVERY SESSION, so that was a live false red waiting
#: on the next session that happened to name a dot-directory.
_BARE_PATH = re.compile(
    r"\.?[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:"
    + "|".join(re.escape(suffix[1:]) for suffix in sorted(BARE_PATH_SUFFIXES))
    + r")(?![A-Za-z0-9_-])(?!\.[A-Za-z0-9_])"
)

#: A bare DIRECTORY citation: a `TREE_ROOTS` prefix, optionally one deeper
#: segment, ending in a slash. `_is_tracked()` has resolved directories since
#: the docs-guards CI job went red over one, and without this the extractor
#: above could never hand it a directory to resolve - the capability was
#: present and unreachable.
#:
#: TRAILING SLASH REQUIRED, and that is a measured limitation rather than a
#: preference. The hand-off hard-wraps prose, and line 93 of the copy standing
#: when this was written ends mid-path on `tests/test_docs_consistency`. A
#: slash-less form is therefore indistinguishable from a wrapped file path, so
#: accepting it would red the suite on a valid document. `agents/pity_engine`,
#: written slash-less on the `python -m pytest` line, is consequently seen only
#: as its root `agents/`.
_BARE_DIRECTORY = re.compile(
    r"(?:"
    + "|".join(re.escape(root) for root in TREE_ROOTS)
    + r")(?:[A-Za-z0-9_-][A-Za-z0-9_./-]*/)?"
)


def _tracked_non_markdown_prose() -> list[str]:
    """Every tracked prose file the backtick-keyed sweeps above cannot see.

    Derived from the SAME cached `git ls-files` as `_tracked_markdown()` and
    the trackedness predicate, so no third view of the index can disagree with
    the other two.
    """
    files, _ = _tracked_paths()
    found = sorted(name for name in files if name.endswith(NON_MARKDOWN_PROSE_SUFFIXES))
    assert found, "git stores no non-markdown prose at all - zero out of zero is not a pass"
    assert HANDOFF_DOCUMENT in found, (
        f"{HANDOFF_DOCUMENT} is not in this corpus - the suffix key has been defeated. "
        f"Either it was renamed out of {NON_MARKDOWN_PROSE_SUFFIXES} or it left the index. "
        f"The sweep still walks {found}, so every arm below would stay green having lost "
        "the one document this whole section exists to guard"
    )
    return found


def _bare_path_citations(text: str) -> list[str]:
    """Every bare FILE path token in plain-text prose, in document order.

    A list rather than a set, matching `_backticked_line_citations()`: the same
    path named twice is two claims, and a set would also let the non-vacuity
    floors below be met by one path repeated.
    """
    return [match.group(0) for match in _BARE_PATH.finditer(text)]


def _bare_directory_citations(text: str) -> list[str]:
    """Every bare DIRECTORY citation in plain-text prose, in document order."""
    return [match.group(0) for match in _BARE_DIRECTORY.finditer(text)]


def _citation_suffix(candidate: str) -> str:
    """The suffix class a file citation belongs to, for the coverage arm."""
    return "." + candidate.rsplit(".", 1)[-1]


@functools.cache
def _is_ignored(candidate: str) -> bool:
    """Is git DELIBERATELY ignoring this path?

    `git check-ignore` RETURNS ITS ANSWER IN THE EXIT CODE and prints nothing
    under `-q`: 0 means ignored, 1 means not ignored, and 128 means the
    invocation itself failed. A caller that inspects only stdout is blind to
    the entire family, which is why `check=False` here is deliberate and 128 is
    re-raised rather than folded into the 1 branch. An error must never read as
    "not ignored" - that would let a broken probe decide a real question.

    TWO THINGS TO KNOW BEFORE TRUSTING THIS. First, the 128 branch is NOT
    reachable from the extractors above: every candidate they produce is a
    relative repo-shaped token, and 128 needs a path git cannot resolve at all.
    It is verified by hand, not by an arm, and an arm that had to fabricate an
    unreachable input to reach it would be testing the fabrication. Second,
    three sibling call sites in this tree pass `--no-index` and this one does
    not. Harmless here only because `_citation_is_accounted_for()` evaluates
    trackedness FIRST, so a tracked path never reaches this function - the flag
    would matter the moment that order changed.
    """
    completed = subprocess.run(
        ["git", "check-ignore", "-q", "--", candidate],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError(
        f"git check-ignore failed on {candidate!r} with exit {completed.returncode}: "
        f"{completed.stderr.strip()!r} - an error is not an answer"
    )


def _citation_is_accounted_for(candidate: str) -> bool:
    """A cited path is legitimate when git STORES it or git IGNORES it.

    Neither one is the defect this exists to catch: a typo, or a pointer that
    decayed when the file it named was moved or deleted. Trackedness is checked
    first because it is answered from the cached index with no subprocess.

    THE IGNORED HALF PROMISES NOTHING ABOUT EXISTENCE. See the module docstring.
    """
    return _is_tracked(candidate) or _is_ignored(candidate)


def test_every_bare_path_citation_in_plain_text_prose_resolves():
    """ARM 3: a bare file or directory citation is tracked, or it is ignored."""
    failures: list[str] = []
    for doc in _tracked_non_markdown_prose():
        text = _read(doc)
        for path in _bare_path_citations(text) + _bare_directory_citations(text):
            if _citation_is_accounted_for(path):
                continue
            failures.append(f"{doc} -> {path} is neither stored by git nor ignored by it")
    assert not failures, "bare citations that resolve to nothing: " + "; ".join(sorted(set(failures)))


def test_the_bare_path_sweep_walked_a_real_corpus():
    """Non-vacuity, four ways, because one total floor was not enough.

    MEASURED, and this is why the single floor was replaced: an extractor
    mutated to match only `md` still yielded 14 citations and cleared a floor of
    10, and one mutated to match only `py` yielded 11 and cleared it too. A
    mutant that deleted 11 of the 13 suffix branches SURVIVED. A total floor
    pins "the extractor matched something", which is not the property - the
    property is that it still matches PATHS, plural, of the several shapes the
    corpus really contains.

    So: every document contributes, the file extractor spans several distinct
    suffix classes, and the directory extractor is not silently dead. Each
    assertion names what went to zero, because "the extractor is broken" without
    a class name sends the next reader back to re-measure from scratch.
    """
    corpus = _tracked_non_markdown_prose()
    per_document = {
        doc: len(_bare_path_citations(_read(doc))) + len(_bare_directory_citations(_read(doc)))
        for doc in corpus
    }
    empty = sorted(doc for doc, count in per_document.items() if count == 0)
    assert not empty, (
        f"the bare sweep found no citation at all in {empty} - a document in the corpus that "
        f"contributes nothing is a document the arms above cannot fail on. Counts: {per_document}"
    )

    classes = sorted({_citation_suffix(p) for doc in corpus for p in _bare_path_citations(_read(doc))})
    assert len(classes) >= 4, (
        f"the file extractor spans only {len(classes)} suffix class(es) - {classes}. The corpus "
        "carries markdown, python, ini and json citations, so a sweep this narrow means suffix "
        "branches have been lost from the pattern, not that the documents changed"
    )

    directories = sum(len(_bare_directory_citations(_read(doc))) for doc in corpus)
    assert directories >= 1, (
        "the directory extractor found nothing - `surface/`, `engines/`, `headless/` and "
        "`ingest/` are all cited in the hand-off and all tracked, so zero means the pattern "
        "is dead and a deleted directory would go unnoticed"
    )

    total = sum(per_document.values())
    assert total >= 10, f"the bare sweep walked only {total} citations in total - the extractor is broken"


def test_the_bare_path_extractor_is_narrow_and_not_blind():
    """Both directions. The dot-directory and double-suffix probes are the two
    that were measured producing a WRONG token rather than no token, which is
    the worse failure: a truncated path resolves to nothing and reds the suite
    for a citation that was correct. `urllib.request` and `http.server` are real
    tokens out of `requirements.txt` that must NOT be read as paths."""
    recognised = _bare_path_citations(
        "see .claude/commands/done.md and ops/loop/slots.py, plus mypy.ini; "
        "urllib.request and http.server are stdlib, core/__pycache__/types.pyc is "
        "build output, tests/_parked/test_engines_costs.py.parked is parked, and "
        "ops/runtime/inbox_seen.json is a real citation."
    )
    assert recognised == [
        ".claude/commands/done.md",
        "ops/loop/slots.py",
        "mypy.ini",
        "tests/_parked/test_engines_costs.py.parked",
        "ops/runtime/inbox_seen.json",
    ], recognised


def test_the_bare_directory_extractor_is_narrow_and_not_blind():
    """The gate is what makes this safe: without `TREE_ROOTS` a slash-shaped
    token matcher would claim `50/50` and `and/or` out of ordinary prose. The
    dotted-symbol probe pins that a trailing file or symbol segment collapses to
    its directory rather than being reported as a directory itself."""
    recognised = _bare_directory_citations(
        "surface/ and agents/pity_engine/ are tracked, the 50/50 is 55.000 percent, "
        "engines/objectives.expand_character_goal is a symbol, and "
        "docs/adr/ADR-003-forecaster-model.md is a file."
    )
    assert recognised == [
        "surface/",
        "agents/pity_engine/",
        "engines/",
        "docs/adr/",
    ], recognised


def test_the_bare_path_arm_can_fail():
    """Non-vacuity for ARM 3, without mutating the tree.

    ARM 3 passes on sight while the hand-off is clean, and an arm that cannot
    fail is not a gate. So the RULE is re-run here against four known inputs
    that must land in four different places: a tracked file, a tracked
    DIRECTORY, a gitignored runtime artifact, and a path that is neither -
    which is the shape of a decayed pointer and the only shape ARM 3 rejects.
    """
    assert _is_tracked("CLAUDE.md"), "CLAUDE.md is untracked - re-measure before trusting this arm"
    assert _citation_is_accounted_for("CLAUDE.md")

    assert _is_tracked("surface/"), (
        "surface/ is no longer a tracked directory - the directory half of the rule has lost its subject"
    )
    assert _citation_is_accounted_for("surface/")

    assert not _is_tracked("ops/runtime/health.json")
    assert _is_ignored("ops/runtime/health.json"), (
        "ops/runtime/health.json is no longer gitignored - the ignore half of the rule has lost its subject"
    )
    assert _citation_is_accounted_for("ops/runtime/health.json")

    decayed = "docs/ARCHITECTURE.md"
    assert not _is_tracked(decayed), f"{decayed} now exists - pick another never-tracked path for this arm"
    assert not _is_ignored(decayed)
    assert not _citation_is_accounted_for(decayed), (
        f"{decayed} is the pointer that started this whole file, and the rule must still reject it"
    )
