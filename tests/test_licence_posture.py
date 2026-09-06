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
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

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


def test_no_file_still_claims_the_project_is_unlicensed():
    """The pre-ADR-006 wording, swept for so it cannot survive in a corner."""
    stale = ["Private. No licence granted", "UNLICENSED"]
    offenders: list[str] = []
    for path in list(REPO_ROOT.glob("*.md")) + [REPO_ROOT / "shell" / "package.json"]:
        text = path.read_text(encoding="utf-8")
        for phrase in stale:
            if phrase in text:
                offenders.append(f"{path.name} still says {phrase!r}")
    assert not offenders, "; ".join(offenders)


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
    oversized = [
        f"{p.relative_to(REPO_ROOT).as_posix()} ({p.stat().st_size} bytes)"
        for p in (REPO_ROOT / "data").rglob("*")
        if p.is_file() and p.stat().st_size > limit
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
    data_files = [p for p in (REPO_ROOT / "data").rglob("*") if p.is_file()]
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
    for path in sorted((REPO_ROOT / "data").rglob("*.json")):
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
    scanned = sorted(p.name for p in (REPO_ROOT / "data").rglob("*.json"))
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
