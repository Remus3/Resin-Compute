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

import re
from pathlib import Path

import pytest

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
GOVERNING_DOCS = ("CLAUDE.md", "README.md", "ROADMAP.md")

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
    for path in sorted((REPO_ROOT / "docs").rglob("*.md")):
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
        for path in [REPO_ROOT / d for d in GOVERNING_DOCS] + sorted((REPO_ROOT / "docs").rglob("*.md"))
    )
    for artifact in RUNTIME_ARTIFACTS:
        assert artifact in corpus, f"{artifact} is exempt but no longer referenced - drop the exemption"


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
    for path in [REPO_ROOT / d for d in GOVERNING_DOCS] + sorted((REPO_ROOT / "docs").rglob("*.md")):
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
    for path in [REPO_ROOT / d for d in GOVERNING_DOCS] + sorted((REPO_ROOT / "docs").rglob("*.md")):
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
