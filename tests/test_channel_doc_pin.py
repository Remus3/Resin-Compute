"""Pin `docs/CHANNEL.md` - the five-way moon-sync channel convention doc.

These bytes are VENDORED. RC authored them, the fleet agreed to carry them
byte-identical at the same relative path, and the digest is taken over
LF-NORMALISED bytes rather than raw bytes so that a tree whose working copy
checks out CRLF is not red while all five git blobs are identical. This tree
DOES pin markdown to LF - `.gitattributes` carries `*.md text eol=lf` - so the
zero-CR arm below is a valid additional check HERE and would not be in a tree
without that rule. See section 9 of the doc itself.

Seven portable arms, as RC specified. RC's own gate module is deliberately NOT
vendored: it hard-imports RC-only tooling that does not exist in this tree, and
a test that cannot import is a test that cannot fail. These arms are stdlib
only and import no sweep module from this tree either, so a refactor of a local
sweep cannot quietly cancel the pin.

  1. the file exists
  2. its LF-normalised sha256 equals the pinned digest
  3. it contains zero CR bytes
  4. the declared CHANNEL_VERSION parses to an int and equals 1
  5. no heading line carries a date
  6. every repo-relative path it names resolves, and it cites no file:line
  7. the filename-variant table is present and parses

A NOTE ON NON-VACUITY. A gate whose fixture excludes the defect cannot fail,
which is a measured failure class in this tree, so arms 2 through 7 each carry
a negative control that mutates the doc text IN MEMORY - never on disk - and
asserts the matcher fires on the mutant. Arms 5 and 6 are the two most likely
to be written vacuously and each has both kinds of control: one proving the
matcher fires on a planted defect, one proving the population it scanned was
non-empty.

Arm 5's scope, stated rather than implied: it grades ATX headings - a line
matching `^#{1,6}\\s` - which is what a dated-heading drift guard keys on. That
population deliberately includes the three `#` lines inside the note-skeleton
fenced block, because including them is stricter than excluding them and the
doc passes either way. A setext heading (text underlined with `===` or `---`)
is NOT graded; the doc uses none, and the doc's own section 2 warns that a rule
after a non-blank line is read as a setext heading by a strict scanner.

Arm 6's resolution rule: a repo-relative path RESOLVES if it exists on disk OR
git reports it ignored. The second disjunct is not a loophole - it is the only
correct rule for this doc, which names `moon_sync_inbox/`, a gitignored
directory the doc itself describes as absent from a fresh clone and every
worktree. Requiring existence would make this test red in exactly the copies
the doc is written for. `git check-ignore` answers in its RETURN CODE, not on
stdout, so that is what is read.

Arm 6 does not reach a BARE filename - a token with no forward slash. That is
the doc's own stated provenance convention (section 4: cites are by bare
filename because the notes live in a gitignored directory). One consequence is
recorded here rather than hidden: the doc calls
`CROSS_REPO_CONVERGENCE_CHARTER.md` "the tracked convergence charter", and that
file is NOT present and NOT tracked in this tree. It is RC's artifact. Do not
"fix" the doc for it - the bytes are pinned byte-identical and a local edit
breaks the pin in five trees.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANNEL_DOC = REPO_ROOT / "docs" / "CHANNEL.md"

#: sha256 over the LF-normalised bytes. Re-pinning is a JOINT act across all
#: five trees, and a byte change without a CHANNEL_VERSION bump is red by
#: construction because arms 2 and 4 live in the same module.
PINNED_SHA256 = "899f6eb957cc26ee25993d83d65d8ca291841fe4eec24a48f729c2dc005f4c6b"
PINNED_VERSION = 1

#: Suffixes that make a slash-bearing token a FILE path rather than prose. A
#: token ending in `/` is a directory path and is admitted without one.
_PATH_SUFFIXES = (
    ".py", ".md", ".json", ".ini", ".toml", ".txt", ".ps1",
    ".cfg", ".yml", ".yaml", ".js", ".html", ".xml", ".cmd",
)

#: A plain structural scan, per the slice brief - no sweep module is imported.
#: The character class admits neither `%` nor a backslash, which is what keeps
#: the one absolute Windows path the doc names out of the population.
_PATHLIKE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]*")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_HEADING = re.compile(r"^#{1,6}\s")
_FILE_LINE = re.compile(
    r"[A-Za-z0-9_./\\-]+\.(?:py|md|json|ini|toml|txt|ps1|cfg|yml|yaml|js|html|xml|cmd):\d+"
)
_VERSION_LINE = re.compile(r"^CHANNEL_VERSION:\s*(\S+)\s*$", re.MULTILINE)


def _doc_bytes() -> bytes:
    return CHANNEL_DOC.read_bytes()


def _doc_text() -> str:
    # ASCII, deliberately: a non-ASCII byte must raise here rather than be
    # silently decoded and then pass a downstream regex.
    return _doc_bytes().decode("ascii")


def _lf_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


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
    return [line for line in text.split("\n") if _HEADING.match(line)]


def _dated_headings(text: str) -> list[str]:
    return [line for line in _heading_lines(text) if _DATE.search(line)]


def _repo_relative_paths(text: str) -> set[str]:
    """Slash-bearing tokens that name a path into a repository."""
    found: set[str] = set()
    for token in _PATHLIKE.findall(text):
        candidate = token.rstrip(".,;:")
        if not candidate or "/" not in candidate:
            continue
        if candidate.endswith("/"):
            found.add(candidate)
            continue
        if candidate.endswith(_PATH_SUFFIXES):
            found.add(candidate)
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


def _variant_table_rows(text: str) -> list[list[str]]:
    """Rows of the filename-variant table, keyed on its header cells.

    Located by `Example` ... `Shape` rather than by a line number: a line
    number into a 300-line doc decays on the next re-pin.
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


def test_the_digest_arm_can_fail():
    """A one-byte change must move the digest."""
    assert _lf_sha256(_doc_bytes() + b"x") != PINNED_SHA256


# ---------------------------------------------------------------------------
# Arm 3 - zero CR bytes (valid here because of the *.md LF pin)
# ---------------------------------------------------------------------------

def test_the_doc_carries_no_carriage_returns():
    count = _doc_bytes().count(b"\r")
    assert count == 0, (
        f"docs/CHANNEL.md carries {count} CR bytes - this tree pins "
        "`*.md text eol=lf` in .gitattributes, so a CRLF working copy means "
        "the file was written with a TEXT write rather than copied at byte "
        "level"
    )


def test_the_carriage_return_arm_can_fail():
    mutant = _doc_bytes().replace(b"\n", b"\r\n", 1)
    assert mutant.count(b"\r") == 1
    # ... and the digest pin SURVIVES that mutant, which is exactly why the CR
    # arm is a separate assertion and not folded into the digest.
    assert _lf_sha256(mutant) == PINNED_SHA256


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


def test_the_dated_heading_arm_can_fail():
    """Plant a dated heading IN MEMORY and prove the matcher fires."""
    for planted in (
        "## 10. An addendum 2026-09-15",
        "# 2026-09-15 conventions",
        "### Measured 1999-01-01 and never revisited",
    ):
        mutant = _doc_text() + "\n" + planted + "\n"
        assert _dated_headings(mutant) == [planted], f"matcher missed: {planted}"
    # And it must NOT fire on a date in ordinary prose, of which the doc has
    # plenty - a matcher that flags those is unusable, not strict.
    assert _dated_headings(_doc_text() + "\nMeasured 2026-09-14 under the harness.\n") == []


# ---------------------------------------------------------------------------
# Arm 6 - repo-relative paths resolve, and no file:line citation
# ---------------------------------------------------------------------------

def test_every_repo_relative_path_resolves():
    unresolved = _unresolved_paths(_doc_text())
    assert not unresolved, (
        "docs/CHANNEL.md names repo-relative paths that neither exist nor are "
        f"gitignored: {unresolved}"
    )


def test_the_path_scan_walked_a_real_population():
    paths = _repo_relative_paths(_doc_text())
    assert "docs/CHANNEL.md" in paths, f"self-reference not found - scan is broken: {sorted(paths)}"
    assert "moon_sync_inbox/" in paths, f"gitignored inbox not found: {sorted(paths)}"
    # The one absolute Windows path in the doc is not repo-relative and must
    # never be looked up on disk.
    assert not any("moonsync" in p for p in paths), f"absolute Windows path admitted: {sorted(paths)}"
    assert not any(p.startswith("n/a") for p in paths), "the prose token 'n/a' was read as a path"


def test_the_path_resolution_arm_can_fail():
    """Plant an unresolvable path IN MEMORY and prove the matcher fires."""
    sentinel = "docs/no-such-channel-path-guard-sentinel.md"
    assert not (REPO_ROOT / sentinel).exists()
    assert not _is_ignored(sentinel), "the sentinel became gitignored - pick another"
    mutant = _doc_text() + f"\nSee `{sentinel}` for more.\n"
    assert _unresolved_paths(mutant) == [sentinel]


def test_the_ignored_disjunct_is_load_bearing_and_narrow():
    """`moon_sync_inbox/` resolves ONLY via the ignored disjunct, not on disk."""
    assert _is_ignored("moon_sync_inbox/"), (
        "moon_sync_inbox/ is no longer gitignored here - re-derive arm 6's "
        "resolution rule before touching it"
    )
    # The disjunct must not be a blanket pass: a plainly non-ignored path is
    # still reported as not-ignored.
    assert not _is_ignored("docs/CHANNEL.md")


def test_the_doc_cites_no_file_line_pair():
    cites = _FILE_LINE.findall(_doc_text())
    assert not cites, (
        f"docs/CHANNEL.md carries file:line citations {cites} - a line number "
        "in a doc five trees re-pin decays on the next append, which is why "
        "the doc cites by bare filename"
    )


def test_the_file_line_matcher_can_fail():
    for planted in (
        "ops/loop/slots.py:39",
        "`tests/test_loop_concurrency.py:141`",
        "docs/CHANNEL.md:1",
    ):
        mutant = _doc_text() + "\nSee " + planted + " for the measurement.\n"
        assert _FILE_LINE.findall(mutant), f"matcher missed: {planted}"
    # A bare filename with no line number is the doc's own convention and must
    # not be flagged.
    assert not _FILE_LINE.findall("See `CROSS_REPO_CONVERGENCE_CHARTER.md` for provenance.")


# ---------------------------------------------------------------------------
# Arm 7 - the filename-variant table is present and parses
# ---------------------------------------------------------------------------
#
# That table, not a second file, is the grammar's test-vector source. Every
# tree grades its own responder against these rows, so the table losing a row
# is a silent loss of coverage in five trees at once.

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
    # And the parser must not simply return every table in the doc: the roster
    # table and the seventeen-rule table must not be picked up.
    rows = _variant_table_rows(text)
    assert all(row[-1] == "PRIMARY" or row[-1].startswith("Variant") for row in rows)
