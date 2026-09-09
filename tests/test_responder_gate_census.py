"""A census of the `# GATE:` tags in `tools/moon_sync_responder.py`.

A gate here has one referent, and it is not the predicate function. It is the
CONSULT SITE inside `_run_once` where a predicate's value binds the cycle. The
distinction is the file's own, stated in the banner comment above
`test_an_armed_run_stops_at_the_hop_budget` in `tests/test_moon_sync_responder.py`:
three mutants disabled a gate inside the cycle and the suite stayed green,
because every arm tested the predicate as a pure function and none tested that
anything consults it. A predicate can be right, tested, and ignored.

THE REFERENT IS THE BROAD READING, STATED SO A LATER READER CAN OVERTURN IT.
A gate is ANY consult site inside `_run_once` whose value binds the cycle,
whatever syntax carries it: an `if`/`elif` (`ast.If`), a `try` (`ast.Try`), or
an expression that CHOOSES a value - a conditional (`ast.IfExp`) or a
short-circuit `and`/`or` (`ast.BoolOp`) - whose choice is written into the
cycle's own result. The narrow reading - only statement-level branches count -
was tried first and shipped a measurable hole: the rule it actually applied was
"tag every if/try", and three sites that bind the cycle went untagged because
of their SYNTAX rather than because of any judgement about them.

  - `result["termination"] = "exhausted" if empty_only else "refused"` is an
    `IfExp`, and the prose immediately above it in the responder calls that
    distinction the one thing that must not be conflated.
  - `result["bounced"] = bool(sent) and all(...)` is a `BoolOp`, and its own
    comment says a failed write must not be recorded as bounced.
  - `result["delivered"] = all(...) and bool(written)` is a `BoolOp` whose
    `bool(written)` term is the guard against `all([])` being vacuously True.

THE CHOOSING HALF IS A PARSE STEP, NOT A LONGER TUPLE OF NODE TYPES. The first
repair accepted a BARE `ast.IfExp` or `ast.BoolOp` anywhere inside `_run_once`.
It caught those three and it BOUGHT FOUR FALSE SITES with them - the
dependency-injection defaults `inbox = inbox or DEFAULT_INBOX`,
`bounds = bounds or Bounds()`,
`roots = load_roots() if roots is None else roots` and
`draft = (spawn or _spawn_headless)(prompt, bounds)`. Each of those picks a
COLLABORATOR; none of them binds the cycle, and a tag parked on one passed the
census clean. `_is_a_consult_site` asks the question the bare shapes were
standing in for: does this statement WRITE A CHOSEN VALUE INTO THE RESULT the
cycle returns - an `ast.Assign` into a subscript whose value contains a
choosing expression. Re-derived by `test_the_two_rules_are_re_derived_here_...`
rather than transcribed, and measured on this tree:

    bare If / Try / IfExp / BoolOp spots inside _run_once:  22, four of them false
    consult-site spots by the rule above:                   18, none false
    tagged sites:                                           18, all covered

Widening a matcher is the response this tree has already been defeated by three
times. The tighter rule has IDENTICAL coverage of every real gate and zero
false sites, so adopting it is not a trade.

If a later reading wants the narrow rule back, it is `_is_a_consult_site` that
changes, and the change is a judgement to be argued rather than a syntax
accident to be inherited.

TWO MATCHING HAZARDS RUN IN OPPOSITE DIRECTIONS, and one discipline answers
both. `# GATE:measure` is a strict PREFIX of `# GATE:measure-cap`, so a prefix
match over-counts; and a naive `if tag in line` lookup matches a `reason-scrub`
line when the tag is `scrub`, because that one is a SUFFIX. So the strict
pattern anchors the WHOLE line, captures the name as a group, and every
comparison is made between captured groups for EQUALITY, never by containment.

A NEAR MISS IS LOUD, AND THAT IS A MISSING PARSE STEP RATHER THAN A WIDER
MATCHER. A single strict regex FAILED OPEN: `# GATE: draft-skip`, one space
after the colon, was invisible to it, so a real gate was tagged by an author
and the census counted nothing and raised nothing. The answer is two patterns,
not one loose one. `_GATE_ATTEMPT` is PERMISSIVE - any whole-line comment whose
text begins `GATE:` in any case with any spacing - and finds every line trying
to be a tag. `_GATE_STRICT` then VALIDATES the name. A line the first finds and
the second rejects raises `GateTagError`, naming the file, the line, the
offending text and the accepted grammar. Admitting the bad shapes into the
matcher instead is the response this tree has already been defeated by three
times, and it is not taken here.

CEILING - what this census does NOT see. Every item below is a claim about this
module's own limits, and a claim like that is testable; the previous wording
asserted that an unclassifiable shape raises, which was FALSE for the whole
name-grammar class above.

  1. NAMING. It checks the name's GRAMMAR and its uniqueness, and nothing about
     its meaning. It cannot tell whether `# GATE:hop-budget` sits above the
     hop-budget consult site rather than above some other one, so a name is a
     label for a human, not a checked claim.
  2. UNTAGGED CONSULT SITES - THE HOLE THAT REMAINS, SAID PLAINLY. Nothing here
     enumerates the gates that OUGHT to exist. A NEW gate added to `_run_once`
     and never tagged is INVISIBLE to this census and every arm stays green.
     `_FLOOR` is a count and not a per-site identity, so retiring one gate while
     tagging an unrelated statement elsewhere also passes.
  3. WHETHER A GATE IS EXERCISED. It says nothing about any test driving a
     gate, and nothing about whether a mutation at a gate's own call site turns
     a suite red. No mutation runner exists in this tree; this census is the
     tagging step such a runner would consume, not the runner.
  4. SCOPE, WITH THE HALF OF ITS OWN CLAIM THAT WAS FALSE CORRECTED. It reads
     the one file `tools/moon_sync_responder.py` and the one function
     `_run_once`. WITHIN THAT FILE the claim holds and is measured: a tag in
     `run_once` - the logging wrapper around it - or above any other accepted
     shape elsewhere in the file is REPORTED as sitting outside the target
     function, and `test_the_classifier_rejects_a_tag_outside_the_target_function`
     fires that path. ACROSS MODULES the previous wording was FALSE. No second
     file is ever opened, so a `# GATE:` tag in any other module is never read,
     never counted and never reported - SILENTLY IGNORED, the exact words that
     wording denied. The hole is LATENT rather than live: sweeping every
     tracked `.py` for a whole-line `# GATE:` comment on 2026-09-09 found 18
     tags, all 18 of them in the responder and 0 anywhere else. That sweep was
     run by hand and is NOT guarded by an arm here, so it is a measurement with
     a date on it and not a standing claim.
  5. SHAPE. The accepted shapes are exactly what `_is_a_consult_site` returns
     True for: `ast.If` (which covers `elif`), `ast.Try` (which covers
     `try/except/finally`), and an `ast.Assign` into a subscript whose value
     contains an `ast.IfExp` or an `ast.BoolOp`. A consult site written as a
     `while` or a `match`, or one whose chosen value lands in a plain local name
     rather than in the result, is NOT accepted, and TAGGING one FAILS rather
     than passing - it is reported by line as not sitting above an accepted
     shape. What is NOT claimed is that the set is complete; it is the set the
     reading above arrived at.
  6. WHAT A TAGGED LINE MEANS. The subscript-write rule is far narrower than a
     bare `ast.BoolOp`, which any `and`/`or` in the function satisfied, but it
     is still a SHAPE and not a semantics. It certifies that a tag sits above a
     statement that chooses a value and writes it into SOME subscript, never
     that the subscript is the result or that the choice binds the cycle:
     `result["seen"] = a or b` and `cache[k] = a or b` are indistinguishable
     here. That is weaker than "this tag marks a gate" and is stated rather
     than hidden.

Why `ast` and not a bounded text window: a window cannot tell code from a
comment or from a string that happens to sit inside it. That ceiling is already
recorded in `ROADMAP.md` and is not re-derived here.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONDER = REPO_ROOT / "tools" / "moon_sync_responder.py"
RELPATH = "tools/moon_sync_responder.py"

TARGET_FUNCTION = "_run_once"

#: The two statement shapes that carry a branch outright.
_BRANCH_STATEMENTS = (ast.If, ast.Try)

#: The two expression shapes that CHOOSE between values rather than between
#: statements. NEITHER IS A CONSULT SITE ON ITS OWN - see the referent
#: paragraph and `_writes_a_chosen_value_into_the_result`.
_CHOOSING_EXPRESSIONS = (ast.IfExp, ast.BoolOp)

_SHAPE_NAMES = "an If, a Try, or an assignment writing a chosen value into a subscript"

# PERMISSIVE. Every whole-line comment that is TRYING to be a tag: any case,
# any spacing around the word and the colon. This one exists to make a near
# miss visible, never to accept it. A comment that trails CODE on the same line
# is deliberately outside it - a tag is a whole line, and the arm
# `test_a_trailing_gate_comment_is_not_read_as_a_tag` pins that.
_GATE_ATTEMPT = re.compile(r"^[ \t]*#[ \t]*gate[ \t]*:", re.IGNORECASE)

# STRICT. Anchored at both ends, with the name as a captured group. Anchoring is
# what makes a prefix tag distinguishable from the longer tag it prefixes;
# capturing is what lets every later comparison be an equality between names
# rather than a containment test against a whole source line.
_GATE_STRICT = re.compile(r"^[ \t]*#[ \t]*GATE:([a-z0-9]+(?:-[a-z0-9]+)*)$")

_GRAMMAR = (
    "a tag is a WHOLE-LINE comment reading exactly `# GATE:<name>` - uppercase "
    "GATE, no space after the colon, nothing at all after the name - where "
    "<name> matches [a-z0-9]+(-[a-z0-9]+)*: lowercase ASCII letters and digits "
    "in groups joined by single hyphens."
)

# ANTI-VACUITY FLOOR. Welded into the same assertion as the judgement below,
# because a floor asserted in a separate arm leaves the primary arm vacuous -
# a census over zero tags passes every placement check it makes. 18 is the count
# observed after the three untagged binding sites named in the referent
# paragraph were tagged. Deliberately retiring a gate is expected to update this
# constant IN THE SAME COMMIT that removes the tag.
_FLOOR = 18


class GateTagError(AssertionError):
    """A line trying to be a `# GATE:` tag that the strict grammar rejects.

    An `AssertionError` subclass so it reads as a failure rather than as a
    harness crash, and a distinct type so the non-vacuity arms below can pin
    which detector fired.
    """


def _tags(source: str, label: str = RELPATH) -> list[tuple[int, str]]:
    """Every `# GATE:` tag as (1-based line number, captured name).

    Raises `GateTagError` on a line the permissive detector finds and the
    strict grammar rejects. Silently skipping such a line is the failure this
    module was repaired for.
    """
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(source.split("\n"), start=1):
        if _GATE_ATTEMPT.match(line) is None:
            continue
        strict = _GATE_STRICT.match(line)
        if strict is None:
            raise GateTagError(
                f"{label}:{lineno}: this line is trying to be a gate tag and is not one.\n"
                f"  offending line: {line!r}\n"
                f"  accepted grammar: {_GRAMMAR}\n"
                "  Fix the tag. Widening the matcher to admit this shape is the "
                "response this tree has already been defeated by three times: an "
                "unparseable tag must FAIL, because the alternative is a real gate "
                "that the census counts as absent."
            )
        found.append((lineno, strict.group(1)))
    return found


def _writes_a_chosen_value_into_the_result(node: ast.AST) -> bool:
    """The parse step that a bare `IfExp`/`BoolOp` shape was standing in for.

    A choosing expression is a consult site only when what it chooses is
    WRITTEN INTO THE CYCLE'S OWN RESULT, which in this responder is always a
    subscript assignment - `result[...] = <choice>`. A choosing expression whose
    value lands in a plain local name is picking a COLLABORATOR before the cycle
    starts rather than binding the cycle: the four dependency-injection defaults
    named in the module docstring are exactly that, and a bare-shape rule
    accepted all four as legal tag sites.
    """
    if not isinstance(node, ast.Assign):
        return False
    if not any(isinstance(target, ast.Subscript) for target in node.targets):
        return False
    return any(isinstance(inner, _CHOOSING_EXPRESSIONS) for inner in ast.walk(node.value))


def _is_a_consult_site(node: ast.AST) -> bool:
    """Whether a `# GATE:` tag may sit immediately above this statement.

    THIS FUNCTION IS THE JUDGEMENT, and changing it is the way to argue with
    that judgement. A site's reported line is the STATEMENT's own `lineno`,
    which for an assignment is the line the tag sits above - not the line of
    some nested expression inside it.
    """
    return isinstance(node, _BRANCH_STATEMENTS) or _writes_a_chosen_value_into_the_result(node)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{RELPATH}: no function named {name}() - the census has no scope to run in")


def _problems(source: str, label: str, function_name: str = TARGET_FUNCTION) -> list[str]:
    """Every tag this census cannot classify, each naming its file and line.

    An unclassifiable shape is REPORTED, never skipped. The two shapes are a
    tag whose following statement is not a consult site at all, and a tag whose
    following statement is one but sits outside the target function.
    """
    tree = ast.parse(source)
    inside = {
        node.lineno
        for node in ast.walk(_function(tree, function_name))
        if _is_a_consult_site(node)
    }
    anywhere = {node.lineno for node in ast.walk(tree) if _is_a_consult_site(node)}

    reported: list[str] = []
    for lineno, name in _tags(source, label):
        if lineno + 1 in inside:
            continue
        if lineno + 1 in anywhere:
            reported.append(
                f"{label}:{lineno}: GATE:{name} tags a statement outside {function_name}()"
            )
        else:
            reported.append(
                f"{label}:{lineno}: GATE:{name} is not immediately above {_SHAPE_NAMES}"
            )
    return reported


def _duplicates(names: list[str]) -> list[str]:
    """Names appearing more than once, compared for EQUALITY between captures."""
    return sorted({name for name in names if names.count(name) > 1})


# ---------------------------------------------------------------------------
# THE CENSUS ITSELF, against the live file.
# ---------------------------------------------------------------------------


def test_every_gate_tag_marks_an_accepted_shape_inside_run_once():
    """Placement, with the floor welded into the same assertion."""
    source = RESPONDER.read_text(encoding="ascii")
    tags = _tags(source)
    problems = _problems(source, RELPATH)

    assert not problems and len(tags) >= _FLOOR, (
        f"gate census failed on {RELPATH}. Unclassifiable tags: {problems or 'none'}. "
        f"Tag count {len(tags)} against a floor of {_FLOOR} (_FLOOR in "
        "tests/test_responder_gate_census.py). A tag must sit on its own line "
        f"immediately above {_SHAPE_NAMES} inside {TARGET_FUNCTION}() that the gate IS. "
        "If a gate was DELIBERATELY retired, _FLOOR is expected to be updated in the same "
        "commit that removes the tag; a count that fell on its own is a gate that went "
        "untagged."
    )


def test_gate_tag_names_are_unique():
    """One name, one site, with the floor welded in for the same reason."""
    source = RESPONDER.read_text(encoding="ascii")
    names = [name for _, name in _tags(source)]
    duplicated = _duplicates(names)

    assert not duplicated and len(names) >= _FLOOR, (
        f"gate census failed on {RELPATH}. Duplicate tag names: {duplicated or 'none'}. "
        f"Tag count {len(names)} against a floor of {_FLOOR}. A repeated name makes two "
        "consult sites indistinguishable to anything that consumes this census, and a "
        "count below the floor makes the uniqueness check vacuous."
    )


def test_no_gate_is_named_after_one_of_the_several_outcomes_its_branch_emits():
    """`draft-refused` named a site that emits BOTH `exhausted` and `refused`.

    The responder's own prose calls that conflation the one distinction
    disposition (i) exists to preserve, so the tag is named for the SITE. This
    arm is a regression pin on the rename, not a general naming rule - the
    NAMING ceiling item says plainly that no such general rule is checked.

    THE CONCESSION STANDS, NOW WITH A MEASURED REASON RATHER THAN A SHRUG. Both
    literals below are pinned, so renaming `draft-verdict` to `draft-exhausted`
    would still pass. The obvious generalisation - forbid any tag containing a
    word that `_run_once` writes into `result["termination"]` - was derived and
    REJECTED on 2026-09-09. That vocabulary is `budget`, `delivered`,
    `disarmed`, `empty`, `exhausted`, `no-destination`, `refused`,
    `spawn-failed`, `unconfirmed`, `unrecordable`, `untrusted-workspace` and
    `window`, and it collides with three tags correctly named for their SITE -
    `hop-budget`, `trial-window`, `empty-queue` - with the tag `no-destination`
    an exact match on a fourth. The general rule would have to fail four good
    names to catch the one it aims at, so it is not adopted.
    """
    names = {name for _, name in _tags(RESPONDER.read_text(encoding="ascii"))}

    assert "draft-refused" not in names, (
        "GATE:draft-refused is named after one of the two terminations its branch "
        "emits. That branch yields both `exhausted` and `refused`; the tag must "
        "name the SITE."
    )
    assert "draft-verdict" in names, sorted(names)


# ---------------------------------------------------------------------------
# NON-VACUITY. Each arm below proves a detector above actually fires, against
# synthetic source held in this file. Nothing here reads or writes the live
# module.
# ---------------------------------------------------------------------------


_TAG = "# GATE:"

_SYNTHETIC_GOOD = (
    "def _run_once():\n"
    "    result = {}\n"
    f"    {_TAG}alpha\n"
    "    if True:\n"
    "        pass\n"
    f"    {_TAG}beta\n"
    "    try:\n"
    "        pass\n"
    "    except ValueError:\n"
    "        pass\n"
    f"    {_TAG}gamma\n"
    '    result["g"] = 1 if True else 2\n'
    f"    {_TAG}delta\n"
    '    result["d"] = bool(result) and all([result])\n'
    "    return result\n"
)


def test_the_classifier_accepts_a_correctly_placed_tag():
    """The control. Without it the refutations below prove nothing.

    It covers every accepted shape - both branch statements and both choosing
    expressions in their accepted position - so it is also the arm that would go
    red if `_is_a_consult_site` were narrowed back without a deliberate
    argument.
    """
    assert _problems(_SYNTHETIC_GOOD, "synthetic") == []
    assert [name for _, name in _tags(_SYNTHETIC_GOOD, "synthetic")] == [
        "alpha",
        "beta",
        "gamma",
        "delta",
    ]


def test_the_classifier_rejects_a_tag_above_a_statement_that_is_not_a_gate():
    source = (
        "def _run_once():\n"
        f"    {_TAG}alpha\n"
        "    x = 1\n"
        "    if x:\n"
        "        pass\n"
    )
    problems = _problems(source, "synthetic")
    assert len(problems) == 1, problems
    assert problems[0].startswith("synthetic:2: GATE:alpha"), problems
    assert f"not immediately above {_SHAPE_NAMES}" in problems[0], problems


def test_the_classifier_rejects_a_tag_outside_the_target_function():
    source = (
        "def elsewhere():\n"
        f"    {_TAG}alpha\n"
        "    if True:\n"
        "        pass\n"
        "def _run_once():\n"
        f"    {_TAG}beta\n"
        "    if True:\n"
        "        pass\n"
    )
    problems = _problems(source, "synthetic")
    assert len(problems) == 1, problems
    assert problems[0] == "synthetic:2: GATE:alpha tags a statement outside _run_once()", problems


def test_duplicate_detection_names_the_duplicate():
    assert _duplicates(["alpha", "beta", "alpha"]) == ["alpha"]
    assert _duplicates(["alpha", "beta"]) == []


def test_the_matcher_compares_captured_groups_and_is_defeated_by_neither_hazard():
    """Both measured hazards, in one arm, running in opposite directions.

    A prefix match would fold `measure-cap` into `measure`; a containment match
    would find a `scrub` inside `reason-scrub`. Matching the captured group and
    comparing for equality answers both, and the counts below say so.
    """
    source = (
        "def _run_once():\n"
        f"    {_TAG}measure\n"
        "    if True:\n"
        "        pass\n"
        f"    {_TAG}measure-cap\n"
        "    if True:\n"
        "        pass\n"
        f"    {_TAG}reason-scrub\n"
        "    if True:\n"
        "        pass\n"
    )
    names = [name for _, name in _tags(source, "synthetic")]

    assert names == ["measure", "measure-cap", "reason-scrub"], names
    # Three DISTINCT tags, not two conflated ones.
    assert len(set(names)) == 3, names
    assert _duplicates(names) == [], names
    # The prefix direction: `measure` names exactly one site, not two.
    assert names.count("measure") == 1, names
    # The suffix direction: `scrub` names none. A containment lookup would
    # have found it inside `reason-scrub`.
    assert names.count("scrub") == 0, names
    assert _problems(source, "synthetic") == []


def test_a_trailing_gate_comment_is_not_read_as_a_tag():
    """A tag is a WHOLE line. Anything after code on the line is not one.

    This is the one shape the permissive detector deliberately does NOT reach,
    so it neither counts nor raises.
    """
    assert _tags(f"    if x:  {_TAG}alpha\n", "synthetic") == []
    assert _tags(f"    {_TAG}alpha\n", "synthetic") == [(1, "alpha")]


# ---------------------------------------------------------------------------
# THE NAME GRAMMAR FAILS LOUD. Every shape below was INVISIBLE to the single
# strict regex this module shipped with: it matched nothing, so it counted
# nothing and raised nothing, and a refuter's real `# GATE: draft-skip` tag
# passed the whole census. Each arm now pins that the near miss RAISES and that
# the message carries the line and the grammar.
# ---------------------------------------------------------------------------


_NEAR_MISSES = [
    ("space after the colon", "# GATE: alpha"),
    ("uppercase in the name", "# GATE:Alpha"),
    ("mixed case in the word", "# Gate:alpha"),
    ("lowercase word", "# gate:alpha"),
    ("underscore in the name", "# GATE:al_pha"),
    ("empty name", "# GATE:"),
    ("trailing comment", "# GATE:alpha  # why"),
    ("trailing whitespace", "# GATE:alpha "),
    ("space before the colon", "# GATE :alpha"),
    ("leading hyphen", "# GATE:-alpha"),
    ("trailing hyphen", "# GATE:alpha-"),
    ("doubled hyphen", "# GATE:al--pha"),
    ("dotted name", "# GATE:al.pha"),
]


@pytest.mark.parametrize(("why", "line"), _NEAR_MISSES, ids=[w for w, _ in _NEAR_MISSES])
def test_a_near_miss_tag_raises_rather_than_being_counted_as_absent(why, line):
    source = f"def _run_once():\n    {line}\n    if True:\n        pass\n"

    with pytest.raises(GateTagError) as caught:
        _tags(source, "synthetic")

    message = str(caught.value)
    assert message.startswith("synthetic:2:"), message
    assert repr(f"    {line}") in message, message
    assert "accepted grammar" in message, message


@pytest.mark.parametrize(("why", "line"), _NEAR_MISSES, ids=[w for w, _ in _NEAR_MISSES])
def test_the_permissive_detector_sees_every_near_miss_it_is_meant_to_see(why, line):
    """The half of the mechanism that would fail SILENTLY if it regressed.

    If `_GATE_ATTEMPT` stopped matching one of these, the arm above would still
    pass in appearance only - a shape nobody detects also raises nothing. So the
    detector is pinned separately from the grammar it feeds.
    """
    assert _GATE_ATTEMPT.match(f"    {line}") is not None, line
    assert _GATE_STRICT.match(f"    {line}") is None, line


def test_the_grammar_accepts_the_shapes_it_is_supposed_to_accept():
    """The control for the block above. Without it, a grammar that rejected
    EVERYTHING would score a perfect 13 out of 13 on the near misses."""
    for good in ("# GATE:alpha", "# GATE:hop-budget", "# GATE:a1-b2-c3", "#GATE:alpha"):
        assert _GATE_ATTEMPT.match(f"    {good}") is not None, good
        assert _GATE_STRICT.match(f"    {good}") is not None, good
    assert _tags("    # GATE:hop-budget\n", "synthetic") == [(1, "hop-budget")]


def test_a_prose_comment_that_merely_mentions_gates_is_not_an_attempt():
    """The other direction: the permissive detector must not swallow prose.

    A detector that matched any comment containing the word would turn every
    explanatory line in the responder into a raise, and the repair would have
    replaced a silent hole with a false alarm.
    """
    for prose in (
        "# the gate below binds the cycle",
        "# GATES are consult sites, not predicates",
        "# see GATE:hop-budget for the shape",
    ):
        assert _GATE_ATTEMPT.match(f"    {prose}") is None, prose


# ---------------------------------------------------------------------------
# THE FOUR FALSE SITES A BARE-SHAPE RULE BUYS. Every line number below is
# DERIVED FROM THE LIVE FILE BY AST at collection time, never transcribed: the
# dependency-injection defaults move whenever the responder is edited, and a
# hardcoded 1643 would rot into an arm about nothing. The control at the end of
# the block is what stops a rule that rejects every choosing expression
# outright from scoring full marks on the four refutations.
# ---------------------------------------------------------------------------


_LIVE_SOURCE = RESPONDER.read_text(encoding="ascii")


def _spots(source: str, accept) -> set[int]:
    """Every line inside the target function that `accept` calls a tag site."""
    tree = ast.parse(source)
    return {node.lineno for node in ast.walk(_function(tree, TARGET_FUNCTION)) if accept(node)}


def _bare_shape_spots(source: str) -> set[int]:
    """What the FIRST repair accepted: any of the four node types, bare.

    Kept here as an executable record of the superseded rule, so the comparison
    below is a measurement rather than a memory of one.
    """
    shapes = _BRANCH_STATEMENTS + _CHOOSING_EXPRESSIONS
    return _spots(source, lambda node: isinstance(node, shapes))


def _consult_site_spots(source: str) -> set[int]:
    return _spots(source, _is_a_consult_site)


#: Lines the bare-shape rule accepted and `_is_a_consult_site` does not. Four
#: on this tree, all four dependency-injection defaults. Derived at import.
_FALSE_SPOTS = sorted(_bare_shape_spots(_LIVE_SOURCE) - _consult_site_spots(_LIVE_SOURCE))


def _tag_parked_above(source: str, lineno: int, name: str) -> str:
    """`source` with a `# GATE:name` line inserted above `lineno`, same indent.

    The tag then sits AT `lineno` and the statement moves to `lineno + 1`,
    which is the arrangement `_problems` reads.
    """
    lines = source.split("\n")
    target = lines[lineno - 1]
    indent = target[: len(target) - len(target.lstrip())]
    return "\n".join(lines[: lineno - 1] + [f"{indent}{_TAG}{name}"] + lines[lineno - 1 :])


def test_the_two_rules_are_re_derived_here_and_the_tighter_one_loses_nothing():
    """The claim the repair rests on, measured rather than asserted in prose.

    Also the anti-vacuity guard for the parametrized refutations below: an
    empty `_FALSE_SPOTS` would generate ZERO test cases and the whole block
    would pass by generating nothing.
    """
    tagged = {lineno + 1 for lineno, _ in _tags(_LIVE_SOURCE)}
    bare = _bare_shape_spots(_LIVE_SOURCE)
    tight = _consult_site_spots(_LIVE_SOURCE)

    assert len(tagged) >= _FLOOR, sorted(tagged)
    assert not tagged - tight, (
        "the tighter rule dropped a site that carries a tag today, so it is a TRADE and "
        f"not a strict improvement: {sorted(tagged - tight)}"
    )
    assert not tight - bare, (
        "a consult site the bare rule did not even see: the two rules are no longer "
        f"comparable as subsets, so the false-site arithmetic below is meaningless: {sorted(tight - bare)}"
    )
    assert _FALSE_SPOTS == sorted(bare - tight), _FALSE_SPOTS
    assert _FALSE_SPOTS, (
        "the bare-shape rule bought no false sites on this file, so the four refutations "
        "below would be parametrized over an empty list and would prove nothing. If the "
        "responder genuinely lost its dependency-injection defaults, this block is what "
        "must be re-derived, not deleted."
    )


@pytest.mark.parametrize("lineno", _FALSE_SPOTS, ids=[str(n) for n in _FALSE_SPOTS])
def test_a_tag_parked_on_a_dependency_injection_default_is_reported(lineno):
    """The refutation, once per false site the bare-shape rule accepted.

    Under that rule each of these passed the census CLEAN - a tag certifying a
    gate that does not exist. Each must now be REPORTED, naming file and line.
    """
    source = _tag_parked_above(_LIVE_SOURCE, lineno, "di-probe")
    problems = _problems(source, "synthetic")

    assert len(problems) == 1, problems
    assert problems[0].startswith(f"synthetic:{lineno}: GATE:di-probe"), problems
    assert f"not immediately above {_SHAPE_NAMES}" in problems[0], problems


def test_the_choosing_sites_that_do_bind_the_cycle_are_still_accepted():
    """THE CONTROL. Without it, a rule rejecting every `IfExp`/`BoolOp`
    outright would score a perfect four out of four on the arm above.

    The three sites are the ones the referent paragraph names - the
    `exhausted`/`refused` `IfExp` and the `bounced`/`delivered` `BoolOp` writes.
    They are found by shape, not by tag name, so a rename does not touch this.
    """
    tree = ast.parse(_LIVE_SOURCE)
    function = _function(tree, TARGET_FUNCTION)
    branches = {node.lineno for node in ast.walk(function) if isinstance(node, _BRANCH_STATEMENTS)}
    chosen = {
        node.lineno
        for node in ast.walk(function)
        if _writes_a_chosen_value_into_the_result(node)
    }
    tagged = {lineno + 1 for lineno, _ in _tags(_LIVE_SOURCE)}
    via_choice = sorted(tagged & (chosen - branches))

    assert len(via_choice) >= 3, (
        "the three tagged sites that are accepted ONLY by the subscript-write rule have "
        f"stopped being accepted, so the refutations above are being scored by a rule that "
        f"rejects every choosing expression: {via_choice}"
    )
    assert _problems(_LIVE_SOURCE, RELPATH) == []
