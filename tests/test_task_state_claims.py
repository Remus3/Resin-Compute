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

_EMITS_OUTPUT = re.compile(r"(?i:Write-Host|Write-Step|Write-Output|Write-Information)|print\(")

_CODE_SUFFIXES = (".ps1", ".py")
_DOC_SUFFIXES = (".md",)

# This module is itself tracked and is scanned like everything else. It has no
# exemption and needs none: the needles above are assembled, so its own bytes
# do not contain them.


def _reads_task_state(line: str) -> bool:
    return _contains_powershell_needle(line, _STATE_PROPERTY, _LAST_RESULT)


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
    if not _starts_a_powershell_command(stripped):
        return False
    # The INFO cmdlet exists to report LastRunTime / NextRunTime / last result,
    # so quoting it at an operator is always a state read. The plain task cmdlet
    # only offends when the state property is pulled off what it returns.
    return _contains_powershell_needle(stripped, _INFO_CMDLET) or _reads_task_state(stripped)


def scan_file(path: Path, relative_name: str) -> list[str]:
    """Return one finding string per offending line in a single file.

    Split out from the corpus walk so the positive control can drive the exact
    same code path over a fixture tree.
    """
    suffix = path.suffix.lower()
    if suffix in _CODE_SUFFIXES:
        predicate = _code_rule_for(suffix)
    elif suffix in _DOC_SUFFIXES:
        predicate = _violates_doc_rule
    else:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:  # FAIL CLOSED. UnreadableCorpusFile is defined at the END of this module.
        raise UnreadableCorpusFile(_unreadable_reason(relative_name, path, exc)) from exc
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


# --- Arm 4: an unreadable corpus file FAILS, it does not sweep clean --------
#
# THE DEFECT THIS ARM EXISTS FOR, recorded in ROADMAP.md as the FIFTH
# degrade-to-empty site in this tree and the first one found inside a guard.
# `scan_file` read the corpus under `except OSError: return []`, so a tracked
# file that could not be opened was reported as ZERO FINDINGS and Arm 1 swept
# CLEAN over it. A guard that degrades to empty on an input it could not read
# passes on both sides of a real defect, which is the exact failure mode this
# module exists to prevent in somebody else's code.
#
# WHICH ERROR CLASSES ARE FOLDED TOGETHER, AND WHERE THE SPLIT SITS.
# `scan_file` folds EVERY `OSError` - permission denied, a file that vanished
# mid-sweep, a device error, a path that turned out to be a directory - into one
# fail-closed verdict, because by then the caller has already decided the path is
# part of the corpus, and the honest answer for all of them is identical: the
# findings for this file are UNKNOWN, and UNKNOWN is not CLEAN.
#
# `scan_tree` keeps its PRE-EXISTING `is_file()` skip for a path that is simply
# ABSENT, unchanged here. That is a different question - whether a path belongs
# to the corpus at all - and a partial checkout must not hard-fail. It is a
# documented boundary, not a claim that it is ideal.
#
# WHY THE INPUTS BELOW ARE REAL. A gate cannot fail if its fixture excludes the
# defect, measured twice in this tree. Neither arm asserts anything about the
# guard until it has PROVED, in its own body, that the input it feeds genuinely
# refuses to be read. Windows file permissions are useless for this - a
# chmod-based fixture stays readable as Administrator - so one arm feeds a
# DIRECTORY wearing a scanned suffix, which fails at `open` on every platform
# this tree runs on, and the other injects the error at the exact call site the
# scanner uses and proves the injection lands there.

#: `errno.EACCES`, spelled as a literal on purpose: `import errno` would have to
#: sit in the import block at the top of this module (ruff E402) and would shift
#: every line number below it, three of which are cited by number from other
#: tracked files. 13 on Windows and on POSIX alike.
_EACCES = 13


def test_scan_file_fails_closed_on_a_genuinely_unreadable_path(tmp_path: Path) -> None:
    """A real filesystem read failure must reach the caller, never become `[]`."""
    victim = tmp_path / "unreadable_handoff.md"
    victim.mkdir()

    # PROVE the fixture genuinely refuses to be read BEFORE grading the guard
    # with it. Measured on this machine: PermissionError, errno 13.
    with pytest.raises(OSError) as direct:
        victim.read_text(encoding="utf-8", errors="replace")
    assert direct.value.errno is not None, "fixture failed with no errno - not a real read failure"

    with pytest.raises(UnreadableCorpusFile) as caught:
        scan_file(victim, "unreadable_handoff.md")

    message = str(caught.value)
    assert "unreadable_handoff.md" in message, "the failure does not name the path: " + message
    assert "errno " + str(direct.value.errno) in message, "the failure hides the raw reason: " + message


def test_scan_tree_fails_closed_rather_than_returning_the_findings_it_could_reach(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One unreadable file must sink the whole sweep, not shrink it quietly.

    The planted violation is scanned FIRST, so a partial result is available at
    the moment the second file refuses. Returning that partial list would be the
    same defect wearing a smaller number.
    """
    planted = tmp_path / "planted_installer.ps1"
    planted.write_text(_fixture_offending_ps1(), encoding="ascii")
    locked = tmp_path / "locked_handoff.md"
    locked.write_text(_fixture_offending_md(), encoding="ascii")

    real_read_text = Path.read_text

    def refuse_one_file(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "locked_handoff.md":
            raise PermissionError(_EACCES, "Access is denied")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", refuse_one_file)

    # PROVE the injection lands on the read the scanner actually performs, and
    # that it refuses ONLY the one file. An injection that refused everything, or
    # nothing, would make the assertion below meaningless in opposite directions.
    with pytest.raises(PermissionError):
        locked.read_text(encoding="utf-8", errors="replace")
    assert _INFO_CMDLET in real_read_text(locked, encoding="ascii"), "fixture lost its planted line"
    assert _STATE_PROPERTY in planted.read_text(encoding="ascii"), "injection refused the wrong file"

    with pytest.raises(UnreadableCorpusFile) as caught:
        scan_tree(tmp_path, ["planted_installer.ps1", "locked_handoff.md"])

    message = str(caught.value)
    assert "locked_handoff.md" in message, "the failure does not name the path: " + message
    assert "errno " + str(_EACCES) in message, "the failure hides the raw reason: " + message


def test_scan_tree_still_skips_a_path_that_is_simply_absent(tmp_path: Path) -> None:
    """The absent-path skip is pre-existing behaviour and is deliberately kept.

    Pinned so the fail-closed change above cannot be mistaken for having turned a
    partial checkout into a hard failure, and so a later edit that does change it
    has to change this arm and say why. This arm passed before that change too -
    it is a survival pin, not the defect arm.
    """
    (tmp_path / "planted_installer.ps1").write_text(_fixture_offending_ps1(), encoding="ascii")

    findings = scan_tree(tmp_path, ["planted_installer.ps1", "never_checked_out.md"])

    assert len(findings) == 1, "an absent path changed the sweep: " + repr(findings)
    assert findings[0].startswith("planted_installer.ps1:1:")


# --- THE FAIL-CLOSED SIGNAL -------------------------------------------------
#
# DEFINED HERE, BELOW ITS ONE USE SITE, AND THAT ORDERING IS DELIBERATE. Four
# tracked prose passages cite positions in THIS module by line number -
# `tests/test_supervisor_task_argv.py` does so three times and `ROADMAP.md`
# once - and every one of them was accurate when this was written. Inserting a
# class above `scan_file` would have shifted all of them by the height of the
# class and silently made four citations off-by-N. Appending costs a reader one
# jump; shifting costs four readers a wrong line. The name resolves out of module
# globals when `scan_file` is called, which is always after import completes.


class UnreadableCorpusFile(OSError):
    """A corpus file could not be read, so this guard's verdict is UNKNOWN.

    UNKNOWN IS NOT CLEAN. `scan_file` answered an unreadable file with `[]` until
    this class existed, which made the sweep report ZERO FINDINGS for a file it
    never opened - a guard passing on both sides of a real defect. Raising is the
    whole point: the caller cannot accidentally treat it as a clean result.

    Subclasses `OSError` because it IS one, reached through `raise ... from exc`,
    so the original errno-bearing cause stays on the traceback for whoever is
    debugging while the message above stays readable for whoever is not.
    """


def _unreadable_reason(relative_name: str, path: Path, exc: OSError) -> str:
    """Name the path and the raw errno reason, without pasting a traceback.

    The raw reason is the errno NUMBER plus the OS `strerror`, and `winerror`
    when the platform supplies one. Measured on this machine 2026-09-11: reading
    a directory yields PermissionError, errno 13, "Permission denied", with
    `winerror` set to None - so the WinError clause is conditional rather than
    assumed present on Windows.
    """
    reason = "errno " + str(exc.errno)
    if exc.strerror:
        reason += " " + exc.strerror
    winerror = getattr(exc, "winerror", None)
    if winerror is not None:
        reason += " (WinError " + str(winerror) + ")"
    return (
        "UNREADABLE, therefore UNKNOWN, therefore FAIL: " + relative_name
        + " could not be read at " + str(path) + " - " + type(exc).__name__ + ", " + reason
        + ". A guard that answers zero findings for a file it could not open passes on both"
        + " sides of a real defect, so the sweep fails here instead of reporting clean. Make"
        + " the file readable, or drop the path from the corpus deliberately."
    )


# --- Arm 5: THE MATCHING DIALECT IS THE MACHINE'S, NOT THE AUTHOR'S ---------
#
# THE DEFECT, measured by driving the real predicates in-process before these
# arms existed. Every line on the right is VALID POWERSHELL that does exactly
# what the line on the left does, and the guard saw only the left one:
#
#   _violates_doc_rule    True  on `powershell -NoProfile -Command "(...).State"`
#                         FALSE on the same line spelled `PowerShell`
#                         FALSE on `get-scheduledtaskinfo -TaskName 'R'`
#   _violates_code_rule   True  on a canonical `Write-Host` line pairing a
#                               state-property read with the word verified
#                         FALSE on the same line spelled `write-host`
#                         FALSE on `... .state` and on `... .lasttaskresult`
#
# The middle entry is DESCRIBED rather than quoted, and that is the self-match
# trap this module's header warns about: written out contiguously it is itself
# an offending line, and the sweep in Arm 1 opens this file like any other.
# Measured - the first draft of this note turned Arm 1 red against itself.
#
# WHY. PowerShell resolves command names, parameter names and property names
# CASE-INSENSITIVELY - `-match`, `-replace`, `-like` and `switch -regex` are
# case-blind by default and `-cmatch` / `-creplace` are the case-SENSITIVE
# forms - while Python's `re` and Python's `in` are case-SENSITIVE by default.
# A Python guard that models a PowerShell command silently disagrees with the
# thing it grades, and the disagreement is invisible: it reports CLEAN.
#
# The author knew the rule. `_VERDICT_WORDS` above carries `re.IGNORECASE`. It
# is the PowerShell-dialect halves that were written in Python's dialect.
# `_unsanctioned_in` in `tests/test_task_liveness.py` gets this right and says
# so - "Comparing case-sensitively grades typography" - and the helpers at the
# foot of this module follow that shape rather than inventing another.
#
# THE POPULATION, DERIVED BY SUBTRACTION AND NOT BY ENUMERATING CASES. The
# subject of these predicates is "a line that POWERSHELL WOULD EXECUTE as a
# scheduled-task state read". PowerShell's own resolution rule says that set is
# closed under case, so the matcher saw exactly one member of each equivalence
# class and could not see the rest. That is why the repair is to fold case
# rather than to add spellings: an enumerated list omits the position nobody
# named, and there is no finite list of casings to enumerate.
#
# WHAT IS DELIBERATELY NOT FOLDED, because the dialect is decided by the
# LANGUAGE and not by the guard: `print(` stays case-sensitive. It is a PYTHON
# builtin, `PRINT(` is a NameError rather than a variant, and folding it would
# be modelling Python in PowerShell's dialect - the same mistake pointing the
# other way. The needle case-fold is therefore scoped with `(?i:...)` around
# the PowerShell emitters only.
#
# THE MEASURED COST OF FOLDING THE STATE NEEDLE, stated rather than hoped, and
# SCOPED so that stating it cannot falsify it.
#
# POPULATION: the tracked `.py` and `.ps1` files, straight from
# `git ls-files "*.py" "*.ps1"`. That answered 142 files on 2026-09-11 - a
# dated reading, not a guarded figure, and only a FLOOR on it is pinned.
# COUNTING RULE: a line counts when the state needle is visible to the FOLDED
# comparison and NOT to the case-SENSITIVE one. That is exactly the set a fold
# would newly capture, and nothing else.
# EMITTER: one of those lines that `_EMITS_OUTPUT` also matches.
#
# THE FIGURE, EXCLUDING THIS MODULE: 76 lines, of which ZERO emit output.
# Almost all of them are a Python attribute named `state`, which is a different
# property from PowerShell's `.State`. Not one of the 76 can reach Rule 1 in
# either dialect, because Rule 1 needs an emitter and none of them is one.
#
# THIS MODULE IS EXCLUDED ON PURPOSE, AND THE EXCLUSION IS THE REPAIR. This
# file is IN the corpus being counted, so an absolute total counts the arms
# below and moves the moment one of them is edited - a comment stating that
# total can be falsified by the same keystroke that writes it. That is measured,
# not feared: the figure that stood here before was EXACT WHEN WRITTEN and
# STALE WHEN SHIPPED, because this change's own new dialect arms were
# themselves lines in the population. Scoped to everything outside this file,
# the figure is stable under edits to this file.
#
# The only emitting members of the conflation population are this module's own
# pinned negative controls, graded by
# `test_the_python_dialect_does_not_fold_a_python_attribute` rather than
# counted here; they carry no verdict word. The verdict-word conjunct is what
# keeps the two apart, the survival arms are what will notice if it stops, and
# `test_the_conflation_figure_still_matches_the_tree` re-derives both figures
# from the real corpus at test time - so the next reader can CHECK this
# paragraph instead of trusting it.


@pytest.mark.parametrize(
    "offending_doc_line",
    [
        # THE LAUNCHER, case-folded. Windows resolves an executable name
        # case-insensitively, so all of these start the same process.
        "PowerShell -NoProfile -Command \"(" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY + "\"",
        "POWERSHELL -NoProfile -Command \"(" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY + "\"",
        # THE CMDLET, case-folded, both as the launcher and as the state read.
        _INFO_CMDLET.lower() + " -TaskName 'ResinCompute-Responder'",
        _TASK_CMDLET.lower() + " -TaskName 'R' | ForEach-Object { $_"
        + _STATE_PROPERTY.lower() + " }",
        # THE OTHER HOST. A CLASS widening rather than a case fold, and graded
        # separately for that reason: `pwsh` is PowerShell 7 and is one of the
        # four names this tree's own resolvers try - see
        # `_starts_a_powershell_command` at the foot of this module for where
        # the set is read from. Before it, a check command quoted through
        # PowerShell 7 was invisible to Rule 2 in EVERY casing.
        "pwsh -NoProfile -Command \"(" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY + "\"",
        "PWSH.EXE -NoProfile -Command \"(" + _INFO_CMDLET + " -TaskName 'R')\"",
        # THE PROPERTY, case-folded.
        "powershell -NoProfile -Command \"(" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY.lower() + "\"",
        "powershell -NoProfile -Command \"(" + _INFO_CMDLET + " -TaskName 'R')." + _LAST_RESULT.lower() + "\"",
    ],
)
def test_the_doc_rule_reads_powershell_in_powershells_dialect(offending_doc_line):
    assert _violates_doc_rule(offending_doc_line), (
        "a case variant of a check command is the same command, and missing it "
        "grades typography rather than the claim: " + offending_doc_line
    )


@pytest.mark.parametrize(
    "offending_code_line",
    [
        # THE EMITTER, case-folded. PowerShell resolves cmdlet names case-blind.
        "write-host \"verified: $((" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY + ")\"",
        "WRITE-STEP \"verified: $((" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY + ")\"",
        # THE PROPERTY, case-folded, with the canonical emitter.
        "Write-Host \"verified: $((" + _TASK_CMDLET + " -TaskName 'R')" + _STATE_PROPERTY.lower() + ")\"",
        "Write-Step \"confirmed alive: $($i." + _LAST_RESULT.lower() + ")\"",
        # Both halves non-canonical at once.
        "write-output \"the task is healthy - $($i." + _LAST_RESULT.upper() + ")\"",
    ],
)
def test_the_code_rule_reads_powershell_in_powershells_dialect(offending_code_line):
    assert _violates_code_rule(offending_code_line), (
        "a case variant of a state read is the same read, and missing it grades "
        "typography rather than the claim: " + offending_code_line
    )


@pytest.mark.parametrize(
    "survivor",
    [
        # THE PARTNER GUARD for the fold, in the POWERSHELL dialect. A sweep
        # that scores 100 percent by deleting its neighbours has failed, and
        # case-folding is exactly the change that could do it.
        #
        # Verdict word, no state read in any casing.
        "Write-Step ('LIVENESS ESTABLISHED - the checker exited 0')",
        # State read in a non-canonical casing, no verdict word.
        "Write-Step ('registered. reported state is ' + $check" + _STATE_PROPERTY.lower() + ")",
        "Write-Host ('last result: ' + $i." + _LAST_RESULT.lower() + ")",
        # Neither half.
        "Write-Host 'the installer finished and the task is registered'",
    ],
)
def test_case_folding_did_not_swallow_the_powershell_neighbours(survivor):
    assert not _violates_code_rule(survivor), "false positive on: " + survivor


@pytest.mark.parametrize(
    "survivor",
    [
        # THE DIALECT BOUNDARY, and the arm that forced it to exist. In a
        # PYTHON file `.state` is a DIFFERENT attribute from `.State`, because
        # Python resolves attribute names case-SENSITIVELY. Folding case there
        # conflates an unrelated domain object with a scheduled task, and the
        # conflation population is measured rather than feared: 76 lines
        # OUTSIDE this module carry a state needle ONLY in a non-canonical
        # spelling, and NONE of them emits output. The population, the counting
        # rule, the reason this module is excluded from its own figure, and
        # the arm that re-derives the whole of it -
        # `test_the_conflation_figure_still_matches_the_tree` - are in the Arm 5
        # note above.
        #
        # The first of these was already pinned above as a legitimate
        # neighbour. The second is the same line with a VERDICT WORD in it, and
        # it went red under a universal fold - which is what turned "fold
        # everywhere" into "fold in the dialect that actually folds".
        "print(f'panel {panel.state} is not ready')",
        "print(f'{panel.state} is running')",
        "    state: PityState,",
        "print('LIVENESS ESTABLISHED - the checker exited 0')",
    ],
)
def test_the_python_dialect_does_not_fold_a_python_attribute(survivor):
    assert not _violates_python_code_rule(survivor), "false positive on: " + survivor


@pytest.mark.parametrize(
    ("line", "in_powershell", "in_python"),
    [
        # THE TWO DIALECTS DISAGREE, AND THAT IS THE POINT. A canonical read is
        # caught by both; a non-canonically cased one is caught only where the
        # language actually resolves names case-blind. Without this arm the
        # split could collapse to one dialect and nothing would notice.
        ("Write-Host ('verified: ' + $t" + _STATE_PROPERTY + ")", True, True),
        ("Write-Host ('verified: ' + $t" + _STATE_PROPERTY.lower() + ")", True, False),
        ("print('verified: ' + task" + _STATE_PROPERTY + ")", True, True),
        ("print('verified: ' + task" + _STATE_PROPERTY.lower() + ")", True, False),
    ],
)
def test_the_two_dialects_differ_exactly_where_the_languages_differ(
    line, in_powershell, in_python
):
    assert _violates_code_rule(line) is in_powershell, "powershell dialect: " + line
    assert _violates_python_code_rule(line) is in_python, "python dialect: " + line


@pytest.mark.parametrize(("suffix", "expected"), [(".ps1", True), (".py", False)])
def test_the_corpus_walk_routes_each_suffix_to_its_own_dialect(suffix, expected):
    """The dispatch really is by suffix, so the split is not two dead functions.

    Asserted by FEEDING A LINE the two dialects disagree about, rather than by
    comparing function objects: an identity check would pass against a pair of
    predicates that had both stopped matching anything.
    """
    divergent = "Write-Host ('verified: ' + $t" + _STATE_PROPERTY.lower() + ")"
    assert _code_rule_for(suffix)(divergent) is expected


def test_the_real_walk_grades_the_same_line_differently_by_suffix(tmp_path: Path) -> None:
    """End to end through `scan_tree`, which is what Arm 1 actually runs.

    A predicate can route correctly while the walk that calls it does not, and
    that gap is exactly the "tested only as a pure predicate" defect this
    module's header says has already recurred three times here.
    """
    divergent = "Write-Host ('verified: ' + $t" + _STATE_PROPERTY.lower() + ")\n"
    (tmp_path / "planted.ps1").write_text(divergent, encoding="ascii")
    (tmp_path / "planted.py").write_text(divergent, encoding="ascii")

    findings = scan_tree(tmp_path, ["planted.ps1", "planted.py"])

    assert len(findings) == 1, "the walk did not split the dialects: " + repr(findings)
    assert findings[0].startswith("planted.ps1:1:")


@pytest.mark.parametrize(
    "survivor",
    [
        # Prose that merely NAMES the tooling is not a recommendation, in any
        # casing, and the nine tracked `.md` lines beginning with the word
        # PowerShell are all of exactly this shape.
        "PowerShell 5.1 ANSI-decodes a no-BOM .ps1 and turns an em-dash into a",
        "powershell is the host; the state it reports is not a capability.",
        "  python ops/check_task_liveness.py ResinCompute-Responder",
        "  powershell -NoProfile -Command \"Get-Content .\\ops\\runtime\\health.json\"",
        # The partner for the pwsh widening: NAMING the host is not quoting a
        # state read at the operator, so a wider launcher set must not start
        # flagging prose or an unrelated command.
        "pwsh is the PowerShell 7 host, and the state it reports is not a capability.",
        "  pwsh -NoProfile -Command 'Get-Content .'",
        # The REAL neighbour from README.md's removal recipe, now also in the
        # casing PowerShell would equally accept.
        _TASK_CMDLET.lower() + " -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue",
    ],
)
def test_case_folding_did_not_swallow_the_doc_rules_neighbours(survivor):
    assert not _violates_doc_rule(survivor), "false positive on: " + survivor


# --- THE POWERSHELL DIALECT -------------------------------------------------
#
# DEFINED HERE, BELOW THEIR USE SITES, FOR THE REASON THE CLASS ABOVE GIVES.
# Four tracked prose passages cite positions in this module BY LINE NUMBER -
# `tests/test_supervisor_task_argv.py` three times, at :216, :259 and :281-282,
# and `ROADMAP.md` once at :216 - and all four were re-measured as ACCURATE
# before this section was written. Inserting these two helpers above
# `_reads_task_state` would have shifted every one of them. They are appended,
# and the predicates above call them by name out of module globals, which
# resolve at call time and so are always after import completes.
#
# WHY FOLD CASE AT ALL. PowerShell resolves command names, parameter names and
# property names CASE-INSENSITIVELY. `get-scheduledtaskinfo` is the same cmdlet
# as `Get-ScheduledTaskInfo`, `$t.state` reads the same property as `$t.State`,
# and Windows resolves `POWERSHELL.EXE` to the same image as `powershell.exe`.
# A guard written in Python `re`'s default dialect - case-SENSITIVE - therefore
# grades TYPOGRAPHY, and it reports CLEAN while doing it. This tree already
# holds the correction: `_unsanctioned_in` in `tests/test_task_liveness.py`
# lowercases both sides and says why in exactly those terms. These follow it.
#
# WHAT IS NOT FOLDED, and it is a deliberate line rather than an oversight.
# `print(` in `_EMITS_OUTPUT` stays case-SENSITIVE, because it is a PYTHON
# builtin and `PRINT(` is a NameError rather than another spelling of it. The
# flag is scoped with `(?i:...)` around the PowerShell emitters alone. Folding
# a Python name into PowerShell's dialect would be the same error as folding a
# PowerShell name into Python's, pointing the other way.


def _contains_powershell_needle(text: str, *needles: str) -> bool:
    """True when `text` carries any of `needles` in ANY casing.

    `casefold` rather than `lower` on principle: it is the full Unicode case
    mapping, and while every needle here is ASCII, the CORPUS is not
    guaranteed to be - `scan_file` reads with `errors="replace"` and hands
    this whatever a tracked file happens to contain.
    """
    folded = text.casefold()
    return any(needle.casefold() in folded for needle in needles)


def _starts_a_powershell_command(stripped: str) -> bool:
    """True when a doc line is QUOTING a command at the operator.

    THE LAUNCHER SET IS READ OFF THE TREE, not enumerated here from memory.
    Two tracked modules already resolve a PowerShell host and both settle on
    the same four names: `_powershell_executable` in
    `ops/check_task_liveness.py` tries `powershell.exe`, `powershell`,
    `pwsh.exe` and `pwsh` in that order, and `_POWERSHELL_NAMES` in
    `scripts/make_shortcut.py` holds the same four. The two prefixes below
    cover all four, because the `.exe` spellings are the bare ones plus a
    suffix. Adding `pwsh` is a CLASS widening and is separate from the case
    fold: before it, a check command quoted at the operator through PowerShell
    7 - the host this box's own resolver reaches for when Windows PowerShell is
    absent - was invisible to Rule 2 no matter how it was cased.
    """
    folded = stripped.casefold()
    return folded.startswith(("powershell", "pwsh", _TASK_CMDLET.casefold()))


def _violates_python_code_rule(line: str) -> bool:
    """Rule 1 in PYTHON's dialect, for a tracked `.py`.

    IDENTICAL to `_violates_code_rule` except that the state-property needle is
    compared CASE-SENSITIVELY, because Python resolves attribute names that way:
    `panel.state` is a different attribute from `task.State`, not another
    spelling of it. Folding case here would be the same error as refusing to
    fold it in a `.ps1`, pointing the other way.

    THE EMITTER IS SHARED and is already correct for both dialects.
    `_EMITS_OUTPUT` folds only the `Write-*` cmdlets, which are PowerShell
    wherever they appear - including inside a Python string that builds a
    script - and leaves `print(` alone.

    THE STATED SCOPE LIMIT. A `.py` that embeds a PowerShell command as a
    STRING and spells the state read non-canonically inside it is not detected.
    `ops/check_task_liveness.py` is the one tracked `.py` that embeds such
    commands, and its own template spells them canonically. This is a boundary
    that had to be drawn somewhere, and the alternative - folding case in `.py`
    too - was measured against the real corpus and flagged a legitimate Python
    attribute read the moment a verdict word appeared beside it.
    """
    if not _EMITS_OUTPUT.search(line):
        return False
    if not (_STATE_PROPERTY in line or _LAST_RESULT in line):
        return False
    return _VERDICT_WORDS.search(line) is not None


def _code_rule_for(suffix: str):
    """The Rule 1 predicate for a file extension.

    `.ps1` is PowerShell and `.py` is Python, and the two resolve names by
    different rules, so one predicate cannot be right for both. `scan_file`
    routes through here rather than naming a predicate directly.
    """
    return _violates_code_rule if suffix == ".ps1" else _violates_python_code_rule


# --- Arm 6: the conflation figure is RE-DERIVED, never trusted --------------
#
# THE DEFECT THIS ARM EXISTS FOR. The Arm 5 note above states a count of the
# tracked lines a case fold would newly capture. The count that stood there
# first was EXACT WHEN WRITTEN and STALE WHEN SHIPPED: the dialect arms added
# in the same change are themselves lines in the corpus being counted, so the
# act of writing the arms moved the number the note reports. A CORPUS IS A
# SNAPSHOT, and a figure nobody re-derives decays in place while reading as
# fact.
#
# THE REPAIR HAS TWO HALVES AND NEEDS BOTH. The figure is SCOPED to exclude
# this module, which is what makes it stable under edits to this file - the Arm
# 5 note says why an absolute total cannot be. And it is RE-DERIVED here, from
# the real corpus, at test time, so drift anywhere else in the tree goes red
# instead of rotting quietly in a comment.
#
# WHY THE NUMBERS ARE PINNED AS CONSTANTS rather than only written in prose:
# prose is not machine-checkable, and this tree has measured twice that a
# hand-maintained figure goes stale silently. The constants below are the
# note's figures; the arm re-measures and compares.

#: The Arm 5 note's figures, for the tracked corpus MINUS this module.
_CONFLATION_LINES_OUTSIDE_THIS_MODULE = 76
_CONFLATION_EMITTERS_OUTSIDE_THIS_MODULE = 0

#: A FLOOR on the corpus, deliberately not its size. `git ls-files "*.py"
#: "*.ps1"` answered 142 files on 2026-09-11; pinning that exact number would
#: redden on the next `.py` anyone adds, which is a figure decaying by another
#: route. The floor exists so an EMPTY or collapsed corpus cannot satisfy the
#: comparisons below by having nothing to compare.
_CONFLATION_CORPUS_FLOOR = 100

#: Derived, never typed as a path: git reports forward-slash names.
_THIS_MODULE_NAME = "tests/" + Path(__file__).name


def _conflation_corpus() -> list[str]:
    """The population the Arm 5 note counts - tracked `.py` and `.ps1`, from git.

    A real corpus and not a stub, and not a hand-maintained list either: a list
    of paths that remembers to do X goes stale silently, measured twice here.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files", "*.py", "*.ps1"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def _conflation_lines(relative_names: list[str]) -> list[tuple[str, int, str]]:
    """Every line whose state needle is visible ONLY to the FOLDED comparison.

    That is the counting rule the Arm 5 note states, spelled once here so the
    note and the arm cannot drift apart: the folded needle hits and the
    case-SENSITIVE one does not. An unreadable tracked file raises `OSError` out
    of `read_text` and reddens this arm rather than shrinking the count, which
    is the same fail-closed posture `scan_file` takes above.
    """
    found: list[tuple[str, int, str]] = []
    for name in relative_names:
        candidate = REPO_ROOT / name
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if _reads_task_state(line) and not (_STATE_PROPERTY in line or _LAST_RESULT in line):
                found.append((name, number, line))
    return found


def test_the_conflation_figure_still_matches_the_tree() -> None:
    """Re-derive the Arm 5 note's figures from the corpus and grade the note.

    Not a shape assertion. A shape arm pins format and not input, and would stay
    green against any number at all.
    """
    corpus = _conflation_corpus()
    present = [name for name in corpus if (REPO_ROOT / name).is_file()]
    assert len(present) > _CONFLATION_CORPUS_FLOOR, (
        "the conflation corpus collapsed to " + str(len(present)) + " readable files, so no "
        "figure derived from it says anything"
    )
    assert _THIS_MODULE_NAME in corpus, (
        "this module left the tracked corpus, so excluding it is no longer the scoping the Arm 5 "
        "note describes"
    )

    every = _conflation_lines(corpus)
    outside = [row for row in every if row[0] != _THIS_MODULE_NAME]
    inside = [row for row in every if row[0] == _THIS_MODULE_NAME]

    assert inside, (
        "the derivation stopped seeing even this module's own pinned survivors, so it is "
        "measuring nothing and both comparisons below would pass by being empty"
    )
    assert len(outside) == _CONFLATION_LINES_OUTSIDE_THIS_MODULE, (
        "the Arm 5 note says " + str(_CONFLATION_LINES_OUTSIDE_THIS_MODULE) + " lines outside this "
        "module carry a state needle only non-canonically. The tree now says "
        + str(len(outside)) + ". Re-measure, then correct the note and the constant together.\n"
        + "\n".join(name + ":" + str(number) for name, number, _ in outside)
    )

    emitters = [row for row in outside if _EMITS_OUTPUT.search(row[2])]
    assert len(emitters) == _CONFLATION_EMITTERS_OUTSIDE_THIS_MODULE, (
        "the Arm 5 note says " + str(_CONFLATION_EMITTERS_OUTSIDE_THIS_MODULE) + " of those lines "
        "emit output. The tree now says " + str(len(emitters)) + ", and an emitting member is one "
        "verdict word away from Rule 1, so this is the half that matters.\n"
        + "\n".join(name + ":" + str(number) for name, number, _ in emitters)
    )
