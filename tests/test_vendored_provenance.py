"""Every vendored third-party artifact must carry a provenance row.

WHY THIS FILE EXISTS. This tree vendored `docs/CHANNEL.md` from a sibling on an
upstream note that named a commit, called the source tree public, and named no
licence at all. Public is a VISIBILITY, not a grant. `docs/LICENSE_NOTES.md` is
the document this repository routes every inbound-licence question through, and
the bytes landed without it ever being opened. A NEIGHBOURING TREE'S licence
gate refused the same file and that is how the omission surfaced - nothing in
this tree would have noticed, because nothing in this tree was asking.

The licence turned out to be clean. The process did not, and the process is what
this module guards: a vendored artifact with no provenance row is
indistinguishable from one nobody ever checked.

WHAT THIS MODULE IS BLIND TO, stated up front rather than discovered later.

  1. A VENDOR DROP THAT ARRIVES WITH NO BYTE PIN. The registry below is checked
     against the pin declarations the tree already carries, which is a real
     second witness for the three artifacts that HAVE pins - but a fourth file
     copied in tomorrow with no pin and no registry row is invisible to every
     arm here. There is no machine-readable marker on a tracked file saying "not
     ours", and inventing one this module alone reads would be a marker nobody
     else applies. Closing this needs a convention, not a wider regex.
  2. WHETHER THE RECORDED LICENCE IS TRUE. These arms check that a row EXISTS
     and names a licence, a holder and a modification disposition. They cannot
     check that `Apache-2.0` is what upstream actually granted. That is a human
     reading of an upstream LICENSE file, done once at vendoring time and
     recorded; a test that re-derived it would be re-deriving it from the same
     row it is grading.
  3. WHETHER THE BYTES STILL MATCH UPSTREAM. That is the byte pins' job, and it
     is deliberately NOT duplicated here. `tests/test_channel_doc_pin.py` and
     `tests/test_loop_concurrency.py` own that claim; a second copy of a digest
     is a second thing to forget to re-pin.

THE CHECKED-COUNT RULE. The sweep returns `(checked, offenders)` and every arm
asserts the CHECKED count before it looks at the offender list. Zero out of zero
reads as a pass and this tree refuses that - `tests/test_no_sibling_names.py`
and `tests/test_mypy_scope.py` both make the same move.

NO UPSTREAM PROJECT NAME APPEARS HERE. `tests/test_no_sibling_names.py` refuses
any tracked file that names a sibling project of this operator's in plain text,
and that includes the clone URLs. The codenames are the citable form and they
resolve only in a gitignored per-host file. `docs/LICENSE_NOTES.md` records why
that trade was made and what it costs a downstream reader.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES = REPO_ROOT / "docs" / "LICENSE_NOTES.md"

#: The artifacts this tree declares as vendored, as repo-relative POSIX paths.
#: A hand-maintained literal, and it is NOT the only witness: the arm
#: `test_the_registry_agrees_with_the_trees_own_byte_pins` derives the same set
#: from the two pin modules' own constants and asserts equality. Deleting a row
#: here to quiet a red therefore breaks that arm too, which is the point -
#: a registry that is its own only authority disarms itself in one edit.
VENDORED_ARTIFACTS = (
    "docs/CHANNEL.md",
    "ops/loop/slots.py",
    "ops/loop/winmutex.py",
)

#: Fields a provenance row must carry. Each is a fact a redistributor is
#: answerable for under Apache-2.0 section 4, and each is checked ON THE SAME
#: LINE as the path, so a row that names the path and leaves the licence to a
#: paragraph three screens away does not count as a record.
SPDX_IDENTIFIER = "Apache-2.0"
COPYRIGHT_HOLDER = "Moonbeam"

#: Every row must SAY whether the bytes were changed. Silence is not "no".
#: A vendored file that HAS been patched locally is legitimate - it just has to
#: declare it, because that is the clause the modification statement satisfies.
MODIFICATION_DISPOSITIONS = ("Byte-identical to upstream", "MODIFIED LOCALLY")


def _rows_for(text: str, path: str) -> list[str]:
    """Every line of `text` that mentions `path` inside backticks."""
    needle = f"`{path}`"
    return [line for line in text.splitlines() if needle in line]


def check_provenance(text: str, artifacts: tuple[str, ...]) -> tuple[int, list[str]]:
    """Return (artifacts examined, offender descriptions).

    PURE on purpose. Every non-vacuity control below drives this function with
    synthetic text rather than mutating the real document - a test that edits a
    tracked file to prove a detector works is a test that can leave the tree
    dirty when it fails halfway, and this tree is worked on by several sessions
    at once.
    """
    checked = 0
    offenders: list[str] = []
    for path in artifacts:
        checked += 1
        rows = _rows_for(text, path)
        if not rows:
            offenders.append(
                f"{path}: vendored, and no line in the notes names it in backticks. "
                "A vendored artifact with no provenance row is indistinguishable "
                "from one nobody checked the licence of."
            )
            continue
        missing = []
        if not any(SPDX_IDENTIFIER in row for row in rows):
            missing.append(f"the SPDX identifier {SPDX_IDENTIFIER!r}")
        if not any(COPYRIGHT_HOLDER in row for row in rows):
            missing.append(f"the copyright holder {COPYRIGHT_HOLDER!r}")
        if not any(any(d in row for d in MODIFICATION_DISPOSITIONS) for row in rows):
            missing.append(
                "a modification disposition, one of "
                + " or ".join(repr(d) for d in MODIFICATION_DISPOSITIONS)
            )
        if missing:
            offenders.append(f"{path}: its row is missing " + ", ".join(missing))
    return checked, offenders


# ---------------------------------------------------------------------------
# The registry describes the real tree
# ---------------------------------------------------------------------------


def test_the_registry_is_not_empty_and_every_artifact_is_on_disk():
    assert VENDORED_ARTIFACTS, "an empty registry makes every arm below vacuous"
    missing = [p for p in VENDORED_ARTIFACTS if not (REPO_ROOT / p).is_file()]
    assert not missing, (
        f"the registry names {missing}, which are not on disk. Either the files "
        "were removed and the registry was not, or the paths are wrong - in "
        "either case the provenance arms below are grading a fiction."
    )


def test_every_vendored_artifact_is_tracked_by_git():
    """Trackedness, not existence. A provenance record is a promise to clones.

    Gated rather than failing, because this repository is routinely received as
    a Download ZIP or an sdist where trackedness is simply unknowable.
    """
    require_git_repository()
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    tracked = {entry for entry in out.stdout.split("\0") if entry}
    assert len(tracked) > 100, (
        f"`git ls-files` returned only {len(tracked)} paths, which is too few to "
        "be this tree - the enumeration is being graded, not the repository"
    )
    untracked = [p for p in VENDORED_ARTIFACTS if p not in tracked]
    assert not untracked, f"vendored but not tracked, so no clone receives them: {untracked}"


def test_the_registry_agrees_with_the_trees_own_byte_pins():
    """THE SECOND WITNESS, and the reason the registry is not self-authorising.

    The two pin modules already declare, in their own constants, exactly which
    files came from somewhere else - that is WHY they are pinned. Deriving the
    set from them and asserting equality means a registry row cannot be deleted
    without also editing a module that exists for a different reason.

    Imported inside the test body rather than at module scope so a failure in
    either pin module is that module's red, not a collection error here.
    """
    from tests.test_channel_doc_pin import CHANNEL_DOC
    from tests.test_loop_concurrency import LOOP_DIR, VENDORED_MODULES

    derived = {CHANNEL_DOC.relative_to(REPO_ROOT).as_posix()}
    for name in VENDORED_MODULES:
        derived.add((LOOP_DIR / name).relative_to(REPO_ROOT).as_posix())

    assert derived, "derived nothing from the pin modules - zero out of zero is not a pass"
    assert set(VENDORED_ARTIFACTS) == derived, (
        f"this registry holds {sorted(VENDORED_ARTIFACTS)} but the tree's own byte "
        f"pins declare {sorted(derived)}. Do not resolve this by editing whichever "
        "side is shorter: decide which file was actually vendored, then fix the "
        "side that is wrong and write the provenance row if one is owed."
    )


# ---------------------------------------------------------------------------
# The live document
# ---------------------------------------------------------------------------


def test_every_vendored_artifact_has_a_provenance_row():
    text = NOTES.read_text(encoding="utf-8")
    checked, offenders = check_provenance(text, VENDORED_ARTIFACTS)
    assert checked == len(VENDORED_ARTIFACTS), (
        f"the sweep examined {checked} of {len(VENDORED_ARTIFACTS)} artifacts"
    )
    assert not offenders, (
        "docs/LICENSE_NOTES.md is the single document this tree routes every "
        "inbound-licence question through. These vendored artifacts have no "
        "usable record in it:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("path", VENDORED_ARTIFACTS)
def test_the_notes_state_that_attribution_cannot_live_inside_the_file(path: str):
    """The pinned bytes cannot carry a header, so the reason must be written down.

    Without this the next maintainer's obvious fix for a missing attribution is
    to add a comment at the top of the file, which changes the digest and
    desynchronises every carrier.
    """
    flat = " ".join(NOTES.read_text(encoding="utf-8").split())
    assert f"`{path}`" in flat, f"{path} vanished from the notes entirely"
    assert "attribution has to sit BESIDE the file" in flat, (
        "the notes no longer explain why these files carry no attribution header, "
        "which is the explanation that stops somebody adding one"
    )


def test_the_notes_state_the_compatibility_direction_and_not_just_the_names():
    """Apache-2.0 inbound into GPL-3.0-or-later outbound is ONE-WAY.

    Naming both licences without naming the direction is the failure mode: it
    reads as a clearance in both directions and it is not one.
    """
    flat = " ".join(NOTES.read_text(encoding="utf-8").split())
    assert "ONE-WAY-COMPATIBLE" in flat, "the notes no longer state the direction"
    assert "GPL-3.0-or-later" in flat, "the notes no longer name this tree's outbound licence"
    assert "The reverse does not hold" in flat, (
        "the notes no longer say that nothing here may travel back upstream under "
        "the inbound licence, which is the half a reader is most likely to assume"
    )


def test_the_notes_record_the_process_finding_and_not_only_the_outcome():
    """The licence was clean. The gate not running is the finding.

    A record that says only "Apache-2.0, compatible, done" loses the reusable
    part, which is that a neighbour's gate caught what this tree's did not.
    """
    flat = " ".join(NOTES.read_text(encoding="utf-8").split())
    assert "Public is a visibility, not a grant" in flat or "Public is a VISIBILITY, not a grant" in flat, (
        "the notes no longer carry the sentence that names the actual error in "
        "the upstream note"
    )
    assert "without running its own inbound gate" in flat, (
        "the notes no longer record that this tree vendored before gating"
    )


# ---------------------------------------------------------------------------
# Non-vacuity: the detector fires, and it spares the legitimate neighbour
# ---------------------------------------------------------------------------


_COMPLETE_ROW = (
    "| `docs/EXAMPLE.md` | Sibling-Z | Apache License 2.0 | `Apache-2.0` | "
    "Moonbeam | **None.** Byte-identical to upstream |"
)


def test_the_detector_fires_when_the_row_is_absent():
    checked, offenders = check_provenance("nothing here at all\n", ("docs/EXAMPLE.md",))
    assert checked == 1
    assert len(offenders) == 1
    assert "no line in the notes names it" in offenders[0]


@pytest.mark.parametrize(
    ("label", "dropped"),
    [
        ("licence", "`Apache-2.0`"),
        ("holder", "Moonbeam"),
        ("modification", "Byte-identical to upstream"),
    ],
)
def test_the_detector_fires_when_a_row_drops_one_required_field(label: str, dropped: str):
    """One field at a time, so a detector that only notices a blank row fails here."""
    mutated = _COMPLETE_ROW.replace(dropped, "")
    assert mutated != _COMPLETE_ROW, f"the {label} mutant is a no-op - it changed nothing"
    assert "`docs/EXAMPLE.md`" in mutated, "the mutant removed the path, which is a different arm"
    checked, offenders = check_provenance(mutated, ("docs/EXAMPLE.md",))
    assert checked == 1
    assert len(offenders) == 1, f"the {label} mutant survived: {offenders}"
    assert "its row is missing" in offenders[0]


def test_the_detector_spares_a_complete_row():
    """THE SURVIVING NEIGHBOUR. A sweep that reds everything has proved nothing."""
    checked, offenders = check_provenance(_COMPLETE_ROW, ("docs/EXAMPLE.md",))
    assert checked == 1
    assert offenders == [], f"a complete row was condemned: {offenders}"


def test_a_locally_patched_artifact_is_admitted_when_it_declares_the_patch():
    """Vendoring WITH changes is legitimate. Undeclared changes are not.

    The arm above could be satisfied by a checker that only ever accepts the
    word "Byte-identical", which would make this repository unable to record a
    patched vendor drop at all - and the pressure would then be to delete the
    modification check rather than to use it.
    """
    patched = _COMPLETE_ROW.replace("**None.** Byte-identical to upstream", "MODIFIED LOCALLY")
    checked, offenders = check_provenance(patched, ("docs/EXAMPLE.md",))
    assert checked == 1
    assert offenders == [], f"a declared local patch was condemned: {offenders}"


def test_the_sweep_counts_before_it_complains():
    checked, offenders = check_provenance("", ())
    assert checked == 0
    assert offenders == []


# ---------------------------------------------------------------------------
# Byte hygiene
# ---------------------------------------------------------------------------


def test_this_module_and_the_notes_are_seven_bit_ascii():
    for target in (Path(__file__), NOTES):
        raw = target.read_bytes()
        bad = sorted({b for b in raw if b > 127})
        assert not bad, f"{target.name} carries non-ascii bytes {bad}"
