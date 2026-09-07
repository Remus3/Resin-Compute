"""Licence QA, guarding BOTH directions.

Two different questions live here and collapsing them is the mistake this file
exists to prevent.

**OUTBOUND** - what may others do with this project? GPL-3.0-or-later, per
ADR-006. The risk is DRIFT: the licence is declared in four places (`LICENSE`,
`NOTICE`, `README.md`, `shell/package.json`) and a project whose own files
disagree about its licence has, in practice, no licence anyone can rely on.

**INBOUND** - what may this project consume? ADR-002: vendor no game data,
re-implement the Enka client from published protocol. The risk is EROSION: a
bulk data dump or a copyleft dependency arriving quietly, one commit at a time.

ADR-006 dissolves exactly ONE of ADR-002's objections - the copyleft
incompatibility - and leaves the one that actually mattered standing, because a
licence on a wrapper cannot grant rights to HoYoverse's underlying game data. The
inbound arms below therefore do NOT relax.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tests.test_guard_worktree_exclusion import swept_files

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

#: SPDX identifier this project declares. One string, checked everywhere.
SPDX = "GPL-3.0-or-later"

#: SHA-256 of the verbatim GPL-3.0 text, the canonical published value. Pinned so
#: an edit to LICENSE - accidental, or a well-meant reformat - fails loudly. The
#: licence text is not ours to reword.
GPL3_SHA256 = "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903"


# ---------------------------------------------------------------------------
# Outbound - the declaration must be consistent everywhere
# ---------------------------------------------------------------------------


def test_the_licence_file_is_the_verbatim_unmodified_gpl3():
    licence = REPO_ROOT / "LICENSE"
    assert licence.is_file(), "no LICENSE file"
    raw = licence.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GPL3_SHA256, "LICENSE is not the verbatim GPL-3.0 text"


def test_the_licence_text_is_seven_bit_ascii():
    """The hard glyph rule has no exception for a vendored licence."""
    raw = (REPO_ROOT / "LICENSE").read_bytes()
    offenders = sorted({byte for byte in raw if byte > 0x7E})
    assert not offenders, f"LICENSE carries non-ASCII bytes: {offenders}"


def test_the_licence_text_is_structurally_complete():
    """A truncated licence is worse than none: it looks authoritative."""
    text = (REPO_ROOT / "LICENSE").read_text(encoding="ascii")
    for marker in (
        "GNU GENERAL PUBLIC LICENSE",
        "Version 3, 29 June 2007",
        "TERMS AND CONDITIONS",
        "END OF TERMS AND CONDITIONS",
        "How to Apply These Terms to Your New Programs",
    ):
        assert marker in text, f"LICENSE is missing {marker!r}"


def test_the_notice_names_the_licence_and_the_holder():
    notice = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "GNU General Public License" in notice
    assert "version 3" in notice
    assert re.search(r"Copyright \d{4}", notice), "NOTICE carries no copyright line"


def test_the_package_manifest_declares_the_same_licence():
    manifest = json.loads((REPO_ROOT / "shell" / "package.json").read_text(encoding="utf-8"))
    assert manifest["license"] == SPDX


def test_the_readme_declares_the_same_licence():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert SPDX in readme


#: The pre-ADR-006 wording. A tracked file still ASSERTING either of these
#: contradicts `LICENSE`, and a project whose own files disagree about its
#: licence has, in practice, no licence anyone can rely on.
STALE_LICENCE_CLAIMS = ("Private. No licence granted", "UNLICENSED")

#: Tracked paths where a stale phrase is a QUOTATION and not a DECLARATION,
#: each with the reason it is exempt.
#:
#: Named ONE AT A TIME rather than by directory glob. An exemption expressed as
#: `docs/adr/*` widens on its own every time an ADR is added, and an exemption
#: that widens on its own has stopped being an exemption and become a hole.
#: Every entry is re-earned on each run by
#: `test_every_quotation_exemption_is_still_earned` below.
QUOTATION_EXEMPT = {
    "tests/test_licence_posture.py": (
        "this guard's own denylist literals - a sweep cannot look for a phrase "
        "it is forbidden to spell"
    ),
    "docs/adr/ADR-006-outbound-licence.md": (
        "quotes the superseded README wording as the very thing it replaced"
    ),
    "docs/adr/ADR-009-per-file-licence-headers.md": (
        "cites ADR-006's finding of that same superseded wording"
    ),
}


def _git(*args: str) -> str:
    """Run git at the repo root, SKIPPING the calling test when git cannot answer.

    Guarded here, at the single point where the dependency is real, rather than
    at module level - every arm in this file that reads a known path off disk
    needs no repository and keeps its coverage in a Download-ZIP or sdist copy.
    See the header of `tests/conftest.py` for why that distinction is not
    theoretical.
    """
    require_git_repository()
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _is_utf8_text(path: Path) -> bool:
    """Can this file's bytes be read as text at all?

    A phrase check has no meaning over binary bytes, and one committed PNG must
    not abort the whole sweep with a `UnicodeDecodeError`.
    """
    try:
        path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _tracked_text_files() -> list[str]:
    """Every tracked path whose bytes decode as UTF-8, sorted.

    ASKED OF GIT, not walked off disk. The question this guard exists to answer
    is what A FRESH CLONE RECEIVES. A `Path.glob` answers the different question
    of what is on this machine - it would drag in `node_modules/` and every
    untracked scratch file, and it would still have missed the defect that
    prompted the widening, because the old corpus was five hand-listed paths.
    """
    tracked = [line for line in _git("ls-files").splitlines() if line]
    return sorted(
        name
        for name in tracked
        # A staged deletion is tracked but absent from disk. Not this guard's
        # problem, and reading it would raise.
        if (REPO_ROOT / name).is_file() and _is_utf8_text(REPO_ROOT / name)
    )


def _swept_for_stale_licence_claims() -> list[str]:
    return [name for name in _tracked_text_files() if name not in QUOTATION_EXEMPT]


def test_no_tracked_file_still_claims_the_project_is_unlicensed():
    """The pre-ADR-006 wording, swept out of the WHOLE tracked tree.

    THE DEFECT THIS WIDENING ENCODES, which this repository shipped. The corpus
    was `REPO_ROOT.glob("*.md")` plus `shell/package.json` - five files out of
    153 tracked. `shell/package-lock.json` sat outside it declaring
    `"license": "UNLICENSED"` while `shell/package.json` three lines of code
    away declared GPL-3.0-or-later, and this guard passed green throughout.

    It did not self-heal and could not. The commit that flipped `package.json`
    ADDED THIS VERY GUARD in the same breath, and npm only rewrites the
    lockfile's root entry when it re-reads the manifest, which nothing since
    made it do. The lockfile root entry is what dependency scanners and GitHub's
    dependency graph read, so the contradiction was the machine-readable half.

    Trap 1 in `docs/LICENSE_NOTES.md` is this exact failure, written in this
    repository's own words before it committed it: "A repo can contradict
    itself. The LICENSE file and the package.json or pyproject.toml licence
    field can disagree. Read both."
    """
    offenders: list[str] = []
    for name in _swept_for_stale_licence_claims():
        text = (REPO_ROOT / name).read_bytes().decode("utf-8")
        for phrase in STALE_LICENCE_CLAIMS:
            if phrase in text:
                offenders.append(f"{name} still says {phrase!r}")
    assert not offenders, (
        "these tracked files contradict LICENSE about this project's own "
        "licence: " + "; ".join(offenders)
    )


def test_the_stale_licence_sweep_reaches_the_whole_tracked_tree():
    """Non-vacuity. This is the arm that would have caught the five-file corpus.

    A sweep is only as good as what it looks at, and a corpus that quietly
    narrows leaves a guard that passes forever while guarding nothing. The named
    paths are the four places the licence is declared plus the lockfile that was
    the actual offender - none of them may fall out of the sweep again.
    """
    swept = set(_swept_for_stale_licence_claims())
    assert len(swept) >= 100, (
        f"the sweep collapsed to {len(swept)} files; it is meant to cover the "
        "whole tracked tree"
    )
    for required in (
        "shell/package-lock.json",
        "shell/package.json",
        "README.md",
        "NOTICE",
        "LICENSE",
        "docs/LICENSE_NOTES.md",
    ):
        assert required in swept, f"the stale-licence sweep no longer reaches {required}"


def test_every_quotation_exemption_is_still_earned():
    """THE DISARM PATH, CLOSED. Read this before adding an entry above.

    The cheapest way to make the sweep green is not to fix the offender but to
    exempt it, and the second cheapest is to leave a dead entry lying around
    until something drifts into its path. Three arms, all mandatory:

      - the exempted path must still EXIST, so a rename cannot leave a stale
        entry silently covering nothing;
      - it must still CONTAIN a stale phrase, so a dead exemption is deleted
        rather than left as a pre-authorised hole;
      - it may not be a MANIFEST. `shell/package-lock.json` and
        `shell/package.json` are exactly what this guard exists to check, and a
        machine-readable licence field is a DECLARATION - it can never be a
        quotation of history, so no `.json` may ever be exempted for one.

    Needs no git repository, so it keeps its teeth in a Download-ZIP copy where
    the sweep above can only skip.
    """
    for name, reason in QUOTATION_EXEMPT.items():
        path = REPO_ROOT / name
        assert path.is_file(), (
            f"the quotation exemption for {name} names a file that is gone; "
            "delete the entry rather than leaving it to cover a future path"
        )
        assert not name.endswith(".json"), (
            f"{name} is a manifest and manifests may never be exempted. A licence "
            "field is a declaration, not a quotation, and exempting one would "
            "disarm the exact check this file exists to perform"
        )
        text = path.read_bytes().decode("utf-8")
        assert any(phrase in text for phrase in STALE_LICENCE_CLAIMS), (
            f"the exemption for {name} is dead - it carries none of "
            f"{list(STALE_LICENCE_CLAIMS)} any more. Remove it. Reason on "
            f"file: {reason}"
        )


def test_the_sweep_skips_undecodable_files_instead_of_erroring(tmp_path):
    """Aimed at the predicate, because the live tree gives it no subject.

    Every one of the 153 tracked files decodes as UTF-8 today, so the binary
    branch is unexercised by the sweep itself - and an unexercised branch is the
    one that breaks the first time a favicon or a screenshot is committed. It is
    therefore asserted here directly rather than assumed.
    """
    decodable = tmp_path / "notes.md"
    decodable.write_bytes(b"a tracked text file\n")
    binary = tmp_path / "icon.png"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\xff\x00")
    assert _is_utf8_text(decodable)
    assert not _is_utf8_text(binary), "the binary guard would let a decode error escape"


def test_the_notice_disclaims_any_right_over_the_game_data():
    """The single most important sentence in the whole licence posture.

    An outbound licence covers THIS project's code. Someone could otherwise read
    a GPL header over a repository full of Genshin nouns as a grant over
    HoYoverse's material, which it is not and cannot be.
    """
    notice = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "HoYoverse" in notice
    assert "NO GAME DATA IS VENDORED" in notice


# ---------------------------------------------------------------------------
# Inbound - ADR-002's posture must not erode
# ---------------------------------------------------------------------------


def test_the_runtime_still_declares_no_third_party_dependency():
    """Stdlib-only at runtime is a recorded decision, not an accident."""
    text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    declared = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert declared == [], f"a runtime dependency appeared: {declared}"


@pytest.mark.parametrize("forbidden", ["enka-py", "enka_py", "ambr-py", "ambr_py", "genshin-db", "genshindata"])
def test_no_forbidden_upstream_is_declared_as_a_dependency(forbidden: str):
    """ADR-006 dissolved the COPYLEFT objection to enka-py and ambr-py. It did
    not dissolve the one that mattered - both wrap HoYoverse game data, which no
    outbound licence of ours can grant rights over. So the refusal stands, and
    this arm must not be relaxed on the strength of ADR-006 alone."""
    for name in ("requirements.txt", "requirements-dev.txt"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8").lower()
        declared = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any(forbidden in line for line in declared), f"{name} declares {forbidden}"


def test_the_node_shell_declares_only_the_window_toolkit():
    """Node exists in this tree solely to host a window - ADR-005. A data
    library appearing among its dependencies would be a posture change."""
    manifest = json.loads((REPO_ROOT / "shell" / "package.json").read_text(encoding="utf-8"))
    assert manifest.get("dependencies", {}) == {}, "the shell declares runtime dependencies"
    assert set(manifest.get("devDependencies", {})) == {"electron"}


def test_no_data_file_is_large_enough_to_be_a_bulk_dump():
    """A vendored dataset does not arrive announced. It arrives as a big file.

    The seed tables are a few kilobytes. Anything past the threshold deserves a
    human deciding it is legitimate rather than a silent commit.
    """
    limit = 64 * 1024
    checked = swept_files(DATA_DIR)
    assert checked, "the sweep of data/ found nothing - zero out of zero is not a pass"
    oversized = [
        f"{p.relative_to(REPO_ROOT).as_posix()} ({p.stat().st_size} bytes)"
        for p in checked
        if p.stat().st_size > limit
    ]
    assert not oversized, f"suspiciously large files under data/: {oversized}"


def test_the_fixtures_directory_still_says_what_it_is():
    readme = (REPO_ROOT / "data" / "fixtures" / "README.md").read_text(encoding="utf-8")
    assert "No upstream dataset is vendored" in readme


def test_the_licence_notes_still_carry_the_blanket_caveat():
    """The sentence that survives every outbound licence decision.

    Whitespace-normalised before matching. The claim is about the PROSE, and
    prose gets reflowed; an assertion that breaks on a line wrap is a false
    alarm that trains people to weaken the test.
    """
    notes = (REPO_ROOT / "docs" / "LICENSE_NOTES.md").read_text(encoding="utf-8")
    flat = " ".join(notes.split())
    assert "HoYoverse" in flat
    # The load-bearing fragment, not a paraphrase of it. The sentence ends
    # "the underlying Genshin Impact data"; asserting my own wording instead of
    # the file's is how a guard ends up testing the test.
    assert "cannot grant rights to the underlying" in flat


def test_the_licence_notes_point_at_the_outbound_decision():
    """The two directions are different questions and each must find the other.

    LICENSE_NOTES answers INBOUND only. A reader arriving there with an outbound
    question needs to be sent to ADR-006 rather than concluding it is unanswered.
    """
    notes = (REPO_ROOT / "docs" / "LICENSE_NOTES.md").read_text(encoding="utf-8")
    assert "ADR-006" in notes


def test_the_inbound_sweep_is_not_vacuous():
    data_files = swept_files(DATA_DIR)
    assert len(data_files) >= 3, f"only found {len(data_files)} data files"
    assert (REPO_ROOT / "requirements.txt").is_file()


# ---------------------------------------------------------------------------
# Helpers
#
# Every prose assertion below matches against WHITESPACE-NORMALISED text. The
# claims are about the prose, and prose gets reflowed; an assertion that breaks
# on a line wrap is a false alarm that trains people to weaken the test. It is
# also not hypothetical - on 2026-09-06 a single-line sweep of this tree for
# "relicense this repo" returned eight files and MISSED data/fixtures/README.md,
# because the phrase wraps across two lines there.
# ---------------------------------------------------------------------------


def _flatten(text: str) -> str:
    """Collapse every run of whitespace, including newlines, to one space."""
    return " ".join(text.split())


def _notice() -> str:
    return (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")


def _fixtures_readme() -> str:
    return (REPO_ROOT / "data" / "fixtures" / "README.md").read_text(encoding="utf-8")


def _warranty_paragraph_from_licence() -> str:
    """The GPL-3 warranty disclaimer, READ FROM LICENSE at runtime.

    Deliberately not a hardcoded copy. GPL-3 section 4 requires a conveyor to
    keep intact all notices of the absence of warranty, so the guard has to
    compare NOTICE against the licence text actually in this tree rather than
    against a transcription of it. A hardcoded copy would let NOTICE and LICENSE
    drift apart while the test stayed green, which is the exact failure mode.
    """
    text = (REPO_ROOT / "LICENSE").read_text(encoding="ascii")
    appendix = text.split("END OF TERMS AND CONDITIONS", 1)[-1]
    match = re.search(
        r"(This program is distributed in the hope that it will be useful,"
        r".*?GNU General Public License for more details\.)",
        _flatten(appendix),
    )
    assert match is not None, "the GPL-3 appendix in LICENSE no longer carries the warranty paragraph"
    return match.group(1)


def _collect_strings(value: object, into: list[str]) -> None:
    if isinstance(value, str):
        into.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_strings(item, into)
    elif isinstance(value, list):
        for item in value:
            _collect_strings(item, into)


def _self_contradiction(document: dict) -> str | None:
    """Does a fixture's structured self-label disagree with its own prose?

    THE DEFECT THIS ENCODES, which this repository shipped: `seed_roster.json`
    and `seed_materials.json` each carried `"_synthetic": true` on the line
    DIRECTLY ABOVE a `"_note"` calling them a hand-authored table of
    independently verified ids. SYNTHETIC means INVENTED. Both lines cannot be
    true of the same bytes, and the flag was the false one - the contents are
    real, publicly known game facts, hand-authored rather than vendored.

    THE RULE IS NOT "never say synthetic". `enka_sample_profile.json` is
    genuinely invented - 9xxxxxxx placeholder ids, SYNTHETIC_* name hashes - and
    must keep saying so. The rule is that the MACHINE-READABLE flag and the
    file's own PROSE must agree, and that the two structured claims are mutually
    exclusive: a payload is either invented or it is a hand-authored record of
    fact, never both.

    Returns the reason a document is an offender, or None when it is honest.
    """
    synthetic = bool(document.get("_synthetic"))
    hand_authored = bool(document.get("_hand_authored"))

    prose_parts: list[str] = []
    for key, value in document.items():
        if key.startswith("_"):
            _collect_strings(value, prose_parts)
    prose = _flatten(" ".join(prose_parts)).lower()

    if synthetic and hand_authored:
        return "flags itself BOTH _synthetic and _hand_authored - a payload cannot be both"
    if synthetic and "synthetic" not in prose:
        tail = " - its notes call it hand-authored" if "hand-authored" in prose else ""
        return f"flags itself _synthetic but its own notes never say so{tail}"
    if hand_authored and "hand-authored" not in prose:
        return "flags itself _hand_authored but its own notes never say so"
    return None


def _fixtures_readme_sections() -> dict[str, str]:
    """The fixtures README's `### <heading>` sections, keyed by heading text."""
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in _fixtures_readme().splitlines():
        if line.startswith("### "):
            if current is not None:
                sections[current] = "\n".join(buffer)
            current = line[4:].strip().strip("`")
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer)
    return sections


def _fixtures_readme_table_rows() -> list[str]:
    """Every markdown table row in the fixtures README, whitespace-normalised."""
    return [
        _flatten(line)
        for line in _fixtures_readme().splitlines()
        if line.lstrip().startswith("|")
    ]


# ---------------------------------------------------------------------------
# Outbound - NOTICE must carry everything GPL-3 and the fan-content posture
# require, not just the half that is flattering
# ---------------------------------------------------------------------------


def test_the_notice_keeps_the_gpl3_warranty_disclaimer_intact():
    """GPL-3 section 4: a conveyor must keep intact all notices of the absence
    of warranty. NOTICE carried the FIRST paragraph of the appendix notice and
    not the SECOND, which is the one that disclaims warranty.

    Matched against the paragraph READ FROM LICENSE at runtime, so NOTICE and
    LICENSE cannot drift and a reworded NOTICE fails here rather than silently
    becoming a paraphrase of a licence term.
    """
    warranty = _warranty_paragraph_from_licence()
    assert warranty in _flatten(_notice()), (
        "NOTICE does not carry the GPL-3 warranty disclaimer. Expected, verbatim "
        f"from the appendix in LICENSE: {warranty!r}"
    )


def test_the_warranty_guard_would_reject_a_paraphrase():
    """Non-vacuity. A guard that any nearby wording satisfies guards nothing."""
    warranty = _warranty_paragraph_from_licence()
    assert "WITHOUT ANY WARRANTY" in warranty
    assert "MERCHANTABILITY" in warranty
    assert len(warranty) > 150, f"the extraction collapsed to {len(warranty)} chars"
    paraphrase = _flatten(
        "This program is distributed in the hope that it will be useful, but it "
        "comes with no warranty of any kind. See the GNU General Public License "
        "for more details."
    )
    assert warranty not in paraphrase, "the warranty guard accepts a paraphrase"


def test_the_notice_acknowledges_the_trademarks():
    """Naming the marks is not the same as acknowledging them AS marks.

    NOTICE already disclaimed affiliation and named the copyright holders. It
    never said the names themselves are trademarks used nominatively, which is
    the acknowledgement a fan project is expected to carry.
    """
    flat = _flatten(_notice())
    for mark in ("Genshin Impact", "HoYoverse", "miHoYo", "Cognosphere"):
        assert mark in flat, f"NOTICE does not name the mark {mark!r}"
    assert "trademark" in flat.lower(), (
        "NOTICE names the marks but never acknowledges them as trademarks"
    )
    assert "respective owners" in flat


def test_the_notice_states_the_non_commercial_posture():
    """Load-bearing, not decoration - but NOT for the reason first written here.

    The original docstring said every retrievable HoYoverse fan-content
    permission is CONDITIONED on non-commercial use, and that this project
    therefore had to state its posture to meet a condition it was relying on.
    ADR-008 refuted that premise: no first-party permission covering software of
    this kind was located at all, so there is no condition being met and no
    permission being relied on.

    The arm stays because the FACT still matters. The one first-party sentence
    that comes anywhere near this project is a non-prohibition of non-commercial
    personal use, self-disclaimed by its author as not an approval. Whatever
    little that is worth, it is worth nothing at all to a commercial project -
    so if this project ever stops being non-commercial, ADR-008's analysis has
    to be redone. Stating the posture keeps that trigger visible.
    """
    assert "non-commercial" in _flatten(_notice()).lower(), (
        "NOTICE does not state the non-commercial posture"
    )


# ---------------------------------------------------------------------------
# Inbound - a compliance label that is false about its own contents is a worse
# position than the true one, and this repo is about to be public
# ---------------------------------------------------------------------------


def test_no_data_fixture_contradicts_itself_about_being_synthetic():
    """See `_self_contradiction` for the defect and the rule."""
    offenders: list[str] = []
    for path in swept_files(DATA_DIR, "*.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            continue
        reason = _self_contradiction(document)
        if reason is not None:
            offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()} {reason}")
    assert not offenders, "; ".join(offenders)


def test_the_self_contradiction_detector_actually_fires():
    """Non-vacuity, and the SURVIVAL arm that pairs with it.

    Both halves are mandatory. A detector that flags everything scores 100
    percent on the offenders by condemning the honest files too, and a sweep
    driven by it would relabel the one fixture that is legitimately synthetic.
    """
    shipped = {
        "_synthetic": True,
        "_note": "Hand-authored seed identity table. No upstream dataset is vendored.",
    }
    assert _self_contradiction(shipped) is not None, "the detector misses the shipped defect"
    both = {"_synthetic": True, "_hand_authored": True, "_note": "synthetic, hand-authored"}
    assert _self_contradiction(both) is not None, "the detector allows both flags at once"

    honest_invention = {
        "_synthetic": True,
        "_note": "SYNTHETIC hand-authored payload. Nothing here is copied from any dataset.",
    }
    assert _self_contradiction(honest_invention) is None, (
        "the detector condemns a genuinely synthetic fixture that says so"
    )
    honest_record = {
        "_hand_authored": True,
        "_note": "Hand-authored table of publicly known facts, independently verified.",
    }
    assert _self_contradiction(honest_record) is None, (
        "the detector condemns an honest hand-authored record"
    )


def test_the_data_fixture_sweep_reaches_every_json():
    """A predicate that scans nothing passes for free."""
    scanned = sorted(p.name for p in swept_files(DATA_DIR, "*.json"))
    for expected in ("enka_sample_profile.json", "seed_materials.json", "seed_roster.json"):
        assert expected in scanned, f"the fixture sweep did not reach {expected}: {scanned}"


def test_the_fixtures_readme_title_agrees_with_its_body():
    """The title was a blanket claim its own body contradicted three lines later.

    It read "SYNTHETIC test data only" over a body saying the contents are
    hand-authored by this repository. Both cannot be true of the same bytes, and
    this README is what a takedown correspondent gets pointed at once the repo is
    public. A compliance document that is demonstrably false about its own
    contents is a far worse position than the true one - which here is also the
    stronger one: no upstream dataset is vendored at all.
    """
    raw = _fixtures_readme()
    title = raw.splitlines()[0]
    assert title.startswith("# "), f"the first line is not an H1: {title!r}"
    assert "synthetic" not in title.lower(), (
        f"the H1 still makes a directory-wide synthetic claim: {title!r}. The seed "
        "tables hold real, independently verified ids, and real ids are not invented"
    )
    assert "hand-authored" in title.lower(), f"the H1 does not say what the directory is: {title!r}"
    body = _flatten(raw[len(title):]).lower()
    assert "hand-authored" in body, "the H1 and the body do not make the same claim"


def test_the_fixtures_readme_labels_each_file_with_its_own_kind():
    """The directory holds BOTH kinds now, and that distinction is the point.

    Two guards, both mandatory. The false label must be gone from the two seed
    tables, and the TRUE one must have survived on `enka_sample_profile.json`,
    which is genuinely invented - 9xxxxxxx placeholder ids, SYNTHETIC_* name
    hashes - and must go on saying so.
    """
    sections = _fixtures_readme_sections()
    for name in ("seed_roster.json", "seed_materials.json", "enka_sample_profile.json"):
        assert name in sections, f"the README has no section for {name}: {sorted(sections)}"

    invented = _flatten(sections["enka_sample_profile.json"]).lower()
    assert "synthetic" in invented, "the one genuinely invented fixture is no longer labelled synthetic"

    for real in ("seed_roster.json", "seed_materials.json"):
        text = _flatten(sections[real]).lower()
        # An explicit denial is honest prose, not a relapse. Strip the denials
        # first so this catches only an AFFIRMATIVE synthetic label, and does not
        # become a trap that punishes someone for writing the correction down.
        affirmative = text.replace("not synthetic", "").replace("never synthetic", "")
        assert "synthetic" not in affirmative, (
            f"the {real} section still calls real, independently verified ids synthetic"
        )
        assert "verified" in text, f"the {real} section does not say the ids were verified"


def test_the_fixtures_readme_records_that_adr_006_dissolved_the_copyleft_reason():
    """A reader who finds ADR-006 must not conclude the refusal has no basis.

    The README's table refused `enka-py` and `ambr-py` because "copyleft would
    relicense this repository". ADR-006 made this tree GPL-3.0-or-later, so that
    reason stopped being true. Left standing unqualified, a public reader checks
    it, finds it void, and reads the whole refusal as void with it.
    """
    flat = _fixtures_readme()
    lowered = _flatten(flat).lower()
    assert "adr-006" in lowered, "the fixtures README never mentions ADR-006"
    assert "dissolve" in lowered, "the README does not say ADR-006 DISSOLVED anything"
    assert "exactly one" in lowered, (
        "the README does not bound the dissolution. ADR-006 dissolved exactly ONE "
        "objection and no others, and a reader who cannot see that bound will read "
        "it as having dissolved the lot"
    )


def test_the_fixtures_readme_does_not_refuse_on_the_dissolved_reason_alone():
    """GUARD ONE of two: the dead reason must not be the whole basis of a row."""
    rows = _fixtures_readme_table_rows()
    for name in ("enka-py", "ambr-py"):
        row = next((r for r in rows if name in r), None)
        assert row is not None, f"the licence table no longer has a row for {name}"
        lowered = row.lower()
        assert "do not vendor" in lowered, f"the {name} row no longer refuses"
        if "relicense" in lowered or "copyleft" in lowered:
            assert "adr-006" in lowered or "dissolved" in lowered, (
                f"the {name} row still rests on the copyleft objection without "
                "saying ADR-006 dissolved exactly that objection. A reader who "
                "checks it will find it void and read the refusal as void with it"
            )


def test_the_fixtures_readme_keeps_the_surviving_reason_to_refuse():
    """GUARD TWO of two: the LEGITIMATE NEIGHBOUR must have survived the sweep.

    ADR-006 dissolved the copyleft objection. It did not dissolve the one that
    actually mattered: both projects wrap HoYoverse game data, and a licence on a
    wrapper cannot grant rights to the payload. The data was always the real
    gate. A sweep that scored on guard one by deleting this reason as well would
    leave the refusal with no stated basis at all, which is worse than the
    stale reason it replaced.

    Whitespace-normalised - this sentence wraps across lines in the file.
    """
    flat = _flatten(_fixtures_readme())
    assert "cannot grant rights to the underlying" in flat, (
        "the fixtures README lost the blanket caveat, which is the surviving reason"
    )
    assert "HoYoverse" in flat
    for name in ("enka-py", "ambr-py"):
        row = next((r for r in _fixtures_readme_table_rows() if name in r), None)
        assert row is not None, f"the licence table no longer has a row for {name}"
        lowered = row.lower()
        assert "game data" in lowered or "hoyoverse" in lowered, (
            f"the {name} row gives no surviving reason to refuse: {row!r}"
        )


# ---------------------------------------------------------------------------
# Inbound - the DIRECTORY-WIDE synthetic claim, swept out of the LIVE docs
#
# "`data/fixtures/` holds synthetic fixtures" is FALSE of two of the three
# files in that directory, and it was written into three places at once. This
# is the sweep that stops it coming back. Being a sweep, it carries the
# surviving-neighbour arm this tree requires of every sweep: the one fixture
# that genuinely IS invented must go on being called synthetic.
# ---------------------------------------------------------------------------


#: An affirmative DIRECTORY-WIDE synthetic claim - `data/fixtures/` and the
#: word `synthetic` inside one sentence.
#:
#: THE `[^.]` IS LOAD-BEARING AND MUST NOT BE RELAXED TO `.`. Refusing to cross
#: a period is what confines the match to a single sentence, and it is also
#: exactly what makes the pattern walk past the TRUE per-file claim: in "only
#: `data/fixtures/enka_sample_profile.json` is synthetic" the period inside the
#: filename breaks the match before it ever reaches the word. Widen it to `.`
#: and this sweep begins condemning the one sentence it exists to protect.
_DIRECTORY_WIDE_SYNTHETIC = re.compile(
    r"data/fixtures/?[^.]{0,140}?\bsynthetic\b", re.IGNORECASE
)

#: Frozen decision records, swept out of the guard below.
#:
#: An ADR states a decision AS IT WAS MADE. `docs/adr/ADR-002-data-posture.md`
#: says so in terms - "The body below is left exactly as it was written" -
#: because editing the reasoning to match a later decision destroys the record
#: `docs/adr/README.md` exists to keep. ADR-002's Decision section therefore
#: still carries the false wording and always will.
#:
#: THAT EXCLUSION IS PAID FOR, not granted. The banner arm at the end of this
#: file requires the correction to appear in ADR-002's AMENDMENT BANNER
#: instead, so a reader cannot take the frozen Decision section at face value.
#: Exempt from the sweep is not exempt from being corrected.
_FROZEN_RECORD_PREFIX = "docs/adr/"


def _live_compliance_docs() -> list[str]:
    """Tracked `.md` under `docs/` that speaks in the present tense.

    `docs/LEDGER.md` is deliberately IN. It narrates rather than decides, so it
    could in principle restate the false claim while reporting it - but a live
    document that repeats "the fixtures are synthetic" WITHOUT marking it
    corrected is a hazard whoever wrote it, and one worth a human reading. It
    does not trip the sweep today.
    """
    return [
        name
        for name in _tracked_text_files()
        if name.startswith("docs/")
        and name.endswith(".md")
        and not name.startswith(_FROZEN_RECORD_PREFIX)
    ]


def test_no_live_doc_calls_the_whole_fixtures_directory_synthetic():
    """The claim is false, and it is false in the direction that costs.

    `data/fixtures/seed_roster.json` and `seed_materials.json` carry
    `_hand_authored: true` and `_vendored: false`, and their own notes call them
    hand-authored tables of independently verified ids. SYNTHETIC MEANS
    INVENTED, and a verified avatarId is not invented. Only
    `enka_sample_profile.json` is genuinely synthetic and flags itself so.

    `data/fixtures/README.md` states the stakes plainly, and this repository is
    public: a compliance document that is demonstrably false about its own
    contents is a far worse position than the true one - which here is also the
    STRONGER one, because hand-authored-and-nothing-vendored is a bigger claim
    than synthetic.

    `CLAUDE.md` routes every contributor to `docs/LICENSE_NOTES.md` as the
    authority on this question, which is what made the wording there load
    bearing rather than cosmetic.
    """
    offenders: list[str] = []
    for name in _live_compliance_docs():
        flat = _flatten((REPO_ROOT / name).read_bytes().decode("utf-8"))
        for match in _DIRECTORY_WIDE_SYNTHETIC.finditer(flat):
            offenders.append(f"{name}: {match.group(0)!r}")
    assert not offenders, (
        "these live documents call the whole fixtures directory synthetic, which "
        "is false of the two hand-authored seed tables in it: " + "; ".join(offenders)
    )


def test_the_directory_wide_synthetic_sweep_spares_the_true_per_file_claim():
    """BOTH ARMS, and neither is optional.

    A sweep that scores on the first arm by deleting the second's subject has
    failed. The false claim must be caught; the true per-file claim about
    `enka_sample_profile.json` must survive untouched, because that fixture is
    genuinely invented - 9xxxxxxx placeholder ids, SYNTHETIC_* name hashes - and
    a sweep that relabelled it would replace one false document with another.
    """
    false_claim = (
        "1. **Vendor no game data.** `data/fixtures/` holds only hand-authored "
        "synthetic fixtures for tests, labelled as such"
    )
    assert _DIRECTORY_WIDE_SYNTHETIC.search(false_claim) is not None, (
        "the detector misses the exact wording this repository shipped"
    )

    true_claim = (
        "Only `data/fixtures/enka_sample_profile.json` is synthetic; the two seed "
        "tables are hand-authored records of publicly verified game fact"
    )
    assert _DIRECTORY_WIDE_SYNTHETIC.search(true_claim) is None, (
        "the detector condemns the TRUE per-file claim - the surviving neighbour "
        "this sweep exists to leave standing"
    )


def test_the_live_docs_sweep_reaches_the_document_that_carried_the_claim():
    """Non-vacuity. A corpus that stopped including the offender passes free."""
    swept = _live_compliance_docs()
    assert "docs/LICENSE_NOTES.md" in swept, (
        "the sweep no longer reaches LICENSE_NOTES, which is the file CLAUDE.md "
        "names as the authority on this question"
    )
    assert len(swept) >= 3, f"only {len(swept)} live docs resolved into the sweep"


def test_the_licence_notes_keep_the_one_genuinely_synthetic_fixture_named():
    """The surviving neighbour, asserted against the LIVE file and not a sample.

    The lazy way to make the sweep above green is to delete every mention of
    synthetic from LICENSE_NOTES. That would swap a false statement for a vaguer
    one and lose the distinction that is the entire point: the directory holds
    two KINDS of file. The correction has to name which file is which.
    """
    flat = _flatten((REPO_ROOT / "docs" / "LICENSE_NOTES.md").read_bytes().decode("utf-8"))
    assert "enka_sample_profile.json" in flat, (
        "LICENSE_NOTES no longer names the one genuinely synthetic fixture"
    )
    assert "hand-authored" in flat.lower(), (
        "LICENSE_NOTES no longer says what the fixtures directory actually is"
    )


def test_adr_002_records_that_its_synthetic_claim_was_later_corrected():
    """THE PRICE OF THE FROZEN-RECORD EXCLUSION ABOVE.

    ADR-002's Decision section still reads "`data/fixtures/` contains only
    hand-authored synthetic fixtures for tests, labelled as synthetic", and it
    must: an ADR records a decision as it was made, and its own banner says the
    body is left exactly as written.

    So the correction goes in the AMENDMENT BANNER, in the same shape the banner
    already uses for ADR-006's dissolution of the copyleft objection. Without
    it, the exclusion in `_FROZEN_RECORD_PREFIX` would be a licence for a false
    compliance claim to sit unmarked in a document readers are sent to.

    The banner must precede the body - a correction a reader meets AFTER the
    claim has already been read is not a correction.

    BANNER AND BODY ARE SPLIT BEFORE ANYTHING IS ASSERTED, and that is not
    tidiness. A correction note QUOTES the sentence it corrects, so a check for
    the false sentence over the whole file would be satisfied by the banner's
    own quotation of it - and the body-preservation arm would then pass over a
    body that had been rewritten away entirely. That is the failure this tree
    has already paid for once: an expectation living inside the same structure
    it checks, one edit from vacuous.
    """
    raw = (REPO_ROOT / "docs" / "adr" / "ADR-002-data-posture.md").read_bytes().decode("utf-8")
    marker = "## Context"
    assert marker in raw, "ADR-002 has no Context heading to split banner from body"
    banner = _flatten(raw[: raw.index(marker)])
    body = _flatten(raw[raw.index(marker) :])

    assert "contains only hand-authored synthetic" in body, (
        "ADR-002's BODY was rewritten. It must not be: an ADR records a decision "
        "as it was made, and this one says so in terms. The correction belongs in "
        "the amendment banner"
    )

    lowered = banner.lower()
    assert "synthetic" in lowered, (
        "the synthetic correction is not in ADR-002's amendment banner. A reader "
        "meets the Decision section's false claim before any note that follows it"
    )
    assert "hand-authored" in lowered, (
        "ADR-002's banner does not say what the fixtures actually are"
    )
    assert "enka_sample_profile.json" in banner, (
        "ADR-002's banner does not name the one fixture that IS synthetic, so it "
        "reads as a blanket retraction of a claim that is true of one file"
    )
    assert "_hand_authored" in banner, (
        "ADR-002's banner does not record the corrected machine-readable labelling"
    )
    assert "data/fixtures/README.md" in banner, (
        "ADR-002's banner does not point at the file carrying the corrected labels"
    )
    assert "ADR-006" in banner, (
        "ADR-002's banner lost the ADR-006 amendment note. This correction is a "
        "SECOND, separate note and must not have replaced the first"
    )
