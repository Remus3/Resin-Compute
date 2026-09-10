"""Every `# GATE:<name>` tag in the responder is BOUND to the site it names.

The census already answers "is every consult site tagged, and is every tag
well-formed". It cannot answer "does this NAME sit on THIS STATEMENT", so a
rename, a swap of two tags, or a tag sliding one statement down the file all
pass it clean. This module closes that hole and nothing wider.

THE BINDING RULE IS EQUALITY AT A LOCATED LINE, NEVER CONTAINMENT.

  - The tag is found by the strict hand-typed grammar in `_TAG_STRICT`.
  - The SITE is the line at `tag_line + 1`. It is LOCATED by the tag's own line
    number and never searched for.
  - The binding holds IF AND ONLY IF that line, stripped, EQUALS the hand-typed
    anchor in `_ANCHORS`.
  - `in`, `startswith`, `endswith` and `re.search` are never applied to an
    anchor anywhere in this file. That is enforced by the MECHANISM and not by
    this sentence, and by TWO arms rather than one.
    `test_no_proper_prefix_or_suffix_of_an_anchor_can_restore_a_match`
    substitutes every NON-EMPTY proper prefix and every NON-EMPTY proper suffix
    of every anchor in `_ANCHORS` and requires each one to FAIL.
    `test_an_empty_anchor_is_reported_and_never_matches` carries the one that
    enumeration leaves out - the EMPTY STRING, which is a proper prefix and a
    proper suffix of every anchor there is - one substitution per anchor in
    `_ANCHORS`. The empty case is held apart ON PURPOSE: an empty anchor is a
    HOLE IN THE TABLE, which I1 forbids outright, and not a trim of a real
    anchor, so folding it into the trim enumeration would blur two distinct
    claims into one count.

    Neither sentence above carries a bare case count, and neither should. A
    count sentence must NAME ITS POPULATION - whose enumeration, of what - and a
    population named as "every anchor in `_ANCHORS`" cannot decay away from the
    loop under it when an anchor is retyped, while a number can and would.

WHY EQUALITY AND NOT CONTAINMENT. A containment rule has a repair gradient.
When an anchor stops matching, the cheap repair is to SHORTEN THE NEEDLE until
it matches again, and matcher-widening has defeated this tree three times.
Under equality no trim can ever restore a match, so the only repair available
is to retype the line - which is re-anchoring, which is the thing that was
wanted.

Because `try:` occurs many times file-wide, an equality rule would be unsound
if the site were SEARCHED FOR. It is not: the site is line `tag_line + 1`, so
`# GATE:spawn-failure` binds to exactly one `try:` and to no other.

THE RESIDUAL, ordered written down by the adjudicated call that kept `try:` as
`spawn-failure`'s single anchor. A binding here is a claim about the TAG-TO-SITE
PAIRING ONLY. The mutant `spawn-failure/except-reraise` is INVARIANT under it,
because that mutant rewrites handler BODIES and leaves the `try:` header line
byte-identical, so this module cannot see it. That mutant is not in the standing
survivor set - it is killed elsewhere - so there is no hole here to close; the
limit is written down rather than hidden, which is the point.

CEILING - three limits, stated so a later reader does not overclaim.

  C1 An anchor is a TEXT EQUALITY, not a semantics. The gate name is now a
     CHECKED claim about WHICH SITE it sits on, and is STILL NOT a claim about
     MEANING. `# GATE:hop-budget` bound to `if not within_budget(inbox, bounds):`
     says the name sits on that statement; nothing here says the name
     DESCRIBES it. Census ceiling item 1 is HALF closed by this module, not
     closed.

  C2 A binding DECAYS on any reflow or rewrite of a bound statement, BY DESIGN.
     The repair is to retype the anchor in the SAME COMMIT as the rewrite. A
     decay that is loud is the feature; a decay that is repaired by trimming is
     the defeat, which is why `_ANCHORS` is compared by equality.

  C3 This IS a shape grader - it reads the responder's TEXT and asks a question
     about text, so 34 of the 35 campaign mutants redden it while changing
     nothing it is actually measuring. Its exclusion from the mutation campaign
     is asserted by the RUNNER'S OWN self-test and NEVER here. A module that
     certifies its own exclusion decides its own verdict. Nothing in this file
     adds this file to any exclusion list.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tools import gate_mutation_runner as gmr

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONDER = REPO_ROOT / "tools" / "moon_sync_responder.py"
RELPATH = "tools/moon_sync_responder.py"

#: The responder as a SNAPSHOT taken at import, the same discipline the census
#: uses. Every arm below mutates a COPY of this string and none of them touches
#: the file on disk, so no arm can leave a mutation behind for the next one.
#: `encoding="ascii"` makes a non-ascii responder a COLLECTION FAILURE and not a
#: skip - a corpus with a hole supports a claim about the corpus minus the hole.
_LIVE_SOURCE = RESPONDER.read_text(encoding="ascii")

#: Same reasoning for a responder that will not parse. This is not used for
#: binding - the binding is line-based - it exists so an unparsable responder
#: fails here loudly rather than being quietly bound anyway.
ast.parse(_LIVE_SOURCE)

# PERMISSIVE. Every whole-line comment TRYING to be a tag, in any case and with
# any spacing. It exists to make a near miss VISIBLE, never to accept one.
_TAG_PERMISSIVE = re.compile(r"^[ \t]*#.*\bgate\b[ \t]*:", re.IGNORECASE)

# STRICT. Anchored at both ends with the name captured, so a prefix tag is
# distinguishable from the longer tag it prefixes and every later comparison is
# an equality between captured NAMES rather than a containment test against a
# whole source line. Hand-typed here rather than imported, so the agreement
# asserted in `test_every_tag_binds_and_the_two_instruments_agree` is between
# two independent readings and not between one reading and itself.
_TAG_STRICT = re.compile(r"^[ \t]*# GATE:([a-z0-9]+(?:-[a-z0-9]+)*)$")

#: The floor every arm carries. A table over zero names satisfies every
#: negative claim in this file, so the floor rides INSIDE the assertion it
#: guards rather than in an arm of its own.
_FLOOR = 18

#: The repair instruction carried in every violation message. The reason is
#: part of it: an instruction without a reason is one a hurried reader talks
#: themselves out of.
_REPAIR = (
    "DO NOT TRIM THE ANCHOR, RE-ANCHOR IT - the binding is an EQUALITY at a "
    "located line, so shortening the expectation until it matches again "
    "destroys the claim it was making instead of repairing it; retype the "
    "anchor from the responder in the SAME COMMIT as the rewrite."
)

#: THE TABLE. Every anchor below was RETYPED BY HAND from the responder, tag
#: line by tag line, and is never sliced out of the source it grades - an
#: expectation cut from the same derivation it grades asserts only that the
#: derivation equals itself. Key order is FILE ORDER, which is what makes the
#: adjacent-swap loop below a loop over real neighbours.
_ANCHORS: dict[str, str] = {
    "counterparty-agreement": "if bounds.armed and not agreed:",
    "trial-window": "if not window_open(bounds, now=started):",
    "hop-budget": "if not within_budget(inbox, bounds):",
    "empty-queue": "if not queue:",
    "no-destination": "if not dests:",
    "armed": "if not bounds.armed:",
    "workspace-trust": "if not trusted:",
    "spawn-failure": "try:",
    "draft-verdict": "if reasons:",
    "termination-kind": 'result["termination"] = "exhausted" if empty_only else "refused"',
    "refusals-usable": "if not usable:",
    "repeat-hold": "if not repeat:",
    "refusal-recorded": "if not recorded:",
    "bounce-once": "if not already_bounced and bounce_capacity(DEFAULT_REFUSALS, note.name, agreement):",
    "bounce-write-all": 'result["bounced"] = bool(sent) and all(ok for ok, _ in sent)',
    "bounce-mark": 'if result["bounced"]:',
    "zero-growth": 'if repeat and already_bounced and not result["held"] and not result["bounced"]:',
    "delivery-write-all": 'result["delivered"] = all(ok for ok, _ in written) and bool(written)',
}


# ---------------------------------------------------------------------------
# The instrument
# ---------------------------------------------------------------------------


def _find_tags(source: str) -> list[tuple[int, str]]:
    """Every well-formed tag in `source` as (1-based line, name), in file order.

    Raises `GateTagError` on a NEAR MISS - a line the permissive detector reads
    as a tag and the strict grammar rejects. Reusing the runner's contract here
    is deliberate: counting a near miss as absent is the one failure this
    instrument cannot afford, because an untagged site and a mistyped tag would
    then be indistinguishable.
    """
    found: list[tuple[int, str]] = []
    for number, line in enumerate(source.split("\n"), start=1):
        if not _TAG_PERMISSIVE.match(line):
            continue
        match = _TAG_STRICT.match(line)
        if match is None:
            raise gmr.GateTagError(
                f"line {number}: {line.strip()!r} reads as a gate tag and fails the "
                f"grammar. A tag is a whole-line comment reading exactly hash space "
                f"GATE colon name, with the name in lowercase-hyphen form."
            )
        found.append((number, match.group(1)))
    return found


def _violations(source: str, table: dict[str, str], label: str) -> list[tuple[str, str]]:
    """Every tag in `source` whose SITE does not EQUAL its anchor in `table`.

    Returns (gate name, message) pairs in file order. The site is the line at
    `tag_line + 1`, LOCATED and never searched for, compared STRIPPED and
    compared by `!=` - no containment operator appears here or anywhere else in
    this module.
    """
    lines = source.split("\n")
    out: list[tuple[str, str]] = []
    for number, name in _find_tags(source):
        site = number + 1
        actual = lines[number].strip() if number < len(lines) else "<past end of file>"
        expected = table.get(name)
        if expected is None:
            out.append(
                (
                    name,
                    f"{label}:{site}: gate `{name}` has NO anchor in the table, so its "
                    f"site {actual!r} is bound to nothing. {_REPAIR}",
                )
            )
        elif actual != expected:
            out.append(
                (
                    name,
                    f"{label}:{site}: gate `{name}` is bound to the line below its tag. "
                    f"Expected exactly {expected!r}, found {actual!r}. {_REPAIR}",
                )
            )
    return out


def _line_of_tag_named(name: str) -> int:
    """The live 1-based line of the one tag with this name.

    The arms name a GATE rather than a line number, because a hardcoded line
    rots the moment the responder is edited while a gate name does not.
    """
    found = [number for number, tag in _find_tags(_LIVE_SOURCE) if tag == name]
    assert len(found) == 1, f"expected exactly one GATE:{name} tag, found {found}"
    return found[0]


def _line_inserted_after(source: str, lineno: int, text: str) -> str:
    """`source` with `text` as a new line directly BELOW 1-based `lineno`."""
    lines = source.split("\n")
    assert lineno < len(lines), f"line {lineno} is past the end of the snapshot"
    return "\n".join(lines[:lineno] + [text] + lines[lineno:])


# ---------------------------------------------------------------------------
# I1 / I2 - the invariants, each welded into ONE assertion in its own arm
# ---------------------------------------------------------------------------


def test_the_table_covers_every_live_tag_name():
    """I1 - TABLE COVERAGE, and the floor rides inside the same assertion.

    Three conjuncts, one assertion, on purpose. The key-set equality alone is
    satisfied by a table over zero names against a responder with zero tags, so
    the floor is welded in; and an empty-string anchor would make a match
    unreachable while still passing a size check, so that is welded in too. A
    floor asserted in a SEPARATE arm leaves this one vacuous.
    """
    live = {name for _, name in _find_tags(_LIVE_SOURCE)}
    assert (
        set(_ANCHORS) == live
        and len(_ANCHORS) >= _FLOOR
        and all(anchor != "" for anchor in _ANCHORS.values())
    ), (
        f"table names {sorted(_ANCHORS)} against live names {sorted(live)}; "
        f"table size {len(_ANCHORS)} against floor {_FLOOR}"
    )


def test_every_tag_binds_and_the_two_instruments_agree():
    """I2 - BINDING, with the second instrument welded into the same assertion.

    `_find_tags` here and `gmr.find_gate_tags` in the runner are two independent
    readings of the same grammar. Requiring them to agree on a NON-EMPTY answer
    is what stops a detector that silently found nothing from passing: zero
    violations over zero tags reads as a pass otherwise.
    """
    mine = _find_tags(_LIVE_SOURCE)
    theirs = [(tag.line, tag.name) for tag in gmr.find_gate_tags(_LIVE_SOURCE)]
    found = _violations(_LIVE_SOURCE, _ANCHORS, RELPATH)
    assert found == [] and len(mine) >= _FLOOR and mine == theirs, (
        f"violations {[message for _, message in found]}; "
        f"tags compared {len(mine)} against floor {_FLOOR}; "
        f"this module read {mine}; the runner read {theirs}"
    )


# ---------------------------------------------------------------------------
# R1 - R6 - the refutation half. Without these the arms above are a shape
# grader that reports nothing and scores full marks for it.
# ---------------------------------------------------------------------------


def test_the_live_table_against_the_live_source_reports_nothing():
    """R3 - THE CONTROL.

    Without this, a detector that reports EVERY gate unconditionally scores
    full marks on the swap arm, the rotation arm and the anti-trim arm. The
    non-empty tag count rides in the same assertion for the same reason as I1.
    """
    found = _violations(_LIVE_SOURCE, _ANCHORS, RELPATH)
    assert found == [] and len(_find_tags(_LIVE_SOURCE)) >= _FLOOR, [
        message for _, message in found
    ]


def test_every_adjacent_swap_of_two_anchors_is_reported():
    """R1 - EVERY ADJACENT SWAP IS REPORTED, and DISTINCTNESS (I3) rides along.

    The expected name set is STATED BY THIS ARM from the permutation it just
    applied. It is never read back from the detector, so a detector that
    reports whatever it likes cannot supply its own expectation.

    I3 is welded into the same assertion rather than parked in an arm of its
    own, because pairwise distinctness is EXACTLY what makes a swap detectable:
    two gates sharing one anchor string would swap into each other invisibly and
    this arm would report nothing while claiming a full pass.
    """
    names = list(_ANCHORS)
    pairs = list(zip(names, names[1:]))
    assert len(pairs) == _FLOOR - 1, f"expected {_FLOOR - 1} adjacent pairs, built {len(pairs)}"
    for left, right in pairs:
        table = dict(_ANCHORS)
        table[left], table[right] = _ANCHORS[right], _ANCHORS[left]
        reported = {name for name, _ in _violations(_LIVE_SOURCE, table, RELPATH)}
        assert reported == {left, right} and len(set(_ANCHORS.values())) == len(_ANCHORS), (
            f"swapping {left!r} with {right!r} was reported as {sorted(reported)}; "
            f"distinct anchors {len(set(_ANCHORS.values()))} of {len(_ANCHORS)}"
        )


def test_rotating_every_anchor_is_reported_in_full():
    """R2 - THE FULL ROTATION, which is the case the census cannot see AT ALL.

    Rotating all 18 anchors leaves every one of the census's problem lists
    EMPTY: every site still carries a well-formed tag, every tag name still
    appears exactly once, and no site is untagged. Only a binding notices.
    """
    names = list(_ANCHORS)
    assert len(names) >= _FLOOR, f"rotation over {len(names)} names, floor {_FLOOR}"
    rotated = {name: _ANCHORS[names[(index + 1) % len(names)]] for index, name in enumerate(names)}
    reported = {name for name, _ in _violations(_LIVE_SOURCE, rotated, RELPATH)}
    assert reported == set(names), f"rotation reported {sorted(reported)}, expected all {len(names)}"


def test_no_proper_prefix_or_suffix_of_an_anchor_can_restore_a_match():
    """R4 - ANTI-TRIM, the executable statement of "a trim does not match".

    This is the arm that makes the equality rule a MECHANISM rather than a
    comment. THE POPULATION IS THE LOOP BELOW: every NON-EMPTY proper prefix and
    every NON-EMPTY proper suffix of every anchor in `_ANCHORS` is substituted
    for that gate's anchor and must produce EXACTLY ONE violation naming that
    gate. `cut` starts at 1, so the EMPTY proper prefix and suffix is NOT built
    here; it is the subject of `test_an_empty_anchor_is_reported_and_never_matches`,
    because an empty anchor is a hole in the table rather than a trim of a real
    anchor.

    The arm's NAME states a PROPERTY - no proper prefix or suffix of an anchor
    restores a match - and stays true of the empty string, which does not
    restore one either. This DOCSTRING states the ENUMERATION, and the
    enumeration is the non-empty half of that property. Do not read either as a
    claim about the other, and do not "repair" one to match the other.

    `derived` is the size of the enumeration in closed form, checked against the
    built list in the same assertion, so the population is NAMED rather than
    numbered and no sentence here has to carry a count that could rot.

    THE FLOORS, both welded into the same assertion as the control, because a
    floor living in an arm of its own leaves this arm vacuous:

      - `len(cases) >= 1000` is the TOTAL floor, and it is deliberately NOT
        raised further. Measured over this table: the largest single anchor
        contributes 164 cases, so retyping that one statement down to the length
        of the shortest live anchor - the C2 decay this module documents as BY
        DESIGN - lands the total at 1010. Any literal above 1010 reddens on a
        single legitimate re-anchor while buying no protection from vacuity that
        1000 does not already give.
      - `covered == set(_ANCHORS)` is the tightening the total floor CANNOT
        give. An anchor one character long builds ZERO cases, so that gate would
        be skipped in silence while the total sat comfortably over the floor on
        the strength of the long anchors. Requiring the built cases to name
        EVERY gate in the table closes that, and costs nothing a real anchor
        pays.
    """
    control = [name for name, _ in _violations(_LIVE_SOURCE, _ANCHORS, RELPATH)]
    cases: list[tuple[str, str]] = []
    for name, anchor in _ANCHORS.items():
        for cut in range(1, len(anchor)):
            cases.append((name, anchor[:cut]))
            cases.append((name, anchor[-cut:]))
    derived = sum(2 * (len(anchor) - 1) for anchor in _ANCHORS.values())
    covered = {name for name, _ in cases}
    assert (
        control == []
        and len(cases) == derived
        and len(cases) >= 1000
        and covered == set(_ANCHORS)
    ), (
        f"control reported {control}; built {len(cases)} cases against derived "
        f"{derived}; those cases name {len(covered)} gates of {len(_ANCHORS)}"
    )
    for name, trimmed in cases:
        table = dict(_ANCHORS)
        table[name] = trimmed
        reported = [gate for gate, _ in _violations(_LIVE_SOURCE, table, RELPATH)]
        assert reported == [name], f"trimming {name!r} to {trimmed!r} reported {reported}"


def test_an_empty_anchor_is_reported_and_never_matches():
    """R7 - THE EMPTY ANCHOR, the one proper prefix and suffix R4 does not build.

    The empty string is a proper prefix AND a proper suffix of every anchor
    there is, and R4's enumeration starts at length 1, so R4 never substitutes
    it. Without this arm the anti-trim property would be claimed over a
    population one case per anchor short of the property's own wording.

    It is carried HERE rather than folded into R4 because it is a DIFFERENT
    failure mode. A trim is a real anchor shortened until it matches again; an
    empty anchor is a TABLE WITH A HOLE IN IT, which invariant I1 already
    forbids outright in `test_the_table_covers_every_live_tag_name`. Folding the
    two together would merge two distinct claims into one count and leave
    neither separately readable.

    THE POPULATION IS THE LOOP BELOW: one substitution per anchor in `_ANCHORS`,
    each required to produce EXACTLY ONE violation naming that gate. The
    untrimmed table rides in as the control in the same assertion as the floor,
    for R4's reason - a run over zero cases must not read as a pass.
    """
    control = [name for name, _ in _violations(_LIVE_SOURCE, _ANCHORS, RELPATH)]
    cases: list[tuple[str, str]] = [(name, "") for name in _ANCHORS]
    assert control == [] and len(cases) >= _FLOOR, (
        f"control reported {control}; built {len(cases)} cases against floor {_FLOOR}"
    )
    for name, emptied in cases:
        table = dict(_ANCHORS)
        table[name] = emptied
        reported = [gate for gate, _ in _violations(_LIVE_SOURCE, table, RELPATH)]
        assert reported == [name], f"emptying the anchor for {name!r} reported {reported}"


def test_a_blank_line_or_a_comment_between_a_tag_and_its_site_is_reported():
    """R6 - THE ADJACENCY ARM, closing the common-mode risk.

    Nothing in the responder forbids a blank line or a comment landing BETWEEN a
    tag and the statement it names. If one did, every binding from that point on
    would shift IN THE SAME DIRECTION, which is the shape of failure a
    per-gate arm is worst at seeing. This arm inserts each kind directly under
    one tag and requires the violation to be REPORTED rather than tolerated.

    The inserted comment deliberately carries no `gate:` text, so it cannot be
    mistaken for a tag by the permissive detector and change what is being
    measured.
    """
    tag_line = _line_of_tag_named("hop-budget")
    cases = ["", "    # a comment that is not a tag"]
    assert len(cases) == 2, f"expected a blank case and a comment case, built {len(cases)}"
    for inserted in cases:
        mutated = _line_inserted_after(_LIVE_SOURCE, tag_line, inserted)
        reported = [name for name, _ in _violations(mutated, _ANCHORS, RELPATH)]
        assert reported == ["hop-budget"], f"inserting {inserted!r} reported {reported}"


def test_the_violation_message_names_the_statement_and_the_repair():
    """R5 - THE MESSAGE, pinned whole against a HAND-TYPED expectation.

    Modelled on `test_the_report_names_the_statement_and_not_only_its_line` in
    the census, and for the census's measured reason: an arm that pins only a
    prefix of the message leaves the statement text free to be wrong. The
    expectation below is typed from reading the responder and is never sliced
    out of the same line the detector reads, so a detector echoing the WRONG
    line cannot agree with it by construction.

    The SITE LINE is derived from the live tag rather than typed, because a
    hardcoded line number rots on the next responder edit while the statement
    text does not.
    """
    site = _line_of_tag_named("hop-budget") + 1
    table = dict(_ANCHORS)
    table["hop-budget"] = "if not within_budget(inbox):"
    found = _violations(_LIVE_SOURCE, table, RELPATH)
    assert len(found) == 1, [message for _, message in found]
    assert found[0][1] == (
        f"tools/moon_sync_responder.py:{site}: gate `hop-budget` is bound to the line "
        "below its tag. Expected exactly 'if not within_budget(inbox):', found "
        "'if not within_budget(inbox, bounds):'. "
        "DO NOT TRIM THE ANCHOR, RE-ANCHOR IT - the binding is an EQUALITY at a "
        "located line, so shortening the expectation until it matches again "
        "destroys the claim it was making instead of repairing it; retype the "
        "anchor from the responder in the SAME COMMIT as the rewrite."
    ), found[0][1]
