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
  7.  the filename-variant table is present and parses

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


def test_the_path_scan_walked_a_real_population():
    """A floor, not just a membership check - arm 5 has one and this needs one.

    The floor is TWO because two is the honest number on these bytes. That is
    itself the finding: see the arm 6 paragraph in the module docstring.
    """
    paths = _repo_relative_paths(_doc_text())
    assert len(paths) >= 2, f"path population collapsed to {len(paths)}: {sorted(paths)}"
    assert "docs/CHANNEL.md" in paths, f"self-reference not found - scan is broken: {sorted(paths)}"
    assert "moon_sync_inbox/" in paths, f"gitignored inbox not found: {sorted(paths)}"
    assert not any("moonsync" in p for p in paths), f"absolute Windows path admitted: {sorted(paths)}"
    assert not any(p.startswith("n/a") for p in paths), "the prose token 'n/a' was read as a path"


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


def test_the_filename_variant_table_parses():
    rows = _variant_table_rows(_doc_text())
    assert rows, "the filename-variant table was not found at all"
    assert len(rows) == len(EXPECTED_SHAPES), (
        f"expected {len(EXPECTED_SHAPES)} variant rows, parsed {len(rows)}: {rows}"
    )
    assert [row[-1] for row in rows] == EXPECTED_SHAPES
    # Seven columns: Example, RC gate 6, the four other trees, then Shape.
    for row in rows:
        assert len(row) == 7, f"variant row has {len(row)} cells, expected 7: {row}"
        assert row[0].startswith("`") and row[0].endswith("`"), (
            f"the Example cell must be a backticked filename: {row[0]}"
        )
        assert row[1] in {"ADMIT", "REFUSE"}, f"RC gate 6 verdict unparsable: {row[1]}"
    # The PRIMARY row is the only ADMIT; RC's gate refuses all three variants.
    assert [row[1] for row in rows] == ["ADMIT", "REFUSE", "REFUSE", "REFUSE"]


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
    assert len(_REPIN_MUTANTS) >= 24, f"mutant table shrank to {len(_REPIN_MUTANTS)}"
