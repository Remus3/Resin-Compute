"""THE SKIP-then-RUN PAIR, MEASURED AT THE SITE rather than on the helper.

WHAT THIS ADDS THAT `tests/test_conftest_git_gate.py` STRUCTURALLY CANNOT.

That module grades the three helpers in `tests/conftest.py` - `classify_git_probe`,
`require_git_repository`, `skip_module_without_git` - and it grades them well. It
never launches a pytest run, so it cannot observe what a REAL guard module
actually does when git is unreachable. A helper that is correct in isolation and
a site that is correctly wired to it are two different claims, and only the
second one is what a reader of a git-less checkout experiences.

So this module runs a real guard module as its own child pytest process, TWICE:

  ABSENT   git unreachable -> the module must report SKIPPED, with the gate's own
           reason text, and must not fail or error.
  PRESENT  ordinary environment -> the SAME module must RUN ITS ASSERTIONS: zero
           skips carrying the gate reason, and a non-zero passed count.

THE RUN HALF IS THE LOAD-BEARING HALF. A skip-only arm is satisfied by a guard
welded to skip unconditionally, which is the exact repair this pair exists to
catch. An empty parametrize is "1 skipped, exit 0", so a bare exit-code
assertion proves nothing either: both halves pin actual counts, and the child is
given `-rs` so every skip has to state its reason.

WHICH SITES ARE ARMED, AND WHY NOT THE THREE THAT WERE PROPOSED.

Armed here, because each shells git directly AND routes the failure through a
gate at the site:

  - `tests/test_shell_contract.py` - IMPORT-time whole-module gate.
    `skip_module_without_git()` at line 53; git shelled at line 79.
  - `tests/test_ports.py` - RUN-time per-test gate, the narrower shape.
    `require_git_repository()` at line 137; git shelled at line 140.

Armed since 2026-09-11, and the three of them were the open defect this
docstring used to record. Each shelled git with NO gate at all - no
`require_git_repository()`, no `skip_module_without_git()`, no `pytest.skip` of
any kind - so with git unreachable each raised FileNotFoundError and reported a
FAILURE rather than a skip. Measured before the gating went in:

  - `tests/test_no_sibling_names.py`        2 failed / 17 passed
  - `tests/test_ci_workflow_complement.py`  5 failed / 29 passed
  - `tests/test_responder_gate_census.py`   1 failed / 79 passed

All three took the RUN-time shape, because in all three the git call sits inside
a test body and the great majority of each module's arms never reach git - 17 of
19, 29 of 34 and 79 of 80 respectively. An import-time whole-module skip would
have thrown those away for a dependency they do not have. Each module's own
docstring states the choice and the measured split.

A FOURTH ARMED THE SAME DAY. The sweep that produced the three above was not
exhaustive, and a second pass over the same probe found two further ungated
modules. ONE of the two is armed here and the other is NOT - the difference is
stated below rather than left as a gap in the table:

  - `tests/test_precommit_gate_corpus.py`  2 failed / 3 passed, exit 1, at
    `test_git_returns_str_on_success` and
    `test_check_staged_passes_a_clean_repo_with_nothing_staged`. Gated RUN-time
    and armed. This is also the counterexample that corrects the suppression
    rule further down: its derived facts were BIT-IDENTICAL to a correctly
    self-gated module's.

`tests/test_commit_trailers.py` IS THE OPEN ONE, AND IT IS OPEN ON A SEAM RATHER
THAN ON EFFORT. Same probe: 1 failed / 7 passed / 5 skipped, exit 1, at
`test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout`. `.git` is on
disk while the binary is missing, so it takes its CHECKOUT branch and demands a
usable git from a machine that has none. That module is already gated in four
other places; being partly gated is not being gated.

It is NOT armed here because gating that one arm reddens
`tests/test_conftest_skip_path_pinned.py`, which drives the same function
through an `_expect_assertion_error` that REJECTS `Skipped` BY NAME and pins
that any non-None reason inside a checkout must REDDEN. SIX ARMS THERE CARRY
THAT AND THEY ARE TWO POPULATIONS, not one: FIVE parametrised cases of
`test_any_non_none_reason_inside_a_checkout_reddens_even_a_falsy_one` PLUS ONE
non-parametrised arm,
`test_a_reason_inside_a_checkout_reddens_and_the_message_carries_that_reason`.
A count that merges the two decays the moment either half moves, and an earlier
version of this paragraph said "six parametrised reasons".

BOTH GATE PLACEMENTS REDDEN, AND THEY DO NOT MEASURE THE SAME. Measured over
the whole `tests` suite, 2026-09-11: INSIDE THE CHECKOUT BRANCH gives 6 failed
/ 2255 passed / 1 skipped, RETURNCODE 1, all six in that module. AT THE TOP OF
THE FUNCTION it gives 8 failed / 2253 passed / 1 skipped, RETURNCODE 1 - seven
in that module and one in `tests/test_commit_trailers.py` itself, because a gate
that fires before the `.git` probe also takes the forced-shape controls with it.

THE SEAM WAS ADJUDICATED ON 2026-09-11 AND THE OUTCOME IS: leave that arm
UNGATED and RECORD THE EXEMPTION. The rule that gated the rest of that module
covers SITES THAT SHELL GIT, and that arm shells nothing - it CONSUMES
`git_unusable_reason()` to AUDIT the helper - so the rule is already applied
there in full and the residual red is the one site OUTSIDE its population. The
record is an ARM in `tests/test_commit_trailers.py`, not a prose note, and it
pins the fact the exemption rests on. Nothing in that ruling answers the
present-but-broken-git question, which stays open.

NOT A FINDING, RECORDED SO IT IS NOT RE-CHASED. `tests/test_task_liveness.py`
reports 10 failed under the same probe and is NOT gated on that evidence.
Replacing PATH with one empty directory also hides `powershell.exe`, so that
reading is not a statement about git at all.

ONE OF THE THREE NEEDED THE GATE IN FOUR PLACES.
`tests/test_ci_workflow_complement.py` reaches git by four routes, and only one
of them is its `_git_z` helper: `_listed()` shells `tools/precommit_gate.py`,
which queries git inside the CHILD, and two arms build their own inline `git
check-ignore`. Gating the obvious helper alone would have left three of its five
nodes still failing while the table below reported the site as armed. The count
that matters is the number of FAILING NODES the absence mechanism produces, not
the number of `subprocess.run(["git", ...])` literals a grep finds.

HOW GIT IS MADE ABSENT, AND WHY THIS MECHANISM AND NOT A BORROWED ONE.

`PATH` is replaced with one empty directory, and nothing else about the
environment is touched. That must defeat BOTH lookup paths, which on Windows are
genuinely different mechanisms and are a documented trap:

  - `shutil.which("git")` walks `os.environ["PATH"]`, prepends `os.curdir` on
    Windows, and tries every `PATHEXT` suffix against each candidate. One empty
    directory plus a working directory holding no `git.*` leaves it nothing.
  - `subprocess.run(["git", ...])` never consults `PATH` in Python at all. It
    hands the command line to `CreateProcess`, which searches the launching
    executable's directory, the current directory, the system directories, and
    then `PATH`.

A borrowed PATH-strip that was only ever checked against one of those two
lookups is contraindicated here precisely because they can disagree. So the
mechanism is not reasoned about, it is MEASURED: `_absence_probe()` runs both
lookups inside a child process under the stripped environment and reports what
each one did. `test_the_absence_mechanism_hides_git_from_both_lookups` asserts
both came up empty, and its partner asserts the same probe FINDS git under the
inherited environment - without that pair, "which returned None" is
indistinguishable from a probe that never worked.

THE THIRD CASE IS DELIBERATELY NOT ARMED. Whether a PRESENT-but-BROKEN git must
FAIL rather than SKIP is an OPEN OPERATOR CALL: this tree's shipped
`classify_git_probe` returns `GIT_PROBE_DID_NOT_ANSWER` and skips, a counterparty
repo's note (LW, R3) says it must fail, and `tests/test_conftest_git_gate.py`
pins the question as open ON PURPOSE. Nothing in this module asserts either
answer. The absence mechanism above produces the not-runnable branch - the arms
check the reason text for `not runnable` exactly so a broken-git outcome could
never satisfy them by accident.

NON-VACUITY OF THE ARM ITSELF. `_present_half_problems()` is the whole PRESENT
judgement as one function over a child's output, so it can be pointed somewhere
its verdict is known. Two stub modules built in `tmp_path` do that: one welded to
skip unconditionally, which it must REPORT, and one that genuinely runs a passing
test, which it must CLEAR. Without the second, a checker armed to flag
everything would pass the first.

TWO FLOORS UNDER THE TABLE AND THE GATE, BECAUSE BOTH HOLES WERE MEASURED.

Everything above is parametrized over `_SITES` or is about the machinery, so an
adversarial mutation pass found two ways to delete the subject and stay green.
`_SITES = ()` left this module at 6 passed / 2 skipped / exit 0 and the whole
suite green - the empty-parametrize trap this docstring already names, with
nothing anywhere asserting a floor. Forcing `_mechanism_holds()` to return False
left 8 passed / 2 skipped / exit 0, the two ABSENT arms simply gone.
`test_the_site_table_is_not_empty_and_carries_both_gate_shapes` and
`test_the_absent_half_cannot_be_skipped_while_the_mechanism_actually_holds`
close those two, and neither is parametrized, on purpose.

THE FLOOR IS A CONSERVATION ASSERTION, WHICH IS WHY IT SURVIVED GROWING. When
the table went from two rows to five, a bare `len(_SITES) >= 2` would have been
satisfied by deleting three of them, and a floor naming only the two gate SHAPES
would have been satisfied by deleting any of the four run-time rows - both leave
a smaller parametrize reporting exit 0, which is not a failure. `_REQUIRED_SHAPES`
therefore names EVERY row rather than one row per shape, and the length floor is
derived from it rather than typed, so the two cannot drift apart.

THE HOLE `_REQUIRED_SHAPES` STILL LEFT, AND WHY THE REPAIR HAD TO BE DERIVED.

`_REQUIRED_SHAPES` conserves `(label, gate)` pairs and NEVER LOOKS AT
`Site.selection`. A row can therefore keep its label, keep its gate string, and
quietly stop measuring the nodes that gate protects. Measured by an adversarial
pass: deleting four of the five `ci-workflow-complement` node strings left this
module at 18 passed / exit 0 while the row reported armed over 1 of 5
git-touching nodes. Extending `_REQUIRED_SHAPES` into a hand-typed triple would
have decayed exactly the way the pair did - an enumerated list omits the
position nobody named - so `_required_nodes()` DERIVES the population from each
guard module's own source with `ast` and the table is checked against that.

WHAT IS DERIVED, AND THE RULE PER GATE SHAPE.

`_analyse_source()` builds the intra-module call graph, because REACHING IS
TRANSITIVE and two of the six gate call sites across the armed modules are
HELPERS rather than tests - `_git_z()` and `_listed()` in
`tests/test_ci_workflow_complement.py`, `_tracked_text_files()` in
`tests/test_no_sibling_names.py`, `_tracked_python_files()` in
`tests/test_responder_gate_census.py`. A test that never writes `git` and never
writes the gate's name still belongs to the population if it calls one of those.
The walk is a fixpoint over the graph, so a test reaches a fact if it calls it or
calls anything that reaches it.

Two facts are derived per function and unioned, and the union is load-bearing in
BOTH directions - each one alone has a measured blind spot:

  - GATE-REACHING - reaches a `require_git_repository()` or
    `skip_module_without_git()` call. Alone this is defeated by deleting a gate
    and its node string together: the node leaves the derived set exactly as it
    leaves the selection, and conservation holds over nothing.
  - GIT-REACHING - reaches a subprocess launch that `tools/git_subprocess_census.py`
    buckets GIT or UNRESOLVED. Alone this MISSES
    `test_the_partition_reaches_the_files_the_old_allowlist_missed`, which
    reaches git only through `_listed()` shelling `tools/precommit_gate.py`,
    which queries git inside the CHILD where no AST here can see it.

THE GIT HALF IS THE TREE'S OWN CENSUS, AND THAT IS THE SECOND REPAIR.

The first version of this derivation asked whether argv[0] was an `ast.Constant`
spelled `git` AT THE CALL SITE. An adversary defeated it in one line - a module
constant `_GIT = "git"` and `subprocess.run([_GIT, "ls-files", ...])` appended to
`tests/test_no_sibling_names.py` with no gate - and both suites stayed green
while the property was broken. The shape was never unsolved: it is resolved by
`tools/git_subprocess_census.py` and already pinned by
`tests/test_git_subprocess_census.py::test_module_level_constant_bound_list_resolves_to_git`.
A matcher that has lost once does not get widened case by case, so there is no
argv-shape logic left in this file at all - `_git_launching_functions()` calls
`census.census_source()` and attributes each site to every enclosing function.
`_GIT_BUCKETS` records the fail-closed treatment of the census's UNRESOLVED
bucket and the measurement showing it changes no armed row.

THE LIMIT OF THE GATE HALF - IT SAYS "I CANNOT GRADE THIS", NOT "THIS IS FINE".

`_GATE_CALLS` names the TWO `tests/conftest.py` helpers that actually SKIP. A
module can be correctly gated without either, by reading `git_unusable_reason()`
and raising its own `pytest.skip`. This derivation cannot see that and would
enumerate every git-touching test in such a module as ungated - all phantoms.
So both conservation arms refuse to enumerate a run-time row whose module
reaches neither recognised helper, and report `_UNRECOGNISED_GATE` once instead.

THE RULE THAT SUPPRESSION ENCODES WAS WRONG UNTIL 2026-09-11, and the correction
is the point of this paragraph. The text here used to say of such a module that
ARMING IT WOULD PRODUCE A FALSE RED. That is a claim about GROUND TRUTH, and
this derivation has no access to it. Two modules make that exact:

  - `tests/test_line_endings.py` gates itself through `_corpus_gate_reason()`
    and IS gated. With git hidden from both lookups: 16 passed / 33 skipped /
    0 failed, exit 0. This derivation calls 21 of its tests ungated - phantoms.
  - `tests/test_precommit_gate_corpus.py` had NO gate of any kind. With git
    hidden the same way: 2 failed / 3 passed, exit 1.

THAT PAIR IS A DATED READING AND NOT A PRESENT-TENSE FACT, because the same
commit that recorded it FALSIFIED ONE HALF OF IT. AS READ ON 2026-09-11 BEFORE
`tests/test_precommit_gate_corpus.py` WAS GATED, the derived facts for the two
were BIT-IDENTICAL - `module_level_gate=False` and `gate_reaching` empty for
both - while their ground truths were OPPOSITE. RE-DERIVED AFTER THE GATING, on
the same day, that module answers `gate_reaching` =
`['_init_repo', 'test_check_staged_passes_a_clean_repo_with_nothing_staged',
'test_git_returns_str_on_success']` and runs 3 passed / 2 skipped at RETURNCODE
0 under the identical probe, so it is no longer an instance of this shape at all
- it is an armed row below. `tests/test_line_endings.py` is unchanged and still
is one. The pair is kept as the RECORD of what was measured, and the finding it
carries survives its own subject moving: nothing in an AST walk over the two
files AS THEY WERE THEN separated them, and only RUNNING each one with git
hidden did. So the suppression is not a verdict of innocence and never was: it is a
refusal to print names it cannot stand behind, and the module is reported ONCE
BY NAME so that arming such a row is RED in BOTH directions. Red is the right
answer for the gated module - this derivation genuinely cannot grade it - and
the right answer for the ungated one, which is simply broken. The remedy is
therefore never "do not arm it". It is: RUN the module with git hidden, then
wire it to one of the two helpers so it can be graded. That is what was done to
`tests/test_precommit_gate_corpus.py`, which is an armed row below.

`test_a_module_gating_itself_without_the_two_helpers_is_named_not_enumerated`
pins the derivation's blindness over a stub, and
`test_the_conservation_arms_name_an_unrecognised_gate_and_still_enumerate_a_recognised_one`
INVOKES both conservation arms so the suppression branch is executed rather than
described - it asserted `_analyse_source` facts and two substrings until
2026-09-11 and never ran the branch it was named for.

RUN-TIME rule: the required set is the union above. IMPORT-TIME rule is
different and wider on purpose - a module-scope `skip_module_without_git()`
protects EVERY test in the module and takes the whole module uncollected with
it, so the required set is every test function the module defines and the row has
to select the module as a whole. `tests/test_shell_contract.py` is the only row
of that shape; 6 of its 11 tests reach git, and all 11 are required because all
11 are what the gate decides for.

Derived today, and every row covers its own set exactly: shell_contract 11 of 11
(import-time), ports 3, no_sibling_names 2, ci_workflow_complement 5,
responder_gate_census 1, precommit_gate_corpus 2. The `test_ports.py` row had
been left explicitly UNREACHED by the adversary that found the hole; the
derivation answers it - its 3 selected nodes ARE its complete git-touching set,
so nothing there was edited.

THE GIT HALF UNDER-REPORTED ON ONE OF THE TWO NEW ROWS, AND THE UNION IS WHAT
CLOSED IT. `tests/test_precommit_gate_corpus.py` had TWO failing nodes under the
absent-git probe and the census-backed git half named only ONE of them:
`test_git_returns_str_on_success` launches nothing itself, and the git it
depends on is reached inside `tools/precommit_gate.py`, a CHILD module no AST
walk over this tree's test file can read. That is the SAME blind spot already
recorded for `test_the_partition_reaches_the_files_the_old_allowlist_missed`,
and it is closed the same way: the gate call placed in that test's body puts it
into GATE-REACHING, so the union carries it even though the git half cannot.
The under-report is a property of the git half alone and is why it is never
used alone.

The derivation is pointed at stub sources whose answers are known by
`test_the_node_derivation_finds_a_transitive_gate_and_an_ungated_git_call`,
because a walk that returned the empty set for everything would satisfy any
subset assertion. The floors below also refuse an empty derived population
outright, for the same reason an empty `parametrize` is not a pass.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pytest

from tools import git_subprocess_census as census

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The sentence every gate skip in `tests/conftest.py` ends with. Matching this
#: fragment rather than a whole reason string keeps the arm a behaviour check:
#: rewording the middle of a reason stays a readability change, while dropping
#: the "SKIPPED rather than passed" contract is a behaviour change and reddens.
GATE_SKIP_MARKER = "this guard is SKIPPED rather than passed"

#: The fragment that identifies the NOT-RUNNABLE branch specifically, as opposed
#: to not-a-repository or did-not-answer. Asserting it keeps these arms silent on
#: the broken-git question, which is an open operator call.
NOT_RUNNABLE_MARKER = "git is not runnable on this machine"

#: Whether git exists at all on this host. Without it neither half of the pair
#: can be run honestly, so the whole module skips and says so. This is the one
#: place a skip is the right answer: the PRESENT half is unconditional wherever
#: git does exist.
_GIT_ON_THIS_HOST = shutil.which("git")

pytestmark = pytest.mark.skipif(
    _GIT_ON_THIS_HOST is None,
    reason=(
        "git is not on this host at all, so neither the git-absent half nor the "
        "git-present half of this pair can be run - there is nothing to make absent "
        "and nothing to prove present"
    ),
)


# ---------------------------------------------------------------------------
# Running a child pytest and reading what it reported
# ---------------------------------------------------------------------------

#: Matches the terse tail line pytest prints, e.g. `2 failed, 17 passed in 0.09s`.
_TAIL = re.compile(r"\bin \d+(?:\.\d+)?s\b")

_COUNT = re.compile(
    r"(\d+)\s+(passed|failed|skipped|errors?|xfailed|xpassed|deselected)\b"
)

_SKIPPED_HEADER = re.compile(r"SKIPPED \[(\d+)\]")


class Outcome(NamedTuple):
    """What a child pytest run reported, as counts rather than as prose."""

    returncode: int
    passed: int
    failed: int
    errors: int
    skipped: int
    gate_skips: int
    gate_skip_lines: tuple[str, ...]
    summary: str
    stdout: str


def _summary_line(stdout: str) -> str:
    """The last line carrying pytest's `in <n>s` stamp.

    `pytest.ini` already supplies `-q`, and a second `-q` on the command line
    doubles into `-qq`, which prints NO summary line at all. That has bitten this
    tree, so no invocation below adds one - the tail line is the only place the
    counts live and it must survive.
    """
    found = [line.strip().strip("=").strip() for line in stdout.splitlines() if _TAIL.search(line)]
    return found[-1] if found else ""


def _run_child_pytest(selection: tuple[str, ...], env: dict[str, str] | None) -> Outcome:
    """Run pytest as its own process over `selection` and read back its counts.

    `--tb=line` keeps a failure to one line, `-rs` forces every skip to state its
    reason, and `-p no:cacheprovider` stops the child writing a cache directory
    into the tree it is measuring. NO `-q`: see `_summary_line`.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *selection,
            "-rs",
            "--tb=line",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    stdout = completed.stdout
    summary = _summary_line(stdout)
    counts = {kind.rstrip("s") if kind.startswith("error") else kind: int(n) for n, kind in _COUNT.findall(summary)}

    gate_lines = []
    gate_skips = 0
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("SKIPPED") or GATE_SKIP_MARKER not in line:
            continue
        gate_lines.append(line)
        header = _SKIPPED_HEADER.match(line)
        gate_skips += int(header.group(1)) if header is not None else 1

    return Outcome(
        returncode=completed.returncode,
        passed=counts.get("passed", 0),
        failed=counts.get("failed", 0),
        errors=counts.get("error", 0),
        skipped=counts.get("skipped", 0),
        gate_skips=gate_skips,
        gate_skip_lines=tuple(gate_lines),
        summary=summary,
        stdout=stdout,
    )


# ---------------------------------------------------------------------------
# Making git absent, and measuring that it really is
# ---------------------------------------------------------------------------


def _absent_git_env(empty_dir: str) -> dict[str, str]:
    """The inherited environment with `PATH` replaced by one empty directory.

    Only `PATH` moves. `SystemRoot`, `PATHEXT` and the rest stay, so the child
    interpreter still starts and `shutil.which` still applies its normal
    Windows suffix rules - a stripped `PATHEXT` would weaken the probe instead of
    testing it.
    """
    env = dict(os.environ)
    env["PATH"] = empty_dir
    return env


_PROBE_SOURCE = (
    "import shutil, subprocess\n"
    "print('WHICH=' + repr(shutil.which('git')))\n"
    "try:\n"
    "    done = subprocess.run(['git', '--version'], capture_output=True)\n"
    "    print('EXEC=rc' + str(done.returncode))\n"
    "except OSError as exc:\n"
    "    print('EXEC=' + type(exc).__name__)\n"
)


class Probe(NamedTuple):
    which: str
    exec_result: str


def _probe(env: dict[str, str] | None) -> Probe:
    """Ask a child process what each of the two git lookups does under `env`."""
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE_SOURCE],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert completed.returncode == 0, (
        f"the lookup probe itself failed to run (rc {completed.returncode}), so it "
        f"measured nothing: {completed.stderr.strip()!r}"
    )
    fields = dict(
        line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line
    )
    return Probe(which=fields.get("WHICH", ""), exec_result=fields.get("EXEC", ""))


@lru_cache(maxsize=1)
def _absence_probe() -> Probe:
    with tempfile.TemporaryDirectory() as empty:
        return _probe(_absent_git_env(empty))


@lru_cache(maxsize=1)
def _mechanism_holds() -> bool:
    probe = _absence_probe()
    return probe.which == "None" and probe.exec_result == "FileNotFoundError"


def test_the_absence_mechanism_hides_git_from_both_lookups():
    """The mechanism is measured, never assumed.

    Asserted rather than skipped on purpose: if this ever goes RED the ABSENT
    arms below become vacuous, and a silent skip is exactly how that would go
    unnoticed. The message names which of the two lookups still reached git so
    the next reader does not have to re-derive it.
    """
    probe = _absence_probe()
    assert probe.which == "None", (
        "shutil.which still found git with PATH stripped to one empty directory, so "
        f"the ABSENT half cannot be trusted on this host: WHICH={probe.which}. The "
        "usual cause is a git shim on the working directory, which Windows "
        "shutil.which searches ahead of PATH."
    )
    assert probe.exec_result == "FileNotFoundError", (
        "subprocess.run(['git', ...]) still launched git with PATH stripped, so the "
        f"ABSENT half cannot be trusted on this host: EXEC={probe.exec_result}. "
        "CreateProcess searches the launching executable's directory, the current "
        "directory and the system directories before it ever looks at PATH."
    )


def test_the_lookup_probe_finds_git_under_the_inherited_environment():
    """The non-vacuity partner of the arm above.

    Without this, `WHICH=None` and `EXEC=FileNotFoundError` are equally well
    explained by a probe that never worked at all.
    """
    probe = _probe(None)
    assert probe.which != "None", (
        "the probe reported no git under the ORDINARY environment, so its negative "
        f"answer above measured the probe and not the mechanism: WHICH={probe.which}"
    )
    assert probe.exec_result == "rc0", (
        "the probe could not launch git under the ORDINARY environment, so its "
        f"FileNotFoundError above says nothing: EXEC={probe.exec_result}"
    )


def test_no_git_shim_sits_in_the_directory_the_child_runs_from():
    """Windows `shutil.which` searches the working directory first.

    The absence mechanism therefore depends on the repo root holding no `git.*`,
    and that is a fact about the tree rather than about PATH, so it is checked
    here instead of being folded into the probe's reasoning.
    """
    suffixes = tuple(
        part.lower() for part in os.environ.get("PATHEXT", ".EXE").split(os.pathsep) if part
    )
    shims = sorted(
        entry.name
        for entry in REPO_ROOT.iterdir()
        if entry.is_file() and entry.stem.lower() == "git" and entry.suffix.lower() in suffixes
    )
    assert not shims, (
        f"an executable named git sits in {REPO_ROOT}: {shims}. Windows shutil.which "
        "searches the working directory ahead of PATH, so the absence mechanism in "
        "this module cannot hold while that file is there."
    )


# ---------------------------------------------------------------------------
# The sites, and the two halves of the judgement
# ---------------------------------------------------------------------------


class Site(NamedTuple):
    """One guard module that shells git AND gates on the gate at the site."""

    label: str
    selection: tuple[str, ...]
    gate: str


_SITES: tuple[Site, ...] = (
    Site(
        label="import-time-whole-module-gate",
        selection=("tests/test_shell_contract.py",),
        gate="skip_module_without_git",
    ),
    Site(
        label="run-time-per-test-gate",
        selection=(
            "tests/test_ports.py::test_no_sibling_port_literal_appears_in_tracked_python_source",
            "tests/test_ports.py::test_the_guard_is_not_vacuous",
            "tests/test_ports.py::test_the_swept_file_list_is_git_derived_and_not_a_disk_walk",
        ),
        gate="require_git_repository",
    ),
    Site(
        label="run-time-per-test-gate-no-sibling-names",
        selection=(
            "tests/test_no_sibling_names.py"
            "::test_the_corpus_is_not_empty_before_anything_is_asserted_about_it",
            "tests/test_no_sibling_names.py::test_no_tracked_file_names_a_sibling_project",
        ),
        gate="require_git_repository",
    ),
    Site(
        label="run-time-per-test-gate-ci-workflow-complement",
        selection=(
            "tests/test_ci_workflow_complement.py"
            "::test_the_two_ascii_gates_cover_every_tracked_file_between_them",
            "tests/test_ci_workflow_complement.py"
            "::test_the_partition_reaches_the_files_the_old_allowlist_missed",
            "tests/test_ci_workflow_complement.py"
            "::test_no_exempt_prefix_names_a_path_that_can_actually_be_committed",
            "tests/test_ci_workflow_complement.py"
            "::test_the_gitignore_probe_actually_distinguishes_ignored_from_tracked",
            "tests/test_ci_workflow_complement.py"
            "::test_the_suite_split_is_load_bearing_and_not_decoration",
        ),
        gate="require_git_repository",
    ),
    Site(
        label="run-time-per-test-gate-responder-gate-census",
        selection=(
            "tests/test_responder_gate_census.py"
            "::test_the_gate_tag_population_across_the_tracked_corpus_is_derived_not_asserted",
        ),
        gate="require_git_repository",
    ),
    Site(
        label="run-time-per-test-gate-precommit-gate-corpus",
        selection=(
            "tests/test_precommit_gate_corpus.py::test_git_returns_str_on_success",
            "tests/test_precommit_gate_corpus.py"
            "::test_check_staged_passes_a_clean_repo_with_nothing_staged",
        ),
        gate="require_git_repository",
    ),
)

_SITE_IDS = [site.label for site in _SITES]

#: EVERY site the table is required to carry, as (label, gate) pairs read off the
#: table above. Held as a separate constant so the floor arm below reddens on a
#: table that was EMPTIED, on one quietly collapsed to copies of a single shape,
#: and - because this list names every row rather than one row per shape - on one
#: that simply DROPPED a site. All three leave every parametrized arm reporting a
#: skip or reporting fewer cases at exit 0, which is not a failure.
#:
#: A CONSERVATION ASSERTION IS THE ONLY SHAPE THAT CATCHES A DROP. A floor on
#: `len(_SITES)` alone is satisfied by deleting one row and duplicating another,
#: and a floor on the two SHAPES alone is satisfied by deleting any of the four
#: run-time rows. Naming every row closes both.
_REQUIRED_SHAPES = (
    ("import-time-whole-module-gate", "skip_module_without_git"),
    ("run-time-per-test-gate", "require_git_repository"),
    ("run-time-per-test-gate-no-sibling-names", "require_git_repository"),
    ("run-time-per-test-gate-ci-workflow-complement", "require_git_repository"),
    ("run-time-per-test-gate-responder-gate-census", "require_git_repository"),
    ("run-time-per-test-gate-precommit-gate-corpus", "require_git_repository"),
)


def test_the_site_table_is_not_empty_and_carries_both_gate_shapes():
    """THE FLOOR UNDER THE TABLE. Without it, deleting `_SITES` is GREEN.

    Measured by an adversarial mutation pass: `_SITES = ()` left this module at
    6 passed / 2 skipped / exit 0 and the whole suite green. An empty
    `parametrize` is ONE SKIPPED and exit 0, never a failure - the exact trap
    this module's own docstring names - and every other arm here is either
    parametrized over `_SITES` or about the machinery, so nothing could notice
    the module's whole subject disappearing. This arm is deliberately NOT
    parametrized: an arm that iterates the table it is defending cannot defend an
    empty one.
    """
    assert len(_SITES) >= len(_REQUIRED_SHAPES), (
        f"the site table holds fewer than {len(_REQUIRED_SHAPES)} sites, so at least "
        "one armed site is no longer measured and the parametrized arms in this "
        "module degenerate towards a skip with exit 0 - which is not a failure and "
        f"would be read as a pass: {_SITE_IDS}"
    )
    present = {(site.label, site.gate) for site in _SITES}
    missing = [pair for pair in _REQUIRED_SHAPES if pair not in present]
    assert not missing, (
        "the site table no longer carries every site it is required to carry, so "
        "this pair is measuring fewer sites - or one shape twice - while still "
        f"reporting parametrized cases: missing {missing}, present {sorted(present)}"
    )
    assert len(set(_SITE_IDS)) == len(_SITE_IDS), (
        "two sites share a parametrize id, so the report cannot say which shape "
        f"was measured: {_SITE_IDS}"
    )


# ---------------------------------------------------------------------------
# The derived node population, and the two floors that use it
# ---------------------------------------------------------------------------

#: The two gate helpers in `tests/conftest.py`. A call to either is what makes a
#: function GATE-REACHING. Held as a constant so the non-vacuity stub arms below
#: can be read against the same names the real modules import.
#:
#: THE LIMIT, NAMED RATHER THAN IMPLIED. `tests/conftest.py` exports FOUR git
#: helpers and `census.GUARD_NAMES` enumerates all four, but only these TWO
#: decide a skip. `git_unusable_reason` and `classify_git_probe` PRODUCE A
#: REASON and skip nothing on their own, so a test that merely asks either one
#: the question is not thereby gated, and folding them in here would let exactly
#: that shape read as gated. See `_UNRECOGNISED_GATE` for what this costs and
#: for the module where it was measured.
_GATE_CALLS = frozenset({"require_git_repository", "skip_module_without_git"})

#: WHAT THIS DERIVATION CANNOT SEE, STATED AT THE SITE THAT WOULD OVER-FIRE.
#:
#: A module may gate itself perfectly well WITHOUT calling either helper above -
#: by asking `git_unusable_reason()` and raising its own `pytest.skip`. Both
#: arms below would then enumerate every git-touching test in it as ungated,
#: and every one of those names would be a PHANTOM.
#:
#: MEASURED IN BOTH DIRECTIONS ON 2026-09-11, AND WHAT FOLLOWS IS THAT DATED
#: READING RATHER THAN A STANDING PROPERTY OF EITHER FILE. As read BEFORE
#: `tests/test_precommit_gate_corpus.py` was gated, the derived facts were
#: BIT-IDENTICAL for these two modules - `module_level_gate` False,
#: `gate_reaching` empty - while their ground truths were opposite:
#:
#:   - `tests/test_line_endings.py` gates itself through `_corpus_gate_reason()`
#:     and IS gated. Git hidden from both lookups: 16 passed / 33 skipped / 0
#:     failed, exit 0. This derivation would name 21 of its tests - phantoms.
#:   - `tests/test_precommit_gate_corpus.py` had NO gate at all. Git hidden the
#:     same way: 2 failed / 3 passed, exit 1. Two real defects, and this
#:     derivation's git half named only ONE of them, because the other reaches
#:     git inside `tools/precommit_gate.py` - a CHILD module no AST here reads.
#:
#: THE SECOND OF THE TWO HAS SINCE MOVED, which is why the dating above matters.
#: It was gated the same day and is an armed row now: re-derived, its
#: `gate_reaching` is NON-EMPTY and it runs 3 passed / 2 skipped at RETURNCODE 0
#: under the identical probe. Re-derive before citing either line as current -
#: only `tests/test_line_endings.py` is still an instance of this shape.
#:
#: SO THE SUPPRESSION IS NOT A VERDICT OF INNOCENCE. An earlier version of this
#: text said arming such a module WOULD PRODUCE A FALSE RED; that is a claim
#: about ground truth, and the second module above refutes it - arming it would
#: have produced a TRUE red, and declining to arm it removed the only arm that
#: would have caught it. Corrected 2026-09-11.
#:
#: What the suppression actually does is REFUSE TO ENUMERATE, because every name
#: it could print might be a phantom, and report the module ONCE BY NAME so that
#: arming such a row is RED EITHER WAY. That is the correct outcome for both: the
#: self-gated module cannot be graded here, and the ungated one is broken. The
#: remedy is never "do not arm it" - it is RUN the module with git hidden, then
#: wire it to a recognised helper so it can be graded.
#:
#: The suppression still cannot hide a partial regression: a module that has lost
#: only SOME of its gate calls keeps a non-empty `gate_reaching` set and is
#: enumerated exactly as before.
_UNRECOGNISED_GATE = (
    "reaches neither require_git_repository() nor skip_module_without_git(), the "
    "only two skip-deciding helpers this derivation recognises, so it cannot be "
    "GRADED here - which is not the same as being FINE here. These same two "
    "derived facts are produced by a module that gates itself by another route "
    "and by a module with no gate at all: tests/test_line_endings.py builds its "
    "own skip from git_unusable_reason() inside _corpus_gate_reason() and reports "
    "16 passed / 33 skipped / 0 failed with git hidden from both lookups, while "
    "tests/test_precommit_gate_corpus.py had no gate at all and reported 2 failed "
    "/ 3 passed under the identical probe. Only RUNNING the module separates "
    "them. So do not read this as permission to leave the row unarmed: run it "
    "with git hidden from both lookups, then wire it to one of the two helpers so "
    "it can be graded"
)


class SourceFacts(NamedTuple):
    """What one guard module's own source says about how it reaches git.

    `tests` is every function whose name starts with `test_`, wherever it is
    defined - a method on a class counts, because pytest collects it.
    """

    tests: frozenset[str]
    gate_reaching: frozenset[str]
    git_reaching: frozenset[str]
    module_level_gate: bool
    duplicate_names: tuple[str, ...]


def _direct_call_names(node: ast.AST) -> set[str]:
    """Every bare-name call under `node`, nested definitions included.

    Descending into nested definitions is deliberate and conservative: a helper
    defined inside a test and called there would otherwise drop the edge.
    """
    return {
        sub.func.id
        for sub in ast.walk(node)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
    }


#: The census buckets that count as REACHING GIT here.
#:
#: `census.GIT` is a launch whose argv[0] statically resolved to a git
#: executable. `census.UNRESOLVED` is folded in FAIL-CLOSED, and that call was
#: MEASURED rather than taken on principle, because fail-closed is also the
#: reading most likely to invent a requirement. Across the five armed modules
#: the census reports ZERO unresolved launch sites, so open and closed derive
#: the IDENTICAL required set for every one of the five rows - not one row gains
#: a requirement, not one loses a node. Measured 2026-09-11. The only module in
#: reach where the two readings differ at all is `tests/test_line_endings.py` -
#: 21 tests closed against 14 open, through its `_launch_git` helper whose argv
#: is a parameter - and it is not an armed row. Closed is therefore free today
#: and is the only reading under which a launch the census cannot answer for
#: leaves the population LOUDLY rather than silently.
_GIT_BUCKETS = frozenset({census.GIT, census.UNRESOLVED})


def _git_launching_functions(tree: ast.AST, source: str) -> frozenset[str]:
    """Every function whose span holds a git-reaching subprocess launch.

    THE RESOLVER IS `tools/git_subprocess_census.py`, NOT A SECOND MATCHER HERE.
    The version this replaces required argv[0] to be an `ast.Constant` spelled
    `git` AT THE CALL SITE, and an adversary defeated it in one line with a
    module constant - `_GIT = "git"` and `subprocess.run([_GIT, "ls-files", ...])`
    - added to `tests/test_no_sibling_names.py` with no gate. Both suites stayed
    green while the property was broken. That shape is not hypothetical and was
    never unsolved: `census._resolve_head` walks the binding chain through it,
    and `tests/test_git_subprocess_census.py::
    test_module_level_constant_bound_list_resolves_to_git` already pinned the
    behaviour over a `MODULE_CONSTANT_ARGV` fixture. A local matcher widened
    case by case would have been the SECOND widening of a matcher that had
    already lost once, so the repair is reuse and there is deliberately no
    argv-shape logic left in this file.

    What reuse buys beyond the one mutant: a name bound in any visible scope, a
    parameter that shadows a module constant, `shell=True` whole-command
    strings, `git.exe` and absolute paths with spaces in them, `Popen` and the
    other three launchers, and `from subprocess import run as ...`. What it
    still cannot see is git reached inside a CHILD process, which is why this
    fact is only ever unioned with the gate-reaching one and never used alone.

    Attribution is to EVERY enclosing function, which is what the `ast.walk` it
    replaces did: a launch inside a helper nested in a test is reached by both,
    and dropping the outer one would cut a real call edge. A decorator
    expression sits at a line BEFORE its `FunctionDef.lineno`, so it falls
    outside every span - correct, since it is evaluated in the enclosing scope.
    """
    lines = {
        site.lineno
        for site in census.census_source(source, "<derivation>")
        if site.bucket in _GIT_BUCKETS
    }
    if not lines:
        return frozenset()
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", None) or node.lineno
        if any(node.lineno <= line <= end for line in lines):
            names.add(node.name)
    return frozenset(names)


def _analyse_source(source: str) -> SourceFacts:
    """Derive the git facts of one module from its text.

    A pure function of the source so it can be pointed at stub modules whose
    answers are already known - see the non-vacuity arm below.

    The closure is a fixpoint rather than a recursion, so a cyclic call graph
    terminates instead of blowing the stack.
    """
    tree = ast.parse(source)

    definitions: dict[str, ast.AST] = {}
    duplicates: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in definitions:
                duplicates.append(node.name)
            definitions[node.name] = node

    module_level_gate = any(
        _direct_call_names(stmt) & _GATE_CALLS
        for stmt in tree.body
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )

    calls = {name: _direct_call_names(node) for name, node in definitions.items()}
    gate_seed = {name for name, called in calls.items() if called & _GATE_CALLS}
    git_seed = set(_git_launching_functions(tree, source))

    def _closure(seed: set[str]) -> frozenset[str]:
        reaching = set(seed)
        changed = True
        while changed:
            changed = False
            for name, called in calls.items():
                if name not in reaching and called & reaching:
                    reaching.add(name)
                    changed = True
        return frozenset(reaching)

    return SourceFacts(
        tests=frozenset(name for name in definitions if name.startswith("test_")),
        gate_reaching=_closure(gate_seed),
        git_reaching=_closure(git_seed),
        module_level_gate=module_level_gate,
        duplicate_names=tuple(sorted(set(duplicates))),
    )


#: Sized rather than unbounded: the table names a handful of modules, and
#: `maxsize=None` is the one spelling `ruff` rejects here (UP033).
@lru_cache(maxsize=16)
def _module_facts(relative_path: str) -> SourceFacts:
    return _analyse_source((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _required_nodes(facts: SourceFacts) -> frozenset[str]:
    """The test functions the gate in that module decides for.

    IMPORT-TIME shape - a module-scope gate call - protects EVERY test in the
    module and takes the whole module uncollected with it, so all of them are
    required. RUN-TIME shape - the gate called from inside a test or a helper -
    requires the union of the gate-reaching and the git-reaching tests; the
    module docstring records the measured blind spot each of those has alone.
    """
    if facts.module_level_gate:
        return facts.tests
    return frozenset(facts.tests & (facts.gate_reaching | facts.git_reaching))


def _selected_nodes(site: Site) -> dict[str, frozenset[str] | None]:
    """The row's selection as `module path -> selected test names`.

    `None` means the entry named the module with no `::`, which selects every
    test in it. A parametrized id keeps only the part before `[`.
    """
    selected: dict[str, frozenset[str] | None] = {}
    for entry in site.selection:
        head, _, tail = entry.partition("::")
        path = head.replace("\\", "/")
        if not tail:
            selected[path] = None
            continue
        if path in selected and selected[path] is None:
            continue
        name = tail.split("::")[-1].split("[")[0]
        current = selected.get(path) or frozenset()
        selected[path] = frozenset(current) | {name}
    return selected


def test_every_git_touching_node_in_an_armed_module_is_covered_by_its_row():
    """CONSERVATION OVER `Site.selection`, which `_REQUIRED_SHAPES` never reads.

    The floor above conserves `(label, gate)` pairs. A row can keep both and
    quietly stop measuring the nodes its gate protects: deleting four of the five
    `ci-workflow-complement` node strings left this module at 18 passed / exit 0
    with the row still reporting armed over 1 of 5 git-touching nodes.

    So the population is DERIVED from each guard module's own source rather than
    re-typed here - a hand-typed triple would decay the way the pair did - and
    every derived node has to appear in the row that claims to measure it. Not
    parametrized, and it pins how many modules it examined, because an arm that
    only iterates the table cannot notice the table shrinking.
    """
    problems: list[str] = []
    examined = 0
    for site in _SITES:
        selected = _selected_nodes(site)
        for path in sorted(selected):
            examined += 1
            facts = _module_facts(path)
            required = _required_nodes(facts)
            chosen = selected[path]
            if facts.duplicate_names:
                problems.append(
                    f"{path}: two functions share a name {facts.duplicate_names}, so a "
                    "node id there does not identify one test and this derivation "
                    "cannot be trusted"
                )
            if not required:
                problems.append(
                    f"{site.label}: {path} derives ZERO git-touching test nodes, so "
                    "this row's conservation check has no subject at all - an empty "
                    "required set is covered by any selection, including none"
                )
                continue
            if facts.module_level_gate and chosen is not None:
                problems.append(
                    f"{site.label}: {path} carries a MODULE-SCOPE gate, which decides "
                    f"collection for all {len(facts.tests)} of its tests, but the row "
                    f"names only {sorted(chosen)} - the rest go unmeasured"
                )
                continue
            if not facts.module_level_gate and not facts.gate_reaching:
                problems.append(f"{site.label}: {path} {_UNRECOGNISED_GATE}")
                continue
            if chosen is None:
                continue
            missing = sorted(required - chosen)
            if missing:
                problems.append(
                    f"{site.label}: {path} has {len(required)} test node(s) that reach "
                    f"git or its gate, and the row selects {len(chosen)} of them - "
                    f"unmeasured: {missing}"
                )
    assert not problems, (
        "a row in `_SITES` no longer covers the nodes its gate protects, so this pair "
        "reports the site as armed while measuring less than it claims:\n  "
        + "\n  ".join(problems)
    )
    assert examined >= len(_REQUIRED_SHAPES), (
        f"only {examined} guard module(s) were examined for {len(_REQUIRED_SHAPES)} "
        "required rows, so the table shrank under this arm rather than reddening it: "
        f"{_SITE_IDS}"
    )


def test_every_git_touching_node_in_an_armed_module_actually_reaches_a_gate():
    """The other half: being SELECTED is not being GATED.

    Conservation alone is defeated by deleting a gate call and its node string
    TOGETHER - the node leaves the derived set exactly as it leaves the
    selection. Measured: dropping `require_git_repository()` from
    `test_the_gitignore_probe_actually_distinguishes_ignored_from_tracked` and
    its node string from the row broke the property under an absent git - that
    module went to 1 failed / 29 passed / 4 skipped - while this module stayed at
    18 passed and the whole suite stayed green.

    A test that shells git literally must therefore reach a gate, whether or not
    anyone remembered to select it.
    """
    problems: list[str] = []
    examined = 0
    for site in _SITES:
        for path in sorted(_selected_nodes(site)):
            examined += 1
            facts = _module_facts(path)
            if not facts.tests & (facts.gate_reaching | facts.git_reaching):
                problems.append(
                    f"{site.label}: {path} derives ZERO gated-or-git-touching tests, so "
                    "this arm examined nothing there"
                )
            if facts.module_level_gate:
                continue
            if not facts.gate_reaching:
                problems.append(f"{site.label}: {path} {_UNRECOGNISED_GATE}")
                continue
            ungated = sorted((facts.tests & facts.git_reaching) - facts.gate_reaching)
            if ungated:
                problems.append(
                    f"{site.label}: {path} shells git from {ungated} with no "
                    f"{site.gate}() on any path to it, so those nodes FAIL rather than "
                    "skip when git is unreachable"
                )
    assert not problems, (
        "a node in an armed module reaches git without reaching the gate that is "
        "supposed to carry the failure:\n  " + "\n  ".join(problems)
    )
    assert examined >= len(_REQUIRED_SHAPES), (
        f"only {examined} guard module(s) were examined for {len(_REQUIRED_SHAPES)} "
        f"required rows: {_SITE_IDS}"
    )


_TRANSITIVE_GATE_STUB = """
import subprocess


def _helper():
    require_git_repository()
    return subprocess.run(["git", "ls-files"], capture_output=True)


def test_reaches_the_gate_only_through_the_helper():
    assert _helper() is not None


def test_touches_nothing():
    assert True
"""

_UNGATED_GIT_STUB = """
import subprocess


def test_shells_git_with_no_gate_anywhere():
    subprocess.run(["git", "ls-files"], capture_output=True)


def test_touches_nothing():
    assert True
"""

_IMPORT_TIME_STUB = """
import subprocess

skip_module_without_git()


def test_shells_git():
    subprocess.run(["git", "ls-files"], capture_output=True)


def test_touches_nothing():
    assert True
"""


def test_the_node_derivation_finds_a_transitive_gate_and_an_ungated_git_call():
    """NON-VACUITY OF THE DERIVATION ITSELF.

    A walk that returned the empty set for every module would satisfy any subset
    assertion - `required - chosen` is empty for an empty `required` - which is
    why both floors above also refuse an empty population outright. This arm
    points `_analyse_source()` at three stub sources whose answers are known by
    construction, so the walk has to actually follow a TRANSITIVE edge, has to
    notice git shelled with no gate anywhere, and has to apply the wider
    import-time rule only where a module-scope gate call really is present.
    """
    transitive = _analyse_source(_TRANSITIVE_GATE_STUB)
    assert {"_helper", "test_reaches_the_gate_only_through_the_helper"} <= (
        transitive.gate_reaching
    ), (
        "the walk did not follow the call edge from a test into the helper holding "
        "the gate, so the real gate sites that live on helpers are invisible to it: "
        f"{sorted(transitive.gate_reaching)}"
    )
    assert "test_touches_nothing" not in transitive.gate_reaching, (
        "the walk marked a test that calls nothing as gate-reaching, so it is armed "
        f"to mark everything: {sorted(transitive.gate_reaching)}"
    )
    assert not transitive.module_level_gate, (
        "a gate called only from inside a helper was read as a MODULE-SCOPE gate, "
        "which would widen every run-time row to its whole module"
    )
    assert _required_nodes(transitive) == {
        "test_reaches_the_gate_only_through_the_helper"
    }, (
        "the run-time rule did not resolve to exactly the transitively gated test: "
        f"{sorted(_required_nodes(transitive))}"
    )

    ungated = _analyse_source(_UNGATED_GIT_STUB)
    assert ungated.git_reaching == {"test_shells_git_with_no_gate_anywhere"}, (
        "the git detector did not find a plain ['git', ...] argument vector, or found "
        f"one where there is none: {sorted(ungated.git_reaching)}"
    )
    assert not ungated.gate_reaching, (
        "a module with no gate call anywhere was reported as gate-reaching: "
        f"{sorted(ungated.gate_reaching)}"
    )

    import_time = _analyse_source(_IMPORT_TIME_STUB)
    assert import_time.module_level_gate, (
        "a module-scope gate call was not seen, so the import-time row would be graded "
        "by the narrower run-time rule and its ungated tests would be required to "
        "reach a gate they never call"
    )
    assert _required_nodes(import_time) == {"test_shells_git", "test_touches_nothing"}, (
        "the import-time rule did not require EVERY test in a module-scope-gated "
        f"module: {sorted(_required_nodes(import_time))}"
    )


_MODULE_CONSTANT_GIT_STUB = """
import subprocess

_GIT = "git"


def test_shells_git_through_a_module_constant():
    subprocess.run([_GIT, "ls-files"], capture_output=True)


def test_touches_nothing():
    assert True
"""

_SPLATTED_GIT_STUB = """
import subprocess

_GIT_LS = ("git", "ls-files")


def test_shells_git_through_a_splat():
    subprocess.run([*_GIT_LS, "--error-unmatch", "x"], capture_output=True)


def test_touches_nothing():
    assert True
"""

_GIT_ONLY_IN_A_STRING_STUB = """
import re
import subprocess

_PATTERN = re.compile(r"git log")


def test_only_mentions_git_inside_a_string():
    assert _PATTERN.search('subprocess.run(["git", "log"])')


def test_touches_nothing():
    assert True
"""

_SELF_GATED_STUB = """
import pytest
import subprocess

from tests.conftest import git_unusable_reason


def _own_gate():
    reason = git_unusable_reason()
    if reason is not None:
        pytest.skip(reason)


def test_gates_itself_then_shells_git():
    _own_gate()
    subprocess.run(["git", "ls-files"], capture_output=True)
"""


def test_the_resolver_sees_the_shapes_a_call_site_literal_matcher_misses():
    """NON-VACUITY OF THE CENSUS-BACKED RESOLVER, in both directions.

    The matcher this replaced asked whether argv[0] was an `ast.Constant`
    spelled `git` AT THE CALL SITE. An adversary killed it with a module
    constant in one line, and both suites stayed green. So the two shapes that
    defeat a call-site literal are pinned here directly, over stubs whose
    answers are known by construction rather than over the tree:

      - a name bound to `"git"` at module scope, the exact mutant;
      - a splatted sequence, where argv[0] is an `ast.Starred` the census
        cannot resolve at all and `_GIT_BUCKETS` therefore takes FAIL-CLOSED.
        This arm is the only place that decision is load-bearing, which is why
        it is stated as a measurement at `_GIT_BUCKETS` and tested here.

    And the other direction, which is what stops the answer being "call
    everything git-reaching": a module whose only `git` and only
    `subprocess.run` are TEXT INSIDE A STRING LITERAL launches nothing, and an
    AST census never parses the contents of a string. That is the shape
    `tools/git_subprocess_census.py` exists to keep out of a population, and a
    resolver that flagged it would put a false requirement on any row.
    """
    constant = _analyse_source(_MODULE_CONSTANT_GIT_STUB)
    assert constant.git_reaching == {"test_shells_git_through_a_module_constant"}, (
        "the resolver did not follow a module constant into argv[0], which is the "
        "exact one-line mutant that defeated the matcher this replaced and left "
        f"both suites green: {sorted(constant.git_reaching)}"
    )

    splatted = _analyse_source(_SPLATTED_GIT_STUB)
    assert splatted.git_reaching == {"test_shells_git_through_a_splat"}, (
        "a splatted argv - argv[0] an ast.Starred, which the census reports "
        "UNRESOLVED - did not land in the git-reaching population, so the "
        "FAIL-CLOSED reading recorded at _GIT_BUCKETS is not actually in force: "
        f"{sorted(splatted.git_reaching)}"
    )

    textual = _analyse_source(_GIT_ONLY_IN_A_STRING_STUB)
    assert not textual.git_reaching, (
        "a module whose only git and only subprocess.run are TEXT INSIDE A STRING "
        "was called git-reaching, so the resolver has widened into a grep and would "
        f"put a false requirement on any row naming such a module: {sorted(textual.git_reaching)}"
    )


def test_a_module_gating_itself_without_the_two_helpers_is_named_not_enumerated():
    """THE DECLARED LIMIT, PINNED AS A MEASUREMENT INSTEAD OF AS PROSE.

    `_GATE_CALLS` names the two `tests/conftest.py` helpers that SKIP, and a
    module can gate itself correctly without either - by reading
    `git_unusable_reason()` and raising its own `pytest.skip`. This derivation
    is BLIND to that, and the blindness over-fires: it would enumerate every
    git-touching test in such a module as ungated, and every name would be a
    phantom. `tests/test_line_endings.py` is that shape today through
    `_corpus_gate_reason()`, it reports 16 passed / 33 skipped / 0 failed with
    git hidden from both lookups, and it is deliberately NOT an armed row.

    A comment saying so would decay. This arm pins the two halves that matter:
    the blindness is real, so nobody arms such a row expecting it to be graded;
    and `_UNRECOGNISED_GATE` is what the arms above say when it happens, so the
    next reader gets ONE named cause rather than a list of phantoms.
    """
    facts = _analyse_source(_SELF_GATED_STUB)
    assert not facts.gate_reaching, (
        "a module gating itself through git_unusable_reason() plus its own "
        "pytest.skip was read as reaching one of the two skip-deciding helpers, "
        "so _GATE_CALLS has been widened past what it can honestly claim: "
        f"{sorted(facts.gate_reaching)}"
    )
    assert facts.git_reaching == {"test_gates_itself_then_shells_git"}, (
        "the git half of the derivation did not see the launch, so this arm is not "
        f"actually demonstrating the over-fire it exists to bound: {sorted(facts.git_reaching)}"
    )
    assert _required_nodes(facts) == {"test_gates_itself_then_shells_git"}, (
        "the over-fire this limit describes did not reproduce, so the text at "
        "_UNRECOGNISED_GATE no longer matches the derivation it is explaining: "
        f"{sorted(_required_nodes(facts))}"
    )
    assert "git_unusable_reason" in _UNRECOGNISED_GATE, (
        "the message the two arms above emit for an unrecognised gate no longer "
        "names the mechanism a module can gate itself with, so a row armed by "
        f"mistake reports a cause nobody can act on: {_UNRECOGNISED_GATE!r}"
    )
    assert "not the same as being FINE here" in _UNRECOGNISED_GATE, (
        "the message no longer says that an unrecognised gate means UNGRADED "
        "rather than INNOCENT. That exact reading shipped here as 'arming it "
        "would produce a FALSE red' and was refuted by "
        "tests/test_precommit_gate_corpus.py, where arming produced a TRUE red "
        f"over two genuinely ungated nodes: {_UNRECOGNISED_GATE!r}"
    )
    assert "run it" in _UNRECOGNISED_GATE.lower() and (
        "wire it to one of the two helpers" in _UNRECOGNISED_GATE
    ), (
        "the message no longer tells the reader the remedy - MEASURE the module "
        "with git hidden, then wire it to a recognised helper. Without both, the "
        f"text reads as permission to leave the row unarmed: {_UNRECOGNISED_GATE!r}"
    )


_SELF_GATED_PAIR_STUB = """
import pytest
import subprocess

from tests.conftest import git_unusable_reason


def _own_gate():
    reason = git_unusable_reason()
    if reason is not None:
        pytest.skip(reason)


def test_gates_itself_then_shells_git_once():
    _own_gate()
    subprocess.run(["git", "ls-files"], capture_output=True)


def test_gates_itself_then_shells_git_twice():
    _own_gate()
    subprocess.run(["git", "log"], capture_output=True)
"""

_PARTIALLY_GATED_PAIR_STUB = """
import subprocess

from tests.conftest import require_git_repository


def test_gated_and_shells_git():
    require_git_repository()
    subprocess.run(["git", "ls-files"], capture_output=True)


def test_ungated_and_shells_git():
    subprocess.run(["git", "log"], capture_output=True)
"""

#: Labels, not files. `_module_facts` is replaced for the duration of the arm
#: below, so nothing at either path is ever opened - and neither path exists, on
#: purpose, so a reader cannot mistake these rows for real ones.
_SUPPRESSED_STUB_PATH = "tests/synthetic_self_gated_pair_stub.py"
_ENUMERATED_STUB_PATH = "tests/synthetic_partially_gated_pair_stub.py"


def _conservation_arm_messages(
    monkeypatch: pytest.MonkeyPatch, path: str, source: str, selected: str
) -> tuple[SourceFacts, list[str]]:
    """EXECUTE both conservation arms over one synthetic row and read what they said.

    The whole point is that the arms are CALLED. Asserting on `_analyse_source`
    facts grades the derivation; only invoking
    `test_every_git_touching_node_in_an_armed_module_is_covered_by_its_row` and
    `test_every_git_touching_node_in_an_armed_module_actually_reaches_a_gate`
    grades the branch inside them that decides between naming a module and
    enumerating its tests.

    `_SITES` is replaced with the single row, and `_module_facts` with a constant
    function, so `path` is a label rather than a file and the arms are pointed at
    a source whose answers are known by construction.
    """
    facts = _analyse_source(source)
    row = Site(
        label="synthetic-probe-row",
        selection=(f"{path}::{selected}",),
        gate="require_git_repository",
    )
    monkeypatch.setattr(sys.modules[__name__], "_module_facts", lambda relative: facts)
    monkeypatch.setattr(sys.modules[__name__], "_SITES", (row,))

    messages = []
    for arm in (
        test_every_git_touching_node_in_an_armed_module_is_covered_by_its_row,
        test_every_git_touching_node_in_an_armed_module_actually_reaches_a_gate,
    ):
        with pytest.raises(AssertionError) as raised:
            arm()
        messages.append(str(raised.value))
    return facts, messages


def test_the_conservation_arms_name_an_unrecognised_gate_and_still_enumerate_a_recognised_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE SUPPRESSION BRANCH, EXECUTED. It was described by no test until now.

    `test_a_module_gating_itself_without_the_two_helpers_is_named_not_enumerated`
    asserts `_analyse_source` facts plus substrings of `_UNRECOGNISED_GATE`. It
    never invokes either conservation arm, so the "named, not enumerated" half of
    its own name was pinned by nothing: delete the two `if not
    facts.gate_reaching:` blocks and it stays GREEN while both arms go back to
    printing phantoms.

    So this arm drives both of them, over two stubs whose verdicts are opposite:

      - SUPPRESSED - a module that gates itself through `git_unusable_reason()`.
        Both arms must emit `_UNRECOGNISED_GATE` and must name NO test function,
        because every name they could print there is a phantom.
      - ENUMERATED - the non-vacuity partner, and without it a suppression welded
        to fire unconditionally would satisfy the half above. One test is gated
        with `require_git_repository()` and the other shells git bare, so the
        module IS recognised and both arms must name the bare one.

    Both stubs under-select on purpose: the row names one of the two tests, so a
    suppression that stopped firing has something concrete to enumerate and the
    difference between the two halves is a difference in OUTPUT, not in whether
    an arm raised.
    """
    suppressed_facts, suppressed = _conservation_arm_messages(
        monkeypatch,
        _SUPPRESSED_STUB_PATH,
        _SELF_GATED_PAIR_STUB,
        "test_gates_itself_then_shells_git_once",
    )
    assert not suppressed_facts.gate_reaching, (
        "the suppressed stub reaches a recognised helper after all, so this half is "
        f"not driving the branch it names: {sorted(suppressed_facts.gate_reaching)}"
    )
    assert len(suppressed_facts.tests & suppressed_facts.git_reaching) == 2, (
        "the suppressed stub does not derive TWO git-reaching tests, so there is no "
        "phantom list for the suppression to be suppressing and this half would pass "
        f"over nothing: {sorted(suppressed_facts.tests & suppressed_facts.git_reaching)}"
    )
    for message in suppressed:
        assert _UNRECOGNISED_GATE in message, (
            "a conservation arm did not report the unrecognised gate by name for a "
            "module that reaches neither helper, so the suppression branch is not "
            f"executing: {message!r}"
        )
        leaked = sorted(name for name in suppressed_facts.tests if name in message)
        assert not leaked, (
            "a conservation arm named individual test functions of a module it cannot "
            "grade. Every one of those names is a PHANTOM - the module may well be "
            f"gated by a route this derivation cannot see: {leaked}"
        )

    enumerated_facts, enumerated = _conservation_arm_messages(
        monkeypatch,
        _ENUMERATED_STUB_PATH,
        _PARTIALLY_GATED_PAIR_STUB,
        "test_gated_and_shells_git",
    )
    assert enumerated_facts.gate_reaching == {"test_gated_and_shells_git"}, (
        "the partially gated stub does not reach a recognised helper from exactly one "
        "of its two tests, so the control below is not the shape it claims: "
        f"{sorted(enumerated_facts.gate_reaching)}"
    )
    for message in enumerated:
        assert _UNRECOGNISED_GATE not in message, (
            "a conservation arm suppressed a module that DOES reach "
            "require_git_repository(), so the suppression has widened into a blanket "
            f"refusal and grades nothing at all: {message!r}"
        )
        assert "test_ungated_and_shells_git" in message, (
            "a conservation arm did not name the one test that shells git with no gate "
            "on any path to it, so the enumeration the suppression is carved out of no "
            f"longer happens anywhere: {message!r}"
        )


def test_every_armed_module_derives_at_least_one_git_reaching_test():
    """THE FLOOR UNDER THE RESOLVER, ON THE REAL MODULES AND NOT ON A STUB.

    `test_every_git_touching_node_in_an_armed_module_is_covered_by_its_row` is a
    SUBSET assertion over a DERIVED set, and `required - chosen` is empty
    whenever `required` is. Measured: forcing `_git_launching_functions()` to
    return the empty set left that arm GREEN - the gate-reaching half kept
    `required` non-empty and hid the loss completely - while this floor named
    all five armed modules. That is why the floor is on the GIT half
    specifically and why it is not folded into the arm above.

    On the REAL modules, deliberately. The stub arms nearby grade the resolver
    on sources whose answers are known, so between them they would catch a
    resolver that answered nothing AT ALL; neither of them would notice one that
    answers for a stub and returns nothing for this tree.

    Pinned per module rather than as one total, because a total is satisfied by
    one module carrying the whole population while four derive nothing.
    """
    examined = 0
    empty: list[str] = []
    for site in _SITES:
        for path in sorted(_selected_nodes(site)):
            examined += 1
            facts = _module_facts(path)
            reaching = sorted(facts.tests & facts.git_reaching)
            if not reaching:
                empty.append(f"{site.label}: {path}")
    assert not empty, (
        "an armed module derives ZERO tests that reach a git launch, so the "
        "conservation arms above are subset assertions over an empty set there and "
        f"cannot fail: {empty}"
    )
    assert examined >= len(_REQUIRED_SHAPES), (
        f"only {examined} guard module(s) were examined for {len(_REQUIRED_SHAPES)} "
        f"required rows, so this floor shrank with the table: {_SITE_IDS}"
    )


def _present_half_problems(outcome: Outcome) -> list[str]:
    """Everything wrong with a run that was supposed to RUN ITS ASSERTIONS.

    A function rather than inline asserts so the whole PRESENT judgement can be
    pointed at a module whose verdict is already known. See the stub arms below.
    """
    problems: list[str] = []
    if outcome.failed or outcome.errors:
        problems.append(
            f"{outcome.failed} failed and {outcome.errors} errored: {outcome.summary!r}"
        )
    if outcome.gate_skips:
        problems.append(
            f"{outcome.gate_skips} test(s) skipped for the git gate with git PRESENT, "
            f"which is the unconditional-skip repair this arm exists to catch: "
            f"{outcome.gate_skip_lines}"
        )
    if outcome.passed <= 0:
        problems.append(
            "zero tests passed, so nothing was actually asserted - an empty "
            f"parametrize is '1 skipped, exit 0' and would look identical: {outcome.summary!r}"
        )
    return problems


@pytest.mark.skipif(
    not _mechanism_holds(),
    reason=(
        "git could not be made unreachable to a child process on this host, so the "
        "git-absent half would measure nothing - see "
        "test_the_absence_mechanism_hides_git_from_both_lookups for which lookup "
        "still reached it"
    ),
)
@pytest.mark.parametrize("site", _SITES, ids=_SITE_IDS)
def test_the_site_skips_and_does_not_fail_when_git_is_absent(site: Site):
    """ABSENT half: the gate has to convert an unreachable git into a SKIP."""
    with tempfile.TemporaryDirectory() as empty:
        outcome = _run_child_pytest(site.selection, _absent_git_env(empty))

    assert not outcome.failed and not outcome.errors, (
        f"{site.selection[0]} FAILED rather than skipped with git unreachable, so "
        f"its {site.gate}() wiring is not carrying the failure: {outcome.summary!r}\n"
        f"{outcome.stdout[-2000:]}"
    )
    # Exit 5 is `no tests collected`, which is what an import-time whole-module
    # skip legitimately produces. Exit 0 is the run-time per-test shape.
    assert outcome.returncode in (0, 5), (
        f"{site.selection[0]} exited {outcome.returncode} with git unreachable, which is "
        f"neither a clean run nor an uncollected module: {outcome.summary!r}"
    )
    assert outcome.gate_skips >= 1, (
        f"{site.selection[0]} reported no skip carrying the gate's own reason with git "
        f"unreachable, so whatever happened was not {site.gate}(): {outcome.summary!r}\n"
        f"{outcome.stdout[-2000:]}"
    )
    joined = "\n".join(outcome.gate_skip_lines)
    assert NOT_RUNNABLE_MARKER in joined, (
        "the skip fired but not on the not-runnable branch, so this arm is no longer "
        "measuring an ABSENT git - and it must stay silent on the broken-git case, "
        f"which is an open operator call: {joined!r}"
    )


@pytest.mark.parametrize("site", _SITES, ids=_SITE_IDS)
def test_the_same_site_runs_its_assertions_when_git_is_present(site: Site):
    """RUN half, and the load-bearing one.

    Unconditional wherever git exists. A guard welded to skip unconditionally
    satisfies the ABSENT arm above perfectly and is caught only here.
    """
    outcome = _run_child_pytest(site.selection, None)
    problems = _present_half_problems(outcome)
    assert not problems, (
        f"{site.selection[0]} did not run its assertions with git PRESENT:\n  "
        + "\n  ".join(problems)
        + f"\n{outcome.stdout[-2000:]}"
    )


def test_the_absent_half_cannot_be_skipped_while_the_mechanism_actually_holds():
    """THE FLOOR UNDER THE GATE. Without it, `_mechanism_holds() -> False` is GREEN.

    Measured by the same pass: forcing that helper to return False left this
    module at 8 passed / 2 skipped / exit 0. The two ABSENT arms simply vanished.
    `test_the_absence_mechanism_hides_git_from_both_lookups` did NOT catch it,
    because it interrogates the probe directly - so it stays green while the GATE
    that consumes the probe has been decoupled from it.

    So this arm pins the gate's decision to that same measurement, and the
    property that buys is worth stating exactly, because it is what makes the
    skip readable on EVERY lane it can fire on: THE ABSENT HALF CANNOT BE SKIPPED
    WHILE THIS MODULE IS GREEN. Either the gate agrees with the probe, in which
    case a skip implies the probe found git still reachable and
    `test_the_absence_mechanism_hides_git_from_both_lookups` is RED with the name
    of the lookup that reached it; or the gate disagrees with the probe, and this
    arm is RED here. A reader on a host where git genuinely cannot be hidden
    therefore sees a FAILURE naming the lookup, never a quiet pass.

    Nothing here asserts anything about a PRESENT-but-BROKEN git. That is an open
    operator call pinned open by `tests/test_conftest_git_gate.py`.
    """
    probe = _absence_probe()
    measured = probe.which == "None" and probe.exec_result == "FileNotFoundError"
    assert _mechanism_holds() == measured, (
        "the gate that skips the ABSENT half no longer agrees with the measurement "
        "it is supposed to be reading, so the ABSENT arms can now be skipped on a "
        "host where git IS successfully hidden and nothing reddens: "
        f"_mechanism_holds()={_mechanism_holds()} while WHICH={probe.which} "
        f"EXEC={probe.exec_result}"
    )

    skipifs = [
        mark
        for mark in getattr(
            test_the_site_skips_and_does_not_fail_when_git_is_absent, "pytestmark", ()
        )
        if mark.name == "skipif"
    ]
    assert len(skipifs) == 1, (
        "the ABSENT half no longer carries exactly one skipif, so what a reader is "
        f"told on a lane where it does not run is pinned nowhere: {skipifs}"
    )
    reason = str(skipifs[0].kwargs.get("reason", ""))
    assert "measure nothing" in reason and "test_the_absence_mechanism" in reason, (
        "the ABSENT half's skip reason no longer says that it would measure "
        "nothing, or no longer names the arm that reports which lookup reached "
        "git, so on any lane where it fires the skip reads as a pass: "
        f"{reason!r}"
    )


# ---------------------------------------------------------------------------
# Proving the RUN half can fail - paired, so it is a gate and not scaffolding
# ---------------------------------------------------------------------------


def _write_stub(tmp_path: Path, name: str, body: str) -> str:
    """Plant a stub test module in `tmp_path` and return its path as a string.

    `newline="\\n"` is pinned: the default translates every `\\n` to `os.linesep`
    on Windows, and a stub whose bytes differ from what was written is a stub
    nobody can reason about.
    """
    target = tmp_path / name
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    return str(target)


_UNCONDITIONAL_SKIP_STUB = (
    "import pytest\n"
    "\n"
    'pytest.skip("welded shut: ' + GATE_SKIP_MARKER + '", allow_module_level=True)\n'
    "\n"
    "\n"
    "def test_never_reached():\n"
    "    assert True\n"
)

_HONEST_STUB = "def test_actually_runs():\n    assert 2 + 2 == 4\n"


def test_the_run_half_reports_a_module_welded_to_skip_unconditionally(tmp_path: Path):
    """THE POSITIVE CONTROL. Point the PRESENT judgement at a guard that cheats.

    This is the repair the pair exists to catch: a module that skips whatever the
    environment says. It satisfies any skip-only arm, so if
    `_present_half_problems()` cleared it, both RUN arms above would be
    decoration.
    """
    stub = _write_stub(tmp_path, "test_welded_shut_stub.py", _UNCONDITIONAL_SKIP_STUB)
    outcome = _run_child_pytest((stub,), None)
    problems = _present_half_problems(outcome)

    assert problems, (
        "the PRESENT judgement cleared a module welded to skip unconditionally, so it "
        f"cannot catch that repair at a real site: {outcome.summary!r}\n{outcome.stdout[-2000:]}"
    )
    assert any("skipped for the git gate" in problem for problem in problems), (
        "the judgement objected, but not to the gate-reason skip - the count arm alone "
        f"would be satisfied by any module with zero passing tests: {problems}"
    )
    assert any("zero tests passed" in problem for problem in problems), (
        "the judgement did not notice that nothing ran, so a cheating module that "
        f"reworded its reason would slip through: {problems}"
    )


def test_the_run_half_clears_a_stub_that_genuinely_runs(tmp_path: Path):
    """The other arm of the pair: the judgement must not flag everything.

    Without this, a `_present_half_problems()` that returned a problem
    unconditionally would pass the control above and redden every real site for
    no reason.
    """
    stub = _write_stub(tmp_path, "test_honest_stub.py", _HONEST_STUB)
    outcome = _run_child_pytest((stub,), None)

    assert outcome.passed == 1, (
        f"the honest stub did not run, so this arm measured nothing: {outcome.summary!r}\n"
        f"{outcome.stdout[-2000:]}"
    )
    assert not _present_half_problems(outcome), (
        "the PRESENT judgement flagged a module that genuinely ran a passing test, so "
        f"it is armed to flag everything: {_present_half_problems(outcome)}"
    )


def test_the_summary_reader_survives_a_run_with_no_tests_at_all():
    """`no tests ran in 0.0s` must read as zeroes, not as an unparsed blank.

    If `_summary_line` ever returned empty for that shape, every count would be
    zero by accident and the RUN arms would still fire - but for the wrong
    reason, and the ABSENT arm's `returncode in (0, 5)` check would be doing all
    the work. Pinned as a unit rather than by spawning a process.
    """
    assert _summary_line("no tests ran in 0.01s\n") == "no tests ran in 0.01s"
    assert _summary_line("") == ""
    assert _COUNT.findall("2 failed, 17 passed in 0.09s") == [
        ("2", "failed"),
        ("17", "passed"),
    ]
    assert _COUNT.findall("1 skipped in 0.03s") == [("1", "skipped")]
