"""Pin `docs/CHANNEL.md` - the five-way moon-sync channel convention doc.

These bytes are VENDORED. RC authored them, the fleet agreed to carry them
byte-identical at the same relative path, and the digest is taken over
LF-NORMALISED bytes rather than raw bytes so that a tree whose working copy
checks out CRLF is not red while all five git blobs are identical. This tree
DOES pin markdown to LF - `.gitattributes` carries `*.md text eol=lf` - so the
zero-CR arm below is a valid additional check HERE and would not be in a tree
without that rule. See section 9 of the doc itself.

Seven portable arms, as RC specified, plus one this tree added (arm 3b, byte
hygiene - see REPAIR 4 below). RC's own gate module is deliberately NOT
vendored: it hard-imports RC-only tooling absent from this tree, and a test
that cannot import is a test that cannot fail. These arms are stdlib only and
import no sweep module from this tree either, so a refactor of a local sweep
cannot quietly cancel the pin.

  1.  the file exists
  2.  its LF-normalised sha256 equals the pinned digest
  3.  it contains zero CR bytes
  3b. every byte is printable ASCII or newline (added here, not RC's)
  4.  the declared CHANNEL_VERSION parses to an int and equals 1
  5.  no heading line carries a date
  6.  every repo-relative path it names resolves, and it cites no file:line
  7.  the filename-variant table is present and parses, every cell pinned

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
PINNED_SHA256 = "899f6eb957cc26ee25993d83d65d8ca291841fe4eec24a48f729c2dc005f4c6b"
PINNED_VERSION = 1

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
        "version bumped": original.replace(b"CHANNEL_VERSION: 1", b"CHANNEL_VERSION: 2"),
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

def test_the_declared_channel_version_is_one():
    declared = _declared_version(_doc_text())
    assert declared is not None, "no parsable CHANNEL_VERSION line in docs/CHANNEL.md"
    assert isinstance(declared, int)
    assert declared == PINNED_VERSION, (
        f"CHANNEL_VERSION is {declared}, this tree pins {PINNED_VERSION} - a "
        "version bump and a digest re-pin land together or not at all"
    )


def test_the_version_parser_can_fail():
    text = _doc_text()
    assert _declared_version(text.replace("CHANNEL_VERSION: 1", "CHANNEL_VERSION: 2")) == 2
    assert _declared_version(text.replace("CHANNEL_VERSION: 1", "CHANNEL_VERSION: two")) is None
    assert _declared_version(text.replace("CHANNEL_VERSION: 1", "CHANNEL_VER: 1")) is None


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


#: Arm 6's ENTIRE graded population on CHANNEL_VERSION 1 bytes, pinned exactly
#: rather than floored, and SPLIT ON WHETHER GIT IGNORES THE TOKEN.
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
    Measured on CHANNEL_VERSION 1 bytes:

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
        "ADMIT", "routes", "any entry", "no responder", "no responder", "PRIMARY",
    ],
    [
        "`2026-09-15-from-RC-FYI-example-topic.md`",
        "REFUSE", "routes", "any entry", "no responder", "no responder", "Variant A",
    ],
    [
        "`from-RC-2026-09-15-0930-FYI-example-topic.md`",
        "REFUSE", "zero destinations", "any entry", "no responder", "no responder", "Variant B",
    ],
    [
        "`2026-09-15-0930-from-RC-FYI-example-topic.txt`",
        "REFUSE", "routes", "any entry", "no responder", "no responder", "Variant C",
    ],
]

#: The header and its separator, pinned as literals. The separator matters on its
#: own: `_variant_table_rows` SKIPS a separator row by content rather than
#: requiring one, so deleting it is invisible to the row walk. Measured here -
#: CS reports its own tree catches that mutation and this tree did NOT.
EXPECTED_TABLE_HEADER = "| Example | RC gate 6 | RSC | LW | CS | LL | Shape |"
EXPECTED_TABLE_SEPARATOR = "|---|---|---|---|---|---|---|"


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
    dropped = text.replace(
        "| `2026-09-15-0930-from-RC-FYI-example-topic.txt` | REFUSE "
        "| routes | any entry | no responder | no responder | Variant C |\n",
        "",
    )
    assert dropped != text, "the Variant C row text moved - re-derive this control"
    assert len(_variant_table_rows(dropped)) == 3
    # The parser must not simply return every table in the doc: the roster table
    # and the seventeen-rule table must not be picked up.
    rows = _variant_table_rows(text)
    assert all(row[-1] == "PRIMARY" or row[-1].startswith("Variant") for row in rows)


# ---------------------------------------------------------------------------
# THE RE-PIN REGRESSION. Arm 2 is excluded on purpose: this is the state every
# CHANNEL_VERSION 2 round is in, and it is the state in which 16 of 31 mutants
# survived the first version of this module.
# ---------------------------------------------------------------------------

_NON_DIGEST_ARMS = (
    test_the_channel_doc_exists,
    test_the_doc_carries_no_carriage_returns,
    test_the_doc_is_printable_ascii,
    test_the_declared_channel_version_is_one,
    test_no_heading_line_carries_a_date,
    test_every_repo_relative_path_resolves,
    test_the_doc_cites_no_line_number,
    test_the_filename_variant_table_parses,
    test_the_variant_table_block_is_present_verbatim,
)


def _bump_version(data: bytes) -> bytes:
    return data.replace(b"CHANNEL_VERSION: 1", b"CHANNEL_VERSION: 2")


def _drop_version(data: bytes) -> bytes:
    return data.replace(b"CHANNEL_VERSION: 1\n", b"")


def _append(text: str):
    return lambda data: data + text.encode("ascii")


def _drop_variant_row(data: bytes) -> bytes:
    return data.replace(
        b"| `2026-09-15-0930-from-RC-FYI-example-topic.txt` | REFUSE "
        b"| routes | any entry | no responder | no responder | Variant C |\n",
        b"",
    )


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


def test_the_repin_regression_excludes_the_digest_deliberately():
    """Guard the guard: if arm 2 ever joins that tuple, every row passes trivially."""
    names = {arm.__name__ for arm in _NON_DIGEST_ARMS}
    assert "test_the_lf_normalised_digest_matches_the_pin" not in names, (
        "the digest arm entered the re-pin tuple - every mutant now 'passes' "
        "through it and the re-pin blindness is no longer measured"
    )
    assert len(names) == len(_NON_DIGEST_ARMS), "duplicate arm in the re-pin tuple"
    assert len(_REPIN_MUTANTS) >= 30, f"mutant table shrank to {len(_REPIN_MUTANTS)}"
