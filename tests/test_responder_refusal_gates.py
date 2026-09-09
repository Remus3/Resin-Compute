"""Driving arms for three REFUSAL-SIDE gates in `tools/moon_sync_responder.py`.

WHY THIS FILE EXISTS AND WHY IT IS SEPARATE. The 2026-09-09 gate mutation
campaign mutates each tagged statement ACCORDING TO ITS KIND, not uniformly -
`_edits_for` at `tools/gate_mutation_runner.py:407` rewrites an `if` test to the
literal `True` and to the literal `False`, a conditional expression's test both
ways, an `except` body to a bare `raise`, and a boolean assignment's WHOLE
expression to each of its operands in turn, dropping the rest
(`tools/gate_mutation_runner.py:448-452`, whose own docstring at line 419 reads
"one mutant per operand, each dropping the rest") - and reports which mutants no
test could tell apart from the real module. The direction matters and an earlier
draft here had it backwards: the whole is rewritten to one operand, not the
operand to the whole. Three of the `if-false` mutants survived in this half:
`no-destination`, `workspace-trust` and `refusal-recorded`.

"SURVIVED" IS NARROWER THAN "THE SUITE WENT GREEN", and the narrowing is the
campaign's own. It hands pytest `--ignore` for `EXCLUDED_MODULES`
(`tools/gate_mutation_runner.py:191`), so a survivor is one the application suite
MINUS those modules could not tell apart. The two exclusions have two DIFFERENT
reasons and merging them loses the distinction: `SELF_TEST_MODULE` (line 138) is
a module that decides its own verdict, and `SHAPE_GRADER_MODULES` (line 186) is a
module that grades the target file's SHAPE, answering a syntax question while the
runner asks a behaviour one. Measured this session against `refusal-recorded/
if-false`, full `tests` run, no `--ignore`, caches purged both sides: 2 failed,
1845 passed, 1 skipped. The two failures were the arm below and the SELF-TEST
module, whose kill is tautological - re-planning the mutant against an
already-mutated tree yields a no-op edit. The census did NOT redden, because
`if False` preserves the AST shape it grades. A gate nothing drives is prose with
an `if` in front of it.

EVERY GATE ARM HERE DRIVES `run_once` AND ASSERTS AN OUTCOME, never a predicate.
There is exactly one arm that does not, and it is not a gate arm:
`test_every_default_path_is_isolated_in_this_module_too` below asserts a
predicate on module state on purpose, because it proves the FIXTURE rather than
a gate, and without it every gate arm would run against the operator's live
runtime directory and still go green.

THAT CONVENTION COMES FROM TWO SEPARATE INCIDENTS, and welding them loses both.
In the first, three mutants disabled three gates inside `run_once` while the
suite stayed green, because the arms tested the predicates - `within_budget`,
`window_open` and the self-code check - as pure functions and none of them
tested that anything consults one
(`tests/test_moon_sync_responder.py:935-939`). In the second, four terminations
- window, budget, empty and disarmed - WERE driven through `run_once`
(`tests/test_moon_sync_responder.py:618`, whose `rsp.run_once` call is at line
645) and were still under-proved, for a different reason: the arm asserted only
the RETURN VALUE and never the invocation-log CALL
(`tests/test_moon_sync_responder.py:1040` and `:1051`). Calling
`destinations_for` and `workspace_trust` in isolation cannot fail when the gate
that consults them is gone, so the assertions below are on the cycle's
termination, on whether a session was spawned at all, and on FILES ON DISK in
the destination inbox.

EVERY REFUSING ARM IS PAIRED WITH A NON-VACUITY SIBLING. The fixture-proving arm
named above is the one arm here with no sibling; it carries its own non-vacuity
check inline instead, as the `len(defaults) >= 4` assertion. A test that asserts
"no spawn" and "no bounce" passes trivially against a responder that never
spawns and never bounces, which is the counterparty's original complaint
restated. So each refusing arm has a permitting arm one field away from it
proving the same bed does the positive thing when the guard's precondition is
not met.
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

    Copied in shape - not imported - from `test_moon_sync_responder.py`, whose
    own docstring records why: an arm that omits an argument here does not
    pollute a record, it delivers a file into another repository's inbox. The
    redirection is DISCOVERED by walking the module rather than listed, so a
    default added tomorrow is isolated today. `DEFAULT_TRUST_CONFIG` is one of
    the discovered ones, which is what makes the workspace-trust arm below able
    to author a trust config without touching the operator's real `~/.claude.json`.
    """
    spec = importlib.util.spec_from_file_location("moon_sync_responder_refusal_gates", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def test_every_default_path_is_isolated_in_this_module_too(rsp, tmp_path):
    """The fixture above is a COPY, so it needs its own proof it isolated anything.

    Without this arm a typo in the copy - a `startswith` that matches nothing, a
    `setattr` on the wrong object - would make every arm below run against the
    operator's live runtime directory and still go green.
    """
    defaults = [n for n in dir(rsp) if n.startswith("DEFAULT_") and isinstance(getattr(rsp, n), Path)]

    assert len(defaults) >= 4, f"the discovery found almost nothing, so this arm is vacuous: {defaults}"
    for name in defaults:
        assert tmp_path in getattr(rsp, name).parents, f"{name} escapes the test's own directory"


# ---------------------------------------------------------------------------
# The bed. One agreed, armed cycle over one note from the one opted-in sender.
# ---------------------------------------------------------------------------

NOTE_NAME = "2026-09-08-1900-from-RC-question.md"


def _note(inbox: Path, name: str = NOTE_NAME, body: str = "please measure your suite\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def _agree(rsp) -> None:
    """Record the counterparty's agreement, as the operator would.

    Called by the bed rather than by the fixture, for the reason the sibling
    module gives: a fixture that pre-agreed would hide the precondition.
    """
    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )


def _draft(rsp, body: str = "measured, and here is the number\n") -> str:
    """A draft that passes every output rule, so an arm varies exactly one thing."""
    return rsp.RESPONDER_TAG + "\n\n" + body


def _bed(rsp, tmp_path):
    """(inbox, the destination inbox). Agreed, one note, a real place to deliver."""
    _agree(rsp)
    inbox = tmp_path / "inbox"
    _note(inbox)
    rc_inbox = tmp_path / "rc" / "moon_sync_inbox"
    rc_inbox.mkdir(parents=True)
    return inbox, rc_inbox


class _Spawn:
    """A spawn double that RECORDS. The count is the load-bearing observation.

    Two of the three gates below exist to stop a session being started at all,
    and a return value cannot distinguish "refused before spawning" from
    "spawned, then refused". Only the call log can.
    """

    def __init__(self, draft: str):
        self.draft = draft
        self.prompts: list[str] = []

    def __call__(self, prompt, bounds):
        self.prompts.append(prompt)
        return self.draft


def _cycle(rsp, tmp_path, inbox, spawn, roots, now=30_000.0):
    return rsp.run_once(
        inbox=inbox,
        roots=roots,
        bounds=rsp.Bounds(armed=True),
        spawn=spawn,
        now=now,
    )


def _held(rsp):
    return sorted(p.name for p in rsp.DEFAULT_STAGING.glob("held/*"))


def _bounces(rc_inbox):
    return sorted(p.name for p in rc_inbox.iterdir())


def _rows(rsp):
    payload = json.loads(rsp.DEFAULT_METRICS.read_text()) if rsp.DEFAULT_METRICS.is_file() else {}
    return payload.get("cycles", [])


# ---------------------------------------------------------------------------
# GATE:no-destination - the sender is opted in and has NO root configured.
# ---------------------------------------------------------------------------


def test_an_opted_in_sender_with_no_configured_root_spawns_nothing(rsp, tmp_path):
    """The two halves of consent are separate, and only one of them was proved.

    `pending()` decides WHO is answered from `OPTED_IN`; `destinations_for()`
    decides WHERE the answer may go, from `roots`. A sender can be on the first
    list and absent from the second - which is exactly the state on a fresh
    machine whose `ops/moon_sync_repos.json` has not been filled in - and the
    responder must stop there, before a session is started, because there is
    nowhere the reply could legally land.

    WITHOUT THIS GATE the cycle runs to completion. Measured this session with
    `if not dests` rewritten to `if False`, one cycle, `roots={}`: 1 session
    spawned, `termination` "delivered", `delivered` False, `actions` ["A5"], the
    destination inbox still EMPTY, a reply file written into THIS repo's own
    inbox, a metrics row reading ("delivered", False), and the note written into
    `DEFAULT_ANSWERED`.

    THE ANSWERED RECORD IS THE COST THAT DOES NOT WASH OUT. A wasted session and
    a row that calls itself delivered while carrying False are one cycle's
    damage. The answered record is permanent: the note is skipped from then on,
    so when `ops/moon_sync_repos.json` is finally filled in the reply that went
    nowhere can never be retried. That is why the spawn count is asserted here
    and not merely the termination.
    """
    inbox, _rc = _bed(rsp, tmp_path)
    spawn = _Spawn(_draft(rsp))

    result = _cycle(rsp, tmp_path, inbox, spawn, roots={})

    assert result["termination"] == "no-destination", result
    assert result["reasons"] == ["no opted-in destination for this sender"], result
    assert spawn.prompts == [], (
        f"a note with no destination still started {len(spawn.prompts)} session(s). "
        "The guard exists to spend nothing on a reply that has nowhere to go"
    )
    assert result["delivered"] is False, result
    assert result["note"] == NOTE_NAME, result


def test_the_same_note_with_a_configured_root_does_spawn_and_deliver(rsp, tmp_path):
    """THE NON-VACUITY ARM for the one above, and it varies exactly one field.

    Both arms use the identical bed and the identical note. The only difference
    is whether `roots` carries an entry for `RC`. Without this arm the arm above
    passes against a responder that answers nobody at all.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    spawn = _Spawn(_draft(rsp))

    result = _cycle(rsp, tmp_path, inbox, spawn, roots={"RC": tmp_path / "rc"})

    assert len(spawn.prompts) == 1, spawn.prompts
    assert result["termination"] != "no-destination", result
    assert result["delivered"] is True, result
    assert len(_bounces(rc_inbox)) == 1, _bounces(rc_inbox)


# ---------------------------------------------------------------------------
# GATE:workspace-trust - the cwd spelling is marked UNTRUSTED in the config.
# ---------------------------------------------------------------------------


def _trust_config(rsp, accepted: bool) -> None:
    """Author a `~/.claude.json` shaped config for THIS repo's spelling.

    `DEFAULT_TRUST_CONFIG` is redirected by the fixture, so this writes into
    `tmp_path` and the operator's real config is never read or touched. The key
    is `str(rsp.REPO_ROOT)` - the native spelling - because that is the one
    `workspace_trust` derives from the cwd it is handed.
    """
    rsp.DEFAULT_TRUST_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_TRUST_CONFIG.write_text(
        json.dumps({"projects": {str(rsp.REPO_ROOT): {"hasTrustDialogAccepted": accepted}}})
    )


def test_an_untrusted_workspace_refuses_to_spawn_at_all(rsp, tmp_path):
    """A degraded session is worse than no session, and it says nothing about it.

    An untrusted workspace makes a headless run DISCARD its permissions without
    erroring - it runs believing it has permissions it does not have. Sibling-D
    lost the first two arms of a hook probe to exactly this and concluded
    wrongly that hooks do not fire headless.

    WITHOUT THIS GATE the responder spawns anyway. The failure is not a crash
    and not an empty draft; it is a draft produced under permissions nobody
    granted, delivered into another repository, with the reason invisible on
    every surface. Measured this session with `if not trusted` rewritten to
    `if False`, one cycle, the untrusted config in place: 1 session spawned,
    `delivered` True, and the reply file landed in the destination inbox. So the
    assertion is the spawn count, plus the metrics row - a refusal the record
    cannot describe is the same as no refusal.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    _trust_config(rsp, accepted=False)
    spawn = _Spawn(_draft(rsp))

    result = _cycle(rsp, tmp_path, inbox, spawn, roots={"RC": tmp_path / "rc"})

    assert spawn.prompts == [], (
        f"an untrusted workspace still started {len(spawn.prompts)} session(s), which "
        "is a session running with permissions it believes it has and does not"
    )
    assert result["termination"] == "untrusted-workspace", result
    assert result["delivered"] is False, result
    assert _bounces(rc_inbox) == [], _bounces(rc_inbox)
    assert [r["termination"] for r in _rows(rsp)] == ["untrusted-workspace"], _rows(rsp)
    assert "UNTRUSTED" in " ".join(result["reasons"]), result


def test_a_trusted_workspace_spawns_normally(rsp, tmp_path):
    """THE NON-VACUITY ARM. One boolean apart from the one above.

    IT IS NOT THE ARM THAT PROVES THE CONFIG IS READ, and an earlier draft here
    claimed it was. An absent, unreadable or wrongly-keyed config is
    TRUSTED-BY-DEFAULT - stated at `tools/moon_sync_responder.py:764` and
    implemented by the `return True` exits at lines 771, 774 and 797 - so if the
    redirected path or the key spelling were wrong, BOTH arms would take the
    trusted branch, THIS one would still pass, and the arm above would be the
    one to go red. The plumbing proof therefore lives in the arm above. What
    this arm rules out is the other failure: a responder that refuses
    unconditionally.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    _trust_config(rsp, accepted=True)
    spawn = _Spawn(_draft(rsp))

    result = _cycle(rsp, tmp_path, inbox, spawn, roots={"RC": tmp_path / "rc"})

    assert len(spawn.prompts) == 1, spawn.prompts
    assert result["termination"] != "untrusted-workspace", result
    assert result["delivered"] is True, result
    assert len(_bounces(rc_inbox)) == 1, _bounces(rc_inbox)


# ---------------------------------------------------------------------------
# GATE:refusal-recorded - the record was USABLE and the write STILL failed.
#
# WHY THE EXISTING UNRECORDABLE ARM DOES NOT REACH HERE. There are two gates on
# this path that both terminate `unrecordable`, and they are not the same gate.
# `GATE:refusals-usable` runs FIRST and asks whether the record can be read and
# written AT ALL; `test_a_refusal_record_that_cannot_be_written_sends_no_bounce`
# drives it by making the record a non-empty DIRECTORY, which `refusals_usable`
# catches on its `not path.is_file()` branch and returns before the bounce block
# is ever entered. `GATE:refusal-recorded` runs much later and asks a different
# question - inspection raised no objection and the write returned False anyway -
# so no arm that poisons the record's SHAPE can reach it, and the four
# self-healing siblings (one arm parametrized four ways,
# `test_a_replaceable_refusal_record_still_bounces_and_self_heals`) all have the
# write SUCCEEDING. Hence the survivor.
#
# THE STATE DRIVEN HERE IS A RECORD THAT NEVER EXISTS ON DISK - measured this
# session, `DEFAULT_REFUSALS.is_file()` is False after five cycles of the arm's
# own bed, and no file is ever created. `refusals_usable` passes it anyway: with
# `path.exists()` False both structural branches short-circuit, `_ensure_parent`
# makes the directory, and the `if path.is_file()` read is skipped, so the
# function returns True having inspected NO FILE. That is not a loophole in the
# arm - it is the only state the arm's own patch can produce, because the patched
# `_remember_refusal` is what would otherwise have created the file.
# ---------------------------------------------------------------------------


def _unpassable(rsp) -> str:
    """A draft the output gate refuses, so the cycle reaches the bounce block."""
    return "no responder tag at all, so validate_draft refuses this\n"


def test_a_refusal_whose_record_write_fails_delivers_no_bounce(rsp, tmp_path, monkeypatch):
    """FAIL CLOSED, BECAUSE THE FAILURE WRITES INTO SOMEBODY ELSE'S REPOSITORY.

    NO RECORD EXISTS HERE - see the block comment above. `refusals_usable`
    passes on the `path.exists()` short-circuit rather than by inspecting a file,
    so the earlier gate does not fire and control reaches this one. The write
    then fails, which is the transient class: a lock, a full disk, a directory
    that vanished between the inspection and the rename. Every suppression
    downstream is keyed on the refusals FILE at `DEFAULT_REFUSALS` - the
    `refusals` rows and the `bounced` ledger both live in it - so an unrecorded
    refusal reads as "never refused, never bounced" on the NEXT cycle too.

    WITHOUT THIS GATE the bounce goes out, and the measured cost is ONE bounce -
    not one per cycle. Measured this session, the same bed with `if not recorded`
    rewritten to `if False` and five cycles: 1 bounce delivered, held count 5,
    `bounced` flags [True, False, False, False, False], and a refusals file whose
    `refusals` map is EMPTY while its `bounced` ledger names the note. The ledger
    is why it stops at one: `mark_bounced`, called at
    `tools/moon_sync_responder.py:1842`, is NOT what this arm patches, so it
    lands and `bounced_under` suppresses cycles 2 through 5. One unrequested file
    in a repository this one does not own is still the wrong number of files, and
    zero is the number this gate exists to produce.

    THE 288-A-DAY FIGURE BELONGS TO THE OTHER GATE AND DOES NOT CARRY ACROSS.
    It is true of `GATE:refusals-usable` - see
    `test_a_refusal_record_that_cannot_be_written_sends_no_bounce` at
    `tests/test_moon_sync_responder.py:1545-1548` - where the whole record is
    unwritable, so `mark_bounced` fails too and NOTHING suppresses the repeat.
    Here only `_remember_refusal` fails. Two gates, two different file counts.

    THE BOUNCE COUNT IS THE LOAD-BEARING ASSERTION - it is the other repo's
    mess. The held file is this repo's own and is NOT asserted absent: the hold
    is written by `GATE:repeat-hold`, upstream of this gate. Measured this
    session, five cycles give a held count of 5 with the gate AND without it, so
    the held file is the real module's behaviour rather than a leak, and holding
    is not part of what this gate buys.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)
    monkeypatch.setattr(rsp, "_remember_refusal", lambda *a, **k: False)

    results = [
        _cycle(rsp, tmp_path, inbox, _Spawn(_unpassable(rsp)), {"RC": tmp_path / "rc"}, now=30_000.0 + 60.0 * i)
        for i in range(3)
    ]

    assert _bounces(rc_inbox) == [], (
        f"an unrecordable refusal delivered {len(_bounces(rc_inbox))} bounce(s) into a "
        "sibling's inbox. A bounce whose record did not land is a bounce that goes "
        "out again on every cycle forever"
    )
    assert all(r["termination"] == "unrecordable" for r in results), results
    assert all(r["bounced"] is False for r in results), results
    assert all("the refusal record could not be written" in r["reasons"] for r in results), results
    assert [r["termination"] for r in _rows(rsp)] == ["unrecordable"] * 3, _rows(rsp)


def test_the_same_refusal_with_a_writable_record_does_bounce_once(rsp, tmp_path):
    """THE NON-VACUITY ARM, and it is the whole distinction being drawn.

    Failing closed on every refusal would be trivially safe and would silence
    the channel - the counterparty's original complaint. This arm is the arm
    above with the write left working: the same bed, the same unpassable draft,
    the same three cycles. One bounce must go out, and exactly one.

    THE SUPPRESSOR IS NOT THE RECORD THE ARM ABOVE BREAKS. What stops the second
    bounce is `mark_bounced`'s `bounced` ledger, read by `bounced_under`, and
    that ledger lands in BOTH arms - measured this session, the without-gate run
    described above still bounces exactly once for precisely that reason. What
    `_remember_refusal` writes, and what fails to land above, is the `refusals`
    rows; those suppress the HOLD through `refusal_seen`. That is why the held
    count is asserted at 1 here and is deliberately left unasserted above.
    """
    inbox, rc_inbox = _bed(rsp, tmp_path)

    results = [
        _cycle(rsp, tmp_path, inbox, _Spawn(_unpassable(rsp)), {"RC": tmp_path / "rc"}, now=30_000.0 + 60.0 * i)
        for i in range(3)
    ]

    assert len(_bounces(rc_inbox)) == 1, _bounces(rc_inbox)
    assert results[0]["termination"] == "refused", results[0]
    assert results[0]["bounced"] is True, results[0]
    assert len(_held(rsp)) == 1, _held(rsp)
    assert json.loads(rsp.DEFAULT_REFUSALS.read_text())["refusals"], (
        "the refusal record did not land, so this arm is not the positive control it claims"
    )
