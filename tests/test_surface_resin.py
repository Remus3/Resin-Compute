"""The Resin panel must project a recorded observation forward to `now`.

WHAT THIS FILE EXISTS TO PIN. The panel used to read a static ledger balance and
render it as the current resin, ignoring the `now` it was handed. The same
account rendered identically at +0h, +4h and +12h while `core.resin.resin_at`
answered 20, 50 and 110 for the same inputs. That is not a stale number, it is a
WRONG one: resin regenerates on a wall clock whether anything reads it or not.

AND THE HONESTY CONSTRAINT THAT COMES WITH THE FIX, from ADR-005. A projection
is an ESTIMATE. The instant the operator spends resin the projection is high and
the panel cannot know, so a projected number must never present itself as a
measurement. Every assertion about a number here is paired with an assertion
that the panel said where the number came from and how old the reading behind it
is.

NOTHING IS HARDCODED. The expected resin values are obtained by CALLING
`core.resin.resin_at`, the cap and the regeneration interval come from
`core.resin`, and the staleness threshold comes from `surface.model.STALE_AFTER`.
A retyped constant would make an arm agree with itself rather than with the
module under test.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core import resin
from core.ledger import record
from core.types import AccountState, CurrencyKind
from surface.model import STALE_AFTER, Panel, PanelState, _humanise, build_dashboard

#: One regeneration tick, derived rather than typed, so a change to the
#: interval moves these tests with the module instead of against it.
TICK = timedelta(minutes=resin.RESIN_REGEN_MINUTES)

T0 = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def observed_account(balance: int, at: datetime | None = T0) -> AccountState:
    """An account whose ledger holds `balance` resin, observed at `at`.

    `at` is both the ledger entry's timestamp and `last_synced_at`, because the
    panel treats the sync moment as the moment the balance was seen.
    """
    state = AccountState(uid="000000000")
    record(state.ledger, CurrencyKind.ORIGINAL_RESIN, balance, "observed", "sync", at or T0)
    state.last_synced_at = at
    return state


def resin_panel(state: AccountState, now: datetime) -> Panel:
    return build_dashboard(state, now=now).panel("resin")


def value_row(panel: Panel) -> tuple[str, str]:
    """The one row that answers 'how much resin'. Its LABEL is load-bearing.

    Exactly one row label starts with "Resin" - "Regenerates" and "Daily budget"
    do not - so this both locates the value and hands the label back for the
    provenance assertions.
    """
    matches = [(label, value) for label, value in panel.rows if label.startswith("Resin")]
    assert len(matches) == 1, f"expected one resin value row, got {matches}"
    return matches[0]


def presented_number(panel: Panel) -> int | None:
    """The integer the panel presents as current resin, or None if it presents none."""
    _, value = value_row(panel)
    head = value.split("/")[0].strip()
    return int(head) if head.isdigit() else None


def row(panel: Panel, label: str) -> str | None:
    for key, value in panel.rows:
        if key == label:
            return value
    return None


# ---------------------------------------------------------------------------
# 1. The regression arm. This is the one that fails against the old panel.
# ---------------------------------------------------------------------------


def test_the_presented_resin_moves_as_the_clock_moves():
    """Same account, three clocks, three different numbers.

    The defect was that this produced the same number three times. Nothing here
    asserts WHICH numbers - that is the next test's job - only that the panel is
    a function of `now` at all.
    """
    state = observed_account(20)
    seen = [presented_number(resin_panel(state, T0 + TICK * k)) for k in (0, 15, 30)]
    assert None not in seen, f"the panel refused to present a number: {seen}"
    assert len(set(seen)) == 3, f"the panel ignored the clock: {seen}"
    assert seen == sorted(seen), f"resin went backwards as time advanced: {seen}"


# ---------------------------------------------------------------------------
# 2. It agrees with core.resin.resin_at, derived by calling it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticks", [1, 5, 30, 100])
def test_the_projection_is_exactly_what_resin_at_returns(ticks: int):
    observed = 20
    state = observed_account(observed)
    now = T0 + TICK * ticks
    expected = resin.resin_at(observed, T0, now)
    assert presented_number(resin_panel(state, now)) == expected


def test_the_projection_agrees_with_resin_at_for_a_stale_reading_too():
    """Four hours out is past STALE_AFTER, and the arithmetic is still the arithmetic."""
    observed = 20
    state = observed_account(observed)
    now = T0 + timedelta(hours=4)
    assert now - T0 > STALE_AFTER
    assert presented_number(resin_panel(state, now)) == resin.resin_at(observed, T0, now)


# ---------------------------------------------------------------------------
# 3. The cap. Regeneration stops at it and the panel says so.
# ---------------------------------------------------------------------------


def test_the_projection_clamps_at_the_cap_and_reads_as_already_at_cap():
    observed = resin.ORIGINAL_RESIN_CAP - 1
    state = observed_account(observed)
    # Five ticks would put an unclamped projection four above the cap.
    now = T0 + TICK * 5
    assert now - T0 <= STALE_AFTER, "this arm is about the cap, not about staleness"
    panel = resin_panel(state, now)
    assert presented_number(panel) == resin.ORIGINAL_RESIN_CAP
    assert presented_number(panel) == resin.resin_at(observed, T0, now)
    assert row(panel, "Time to cap") == "already at cap"


def test_an_above_cap_overflow_balance_is_not_clipped_down():
    """Fragile Resin pushes past the cap legally, and core/resin.py refuses to clip it.

    A panel that rendered `min(200, balance)` would destroy a real balance the
    operator paid for. The projection stands still instead, which is exactly what
    `resin_at` does with an above-cap input.
    """
    observed = resin.ORIGINAL_RESIN_CAP + 60
    state = observed_account(observed)
    now = T0 + TICK * 3
    panel = resin_panel(state, now)
    assert presented_number(panel) == observed
    assert row(panel, "Time to cap") == "already at cap"


# ---------------------------------------------------------------------------
# 4. Degraded inputs. Never project backwards, never invent an observation.
# ---------------------------------------------------------------------------


def test_a_never_synced_account_claims_no_balance_at_all():
    """No observation, so no number - not a zero dressed up as a measurement."""
    state = AccountState(uid="000000000")
    panel = resin_panel(state, T0)
    assert presented_number(panel) is None
    assert panel.rows, "the regeneration rules are true of every account and are worth saying"
    _, value = value_row(panel)
    assert "0" not in value


def test_a_balance_with_no_observation_time_is_not_projected():
    """The ledger knows the number and nothing knows when it was seen.

    Projecting from an undated reading would be inventing the elapsed time.
    """
    state = observed_account(20, at=None)
    state.last_synced_at = None
    panel = resin_panel(state, T0 + timedelta(hours=6))
    assert panel.state is not PanelState.READY
    assert panel.waiting_on
    assert presented_number(panel) is None


def test_an_observation_stamped_in_the_future_is_not_projected_backwards():
    """One of the two clocks is wrong and the panel must not pick a number anyway."""
    ahead = T0 + timedelta(hours=5)
    state = observed_account(20, at=ahead)
    panel = resin_panel(state, T0)
    assert panel.state is not PanelState.READY
    assert panel.waiting_on
    assert presented_number(panel) is None


def test_a_naive_observation_time_does_not_raise():
    """A hand-edited state file can carry either kind, and mixing them raises.

    `build_dashboard` swallows a builder exception into a PARTIAL panel, so the
    real assertion is that the panel came back READY with the right number - a
    degraded card here would be the crash, hidden.
    """
    naive_t0 = datetime(2026, 9, 6, 12, 0)
    state = observed_account(20, at=naive_t0)
    now = T0 + TICK * 5
    panel = resin_panel(state, now)
    assert panel.state is PanelState.READY
    assert presented_number(panel) == resin.resin_at(20, naive_t0, now)


def test_a_naive_now_does_not_raise_against_an_aware_observation():
    state = observed_account(20, at=T0)
    naive_now = datetime(2026, 9, 6, 12, 40)
    panel = resin_panel(state, naive_now)
    assert panel.state is PanelState.READY
    assert presented_number(panel) == resin.resin_at(20, T0, naive_now)


# ---------------------------------------------------------------------------
# 5. Provenance and staleness. A reader can tell an estimate from a measurement.
# ---------------------------------------------------------------------------


def test_a_projected_number_says_it_is_projected_and_shows_what_was_observed():
    state = observed_account(20)
    now = T0 + TICK * 5
    assert now - T0 <= STALE_AFTER, "a fresh reading is still a projection"
    panel = resin_panel(state, now)
    label, _ = value_row(panel)
    assert "projected" in label.lower()
    observed_row = row(panel, "Observed")
    assert observed_row is not None
    assert "20" in observed_row


def test_the_age_of_the_observation_is_on_the_panel():
    state = observed_account(20)
    panel = resin_panel(state, T0 + timedelta(hours=3, minutes=12))
    age = row(panel, "Observation age")
    assert age is not None
    assert "3h" in age


def test_a_stale_reading_is_partial_and_names_the_limitation():
    state = observed_account(20)
    now = T0 + timedelta(hours=4)
    assert now - T0 > STALE_AFTER
    panel = resin_panel(state, now)
    assert panel.state is PanelState.PARTIAL
    assert "upper bound" in panel.waiting_on.lower()
    assert "upper bound" in value_row(panel)[0].lower()


def test_a_fresh_reading_is_ready_and_claims_no_upper_bound():
    """The non-vacuity arm for the staleness detector.

    Without this, the test above would pass against a panel that called every
    reading stale - which would be a different lie in the same place.
    """
    state = observed_account(20)
    now = T0 + TICK
    assert now - T0 <= STALE_AFTER
    panel = resin_panel(state, now)
    assert panel.state is PanelState.READY
    assert "upper bound" not in value_row(panel)[0].lower()


def test_a_reading_older_than_a_full_refill_presents_no_number():
    """Past saturation the projection stops being about this account.

    `resin_at` would answer the cap for an observation of 10 and for one of 190
    alike, so the number would be a function of the constants and of nothing the
    operator did. Printing it would read as a measurement of a capped account.
    """
    observed = 10
    refill = resin.time_to_reach(observed, resin.ORIGINAL_RESIN_CAP)
    assert refill is not None
    state = observed_account(observed)
    now = T0 + refill + timedelta(hours=1)
    panel = resin_panel(state, now)
    assert panel.state is PanelState.PARTIAL
    assert presented_number(panel) is None
    assert panel.waiting_on
    observed_row = row(panel, "Observed")
    assert observed_row is not None and str(observed) in observed_row


def test_just_short_of_a_full_refill_still_presents_the_upper_bound():
    """Non-vacuity for the saturation cutoff above."""
    observed = 10
    refill = resin.time_to_reach(observed, resin.ORIGINAL_RESIN_CAP)
    assert refill is not None
    state = observed_account(observed)
    now = T0 + refill - timedelta(hours=1)
    panel = resin_panel(state, now)
    presented = presented_number(panel)
    assert presented == resin.resin_at(observed, T0, now)
    assert presented is not None and presented < resin.ORIGINAL_RESIN_CAP


# ---------------------------------------------------------------------------
# 6. The control. Without it arm 1 would pass against a panel adding a constant.
# ---------------------------------------------------------------------------


def test_at_the_observation_moment_the_panel_shows_the_observed_value_unchanged():
    observed = 73
    state = observed_account(observed)
    panel = resin_panel(state, T0)
    assert panel.state is PanelState.READY
    assert presented_number(panel) == observed
    assert "projected" not in value_row(panel)[0].lower()
    assert "observed" in value_row(panel)[0].lower()


def test_the_regeneration_rules_are_stated_on_every_variant():
    """They are constants, true of every account, and they never go missing."""
    for state, now in (
        (AccountState(uid="000000000"), T0),
        (observed_account(20), T0),
        (observed_account(20), T0 + timedelta(hours=4)),
        (observed_account(20), T0 + timedelta(days=3)),
    ):
        panel = resin_panel(state, now)
        assert row(panel, "Regenerates") == f"1 per {resin.RESIN_REGEN_MINUTES} minutes"
        assert row(panel, "Daily budget") == str(resin.daily_resin_budget())


# ---------------------------------------------------------------------------
# 7. Saturation is one branch with THREE honest readings, and the value cell
#    that announces it is a cell, not a paragraph.
# ---------------------------------------------------------------------------
#
# WHY THIS SECTION EXISTS. Band 6b fires the instant the reading is stale AND
# the refill span has elapsed. For an observation AT the cap that span is
# `timedelta(0)`, so the branch fires with NO refill having happened at all,
# and the panel said the reading was "longer than a full refill from that
# balance" - longer than zero, which is true of every reading and says nothing.
# The operator's real board reads 200 / 200, so this was not a corner case, it
# was the case. An above-cap overflow balance reached the same sentence by the
# same route. Three balances, three different true things to say, and the
# DECISION to withhold the projected number is correct in all three and is
# pinned unchanged below.
#
# The second defect is presentational and was measured in Chromium: the reason
# was rendered into a right-aligned `dd`, where it wrapped to four lines at
# 360px and five at 620px with a ragged left edge. The value cell carries a
# short value; the prose lives in `waiting_on`, which is left-aligned and
# already exists.

#: Comfortably past the refill span for any balance, so the saturation branch
#: is what is under test rather than the boundary into it.
SATURATED_AFTER = timedelta(days=2)


def saturated_panel(observed: int) -> Panel:
    """A band-6b panel: past STALE_AFTER and past the refill span for `observed`.

    The refill span is obtained by CALLING `resin.time_to_reach`, so an
    observation at or above the cap gets the `timedelta(0)` the module really
    returns rather than a span this file assumed.
    """
    refill = resin.time_to_reach(observed, resin.ORIGINAL_RESIN_CAP)
    assert refill is not None
    now = T0 + refill + SATURATED_AFTER
    assert now - T0 > STALE_AFTER
    panel = resin_panel(observed_account(observed), now)
    assert panel.state is PanelState.PARTIAL, "this helper is about band 6b"
    return panel


def explanation(panel: Panel) -> str:
    """Everything the panel says about WHY it withholds a number, lowercased.

    Deliberately spans BOTH the value cell and `waiting_on`. An arm that read
    only one of the two could be satisfied by moving a false sentence from one
    to the other instead of by correcting it.
    """
    return f"{value_row(panel)[1]} {panel.waiting_on}".lower()


def test_a_saturated_reading_at_the_cap_does_not_claim_a_refill_span_elapsed():
    """`time_to_reach(CAP, CAP)` is zero, so no refill span elapsed. Say that.

    Paired assertions: the false claim is absent AND a true one is present. An
    arm that only checked for an absence would pass against an empty string.
    """
    panel = saturated_panel(resin.ORIGINAL_RESIN_CAP)
    text = explanation(panel)
    assert "full refill" not in text, f"claimed a refill span that never elapsed: {text!r}"
    assert "already at the cap" in text, f"no true reason given for withholding: {text!r}"


def test_a_saturated_reading_above_the_cap_names_the_overflow_and_implies_no_clamp():
    """Fragile Resin overflow is legal per core/resin.py and regeneration never adds to it."""
    observed = resin.ORIGINAL_RESIN_CAP + 60
    panel = saturated_panel(observed)
    text = explanation(panel)
    assert "full refill" not in text, f"claimed a refill span that never elapsed: {text!r}"
    assert "above the cap" in text, f"no true reason given for withholding: {text!r}"
    observed_row = row(panel, "Observed")
    assert observed_row is not None
    assert str(observed) in observed_row, f"the overflow balance went missing: {observed_row!r}"
    clamped = f"{resin.ORIGINAL_RESIN_CAP} / {resin.ORIGINAL_RESIN_CAP}"
    assert clamped not in observed_row, f"the row reads as clamped to the cap: {observed_row!r}"


def test_a_saturated_reading_below_the_cap_still_names_the_refill_span():
    """The control. A real refill span DID elapse here and the true sentence must survive.

    Without this arm the two above could be satisfied by deleting the refill
    wording outright, which would fix a false statement by removing a true one.
    """
    panel = saturated_panel(10)
    text = explanation(panel)
    assert "full refill" in text, f"the true refill-span reason was deleted: {text!r}"


def test_the_saturated_value_cell_is_short_and_loses_no_information():
    """The `dd` is right-aligned, so a sentence in it wraps with a ragged left edge.

    The bound is on the VALUE cell only. Everything the long form said is still
    reachable, which is what the second half asserts: the age, and the reason.
    """
    observed = 10
    refill = resin.time_to_reach(observed, resin.ORIGINAL_RESIN_CAP)
    assert refill is not None
    now = T0 + refill + SATURATED_AFTER
    panel = resin_panel(observed_account(observed), now)
    _, value = value_row(panel)
    assert len(value) <= 24, f"the value cell is a paragraph, not a value: {value!r}"
    assert "." not in value and "," not in value, f"sentence punctuation in a value cell: {value!r}"
    assert _humanise(now - T0) in panel.waiting_on, f"the reading age was lost: {panel.waiting_on!r}"
    assert "full refill" in panel.waiting_on.lower(), f"the reason was lost: {panel.waiting_on!r}"


@pytest.mark.parametrize(
    "observed",
    [10, resin.ORIGINAL_RESIN_CAP, resin.ORIGINAL_RESIN_CAP + 60],
)
def test_saturation_still_withholds_the_number_whatever_the_balance(observed: int):
    """The DECISION is unchanged by the wording fix. Only the explanation differs."""
    panel = saturated_panel(observed)
    assert panel.state is PanelState.PARTIAL
    assert presented_number(panel) is None
    _, value = value_row(panel)
    assert not any(ch.isdigit() for ch in value), f"a present-tense number came back: {value!r}"
    assert panel.waiting_on
    observed_row = row(panel, "Observed")
    assert observed_row is not None and str(observed) in observed_row


# ---------------------------------------------------------------------------
# House rules
# ---------------------------------------------------------------------------


def test_no_panel_variant_emits_a_non_ascii_character():
    for state, now in (
        (AccountState(uid="000000000"), T0),
        (observed_account(20), T0),
        (observed_account(20), T0 + timedelta(hours=4)),
        (observed_account(20), T0 + timedelta(days=3)),
        (observed_account(20, at=T0 + timedelta(hours=5)), T0),
    ):
        panel = resin_panel(state, now)
        blob = "".join(f"{a}{b}" for a, b in panel.rows) + panel.waiting_on + panel.note
        assert blob.isascii(), f"non-ascii in the resin panel: {blob!r}"
