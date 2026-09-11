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

    bare If / Try / IfExp / BoolOp spots inside _run_once:  24, four of them false
    consult-site spots by the rule above:                   20, none false
    tagged sites:                                           20, all covered

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

  1. NAMING - HALF CLOSED, AND THE OPEN HALF IS THE MEANING. THIS MODULE still
     checks the name's GRAMMAR and its uniqueness and nothing else. It binds no
     name to any site of its own, so on this module's evidence alone
     `# GATE:hop-budget` could sit above any consult site whatever.
     The SITE half is now checked ELSEWHERE, by
     `tests/test_gate_name_bindings.py`, which binds each gate name to its site
     by EQUALITY against the line immediately below the tag. That makes "the
     tag sits above the right site" false as a claim about the SUITE while it
     stays true as a claim about THIS MODULE, which is why the limit is still
     recorded here rather than deleted.
     The MEANING half is STILL OPEN AND IS CLOSED BY NOTHING. An anchor is a
     TEXT EQUALITY: binding `# GATE:hop-budget` to
     `if not within_budget(inbox, bounds):` asserts that the name sits on THAT
     STATEMENT and asserts nothing at all about whether the name DESCRIBES it.
     A name reading `hop-budget` over a statement that consults a hop budget is
     an agreement no machine in this tree checks, so on MEANING a name remains
     a label for a human, not a checked claim.
  2. UNTAGGED CONSULT SITES - HALF-CLOSED, WITH THE OPEN HALF NAMED. Both
     directions of one comparison are now asserted. That every TAG sits on a
     real site is `not tagged - tight`, asserted by
     `test_the_two_rules_are_re_derived_here_and_the_tighter_one_loses_nothing`.
     That every real SITE carries a tag is `not tight - tagged`, asserted by
     `test_every_consult_site_inside_run_once_carries_a_tag`, whose message
     names each untagged line and prints the offending statements themselves
     ALONGSIDE three counts, not instead of them.
     THOSE TWO DIRECTIONS MAKE THE TWO SETS IDENTICAL AS SETS OF LINE NUMBERS,
     AND NO MORE THAN THAT. `_tags` yields one entry per tag LINE and
     `_consult_site_spots` yields a SET of site lines, so TWO accepted sites
     written on ONE line share a single tag and both directions stay green.
     Measured 2026-09-09 and re-derived 2026-09-10 against the 20-gate
     responder, by inserting a hand-typed `# GATE:oneliner` above
     `if agreed: result['z'] = agreed or why` in a copy of the responder: 22
     site nodes, 21 distinct site lines, 21 tags, nothing untagged and nothing
     reported. Both halves of that line are shapes item 5 lists as ACCEPTED, so
     the open-shapes paragraph below does not cover it. `ruff` flags E701 there,
     and that is a DIFFERENT TOOL whose coverage this item may not claim as its
     own. So a FOURTH conjunct in the coverage arm requires the accepted-site
     NODES to sit on DISTINCT LINES - 20 nodes on 20 distinct lines here, so it
     passes today - and it is that requirement PLUS the two directions that
     gives identity per SITE rather than per line. FOURTH, not third: the arm's
     single assertion is a four-term `and`, counted by AST on 2026-09-09 and
     stated the same way in the arm's own docstring; the earlier "third" here
     was stale by one.
     `test_two_accepted_sites_on_one_line_defeat_line_identity` drives the
     conjunct's own predicate to False, with a control pinning it True on the
     live file.
     THE WELD IS GRADED FOR WHICH CONJUNCT FIRED, and until 2026-09-09 it was
     not. `test_the_coverage_arm_itself_goes_red_on_two_sites_sharing_one_line`
     proves the arm reddens on a one-liner and CANNOT prove the distinct-line
     conjunct is what reddened it - measured, substituting the coincidental
     proxy `len(sites) == len(_TAG_LINES)`, true today at 20/20 and not the
     distinct-line property, left the whole file GREEN at 69 passed. No payload
     on that arm can fix it, because the proxy reddens on that same source too;
     what fixes it is a DIFFERENT SOURCE.
     `test_the_coverage_arm_reddens_on_the_collision_and_not_on_a_count_identity`
     is that source: a second accepted site appended onto an EXISTING tagged
     site's line with a `;`, giving 21 site NODES on 20 distinct LINES against
     20 tags, so the proxy is TRUE, the other two conjuncts are TRUE, and only
     the distinct-line conjunct is False. The proxy leaves it GREEN and the real
     conjunct reddens it. Measured 2026-09-09: with the proxy substituted that
     arm is the ONLY failure in the file.
     THAT ARM DEFEATS ONE LITERAL AND ITS NAME CLAIMED A CLASS, corrected
     2026-09-09 after an independent refutation measured it. SEVEN other wrong
     fourth conjuncts, and one wrong `_colliding_site_lines` body, each left all
     71 cases green: `len(_colliding_site_lines(source)) != 1`,
     `... % 2 == 0`, `len(site_lines) == len(_TAG_LINES)`,
     `len(site_lines) <= len(_TAG_LINES)`, `len(site_lines) <= _FLOOR`,
     `len(site_lines) == 18`, and `lines.count(lineno) == 2` in the helper. They
     fail in OPPOSITE directions, which is why one source could not see them:
     the first two UNDER-FIRE, reading TRUE while TWO real collisions sit in the
     file, and the four `site_lines` conjuncts OVER-FIRE, reddening a clean
     fully tagged responder that merely gained a gate. The repair is IDENTITY AT
     SEVERAL ARITIES rather than a longer count.
     `test_the_collision_detector_names_every_colliding_line_at_three_arities`
     pins `_colliding_site_lines` by EQUALITY at one, two and three sites per
     line, which also kills the `[:1]` and `[-1:]` truncations that let the
     failure message name one colliding line where two existed.
     `test_the_coverage_arm_fires_on_every_collision_arity_and_not_on_a_clean_extra_gate`
     drives THE ARM over those same three sources requiring a RAISE, and then
     over a hand-typed responder carrying one EXTRA CORRECTLY TAGGED gate - 21
     nodes, 21 distinct lines, 21 tags, nothing untagged - requiring NO raise.
     That over-fire control is what kills the four `site_lines` conjuncts, and
     no collision source of any arity can.
     WHAT REMAINS OPEN: the arities are a SAMPLE. A wrong conjunct agreeing with
     the real one on a clean source, on one collision, on two collisions and on
     three sites sharing a line passes every arm here.
     WHAT IS NOW GUARDED: a new gate added to `_run_once` in a shape
     `_is_a_consult_site` accepts, and never tagged, turns that arm RED and is
     reported by line. The detector is PROVED to fire rather than assumed to:
     `test_removing_one_tag_reports_exactly_that_site_as_untagged` runs it
     against the live source with exactly one tag line deleted, once for every
     tag in the file, and requires that site back alone and BY LINE NUMBER.
     BY LINE NUMBER AND NOT BY STATEMENT TEXT, corrected 2026-09-09: those 18
     cases assert only
     `startswith(f"synthetic:{lineno}: consult site inside ")`, and replacing
     the reported statement everywhere with the literal `'advF-garbage'` leaves
     all 18 of them PASSING. Three OTHER arms redden on that mutant and they are
     what pin the statement text -
     `test_the_report_names_the_statement_and_not_only_its_line`,
     `test_a_new_untagged_gate_added_to_run_once_is_reported_by_line` and
     `test_the_coverage_arm_itself_goes_red_on_a_newly_added_untagged_gate`.
     MULTIPLICITY IS GRADED, and until 2026-09-09 it was graded by nothing.
     Every arm in that block pins `len(untagged) == 1`, so a helper returning
     `reported[:1]` - a census naming only the FIRST forgotten gate - passed the
     entire file at 69 passed.
     `test_removing_two_tags_reports_both_sites_and_not_only_the_first`
     deletes the first and the last tag in one pass and requires BOTH sites back
     by line and by statement; with `reported[:1]` substituted it is the ONLY
     failure in the file.
     THAT ARM IS DEPTH-ONE, corrected 2026-09-09. Removing exactly two tags
     grades multiplicity at one literal, and `return reported[:2]` and
     `return reported[:3]` each left all 71 cases green against it. Depth is now
     graded by SET EQUALITY between the reported lines and the removed tag lines
     at k = 1, 2 and 3 in
     `test_removing_k_tags_reports_exactly_those_k_sites_as_a_set`, over gates
     asserted to be non-neighbours in tag order. NO FIXED ARITY BOUNDS AN
     ARBITRARY TRUNCATION - an arm removing k tags is satisfied by `[:k]` - so
     `test_removing_every_tag_reports_every_site_and_bounds_no_truncation`
     removes EVERY tag and requires all 20 sites back by set equality, which
     kills `reported[:n]` for every n below the tag count and claims nothing
     about an n at or above it.
     WHAT KILLS AN UNCONDITIONAL REPORTER, STATED OVER THE WHOLE FILE, because
     the two earlier readings of this sentence were each measured over part of
     it and each reversed the other. Substituting a detector that reports EVERY
     accepted site and running THE WHOLE FILE on 2026-09-09 turns 27 of the 71
     cases RED, across 10 arms. The `len(untagged) == 1` conjunct in
     `test_removing_one_tag_reports_exactly_that_site_as_untagged` scores 0 of
     18 against it, which is the original claim's half. AND SO DOES THE CONTROL:
     `test_removing_no_tag_at_all_reports_nothing` goes red too, because its own
     `_untagged_consult_sites(_LIVE_SOURCE, RELPATH) == []` comes back with 18
     entries. So the answer to "is it the block or the control" is BOTH, and the
     other eight red arms are the coverage arm itself,
     `test_removing_two_tags_reports_both_sites_and_not_only_the_first`,
     `test_two_accepted_sites_on_one_line_defeat_line_identity`,
     `test_the_report_names_the_statement_and_not_only_its_line`,
     `test_a_new_untagged_gate_added_to_run_once_is_reported_by_line` and all
     three coverage-arm wiring arms. The earlier wording said the control is NOT
     what stops it; that was measured over the parametrized block alone and is
     false of the file.
     THE ARM'S OWN WIRING IS GRADED, NOT ONLY THE HELPER IT CALLS. Measured
     2026-09-09: deleting the judgement conjunct from BOTH the coverage arm and
     that control left the suite green, because every refutation here drove
     `_untagged_consult_sites` directly and none ever drove the arm.
     `test_the_coverage_arm_itself_goes_red_on_a_newly_added_untagged_gate`
     now points the arm at a synthetic responder carrying one hand-typed
     untagged gate and requires the ARM to raise, with the unmutated copy as its
     control. Because the two
     sets are identical, the old reading of this item - retire one gate, tag an
     unrelated statement elsewhere, pass - no longer holds: the stray tag is
     reported by `_problems` and the vanished site is reported here.
     WHAT IS STILL OPEN: the coverage arm sees only the shapes item 5 lists. A
     consult site written as a `while`, as a `match`, one whose chosen value
     lands in a plain local name rather than in a subscript, one carried by a
     `return` expression, or one assigned to an ATTRIBUTE target is not a site
     to `_is_a_consult_site`, so leaving it untagged stays INVISIBLE exactly as
     before.
     ARGUMENT POSITION IS NOT ON THAT LIST, and the earlier wording that put it
     there had the discriminator wrong. `_writes_a_chosen_value_into_the_result`
     walks the WHOLE of `node.value`, so a choosing expression nested in a call
     ARGUMENT is seen; what decides is the ASSIGNMENT TARGET. Measured
     2026-09-09 against `_is_a_consult_site` with four hand-typed `_run_once`
     statements:
         return result if written else result                          SILENT
         _hold(DEFAULT_STAGING, note.name or "x", "", [], started)     SILENT
         bounds.probe = written or True                                SILENT
         result["advF"] = _hold(DEFAULT_STAGING, note.name or "x",
                                "", [], started)                       CAUGHT
     The fourth differs from the second ONLY in being assigned into a subscript,
     and it is the one that is seen. So the open shapes are the three targets
     above - no target at all, a plain local name, an attribute - plus `while`,
     `match` and `return`; a choosing expression buried at any depth inside a
     subscript assignment's value is NOT open. The two directions are equal ON
     THE ACCEPTED SHAPES and say nothing whatever outside them.
     THE OMITTED SHAPES HAVE ZERO CURRENT INSTANCES, measured by hand over
     `_run_once` - lines 1622 to 1876 - on 2026-09-09: 12 `ast.Return` nodes, of
     which 0 carry a choosing expression; 0 calls taking a choosing expression
     as an argument; and 0 assignments to an attribute target.
     TWO DIFFERENT QUANTITIES WERE BOTH CALLED FOUR HERE, and only one of them
     is. Re-measured 2026-09-09 by walking `_run_once`:
       - choosing expressions sitting OUTSIDE the subtree of any accepted site:
         THREE, at 1643, 1644 and 1645, the dependency-injection defaults
         `inbox = inbox or DEFAULT_INBOX`, `bounds = bounds or Bounds()` and
         `roots = load_roots() if roots is None else roots`.
       - `_FALSE_SPOTS`, the line-set difference `bare - tight` that the
         four-false-sites paragraph at the top of this module is about: FOUR, at
         1643, 1644, 1645 and 1737.
     1737 belongs to the second list and not the first.
     `draft = (spawn or _spawn_headless)(prompt, bounds)` sits INSIDE the `try:`
     at 1736, which IS an accepted site and carries `# GATE:spawn-failure` at
     1735; it is a false spot because the bare rule saw its `BoolOp` as a tag
     site of its own, not because it is an orphan. That sweep was run by hand
     and is NOT guarded by an arm here, so it is a measurement with a date on it
     and not a standing claim.
     `_FLOOR` is still a count and not a per-site identity, and it is asserted
     in MANY arms rather than one. NO NUMBER IS PINNED HERE ON PURPOSE. The
     previous two wordings said "one" and then "five"; an AST count of the
     `ast.Assert` nodes whose test names `_FLOOR` gave SIX at the time "five"
     was written and gives SEVEN now, so the figure is a fact about an edit
     rather than about the design, and nothing in this tree guards it. What the
     occurrences are FOR is the part worth stating, and there are two kinds.
     WELDED: in `test_every_gate_tag_marks_an_accepted_shape_inside_run_once`,
     in the coverage arm and in `test_gate_tag_names_are_unique` it shares one
     assertion with that arm's own judgement, because a floor in a separate arm
     leaves the primary arm vacuous. STANDALONE: elsewhere it pins the SCALE a
     block runs at - that `_TAG_LINES` is long enough to parametrize 20 cases,
     that the re-derivation block is comparing real sets, that a synthetic
     mutant is still responder-sized - and there a separate line is right,
     because the scale is not the arm's judgement. Inside the coverage arm
     the two floor conjuncts buy two DIFFERENT things and neither of them is the
     judgement. `len(sites) >= _FLOOR` catches a gutted `_is_a_consult_site`,
     which finds zero sites and so makes the set difference empty for the wrong
     reason - measured 2026-09-09, forcing that predicate to False gives 0 sites
     and 0 untagged reports. `len(_TAG_LINES) >= _FLOOR` catches an empty
     `_TAG_LINES`, which would parametrize the 20-case refutation below over
     nothing and report `1 skipped` at exit 0 rather than a failure. Neither
     conjunct is what reddens an untagged site: stripping every tag from the
     responder gives 20 untagged reports and turns the FIRST conjunct alone
     False while both floors stay True.
  3. WHETHER A GATE IS EXERCISED. THIS CENSUS still says nothing about any test
     driving a gate, and nothing about whether a mutation at a gate's own call
     site turns a suite red. It is the tagging step, not the runner. The
     sentence that used to sit here - "no mutation runner exists in this tree" -
     WAS TRUE WHEN WRITTEN AND IS FALSE NOW: `tools/gate_mutation_runner.py`
     landed 2026-09-09 and CONSUMES these tags. Measured by it on that date,
     35 mutants over the 18 tagged sites: 27 killed, 8 survived. So the answer
     to "is this gate exercised" is NO for eight of them, and it is the runner's
     report that says so rather than anything here.
     ONE COUPLING RUNS THE OTHER WAY AND IS RECORDED HERE BECAUSE IT IS THIS
     MODULE'S DOING. This module reads the responder AT IMPORT and grades its
     AST SHAPE, so a mutant that DROPS A BoolOp OPERAND reddens it for a reason
     that is not about behaviour, and under `pytest -x` that was
     indistinguishable from a real kill: all four such mutants scored 32 of 32
     failing nodes HERE and zero elsewhere, and survive at 1716 passed 1 skipped
     once this file is ignored. The runner therefore excludes this module by
     name as a SHAPE GRADER. Adding a shape-grading arm here does not affect its
     verdicts and does enlarge that exclusion, which is the price of the
     coupling and is stated rather than discovered later.
  4. SCOPE, WITH THE HALF OF ITS OWN CLAIM THAT WAS FALSE CORRECTED. It reads
     the one file `tools/moon_sync_responder.py` and the one function
     `_run_once`. WITHIN THAT FILE the claim holds and is measured: a tag in
     `run_once` - the logging wrapper around it - or above any other accepted
     shape elsewhere in the file is REPORTED as sitting outside the target
     function, and `test_the_classifier_rejects_a_tag_outside_the_target_function`
     fires that path. ACROSS MODULES the previous wording was FALSE. No second
     file is ever opened, so a `# GATE:` tag in any other module is never read,
     never counted and never reported - SILENTLY IGNORED, the exact words that
     wording denied. The hole is LATENT rather than live, and THAT IS NOW
     DERIVED RATHER THAN TYPED. The earlier wording here said the sweep found
     18 tags, all of them in the responder and none anywhere else. The first
     half still holds; THE SECOND HALF WAS FALSE, and it was false by decay
     rather than by error - it was true when it was written, and commit 06f8557
     then shipped `tests/test_responder_delivery_gates.py` carrying a
     section-banner tag at its line 272, with no instrument watching. What is
     true, re-derived over the git-tracked `.py` corpus with `tokenize`:
       - 20 tags in `tools/moon_sync_responder.py`, the number `_FLOOR` pins;
       - ONE more, `delivery-write-all` in
         `tests/test_responder_delivery_gates.py`, a banner cross-referencing
         the responder gate that file's arms exercise. It is documentation, not
         a gate on a consult site: that module is a test file with no
         `_run_once`, and nothing here ever opens it;
       - tag-shaped text in `tests/test_gate_mutation_runner.py` that is NOT a
         tag at all. It sits inside STRING LITERALS - synthetic fixture sources
         the runner's own self-test feeds to its matcher - and a comment token
         is what tells it apart from the two real cases above. A text sweep
         cannot make that distinction, which is why this one does not use one.
     That population is no longer a measurement with a date on it. It is
     guarded by
     `tests/test_responder_gate_census.py::test_the_gate_tag_population_across_the_tracked_corpus_is_derived_not_asserted`,
     which enumerates from `git ls-files`, reads `tokenize.COMMENT` tokens, and
     asserts the whole population by EQUALITY against a structure whose
     responder half is derived rather than typed - so a tag appearing in any new
     file reddens it by name and line.
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
import subprocess
import tokenize
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
# a census over zero tags passes every placement check it makes. It was 18 after
# the three untagged binding sites named in the referent paragraph were tagged,
# and is 20 as of 2026-09-10, when `answered-usable` and `answered-recorded`
# landed in `_run_once`. Adding OR deliberately retiring a gate is expected to
# update this constant IN THE SAME COMMIT that moves the tag.
_FLOOR = 20


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


def _untagged_consult_sites(
    source: str, label: str, function_name: str = TARGET_FUNCTION
) -> list[str]:
    """The OTHER direction of the comparison `_problems` makes.

    `_problems` walks the tags and asks whether each one sits on a site. This
    walks the SITES and asks whether each one carries a tag, which is the half
    ceiling item 2 recorded as open. A new consult site added to
    `_run_once` and never tagged is caught here and nowhere else.

    Each report names the file, the line and the SOURCE LINE ITSELF, because a
    bare count mismatch tells an author which arm went red and not which
    statement they forgot. THAT SENTENCE IS AN ASSERTED CLAIM AND NOT PROSE:
    until 2026-09-09 every arm pinned only the report's `file:line:` prefix, so
    replacing the statement with the literal `"advA-garbage"` left the suite
    green. `test_the_report_names_the_statement_and_not_only_its_line` now pins
    the whole message against a hand-typed expectation.
    """
    lines = source.split("\n")
    tree = ast.parse(source)
    sites = {
        node.lineno
        for node in ast.walk(_function(tree, function_name))
        if _is_a_consult_site(node)
    }
    tagged = {lineno + 1 for lineno, _ in _tags(source, label)}

    reported: list[str] = []
    for lineno in sorted(sites - tagged):
        statement = lines[lineno - 1].strip() if lineno - 1 < len(lines) else ""
        reported.append(
            f"{label}:{lineno}: consult site inside {function_name}() carries no "
            f"`# GATE:` tag on the line above it: {statement!r}"
        )
    return reported


def _consult_site_node_lines(
    source: str, function_name: str = TARGET_FUNCTION
) -> list[int]:
    """Every accepted site's line WITH REPEATS, unlike `_consult_site_spots`.

    This exists because the coverage comparison is made between two sets of
    LINE NUMBERS and not between sites and tags: `_tags` yields one entry per
    tag LINE, `_consult_site_spots` yields a SET of site lines, and a tag is
    matched to a site by `lineno + 1`. Two accepted sites written on ONE line
    therefore share a single tag and both directions stay green. This list is
    what `_sites_sit_on_distinct_lines` is derived from.
    """
    tree = ast.parse(source)
    return [
        node.lineno
        for node in ast.walk(_function(tree, function_name))
        if _is_a_consult_site(node)
    ]


def _colliding_site_lines(
    source: str, function_name: str = TARGET_FUNCTION
) -> list[int]:
    """Every line carrying MORE THAN ONE accepted site node, sorted.

    The evidence behind `_sites_sit_on_distinct_lines`, split out so the
    coverage arm's failure message can NAME the colliding line rather than only
    say that a collision exists. Empty on a source with one site per line, so a
    message built from it says nothing when there is nothing to say.

    THE LIST IS PINNED BY EQUALITY, and until 2026-09-09 only its length was.
    Truncating this body to `sorted(...)[:1]` or to `[-1:]` left the whole file
    green at 71 passed, so the message named ONE colliding line where TWO
    existed - which is the naming this helper was split out to provide.
    `lines.count(lineno) == 2` stayed green as well and calls a line carrying
    THREE accepted sites clean.
    `test_the_collision_detector_names_every_colliding_line_at_three_arities`
    now asserts this list by equality at one, two and three sites per line, and
    kills all three. It says nothing about arities above three.
    """
    lines = _consult_site_node_lines(source, function_name)
    return sorted({lineno for lineno in lines if lines.count(lineno) > 1})


def _sites_sit_on_distinct_lines(
    source: str, function_name: str = TARGET_FUNCTION
) -> bool:
    """One accepted site per line - what turns LINE identity into SITE identity.

    Welded into the coverage arm's single assertion rather than asserted in an
    arm of its own, for the same reason the floor is: a separate arm leaves the
    primary one able to pass while the property it depends on is false. It does
    NOT widen or narrow `_is_a_consult_site`; it sits alongside the predicate
    and says nothing about what the predicate accepts.
    """
    return not _colliding_site_lines(source, function_name)


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


def test_every_consult_site_inside_run_once_carries_a_tag():
    """COVERAGE - the direction ceiling item 2 recorded as open.

    `test_every_gate_tag_marks_an_accepted_shape_inside_run_once` asserts every
    TAG sits on a real site. This asserts every real SITE carries a tag. Those
    two directions make the two sets identical AS SETS OF LINE NUMBERS; the
    FOURTH conjunct here is what makes that per-SITE identity, by requiring the
    accepted-site nodes to sit on distinct lines. Without it, two accepted sites
    on one line share a tag and both directions stay green - measured, and
    driven by `test_two_accepted_sites_on_one_line_defeat_line_identity`.

    FOUR CONJUNCTS, ONE ASSERTION, because a property asserted in a separate arm
    leaves this one able to pass while what it rests on is false. The first is
    the judgement. The second pins the site count, so a gutted
    `_is_a_consult_site` that finds NO sites cannot satisfy the judgement by
    measuring an empty difference. The third pins the number of cases
    `test_removing_one_tag_reports_exactly_that_site_as_untagged` generates,
    because an empty `parametrize` list is `1 skipped` at exit 0 and not a
    failure. The fourth is the distinct-line requirement.
    """
    source = RESPONDER.read_text(encoding="ascii")
    untagged = _untagged_consult_sites(source, RELPATH)
    sites = _consult_site_spots(source)
    site_lines = _consult_site_node_lines(source)
    collisions = _colliding_site_lines(source)

    assert (
        not untagged
        and len(sites) >= _FLOOR
        and len(_TAG_LINES) >= _FLOOR
        and _sites_sit_on_distinct_lines(source)
    ), (
        f"gate census failed on {RELPATH}. Untagged consult sites: "
        f"{untagged or 'none'}. Accepted sites {len(sites)} and tag lines "
        f"{len(_TAG_LINES)} against a floor of {_FLOOR} (_FLOOR in "
        f"tests/test_responder_gate_census.py). Colliding lines: "
        f"{collisions or 'none'}. Accepted site NODES "
        f"{len(site_lines)} on {len(set(site_lines))} distinct lines - these "
        "must be equal, because a tag is matched to a site by line and two "
        "accepted sites sharing one line would share one tag. Every statement "
        f"`_is_a_consult_site` accepts inside {TARGET_FUNCTION}() must carry a "
        "`# GATE:<name>` comment on its own line immediately above it, and must "
        "be the only accepted site on its line. If a gate was DELIBERATELY "
        "retired, _FLOOR is expected to be updated in the same commit that "
        "removes the tag."
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


def _tag_line_removed(source: str, lineno: int) -> str:
    """`source` with the whole line at `lineno` deleted.

    The sibling of `_tag_parked_above`, running the opposite mutation: that one
    ADDS a tag where no gate is, this one REMOVES a tag from where a gate is.
    Every line below `lineno` shifts up by one, tags and statements alike, so
    the surviving tags stay directly above their own statements and the only
    site left uncovered is the one whose tag was deleted - which now sits AT
    `lineno` itself.
    """
    lines = source.split("\n")
    return "\n".join(lines[: lineno - 1] + lines[lineno:])


def _tag_lines_removed(source: str, linenos: list[int]) -> str:
    """`source` with EVERY line in `linenos` deleted, in one pass.

    The multi-line sibling of `_tag_line_removed`, and it exists because
    MULTIPLICITY was graded by nothing: every arm above pins `len(...) == 1`,
    so a census reporting only the FIRST forgotten gate passed the whole file.
    Deleting in one pass rather than by repeated single deletions keeps the
    arithmetic stated in the arm's own expectation - a surviving line's new
    number is its old number minus the count of deleted lines above it.
    """
    doomed = set(linenos)
    return "\n".join(
        line for number, line in enumerate(source.split("\n"), start=1)
        if number not in doomed
    )


#: The line of every `# GATE:` tag in the live responder, derived at import.
#: Parametrizes the refutation below so a rule that happens to see only some
#: tagged shapes is caught by the tags it cannot see.
_TAG_LINES = [lineno for lineno, _ in _tags(_LIVE_SOURCE)]


@pytest.mark.parametrize("lineno", _TAG_LINES, ids=[str(n) for n in _TAG_LINES])
def test_removing_one_tag_reports_exactly_that_site_as_untagged(lineno):
    """THE REFUTATION for the coverage arm, once per tag on the live file.

    An arm asserting an already-empty set difference is vacuous - it would pass
    just as cleanly against a rule that finds zero sites. So the detector is
    driven against a source where the answer is KNOWN and NOT empty: the live
    responder with exactly one tag line deleted. The site must come back, by its
    own line number, and it must come back ALONE - a report of two would mean
    the deletion disturbed a neighbouring tag rather than only its own.

    `_problems` must stay silent on the same source, because deleting a tag
    leaves no misplaced tag behind. That second assertion is what stops this
    from passing against a detector that simply reports every line it sees.
    """
    mutated = _tag_line_removed(_LIVE_SOURCE, lineno)
    untagged = _untagged_consult_sites(mutated, "synthetic")

    assert len(untagged) == 1, untagged
    assert untagged[0].startswith(f"synthetic:{lineno}: consult site inside "), untagged
    assert _problems(mutated, "synthetic") == [], _problems(mutated, "synthetic")


def test_removing_two_tags_reports_both_sites_and_not_only_the_first():
    """MULTIPLICITY, which until 2026-09-09 was graded by NOTHING here.

    Every arm above pins `len(untagged) == 1`, so a detector that stops after
    the first forgotten gate satisfies all of them: measured 2026-09-09 by
    changing `_untagged_consult_sites` to `return reported[:1]`, the whole file
    stayed GREEN at 69 passed. Yet "names WHICH statement you forgot" is the
    property that helper's own docstring makes central, and an author who
    forgets two gates in one edit is told about one of them.

    Two tags are deleted in ONE pass, the first and the last in the file, so
    the two reports cannot be neighbours and a detector that merely widened its
    window by one cannot satisfy this either. The expected line numbers are
    ARITHMETIC stated here rather than read back out of the detector: the lower
    site loses the one deleted line above it, the upper site loses two.

    THIS ARM IS DEPTH-ONE, corrected 2026-09-09 after an independent refutation
    measured it. It removes exactly TWO tags, so it grades multiplicity at one
    literal: `return reported[:2]` and `return reported[:3]` each left all 71
    cases green against it, and an author who forgot three gates was still told
    about two. What this arm does pin, and the arms below do not, is the
    reported STATEMENT TEXT and the ORDER of the two reports. Depth is graded by
    `test_removing_k_tags_reports_exactly_those_k_sites_as_a_set` at k = 1, 2
    and 3 by set equality, and bounded for every truncation below the tag count
    by `test_removing_every_tag_reports_every_site_and_bounds_no_truncation`.
    """
    lower_tag = _line_of_tag_named("counterparty-agreement")
    upper_tag = _line_of_tag_named("delivery-write-all")
    assert lower_tag < upper_tag, (lower_tag, upper_tag)

    mutated = _tag_lines_removed(_LIVE_SOURCE, [lower_tag, upper_tag])
    untagged = _untagged_consult_sites(mutated, "synthetic")

    assert len(untagged) == 2, untagged
    assert untagged[0] == (
        f"synthetic:{lower_tag}: consult site inside _run_once() carries no "
        "`# GATE:` tag on the line above it: "
        "'if bounds.armed and not agreed:'"
    ), untagged
    assert untagged[1] == (
        f"synthetic:{upper_tag - 1}: consult site inside _run_once() carries no "
        "`# GATE:` tag on the line above it: "
        "'result[\"delivered\"] = all(ok for ok, _ in written) and bool(written)'"
    ), untagged
    assert _problems(mutated, "synthetic") == [], _problems(mutated, "synthetic")


def test_removing_no_tag_at_all_reports_nothing():
    """THE BASELINE GUARD on `_LIVE_SOURCE`, which nothing else asserts.

    THIS DOCSTRING HAS NOW BEEN WRONG TWICE IN OPPOSITE DIRECTIONS, so the
    history is written down rather than overwritten a third time. It first said
    an unconditional reporter would score 18 of 18 without this arm; a
    refutation that scored only the parametrized block falsified that, and the
    replacement said the unconditional reporter is killed "not by anything
    here". Running THE WHOLE FILE on 2026-09-09 falsified the replacement:
    substituting a detector that reports EVERY accepted site turns 27 of the 71
    cases red across 10 arms, and THIS ARM IS ONE OF THEM, because
    `_untagged_consult_sites(_LIVE_SOURCE, RELPATH)` then comes back with 18
    entries instead of none. Both halves are true at once - the
    `len(untagged) == 1` conjunct in the parametrized block scores that reporter
    0 of 18, AND this arm goes red as well.

    IT DOES NOT BUY NOTHING, which is what the previous wording claimed. Its
    SUBJECT is different from the coverage arm's. The coverage arm reads
    `RESPONDER.read_text()` at call time, and three arms in this file
    MONKEYPATCH `RESPONDER` at a synthetic file. This arm grades `_LIVE_SOURCE`,
    the import-time snapshot that `_TAG_LINES`, `_FALSE_SPOTS` and all 20
    mutation cases are cut from. Its own first assertion is the ONLY call to
    `_untagged_consult_sites` on `_LIVE_SOURCE` in this file, so no other arm
    asserts that the snapshot itself is covered; every other arm asserts about a
    MUTATED derivative of it, or about `_problems`, or about line distinctness.

    WHAT IS NOT CLAIMED, because the coverage arm does read one thing cut from
    the snapshot: its third conjunct is `len(_TAG_LINES) >= _FLOOR`, and
    `_TAG_LINES` comes from `_LIVE_SOURCE`. So this arm is not the sole arm that
    can NOTICE a dirty snapshot. Measured 2026-09-09 by making `_LIVE_SOURCE`
    diverge from the file on disk by one deleted tag line while `RESPONDER`
    still pointed at the real file: 26 cases go red across 10 arms, this one
    among them. Its job is DIAGNOSTIC rather than exclusive - it is the only one
    whose failure names the baseline rather than its own mutation. A claim that
    it is the SOLE detector of anything would be the third reversal of this
    docstring and is not made.
    """
    assert _untagged_consult_sites(_LIVE_SOURCE, RELPATH) == []
    assert len(_TAG_LINES) >= _FLOOR, _TAG_LINES


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


# ---------------------------------------------------------------------------
# LINE IDENTITY IS NOT SITE IDENTITY. The two directions of the coverage
# comparison are made between sets of LINE NUMBERS, so one tag can cover two
# accepted sites that share a line and both directions stay green. The source
# below is HAND-TYPED rather than generated from the rule it refutes.
# ---------------------------------------------------------------------------


_SYNTHETIC_TWO_SITES_ON_ONE_LINE = (
    "def _run_once():\n"
    "    result = {}\n"
    "    agreed = True\n"
    "    why = None\n"
    f"    {_TAG}oneliner\n"
    "    if agreed: result['z'] = agreed or why\n"
    "    return result\n"
)


def test_two_accepted_sites_on_one_line_defeat_line_identity():
    """THE REFUTATION that drives the coverage arm's distinct-line conjunct.

    The `if` and the subscript write on that one line are BOTH shapes ceiling
    item 5 lists as ACCEPTED, so this is not an instance of the open-shapes
    paragraph - it is a hole inside the shapes the census does see. Two nodes,
    one line, one tag: the tag half and the site half agree and the census
    reports nothing, which is why `_sites_sit_on_distinct_lines` is asserted
    rather than assumed. `ruff` flags E701 on that line, and delegating a claim
    of this module's to a different tool is not something ceiling item 2 may do.
    """
    source = _SYNTHETIC_TWO_SITES_ON_ONE_LINE

    assert _untagged_consult_sites(source, "synthetic") == []
    assert _problems(source, "synthetic") == []
    assert len(_consult_site_node_lines(source)) == 2, _consult_site_node_lines(source)
    assert len(_consult_site_spots(source)) == 1, _consult_site_spots(source)
    assert len(_tags(source, "synthetic")) == 1
    assert _sites_sit_on_distinct_lines(source) is False


def test_one_accepted_site_per_line_is_true_on_the_live_responder():
    """THE CONTROL. Without it a predicate returning False unconditionally
    would score a perfect one out of one on the refutation above."""
    assert _sites_sit_on_distinct_lines(_LIVE_SOURCE) is True
    assert len(_consult_site_node_lines(_LIVE_SOURCE)) == len(
        _consult_site_spots(_LIVE_SOURCE)
    )
    assert len(_consult_site_node_lines(_LIVE_SOURCE)) >= _FLOOR


# ---------------------------------------------------------------------------
# THE REPORT'S TEXT, AND THE ARM THAT CONSUMES IT. Everything above pins the
# `file:line:` prefix of a report and nothing about what it says, and every
# refutation above calls a helper rather than an arm. Both gaps are measured,
# and both are closed here.
# ---------------------------------------------------------------------------


def _line_of_tag_named(name: str) -> int:
    """The live line of the one tag with this name.

    The arms below name a GATE rather than a line number, because a hardcoded
    line rots the moment the responder is edited while a gate name does not.
    """
    found = [lineno for lineno, tag in _tags(_LIVE_SOURCE) if tag == name]
    assert len(found) == 1, f"expected exactly one GATE:{name} tag, found {found}"
    return found[0]


def test_the_report_names_the_statement_and_not_only_its_line():
    """The reported STATEMENT TEXT, asserted rather than described.

    Measured 2026-09-09: replacing the statement in `_untagged_consult_sites`'s
    message with the literal `"advA-garbage"` left the whole file green, because
    every arm pinned only `startswith(f"synthetic:{lineno}: consult site inside ")`.
    The expectation below is HAND-TYPED from reading the responder and is never
    sliced out of the same source line the detector reads, so a detector echoing
    the wrong line cannot agree with it by construction.
    """
    lineno = _line_of_tag_named("hop-budget")
    mutated = _tag_line_removed(_LIVE_SOURCE, lineno)
    untagged = _untagged_consult_sites(mutated, "synthetic")

    assert len(untagged) == 1, untagged
    assert untagged[0] == (
        f"synthetic:{lineno}: consult site inside _run_once() carries no "
        "`# GATE:` tag on the line above it: "
        "'if not within_budget(inbox, bounds):'"
    ), untagged


#: The one statement in `_run_once` the probe below is inserted beneath, and the
#: probe itself. The ANCHOR is matched against the live file so the insertion
#: point cannot rot; the STATEMENT is hand-typed so the expectation is not
#: derived from the thing it grades.
_PROBE_ANCHOR = 'result["actions"] = ["A5"]'
_PROBE_STATEMENT = 'result["advA_probe"] = bool(written) and True'


def _lines_inserted_after_anchor(
    source: str, anchor: str, inserted: list[str]
) -> tuple[str, int]:
    """`source` with `inserted` written directly below the unique `anchor`.

    Returns the mutated source and the 1-based line the FIRST inserted line
    lands on, each line taking the anchor's own indentation. The anchor is
    compared against the STRIPPED line and required to be unique, so a responder
    edit that moves or duplicates it fails loudly here rather than silently
    relocating the probe.
    """
    lines = source.split("\n")
    hits = [index for index, line in enumerate(lines) if line.strip() == anchor]
    assert len(hits) == 1, f"anchor {anchor!r} is not unique in the source: {hits}"
    at = hits[0]
    indent = lines[at][: len(lines[at]) - len(lines[at].lstrip())]
    body = [f"{indent}{line}" for line in inserted]
    return "\n".join(lines[: at + 1] + body + lines[at + 1 :]), at + 2


def _statement_inserted_after_anchor(
    source: str, anchor: str, statement: str
) -> tuple[str, int]:
    """One statement below the anchor - the single-line case of the above."""
    return _lines_inserted_after_anchor(source, anchor, [statement])


def _appended_to_anchor_line(source: str, anchor: str, appended: str) -> tuple[str, int]:
    """`source` with `appended` written onto the END of the unique `anchor` line.

    The sibling of `_lines_inserted_after_anchor`, running the mutation that
    arm cannot: this one adds a site WITHOUT adding a line, so the number of
    accepted-site NODES rises while the number of distinct site LINES does not.
    That is the shape a count-identity proxy cannot tell from a clean file.
    Returns the mutated source and the 1-based line the anchor sits on.
    """
    lines = source.split("\n")
    hits = [index for index, line in enumerate(lines) if line.strip() == anchor]
    assert len(hits) == 1, f"anchor {anchor!r} is not unique in the source: {hits}"
    at = hits[0]
    lines[at] = lines[at] + appended
    return "\n".join(lines), at + 1


def test_a_new_untagged_gate_added_to_run_once_is_reported_by_line():
    """THE SCENARIO ceiling item 2 claims to guard, DRIVEN rather than assumed.

    Every other refutation here DELETES a tag from a site that already exists.
    This one ADDS a gate: a hand-typed accepted-shape statement written into a
    synthetic copy of the responder and never tagged, which is the case an author
    actually hits. `_problems` must stay silent, because no misplaced tag was
    added - and that is what stops this passing against a detector that reports
    every line it is shown.
    """
    mutated, lineno = _statement_inserted_after_anchor(
        _LIVE_SOURCE, _PROBE_ANCHOR, _PROBE_STATEMENT
    )
    untagged = _untagged_consult_sites(mutated, "synthetic")

    assert len(untagged) == 1, untagged
    assert untagged[0] == (
        f"synthetic:{lineno}: consult site inside _run_once() carries no "
        f"`# GATE:` tag on the line above it: {_PROBE_STATEMENT!r}"
    ), untagged
    assert _problems(mutated, "synthetic") == [], _problems(mutated, "synthetic")


def test_the_coverage_arm_itself_goes_red_on_a_newly_added_untagged_gate(
    tmp_path, monkeypatch
):
    """THE ARM'S WIRING, which every refutation above leaves ungraded.

    Measured 2026-09-09: deleting the judgement conjunct from BOTH
    `test_every_consult_site_inside_run_once_carries_a_tag` and its control left
    the suite GREEN, because the parametrized block drives
    `_untagged_consult_sites` directly and nothing ever calls the arm. So this
    arm points the arm at a synthetic responder and requires it to RAISE, then
    points it at an unmutated copy as the control - without that second half a
    redirection that reddened everything would score a perfect one out of one.

    The bytes go out through `write_bytes`. `Path.write_text` emits CRLF on this
    platform, and a `\\r` surviving `source.split("\\n")` sits past the `$`
    anchor in `_GATE_STRICT`, so every real tag would raise `GateTagError` and
    this arm would go red for a reason about the harness rather than about the
    census.
    """
    mutated, lineno = _statement_inserted_after_anchor(
        _LIVE_SOURCE, _PROBE_ANCHOR, _PROBE_STATEMENT
    )
    mutated_file = tmp_path / "mutated_responder.py"
    mutated_file.write_bytes(mutated.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", mutated_file)

    with pytest.raises(AssertionError) as caught:
        test_every_consult_site_inside_run_once_carries_a_tag()

    message = str(caught.value)
    assert f"{RELPATH}:{lineno}:" in message, message
    assert _PROBE_STATEMENT in message, message

    clean_file = tmp_path / "clean_responder.py"
    clean_file.write_bytes(_LIVE_SOURCE.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", clean_file)

    test_every_consult_site_inside_run_once_carries_a_tag()


def test_the_coverage_arm_itself_goes_red_on_two_sites_sharing_one_line(
    tmp_path, monkeypatch
):
    """SOMETHING in the arm reddens on a one-liner. WHICH conjunct is next door.

    `test_two_accepted_sites_on_one_line_defeat_line_identity` drives the
    predicate. This drives the ARM, and it is a different claim: a conjunct can
    be correct and simply not wired into the assertion that matters. Both
    inserted lines are hand-typed.

    WHAT THIS ARM CANNOT DO, stated because it was once claimed to. It cannot
    show that the DISTINCT-LINE conjunct is what reddened the arm. Measured
    2026-09-09: substituting the coincidental proxy
    `len(sites) == len(_TAG_LINES)` for `_sites_sit_on_distinct_lines(source)`
    left this arm GREEN, because the inserted line raises the distinct site
    lines to 21 against a `_TAG_LINES` frozen at 20 - counts re-derived
    2026-09-10 - and the proxy reddens too.
    No payload here fixes that - the phrase "distinct lines" and the colliding
    line number are both in the message whichever conjunct fired. The
    discrimination needs a DIFFERENT SOURCE and lives in
    `test_the_coverage_arm_reddens_on_the_collision_and_not_on_a_count_identity`
    below. The docstring's earlier claim that "the arm can only go red on the
    fourth" was about the other three conjuncts and did not cover a substituted
    fourth; it is dropped rather than repaired.
    """
    mutated, first = _lines_inserted_after_anchor(
        _LIVE_SOURCE,
        _PROBE_ANCHOR,
        [f"{_TAG}oneliner", "if agreed: result['z'] = agreed or why"],
    )
    collision = first + 1
    assert _untagged_consult_sites(mutated, "synthetic") == []
    assert _problems(mutated, "synthetic") == []
    assert len(_consult_site_node_lines(mutated)) == len(_consult_site_spots(mutated)) + 1

    mutated_file = tmp_path / "oneliner_responder.py"
    mutated_file.write_bytes(mutated.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", mutated_file)

    with pytest.raises(AssertionError) as caught:
        test_every_consult_site_inside_run_once_carries_a_tag()

    message = str(caught.value)
    assert "distinct lines" in message, message
    assert f"Colliding lines: [{collision}]" in message, message


#: The one accepted site the arm below EXTENDS rather than follows, and the
#: second accepted site appended onto its line. The ANCHOR is a tagged site in
#: the live responder and is matched against it, so the mutation cannot land on
#: a line that has moved; the APPENDED half is hand-typed. `;` is what puts a
#: second `ast.Assign` on the SAME `lineno`, which is the whole point.
_COLLISION_ANCHOR = 'result["termination"] = "exhausted" if empty_only else "refused"'
_COLLISION_APPENDED = '; result["advG_probe"] = written or True'


def test_the_coverage_arm_reddens_on_the_collision_and_not_on_a_count_identity(
    tmp_path, monkeypatch
):
    """THE WELD IS GRADED FOR WHICH CONJUNCT FIRED, not merely THAT one did.

    `test_the_coverage_arm_itself_goes_red_on_two_sites_sharing_one_line`
    proves the arm reddens on a one-liner. It does NOT prove the DISTINCT-LINE
    conjunct is what reddened it, and measured 2026-09-09 that gap is real:
    substituting the COINCIDENTAL PROXY `len(sites) == len(_TAG_LINES)` for
    `_sites_sit_on_distinct_lines(source)` - true today at 20/20, re-derived
    2026-09-10, and not the
    distinct-line property at all - left the whole file GREEN at 69 passed,
    because the proxy happens to redden on that one-liner too (21 distinct site
    lines against 20 frozen tag lines) and the message says "distinct lines"
    whichever conjunct fired.

    So this arm DEFEATS THE PROXY BY CONSTRUCTION. A second accepted site is
    appended onto an EXISTING tagged site's line with a `;`, so (re-derived
    2026-09-10 against the 20-gate responder):

        accepted site NODES         21        (was 20)
        distinct site LINES         20        (unchanged - this is the trick)
        tags                        20
        untagged reports             0

    Under that source `len(sites) == len(_TAG_LINES)` is 20 == 20 and TRUE, the
    other two conjuncts are TRUE, and ONLY the distinct-line conjunct is False.
    That proxy therefore leaves the arm GREEN here and the real conjunct reddens
    it, which is the discrimination the sibling arm cannot make. The three
    non-judgement conjuncts are asserted below before the arm is driven, so a
    failure cannot be blamed on one of them.

    WHAT THIS ARM DOES NOT DO, corrected 2026-09-09 after an independent
    refutation measured it. Its name says "not on a count identity" and that is
    a claim about a CLASS; what it defeats is ONE LITERAL, the proxy
    `len(sites) == len(_TAG_LINES)`. Seven other wrong fourth conjuncts each
    left all 71 cases green against it - `len(_colliding_site_lines(source))`
    compared `!= 1` or `% 2 == 0`, `len(site_lines)` compared `== len(_TAG_LINES)`,
    `<= len(_TAG_LINES)`, `<= _FLOOR` or `== 18`, and the helper body written
    `lines.count(lineno) == 2`. One collision source cannot see any of them: the
    first two need TWO collisions and the next four need a CLEAN source that
    gained a gate. Those are covered by
    `test_the_coverage_arm_fires_on_every_collision_arity_and_not_on_a_clean_extra_gate`
    and `test_the_collision_detector_names_every_colliding_line_at_three_arities`
    at the end of this file. WHAT IS STILL NOT COVERED anywhere here: a wrong
    conjunct that agrees with the real one on a clean source, on one collision,
    on two collisions and on three sites sharing a line is invisible to all of
    them, because the arities are a sample and not a proof.

    The bytes go out through `write_bytes` for the reason the sibling arm
    records: `Path.write_text` emits CRLF on this platform and a surviving
    `\\r` sits past the `$` anchor in `_GATE_STRICT`.
    """
    mutated, collision = _appended_to_anchor_line(
        _LIVE_SOURCE, _COLLISION_ANCHOR, _COLLISION_APPENDED
    )
    assert _untagged_consult_sites(mutated, "synthetic") == []
    assert len(_consult_site_node_lines(mutated)) == 21
    assert len(_consult_site_spots(mutated)) == 20
    assert len(_consult_site_spots(mutated)) == len(_TAG_LINES)
    assert len(_consult_site_spots(mutated)) >= _FLOOR
    assert _colliding_site_lines(mutated) == [collision]
    assert _sites_sit_on_distinct_lines(mutated) is False

    mutated_file = tmp_path / "collision_responder.py"
    mutated_file.write_bytes(mutated.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", mutated_file)

    with pytest.raises(AssertionError) as caught:
        test_every_consult_site_inside_run_once_carries_a_tag()

    message = str(caught.value)
    assert f"Colliding lines: [{collision}]" in message, message
    assert "Untagged consult sites: none" in message, message

    clean_file = tmp_path / "clean_responder.py"
    clean_file.write_bytes(_LIVE_SOURCE.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", clean_file)

    test_every_consult_site_inside_run_once_carries_a_tag()


# ---------------------------------------------------------------------------
# IDENTITY OVER MORE THAN ONE ARITY. Everything above this line pins a SINGLE
# LITERAL of each property it grades, and a single literal is not a class.
# Measured 2026-09-09 against the file as it stood: SEVEN wrong fourth conjuncts
# and one wrong `_colliding_site_lines` body each left all 71 cases GREEN -
# `len(_colliding_site_lines(source)) != 1`,
# `len(_colliding_site_lines(source)) % 2 == 0`,
# `len(site_lines) == len(_TAG_LINES)`, `len(site_lines) <= len(_TAG_LINES)`,
# `len(site_lines) <= _FLOOR`, `len(site_lines) == 18`, and the helper's own
# `lines.count(lineno) > 1` written as `== 2`; plus `return reported[:2]` and
# `return reported[:3]` in `_untagged_consult_sites`. The single literal the
# arms above pin is `len(sites) == len(_TAG_LINES)`, and killing it says nothing
# about the other seven.
#
# THE SHAPE OF THE ANSWER IS EQUALITY AT SEVERAL ARITIES, NOT A LONGER `len`.
# The mutants fail in OPPOSITE directions and a fix aimed at one leaves the
# other alive: `!= 1` and `% 2 == 0` UNDER-FIRE, staying green on a source
# carrying two real collisions, while `== len(_TAG_LINES)`, `<= _FLOOR` and
# `== 18` OVER-FIRE, reddening a clean and fully tagged responder that simply
# gained a gate. So the block below drives BOTH directions: three collision
# arities that must redden the arm, and one clean-extra-gate source that must
# not.
# ---------------------------------------------------------------------------


#: THE COLLISION FAMILY, at three arities. Every fragment here is HAND-TYPED.
#: Each is appended onto a line that ALREADY carries a tagged accepted site, so
#: the mutation adds accepted-site NODES without adding a site LINE and without
#: leaving anything untagged - the only property that changes is the one the
#: fourth conjunct is about. The anchors are matched against the live responder
#: rather than written as line numbers, so a responder edit relocates the probe
#: instead of rotting it.
_COLLISION_ANCHOR_SECOND = 'result["delivered"] = all(ok for ok, _ in written) and bool(written)'
_COLLISION_APPENDED_SECOND = '; result["advL_second"] = written or True'
_COLLISION_APPENDED_PAIR = (
    '; result["advL_pair_a"] = written or True'
    '; result["advL_pair_b"] = written or True'
)

#: THE OVER-FIRE CONTROL. One EXTRA accepted site, on its own new line, with a
#: correct tag above it - a responder that simply grew a gate and tagged it. Its
#: site count and node count both rise to 21 against an import-time `_TAG_LINES`
#: frozen at 20, which is exactly the difference every count-shaped proxy reads
#: as a fault and the real property does not. Hand-typed, both lines.
_CLEAN_EXTRA_TAG = f"{_TAG}advl-extra"
_CLEAN_EXTRA_STATEMENT = 'result["advL_extra"] = bool(written) and True'


def _collision_source_one() -> tuple[str, list[int]]:
    """The live responder with ONE line carrying two accepted sites."""
    source, line = _appended_to_anchor_line(
        _LIVE_SOURCE, _COLLISION_ANCHOR, _COLLISION_APPENDED
    )
    return source, [line]


def _collision_source_two() -> tuple[str, list[int]]:
    """The live responder with TWO separate lines each carrying two sites.

    This is the arity `!= 1` and `% 2 == 0` cannot survive: both read TRUE at
    two collisions and so leave the coverage arm green while two real collisions
    sit in the file. Appending never renumbers a line, so the second anchor
    match is still valid after the first append.
    """
    source, first = _appended_to_anchor_line(
        _LIVE_SOURCE, _COLLISION_ANCHOR, _COLLISION_APPENDED
    )
    source, second = _appended_to_anchor_line(
        source, _COLLISION_ANCHOR_SECOND, _COLLISION_APPENDED_SECOND
    )
    return source, sorted([first, second])


def _collision_source_three_on_one_line() -> tuple[str, list[int]]:
    """The live responder with ONE line carrying THREE accepted sites.

    Both fragments go on in a single append, because `_appended_to_anchor_line`
    matches the anchor against the STRIPPED line and the first append would make
    a second match impossible. This is the arity the helper mutant
    `lines.count(lineno) == 2` cannot survive: a line with three sites is not a
    line with two, so that body returns nothing and calls a triple collision
    clean.
    """
    source, line = _appended_to_anchor_line(
        _LIVE_SOURCE, _COLLISION_ANCHOR, _COLLISION_APPENDED_PAIR
    )
    return source, [line]


def _clean_extra_gate_source() -> tuple[str, int]:
    """The live responder plus one EXTRA, CORRECTLY TAGGED accepted site."""
    return _lines_inserted_after_anchor(
        _LIVE_SOURCE, _PROBE_ANCHOR, [_CLEAN_EXTRA_TAG, _CLEAN_EXTRA_STATEMENT]
    )


def test_the_collision_detector_names_every_colliding_line_at_three_arities():
    """`_colliding_site_lines` by EQUALITY, at one, two and three sites a line.

    An arm that pins only the `len` of this list grades a number and not the
    list. Measured 2026-09-09: with the body truncated to `sorted(...)[:1]` or
    to `[-1:]` the whole file stayed GREEN at 71 passed, so the coverage arm's
    message named ONE colliding line where TWO existed - defeating the stated
    reason this helper was split out of `_sites_sit_on_distinct_lines` at all.
    Writing `lines.count(lineno) == 2` instead of `> 1` also stayed green, and
    it calls a line carrying THREE accepted sites clean.

    Equality against the anchor-derived lines at all three arities kills those
    three in one arm. The FIRST assertion is the control that stops a helper
    returning a constant from scoring full marks on the other three.
    """
    assert _colliding_site_lines(_LIVE_SOURCE) == []

    one, expected_one = _collision_source_one()
    assert _colliding_site_lines(one) == expected_one, _colliding_site_lines(one)
    assert len(_consult_site_node_lines(one)) == len(_consult_site_spots(one)) + 1

    two, expected_two = _collision_source_two()
    assert len(expected_two) == 2, expected_two
    assert _colliding_site_lines(two) == expected_two, _colliding_site_lines(two)
    assert len(_consult_site_node_lines(two)) == len(_consult_site_spots(two)) + 2

    three, expected_three = _collision_source_three_on_one_line()
    assert _colliding_site_lines(three) == expected_three, _colliding_site_lines(three)
    assert _consult_site_node_lines(three).count(expected_three[0]) == 3, (
        _consult_site_node_lines(three)
    )
    assert len(_consult_site_node_lines(three)) == len(_consult_site_spots(three)) + 2


def test_the_coverage_arm_fires_on_every_collision_arity_and_not_on_a_clean_extra_gate(
    tmp_path, monkeypatch
):
    """THE ARM ITSELF, over both directions, because the mutants run both ways.

    `test_the_coverage_arm_reddens_on_the_collision_and_not_on_a_count_identity`
    drives the arm over ONE collision source and so grades one literal. Seven
    wrong fourth conjuncts survive it, measured 2026-09-09, and they divide:

      UNDER-FIRE, green while real collisions exist -
        `len(_colliding_site_lines(source)) != 1` and `... % 2 == 0` are both
        TRUE at two collisions, so the two-collision source below is what kills
        them. Neither survives ONE collision, which is why one source was not
        enough and three arities are.
      OVER-FIRE, red on a clean file -
        `len(site_lines) == len(_TAG_LINES)`, `len(site_lines) <= len(_TAG_LINES)`,
        `len(site_lines) <= _FLOOR` and `len(site_lines) == 18` are all FALSE on
        a responder that gained ONE correctly tagged gate, because its nodes go
        to 21 against an import-time `_TAG_LINES` frozen at 20. Every collision
        source in the world leaves those four alive; the CLEAN-EXTRA control at
        the end of this arm is what kills them, and it is also what stops a
        conjunct hardcoded to today's 20 from re-pinning in the fourth position
        a number the ceiling says is deliberately not pinned there.

    No `parametrize` here on purpose: an empty list is `1 skipped` at exit 0
    rather than a failure, and these four sources are the arm's own judgement
    rather than its scale. The case count is asserted before the loop, so a case
    silently dropped is a failure.

    The bytes go out through `write_bytes` for the reason the sibling arms
    record: `Path.write_text` emits CRLF on this platform and a surviving `\\r`
    sits past the `$` anchor in `_GATE_STRICT`, which would raise `GateTagError`
    on every real tag and redden this arm for a reason about the harness.
    """
    cases = [
        ("one collision", _collision_source_one()),
        ("two collisions", _collision_source_two()),
        ("three sites on one line", _collision_source_three_on_one_line()),
    ]
    assert len(cases) == 3, cases

    for index, (why, (mutated, expected)) in enumerate(cases):
        assert _untagged_consult_sites(mutated, "synthetic") == [], why
        assert _problems(mutated, "synthetic") == [], why
        assert len(_consult_site_spots(mutated)) >= _FLOOR, why
        assert _colliding_site_lines(mutated) == expected, why

        mutated_file = tmp_path / f"collision_{index}_responder.py"
        mutated_file.write_bytes(mutated.encode("ascii"))
        monkeypatch.setitem(globals(), "RESPONDER", mutated_file)

        with pytest.raises(AssertionError) as caught:
            test_every_consult_site_inside_run_once_carries_a_tag()

        message = str(caught.value)
        assert f"Colliding lines: {expected}" in message, (why, message)
        assert "Untagged consult sites: none" in message, (why, message)

    clean, tag_line = _clean_extra_gate_source()
    assert _untagged_consult_sites(clean, "synthetic") == []
    assert _problems(clean, "synthetic") == []
    assert _colliding_site_lines(clean) == []
    assert len(_consult_site_node_lines(clean)) == len(_TAG_LINES) + 1
    assert len(_consult_site_spots(clean)) == len(_TAG_LINES) + 1
    assert len(_tags(clean, "synthetic")) == len(_TAG_LINES) + 1
    assert clean.split("\n")[tag_line - 1].strip() == _CLEAN_EXTRA_TAG

    clean_file = tmp_path / "clean_extra_gate_responder.py"
    clean_file.write_bytes(clean.encode("ascii"))
    monkeypatch.setitem(globals(), "RESPONDER", clean_file)

    test_every_consult_site_inside_run_once_carries_a_tag()


#: THE MULTIPLICITY ARITIES, and the gates each case deletes. The names are
#: spread through the file so no two chosen tags are neighbours in tag order: a
#: detector that merely widened its window by one cannot satisfy k = 2 or k = 3.
#: Names rather than line numbers, because a line rots on the next responder
#: edit and a gate name does not. Whether this tuple has emptied is asserted by
#: `test_removing_every_tag_reports_every_site_and_bounds_no_truncation`, which
#: is not parametrized and therefore always runs.
_MULTIPLICITY_TAG_NAMES = ("counterparty-agreement", "empty-queue", "refusal-recorded")
_MULTIPLICITY_ARITIES = (1, 2, 3)


def _tag_lines_named(names: tuple[str, ...]) -> list[int]:
    """The live lines of these gates, ascending."""
    return sorted(_line_of_tag_named(name) for name in names)


def _expected_untagged_lines_after_removal(removed: list[int]) -> set[int]:
    """Where each orphaned site lands once every line in `removed` is deleted.

    ARITHMETIC STATED HERE rather than read back out of the detector, which is
    the whole point of a set-equality assertion. A tag at line `t` sits directly
    above its site at `t + 1`. The doomed lines at or below `t` are, for the
    `j`-th tag in ascending order, every doomed line up to and including its
    own - `j + 1` of them - so that site moves from `t + 1` to `t - j`.
    """
    return {lineno - index for index, lineno in enumerate(sorted(removed))}


@pytest.mark.parametrize(
    "arity", _MULTIPLICITY_ARITIES, ids=[f"k{n}" for n in _MULTIPLICITY_ARITIES]
)
def test_removing_k_tags_reports_exactly_those_k_sites_as_a_set(arity):
    """MULTIPLICITY AT THREE ARITIES, BY SET EQUALITY rather than by length.

    `test_removing_two_tags_reports_both_sites_and_not_only_the_first` removes
    exactly TWO tags, so it grades depth at one literal. Measured 2026-09-09:
    with `_untagged_consult_sites` truncated to `return reported[:2]` the whole
    file stayed GREEN at 71 passed, and `return reported[:3]` did too. An author
    who forgot three gates was told about two, and the arm that exists to grade
    multiplicity could not see it.

    Set equality at k = 1, 2 and 3 is strictly stronger than the length check it
    joins: it kills `[:1]` and `[:2]`, and it kills them by naming WHICH sites
    are missing rather than by disagreeing about a count. The unbounded half -
    what stops `[:3]`, `[:4]` and every larger truncation - is
    `test_removing_every_tag_reports_every_site_and_bounds_no_truncation` below,
    because no fixed arity can bound an arbitrary truncation and this arm does
    not claim to.

    NON-ADJACENCY IS ASSERTED, not assumed. The chosen gates are checked to be
    non-neighbours in tag order, so a detector that reported a forgotten site
    plus its neighbour cannot pass k = 2 or k = 3 by accident.
    """
    chosen = _tag_lines_named(_MULTIPLICITY_TAG_NAMES)[:arity]
    assert len(chosen) == arity, chosen

    ordered = sorted(_TAG_LINES)
    positions = [ordered.index(lineno) for lineno in chosen]
    assert all(
        later - earlier > 1 for earlier, later in zip(positions, positions[1:])
    ), positions

    mutated = _tag_lines_removed(_LIVE_SOURCE, chosen)
    untagged = _untagged_consult_sites(mutated, "synthetic")
    reported_lines = {int(report.split(":")[1]) for report in untagged}

    assert reported_lines == _expected_untagged_lines_after_removal(chosen), (
        arity,
        untagged,
    )
    assert _problems(mutated, "synthetic") == [], _problems(mutated, "synthetic")


def test_removing_every_tag_reports_every_site_and_bounds_no_truncation():
    """DEPTH WITHOUT AN ARITY CEILING, which no fixed k can give.

    Set equality at k = 1, 2 and 3 kills `reported[:1]` and `reported[:2]` and
    leaves `reported[:3]` alive - measured 2026-09-09, `[:3]` passed all 71
    cases. Any arm that removes k tags is satisfied by a truncation at k, so the
    only assertion that bounds the whole family is one whose expected set is as
    large as the census gets: every tag removed, every site orphaned, all of
    them named. That kills `reported[:n]` for every n below the tag count, and
    claims nothing about an n at or above it.

    THE ARITY LIST IS GUARDED HERE, and a standalone assertion is right for it.
    An empty `parametrize` list reports `1 skipped` at exit 0 rather than a
    failure, so the block above could silently stop running; this arm is not
    parametrized and always does. Standalone rather than welded into the
    judgement below, following the rule this file already applies to `_FLOOR`: a
    floor is WELDED when it makes the arm's OWN judgement non-vacuous, and
    STANDALONE when it pins the SCALE some other block runs at. The arities are
    that other block's scale.
    """
    assert tuple(_MULTIPLICITY_ARITIES) == (1, 2, 3), _MULTIPLICITY_ARITIES
    assert len(_MULTIPLICITY_TAG_NAMES) == 3, _MULTIPLICITY_TAG_NAMES

    ordered = sorted(_TAG_LINES)
    assert len(ordered) >= _FLOOR, ordered

    mutated = _tag_lines_removed(_LIVE_SOURCE, ordered)
    untagged = _untagged_consult_sites(mutated, "synthetic")
    reported_lines = {int(report.split(":")[1]) for report in untagged}

    assert reported_lines == _expected_untagged_lines_after_removal(ordered), untagged
    assert len(untagged) == len(ordered), untagged
    assert _tags(mutated, "synthetic") == []
    assert _problems(mutated, "synthetic") == [], _problems(mutated, "synthetic")


# ---------------------------------------------------------------------------
# THE CORPUS CENSUS. Every arm above reads ONE file. This block reads the whole
# git-tracked `.py` corpus, because the cross-module half of the scope
# paragraph was a HAND-TYPED COUNT NOBODY RE-DERIVED, and it decayed: true on
# the day it was typed, false three commits later, with no instrument watching.
# Where the gate tags live is a fact about the tree, so it is DERIVED here
# rather than asserted in prose with a date on it.
# ---------------------------------------------------------------------------


#: Files OTHER THAN the responder allowed to carry a strict-grammar gate tag,
#: mapped to the tag NAMES they may carry, in line order.
#:
#: Spelled by NAME and not by a count on purpose. A count of one is satisfied by
#: any one tag, so a second banner replacing the first would slide through.
#:
#: The responder's own entry is deliberately NOT here. It is derived from
#: `_tags` at run time, because a hand-typed responder count is the precise
#: defect this block exists to retire.
#: THE ONE ENTRY IS DOCUMENTATION AND NOT A GATE. `tests/test_responder_delivery_gates.py`
#: opens a section with a banner comment naming the responder gate the arms
#: below it exercise. It is a cross-reference, not a tag on a consult site: the
#: file is a test module, it has no `_run_once`, and nothing in this module ever
#: opens it looking for one. It is allowed because it is real and harmless, and
#: it is LISTED because an unlisted real tag is indistinguishable from a stray
#: one - which is exactly how the previous prose claim died.
_ALLOWED_NON_RESPONDER_TAGS: dict[str, tuple[str, ...]] = {
    "tests/test_responder_delivery_gates.py": ("delivery-write-all",),
}


def _tracked_python_files() -> list[str]:
    """Every git-tracked `.py` path, repo-relative with forward slashes.

    ENUMERATED FROM GIT, NOT FROM A DIRECTORY WALK. A walk down `REPO_ROOT`
    picks up `.claude/worktrees/`, `__pycache__` and untracked scratch, and a
    census whose corpus contains stale copies of the tree is a measurement of
    the copies rather than of the tree.
    """
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(path for path in completed.stdout.split("\0") if path)


def _comment_gate_tags(path: Path) -> list[tuple[int, str]]:
    """Strict-grammar gate tags carried by a REAL COMMENT in `path`.

    `tokenize` and not a text sweep. A regex over lines cannot tell a comment
    from the same characters sitting inside a string literal, and the synthetic
    fixture sources in `tests/test_gate_mutation_runner.py` hold tag-shaped text
    inside string literals on purpose. A text sweep either counts those - wrong,
    they are test DATA describing a tag rather than tags - or gets widened until
    it stops catching real ones, which is the defeat this tree has already taken
    three times. A `tokenize.COMMENT` token draws the line, and the tokenizer
    draws it rather than this module approximating it.

    The whole-line rule from `_tags` is kept: a comment trailing code on the
    same line is not a tag, and the prefix before the token on its own physical
    line is what decides.
    """
    found: list[tuple[int, str]] = []
    with open(path, "rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type != tokenize.COMMENT:
                continue
            if token.line[: token.start[1]].strip():
                continue
            match = _GATE_STRICT.match(token.string)
            if match is not None:
                found.append((token.start[0], match.group(1)))
    return found


def test_the_gate_tag_population_across_the_tracked_corpus_is_derived_not_asserted():
    """WHERE THE GATE TAGS LIVE, DERIVED FROM THE TRACKED CORPUS.

    The scope paragraph in this module's own docstring used to end in a
    hand-typed cross-module count. Nothing was wrong when it was written and
    nothing re-derived it afterwards, so when a section banner shipped in
    another test module the sentence became false in place. This arm is the
    instrument that sentence never had.

    NOT VACUOUS, and not by asserting only a negative. Three positive floors
    ride in the same arm as the judgement:

      1. the corpus is non-empty, and every file the expectation names is
         actually IN it - a sweep over nothing satisfies any negative claim;
      2. the responder's tag count is non-zero and equals `_FLOOR`, derived
         from the sweep rather than typed;
      3. the token-level census of the responder must EQUAL the line-level
         census `_tags` already computes - two instruments of different kinds
         agreeing on a non-empty answer, so a tokenizer walk that silently
         found nothing cannot pass.

    A tokenize failure on any tracked file is a FAILURE and not a skip. A
    corpus with holes in it supports a claim about the corpus minus the holes,
    which is not the claim being made.
    """
    tracked = _tracked_python_files()
    assert tracked, "git ls-files returned no .py paths - this sweep saw nothing"

    census: dict[str, list[tuple[int, str]]] = {}
    unreadable: list[str] = []
    for relpath in tracked:
        full = REPO_ROOT / relpath
        if not full.is_file():
            unreadable.append(f"{relpath}: tracked by git and not on disk")
            continue
        try:
            hits = _comment_gate_tags(full)
        except (SyntaxError, tokenize.TokenError, UnicodeDecodeError) as exc:
            unreadable.append(f"{relpath}: {type(exc).__name__}: {exc}")
            continue
        if hits:
            census[relpath] = hits

    assert unreadable == [], (
        "the sweep could not tokenize these tracked files, so its result is a "
        "statement about a corpus with holes in it and not about this tree:\n"
        + "\n".join("  " + line for line in unreadable)
    )

    for named in [RELPATH, *sorted(_ALLOWED_NON_RESPONDER_TAGS)]:
        assert named in tracked, (
            f"{named} is named by this arm's expectation and is not in the "
            "tracked corpus, so the expectation is about a file the sweep "
            "never opened"
        )

    live = _tags(_LIVE_SOURCE)
    assert live, "the responder census is empty - the anti-vacuity floor is gone"
    assert len(live) == _FLOOR, (len(live), _FLOOR)
    assert census.get(RELPATH) == live, (
        "the token-level census and the line-level census disagree about the "
        "responder, so one of the two instruments is not reading what it "
        f"claims to read:\n  tokens: {census.get(RELPATH)}\n  lines:  {live}"
    )

    expected: dict[str, tuple[str, ...]] = {RELPATH: tuple(name for _, name in live)}
    expected.update(_ALLOWED_NON_RESPONDER_TAGS)
    actual = {
        relpath: tuple(name for _, name in hits) for relpath, hits in census.items()
    }

    offenders: list[str] = []
    for relpath in sorted(set(actual) | set(expected)):
        if actual.get(relpath, ()) == expected.get(relpath, ()):
            continue
        if relpath not in expected:
            offenders.extend(
                f"{relpath}:{lineno}: gate tag {name!r} in a file this module "
                "does not allow to carry one"
                for lineno, name in census[relpath]
            )
            continue
        sited = ", ".join(
            f"{name!r} at line {lineno}" for lineno, name in census.get(relpath, [])
        )
        offenders.append(
            f"{relpath}: expected {list(expected[relpath])} and found "
            + (sited or "nothing")
        )

    assert actual == expected, (
        "the gate-tag population across the tracked corpus is not what this "
        "module says it is. Either the new tag belongs in "
        "`_ALLOWED_NON_RESPONDER_TAGS` with a reason, or it should not be "
        "there at all:\n" + "\n".join("  " + line for line in offenders)
    )
