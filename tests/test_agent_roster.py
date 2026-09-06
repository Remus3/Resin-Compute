"""The subagent roster is a MECHANISM, and an unguarded mechanism is a promise.

WHY THIS EXISTS. `.claude/agents/*.md` is not documentation. Claude Code reads
these files to register subagents, and four properties of them are load-bearing
in a way that no reader and no runtime error would ever flag:

1. READ-ONLY IS THE `tools:` LIST, NOT THE PROSE. An agent whose job is to grade
   work must not be able to edit the work. That is enforced by OMITTING Edit,
   Write, NotebookEdit and MultiEdit from `tools:`. A paragraph telling the agent
   not to edit anything is a promise; the omission is a mechanism, and the two
   are not interchangeable. Adding one word to a `tools:` line silently converts
   an adjudicator into a participant, and nothing anywhere would say so.

   The inverse is equally real and is guarded too: `builder` and `ui-auditor`
   deliberately carry NO `tools:` key, which is what grants them full tools. A
   well-meaning later edit that "tidies up" by giving every agent an explicit
   restrictive list would disarm the only two agents that are supposed to write.

2. SUBAGENT CONTEXT DOES NOT INHERIT THE MAIN THREAD'S. The session-shape
   doctrine in CLAUDE.md reaches a subagent only because every agent file repeats
   it inline. Delete that block and nothing errors - the agent runs, sounds
   plausible, and grades its own work. This file asserts on the load-bearing
   PHRASES rather than on a whole block, so the prose can still be improved
   without breaking the guard.

3. THE VERDICT VOCABULARIES ARE STRING-MATCHED BY THE ORCHESTRATOR. A verdict
   the agent was never told to emit reads downstream as no objection, which is
   the exact shape of "CONFIRMED WITH CORRECTIONS" being rounded up to
   "CONFIRMED". So each vocabulary is asserted VERBATIM.

4. A NAME THAT DOES NOT MATCH ITS FILENAME TARGETS NOTHING. A dispatch naming
   `verifier` when `verifier.md` declares `name: verifer` does not fail loudly.
   It silently does not run the agent, and the phase reports no findings.

WHY NO PyYAML. `requirements-dev.txt` pins ruff, pytest and mypy and nothing
else, and CI installs exactly that file. `import yaml` would pass on this
workstation and ImportError on the runner, so the frontmatter parser below is
stdlib-only and deliberately minimal - it needs to answer "is there a delimited
block", "what is `name`" and "is there a `tools:` key", not to implement YAML.

CASE SENSITIVITY, STATED RATHER THAN ASSUMED, AND DIFFERENT PER PHRASE. The two
doctrine phrases get opposite policies, and the split is the whole design:

  "never grades it" is matched CASE-INSENSITIVELY. CLAUDE.md renders it lowercase
  mid-sentence and the roster renders it shouted - THE AGENT THAT PRODUCED A
  THING NEVER GRADES IT - and both say the same thing. Measured 2026-09-06: all
  seven files shout it. Case carries no meaning for this phrase, so demanding one
  rendering would assert on FORMATTING and force a cosmetic edit to seven files
  every time an author emphasised the line. A guard that fires on prose style is
  a guard people delete.

  "REFUTE" is matched CASE-SENSITIVELY, uppercase. Here the shout IS the meaning:
  REFUTED and NOT REFUTED are the adversary's literal verdict tokens and an
  orchestrator string-matches them uppercase, so a file that only says "refute"
  in passing prose has lost the directive while a case-insensitive check would
  wave it through. Matching "REFUTE" as a substring intentionally also accepts
  "REFUTED" and "REFUTES".

The paired arm below plants both renderings, so this policy is asserted rather
than merely described here.

NON-VACUITY IS THE CONVENTION HERE, not a nicety - see the paired arms in
tests/test_docs_consistency.py and tests/test_line_endings.py. Every guard below
has an arm proving its detector fires on a planted violation. Planted cases are
written to tmp_path; no arm ever mutates a real agent file, not even briefly,
because a break-revert-observe cycle on a tracked file is how a parallel agent
turns an unrelated suite red while someone else is measuring it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / ".claude" / "agents"

#: The roster, exactly. Seven, no more and no fewer. An extra file here is not a
#: harmless note - it is a registered agent nobody decided to add.
EXPECTED_AGENTS = frozenset(
    {"planner", "builder", "verifier", "adversary", "adjudicator", "researcher", "ui-auditor"}
)

#: Read-only by mechanism: each MUST declare a `tools:` list, and that list must
#: contain none of MUTATING_TOOLS.
READ_ONLY_AGENTS = ("adjudicator", "adversary", "planner", "researcher", "verifier")

#: Full tools by mechanism: each MUST omit `tools:` entirely. Omission is the
#: grant, so an explicit list appearing here is a downgrade, not a clarification.
FULL_TOOL_AGENTS = ("builder", "ui-auditor")

#: The four tools that can mutate the tree. MultiEdit and NotebookEdit are in the
#: set even though nothing in this repo uses notebooks: the list guards against a
#: FUTURE grant, and an omission that only covers today's tools is not a guard.
MUTATING_TOOLS = frozenset({"Edit", "MultiEdit", "NotebookEdit", "Write"})

#: Phrases, not blocks, as (phrase, case_sensitive). The per-phrase case policy
#: is deliberate and is argued in the module docstring: case is formatting for
#: the first phrase and meaning for the second.
DOCTRINE_PHRASES = (("never grades it", False), ("REFUTE", True))

#: Verbatim, because the orchestrator string-matches these.
#:
#: `ui-auditor` appears here despite holding full tools: its first line is
#: string-matched exactly like a read-only agent's, so the vocabulary is
#: load-bearing regardless of what it is allowed to touch.
#:
#: The researcher's tokens are listed as three separate strings rather than as
#: "GATE: REFUSED" and "GATE: UNRESOLVED" so that both renderings pass - the
#: single line "GATE: CLEARED / REFUSED / UNRESOLVED" and the three-line form.
VERDICT_VOCABULARY = {
    "adjudicator": ("DECISION:", "RUNNER-UP:", "COMMON-MODE RISK:"),
    "adversary": ("REFUTED", "NOT REFUTED", "REFUTED (UNCERTAIN)"),
    "researcher": ("GATE: CLEARED", "REFUSED", "UNRESOLVED"),
    "ui-auditor": ("AUDIT: PASS", "AUDIT: BLOCKED"),
    "verifier": ("CONFIRMED", "CONFIRMED WITH CORRECTIONS", "REFUTED", "UNVERIFIABLE"),
}

#: Control bytes a text file may legitimately contain: tab, newline, carriage
#: return. Mirrors tests/test_docs_consistency.py, deliberately including the
#: LOWER end of the range - that file's own docstring records a BEL written into
#: a tracked doc while a `byte > 0x7E` check said nothing.
_ALLOWED_CONTROL = frozenset({0x09, 0x0A, 0x0D})

CRLF = b"\r\n"

#: A frontmatter key, anchored at column 0. The character class excludes
#: whitespace, so an indented `tools:` inside a folded `description:` cannot be
#: mistaken for a key - which is what makes "this file has no tools: key" a
#: statement the parser can actually make.
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


# ---------------------------------------------------------------------------
# Helpers - every guard and its paired non-vacuity arm run through these, so an
# arm that passes is evidence about the real detector rather than about a
# parallel reimplementation of it.
# ---------------------------------------------------------------------------


def _agent_path(agent: str) -> Path:
    return AGENT_DIR / f"{agent}.md"


def _rel(path: Path) -> str:
    """A repo-relative path for an assertion message, and never an exception.

    `Path.relative_to` RAISES for anything outside REPO_ROOT. This only ever
    renders failure messages, so a throw here would replace a clean "the roster
    is incomplete" with an unrelated ValueError traceback - the guard would still
    be red, but about the wrong thing, which is the one failure mode a guard
    cannot afford.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_agent(agent: str) -> str:
    path = _agent_path(agent)
    assert path.is_file(), f"{_rel(path)} does not exist - the roster is incomplete"
    return path.read_text(encoding="utf-8")


def _roster_stems(directory: Path) -> set[str]:
    """The agent names a roster directory actually registers."""
    if not directory.is_dir():
        return set()
    return {path.stem for path in directory.glob("*.md")}


def _roster_drift(directory: Path) -> tuple[list[str], list[str]]:
    """(missing, unexpected) against EXPECTED_AGENTS."""
    present = _roster_stems(directory)
    return sorted(EXPECTED_AGENTS - present), sorted(present - EXPECTED_AGENTS)


def _frontmatter(text: str) -> dict[str, str] | None:
    """Top-level frontmatter keys, or None when the block is absent or unclosed.

    Not a YAML implementation and not trying to be. It answers three questions:
    is there a `---` delimited block at the top, what does `name` say, and is
    there a `tools:` key at all.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    body: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        body.append(line)
    if not closed:
        return None

    front: dict[str, str] = {}
    key: str | None = None
    for line in body:
        if not line.strip():
            continue
        match = _FRONTMATTER_KEY.match(line)
        if match:
            key = match.group(1)
            front[key] = match.group(2).strip()
        elif key is not None:
            # A continuation line of a folded value.
            front[key] = f"{front[key]} {line.strip()}".strip()
    return front


def _declared_name(text: str) -> str | None:
    front = _frontmatter(text)
    if front is None:
        return None
    return front.get("name")


def _declared_tools(text: str) -> list[str] | None:
    """The `tools:` grant, or None when the key is ABSENT - which means full tools.

    None and [] are different answers and the distinction is the whole point, so
    this never collapses one into the other.
    """
    front = _frontmatter(text)
    if front is None or "tools" not in front:
        return None
    raw = front["tools"].strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [token.strip().strip("'\"") for token in raw.split(",") if token.strip()]


def _missing_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    """Verbatim, case-sensitive. Used for the verdict vocabularies, where every
    token is string-matched exactly as written."""
    return [phrase for phrase in phrases if phrase not in text]


def _missing_doctrine(text: str) -> list[str]:
    """The doctrine phrases, each under its own case policy."""
    missing: list[str] = []
    for phrase, case_sensitive in DOCTRINE_PHRASES:
        haystack = text if case_sensitive else text.lower()
        needle = phrase if case_sensitive else phrase.lower()
        if needle not in haystack:
            missing.append(phrase)
    return missing


def _bad_bytes(raw: bytes) -> list[int]:
    """Both ends of the 7-bit range, mirroring test_docs_consistency.py."""
    return sorted({b for b in raw if b > 0x7E or (b < 0x20 and b not in _ALLOWED_CONTROL)})


def _git_ignores(relative_path: str) -> bool:
    """True when git's ignore rules exclude `relative_path`.

    `--no-index` is load-bearing, not an optimisation. Without it git consults
    the INDEX first and answers "not ignored" for any TRACKED path regardless of
    the patterns in force - so this guard would start passing unconditionally the
    moment the roster is committed, which is precisely when it must keep biting.

    The path need not exist on disk; check-ignore evaluates rules, not files.

    Outside a repository there are no ignore rules to evaluate and git exits
    128, which the assertion below deliberately refuses to collapse into "not
    ignored". Skipping first keeps that refusal intact.
    """
    require_git_repository()

    completed = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", relative_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # 0 = ignored, 1 = not ignored, 128 = fatal. Collapsing 128 into "not
    # ignored" would turn a broken git invocation into a green guard.
    assert completed.returncode in (0, 1), (
        f"git check-ignore failed with {completed.returncode}: {completed.stderr.strip()}"
    )
    return completed.returncode == 0


def _synthetic_agent(
    name: str,
    *,
    tools: str | None = "Read, Grep, Glob, Bash",
    doctrine: bool = True,
    vocabulary: tuple[str, ...] = (),
) -> str:
    """A minimal well-formed agent file, for planting violations into."""
    lines = ["---", f"name: {name}", "description: A synthetic agent used only by this test module."]
    if tools is not None:
        lines.append(f"tools: {tools}")
    lines.append("---")
    lines.append("")
    if doctrine:
        lines.append("The agent that produced a thing never grades it.")
        lines.append("Findings get an independent pass whose job is to REFUTE them.")
    lines.extend(vocabulary)
    return "\n".join(lines) + "\n"


def _plant(directory: Path, agent: str, text: str) -> Path:
    path = directory / f"{agent}.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------------------
# Guard 1 - the roster is exactly seven, and exactly these seven
# ---------------------------------------------------------------------------


def test_the_two_tool_tiers_partition_the_whole_roster():
    """A constants-level guard. If a new agent were added to EXPECTED_AGENTS but
    to neither tier, guard 3 would never look at its `tools:` line and the most
    important check in this file would skip it in silence."""
    tiered = set(READ_ONLY_AGENTS) | set(FULL_TOOL_AGENTS)
    assert tiered == set(EXPECTED_AGENTS), f"tier lists and roster disagree: {tiered ^ set(EXPECTED_AGENTS)}"
    assert not set(READ_ONLY_AGENTS) & set(FULL_TOOL_AGENTS)
    assert set(VERDICT_VOCABULARY) <= set(EXPECTED_AGENTS)


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_expected_agent_file_exists(agent: str):
    path = _agent_path(agent)
    assert path.is_file(), f"{_rel(path)} is missing - a dispatch naming it would target nothing"


def test_the_roster_has_no_unexpected_members():
    """An agent file nobody decided to add is drift, not a spare."""
    _, unexpected = _roster_drift(AGENT_DIR)
    assert not unexpected, f"unexpected agent files in .claude/agents/: {unexpected}"


def test_the_roster_sweep_detects_a_missing_and_an_unexpected_agent(tmp_path):
    """Non-vacuity. Both directions, because a sweep that only checked for
    extras would pass on an empty directory."""
    _plant(tmp_path, "planner", _synthetic_agent("planner"))
    _plant(tmp_path, "rogue", _synthetic_agent("rogue"))
    missing, unexpected = _roster_drift(tmp_path)
    assert unexpected == ["rogue"]
    assert "verifier" in missing and "planner" not in missing
    assert _roster_drift(tmp_path / "does-not-exist")[0] == sorted(EXPECTED_AGENTS)


# ---------------------------------------------------------------------------
# Guard 2 - frontmatter parses, and `name` matches the filename
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_agent_file_opens_with_a_delimited_frontmatter_block(agent: str):
    assert _frontmatter(_read_agent(agent)) is not None, (
        f"{agent}.md has no --- delimited frontmatter, so it registers no agent at all"
    )


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_agent_declares_the_name_that_matches_its_filename(agent: str):
    declared = _declared_name(_read_agent(agent))
    assert declared == agent, f"{agent}.md declares name: {declared!r} - a dispatch for {agent!r} would target nothing"


def test_the_frontmatter_parser_rejects_the_shapes_that_register_nothing(tmp_path):
    """Non-vacuity for the parse arm."""
    no_block = _plant(tmp_path, "a", "# Just a heading\n\nname: planner\n")
    unclosed = _plant(tmp_path, "b", "---\nname: planner\n\nno closing delimiter\n")
    assert _frontmatter(no_block.read_text(encoding="utf-8")) is None
    assert _frontmatter(unclosed.read_text(encoding="utf-8")) is None
    good = _plant(tmp_path, "c", _synthetic_agent("planner"))
    assert _frontmatter(good.read_text(encoding="utf-8")) is not None


def test_a_name_that_does_not_match_its_filename_is_detected(tmp_path):
    """Non-vacuity for the mismatch arm, including the typo case that motivated it."""
    planted = _plant(tmp_path, "verifier", _synthetic_agent("verifer"))
    assert _declared_name(planted.read_text(encoding="utf-8")) != planted.stem
    honest = _plant(tmp_path, "adversary", _synthetic_agent("adversary"))
    assert _declared_name(honest.read_text(encoding="utf-8")) == honest.stem


# ---------------------------------------------------------------------------
# Guard 3 - tool scoping, which is the mechanism the whole doctrine rests on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", READ_ONLY_AGENTS)
def test_read_only_agents_are_read_only_by_omission_not_by_promise(agent: str):
    tools = _declared_tools(_read_agent(agent))
    assert tools is not None, f"{agent}.md declares no tools: key, and that OMISSION grants full tools"
    granted = sorted(MUTATING_TOOLS.intersection(tools))
    assert not granted, f"{agent}.md grants mutating tools {granted} - it can now edit the work it grades"


def test_the_read_only_sweep_did_not_also_strip_the_researchers_web_tools():
    """The over-fire half of the pair. A sweep can score a perfect result on
    "no mutating tools" by granting nothing at all, which would disarm the
    licence gate rather than enforce it. So assert the legitimate grant survived.
    """
    tools = _declared_tools(_read_agent("researcher"))
    assert tools is not None
    missing = [tool for tool in ("WebSearch", "WebFetch") if tool not in tools]
    assert not missing, f"researcher.md is missing {missing} - it cannot run the licence gate without them"


@pytest.mark.parametrize("agent", FULL_TOOL_AGENTS)
def test_full_tool_agents_omit_the_tools_key_entirely(agent: str):
    tools = _declared_tools(_read_agent(agent))
    assert tools is None, (
        f"{agent}.md declares tools: {tools} - omission is what grants full tools, "
        "so an explicit list here silently downgrades an agent that must write"
    )


def test_a_planted_mutating_grant_is_detected(tmp_path):
    """Non-vacuity, one planted violation per mutating tool."""
    for tool in sorted(MUTATING_TOOLS):
        planted = _plant(tmp_path, "verifier", _synthetic_agent("verifier", tools=f"Read, Grep, {tool}"))
        tools = _declared_tools(planted.read_text(encoding="utf-8"))
        assert tools is not None
        assert MUTATING_TOOLS.intersection(tools) == {tool}
    clean = _plant(tmp_path, "clean", _synthetic_agent("clean", tools="Read, Grep, Glob, Bash"))
    assert not MUTATING_TOOLS.intersection(_declared_tools(clean.read_text(encoding="utf-8")) or [])


def test_a_tools_key_planted_on_a_full_agent_is_distinguished_from_its_absence(tmp_path):
    """Non-vacuity for the inverse arm. None and [] must not be confused."""
    downgraded = _plant(tmp_path, "builder", _synthetic_agent("builder", tools="Read, Grep"))
    assert _declared_tools(downgraded.read_text(encoding="utf-8")) == ["Read", "Grep"]
    correct = _plant(tmp_path, "ui-auditor", _synthetic_agent("ui-auditor", tools=None))
    assert _declared_tools(correct.read_text(encoding="utf-8")) is None
    bracketed = _plant(tmp_path, "flow", _synthetic_agent("flow", tools="[Read, Grep, Glob]"))
    assert _declared_tools(bracketed.read_text(encoding="utf-8")) == ["Read", "Grep", "Glob"]


def test_an_indented_tools_line_inside_a_description_is_not_read_as_a_grant(tmp_path):
    """The parser's own failure mode. If a folded description mentioning tools
    were parsed as a key, a full-tools agent would look downgraded and a
    read-only one would look armed - both from prose."""
    planted = _plant(
        tmp_path,
        "builder",
        "---\nname: builder\ndescription: >\n  Implements one slice.\n  tools: Edit, Write\n---\n\nbody\n",
    )
    assert _declared_tools(planted.read_text(encoding="utf-8")) is None


# ---------------------------------------------------------------------------
# Guard 4 - the doctrine is repeated inline, because context does not inherit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_agent_repeats_the_doctrine_inline(agent: str):
    missing = _missing_doctrine(_read_agent(agent))
    assert not missing, (
        f"{agent}.md is missing {missing} - subagent context does NOT inherit the "
        "main thread's, so a missing doctrine block degrades the agent in silence"
    )


def test_the_doctrine_sweep_fires_on_each_missing_phrase(tmp_path):
    """Non-vacuity, one planted violation per phrase, so dropping either one from
    DOCTRINE_PHRASES is itself caught - and one planted case per side of the
    per-phrase case policy, so the policy is asserted and not just documented."""
    every_phrase = [phrase for phrase, _ in DOCTRINE_PHRASES]

    stripped = _plant(tmp_path, "planner", _synthetic_agent("planner", doctrine=False))
    assert _missing_doctrine(stripped.read_text(encoding="utf-8")) == every_phrase

    half = _plant(tmp_path, "adversary", _synthetic_agent("adversary", doctrine=False, vocabulary=("REFUTED",)))
    assert _missing_doctrine(half.read_text(encoding="utf-8")) == ["never grades it"]

    whole = _plant(tmp_path, "verifier", _synthetic_agent("verifier"))
    assert _missing_doctrine(whole.read_text(encoding="utf-8")) == []

    # Case policy, side 1: the SHOUTED rendering is what the roster actually
    # ships, and it must satisfy the phrase. This is the arm that would have
    # caught the first draft of this file, which demanded lowercase and failed
    # all seven real agents over capitalisation alone.
    shouted = _plant(
        tmp_path,
        "loud",
        "- THE AGENT THAT PRODUCED A THING NEVER GRADES IT.\n- Findings get a pass whose job is to REFUTE them.\n",
    )
    assert _missing_doctrine(shouted.read_text(encoding="utf-8")) == []

    # Case policy, side 2: a lowercase "refute" in passing prose does NOT satisfy
    # the shouted verdict token, even though the other phrase is satisfied by its
    # lowercase form. Both halves of the split are exercised by this one file.
    quiet = _plant(tmp_path, "quiet", "we may refute a claim, and the author never grades it\n")
    assert _missing_doctrine(quiet.read_text(encoding="utf-8")) == ["REFUTE"]


# ---------------------------------------------------------------------------
# Guard 5 - verdict vocabularies, verbatim, because they are string-matched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", sorted(VERDICT_VOCABULARY))
def test_every_verdict_vocabulary_appears_verbatim(agent: str):
    missing = _missing_phrases(_read_agent(agent), VERDICT_VOCABULARY[agent])
    assert not missing, (
        f"{agent}.md never states {missing} - the orchestrator string-matches "
        "these, and a verdict the agent was not told to emit reads as no objection"
    )


def test_a_dropped_verdict_token_is_detected(tmp_path):
    """Non-vacuity. UNVERIFIABLE is the planted casualty on purpose: it is the
    token whose loss looks most harmless and costs the most, because its absence
    is exactly what turns "could not check" into "no objection"."""
    full = VERDICT_VOCABULARY["verifier"]
    complete = _plant(tmp_path, "verifier", _synthetic_agent("verifier", vocabulary=full))
    assert _missing_phrases(complete.read_text(encoding="utf-8"), full) == []

    thinned = _plant(
        tmp_path,
        "verifier-thin",
        _synthetic_agent("verifier", vocabulary=tuple(t for t in full if t != "UNVERIFIABLE")),
    )
    assert _missing_phrases(thinned.read_text(encoding="utf-8"), full) == ["UNVERIFIABLE"]

    # The subtle one: "CONFIRMED" alone must not satisfy the qualified verdict.
    rounded = _plant(tmp_path, "rounded", _synthetic_agent("verifier", vocabulary=("CONFIRMED", "REFUTED")))
    assert "CONFIRMED WITH CORRECTIONS" in _missing_phrases(rounded.read_text(encoding="utf-8"), full)


# ---------------------------------------------------------------------------
# Guard 6 - bytes on disk: 7-bit ASCII, no stray control codes, no CRLF
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_agent_file_is_seven_bit_ascii(agent: str):
    path = _agent_path(agent)
    assert path.is_file(), f"{_rel(path)} does not exist"
    bad = _bad_bytes(path.read_bytes())
    assert not bad, f"{_rel(path)} carries non-ASCII or control bytes: {bad}"


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_no_agent_file_carries_crlf(agent: str):
    path = _agent_path(agent)
    assert path.is_file(), f"{_rel(path)} does not exist"
    count = path.read_bytes().count(CRLF)
    assert not count, f"{_rel(path)} has {count} CRLF; the index normalises this so no diff will show it"


def test_the_byte_guard_checks_both_ends_of_the_range(tmp_path):
    """Non-vacuity, aimed at the hole test_docs_consistency.py records as real:
    a `byte > 0x7E` check alone is silent on a BEL written by a stray escape."""
    clean = tmp_path / "clean.md"
    clean.write_bytes(b"---\nname: planner\n---\n\nplain ascii\n")
    assert _bad_bytes(clean.read_bytes()) == []

    # Built from CODEPOINTS, never typed. This module is itself subject to the
    # tree's ASCII rule and to the very guard it is testing, so the two glyphs
    # CLAUDE.md names by hand - U+2014 em-dash and U+2019 right single quote -
    # are assembled with chr() rather than pasted in. A test for an ASCII rule
    # that has to break the ASCII rule to run is not a test anyone can keep.
    high = tmp_path / "high.md"
    high.write_bytes(("an em-dash " + chr(0x2014) + " a smart quote " + chr(0x2019)).encode() + b"\n")
    assert _bad_bytes(high.read_bytes()), "the upper end of the range is not detected"

    low = tmp_path / "low.md"
    low.write_bytes(b"a BEL \x07 a NUL \x00 an ESC \x1b\n")
    assert _bad_bytes(low.read_bytes()) == [0x00, 0x07, 0x1B]

    tabbed = tmp_path / "tabbed.md"
    tabbed.write_bytes(b"tab\there\r\nand a CR\n")
    assert _bad_bytes(tabbed.read_bytes()) == [], "tab, LF and CR must stay legal"


def test_the_crlf_guard_fires_on_a_planted_carriage_return(tmp_path):
    """Non-vacuity for the line-ending arm, mirroring test_line_endings.py."""
    clean = tmp_path / "clean.md"
    dirty = tmp_path / "dirty.md"
    clean.write_bytes(b"one\ntwo\n")
    dirty.write_bytes(b"one\r\ntwo\n")
    assert clean.read_bytes().count(CRLF) == 0
    assert dirty.read_bytes().count(CRLF) == 1


# ---------------------------------------------------------------------------
# Guard 7 - the roster reaches a fresh clone
# ---------------------------------------------------------------------------
#
# WHY check-ignore AND NOT ls-files. `git ls-files` answers "is this committed
# right now", which is a question about the operator's last commit rather than
# about the rules. This test is written to run alongside the roster being
# authored, when the files are legitimately brand new and untracked, and an arm
# that goes red on uncommitted-but-correct files trains people to ignore it.
#
# The rule is what actually decides whether the roster survives a fresh clone:
# `.gitignore` excludes `.claude/*` and re-admits `.claude/agents/*.md` by
# negation. A negation cannot re-include a file whose PARENT DIRECTORY is
# excluded, so writing `.claude/` instead of `.claude/agents/*` would make the
# negation silently dead and the whole roster would stop being clonable while
# every local checkout kept working. That is the regression this guard catches,
# and check-ignore catches it on the rules whether or not anyone has committed.


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_every_agent_file_is_reachable_by_a_fresh_clone(agent: str):
    relative = f".claude/agents/{agent}.md"
    assert not _git_ignores(relative), (
        f"{relative} is gitignored - the .claude/agents/*.md negation has regressed "
        "and the roster would not reach a fresh clone"
    )


def test_the_ignore_probe_still_fires_on_a_genuinely_ignored_sibling():
    """Non-vacuity.

    tmp_path is deliberately NOT used here, and that is the whole point: a
    scratch directory outside the repository has no ignore rules to test, and
    `git check-ignore` resolves paths against the repo root. So the planted case
    is a hypothetical PATH rather than a planted file - check-ignore evaluates
    rules, not files, so nothing is written to the tree at all.

    The `.txt` sibling proves the exclusion is live and the `.md` proves the
    negation is what re-admits it. Assert BOTH or the guard cannot tell a working
    negation apart from a `.gitignore` that stopped matching anything.
    """
    assert _git_ignores(".claude/agents/scratch-notes.txt"), (
        ".claude/agents/* no longer excludes anything, so the negation below proves nothing"
    )
    assert not _git_ignores(".claude/agents/scratch-notes.md")
    assert _git_ignores("logs/some.log"), "an unrelated known-ignored path stopped registering"
    assert not _git_ignores("CLAUDE.md")
