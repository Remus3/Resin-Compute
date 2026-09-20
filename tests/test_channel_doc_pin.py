"""Pin `docs/CHANNEL.md` - the five-way moon-sync channel convention doc.

These bytes are VENDORED. RC authored them, the fleet agreed to carry them
byte-identical at the same relative path, and the digest is taken over
LF-NORMALISED bytes rather than raw bytes so that a tree whose working copy
checks out CRLF is not red while all five git blobs are identical. This tree
DOES pin markdown to LF - `.gitattributes` carries `*.md text eol=lf` - so the
zero-CR arm below is a valid additional check HERE and would not be in a tree
without that rule. See section 9 of the doc itself.

Seven portable arms, as RC specified, plus two this tree added (arm 3b, byte
hygiene - see REPAIR 4 below; and arm 8, the roster tie - see REPAIR 5).
RC's own gate module is deliberately NOT
vendored: it hard-imports RC-only tooling absent from this tree, and a test
that cannot import is a test that cannot fail. These arms are stdlib only and
import no sweep module from this tree either, so a refactor of a local sweep
cannot quietly cancel the pin.

  1.  the file exists
  2.  its LF-normalised sha256 equals the pinned digest
  3.  it contains zero CR bytes
  3b. every byte is printable ASCII or newline (added here, not RC's)
  4.  the declared CHANNEL_VERSION parses to an int and equals PINNED_VERSION
      (numeral deliberately not named here - this line read "equals 1" and went
      false on the version 2 vendor, in a TRACKED file, with nothing to catch it)
  5.  no heading line carries a date
  6.  every repo-relative path it names resolves, and it cites no file:line
  7.  the filename-variant table is present and parses, every cell pinned
  8.  the section 0 roster table parses, and BOTH the variant table's responder
      columns, all nineteen prose roster/carrier numeral sites and the roster
      CODE-LENGTH claim are DERIVED from it rather than typed, while the nine
      exempt charter-quote and version-1 numerals are held AT FIVE (added here,
      not RC's - see REPAIR 5)

THE RE-PIN BLINDNESS, and why this module is shaped the way it is. An
independent adversary fired 31 disk mutants at the first version of this file.
All 31 were red - but only because arm 2 is a total digest, and with arm 2
neutralised 16 of the 31 SURVIVED. Every future CHANNEL_VERSION 2 re-pin round
is in exactly that state: the digest is recomputed over the new bytes and is
therefore blind by construction, and the other arms are the only thing standing.
`test_every_repin_mutant_is_caught_without_the_digest` encodes that: each mutant
must be caught by some arm OTHER than the digest. Never add a mutant to that
table without checking it is not a no-op - a generalised mutant table quietly
accumulates entries whose target does not occur, and an arm that cannot fire
reads as an arm that passed.

HOW THE CONTROLS WORK, because the first version of this file got this wrong
twice. A control that merely proves sha256 is not a constant function controls
nothing: `_lf_sha256(doc + b"x") != PINNED` is true for every input, and its only
dependence on the doc is that the file opens. Worse, a control whose assertion
is `_lf_sha256(mutant) == PINNED` is a SECOND COPY of arm 2 and fires happily on
mutants containing no CR at all - delete the CR check from arm 3 entirely and
such a control does not notice. Both were deleted.

The replacement is behavioural, not a shape arm: `_run_arm_against` points the
module's `CHANNEL_DOC` at mutated bytes in a tmp file and CALLS THE GUARDED ARM
FUNCTION ITSELF, then asserts it raised. That fails when and only when the
specific arm it guards stops working - whether somebody deletes its assertion,
loosens its matcher, or makes the pin self-fulfilling by recomputing it from the
file. It is deliberately not an `inspect.getsource` token check: that would pin
the arm's TEXT rather than its behaviour, and a shape arm can be satisfied by
code that no longer does anything.

ARM 7 WAS A SHAPE ARM PRETENDING TO BE A PIN, and CS's REVIEW of the shared test
core is what surfaced it. The table it names as the grammar's test-vector source
was graded on column count, row count, the Shape column order, the verdict's
MEMBERSHIP in the admit-or-refuse pair and that the Example cell was backticked,
and four of the seven columns were never read. CS supplied six mutations; run
against THIS tree's arms before any change, five passed arm 7 AND every other
non-digest arm. Two results differ from CS's own tree and both are recorded
because a shared core is only shared where the bytes are:

  * CS reports a PRIMARY verdict flipped from ADMIT to REFUSE passes. HERE IT
    DID NOT. This tree's arm already asserted the exact verdict list
    `["ADMIT", "REFUSE", "REFUSE", "REFUSE"]` rather than only per-cell
    membership, so the flip was caught. This tree was stronger on that one.
  * CS reports deleting the header SEPARATOR row "correctly fails". HERE IT DID
    NOT. `_variant_table_rows` skips a separator row by CONTENT rather than
    requiring one, so deleting it leaves the same four rows and the row walk is
    blind. This tree was weaker on that one, and it now has its own arm.

The repair is CS's: every cell of every row pinned as `EXPECTED_VARIANT_TABLE`,
with the ROW COUNT asserted BEFORE the content compare as the anti-narrowing
control, because rows go absent exactly where a count miscounts and a roster
without its size is half a pin. The per-row WIDTH is asserted before the cell
compare for the same reason - a row short one cell shifts every later cell left
and a content compare would blame the wrong column. Alongside it,
`test_the_variant_table_block_is_present_verbatim` pins the header, the
separator and all four rows as contiguous bytes, which is what catches the
separator deletion and what sees cell whitespace the stripped parse cannot.
All six mutations are now in `_REPIN_MUTANTS`, so they are re-measured in the
digest-blind state every run.

Why none of this was urgent and was worth doing anyway: while the digest pin
holds, any of these mutations also reddens arm 2. The blindness becomes live at
exactly one moment - a CHANNEL_VERSION 2 re-pin, when the digest is legitimately
recomputed and a hand-copied table is most likely to be mangled. That is the one
moment arm 7 was ever going to be load-bearing.

Arm 5's scope. It grades ATX headings (`^#{1,6}\\s`) AND setext headings (a
non-blank line whose successor is all `=` or all `-`), because an ISO date in a
setext heading survived the first version. Setext detection requires the
PRECEDING line to be non-blank, which is also how markdown distinguishes a
setext underline from a horizontal rule, and is exactly the trap the doc's own
section 2 warns about. Two limits, stated rather than implied: a `-` run inside
a fenced code block following a non-blank line would be read as a setext
underline (the doc contains no such construct - measured, 0 setext headings
today), and the ATX population deliberately includes the three `#` lines inside
the note-skeleton fenced block because including them is stricter.

Arm 5's date formats are the ones this fleet actually writes, each verified to
produce ZERO false positives against the real doc's 16 heading lines: ISO, ISO
with a time suffix (`2026-09-15T00:35` - the first version used a trailing `\\b`
and there is no word boundary between the `5` and the `T`, so it missed this),
`2026/09/15`, `09-15-2026`, `20260915`, `15 Sep 2026` and `Sept 15`. The
8-digit-run pattern is the loosest of them; a heading that legitimately carries
an 8-digit number would be a false positive, and no such heading exists today.

Arm 6's resolution rule: a repo-relative path RESOLVES if it exists on disk OR
git reports it ignored. The second disjunct is not a loophole - it is the only
correct rule for this doc, which names `moon_sync_inbox/`, a gitignored
directory the doc itself describes as absent from a fresh clone and every
worktree. Requiring existence would make this test red in exactly the copies the
doc is written for. `git check-ignore` answers in its RETURN CODE, not on stdout,
so that is what is read.

ARM 6 IS THE WEAKEST ARM HERE AND THE HONEST STATEMENT IS THIS: on the current
bytes its graded population is TWO tokens - `docs/CHANNEL.md`, which arm 1
already asserts, and `moon_sync_inbox/`, which resolves only via the ignored
disjunct. So arm 6 contributes approximately ZERO independent existence signal
against CHANNEL_VERSION 1. Its value is entirely prospective: it bites when a
future re-pin adds a path that does not resolve. The extractor was widened so
that it will actually bite then - `.githooks/nope-hook` (extensionless, admitted
by its root segment), `scripts/nope.sh` and `core/nope.pyi` (suffixes added),
and `docs\\nope2.md` (backslash separator, normalised) all escaped the first
version and are now caught.

THIS MODULE MUST BE RUN IN BOTH CHECKOUT SHAPES BEFORE IT IS BELIEVED, and that
sentence was written in blood. Two arms here were built in a worktree, went
green there, merged, and went RED in the primary checkout on identical bytes at
an identical commit. Nothing about the doc differed. `moon_sync_inbox/` is
gitignored, and a gitignored directory exists exactly where somebody created
one: the primary checkout receives notes, a fresh worktree never does. An arm
that asked `Path.exists()` about it was asking about the filesystem it happened
to be standing on, and a population pinned from one shape is a claim about that
shape alone.

The rule generalises past this one directory, which is why it is at the top of
the module rather than beside the arm: every tree in this fleet uses isolated
checkouts for parallel work, so ANY presence that is a property of the checkout
rather than of the repository has this exposure - gitignored paths, generated
artifacts, caches, runtime state under `ops/runtime/`, anything a session
creates. Where a claim can be phrased against the REPOSITORY - what git tracks,
what git ignores, what a tracked file contains - phrase it that way and it holds
everywhere. Where it cannot, it is not a claim this module can make.

No arm can assert this rule; it is a statement about how the module is RUN, and
a test that could check it would have to be run in both shapes to be trusted,
which is the same regress. What is armed instead is the specific mechanism -
`test_a_gitignored_directorys_presence_is_a_property_of_the_checkout` pins the
trailing-slash asymmetry that makes the repository-level question answerable at
all. The rule itself lives here, unarmed and stated, which is the honest shape.

That paragraph was a concession in prose. It is now an ASSERTION, because a
concession nobody re-reads is indistinguishable from a defect nobody found. CS's
REVIEW of the shared test core and an independent adversary in this tree
converged on the same point from opposite directions: arm 6's anti-vacuity guard
was a FLOOR (`len(paths) >= 2`), and a floor advertises independent existence
evidence that a population of one self-reference plus one gitignored directory
does not supply. `test_the_path_scan_walked_a_real_population` now pins the
population EXACTLY and splits it into the disk-resolving half and the
ignored-only half, and asserts in as many words that the disk-resolving half is
the file under test. The guard was PINNED rather than DROPPED: dropping it
removes arm 6's only anti-narrowing control, and a collapsed extractor would
make `_unresolved_paths` return an empty list over an empty population - green
forever, measuring nothing. An exact equality also catches the population
GROWING by accident, which a floor never could.

MEASURED BLIND SPOTS in arm 6, written down rather than left to be discovered:

  * A BARE FILENAME - a token with no separator - is out of scope, structurally
    and permanently. That is the doc's own provenance convention (section 4:
    cites are by bare filename because the notes live in a gitignored
    directory), and closing it would make this test RED on the nine inbox note
    names the doc cites and on `CROSS_REPO_CONVERGENCE_CHARTER.md`, which the
    doc calls "the tracked convergence charter" and which is neither present nor
    tracked in this tree. That charter is RC's artifact. Do NOT edit the doc for
    it - the bytes are pinned in five trees and section 9 forbids a local edit.
    What would settle it is a `CORRECTION-` note to RC naming CHANNEL_VERSION 1,
    landing as a joint v2 re-pin.
  * The ignored disjunct OVER-fires: `ops/runtime/bogus.json` is admitted to the
    population and passes, not because anything checked it, but because a
    gitignore pattern matches it. `test_the_ignored_disjunct_over_fires` pins
    that as a known cost so it cannot be rediscovered as a surprise.
  * A path inside a `%`-bearing or whitespace-bearing token is excluded, which
    is what keeps the doc's one absolute Windows path
    (`%LOCALAPPDATA%\\moonsync\\status.md`) out of a disk lookup.
  * A SPACE-BEARING path is not merely dropped - it is SHATTERED. `_PATHLIKE`'s
    character class excludes the space, so `docs/my notes/thing.md` is admitted
    as the two fragments `docs/my` and `notes/thing.md`, and BOTH are reported
    unresolved. Arm 6 goes red naming two paths that were never in the doc. CS's
    REVIEW describes this narrowing as making such a path "invisible to the
    arm"; measured here it is a false positive rather than a blind spot, which
    fails safe but misdirects. `test_the_path_extractor_shatters_a_space_bearing
    _path` pins it. Separately and cleanly: the space in THIS checkout root
    (`C:\\Resin Compute`) breaks nothing, because resolution is pathlib plus an
    argument LIST to `git check-ignore` and never a shell string - a distinct
    question, pinned separately so the two cannot be confused.
  * A path WRAPPED ACROSS A LINE is seen only as its first fragment, with the
    same false-positive shape. Pinned by
    `test_the_path_extractor_cannot_see_a_line_wrapped_path`.

NEITHER OF THOSE TWO WAS WIDENED, and that is the ruling rather than an
omission. This tree has a measured rule that after a second defeat you stop
widening the matcher and instead narrow the CLAIM to what the mechanism can
support, recording the blind list as measured fact. Admitting spaces makes every
prose phrase around a slash a path candidate; matching across a newline makes
the pattern non-line-local and joins unrelated prose across paragraph breaks.
The doc contains neither construct today, section 9 forbids a local edit that
would add one, and a recorded blind spot is acceptable where an unrecorded one
is the defect.

REPAIR 4, and which half was fixed. The first version's docstring claimed a
non-ASCII byte must raise from `decode("ascii")`. That claim is true only for
bytes above 0x7F: BEL (0x07) and DEL (0x7F) both decode cleanly and sailed
through. They are caught by `tests/test_docs_consistency.py`'s ASCII arm, which
allows 0x09/0x0A/0x0D and rejects everything else below 0x20 or above 0x7E - but
they were NOT caught by this pin, and under a re-pin a smuggled BEL would have
had nothing standing in its way. The CHECK was fixed rather than the wording:
arm 3b asserts every byte is 0x20..0x7E or newline, which is stricter than the
tree-wide arm (it forbids tab and CR outright) and is satisfied by the current
bytes - measured, zero offending bytes.

REPAIR 5 - the roster numeral had no mechanical tie. Arm 7 pinned the grammar
table's header as the literal `| Example | RC gate 6 | RSC | LW | CS | LL | SS |
Shape |`, and the doc's prose spells the roster size as a WORD in eight
sentences. Nothing connected either to section 0's roster table. The sixth
participant was added BY HAND at CHANNEL_VERSION 2 and a seventh would have gone
in the same way. MEASURED HERE before the repair, in the digest-blind state:
`roster row added`, `roster row dropped` and `roster code renamed` were caught by
NO arm at all - `caught == []`, not merely a weak catch.

Arm 8 is the tie, and it is two ties rather than one because they fail on
different mutations. The COUNT is parsed out of the roster table and the doc's
numeral words are rebuilt from it, which catches a row added without a prose
edit and catches a carrier demoted from YES to NO. The CODE SET is parsed out of
the same table and compared against the responder columns the grammar table's
own header names, which catches a row added without a column and catches a code
respelled while every numeral stays correct. Measured after the repair: the
renamed-code mutant is caught ONLY by the column tie and the demoted-carrier
mutant ONLY by the numeral tie, so neither half is decoration.

What arm 8 deliberately does NOT do is sweep the doc for the word `five`.
Section 4 says in capitals that two rows quote charter text saying FIVE and are
left at FIVE on purpose, because VERBATIM is a measured property of the quote
against the charter as it exists today. A blanket sweep would demand exactly the
edit the doc forbids, and would turn a measured status cell into a false one.
`_EXEMPT_FIVE_NUMERALS` is the other half of that: seven passages that must STILL
say five, asserted by `test_the_exempt_five_numerals_survive`. Every sweep in
this tree carries two guards - one that the bad thing is gone, one that the
legitimate neighbours survived - and that is this one's second.

REPAIR 5b - THE FIRST VERSION OF ARM 8 PINNED EIGHT SENTENCES AND THERE ARE
NINETEEN. An independent adversary on the scope-and-siblings lens upheld five
seams and broke this one. Its mutant was an HONEST seven-way re-pin: a seventh
roster row, a seventh responder column, the module's table literals retyped by
hand exactly as section 9 says a carrier does, and all eight pinned sentences
moved to `seven`. NOTHING CAUGHT IT. Eleven roster-bearing numerals across eight
more sites still read `six`, and the digest is blind by construction in a re-pin
round - so that was the seventh participant being missed in eight places exactly
the way the sixth was missed.

Three of those eight are PROVABLY in the defect class rather than exempt, and
`git diff 8212390 93898dd -- docs/CHANNEL.md` is the evidence: `four of five
trees`, `five independent pollers would cost five wakeups` and `Five trees
sharing a prior produce five approvals` were all HAND-EDITED to six at the
version 1 to version 2 bump. A numeral a human had to hand-edit at the last
roster change is precisely the population this arm exists to mechanise, and
calling it illustrative does not survive that diff. Two more - `Editing either
quote to six` and `which is now six` - are the doc talking ABOUT the exempt
charter quotes. Meta-commentary on an exempt quote is not itself exempt: the
quote is frozen at five because VERBATIM is measured against the charter, while
the sentence describing it names the LIVE roster.

REPAIR 5c - the arm over-fired, and the templates are short because of it. The
eight pinned sentences were pinned WHOLE, so rewording `Every thread goes to all
six,` to `Every thread is sent to all six,` reddened the arm while the roster was
perfectly correct. An arm that reddens for an innocent reword is one a
contributor learns to route around. Each site is now the shortest phrase that
still carries the numeral and is still roster-bearing, the failure separates a
STALE NUMERAL from a moved ANCHOR because those want opposite responses, and
`test_every_roster_numeral_site_is_unique` guards the shortening by requiring
every rendered phrase to occur exactly once - a phrase that collided would let a
stale site hide behind the wrong match.

`EXPECTED_TABLE_HEADER` and `EXPECTED_VARIANT_TABLE` stay literal. They are a
cross-tree byte contract and a re-pin must still retype them by hand from the
new doc. Arm 8 is what makes a roster change red WITHOUT a hand edit, and it
holds no roster literal of its own - re-pinning at a seven-tree roster makes it
pass again with nothing here to update.

REPAIR 5d - THE EXEMPT SET WAS TWO SHORT, AND THE RULE COULD NOT BE APPLIED BY
A STRANGER. A third pass built its census BLIND from the doc - it read the
document and ran its sweep before opening this module - because the previous two
passes each worked from the other's list, and agreement between two agents that
share an input is not evidence. The tied set came back byte-for-byte identical,
with zero over-ties. Two findings stood.

First, `_EXEMPT_FIVE_NUMERALS` held seven entries and the census's exempt set is
nine. Against a fully honest seven-way re-pin, dragging section 4's header
sentence (`... SAYS FIVE, AND THEY ARE LEFT AT FIVE ON PURPOSE`) or rule 2's
quoted example (`Rule 2's "2 of 5 reviews" is an EXAMPLE`) to the live roster
was caught by NOTHING - `caught == []` - while the same attack on the other
seven was caught. Rule 6's equivalent sentence WAS pinned and rule 2's twin was
not; that asymmetry was the finding. Reproduced here before the fix.

Second, the exemption rule as first written - "meta-commentary about an exempt
quote is NOT exempt" - contradicted this module's own third exempt entry, which
is meta-commentary about a quote and is exempt. Applied literally by someone who
was not in that conversation it TIES the header sentence, and the module then
renders `SAYS SEVEN ... LEFT AT SEVEN ON PURPOSE`: false, and green. An
ambiguous rule silently becomes a hand judgement, which is the defect class this
arm exists to remove. The rule is restated at `_EXEMPT_FIVE_NUMERALS` in terms
of what a sentence REPORTS, and it is shown there discriminating four sites that
go two each way rather than merely asserted.

REPAIR 5e - a tie can produce a WRONG SENTENCE, and two of them did. `the sixth
participant's watcher is UNMEASURED here` and `that the sixth is asked to meet`
are ordinals. They must move when the roster moves, so tying them is right - but
the mechanical render at seven is `the seventh participant's watcher`, which
SILENTLY DROPS THE SIXTH. Those two are now graded on the ABSENCE of the stale
wording and the failure says a human must write the replacement, naming the
mechanical one as wrong. A red saying "this needs a human" is honest; a green
that drops a participant is not. The weaker claim that buys is stated at
`_HUMAN_REWRITE_SITES` rather than left to be discovered.

REPAIR 5f - the last typed literal on the test side is gone. The roster CODE
shape was `^[A-Z]{2,3}$`, typed. Section 0's own `two-to-three letter CODE` is
itself a roster-dependent literal, so the bounds are parsed out of that claim
and the codes are checked against it: a four-letter tree joining, or the prose
narrowing under the roster, each go red. Deriving the pattern from the codes
instead would have been tautological. Section 6's `two-to-four character code
group` is deliberately NOT tied and the reason is recorded at
`_UNTIED_PARSER_BOUND`: it states what the filename grammar ACCEPTS, not what
the roster IS, and forcing the two to agree would manufacture a red at the first
four-letter tree.

WHAT "GRADE" MEANS HERE, because nobody who argued about it had defined it - this
module included - and two reasonable readings give two different answers. "Reads
the bytes" is what a read-tracer measures. "Can go red because of the content" is
a strictly smaller question, and it is settled by mutation rather than by tracing.
Wherever this file says an arm GRADES something, it means the second: the arm's
outcome can change because of what is in the file.

docs/CHANNEL.md is graded by the pointer, trackedness, ADR-reference and ASCII
arms of `tests/test_docs_consistency.py` via its `_docs_markdown()`, a filesystem
sweep, and by its line-citation arms via its `_tracked_markdown()`, which is
`git ls-files`. The second route sees the file only while git STORES it, so the
set of arms that grade it is smaller in a tree where the file is present but
unstaged. Do not record a number here; re-derive it if you need one. A number
would be an unguarded claim that moves the moment somebody runs `git add`, and
two independent passes already disagreed about it - the low answer turned out to
be exactly the present-but-unstaged set, so the wrong figure looked right by
coincidence and agreed with nothing.

That one file is also not the whole picture, and a figure taken from it
understates the population badly: these bytes are read by tests spread across
many files of the application suite, not only by the docs-consistency arms.
Which is the second reason not to write a number down here.

Finally, a read-tracer is a LOWER BOUND by construction. A grader that reaches
this file through corpus membership alone, or through a subprocess whose reads a
tracer does not patch, is invisible to one. Removing the doc from BOTH the index
and the disk leaves every arm of `tests/test_docs_consistency.py` green -
measured in this worktree, and so evidence against such a grader living in that
file rather than proof of its absence. Note that the present-but-UNSTAGED case is
not green, and for an unrelated reason: this doc cites its own path, so the
trackedness arm fails on it. What would settle the residual is a per-test run
with the doc swapped for a byte-differing copy, asserting that only the
content-sensitive arms change outcome.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANNEL_DOC = REPO_ROOT / "docs" / "CHANNEL.md"

#: sha256 over the LF-normalised bytes. A module-level LITERAL on purpose: a pin
#: recomputed from the file it guards is self-fulfilling. Re-pinning is a JOINT
#: act across all five trees, and a byte change without a CHANNEL_VERSION bump is
#: red by construction because arms 2 and 4 live in the same module.
PINNED_SHA256 = "fc22e86eebe93bb247a91f44835257a3fe717a287c4a3184a8e7a7b9a463fb9c"
PINNED_VERSION = 2

#: The declared version line, DERIVED from the pin rather than typed. At
#: CHANNEL_VERSION 1 the version mutants and the version-parser control each
#: carried the literal `CHANNEL_VERSION: 1`, and vendoring version 2 turned all
#: of them into NO-OPS - a mutant whose target no longer occurs in the doc
#: cannot fail, and a parser control that replaces nothing measures nothing.
#: Deriving the token here makes the next bump carry them along for free.
_DECLARED_VERSION_TOKEN = f"CHANNEL_VERSION: {PINNED_VERSION}"

#: Bytes a line of this doc may contain: printable ASCII plus the line feed.
#: Stricter than the tree-wide docs arm, which also allows tab and CR - this doc
#: contains neither and arm 3 forbids CR anyway.
_MIN_PRINTABLE = 0x20
_MAX_PRINTABLE = 0x7E
_NEWLINE = 0x0A

#: Suffixes that make a separator-bearing token a FILE path. `.sh` and `.pyi`
#: are here because a mutant naming `scripts/nope.sh` or `core/nope.pyi` escaped
#: the first version of this extractor entirely.
_PATH_SUFFIXES = (
    ".py", ".pyi", ".md", ".json", ".ini", ".toml", ".txt", ".ps1", ".sh",
    ".cfg", ".yml", ".yaml", ".js", ".html", ".xml", ".cmd", ".bat", ".lock",
    ".gitignore", ".gitattributes",
)

#: First segments that make an EXTENSIONLESS token a path into this tree, which
#: is how `.githooks/nope-hook` is admitted. Hardcoded and explicit rather than
#: read off disk, so widening it is a visible edit.
_KNOWN_ROOTS = frozenset({
    "agents", "core", "data", "docs", "engines", "headless", "ingest", "ops",
    "scripts", "shell", "surface", "tests", "tools",
    ".githooks", ".claude", ".github", "moon_sync_inbox",
})

#: A plain structural scan, per the slice brief - no sweep module is imported.
#: Accepts either separator so a backslash-separated path cannot slip past.
_PATHLIKE = re.compile(r"[A-Za-z0-9_.%-]+(?:[/\\][A-Za-z0-9_.%-]*)+")

_ATX = re.compile(r"^#{1,6}\s")

_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"

#: Every date shape this fleet writes. Each verified to fire zero times against
#: the real doc's heading lines; the whole set is applied to headings only, which
#: is why the looser members are affordable.
_DATE_PATTERNS = (
    ("iso", re.compile(r"\d{4}-\d{2}-\d{2}")),
    ("iso_slash", re.compile(r"\d{4}/\d{2}/\d{2}")),
    ("us_dash", re.compile(r"\d{2}-\d{2}-\d{4}")),
    ("compact8", re.compile(r"(?<!\d)\d{8}(?!\d)")),
    ("year_month", re.compile(r"(?<!\d)\d{4}-\d{2}(?!\d)")),
    ("month_name_first", re.compile(r"\b(?:" + _MONTHS + r")\w*\.?\s+\d{1,2}\b", re.IGNORECASE)),
    ("day_month_first", re.compile(r"\b\d{1,2}\s+(?:" + _MONTHS + r")\w*\.?", re.IGNORECASE)),
)

#: Citation shapes that bind a claim to a line number. `core/ports:12` carries no
#: suffix, `slots.py#L39` uses the web form, and "line 39 of slots.py" is the
#: prose form - all three escaped the first version's single pattern.
_CITE_PATTERNS = (
    ("suffix_colon", re.compile(r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,6}:\d+")),
    ("slash_colon", re.compile(r"[A-Za-z0-9_.\\-]+/[A-Za-z0-9_.\\-]+:\d+")),
    ("hash_ell", re.compile(r"[A-Za-z0-9_./\\-]+#L\d+")),
    ("prose_line", re.compile(r"\bline\s+\d+\s+of\s+[A-Za-z0-9_./\\-]+", re.IGNORECASE)),
)

_VERSION_LINE = re.compile(r"^CHANNEL_VERSION:\s*(\S+)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Detectors. Each arm's teeth live in a NAMED helper so that a control can call
# the same function the arm calls, rather than a re-implementation of it - a
# re-implemented grader can be weaker than the thing it grades.
# ---------------------------------------------------------------------------

def _doc_bytes() -> bytes:
    return CHANNEL_DOC.read_bytes()


def _doc_text() -> str:
    """Strict ASCII decode. Raises on any byte above 0x7F.

    It does NOT raise on BEL or DEL, both of which are ASCII - arm 3b is what
    catches those. See REPAIR 4 in the module docstring.
    """
    return _doc_bytes().decode("ascii")


def _lf_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _cr_count(data: bytes) -> int:
    return data.count(b"\r")


def _forbidden_bytes(data: bytes) -> list[int]:
    return sorted({
        b for b in data
        if b != _NEWLINE and not (_MIN_PRINTABLE <= b <= _MAX_PRINTABLE)
    })


def _declared_version(text: str) -> int | None:
    """The int on the CHANNEL_VERSION line, or None if absent or unparsable."""
    match = _VERSION_LINE.search(text)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _heading_lines(text: str) -> list[str]:
    """ATX headings plus setext heading TEXT lines.

    A setext underline must follow a NON-BLANK line; a rule after a blank line
    is a horizontal rule, which is the distinction the doc's section 2 warns a
    strict header scanner about.
    """
    lines = text.split("\n")
    out: list[str] = []
    for index, line in enumerate(lines):
        if _ATX.match(line):
            out.append(line)
            continue
        if not line.strip():
            continue
        successor = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if successor and set(successor) in ({"="}, {"-"}):
            out.append(line)
    return out


def _dated_headings(text: str) -> list[str]:
    return [
        line for line in _heading_lines(text)
        if any(pattern.search(line) for _, pattern in _DATE_PATTERNS)
    ]


def _repo_relative_paths(text: str) -> set[str]:
    """Separator-bearing tokens that name a path into a repository.

    Backslashes are normalised to forward slashes so a Windows-separated path
    cannot escape the disk lookup. A bare filename is out of scope by
    construction - see the blind-spot list in the module docstring.
    """
    found: set[str] = set()
    for token in _PATHLIKE.findall(text):
        candidate = token.rstrip(".,;:")
        if not candidate or "%" in candidate:
            continue
        normalised = candidate.replace("\\", "/")
        if "/" not in normalised:
            continue
        if normalised.endswith("/"):
            found.add(normalised)
            continue
        last = normalised.rsplit("/", 1)[-1]
        if last.endswith(_PATH_SUFFIXES):
            found.add(normalised)
            continue
        if normalised.split("/", 1)[0] in _KNOWN_ROOTS:
            found.add(normalised)
    return found


def _is_ignored(candidate: str) -> bool:
    """git check-ignore answers in the RETURN CODE, not on stdout."""
    completed = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", candidate],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _unresolved_paths(text: str) -> list[str]:
    paths = _repo_relative_paths(text)
    return sorted(p for p in paths if not (REPO_ROOT / p).exists() and not _is_ignored(p))


def _line_citations(text: str) -> list[str]:
    found: list[str] = []
    for _, pattern in _CITE_PATTERNS:
        found.extend(pattern.findall(text))
    return found


def _variant_table_rows(text: str) -> list[list[str]]:
    """Rows of the filename-variant table, keyed on its header cells.

    Located by `Example` ... `Shape` rather than by a line number: a line number
    into a 300-line doc decays on the next re-pin.
    """
    rows: list[list[str]] = []
    in_table = False
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if cells and cells[0] == "Example" and cells[-1] == "Shape":
                in_table = True
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # the header separator row
        rows.append(cells)
    return rows


def _variant_table_header(text: str) -> list[str]:
    """The filename-variant table's HEADER cells, which `_variant_table_rows` skips.

    Keyed the same way - `Example` ... `Shape` - so the two functions cannot
    disagree about which table they are looking at.
    """
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and cells[0] == "Example" and cells[-1] == "Shape":
            return cells
    return []


def _roster_table_rows(text: str) -> list[list[str]]:
    """Rows of the section 0 roster table, keyed on its header cells.

    Same idiom as `_variant_table_rows`, and keyed on `Code` ... `Standing in
    the channel` rather than on a line number or a section offset, both of which
    decay on the next re-pin. The seventeen-rule table and the filename-variant
    table must not be picked up - `test_the_roster_table_parser_can_fail`
    measures that.
    """
    rows: list[list[str]] = []
    in_table = False
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if cells and cells[0] == "Code" and cells[-1] == "Standing in the channel":
                in_table = True
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # the header separator row
        rows.append(cells)
    return rows


def _roster_codes(text: str) -> list[str]:
    """The participant CODES, in the order section 0 lists them."""
    return [row[0] for row in _roster_table_rows(text)]


def _carrier_codes(text: str) -> list[str]:
    """The subset that declares YES in the Carrier column.

    Section 0 is explicit that participation and carriage are different things
    and that a carrier count must never be written as a roster count, so the two
    are derived separately here rather than one from the other.
    """
    return [row[0] for row in _roster_table_rows(text) if row[1].startswith("YES")]


# ---------------------------------------------------------------------------
# The behavioural control harness. See "HOW THE CONTROLS WORK" above.
# ---------------------------------------------------------------------------

def _run_arm_against(monkeypatch, tmp_path: Path, arm, data: bytes) -> BaseException | None:
    """Point `CHANNEL_DOC` at `data` and run the real arm. Return what it raised.

    A UnicodeDecodeError counts as a rejection alongside AssertionError: a byte
    above 0x7F makes the strict decode raise, and an arm that refuses to read
    the file at all has still refused the mutant.
    """
    target = tmp_path / "CHANNEL.md"
    target.write_bytes(data)
    monkeypatch.setattr(sys.modules[__name__], "CHANNEL_DOC", target)
    try:
        arm()
    except (AssertionError, UnicodeDecodeError) as exc:
        return exc
    return None


# ---------------------------------------------------------------------------
# Arm 1 - the file exists
# ---------------------------------------------------------------------------

def test_the_channel_doc_exists():
    assert CHANNEL_DOC.is_file(), f"vendored channel doc is missing: {CHANNEL_DOC}"


# ---------------------------------------------------------------------------
# Arm 2 - the LF-normalised digest
# ---------------------------------------------------------------------------

def test_the_lf_normalised_digest_matches_the_pin():
    measured = _lf_sha256(_doc_bytes())
    assert measured == PINNED_SHA256, (
        f"docs/CHANNEL.md LF-normalised sha256 is {measured}, pinned "
        f"{PINNED_SHA256} - these bytes are byte-identical across five "
        "repositories and a re-pin is a joint act, so do not edit the doc to "
        "make this green"
    )


def test_the_digest_arm_has_teeth(monkeypatch, tmp_path):
    """Run ARM 2 ITSELF against doc-derived mutants and require it to reject.

    Goes red if arm 2's assertion is deleted, if its comparison is loosened, or
    if PINNED_SHA256 is ever recomputed from the file it guards.
    """
    original = _doc_bytes()
    mutants = {
        "one byte appended": original + b"x",
        "version bumped": _bump_version(original),
        "one heading reworded": original.replace(b"## 0. Roster", b"## 0. Rosters"),
        "final newline stripped": original.rstrip(b"\n"),
    }
    for label, mutant in mutants.items():
        assert mutant != original, f"no-op mutant: {label}"
        raised = _run_arm_against(monkeypatch, tmp_path, test_the_lf_normalised_digest_matches_the_pin, mutant)
        assert raised is not None, f"arm 2 accepted mutated bytes: {label}"
    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_lf_normalised_digest_matches_the_pin, original
    ) is None, "arm 2 rejects the real bytes"


def test_the_pin_is_a_literal_not_a_recomputation():
    """A pin derived from its own subject is green forever and means nothing."""
    assert re.fullmatch(r"[0-9a-f]{64}", PINNED_SHA256), "the pin is not a bare 64-hex literal"
    source = Path(__file__).read_text(encoding="ascii")
    assignment = re.search(r"^PINNED_SHA256 = (.+)$", source, re.MULTILINE)
    assert assignment is not None
    assert assignment.group(1).strip() == f'"{PINNED_SHA256}"', (
        "PINNED_SHA256 is no longer a quoted literal - a computed pin cannot fail"
    )


# ---------------------------------------------------------------------------
# Arm 3 - zero CR bytes (valid here because of the *.md LF pin)
# ---------------------------------------------------------------------------

def test_the_doc_carries_no_carriage_returns():
    count = _cr_count(_doc_bytes())
    assert count == 0, (
        f"docs/CHANNEL.md carries {count} CR bytes - this tree pins "
        "`*.md text eol=lf` in .gitattributes, so a CRLF working copy means "
        "the file was written with a TEXT write rather than copied at byte "
        "level"
    )


def test_the_carriage_return_arm_has_teeth(monkeypatch, tmp_path):
    """Arm 3 must reject a CRLF mutant that arm 2 provably ACCEPTS.

    The second half is not a second copy of arm 2 - it is the proof that arm 3
    is irreplaceable, and it is gated behind a mutant shown to carry the defect,
    so it cannot pass on a mutant containing no CR at all.
    """
    original = _doc_bytes()
    crlf = original.replace(b"\n", b"\r\n")
    assert _cr_count(crlf) > 0, "the CRLF mutant carries no CR - control measures nothing"

    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_doc_carries_no_carriage_returns, crlf
    ) is not None, "arm 3 accepted a CRLF working copy"

    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_lf_normalised_digest_matches_the_pin, crlf
    ) is None, "arm 2 now rejects CRLF, so the LF-normalisation broke"

    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_doc_carries_no_carriage_returns, original
    ) is None, "arm 3 rejects the real bytes"


# ---------------------------------------------------------------------------
# Arm 3b - byte hygiene. Added here; not one of RC's seven. See REPAIR 4.
# ---------------------------------------------------------------------------

def test_the_doc_is_printable_ascii():
    offenders = _forbidden_bytes(_doc_bytes())
    assert not offenders, (
        f"docs/CHANNEL.md carries bytes outside printable ASCII: "
        f"{[hex(b) for b in offenders]}"
    )


def test_the_byte_hygiene_arm_has_teeth(monkeypatch, tmp_path):
    """BEL and DEL are ASCII and survive a strict decode - this is what stops them."""
    original = _doc_bytes()
    mutants = {
        "BEL": original + bytes([0x07]),
        "DEL": original + bytes([0x7F]),
        "NUL": original + bytes([0x00]),
        "tab": original + b"\t",
        # Built with chr() rather than typed: typing the glyph would make this
        # file violate the ASCII rule it exists to enforce.
        "em dash": original + chr(0x2014).encode("utf-8"),
    }
    for label, mutant in mutants.items():
        assert mutant != original, f"no-op mutant: {label}"
        assert _forbidden_bytes(mutant), f"detector blind to {label}"
        assert _run_arm_against(
            monkeypatch, tmp_path, test_the_doc_is_printable_ascii, mutant
        ) is not None, f"arm 3b accepted {label}"
    # BEL and DEL specifically pass the strict decode, which is the claim the
    # first version of this module got wrong.
    for byte in (0x07, 0x7F):
        bytes([byte]).decode("ascii")
    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_doc_is_printable_ascii, original
    ) is None, "arm 3b rejects the real bytes"


# ---------------------------------------------------------------------------
# Arm 4 - the declared CHANNEL_VERSION
# ---------------------------------------------------------------------------

def test_the_declared_channel_version_is_the_pinned_version():
    declared = _declared_version(_doc_text())
    assert declared is not None, "no parsable CHANNEL_VERSION line in docs/CHANNEL.md"
    assert isinstance(declared, int)
    assert declared == PINNED_VERSION, (
        f"CHANNEL_VERSION is {declared}, this tree pins {PINNED_VERSION} - a "
        "version bump and a digest re-pin land together or not at all"
    )


def test_the_version_parser_can_fail():
    text = _doc_text()
    bumped = f"CHANNEL_VERSION: {PINNED_VERSION + 1}"
    # The non-vacuity control comes first: at the version 2 vendor every line
    # below replaced a token the doc no longer contained, so all three compared
    # the UNCHANGED text and passed while measuring nothing.
    assert text.replace(_DECLARED_VERSION_TOKEN, bumped) != text, (
        f"{_DECLARED_VERSION_TOKEN!r} does not occur in docs/CHANNEL.md - every assertion "
        "below is replacing nothing and this control is vacuous"
    )
    assert _declared_version(text.replace(_DECLARED_VERSION_TOKEN, bumped)) == PINNED_VERSION + 1
    assert _declared_version(text.replace(_DECLARED_VERSION_TOKEN, "CHANNEL_VERSION: two")) is None
    assert _declared_version(
        text.replace(_DECLARED_VERSION_TOKEN, f"CHANNEL_VER: {PINNED_VERSION}")
    ) is None


# ---------------------------------------------------------------------------
# Arm 5 - no heading line carries a date
# ---------------------------------------------------------------------------

def test_no_heading_line_carries_a_date():
    dated = _dated_headings(_doc_text())
    assert not dated, f"dated heading lines in docs/CHANNEL.md: {dated}"


def test_the_dated_heading_scan_walked_a_real_population():
    """Zero out of zero is not a pass - the doc must really have headings."""
    headings = _heading_lines(_doc_text())
    assert len(headings) > 10, f"only {len(headings)} heading lines found - the matcher is broken"
    assert "# Moon-sync channel conventions" in headings


def test_every_date_shape_the_fleet_writes_is_caught_in_a_heading():
    """One planted heading per date format, including the re-pin survivors."""
    planted = {
        "iso": "## 10. Addendum 2026-09-15",
        "iso with time": "## 10. Addendum 2026-09-15T00:35",
        "day month year": "## 10. Addendum 15 Sep 2026",
        "slash": "## 10. Addendum 2026/09/15",
        "abbreviated month": "## 10. Addendum Sept 15",
        "compact": "## 10. Addendum 20260915",
        "us order": "## 10. Addendum 09-15-2026",
    }
    text = _doc_text()
    for label, heading in planted.items():
        mutant = text + "\n" + heading + "\n"
        assert _dated_headings(mutant) == [heading], f"arm 5 missed a {label} date"


def test_a_dated_setext_heading_is_caught():
    """A setext heading carrying a date survived the first version of this arm."""
    text = _doc_text()
    mutant = text + "\nAddendum 2026-09-15\n===================\n"
    assert _dated_headings(mutant) == ["Addendum 2026-09-15"]
    mutant_h2 = text + "\nAddendum 2026-09-15\n-------------------\n"
    assert _dated_headings(mutant_h2) == ["Addendum 2026-09-15"]


def test_the_setext_detector_does_not_confuse_a_horizontal_rule():
    """A rule after a BLANK line is a rule, not a heading."""
    assert _heading_lines("alpha\n\n---\nbravo\n") == []
    assert _heading_lines("alpha\n---\nbravo\n") == ["alpha"]


def test_the_dated_heading_arm_does_not_fire_on_prose():
    """The doc is full of dates in prose - flagging those makes the arm unusable."""
    assert _dated_headings(_doc_text() + "\nMeasured 2026-09-14 under the harness.\n") == []


# ---------------------------------------------------------------------------
# Arm 6 - repo-relative paths resolve, and no line citation
# ---------------------------------------------------------------------------

def test_every_repo_relative_path_resolves():
    unresolved = _unresolved_paths(_doc_text())
    assert not unresolved, (
        "docs/CHANNEL.md names repo-relative paths that neither exist nor are "
        f"gitignored: {unresolved}"
    )


#: Arm 6's ENTIRE graded population, pinned exactly rather than floored, and
#: SPLIT ON WHETHER GIT IGNORES THE TOKEN. Re-measured on the CHANNEL_VERSION 2
#: bytes and UNCHANGED from version 1 - same two tokens, same side of the split
#: each. The label, not the numbers, was what went stale at the version 2
#: vendor, so no numeral is named here now.
#:
#: The split key is load-bearing and it is the second thing this pin got wrong.
#: The first version of it split on `Path.exists()`, which is a fact about the
#: FILESYSTEM THE TEST HAPPENS TO BE STANDING ON. `moon_sync_inbox/` is
#: gitignored, and a gitignored directory exists exactly where somebody created
#: one: notes ARRIVE in the primary checkout, so it is there, while a worktree
#: is a fresh checkout that never created it. Pinned from a worktree the
#: disk-resolving half had one member; run in the primary checkout it had two,
#: and the arm went red on identical bytes at identical commits.
#:
#: Whether git IGNORES a path is a fact about the REPOSITORY - the rule lives in
#: a tracked `.gitignore` and answers the same in every checkout. That is also
#: what the doc is actually claiming when it says a clone has no channel. So the
#: split is by ignore rule, and nothing here asks whether the inbox exists.
EXPECTED_PATHS_GIT_IGNORES = {"moon_sync_inbox/"}
EXPECTED_PATHS_GIT_DOES_NOT_IGNORE = {"docs/CHANNEL.md"}

#: THE TRAILING SLASH IS NOT COSMETIC. `.gitignore`'s rule is `moon_sync_inbox/`,
#: and a trailing slash makes a pattern DIRECTORY-ONLY. Git can only tell that a
#: pathspec names a directory from a trailing slash on the pathspec or from the
#: path being on disk, so a probe that STRIPS the slash falls back to the
#: filesystem and reproduces the exact checkout-dependence this split exists to
#: remove. `_repo_relative_paths` preserves the slash on a directory token; the
#: exact set equality below is what keeps it preserved, and
#: `test_a_gitignored_directorys_presence_is_a_property_of_the_checkout` is what
#: pins the asymmetry itself.


def test_the_path_scan_walked_a_real_population():
    """The population pinned EXACTLY, split by GIT'S RULES, not by the disk.

    THE ARM THIS GUARDS IS VACUOUS ON THESE BYTES AND THIS TEST SAYS SO RATHER
    THAN HIDING IT. CS's REVIEW of the shared test core found that the
    anti-vacuity guard here is satisfied by a self-reference, and an independent
    adversary in this tree found the same thing before that note arrived.
    Measured on the CHANNEL_VERSION 2 bytes, and UNCHANGED from version 1 -
    every figure below was re-derived after the version 2 vendor and moved by
    nothing:

      * the population is exactly TWO tokens;
      * exactly ONE of them is a path git does not ignore - `docs/CHANNEL.md`,
        the file under test, whose existence arm 1 already asserts;
      * the other, `moon_sync_inbox/`, is matched by a tracked ignore rule and
        is what the doc calls the channel a fresh clone does not have.

    So arm 6's only existence evidence is its own subject. A guard reading
    `len(paths) >= 2` implied otherwise.

    WHAT WAS DROPPED HERE, AND WHY IT COULD NOT BE SAVED. The previous version
    also asserted that the set of population members PRESENT ON DISK was exactly
    `{docs/CHANNEL.md}`. That claim is unmakeable: it is true in a fresh
    worktree and false in the primary checkout, where `moon_sync_inbox/` is on
    disk because notes were delivered into it. It is a statement about a
    filesystem rather than about this repository, and there is no wording of it
    that survives both checkout shapes - so it is gone rather than weakened.
    What replaces it is the ignore-rule split, which asserts the same INTENT -
    only one of these two is a path this repository actually carries - out of
    facts that are identical in every checkout. This tree's standing rule is to
    narrow the CLAIM after a defeat rather than widen the matcher, and this is
    that narrowing.

    WHY THE GUARD IS PINNED RATHER THAN DROPPED ENTIRELY. Dropping it removes
    the only anti-narrowing control arm 6 has: if `_repo_relative_paths` ever
    collapsed - a mangled character class, a suffix list edit - then
    `_unresolved_paths` would return an empty list over an empty population and
    arm 6 would be vacuously green forever with nothing to notice. The original
    defect was never that the guard exists; it was that a FLOOR advertises
    independent existence evidence this population does not supply. An exact set
    equality plus the split keeps the anti-narrowing function and states the
    truth about the value. An honest narrow arm beats a guard advertising a
    property it does not have.

    A floor would also have accepted a population that GREW by accident, which
    is the other direction a re-pin can go wrong. This equality does not.
    """
    paths = _repo_relative_paths(_doc_text())
    expected = EXPECTED_PATHS_GIT_IGNORES | EXPECTED_PATHS_GIT_DOES_NOT_IGNORE
    assert paths == expected, (
        f"arm 6's graded population moved.\n"
        f"  measured: {sorted(paths)}\n"
        f"  pinned  : {sorted(expected)}\n"
        "If a re-pin legitimately added a path, add it to the half that matches "
        "git's answer for it, and re-read this docstring - a path that lands in "
        "the NOT-ignored half is the first real existence evidence this arm has "
        "ever had. Keep any trailing slash exactly as the extractor emits it."
    )

    # The split, from git's rules alone. No `Path.exists()` anywhere in it:
    # that is what made this arm answer differently in two checkouts.
    ignored = {p for p in paths if _is_ignored(p)}
    assert ignored == EXPECTED_PATHS_GIT_IGNORES, (
        f"the git-ignored half moved: {sorted(ignored)} - if a trailing slash "
        "was dropped from a directory token, git is now answering from the "
        "filesystem instead of from .gitignore and this arm has silently become "
        "checkout-dependent again"
    )
    assert paths - ignored == EXPECTED_PATHS_GIT_DOES_NOT_IGNORE, (
        f"the not-ignored half moved: {sorted(paths - ignored)}"
    )

    # A path git does not ignore is one this repository carries, so it must be
    # on disk in EVERY checkout. This is the one existence check here that is
    # checkout-independent, and it is also the whole of arm 6's evidence.
    for path in sorted(paths - ignored):
        assert (REPO_ROOT / path).exists(), (
            f"{path} is not ignored and not present - a tracked path missing "
            "from this checkout is a broken checkout, not a doc defect"
        )

    # The vacuity, stated as an assertion so it cannot rot into a surprise: the
    # only thing arm 6 proves to exist is the file arm 1 already proved exists.
    assert paths - ignored == {"docs/CHANNEL.md"}, (
        "arm 6 now resolves something other than its own subject - that is an "
        "IMPROVEMENT, and this assertion plus the docstring above must be "
        "rewritten to stop calling the arm vacuous"
    )

    # Two exclusions that are the extractor working, not the population failing.
    assert not any("moonsync" in p for p in paths), f"absolute Windows path admitted: {sorted(paths)}"
    assert not any(p.startswith("n/a") for p in paths), "the prose token 'n/a' was read as a path"


def test_a_gitignored_directorys_presence_is_a_property_of_the_checkout():
    """THE DEFECT THAT SHIPPED RED, pinned as the mechanism rather than a note.

    This module was built in a worktree and merged into the primary checkout,
    where two of its arms went red on IDENTICAL BYTES AT AN IDENTICAL COMMIT.
    The cause is that `moon_sync_inbox/` is gitignored, and a gitignored
    directory exists exactly where somebody created one - the primary checkout
    receives notes, a fresh worktree never does. CS built the same arm, made the
    same error, and published the same mechanism; this is its repair, measured
    here rather than adopted on its word.

    THE TRAP INSIDE THE REPAIR is the trailing slash. `.gitignore`'s rule is
    `moon_sync_inbox/`, and a trailing slash makes a pattern DIRECTORY-ONLY. Git
    can only know a pathspec names a directory from a trailing slash on the
    pathspec, or from the path being on disk. So a probe that strips the slash
    answers from the FILESYSTEM, which is the defect it was written to remove.

    Measured in this tree, five runs per form per checkout, CS's asymmetry
    REPRODUCES exactly:

      pathspec `moon_sync_inbox`   NOT ignored in the worktree (0/5 rc=0),
                                   ignored in the primary      (5/5 rc=0)
      pathspec `moon_sync_inbox/`  ignored in BOTH             (5/5 rc=0)

    and `git check-ignore -v` returns the identical rule line
    `.gitignore:115:moon_sync_inbox/` in both checkouts for the slashed form.

    The assertions below are written so that they hold in BOTH shapes. The
    slashed form is asserted outright because it is a repository fact. The
    unslashed form is asserted as a BICONDITIONAL against disk presence, which
    is the trap stated exactly: without the slash, git's answer IS the
    filesystem's answer.

    `_is_ignored` reads check-ignore's RETURN CODE rather than its stdout, which
    is correct and must not be regressed - check-ignore returns its answer in
    the exit code, and a filter that only looks at stdout is blind to it.
    """
    assert _is_ignored("moon_sync_inbox/"), (
        "the slashed pathspec is no longer ignored - .gitignore's rule moved, "
        "and arm 6's resolution rule must be re-derived before anything else"
    )

    on_disk = (REPO_ROOT / "moon_sync_inbox").exists()
    assert _is_ignored("moon_sync_inbox") == on_disk, (
        "the unslashed pathspec no longer tracks disk presence - git's "
        "directory-only pattern handling changed, and the trailing-slash "
        "reasoning in this module must be re-measured in both checkout shapes "
        f"(on disk here: {on_disk})"
    )

    # The extractor must keep the slash, or the population pin above starts
    # asking the filesystem again without anything saying so.
    assert "moon_sync_inbox/" in _repo_relative_paths(_doc_text()), (
        "the directory token lost its trailing slash in extraction"
    )


def test_the_population_pin_has_teeth_in_both_directions(monkeypatch, tmp_path):
    """The non-vacuity arm for the pin above, and the proof it beats the floor.

    Runs the population guard ITSELF against doc-derived mutants, per the
    control convention at the top of this module - not a re-implementation of
    it, which could be weaker than what it grades.

    The GROWTH case is the one the old `len(paths) >= 2` floor could never
    catch: measured, that floor is still satisfied on a population of three.
    """
    original = _doc_bytes()
    grown = original + b"\nSee `docs/nope-population-sentinel.md`.\n"
    shrunk = original.replace(b"moon_sync_inbox/", b"INBOXDIR")
    assert grown != original and shrunk != original, "no-op mutant"

    # The floor the exact equality replaced, re-stated here only to show it is
    # silent on growth. This is the ONLY place a re-implementation appears, and
    # it is the thing being refuted rather than the thing being trusted.
    assert len(_repo_relative_paths(grown.decode("ascii"))) >= 2, (
        "the old floor would have fired on the growth case after all - "
        "re-derive the defence in the docstring above"
    )

    for label, mutant in (("grown", grown), ("shrunk", shrunk)):
        assert _run_arm_against(
            monkeypatch, tmp_path, test_the_path_scan_walked_a_real_population, mutant
        ) is not None, f"the population pin accepted a {label} population"

    assert _run_arm_against(
        monkeypatch, tmp_path, test_the_path_scan_walked_a_real_population, original
    ) is None, "the population pin rejects the real bytes"


def test_the_verbatim_block_arm_is_the_only_guard_on_the_separator(monkeypatch, tmp_path):
    """Isolation proof: without the block arm, the separator deletion survives.

    This is the measured statement behind the docstring's claim that this tree
    was WEAKER than CS's on that one mutation. `_variant_table_rows` skips a
    separator row by content rather than requiring one, so the row walk returns
    the same four rows either way and arm 7's parse still passes.
    """
    original = _doc_bytes()
    mutant = _drop_table_separator(original)
    assert mutant != original, "no-op mutant - the header or separator spelling moved"

    caught = [
        arm.__name__ for arm in _NON_DIGEST_ARMS
        if _run_arm_against(monkeypatch, tmp_path, arm, mutant) is not None
    ]
    assert caught == ["test_the_variant_table_block_is_present_verbatim"], (
        "the separator deletion is no longer caught by exactly the block arm - "
        f"caught by: {caught}. If another arm now catches it that is an "
        "improvement and this isolation note is stale; if NOTHING catches it "
        "the separator has lost its only guard."
    )


def test_the_path_extractor_shatters_a_space_bearing_path():
    """FINDING THREE, first half - recorded beside the arm, not widened.

    CS reports the path filter "drops any token containing a SPACE, so a
    checkout path with a space in it is invisible to the arm". Measured here,
    that is NOT what this tree's extractor does, and the difference matters:
    `_PATHLIKE`'s character class simply excludes the space, so the regex does
    not drop the token - it SHATTERS it into fragments and admits the fragments.

    `docs/my notes/thing.md` becomes `docs/my` (admitted by its known root) and
    `notes/thing.md` (admitted by its suffix). Neither names anything. Both are
    then reported UNRESOLVED, so arm 6 goes RED on two paths that were never in
    the doc. That is a FALSE POSITIVE, not a blind spot - louder than CS
    describes, and it fails safe rather than silent, but it would send a
    re-pinner hunting for files that do not exist.

    NOT WIDENED, deliberately. This tree has a measured rule that after a second
    defeat you stop widening the matcher and narrow the CLAIM to what the
    mechanism can support, recording the blind list as measured fact. Admitting
    spaces would make every prose phrase around a slash a path candidate. The
    doc contains no space-bearing path today and section 9 forbids a local edit
    to add one, so the cost is bounded and written down here.
    """
    shattered = _repo_relative_paths("See `docs/my notes/thing.md` for more.")
    assert shattered == {"docs/my", "notes/thing.md"}, (
        f"the shatter behaviour changed - re-derive this record: {sorted(shattered)}"
    )
    assert "docs/my notes/thing.md" not in shattered, "the whole token entered the population"
    # And the fragments are not merely admitted, they are reported unresolved.
    assert _unresolved_paths("See `docs/my notes/thing.md` for more.") == [
        "docs/my", "notes/thing.md",
    ]


def test_a_space_in_this_checkout_root_does_not_break_resolution():
    """FINDING THREE, first half, second question - and it is a CLEAN result.

    CS notes the space narrowing "matters more than it looks because at least
    one participating tree's root contains a space". THIS tree is that tree:
    the repo root is `C:\\Resin Compute`. Measured here, the space in the ROOT
    breaks nothing, and the two are separate questions that are easy to run
    together and get wrong.

    The reason is mechanical rather than lucky. Resolution never builds a shell
    string: `(REPO_ROOT / p).exists()` is pathlib, and `_is_ignored` hands
    `git check-ignore` an argument LIST, so no word splitting happens anywhere.
    The narrowing above is about spaces inside a token IN THE DOC; it says
    nothing about the checkout path, and this test is what keeps the two apart.
    """
    if " " not in str(REPO_ROOT):
        pytest.skip(
            "this checkout root carries no space, so the question this arm "
            "exists to answer cannot be asked here - measured on CI, whose "
            "checkout root carries no space anywhere in it. The "
            "arm is a statement about roots that DO carry one, and asserting "
            "the root's shape made it a claim about the MACHINE rather than "
            "about the code. Skipping is the honest answer; the resolution "
            "mechanism itself is graded unconditionally below."
        )
    assert (REPO_ROOT / "docs/CHANNEL.md").exists()
    assert _is_ignored("moon_sync_inbox/")
    assert not _is_ignored("docs/CHANNEL.md")
    assert _unresolved_paths(_doc_text()) == []


def test_the_path_extractor_cannot_see_a_line_wrapped_path():
    """FINDING THREE, second half - REPRODUCED, with the same correction.

    CS: "the backtick pattern cannot see a path wrapped across a line, so a long
    path broken by the doc's own wrapping is not a token at all." Measured here,
    the second clause is wrong in this tree for the same reason as above. The
    wrapped path is not absent - its FIRST fragment is admitted and reported
    unresolved, and its tail, having no separator, is dropped by the bare-
    filename rule. Arm 6 goes red naming a path that does not exist.

    Also not widened, and for a stronger reason than the space case: seeing
    across a newline means the matcher stops being line-local, and a
    multiline-dotall path pattern over a 300-line markdown doc would join
    unrelated prose across paragraph breaks. The doc wraps no path today.
    """
    wrapped = "See `docs/very-long-\nname-sentinel.md` for more."
    found = _repo_relative_paths(wrapped)
    assert found == {"docs/very-long-"}, (
        f"the wrapped-path behaviour changed - re-derive this record: {sorted(found)}"
    )
    assert _unresolved_paths(wrapped) == ["docs/very-long-"]
    # The unwrapped spelling of the same path is seen whole, which is the proof
    # that the newline is the cause and not the name.
    assert _repo_relative_paths("See `docs/very-long-name-sentinel.md` for more.") == {
        "docs/very-long-name-sentinel.md"
    }


def test_the_path_extractor_catches_every_shape_that_escaped_the_first_version():
    """Each of these was admitted by nothing and therefore graded by nothing."""
    escapes = {
        ".githooks/nope-hook": ".githooks/nope-hook",
        "scripts/nope.sh": "scripts/nope.sh",
        "core/nope.pyi": "core/nope.pyi",
        "docs\\nope2.md": "docs/nope2.md",
    }
    for raw, expected in escapes.items():
        found = _repo_relative_paths(f"See `{raw}` for more.")
        assert expected in found, f"extractor still blind to {raw}: {found}"


def test_the_path_resolution_arm_has_teeth(monkeypatch, tmp_path):
    """Run ARM 6 ITSELF against each planted unresolvable path."""
    text = _doc_text()
    for sentinel in (
        "docs/no-such-channel-path-guard-sentinel.md",
        ".githooks/no-such-hook-guard-sentinel",
        "core/no-such-module-guard-sentinel.pyi",
    ):
        assert not (REPO_ROOT / sentinel).exists()
        assert not _is_ignored(sentinel), f"sentinel became gitignored: {sentinel}"
        mutant = (text + f"\nSee `{sentinel}` for more.\n").encode("ascii")
        assert _run_arm_against(
            monkeypatch, tmp_path, test_every_repo_relative_path_resolves, mutant
        ) is not None, f"arm 6 accepted an absent path: {sentinel}"


def test_the_bare_filename_blind_spot_is_real_and_deliberate():
    """Pins the docstring's blind-spot claim so it cannot rot into a surprise."""
    found = _repo_relative_paths("See `CROSS_REPO_CONVERGENCE_CHARTER.md` and `NOPE_CHARTER.md`.")
    assert found == set(), f"bare filenames entered the population: {found}"
    # And the charter really is absent here, which is why admitting bare
    # filenames would turn this test red on correct, pinned bytes.
    assert not (REPO_ROOT / "CROSS_REPO_CONVERGENCE_CHARTER.md").exists()


def test_the_ignored_disjunct_is_load_bearing_and_narrow():
    """`moon_sync_inbox/` resolves ONLY via the ignored disjunct, not on disk."""
    assert _is_ignored("moon_sync_inbox/"), (
        "moon_sync_inbox/ is no longer gitignored here - re-derive arm 6's "
        "resolution rule before touching it"
    )
    assert not _is_ignored("docs/CHANNEL.md")


def test_the_ignored_disjunct_over_fires():
    """A measured COST of the disjunct, pinned so it stays measured.

    `ops/runtime/bogus.json` does not exist and is not graded by anything; it
    passes because a gitignore pattern matches it.
    """
    bogus = "ops/runtime/bogus.json"
    assert bogus in _repo_relative_paths(f"See `{bogus}`.")
    assert not (REPO_ROOT / bogus).exists()
    assert _is_ignored(bogus), "ops/runtime stopped being ignored - the over-fire note is stale"
    assert _unresolved_paths(f"See `{bogus}`.") == []


def test_the_doc_cites_no_line_number():
    cites = _line_citations(_doc_text())
    assert not cites, (
        f"docs/CHANNEL.md carries line-number citations {cites} - a line number "
        "in a doc five trees re-pin decays on the next append, which is why "
        "the doc cites by bare filename"
    )


def test_every_citation_shape_is_caught():
    """Three of these four escaped the first version's single pattern."""
    planted = {
        "suffix and colon": "ops/loop/slots.py:39",
        "backticked": "`tests/test_loop_concurrency.py:141`",
        "no suffix": "core/ports:12",
        "web form": "slots.py#L39",
        "prose form": "line 39 of slots.py",
    }
    for label, cite in planted.items():
        mutant = _doc_text() + "\nSee " + cite + " for the measurement.\n"
        assert _line_citations(mutant), f"citation matcher missed the {label}: {cite}"
    # A bare filename with no line number is the doc's own convention.
    assert not _line_citations("See `CROSS_REPO_CONVERGENCE_CHARTER.md` for provenance.")


# ---------------------------------------------------------------------------
# Arm 7 - the filename-variant table is present and parses
# ---------------------------------------------------------------------------
#
# That table, not a second file, is the grammar's test-vector source. Every tree
# grades its own responder against these rows, so the table losing a row is a
# silent loss of coverage in five trees at once.

EXPECTED_SHAPES = ["PRIMARY", "Variant A", "Variant B", "Variant C"]

#: EVERY CELL OF EVERY ROW, not a shape summary. CS's REVIEW of the shared test
#: core showed that grading column count, row count, the Shape column and the
#: verdict's MEMBERSHIP in the admit-or-refuse pair leaves four of the seven
#: columns ungraded, so the Example names - the actual test vectors - could be
#: replaced with nonsense or swapped between rows and the arm still passed.
#: Measured here before the repair: of CS's six mutations, five passed this
#: tree's arm 7 and every other non-digest arm.
#:
#: The example filenames ARE the grammar's test vectors. Every tree grades its
#: own responder against these strings, so a mangled cell is a silent loss of
#: coverage in five trees at once - and it goes unnoticed at exactly one moment,
#: a CHANNEL_VERSION 2 re-pin, when the digest is legitimately recomputed and a
#: hand-copied table is most likely to be damaged.
EXPECTED_VARIANT_TABLE = [
    [
        "`2026-09-15-0930-from-RC-FYI-example-topic.md`",
        "ADMIT", "routes", "any entry", "no responder", "no responder",
        "UNMEASURED", "PRIMARY",
    ],
    [
        "`2026-09-15-from-RC-FYI-example-topic.md`",
        "REFUSE", "routes", "any entry", "no responder", "no responder",
        "UNMEASURED", "Variant A",
    ],
    [
        "`from-RC-2026-09-15-0930-FYI-example-topic.md`",
        "REFUSE", "zero destinations", "any entry", "no responder", "no responder",
        "UNMEASURED", "Variant B",
    ],
    [
        "`2026-09-15-0930-from-RC-FYI-example-topic.txt`",
        "REFUSE", "routes", "any entry", "no responder", "no responder",
        "UNMEASURED", "Variant C",
    ],
]

#: The header and its separator, pinned as literals. The separator matters on its
#: own: `_variant_table_rows` SKIPS a separator row by content rather than
#: requiring one, so deleting it is invisible to the row walk. Measured here -
#: CS reports its own tree catches that mutation and this tree did NOT.
#:
#: CHANNEL_VERSION 2 INSERTED AN `SS` COLUMN between `LL` and `Shape`, so both
#: of these strings changed and every variant row gained an eighth cell. That
#: sixth participant was added BY HAND, and this comment used to end here saying
#: the roster numeral was still frozen in these literals with nothing tying them
#: to a roster list anywhere in the tree. THAT IS NO LONGER TRUE: arm 8 parses
#: the section 0 roster table and requires the responder columns between
#: `Example` and `Shape` to be exactly that set of CODEs. These strings stay
#: literal on purpose - they are a cross-tree byte contract and a re-pin must
#: still retype them by hand - but a seventh roster row now reddens arm 8 on its
#: own rather than waiting on a human to remember this string exists.
EXPECTED_TABLE_HEADER = "| Example | RC gate 6 | RSC | LW | CS | LL | SS | Shape |"
EXPECTED_TABLE_SEPARATOR = "|---|---|---|---|---|---|---|---|"


def _render_row(cells: list[str]) -> str:
    """The doc's own row spelling, so a pin and a mutant cannot disagree."""
    return "| " + " | ".join(cells) + " |"


def test_the_filename_variant_table_parses():
    """Every cell of every row, not a shape summary.

    THE ORDER OF THESE ASSERTIONS IS LOAD-BEARING. The row count is asserted
    BEFORE the content compare because rows go absent exactly where a count
    miscounts: delete row 2 and a straight content compare reports "row 2 is
    wrong", which reads as a corrupted cell and sends the reader looking in the
    wrong place. A roster without its size is half a pin.

    What this replaced, and why: the previous version graded column count, row
    count, the Shape column order, the verdict's MEMBERSHIP in the admit-or-
    refuse pair and that the Example cell was backticked - and never read four
    of the seven columns. Measured against CS's six mutations before the repair,
    five passed this arm and every other non-digest arm.
    """
    rows = _variant_table_rows(_doc_text())
    assert rows, "the filename-variant table was not found at all"

    # (1) the anti-narrowing control, first.
    assert len(rows) == len(EXPECTED_VARIANT_TABLE), (
        f"expected {len(EXPECTED_VARIANT_TABLE)} variant rows, parsed "
        f"{len(rows)} - a row was added or lost, which is a silent change to "
        f"the grammar's test vectors in five trees at once: {rows}"
    )

    # (2) the per-row width, before the cell compare, for the same reason: a
    #     row short one cell shifts every later cell left and a content compare
    #     would blame the wrong column.
    for index, row in enumerate(rows):
        assert len(row) == len(EXPECTED_VARIANT_TABLE[index]), (
            f"variant row {index} has {len(row)} cells, expected "
            f"{len(EXPECTED_VARIANT_TABLE[index])}: {row}"
        )

    # (3) the content compare - every cell of every row.
    for index, (parsed, expected) in enumerate(zip(rows, EXPECTED_VARIANT_TABLE)):
        assert parsed == expected, (
            f"variant table row {index} does not match the pin.\n"
            f"  parsed  : {parsed}\n"
            f"  expected: {expected}\n"
            "These filenames ARE the grammar's test vectors. Do not edit the "
            "doc to make this green - the bytes are pinned in five trees. If "
            "this is a CHANNEL_VERSION 2 re-pin, retype EXPECTED_VARIANT_TABLE "
            "from the new doc by hand and check every cell."
        )
    assert rows == EXPECTED_VARIANT_TABLE

    # (4) the two derived claims the previous version made, kept because they
    #     say WHAT the table means rather than what it contains. Both are
    #     implied by (3); they survive as documentation that goes red.
    assert [row[-1] for row in rows] == EXPECTED_SHAPES
    # The PRIMARY row is the only ADMIT; RC's gate refuses all three variants.
    assert [row[1] for row in rows] == ["ADMIT", "REFUSE", "REFUSE", "REFUSE"]


def test_the_variant_table_block_is_present_verbatim():
    """The header, its separator and all four rows, as contiguous bytes.

    NOT a second copy of arm 2. Arm 2 is a digest over the whole doc and is
    blind by construction in the one round that matters - a re-pin, where it is
    recomputed over the new bytes. This is a narrow pin over the ONE region
    whose content is a cross-tree contract, and on a re-pin it must be retyped
    by hand from the new doc, which is exactly the moment a mangled hand-copy
    should go red.

    It also grades what the parsed-cell arm cannot: `_variant_table_rows` strips
    each cell, so `|  ADMIT  |` parses identically to `| ADMIT |`. This sees the
    spelling.

    The SEPARATOR is the half that has no other guard. `_variant_table_rows`
    skips a separator row by CONTENT rather than requiring one, so deleting it
    leaves the row walk returning the same four rows. CS reports its own tree
    catches that mutation; measured here, this tree did not.
    """
    text = _doc_text()
    block = "\n".join(
        [EXPECTED_TABLE_HEADER, EXPECTED_TABLE_SEPARATOR]
        + [_render_row(row) for row in EXPECTED_VARIANT_TABLE]
    )
    if block in text:
        return
    # Narrow the failure to the first line that moved, so the reader is not
    # handed a seven-line diff to eyeball.
    for line in block.split("\n"):
        assert line in text, (
            "the filename-variant table block does not appear verbatim in "
            f"docs/CHANNEL.md - this line is absent or respelled:\n  {line}"
        )
    raise AssertionError(
        "every line of the variant table is present but not as one contiguous "
        "block - a row was reordered, or something was inserted between rows"
    )


def test_the_variant_table_parser_can_fail():
    text = _doc_text()
    dropped = text.replace(_render_row(EXPECTED_VARIANT_TABLE[3]) + "\n", "")
    assert dropped != text, "the Variant C row text moved - re-derive this control"
    assert len(_variant_table_rows(dropped)) == 3
    # The parser must not simply return every table in the doc: the roster table
    # and the seventeen-rule table must not be picked up.
    rows = _variant_table_rows(text)
    assert all(row[-1] == "PRIMARY" or row[-1].startswith("Variant") for row in rows)


# ---------------------------------------------------------------------------
# Arm 8 - the roster numeral is DERIVED, not frozen
# ---------------------------------------------------------------------------
#
# THE DEFECT THIS CLOSES. `EXPECTED_TABLE_HEADER` above names the six responder
# codes as a literal, and the doc's prose spells the roster size as a word in
# eight places. Before this arm, nothing tied either to section 0's roster
# table: the sixth participant was added BY HAND at CHANNEL_VERSION 2 and a
# seventh would have been missed with every arm green. Measured before the
# repair - `roster row added`, `roster row dropped` and `roster code renamed`
# were caught by NO arm other than the digest, and the digest is blind by
# construction in the one round that matters.
#
# The tie is mechanical in both directions. The COUNT is parsed out of the
# roster table and the doc's own numeral words are rebuilt from it, so a row
# added without a prose edit is red. The CODE SET is parsed out of the same
# table and compared against the variant table's responder columns, so a row
# added without a column is red even when every numeral is consistent.
#
# Nothing here is a second copy of the digest: every claim is derived from the
# PARSED table, so re-pinning the doc at a seven-tree roster makes this arm pass
# again with no literal to retype - which is the whole point.

#: Cardinal numerals, index = value. The doc spells the roster size as a WORD,
#: never a digit, so a derived claim has to spell it the same way. Sized well
#: past any plausible roster so a growth step is a doc edit and not a test edit.
_CARDINALS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve",
)

#: Ordinals, same indexing. Two sites name the NEWEST participant by ordinal
#: rather than counting the roster - "the sixth participant's watcher is
#: UNMEASURED here" - and an ordinal goes stale on a roster change exactly like
#: a cardinal does.
_ORDINALS = (
    "zeroth", "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
)

#: Section 0 says each tree is named by a `two-to-three letter CODE` and by
#: nothing else. THAT PROSE IS ITSELF A ROSTER-DEPENDENT LITERAL, so the bounds
#: are parsed out of it rather than typed here - a typed `{2,3}` would go stale
#: the same way the header literal did, and deriving the bounds from the roster
#: codes instead would be tautological: a pattern built from the strings it then
#: validates cannot fail. Parsing the CLAIM and checking the CODES against it is
#: a real assertion, and it fires in both directions - a four-letter code added
#: without updating the prose, or the prose narrowed without the roster.
_CODE_LENGTH_CLAIM = re.compile(r"([a-z]+)-to-([a-z]+) letter CODE")

#: THE DOC'S OTHER CODE-LENGTH NUMBER IS DELIBERATELY NOT TIED, recorded here as
#: an exclusion with its reason rather than left as an oversight. Section 6 says
#: a 12-character token "cannot bind a two-to-four character code group". That
#: reads as a disagreement with section 0's two-to-three and it is not one: the
#: two sentences have different subjects. Section 0 states what the roster IS
#: today; section 6 states what the filename grammar's sender-code slot ACCEPTS,
#: which is deliberately wider so a future four-letter code needs no grammar
#: change. A parser bound is not a roster fact and must not track the roster, so
#: tying it would manufacture a red at the first four-letter tree - the opposite
#: of the defect this module exists to catch. Measured this run: the roster
#: codes are 2 and 3 characters long, so section 0 is accurate and section 6 is
#: accurate, and no arm should force them to agree.
_UNTIED_PARSER_BOUND = "two-to-four character code group"


def _declared_code_lengths(text: str) -> tuple[int, int]:
    """The (low, high) code length section 0 CLAIMS, as words, parsed to ints."""
    match = _CODE_LENGTH_CLAIM.search(_flat(text))
    assert match, (
        "section 0's code-length claim was not found, so the roster-code shape "
        "check below has nothing to check against and is vacuous. It should "
        "read like 'two-to-three letter CODE'."
    )
    words = match.group(1), match.group(2)
    for word in words:
        assert word in _CARDINALS, (
            f"section 0's code-length claim spells {word!r}, which is not a "
            f"cardinal this module knows: {_CARDINALS}"
        )
    return _CARDINALS.index(words[0]), _CARDINALS.index(words[1])


def _declared_code_pattern(text: str) -> re.Pattern[str]:
    low, high = _declared_code_lengths(text)
    assert 1 <= low <= high, f"section 0 claims an impossible code length range: {low}..{high}"
    return re.compile(f"^[A-Z]{{{low},{high}}}$")

_ROSTER_HEADER_CELLS = ["Code", "Carrier of these bytes", "Standing in the channel"]


def _flat(text: str) -> str:
    """Whitespace-collapsed doc text.

    The doc hard-wraps at about 90 columns, so several of the sentences below
    straddle a newline - `Roster is the six\\ncodes` is one. Matching against
    the raw text would make those claims depend on where the author's wrap fell,
    which is not what is being pinned.
    """
    return re.sub(r"\s+", " ", text)


#: THE NINETEEN ROSTER-BEARING NUMERAL SITES, as `(why, axis, template)`.
#:
#: NINETEEN SITES CARRYING TWENTY NUMERALS. Only `{less2} of the {n} trees`
#: carries two - a corrected figure; this comment first said twenty-one, which
#: double-counted. The site count is what the arms iterate; the numeral count is
#: what a reader recounting the doc by hand will arrive at, and the two are
#: written down separately here so a later reader is not forced to guess which
#: population a figure refers to.
#:
#: HOW A SITE IS PHRASED, and why it is not a whole sentence. The first version
#: of this arm pinned eight FULL sentences. That over-fires: rewording `Every
#: thread goes to all six,` to `Every thread is sent to all six,` reddened the
#: arm while the roster was perfectly correct, and an arm that reddens for an
#: innocent reword is one a contributor learns to route around. Each template
#: here is therefore the SHORTEST phrase that still carries the numeral and is
#: still roster-bearing on its own reading.
#:
#: Shortening trades one risk for another: a short phrase could collide with
#: another passage and a stale site would hide behind the wrong match.
#: `test_every_roster_numeral_site_is_unique` measures that - every rendered
#: phrase must occur EXACTLY ONCE - so the trade is guarded rather than assumed.
#:
#: AXIS says which count the site tracks. No site mixes the two: the section 0
#: roster-versus-carrier sentence is split into two entries precisely so that a
#: carrier promotion and a roster addition redden different rows. Section 0 is
#: explicit that a carrier count must never be written as a roster count.
#:
#: FIELDS: {n} cardinal, {N} capitalised, {NU} upper, {o} ordinal, {less2} the
#: cardinal of n-2, {c}/{CU} the carrier cardinal.
_ROSTER_NUMERAL_SITES = (
    ("section 0 opening sentence",
     "roster", "{N} participating repositories"),
    ("section 0 roster-versus-carrier sentence, roster half",
     "roster", "the roster is {NU}"),
    ("section 0 roster-versus-carrier sentence, carrier half",
     "carrier", "the carrier set is {CU}"),
    ("section 0 address-list sentence",
     "roster", "all {n}, and the address"),
    ("section 3 REVIEW- denominator",
     "roster", "all {n} before the sender"),
    # {less2} is the remainder after the sender and the one recipient - the doc
    # says so in the next sentence, and the v1-to-v2 diff shows this read "four
    # of five trees" and was hand-edited. Both numerals move with the roster.
    ("section 4 BILATERAL-ORIGIN remainder",
     "roster", "{less2} of the {n} trees"),
    ("section 4 BILATERAL-ORIGIN recount",
     "roster", "counted afresh at {n}"),
    # Meta-commentary ON the exempt charter quotes. The QUOTES stay at five;
    # these two sentences are the doc talking ABOUT them and they name the LIVE
    # roster, so they are tied. See `_EXEMPT_FIVE_NUMERALS` for the other half.
    ("section 4 commentary on editing the exempt quote",
     "roster", "Editing either quote to {n}"),
    ("section 4 reading of the two VERBATIM charter quotes",
     "roster", "CURRENT ROSTER OF {NU}"),
    ("section 4 pointer into convention 3",
     "roster", "where the roster is {n}"),
    ("section 4 gloss on rule 6's ALL FIVE",
     "roster", "which is now {n}"),
    # Ordinals, and the two HUMAN-REWRITE sites - see `_HUMAN_REWRITE_SITES`.
    ("section 5 unmeasured newest watcher",
     "roster", "the {o} participant's watcher"),
    ("section 5 what the newest participant is asked to meet",
     "roster", "the {o} is asked to meet"),
    ("section 5 disclaimer on the measured population",
     "roster", "that {n} were looked at"),
    # Hand-edited five-to-six at the v1-to-v2 bump; both numerals, both sites.
    ("section 5 poller-count argument, pollers",
     "roster", "{n} independent pollers"),
    ("section 5 poller-count argument, wakeups",
     "roster", "cost {n} wakeups"),
    ("section 7 convention 3 denominator",
     "roster", "Roster is the {n} codes"),
    ("section 7 convention 4 decorrelation argument, trees",
     "roster", "{N} trees sharing a prior"),
    ("section 7 convention 4 decorrelation argument, approvals",
     "roster", "produce {n} approvals"),
)

#: SITES WHOSE REPLACEMENT A MACHINE MUST NOT WRITE.
#:
#: Both are ORDINALS naming the participants beyond the five watchers measured
#: at CHANNEL_VERSION 1: `the sixth participant's watcher is UNMEASURED here`
#: and `that the sixth is asked to meet`. They genuinely move when the roster
#: moves, so tying them is right - but the mechanical render at a roster of
#: seven is `the seventh participant's watcher`, which SILENTLY DROPS THE SIXTH.
#: The honest text is `the sixth and seventh participants' watchers`, and no
#: template here can produce it.
#:
#: So these two are graded on the ABSENCE OF THE STALE WORDING rather than on
#: the presence of a derived one, and the failure says a human must write the
#: sentence. A red that says "this needs a human" is honest; a green that
#: silently drops a participant is not, and a prescriptive message telling the
#: editor to write the dropping version would be worse than either.
#:
#: THE COST, stated rather than discovered later: this is a WEAKER claim than
#: the other seventeen sites carry. It catches the old wording left in place -
#: which is the defect that actually happens at a re-pin - but it cannot tell a
#: good rewrite from a bad one, and deleting the sentence outright would pass.
#: `test_every_roster_numeral_site_is_unique` requires at most one occurrence
#: for these rather than exactly one, for the same reason.
_HUMAN_REWRITE_SITES = frozenset({
    "section 5 unmeasured newest watcher",
    "section 5 what the newest participant is asked to meet",
})

#: What an honest editor leaves behind at a human-rewrite site. It carries no
#: numeral, no path separator and no date, so it trips none of the other arms.
_HUMAN_REWRITE_MARKER = "REWRITTEN BY HAND AT THIS RE-PIN"


#: ========================= THE EXEMPTION RULE =========================
#:
#: THIS IS THE RULE A FUTURE MAINTAINER APPLIES, and it has to decide every case
#: from the DOCUMENT ALONE - nobody reading it was in the conversation that
#: produced it. The first wording here failed that test and is recorded below
#: with its failure, because an ambiguous rule silently becomes a hand
#: judgement, which is the exact defect class this arm exists to remove.
#:
#: THE RULE. Ask what the sentence would be REPORTING if its numeral changed.
#:
#:   * If changing it would make the sentence MISQUOTE OR MISREPORT something
#:     FIXED - a charter's wording, a quoted string, the state of the fleet at
#:     an earlier CHANNEL_VERSION - the numeral is part of what the sentence
#:     reports, and the site is EXEMPT. Its subject is text or history, neither
#:     of which moves when a tree joins.
#:
#:   * If changing it would make the sentence STATE A FALSEHOOD ABOUT HOW THE
#:     CHANNEL WORKS TODAY, the numeral is a live denominator and the site is
#:     TIED. This holds even when the sentence sits beside a quote, and even
#:     when it is talking about one.
#:
#: WHAT THE FIRST WORDING GOT WRONG. It read "meta-commentary about an exempt
#: quote is NOT exempt". Applied literally that TIES the section 4 header
#: sentence, and the module would then render `SAYS SEVEN ... LEFT AT SEVEN ON
#: PURPOSE` - false, and green. It also contradicted this tuple's own third
#: entry, which is meta-commentary about a quote and IS exempt. The distinction
#: being used was sound; only its statement was wrong.
#:
#: THE RULE DISCRIMINATING, on the four sites that forced the rewrite. Two go
#: each way, so this is a demonstration and not an assertion:
#:
#:   EXEMPT  s4 header  `... QUOTE CHARTER TEXT THAT SAYS FIVE, AND THEY ARE
#:           LEFT AT FIVE ON PURPOSE` - its subject is what the two rows SAY.
#:           At SEVEN it misreports them; they say five.
#:   EXEMPT  s4 `Rule 2's "2 of 5 reviews" is an EXAMPLE` - the numeral is
#:           inside the quoted string. At `2 of 7` it misquotes rule 2.
#:   TIED    s4 `Editing either quote to six would leave the status cell...` -
#:           SIX is not the quote's wording, it is the value a maintainer would
#:           wrongly propagate. At five the warning names the wrong number.
#:   TIED    s4 `Rule 6's ALL FIVE is the charter's wording ... which is now
#:           six` - ONE sentence, TWO sites. `ALL FIVE` is reported text and is
#:           exempt below; `which is now six` is a present-tense claim about the
#:           live roster and is tied above. They are anchored separately for
#:           exactly this reason.
#:
#: THE TUPLE ITSELF is the second guard every sweep in this tree is required to
#: carry. The derivation arm proves the stale numerals are gone; this one proves
#: the LEGITIMATE NEIGHBOURS SURVIVED. If a later reader decides to "finish the
#: job" by mechanising these to the live roster too, that is the doc's own
#: documented defect and it goes red here rather than passing as tidying.
#:
#: MEASURED, and the reason entries 1 and 2 exist: an independent census built
#: BLIND from the doc found this tuple two short. Against a fully honest
#: seven-way re-pin, dragging the section 4 header sentence and rule 2's quoted
#: example to the live roster was caught by NOTHING - `caught == []` on all
#: fourteen non-digest arms, with the digest blind by construction in a re-pin
#: round. Rule 6's twin was protected and rule 2's was not; that asymmetry was
#: the whole finding.
#:
#: WRAP TOLERANCE. TWO of these nine straddle the doc's hard wrap and have a RAW
#: occurrence count of zero while their FLAT count is one - entries 6 and 7,
#: measured this run. The arm matches against `_flat`, so both are found; a raw
#: `str.replace` would report them absent and silently guard nothing. Verified
#: by counting every anchor in the raw text and in the flattened text and
#: requiring flat == 1 regardless of raw, and the straddling count is asserted
#: rather than only asserted non-empty - this comment first said three, which
#: was wrong, and a non-empty check could not see that.
_EXEMPT_FIVE_NUMERALS = (
    ("section 4 header sentence governing BOTH quoted rows",
     "SAYS FIVE, AND THEY ARE LEFT AT FIVE ON PURPOSE"),
    ("section 4 naming rule 2's quoted string as an example",
     'Rule 2\'s "2 of 5 reviews" is an EXAMPLE'),
    ("rule 2's charter quote - VERBATIM status is measured against the charter",
     "landed with 2 of 5 reviews"),
    ("rule 6's charter quote - same",
     "goes to ALL FIVE and the address list"),
    ("section 4 naming rule 6's quote as a quote",
     "Rule 6's ALL FIVE is the charter's wording"),
    ("section 4 historical statement about when the charter was written",
     "the roster was five and records what was true then"),
    ("section 5 population measured at CHANNEL_VERSION 1",
     "the FIVE watchers that were running at CHANNEL_VERSION 1"),
    ("section 5 what that measured population demonstrated",
     "properties that the five demonstrated"),
    ("section 9 quoting the two numbers version 1 carried",
     '"all five" and "both trees"'),
)


def _render_site(template: str, axis: str, value: int) -> str:
    """One site's phrase at a given count. No numeral is typed here."""
    if axis == "carrier":
        return template.format(c=_CARDINALS[value], CU=_CARDINALS[value].upper())
    return template.format(
        n=_CARDINALS[value],
        N=_CARDINALS[value].capitalize(),
        NU=_CARDINALS[value].upper(),
        o=_ORDINALS[value],
        less2=_CARDINALS[max(value - 2, 0)],
    )


def _site_sizes(text: str) -> dict[str, int]:
    return {
        "roster": len(_roster_codes(text)),
        "carrier": len(_carrier_codes(text)),
    }


def test_the_roster_table_parses():
    """Section 0's roster table is found and every row is a roster row.

    Asserted BEFORE the two derivation arms below for the reason arm 7 states:
    a derivation off an empty or drifted parse is vacuously true, and an arm
    that cannot fire reads as an arm that passed.
    """
    text = _doc_text()
    rows = _roster_table_rows(text)
    assert rows, (
        "the section 0 roster table was not found - `_roster_table_rows` keys on "
        f"{_ROSTER_HEADER_CELLS[0]!r} ... {_ROSTER_HEADER_CELLS[-1]!r}; if the doc "
        "respelled that header, every derived claim below went vacuous"
    )
    # The shape comes from section 0's own `two-to-three letter CODE` claim,
    # parsed. See `_CODE_LENGTH_CLAIM` for why it is neither typed here nor
    # derived from the codes themselves.
    low, high = _declared_code_lengths(text)
    code_shape = _declared_code_pattern(text)
    for index, row in enumerate(rows):
        assert len(row) == len(_ROSTER_HEADER_CELLS), (
            f"roster row {index} has {len(row)} cells, expected "
            f"{len(_ROSTER_HEADER_CELLS)}: {row}"
        )
        assert code_shape.match(row[0]), (
            f"roster row {index} does not start with a CODE of the length "
            f"section 0 itself claims ({low} to {high} letters), so either the "
            f"parse walked onto another table or a tree joined with a code the "
            f"doc's own prose does not admit: {row}"
        )
        assert row[1].startswith(("YES", "NO")), (
            f"roster row {index} has an ungradable Carrier cell, so the carrier "
            f"count derived from it is not a count of anything: {row}"
        )
    codes = _roster_codes(text)
    assert len(set(codes)) == len(codes), f"a roster CODE is listed twice: {codes}"
    carriers = _carrier_codes(text)
    assert set(carriers) <= set(codes)
    assert carriers, "no tree declares YES in the Carrier column"
    # Section 0 states this as an invariant of CHANNEL_VERSION 2 onward: a
    # carrier count must never be written as a roster count, and the two were
    # equal at version 1 and are not equal now.
    assert len(carriers) <= len(codes)


def test_the_variant_table_columns_are_exactly_the_roster():
    """THE MECHANICAL TIE. One responder column per roster CODE, no literal.

    `EXPECTED_TABLE_HEADER` names the codes as frozen bytes and is still pinned
    above, because those bytes are a cross-tree contract. This arm is the other
    half: it reads the roster out of section 0 and the responder columns out of
    the grammar table's own header, and requires them to be the same set. Add a
    seventh roster row and this goes red on its own, with no hand edit anywhere.

    The code is the FIRST token of the column label, because RC's column is
    spelled `RC gate 6` - it names the gate as well as the tree.
    """
    text = _doc_text()
    header = _variant_table_header(text)
    assert header, "the filename-variant table header was not found"
    assert header[0] == "Example" and header[-1] == "Shape"

    responder_columns = header[1:-1]
    responder_codes = [cell.split()[0] for cell in responder_columns if cell.split()]
    assert len(responder_codes) == len(responder_columns), (
        f"a responder column is blank, so it names no tree: {responder_columns}"
    )

    roster = _roster_codes(text)
    assert set(responder_codes) == set(roster), (
        "the grammar table's responder columns are not the section 0 roster.\n"
        f"  roster    : {sorted(roster)}\n"
        f"  responders: {sorted(responder_codes)}\n"
        f"  in the roster and not a column: {sorted(set(roster) - set(responder_codes))}\n"
        f"  a column and not in the roster: {sorted(set(responder_codes) - set(roster))}\n"
        "A roster row was added or removed without the matching column. Do not "
        "edit docs/CHANNEL.md to silence this - the bytes are pinned in five "
        "trees and section 9 makes a change a joint re-pin round."
    )
    assert len(set(responder_codes)) == len(responder_codes), (
        f"a responder column is named twice: {responder_codes}"
    )
    # Every variant row therefore carries Example + one cell per tree + Shape.
    assert len(header) == len(roster) + 2
    for index, row in enumerate(EXPECTED_VARIANT_TABLE):
        assert len(row) == len(roster) + 2, (
            f"pinned variant row {index} has {len(row)} cells but the roster is "
            f"{len(roster)} trees, so the pin above was retyped without the "
            "roster change reaching it"
        )


def test_the_roster_numerals_are_derived_from_the_roster_table():
    """Every prose numeral that states the roster or carrier size, rebuilt.

    This is the arm the module's own comment at `EXPECTED_TABLE_HEADER` said did
    not exist: "nothing ties this header to a roster list anywhere in the tree,
    so the next roster change is caught only by a human remembering that this
    string exists."

    The failure NAMES THE SITE and says what it currently reads, because the
    first version reported only that some claim did not match, and a re-pin
    round handed the reader nineteen sentences to eyeball. It also separates the
    two ways a site can miss: a STALE NUMERAL, where the phrase is present at
    some other count, and a REWORD, where the anchor itself has moved. Those
    want opposite responses - fix the doc, versus fix this table - so they are
    not reported with one message.
    """
    text = _doc_text()
    flat = _flat(text)
    sizes = _site_sizes(text)
    roster = _roster_codes(text)
    carriers = _carrier_codes(text)
    population = (
        f"the roster table lists {len(roster)} participants {sorted(roster)} "
        f"and {len(carriers)} carriers {sorted(carriers)}"
    )

    for why, axis, template in _ROSTER_NUMERAL_SITES:
        expected = _render_site(template, axis, sizes[axis])
        stale = [
            (count, _render_site(template, axis, count))
            for count in range(len(_CARDINALS))
            if count != sizes[axis] and _render_site(template, axis, count) in flat
        ]
        if why in _HUMAN_REWRITE_SITES:
            # Graded on absence of the stale wording. No replacement is
            # proposed, because the mechanical one drops a participant.
            if not stale:
                continue
            count, found = stale[0]
            raise AssertionError(
                f"STALE ORDINAL, AND A HUMAN MUST WRITE THE REPLACEMENT - {why}.\n"
                f"  it reads: {found!r}  (a {axis} of {count})\n"
                f"  {population}\n"
                "This sentence names the participants beyond the five watchers "
                "measured at CHANNEL_VERSION 1. The mechanical substitution here "
                f"would be {expected!r}, and that is WRONG: it silently drops "
                "the tree this sentence already named. The honest text names "
                "them all. No replacement is proposed on purpose - write it by "
                "hand in the re-pin round, then this arm goes green because the "
                "stale wording is gone."
            )
            continue
        if expected in flat:
            continue
        if stale:
            count, found = stale[0]
            raise AssertionError(
                f"STALE {axis.upper()} NUMERAL - {why}.\n"
                f"  it reads    : {found!r}  (a {axis} of {count})\n"
                f"  it must read: {expected!r}  (a {axis} of {sizes[axis]})\n"
                f"  {population}\n"
                "The roster table moved and this sentence did not follow it. "
                "This is the defect class the sixth participant went in through: "
                "it was added by hand and ten numerals were hand-edited with it. "
                "Do not edit docs/CHANNEL.md to silence this - its bytes are "
                "pinned in five trees and section 9 makes any change a joint "
                "re-pin round. Fix it IN THAT ROUND, with this arm as the list."
            )
        raise AssertionError(
            f"ANCHOR MOVED - {why}.\n"
            f"  expected to find: {expected!r}\n"
            "  and no other count matches either, so this is a REWORD rather "
            "than a stale numeral: the roster may well be correct.\n"
            f"  {population}\n"
            "Re-derive this entry of `_ROSTER_NUMERAL_SITES` from the new doc. "
            "The template is meant to be the shortest phrase that still carries "
            "the numeral, so that an innocent reword around it does not fire."
        )


def test_every_roster_numeral_site_is_unique():
    """The control on SHORTENING. Each rendered phrase occurs exactly once.

    The templates above were deliberately cut down to the shortest roster-
    bearing phrase, to stop the arm firing on an innocent reword. That trade is
    only safe while no phrase collides with another passage - a collision would
    let a stale site hide behind a match somewhere else in the doc. Measured
    here rather than assumed.
    """
    text = _doc_text()
    flat = _flat(text)
    sizes = _site_sizes(text)
    seen: dict[str, str] = {}
    for why, axis, template in _ROSTER_NUMERAL_SITES:
        phrase = _render_site(template, axis, sizes[axis])
        # A human-rewrite site is graded on the ABSENCE of stale wording, so
        # after an honest hand rewrite its derived phrase is legitimately gone.
        # At most one, therefore, rather than exactly one.
        exact = why not in _HUMAN_REWRITE_SITES
        occurrences = flat.count(phrase)
        allowed = {1} if exact else {0, 1}
        assert occurrences in allowed, (
            f"the phrase for {why} occurs {occurrences} times, expected "
            f"{'exactly' if exact else 'at most'} one: {phrase!r}. A phrase that "
            "occurs twice lets one stale site hide behind the other's match; a "
            "phrase that occurs zero times at a DERIVED site is reported by the "
            "derivation arm. Lengthen the template until it is unique again."
        )
        if occurrences == 0:
            continue
        assert phrase not in seen, (
            f"{why} and {seen[phrase]} render the same phrase {phrase!r}, so one "
            "of the two sites is not being graded at all"
        )
        seen[phrase] = why


#: Every field name a template may carry. Used to count numerals rather than
#: sites, because the two figures differ and both are quoted in this module.
_NUMERAL_FIELD = re.compile(r"\{(n|N|NU|o|less2|c|CU)\}")


def test_the_site_and_numeral_counts_are_what_the_comments_claim():
    """Guard the two figures, because a comment is not a source of truth.

    This module quotes a SITE count and a NUMERAL count and they are different
    numbers - nineteen and twenty. An earlier revision of the comment said
    twenty-one, having double-counted, and nothing would have caught it. Both
    are now derived from the table and asserted, so the prose cannot drift from
    what the arms actually iterate.
    """
    sites = len(_ROSTER_NUMERAL_SITES)
    numerals = sum(
        len(_NUMERAL_FIELD.findall(template))
        for _why, _axis, template in _ROSTER_NUMERAL_SITES
    )
    multi = [
        template for _why, _axis, template in _ROSTER_NUMERAL_SITES
        if len(_NUMERAL_FIELD.findall(template)) > 1
    ]
    assert sites == 19, f"the site table holds {sites} entries, not nineteen"
    assert numerals == 20, f"the site table carries {numerals} numerals, not twenty"
    assert multi == ["{less2} of the {n} trees"], (
        f"exactly one site should carry two numerals; these do: {multi}"
    )
    for _why, _axis, template in _ROSTER_NUMERAL_SITES:
        assert _NUMERAL_FIELD.search(template), (
            f"the template {template!r} carries no numeral field at all, so it "
            "renders identically at every roster size and grades nothing"
        )
    assert _HUMAN_REWRITE_SITES <= {why for why, _a, _t in _ROSTER_NUMERAL_SITES}, (
        "a human-rewrite site names a `why` that is not in the site table, so "
        "it selects nothing and those sites are being graded as derived"
    )


def test_every_exempt_anchor_is_present_exactly_once_and_wrap_tolerant():
    """Non-vacuity for the exempt tuple, and the wrap measurement it depends on.

    An exempt entry whose anchor does not occur guards nothing and cannot fail,
    which is the same no-op failure `_REPIN_MUTANTS` carries a guard for. An
    anchor that occurs twice is worse: mechanising one copy would still pass.

    The RAW-versus-FLAT count is asserted rather than assumed because several of
    these straddle the doc's hard wrap. A raw `str.replace` sees zero of those,
    so a future maintainer who reaches for one instead of `_flat` gets a silent
    no-op. This records which entries are in that state at measurement time.
    """
    text = _doc_text()
    flat = _flat(text)
    straddling = []
    for why, passage in _EXEMPT_FIVE_NUMERALS:
        assert flat.count(passage) == 1, (
            f"the exempt anchor for {why} occurs {flat.count(passage)} times, "
            f"not once: {passage!r}. Zero means it guards nothing; two means "
            "mechanising one copy would still pass."
        )
        if text.count(passage) == 0:
            straddling.append(why)
    assert len(_EXEMPT_FIVE_NUMERALS) == 9, (
        f"the exempt tuple holds {len(_EXEMPT_FIVE_NUMERALS)} entries. It was "
        "measured at nine by a census built blind from the doc; it went from "
        "seven to nine when that census found the section 4 header sentence and "
        "rule 2's quoted example guarded by nothing at all."
    )
    assert len(straddling) == 2, (
        f"{len(straddling)} exempt anchors straddle the doc's wrap, not the two "
        f"this arm records: {straddling}. The figure is asserted rather than "
        "merely required non-empty because the comment above first said three "
        "and a non-empty check could not see that it was wrong."
    )


def test_the_exempt_five_numerals_survive():
    """THE SWEEP'S OTHER GUARD - the legitimate neighbours must survive.

    A sweep that scores full marks on "no stale numeral" by mechanising the
    charter quotes too has destroyed what it was protecting. Section 4 of the
    doc says in capitals that rules 2 and 6 quote charter text saying FIVE and
    are left at FIVE on purpose, because VERBATIM is a MEASURED property of the
    quote against the charter as it exists today; editing them to the live
    roster turns a measured cell into a false one and degrades exactly the
    honesty guarantee the status column exists for.

    So this arm requires those seven passages to still say five. It is the
    reason the derivation above is a list of named sites rather than a regex
    sweep for the word - a sweep cannot tell a live denominator from a quote.
    """
    flat = _flat(_doc_text())
    for why, passage in _EXEMPT_FIVE_NUMERALS:
        assert passage in flat, (
            f"an EXEMPT five-numeral is gone - {why}: {passage!r}\n"
            "These stay at FIVE deliberately. If this went red because somebody "
            "propagated the live roster into a charter quote or into a sentence "
            "about CHANNEL_VERSION 1, that is a regression and not tidying: the "
            "doc's own section 4 forbids it in capitals, and the VERBATIM status "
            "cell beside rule 2 and rule 6 becomes false the moment it happens."
        )


def test_the_roster_table_parser_can_fail():
    """Non-vacuity, plus the sweep's two legitimate neighbours SURVIVING.

    The first half proves the parser is a detector at all. The second is the
    control `_variant_table_rows` carries for the same reason: a table parser
    that simply returned every table in the doc would make both derivation arms
    above read whichever table came first and pass on nonsense.
    """
    text = _doc_text()
    rows = _roster_table_rows(text)

    # (1) it fires - drop the last row and the count drops with it.
    dropped = text.replace(_render_row(rows[-1]) + "\n", "")
    assert dropped != text, "the last roster row moved - re-derive this control"
    assert len(_roster_table_rows(dropped)) == len(rows) - 1

    # (2) it fires the other way - a seventh row is seen.
    grown = text.replace(
        _render_row(rows[-1]),
        _render_row(rows[-1]) + "\n" + _render_row(["ZZ", "NO - control", "Control row."]),
    )
    assert len(_roster_table_rows(grown)) == len(rows) + 1
    assert "ZZ" in _roster_codes(grown)

    # (3) the neighbours survive: neither the filename-variant table nor the
    #     seventeen-rule table is picked up. Both would fail the CODE shape.
    assert all(_declared_code_pattern(text).match(row[0]) for row in rows)
    assert not any(row[-1] == "Shape" or row[-1] in {"VERBATIM", "PARAPHRASE"} for row in rows)
    # The section 6 parser bound is a DIFFERENT subject and stays untied - see
    # `_UNTIED_PARSER_BOUND`. Asserted present so the exclusion is a recorded
    # fact about the doc rather than a comment that could quietly go false.
    assert _UNTIED_PARSER_BOUND in _flat(text)
    assert _declared_code_lengths(text) == (2, 3), (
        "section 0's claimed code lengths moved; this control records what was "
        "measured, and the arm above is what enforces it against the roster"
    )
    # ...and the variant parser is still not picking up the roster.
    assert all(
        row[-1] == "PRIMARY" or row[-1].startswith("Variant")
        for row in _variant_table_rows(text)
    )

    # (4) the header accessor is a detector too, not a constant.
    assert _variant_table_header(text.replace(EXPECTED_TABLE_HEADER, "| x |")) == []


# ---------------------------------------------------------------------------
# THE RE-PIN REGRESSION. Arm 2 is excluded on purpose: this is the state every
# CHANNEL_VERSION 2 round is in, and it is the state in which 16 of 31 mutants
# survived the first version of this module.
# ---------------------------------------------------------------------------

_NON_DIGEST_ARMS = (
    test_the_channel_doc_exists,
    test_the_doc_carries_no_carriage_returns,
    test_the_doc_is_printable_ascii,
    test_the_declared_channel_version_is_the_pinned_version,
    test_no_heading_line_carries_a_date,
    test_every_repo_relative_path_resolves,
    test_the_doc_cites_no_line_number,
    test_the_filename_variant_table_parses,
    test_the_variant_table_block_is_present_verbatim,
    test_the_roster_table_parses,
    test_the_variant_table_columns_are_exactly_the_roster,
    test_the_roster_numerals_are_derived_from_the_roster_table,
    test_every_roster_numeral_site_is_unique,
    test_the_exempt_five_numerals_survive,
    test_every_exempt_anchor_is_present_exactly_once_and_wrap_tolerant,
)


def _bump_version(data: bytes) -> bytes:
    return data.replace(
        _DECLARED_VERSION_TOKEN.encode("ascii"),
        f"CHANNEL_VERSION: {PINNED_VERSION + 1}".encode("ascii"),
    )


def _drop_version(data: bytes) -> bytes:
    return data.replace((_DECLARED_VERSION_TOKEN + "\n").encode("ascii"), b"")


def _append(text: str):
    return lambda data: data + text.encode("ascii")


def _drop_variant_row(data: bytes) -> bytes:
    # Derived from the pin, not typed. The typed version carried the version 1
    # six-column spelling and went NO-OP the moment the SS column landed.
    return data.replace(_render_row(EXPECTED_VARIANT_TABLE[3]).encode("ascii") + b"\n", b"")


def _corrupt_variant_verdict(data: bytes) -> bytes:
    return data.replace(b"| ADMIT |", b"| MAYBE |")


# --- CS's six table mutations, added after its REVIEW of the shared test core.
# Each is built from EXPECTED_VARIANT_TABLE so a pin and a mutant cannot drift
# apart: if the doc's row spelling ever moves, the no-op assertion in the
# parametrised test fires rather than the row quietly mutating nothing.

def _row_bytes(index: int) -> bytes:
    return _render_row(EXPECTED_VARIANT_TABLE[index]).encode("ascii")


def _replace_row(data: bytes, index: int, cells: list[str]) -> bytes:
    return data.replace(_row_bytes(index), _render_row(cells).encode("ascii"))


def _nonsense_primary_example(data: bytes) -> bytes:
    cells = list(EXPECTED_VARIANT_TABLE[0])
    cells[0] = "`zzz-nonsense-primary.md`"
    return _replace_row(data, 0, cells)


def _nonsense_variant_example(data: bytes) -> bytes:
    cells = list(EXPECTED_VARIANT_TABLE[1])
    cells[0] = "`zzz-nonsense-variant.md`"
    return _replace_row(data, 1, cells)


def _swap_two_variant_examples(data: bytes) -> bytes:
    """Variant A and Variant B trade example names; every other cell is intact.

    The nastiest of the six: row count, column count, Shape order and every
    verdict are all still correct, so a shape-only arm sees a perfect table
    while two of the four grammar vectors now test the wrong shape.
    """
    a_cells = list(EXPECTED_VARIANT_TABLE[1])
    b_cells = list(EXPECTED_VARIANT_TABLE[2])
    a_cells[0], b_cells[0] = b_cells[0], a_cells[0]
    out = _replace_row(data, 1, a_cells)
    return _replace_row(out, 2, b_cells)


def _flip_primary_verdict(data: bytes) -> bytes:
    cells = list(EXPECTED_VARIANT_TABLE[0])
    cells[1] = "REFUSE"
    return _replace_row(data, 0, cells)


def _blank_responder_columns(data: bytes) -> bytes:
    """Columns 2..5 - the four non-RC trees - emptied on every row."""
    out = data
    for index, row in enumerate(EXPECTED_VARIANT_TABLE):
        cells = list(row)
        for column in (2, 3, 4, 5):
            cells[column] = ""
        out = _replace_row(out, index, cells)
    return out


def _flexible_sub(text: str, phrase: str, replacement: str) -> str:
    """Replace `phrase` once, tolerating the doc's hard wrap inside it.

    The doc wraps at about 90 columns, so a pinned phrase can straddle a
    newline - `Roster is the six\\ncodes` and `six\\n   independent pollers` both
    do. A plain `str.replace` finds neither and would silently produce a NO-OP
    mutant, which reads as an arm that passed. Matching each inter-word gap as
    `\\s+` is what makes these mutants actually mutate.
    """
    pattern = re.compile(r"\s+".join(re.escape(word) for word in phrase.split(" ")))
    return pattern.sub(lambda _: replacement, text, count=1)


def _stale_numeral_at(index: int):
    """A mutant that walks ONE numeral site back by one, leaving the table alone.

    The roster table is untouched, so the column tie cannot fire and the numeral
    arm is the only thing standing. That is what makes this a detector test for
    the site rather than for the module.
    """
    why, axis, template = _ROSTER_NUMERAL_SITES[index]

    def mutate(data: bytes) -> bytes:
        text = data.decode("ascii")
        size = _site_sizes(text)[axis]
        current = _render_site(template, axis, size)
        stale = _render_site(template, axis, max(size - 1, 0))
        return _flexible_sub(text, current, stale).encode("ascii")

    mutate.__doc__ = f"walk the numeral at {why} back by one"
    return mutate


def _narrow_the_code_length_claim(data: bytes) -> bytes:
    """Section 0 claims two-to-TWO letter codes while RSC is three.

    The tie runs both ways: this is the prose narrowing under a roster that did
    not move. The other direction - a four-letter tree joining while the prose
    still says two-to-three - is covered by `_add_a_long_code_roster_row`.
    """
    text = data.decode("ascii")
    low, high = _declared_code_lengths(text)
    before = f"{_CARDINALS[low]}-to-{_CARDINALS[high]} letter CODE"
    after = f"{_CARDINALS[low]}-to-{_CARDINALS[low]} letter CODE"
    return _flexible_sub(text, before, after).encode("ascii")


def _add_a_long_code_roster_row(data: bytes) -> bytes:
    """A four-letter tree joins while section 0 still claims two-to-three."""
    anchor = _roster_row_bytes(data, -1)
    extra = _render_row(
        ["ZZZZ", "NO - hypothetical", "Participant. A tree with a four-letter code."]
    ).encode("ascii")
    return data.replace(anchor, anchor + b"\n" + extra)


def _mechanise_an_exempt_quote(data: bytes) -> bytes:
    """The NEIGHBOUR-DESTROYING mutant - somebody "finishes the job".

    Rule 2's charter quote is dragged to the live roster, which is precisely the
    edit section 4 forbids in capitals. A sweep that scored full marks by doing
    this would have destroyed the VERBATIM guarantee it was meant to protect.
    """
    return data.replace(b"landed with 2 of 5 reviews", b"landed with 2 of 6 reviews")


# --- The roster mutants. THE DEFECT THEY MEASURE: before these landed, the
# roster numeral and the variant table's responder columns were frozen literals
# with nothing tying them to section 0's roster table. A sixth participant was
# added BY HAND at CHANNEL_VERSION 2; a seventh would have been missed with
# every arm green. Each mutant is derived from the PARSED roster rather than
# typed, so it cannot go no-op the way the typed six-column `_drop_variant_row`
# did the moment the SS column landed.

def _roster_row_bytes(data: bytes, index: int) -> bytes:
    rows = _roster_table_rows(data.decode("ascii"))
    return _render_row(rows[index]).encode("ascii")


def _add_roster_row(data: bytes) -> bytes:
    """A seventh participant appears in section 0 and nowhere else.

    This is the exact shape of the next roster change: someone appends a row and
    forgets the prose numeral, the address-list sentence and the variant table's
    responder column. Nothing in this module caught it before the derivation.
    """
    anchor = _roster_row_bytes(data, -1)
    extra = _render_row(
        ["ZZ", "NO - hypothetical", "Participant. A seventh tree, added for this control."]
    ).encode("ascii")
    return data.replace(anchor, anchor + b"\n" + extra)


def _drop_roster_row(data: bytes) -> bytes:
    """The last roster row is deleted and every numeral is left at six."""
    anchor = _roster_row_bytes(data, -1)
    return data.replace(anchor + b"\n", b"")


def _rename_roster_code(data: bytes) -> bytes:
    """A code is respelled in the roster only, so the two tables disagree.

    Row count, column count and every numeral in the doc stay correct, which is
    what a count-only tie would miss.
    """
    rows = _roster_table_rows(data.decode("ascii"))
    cells = list(rows[-1])
    cells[0] = "ZZ"
    return data.replace(_render_row(rows[-1]).encode("ascii"), _render_row(cells).encode("ascii"))


def _demote_a_carrier(data: bytes) -> bytes:
    """One YES becomes NO, so the carrier numeral FIVE is stale and the roster is not."""
    rows = _roster_table_rows(data.decode("ascii"))
    carrier = next(row for row in rows if row[1].startswith("YES"))
    cells = list(carrier)
    cells[1] = "NO - hypothetical demotion"
    return data.replace(_render_row(carrier).encode("ascii"), _render_row(cells).encode("ascii"))


def _drop_table_separator(data: bytes) -> bytes:
    return data.replace(
        (EXPECTED_TABLE_HEADER + "\n" + EXPECTED_TABLE_SEPARATOR + "\n").encode("ascii"),
        (EXPECTED_TABLE_HEADER + "\n").encode("ascii"),
    )


#: Every entry is a DEFECT CLASS a re-pin round must still catch. Adding one
#: without checking `mutant != original` is how a table accumulates no-op
#: entries that read as passes; the test asserts that for every row.
_REPIN_MUTANTS = {
    "atx iso date": _append("\n## 10. Addendum 2026-09-15\n"),
    "atx iso date with time": _append("\n## 10. Addendum 2026-09-15T00:35\n"),
    "atx day month year": _append("\n## 10. Addendum 15 Sep 2026\n"),
    "atx slash date": _append("\n## 10. Addendum 2026/09/15\n"),
    "atx abbreviated month": _append("\n## 10. Addendum Sept 15\n"),
    "atx compact date": _append("\n## 10. Addendum 20260915\n"),
    "atx us order date": _append("\n## 10. Addendum 09-15-2026\n"),
    "setext iso date": _append("\nAddendum 2026-09-15\n===================\n"),
    "version bumped": _bump_version,
    "version removed": _drop_version,
    "absent path with suffix": _append("\nSee `docs/nope-sentinel.md`.\n"),
    "absent extensionless path": _append("\nSee `.githooks/nope-hook-sentinel`.\n"),
    "absent shell script": _append("\nSee `scripts/nope-sentinel.sh`.\n"),
    "absent stub": _append("\nSee `core/nope-sentinel.pyi`.\n"),
    "absent backslash path": _append("\nSee `docs\\nope2-sentinel.md`.\n"),
    "cite with suffix": _append("\nSee ops/loop/slots.py:39.\n"),
    "cite without suffix": _append("\nSee core/ports:12.\n"),
    "cite web form": _append("\nSee slots.py#L39.\n"),
    "cite prose form": _append("\nSee line 39 of slots.py.\n"),
    "variant row dropped": _drop_variant_row,
    "variant verdict corrupted": _corrupt_variant_verdict,
    "primary example name nonsense": _nonsense_primary_example,
    "variant example name nonsense": _nonsense_variant_example,
    "two variant example names swapped": _swap_two_variant_examples,
    "primary verdict flipped to refuse": _flip_primary_verdict,
    "responder columns blanked": _blank_responder_columns,
    "table separator row dropped": _drop_table_separator,
    "roster row added": _add_roster_row,
    "roster row dropped": _drop_roster_row,
    "roster code renamed": _rename_roster_code,
    "carrier demoted to non-carrier": _demote_a_carrier,
    "exempt charter quote mechanised to the live roster": _mechanise_an_exempt_quote,
    "code length claim narrowed below the roster": _narrow_the_code_length_claim,
    "four letter code joins a two-to-three roster": _add_a_long_code_roster_row,
    "bel byte": lambda data: data + bytes([0x07]),
    "del byte": lambda data: data + bytes([0x7F]),
    "crlf conversion": lambda data: data.replace(b"\n", b"\r\n"),
}


@pytest.mark.parametrize("label", sorted(_REPIN_MUTANTS))
def test_every_repin_mutant_is_caught_without_the_digest(monkeypatch, tmp_path, label):
    original = _doc_bytes()
    mutant = _REPIN_MUTANTS[label](original)
    assert mutant != original, (
        f"no-op mutant {label!r} - its target does not occur in the doc, so this "
        "row cannot fail and is measuring nothing"
    )
    caught = [
        arm.__name__ for arm in _NON_DIGEST_ARMS
        if _run_arm_against(monkeypatch, tmp_path, arm, mutant) is not None
    ]
    assert caught, (
        f"mutant {label!r} survives every arm except the digest - in a "
        "CHANNEL_VERSION 2 re-pin round, where the digest is recomputed over the "
        "new bytes, nothing would catch it"
    )


_NUMERAL_ARM = "test_the_roster_numerals_are_derived_from_the_roster_table"


@pytest.mark.parametrize("index", range(len(_ROSTER_NUMERAL_SITES)))
def test_every_roster_numeral_site_is_a_detector(monkeypatch, tmp_path, index):
    """Each of the nineteen sites, walked back one, must redden the numeral arm.

    A site that cannot fire is a row in a table measuring nothing - the exact
    failure mode the module docstring warns about for `_REPIN_MUTANTS`, and the
    exact reason this arm names the numeral arm specifically rather than
    accepting any catch. The roster table is untouched by these mutants, so a
    catch cannot come from the column tie by accident.
    """
    why, axis, _template = _ROSTER_NUMERAL_SITES[index]
    original = _doc_bytes()
    mutant = _stale_numeral_at(index)(original)
    assert mutant != original, (
        f"NO-OP mutant for {why} - its phrase does not occur in the doc even "
        "with the wrap-tolerant match, so this site is pinned to text that is "
        "not there and the derivation arm has already reported it"
    )
    caught = [
        arm.__name__ for arm in _NON_DIGEST_ARMS
        if _run_arm_against(monkeypatch, tmp_path, arm, mutant) is not None
    ]
    assert _NUMERAL_ARM in caught, (
        f"a stale numeral at {why} is NOT caught by the derivation arm - it is "
        f"caught only by {caught}. That site is pinned but not graded."
    )


def _honest_repin_leaving_one_stale(index: int) -> tuple[bytes, dict[str, object], bool]:
    """An HONEST seven-way re-pin with exactly one numeral site left behind.

    This is the generalised form of the mutant that refuted the first version of
    this slice. That one added a seventh roster row, added the seventh responder
    column, retyped the module's table literals by hand exactly as the re-pin
    ritual says to, and updated the eight sentences the first version happened
    to pin - and NOTHING CAUGHT IT, because eleven other roster-bearing numerals
    had no tie at all. The digest is blind by construction in a re-pin round, so
    that was the seventh participant being missed in eleven places exactly the
    way the sixth was missed in ten.

    Everything here is derived, so it stays honest as the doc moves: the roster
    row, the new column and every numeral come from the pins and the parse.
    """
    data = _add_roster_row(_doc_bytes())
    text = data.decode("ascii")
    sizes_after = _site_sizes(text)

    # Every site EXCEPT `index` follows the new roster - an honest editor.
    # `left_stale` records whether skipping `index` actually left anything
    # behind. The new row joins as a NON-carrier, so the CARRIER sites do not
    # move at all and skipping one of those leaves a perfectly honest re-pin.
    # Reporting that rather than assuming it is what keeps the caller from
    # demanding a catch where there is nothing to catch.
    left_stale = False
    sizes_before = _site_sizes(_doc_text())
    for position, (why, axis, template) in enumerate(_ROSTER_NUMERAL_SITES):
        before = _render_site(template, axis, sizes_before[axis])
        after = _render_site(template, axis, sizes_after[axis])
        if before == after:
            continue
        if position == index:
            left_stale = True
            continue
        if why in _HUMAN_REWRITE_SITES:
            # An honest editor at one of these does NOT paste the mechanical
            # render - that is the sentence that drops a participant. It writes
            # something by hand. The marker stands in for that, and carries no
            # numeral, so the site's own arm sees no stale wording.
            text = _flexible_sub(text, before, _HUMAN_REWRITE_MARKER)
            continue
        text = _flexible_sub(text, before, after)

    # The grammar table gains the seventh responder column, and the module's
    # literals are retyped to match - which is what section 9 says a carrier
    # does in a re-pin round.
    header_cells = _variant_table_header(_doc_text())
    # The CODE is the first token of the column label - RC's reads `RC gate 6`.
    # Comparing against the raw cells instead counted RC as a new code.
    present = {cell.split()[0] for cell in header_cells[1:-1] if cell.split()}
    new_code = [code for code in _roster_codes(text) if code not in present]
    assert len(new_code) == 1, f"expected exactly one new code, got {new_code}"
    new_header = _render_row(header_cells[:-1] + new_code + header_cells[-1:])
    new_separator = EXPECTED_TABLE_SEPARATOR + "---|"
    new_rows = [row[:-1] + ["UNMEASURED"] + row[-1:] for row in EXPECTED_VARIANT_TABLE]

    text = text.replace(
        EXPECTED_TABLE_HEADER + "\n" + EXPECTED_TABLE_SEPARATOR,
        new_header + "\n" + new_separator,
    )
    for old, new in zip(EXPECTED_VARIANT_TABLE, new_rows):
        text = text.replace(_render_row(old), _render_row(new))

    patches = {
        "EXPECTED_TABLE_HEADER": new_header,
        "EXPECTED_TABLE_SEPARATOR": new_separator,
        "EXPECTED_VARIANT_TABLE": new_rows,
    }
    return text.encode("ascii"), patches, left_stale


@pytest.mark.parametrize("index", range(len(_ROSTER_NUMERAL_SITES)))
def test_an_honest_repin_is_caught_when_one_numeral_is_left_stale(
    monkeypatch, tmp_path, index
):
    """THE REGRESSION FOR THE REFUTATION. Reproduce that mutant, then fail it.

    Nineteen cases, one per site. Each is a re-pin that is correct in every
    respect except one sentence, with the module's own table literals retyped
    the way the ritual demands - so the column tie is satisfied and the digest
    is recomputed. The numeral arm is the only thing left, which is the whole
    point of the arm.
    """
    why, axis, _template = _ROSTER_NUMERAL_SITES[index]
    mutant, patches, left_stale = _honest_repin_leaving_one_stale(index)
    for name, value in patches.items():
        monkeypatch.setattr(sys.modules[__name__], name, value)
    caught = [
        arm.__name__ for arm in _NON_DIGEST_ARMS
        if _run_arm_against(monkeypatch, tmp_path, arm, mutant) is not None
    ]
    if not left_stale:
        # The seventh tree joins as a NON-carrier, so a CARRIER site is
        # unaffected and nothing was left behind. This case is not a weaker
        # test, it is the TWO-POPULATIONS control: it proves a roster addition
        # does not drag the carrier numeral with it, which is the conflation
        # section 0 forbids in capitals.
        assert axis == "carrier", (
            f"{why} did not move on a roster change, but it is a {axis} site - "
            "either the template carries no numeral or it is pinned to the "
            "wrong axis, and it is measuring nothing in this harness"
        )
        assert caught == [], (
            f"nothing was left stale, yet {caught} reddened - a roster addition "
            "is dragging the carrier numeral with it"
        )
        return
    assert _NUMERAL_ARM in caught, (
        f"an otherwise-honest re-pin that left {why} stale was caught by "
        f"{caught or 'NOTHING'}. This is the exact shape that refuted the first "
        "version of this arm: roster row added, column added, literals retyped, "
        "digest recomputed, and one sentence still naming the old roster."
    )


def test_the_honest_repin_harness_is_honest(monkeypatch, tmp_path):
    """Guard the guard: with NO site left stale, the same re-pin must be GREEN.

    Without this, `_honest_repin_leaving_one_stale` could be reddening the
    numeral arm through some incidental damage it does - a mangled table, a
    broken path, a stray numeral - and all nineteen cases above would pass while
    measuring that damage instead of the stale sentence. Index -1 is not a site,
    so every site follows the new roster and the result must be a clean re-pin.
    """
    mutant, patches, left_stale = _honest_repin_leaving_one_stale(-1)
    assert not left_stale, "index -1 is not a site; nothing should be left behind"
    # ...and the harness must actually be exercising most of the table. If a
    # refactor made every site render identically at six and seven, all
    # nineteen cases above would pass vacuously.
    moved = sum(
        1 for index in range(len(_ROSTER_NUMERAL_SITES))
        if _honest_repin_leaving_one_stale(index)[2]
    )
    assert moved == len(_ROSTER_NUMERAL_SITES) - 1, (
        f"{moved} of {len(_ROSTER_NUMERAL_SITES)} sites move when the roster "
        "gains a tree; exactly one - the carrier half - should not"
    )
    for name, value in patches.items():
        monkeypatch.setattr(sys.modules[__name__], name, value)
    caught = [
        arm.__name__ for arm in _NON_DIGEST_ARMS
        if _run_arm_against(monkeypatch, tmp_path, arm, mutant) is not None
    ]
    assert caught == [], (
        "a fully honest seven-way re-pin reddens "
        f"{caught} - so the nineteen cases above are measuring collateral damage "
        "from the harness rather than the one stale sentence each leaves behind"
    )


def test_the_repin_regression_excludes_the_digest_deliberately():
    """Guard the guard: if arm 2 ever joins that tuple, every row passes trivially."""
    names = {arm.__name__ for arm in _NON_DIGEST_ARMS}
    assert "test_the_lf_normalised_digest_matches_the_pin" not in names, (
        "the digest arm entered the re-pin tuple - every mutant now 'passes' "
        "through it and the re-pin blindness is no longer measured"
    )
    assert len(names) == len(_NON_DIGEST_ARMS), "duplicate arm in the re-pin tuple"
    assert len(_REPIN_MUTANTS) >= 30, f"mutant table shrank to {len(_REPIN_MUTANTS)}"
