"""Arms that DRIVE the delivery and bounce write-verdict gates in `_run_once`.

WHY THIS FILE EXISTS SEPARATELY FROM `tests/test_moon_sync_responder.py`.

The 2026-09-09 mutation campaign ran `tools/gate_mutation_runner.py` over the
tagged gates in `tools/moon_sync_responder.py` and reported five SURVIVORS in
this half of the cycle:

    delivery-write-all/operand-1   delivery-write-all/operand-2
    bounce-write-all/operand-1     bounce-write-all/operand-2
    bounce-mark/if-true

A survivor is not a gate that is wrong. Every one of these gates is CORRECT as
written. A survivor is a gate that NOTHING DRIVES - neutralise it and the whole
application suite stays green, so the suite's greenness says nothing at all
about it. That is the same class of hole this module's parent already records
at length: a predicate can be right, tested as a pure function, and never
consulted.

FIVE of the eight arms below are each written to turn exactly one of those five
mutants into a kill, and each says which one in its own docstring. The other
three name no mutant and are not meant to: one proves this file's own fixture
really isolates, and the two at the foot of the file prove the legitimate
neighbours survive. The proof is the runner, not the eye - an arm that merely
looks relevant is what let the survivors survive.

THE TWO SITES, QUOTED SO A LATER READER NEED NOT GO LOOKING.

    result["bounced"] = bool(sent) and all(ok for ok, _ in sent)
    if result["bounced"]:
        mark_bounced(...)

    result["delivered"] = all(ok for ok, _ in written) and bool(written)

The runner's mutants replace the whole BoolOp assignment with ONE of its
operands, and replace an `if` test with a constant. So each conjunct needs its
OWN arm: an arm that only ever sees both conjuncts agree cannot tell which one
is load-bearing, and a suite full of such arms is exactly what the campaign
measured.

THE STATED LIMIT OF THE TWO EMPTY-LIST ARMS, and it is a real one.

`deliver` returns exactly one row per inbox handed to it, and `_run_once`
reaches both of these sites only PAST the `GATE:no-destination` early return,
so `dests` is never empty by the time either runs. THE EMPTY LIST IS THEREFORE
NOT REACHABLE THROUGH REAL DESTINATIONS, and the two arms that need it
substitute the module's own `deliver` with a stub returning `[]`.

That substitution is the honest shape rather than a shortcut. The guard the
module's comment at `tools/moon_sync_responder.py:1861-1863` calls "the guard,
not decoration" exists for a CALLER SHAPE the current callers cannot produce -
`all([])` is vacuously True, so a delivery to zero destinations would report
itself delivered. A guard against a shape no current caller makes is exactly the
kind that rots quietly when a later caller starts making it, and the only way to
drive it today is to be that caller. The arm is therefore a statement about the
assignment, not about the reachability of an empty `dests`.

THE FAILED-ROW ARMS USE A REAL FAILURE, not a stub. A destination inbox path
that is an existing FILE makes `inbox.mkdir(parents=True, exist_ok=True)` raise
`FileExistsError`, which `deliver` absorbs into a `(False, target)` row by the
`except (OSError, ValueError)` at `tools/moon_sync_responder.py:1020` onward.
That is the module's own absorption path rather than a substitute for it.

EVERY ARM CARRIES ITS REACHABILITY FLOOR IN ITS OWN BODY. ALL FIVE of the five
close on a negative, not four of them - `delivered is False` twice, `bounced is
False` twice, and `bounced_under(...) is False` once - and a negative is equally
true of a cycle that never reached the site at all, so every one of the five
also records POSITIVE evidence that the module got there. Those floors are of
THREE kinds rather than one, and which kind an arm can use is forced by what
that arm had to substitute:

  * `len(attempts) == 1` from `_recording_deliver`, which wraps the module's own
    `deliver` so that reaching the call site leaves a trace. Used by the two
    failed-row BOUNCE arms.
  * `rc_inbox in handed[0]` - the destination list the module itself computed
    and handed to a substituted `deliver`. Used by the two zero-destination
    arms, which have no real call to record.
  * NEITHER, for `test_a_delivery_whose_only_write_failed_is_never_reported_as_delivered`.
    It substitutes nothing and records nothing, and its floor is
    `result["termination"] == "delivered"` alone. That is honest evidence only
    in the DELIVERY branch, where `termination` is assigned at
    `tools/moon_sync_responder.py:1867`, two lines past the gate's own
    assignment at 1865 and inside the same straight-line block as the write at
    1856. The refusal branch cannot borrow the trick: there `termination` is
    already set 60 lines upstream at line 1769, before the bounce block is
    entered at all, which is exactly why the bounce arms need
    `_recording_deliver` instead.

A floor parked in a separate sibling arm would leave the arm that needs it
vacuous, which is why none of them is written that way.

THE STATED LIMIT OF THE `rc_inbox in handed[0]` FLOOR, and it is a real one. It
is a MEMBERSHIP test and not an equality one, so it bounds the handed list from
BELOW only. Appending a further destination - including an inbox in a repository
this tree does not own - leaves both zero-destination arms GREEN. Those arms say
the right destination was AMONG those handed; they do not say it was the only
one, and nothing in this file pins the exact destination set.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_` path redirected into `tmp_path`.

    A DELIBERATE RE-DEFINITION rather than an import from the sibling test
    module, which would make two files share one fixture object and one import
    cycle. The shape is the sibling's and the reason is the sibling's: the
    defaults are DISCOVERED by enumerating the module, never listed by hand,
    because a hand-maintained list of things to isolate goes stale the moment
    someone adds the next one and it fails SILENTLY - the arm that would have
    caught it being the same list.

    For this module the stakes are not a polluted record. An escaped default
    here delivers a note into a sibling repository's inbox.
    """
    spec = importlib.util.spec_from_file_location("responder_delivery_gates_under_test", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def test_every_default_path_in_this_module_is_redirected(rsp, tmp_path):
    """The non-vacuity arm for this file's OWN fixture.

    Without it the five arms below would pass identically against a fixture
    that redirected nothing, and their writes would land in the operator's live
    state. Discovered rather than listed, for the reason the fixture gives.
    """
    defaults = [
        n for n in dir(rsp) if n.startswith("DEFAULT_") and isinstance(getattr(rsp, n), Path)
    ]

    assert len(defaults) >= 4, f"the discovery found almost nothing, so this arm is vacuous: {defaults}"
    for name in defaults:
        assert tmp_path in getattr(rsp, name).parents, (
            f"{name} escapes this test's own directory, so an arm below writes "
            "into live state - and for this module that can mean a note in a "
            "sibling repository's inbox"
        )


# ---------------------------------------------------------------------------
# Helpers. RE-DEFINED here rather than imported from the sibling test module,
# per the same reasoning as the fixture.
# ---------------------------------------------------------------------------


def _note(inbox: Path, name: str, body: str = "please measure your suite\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def _agree(rsp) -> None:
    """Record the counterparty's agreement, as the operator would.

    Called EXPLICITLY by every arm that drives an armed cycle rather than being
    written by the fixture. A fixture that pre-agreed would hide the
    precondition and make the arms pass whether or not the gate existed.
    """
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )


def _draft(rsp, body: str) -> str:
    """A draft that passes every rule, so an arm varies exactly one thing."""
    return rsp.RESPONDER_TAG + "\n\n" + body


NOTE_NAME = "2026-09-08-1900-from-RC-question.md"


def _bed(rsp, tmp_path):
    """An agreed, armed setup with one note and a REAL destination directory."""
    _agree(rsp)
    inbox = tmp_path / "inbox"
    _note(inbox, NOTE_NAME)
    rc_inbox = tmp_path / "rc" / "moon_sync_inbox"
    rc_inbox.mkdir(parents=True)
    return inbox, rc_inbox


def _bed_with_unwritable_destination(rsp, tmp_path):
    """The same bed, except the destination inbox path is an existing FILE.

    A REAL FAILURE AND NOT A STUB. `deliver` computes `target = inbox / name`,
    finds `target.exists()` False because nothing can exist under a regular
    file, then calls `inbox.mkdir(parents=True, exist_ok=True)`, which raises
    `FileExistsError` - `exist_ok` swallows that only for a path that IS a
    directory. `FileExistsError` is an `OSError`, so `deliver`'s own guard
    absorbs it into the `(False, target)` row the two gates then reduce.

    This is the module's real absorption path rather than a substitute for it,
    which is why the failed-row arms prefer it to a monkeypatched `deliver`.
    """
    _agree(rsp)
    inbox = tmp_path / "inbox"
    _note(inbox, NOTE_NAME)
    blocked = tmp_path / "rc" / "moon_sync_inbox"
    blocked.parent.mkdir(parents=True, exist_ok=True)
    blocked.write_bytes(b"a regular file sitting where the inbox directory would go\n")
    assert blocked.is_file() and not blocked.is_dir(), (
        "this bed only means anything if the destination is a FILE - a "
        "directory here makes every arm using it vacuous"
    )
    return inbox, blocked


def _recording_deliver(rsp) -> list[list[tuple[bool, Path]]]:
    """Wrap the module's OWN `deliver` so reaching the call site leaves a trace.

    NOT A STUB AND NOT A SUBSTITUTE. The real `deliver` still runs, still tries
    the real write, and still absorbs the real `FileExistsError` into its own
    `(False, target)` row; this records only THAT the module called it and WHAT
    its own absorption produced.

    WHY THE ARMS BELOW NEED IT, measured 2026-09-09 rather than argued.
    Neutralise `GATE:bounce-once` at `tools/moon_sync_responder.py:1829` to
    `if False:` so the bounce block executes zero times, and the two failed-
    bounce arms BOTH STAY GREEN on negatives alone: `result["termination"]` is
    already "refused" from `GATE:termination-kind` at line 1769, a full 60
    lines ABOVE the bounce block; the blocked destination is still a file because the
    bed made it one; and the ledger is still unmarked precisely BECAUSE nothing
    tried to mark it. `bounce_capacity` returning False at the
    `MAX_BOUNCED_NOTES` stop is a real future path to that same skip, so the
    hole is not hypothetical. A recorded call is the one piece of evidence a
    cycle that skipped the block cannot produce.
    """
    real = rsp.deliver
    attempts: list[list[tuple[bool, Path]]] = []

    def _recorded(*args, **kwargs):
        rows = real(*args, **kwargs)
        attempts.append(list(rows))
        return rows

    rsp.deliver = _recorded
    return attempts


def _armed_cycle(rsp, tmp_path, inbox, draft, now=20_000.0):
    """One armed cycle with the session replaced by a stub returning `draft`."""
    return rsp.run_once(
        inbox=inbox,
        roots={"RC": tmp_path / "rc"},
        bounds=rsp.Bounds(armed=True),
        spawn=lambda *a, **k: draft,
        now=now,
    )


# ---------------------------------------------------------------------------
# GATE:delivery-write-all
#
#   result["delivered"] = all(ok for ok, _ in written) and bool(written)
#
# Two conjuncts, two mutants, two arms. Neither arm can kill the other's
# mutant, which is the whole reason there are two.
# ---------------------------------------------------------------------------


def test_a_delivery_to_zero_destinations_is_never_reported_as_delivered(rsp, tmp_path):
    """KILLS `delivery-write-all/operand-1` - `all(ok for ok, _ in written)` alone.

    `all([])` is VACUOUSLY TRUE. Drop the `bool(written)` conjunct and a cycle
    that wrote to nowhere reports `delivered=True`, which is the strongest
    possible false claim this module can make: the metrics row and the return
    value both say a sibling received a reply that was never written anywhere.

    THE STATED LIMIT OF THIS ARM. `deliver` returns one row per inbox and this
    site sits past `GATE:no-destination`, so `written` cannot be empty through
    real destinations - the module's own comment calls the conjunct "the guard,
    not decoration" precisely because it guards a CALLER SHAPE the current
    callers cannot produce. So `deliver` is substituted with a stub returning
    `[]`. The claim this arm supports is therefore about the ASSIGNMENT and not
    about the reachability of an empty destination list, and it is written down
    here rather than left for a later reader to discover.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    handed: list[list[Path]] = []

    def _delivers_nowhere(text, name, inboxes, *a, **k):
        handed.append(list(inboxes))
        return []

    rsp.deliver = _delivers_nowhere

    result = _armed_cycle(rsp, tmp_path, inbox, _draft(rsp, "exit 0, 12 passed\n"))

    assert handed, "the cycle never reached the delivery step, so this arm is vacuous"
    # WHAT THE MODULE DECIDED, not what the stub did. The destination list is
    # computed inside `_run_once` as `[d / "moon_sync_inbox" for d in dests]`,
    # so this says the arm drove the real site with the real destination. An
    # assertion on the DIRECTORY'S CONTENTS would say nothing at all instead,
    # and that is checkable right here rather than on trust: `_delivers_nowhere`
    # is bound to `rsp.deliver` at the head of this arm, and that is the global
    # every `deliver` call site in `_run_once` resolves, so `rc_inbox` stays
    # empty whatever the module decides and `list(rc_inbox.iterdir()) == []`
    # could not fail.
    #
    # AND THIS ONE IS MEMBERSHIP, NOT EQUALITY - it bounds `handed[0]` from
    # below only. An extra destination appended to that list, including one in a
    # repository this tree does not own, leaves the arm green.
    assert rc_inbox in handed[0], (
        "the module handed the delivery step some other destination list, so "
        f"this arm is not driving the site it names: {handed[0]}"
    )
    assert result["termination"] == "delivered", (
        f"this arm must drive the DELIVERY branch, not another one: {result}"
    )
    assert result["delivered"] is False, (
        "a cycle that wrote to zero destinations reported itself delivered. "
        "`all([])` is vacuously True, so the `bool(written)` conjunct is the "
        "only thing standing between an empty write and a claim that a sibling "
        "was answered"
    )


def test_a_delivery_whose_only_write_failed_is_never_reported_as_delivered(rsp, tmp_path):
    """KILLS `delivery-write-all/operand-2` - `bool(written)` alone.

    A NON-EMPTY `written` CARRYING A FAILED ROW. Drop the `all(...)` conjunct
    and the truthiness of the list is the whole verdict, so a delivery that was
    ATTEMPTED and failed reports `delivered=True` - the row said False and
    nothing read it.

    This is the mirror of the arm above and neither can stand in for the other:
    that one needs an empty list, this one needs a non-empty list with a False
    in it. An arm that only ever sees both conjuncts agree proves neither.

    The failure is REAL rather than stubbed - the destination inbox path is an
    existing file, so `mkdir` raises and `deliver` absorbs it into its own
    `(False, target)` row. See `_bed_with_unwritable_destination`.
    """
    inbox, blocked = _bed_with_unwritable_destination(rsp, tmp_path)

    result = _armed_cycle(rsp, tmp_path, inbox, _draft(rsp, "exit 0, 12 passed\n"))

    assert result["termination"] == "delivered", (
        f"this arm must drive the DELIVERY branch, not another one: {result}"
    )
    assert result["delivered"] is False, (
        "a delivery whose every write failed reported itself delivered. The "
        "list was non-empty, so `bool(written)` alone is True and the "
        "`all(...)` conjunct is the only thing that reads the rows"
    )
    assert blocked.is_file(), "the destination is still the file it was, so the write really failed"


# ---------------------------------------------------------------------------
# GATE:bounce-write-all and GATE:bounce-mark
#
#   result["bounced"] = bool(sent) and all(ok for ok, _ in sent)
#   if result["bounced"]:
#       mark_bounced(...)
#
# The bounce is once per note per agreement, so a bounce falsely recorded as
# sent is a bounce the sender NEVER RECEIVES and the responder never retries.
# ---------------------------------------------------------------------------


def test_a_bounce_whose_only_write_failed_is_not_recorded_as_bounced(rsp, tmp_path):
    """KILLS `bounce-write-all/operand-1` - `bool(sent)` alone.

    A NON-EMPTY `sent` CARRYING A FAILED ROW, produced by a destination inbox
    path that is an existing file. Drop the `all(...)` conjunct and the mere
    fact that a delivery was ATTEMPTED becomes the verdict, so a bounce nobody
    received is reported as bounced.

    That is worse here than in the delivery branch. The module's own comment
    directly above the site says a failed write must not be recorded as
    bounced SO THE NEXT CYCLE TRIES AGAIN, and the bounce is once per note per
    agreement - a false True is a bounce that is never sent and never retried,
    and the sender simply never learns its note was refused.
    """
    inbox, blocked = _bed_with_unwritable_destination(rsp, tmp_path)
    attempts = _recording_deliver(rsp)

    result = _armed_cycle(rsp, tmp_path, inbox, "no tag at all\n")

    assert result["termination"] == "refused", (
        f"this arm must drive the REFUSAL branch, not another one: {result}"
    )
    assert len(attempts) == 1, (
        "the bounce step never ran, so every negative below is true by "
        "construction of the bed rather than by the gate - and `termination` "
        f"is set 60 lines upstream, so it is no evidence either: {attempts}"
    )
    assert attempts[0] and not any(ok for ok, _ in attempts[0]), (
        "the bounce step ran but did not produce the non-empty all-failed rows "
        f"this arm needs the gate to reduce: {attempts[0]}"
    )
    assert result["bounced"] is False, (
        "a bounce whose every write failed was recorded as bounced. `bool(sent)` "
        "alone only says a delivery was attempted, and the bounce is once per "
        "note per agreement - so a false True here is a refusal the sender is "
        "never told about and the responder never retries"
    )
    assert blocked.is_file(), "the destination is still the file it was, so the write really failed"


def test_a_bounce_to_zero_destinations_is_not_recorded_as_bounced(rsp, tmp_path):
    """KILLS `bounce-write-all/operand-2` - `all(ok for ok, _ in sent)` alone.

    `all([])` is VACUOUSLY TRUE here for the same reason it is in the delivery
    branch, so `bool(sent)` is the conjunct that refuses to call a write to
    nowhere a bounce.

    THE SAME STATED LIMIT AS THE DELIVERY ARM ABOVE. `sent` cannot be empty
    through real destinations - `deliver` returns one row per inbox and this
    site sits past `GATE:no-destination` - so `deliver` is substituted with a
    stub returning `[]`. The claim is about the assignment, not about an empty
    `dests` being reachable today.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    handed: list[list[Path]] = []

    def _delivers_nowhere(text, name, inboxes, *a, **k):
        handed.append(list(inboxes))
        return []

    rsp.deliver = _delivers_nowhere

    result = _armed_cycle(rsp, tmp_path, inbox, "no tag at all\n")

    assert handed, "the cycle never reached the bounce step, so this arm is vacuous"
    # WHAT THE MODULE DECIDED, for the reason spelled out in the delivery arm
    # above: an assertion about the destination directory's contents would be
    # an assertion about the stub, which cannot fail.
    assert rc_inbox in handed[0], (
        "the module handed the bounce step some other destination list, so "
        f"this arm is not driving the site it names: {handed[0]}"
    )
    assert result["termination"] == "refused", (
        f"this arm must drive the REFUSAL branch, not another one: {result}"
    )
    assert result["bounced"] is False, (
        "a bounce that reached zero destinations was recorded as bounced. "
        "`all([])` is vacuously True, so `bool(sent)` is the only conjunct that "
        "can tell a delivery from a no-op"
    )


def test_a_failed_bounce_leaves_the_note_unmarked_so_the_next_cycle_retries(rsp, tmp_path):
    """KILLS `bounce-mark/if-true` - `mark_bounced` called unconditionally.

    MEASURED IN THE RECORD, NOT IN THE RETURN VALUE. `mark_bounced` writes the
    per-agreement ledger that `bounced_under` reads, and `result["bounced"]` is
    set BEFORE the `if` and is not touched by it - so an arm asserting the
    return value would pass against this mutant while the ledger silently said
    the sender had been told. The gate is proven where the mutant acts.

    The bounce here really failed: the destination inbox path is an existing
    file. With the `if` forced True the note is marked bounced anyway,
    `bounced_under` goes True, and the bounce is once per note per agreement -
    so the next cycle skips it forever and a refusal nobody received is
    recorded as delivered. Retry is the entire purpose of the condition.
    """
    inbox, blocked = _bed_with_unwritable_destination(rsp, tmp_path)
    attempts = _recording_deliver(rsp)

    result = _armed_cycle(rsp, tmp_path, inbox, "no tag at all\n")
    agreement = rsp.agreement_id(rsp.DEFAULT_CONFIRMATION)

    assert result["termination"] == "refused", (
        f"this arm must drive the REFUSAL branch, not another one: {result}"
    )
    assert len(attempts) == 1, (
        "the bounce step never ran, so the unmarked ledger below is unmarked "
        "because nothing tried to mark it rather than because the gate refused "
        f"to - which is exactly what this arm must not accept: {attempts}"
    )
    assert attempts[0] and not any(ok for ok, _ in attempts[0]), (
        "the bounce step ran but every row was not a failure, so the `if` below "
        f"was not being asked the question this arm names: {attempts[0]}"
    )
    assert agreement != "none", (
        "the agreement did not read back, so `bounced_under` below is scoped to "
        "a fallback identity and this arm proves less than it claims"
    )
    assert rsp.bounced_under(rsp.DEFAULT_REFUSALS, NOTE_NAME, agreement) is False, (
        "a bounce that was never written was recorded in the ledger as bounced. "
        "The bounce is once per note per agreement, so the next cycle will skip "
        "it and the sender is never told its note was refused"
    )
    assert blocked.is_file(), "the destination is still the file it was, so the write really failed"


def test_a_bounce_that_succeeds_is_recorded_as_bounced(rsp, tmp_path):
    """THE NON-VACUITY ARM for the THREE REFUSAL-BRANCH arms above.

    Five arms above assert that something did NOT happen, and they split by
    branch rather than sitting under one cover. THIS ONE COVERS THE THREE THAT
    DRIVE THE REFUSAL BRANCH - the failed-row bounce arm, the zero-destination
    bounce arm, and the unmarked-ledger arm. All three pass perfectly against a
    responder that never bounces at all or whose refusal branch is unreachable,
    so without this the sweep would score 100 percent by deleting its own
    subject. The remaining two of the five are delivery arms and are covered by
    the arm below instead; three plus two accounts for all five, and neither
    non-vacuity arm covers an arm in the other's branch.

    This one asserts the LEGITIMATE neighbour SURVIVES: a real destination
    directory, a real refused draft, one bounce file on disk, `bounced` True,
    and the ledger marked.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)

    result = _armed_cycle(rsp, tmp_path, inbox, "no tag at all\n")
    agreement = rsp.agreement_id(rsp.DEFAULT_CONFIRMATION)
    landed = sorted(p.name for p in rc_inbox.iterdir())

    assert result["termination"] == "refused", result
    assert result["bounced"] is True, f"a bounce to a writable inbox was not recorded: {result}"
    assert len(landed) == 1, f"expected exactly one bounce file, got {landed}"
    assert rsp.bounced_under(rsp.DEFAULT_REFUSALS, NOTE_NAME, agreement) is True, (
        "a delivered bounce was not marked, so the next cycle would send it again"
    )


def test_a_delivery_that_succeeds_is_reported_as_delivered(rsp, tmp_path):
    """THE NON-VACUITY ARM for the two delivery arms above.

    Same reasoning: two arms asserting `delivered is False` both pass against a
    responder whose delivery branch is dead. This one proves the branch is
    alive and that the two conjuncts together still say True when they should.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)

    result = _armed_cycle(rsp, tmp_path, inbox, _draft(rsp, "exit 0, 12 passed\n"))
    landed = sorted(p.name for p in rc_inbox.iterdir())

    assert result["termination"] == "delivered", result
    assert result["delivered"] is True, f"a delivery to a writable inbox was not reported: {result}"
    assert len(landed) == 1, f"expected exactly one reply, got {landed}"
