"""The scheduled task's argv is graded against the code it actually calls.

THE DEFECT THIS EXISTS FOR. `ops/ResinCompute-Responder.xml` gained
`--source scheduledtask` BY HAND at the 2026-09-08 merge, and until this file
nothing asserted it was there. An edit to that XML alone could silently return
the one-label invocation record that commit 3964544 fixed, and every suite would
stay green: the XML is a tracked artifact naming a command, and nothing read the
command back against the parser that has to accept it.

THE FIRST VERSION OF THIS FILE WAS REFUTED, and the repair is the interesting
part. An adversary ran mutants in memory against its `grade_task_argv` and six
of them came back green - swap the script the argv names to a different real
file, drop `--arm`, swap the window's open and close values, append a bare
positional, or abbreviate a flag to `--ar` or `--latency-onl`. Each is a drift
this file exists to catch and each passed. The root causes, all now closed:

  - THE SCRIPT WAS NEVER GRADED, ONLY COUNTED. The old grader held the
    responder's path as a constant and interrogated that parser no matter what
    argv[0] said, then checked argv[0] with `is_file()` - existence, not
    identity. That is `command -v python3` succeeding on a Store alias. Now the
    parser comes from THE SCRIPT THE ARGV NAMES, and the script must be the one
    file in the tree that declares `SOURCE_SCHEDULED_TASK`.
  - MEANING WAS NEVER GRADED, ONLY ACCEPTANCE. `--latency-only --source
    scheduledtask` with no `--arm` parses perfectly and spawns nothing, so the
    trial goes silent while the argv stays valid. Acceptance by argparse is not
    the property that matters, so the argv is now run through `main` itself with
    `run_once` intercepted, and the `Bounds` the code BUILDS is what is graded.
  - ARGPARSE ABBREVIATION IS TOLERANCE, NOT AGREEMENT. `--ar` reaches `--arm`
    and `--sourc` reaches `--source`, so a truncated flag in a tracked artifact
    parsed clean. Every `--` token is now checked against the option spellings
    the parser itself declares.
  - NON-DASH EXTRAS WERE BINNED. `parse_known_args` returns them and the old
    loop only looked at extras beginning with `-`. The parser declares no
    positional action at all, so any positional is junk and is now named.

WHAT IS GRADED, AND AGAINST WHAT. Both sides are READ, neither is retyped. No
expected argv is written down here - a literal argv in a test is a snapshot, and
it agrees with itself the day it is written and with nothing afterwards:

  - WHICH SCRIPT: the tree is scanned for the file that declares
    `SOURCE_SCHEDULED_TASK`, and argv[0] must be it. The constant's own
    docstring at `tools/moon_sync_responder.py:363-372` says the task's argv is
    where that label has to be spelled, so this grades that sentence from the
    other end.
  - WHICH FLAGS: the option spellings come from the REAL `argparse` parser built
    inside that script's `main`, captured by letting `main` build it and
    intercepting the `parse_args` call.
  - WHAT THE FLAGS MEAN: the argv is handed to `main` with `run_once` replaced,
    and the captured `Bounds` must be ARMED. A task that parses and does nothing
    is the failure, not a task that fails to parse.
  - WHICH WINDOW IS WHICH: the `--window-opens` and `--window-closes` values are
    compared to the `StartBoundary` and `EndBoundary` of the task's own
    `TimeTrigger`, in the same file. The scheduler's window and the responder's
    window are the two independent halves of one kill switch, and a swap makes
    the responder's half close before it opens while both still look like ISO
    placeholders.
  - WHICH LABEL: `source_from_argv`, the scanner the `__main__` guard actually
    uses, plus the `SOURCE_*` constants the module declares, collected by
    attribute name.

THE THIRD REFUTATION, and it was an ASYMMETRY rather than a wrong answer.
`tests/test_supervisor_task_argv.py` arrived at b3bef1a to grade the supervisor
task's whole `<Exec>` block, and its docstring describes an edit that points a
task at the wrong interpreter with every suite staying green. That description
was STILL TRUE OF THIS TASK. Measured: `Command` and `WorkingDirectory` appeared
nowhere in this file, and `ops/ResinCompute-Responder.xml:92,94` carry
`__PYTHONW_EXE__` and `__INSTALL_ROOT__` whose only mention anywhere under
`tests/` was that new file - a file about the OTHER task. The responder is the
task this tree actually arms, so the ungraded half was the half that matters.
Closed here, and the two graders now make the same class of claim about their
own subjects:

  - WHICH INTERPRETER: `ops/install_responder_task.ps1:186` prints the
    interpreter it believes it is registering, from the same `$PythonwExe` it
    substitutes into the XML. Mapping that variable back through the installer's
    substitution table yields the placeholder `<Command>` must carry, by
    IDENTITY rather than by "some placeholder is there". `pythonw` and not
    `python` is load bearing and that installer says so at its lines 33-34 and
    62-64.
  - WHICH WORKING DIRECTORY: `ops/install_responder_task.ps1:151` builds the
    path it reads THIS XML from as `Join-Path $InstallRoot '...'`, and the
    relative path in that expression is asserted to be this grader's own
    `TASK_XML`. Not decoration: the argv names its script RELATIVELY.
  - WHICH SCRIPT, FROM THE INSTALLER'S SIDE TOO: that installer refuses at its
    line 102 to register unless `tools/moon_sync_responder.py` exists under the
    install root, so the argv must name the same file or the refusal guards a
    file the task never runs.
  - HOW MANY ACTIONS, AND WHICH ELEMENTS: the `<Exec>` count and the block's
    child element names, pinned by tuple equality so ORDER and LENGTH are one
    claim in one arm. A membership test would hold at any length.
  - WHICH PLACEHOLDERS: the file's `__NAME__` token set against the token half
    of the installer's `$xml.Replace` table, by SET EQUALITY with both
    cardinalities pinned in the same arm. A subset test passes on an XML that
    dropped one; a superset test passes on an installer filling tokens nobody
    uses.

THE INSTALLER IS `ops/install_responder_task.ps1`, NOT `ops/install_scheduled_task.ps1`.
Two installers live in `ops/` and they register two different tasks. Nothing
under `tests/` read the responder's one at all before this, and its six-entry
`$xml.Replace` table was checked back against nothing. `_installer_install_root_placeholder`
asserts the XML that installer reads IS the XML this grader grades, so aiming
this at the other one goes red rather than quietly grading one task against
another task's script.

ENCODING, MEASURED RATHER THAN ASSUMED. Commit fbe5c23 is about the XML
declaration, and it is easy to read it as "the file is UTF-16". It is not.
Measured at this HEAD: `ops/ResinCompute-Responder.xml` is 7-bit ASCII on disk,
no BOM, no NUL bytes, LF line endings, and its declaration says UTF-8. The
UTF-16 relabel happens IN MEMORY in `ops/install_responder_task.ps1` at
registration time, because `Register-ScheduledTask` takes a .NET string.

THE SECOND REFUTATION, and the two holes it measured in the repair above:

  - A TOKEN FOUR CAUSES CAN MINT IS NOT A FINGERPRINT. `main-refused-argv:2`
    keyed on the EXIT CODE, and argparse exits 2 as well, so half a window, a
    non-integer `--max-hops`, an undeclared flag and a bare positional all
    produced the same string. This tree keys on CATEGORY, never on a shared code
    or an interpolated message, so the refusal is now named from behaviour:
    whether it left through `main`'s own `return` or through argparse's
    `SystemExit`, and then what `parse_known_args` makes of the same argv.
  - `--latency-only` WAS CALLED UNGRADEABLE, AND IT WAS NOT. The previous repair
    said the code marks the flag optional so requiring it would be a snapshot.
    The basis was already inside the call this file intercepts: `main` selects
    `GRAMMAR_LATENCY_ONLY` from that flag and passes it to `run_once`. Grading
    the grammar the intercepted call RECEIVES, by identity against the module's
    own constant, reads a meaning off the code. It matters because the far end
    of this task is a HUMAN: with the flag dropped the argv parses, arms and
    graded clean, while every recorded cycle publishes `hops` as an integer
    under a lower-bound M1 - the exact row an earlier commit fixed by recording
    M1 INAPPLICABLE and never zero.
  - AND EXECUTION NOW WAITS FOR IDENTITY EVERYWHERE. Two arms called
    `_load_script` straight off `argv[0]`, running whatever the XML named -
    `core`, `core.atomic_io` and `ops.health` come in with it - before anything
    asked what it was. The gate moved into `_load_script` itself, so no caller
    can forget it.

NON-VACUITY, AND WHY THE OLD CONTROLS COULD NOT FIND THIS. The old file had six
controls and all six planted inside the four detector families the matcher was
already built for. A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES
CANNOT DISCOVER THAT THE MATCHER IS NARROW. The controls below therefore vary
the SHAPE as well as the value: a valid-shape wrong-meaning argv, a non-dash
positional, an abbreviation, and a script path that EXISTS and is the wrong
file. Every mutant is held in memory - the real file is never written.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shlex
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

# THE LIVENESS GRADER IS IMPORTED, NOT TRANSCRIBED. `ops/install_responder_task.ps1`
# and `ops/install_scheduled_task.ps1` run the SAME construct with the same
# variable names, so a second copy of the grader here would be a second thing to
# keep in step - which is how this tree earned a neutraliser asymmetry it is
# still carrying. One grader, two texts, one mutant table.
from tests.test_supervisor_task_argv import (
    _CALL_OPERATOR_RE,
    _EXIT_RE,
    _LASTEXITCODE_RE,
    LIVENESS_MUTANTS,
    LIVENESS_TOKENS,
    _installer_console_python_variable,
    _installer_liveness_checker,
    _installer_task_name_variable,
    _significant_statements,
    grade_installer_liveness,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_XML = REPO_ROOT / "ops" / "ResinCompute-Responder.xml"
#: The responder's OWN installer, and not `ops/install_scheduled_task.ps1`.
#: Two installers exist here and they register two different tasks; the one
#: that reads THIS XML is the one whose expectations may be read back into it,
#: and `_installer_install_root_placeholder` asserts that pairing rather than
#: assuming it.
INSTALLER_PS1 = REPO_ROOT / "ops" / "install_responder_task.ps1"
TASK_NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"

#: Every complaint bucket this grader can mint. `_complaint` refuses a bucket
#: that is not listed, so the declared set cannot drift away from the code that
#: mints the tokens, and `test_every_detector_has_a_control` pins it to the
#: mutant table by SET EQUALITY - a detector added without a control goes red on
#: its own, and so does a control added for a bucket the grader cannot mint.
GRADED_TOKENS = (
    "exec-count",
    "command-absent",
    "arguments-empty",
    "working-directory-absent",
    "unsubstituted-placeholder",
    "command-is-not-the-installer-interpreter",
    "working-directory-is-not-the-install-root",
    "script-is-not-the-path-the-installer-requires",
    "script-missing",
    "script-does-not-declare-the-task-label",
    "script-will-not-import",
    "script-not-the-responder",
    "flag-not-a-declared-spelling",
    "parser-rejects-argv",
    "unknown-flag",
    "unexpected-positional",
    "window-opens-is-not-the-trigger-start",
    "window-closes-is-not-the-trigger-end",
    "main-refused-argv",
    "task-argv-does-not-arm",
    "grammar-is-not-the-latency-only-grammar",
    "source-flag-absent",
    "source-label-unusable",
    "source-not-a-declared-label",
    "source-not-the-task-label",
)

#: Detectors with no in-memory control, and the measured reason for each. Held
#: as an explicit tuple so the coverage arm can compare by SET EQUALITY: a new
#: uncontrolled detector goes red, and so does controlling one of these later
#: without removing it from here.
#:
#: Both are blocked by the same measured fact, and it is a fact this file
#: ASSERTS rather than assumes - `test_exactly_one_file_declares_the_task_label`.
#: Reaching either detector needs a file that DECLARES `SOURCE_SCHEDULED_TASK`
#: and then either fails to import or lacks a `RESPONDER_CONTRACT` member.
#: Exactly one file in the tree declares it and it does neither, so the only way
#: to plant these controls is to write a second such file to disk, which this
#: file does not do.
UNCONTROLLED_TOKENS = ("script-will-not-import", "script-not-the-responder")

#: The installer's own placeholder shape, at `ops/install_responder_task.ps1:181`,
#: where it throws on any survivor. Same pattern, so a token this grader calls a
#: placeholder is a token that installer would refuse to leave behind.
_PLACEHOLDER_RE = re.compile(r"__[A-Z_]+__")

_REPLACE_RE = re.compile(
    r"\$xml\s*=\s*\$xml\.Replace\(\s*'(__[A-Z_]+__)'\s*,\s*(\$[A-Za-z_]\w*)\s*\)"
)
_INTERPRETER_BANNER_RE = re.compile(
    r"Write-Step\s*\(\s*'interpreter\s*:\s*'\s*\+\s*(\$[A-Za-z_]\w*)\s*\)"
)
_XML_PATH_RE = re.compile(r"\$xmlPath\s*=\s*Join-Path\s+(\$[A-Za-z_]\w*)\s+'([^']*)'")
_SCRIPT_GUARD_RE = re.compile(
    r"Test-Path\s+-LiteralPath\s+\(\s*Join-Path\s+(\$[A-Za-z_]\w*)\s+'([^']*\.py)'\s*\)"
)

#: The attribute name whose declaration IDENTIFIES the responder. Not a path -
#: a path is the thing that went stale. The scan below finds whichever file
#: declares it, so moving or renaming the responder moves this grader with it,
#: while pointing the task at some other real file goes red.
TASK_LABEL_CONSTANT = "SOURCE_SCHEDULED_TASK"

#: What this grader has to be able to reach on the script the argv names. It is
#: the grader's own dependency list rather than a description of the responder,
#: which is why it cannot drift away from what is actually used below.
RESPONDER_CONTRACT = (
    "main",
    "run_once",
    "source_from_argv",
    "GRAMMAR_LATENCY_ONLY",
    "SOURCE_FLAG",
    TASK_LABEL_CONSTANT,
)

#: The reasons `main` can decline an argv, as CATEGORIES rather than as an exit
#: code. `main` returns 2 from its own window precondition and argparse exits 2
#: from three unrelated causes, so the code is a token four different drifts can
#: mint. Each name below is derived from behaviour - which control path the
#: refusal left through, then what `parse_known_args` does with the same argv -
#: and never from argparse's message text, which is prose this tree does not own.
REFUSAL_OWN_PRECONDITION = "own-precondition"
REFUSAL_FLAG_VALUE_REJECTED = "flag-value-rejected"
REFUSAL_UNDECLARED_FLAG = "undeclared-flag"
REFUSAL_UNDECLARED_POSITIONAL = "undeclared-positional"
#: The residual bucket: argparse refused an argv that `parse_known_args` accepts
#: whole. No known cause reaches it, and it exists so an unknown one arrives
#: named rather than wearing one of the four fingerprints above.
REFUSAL_UNCLASSIFIED = "unclassified"

_IMPORT_FAILURES = (
    AttributeError,
    ImportError,
    NameError,
    OSError,
    SyntaxError,
    SystemExit,
    TypeError,
    ValueError,
)


def _complaint(bucket: str, detail: str = "") -> str:
    """One stable complaint token, `bucket` or `bucket:detail`.

    The bucket is checked against `GRADED_TOKENS` on the way out, so the
    declared detector set is enforced by the code that mints the tokens rather
    than maintained alongside it.
    """
    if bucket not in GRADED_TOKENS:
        raise AssertionError(f"{bucket} is not a declared complaint bucket")
    return f"{bucket}:{detail}" if detail else bucket


def _installer_text() -> str:
    """The responder's installer, decoded, with a non-vacuity floor on its size."""
    raw = INSTALLER_PS1.read_bytes()
    if not raw:
        raise AssertionError(f"{INSTALLER_PS1} is empty - every derivation below reads it")
    return raw.decode("ascii", errors="replace")


def _installer_substitutions() -> dict[str, str]:
    """Placeholder token -> the PowerShell variable the installer fills it from.

    Read from the `$xml.Replace(...)` calls at `ops/install_responder_task.ps1:174-179`.
    This is the authoritative answer to "which tokens in this XML are placeholders
    the installer will actually substitute", and the installer itself throws at
    its line 181 on any `__NAME__` survivor.
    """
    found = dict(_REPLACE_RE.findall(_installer_text()))
    if not found:
        raise AssertionError(
            "no placeholder substitutions found in the installer - the scan is measuring nothing"
        )
    return found


def _by_variable() -> dict[str, str]:
    """The substitution table read backwards: variable -> the token it fills."""
    return {value: key for key, value in _installer_substitutions().items()}


def _installer_interpreter_placeholder() -> str:
    """The placeholder the `<Command>` must carry, derived from the installer's banner.

    `ops/install_responder_task.ps1:186` prints the interpreter it believes it is
    registering, from the same `$PythonwExe` variable it substitutes into the
    XML. Mapping that variable back through the substitution table yields the
    token by IDENTITY rather than by "some placeholder is there".

    THE RESPONDER INSTALLER PRINTS NO COMMAND BANNER, which is where it differs
    from the supervisor's. There is no line announcing interpreter-plus-argv, so
    the argv half of that grade is unavailable here and is read from the
    installer's responder guard instead - see `_installer_required_script`.

    `pythonw` rather than `python` is load bearing and the installer says so at
    its lines 33-34 and 62-64: a scheduled task started with `python.exe` flashes
    a console window on every fire, and this XML pairs the choice with
    `<Hidden>true</Hidden>` at its line 69.
    """
    match = _INTERPRETER_BANNER_RE.search(_installer_text())
    if match is None:
        raise AssertionError(
            "the installer prints no interpreter banner - the interpreter derivation is measuring nothing"
        )
    variable = match.group(1)
    by_variable = _by_variable()
    if variable not in by_variable:
        raise AssertionError(
            f"the installer banner names {variable}, which it substitutes into no placeholder"
        )
    return by_variable[variable]


def _installer_install_root_placeholder() -> str:
    """The placeholder standing for the checkout root, and the XML it reads.

    `ops/install_responder_task.ps1:151` builds the path to THIS task definition
    as `Join-Path $InstallRoot 'ops/ResinCompute-Responder.xml'`. The variable in
    that expression is the install root by construction, and the relative path
    beside it is asserted to be this grader's own `TASK_XML` - so the installer
    that supplies the expectation is the installer that reads the graded file,
    and pointing this at the OTHER installer in `ops/` goes red here rather than
    quietly grading one task against another task's script.

    Not decoration: the argv names its script by a RELATIVE path, which resolves
    only from the checkout root.
    """
    match = _XML_PATH_RE.search(_installer_text())
    if match is None:
        raise AssertionError(
            "the installer builds no task-XML path - the install-root derivation is measuring nothing"
        )
    variable, relative = match.group(1), match.group(2).replace("\\", "/")
    if relative != TASK_XML.relative_to(REPO_ROOT).as_posix():
        raise AssertionError(
            f"the installer reads {relative}, but this grader grades "
            f"{TASK_XML.relative_to(REPO_ROOT).as_posix()}"
        )
    by_variable = _by_variable()
    if variable not in by_variable:
        raise AssertionError(
            f"the installer locates the XML with {variable}, which it substitutes into no placeholder"
        )
    return by_variable[variable]


def _installer_required_script() -> str:
    """The repo-relative script the installer REFUSES to register without.

    `ops/install_responder_task.ps1:102-104` throws unless
    `Join-Path $InstallRoot 'tools/moon_sync_responder.py'` exists, so that path
    is the installer's own statement of what it believes it is arming. The argv
    in the `<Exec>` block must name the same file or the installer's precondition
    guards a file the task never runs - a check that passes while proving nothing.

    THE MATCH IS ASSERTED UNIQUE. `ops/install_responder_task.ps1:231` also joins
    the install root to a `.py` path, so a pattern that merely found A `.py` join
    could silently start reading the liveness checker instead. The anchor is the
    `Test-Path -LiteralPath (Join-Path ...)` form, and exactly one of those
    exists in the file.
    """
    matches = _SCRIPT_GUARD_RE.findall(_installer_text())
    if len(matches) != 1:
        raise AssertionError(
            f"the installer has {len(matches)} Test-Path script guards - the derivation is ambiguous"
        )
    variable, relative = matches[0][0], matches[0][1].replace("\\", "/")
    if variable not in _by_variable():
        raise AssertionError(
            f"the installer guards the script with {variable}, which it substitutes into no placeholder"
        )
    return relative


def _repo_python_files() -> list[Path]:
    """Every tracked-looking `.py` under the repo root, dot dirs and caches out."""
    return [
        path
        for path in REPO_ROOT.rglob("*.py")
        if not any(
            part.startswith(".") or part == "__pycache__" for part in path.relative_to(REPO_ROOT).parts
        )
    ]


def _scripts_declaring_the_task_label() -> set[str]:
    """Repo-relative POSIX paths of the files that DECLARE the task's label.

    A BYTE SCAN, NOT AN IMPORT SWEEP. Importing every `.py` in the tree to ask
    which one owns a constant would run 90-odd modules' import-time code to
    answer a question about text. The declaration is matched at the start of a
    line so a mention of the name in a docstring or an import does not count as
    owning it.
    """
    needle = (TASK_LABEL_CONSTANT + " = ").encode("ascii")
    owners = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in _repo_python_files()
        if any(line.startswith(needle) for line in path.read_bytes().splitlines())
    }
    if not owners:
        raise AssertionError(
            f"no file in the tree declares {TASK_LABEL_CONSTANT} - the scan is measuring nothing"
        )
    return owners


_MODULE_CACHE: dict[str, ModuleType] = {}


def _load_script(script: str) -> ModuleType:
    """Load the module at a repo-relative path, as `tests/test_moon_sync_responder.py` does.

    `tools/` carries no `__init__.py`, so loading by file location is the tree's
    existing convention and does not lean on implicit namespace packages. Cached
    because a mutant sweep would otherwise re-execute the responder once per arm.

    IDENTITY BEFORE EXECUTION, AT THE CHOKE POINT. Loading runs the named
    module's top level - `core`, `core.atomic_io` and `ops.health` all come in
    with it - so asking WHAT a path is only after running it is the same shape
    as the script-identity hole this file already closed once. `grade_task_argv`
    checks before it calls here; the arms that call here directly off `argv[0]`
    did not, and the gate belongs in one place rather than at each caller.
    """
    if script not in _scripts_declaring_the_task_label():
        raise AssertionError(
            f"refusing to execute {script}: it does not declare {TASK_LABEL_CONSTANT}"
        )
    if script in _MODULE_CACHE:
        return _MODULE_CACHE[script]
    spec = importlib.util.spec_from_file_location(
        f"task_argv_grader_{abs(hash(script))}", REPO_ROOT / script
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"no loader for {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _MODULE_CACHE[script] = module
    return module


class _ParserCaptured(Exception):
    """Raised to unwind out of `main` the instant the parser is built."""


def _live_parser(module: ModuleType) -> argparse.ArgumentParser:
    """The REAL parser from that module's `main`, captured before it parses anything.

    `main` builds its parser as a local and never exposes it, so the only way to
    read the authoritative flag set is to let `main` build it. `parse_args` is
    the first thing that happens after construction and before any side effect,
    so intercepting it yields the finished parser and runs none of the
    responder.
    """
    captured: dict[str, argparse.ArgumentParser] = {}
    real_parse_args = argparse.ArgumentParser.parse_args

    def _spy(self: argparse.ArgumentParser, *args: object, **kwargs: object) -> None:
        captured["parser"] = self
        raise _ParserCaptured

    argparse.ArgumentParser.parse_args = _spy  # type: ignore[method-assign]
    try:
        module.main(argv=[])
    except _ParserCaptured:
        pass
    finally:
        argparse.ArgumentParser.parse_args = real_parse_args  # type: ignore[method-assign]

    parser = captured.get("parser")
    if parser is None:
        raise AssertionError(
            "main() did not reach parse_args - the capture is measuring nothing"
        )
    return parser


def _declared_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Every option spelling the parser declares, e.g. `--arm`, `--window-opens`.

    ARGPARSE ACCEPTS ABBREVIATIONS AND THAT IS THE POINT OF THIS FUNCTION.
    `--ar` reaches `--arm` and `--sourc` reaches `--source`, so acceptance by
    the parser says nothing about whether the tracked artifact spells the flag
    the way the code declares it. `_actions` is private, and it is the only
    place the declared spellings exist; the alternative is retyping them here,
    which is the snapshot this file refuses to keep.
    """
    spellings = {option for action in parser._actions for option in action.option_strings}
    if not spellings:
        raise AssertionError("the captured parser declares no options - it is not the real one")
    return spellings


def _parser_takes_positionals(parser: argparse.ArgumentParser) -> bool:
    """Whether the parser declares any positional action at all.

    Grounds the positional-junk complaint in the parser rather than in an
    assumption: if a positional is ever added, this stops complaining on its own.
    """
    return any(not action.option_strings for action in parser._actions)


def _declared_source_labels(module: ModuleType) -> set[str]:
    """Every routing label the module declares, by attribute name.

    `SOURCE_FLAG` is excluded because it is the flag spelling `--source`, not a
    label. Collected dynamically so a label added to the module needs no edit
    here, and so this asserts against the module rather than against a literal
    retyped into a test.
    """
    labels = {
        value
        for name, value in vars(module).items()
        if name.startswith("SOURCE_") and name != "SOURCE_FLAG" and isinstance(value, str)
    }
    if not labels:
        raise AssertionError(
            "no SOURCE_* labels found on the module - the collector is measuring nothing"
        )
    return labels


class _MainRun(NamedTuple):
    """What one intercepted run of `main` revealed about the argv it was handed.

    `raised` is the discriminant the exit code cannot carry: `main` declines its
    own precondition with `return 2`, while argparse leaves through
    `SystemExit(2)`. Two unrelated refusals, one number.
    """

    code: object
    bounds: object | None
    grammar: object | None
    raised: bool


def _refusal_category(
    parser: argparse.ArgumentParser, flags: list[str], run: _MainRun
) -> str:
    """Name WHY `main` declined this argv, from behaviour rather than from a code.

    Four causes minted the identical `main-refused-argv:2` before this existed.
    They are separated by asking the code two structural questions, neither of
    which reads argparse's message text:

      - which control path the refusal left through - `main`'s own `return`, or
        argparse's `SystemExit`;
      - and, for an argparse refusal, what `parse_known_args` makes of the same
        argv. It tolerates undeclared tokens and hands them back, so a refusal
        it ALSO raises on is a declared flag given an unusable value, while one
        it accepts is an undeclared token - a flag or a positional by its prefix.
    """
    if not run.raised:
        return REFUSAL_OWN_PRECONDITION
    try:
        _, extras = parser.parse_known_args(flags)
    except SystemExit:
        return REFUSAL_FLAG_VALUE_REJECTED
    if any(extra.startswith("-") for extra in extras):
        return REFUSAL_UNDECLARED_FLAG
    if extras:
        return REFUSAL_UNDECLARED_POSITIONAL
    return REFUSAL_UNCLASSIFIED


def _bounds_from_main(module: ModuleType, flags: list[str]) -> _MainRun:
    """Run the argv through the REAL `main`, and capture the `Bounds` it builds.

    THE ONLY GRADE THAT CAN SEE A NO-OP. `--latency-only --source scheduledtask`
    without `--arm` is a perfectly valid argv that spawns nothing and delivers
    nothing, so no amount of parser interrogation can tell it from the real
    thing. `main` composes `Bounds(armed=args.arm, ...)` and hands it to
    `run_once`, so replacing `run_once` reads the decision the code actually
    made, and reuses `main`'s own precondition - the `return 2` when `--arm`
    arrives without a window - rather than reimplementing it here.

    THE GRAMMAR IS CAPTURED TOO, and it is not decoration. `main` selects
    `GRAMMAR_LATENCY_ONLY` or `GRAMMAR` from `--latency-only` and passes the
    choice here, so the flag's presence is readable as a MEANING from the call
    the code makes rather than as a spelling in an argv retyped into a test.

    NOTHING TOUCHES THE DISK. `run_once` is the only side effect on this path;
    `main` before it builds a `Path` and selects a grammar. `bounds` and
    `grammar` are `None` when `main` refused the argv and never called through.
    """
    captured: dict[str, object] = {}
    real_run_once = module.run_once
    raised = False

    def _spy(**kwargs: object) -> dict[str, object]:
        captured["bounds"] = kwargs.get("bounds")
        captured["grammar"] = kwargs.get("grammar")
        return {"note": None, "delivered": False, "reasons": [], "held": False}

    module.run_once = _spy
    try:
        code: object = module.main(argv=list(flags))
    except SystemExit as exit_call:
        code = exit_call.code
        raised = True
    finally:
        module.run_once = real_run_once
    return _MainRun(code, captured.get("bounds"), captured.get("grammar"), raised)


def _exec_fields(xml_text: str) -> tuple[int, str | None, str | None, str | None]:
    """`(exec count, Command, Arguments, WorkingDirectory)` from a task XML.

    The COUNT is returned rather than asserted so a second `<Exec>` arrives as a
    graded complaint instead of an exception. Two Exec blocks means the argv this
    file grades is only one of the things the task runs, which is a drift and not
    a crash.
    """
    root = ElementTree.fromstring(xml_text)
    exec_nodes = root.findall(f".//{TASK_NS}Exec")
    if len(exec_nodes) != 1:
        return len(exec_nodes), None, None, None
    node = exec_nodes[0]
    return (
        1,
        node.findtext(f"{TASK_NS}Command"),
        node.findtext(f"{TASK_NS}Arguments"),
        node.findtext(f"{TASK_NS}WorkingDirectory"),
    )


def _exec_child_tags(xml_text: str) -> tuple[str, ...]:
    """The `<Exec>` block's child element names, in document order, namespace stripped.

    Order and length both matter and both are pinned by the arm that reads this:
    an `<Exec>` is not a bag of optional fields here, it is the three elements
    `ops/install_responder_task.ps1` fills.
    """
    root = ElementTree.fromstring(xml_text)
    exec_nodes = root.findall(f".//{TASK_NS}Exec")
    if len(exec_nodes) != 1:
        raise AssertionError(f"expected exactly one Exec element, found {len(exec_nodes)}")
    return tuple(child.tag.removeprefix(TASK_NS) for child in exec_nodes[0])


def _exec_argv(xml_text: str) -> list[str]:
    """The `<Exec>` argv from a task XML, script path first."""
    count, _, arguments, _ = _exec_fields(xml_text)
    if count != 1:
        raise AssertionError(f"expected exactly one Exec element, found {count}")
    if not arguments:
        raise AssertionError("Exec carries no Arguments element")
    return shlex.split(arguments)


def _trigger_boundaries(xml_text: str) -> tuple[str, str]:
    """The trigger's own `StartBoundary` and `EndBoundary`, in that order.

    THE SECOND HALF OF THE KILL SWITCH, read from the same file. The window the
    responder is told about on argv and the window the scheduler enforces are
    deliberately independent, which is exactly why they must be the same two
    values pointing the same way round. Both are placeholder tokens in the
    tracked file and both are substituted by `ops/install_responder_task.ps1`,
    so comparing them to each other survives substitution while a swap does not.
    """
    root = ElementTree.fromstring(xml_text)
    start = root.findtext(f".//{TASK_NS}StartBoundary")
    end = root.findtext(f".//{TASK_NS}EndBoundary")
    if not start or not end:
        raise AssertionError("the trigger carries no StartBoundary/EndBoundary pair")
    return start, end


def grade_task_argv(xml_text: str) -> list[str]:
    """Complaints about a task XML's argv, graded against the live code.

    Returns an empty list when the argv names the responder, spells every flag
    the way the responder declares it, means an ARMED cycle inside the trigger's
    own window, and carries the label the responder routes the task on. Every
    complaint is a stable token so an arm can name which detector fired rather
    than merely that something did.
    """
    complaints: list[str] = []
    count, command, arguments, working_directory = _exec_fields(xml_text)
    if count != 1:
        return [_complaint("exec-count", str(count))]

    interpreter_placeholder = _installer_interpreter_placeholder()
    install_root_placeholder = _installer_install_root_placeholder()
    required_script = _installer_required_script()
    substituted = _installer_substitutions()

    # PLACEHOLDER SURVIVORS, the installer's own failure mode at its line 181.
    # A token shaped like a placeholder that the installer does not substitute
    # reaches `Register-ScheduledTask` verbatim, so the task runs an interpreter
    # literally named `__PYTHON_EXE__`.
    block = " ".join(part or "" for part in (command, arguments, working_directory))
    for token in sorted(set(_PLACEHOLDER_RE.findall(block))):
        if token not in substituted:
            complaints.append(_complaint("unsubstituted-placeholder", token))

    # WHICH INTERPRETER. `python.exe` here is a task that flashes a console on
    # every fire, which is the case the installer's own comment calls out and
    # which `<Hidden>true</Hidden>` cannot undo.
    if command is None:
        complaints.append(_complaint("command-absent"))
    elif command != interpreter_placeholder:
        complaints.append(_complaint("command-is-not-the-installer-interpreter", command))

    # WHICH WORKING DIRECTORY. The argv names its script RELATIVELY, so this is
    # what makes the path in `<Arguments>` resolve at all.
    if working_directory is None:
        complaints.append(_complaint("working-directory-absent"))
    elif working_directory != install_root_placeholder:
        complaints.append(
            _complaint("working-directory-is-not-the-install-root", working_directory)
        )

    if not arguments:
        return [*complaints, _complaint("arguments-empty")]
    argv = shlex.split(arguments)
    if not argv:
        return [*complaints, _complaint("arguments-empty")]

    script, flags = argv[0], argv[1:]

    # WHAT THE INSTALLER BELIEVES IT IS ARMING. Its line 102 refuses to register
    # unless this exact relative path exists under the install root; an argv
    # naming anything else makes that precondition a check on a file the task
    # never runs.
    if script != required_script:
        complaints.append(_complaint("script-is-not-the-path-the-installer-requires", script))

    # IDENTITY BEFORE ANYTHING ELSE. Everything below reads the named script's
    # own parser and constants, so grading has no meaning until the argv is
    # known to name the responder rather than merely to name a file.
    if not (REPO_ROOT / script).is_file():
        return [*complaints, _complaint("script-missing", script)]
    if script not in _scripts_declaring_the_task_label():
        return [*complaints, _complaint("script-does-not-declare-the-task-label", script)]
    try:
        module = _load_script(script)
    except _IMPORT_FAILURES:
        return [*complaints, _complaint("script-will-not-import", script)]
    missing = [name for name in RESPONDER_CONTRACT if not hasattr(module, name)]
    if missing:
        return [
            *complaints,
            _complaint("script-not-the-responder", f"{script}:{','.join(missing)}"),
        ]

    parser = _live_parser(module)
    declared = _declared_option_strings(parser)

    # SPELLING, WHICH ARGPARSE WILL NOT CHECK FOR US. Only `--` tokens are
    # examined: this parser declares no single-dash option, and a bare `-`
    # prefix is how a negative number would arrive as a value.
    for token in flags:
        if not token.startswith("--"):
            continue
        spelling = token.split("=", 1)[0]
        if spelling not in declared:
            complaints.append(_complaint("flag-not-a-declared-spelling", spelling))

    parsed: argparse.Namespace | None = None
    try:
        parsed, extras = parser.parse_known_args(flags)
    except SystemExit:
        complaints.append(_complaint("parser-rejects-argv"))
    else:
        for extra in extras:
            if extra.startswith("-"):
                complaints.append(_complaint("unknown-flag", extra))
            elif not _parser_takes_positionals(parser):
                complaints.append(_complaint("unexpected-positional", extra))

    # WHICH WINDOW IS WHICH, against the trigger in the same file.
    if parsed is not None:
        start_boundary, end_boundary = _trigger_boundaries(xml_text)
        if parsed.window_opens != start_boundary:
            complaints.append(
                _complaint("window-opens-is-not-the-trigger-start", str(parsed.window_opens))
            )
        if parsed.window_closes != end_boundary:
            complaints.append(
                _complaint("window-closes-is-not-the-trigger-end", str(parsed.window_closes))
            )

    # WHAT THE ARGV MEANS, from the code's own construction.
    run = _bounds_from_main(module, flags)
    if run.bounds is None:
        complaints.append(_complaint("main-refused-argv", _refusal_category(parser, flags, run)))
    else:
        if not getattr(run.bounds, "armed", False):
            complaints.append(_complaint("task-argv-does-not-arm"))
        # WHICH GRAMMAR THE CALL ACTUALLY CARRIES. Compared by IDENTITY against
        # the module's own constant, so an equal literal cannot stand in for it
        # and a reworded grammar needs no edit here. The far end of this task is
        # a human: without `--latency-only` the argv still parses and still
        # arms, and every cycle it records publishes `hops` as an integer under
        # a lower-bound M1 for a run that has no machine at the other end. That
        # is the row the latency-only grammar exists to make impossible.
        if run.grammar is not module.GRAMMAR_LATENCY_ONLY:
            complaints.append(_complaint("grammar-is-not-the-latency-only-grammar"))

    # THE LABEL. Membership and identity are reported INDEPENDENTLY rather than
    # chained: under an `elif` the membership check could never speak on a real
    # drift, because any label that fails it also fails the identity check and
    # the identity check spoke first. Separated, "no constant declares this" and
    # "a declared label, but not the task's" are two different repairs.
    routed = module.source_from_argv(flags)
    inline = module.SOURCE_FLAG + "="
    named = module.SOURCE_FLAG in flags or any(item.startswith(inline) for item in flags)
    if not named:
        complaints.append(_complaint("source-flag-absent"))
    elif routed is None:
        complaints.append(_complaint("source-label-unusable"))
    else:
        if routed not in _declared_source_labels(module):
            complaints.append(_complaint("source-not-a-declared-label", routed))
        if routed != getattr(module, TASK_LABEL_CONSTANT):
            complaints.append(_complaint("source-not-the-task-label", routed))

    return complaints


def _real_xml_text() -> str:
    """The task XML, decoded as measured rather than as assumed.

    Asserts the on-disk bytes are 7-bit ASCII before decoding. That is both the
    repo's own rule and the honest reading of fbe5c23: the UTF-16 declaration is
    written by the installer into a .NET string, and never onto this file.
    """
    raw = TASK_XML.read_bytes()
    non_ascii = [byte for byte in raw if byte > 0x7F]
    assert not non_ascii, f"task XML is not 7-bit ASCII on disk: {non_ascii[:8]}"
    return raw.decode("ascii")


def _mutate(xml_text: str, old: str, new: str) -> str:
    """Replace inside the argv line, asserting the mutation actually landed.

    A mutant built from a pattern that is not present would leave the text
    identical, and the arm below would then pass while testing the real file
    twice - a control that controls nothing.
    """
    assert old in xml_text, f"mutation target not present: {old!r}"
    mutated = xml_text.replace(old, new, 1)
    assert mutated != xml_text, "mutation did not change the text"
    return mutated


def test_task_xml_is_ascii_on_disk() -> None:
    """The measured encoding claim, so a silent re-encode is not invisible."""
    raw = TASK_XML.read_bytes()
    assert raw[:2] != b"\xff\xfe", "task XML gained a UTF-16 LE BOM"
    assert raw[:3] != b"\xef\xbb\xbf", "task XML gained a UTF-8 BOM"
    assert b"\x00" not in raw, "task XML contains NUL bytes"
    _real_xml_text()


def test_real_task_argv_is_accepted_by_the_code_it_calls() -> None:
    """The neighbours-survive guard: the tracked artifact grades clean."""
    assert grade_task_argv(_real_xml_text()) == []


def test_exactly_one_file_declares_the_task_label() -> None:
    """The identity anchor is an anchor only while it names one file.

    If two files declared the label, `script-does-not-declare-the-task-label`
    would accept either and the script grade would go soft without any arm going
    red. So the uniqueness is asserted rather than assumed.
    """
    owners = _scripts_declaring_the_task_label()
    assert len(owners) == 1, f"{TASK_LABEL_CONSTANT} is declared in more than one file: {sorted(owners)}"


def test_real_task_argv_names_the_script_that_declares_the_task_label() -> None:
    """WHICH script the XML calls, not merely that some file is there.

    The old version of this arm asked `is_file()` and would have accepted any
    real path in the tree, which is how a swap to a different tool passed.
    """
    script = _exec_argv(_real_xml_text())[0]
    assert (REPO_ROOT / script).is_file(), f"task argv names a missing script: {script}"
    assert script in _scripts_declaring_the_task_label(), (
        f"task argv names {script}, which does not declare {TASK_LABEL_CONSTANT}"
    )


def test_real_task_argv_names_the_scheduled_task_label() -> None:
    """The value assertion, not a shape one.

    `--source scheduledtask` is the case known to carry a value, so the value is
    asserted - against the module constant, so a rename in the module and a
    rename in the XML have to happen together or this goes red.
    """
    argv = _exec_argv(_real_xml_text())
    module = _load_script(argv[0])
    assert module.source_from_argv(argv[1:]) == module.SOURCE_SCHEDULED_TASK


def test_real_task_argv_means_an_armed_cycle() -> None:
    """The meaning assertion: the code, handed this argv, builds an ARMED run.

    A task that parses and then does nothing is the silent failure this whole
    file exists to make loud, and it is invisible to every parser-level check.
    """
    argv = _exec_argv(_real_xml_text())
    module = _load_script(argv[0])
    run = _bounds_from_main(module, argv[1:])
    assert run.bounds is not None, f"main refused the tracked argv with exit {run.code}"
    assert run.bounds.armed is True, (
        "the tracked argv builds a disarmed cycle - it delivers nothing"
    )


def test_real_task_argv_means_a_latency_only_cycle() -> None:
    """The far end of this task is a HUMAN, and the call says so or it does not.

    The previous version of this file left `--latency-only` ungraded on the
    grounds that the code marks it optional and there was no code-grounded basis
    to require it. The basis is in the call this file already intercepts:
    `main` passes `grammar=` and the value is the module's own
    `GRAMMAR_LATENCY_ONLY` exactly when the flag is present. That is a property
    read from the code, not a snapshot of the argv.

    WHY IT MATTERS. Without the flag the argv parses, arms, and grades clean on
    every other detector, while each `record_cycle` row publishes `hops` as an
    integer under `m1_status='lower-bound'` for a run whose far end is a person.
    The second half of this arm is its own non-vacuity control: it drops the
    flag in memory and shows the captured grammar change.
    """
    argv = _exec_argv(_real_xml_text())
    module = _load_script(argv[0])

    run = _bounds_from_main(module, argv[1:])
    assert run.grammar is module.GRAMMAR_LATENCY_ONLY, (
        f"the tracked argv runs under {run.grammar!r}, not the latency-only grammar"
    )

    without = _bounds_from_main(module, [item for item in argv[1:] if item != "--latency-only"])
    assert without.bounds is not None, "the control argv did not reach run_once"
    assert without.grammar is not module.GRAMMAR_LATENCY_ONLY, (
        "dropping the flag changed nothing - the grammar capture is measuring nothing"
    )


def test_real_task_argv_window_matches_its_own_trigger() -> None:
    """The two halves of the kill switch point the same way round."""
    xml_text = _real_xml_text()
    argv = _exec_argv(xml_text)
    module = _load_script(argv[0])
    parsed, _ = _live_parser(module).parse_known_args(argv[1:])
    start_boundary, end_boundary = _trigger_boundaries(xml_text)
    assert parsed.window_opens == start_boundary
    assert parsed.window_closes == end_boundary
    assert start_boundary != end_boundary, "the trigger opens and closes on the same value"


def test_the_tracked_exec_block_declares_exactly_the_elements_the_installer_fills() -> None:
    """One action, three elements, in order - and the count is pinned in the SAME arm.

    A separate length arm leaves the primary one vacuous, and a membership test
    would hold at any length: `("Command", *rest)` is true of an Exec block that
    also carries a second action. Tuple equality pins ORDER and LENGTH together,
    and the Exec count is compared inside the same tuple so a second `<Exec>`
    cannot slip past a passing element check.
    """
    count, _, _, _ = _exec_fields(_real_xml_text())
    assert (count, _exec_child_tags(_real_xml_text())) == (
        1,
        ("Command", "Arguments", "WorkingDirectory"),
    )


def test_the_tracked_command_is_the_interpreter_the_installer_resolves() -> None:
    """WHICH interpreter, by identity against the placeholder the installer fills.

    THE DEFECT THIS CLOSES. `Command` and `WorkingDirectory` appeared nowhere in
    this file until now, so `ops/ResinCompute-Responder.xml:92,94` were graded by
    nothing under `tests/` - the supervisor grader names those two tokens, and it
    is a file about the other task. An edit pointing THIS task at `python.exe`,
    at a placeholder nobody substitutes, or at nothing at all left every suite
    green, and this is the task the tree actually arms.

    The expectation is READ, not retyped: `ops/install_responder_task.ps1:186`
    prints the interpreter it believes it is registering, and the variable in
    that banner is mapped back through the installer's own substitution table.
    The size of that table is pinned in this same arm, because a banner or a
    table that stopped parsing would raise rather than pass - and a derivation
    that silently narrowed would not.
    """
    substituted = _installer_substitutions()
    assert len(substituted) == 6, f"the installer substitutes {sorted(substituted)}"

    _, command, _, _ = _exec_fields(_real_xml_text())
    assert command == _installer_interpreter_placeholder()


def test_the_tracked_working_directory_is_the_root_the_installer_reads_from() -> None:
    """The argv names its script RELATIVELY, so this element is what resolves it.

    The expectation comes from the installer expression that locates THIS file -
    `ops/install_responder_task.ps1:151` - and `_installer_install_root_placeholder`
    asserts the relative path in that expression is this grader's own `TASK_XML`.
    So the installer supplying the answer is the installer reading the graded
    artifact, and aiming this at `ops/install_scheduled_task.ps1` goes red here
    instead of grading one task against another task's script.
    """
    _, _, _, working_directory = _exec_fields(_real_xml_text())
    assert working_directory == _installer_install_root_placeholder()


def test_the_tracked_script_is_the_file_the_installer_refuses_to_register_without() -> None:
    """The installer's precondition and the task's argv name the SAME file.

    `ops/install_responder_task.ps1:102-104` throws unless that relative path
    exists under the install root. If the argv named something else, the throw
    would be guarding a file the task never runs - a check that passes while
    proving nothing about what was armed.
    """
    script = _exec_argv(_real_xml_text())[0]
    assert script == _installer_required_script()


def test_the_tracked_placeholders_are_exactly_the_ones_the_installer_substitutes() -> None:
    """SET EQUALITY over the whole file, with both cardinalities pinned in one arm.

    A subset test would pass on an XML that dropped a placeholder, and a
    superset test would pass on an installer that filled tokens nobody uses.
    Equality is the only relation that catches both directions, and the count
    rides in the same tuple so an arm comparing two empty sets cannot read as a
    pass. Populations, named: the left set is every `__NAME__` token appearing
    anywhere in `ops/ResinCompute-Responder.xml`, comment block included; the
    right set is the token half of the `$xml.Replace` calls in
    `ops/install_responder_task.ps1`.

    The Exec block's own four are then pinned separately, and the literals are
    welded to the installer by the PROPER-subset assertion beside them: a rename
    on either side goes red rather than quietly agreeing with itself.
    """
    substituted = set(_installer_substitutions())
    xml_tokens = set(_PLACEHOLDER_RE.findall(_real_xml_text()))
    assert (xml_tokens, len(xml_tokens)) == (substituted, 6)

    _, command, arguments, working_directory = _exec_fields(_real_xml_text())
    block = " ".join(part or "" for part in (command, arguments, working_directory))
    exec_tokens = set(_PLACEHOLDER_RE.findall(block))
    assert exec_tokens == {
        "__PYTHONW_EXE__",
        "__INSTALL_ROOT__",
        "__START_BOUNDARY__",
        "__END_BOUNDARY__",
    }
    assert exec_tokens < substituted, (
        "the Exec block carries every placeholder in the file - the split is measuring nothing"
    )


def test_the_label_membership_check_can_speak_on_its_own() -> None:
    """The two label complaints are independent, not one shadowing the other.

    The refutation noted the membership check was dominated by the equality
    check: under an `elif`, a label no constant declares reported ONLY
    "undeclared" and the equality check never got to speak, so the pair carried
    one bit between them where the repairs are different. Un-chained, an
    undeclared label now fires BOTH - it is neither declared nor the task's -
    while a label that IS declared but wrong fires only the identity one. That
    is the discrimination, and it takes both halves of this arm to show it:
    without the first half the un-chaining is invisible, and without the second
    half a grader that simply always emitted both would pass.
    """
    undeclared = _mutate(
        _real_xml_text(), "--source scheduledtask", "--source notalabelthiscodeknows"
    )
    both = grade_task_argv(undeclared)
    assert "source-not-a-declared-label:notalabelthiscodeknows" in both
    assert "source-not-the-task-label:notalabelthiscodeknows" in both

    declared_but_wrong = _mutate(_real_xml_text(), "--source scheduledtask", "--source cli")
    complaints = grade_task_argv(declared_but_wrong)
    assert "source-not-the-task-label:cli" in complaints
    assert not [item for item in complaints if item.startswith("source-not-a-declared-label")]


#: One in-memory mutant per detector, as `pytest.param(old, new, expected)`.
#: Held at module level so `test_every_detector_has_a_control` can pin the
#: declared detector set to it by SET EQUALITY. Shapes vary as well as values:
#: a valid placeholder in the wrong slot, a real file that is the wrong file,
#: an abbreviation argparse resolves, and a valid-shape wrong-meaning argv.
#: The real file is never written - every mutant is a string in memory.
ARGV_MUTANTS = (
    # --- the four detector families the first version already had ---
    pytest.param(
        "--source scheduledtask ",
        "",
        "source-flag-absent",
        id="the-hand-added-flag-silently-disappears",
    ),
    pytest.param(
        "--source scheduledtask",
        "--source notalabelthiscodeknows",
        "source-not-a-declared-label:notalabelthiscodeknows",
        id="a-label-no-constant-declares",
    ),
    pytest.param(
        "--source scheduledtask",
        "--source SCHEDULEDTASK",
        "source-label-unusable",
        id="a-label-the-scanner-refuses",
    ),
    pytest.param(
        "--arm",
        "--arm --not-a-flag-this-parser-has",
        "unknown-flag:--not-a-flag-this-parser-has",
        id="a-flag-the-parser-does-not-accept",
    ),
    pytest.param(
        "tools/moon_sync_responder.py",
        "tools/moon_sync_responder_that_is_not_there.py",
        "script-missing:tools/moon_sync_responder_that_is_not_there.py",
        id="an-argv-naming-a-script-that-is-not-on-disk",
    ),
    pytest.param(
        "--arm",
        "--arm --max-hops notaninteger",
        "parser-rejects-argv",
        id="a-declared-flag-handed-a-value-of-the-wrong-type",
    ),
    # --- the shapes the first version's controls never varied ---
    # A REAL FILE, WRONG FILE. `tools/caveman_default.py` exists, is 7-bit
    # ASCII, and guards its own `main`, so it is safe to name and it is not
    # the responder. Existence passed the old grader outright.
    pytest.param(
        "tools/moon_sync_responder.py",
        "tools/caveman_default.py",
        "script-does-not-declare-the-task-label:tools/caveman_default.py",
        id="an-argv-naming-a-real-script-that-is-the-wrong-one",
    ),
    # VALID SHAPE, WRONG MEANING: parses clean, spawns nothing, delivers
    # nothing, and the trial goes silent with a green suite.
    pytest.param(
        "--arm ",
        "",
        "task-argv-does-not-arm",
        id="a-valid-argv-that-quietly-does-nothing",
    ),
    # VALID SHAPE, WRONG MEANING: a window that closes before it opens,
    # while both values stay the placeholders the installer substitutes.
    pytest.param(
        "--window-opens __START_BOUNDARY__ --window-closes __END_BOUNDARY__",
        "--window-opens __END_BOUNDARY__ --window-closes __START_BOUNDARY__",
        "window-opens-is-not-the-trigger-start:__END_BOUNDARY__",
        id="the-window-opens-where-it-should-close",
    ),
    pytest.param(
        "--window-opens __START_BOUNDARY__ --window-closes __END_BOUNDARY__",
        "--window-opens __END_BOUNDARY__ --window-closes __START_BOUNDARY__",
        "window-closes-is-not-the-trigger-end:__START_BOUNDARY__",
        id="the-window-closes-where-it-should-open",
    ),
    # `main`'s OWN precondition, reused rather than reimplemented: armed
    # with no window is a refusal before anything is spawned. The token
    # names the CATEGORY, because the exit code is shared with argparse.
    pytest.param(
        "--window-opens __START_BOUNDARY__ ",
        "",
        "main-refused-argv:own-precondition",
        id="armed-with-half-a-window",
    ),
    # THE GRAMMAR, WHICH IS A MEANING AND NOT A SPELLING. Dropping this flag
    # leaves an argv that parses, arms, and grades clean everywhere else,
    # while every `record_cycle` row it produces publishes `hops` as an
    # integer under `m1_status='lower-bound'` for a run whose far end is a
    # HUMAN. That is the defect the latency-only grammar exists to prevent.
    pytest.param(
        "--latency-only ",
        "",
        "grammar-is-not-the-latency-only-grammar",
        id="the-flag-that-makes-M1-inapplicable-quietly-disappears",
    ),
    # A NON-DASH EXTRA, which the old loop discarded in silence.
    pytest.param(
        "--arm",
        "--arm garbagepositional",
        "unexpected-positional:garbagepositional",
        id="positional-junk-the-parser-hands-back-and-nobody-read",
    ),
    # ABBREVIATIONS, which argparse resolves and a tracked artifact must not
    # rely on. All three reached their flag and graded clean before.
    pytest.param(
        "--latency-only",
        "--latency-onl",
        "flag-not-a-declared-spelling:--latency-onl",
        id="an-abbreviated-flag-argparse-is-happy-to-resolve",
    ),
    pytest.param(
        "--arm ",
        "--ar ",
        "flag-not-a-declared-spelling:--ar",
        id="a-two-letter-abbreviation-of-the-flag-that-arms-it",
    ),
    pytest.param(
        "--source scheduledtask",
        "--sourc scheduledtask",
        "flag-not-a-declared-spelling:--sourc",
        id="an-abbreviated-source-flag-caught-by-the-parser-not-by-a-substring",
    ),
    # --- the Exec block itself, which nothing under tests/ read before ---
    # A SECOND ACTION. The argv this file grades is then only one of the things
    # the task runs, and the other one is graded by nothing at all.
    pytest.param(
        "    <Exec>",
        "    <Exec/>\n    <Exec>",
        "exec-count:2",
        id="two-exec-blocks-so-the-graded-argv-is-only-half-the-task",
    ),
    # THE INTERPRETER, which is the case the supervisor grader's docstring
    # describes and which was still true of THIS task. `python.exe` flashes a
    # console on every fire, and `<Hidden>true</Hidden>` does not undo it.
    pytest.param(
        "<Command>__PYTHONW_EXE__</Command>",
        "<Command>python.exe</Command>",
        "command-is-not-the-installer-interpreter:python.exe",
        id="the-interpreter-becomes-the-one-that-flashes-a-console",
    ),
    pytest.param(
        "      <Command>__PYTHONW_EXE__</Command>\n",
        "",
        "command-absent",
        id="the-command-element-disappears-entirely",
    ),
    # A TOKEN SHAPED LIKE A PLACEHOLDER THAT NOBODY FILLS. The installer throws
    # on a survivor, so this is the drift that turns registration into a crash
    # nobody sees until the trial is supposed to start.
    pytest.param(
        "<Command>__PYTHONW_EXE__</Command>",
        "<Command>__PYTHON_EXE__</Command>",
        "unsubstituted-placeholder:__PYTHON_EXE__",
        id="a-placeholder-the-installer-would-never-substitute",
    ),
    # A REAL PLACEHOLDER IN THE WRONG SLOT. Shape-valid, substituted happily,
    # and the task's working directory becomes the path to pythonw.exe.
    pytest.param(
        "<WorkingDirectory>__INSTALL_ROOT__</WorkingDirectory>",
        "<WorkingDirectory>__PYTHONW_EXE__</WorkingDirectory>",
        "working-directory-is-not-the-install-root:__PYTHONW_EXE__",
        id="a-real-placeholder-in-the-wrong-slot",
    ),
    pytest.param(
        "      <WorkingDirectory>__INSTALL_ROOT__</WorkingDirectory>\n",
        "",
        "working-directory-absent",
        id="the-working-directory-disappears-so-a-relative-script-resolves-from-anywhere",
    ),
    pytest.param(
        "<Arguments>tools/moon_sync_responder.py --arm --latency-only --source"
        " scheduledtask --window-opens __START_BOUNDARY__ --window-closes"
        " __END_BOUNDARY__</Arguments>",
        "<Arguments></Arguments>",
        "arguments-empty",
        id="the-arguments-element-goes-empty",
    ),
    # THE INSTALLER'S OWN PRECONDITION, GUARDING A FILE THE TASK NEVER RUNS.
    # Same mutant as the wrong-script one above, different detector: that one
    # says the file is not the responder, this one says the installer refuses
    # to register without a file the argv no longer names.
    pytest.param(
        "tools/moon_sync_responder.py",
        "tools/caveman_default.py",
        "script-is-not-the-path-the-installer-requires:tools/caveman_default.py",
        id="an-argv-naming-a-script-the-installer-does-not-check-for",
    ),
    # A DECLARED LABEL THAT IS NOT THIS TASK'S. Controlled here as well as in
    # `test_the_label_membership_check_can_speak_on_its_own`, so the coverage
    # arm below sees a control for it rather than an exemption.
    pytest.param(
        "--source scheduledtask",
        "--source cli",
        "source-not-the-task-label:cli",
        id="a-declared-label-that-belongs-to-a-different-invocation",
    ),
)


@pytest.mark.parametrize(("old", "new", "expected"), ARGV_MUTANTS)
def test_the_grader_fires_on_a_mutated_argv(old: str, new: str, expected: str) -> None:
    """Non-vacuity: each detector is shown red on an in-memory mutant.

    The real file is never written. `--max-hops` is absent from the real argv,
    so its arm plants the flag with a non-integer value to reach the
    argparse-rejects path.
    """
    mutated = _mutate(_real_xml_text(), old, new)
    assert expected in grade_task_argv(mutated)


#: One planted cause per refusal category: `(id, old, new, category)`. These are
#: the four unrelated drifts that all minted `main-refused-argv:2` while the
#: token carried the exit code, and the exit code is shared - `main` returns 2
#: from its own window precondition and argparse exits 2 from the other three.
REFUSAL_CAUSES = (
    ("armed-with-half-a-window", "--window-opens __START_BOUNDARY__ ", "", "own-precondition"),
    ("an-unusable-value", "--arm", "--arm --max-hops notaninteger", "flag-value-rejected"),
    ("an-undeclared-flag", "--arm", "--arm --not-a-flag-this-parser-has", "undeclared-flag"),
    ("positional-junk", "--arm", "--arm garbagepositional", "undeclared-positional"),
)


def test_every_refusal_cause_mints_its_own_category() -> None:
    """A token four different causes can mint is not a fingerprint.

    THE DEFECT THIS ARM EXISTS FOR, measured before the repair: half a window,
    a non-integer `--max-hops`, an undeclared flag and a bare positional all
    produced the identical `main-refused-argv:2`, because the token carried the
    EXIT CODE and `main`'s own precondition returns the same 2 that argparse
    exits with. Keying on a shared code says only that something refused.

    The categories are derived from the parser's own behaviour - whether the
    refusal left through `main`'s `return` or through argparse's `SystemExit`,
    and then what `parse_known_args` does with the same argv - never from
    argparse's message text, which is prose this tree does not own.
    """
    minted: dict[str, str] = {}
    for name, old, new, category in REFUSAL_CAUSES:
        complaints = grade_task_argv(_mutate(_real_xml_text(), old, new))
        tokens = [item for item in complaints if item.startswith("main-refused-argv:")]
        assert len(tokens) == 1, f"{name} minted {tokens} - expected exactly one refusal token"
        assert tokens[0] == f"main-refused-argv:{category}", f"{name} minted {tokens[0]}"
        minted[name] = tokens[0]

    assert len(set(minted.values())) == len(REFUSAL_CAUSES), (
        f"the refusal token does not discriminate between its causes: {minted}"
    )
    # The neighbour arm: the tracked artifact mints no refusal token at all, so
    # the discrimination above is not bought by complaining about everything.
    assert not [
        item for item in grade_task_argv(_real_xml_text()) if item.startswith("main-refused-argv:")
    ]


def test_loading_a_script_is_gated_on_identity_first() -> None:
    """Executing what a path names before checking WHAT it is, is the old hole.

    `_load_script` runs the named module's top level, which pulls in `core`,
    `core.atomic_io` and `ops.health`. Two arms called it straight off `argv[0]`
    with no identity gate, unlike `grade_task_argv`, so a task XML edited to
    name any other importable file would have had that file executed by the
    suite before anything asked what it was. The gate is at the choke point, so
    every caller inherits it.

    The positive control is the second half: a gate that refused everything
    would pass the first half and is caught by the second.
    """
    wrong_but_real = "tools/caveman_default.py"
    assert (REPO_ROOT / wrong_but_real).is_file(), "the control names a file that is not there"
    with pytest.raises(AssertionError):
        _load_script(wrong_but_real)
    assert wrong_but_real not in _MODULE_CACHE, "the refused script was executed anyway"

    responder = _exec_argv(_real_xml_text())[0]
    assert hasattr(_load_script(responder), TASK_LABEL_CONSTANT)


def test_every_detector_has_a_control() -> None:
    """The detector set and the mutant table are pinned to each other by SET EQUALITY.

    A detector added without a control goes red here on its own, and so does
    controlling one of the two exempt buckets later without removing it from
    `UNCONTROLLED_TOKENS`. Populations, named: `GRADED_TOKENS` is every complaint
    bucket `_complaint` will mint, and the covered set is the bucket half of
    every expected token in `ARGV_MUTANTS`.
    """
    assert ARGV_MUTANTS, "the mutant table is empty - this arm is measuring nothing"
    covered = {param.values[2].split(":", 1)[0] for param in ARGV_MUTANTS}
    assert covered <= set(GRADED_TOKENS), (
        f"the mutant table expects buckets the grader cannot mint: {sorted(covered - set(GRADED_TOKENS))}"
    )
    assert set(GRADED_TOKENS) - covered == set(UNCONTROLLED_TOKENS)


def test_the_installer_derivations_are_not_empty() -> None:
    """Every expectation above is READ from the installer, so an empty read is fatal.

    Each helper raises on an empty derivation, and this arm is what makes those
    floors non-vacuous: it names the count and the population it is counted over,
    and shows both derived placeholders are drawn from that same table rather
    than invented. `substituted` is the placeholder-token half of the
    `$xml.Replace` calls in `ops/install_responder_task.ps1`.
    """
    substituted = _installer_substitutions()
    assert len(substituted) == 6, f"the installer substitutes {sorted(substituted)}"
    assert _installer_interpreter_placeholder() in substituted
    assert _installer_install_root_placeholder() in substituted
    assert _installer_interpreter_placeholder() != _installer_install_root_placeholder(), (
        "both derivations resolve to one placeholder - they cannot discriminate"
    )
    assert _installer_required_script().endswith(".py")


# ---------------------------------------------------------------------------
# THIS INSTALLER'S LIVENESS INVOCATION
#
# THE DEFECT THIS EXISTS FOR, measured at 88c0874. The liveness grading added to
# `tests/test_supervisor_task_argv.py` covered ONE of the TWO tracked installers.
# `git grep -n 'exit $livenessExit' -- ops/` returns two hits,
# `ops/install_responder_task.ps1:254` and `ops/install_scheduled_task.ps1:217`,
# and `ops/install_responder_task.ps1:231-254` runs the same construct - the
# console python resolved by the same function, the checker built by the same
# `Join-Path`, `$LASTEXITCODE` captured into `$livenessExit`, that value exited.
# Zero tracked tests graded it. This file mentioned line 231 exactly once, at
# `_installer_required_script`, and only to EXCLUDE it from a match. So an edit
# that pointed the responder's checker at the wrong interpreter, dropped the
# task name, or swallowed the exit status left every suite green while the
# installer went on printing LIVENESS ESTABLISHED for a task nothing had
# established.
#
# WHAT THESE ARMS ARE, IN THE SAME TERMS AS THE GRADER THEY CALL: A SHAPE GRADER
# OVER TEXT. Nothing below registers the task, executes the `.ps1`, or runs the
# checker. An installer that is textually perfect and broken at runtime - a
# `Set-StrictMode` violation, a quoting bug, a `PATH` that resolves some other
# `python.exe` - grades clean from here. What is ruled out is a text-level drift
# in WHICH interpreter, WHICH arguments, and whether the checker's status
# survives to the caller.
#
# NOTHING IS WRITTEN TO `ops/install_responder_task.ps1`. Every mutant is an
# in-memory string.
# ---------------------------------------------------------------------------


def test_the_responder_installer_liveness_invocation_grades_clean() -> None:
    """The neighbours-survive guard for this installer's liveness grade.

    A grader that complained about everything would score on every mutant below
    and mean nothing. This one assertion is what makes that impossible HERE - the
    equivalent arm in `tests/test_supervisor_task_argv.py` is about a different
    file and cannot stand in for it.
    """
    assert grade_installer_liveness(_installer_text(), INSTALLER_PS1.name) == []


def test_the_responder_liveness_checker_is_run_with_the_console_python_and_the_task_name() -> None:
    """WHICH interpreter and WHICH arguments, by equality, in order, at pinned length.

    ONE ASSERTION CARRIES THE WHOLE CLAIM. The tuple on the left is the whole
    invocation read out of the installer and the tuple on the right is built from
    three independent derivations, so order and length are pinned with identity
    rather than beside it - `EXPECTED == (a, *rest)` holds at any length, and
    that arity blindness is a defect this tree has already been caught by.

    THE TASK NAME IS THE REGISTERED ONE. This installer prints no task-name
    banner, so the derivation reads `Register-ScheduledTask -TaskName`: the
    checker takes the task name as its one positional
    (`ops/check_task_liveness.py:705`), and any other variable asks about a task
    that was never registered.

    The floor that stops this comparing two empties: the derivations each raise
    on an empty read, and the invocation must be found at all.
    """
    text = _installer_text()
    label = INSTALLER_PS1.name
    statements = _significant_statements(text)
    calls = [match for statement in statements if (match := _CALL_OPERATOR_RE.match(statement))]
    assert len(calls) == 1, f"{label} makes {len(calls)} call-operator invocations"

    interpreter = calls[0].group(1)
    argv = tuple(calls[0].group(2).split())
    checker_variable, checker_path = _installer_liveness_checker(text, label)

    assert (interpreter, argv) == (
        _installer_console_python_variable(text, label),
        (checker_variable, _installer_task_name_variable(text, label)),
    )
    assert checker_path.is_file()


def test_the_responder_liveness_exit_status_is_captured_adjacently_and_propagated() -> None:
    """The status must reach the caller, and the read must be about the checker.

    Two mechanisms, both asserted here rather than inferred from the absence of a
    complaint: the statement IMMEDIATELY after the invocation reads
    `$LASTEXITCODE` into a variable, and the LAST exit in the script is that
    variable with no other exit after the invocation to pre-empt it.
    `$LASTEXITCODE` is clobbered by the next native command, so adjacency is the
    mechanism and not a style preference.

    THE EARLIER EXITS ARE NOT COUNTED, AND THAT IS DELIBERATE. This installer
    exits 3 twice before the invocation, for an absent checker and an absent
    console python. Those are LIVENESS UNVERIFIED paths that never reach the
    checker, so the population is the exits AFTER the call and not every exit.
    """
    text = _installer_text()
    statements = _significant_statements(text)
    index = next(
        position
        for position, statement in enumerate(statements)
        if _CALL_OPERATOR_RE.match(statement)
    )
    following = statements[index + 1 :]
    assert following, "the liveness invocation is the last statement - nothing reads its status"

    captured = _LASTEXITCODE_RE.match(following[0])
    assert captured is not None, (
        f"the statement after the liveness invocation is {following[0]!r}, "
        "so the captured status is not the checker's"
    )
    exits = [statement for statement in following if _EXIT_RE.match(statement)]
    assert exits == [f"exit {captured.group(1)}"], (
        f"the exits after the liveness invocation are {exits} - the script's verdict is "
        "either not the checker's status or is pre-empted by an earlier exit"
    )


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [pytest.param(old, new, expected, id=name) for name, old, new, expected in LIVENESS_MUTANTS],
)
def test_the_liveness_grader_fires_on_a_mutated_responder_installer(
    old: str, new: str, expected: str
) -> None:
    """Non-vacuity: each liveness detector is shown red against THIS installer.

    THE TABLE IS THE SUPERVISOR'S, AND THAT IS THE POINT. Both installers carry
    the mutation targets verbatim, so importing the table proves the two files
    are graded by one mechanism rather than by two that may drift apart. The
    uniqueness floor is asserted HERE rather than in a separate arm: `_mutate`
    replaces the FIRST occurrence, so a target present twice would leave a second
    copy standing and the mutant would be a weaker text than its id claims - and
    a target present ZERO times would make this arm grade the real file twice.
    """
    text = _installer_text()
    assert text.count(old) == 1, f"{old!r} appears {text.count(old)} times - _mutate replaces one"
    assert expected in grade_installer_liveness(_mutate(text, old, new), INSTALLER_PS1.name)


def test_every_liveness_detector_has_a_control_on_the_responder_installer() -> None:
    """`LIVENESS_TOKENS` is pinned to what the mutants ACTUALLY MINT from this file.

    STRONGER THAN THE TABLE-LEVEL EQUALITY IT COMPLEMENTS. The supervisor's
    control arm compares `LIVENESS_TOKENS` against the EXPECTED tokens written
    into `LIVENESS_MUTANTS` - a claim about the table. This one runs the grader
    and collects the buckets it MINTS from mutated copies of
    `ops/install_responder_task.ps1`, so a detector that the shared table names
    but that cannot fire against this installer goes red here.

    Populations, named: `LIVENESS_TOKENS` is every bucket
    `grade_installer_liveness` will mint, and `observed` is the bucket half of
    every complaint the mutants below actually produced from THIS file.
    """
    assert LIVENESS_MUTANTS, "the liveness mutant table is empty - this arm is measuring nothing"
    text = _installer_text()
    observed: set[str] = set()
    for _name, old, new, expected in LIVENESS_MUTANTS:
        complaints = grade_installer_liveness(_mutate(text, old, new), INSTALLER_PS1.name)
        assert expected in complaints, (
            f"{expected} was not minted from a mutated {INSTALLER_PS1.name} - got {complaints}"
        )
        observed.update(complaint.split(":", 1)[0] for complaint in complaints)
    assert observed == set(LIVENESS_TOKENS), (
        f"detectors that never fired against this installer "
        f"{sorted(set(LIVENESS_TOKENS) - observed)}, buckets minted that are not declared "
        f"{sorted(observed - set(LIVENESS_TOKENS))}"
    )
