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
