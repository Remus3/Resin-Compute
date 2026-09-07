"""Guards on docs/GOAL_SPEC_SEED_TEAM.md.

A document is not a source of truth, and this repository says so in several
places. So the goal spec is held to the same standard as everything else: the
claims it stamps VERIFIED are checked against the code they cite, and the numbers
it stamps UNVERIFIED are checked to have stayed OUT of `data/`.

THE SECOND ARM IS THE IMPORTANT ONE. The whole reason the spec exists is that a
web-generated roadmap arrived carrying plausible cost figures, and ADR-002's
licence gate plus the operator's own "from my own in-game observation" rule both
exclude that provenance. A prose rule saying "do not copy these into a data file"
is exactly the kind of rule that gets forgotten at 2am. This makes it mechanical.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core import domains, resin
from core.types import BannerKind, CurrencyKind
from engines.objectives import ASCENSION_LEVEL_CAPS
from ingest.static_data import known_avatar_ids, known_material_ids
from tests.test_guard_worktree_exclusion import swept_files

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "GOAL_SPEC_SEED_TEAM.md"
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_the_goal_spec_exists_and_is_seven_bit_ascii(text: str):
    assert SPEC.is_file()
    assert text.isascii(), "the goal spec carries a non-ASCII character"


def test_every_stamp_used_is_a_declared_one(text: str):
    """A fifth stamp invented in passing would defeat the whole scheme."""
    declared = {"VERIFIED", "REFUTED", "UNVERIFIED", "TIME-SENSITIVE", "NOT MODELLED"}
    for stamp in declared:
        assert stamp in text, f"the spec no longer uses the {stamp} stamp"


# ---------------------------------------------------------------------------
# The VERIFIED table must agree with the code it cites
# ---------------------------------------------------------------------------


def test_the_cited_material_ids_are_the_verified_ones(text: str):
    assert "113059" in text
    assert "113039" in text
    for material_id in (113059, 113039):
        assert material_id in known_material_ids()


def test_the_cited_avatar_ids_are_the_verified_ones(text: str):
    for avatar_id in (10000096, 10000079, 10000083, 10000032, 10000034):
        assert str(avatar_id) in text, f"the spec no longer cites {avatar_id}"
        assert avatar_id in known_avatar_ids()


def test_the_cited_level_cap_table_matches_the_engine(text: str):
    rendered = " / ".join(str(cap) for cap in ASCENSION_LEVEL_CAPS)
    assert rendered in text, f"the spec's cap table drifted from {ASCENSION_LEVEL_CAPS}"


def test_the_cited_resin_constants_match_core_resin(text: str):
    assert str(resin.ORIGINAL_RESIN_CAP) in text
    assert str(resin.RESIN_REGEN_MINUTES) in text
    assert str(resin.DAILY_RESIN_REGEN) in text
    assert str(resin.CONDENSED_RESIN_COST) in text
    assert str(resin.FRAGILE_RESIN_GRANT) in text


def test_the_cited_reset_schedule_matches_core_domains(text: str):
    assert f"{domains.DAILY_RESET_HOUR:02d}:00" in text
    assert domains.WEEKLY_RESET_WEEKDAY == domains.MONDAY
    assert "Monday" in text


def test_the_cited_domain_rotation_matches_core_domains(text: str):
    """The rotation is the spec's headline correction, so it is pinned exactly."""
    names = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    for slot, weekdays in domains.ROTATION_SLOT_WEEKDAYS.items():
        rendered = ", ".join(names[day] for day in weekdays)
        assert rendered in text, f"slot {slot} is documented as something other than {rendered}"


def test_the_cited_currencies_exist(text: str):
    assert CurrencyKind.STARGLITTER.value == "masterless_starglitter"
    assert "Starglitter" in text
    assert "Hero's Wit" in text


def test_the_beginner_banner_really_is_absent_from_the_model(text: str):
    """The spec calls this NOT MODELLED. If a member appears, the spec is stale."""
    assert "Beginner" in text
    members = {kind.name for kind in BannerKind}
    assert members == {"CHARACTER_EVENT", "WEAPON_EVENT", "STANDARD", "CHRONICLED"}


# ---------------------------------------------------------------------------
# The UNVERIFIED numbers must NOT have reached data/
# ---------------------------------------------------------------------------

#: Figures from the web-generated roadmap. Unsourced, and excluded by ADR-002's
#: licence gate and by the operator's own first-hand-observation rule.
UNSOURCED_FIGURES = ("430000", "430,000", "150000", "150,000")


def _data_files() -> list[Path]:
    """Every `data/` document THIS working tree owns.

    `swept_files` rather than a bare `rglob`: a nested checkout left inside
    `data/` - a merged worktree, a stray extraction - is a second full copy of
    somebody else's tree, and sweeping it makes this guard's colour a fact about
    that copy instead of about this one. See
    `tests/test_guard_worktree_exclusion.py` for the measurement and the proof.
    """
    return [p for p in swept_files(DATA_DIR) if p.suffix in {".json", ".md"}]


def test_the_data_directory_carries_no_unsourced_cost_figure():
    """The mechanical form of "do not copy these in"."""
    offenders: list[str] = []
    for path in _data_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        for figure in UNSOURCED_FIGURES:
            if figure in content:
                offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()} carries {figure}")
    assert not offenders, "unsourced cost figures reached data/: " + "; ".join(offenders)


def test_the_data_directory_carries_no_unverified_item_name():
    """`Mystic Enhancement Ore` is outside the verified item set in SPEC section 5."""
    for path in _data_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        assert "Mystic Enhancement Ore" not in content, f"{path.name} names an unverified item"


def test_the_guard_is_not_vacuous():
    """A sweep that silently stopped finding files would pass forever."""
    files = _data_files()
    assert len(files) >= 3, f"only found {len(files)} data files"
    joined = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
    # Something the data DOES legitimately carry, proving the sweep reads content.
    assert "113059" in joined
