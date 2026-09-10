"""The supervisor scheduled task's argv is graded against the code it calls.

THE DEFECT THIS EXISTS FOR, measured at b5dc138. `ops/ResinCompute-Supervisor.xml`
is a tracked 3483-byte artifact naming a command, and nothing in the tree read
that command back against anything. The only argv grader here was
`tests/test_responder_task_argv.py`, whose `TASK_XML` at line 114 is
`ops/ResinCompute-Responder.xml`. Twelve tracked files name the supervisor task
and the only `.py` among them is `tests/test_task_state_claims.py:281-282`, which
scans PowerShell command strings inside docs and never opens this XML. The task
is also NOT registered on this machine - `schtasks /Query /TN ResinCompute-Supervisor`
exits 1 - so nothing in the live scheduler could contradict a wrong argv either.
An edit to the `<Exec>` block could point the logon-triggered supervisor at the
wrong interpreter, the wrong module, or a dry run that spawns nothing, and every
suite would stay green.

WHAT IS NOT GRADED HERE, AND WHY. Registration. This file reads a static tracked
artifact and never calls `schtasks`, never runs `ops/install_scheduled_task.ps1`,
and never asserts the task IS registered - it deliberately is not. The honest
grade of "the scheduler would accept this" needs a registration, so it is a
stated scope limit rather than a claim.

THE SHAPE IS THE RESPONDER GRADER'S, THE LITERALS ARE NOT. That file grades a
different task, and two of its central mechanisms do not transfer:

  - IT INTERCEPTS `parse_args` to capture a parser `main` builds as a local.
    `ops/supervisor.py:368` exposes `build_parser()` as a module-level function,
    so the authoritative option set is readable without intercepting anything.
  - IT RUNS THE ARGV THROUGH `main` with `run_once` replaced, to read the
    `Bounds` the code builds. `ops/supervisor.py:415` `main` reaches
    `supervise()`, which spawns a child process and loops forever. Running it is
    not an option, so the meaning grade here is read from the parsed namespace
    instead: `--dry-run` is the supervisor's own do-nothing mode
    (`ops/supervisor.py:427-446` prints a report and returns 0 without
    spawning), and a scheduled task carrying it is a supervisor that starts at
    logon, prints into a hidden `pythonw.exe` with no console, and exits.

NEITHER SIDE OF ANY COMPARISON IS RETYPED. A literal argv written into a test is
a snapshot: it agrees with itself on the day it is written and with nothing
afterwards. Both sides are READ:

  - WHICH INTERPRETER: `ops/install_scheduled_task.ps1:120-122` declares which
    placeholder tokens it substitutes and what it substitutes into each, and
    line 132 prints the command it believes it is registering as
    `$PythonwExe + ' -m ops.supervisor'`. The XML's `<Command>` must be the
    placeholder that installer fills from that same variable. `pythonw` rather
    than `python` is load bearing and the installer says so at its lines 37 and
    60: a logon-triggered task under `python.exe` flashes a console window, and
    the XML pairs the choice with `<Hidden>true</Hidden>`.
  - WHICH ARGUMENTS: from the same line 132, so the installer's banner and the
    XML it registers have to agree or one of them is lying to the operator.
  - WHICH WORKING DIRECTORY: `ops/install_scheduled_task.ps1:116` builds the
    path it reads THIS XML from as `Join-Path $InstallRoot 'ops\\...xml'`. The
    variable in that expression is the install root, so the placeholder the
    installer fills from it is the one the `<WorkingDirectory>` must carry.
    Not decoration: `-m ops.supervisor` resolves only from the checkout root.
  - WHICH MODULE: the dotted name after `-m` is resolved to a file on disk, and
    that file must declare a `__main__` guard - `-m` on a module without one
    imports it and exits, which is the quietest possible failure - and must
    carry the supervisor's own identity symbols.
  - WHICH FLAGS AND WHAT THEY MEAN: the option spellings come from the real
    `build_parser()` of the module the argv names, and the parsed namespace must
    not be a dry run.

WHAT IS DELIBERATELY NOT GRADED. `argparse`'s `prog=` at `ops/supervisor.py:370`
reads like a link between the module and the dotted name in the argv, and it is
not one: `prog` only shapes `--help` text, so a mismatch is cosmetic and grading
it would put a detector here that can go red without a defect existing.

EQUALITY, NEVER CONTAINMENT. Every anchor below is an `==` or a set membership
against a value read from the other side. Containment has a repair gradient - a
failing substring invites shortening the needle - and matcher-widening is the
response this tree has been defeated by three times. If an anchor fails here,
re-anchor it; do not trim it.

NON-VACUITY. Every detector is shown red on an in-memory mutant, and
`test_every_detector_has_a_control` pins the detector set to the mutant table by
SET EQUALITY, so a detector added without a control goes red on its own. The
mutants vary SHAPE as well as value - a valid placeholder in the wrong slot, a
real module that is the wrong module, a real module that is not a CLI at all, an
abbreviation `argparse` resolves happily - because a control that only plants
the case the matcher already handles cannot discover that the matcher is narrow.
The real file is never written; every mutant is a string in memory.
"""
from __future__ import annotations

import argparse
import importlib
import re
import shlex
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_XML = REPO_ROOT / "ops" / "ResinCompute-Supervisor.xml"
INSTALLER_PS1 = REPO_ROOT / "ops" / "install_scheduled_task.ps1"
TASK_NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"

#: The symbols that IDENTIFY the supervisor, each declared at a located line in
#: `ops/supervisor.py`: `build_parser` at 368, `main` at 415, `supervise` at
#: 293, `SupervisorConfig` at 98, `DEFAULT_CHILD_ARGS` at 74. This is an
#: identity list and not the grader's dependency list - the grader itself only
#: calls `build_parser` - because the question a task argv raises is WHICH
#: module it names, and `headless/runner.py` also declares `build_parser` and
#: `main` at module level.
SUPERVISOR_CONTRACT = (
    "build_parser",
    "main",
    "supervise",
    "SupervisorConfig",
    "DEFAULT_CHILD_ARGS",
)

#: Every complaint bucket this grader can mint. `_complaint` refuses a bucket
#: that is not listed, so the tuple cannot drift away from the code, and
#: `test_every_detector_has_a_control` pins it to the mutant table by set
#: equality.
GRADED_TOKENS = (
    "exec-count",
    "command-absent",
    "arguments-empty",
    "working-directory-absent",
    "unsubstituted-placeholder",
    "command-is-not-the-installer-interpreter",
    "working-directory-is-not-the-install-root",
    "argv-is-not-the-installer-command",
    "module-switch-is-not-dash-m",
    "module-name-absent",
    "module-file-missing",
    "module-has-no-main-guard",
    "module-is-not-a-cli",
    "module-will-not-import",
    "module-not-the-supervisor",
    "module-lacks",
    "flag-not-a-declared-spelling",
    "parser-rejects-argv",
    "unknown-flag",
    "unexpected-positional",
    "task-argv-is-a-dry-run",
)

#: Detectors with no in-memory control, and the measured reason. Held as an
#: explicit tuple so the coverage arm can compare by SET EQUALITY: a new
#: uncontrolled detector goes red, and so does controlling this one later
#: without updating the tuple.
#:
#: `module-will-not-import` needs a file that exists, declares `build_parser`
#: and `main` at line start, and then raises on import. Measured at this HEAD:
#: the tree contains no such file, and manufacturing one means writing a broken
#: module to disk, which this file does not do.
UNCONTROLLED_TOKENS = ("module-will-not-import",)

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

#: The installer's own placeholder shape, at `ops/install_scheduled_task.ps1:125`,
#: where it throws on any survivor. Same pattern, so a token this grader calls a
#: placeholder is a token that installer would refuse to leave behind.
_PLACEHOLDER_RE = re.compile(r"__[A-Z_]+__")

_REPLACE_RE = re.compile(
    r"\$xml\s*=\s*\$xml\.Replace\(\s*'(__[A-Z_]+__)'\s*,\s*(\$[A-Za-z_]\w*)\s*\)"
)
_BANNER_RE = re.compile(
    r"Write-Step\s*\(\s*'command\s*:\s*'\s*\+\s*(\$[A-Za-z_]\w*)\s*\+\s*'([^']*)'\s*\)"
)
_XML_PATH_RE = re.compile(r"\$xmlPath\s*=\s*Join-Path\s+(\$[A-Za-z_]\w*)\s+'([^']*)'")


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
    """The installer script, decoded, with a non-vacuity floor on its size."""
    raw = INSTALLER_PS1.read_bytes()
    if not raw:
        raise AssertionError(f"{INSTALLER_PS1} is empty - every derivation below reads it")
    return raw.decode("ascii", errors="replace")


def _installer_substitutions() -> dict[str, str]:
    """Placeholder token -> the PowerShell variable the installer fills it from.

    Read from the `$xml.Replace(...)` calls at `ops/install_scheduled_task.ps1:120-122`.
    This is the authoritative answer to "which tokens in the XML are placeholders
    the installer will actually substitute", and the installer itself throws at
    its line 125 on any `__NAME__` survivor.
    """
    found = dict(_REPLACE_RE.findall(_installer_text()))
    if not found:
        raise AssertionError(
            "no placeholder substitutions found in the installer - the scan is measuring nothing"
        )
    return found


def _installer_command() -> tuple[str, tuple[str, ...]]:
    """The interpreter PLACEHOLDER and the argument list the installer announces.

    `ops/install_scheduled_task.ps1:132` prints the command it believes it is
    registering, built from the same `$PythonwExe` variable it substitutes into
    the XML. Mapping that variable back through the substitution table yields the
    placeholder the XML's `<Command>` has to carry, so the interpreter is graded
    by IDENTITY rather than by "some placeholder is there".
    """
    match = _BANNER_RE.search(_installer_text())
    if match is None:
        raise AssertionError(
            "the installer prints no command banner - the interpreter derivation is measuring nothing"
        )
    variable, arguments = match.group(1), match.group(2)
    by_variable = {value: key for key, value in _installer_substitutions().items()}
    if variable not in by_variable:
        raise AssertionError(
            f"the installer banner names {variable}, which it substitutes into no placeholder"
        )
    argv = tuple(shlex.split(arguments))
    if not argv:
        raise AssertionError("the installer banner carries no arguments - the derivation is empty")
    return by_variable[variable], argv


def _installer_install_root_placeholder() -> str:
    """The placeholder standing for the checkout root, and the XML it reads.

    `ops/install_scheduled_task.ps1:116` builds the path to THIS task definition
    as `Join-Path $InstallRoot 'ops\\ResinCompute-Supervisor.xml'`. The variable
    in that expression is the install root by construction, and the relative path
    beside it is asserted to be this grader's own `TASK_XML` - so the installer
    that supplies the expectation is the installer that reads the graded file.
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
    by_variable = {value: key for key, value in _installer_substitutions().items()}
    if variable not in by_variable:
        raise AssertionError(
            f"the installer locates the XML with {variable}, which it substitutes into no placeholder"
        )
    return by_variable[variable]


def _exec_fields(xml_text: str) -> tuple[int, str | None, str | None, str | None]:
    """`(exec count, Command, Arguments, WorkingDirectory)` from a task XML.

    The count is returned rather than asserted so a second `<Exec>` arrives as a
    graded complaint. Two Exec blocks means the argv this file grades is only one
    of the things the task runs.
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


def _module_file(dotted: str) -> Path | None:
    """The file `-m <dotted>` would run, or `None` when nothing is there.

    Both layouts are resolved because `-m` accepts either: a module file, or a
    package whose `__main__.py` is what actually runs.
    """
    parts = dotted.split(".")
    if not all(part.isidentifier() for part in parts):
        return None
    as_module = REPO_ROOT.joinpath(*parts).with_suffix(".py")
    if as_module.is_file():
        return as_module
    as_package = REPO_ROOT.joinpath(*parts, "__main__.py")
    if as_package.is_file():
        return as_package
    return None


def _declares(path: Path, declaration: str) -> bool:
    """Whether the file declares `declaration` at the START of a line.

    A BYTE SCAN, NOT AN IMPORT. This is what stands between the grader and
    executing whatever module a mutated XML happens to name, so it must not
    itself run the file. Line-start matching means a mention inside a docstring
    or an import does not count as declaring.
    """
    needle = declaration.encode("ascii")
    return any(line.startswith(needle) for line in path.read_bytes().splitlines())


def _declared_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Every option spelling the parser declares, e.g. `--dry-run`, `--interval`.

    ARGPARSE RESOLVES ABBREVIATIONS AND THAT IS WHY THIS EXISTS. `--dry-ru`
    reaches `--dry-run`, so acceptance by the parser says nothing about whether
    the tracked artifact spells the flag the way the code declares it.
    `_actions` is private and it is the only place the declared spellings live;
    the alternative is retyping them here, which is the snapshot this file
    refuses to keep.
    """
    spellings = {option for action in parser._actions for option in action.option_strings}
    if not spellings:
        raise AssertionError("the parser declares no options - it is not the real one")
    return spellings


def _parser_takes_positionals(parser: argparse.ArgumentParser) -> bool:
    """Whether the parser declares any positional action at all.

    Grounds the positional-junk complaint in the parser rather than in an
    assumption: if a positional is ever added, this stops complaining on its own.
    """
    return any(not action.option_strings for action in parser._actions)


def _load_module(dotted: str) -> ModuleType:
    """Import the module `-m` would run, gated on identity FIRST.

    Importing runs the named module's top level. Asking WHAT a path is only
    after running it is the hole the responder grader closed once already, so
    the gate lives at the choke point and no caller can forget it: the file must
    resolve under this repo root and must declare both `build_parser` and `main`
    at line start before anything is executed.
    """
    path = _module_file(dotted)
    if path is None:
        raise AssertionError(f"refusing to import {dotted}: no file under {REPO_ROOT}")
    if not (_declares(path, "def build_parser(") and _declares(path, "def main(")):
        raise AssertionError(
            f"refusing to import {dotted}: it does not declare both build_parser and main"
        )
    return importlib.import_module(dotted)


def grade_task_argv(xml_text: str) -> list[str]:
    """Complaints about the supervisor task XML's Exec block.

    Returns an empty list when the task runs the interpreter the installer
    resolves, with the argument list the installer announces, from the install
    root, naming a module that is on disk, is runnable under `-m`, is the
    supervisor, and whose flags spell and mean a real supervising run.
    """
    complaints: list[str] = []
    count, command, arguments, working_directory = _exec_fields(xml_text)
    if count != 1:
        return [_complaint("exec-count", str(count))]

    interpreter_placeholder, installer_argv = _installer_command()
    install_root_placeholder = _installer_install_root_placeholder()
    substituted = _installer_substitutions()

    # PLACEHOLDER SURVIVORS, the installer's own failure mode at its line 125.
    block = " ".join(part or "" for part in (command, arguments, working_directory))
    for token in sorted(set(_PLACEHOLDER_RE.findall(block))):
        if token not in substituted:
            complaints.append(_complaint("unsubstituted-placeholder", token))

    if command is None:
        complaints.append(_complaint("command-absent"))
    elif command != interpreter_placeholder:
        complaints.append(_complaint("command-is-not-the-installer-interpreter", command))

    if working_directory is None:
        complaints.append(_complaint("working-directory-absent"))
    elif working_directory != install_root_placeholder:
        complaints.append(
            _complaint("working-directory-is-not-the-install-root", working_directory)
        )

    if not arguments:
        return [*complaints, _complaint("arguments-empty")]

    argv = tuple(shlex.split(arguments))
    if argv != installer_argv:
        complaints.append(_complaint("argv-is-not-the-installer-command", shlex.join(argv)))
    if not argv:
        return complaints

    if argv[0] != "-m":
        return [*complaints, _complaint("module-switch-is-not-dash-m", argv[0])]
    if len(argv) < 2:
        return [*complaints, _complaint("module-name-absent")]

    dotted, flags = argv[1], list(argv[2:])
    module_path = _module_file(dotted)
    if module_path is None:
        return [*complaints, _complaint("module-file-missing", dotted)]

    # REPORTED INDEPENDENTLY, NOT CHAINED. "no main guard" and "not a CLI" are
    # two different repairs, and a module that is neither must say both. Under an
    # `elif` the second could never speak on a file that fails the first.
    if not _declares(module_path, 'if __name__ == "__main__":'):
        complaints.append(_complaint("module-has-no-main-guard", dotted))
    if not (
        _declares(module_path, "def build_parser(") and _declares(module_path, "def main(")
    ):
        return [*complaints, _complaint("module-is-not-a-cli", dotted)]

    try:
        module = _load_module(dotted)
    except _IMPORT_FAILURES:
        return [*complaints, _complaint("module-will-not-import", dotted)]

    missing = [name for name in SUPERVISOR_CONTRACT if not hasattr(module, name)]
    if missing:
        complaints.append(_complaint("module-not-the-supervisor", dotted))
        complaints.extend(_complaint("module-lacks", f"{dotted}:{name}") for name in missing)
        return complaints

    parser = module.build_parser()
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

    # WHAT THE ARGV MEANS. `--dry-run` parses clean, spells correctly, and turns
    # the logon-triggered supervisor into a program that prints a report into a
    # hidden pythonw process with no console and exits 0. Nothing is spawned and
    # nothing is watched, and every other detector here stays quiet.
    if parsed is not None and getattr(parsed, "dry_run", False):
        complaints.append(_complaint("task-argv-is-a-dry-run"))

    return complaints


def _real_xml_text() -> str:
    """The task XML, decoded as measured rather than as assumed.

    The bytes are asserted 7-bit ASCII before decoding. That is the repo rule and
    it is also the honest reading of the file's own header: the declaration says
    UTF-8 and the installer hands the text to `Register-ScheduledTask` as a .NET
    string, so nothing on disk is ever UTF-16 here.
    """
    raw = TASK_XML.read_bytes()
    non_ascii = [byte for byte in raw if byte > 0x7F]
    assert not non_ascii, f"task XML is not 7-bit ASCII on disk: {non_ascii[:8]}"
    return raw.decode("ascii")


def _mutate(xml_text: str, old: str, new: str) -> str:
    """Replace once, asserting the mutation actually landed.

    A mutant built from a pattern that is not present would leave the text
    identical, and the arm below would then pass while grading the real file
    twice - a control that controls nothing.
    """
    assert old in xml_text, f"mutation target not present: {old!r}"
    mutated = xml_text.replace(old, new, 1)
    assert mutated != xml_text, "mutation did not change the text"
    return mutated


#: `(id, old, new, expected token)`. One in-memory mutant per detector. Shapes
#: vary as well as values: a valid placeholder in the wrong slot, a real module
#: that is the wrong module, a real module that is not a CLI, and an
#: abbreviation `argparse` resolves without complaint.
ARGV_MUTANTS = (
    (
        "two-exec-blocks-so-the-graded-argv-is-only-half-the-task",
        "    <Exec>",
        "    <Exec/>\n    <Exec>",
        "exec-count:2",
    ),
    (
        "the-interpreter-becomes-the-one-that-flashes-a-console",
        "<Command>__PYTHONW_EXE__</Command>",
        "<Command>python.exe</Command>",
        "command-is-not-the-installer-interpreter:python.exe",
    ),
    (
        "the-command-element-disappears-entirely",
        "      <Command>__PYTHONW_EXE__</Command>\n",
        "",
        "command-absent",
    ),
    (
        "a-placeholder-the-installer-would-never-substitute",
        "<Command>__PYTHONW_EXE__</Command>",
        "<Command>__PYTHON_EXE__</Command>",
        "unsubstituted-placeholder:__PYTHON_EXE__",
    ),
    (
        "a-real-placeholder-in-the-wrong-slot",
        "<WorkingDirectory>__INSTALL_ROOT__</WorkingDirectory>",
        "<WorkingDirectory>__PYTHONW_EXE__</WorkingDirectory>",
        "working-directory-is-not-the-install-root:__PYTHONW_EXE__",
    ),
    (
        "the-working-directory-disappears-so--m-resolves-from-anywhere",
        "      <WorkingDirectory>__INSTALL_ROOT__</WorkingDirectory>\n",
        "",
        "working-directory-absent",
    ),
    (
        "the-arguments-element-goes-empty",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments></Arguments>",
        "arguments-empty",
    ),
    (
        "the-argv-drifts-from-the-banner-the-installer-prints",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor --log-level DEBUG</Arguments>",
        "argv-is-not-the-installer-command:-m ops.supervisor --log-level DEBUG",
    ),
    (
        "the-module-switch-becomes-something-else",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-c ops.supervisor</Arguments>",
        "module-switch-is-not-dash-m:-c",
    ),
    (
        "dash-m-with-nothing-after-it",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m</Arguments>",
        "module-name-absent",
    ),
    (
        "a-module-name-that-is-not-on-disk",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor_that_is_not_there</Arguments>",
        "module-file-missing:ops.supervisor_that_is_not_there",
    ),
    # A REAL MODULE, WRONG MODULE. `headless/runner.py` is on disk, imports
    # cleanly, declares `build_parser` at 384 and `main` at 447 and carries a
    # `__main__` guard - so it clears every shape check and is still not the
    # supervisor. Shape alone would have accepted it outright.
    (
        "a-real-importable-module-that-is-the-wrong-one",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m headless.runner</Arguments>",
        "module-not-the-supervisor:headless.runner",
    ),
    (
        "and-it-is-named-which-symbol-it-lacks",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m headless.runner</Arguments>",
        "module-lacks:headless.runner:supervise",
    ),
    # A REAL MODULE THAT IS NOT A CLI AT ALL. `ops/health.py` is on disk and is
    # imported by the supervisor itself, and declares no `build_parser`, no
    # `main` and no `__main__` guard, so `-m` would import it and exit. Both
    # detectors must speak, which is why they are not chained.
    (
        "a-real-module-with-no-main-guard-so--m-imports-it-and-exits",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.health</Arguments>",
        "module-has-no-main-guard:ops.health",
    ),
    (
        "and-the-same-module-is-not-a-cli-either",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.health</Arguments>",
        "module-is-not-a-cli:ops.health",
    ),
    # AN ABBREVIATION ARGPARSE IS HAPPY TO RESOLVE. `--dry-ru` reaches
    # `--dry-run`, so the parser accepts a spelling the code never declared.
    (
        "an-abbreviated-flag-argparse-resolves-without-complaint",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor --dry-ru</Arguments>",
        "flag-not-a-declared-spelling:--dry-ru",
    ),
    (
        "a-declared-flag-handed-a-value-of-the-wrong-type",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor --interval notanumber</Arguments>",
        "parser-rejects-argv",
    ),
    (
        "a-flag-the-parser-does-not-have",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor --not-a-flag-this-parser-has</Arguments>",
        "unknown-flag:--not-a-flag-this-parser-has",
    ),
    (
        "positional-junk-the-parser-hands-back-and-nobody-read",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor garbagepositional</Arguments>",
        "unexpected-positional:garbagepositional",
    ),
    # VALID SHAPE, WRONG MEANING: spelled correctly, parsed happily, and the
    # supervisor starts at logon, prints a report into a hidden pythonw process
    # with no console, and exits 0 having spawned nothing.
    (
        "a-valid-argv-that-quietly-supervises-nothing",
        "<Arguments>-m ops.supervisor</Arguments>",
        "<Arguments>-m ops.supervisor --dry-run</Arguments>",
        "task-argv-is-a-dry-run",
    ),
)


def test_task_xml_is_ascii_on_disk() -> None:
    """The measured encoding claim, so a silent re-encode is not invisible."""
    raw = TASK_XML.read_bytes()
    assert raw[:2] != b"\xff\xfe", "task XML gained a UTF-16 LE BOM"
    assert raw[:3] != b"\xef\xbb\xbf", "task XML gained a UTF-8 BOM"
    assert b"\x00" not in raw, "task XML contains NUL bytes"
    _real_xml_text()


def test_the_tracked_supervisor_task_argv_grades_clean() -> None:
    """The neighbours-survive guard: the real artifact mints no complaint.

    A sweep that scores on its mutants by complaining about everything has
    failed, and this single assertion is what makes that impossible.
    """
    assert grade_task_argv(_real_xml_text()) == []


def test_the_tracked_argv_is_exactly_the_command_the_installer_announces() -> None:
    """WHICH interpreter and WHICH arguments, by equality, in order, at pinned length.

    ONE ASSERTION CARRIES THE WHOLE CLAIM. Tuple equality pins order AND length,
    and the length of the derived expectation is pinned in the same arm rather
    than in a separate one: an installer banner that stopped parsing would yield
    an empty expectation, and an equality against an empty tuple compared with an
    empty argv is an arm that has measured nothing.
    """
    interpreter_placeholder, installer_argv = _installer_command()
    assert len(installer_argv) == 2, (
        f"the installer banner derived {installer_argv} - the expectation is not the real one"
    )

    _, command, arguments, _ = _exec_fields(_real_xml_text())
    assert arguments is not None, "the tracked Exec carries no Arguments element"
    assert (command, tuple(shlex.split(arguments))) == (interpreter_placeholder, installer_argv)


def test_the_tracked_working_directory_is_the_root_the_installer_reads_from() -> None:
    """The `-m` module resolves only from the checkout root, so the task must sit there.

    The expectation is derived from the installer expression that locates THIS
    file, so the installer supplying the answer is the installer reading the
    graded artifact - `_installer_install_root_placeholder` asserts that pairing.
    """
    _, _, _, working_directory = _exec_fields(_real_xml_text())
    assert working_directory == _installer_install_root_placeholder()


def test_the_tracked_argv_names_a_module_that_is_on_disk_and_runnable() -> None:
    """The path that must exist, and the guard that makes `-m` do anything at all.

    A module without a `__main__` guard is imported by `-m` and then exits, which
    is the quietest failure a scheduled task can have: it starts, it succeeds, and
    it supervises nothing.
    """
    _, _, arguments, _ = _exec_fields(_real_xml_text())
    assert arguments is not None
    dotted = shlex.split(arguments)[1]
    path = _module_file(dotted)
    assert path is not None, f"the tracked argv names {dotted}, which is not on disk"
    assert _declares(path, 'if __name__ == "__main__":'), (
        f"{path.relative_to(REPO_ROOT).as_posix()} has no __main__ guard, so -m would do nothing"
    )


def test_the_tracked_argv_names_the_supervisor_and_not_a_neighbour() -> None:
    """Identity, not existence. `headless/runner.py` clears every shape check.

    The second half is the arm's own positive control: without it, a contract
    that no module in the tree could satisfy would pass the first half.
    """
    _, _, arguments, _ = _exec_fields(_real_xml_text())
    assert arguments is not None
    module = _load_module(shlex.split(arguments)[1])
    assert [name for name in SUPERVISOR_CONTRACT if not hasattr(module, name)] == []

    neighbour = importlib.import_module("headless.runner")
    assert [name for name in SUPERVISOR_CONTRACT if not hasattr(neighbour, name)] != [], (
        "headless.runner satisfies the supervisor contract - the contract identifies nothing"
    )


def test_the_tracked_argv_means_a_supervising_run_and_not_a_dry_one() -> None:
    """The meaning grade, read off the namespace the supervisor's own parser builds.

    The second half is the non-vacuity control in the same arm: adding
    `--dry-run` to the same argv must flip the same field, or the field is not
    the one the code reads.
    """
    _, _, arguments, _ = _exec_fields(_real_xml_text())
    assert arguments is not None
    argv = shlex.split(arguments)
    parser = _load_module(argv[1]).build_parser()

    assert parser.parse_args(argv[2:]).dry_run is False
    assert parser.parse_args([*argv[2:], "--dry-run"]).dry_run is True, (
        "the dry-run field does not move with the flag - the meaning grade is measuring nothing"
    )


def test_loading_a_module_is_gated_on_identity_first() -> None:
    """Executing what a path names before asking WHAT it is, is the old hole.

    `_load_module` runs the named module's top level. A task XML edited to name
    any importable file would otherwise have had that file executed by the suite
    before anything checked it. The second half is the positive control: a gate
    that refused everything would pass the first half.
    """
    not_a_cli = _module_file("ops.health")
    assert not_a_cli is not None, "the control names a module that is not on disk"
    with pytest.raises(AssertionError):
        _load_module("ops.health")

    _, _, arguments, _ = _exec_fields(_real_xml_text())
    assert arguments is not None
    assert hasattr(_load_module(shlex.split(arguments)[1]), "supervise")


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [pytest.param(old, new, expected, id=name) for name, old, new, expected in ARGV_MUTANTS],
)
def test_the_grader_fires_on_a_mutated_argv(old: str, new: str, expected: str) -> None:
    """Non-vacuity: each detector is shown red on an in-memory mutant.

    The real file is never written. Membership is by list `in`, which compares
    whole tokens for equality - not a substring search over joined text.
    """
    assert expected in grade_task_argv(_mutate(_real_xml_text(), old, new))


def test_every_detector_has_a_control() -> None:
    """The detector set and the mutant table are pinned to each other by SET EQUALITY.

    A detector added without a control goes red here on its own, and so does
    controlling `module-will-not-import` later without removing it from
    `UNCONTROLLED_TOKENS`. Populations, named: `GRADED_TOKENS` is every complaint
    bucket `_complaint` will mint, and the covered set is the bucket half of every
    expected token in `ARGV_MUTANTS`.
    """
    assert ARGV_MUTANTS, "the mutant table is empty - this arm is measuring nothing"
    covered = {expected.split(":", 1)[0] for _, _, _, expected in ARGV_MUTANTS}
    assert covered <= set(GRADED_TOKENS), (
        f"the mutant table expects buckets the grader cannot mint: {sorted(covered - set(GRADED_TOKENS))}"
    )
    assert set(GRADED_TOKENS) - covered == set(UNCONTROLLED_TOKENS)


def test_the_installer_derivations_are_not_empty() -> None:
    """Every expectation above is READ from the installer, so an empty read is fatal.

    Each helper raises on an empty derivation, and this arm is what makes those
    floors non-vacuous: it names the three counts and the population each is
    counted over. `substituted` is the placeholder-token half of the
    `$xml.Replace` calls in `ops/install_scheduled_task.ps1`.
    """
    substituted = _installer_substitutions()
    assert len(substituted) == 3, f"the installer substitutes {sorted(substituted)}"
    assert _installer_command()[0] in substituted
    assert _installer_install_root_placeholder() in substituted
