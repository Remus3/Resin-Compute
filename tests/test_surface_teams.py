"""The Teams panel - elemental IDENTITY over the roster, and nothing that ranks.

WHERE THE LINE IS, which is the whole point of this file. ROADMAP's `## Later`
holds the TEAM COMPOSITION SOLVER, and the reason it gives is that elemental
REACTION MODELLING is a large piece of domain work that should not start before
the resource layer is complete. Elemental IDENTITY is a different thing and is
already in this tree, licence-clean: the five verified avatarIds in
`data/fixtures/seed_roster.json` each carry an element, and
`ingest.static_data.element_for` is the shipped lookup over them.

So the panel is allowed to answer "who is here, what element are they, and which
of the verified five are missing". It is not allowed to answer "which of them is
a good team". Every arm below exists to hold that line: nothing scores, nothing
ranks, nothing recommends, and `waiting_on` keeps naming the held reaction work
so that a later session cannot quietly promote this panel to READY without
deleting an assertion on purpose.

TWO ARMS ARE ABOUT THE TESTS RATHER THAN THE PANEL.
`test_the_cost_word_detector_actually_fires` proves the absence-of-cost sweep can
fail at all - an absence assertion whose detector is broken passes against
anything. And `test_two_different_rosters_produce_different_rows` is the control:
without it every other arm here would still pass against a panel that ignored its
input entirely and returned one fixed block of text.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from core.types import AccountState, Element, MappedCharacter
from ingest.static_data import (
    FIXTURES_DIR,
    ROSTER_FILE,
    character_name,
    element_for,
    known_avatar_ids,
)
from surface.model import Panel, PanelState, build_dashboard

NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)


def account(**kwargs) -> AccountState:
    state = AccountState(uid="000000000")
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state


def _fixture_characters() -> dict[int, dict]:
    """The seed table read as raw JSON, NOT through the API under test.

    Arm 2 needs an expectation the panel did not supply. Calling `element_for`
    for both the expected and the actual value would let the arm agree with
    itself no matter what the fixture said, so the expectation is parsed out of
    the file and the shipped lookup is then checked AGAINST it.
    """
    raw = json.loads((FIXTURES_DIR / ROSTER_FILE).read_text(encoding="utf-8"))
    return {int(entry["avatar_id"]): entry for entry in raw["characters"]}


def _teams(state: AccountState) -> Panel:
    return build_dashboard(state, now=NOW).panel("teams")


def _blob(panel: Panel) -> str:
    return " | ".join(f"{label} {value}" for label, value in panel.rows).lower()


#: Words that would mean a cost figure had reached this panel.
#: docs/GOAL_SPEC_SEED_TEAM.md section 3 stamps the roadmap's cost figures
#: UNVERIFIED and forbids them entering a calculation; a UI row is the last
#: place one of them should be allowed to surface as though it were known.
_COST_WORDS = ("mora", "material", "cost", "resin", "primogem", "ascension", "xp")


def _cost_mentions(rows: tuple[tuple[str, str], ...]) -> list[str]:
    hits: list[str] = []
    for label, value in rows:
        text = f"{label} {value}".lower()
        hits.extend(word for word in _COST_WORDS if word in text)
    return hits


def _known_roster(count: int = 3) -> tuple[MappedCharacter, ...]:
    ids = sorted(_fixture_characters())[:count]
    return tuple(
        MappedCharacter(avatar_id=avatar_id, level=80, ascension=5, constellations=0) for avatar_id in ids
    )


# ---------------------------------------------------------------------------
# 1. Empty is an absence of a reading, not an absence of characters
# ---------------------------------------------------------------------------


def test_an_empty_roster_is_not_wired_and_says_what_it_waits_on():
    """Same reasoning as the Roster panel, and it is upstream's, not ours.

    Enka omits `avatarInfoList` entirely when the in-game showcase is closed, so
    an empty roster overwhelmingly means "we were not shown one" rather than
    "this account owns nobody". Rendering an element distribution over zero
    characters would be a confident statement about an account nobody looked at.
    """
    panel = _teams(account())
    assert panel.state is PanelState.NOT_WIRED
    assert panel.waiting_on
    assert panel.rows == ()


# ---------------------------------------------------------------------------
# 2. Elements come from the seed table, never from a literal typed here
# ---------------------------------------------------------------------------


def test_each_roster_element_is_the_one_the_seed_table_records():
    fixture = _fixture_characters()
    roster = _known_roster()
    panel = _teams(account(roster=roster))

    by_label = dict(panel.rows)
    for character in roster:
        entry = fixture[character.avatar_id]
        expected = entry["element"]
        assert by_label[entry["name"]] == expected, f"{entry['name']} row disagrees with the seed table"
        resolved = element_for(character.avatar_id)
        assert resolved is not None
        assert resolved.value == expected, "element_for drifted from the fixture it reads"


def test_the_panel_counts_the_elements_it_found():
    fixture = _fixture_characters()
    roster = _known_roster()
    panel = _teams(account(roster=roster))

    pyro_expected = sum(1 for c in roster if fixture[c.avatar_id]["element"] == Element.PYRO.value)
    assert pyro_expected >= 2, "the seed table stopped supporting this arm - re-derive it"
    assert f"{Element.PYRO.value} x{pyro_expected}" in _blob(panel)


def test_the_panel_names_the_verified_seed_characters_that_are_absent():
    roster = _known_roster(count=2)
    present = {c.avatar_id for c in roster}
    missing = [character_name(a) for a in known_avatar_ids() if a not in present]
    assert missing, "this arm needs at least one absent seed character"
    blob = _blob(_teams(account(roster=roster)))
    for name in missing:
        assert name.lower() in blob


# ---------------------------------------------------------------------------
# 3. An unknown id must degrade honestly and must never be guessed at
# ---------------------------------------------------------------------------


def test_a_character_outside_the_seed_set_gets_no_invented_element():
    """The arm that stops a later session guessing.

    The id is DERIVED rather than typed, so it cannot quietly become a verified
    id later and turn this arm green for the wrong reason. The character is also
    handed a FABRICATED `element` field: in production `ingest/enka_mapper.py`
    fills that field from `element_for` itself, so a panel reading it back would
    be consulting a second source of truth that a hand-built object can poison.
    The panel must ignore it.
    """
    unknown_id = max(known_avatar_ids()) + 1000
    assert element_for(unknown_id) is None, "the derived id is no longer outside the seed set"

    state = account(
        roster=(
            MappedCharacter(
                avatar_id=unknown_id,
                level=90,
                ascension=6,
                constellations=0,
                element=Element.HYDRO,
            ),
        )
    )
    panel = _teams(state)
    blob = _blob(panel)
    for element in Element:
        assert element.value not in blob, f"the panel invented {element.value} for an unverified id"
    assert "verified seed set" in blob


# ---------------------------------------------------------------------------
# 4. The fence - waiting_on keeps naming the held work
# ---------------------------------------------------------------------------


def test_the_panel_still_names_the_held_reaction_work():
    for roster in (_known_roster(), _known_roster(count=1)):
        panel = _teams(account(roster=roster))
        assert panel.state is not PanelState.READY, "reaction modelling is held - this cannot be READY"
        assert panel.waiting_on
        assert "reaction" in panel.waiting_on.lower()


def test_the_panel_does_not_rank_score_or_recommend():
    panel = _teams(account(roster=_known_roster(count=5)))
    blob = _blob(panel)
    for word in ("best", "recommend", "score", "rank", "tier", "synergy", "strongest"):
        assert word not in blob, f"the panel crossed into held work with {word!r}"


# ---------------------------------------------------------------------------
# 5. No cost figure reaches a row - and the detector that says so can fail
# ---------------------------------------------------------------------------


def test_no_cost_figure_reaches_any_row():
    panel = _teams(account(roster=_known_roster(count=5)))
    assert _cost_mentions(panel.rows) == []


def test_the_cost_word_detector_actually_fires():
    """Non-vacuity. Without this the arm above passes against a broken sweep."""
    planted = (("Mora needed", "1 200 000"), ("Talent material", "12"))
    assert sorted(set(_cost_mentions(planted))) == ["material", "mora"]


# ---------------------------------------------------------------------------
# 6. The control - the panel actually reads its input
# ---------------------------------------------------------------------------


def test_two_different_rosters_produce_different_rows():
    first = _teams(account(roster=_known_roster(count=2)))
    second = _teams(account(roster=_known_roster(count=5)))
    assert first.rows != second.rows
    assert first.state is second.state is PanelState.PARTIAL
