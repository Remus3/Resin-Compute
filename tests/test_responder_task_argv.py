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
import shlex
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_XML = REPO_ROOT / "ops" / "ResinCompute-Responder.xml"
TASK_NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"

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


def _exec_argv(xml_text: str) -> list[str]:
    """The `<Exec>` argv from a task XML, script path first."""
    root = ElementTree.fromstring(xml_text)
    exec_nodes = root.findall(f".//{TASK_NS}Exec")
    if len(exec_nodes) != 1:
        raise AssertionError(f"expected exactly one Exec element, found {len(exec_nodes)}")
    arguments = exec_nodes[0].findtext(f"{TASK_NS}Arguments")
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
    argv = _exec_argv(xml_text)
    script, flags = argv[0], argv[1:]

    # IDENTITY BEFORE ANYTHING ELSE. Everything below reads the named script's
    # own parser and constants, so grading has no meaning until the argv is
    # known to name the responder rather than merely to name a file.
    if not (REPO_ROOT / script).is_file():
        return [*complaints, f"script-missing:{script}"]
    if script not in _scripts_declaring_the_task_label():
        return [*complaints, f"script-does-not-declare-the-task-label:{script}"]
    try:
        module = _load_script(script)
    except _IMPORT_FAILURES:
        return [*complaints, f"script-will-not-import:{script}"]
    missing = [name for name in RESPONDER_CONTRACT if not hasattr(module, name)]
    if missing:
        return [*complaints, f"script-not-the-responder:{script}:{','.join(missing)}"]

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
            complaints.append(f"flag-not-a-declared-spelling:{spelling}")

    parsed: argparse.Namespace | None = None
    try:
        parsed, extras = parser.parse_known_args(flags)
    except SystemExit:
        complaints.append("parser-rejects-argv")
    else:
        for extra in extras:
            if extra.startswith("-"):
                complaints.append(f"unknown-flag:{extra}")
            elif not _parser_takes_positionals(parser):
                complaints.append(f"unexpected-positional:{extra}")

    # WHICH WINDOW IS WHICH, against the trigger in the same file.
    if parsed is not None:
        start_boundary, end_boundary = _trigger_boundaries(xml_text)
        if parsed.window_opens != start_boundary:
            complaints.append(f"window-opens-is-not-the-trigger-start:{parsed.window_opens}")
        if parsed.window_closes != end_boundary:
            complaints.append(f"window-closes-is-not-the-trigger-end:{parsed.window_closes}")

    # WHAT THE ARGV MEANS, from the code's own construction.
    run = _bounds_from_main(module, flags)
    if run.bounds is None:
        complaints.append(f"main-refused-argv:{_refusal_category(parser, flags, run)}")
    else:
        if not getattr(run.bounds, "armed", False):
            complaints.append("task-argv-does-not-arm")
        # WHICH GRAMMAR THE CALL ACTUALLY CARRIES. Compared by IDENTITY against
        # the module's own constant, so an equal literal cannot stand in for it
        # and a reworded grammar needs no edit here. The far end of this task is
        # a human: without `--latency-only` the argv still parses and still
        # arms, and every cycle it records publishes `hops` as an integer under
        # a lower-bound M1 for a run that has no machine at the other end. That
        # is the row the latency-only grammar exists to make impossible.
        if run.grammar is not module.GRAMMAR_LATENCY_ONLY:
            complaints.append("grammar-is-not-the-latency-only-grammar")

    # THE LABEL. Membership and identity are reported INDEPENDENTLY rather than
    # chained: under an `elif` the membership check could never speak on a real
    # drift, because any label that fails it also fails the identity check and
    # the identity check spoke first. Separated, "no constant declares this" and
    # "a declared label, but not the task's" are two different repairs.
    routed = module.source_from_argv(flags)
    inline = module.SOURCE_FLAG + "="
    named = module.SOURCE_FLAG in flags or any(item.startswith(inline) for item in flags)
    if not named:
        complaints.append("source-flag-absent")
    elif routed is None:
        complaints.append("source-label-unusable")
    else:
        if routed not in _declared_source_labels(module):
            complaints.append(f"source-not-a-declared-label:{routed}")
        if routed != getattr(module, TASK_LABEL_CONSTANT):
            complaints.append(f"source-not-the-task-label:{routed}")

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


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
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
    ],
)
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
