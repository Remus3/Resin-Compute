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

NOT armed, and this is a measured finding rather than an omission. Three other
modules shell git and carry NO gate at all - no `require_git_repository()`, no
`skip_module_without_git()`, no `pytest.skip` of any kind:

  - `tests/test_no_sibling_names.py:86`        `["git", "ls-files"]`, check=True
  - `tests/test_ci_workflow_complement.py:195` `["git", *args]`
  - `tests/test_responder_gate_census.py:1909` `["git", "ls-files", "-z", ...]`

Measured this run under the absence mechanism below, each selected node reported
a FileNotFoundError FAILURE and not a skip: 2 failed / 17 passed for the first,
1 failed for a representative node of each of the other two. Arming the ABSENT
half against them would therefore ship a permanently red test asserting a
behaviour the tree does not have. Gating those three modules is a change to
files outside this slice's write-list, so the defect is reported and NOT armed
here. When they are gated, add them to `_SITES`.

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
"""
from __future__ import annotations

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
)

_SITE_IDS = [site.label for site in _SITES]


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
