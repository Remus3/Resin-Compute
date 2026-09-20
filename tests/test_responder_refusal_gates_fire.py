"""The BEHAVIOURAL arm beside the syntax census in
`tests/test_responder_gate_census.py`.

WHY THIS FILE EXISTS, AS A MEASUREMENT AND NOT AS AN OPINION. The census is a
PURE STATIC guard: it parses `tools/moon_sync_responder.py`, walks the AST of
the ONE function `_run_once`, and asserts that every `# GATE:` tag sits above a
node `_is_a_consult_site` accepts and that every such node carries a tag. It
never imports the responder and never runs a cycle. Its own ceiling item 3 says
so in as many words - "THIS CENSUS still says nothing about any test driving a
gate".

THAT CEILING WAS PREDICTED TO BE EXPLOITABLE AND IS. Measured 2026-09-20 on a
scratchpad copy of this tree, with `__pycache__` purged on both sides and
`-p no:cacheprovider`:

  - BEFORE: `tests/test_responder_gate_census.py` collected 80 nodes,
    79 passed 1 skipped (the one git-gated cross-corpus arm, skipped because the
    scratchpad copy carries no repository).
  - MUTATION: the `GATE:trial-window` refusal was RELOCATED out of `_run_once`
    into a new module-level helper `_trial_window_refusal(bounds, started,
    result)`, behaviour preserved exactly, with `_run_once` left holding only
    `if (refusal := _trial_window_refusal(...)) is not None: return refusal`
    under the same unmoved tag. The sole call to
    `window_open(bounds, now=started)` - the actual predicate consult the gate
    IS - no longer occurs anywhere inside `_run_once`.
  - AFTER: the census collected 80 nodes, 79 passed 1 skipped. IDENTICAL.

So the outcome was (a), the predicted defeat, and NOT (c): the arm count did not
drop, it did not move at all. The census cannot distinguish a gate from a
null-check on a helper's return value, because both are an `ast.If` on a line
carrying a tag. Behaviour was confirmed unchanged by running `pytest tests -k
responder` on both copies: 355 passed on each, with the same two pre-existing
no-repository failures on both sides, so the mutant is a genuine refactor and
not a behaviour change that happened to stay quiet.

THE REPAIR IS THIS FILE BESIDE THE CENSUS, NEVER INSTEAD OF IT. A syntax census
is a legitimate cheap tripwire - it is what catches an author who adds a gate
and forgets to tag it, and it runs without importing anything. Deleting it to
"replace it with a real test" would trade a working guard for a different
working guard. What it cannot do is notice that a gate stopped being consulted,
and that is the one thing every arm below does.

WHAT AN ARM HERE ASSERTS. It drives `_run_once` to the gate's own condition and
observes the CYCLE'S OWN RESULT - the `termination` label and the `delivered`
flag the responder returns. Nothing here parses source, counts nodes, or names a
line. Relocating a gate into a helper leaves every arm GREEN for the right
reason, because the refusal still happens; REMOVING a gate turns the arm RED,
because the cycle then falls through to a different termination.

PROVED NOT VACUOUS BY DELETION, not assumed. Measured 2026-09-20 on a second
scratchpad copy, deleting the `GATE:trial-window` branch and its tag outright
from `_run_once` and leaving everything else alone:

    AssertionError: the trial-window gate did not refuse a cycle it is the gate
    for: termination='no-destination', reasons=['no opted-in destination for
    this sender']

`termination='no-destination'` is the RIGHT reason and is worth stating rather
than just quoting: with the window gate gone the cycle did not stop, it ran ON
through the three gates below and fell out at `GATE:no-destination` instead.
That is exactly the shape of the defect this arm exists to catch - a refusal
that silently stopped happening.

THE PREDICTED LABEL WAS WRONG AND IS CORRECTED HERE RATHER THAN QUIETLY FIXED.
This paragraph first read `termination='empty', reasons=[]`, written from
reading the gate order before the mutant was run. It is `no-destination`,
because this arm's inbox holds one answerable note from RC and the arm passes
`roots={}`, so the queue is NOT empty and the cycle reaches the destination gate.

THE CENSUS ALSO REDDENS ON THAT SAME DELETION - 10 failed, 68 passed, 1 skipped
- and that is the honest half of the finding. A gate that is REMOVED is caught
by both guards. The census's blind spot is RELOCATION specifically, which is the
mutation it scored 79 passed 1 skipped on while the consult left the function.
This file is the arm for that case, not a claim that the census catches nothing.

EVERY ARM IS A PAIR, per this tree's standing sweep convention: the REFUSAL
direction and a NEIGHBOUR-SURVIVED control in which the gate's condition is NOT
met, so a responder that refused unconditionally - the mutant that would score
full marks on the refusal direction alone - fails the control.

ISOLATION, AND WHY IT IS DISCOVERED RATHER THAN LISTED. The `rsp` fixture
rebinds EVERY `DEFAULT_*` Path on a freshly loaded module object into
`tmp_path`, by enumerating the module rather than naming the paths by hand. That
list is not maintained here on purpose: `tests/test_moon_sync_responder.py`
records that its own first hand-written version named three paths, a fourth was
added an hour later, and the suite wrote five real lines into the live
`ops/runtime/responder_invocations.log`. The same enumeration is used here for
the same reason.

NOTHING HERE NEEDS THE FLEET, and that is a requirement rather than a
convenience. No arm requires the scheduled task to be enabled, none requires a
counterparty, none writes `ops/runtime/trial_confirmed.json` - the
counterparty arm drives its gate by pointing `DEFAULT_CONFIRMATION` at a path
under `tmp_path` that does not exist, which is a READ of an absent record and
never a write of a present one. `roots` is passed explicitly on every call, so
`load_roots()` never reads the host config, and the only root any arm supplies
is a directory under `tmp_path`. No arm delivers: the two arms that reach as far
as note selection stop at `GATE:no-destination` and `GATE:armed`, both of which
return before `deliver` is called. `Bounds(armed=True)` appears in exactly one
arm, where the FIRST gate in the function refuses it immediately.

THIS MODULE MUST NEVER READ THE RESPONDER'S SOURCE TEXT, and that is a hard
constraint rather than a preference. `tools/gate_mutation_runner.py` refuses to
run a campaign while any module that grades the target file's SHAPE is
undeclared, because such a module reddens over syntax and would be scored as a
KILL while saying nothing about whether a gate is driven. Its detector,
`_binds_and_reads_responder`, is a CONJUNCTION of two criteria, both verified
here by reading it rather than inferred:

  1. a MODULE-LEVEL assignment to a plain `Name` whose value mentions
     `moon_sync_responder` - which `MODULE` below satisfies and must, since the
     fixture needs the path;
  2. that same name LATER being the RECEIVER of `.read_text`, `.read_bytes` or
     `.open` - `_READ_ATTRS` at `tools/gate_mutation_runner.py:712`.

Criterion 2 is what this module must not satisfy. Passing `MODULE` to
`importlib.util.spec_from_file_location` does NOT satisfy it: the bound name is
an ARGUMENT there and never the receiver of an attribute access. That is the
detector's own documented blind spot, and it is the reason the four existing
behavioural modules that import the responder - `test_moon_sync_responder.py`,
`test_responder_broadcast_refusal.py`, `test_responder_delivery_gates.py` and
`test_responder_refusal_gates.py` - are correctly not candidates. This module is
deliberately the fifth of that shape.

AN ARM WAS DELETED HERE, NOT MOVED, AND THE DIFFERENCE IS THE POINT. The first
version of this file carried
`test_every_gate_driven_here_is_one_the_census_names`, which did
`MODULE.read_text(...)` to check that the six names driven below are real tags.
That single line satisfied criterion 2 and made this WHOLE FILE a candidate for
exclusion - which would have removed the ten behavioural arms from the campaign
they exist to feed, the exact opposite of this module's purpose. The obvious
repair, declaring the file in `SHAPE_GRADER_MODULES`, is therefore the wrong
one. Relocating the arm into `tests/test_responder_gate_census.py` was also
wrong, because it is REDUNDANT there: `tests/test_gate_name_bindings.py:251`
already asserts `set(_ANCHORS) == live` - the tag-name set by EQUALITY, not a
subset - and its `_ANCHORS` table binds all six of these names to their exact
statement text. A strictly weaker duplicate is deleted rather than rehoused, so
nothing was lost and this file stays inside the campaign.

A NEW TEST FILE IS NOT GRADED UNTIL IT IS TRACKED. This defect reached a commit
because `missing_exclusions` derives its corpus from `git ls-files`, so while
this file was untracked the guard could not see it BY CONSTRUCTION and every
suite run over it was vacuous for that guard. Staging is part of proving a fix
here, not a formality.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "tools" / "moon_sync_responder.py"

#: A fixed epoch so every window comparison here is arithmetic and not a clock.
#: `_run_once` takes `started` and passes it as `now=` to both `window_open` and
#: `counterparty_agreed`, so pinning it makes those two gates deterministic.
STARTED = 1_700_000_000.0

#: `_run_once` carries this into the result untouched. It is not a gate input.
GRAMMAR = "suite-behavioural-arm"


@pytest.fixture
def rsp(tmp_path):
    """The responder, loaded fresh with every `DEFAULT_*` path under `tmp_path`.

    DISCOVERED, NOT LISTED - see the module docstring for the measured reason a
    hand-maintained list of paths to isolate is the wrong shape here.
    """
    spec = importlib.util.spec_from_file_location("moon_sync_responder_gate_arms", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    redirected = 0
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
            redirected += 1

    assert redirected >= 4, (
        "the DEFAULT_ discovery found almost nothing, so this fixture isolates "
        f"nothing and every arm below would reach live state: {redirected}"
    )
    return module


def _inbox(tmp_path, *names: str) -> Path:
    """An inbox directory under `tmp_path` holding one `.md` file per name."""
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for name in names:
        (inbox / name).write_text("a note body\n", encoding="ascii")
    return inbox


def _cycle(rsp, inbox: Path, bounds, roots: dict[str, Path] | None = None) -> dict:
    """One cycle, driven in process, with no spawn and no live defaults.

    `spawn` is passed as a callable that RAISES, not as None. None would make
    `_run_once` fall back to `_spawn_headless`, which starts a real session; no
    arm here is supposed to reach that line, and a raise makes it loud if one
    ever does rather than launching something.
    """

    def _never_spawn(prompt, bounds):  # pragma: no cover - reaching this is the failure
        raise AssertionError("an arm reached the spawn seam; no arm here should")

    return rsp._run_once(
        inbox=inbox,
        roots={} if roots is None else roots,
        bounds=bounds,
        spawn=_never_spawn,
        started=STARTED,
        grammar=GRAMMAR,
    )


def _why(label: str, result: dict) -> str:
    return (
        f"the {label} gate did not refuse a cycle it is the gate for: "
        f"termination={result['termination']!r}, reasons={result['reasons']!r}. "
        "This arm observes the CYCLE'S OWN RESULT, so it goes red when the gate "
        "stops being consulted and stays green when the gate merely moves into a "
        "helper - which is exactly the distinction "
        "tests/test_responder_gate_census.py cannot make."
    )


# ---------------------------------------------------------------------------
# ONE PAIR PER GATE: the refusal, and the neighbour that must survive it.
# ---------------------------------------------------------------------------


def test_the_counterparty_agreement_gate_refuses_an_armed_cycle_with_no_record(rsp, tmp_path):
    """GATE:counterparty-agreement - the first gate in the function.

    Driven by ABSENCE: `DEFAULT_CONFIRMATION` is a redirected path under
    `tmp_path` that was never created, so `counterparty_agreed` answers False
    without this arm writing any agreement record anywhere. The cycle refuses at
    the first gate and returns before anything else in the function runs.
    """
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")
    assert not rsp.DEFAULT_CONFIRMATION.exists(), rsp.DEFAULT_CONFIRMATION

    refused = _cycle(rsp, inbox, rsp.Bounds(armed=True))

    assert refused["termination"] == "unconfirmed", _why("counterparty-agreement", refused)
    assert refused["delivered"] is False, refused
    assert refused["reasons"], "a refusal with no stated reason is not a refusal"


def test_a_disarmed_cycle_does_not_reach_the_counterparty_gate_at_all(rsp, tmp_path):
    """THE NEIGHBOUR. The gate reads `bounds.armed and not agreed`, not `not agreed`.

    Without this, a responder that returned `unconfirmed` on EVERY cycle would
    pass the arm above outright.
    """
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")

    result = _cycle(rsp, inbox, rsp.Bounds(armed=False))

    assert result["termination"] != "unconfirmed", (
        "a DISARMED cycle was refused by the counterparty gate, which only "
        f"applies to an armed one: {result!r}"
    )


def test_the_trial_window_gate_refuses_a_cycle_outside_the_window(rsp, tmp_path):
    """GATE:trial-window. The window closed one second before this cycle began."""
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")
    closed = rsp.Bounds(armed=False, window_closes=STARTED - 1.0)

    refused = _cycle(rsp, inbox, closed)

    assert refused["termination"] == "window", _why("trial-window", refused)
    assert refused["delivered"] is False, refused
    assert refused["reasons"] == ["the trial window is not open"], refused


def test_a_cycle_inside_the_trial_window_is_not_refused_by_that_gate(rsp, tmp_path):
    """THE NEIGHBOUR. An open window must not be reported as a closed one."""
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")
    open_window = rsp.Bounds(
        armed=False, window_opens=STARTED - 60.0, window_closes=STARTED + 60.0
    )

    result = _cycle(rsp, inbox, open_window)

    assert result["termination"] != "window", (
        f"a cycle inside the agreed window was refused as outside it: {result!r}"
    )


def test_the_hop_budget_gate_refuses_a_cycle_at_a_spent_budget(rsp, tmp_path):
    """GATE:hop-budget. A budget of zero is spent before the first hop."""
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")

    refused = _cycle(rsp, inbox, rsp.Bounds(armed=False, max_hops=0))

    assert refused["termination"] == "budget", _why("hop-budget", refused)
    assert refused["delivered"] is False, refused
    assert refused["reasons"] == ["hop budget of 0 reached"], refused


def test_a_cycle_with_budget_remaining_is_not_refused_by_that_gate(rsp, tmp_path):
    """THE NEIGHBOUR. An unspent budget must not read as a spent one."""
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")

    result = _cycle(rsp, inbox, rsp.Bounds(armed=False, max_hops=8))

    assert result["termination"] != "budget", (
        f"a cycle with 8 hops of budget was refused as over budget: {result!r}"
    )


def test_the_empty_queue_gate_refuses_a_cycle_with_nothing_to_answer(rsp, tmp_path):
    """GATE:empty-queue. An inbox with no note from an opted-in sender."""
    empty = _inbox(tmp_path)

    refused = _cycle(rsp, empty, rsp.Bounds(armed=False))

    assert refused["termination"] == "empty", _why("empty-queue", refused)
    assert refused["note"] is None, refused
    assert refused["delivered"] is False, refused


def test_a_cycle_with_a_note_to_answer_is_not_refused_as_empty(rsp, tmp_path):
    """THE NEIGHBOUR, and it is load-bearing twice over.

    It stops a responder that called every queue empty from passing the arm
    above, and it is also what proves the note fixture the two arms below rely
    on is actually SELECTED by `pending` rather than silently filtered out.
    """
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")

    result = _cycle(rsp, inbox, rsp.Bounds(armed=False))

    assert result["termination"] != "empty", (
        f"an inbox holding one answerable note was reported empty: {result!r}"
    )
    assert result["note"] == "2026-09-20-1200-from-RC-hello.md", result


def test_the_no_destination_gate_refuses_a_note_whose_sender_has_no_root(rsp, tmp_path):
    """GATE:no-destination. The note is selected; no root is configured for RC.

    `roots` is passed EXPLICITLY as an empty mapping, so `load_roots()` never
    runs and the host's `ops/moon_sync_repos.json` is never read.
    """
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")

    refused = _cycle(rsp, inbox, rsp.Bounds(armed=False), roots={})

    assert refused["termination"] == "no-destination", _why("no-destination", refused)
    assert refused["note"] == "2026-09-20-1200-from-RC-hello.md", refused
    assert refused["delivered"] is False, refused


def test_the_armed_gate_holds_a_deliverable_note_on_a_disarmed_cycle(rsp, tmp_path):
    """GATE:armed, and it is the NEIGHBOUR for `no-destination` at the same time.

    The only difference from the arm above is that RC now HAS a root - a
    directory under `tmp_path`, never a sibling checkout - so the cycle passes
    `no-destination` and is stopped one gate later by being disarmed. That makes
    this arm the proof that `no-destination` fired on the destination and not on
    the note, and the proof that the disarmed gate fires at all.

    It returns before `deliver` is ever called, so nothing is written into the
    root this arm supplies, and the arm asserts that.
    """
    inbox = _inbox(tmp_path, "2026-09-20-1200-from-RC-hello.md")
    root = tmp_path / "fake_rc_root"
    (root / "moon_sync_inbox").mkdir(parents=True, exist_ok=True)

    held = _cycle(rsp, inbox, rsp.Bounds(armed=False), roots={"RC": root})

    assert held["termination"] == "disarmed", _why("armed", held)
    assert held["note"] == "2026-09-20-1200-from-RC-hello.md", held
    assert held["delivered"] is False, held
    assert list((root / "moon_sync_inbox").iterdir()) == [], (
        "a DISARMED cycle wrote into the destination it was only supposed to "
        f"name: {sorted(p.name for p in (root / 'moon_sync_inbox').iterdir())}"
    )
