"""No tracked file may name a sibling project in plain text.

This repository is public. Its tracked files once named six sibling projects of
the same operator's 451 times across 74 files, publishing a roster of a private
fleet as a side effect of documenting this tree's own inheritance. Each sibling
is now an opaque codename and the resolution map is a single gitignored per-host
file.

STATE THE SEVERITY AS THE OPERATOR DID, NOT HIGHER. The ruling was that these
names are not secrets and the tree only needs to be ambiguous about them. This
guard keeps a roster out of a public repository. It does NOT make the fleet
unlearnable to anyone who already knows it, and prior commits and prior blobs
are outside its reach entirely.

WHY THIS FILE EXISTS AT ALL. The scrub itself shipped green with four hits still
in the tree, and an adversary found them afterwards. There was no tracked guard
asserting the property, so nothing could have caught them - a one-off sweep
verifies the moment it ran and nothing after it. All four are recorded below as
the regression corpus, because each escaped for a DIFFERENT structural reason
and a guard that only catches the easy spelling would have caught none of them:

  1. lowercase "riot commander" in a quoted brief - a case-SENSITIVE grep misses
     it, and the original sweep used one.
  2. "daemon_slayer_bundle.d.ts" - underscore-joined, so a pattern expecting a
     space misses it.
  3. "Riot" ending a comment line with "Commander" beginning the next - a
     LINE-BASED matcher is structurally blind to it, and 16 more were found the
     same way earlier in the same session.
  4. A codenamed module explained a sibling by naming a third-party vendor whose
     name is the first word of that project's name. This guard cannot catch that
     class, and says so rather than implying coverage it does not have.

So the matcher here is case-insensitive, joins the whole file before matching so
a wrapped name cannot hide, and treats space, underscore, hyphen, dot and colon
as interchangeable separators.

WHICH GIT GATE THIS MODULE USES, AND WHY THAT ONE.

`require_git_repository()` - the RUN-time per-test shape - called from inside
`_tracked_text_files()`, which is the single function here that shells git.

Not `skip_module_without_git()`. That shape is for a module that touches git
while it is being IMPORTED, typically to build a `parametrize` argument list.
Nothing at module scope here reaches git: the corpus is built inside two test
bodies, and the other arms in this file - the planted-offender controls, the
codenamed-neighbour control, the comment-break pair, the stripped-view
equivalence, the documented-blindness arm, the scoped channel-code pin and its
red control - all work on `tmp_path` fixtures, on two files read by path, or on
this module's own constants. An import-time whole-module skip would throw those
working guards away for a dependency they do not have. Measured 2026-09-20 with
git made unrunnable by stripping it from PATH: 2 of 23 nodes skip, so 21 keep
running.

The gate sits in the helper rather than being repeated at the top of each of the
two callers, so a third caller added later cannot forget it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

# This module necessarily contains every string it searches for. Exempting it by
# name is the honest fix; obfuscating the literals so the sweep cannot see them
# would hide the patterns from the next reader too, and a detector tripping its
# own sweep has bitten this tree before.
SELF = "tests/test_no_sibling_names.py"

# The ledger records the substitution itself and must be able to say what was
# substituted. It is exempt from the FIRST-WORD list only, never from full names.
LEDGER = "docs/LEDGER.md"

_SEP = r"[\s_.:-]*"

_FIRST = ("riot", "legion", "daemon", "red")
_SECOND = ("commander", "wallpaper", "slayer", "moon")

# Two-word names, matched as a product so "red commander" is caught too - a
# partial rename that fixes one half is the likely failure, not a clean revert.
_PAIRED = re.compile(
    "(" + "|".join(_FIRST) + ")" + _SEP + "(" + "|".join(_SECOND) + ")",
    re.IGNORECASE,
)

# One-word names.
#
# `substrate` is the sixth fleet member, joined 2026-09-20. Its false-positive
# cost over the tracked corpus was MEASURED before the literal went in, not
# assumed: 0 hits across 239 examined files. The nearest word in this Genshin
# domain tree is `substats`, which diverges after `subst`, and no tracked file
# contains the substring at all. Its two-letter channel code is deliberately
# NOT here - a word-boundary IGNORECASE match on two letters false-positives
# across a Python tree, and the neighbour-survival arm below pins that choice.
_SOLO = re.compile(
    r"clockspeed|lanternlight|amberstone|legionwallpaper|redmoon|substrate",
    re.IGNORECASE,
)


def _tracked_text_files() -> list[str]:
    """Corpus from `git ls-files`, never an rglob.

    Measured in this tree: a leftover linked worktree under the repo root makes
    an rglob scan a second full copy and report content that is not ours. git
    does not descend into a nested checkout, so a git-sourced corpus is
    structurally immune. 34 of 39 test modules here were immune for exactly this
    reason and 4 were not.

    GATED, because a git-less checkout is a shape this repository is routinely
    received in - Download ZIP, an sdist, a `git archive` extract. Without the
    gate the `check=True` below raises FileNotFoundError and the caller reports a
    FAILURE, which tells a reader nothing is wrong with the code and trains them
    to ignore red. Trackedness is simply UNKNOWABLE there, so the honest answer
    is a skip that names the missing repository. Falling back to an rglob would
    be worse than either: it answers a different question while reporting green,
    which is the exact defect the git-sourced corpus above exists to remove.
    """
    require_git_repository()
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _scan(paths: list[str], root: Path) -> tuple[int, list[str]]:
    """Return (files actually examined, offender descriptions).

    Zero out of zero reads as a pass, so the caller asserts the CHECKED count
    before it looks at the offender list.

    WHAT THIS SCAN IS LEXICALLY BLIND TO. Six classes, measured 2026-09-10
    against this function, each returning zero in a run where a contiguous
    positive control returned two hits - so the zeroes are the detector
    staying silent and not the harness being dead. This is the list of six
    that were measured. It is not a proof that no seventh exists.

      1. A name split across a string-literal concatenation, as in an adjacent
         pair of quoted fragments or an explicit `+` join.
      2. A name with an intervening word between the halves.
      3. A name whose two halves appear in reversed order.
      4. A break on a character outside _SEP that the stripper does not remove.
         Measured on `%`, `;`, `|`, `+`, and on an html comment opener.
      5. A break inside a word rather than at the boundary between the halves.
      6. A tracked file in a non-UTF-8 encoding. `errors="replace"` decodes it
         to noise and it reads clean; measured on a utf-16 file whose utf-8
         twin returned two hits in the same run.

    None of the six is fixed here. Widening the matchers is not the answer to
    them - that response has been tried in this tree and defeated. They are
    written down so the next reader meets them before assuming coverage.
    """
    checked = 0
    offenders: list[str] = []
    for rel in paths:
        if rel == SELF:
            continue
        path = root / rel
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        checked += 1
        # Strip comment markers so a name split across a wrapped comment cannot
        # hide behind the next line's "#". The separator class in the pattern
        # already spans the newline and the indentation, so nothing more is
        # needed - and nothing more is SAFE: a substitution whose pattern can
        # match the empty string fires between every pair of characters and
        # shreds the words it was meant to preserve. That was measured here on
        # this very line, and the positive controls below are what caught it.
        flat = re.sub(r"#|//", " ", body)
        # BOTH matchers read `flat`, so the two make the same class of claim
        # and a reader cannot mistake one matcher's property for the function's.
        # STATE WHAT THAT BUYS, WHICH IS LESS THAN IT LOOKS. The stripping is
        # load-bearing for _PAIRED and INERT for _SOLO: a solo alternative is
        # one contiguous word with no separator class, and the substitution
        # emits a SPACE rather than nothing, so a solo name broken by a comment
        # marker still does not match on either view. Measured 2026-09-10 -
        # over 400000 differential fuzz cases, 61961 of which carried a real
        # solo hit, _SOLO on `flat` and _SOLO on `body` disagreed zero times,
        # and over the 213-path tracked corpus the offender list is identical
        # either way. This is a consistency fix and it closes no detection gap.
        # Two of the five solo names do decompose into the _FIRST x _SECOND
        # product, so a comment break in those two is caught - by _PAIRED, and
        # never by _SOLO. The arm below pins all of that as behaviour.
        for match in _PAIRED.finditer(flat):
            offenders.append(f"{rel} -> {match.group(0)!r}")
        for match in _SOLO.finditer(flat):
            offenders.append(f"{rel} -> {match.group(0)!r}")
    return checked, offenders


def test_the_corpus_is_not_empty_before_anything_is_asserted_about_it():
    """A guard over zero files passes perfectly and proves nothing."""
    paths = _tracked_text_files()
    assert len(paths) > 100, (
        f"git ls-files returned {len(paths)} paths, which is too few to be this "
        "repository. The corpus is wrong, so any clean result below is vacuous."
    )


def test_no_tracked_file_names_a_sibling_project():
    checked, offenders = _scan(_tracked_text_files(), REPO_ROOT)
    assert checked > 100, (
        f"only {checked} files were examined, so a clean result says nothing"
    )
    assert not offenders, (
        f"{checked} files examined and these name a sibling project in plain "
        "text, in a PUBLIC repository. Use the codename. The map from codename "
        "to project is gitignored and must stay that way:\n  "
        + "\n  ".join(sorted(offenders))
    )


@pytest.mark.parametrize(
    "planted",
    [
        # The four that actually escaped the one-off sweep, each restated as the
        # shape that let it through rather than as the literal that was found.
        "an existing project called riot commander.",
        "a generated daemon_slayer_bundle.d.ts inside a mirror",
        "# ported from Riot\n# Commander, which asserts this",
        "vendored from Clockspeed on 2026-09-06",
        # The sixth fleet member, joined 2026-09-20. Not one of the four
        # escapes - added because the matcher was measured blind to it while
        # both shared re-pinned files already sit in the corpus.
        "the slot bucket is shared with Substrate as of 2026-09-20",
    ],
)
def test_the_scan_fires_on_a_planted_offender(tmp_path: Path, planted: str):
    """Without a positive control, a clean result and an unarmed check are the same.

    The first four cases are the four real escapes. A guard that catches only
    the obvious spelling would report clean on three of them. The fifth is the
    sixth fleet member, which was not an escape but a measured blind spot.

    Every case here goes through `_scan`, the SWEEP the real corpus test calls,
    and not through `_SOLO` or `_PAIRED` directly. An arm that matched the
    pattern by hand would pass while the sweep stayed blind, which is the
    failure shape this tree has already been bitten by.
    """
    (tmp_path / "innocent.md").write_bytes(
        b"This file mentions Sibling-C and Sibling-F and is entirely fine.\n"
    )
    (tmp_path / "offender.md").write_bytes(planted.encode("ascii"))

    checked, offenders = _scan(["innocent.md", "offender.md"], tmp_path)

    assert checked == 2, f"the control corpus was {checked} files, expected 2"
    assert len(offenders) == 1, (
        f"expected exactly the planted offender, got {offenders}"
    )
    assert offenders[0].startswith("offender.md"), offenders


def test_the_scan_does_not_flag_a_codenamed_neighbour(tmp_path: Path):
    """A sweep needs two arms: the bad thing is gone AND the neighbours survived.

    A guard that flagged everything would be turned off, and a guard that is
    turned off is worse than one that was never written.
    """
    (tmp_path / "a.md").write_bytes(
        b"Sibling-A through Sibling-F, short codes sa sb sc sd se sf.\n"
        b"The RC_DATA_DIR prefix is this repository's own and is not a sibling.\n"
        b"A red herring, a legion of tests, and a moon phase are all fine.\n"
        b"Bare two-letter channel codes are NOT matched, on purpose: a word-\n"
        b"boundary IGNORECASE match on two letters would fire on ordinary\n"
        b"prose and identifiers. artifact substats, a class, a pass, ss.\n"
    )
    checked, offenders = _scan(["a.md"], tmp_path)
    assert checked == 1
    assert not offenders, offenders


@pytest.mark.parametrize(
    ("planted", "expected"),
    [
        # The comment stripping is LOAD-BEARING for the paired matcher.
        ("# ported from Riot\n# Commander, which asserts this", 1),
        ("riot#commander", 1),
        ("daemon//slayer", 1),
        # It is INERT for the solo matcher. The substitution emits a space, and
        # a solo alternative is one contiguous word with no separator class, so
        # the same break that is caught above is missed here on EITHER view.
        # These three zeroes are the honest residual, not a fixed defect.
        ("# vendored from Clock\n# speed on 2026-09-06", 0),
        ("clock#speed", 0),
        ("lantern//light", 0),
        ("amber#stone", 0),
        ("sub//strate", 0),
        # ...except where a solo name happens to decompose into the paired
        # product, which two of the five do. _PAIRED catches these; _SOLO does
        # not, and moving _SOLO to the stripped view did not change that.
        ("red#moon", 1),
        ("legion//wallpaper", 1),
        # The control. Without it the zeroes above and a dead harness read the
        # same, so it lives in THIS arm rather than in a separate one.
        ("vendored from Clockspeed on 2026-09-06", 1),
    ],
)
def test_a_comment_break_is_caught_in_a_paired_name_and_missed_in_a_solo_one(
    tmp_path: Path, planted: str, expected: int
):
    """Pin the asymmetry as BEHAVIOUR so a later edit cannot move it silently.

    Both matchers read the stripped view, but only one of them can use it. A
    reader who sees a single `flat` feeding two `finditer` calls will assume
    the comment-wrap property covers both names, and it does not. This arm is
    what a future widening of _SOLO, or a change to the stripper's replacement
    string, has to come here and update on purpose.
    """
    (tmp_path / "offender.md").write_bytes(planted.encode("ascii"))
    checked, offenders = _scan(["offender.md"], tmp_path)

    assert checked == 1, f"the control corpus was {checked} files, expected 1"
    assert len(offenders) == expected, (
        f"{planted!r} produced {offenders}, expected {expected} hit(s)"
    )


def test_moving_the_solo_matcher_to_the_stripped_view_changed_no_behaviour():
    """The stripped view and the raw view are the same input to _SOLO.

    Measured before the move and asserted here after it, so the claim in
    _scan's comment is checked rather than remembered. This goes red the day
    the stripper stops emitting a space, or _SOLO grows a separator class -
    either of which would be a real change and needs a deliberate edit here.
    """
    probes = [
        "clock#speed",
        "clock//speed",
        "# vendored from Clock\n# speed on 2026-09-06",
        "lantern#light",
        "amber//stone",
        "clockspeed",
        "a#b clockspeed //c",
    ]
    hits = 0
    for probe in probes:
        flat = re.sub(r"#|//", " ", probe)
        raw_hits = [m.group(0) for m in _SOLO.finditer(probe)]
        flat_hits = [m.group(0) for m in _SOLO.finditer(flat)]
        hits += len(raw_hits)
        assert raw_hits == flat_hits, (
            f"{probe!r} differs between the raw and stripped views: "
            f"{raw_hits} vs {flat_hits}"
        )
    assert hits == 2, (
        f"the probe set produced {hits} solo hits, expected 2 - a probe set "
        "that matches nothing would agree with itself trivially"
    )


def test_the_guard_states_what_it_cannot_catch():
    """A guard that implies coverage it lacks is worse than a missing guard.

    The residual-inference class - a codenamed sentence that identifies a
    project by some OTHER distinctive fact, such as a third-party vendor whose
    name is the project's first word - is not detectable by a name match. One
    real instance shipped past the scrub and was caught by an adversary reading
    for meaning rather than for strings.
    """
    doc = Path(__file__).read_text(encoding="ascii")
    assert "cannot catch that" in doc, (
        "the module docstring must keep stating the class this guard does not "
        "cover, so a reader does not mistake a green run for anonymity"
    )


# The two files below are byte-identical-by-contract across six repositories and
# are pinned by sha256 in tests/test_loop_concurrency.py. NEVER edit them here.
_SHARED_FILES = ("ops/loop/slots.py", "ops/loop/winmutex.py")

# Uppercase channel codes only. Case sensitivity is the whole false-positive
# control and is not a style choice: measured this run over the two files, the
# case-SENSITIVE pattern returns 1 hit and the IGNORECASE pattern returns 7,
# the extra 6 being ordinary lowercase tokens such as the `rc` wait-result
# variable in winmutex. Corpus-wide was rejected before it was written: the
# same codes over the whole `git ls-files` corpus, measured 2026-09-20 across
# the 239 files outside this module, return 1621 case-sensitive and 1831
# IGNORECASE hits. Either figure is a matcher that can only be turned off.
# A brief handed to this slice quoted 1540 and 173 for that pair; those did NOT
# reproduce here and are recorded as not reproduced. The verdict is unchanged,
# the magnitudes are not the brief's.
# RSC leads the alternation so the longer code wins.
_CHANNEL_CODES = ("RSC", "RC", "CS", "LW", "LL", "SS", "RM", "DS")
_CHANNEL = re.compile(r"\b(" + "|".join(_CHANNEL_CODES) + r")\b")

# PINNED BY (file, code) AND BY MULTIPLICITY, NOT BY LINE NUMBER.
#
# A line number decays: these files change only in a joint re-pin round, and
# such a round rewrites bytes wholesale, so an unrelated re-pin would turn this
# arm red for a reason that has nothing to do with a channel code and train a
# reader to bump the number without reading it. (file, code) survives that.
#
# The cost of dropping the line is that a SECOND occurrence of an
# already-pinned code would be invisible to a set comparison - so this is a
# sorted LIST including duplicates, not a set, and a second `RC` in winmutex
# lengthens it and goes red.
# THE ONE REAL VIOLATION WAS REPAIRED ON ROUND B, 2026-09-20, and this list is
# now EMPTY. It held one entry: a comment line in ops/loop/winmutex.py that
# named a sibling by channel code. LW authored the repair, this tree confirmed
# the digest and landed the bytes byte-wise, and the joint re-pin moved in
# tests/test_loop_concurrency.py in the same commit. ONE COMMENT LINE moved and
# no behaviour. Verified this run: the scoped scan over the two shared files
# returns nothing.
#
# AN EMPTY LIST IS THE STRICTER PIN, not a weaker one. The comparison is now
# against zero, so a FIRST occurrence of any channel code in either shared file
# goes red; while the entry stood, only a SECOND one did.
_KNOWN_CHANNEL_CODE_VIOLATIONS: list[tuple[str, str]] = []

_CHANNEL_MESSAGE = (
    "The two shared loop files are byte-identical-by-contract across SIX "
    "repositories and are pinned by sha256, so DO NOT EDIT EITHER FILE HERE. "
    "A local edit desynchronises every carrier that has not moved, and the "
    "sha256 pin then goes red in every one of them. The only fix is a JOINT "
    "RE-PIN ROUND agreed with the other carriers, and this pin is updated in "
    "that same round.\n"
    "If the list GREW, a new channel code entered a shared file and must come "
    "out in that round. If it SHRANK, the known violation was fixed upstream "
    "and this pin is now stale - delete the entry, do not re-add the code."
)


def _channel_code_hits(root: Path) -> list[tuple[str, str]]:
    """Every uppercase channel-code occurrence in the two shared files."""
    hits: list[tuple[str, str]] = []
    for rel in _SHARED_FILES:
        body = (root / rel).read_text(encoding="utf-8", errors="replace")
        for match in _CHANNEL.finditer(body):
            hits.append((rel, match.group(1)))
    return sorted(hits)


def test_the_shared_files_name_no_sibling_channel_code():
    """A CLEAN-TREE ASSERTION since round B, and a known-violation pin before it.

    It was a pin because the one violation lived in a file six carriers hold
    jointly, which this repository could not fix alone: asserting zero then
    would have landed a permanently red arm on a defect owned by all of them,
    and a red arm nobody can close is an arm that gets skipped. Round B closed
    the defect instead - LW authored the repair, this tree landed the bytes and
    moved the sha256 pin in the same commit - so
    `_KNOWN_CHANNEL_CODE_VIOLATIONS` is empty and the comparison is against
    zero, which is strictly stronger than what it replaces.

    THE PIN SHAPE IS KEPT rather than collapsed into `assert not hits`. A
    future joint round may have to admit a violation it cannot close the same
    day, and the reasoning above the list - (file, code) rather than line
    number, a sorted list rather than a set, scoped to the two shared files -
    is what makes that admission safe. It costs one empty literal to keep.

    DELIBERATELY UNGATED. `_channel_code_hits()` reads two files from disk by
    path and never shells git, so this arm holds in a git-less checkout - a ZIP
    download, an sdist, a `git archive` extract - and gating it would skip a
    working guard for a dependency it does not have. That is the same reasoning
    the module docstring gives for the run-time shape, applied in the other
    direction. The conservation check in
    `tests/test_conftest_git_gate_sites.py` measures this: with the gate call
    present it reported this module as having 3 git-or-gate-reaching nodes
    against a row that selects 2.
    """
    hits = _channel_code_hits(REPO_ROOT)
    expected = sorted(_KNOWN_CHANNEL_CODE_VIOLATIONS)
    assert hits == expected, (
        f"the scoped channel-code scan returned {hits}, pinned {expected}.\n"
        + _CHANNEL_MESSAGE
    )


def test_the_scoped_channel_code_scan_can_actually_go_red(tmp_path: Path):
    """Prove the predicate fires, WITHOUT touching the real shared files.

    The real bytes are copied out and a second code is injected into the copy.
    Nothing imports the copies - they are read as text - so no bytecode of
    theirs exists on either side of the control and a stale-pycache read is
    structurally impossible here rather than merely unobserved.
    """
    for rel in _SHARED_FILES:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((REPO_ROOT / rel).read_bytes())

    clean = _channel_code_hits(tmp_path)
    assert clean == sorted(_KNOWN_CHANNEL_CODE_VIOLATIONS), (
        f"the copy disagrees with the real tree: {clean}"
    )

    injected = tmp_path / "ops/loop/slots.py"
    injected.write_bytes(
        injected.read_bytes() + b"\n# re-pinned with LW on 2026-09-20\n"
    )
    dirty = _channel_code_hits(tmp_path)

    assert dirty != clean, "injecting a second channel code changed nothing"
    assert ("ops/loop/slots.py", "LW") in dirty, dirty
    assert (REPO_ROOT / "ops/loop/slots.py").read_bytes() != injected.read_bytes()
