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

EVERY EXPECTATION ABOUT THE ARGV IS READ, NEVER RETYPED. A literal argv written
into a test is a snapshot: it agrees with itself on the day it is written and
with nothing afterwards. So for each of the five questions below, the value the
tracked XML is graded against is derived from the installer or from the module,
and only the XML side is a literal:

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

WHAT IS HAND-TYPED HERE ANYWAY, AND WHETHER DRIFT REDDENS. The sentence above
used to read "NEITHER SIDE OF ANY COMPARISON IS RETYPED", which was FALSE AS
WRITTEN and worse than no sentence, because a reader trusts it. It is true only
of the five ARGV EXPECTATIONS listed above. The population enumerated here is
different and larger: every hand-typed value in this file that stands opposite
something readable on disk - the NEEDLES that find each side, and the IDENTITY
LISTS that interpret them. None of these is an expectation about the argv; all
of them can drift.

  - `TASK_NS`, the task-schema namespace URI. GUARDED, indirectly and totally:
    if the tracked XML's `xmlns` moves, `_exec_fields` finds zero `Exec` nodes
    and `test_the_tracked_supervisor_task_argv_grades_clean` reddens on
    `exec-count:0`. A wrong namespace here cannot go quiet.
  - `SUPERVISOR_CONTRACT`, the chosen identity subset of `ops/supervisor.py`'s
    module-level names. `ops/supervisor.py` declares no `__all__`, so there is
    no list to read and the choice has no other side. GUARDED by
    `test_the_supervisor_contract_is_pinned_by_membership_and_by_length`, which
    pins length and set identity in one assertion and requires every name to be
    declared at module level in that file. It was UNGUARDED until that arm
    existed, and four of the five symbols could be dropped together with zero
    red anywhere in the suite.
  - `_REPLACE_RE`, `_BANNER_RE`, `_XML_PATH_RE` and `_MATCH_RE` hand-type the
    installer's SYNTAX, never its values. GUARDED: each derivation raises on an
    empty scan, and `test_the_installer_derivations_are_not_empty` names the
    count each scan is expected to return and the population it counts over.
  - `'if __name__ == "__main__":'` and the `"def build_parser("` /
    `"def main("` needles, in the exact double-quote form this tree formats to.
    GUARDED BY POLARITY rather than by a detector: a reformat to single quotes
    makes these arms go RED, not quietly green, so the failure mode is a false
    alarm and never a miss.
  - `"dry_run"`, `argparse`'s dest derived from `--dry-run`. GUARDED, BUT IN A
    DIFFERENT ARM: `grade_task_argv` reads it as `getattr(parsed, "dry_run",
    False)`, so a renamed dest would make that one detector go SILENTLY quiet,
    while `test_the_tracked_argv_means_a_supervising_run_and_not_a_dry_one`
    reads `.dry_run` as a plain attribute and raises `AttributeError`. The
    rename is caught by the suite; it is not caught by the detector.
  - The control subjects `headless.runner` and `ops.health`, and the XML
    literals in `ARGV_MUTANTS`. GUARDED: `_module_file` returning `None`
    reddens the arms that name them, and `_mutate` asserts `old in xml_text` so
    a stale mutation target reddens rather than mutating nothing.

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
`test_every_detector_has_a_control` pins `GRADED_TOKENS` - the complaint buckets
and nothing else - to the mutant table by SET EQUALITY, so a detector added
without a control goes red on its own. It says nothing about the other two
collections here: `SUPERVISOR_CONTRACT` is pinned by its own arm, and
`UNCONTROLLED_TOKENS` is pinned as the difference this same arm asserts. The
mutants vary SHAPE as well as value - a valid placeholder in the wrong slot, a
real module that is the wrong module, a real module that is not a CLI at all, an
abbreviation `argparse` resolves happily - because a control that only plants
the case the matcher already handles cannot discover that the matcher is narrow.
The real file is never written; every mutant is a string in memory.

WHAT WAS ADDED AFTER THE FACT, AND WHERE. Two graders live below the argv one and
are documented at the block comment that introduces them: the installer's LIVENESS
INVOCATION (`ops/install_scheduled_task.ps1:198` and `:217`), which was graded by
nothing at 88c0874, and the CLAIM THIS DOCSTRING MAKES about derivation, which was
graded by nothing either. Both read tracked bytes off disk and neither registers,
runs or executes anything.
"""
from __future__ import annotations

import argparse
import ast
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

#: The installer's own placeholder-survivor test, `$xml -match '...'` at
#: `ops/install_scheduled_task.ps1:124`, which throws on any survivor at 125.
#: The pattern INSIDE those quotes is read rather than retyped - see
#: `_installer_placeholder_pattern`.
_MATCH_RE = re.compile(r"\$xml\s+-match\s+'([^']*)'")

#: The token half of the installer's `.Replace(...)` calls. The class matches
#: the DELIMITER plus a full identifier run rather than SCREAMING_SNAKE, for the
#: same reason the installer's own guard does - see the block above
#: `DELIMITED_SURVIVORS` at the foot of this file.
_REPLACE_RE = re.compile(
    r"\$xml\s*=\s*\$xml\.Replace\(\s*'(__[A-Za-z0-9_]+__)'\s*,\s*(\$[A-Za-z_]\w*)\s*\)"
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


def _installer_placeholder_pattern() -> re.Pattern[str]:
    """What the installer CALLS a placeholder, read from the installer itself.

    WHY READ RATHER THAN GUARD. Retyping `__[A-Z_]+__` here and welding a
    drift guard beside it would leave two authorities and a detector between
    them; reading deletes the second authority instead of policing it, and it
    is what the rest of this file already does with every other expectation.
    The pattern is the one the installer enforces at
    `ops/install_scheduled_task.ps1:124-125`, so a token this grader calls a
    placeholder is exactly a token that installer would refuse to leave behind.
    Widen or narrow that line and this derivation moves with it.

    Three floors, all in this one derivation rather than in a separate arm:
    the declaration must be found, the pattern must compile under Python's
    `re` (PowerShell's `-match` is a .NET regex, and the two dialects agree on
    this shape but are not the same language), and it must both accept every
    token the installer actually substitutes and reject a bare XML word - a
    pattern matching everything or nothing would otherwise be handed back as
    authoritative.
    """
    match = _MATCH_RE.search(_installer_text())
    if match is None:
        raise AssertionError(
            "the installer declares no placeholder-survivor pattern - "
            "the placeholder derivation is measuring nothing"
        )
    source = match.group(1)
    try:
        # `re.IGNORECASE` because PowerShell's `-match` IS case-insensitive -
        # `-cmatch` is the case-sensitive operator, and `_MATCH_RE` only matches
        # the former, so an installer switching to `-cmatch` reddens the
        # derivation above rather than being silently mismodelled here. Measured
        # 2026-09-11: under the superseded `__[A-Z_]+__` this was a REAL
        # disagreement - PowerShell threw on a planted `__pythonw_exe__` that a
        # case-sensitive Python model said it would miss. The current class is
        # case-complete, so the flag is a no-op today and is carried to keep the
        # two languages agreeing if the class is ever narrowed again.
        pattern = re.compile(source, re.IGNORECASE)
    except re.error as exc:
        raise AssertionError(
            f"the installer's placeholder pattern {source!r} does not compile under Python re: {exc}"
        ) from exc
    substituted = sorted(_installer_substitutions())
    rejected = [token for token in substituted if not pattern.fullmatch(token)]
    if rejected:
        raise AssertionError(
            f"the installer's own pattern {source!r} does not match tokens it substitutes: {rejected}"
        )
    if pattern.search("WorkingDirectory"):
        raise AssertionError(
            f"the installer's placeholder pattern {source!r} matches ordinary XML text - "
            "every element in the Exec block would be reported as a placeholder"
        )
    return pattern


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


def _declares_a_module_level_name(path: Path, name: str) -> bool:
    """Whether the file declares `name` at module level as a def, class or assignment.

    Built on `_declares`, so it is the same BYTE SCAN and still never imports
    the file it is asked about. The four prefixes are the ways the symbols in
    `SUPERVISOR_CONTRACT` are actually declared in `ops/supervisor.py`:
    `def supervise(` at 293, `class SupervisorConfig:` at 98, and
    `DEFAULT_CHILD_ARGS = ` at 74. `class Name(` is included because a base
    class is a spelling of the same declaration, not a different one.
    """
    return any(
        _declares(path, prefix)
        for prefix in (f"def {name}(", f"class {name}:", f"class {name}(", f"{name} = ")
    )


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
    # `group(0)` rather than `findall`: the pattern comes off the installer, and
    # `findall` would silently return CAPTURE GROUPS instead of whole tokens if a
    # future installer wrapped its pattern in parentheses.
    placeholder_re = _installer_placeholder_pattern()
    for token in sorted({found.group(0) for found in placeholder_re.finditer(block)}):
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


def test_the_supervisor_contract_is_pinned_by_membership_and_by_length() -> None:
    """`SUPERVISOR_CONTRACT` itself, pinned - the arm the file shipped without.

    THE DEFECT THIS EXISTS FOR, measured at b3bef1a by driving 24 arms in memory
    against mutated contracts. The population of 24: the two arms that grade the
    real artifact's identity, `test_every_detector_has_a_control`,
    `test_loading_a_module_is_gated_on_identity_first`, and every entry of
    `ARGV_MUTANTS` through `test_the_grader_fires_on_a_mutated_argv`. Replacing
    the whole contract with `("supervise",)` scored 24/24 with zero failures, so
    FOUR of its five symbols could be deleted together and nothing anywhere went
    red. The contract carries the entire module-identity claim and was the one
    collection in this file with neither its length nor its set identity pinned.
    `test_every_detector_has_a_control` pins a set by equality, but the set it
    pins is `GRADED_TOKENS`, and it says nothing about this tuple.

    WHY THE EXPECTATION IS HAND-TYPED HERE, AND WHAT GUARDS IT. `ops/supervisor.py`
    declares no `__all__`, so there is no readable list to compare against; the
    contract is a CHOSEN subset of that module's module-level names, and a
    choice has no other side to be read from. The hand-typed set is therefore
    graded against ground truth by the second assertion: every name in it must
    be declared at module level in `ops/supervisor.py`, so a symbol cannot be
    invented here without also being invented there.

    WHY THE REDUNDANCY IS DELIBERATE. Measured above, `("supervise",)` alone
    already discriminates `ops.supervisor` from every neighbour in the tree
    today. The other four are not there to discriminate - they are there to say
    WHICH MODULE this is against a tree that may grow a second `supervise`, and
    a future reader who shrinks the tuple to the minimum that still passes has
    traded the identity claim for the discrimination one. That is why the length
    is pinned in the SAME assertion as the membership rather than beside it: a
    length in a separate arm leaves the membership arm free to be satisfied by a
    prefix, which is exactly the arity blindness this tree was caught by last
    session.
    """
    supervisor_source = _module_file("ops.supervisor")
    assert supervisor_source is not None, "ops.supervisor is not on disk - this arm reads it"

    # ONE ASSERTION, BOTH DIRECTIONS. Set equality reddens on a dropped symbol
    # and on an invented one; the length beside it reddens on a duplicate, which
    # set equality alone would absorb.
    assert (len(SUPERVISOR_CONTRACT), set(SUPERVISOR_CONTRACT)) == (
        5,
        {"build_parser", "main", "supervise", "SupervisorConfig", "DEFAULT_CHILD_ARGS"},
    ), (
        f"the supervisor contract is {SUPERVISOR_CONTRACT} - it identifies the module the "
        "task argv names, and no other arm in this file notices when it shrinks"
    )

    undeclared = [
        name
        for name in SUPERVISOR_CONTRACT
        if not _declares_a_module_level_name(supervisor_source, name)
    ]
    assert undeclared == [], (
        f"the contract names symbols {supervisor_source.relative_to(REPO_ROOT).as_posix()} "
        f"does not declare at module level: {undeclared}"
    )

    # The positive control for that scan, in the same arm: a scan that answered
    # True for everything would have passed the assertion above vacuously.
    assert not _declares_a_module_level_name(
        supervisor_source, "SymbolTheSupervisorDoesNotDeclare"
    ), "the declaration scan accepts a name that is not in the file - it is measuring nothing"


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


def test_the_placeholder_shape_is_read_from_the_installer_that_enforces_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WHAT COUNTS AS A PLACEHOLDER is read, and installer drift reddens here.

    THE DEFECT THIS EXISTS FOR, measured at b3bef1a. `_PLACEHOLDER_RE` hand-typed
    `__[A-Z_]+__`, duplicating the pattern `ops/install_scheduled_task.ps1:124`
    enforces and throws on at 125, with no drift guard of any kind. Change the
    installer's notion of a placeholder and this grader silently disagreed with
    it about what a placeholder even is, staying green in both directions - a
    survivor the installer would now refuse could go unreported here, and a
    token the installer no longer substitutes could still read as legitimate.

    The three controls below are in-memory drifted installers. The real
    `ops/install_scheduled_task.ps1` is never written, and the drifted texts are
    built from the pattern READ out of it through `_mutate`, whose presence
    assertion means a stale drift target reddens rather than mutating nothing.
    """
    real = _installer_text()
    source = _installer_placeholder_pattern().pattern
    assert source, "the installer's placeholder pattern is empty - this arm is measuring nothing"

    # THE STRONG CONTROL: the derived pattern reaches the grader's output. A
    # widened installer pattern - one that also calls the dotted module name a
    # placeholder - must make the UNMUTATED tracked XML mint a complaint. A
    # grader still consulting a hardcoded pattern cannot produce this token.
    widened = _mutate(real, f"-match '{source}'", f"-match '(?:{source}|ops\\.supervisor)'")
    monkeypatch.setitem(globals(), "_installer_text", lambda: widened)
    assert "unsubstituted-placeholder:ops.supervisor" in grade_task_argv(_real_xml_text())
    monkeypatch.undo()

    # DRIFT, NARROWED: an installer that calls only one literal token a
    # placeholder no longer describes the tokens it substitutes, and the
    # derivation refuses to hand that back as authoritative.
    narrowed = _mutate(real, f"-match '{source}'", "-match '__INSTALL_ROOT__'")
    monkeypatch.setitem(globals(), "_installer_text", lambda: narrowed)
    with pytest.raises(AssertionError):
        _installer_placeholder_pattern()
    monkeypatch.undo()

    # DRIFT, DECLARATION GONE: the installer stops testing for survivors at all.
    # The derivation must go red rather than fall back to a remembered shape.
    renamed = _mutate(real, f"$xml -match '{source}'", f"$xmlBody -match '{source}'")
    monkeypatch.setitem(globals(), "_installer_text", lambda: renamed)
    with pytest.raises(AssertionError):
        _installer_placeholder_pattern()


# ---------------------------------------------------------------------------
# THE LIVENESS INVOCATION, AND THE DOCSTRING'S OWN CLAIM
#
# Added because both were UNGRADED at 88c0874, measured this session.
#
#   1. `ops/install_scheduled_task.ps1:198` runs the liveness checker and `:217`
#      exits with its status. A grep of `tests/` for `consolePython`,
#      `livenessExit` or `LIVENESS` returned exactly one hit -
#      `tests/test_task_state_claims.py:259` - and that hit is a SYNTHETIC
#      negative-control literal inside a parametrize for `_violates_code_rule`.
#      It never opens the installer. The block above this one reads the same
#      `.ps1` and stops at its line 132 banner, so an edit that pointed the
#      checker at the wrong interpreter, dropped the task name, or swallowed the
#      exit status left every suite green while the installer went on printing
#      LIVENESS ESTABLISHED for a task nothing had established.
#   2. The docstring paragraph "EVERY EXPECTATION ABOUT THE ARGV IS READ, NEVER
#      RETYPED" replaced a sentence that was FALSE AS WRITTEN, and nothing
#      grades the replacement. A drift back is a silent lie to the next reader.
#
# THE POPULATION IS TWO, AND THE FIRST VERSION GRADED ONE. `git grep -n
# 'exit $livenessExit' -- ops/` returns two tracked hits,
# `ops/install_responder_task.ps1:254` and `ops/install_scheduled_task.ps1:217`,
# and `ops/install_responder_task.ps1:231-254` runs the same construct with the
# same variable names. So the grader below takes its text and its label as
# PARAMETERS, and `tests/test_responder_task_argv.py` runs the identical mutant
# battery against the second installer. The one derivation that did not
# transfer was the task name: it was read from a banner only the supervisor
# prints, and it now reads `Register-ScheduledTask -TaskName`, which both carry.
#
# STILL NOT GRADED, AND STILL DELIBERATELY: registration, and RUNTIME BEHAVIOUR
# OF ANY KIND. Nothing below calls `schtasks`, runs either installer, or
# executes the checker. THIS IS A SHAPE GRADER OVER TEXT: an installer that is
# textually perfect and broken at runtime - `Set-StrictMode`, quoting, a `PATH`
# that resolves some other `python.exe` - grades clean from here. The installer
# is READ as text and the checker is checked for existence and for a `__main__`
# guard, and no claim beyond that is made.
#
# WHAT WAS TRUE BEFORE THIS BLOCK EXISTED, stated precisely because a looser
# version of it is false: `ops/install_scheduled_task.ps1` was already pinned by
# `tests/test_task_state_claims.py:216` and by
# `tests/test_ci_workflow_complement.py:241,263` for NEGATIVE properties. What
# nothing graded was the liveness INVOCATION and its exit propagation.
# ---------------------------------------------------------------------------

#: Every complaint bucket the liveness grader can mint. Held apart from
#: `GRADED_TOKENS` because the two graders read different artifacts and a shared
#: bucket list would let a mutant for one satisfy the coverage arm for the other.
LIVENESS_TOKENS = (
    "liveness-invocation-count",
    "liveness-interpreter-is-not-the-resolved-console-python",
    "liveness-argv-is-not-the-checker-and-the-task-name",
    "liveness-exit-not-captured",
    "liveness-exit-not-propagated",
    "liveness-exit-shadows-the-verdict",
)

#: `& $exe $arg $arg ...` - a PowerShell call-operator invocation whose every
#: token is a variable. The real invocation at `ops/install_scheduled_task.ps1:198`
#: has that shape, and requiring it is what makes the argv readable at all.
_CALL_OPERATOR_RE = re.compile(r"^&\s+(\$[A-Za-z_]\w*)((?:\s+\$[A-Za-z_]\w*)+)$")

#: `$var = Resolve-Something`. The installer resolves the CONSOLE interpreter
#: through a function rather than reusing `$PythonwExe`, and which variable
#: holds the result is read from this assignment rather than retyped.
_CONSOLE_PYTHON_RE = re.compile(r"^[ \t]*(\$[A-Za-z_]\w*)\s*=\s*(Resolve-[A-Za-z]\w*)\s*$", re.M)

#: Every `$var = Join-Path $root 'relative'` in the installer. The XML path is
#: derived from this shape too, at `_XML_PATH_RE`; here the whole population is
#: read so the `.py` member can be selected rather than its name retyped.
_JOIN_PATH_RE = re.compile(
    r"^[ \t]*(\$[A-Za-z_]\w*)\s*=\s*Join-Path\s+(\$[A-Za-z_]\w*)\s+'([^']*)'\s*$", re.M
)

#: The banner that tells the operator WHICH task the script is acting on. Same
#: shape as `_BANNER_RE`, and it is the reason the task-name variable is derived
#: rather than assumed: the checker takes the task name as its one positional
#: (`ops/check_task_liveness.py:705`), so handing it any other variable queries
#: a task that does not exist and the verdict is about nothing.
_TASK_NAME_BANNER_RE = re.compile(
    r"Write-Step\s*\(\s*'task name\s*:\s*'\s*\+\s*(\$[A-Za-z_]\w*)\s*\)"
)

#: `Register-ScheduledTask -TaskName $Var`. THE TASK-NAME DERIVATION FOR BOTH
#: INSTALLERS, and the reason it is this statement rather than the banner: the
#: checker must be asked about the task that was actually REGISTERED, and this
#: is the only line in either script that registers one. The supervisor also
#: prints a task-name banner and the responder does not, so a banner-based
#: derivation graded one installer and raised on the other - which is how the
#: liveness grading came to cover one of the two tracked installers. The
#: supervisor's banner keeps its own floor, at the arm that names it.
_REGISTER_TASK_NAME_RE = re.compile(
    r"Register-ScheduledTask\s+-TaskName\s+(\$[A-Za-z_]\w*)\b"
)

#: `$var = $LASTEXITCODE`, the only reading of a native command's status that
#: PowerShell offers, and it is clobbered by the next native call.
_LASTEXITCODE_RE = re.compile(r"^(\$[A-Za-z_]\w*)\s*=\s*\$LASTEXITCODE$")

_EXIT_RE = re.compile(r"^exit\b.*$")


def _liveness_complaint(bucket: str, detail: str = "") -> str:
    """One stable complaint token for the liveness grader, `bucket` or `bucket:detail`.

    Mirrors `_complaint`, including the refusal of an undeclared bucket, so the
    declared detector set is enforced by the code that mints the tokens.
    """
    if bucket not in LIVENESS_TOKENS:
        raise AssertionError(f"{bucket} is not a declared liveness complaint bucket")
    return f"{bucket}:{detail}" if detail else bucket


def _significant_statements(text: str) -> list[str]:
    """Every non-blank, non-comment line of a PowerShell script, stripped.

    ADJACENCY IS THE POINT. `$LASTEXITCODE` holds the status of the LAST native
    command, so a statement wedged between the invocation and the capture can
    replace the verdict with its own. Comments and blank lines cannot run, so
    they are removed rather than counted, and the strip also drops the `\\r` of
    the CRLF this `.ps1` carries on disk.
    """
    statements = [line.strip() for line in text.splitlines()]
    return [line for line in statements if line and not line.startswith("#")]


def _installer_console_python_variable(text: str, label: str) -> str:
    """The variable holding the CONSOLE interpreter, and the function it comes from.

    Two floors in the one derivation: exactly one `Resolve-*` assignment must
    exist, and the function it names must be DECLARED in the same script. A
    resolver that is called but never defined would be a `CommandNotFoundException`
    under `Set-StrictMode`, not a console python.

    `label` names WHICH installer the text came from, so a red says which of the
    two tracked scripts drifted rather than "the installer".
    """
    found = _CONSOLE_PYTHON_RE.findall(text)
    if len(found) != 1:
        raise AssertionError(
            f"{label} makes {len(found)} Resolve-* assignments - "
            "the console-interpreter derivation is not reading one variable"
        )
    variable, function = found[0]
    declared = any(
        line.startswith(f"function {function}") for line in text.splitlines()
    )
    if not declared:
        raise AssertionError(
            f"{label} assigns {variable} from {function}, which it never declares"
        )
    return variable


def _installer_liveness_checker(text: str, label: str) -> tuple[str, Path]:
    """The variable holding the checker path, and the file `-LiteralPath` would find.

    The checker is SELECTED out of the installer's Join-Path population by being
    the `.py` one, so its filename is read rather than retyped. Three floors:
    exactly one such path, it must be rooted at the same install-root variable
    the task XML is read from, and the file it names must exist AND carry a
    `__main__` guard. That last one is not decoration - a checker without a guard
    is imported by `python` and exits 0, and `ops/install_scheduled_task.ps1:201`
    reads 0 as LIVENESS ESTABLISHED.
    """
    candidates = [
        (variable, root, relative)
        for variable, root, relative in _JOIN_PATH_RE.findall(text)
        if relative.endswith(".py")
    ]
    if len(candidates) != 1:
        raise AssertionError(
            f"{label} builds {len(candidates)} .py paths with Join-Path - "
            "the liveness-checker derivation is not reading one file"
        )
    variable, root, relative = candidates[0]
    xml_root = _XML_PATH_RE.search(text)
    if xml_root is None or root != xml_root.group(1):
        raise AssertionError(
            f"{label} roots the checker at {root} but reads the task XML from "
            f"{xml_root.group(1) if xml_root else 'nothing'} - they are not the same checkout"
        )
    path = REPO_ROOT / relative.replace("\\", "/")
    if not path.is_file():
        raise AssertionError(f"{label} runs {relative}, which is not on disk")
    if not _declares(path, 'if __name__ == "__main__":'):
        raise AssertionError(
            f"{relative} has no __main__ guard - python would import it and exit 0, "
            "which the installer reads as LIVENESS ESTABLISHED"
        )
    if not _declares(path, "def main("):
        raise AssertionError(f"{relative} declares no main - it is not a CLI")
    return variable, path


def _installer_task_name_variable(text: str, label: str) -> str:
    """The variable the installer REGISTERS the task under.

    Read from the one `Register-ScheduledTask -TaskName` statement rather than
    from the param block, so the variable handed to the checker is the same one
    the scheduler was given. The checker takes the task name as its one
    positional (`ops/check_task_liveness.py:705`), so any other variable queries
    a task that was never registered and the verdict is about nothing.

    Two floors: exactly one registration, and the variable it names must be
    declared in the param block with a non-empty default, or the checker is
    handed an empty task name and reports on nothing.

    NOT THE BANNER. `_TASK_NAME_BANNER_RE` reads a line only the supervisor
    installer has, so deriving from it graded one of the two tracked installers
    and raised on the other. The banner is still a floor, but a supervisor-only
    one, asserted at the arm that reads it.
    """
    registrations = _REGISTER_TASK_NAME_RE.findall(text)
    if len(registrations) != 1:
        raise AssertionError(
            f"{label} makes {len(registrations)} Register-ScheduledTask -TaskName calls - "
            "the task-name derivation is not reading one registration"
        )
    variable = registrations[0]
    default = re.search(
        r"^\s*\[string\]\s*" + re.escape(variable) + r"\s*=\s*'([^']+)'", text, re.M
    )
    if default is None:
        raise AssertionError(
            f"{label} registers the task under {variable} but declares no non-empty "
            "default for it in the param block"
        )
    return variable


def grade_installer_liveness(text: str, label: str) -> list[str]:
    """Complaints about an installer's liveness invocation and its exit propagation.

    A SHAPE GRADER OVER TEXT, AND NOTHING MORE. Nothing here registers a task,
    executes the `.ps1`, or runs the checker. An installer that is textually
    perfect and broken at runtime - a `Set-StrictMode` violation, a quoting bug,
    a `PATH` that resolves a different `python.exe` - grades clean from here.
    What this rules out is a text-level drift in WHICH interpreter, WHICH
    arguments, and whether the status survives to the caller.

    BOTH TRACKED INSTALLERS RUN THROUGH IT. `ops/install_scheduled_task.ps1` and
    `ops/install_responder_task.ps1` carry the same construct, so `text` and
    `label` are parameters rather than a hardcoded read: the first version of
    this grader read one file by name and left the second ungraded.

    Returns an empty list when the installer runs the checker it resolves, with
    the console interpreter it resolves and the task name it announces, captures
    that run's status from `$LASTEXITCODE` in the very next statement, and exits
    with the captured value and nothing else.

    EQUALITY, NEVER CONTAINMENT, as everywhere else in this file: the argv is
    compared as a TUPLE, which pins its length and its identity in one
    comparison, and a dropped `$TaskName` is therefore a complaint rather than a
    prefix that still matches.
    """
    complaints: list[str] = []
    statements = _significant_statements(text)
    calls = [
        (index, match)
        for index, statement in enumerate(statements)
        if (match := _CALL_OPERATOR_RE.match(statement)) is not None
    ]
    if len(calls) != 1:
        return [_liveness_complaint("liveness-invocation-count", str(len(calls)))]

    index, match = calls[0]
    interpreter = match.group(1)
    argv = tuple(match.group(2).split())

    expected_interpreter = _installer_console_python_variable(text, label)
    checker_variable, _ = _installer_liveness_checker(text, label)
    expected_argv = (checker_variable, _installer_task_name_variable(text, label))

    if interpreter != expected_interpreter:
        complaints.append(
            _liveness_complaint(
                "liveness-interpreter-is-not-the-resolved-console-python", interpreter
            )
        )
    if argv != expected_argv:
        complaints.append(
            _liveness_complaint(
                "liveness-argv-is-not-the-checker-and-the-task-name", " ".join(argv)
            )
        )

    # THE CAPTURE, AND ITS ADJACENCY. Anything at all between the invocation and
    # the read is a chance for `$LASTEXITCODE` to be about a different command.
    following = statements[index + 1 :]
    if not following:
        return [*complaints, _liveness_complaint("liveness-exit-not-captured", "end of script")]
    captured = _LASTEXITCODE_RE.match(following[0])
    if captured is None:
        return [*complaints, _liveness_complaint("liveness-exit-not-captured", following[0])]
    capture_variable = captured.group(1)

    # PROPAGATION. The LAST exit reachable after the invocation is the script's
    # verdict, and every earlier one after the invocation can pre-empt it.
    exits = [statement for statement in following if _EXIT_RE.match(statement)]
    if not exits:
        return [*complaints, _liveness_complaint("liveness-exit-not-propagated", "none")]
    if exits[-1] != f"exit {capture_variable}":
        complaints.append(_liveness_complaint("liveness-exit-not-propagated", exits[-1]))
    complaints.extend(
        _liveness_complaint("liveness-exit-shadows-the-verdict", statement)
        for statement in exits[:-1]
    )
    return complaints


#: `(id, old, new, expected token)`. One in-memory mutant per liveness detector,
#: and TWO for every bucket whose single token hides two different repairs. The
#: real `ops/install_scheduled_task.ps1` is never written.
LIVENESS_MUTANTS = (
    (
        "the-checker-is-never-run-at-all",
        "& $consolePython $livenessChecker $TaskName",
        "Write-Step 'skipping the liveness check'",
        "liveness-invocation-count:0",
    ),
    (
        "a-second-call-operator-so-the-graded-invocation-is-only-one-of-them",
        "& $consolePython $livenessChecker $TaskName",
        "& $consolePython $livenessChecker $TaskName\n& $consolePython $livenessChecker $TaskUser",
        "liveness-invocation-count:2",
    ),
    (
        "the-checker-runs-under-the-windowless-interpreter-the-task-uses",
        "& $consolePython $livenessChecker $TaskName",
        "& $PythonwExe $livenessChecker $TaskName",
        "liveness-interpreter-is-not-the-resolved-console-python:$PythonwExe",
    ),
    # ARITY, NOT JUST IDENTITY. The checker's one positional is the task name,
    # so a dropped argument is a checker invoked with no subject at all.
    (
        "the-task-name-argument-is-dropped",
        "& $consolePython $livenessChecker $TaskName",
        "& $consolePython $livenessChecker",
        "liveness-argv-is-not-the-checker-and-the-task-name:$livenessChecker",
    ),
    (
        "the-checker-is-handed-the-account-instead-of-the-task",
        "& $consolePython $livenessChecker $TaskName",
        "& $consolePython $livenessChecker $TaskUser",
        "liveness-argv-is-not-the-checker-and-the-task-name:$livenessChecker $TaskUser",
    ),
    (
        "the-status-is-assigned-a-constant-instead-of-being-read",
        "$livenessExit = $LASTEXITCODE",
        "$livenessExit = 0",
        "liveness-exit-not-captured:$livenessExit = 0",
    ),
    # ADJACENCY, WHICH A PRESENCE CHECK CANNOT SEE. The capture is still there
    # and still reads `$LASTEXITCODE`; it is simply no longer about the checker.
    (
        "a-native-call-lands-between-the-checker-and-the-capture",
        "$livenessExit = $LASTEXITCODE",
        "& $consolePython --version\n$livenessExit = $LASTEXITCODE",
        "liveness-exit-not-captured:& $consolePython --version",
    ),
    (
        "the-verdict-is-captured-and-then-thrown-away",
        "exit $livenessExit",
        "exit 0",
        "liveness-exit-not-propagated:exit 0",
    ),
    (
        "the-script-simply-runs-off-the-end-after-capturing",
        "exit $livenessExit",
        "Write-Step 'finished'",
        "liveness-exit-not-propagated:none",
    ),
    (
        "an-earlier-exit-pre-empts-the-verdict-that-is-still-written-below-it",
        "exit $livenessExit",
        "exit 0\nexit $livenessExit",
        "liveness-exit-shadows-the-verdict:exit 0",
    ),
)


def test_the_installer_liveness_invocation_grades_clean() -> None:
    """The neighbours-survive guard for the liveness grader.

    A grader that complained about everything would score on every mutant below
    and mean nothing. This one assertion is what makes that impossible.
    """
    assert grade_installer_liveness(_installer_text(), INSTALLER_PS1.name) == []


def test_the_liveness_checker_is_run_with_the_console_python_and_the_task_name() -> None:
    """WHICH interpreter and WHICH arguments, by equality, in order, at pinned length.

    ONE ASSERTION CARRIES THE WHOLE CLAIM. The tuple on the left is the whole
    invocation read out of the installer and the tuple on the right is built from
    three independent derivations, so order and length are pinned with identity
    rather than beside it - `EXPECTED == (a, *rest)` holds at any length and that
    is the arity blindness this tree was caught by.

    The floor that stops this from comparing two empties: the derivations each
    raise on an empty read, and the invocation must be found at all.

    THE BANNER FLOOR IS IN THIS ARM AND NOT BESIDE IT. The task-name derivation
    now reads `Register-ScheduledTask -TaskName`, which both tracked installers
    carry; the banner it used to read is supervisor-only. Asserting the banner in
    a separate arm would leave this one free to agree with a registration the
    operator was never shown, so the cross-check sits under the tuple it guards.
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

    # THE SUPERVISOR-ONLY FLOOR, kept from the banner derivation this arm used
    # to depend on. The responder installer prints no such banner, so the
    # requirement moved here rather than being dropped: the task this installer
    # SHOWS the operator must be the task it registers and asks about.
    banner = _TASK_NAME_BANNER_RE.search(text)
    assert banner is not None, (
        f"{label} prints no task-name banner - the operator is not shown which task "
        "the liveness verdict below it is about"
    )
    assert banner.group(1) == argv[1], (
        f"{label} shows the operator {banner.group(1)} and asks the checker about "
        f"{argv[1]} - the verdict is about a different task than the banner names"
    )


def test_the_liveness_exit_status_is_captured_adjacently_and_propagated() -> None:
    """The status must reach the caller, and the read must be about the checker.

    Two mechanisms, both asserted here rather than inferred from the absence of a
    complaint: the statement IMMEDIATELY after the invocation reads
    `$LASTEXITCODE` into a variable, and the LAST exit in the script is that
    variable and there is no other exit after the invocation to pre-empt it.
    `$LASTEXITCODE` is clobbered by the next native command, so adjacency is the
    mechanism and not a style preference.
    """
    statements = _significant_statements(_installer_text())
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
def test_the_liveness_grader_fires_on_a_mutated_installer(
    old: str, new: str, expected: str
) -> None:
    """Non-vacuity: each liveness detector is shown red on an in-memory mutant.

    `ops/install_scheduled_task.ps1` is never written. `_mutate` asserts the
    target is present, so a stale mutation reddens rather than grading the real
    file twice, and the uniqueness floor is asserted HERE rather than in a
    separate arm: `_mutate` replaces the FIRST occurrence, so a target that
    appears twice would leave a second copy standing and the mutant would be a
    weaker text than its id claims.
    """
    text = _installer_text()
    assert text.count(old) == 1, f"{old!r} appears {text.count(old)} times - _mutate replaces one"
    assert expected in grade_installer_liveness(_mutate(text, old, new), INSTALLER_PS1.name)


def test_every_liveness_detector_has_a_control() -> None:
    """`LIVENESS_TOKENS` and `LIVENESS_MUTANTS` are pinned to each other by SET EQUALITY.

    A detector added without a control goes red here on its own. Populations,
    named: `LIVENESS_TOKENS` is every bucket `_liveness_complaint` will mint, and
    the covered set is the bucket half of every expected token in
    `LIVENESS_MUTANTS`. Unlike `GRADED_TOKENS` there is no uncontrolled member,
    so the equality is exact in both directions.
    """
    assert LIVENESS_MUTANTS, "the liveness mutant table is empty - this arm is measuring nothing"
    covered = {expected.split(":", 1)[0] for _, _, _, expected in LIVENESS_MUTANTS}
    assert covered == set(LIVENESS_TOKENS), (
        f"uncontrolled detectors {sorted(set(LIVENESS_TOKENS) - covered)}, "
        f"controls for buckets that cannot be minted {sorted(covered - set(LIVENESS_TOKENS))}"
    )


# ---------------------------------------------------------------------------
# THE DOCSTRING'S OWN CLAIM, GRADED AS A CLAIM
# ---------------------------------------------------------------------------

#: The sentence `fe6c004` put in place of one that was false as written. Read
#: out of the parsed module docstring, never out of this file's raw source - the
#: needle below is itself a line of that source, so a raw-source search would
#: find its own definition and pass on a module whose docstring said nothing.
ARGV_DERIVATION_CLAIM = "EVERY EXPECTATION ABOUT THE ARGV IS READ, NEVER RETYPED."

#: The bullets under that claim, `  - WHICH ...:`. The claim enumerates the
#: questions it covers, so the enumeration is the population the arm below must
#: control - and it is READ from the prose rather than retyped beside it.
_CLAIMED_QUESTION_RE = re.compile(r"^  - (WHICH [A-Z ]+?):", re.M)


def _module_docstring() -> str:
    """This module's docstring, parsed out of the tracked source bytes.

    READ FROM DISK, NOT FROM `__doc__`. `python -OO` discards docstrings, and a
    `__doc__` of `None` under it would make every check below vacuous rather than
    red. `ast` reads the source either way.
    """
    source = Path(__file__).resolve().read_bytes()
    non_ascii = [byte for byte in source if byte > 0x7F]
    assert not non_ascii, f"this module is not 7-bit ASCII on disk: {non_ascii[:8]}"
    docstring = ast.get_docstring(ast.parse(source.decode("ascii")))
    assert docstring, "this module has no docstring - the claim below is about nothing"
    return docstring


def test_the_docstrings_derivation_claim_is_true_of_this_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The docstring says the argv expectations are DERIVED. This proves it.

    THE DEFECT THIS EXISTS FOR, measured at 88c0874. `fe6c004` replaced
    "NEITHER SIDE OF ANY COMPARISON IS RETYPED" - false as written - with the
    sentence in `ARGV_DERIVATION_CLAIM`, and a grep of this module for `__doc__`,
    `MODULE_DOC` or `_DOCSTRING` returned zero. The corrected sentence could drift
    back to the false one, or stay while the code beneath it stopped deriving
    anything, and nothing anywhere would go red.

    A STRING-PRESENCE CHECK IS NOT A GRADER, so presence is only the first half.
    The second half DRIFTS EACH EXPECTATION'S SOURCE and requires the UNMUTATED
    tracked XML to mint a specific complaint. A retyped expectation cannot
    produce that complaint: it does not move when its source moves. That is the
    whole content of the word "read" in the sentence being graded.

    THE POPULATION IS READ FROM THE PROSE. The claim enumerates five questions as
    `  - WHICH ...` bullets, and the drift table below is pinned to that
    enumeration by set equality, so a sixth question added to the docstring
    without a control reddens here, and so does dropping a control.

    NOTHING IS WRITTEN. The installer drifts are in-memory strings built through
    `_mutate`, whose presence assertion means a stale drift target reddens rather
    than drifting nothing, and the parser drift is a `monkeypatch.setattr` on the
    imported supervisor module.
    """
    docstring = _module_docstring()
    assert docstring.count(ARGV_DERIVATION_CLAIM) == 1, (
        f"the module docstring carries {docstring.count(ARGV_DERIVATION_CLAIM)} copies of the "
        f"corrected derivation claim {ARGV_DERIVATION_CLAIM!r} - fe6c004 put exactly one there "
        "in place of a sentence that was false as written"
    )
    # NON-VACUITY, NOT A RETYPED COUNT. The number of questions is NOT pinned
    # here: the set equality at the bottom of this arm pins the population in
    # both directions, and a hand-typed count beside it would be a second
    # authority to keep in step for no added detection. All this floor says is
    # that the scan found something to control.
    claimed = set(_CLAIMED_QUESTION_RE.findall(docstring))
    assert claimed, (
        "the docstring enumerates no WHICH-question bullets - either the claim lost its "
        "enumeration or this scan no longer reads it, and the equality below would be vacuous"
    )

    real = _installer_text()
    covered: set[str] = set()

    # WHICH INTERPRETER. The installer stops substituting the token the XML
    # carries. A grader holding a retyped `__PYTHONW_EXE__` cannot notice.
    drifted = _mutate(real, "$xml.Replace('__PYTHONW_EXE__'", "$xml.Replace('__PYTHONW_BINARY__'")
    monkeypatch.setitem(globals(), "_installer_text", lambda: drifted)
    assert "command-is-not-the-installer-interpreter:__PYTHONW_EXE__" in grade_task_argv(
        _real_xml_text()
    )
    monkeypatch.undo()
    covered.add("WHICH INTERPRETER")

    # WHICH ARGUMENTS. The banner the installer prints grows a flag the XML does
    # not carry, and the tracked argv is now the one that disagrees.
    drifted = _mutate(real, "+ ' -m ops.supervisor')", "+ ' -m ops.supervisor --interval 30')")
    monkeypatch.setitem(globals(), "_installer_text", lambda: drifted)
    assert "argv-is-not-the-installer-command:-m ops.supervisor" in grade_task_argv(
        _real_xml_text()
    )
    monkeypatch.undo()
    covered.add("WHICH ARGUMENTS")

    # WHICH WORKING DIRECTORY. The install-root placeholder is renamed at the
    # substitution the expectation is derived through.
    drifted = _mutate(real, "$xml.Replace('__INSTALL_ROOT__'", "$xml.Replace('__CHECKOUT_ROOT__'")
    monkeypatch.setitem(globals(), "_installer_text", lambda: drifted)
    assert "working-directory-is-not-the-install-root:__INSTALL_ROOT__" in grade_task_argv(
        _real_xml_text()
    )
    monkeypatch.undo()
    covered.add("WHICH WORKING DIRECTORY")

    # WHICH MODULE. The expectation is the DISK, reached through `_module_file`.
    # Replace that reader and the verdict must move with it.
    monkeypatch.setitem(globals(), "_module_file", lambda dotted: None)
    assert "module-file-missing:ops.supervisor" in grade_task_argv(_real_xml_text())
    monkeypatch.undo()
    covered.add("WHICH MODULE")

    # WHICH FLAGS AND WHAT THEY MEAN. The spellings and the meaning both come off
    # the supervisor's own `build_parser`. Flip what that parser says `--dry-run`
    # defaults to and the meaning grade must flip with it, on an argv that is
    # byte-for-byte the tracked one.
    supervisor = _load_module("ops.supervisor")
    original_build_parser = supervisor.build_parser

    def _dry_run_by_default() -> argparse.ArgumentParser:
        parser = original_build_parser()
        for action in parser._actions:
            if action.dest == "dry_run":
                action.default = True
        return parser

    assert "task-argv-is-a-dry-run" not in grade_task_argv(_real_xml_text())
    monkeypatch.setattr(supervisor, "build_parser", _dry_run_by_default)
    assert "task-argv-is-a-dry-run" in grade_task_argv(_real_xml_text())
    monkeypatch.undo()
    covered.add("WHICH FLAGS AND WHAT THEY MEAN")

    assert covered == claimed, (
        f"questions the docstring claims with no drift control {sorted(claimed - covered)}, "
        f"drift controls for questions the docstring does not claim {sorted(covered - claimed)}"
    )


# ---------------------------------------------------------------------------
# THE PLACEHOLDER DELIMITER IS THE GRAMMAR. THE SPELLING IS NOT.
#
# DERIVED BY SUBTRACTION, measured this run against the tracked templates.
# Scanning ops/ResinCompute-Supervisor.xml and ops/ResinCompute-Responder.xml
# for the DELIMITER PAIR alone - every `__...__` run, whatever it spells -
# returns the supervisor's three tokens and the responder's six and NOTHING
# ELSE. In the template files the delimiter is a PERFECT discriminator: every
# occurrence of it is a placeholder, and no other construct in either file uses
# it. Subtracting what the old `__[A-Z_]+__` already caught from that scan left
# the EMPTY SET.
#
# So the widening is NOT justified by a token that exists today. It is
# justified by what the guard's SUBJECT is, and that is the argument this block
# exists to record.
#
# The guard's subject is not the template's current token list. It is the
# post-substitution string about to be handed to `Register-ScheduledTask`, and
# its token content is decided by two independently hand-maintained lists: the
# template, which is editable data, and the `.Replace(...)` calls in the
# installer. The guard exists to detect DRIFT between those two lists. A drift
# detector whose grammar is derived from the CURRENT state of one of them is
# exactly as tight as the other already is, and adds nothing over enumerating
# the `.Replace` calls - which is the thing the guard is there to avoid. Only
# the DELIMITER can be derived as invariant across template edits, so the
# delimiter is what is matched and the inner run is the full identifier class.
#
# THE COST, stated rather than hidden. The subject also contains SUBSTITUTED
# VALUES - the install root and the interpreter path. A checkout living under a
# directory spelled `my__build__2` would now trip the guard where it once did
# not. That false positive is LOUD, names the matched text, and is recoverable
# in one read. The false negative it replaces is a task ARMED with a literal
# `__Slot1__` inside its argv, which a scheduled task reports as State Ready
# forever. The asymmetry is what decides it.

#: Tokens carrying the placeholder DELIMITER while escaping the SCREAMING_SNAKE
#: spelling the guard used to assume. Every entry differs from every other in
#: MORE THAN ONE position - case pattern, digit presence, and inner-underscore
#: presence all vary - so a guard that admitted one of them by a single-axis
#: accident still could not admit the table.
DELIMITED_SURVIVORS = (
    "__Slot1__",
    "__pythonw_exe__",
    "__taskUser2__",
    "__WINDOW_v3__",
)

#: Strings that must NOT read as placeholders, varying in more than one way: no
#: delimiter at all, single underscores throughout, a half-delimiter at either
#: end, the dotted module name this task actually runs, and a timestamp of the
#: shape a sibling installer substitutes IN and must not report back.
UNDELIMITED_NON_PLACEHOLDERS = (
    "WorkingDirectory",
    "_INSTALL_ROOT_",
    "__INSTALL_ROOT",
    "INSTALL_ROOT__",
    "ops.supervisor",
    "2026-09-07T19:00:00",
)

#: The grammar the guard used to carry, AS POWERSHELL ACTUALLY EVALUATED IT.
#: Frozen here as a NON-VACUITY CONTROL and deliberately not as a second
#: authority: nothing is graded against it, it only proves that the survivors
#: below really did escape the old guard, so the arm cannot quietly become a
#: table of tokens that always passed.
#:
#: `re.IGNORECASE` is the load-bearing half. This slice was dispatched with the
#: premise that a token carrying "a LOWERCASE LETTER OR A DIGIT" sailed through
#: both guards, and the lowercase half of that is FALSE. PowerShell's `-match`
#: is case-insensitive, so `__[A-Z_]+__` behaved as `__[A-Za-z_]+__` at runtime.
#: Measured 2026-09-11 end to end against both real installers with
#: `-WhatIfOnly`, return codes read in Python: a planted `__pythonw_exe__` threw
#: in BOTH (rc=1); a planted `__Slot1__` cleared BOTH (rc=0). Only the DIGIT
#: axis ever leaked, and a case-sensitive control here would have credited the
#: widening with closing a hole that was never open.
_SUPERSEDED_RE = re.compile(r"__[A-Z_]+__", re.IGNORECASE)

#: The sibling installer. The defect this arm defends against was SHARED by both
#: scripts and symmetric, so the fix has to be symmetric too.
SIBLING_INSTALLER_PS1 = REPO_ROOT / "ops" / "install_responder_task.ps1"


def test_the_installer_guard_catches_a_survivor_that_is_not_screaming_snake() -> None:
    """A surviving `__token__` is caught whatever it SPELLS, in both installers.

    THE DEFECT, measured before this arm existed. Both installers tested for
    survivors with `__[A-Z_]+__`. Because PowerShell's `-match` is
    case-insensitive that grammar caught lowercase tokens too, so the hole was
    narrower than first reported and exactly one axis wide: a DIGIT. Measured
    2026-09-11 end to end with `-WhatIfOnly` against a scratchpad mirror, return
    codes read in Python - a planted `__Slot1__` left BOTH installers exiting 0,
    and the unsubstituted token would have gone to `Register-ScheduledTask`
    verbatim, while a planted `__pythonw_exe__` threw in both.

    The pattern under test is READ from each installer rather than retyped, so
    this arm grades the guard that actually runs and moves with it.
    """
    assert len(DELIMITED_SURVIVORS) >= 4, (
        "the survivor table is empty or too thin to vary in more than one position - "
        "this arm would be measuring nothing"
    )
    assert len(UNDELIMITED_NON_PLACEHOLDERS) >= 5, (
        "the negative table is too thin to vary in more than one way - a decoy that "
        "varies one position pins one position"
    )

    # NON-VACUITY, and it is deliberately NOT "every survivor escaped". Under
    # the superseded grammar as PowerShell ran it, the digit-bearing entries
    # escaped and `__pythonw_exe__` did not; that one is carried as a CASE-AXIS
    # decoy the widening must still accept, not as evidence for it. What has to
    # hold is that enough of the table genuinely was leaking, or this arm is a
    # list of tokens that always passed.
    escaped = [token for token in DELIMITED_SURVIVORS if not _SUPERSEDED_RE.search(token)]
    assert len(escaped) >= 3, (
        f"only {escaped} escaped the superseded guard as PowerShell evaluated it - "
        "the survivor table is no longer testing the widening"
    )

    sibling_match = _MATCH_RE.search(
        SIBLING_INSTALLER_PS1.read_bytes().decode("ascii", errors="replace")
    )
    assert sibling_match is not None, (
        f"{SIBLING_INSTALLER_PS1.name} declares no placeholder-survivor pattern - "
        "the symmetry half of this arm is measuring nothing"
    )
    patterns = {
        INSTALLER_PS1.name: _installer_placeholder_pattern(),
        SIBLING_INSTALLER_PS1.name: re.compile(sibling_match.group(1)),
    }

    for name, pattern in patterns.items():
        missed = [token for token in DELIMITED_SURVIVORS if not pattern.search(token)]
        assert not missed, (
            f"{name} would leave {missed} unsubstituted in the XML it hands to "
            f"Register-ScheduledTask - its guard pattern {pattern.pattern!r} does not see them"
        )
        caught = [text for text in UNDELIMITED_NON_PLACEHOLDERS if pattern.search(text)]
        assert not caught, (
            f"{name}'s guard pattern {pattern.pattern!r} calls {caught} a placeholder, so "
            "ordinary task text and substituted values would refuse the registration"
        )

    # SYMMETRY. One installer widened and the other left behind is the asymmetry
    # this slice was dispatched believing it had found. Diverge them and this
    # goes red rather than leaving one script guarded and one not.
    sources = {name: pattern.pattern for name, pattern in patterns.items()}
    assert len(set(sources.values())) == 1, (
        f"the two installers disagree about what a placeholder is: {sources}"
    )
