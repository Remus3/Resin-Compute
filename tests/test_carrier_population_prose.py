"""Lexical guard: no parity claim in the loop-concurrency module may leave its
population unnamed, scope itself to the `ops/loop` DIRECTORY, or cite a carrier
count that disagrees with the module's own measured tuples.

WHY THIS MODULE IS SEPARATE, AND WHY THAT IS THE WHOLE TRICK.

A first pass at this repair declined to build this guard, arguing that a
self-scanning check must be vacuous: it would have to exempt the lines holding
its own patterns, and a guard whose corpus excludes the shape it hunts is the
failure this tree has been bitten by before. That argument was WRONG, and the
reason is structural rather than clever. The scanner here reads a TARGET file as
a STRING. It never scans the file it lives in. Put the patterns in a different
module from the prose they police and the self-exclusion problem does not arise
at all - there is nothing to exempt, because the exempt thing was never in the
corpus. This module holds the patterns; `tests/test_loop_concurrency.py` holds
the prose; neither reads the other's text.

WHAT THE SCANNER LOOKS AT. Every string Constant reachable from the target's
AST - module and function docstrings, assertion messages, dict values - plus
every COMMENT token from `tokenize`. Comments are joined into contiguous blocks
first, so a claim wrapped across two `#` lines is one span rather than two
half-claims that each look innocent. That join is the same reasoning
`tests/test_no_sibling_names.py` gives for stripping comment markers before it
matches.

FOUR RULES, and each one exists because a real sentence in that file broke it:

  A. DIRECTORY-SCOPED SAMENESS. A span naming `ops/loop/` as a directory - the
     path with no filename after it - together with a sameness word. This is the
     defect an adversarial pass found: `ops/loop/` holds two modules with
     DIFFERENT carrier sets, so a directory-wide sameness claim is false at every
     count, and its binding condition being narrower than its wording is the
     exact defeat shape recorded in this tree's roadmap.
  B. UNNAMED POPULATION beside a sameness word.
  C. WRONG COUNT. A span that names `slots.py` or `winmutex.py` and carries a
     population numeral whose value disagrees with that module's tuple.
  D. UNNAMED POPULATION anywhere. A bare "three repos" or "two sibling trees"
     that names no module and no population constant. This is the broadest rule
     and it catches the most, because the original defect was never really a
     wrong number - it was a number with no stated population, which is why two
     correct numerals sat side by side for weeks each refuting the other.

WHAT IT STRUCTURALLY CANNOT SEE, stated plainly because the limits are large:

  * INTERPOLATED TEXT. The target builds its most important messages with
    f-strings, so the population arrives at runtime and the AST holds only the
    literal chunks either side of it. A static reader cannot check a value that
    does not exist until the assert fires. That gap is covered from the other
    direction by
    `test_loop_concurrency.py::test_this_tree_s_own_membership_matches_this_tree_s_own_disk`,
    which ties those tuples to this tree's own disk. Neither guard subsumes the
    other and neither is parity.
  * ANY OTHER FILE. The corpus is one module, named below. That is a deliberate
    narrow scope, not an oversight: this rule is about one file's cross-repo
    prose, and a sweep over every test module would go red on unrelated English.
    The corpus arm below asserts the scan actually found spans, because a
    one-file corpus is the easiest kind to accidentally empty.
  * A CLAIM PHRASED WITHOUT ANY OF THESE WORDS. The word lists are finite. A
    sentence that says "everywhere" instead of "identical", or "trees" in a
    construction the population pattern does not model, passes. Widening the
    matchers is not the standing answer to that in this tree, so the shapes are
    written down rather than chased.
"""
from __future__ import annotations

import ast
import re
import tokenize
from io import StringIO
from pathlib import Path

import pytest

from tests import test_loop_concurrency as target_module

ROOT = Path(__file__).resolve().parents[1]

#: The one file this guard polices. Named as a path rather than imported, so the
#: scanner reads bytes off disk exactly as a reviewer would.
TARGET = ROOT / "tests" / "test_loop_concurrency.py"

#: Words that assert two things are the same across trees.
_SAMENESS = re.compile(r"byte[- ]identical|identical|parity|mirror", re.IGNORECASE)

#: `ops/loop/` used as a DIRECTORY - not followed by a filename.
_DIRECTORY = re.compile(r"ops/loop/(?![A-Za-z_]+\.[A-Za-z0-9]+)")

#: A population: a count immediately in front of a population noun.
_POPULATION = re.compile(
    r"\b(?:all\s+)?(two|three|four|five|six|seven|\d{1,2})\s+"
    r"(?:sibling\s+)?"
    r"(?:repos|repositories|trees|carriers|sides|participants|declarers|siblings)\b",
    re.IGNORECASE,
)

#: Naming any of these discharges the obligation to say which population.
_NAMED = re.compile(
    r"slots\.py|winmutex\.py|CHANNEL\.md|SLOTS_CARRIERS|WINMUTEX_CARRIERS"
    r"|WINMUTEX_DIVERGENT|CARRIERS_BY_MODULE|LANE_WIDTH_DECLARERS",
)

_WORD_VALUES = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
}

#: Rule C only applies to modules whose carrier tuple this repo actually holds.
_MODULE_TUPLES = {
    "slots.py": "SLOTS_CARRIERS",
    "winmutex.py": "WINMUTEX_CARRIERS",
}


def _numeral(token: str) -> int:
    return _WORD_VALUES.get(token.lower(), 0) or int(token)


def _comment_blocks(source: str) -> list[str]:
    """Contiguous runs of `#` lines, joined into one span each.

    A claim wrapped across two comment lines is one claim. Reading the lines
    separately is how half a sentence looks innocent.
    """
    blocks: list[str] = []
    current: list[str] = []
    previous_row = -2
    for token in tokenize.generate_tokens(StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        row = token.start[0]
        text = token.string.lstrip("#").strip()
        if row == previous_row + 1 and current:
            current.append(text)
        else:
            if current:
                blocks.append(" ".join(current))
            current = [text]
        previous_row = row
    if current:
        blocks.append(" ".join(current))
    return blocks


def _string_constants(source: str) -> list[str]:
    """Every string literal in the AST, f-string literal chunks included."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(" ".join(node.value.split()))
    return found


def _spans(source: str) -> list[str]:
    """Sentence-ish spans from comments and string literals in `source`."""
    spans: list[str] = []
    for block in _comment_blocks(source) + _string_constants(source):
        for sentence in re.split(r"\.\s+", block):
            sentence = sentence.strip()
            if sentence:
                spans.append(sentence)
    return spans


def scan(source: str) -> list[str]:
    """Offender descriptions for `source`. Empty means clean."""
    offenders: list[str] = []
    for span in _spans(source):
        excerpt = span if len(span) <= 110 else span[:107] + "..."
        named = _NAMED.search(span)
        sameness = _SAMENESS.search(span)
        population = _POPULATION.search(span)

        if sameness and _DIRECTORY.search(span):
            offenders.append(f"A directory-scoped sameness claim: {excerpt!r}")
            continue
        if sameness and population and not named:
            offenders.append(f"B sameness over an unnamed population: {excerpt!r}")
            continue
        if population and named:
            count = _numeral(population.group(1))
            for module, tuple_name in _MODULE_TUPLES.items():
                if module in span:
                    expected = len(getattr(target_module, tuple_name))
                    if count != expected:
                        offenders.append(
                            f"C {module} is cited as {count} but {tuple_name} "
                            f"holds {expected}: {excerpt!r}"
                        )
                    break
            continue
        if population and not named:
            offenders.append(f"D a population count that names no population: {excerpt!r}")
    return offenders


def test_the_target_names_every_population_it_counts():
    """The guard itself, against the file on disk."""
    offenders = scan(TARGET.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{TARGET.name} carries {len(offenders)} claim(s) whose population is unnamed, "
        "directory-scoped, or numerically at odds with that module's own tuple. "
        "ops/loop holds two modules with DIFFERENT carrier sets, so a sentence that "
        "scopes to the directory is false at every count. Name the module or the "
        "population constant in the same sentence as the number:\n  "
        + "\n  ".join(offenders)
    )


def test_the_scan_examined_a_real_corpus():
    """A scanner that found no spans would make the arm above vacuous."""
    spans = _spans(TARGET.read_text(encoding="utf-8"))
    assert len(spans) > 200, (
        f"only {len(spans)} spans were extracted from {TARGET.name}, which is too few to "
        "be that file. The extractor is broken, so a clean result above says nothing."
    )


@pytest.mark.parametrize(
    ("label", "planted"),
    [
        # Each of these is a real sentence shape that was live in this target
        # before the repair, restated as the shape rather than the literal.
        ("directory-scoped", "ops/loop/ is BYTE-IDENTICAL-BY-CONTRACT across all three repos."),
        ("directory backticked", "`ops/loop/` is byte-identical-by-contract across the carriers."),
        ("unnamed mirror", "This directory is a byte-identical mirror of two sibling trees."),
        ("bare carrier count", "All three carriers are published and nothing else changed."),
        ("bare repo count", "The short version is that all three repos change in ONE round."),
        ("wrong slots count", "The slots.py carriers are three repos and they all agree."),
    ],
)
def test_the_scan_fires_on_a_planted_claim(tmp_path: Path, label: str, planted: str):
    """Non-vacuity, on a tmp_path COPY of the real bytes.

    The target is a tracked file other agents may be measuring, so the mutation
    never touches it - the same copy-and-mutate idiom the target itself uses for
    its carriage-return detector. Each case goes through `scan`, the function
    the real arm calls, rather than through a pattern by hand: an arm that
    matched the regex directly would pass while the sweep stayed blind.
    """
    original = TARGET.read_text(encoding="utf-8")
    mutant = tmp_path / "mutant.py"
    mutant.write_text(original + f"\n\n# {planted}\n", encoding="utf-8", newline="\n")

    offenders = scan(mutant.read_text(encoding="utf-8"))
    assert offenders, f"the scan accepted a {label} claim: {planted!r}"


def test_the_untouched_copy_stays_clean(tmp_path: Path):
    """The survivor arm: a detector that fires on everything guards nothing."""
    original = TARGET.read_text(encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text(original, encoding="utf-8", newline="\n")

    assert scan(clean.read_text(encoding="utf-8")) == [], (
        "a byte-wise copy of the real target must scan clean, or this detector is "
        "reporting on itself rather than on the prose"
    )


def test_rule_c_reads_the_live_tuples_and_not_a_frozen_number():
    """Rule C must track the tuples, or it is a second hand-maintained literal.

    The whole complaint that produced this module was a count retyped in prose
    with nothing tying it to the measurement. A rule C keyed on a literal 4
    would reproduce that defect one layer up.
    """
    sizes = {name: len(getattr(target_module, const)) for name, const in _MODULE_TUPLES.items()}
    assert sizes == {"slots.py": 4, "winmutex.py": 5}, (
        f"the carrier tuples now measure {sizes}. If that is a real change, it was "
        "measured across the fleet and this arm's expectation moves with it; if it is "
        "not, the tuples were edited without a measurement."
    )
    for module, expected in sizes.items():
        wrong = "five" if expected != 5 else "four"
        span = f"The {module} carriers are {wrong} repos and they all agree."
        assert scan(f"# {span}\n"), f"rule C missed a wrong count for {module}"
