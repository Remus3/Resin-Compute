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
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

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
_SOLO = re.compile(
    r"clockspeed|lanternlight|amberstone|legionwallpaper|redmoon",
    re.IGNORECASE,
)


def _tracked_text_files() -> list[str]:
    """Corpus from `git ls-files`, never an rglob.

    Measured in this tree: a leftover linked worktree under the repo root makes
    an rglob scan a second full copy and report content that is not ours. git
    does not descend into a nested checkout, so a git-sourced corpus is
    structurally immune. 34 of 39 test modules here were immune for exactly this
    reason and 4 were not.
    """
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
        for match in _PAIRED.finditer(flat):
            offenders.append(f"{rel} -> {match.group(0)!r}")
        for match in _SOLO.finditer(body):
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
    ],
)
def test_the_scan_fires_on_a_planted_offender(tmp_path: Path, planted: str):
    """Without a positive control, a clean result and an unarmed check are the same.

    Each case is one of the four real escapes. A guard that catches only the
    obvious spelling would report clean on three of them.
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
    )
    checked, offenders = _scan(["a.md"], tmp_path)
    assert checked == 1
    assert not offenders, offenders


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
