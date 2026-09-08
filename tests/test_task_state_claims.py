"""A Windows scheduled-task State string must never be presented as liveness.

THE ROOT CAUSE, MEASURED ON THIS MACHINE 2026-09-08.

`Get-ScheduledTask` reports `State: Ready` and `Get-ScheduledTaskInfo` reports
`LastTaskResult: 0` FOREVER once every trigger on the task has expired. There is
no state value that means "expired". ResinCompute-Responder read Ready that day
with its EndBoundary at 2026-09-07T21:00:00 - twenty-four hours in the past -
NextRunTime EMPTY, LastRunTime 2026-09-07 20:55, and not one invocation-log line
since. It will never fire again. A previous session read that Ready, wrote
"Ready on a 5-minute tick" into the hand-off, and was wrong by a full day.

A STATE STRING NAMES A STATE, NOT A CAPABILITY. The only honest verdict comes
from `ops/check_task_liveness.py`, whose command-line contract is fixed:

    python ops/check_task_liveness.py <TaskName>

exits 0 IF AND ONLY IF the task is positively established to fire again. Every
non-zero exit means "not established"; the values are not enumerated here on
purpose, because that file may add new ones.

WHAT THIS GUARD DETECTS, AND WHAT IT DELIBERATELY DOES NOT.

Printing a State string as CONTEXT is legitimate and stays legal. Presenting it
as the VERDICT is the defect. Those two cannot be separated by reading the state
read alone, so the detector keys on the pairing instead, and guards the narrower
thing it can actually see:

  Rule 1, over tracked `.ps1` and `.py`: one line that BOTH emits output
  (Write-Host / Write-Step / Write-Output / print) AND reads a scheduled-task
  state property AND carries a verdict word as a whole word. That is a line
  telling an operator "verified" in the same breath as a state name, which is
  exactly the false claim.

  Rule 2, over tracked `.md`: a line presented as the operator's CHECK COMMAND
  - it begins with `powershell` or with the cmdlet itself - that reads scheduled
  task STATE, meaning it calls the info cmdlet or pulls the state property.
  Prose that merely names the cmdlet mid-sentence is not a recommendation and
  does not trip, which is what lets the ledger keep describing the defect it
  recorded.

  Rule 2 was NARROWED after its first run, and the narrowing is the interesting
  part. Written to fire on the plain task cmdlet as well, it flagged
  README.md:293 - the first line of the REMOVAL recipe, where fetching the task
  object is an existence probe on the way to unregistering it, and nothing is
  claimed about firing. That is a legitimate neighbour, so the rule now keys on
  the state read rather than on touching the scheduler at all. Guarding the
  narrower thing that can actually be detected beats a broad rule carrying an
  exception list. That exact README line is pinned below as a survival arm: a
  sweep that scores 100 percent by deleting its neighbours has failed.

Neither rule is a claim to catch every possible phrasing. They catch the shape
that actually shipped here three times over.

THE SELF-MATCH TRAP, HANDLED AT SOURCE. This file must talk about the banned
pattern in order to ban it. Rather than carve an allowlist entry - a chunk of
regex nobody can read, which goes unstable the moment the line beside it is
edited - every needle below is ASSEMBLED FROM FRAGMENTS, so the literal strings
this module hunts for never appear contiguously in its own bytes.

NON-VACUITY. A guard that sweeps a corpus and finds nothing is indistinguishable
from a broken regex, and a gate exercised only as a pure predicate is not an
enforced gate - that defect has now recurred three times in this tree. So there
are three arms below, not one: the corpus sweep itself, an arm proving the sweep
really opened the files it claims to have swept, and a positive control that
runs THE SAME directory-walking scanner over a fixture tree and requires it to
fire.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Needles, assembled so this file never contains them contiguously -------

_STATE_PROPERTY = "." + "State"
_LAST_RESULT = "LastTask" + "Result"
_INFO_CMDLET = "Get-Scheduled" + "TaskInfo"
_TASK_CMDLET = "Get-Scheduled" + "Task"

# Words that turn a state read into an assertion about capability.
_VERDICT_WORDS = re.compile(
    r"\b(verified|verify|verifies|confirmed|confirms|healthy|alive|live"
    r"|running|active|ok|success|succeeded|succeeds|working|works|fine|good)\b",
    re.IGNORECASE,
)

_EMITS_OUTPUT = re.compile(r"Write-Host|Write-Step|Write-Output|Write-Information|print\(")

_CODE_SUFFIXES = (".ps1", ".py")
_DOC_SUFFIXES = (".md",)

# This module is itself tracked and is scanned like everything else. It has no
# exemption and needs none: the needles above are assembled, so its own bytes
# do not contain them.


def _reads_task_state(line: str) -> bool:
    return _STATE_PROPERTY in line or _LAST_RESULT in line


def _violates_code_rule(line: str) -> bool:
    """A single output line that pairs a task state read with a verdict word."""
    if not _EMITS_OUTPUT.search(line):
        return False
    if not _reads_task_state(line):
        return False
    return _VERDICT_WORDS.search(line) is not None


def _violates_doc_rule(line: str) -> bool:
    """A doc line presenting a scheduled-task state read as the check command."""
    stripped = line.strip()
    # Docs quote commands inside fenced blocks and inside indented blocks, and
    # both arrive here with the leading whitespace already gone.
    if not (stripped.startswith("powershell") or stripped.startswith(_TASK_CMDLET)):
        return False
    # The INFO cmdlet exists to report LastRunTime / NextRunTime / last result,
    # so quoting it at an operator is always a state read. The plain task cmdlet
    # only offends when the state property is pulled off what it returns.
    return _INFO_CMDLET in stripped or _reads_task_state(stripped)


def scan_file(path: Path, relative_name: str) -> list[str]:
    """Return one finding string per offending line in a single file.

    Split out from the corpus walk so the positive control can drive the exact
    same code path over a fixture tree.
    """
    suffix = path.suffix.lower()
    if suffix in _CODE_SUFFIXES:
        predicate = _violates_code_rule
    elif suffix in _DOC_SUFFIXES:
        predicate = _violates_doc_rule
    else:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if predicate(line):
            findings.append(relative_name + ":" + str(number) + ": " + line.strip())
    return findings


def scan_tree(root: Path, relative_names: list[str]) -> list[str]:
    """Walk a set of relative paths under `root` and collect every finding."""
    findings = []
    for name in relative_names:
        candidate = root / name
        if not candidate.is_file():
            # A tracked path can be absent in a partial checkout or while a
            # sibling slice is mid-merge. Skipping is honest; the corpus arm
            # below is what makes an empty sweep impossible to mistake for a
            # clean one.
            continue
        findings.extend(scan_file(candidate, name))
    return findings


def _tracked_files() -> list[str]:
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def _scannable_tracked_files() -> list[str]:
    # Derived from git, never a hand-maintained list. A hand-maintained list of
    # paths that remember to do X goes stale silently, measured twice here.
    wanted = _CODE_SUFFIXES + _DOC_SUFFIXES
    return [name for name in _tracked_files() if name.lower().endswith(wanted)]


# --- Arm 1: the corpus sweep -----------------------------------------------


def test_no_tracked_file_presents_task_state_as_liveness() -> None:
    findings = scan_tree(REPO_ROOT, _scannable_tracked_files())
    assert findings == [], (
        "A scheduled-task state string is being presented as evidence that the "
        "task will fire again. It is not: a task reports Ready and result 0 "
        "forever once its triggers have expired. Report the exit code of "
        "ops/check_task_liveness.py instead, or say plainly that liveness is "
        "UNVERIFIED.\n" + "\n".join(findings)
    )


# --- Arm 2: the sweep really opened the corpus it claims to have swept ------


def test_the_sweep_actually_covers_the_real_installers_and_the_hand_off() -> None:
    """Assert the corpus, not the predicate.

    A gate tested only as a pure predicate is not an enforced gate. This arm
    proves the paths that carried the defect are inside the set Arm 1 walks, and
    that the walk opens real files rather than silently skipping everything.
    """
    corpus = _scannable_tracked_files()
    for expected in (
        "ops/install_responder_task.ps1",
        "ops/install_scheduled_task.ps1",
        "NEXT_SESSION_PROMPT.md",
        "README.md",
    ):
        assert expected in corpus, "corpus lost a path that carried the defect: " + expected
    present = [name for name in corpus if (REPO_ROOT / name).is_file()]
    assert len(present) > 30, "corpus collapsed to " + str(len(present)) + " readable files"


# --- Arm 3: the positive control -------------------------------------------


def _fixture_offending_ps1() -> str:
    # Assembled, so this source file does not contain the offending line.
    return "Write-Step ('" + "verified present, state: ' + $check" + _STATE_PROPERTY + ")\n"


def _fixture_offending_md() -> str:
    return "  powershell -NoProfile -Command \"" + _INFO_CMDLET + " -TaskName 'X'\"\n"


def test_positive_control_the_scanner_fires_on_a_planted_violation(tmp_path: Path) -> None:
    """The same directory walk Arm 1 uses must trip on a fixture that should trip.

    Without this, an empty result from Arm 1 is indistinguishable from a regex
    that matches nothing at all.
    """
    (tmp_path / "planted_installer.ps1").write_text(_fixture_offending_ps1(), encoding="ascii")
    (tmp_path / "planted_handoff.md").write_text(_fixture_offending_md(), encoding="ascii")

    findings = scan_tree(tmp_path, ["planted_installer.ps1", "planted_handoff.md"])

    assert len(findings) == 2, "scanner missed a planted violation: " + repr(findings)
    assert any(finding.startswith("planted_installer.ps1:1:") for finding in findings)
    assert any(finding.startswith("planted_handoff.md:1:") for finding in findings)


@pytest.mark.parametrize(
    "legal_line",
    [
        # State printed as CONTEXT, with no verdict word, stays legal.
        "Write-Step ('registered. reported state is ' + $check" + _STATE_PROPERTY + ")",
        # A verdict word with no state read is somebody else's business.
        "Write-Step ('LIVENESS ESTABLISHED - the checker exited 0')",
        # Unrelated domain identifiers must never trip this.
        "    state: PityState,",
        "print(f'panel {panel.state} is not ready')",
    ],
)
def test_legitimate_neighbours_survive_the_code_rule(legal_line: str) -> None:
    """A sweep that scores 100 percent by deleting its neighbours has failed."""
    assert not _violates_code_rule(legal_line), "false positive on: " + legal_line


@pytest.mark.parametrize(
    "legal_line",
    [
        # Prose naming the cmdlet in order to explain the defect is not a
        # recommendation and must keep working.
        "The task read Ready with " + _LAST_RESULT + " 0 long after it expired.",
        "  python ops/check_task_liveness.py ResinCompute-Responder",
        "  powershell -NoProfile -Command \"Get-Content .\\ops\\runtime\\health.json\"",
        # The REAL neighbour, lifted verbatim from README.md's removal recipe.
        # Fetching the task object on the way to unregistering it claims
        # nothing about whether it will ever fire.
        _TASK_CMDLET + " -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue",
        "Unregister-Scheduled" + "Task -TaskName 'ResinCompute-Supervisor' -Confirm:$false",
    ],
)
def test_legitimate_neighbours_survive_the_doc_rule(legal_line: str) -> None:
    assert not _violates_doc_rule(legal_line), "false positive on: " + legal_line


def test_this_guard_file_is_pure_ascii() -> None:
    """The needles are assembled to dodge self-match; ASCII is the other rule."""
    raw = Path(__file__).read_bytes()
    offenders = sorted({byte for byte in raw if byte > 127})
    assert offenders == [], "non-ASCII bytes in the guard: " + repr(offenders)
