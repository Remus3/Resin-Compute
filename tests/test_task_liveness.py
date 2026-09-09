"""Regression tests for ops/check_task_liveness.py.

THE FIRST FINDING THESE TESTS PIN, measured on this machine 2026-09-08:

    Get-ScheduledTaskInfo -TaskName 'ResinCompute-Responder' reported
    LastTaskResult 0 and Get-ScheduledTask reported State: Ready. Both read as
    healthy. The task's ONLY trigger carried EndBoundary 2026-09-07T21:00:00,
    already in the past. NextRunTime was empty. The task would never fire
    again, and a session hand-off asserted "Ready on a 5-minute tick" from that
    State string and was wrong by 24 hours.

    A TASK STATE STRING NAMES A STATE, NOT A CAPABILITY.

THE SECOND FINDING, which the first version of this file ENSHRINED AS CORRECT
rather than caught. It asserted that an ABSENT EndBoundary is LIVE, which is
absence of evidence sold as evidence. Measured on this same machine the same
day, the task RunPlatformExperienceHelper_Metrics under TaskPath
'\\GoogleUserPEH\\' has State Ready, an EMPTY NextRunTime, and one enabled
MSFT_TaskTimeTrigger with StartBoundary 2026-07-08T19:37:35-05:00, no
EndBoundary and no repetition. It fired two months ago and is spent, and the
old rule called it LIVE. MEASURED_SPENT_ONE_SHOT below is that exact payload,
captured from the probe rather than imagined.

DESIGN OF THIS FILE, and it is deliberate:

  - EVERY NEGATIVE ARM IS PAIRED WITH A POSITIVE CONTROL THROUGH THE SAME CODE
    PATH. A test asserting DORMANT is worth nothing on its own - a function
    that returns DORMANT unconditionally would pass it. Each such arm has a
    sibling feeding a fixture that differs in ONE field and asserting LIVE.

  - MOST ARMS RUN NO POWERSHELL, so the suite passes on a machine carrying no
    such task. But THREE DO, and they are the point: a hand-typed fixture can
    only ever prove the parser agrees with the person who typed it. The probe
    can stop emitting a field the parser reads and every fixture arm stays
    green. The arms under "THE PROBE AND THE PARSER MUST AGREE" run the real
    probe against a real task and derive the required key set FROM THE PARSER
    by recording which keys it asks for. They skip, loudly, off Windows or
    without PowerShell.

  - NO SCHEDULED TASK IS REGISTERED, MODIFIED, ENABLED OR DISABLED anywhere in
    this file. Every PowerShell call here is a Get-.

  - A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE, and the first
    version of this docstring claimed enforcement it did not have. It said one
    arm proved "the real entry path routes through", which was true of the
    VERDICT function and false of validate_task_name: every main() arm stubbed
    collect_facts, the gate's only caller, so deleting the gate left the suite
    green. The arms under "THE NAME GATE IS ENFORCED" stub subprocess.run
    instead of collect_facts, so the real gate runs on the real path.

THE CEILING. Read this before naming any arm in this file, because five rounds
of refutation established it and the sixth round is what wrote it down:

    A TEST SUITE CANNOT PREVENT ARBITRARY RUNTIME BEHAVIOUR IN A MODULE IT
    IMPORTS. It can grade that module's SOURCE, and it can refuse to import a
    source that fails the grade. It cannot prove that a source which passes the
    grade will behave the same way at runtime, because the imported module can
    always branch on something the harness did not think to make identical.

  WHAT IS GUARANTEED HERE:

    A SOURCE GRADE, ENFORCED BEFORE THE IMPORT. The block under "THE SOURCE
    GATE" reads ops/check_task_liveness.py as bytes, parses it with ast, and
    raises if the grade fails - ahead of `from ops import check_task_liveness`,
    so the subject's module-level code has not run when the refusal happens.
    The grade covers: no mutating PowerShell Verb-Noun and no native mutator
    executable anywhere in the text; no call at import time other than
    re.compile, dataclass and field; and no reference anywhere to the channels
    a module would use to tell a harness from production - subprocess's
    identity or any attribute of it beyond the four it legitimately names,
    sys.modules, __debug__, the environment, sys.argv, and isatty.

  WHAT IS NOT GUARANTEED:

    RUNTIME BEHAVIOUR UNDER AN ADVERSARIAL MODULE. The argv derivation below
    must replace subprocess.run with something that does not launch a process,
    and that single divergence is observable in principle - a module that
    stashed the real subprocess.run at import and compared against it later
    would build one string here and another in real use. The source gate is
    what refuses that comparison; nothing in this file could detect it after
    the fact. An arm here that says "the text that ACTUALLY reaches PowerShell"
    would be claiming more than it checks, and an arm whose name claims more
    than it checks is worse than no arm, because the next reader stops looking.
    So no arm in this file is named that way.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import typing

import pytest

# --- THE SOURCE GATE, AND IT RUNS BEFORE THE SUBJECT IS IMPORTED ----------
#
# THE THIRD 2026-09-08 KILL, and it did not defeat a matcher. It went around
# the grading entirely. Every guard in this file used to sit BELOW
#
#     from ops import check_task_liveness as liveness
#
# and an import EXECUTES the subject's module-level code. Measured: a
# module-level
#
#     import os as _diag
#     _diag.remove('<canary>')
#
# planted in ops/check_task_liveness.py ran at that import, the canary file was
# deleted from disk, and `python -m pytest tests/test_task_liveness.py -q`
# reported every arm passing at exit 0. PREVENTION IS A CLAIM ABOUT AN INSTANT:
# a guard that runs after the import is a statement about a machine the subject
# has already had its way with.
#
# So the SOURCE IS GRADED FIRST, as bytes, through ast.parse, and the import
# below happens only if the grade is clean. A failure here is a COLLECTION
# error, which is stronger than a failing arm: no arm in this module runs, and
# the subject is never imported at all.
#
# WHAT THIS GATE GUARANTEES IS NARROW AND IS STATED IN FULL IN THE MODULE
# DOCSTRING UNDER "THE CEILING". It grades source and refuses to import a
# source that fails. It does not, and structurally cannot, prove that a module
# which passes will behave.

_SUBJECT_PATH = pathlib.Path(__file__).resolve().parent.parent / "ops" / "check_task_liveness.py"

# Verbs whose presence ANYWHERE in the module - not merely in the probe - would
# mean this tool had grown a way to change the machine. Matched by SHAPE, so a
# verb nobody enumerated is still caught the moment it is used on a noun.
#
# IGNORECASE, and the flag is the correction rather than a decoration. Measured
# 2026-09-08 against the version without it: lowercase `stop-process`, lowercase
# `unregister-scheduledtask` and uppercase `REMOVE-ITEM` all passed, while the
# comment beside it already ASSERTED case-insensitivity. The comment was true of
# the intent and false of the code, which is the worst of the two. PowerShell
# resolves a cmdlet name case-insensitively, so a case-sensitive guard over
# PowerShell text grades typography and not behaviour.
#
# It lives HERE, above the import, because the source gate needs it. Everything
# further down in this file uses this same object.
_MUTATING_VERB_RE = re.compile(
    r"\b(?:Set|Remove|New|Start|Stop|Register|Unregister|Enable|Disable|Add|Clear|Out|Write|"
    r"Move|Rename|Invoke|Restart|Suspend|Resume|Export|Import|Copy)-[A-Za-z][A-Za-z0-9]*\b",
    re.IGNORECASE,
)

# Native Windows mutators that carry NO hyphen, so the Verb-Noun shape above
# cannot see them. Deliberately NARROW: every token here was measured to occur
# zero times in ops/check_task_liveness.py on 2026-09-08, because this set is
# applied to PYTHON source where `set`, `start`, `move` and `copy` are ordinary
# words. The wide alias list lives in _KNOWN_MUTATOR_TOKENS below and is applied
# only to PowerShell text, where those words are commands.
_NATIVE_MUTATOR_EXES = ("taskkill", "schtasks", "wmic", "rundll32", "bitsadmin", "certutil")

# Calls the subject is allowed to make WHILE IT IS BEING IMPORTED. A module-level
# statement runs at import; so does a class body, a decorator expression and a
# default argument. A function BODY does not, and neither does the block under
# `if __name__ == "__main__":`. Everything that DOES run may call only these
# three, each of which builds a value and touches nothing outside the process.
#
# This is a STRUCTURAL rule and not a denylist, which is the point. The kill was
# `_diag.remove(...)`; so is `_x = os.unlink(...)`, so is a decorator that
# writes a file, and none of them is spelled like anything anybody enumerated.
_SANCTIONED_IMPORT_TIME_CALLS = frozenset({"re.compile", "dataclass", "field"})

# The only attributes of `subprocess` the subject may name, measured 2026-09-08:
# it uses subprocess.run and subprocess.TimeoutExpired and nothing else.
# CalledProcessError and SubprocessError are allowed ahead of use because they
# are exception types and cannot launch anything.
#
# Popen, __name__, __spec__ and __file__ are absent for a REASON. Naming one is
# how a module tells a test harness apart from production: the derivation below
# must replace subprocess.run, and a module that asks whether Popen is there, or
# what the module's __name__ is, is asking whether it is being watched.
_SANCTIONED_SUBPROCESS_ATTRS = frozenset(
    {"run", "TimeoutExpired", "SubprocessError", "CalledProcessError"}
)

# Attribute names that read the AMBIENT WORLD rather than the arguments. Each is
# a channel a module can branch on to behave one way under a harness and another
# way in real use. `argv` is here because `sys.argv[0].endswith('pytest')` is the
# cheapest such test there is, and the subject's main() takes argv as a
# parameter, so it has no need of it.
_OBSERVATION_ATTRS = frozenset(
    {"modules", "environ", "getenv", "isatty", "gettrace", "_getframe", "flags", "argv"}
)

# Calls that reach the interpreter's own bookkeeping. hasattr and getattr are
# the two the first kill used - `if hasattr(subprocess, 'Popen'):` - and the
# rest reach the same information by other routes.
_OBSERVATION_CALLS = frozenset(
    {
        "hasattr", "getattr", "vars", "globals", "locals", "eval", "exec",
        "__import__", "importlib.import_module", "sys._getframe", "sys.gettrace",
    }
)

# Names that ARE the ambient world, with no attribute access to give them away.
_OBSERVATION_NAMES = frozenset({"__debug__"})


def _dotted_name(node: ast.AST) -> str:
    """The dotted text of a Name/Attribute chain, or '' for anything else."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _is_main_guard(node: ast.AST) -> bool:
    """True for `if __name__ == "__main__":`, whose body never runs on import."""
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    return (
        isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _import_time_nodes(node: ast.AST) -> typing.Iterator[ast.AST]:
    """Every node the subject EXECUTES on import, and none that it does not.

    A function body is skipped because it does not run at import. Its
    decorators, its default arguments and its return annotation DO run, so they
    are walked in full. A class body is walked in full for the same reason: the
    `field(default_factory=list)` in a dataclass is evaluated at import.
    """
    for child in ast.iter_child_nodes(node):
        if _is_main_guard(child):
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            heads: list[ast.AST] = list(getattr(child, "decorator_list", []))
            args = getattr(child, "args", None)
            if args is not None:
                heads.extend(d for d in args.defaults if d is not None)
                heads.extend(d for d in args.kw_defaults if d is not None)
            returns = getattr(child, "returns", None)
            if returns is not None:
                heads.append(returns)
            for head in heads:
                yield head
                yield from ast.walk(head)
            continue
        yield child
        yield from _import_time_nodes(child)


def _import_time_call_findings(tree: ast.AST) -> list[str]:
    """Calls the subject would make simply by being imported."""
    out = []
    for node in _import_time_nodes(tree):
        if isinstance(node, ast.Call):
            name = _dotted_name(node.func) or "<a computed callee>"
            if name not in _SANCTIONED_IMPORT_TIME_CALLS:
                out.append(f"line {node.lineno}: the module CALLS {name}() while being imported")
    return out


def _subprocess_aliases(tree: ast.AST) -> set[str]:
    """Every local name bound to the subprocess MODULE by an import.

    `import subprocess as sp` launders every rule below that keys on the
    spelling `subprocess`, so the rules key on this set instead.
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" or alias.name.startswith("subprocess."):
                    names.add(alias.asname or alias.name.split(".", 1)[0])
    return names


def _observation_findings(tree: ast.AST) -> list[str]:
    """Every place the subject could ask whether it is being watched.

    A PROBE THAT BEHAVES DIFFERENTLY WHEN OBSERVED IS THE DEFECT, independently
    of what it then does, so this refuses the QUESTION and never tries to judge
    the answer. There is no way to make a harness that neuters subprocess.run
    indistinguishable from one that does not, so the only closable version of
    this is a refusal to ask.
    """
    out = []
    aliases = _subprocess_aliases(tree)
    attribute_bases = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    call_funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "subprocess":
            out.append(
                f"line {node.lineno}: `from subprocess import ...` binds a launcher under a name no "
                "rule here can follow. The module must use `import subprocess`."
            )
        elif isinstance(node, ast.Name):
            if node.id in _OBSERVATION_NAMES:
                out.append(f"line {node.lineno}: the module reads {node.id}")
            elif node.id in aliases and id(node) not in attribute_bases:
                out.append(
                    f"line {node.lineno}: the module names the subprocess MODULE ITSELF, which is "
                    "how a branch on its identity is written"
                )
        elif isinstance(node, ast.Attribute):
            if node.attr in _OBSERVATION_ATTRS:
                out.append(
                    f"line {node.lineno}: the module reads .{node.attr}, which is ambient state "
                    "and not an argument"
                )
            if _dotted_name(node.value) in aliases:
                if node.attr not in _SANCTIONED_SUBPROCESS_ATTRS:
                    out.append(
                        f"line {node.lineno}: the module names subprocess.{node.attr}, which is not "
                        "one of the four attributes it needs and is a way to detect a harness"
                    )
                elif node.attr == "run" and id(node) not in call_funcs:
                    # `_REAL_RUN = subprocess.run` at import, then
                    # `if subprocess.run is _REAL_RUN:` later. Both halves name
                    # only a sanctioned attribute, so nothing above can see it.
                    out.append(
                        f"line {node.lineno}: the module names subprocess.run WITHOUT CALLING IT, "
                        "which is how the real launcher is stashed for a later identity comparison"
                    )
        elif isinstance(node, ast.Compare):
            for operand in [node.left] + list(node.comparators):
                if _dotted_name(operand).split(".")[0] in aliases:
                    out.append(
                        f"line {node.lineno}: the module COMPARES against "
                        f"{_dotted_name(operand)}, which is a branch on whether subprocess is the "
                        "one production uses"
                    )
        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name in _OBSERVATION_CALLS or name.endswith(".import_module"):
                out.append(f"line {node.lineno}: the module calls {name}(), which inspects the runtime")
    return sorted(out)


def _mutating_verbs_in_source(text: str) -> list[str]:
    """The whole-file PowerShell scan, run over the subject's bytes."""
    out = [f"the mutating cmdlet {v}" for v in sorted(set(_MUTATING_VERB_RE.findall(text)))]
    lowered = text.lower()
    out.extend(
        f"the native mutator {token}"
        for token in ("stop-process",) + _NATIVE_MUTATOR_EXES
        if token in lowered
    )
    return out


def _source_gate_findings(text: str, tree: ast.AST) -> list[str]:
    """Every grade this file can apply to the subject WITHOUT importing it."""
    return (
        _mutating_verbs_in_source(text)
        + _import_time_call_findings(tree)
        + _observation_findings(tree)
    )


if not _SUBJECT_PATH.is_file():
    raise RuntimeError(
        f"the subject this file grades is not at {_SUBJECT_PATH}. Refusing to import rather than "
        "grading nothing and reporting a pass - zero out of zero reads as green."
    )
_SUBJECT_SOURCE = _SUBJECT_PATH.read_text(encoding="ascii")
_SUBJECT_TREE = ast.parse(_SUBJECT_SOURCE)
_SOURCE_GATE_FINDINGS = _source_gate_findings(_SUBJECT_SOURCE, _SUBJECT_TREE)
if _SOURCE_GATE_FINDINGS:
    raise RuntimeError(
        f"{_SUBJECT_PATH} fails the source grade, so it is NOT being imported: "
        f"{_SOURCE_GATE_FINDINGS}. Raising here rather than in an arm, because an arm runs AFTER "
        "the import and an import runs the subject's module-level code - by then a module-level "
        "side effect has already happened."
    )

from ops import check_task_liveness as liveness  # noqa: E402

# --- Fixtures, every one of them CAPTURED FROM THE PROBE -------------------
#
# These three are verbatim `python -c "collect_facts(...)"` output taken on
# 2026-09-08 on this machine. Do not "tidy" them: State Ready beside an
# expired EndBoundary and an empty NextRunTime IS the first finding, and State
# Ready beside an absent EndBoundary on a two-month-old one-shot IS the second.

MEASURED_DORMANT = {
    "exists": True,
    "ambiguous": False,
    "task_name": "ResinCompute-Responder",
    "task_path": "\\",
    "state": "Ready",
    "next_run_time": None,
    "last_run_time": "2026-09-07T20:55:55-05:00",
    "last_task_result": 0,
    "triggers": [
        {
            "kind": "MSFT_TaskTimeTrigger",
            "enabled": True,
            "start_boundary": "2026-09-07T19:00:00",
            "end_boundary": "2026-09-07T21:00:00",
            "repetition_interval": "PT5M",
            "repetition_duration": "PT2H",
        }
    ],
}

# The FALSE LIVE. No EndBoundary at all, and spent regardless.
MEASURED_SPENT_ONE_SHOT = {
    "exists": True,
    "ambiguous": False,
    "task_name": "RunPlatformExperienceHelper_Metrics",
    "task_path": "\\GoogleUserPEH\\",
    "state": "Ready",
    "next_run_time": None,
    "last_run_time": "2026-07-08T19:37:37-05:00",
    "last_task_result": 0,
    "triggers": [
        {
            "kind": "MSFT_TaskTimeTrigger",
            "enabled": True,
            "start_boundary": "2026-07-08T19:37:35-05:00",
            "end_boundary": "",
            "repetition_interval": "",
            "repetition_duration": "",
        }
    ],
}

# The LIVE POSITIVE CONTROL, and the regression guard on the whole repair: a
# task that genuinely does still fire must not be swept up by the new rule.
MEASURED_LIVE_WATCHDOG = {
    "exists": True,
    "ambiguous": False,
    "task_name": "LW-CIWatchdog",
    "task_path": "\\",
    "state": "Ready",
    "next_run_time": "2026-09-08T16:46:46-05:00",
    "last_run_time": "2026-09-08T16:44:44-05:00",
    "last_task_result": 0,
    "triggers": [
        {
            "kind": "MSFT_TaskBootTrigger",
            "enabled": True,
            "start_boundary": "",
            "end_boundary": "",
            "repetition_interval": "",
            "repetition_duration": "",
        },
        {
            "kind": "MSFT_TaskTimeTrigger",
            "enabled": True,
            "start_boundary": "2026-08-16T21:52:27",
            "end_boundary": "",
            "repetition_interval": "PT2M",
            "repetition_duration": "",
        },
    ],
}

MEASURED_AMBIGUOUS = {
    "exists": True,
    "ambiguous": True,
    "task_name": "Backup",
    "matches": ["\\Microsoft\\Windows\\AppListBackup\\", "\\Microsoft\\Windows\\CloudRestore\\"],
}

# NOW is fixed so every arm below is deterministic. It sits AFTER the measured
# EndBoundary of the responder, which is what makes that trigger expired, and
# BEFORE the watchdog's NextRunTime, which is what keeps that one live.
NOW = dt.datetime(2026, 9, 8, 10, 0, 0)


def _payload(base=None, **overrides):
    """A copy of a measured payload with named fields replaced."""
    base = MEASURED_DORMANT if base is None else base
    out = dict(base)
    triggers = [dict(t) for t in base.get("triggers", [])]
    for key, value in overrides.items():
        if key.startswith("trigger_"):
            for trig in triggers:
                trig[key[len("trigger_") :]] = value
        else:
            out[key] = value
    if "triggers" not in overrides:
        out["triggers"] = triggers
    return out


def _verdict(payload, now=NOW):
    return liveness.verdict(liveness.parse_facts(payload), now=now)


# --- FINDING ONE: an expired EndBoundary, and its positive control ---------


def test_expired_end_boundary_is_dormant_despite_a_ready_state():
    result = _verdict(MEASURED_DORMANT)
    assert result.status == "DORMANT"
    # State is REPORTED, never used as the verdict.
    assert result.state == "Ready"


def test_positive_control_a_future_end_boundary_is_live_on_the_same_path():
    # ONE field differs from the arm above: the trigger's EndBoundary. Same
    # parse, same verdict function, same fixed NOW.
    result = _verdict(_payload(trigger_end_boundary="2026-09-09T21:00:00"))
    assert result.status == "LIVE"
    assert result.state == "Ready"


def test_an_end_boundary_exactly_equal_to_now_is_expired_not_live():
    # The BOUNDARY of the boundary check. `end <= now` and `end < now` differ
    # only here, and without this arm a mutant flipping the operator survives.
    result = _verdict(_payload(trigger_end_boundary=NOW.isoformat()))
    assert result.status == "DORMANT"


def test_positive_control_one_second_past_now_is_live():
    one_second_later = (NOW + dt.timedelta(seconds=1)).isoformat()
    result = _verdict(_payload(trigger_end_boundary=one_second_later))
    assert result.status == "LIVE"


# --- FINDING TWO: an ABSENT EndBoundary is not evidence of anything --------


def test_a_spent_one_shot_with_no_end_boundary_is_dormant_not_live():
    # The measured RunPlatformExperienceHelper_Metrics payload. Enabled
    # trigger, no EndBoundary, StartBoundary two months past, no repetition.
    # The refuted version of this module called this LIVE.
    result = _verdict(MEASURED_SPENT_ONE_SHOT)
    assert result.status == "DORMANT", "a fired one-shot with no EndBoundary must not read LIVE"
    assert result.live_trigger_indexes == []
    assert any("SPENT" in reason for reason in result.reasons)


def test_positive_control_the_same_one_shot_with_a_repetition_interval_is_live():
    # ONE field differs: the trigger now repeats. It therefore does fire again.
    result = _verdict(_payload(MEASURED_SPENT_ONE_SHOT, trigger_repetition_interval="PT5M"))
    assert result.status == "LIVE"


def test_positive_control_the_same_one_shot_with_a_future_start_is_live():
    # ONE field differs: the StartBoundary has not arrived. It has not fired.
    result = _verdict(_payload(MEASURED_SPENT_ONE_SHOT, trigger_start_boundary="2026-12-01T09:00:00"))
    assert result.status == "LIVE"


def test_a_boot_trigger_with_no_boundaries_at_all_is_live():
    # No StartBoundary and no EndBoundary is a DIFFERENT shape from a spent
    # one-shot: it fires on every boot. Sweeping it into DORMANT would be the
    # same error pointed the other way.
    boot_only = _payload(MEASURED_LIVE_WATCHDOG, next_run_time=None, triggers=[
        dict(MEASURED_LIVE_WATCHDOG["triggers"][0])
    ])
    result = _verdict(boot_only)
    assert result.status == "LIVE"


def test_an_elapsed_repetition_window_with_no_end_boundary_is_dormant():
    # StartBoundary + Duration is already past and StopAtDurationEnd applies,
    # so the repetition has stopped even though no EndBoundary says so.
    payload = _payload(
        MEASURED_SPENT_ONE_SHOT,
        trigger_start_boundary="2026-09-08T06:00:00",
        trigger_repetition_interval="PT5M",
        trigger_repetition_duration="PT2H",
    )
    result = _verdict(payload)
    assert result.status == "DORMANT"
    assert any("CLOSED" in reason for reason in result.reasons)


def test_positive_control_a_repetition_window_still_open_is_live():
    # ONE field differs from the arm above: the duration reaches past NOW.
    payload = _payload(
        MEASURED_SPENT_ONE_SHOT,
        trigger_start_boundary="2026-09-08T06:00:00",
        trigger_repetition_interval="PT5M",
        trigger_repetition_duration="PT8H",
    )
    result = _verdict(payload)
    assert result.status == "LIVE"


def test_a_repetition_window_that_closes_exactly_at_now_is_spent_not_live():
    # The BOUNDARY of the repetition window, and the exact counterpart of
    # test_an_end_boundary_exactly_equal_to_now_is_expired_not_live. `closes <=
    # now` and `closes < now` differ ONLY here: with StartBoundary 06:00 and a
    # PT4H duration the window closes at 10:00:00, which is NOW to the second.
    # Without this arm the operator flip survives, and the two boundaries in
    # this module are graded asymmetrically.
    payload = _payload(
        MEASURED_SPENT_ONE_SHOT,
        trigger_start_boundary="2026-09-08T06:00:00",
        trigger_repetition_interval="PT5M",
        trigger_repetition_duration="PT4H",
    )
    result = _verdict(payload)
    assert result.status == "DORMANT", "a repetition window closing exactly at now has closed"
    assert result.live_trigger_indexes == []
    assert any("CLOSED" in reason for reason in result.reasons)


def test_positive_control_a_repetition_window_closing_one_second_from_now_is_live():
    # ONE second differs from the arm above, through the same code path.
    payload = _payload(
        MEASURED_SPENT_ONE_SHOT,
        trigger_start_boundary="2026-09-08T06:00:00",
        trigger_repetition_interval="PT5M",
        trigger_repetition_duration="PT4H1S",
    )
    result = _verdict(payload)
    assert result.status == "LIVE"


def test_the_live_watchdog_stays_live_and_is_the_regression_guard():
    # The whole repair is worthless if it turns a task that DOES fire into
    # DORMANT. This is the measured payload of a task ticking every 2 minutes.
    result = _verdict(MEASURED_LIVE_WATCHDOG)
    assert result.status == "LIVE"
    # Both of its triggers must read live in their own right, so the verdict
    # does not rest on NextRunTime alone.
    assert result.live_trigger_indexes == [0, 1]


def test_the_watchdog_is_still_live_with_its_next_run_time_stripped():
    # Rule 1 removed, so only the trigger reading can carry it.
    result = _verdict(_payload(MEASURED_LIVE_WATCHDOG, next_run_time=None))
    assert result.status == "LIVE"


# --- FINDING THREE: an UNREADABLE boundary must never read LIVE ------------


def test_a_malformed_end_boundary_is_never_live():
    result = _verdict(_payload(trigger_end_boundary="07/08/2026 7:37:35 PM"))
    assert result.status != "LIVE", "an unparseable EndBoundary must not fail open to LIVE"
    assert result.status == "UNKNOWN", "and it is not knowably DORMANT either"
    assert result.live_trigger_indexes == []
    assert any("UNREADABLE" in reason for reason in result.reasons)


def test_positive_control_the_same_instant_written_readably_is_dormant():
    # ONE thing differs: the same past instant in a format that parses. This
    # proves the arm above turns on the MALFORMEDNESS and not on the date.
    result = _verdict(_payload(trigger_end_boundary="2026-07-08T19:37:35"))
    assert result.status == "DORMANT"


def test_a_malformed_boundary_does_not_veto_independent_positive_evidence():
    # A future NextRunTime still carries the task. The unreadable trigger is
    # reported as a caveat rather than allowed to erase the scheduler's own
    # commitment.
    result = _verdict(
        _payload(trigger_end_boundary="not a date at all", next_run_time="2026-09-08T10:05:00-05:00")
    )
    assert result.status == "LIVE"
    assert any("could not be read" in caveat for caveat in result.caveats)


def test_a_malformed_start_boundary_with_no_end_boundary_is_unknown():
    result = _verdict(_payload(MEASURED_SPENT_ONE_SHOT, trigger_start_boundary="whenever"))
    assert result.status == "UNKNOWN"


def test_a_malformed_repetition_interval_is_unknown_not_live():
    result = _verdict(_payload(MEASURED_SPENT_ONE_SHOT, trigger_repetition_interval="every 5 min"))
    assert result.status == "UNKNOWN"


def test_the_duration_parser_reads_the_shapes_the_scheduler_writes():
    assert liveness._parse_duration("PT5M") == dt.timedelta(minutes=5)
    assert liveness._parse_duration("PT2H") == dt.timedelta(hours=2)
    assert liveness._parse_duration("P1DT12H30M") == dt.timedelta(days=1, hours=12, minutes=30)


def test_the_duration_parser_refuses_rather_than_guesses():
    # Each of these must be None, so the caller fails CLOSED. P1W is the one
    # that matters: guessing at weeks would be a silent seven-fold error.
    for bad in ("", "P", "PT", "P1W", "5 minutes", "PT", "T5M", "P1M"):
        assert liveness._parse_duration(bad) is None, f"{bad!r} must not parse"


# --- Absent is a THIRD outcome, not a flavour of dead ----------------------


def test_a_task_that_does_not_exist_is_absent_and_not_dormant():
    result = _verdict({"exists": False, "task_name": "ResinCompute-Nonesuch"})
    assert result.status == "ABSENT"
    assert result.status != "DORMANT"


def test_positive_control_the_same_name_present_is_not_absent():
    result = _verdict(MEASURED_DORMANT)
    assert result.status != "ABSENT"


# --- A DUPLICATED NAME is answered as AMBIGUOUS, never silently picked -----


def test_a_name_registered_under_two_task_paths_is_ambiguous():
    # Measured: 'Backup' exists under both \Microsoft\Windows\AppListBackup\
    # and \Microsoft\Windows\CloudRestore\ on this machine.
    result = _verdict(MEASURED_AMBIGUOUS)
    assert result.status == "AMBIGUOUS"
    assert result.status not in ("LIVE", "DORMANT"), "a silent pick between two tasks is not an answer"
    text = liveness.render(result)
    assert "\\Microsoft\\Windows\\AppListBackup\\" in text
    assert "\\Microsoft\\Windows\\CloudRestore\\" in text


def test_positive_control_a_single_match_of_the_same_shape_is_answered():
    result = _verdict(_payload(MEASURED_DORMANT, task_name="Backup"))
    assert result.status == "DORMANT"
    assert result.status != "AMBIGUOUS"


def test_main_gives_ambiguity_its_own_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(liveness, "collect_facts", lambda *a, **k: MEASURED_AMBIGUOUS)
    code = liveness.main(["Backup"])
    assert "AMBIGUOUS" in capsys.readouterr().out
    assert code == liveness.EXIT_AMBIGUOUS
    assert code not in (liveness.EXIT_LIVE, liveness.EXIT_DORMANT, liveness.EXIT_ABSENT)


def test_a_disabled_duplicate_cannot_be_rendered_into_a_ready_string():
    # The root cause of the ambiguity finding: PowerShell renders an ARRAY of
    # states as 'Disabled Ready', which a lowercase == "disabled" veto misses.
    # The parser must never see that shape, but if it ever did, the veto must
    # not be fooled into LIVE by the concatenation.
    result = _verdict(_payload(state="Disabled Ready", trigger_end_boundary="2026-09-09T21:00:00"))
    assert result.status != "LIVE", "a concatenated state string must not defeat the Disabled veto"


# --- The State string may VETO, never VOUCH -------------------------------


def test_a_ready_state_with_no_triggers_at_all_is_dormant():
    # Nothing positive to rest on. A verdict function that trusted State would
    # call this LIVE.
    result = _verdict(_payload(triggers=[]))
    assert result.status == "DORMANT"


def test_a_disabled_trigger_is_not_evidence_even_with_a_future_boundary():
    result = _verdict(_payload(trigger_end_boundary="2026-09-09T21:00:00", trigger_enabled=False))
    assert result.status == "DORMANT"


def test_a_disabled_task_state_vetoes_an_otherwise_live_trigger():
    # State is allowed to take LIVE away. It is never allowed to grant it.
    result = _verdict(_payload(state="Disabled", trigger_end_boundary="2026-09-09T21:00:00"))
    assert result.status == "DORMANT"


def test_positive_control_the_identical_fixture_at_ready_is_live():
    result = _verdict(_payload(state="Ready", trigger_end_boundary="2026-09-09T21:00:00"))
    assert result.status == "LIVE"


# --- NextRunTime as evidence, and only when it is in the FUTURE -----------


def test_a_future_next_run_time_is_positive_evidence_on_its_own():
    result = _verdict(_payload(next_run_time="2026-09-08T10:05:00-05:00", triggers=[]))
    assert result.status == "LIVE"
    assert any("NextRunTime" in reason for reason in result.reasons)


def test_a_past_next_run_time_is_not_evidence():
    result = _verdict(_payload(next_run_time="2026-09-07T20:55:00-05:00", triggers=[]))
    assert result.status == "DORMANT"


# --- The report must carry the EVIDENCE, not just the word ----------------


def test_the_rendered_report_names_the_trigger_and_every_boundary():
    text = liveness.render(_verdict(MEASURED_DORMANT))
    assert "DORMANT" in text
    assert "2026-09-07T19:00:00" in text, "the StartBoundary must be shown"
    assert "2026-09-07T21:00:00" in text, "the expired EndBoundary must be shown"
    assert "MSFT_TaskTimeTrigger" in text, "the trigger must be identified"
    assert "2026-09-07T20:55:55" in text, "LastRunTime must be shown"
    assert "NextRunTime" in text
    assert "Ready" in text, "State must be REPORTED even though it is not the verdict"
    assert "PT5M" in text, "the repetition interval is now load-bearing, so it must be shown"
    assert "PT2H" in text, "so is the repetition duration"


def test_the_rendered_report_shows_the_task_path_it_actually_answered_about():
    text = liveness.render(_verdict(MEASURED_SPENT_ONE_SHOT))
    assert "\\GoogleUserPEH\\" in text, "a task outside the root path must say which path it was found in"


def test_the_rendered_report_is_seven_bit_ascii():
    for fixture in (MEASURED_DORMANT, MEASURED_SPENT_ONE_SHOT, MEASURED_LIVE_WATCHDOG, MEASURED_AMBIGUOUS):
        liveness.render(_verdict(fixture)).encode("ascii")


# --- main() routes through the verdict function, and exits on it ----------


def test_main_routes_through_the_verdict_function_and_exits_nonzero_on_dormant(monkeypatch, capsys):
    seen = {}

    def fake_collect(task_name, timeout=None, task_path=""):
        seen["task_name"] = task_name
        return MEASURED_DORMANT

    monkeypatch.setattr(liveness, "collect_facts", fake_collect)
    code = liveness.main(["ResinCompute-Responder"])
    out = capsys.readouterr().out

    assert seen["task_name"] == "ResinCompute-Responder", "main must probe the name it was given"
    assert "DORMANT" in out, "main must print the VERDICT, not the State string"
    assert code == liveness.EXIT_DORMANT
    assert code != 0


def test_positive_control_main_exits_zero_when_the_same_path_finds_it_live(monkeypatch, capsys):
    live_payload = _payload(trigger_end_boundary="2026-09-09T21:00:00")
    monkeypatch.setattr(liveness, "collect_facts", lambda *a, **k: live_payload)
    code = liveness.main(["ResinCompute-Responder"])
    out = capsys.readouterr().out
    assert "LIVE" in out
    assert code == liveness.EXIT_LIVE == 0


def test_main_exits_dormant_on_the_spent_one_shot(monkeypatch, capsys):
    monkeypatch.setattr(liveness, "collect_facts", lambda *a, **k: MEASURED_SPENT_ONE_SHOT)
    code = liveness.main(["RunPlatformExperienceHelper_Metrics"])
    assert "DORMANT" in capsys.readouterr().out
    assert code == liveness.EXIT_DORMANT


def test_main_gives_absent_its_own_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(liveness, "collect_facts", lambda *a, **k: {"exists": False})
    code = liveness.main(["ResinCompute-Nonesuch"])
    out = capsys.readouterr().out
    assert "ABSENT" in out
    assert code == liveness.EXIT_ABSENT
    assert code != liveness.EXIT_DORMANT


# --- No raw error string reaches the operator's surface -------------------


def test_a_probe_failure_degrades_friendly_and_leaks_no_raw_error(monkeypatch, capsys):
    raw = "Get-ScheduledTask : Traceback 0x80070005 ACCESS_DENIED at line 1 char 1"

    def exploding_collect(task_name, timeout=None, task_path=""):
        raise liveness.ProbeError("could not read the scheduler", raw)

    monkeypatch.setattr(liveness, "collect_facts", exploding_collect)
    code = liveness.main(["ResinCompute-Responder"])
    captured = capsys.readouterr()

    assert code == liveness.EXIT_UNKNOWN
    assert "UNKNOWN" in captured.out
    assert raw not in captured.out, "the raw scheduler error must not reach stdout"
    assert "0x80070005" not in captured.out
    assert raw in captured.err, "the raw error must still be LOGGED so it is recoverable"


def test_positive_control_a_working_probe_prints_no_degraded_banner(monkeypatch, capsys):
    monkeypatch.setattr(liveness, "collect_facts", lambda *a, **k: MEASURED_DORMANT)
    liveness.main(["ResinCompute-Responder"])
    assert "UNKNOWN" not in capsys.readouterr().out


# --- The tool is READ ONLY ------------------------------------------------


# A DENYLIST PINS TOKENS, NOT INTENT, and the first version of this section was
# exactly that: a list of seven literal strings. A mutation sweep on 2026-09-08
# prepended
#
#     Remove-Item -Path 'ZZ-no-such-path-9f6839e' -ErrorAction SilentlyContinue
#
# to the probe and the whole suite stayed green, because Remove-Item was not one
# of the seven. Nor were Set-Content, Out-File, New-Item, Enable-ScheduledTask
# or - despite the arm's own name saying "never stops anything" -
# Stop-ScheduledTask. Extending the list by six would only move the hole.
#
# So the scan is INVERTED. The probe text is the only thing this module ever
# hands to PowerShell, and every command-shaped token in it must be one of a
# named, sanctioned, read-only set. An unfamiliar cmdlet fails whether or not
# anybody thought to ban it, which is the difference between grading intent and
# grading a token list.

# The five cmdlets the probe is allowed to be built from. Adding to this set is
# a deliberate act, and the verb check below constrains what may be added.
_SANCTIONED_PROBE_CMDLETS = frozenset(
    {
        "Get-ScheduledTask",
        "Get-ScheduledTaskInfo",
        "ConvertTo-Json",
        "Where-Object",
        "ForEach-Object",
    }
)

# PowerShell verbs that only READ. Get and Select and their kin cannot change
# the scheduler; Set, Remove, Register, Start, Stop, Enable, Disable, New, Out
# and Write can, and none of them may appear in the set above.
_READ_ONLY_PS_VERBS = frozenset(
    {"get", "convertto", "where", "foreach", "select", "measure", "sort", "compare"}
)

# _MUTATING_VERB_RE and _NATIVE_MUTATOR_EXES USED TO BE DEFINED HERE. They now
# live above the `from ops import check_task_liveness` line, because the source
# gate that runs BEFORE that import needs them. Moving them was not cosmetic: a
# second copy down here would be a second thing to keep in step, and the two
# copies would drift the first time one of them was widened.

# --- THE PROBE SCAN, AND WHY IT IS NO LONGER A VERB-NOUN SHAPE ------------
#
# The version this replaces matched `[A-Za-z]+-[A-Za-z]+` and nothing else, and
# the comment beside it said "case-insensitive because PowerShell is". Both
# halves were wrong. POWERSHELL ALIASES CARRY NO HYPHEN. Measured 2026-09-08, an
# adversary prepended
#
#     ri 'ZZ-canary'
#
# to the probe template. `ri` IS Remove-Item. The probe RAN, the canary file was
# DELETED FROM DISK, and every arm in this file reported green at exit 0,
# because `ri` is not Verb-Noun. `del`, `rm`, `sc`, `kill`, `ni`, `cmd /c`, a
# verb assembled by string concatenation and a bare `.Delete()` method call all
# survived the same net.
#
# So the scan no longer asks "does this token look like a command". It asks
# WHAT SITS IN EXECUTABLE POSITION - the start of a statement, or just after a
# newline, `;`, `|`, `&`, a brace, a paren, `=` or a comma - and requires every
# such token to be sanctioned. A bareword nobody enumerated is caught because it
# is a bareword in command position, which is what PowerShell will execute,
# whether or not anybody thought to ban that particular spelling.

# PowerShell language keywords. These sit in executable position and are not
# commands, so they are exempt. Everything else in that position is a command.
_PS_KEYWORDS = frozenset(
    {
        "if", "else", "elseif", "foreach", "for", "while", "do", "switch",
        "try", "catch", "finally", "return", "exit", "break", "continue",
        "param", "function", "begin", "process", "end", "in", "throw", "data",
        "filter", "workflow", "class", "enum", "using",
    }
)

# Statement separators. A bareword after any of these is about to be EXECUTED.
# `=` is in the set because the right-hand side of an assignment is a statement
# position too: without it `$i = Get-ScheduledTaskInfo ...` is invisible, and so
# would be `$x = Remove-Item ZZ`.
_EXECUTABLE_POSITION_RE = re.compile(
    r"(?:^|[\n;|&{}()=,])\s*([A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*)",
    re.MULTILINE,
)

# A method call that CHANGES something, which no Verb-Noun scan can see because
# there is no verb and no noun. `(Get-ScheduledTask -TaskName 'x').Delete()` is
# a read cmdlet followed by a destructive method. `.ToString(` is not here, and
# the probe legitimately uses it.
#
# `(?:\.|::)` and not `\.`, and that one character is the whole of the FIRST
# 2026-09-08 kill. A type accelerator calls a static method through `::` and
# never through `.`, so `[System.IO.File]::Delete('ZZ')` matched nothing here
# while `$t.Delete()` matched. Measured before the fix: the eight shapes in
# _STATIC_AND_REDIRECTION_INJECTIONS below were each spliced into the template
# immediately after the error-preference line and _unsanctioned_in,
# _bare_mutators_in, _mutating_constructs_in and _MUTATING_VERB_RE all returned
# empty for every one of them.
_MUTATING_METHOD_RE = re.compile(
    r"(?:\.|::)\s*(?:Delete|Remove|Stop|Kill|Start|Disable|Enable|Register|Unregister|"
    r"Save|SetValue|SetInfo|Create|Terminate|Move|Rename|Write|Put)\s*\(",
    re.IGNORECASE,
)

# THE SECOND HALF OF THAT KILL, and a denylist of method names could never have
# closed it: [System.IO.File]::AppendAllText and [System.IO.File]::WriteAllBytes
# are as destructive as ::Delete and neither is a mutating VERB. So the method
# scan is INVERTED the same way the cmdlet scan already was. Every method the
# probe calls must be named here, and a static `::` call is banned OUTRIGHT
# because the probe makes none: it uses `[string]`, `[bool]`, `[int]` and
# `[pscustomobject]` as CASTS, which carry no `::`.
#
# Why this rather than widening _EXECUTABLE_POSITION_RE to accept `[`. That
# regex requires `[A-Za-z_]` after a delimiter, so a bracketed type name is
# invisible to it - but adding `[` to the delimiter class would make `string`
# in `kind = [string]$tr.CimClass.CimClassName` read as a command in executable
# position and the pristine probe would fail its own scan. The bareword scan
# grades barewords; the shape scans below grade what is not a bareword.
_SANCTIONED_PROBE_METHODS = frozenset({"ToString"})
_METHOD_CALL_RE = re.compile(r"(?:\.|::)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_STATIC_CALL_RE = re.compile(r"::")

# REDIRECTION OVERWRITES A FILE AND CARRIES NO COMMAND TOKEN AT ALL. Measured
# 2026-09-08: `'x' > 'ZZ'` spliced into the template left every scan silent,
# because there is nothing in it for a command scan to read. The probe contains
# no `>` of any kind, so the character is banned outright once quoted literals
# have been blanked out.
_REDIRECTION_RE = re.compile(r">")


def _inert(script: str) -> str:
    """The script with quoted literals blanked - they are data, not syntax."""
    return re.sub(r'"[^"]*"', '""', re.sub(r"'[^']*'", "''", script))

# `& ('Remo' + 've-Item')` builds a verb at runtime, so no static name scan can
# ever see it. The call operator and string concatenation are therefore banned
# OUTRIGHT from the probe rather than inspected. The probe carries neither.
_CALL_OPERATOR_RE = re.compile(r"(?:^|[\n;|({])\s*&\s*[\(\"'$]", re.MULTILINE)
_CONCATENATION_RE = re.compile(r"['\"]\s*\+|\+\s*['\"]")


def _commands_in(script: str) -> set[str]:
    """Every bareword in EXECUTABLE position in a PowerShell script.

    Single-quoted literals are blanked first: they are inert data, and blanking
    them keeps the datetime format 'yyyy-MM-ddTHH:mm:sszzz' from reading as a
    command while leaving any injected command outside the quotes visible.

    A bareword immediately followed by `=` is an assignment target, not a
    command: that exemption is what keeps the hashtable keys the probe builds
    (`exists = $false`, `kind = [string]...`) from reading as commands. It is
    narrow - `del 'x'` and `Remove-Item -Path x` carry no `=` in that position.
    """
    inert = re.sub(r"'[^']*'", "''", script)
    found = set()
    for match in _EXECUTABLE_POSITION_RE.finditer(inert):
        token = match.group(1)
        if re.match(r"\s*=(?!=)", inert[match.end():]):
            continue
        if token.lower() in _PS_KEYWORDS:
            continue
        found.add(token)
    return found


def _mutating_constructs_in(script: str) -> list[str]:
    """Named DANGEROUS SHAPES that carry no command name for a scan to read."""
    seen = []
    if _MUTATING_METHOD_RE.search(script):
        seen.append("a mutating .Method() or ::Method() call")
    if _STATIC_CALL_RE.search(_inert(script)):
        seen.append("a :: static call on a type, which reaches the whole .NET surface")
    for method in sorted(set(_METHOD_CALL_RE.findall(script))):
        if method not in _SANCTIONED_PROBE_METHODS:
            seen.append(f"the unsanctioned method call .{method}()")
    if _REDIRECTION_RE.search(_inert(script)):
        seen.append("a > redirection, which overwrites a file and names no command")
    if _CALL_OPERATOR_RE.search(script):
        seen.append("the & call operator, which can invoke a name built at runtime")
    if _CONCATENATION_RE.search(script):
        seen.append("string concatenation, which can assemble a verb no scan can see")
    return seen


# The hyphenless spellings that reach the same cmdlets. CHOSEN, not invented:
# every entry is either a DEFAULT PowerShell 5.1 alias for a cmdlet whose verb
# already appears in _MUTATING_VERB_RE above, or a native Windows executable
# that changes state. So the set is derived from the mutating-verb list this
# file already committed to, mapped through the alias table, rather than being a
# second denylist with its own independent holes.
#
# It is NOT the allowlist. The allowlist is _SANCTIONED_PROBE_CMDLETS, and
# _commands_in catches a bareword whether or not it appears below. This set
# exists so the non-vacuity controls plant real weapons rather than made-up
# ones, and so a hit can be NAMED in a failure message.
_KNOWN_MUTATOR_TOKENS = frozenset(
    {
        # Remove-Item and friends
        "ri", "rm", "rmdir", "del", "erase", "rd", "rp", "rv", "rjb", "rni",
        # New-Item / Set-* / Add-* / Clear-*
        "ni", "md", "mkdir", "si", "sp", "sc", "ac", "clc", "cli", "sal", "nal", "sv",
        # Move / Rename / Copy
        "mi", "mv", "move", "ren", "cpi", "copy", "cp",
        # Process and service control
        "spps", "kill", "spsv", "saps", "sasv", "start",
        # Invocation, which can carry any of the above inside a string
        "iex", "icm", "irm", "iwr",
        # Output that writes to disk
        "oh", "echo", "write",
        # Native Windows mutators
        "cmd", "taskkill", "schtasks", "reg", "wmic", "rundll32", "net",
        "bitsadmin", "certutil", "powershell", "pwsh", "curl",
    }
)


def _bare_mutators_in(script: str) -> list[str]:
    """Known hyphenless mutators sitting in EXECUTABLE position in PowerShell text.

    Applied to PowerShell only. Running this token set over PYTHON source would
    false-positive at once: measured 2026-09-08, ops/check_task_liveness.py
    contains `ri`, `rd`, `start`, `set` and `powershell` as ordinary Python
    text. The whole-file scan therefore uses _NATIVE_MUTATOR_EXES, which was
    measured to occur zero times in that same file.
    """
    return sorted({t for t in _commands_in(script) if t.lower() in _KNOWN_MUTATOR_TOKENS})


_EVASIVE_INJECTIONS = (
    "ri 'ZZ-no-such-path-9f6839e'",
    "del ZZ",
    "rm ZZ",
    "sc -Path ZZ -Value x",
    "kill 1234",
    "ni ZZ -ItemType File",
    "cmd /c del ZZ",
    "$null = schtasks /delete /tn ZZ /f",
    "& ('Remo' + 've-Item') ZZ",
    "$s = 'Remove'; & ($s + '-Item') ZZ",
    "$t.Delete()",
    "(Get-ScheduledTask -TaskName 'ZZ').Delete()",
    "remove-item ZZ",
    "REMOVE-ITEM ZZ",
    "iex 'Remove-Item ZZ'",
    "$x = Remove-Item ZZ",
    "taskkill /F /PID 1",
)


# THE 2026-09-08 KILL CORPUS, every member of it MEASURED to walk through the
# version of this file that preceded this one, with a canary file really
# deleted from disk while the suite reported a pass at exit 0.
#
# SHAPE VARIATION IS THE POINT and is why the corpus looks like this. Rounds
# two and three of this guard were both defeated because the non-vacuity
# controls planted only the shape the matcher already handled - capitalised
# Verb-Noun, then hyphenless alias - so neither could discover that the matcher
# was narrow. Nothing below is Verb-Noun and nothing below is a bareword: six
# reach .NET through a type accelerator and `::`, which carries no command
# token, and two are bare redirection, which carries no token at all.
_STATIC_AND_REDIRECTION_INJECTIONS = (
    "[System.IO.File]::Delete('ZZ-no-such-path-9f6839e')",
    "[IO.Directory]::Delete('ZZ-no-such-dir-9f6839e')",
    "[System.IO.File]::WriteAllText('ZZ-no-such-path-9f6839e', 'x')",
    "[System.IO.File]::Move('ZZ-a-9f6839e', 'ZZ-b-9f6839e')",
    "[Diagnostics.Process]::Start('cmd.exe','/c del ZZ')",
    "[Microsoft.Win32.Registry]::SetValue('HKEY_CURRENT_USER\\ZZ', 'v', 1)",
    "'x' > 'ZZ-no-such-path-9f6839e'",
    "'x' >> 'ZZ-no-such-path-9f6839e'",
)


_SANCTIONED_LOWER = frozenset(n.lower() for n in _SANCTIONED_PROBE_CMDLETS)


def _unsanctioned_in(script: str) -> list[str]:
    """Everything in this script that is not one of the five sanctioned cmdlets.

    Membership is CASE-INSENSITIVE because PowerShell resolves cmdlet names
    that way: `get-scheduledtask` is the same read as `Get-ScheduledTask`, and
    `remove-item` is the same write as `Remove-Item`. Comparing case-sensitively
    grades typography.

    The dangerous SHAPES are folded in here too, so a caller cannot pass the
    name scan while carrying a `.Delete()` or a concatenated verb.
    """
    named = sorted(n for n in _commands_in(script) if n.lower() not in _SANCTIONED_LOWER)
    return named + _mutating_constructs_in(script)


def _findings_in(script: str) -> list[str]:
    """Every scan this file has, run over one piece of PowerShell text."""
    return (
        _unsanctioned_in(script)
        + _bare_mutators_in(script)
        + sorted(set(_MUTATING_VERB_RE.findall(script)))
    )


# --- A GUARD BOUND TO AN IDENTIFIER IS DEFEATED BY ADDING AN IDENTIFIER ----
#
# THE SECOND 2026-09-08 KILL. Every scan above was aimed at the NAME
# `liveness._PS_TEMPLATE`. Adding a module-level
#
#     _PS_EXTRA = "ri 'ZZ-canary' -ErrorAction SilentlyContinue"
#
# and assembling `script = _PS_EXTRA + _PS_TEMPLATE.format(...)` left every one
# of them looking at the wrong string: the template was pristine, the scans
# reported empty, the canary was deleted from disk and the suite exited 0. The
# whole-file half could not help either, because it grades PYTHON source with
# _NATIVE_MUTATOR_EXES, a six-entry tuple that does not contain `ri` and cannot
# be widened to contain it without false-positiving on the module's own text.
#
# So the text under test is DERIVED FROM THE MODULE'S BEHAVIOUR instead of
# named. collect_facts is run with subprocess replaced by a shim, and whatever
# it hands to `-Command` is what gets graded - assembled from one constant, two
# constants, an f-string or a runtime concatenation, it makes no difference.
#
# AND IT RUNS AT IMPORT, WHICH IS THE DIFFERENCE BETWEEN DETECTION AND
# PREVENTION. Both kills were caught after the fact by other arms - a second
# subprocess.run by the spy count, an alias that threw by ProbeError - and in
# both cases the canary had already died, because the destructive call was made
# by the real-probe arms at the bottom of this file and a failing arm at the
# top does not stop them. A raise here is a COLLECTION error: no arm in this
# module runs, so no PowerShell is launched at all.
#
# THE HARNESS ITSELF WAS THE FOURTH KILL, and it is why this looks the way it
# does. The version this replaces shimmed liveness.subprocess with a hand-rolled
# class defining exactly three names - TimeoutExpired, SubprocessError and run.
# It had NO Popen. Measured 2026-09-08, a branch on precisely that divergence,
# planted in collect_facts right after the template format,
#
#     if hasattr(subprocess, 'Popen'):
#         script = script + "\nri '<canary>' ... \nexit 0\n"
#
# built the pristine text under the shim and the armed text in production. The
# equality check passed, every scan passed, the suite reported all arms green at
# exit 0, and the canary file was deleted from disk by the real-probe arms.
#
# So the harness no longer BUILDS a stand-in for the subprocess module. It uses
# THE REAL MODULE and replaces only the entry points that can start a process.
# liveness.subprocess is therefore the identical object it is in production,
# with the identical type, __name__, __spec__, __file__, exception classes,
# DEVNULL and PIPE constants and every attribute stdlib adds in future - because
# it IS that object, not a list of three attributes somebody remembered.
#
# Popen is replaced by a SUBCLASS of the real Popen rather than by a function,
# so `isinstance(subprocess.Popen, type)` and `issubclass(..., Popen)` answer
# the same as they do in production.
#
# ONE DIVERGENCE REMAINS AND CANNOT BE REMOVED: subprocess.run is not the real
# subprocess.run while the derivation is in flight. A module that stashed the
# real one at import and compared later would still tell the difference. That is
# THE CEILING in the module docstring, and it is closed by the SOURCE GATE at
# the top of this file - which refuses any reference to subprocess beyond the
# four attributes the subject needs - and not by anything here.


class _DerivationLaunchAttempt(Exception):
    """A process-launching entry point other than run() was reached."""


def _powershell_text_reaching_argv() -> str:
    """The -Command payload collect_facts builds UNDER THIS HARNESS.

    Not "what actually reaches PowerShell" - see THE CEILING. Under an
    adversarial subject those are different strings, and the source gate rather
    than this function is what refuses that subject.

    No process is launched: every launching entry point on the real subprocess
    module is replaced for the duration and restored in a finally.
    """
    captured: dict[str, list[str]] = {}

    if liveness.subprocess is not subprocess or subprocess is not sys.modules["subprocess"]:
        raise AssertionError(
            "ops/check_task_liveness.py is not bound to the real stdlib subprocess module. "
            "Refusing to run the derivation: replacing entry points on the real module would "
            "not neuter whatever object the subject is actually holding, and calling "
            "collect_facts would launch it."
        )

    def _capturing_run(argv, **kwargs):
        captured["argv"] = list(argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"exists": False, "task_name": "ZZ"}), ""
        )

    def _refusing(name: str):
        def _launcher(argv=None, *rest, **kwargs):
            captured.setdefault("argv", list(argv) if argv else [])
            raise _DerivationLaunchAttempt(name)

        return _launcher

    class _RefusingPopen(subprocess.Popen):
        # Popen.__del__ returns immediately when this is false, which keeps an
        # "Exception ignored in __del__" off stderr for an object whose
        # __init__ deliberately never completed.
        _child_created = False

        def __init__(self, argv=None, *rest, **kwargs):
            captured.setdefault("argv", list(argv) if argv else [])
            raise _DerivationLaunchAttempt("subprocess.Popen")

    replacements: dict[str, object] = {
        "run": _capturing_run,
        "Popen": _RefusingPopen,
        "call": _refusing("subprocess.call"),
        "check_call": _refusing("subprocess.check_call"),
        "check_output": _refusing("subprocess.check_output"),
        "getoutput": _refusing("subprocess.getoutput"),
        "getstatusoutput": _refusing("subprocess.getstatusoutput"),
    }
    saved = {name: getattr(subprocess, name) for name in replacements}

    # The interpreter lookup is left ALONE wherever it works, so that on the
    # Windows box this tool exists for there is exactly ONE divergence from
    # production and not two. It is stubbed only where the real lookup raises,
    # which is every machine with no PowerShell on PATH, and there the whole
    # question of a real probe is moot anyway.
    real_exe = liveness._powershell_executable
    try:
        real_exe()
        stub_exe = False
    except Exception:  # noqa: BLE001 - any failure here means "no interpreter", nothing more
        stub_exe = True

    for name, value in replacements.items():
        setattr(subprocess, name, value)
    if stub_exe:
        liveness._powershell_executable = lambda: "powershell.exe"
    try:
        liveness.collect_facts(_ARGV_PROBE_NAME, task_path=_ARGV_PROBE_PATH)
    except _DerivationLaunchAttempt:
        # The argv was captured on the way in. Grading it is the point; the
        # subject reaching for Popen instead of run changes nothing about that.
        pass
    finally:
        for name, value in saved.items():
            setattr(subprocess, name, value)
        liveness._powershell_executable = real_exe

    argv = captured.get("argv") or []
    if "-Command" not in argv:
        raise AssertionError(f"collect_facts built an argv with no -Command payload: {argv}")
    return argv[argv.index("-Command") + 1]


_ARGV_PROBE_NAME = "ResinCompute-Responder"
_ARGV_PROBE_PATH = "\\GoogleUserPEH\\"

# Executable string constants in the module, docstrings excluded. A docstring
# is never run and never reaches an argv, and the module's own docstring
# carries `->` arrows and the word Stop in prose, so grading it would flag
# English. Comments are not in the AST at all, for the same reason.
_MODULE_STRINGS: list[str] = []


def _executable_string_constants(path: str) -> list[str]:
    tree = ast.parse(open(path, encoding="ascii").read())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


_MODULE_STRINGS = _executable_string_constants(liveness.__file__)

# The SHAPE scans only. The bareword scan is deliberately NOT run over every
# string: measured 2026-09-08, the module's own diagnostic "shutil.which found
# none of: powershell.exe, powershell, pwsh.exe, pwsh" puts `powershell` and
# `pwsh` in executable position and _KNOWN_MUTATOR_TOKENS holds both. That
# string reaches an exception message and never an argv, and the argv
# derivation above is what covers reachability.


def _shape_findings_in_module_strings() -> list[str]:
    out = []
    for text in _MODULE_STRINGS:
        for finding in _mutating_constructs_in(text):
            out.append(f"{finding} in {text[:60]!r}")
        for verb in sorted(set(_MUTATING_VERB_RE.findall(text))):
            out.append(f"{verb} in {text[:60]!r}")
    return out


_ARGV_PROBE_TEXT = _powershell_text_reaching_argv()
_ARGV_PROBE_EXPECTED = liveness._PS_TEMPLATE.format(
    task_name=_ARGV_PROBE_NAME, task_path=_ARGV_PROBE_PATH
)
_IMPORT_TIME_FINDINGS = _findings_in(_ARGV_PROBE_TEXT) + _shape_findings_in_module_strings()
if _ARGV_PROBE_TEXT != _ARGV_PROBE_EXPECTED:
    # Text WRAPPED AROUND the template, whether or not any scan can read it as
    # dangerous. This is here and not only in an arm because a quiet prefix is
    # a place to hide, and an arm that fails does not stop the real-probe arms
    # further down from running the text.
    _IMPORT_TIME_FINDINGS.append(
        "the -Command payload is not the formatted template alone - text is being "
        "concatenated onto it"
    )
if _IMPORT_TIME_FINDINGS:
    raise RuntimeError(
        "ops/check_task_liveness.py would hand PowerShell text this file grades as "
        f"able to change this machine: {_IMPORT_TIME_FINDINGS}. Raising at IMPORT rather than "
        "in an arm, so that no test in this module runs and no subprocess is launched - a "
        "failing assertion further down would be reported AFTER the real-probe arms had "
        "already executed the text."
    )


# Every axis a mutation could test to tell this harness from production. The
# hand-rolled three-attribute shim this replaces failed ALL of them.
_HARNESS_AXES = (
    "Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput",
    "CalledProcessError", "SubprocessError", "TimeoutExpired", "CompletedProcess",
    "DEVNULL", "PIPE", "STDOUT", "list2cmdline",
    "__name__", "__spec__", "__file__", "__doc__",
)


def test_the_subprocess_module_the_subject_sees_under_the_harness_is_the_real_one():
    # THE FOURTH KILL, closed at the harness rather than at a matcher. The spy
    # is installed on validate_task_name, which collect_facts calls AFTER the
    # harness has swapped the launchers in, so what it records is exactly what
    # a mutation planted in collect_facts would see.
    real_popen = subprocess.Popen
    real_module = subprocess
    real_spec = subprocess.__spec__
    real_file = subprocess.__file__
    real_timeout = subprocess.TimeoutExpired
    seen: dict[str, object] = {}
    real_validate = liveness.validate_task_name

    def _spy(task_name):
        mod = liveness.subprocess
        seen["identical"] = mod is real_module and mod is sys.modules["subprocess"]
        seen["type"] = type(mod)
        seen["name"] = mod.__name__
        seen["spec"] = mod.__spec__
        seen["file"] = mod.__file__
        seen["missing"] = [axis for axis in _HARNESS_AXES if not hasattr(mod, axis)]
        seen["popen_is_a_class"] = isinstance(mod.Popen, type)
        seen["popen_subclasses_real"] = issubclass(mod.Popen, real_popen)
        seen["timeout_is_real"] = mod.TimeoutExpired is real_timeout
        return real_validate(task_name)

    liveness.validate_task_name = _spy
    try:
        text = _powershell_text_reaching_argv()
    finally:
        liveness.validate_task_name = real_validate

    assert text, "the derivation captured nothing, so this arm graded nothing"
    assert seen, "the spy never ran, so this arm graded nothing"
    assert seen["identical"], (
        "the subject is not looking at the real stdlib subprocess module while the derivation "
        "runs, so a mutation could branch on the difference"
    )
    assert seen["type"] is type(real_module)
    assert seen["name"] == "subprocess"
    assert seen["spec"] is real_spec
    assert seen["file"] == real_file
    assert seen["missing"] == [], f"the harness is missing {seen['missing']}, which is detectable"
    assert seen["popen_is_a_class"], "Popen must stay a class, or isinstance(..., type) tells"
    assert seen["popen_subclasses_real"], "Popen must stay a real Popen, or issubclass tells"
    assert seen["timeout_is_real"]

    # And the harness put everything back.
    assert liveness.subprocess is real_module
    assert subprocess.Popen is real_popen
    for axis in ("run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        assert getattr(subprocess, axis).__module__ == "subprocess", (
            f"the harness did not restore subprocess.{axis}"
        )


def test_non_vacuity_the_shim_that_was_defeated_fails_every_axis_above():
    # The exact three-attribute stand-in this file used to build. It is here so
    # the arm above is a detector and not a description: `hasattr(subprocess,
    # 'Popen')` planted in collect_facts read False under this object and True
    # in production, which is how the pristine text got graded while the armed
    # text ran. THIS IS NOT INSTALLED ANYWHERE - it is a fixture.
    class _DefeatedShim:
        TimeoutExpired = subprocess.TimeoutExpired
        SubprocessError = subprocess.SubprocessError

        @staticmethod
        def run(argv, **kwargs):
            return None

    missing = [axis for axis in _HARNESS_AXES if not hasattr(_DefeatedShim, axis)]
    assert "Popen" in missing, "the measured kill branched on exactly this absence"
    assert len(missing) >= 10, (
        f"the defeated shim diverged on {len(missing)} axes, and any one of them is a branch"
    )
    assert _DefeatedShim is not subprocess
    assert type(_DefeatedShim) is not type(subprocess)
    assert _DefeatedShim.__name__ != "subprocess"


def test_the_powershell_text_built_under_this_harness_is_sanctioned():
    # RENAMED, and the old name is the reason. It was
    # test_the_text_that_actually_reaches_powershell_is_sanctioned, which claims
    # a fact about production; this arm grades the text built while
    # subprocess.run is replaced, which is not the same instant. See THE CEILING
    # in the module docstring. An arm whose name claims more than it checks is
    # worse than no arm, because the next reader stops looking.
    #
    # The same derivation the import-time block ran, asserted as an arm so it
    # is named in the report rather than only in a collection error.
    assert _ARGV_PROBE_TEXT, "no -Command payload was captured, so this arm grades nothing"
    assert "Get-ScheduledTask" in _ARGV_PROBE_TEXT, "the captured payload is not the probe"
    assert _findings_in(_ARGV_PROBE_TEXT) == []

    # NOTHING MAY BE WRAPPED AROUND THE TEMPLATE. The kill added a second
    # constant either side of it; equality catches that whatever the added text
    # says, including text that carries no command shape at all.
    assert _ARGV_PROBE_TEXT == _ARGV_PROBE_EXPECTED, (
        "the text handed to PowerShell is not the formatted template alone - something is being "
        "concatenated onto it"
    )


def test_non_vacuity_text_concatenated_around_the_template_is_caught():
    # The kill, replayed through the same helper the arm above uses. The
    # template is UNTOUCHED in every case, which is what defeated the previous
    # version of this file.
    pristine = liveness._PS_TEMPLATE.format(task_name=_ARGV_PROBE_NAME, task_path=_ARGV_PROBE_PATH)
    assert _findings_in(pristine) == [], "the positive control must pass before the mutants fail"

    for extra in (
        "ri 'ZZ-no-such-path-9f6839e' -ErrorAction SilentlyContinue\n",
        "del ZZ\n",
        "[System.IO.File]::Delete('ZZ-no-such-path-9f6839e')\n",
        "'x' > 'ZZ-no-such-path-9f6839e'\n",
    ):
        assert _findings_in(extra + pristine), f"prepending {extra!r} was not caught"
        assert _findings_in(pristine + extra), f"appending {extra!r} was not caught"
        assert extra + pristine != pristine, "the equality arm would also have seen this"

    # SHAPE VARIATION on the same defect: text that carries NO command shape at
    # all is invisible to every scan and is caught only by the equality arm.
    # Without this case the corpus would again be planting only what the
    # matcher handles.
    quiet = "$ZZunused = 1\n"
    assert _findings_in(quiet + pristine) == [], (
        "this is the honest half - a quiet prefix passes every scan this file has, and NOTHING "
        "in the scans can see it"
    )
    # It is the EQUALITY check that catches it, and that check is also part of
    # the import-time block, so a quiet prefix is prevented rather than merely
    # reported. Measured 2026-09-08: with the quiet prefix planted, pytest
    # exits 2 on a collection error and no arm in this module runs.
    assert quiet + pristine != _ARGV_PROBE_EXPECTED


def test_non_vacuity_the_module_string_shape_scan_is_not_reading_an_empty_haystack():
    assert len(_MODULE_STRINGS) > 20, (
        f"the AST walk found only {len(_MODULE_STRINGS)} executable string constants in the "
        "module, which is too few for it to be reading the real file"
    )
    assert any("Get-ScheduledTask" in s for s in _MODULE_STRINGS), (
        "the probe template must be among the strings this scan grades"
    )
    # The module docstring must NOT be, and that exclusion is load bearing:
    # it carries `->` arrows that the redirection scan would flag.
    assert not any(s.startswith("check_task_liveness.py - does a Windows") for s in _MODULE_STRINGS)
    assert _shape_findings_in_module_strings() == []

    # The detector fires on a planted string, through the same helper.
    planted = ["[System.IO.File]::Delete('ZZ')", "$x = Remove-Item ZZ", "'x' > 'ZZ'"]
    for text in planted:
        assert _mutating_constructs_in(text) or _MUTATING_VERB_RE.findall(text), (
            f"the module-string shape scan would not have caught {text!r}"
        )
    # And the legitimate neighbours in the real module survive it.
    for benign in ("task name must be letters, digits, space, dot, underscore, hyphen or backslash",
                   "no PowerShell interpreter was found on PATH"):
        assert _mutating_constructs_in(benign) == []
        assert _MUTATING_VERB_RE.findall(benign) == []


# --- THE SOURCE GATE IS A DETECTOR, AND IT GRADED THE IMPORTED FILE -------


def test_the_source_gate_graded_the_same_bytes_that_were_then_imported():
    # A gate that grades one path and imports another has graded nothing. This
    # is the arm that would go red if _SUBJECT_PATH ever stopped agreeing with
    # what `from ops import check_task_liveness` resolves to.
    imported = pathlib.Path(liveness.__file__).resolve()
    assert imported == _SUBJECT_PATH, (
        f"the source gate graded {_SUBJECT_PATH} and the import resolved to {imported}"
    )
    assert _SUBJECT_SOURCE == imported.read_text(encoding="ascii"), (
        "the file changed between the gate and this arm"
    )
    assert len(_SUBJECT_SOURCE) > 5000, (
        f"the gate read only {len(_SUBJECT_SOURCE)} characters, which is too few to be the subject - "
        "zero out of zero reads as a pass"
    )
    assert _source_gate_findings(_SUBJECT_SOURCE, _SUBJECT_TREE) == []


def test_non_vacuity_the_source_gate_refuses_a_module_level_side_effect():
    # THE MEASURED KILL, replayed: `import os as _diag` plus `_diag.remove(...)`
    # at module scope in the subject ran at the import on line 63 of the version
    # of this file that preceded this one, deleted the canary from disk, and the
    # suite reported every arm passing at exit 0.
    #
    # SHAPE VARIATION, and it is the point rather than decoration. None of these
    # is a PowerShell cmdlet, so nothing else in this file can see any of them,
    # and no two of them put the call in the same syntactic place.
    for planted in (
        "import os as _diag\n_diag.remove('ZZ')\n",                  # the kill
        "import shutil\n_x = shutil.rmtree('ZZ')\n",                 # hidden in an assignment
        "import pathlib\npathlib.Path('ZZ').unlink()\n",             # chained off a constructor
        "def _f(_unused=open('ZZ', 'w')):\n    pass\n",              # a default argument runs
        "class _C:\n    _x = open('ZZ', 'w')\n",                     # a class body runs
        "def _d(a):\n    return a\n@_d(open('ZZ', 'w'))\ndef _g():\n    pass\n",  # so does a decorator
        "_MSG = f'{open(chr(90)) !r}'\n",                            # and an f-string
    ):
        assert _import_time_call_findings(ast.parse(planted)), (
            f"the source gate let {planted!r} through, so it would have been imported"
        )

    # POSITIVE CONTROL, and it is the half a blind sweep would fail. The subject
    # legitimately calls re.compile, dataclass and field while being imported,
    # and a gate that flagged those would have to be switched off.
    for benign in (
        "import re\n_RE = re.compile('x')\n",
        "from dataclasses import dataclass, field\n@dataclass\nclass C:\n"
        "    xs: list = field(default_factory=list)\n",
        "def main():\n    return 0\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
        # A function BODY is not import-time code, and calling it one is how a
        # gate becomes noise nobody can leave switched on.
        "def f():\n    import os\n    os.remove('ZZ')\n",
    ):
        assert _import_time_call_findings(ast.parse(benign)) == [], (
            f"the source gate false-positived on {benign!r}"
        )

    # And the real subject passes it, which is what makes the arms above mean
    # something rather than describing a file nobody has.
    assert _import_time_call_findings(_SUBJECT_TREE) == []


def test_non_vacuity_the_source_gate_refuses_a_module_that_asks_whether_it_is_watched():
    # ROUNDS TWO, THREE AND FOUR of this guard were each defeated because the
    # controls planted only the shape the matcher already handled. So no two of
    # the twelve below use the same channel, and the first of them is the
    # measured kill rather than an invented one.
    for planted in (
        "import subprocess\nif hasattr(subprocess, 'Popen'):\n    pass\n",   # THE KILL
        "import subprocess\nif getattr(subprocess, 'Popen', None):\n    pass\n",
        "import subprocess\nif subprocess.Popen:\n    pass\n",               # unsanctioned attribute
        "import subprocess\nif subprocess.__name__ == 'subprocess':\n    pass\n",
        "import subprocess\nimport sys\nif subprocess is sys.modules['subprocess']:\n    pass\n",
        "import subprocess\n_R = subprocess.run\ndef f():\n    return subprocess.run is _R\n",
        "import subprocess as sp\nif sp.Popen:\n    pass\n",                 # alias laundering
        "from subprocess import Popen\n",                                    # from-import laundering
        "import sys\nif sys.modules.get('pytest'):\n    pass\n",
        "if __debug__:\n    pass\n",
        "import os\nif os.environ.get('PYTEST_CURRENT_TEST'):\n    pass\n",
        "import sys\nif sys.stdout.isatty():\n    pass\n",
        "import sys\nif sys.argv[0].endswith('pytest'):\n    pass\n",
    ):
        assert _observation_findings(ast.parse(planted)), (
            f"the source gate let {planted!r} through, so a module could build one PowerShell "
            "string under this file's harness and a different one in real use"
        )

    # POSITIVE CONTROL: everything the subject genuinely does with subprocess
    # survives. A rule that banned these would ban the module it grades.
    for benign in (
        "import subprocess\ncompleted = subprocess.run(['x'], check=False)\n",
        "import subprocess\ntry:\n    pass\nexcept subprocess.TimeoutExpired as exc:\n    raise\n",
        "import sys\nprint('x', file=sys.stderr)\n",
        "import shutil\nfound = shutil.which('powershell.exe')\n",
    ):
        assert _observation_findings(ast.parse(benign)) == [], (
            f"the source gate false-positived on {benign!r}"
        )

    assert _observation_findings(_SUBJECT_TREE) == []


def test_the_probe_is_built_only_from_sanctioned_read_only_commands():
    found = _commands_in(liveness._PS_TEMPLATE)
    assert found, "the scan found no command at all in the probe - it is not reading the template"
    assert "Get-ScheduledTask" in found, "the scan must see the probe's real content, not an empty haystack"

    unsanctioned = _unsanctioned_in(liveness._PS_TEMPLATE)
    assert unsanctioned == [], (
        f"the probe carries {unsanctioned}, which is not in the sanctioned read-only set. "
        "A read-only liveness probe runs Get- and nothing else."
    )
    assert _bare_mutators_in(liveness._PS_TEMPLATE) == [], "the probe carries a hyphenless mutator"
    assert _mutating_constructs_in(liveness._PS_TEMPLATE) == []

    # The allowlist itself is constrained, so it cannot be widened into a
    # mutating cmdlet by whoever finds this arm inconvenient.
    for name in sorted(_SANCTIONED_PROBE_CMDLETS):
        verb = name.split("-", 1)[0].lower()
        assert verb in _READ_ONLY_PS_VERBS, f"{name} carries verb {verb!r}, which is not a read-only verb"


def test_non_vacuity_the_allowlist_catches_every_verb_the_old_denylist_missed():
    # The same scan, run over the template with one command PREPENDED, must
    # report it. These are exactly the verbs the seven-token denylist let past,
    # plus the Get-Item of the non-terminating-error mutant.
    injections = [
        "Remove-Item -Path 'ZZ-no-such-path-9f6839e' -ErrorAction SilentlyContinue",
        "Set-Content -Path 'ZZ' -Value 'x'",
        "Out-File -FilePath 'ZZ'",
        "New-Item -Path 'ZZ' -ItemType File",
        "Enable-ScheduledTask -TaskName 'ZZ'",
        "Stop-ScheduledTask -TaskName 'ZZ'",
        "Get-Item 'ZZ-no-such-item-9f6839e'",
        # D3: the six shapes the capitalised-Verb-Noun corpus above could not
        # have discovered, because every member of it was already the one shape
        # the matcher handled. A control that plants only the case the matcher
        # handles cannot find out that the matcher is case-sensitive.
        "ri 'ZZ'",                              # alias
        "remove-item 'ZZ'",                     # lowercase
        "REMOVE-ITEM 'ZZ'",                     # uppercase
        "& ('Remo' + 've-Item') 'ZZ'",          # concatenated verb
        "cmd /c del ZZ",                        # shell-out
        "(Get-ScheduledTask -TaskName 'ZZ').Delete()",  # method call
    ]
    for line in injections:
        mutated = line + "\n" + liveness._PS_TEMPLATE
        assert _unsanctioned_in(mutated), f"the allowlist scan let {line!r} through"

    # The positive control, through the same scan: the pristine template passes.
    assert _unsanctioned_in(liveness._PS_TEMPLATE) == []


def test_the_module_source_carries_no_stop_modify_or_unregister_shape():
    # RENAMED from test_the_module_never_stops_modifies_or_unregisters_anything,
    # which asserted a fact about the module's BEHAVIOUR from a scan of its
    # TEXT. Those are different claims and only the second one is checkable
    # here. See THE CEILING in the module docstring.
    #
    # The whole-file half, also by SHAPE rather than by a list of names: any
    # Verb-Noun built on a mutating verb, anywhere in the module.
    source = liveness.__file__
    with open(source, encoding="ascii") as handle:
        body = handle.read()
    found = sorted(set(_MUTATING_VERB_RE.findall(body)))
    assert found == [], f"a read-only liveness probe must never carry {found}"
    # Case-INSENSITIVELY, because `stop-process` is the same call as
    # Stop-Process and the old arm compared bytes.
    lowered = body.lower()
    for token in ("stop-process",) + _NATIVE_MUTATOR_EXES:
        assert token not in lowered, f"a read-only liveness probe must never carry {token}"
    # The probe text inside this module gets the PowerShell-aware scan too, so a
    # hyphenless alias planted in the template is caught by the whole-file arm
    # and not only by the probe arm.
    assert _bare_mutators_in(liveness._PS_TEMPLATE) == []


def test_non_vacuity_the_read_only_scan_would_catch_a_planted_mutation():
    # Proves the guard above is a detector and not a tautology over an empty
    # haystack: the same scan run over a deliberately bad body must FAIL, for
    # every one of the six verbs the old seven-token denylist missed.
    for verb_noun in (
        "Unregister-ScheduledTask",
        "Remove-Item",
        "Set-Content",
        "Out-File",
        "New-Item",
        "Enable-ScheduledTask",
        "Stop-ScheduledTask",
        # D3: SHAPE variation. The seven above are all capitalised Verb-Noun,
        # which is exactly the one spelling the matcher already handled, so
        # none of them could ever have discovered that it was case-sensitive.
        "stop-process",
        "unregister-scheduledtask",
        "REMOVE-ITEM",
        "sToP-sChEdUlEdTaSk",
    ):
        body = f"subprocess.run(['powershell', '-Command', '{verb_noun} -TaskName x'])"
        assert _MUTATING_VERB_RE.findall(body) == [verb_noun], f"the shape scan missed {verb_noun}"

    # The hyphenless half, which the Verb-Noun shape structurally cannot see.
    # These run through the PowerShell-aware scan, in executable position.
    for fragment in ("ri 'ZZ'", "DEL ZZ", "cmd /c del ZZ", "TASKKILL /F /PID 1", "iex 'x'"):
        assert _bare_mutators_in(fragment), f"the hyphenless scan missed {fragment!r}"

    # And the shapes that carry no command NAME at all.
    for fragment in ("$t.Delete()", "& ('Remo' + 've-Item') ZZ"):
        assert _mutating_constructs_in(fragment), f"the construct scan missed {fragment!r}"

    # POSITIVE CONTROL for all three scans: the legitimate neighbours SURVIVE.
    # A sweep that scores 100 percent by flagging everything has failed.
    for benign in ("Get-ScheduledTask -TaskName x", "$i.NextRunTime.ToString($fmt)", "$ri = ''"):
        assert _bare_mutators_in(benign) == [], f"the hyphenless scan false-positived on {benign!r}"
        assert _mutating_constructs_in(benign) == [], f"the construct scan false-positived on {benign!r}"
        assert _MUTATING_VERB_RE.findall(benign) == []


def test_non_vacuity_the_probe_scan_sees_shapes_that_are_not_capitalised_verb_noun():
    for line in _EVASIVE_INJECTIONS:
        mutated = line + "\n" + liveness._PS_TEMPLATE
        assert _unsanctioned_in(mutated), f"the probe scan let {line!r} through"

    assert _unsanctioned_in(liveness._PS_TEMPLATE) == []


def test_non_vacuity_the_probe_scan_sees_static_calls_and_bare_redirection():
    # THE 2026-09-08 KILL, replayed at the position it was planted: not
    # prepended, but spliced in AFTER the error-preference line, where the
    # first-executable-line arm cannot see it either. Every one of these left
    # all four scans empty before this repair; the assertion below is what
    # turns each of them red.
    preference = liveness._PS_TEMPLATE.index(_ERROR_PREFERENCE_LINE) + len(_ERROR_PREFERENCE_LINE)
    for line in _STATIC_AND_REDIRECTION_INJECTIONS:
        mutated = (
            liveness._PS_TEMPLATE[:preference] + "\n" + line + liveness._PS_TEMPLATE[preference:]
        )
        assert _unsanctioned_in(mutated), f"the probe scan let {line!r} through"
        # And the arm that would have caught a PREPENDED line is shown to be
        # silent here, so nobody reads this repair as belonging to that one.
        assert _first_executable_line(mutated) == _ERROR_PREFERENCE_LINE

    # POSITIVE CONTROL: the shapes the probe legitimately uses are not flagged.
    # `[string]$tr.EndBoundary` and `[pscustomobject]@{` are casts, which carry
    # no `::`, and `.ToString(` is the one sanctioned method.
    for benign in (
        "$k = [string]$tr.EndBoundary",
        "[pscustomobject]@{ exists = $false }",
        "$next = $i.NextRunTime.ToString($fmt)",
        "$b = [bool]$tr.Enabled",
        "if ($all.Count -gt 1) { exit 0 }",
    ):
        assert _mutating_constructs_in(benign) == [], f"the shape scan false-positived on {benign!r}"
    assert _unsanctioned_in(liveness._PS_TEMPLATE) == []


def test_non_vacuity_the_read_only_scan_is_case_insensitive_as_its_comment_claims():
    for spelling in ("stop-process", "unregister-scheduledtask", "REMOVE-ITEM", "Set-Content"):
        body = f"subprocess.run(['powershell', '-Command', '{spelling} -TaskName x'])"
        assert _MUTATING_VERB_RE.findall(body) == [spelling], f"the shape scan missed {spelling}"
    for bare in ("TASKKILL /F /PID 1", "ri 'ZZ'", "cmd /c del ZZ"):
        assert _bare_mutators_in(bare), f"the whole-file scan missed {bare!r}"


def test_non_vacuity_discovery_failure_is_not_reported_as_an_empty_machine():
    # The three reasons the old helper collapsed into one (None, None), plus
    # the shapes a neutered enumeration produces at exit 0. Every one of them
    # must read FAILED, because none of them is evidence about this machine.
    def _rows(*pairs):
        return json.dumps({"tasks": [{"name": n, "path": p} for n, p in pairs]})

    for returncode, stdout, why in (
        (1, "", "non-zero exit"),
        (0, "", "exit 0 with no output"),
        (0, "not json at all", "exit 0 with unparseable output"),
        (0, '{"found": false}', "exit 0 carrying no task records at all"),
        (0, '{"tasks": []}', "exit 0 having delivered nothing"),
        (0, '{"tasks": null}', "exit 0 with the 5.1 empty-array collapse to null"),
        (0, '{"tasks": ["Backup", "WiFiTask"]}', "exit 0 with records of the wrong shape"),
    ):
        got = _classify_discovery(returncode, stdout)
        assert got.status == "FAILED", f"{why} was not reported as a failed discovery"
        assert got.detail, "a FAILED discovery must say what went wrong"

    # POSITIVE CONTROL, same classifier: a discovery that really ran and really
    # found no duplicate is NONE and not FAILED. Without this arm the classifier
    # could return FAILED unconditionally and pass everything above.
    ran = _classify_discovery(0, _rows(("Alpha", "\\"), ("Beta", "\\X\\"), ("Gamma", "\\")))
    assert ran.status == "NONE"
    assert ran.total == 3

    # AND THE REGRESSION THE OLD FLOOR OF TEN WOULD HAVE FAILED. A Server Core
    # box or a Windows container holding three tasks and no duplicate is a
    # SPARSE MACHINE, not a broken enumeration, and must not be slandered as
    # one. The previous floor classified exactly this as FAILED.
    assert ran.total < 10, "this control is only meaningful below the refuted floor of ten"

    # POSITIVE CONTROL, the other arm of the same classifier: a real duplicate,
    # grouped in Python from records that carry no found flag of their own.
    hit = _classify_discovery(0, _rows(("Backup", "\\"), ("Alpha", "\\"), ("Backup", "\\X\\")))
    assert hit.status == "FOUND"
    assert hit.name == "Backup"
    assert hit.paths == ["\\", "\\X\\"]
    assert hit.total == 3

    # A name the module's own gate would REFUSE is not offered, even duplicated.
    refused = _classify_discovery(0, _rows(("bad;name", "\\"), ("bad;name", "\\X\\")))
    assert refused.status == "NONE", "a duplicated name collect_facts would reject is not a lead"

    # The 5.1 scalar-collapse normalisation still holds through the new path.
    scalar = _classify_discovery(0, '{"tasks": {"name": "Alpha", "path": "\\\\"}}')
    assert scalar.status == "NONE"
    assert scalar.total == 1

    # The three statuses are genuinely distinct, which is the defect closed.
    assert len({_classify_discovery(1, "").status, ran.status, hit.status}) == 3


# --- NOTHING RUNS BEFORE THE ERROR PREFERENCE -----------------------------
#
# $ErrorActionPreference = 'Stop' is what makes a failure inside the probe
# TERMINATING, which is what makes it reach a non-zero exit code, which is the
# only thing collect_facts reads to decide the scheduler could not be answered.
# A command placed BEFORE that line runs under the default Continue: a
# non-terminating error, exit code still 0, payload unchanged, and every arm in
# this file green. Measured 2026-09-08 - prepending
#
#     Get-Item 'ZZ-no-such-item-9f6839e'
#
# to the template left collect_facts('ResinCompute-Responder') returning
# exists=True and a DORMANT verdict with the injected line in the template head.
#
# So the ORDER is asserted, not just the presence. The line must be the first
# thing the interpreter executes.

_ERROR_PREFERENCE_LINE = "$ErrorActionPreference = 'Stop'"


def _first_executable_line(script: str) -> str:
    """The first line PowerShell would actually run - blanks and comments skipped."""
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return ""


def test_the_probe_sets_its_error_preference_before_it_runs_anything():
    first = _first_executable_line(liveness._PS_TEMPLATE)
    assert first == _ERROR_PREFERENCE_LINE, (
        f"the probe's first executable line is {first!r}. Anything running ahead of "
        f"{_ERROR_PREFERENCE_LINE!r} runs under the default Continue, so its failure leaves exit 0 "
        "and the probe answers as though nothing went wrong."
    )
    assert _ERROR_PREFERENCE_LINE in liveness._PS_TEMPLATE


def test_non_vacuity_a_command_prepended_before_the_error_preference_is_caught():
    # The same derivation over the mutated template must NOT return the
    # preference line. Both a benign-looking Get- and a destructive verb are
    # shown, because the defect is the POSITION and not the verb.
    for injected in ("Get-Item 'ZZ-no-such-item-9f6839e'", "Remove-Item -Path 'ZZ'"):
        mutated = injected + "\n" + liveness._PS_TEMPLATE
        assert _first_executable_line(mutated) != _ERROR_PREFERENCE_LINE, (
            f"{injected!r} was prepended and the first-line check did not notice"
        )
        assert _first_executable_line(mutated) == injected

    # Positive control through the same helper: a leading blank line and a
    # leading comment are NOT injections and must still pass.
    assert _first_executable_line("\n\n# a comment\n" + liveness._PS_TEMPLATE) == _ERROR_PREFERENCE_LINE


# --- THE NAME GATE IS ENFORCED on the real path, not merely correct -------
#
# These arms stub subprocess.run and NOT collect_facts, which is what makes
# them statements about the gate rather than about the regex. Deleting
# `validate_task_name(...)` from collect_facts turns every one of them red.


class _SubprocessSpy:
    """Records every subprocess.run call and answers with a canned payload."""

    def __init__(self, payload=None, returncode=0, stdout=None):
        self.calls = []
        self._stdout = json.dumps(payload if payload is not None else MEASURED_DORMANT)
        if stdout is not None:
            self._stdout = stdout
        self._returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, self._returncode, self._stdout, "")


def test_collect_facts_refuses_a_metacharacter_name_before_any_subprocess(monkeypatch):
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    with pytest.raises(ValueError):
        liveness.collect_facts("ResinCompute'; Unregister-ScheduledTask -TaskName x; '")
    assert spy.calls == [], "the gate must fire BEFORE PowerShell is launched, not after"


def test_positive_control_a_clean_name_does_reach_the_subprocess(monkeypatch):
    # Same stub, same call site. Proves the arm above measures the GATE and not
    # a subprocess that never runs anyway.
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    liveness.collect_facts("ResinCompute-Responder")
    assert len(spy.calls) == 1


def test_main_refuses_a_metacharacter_name_on_the_real_entry_path(monkeypatch, capsys):
    # collect_facts is NOT stubbed here. main -> collect_facts -> the gate.
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    code = liveness.main(["bad; Unregister-ScheduledTask -TaskName x"])
    out = capsys.readouterr().out
    assert code == liveness.EXIT_UNKNOWN
    assert spy.calls == [], "a rejected name must never reach PowerShell through main() either"
    assert "Unregister-ScheduledTask" not in out, "the rejected name must not be echoed back"


def test_the_task_path_is_gated_too_since_it_reaches_the_same_literal(monkeypatch):
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    with pytest.raises(ValueError):
        liveness.collect_facts("ResinCompute-Responder", task_path="\\'; Unregister-ScheduledTask x; '")
    assert spy.calls == []


def test_positive_control_a_real_task_path_is_accepted_and_interpolated(monkeypatch):
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    liveness.collect_facts("RunPlatformExperienceHelper_Metrics", task_path="\\GoogleUserPEH\\")
    script = spy.calls[0][0][-1]
    assert "\\GoogleUserPEH\\" in script


def test_a_task_name_carrying_shell_metacharacters_is_refused():
    with pytest.raises(ValueError):
        liveness.validate_task_name("ResinCompute'; Unregister-ScheduledTask -TaskName x; '")


def test_positive_control_the_real_task_name_validates():
    assert liveness.validate_task_name("ResinCompute-Responder") == "ResinCompute-Responder"


# --- The PowerShell INVOCATION itself is part of the contract -------------


def test_the_interpreter_is_launched_with_no_profile_and_non_interactive(monkeypatch):
    # A profile can print a banner into stdout and break the JSON parse, and an
    # interactive prompt can hang until the timeout. Both flags are load
    # bearing and neither is visible in any payload, so they are asserted here.
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    liveness.collect_facts("ResinCompute-Responder")
    argv = spy.calls[0][0]
    assert "-NoProfile" in argv
    assert "-NonInteractive" in argv


def test_non_vacuity_the_flag_assertion_would_catch_their_absence():
    # The same membership test over an argv that lacks them must be false.
    stripped = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", "..."]
    assert "-NoProfile" not in stripped
    assert "-NonInteractive" not in stripped


def test_the_timeout_argument_actually_reaches_the_subprocess(monkeypatch):
    # main -> collect_facts -> subprocess.run, with nothing stubbed between.
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    liveness.main(["ResinCompute-Responder", "--timeout", "7"])
    assert spy.calls[0][1]["timeout"] == 7


def test_positive_control_the_default_timeout_is_used_when_none_is_given(monkeypatch):
    spy = _SubprocessSpy()
    monkeypatch.setattr(liveness.subprocess, "run", spy)
    liveness.main(["ResinCompute-Responder"])
    assert spy.calls[0][1]["timeout"] == liveness.DEFAULT_TIMEOUT_SECONDS
    assert liveness.DEFAULT_TIMEOUT_SECONDS != 7, "the arm above would be vacuous if these collided"


# --- THE PROBE AND THE PARSER MUST AGREE ----------------------------------
#
# Every arm above this line runs on a hand-held fixture, and a hand-held
# fixture can only prove the parser agrees with whoever typed it. The probe
# could stop emitting end_boundary entirely - the single field this tool exists
# to read - and every one of them would stay green. These arms close that by
# running the REAL probe against a REAL task and checking the payload against
# a key set RECORDED FROM THE PARSER rather than listed by hand.

# AND WHAT THESE ARMS DO NOT BUY. _WINDOWS_ONLY is a skipif, so on Linux CI
# every arm carrying it is skipped outright and the repair below buys CI
# nothing at all. That is stated here rather than left for a reader to
# discover, because a comment claiming otherwise would be the same defect this
# file keeps being refuted for. What DOES run everywhere is the import-time
# probe grading, the static threshold arm, and the pure classifier arms - all
# of which are deliberately written to need no PowerShell.
_WINDOWS_ONLY = pytest.mark.skipif(
    sys.platform != "win32", reason="the probe reads the Windows Task Scheduler"
)


class _WatchedDict(dict):
    """A dict that remembers which keys were asked for via .get()."""

    def __init__(self, source, seen):
        super().__init__(source)
        self._seen = seen

    def get(self, key, default=None):
        self._seen.add(key)
        return super().get(key, default)


def _keys_the_parser_reads():
    """Every payload key parse_facts depends on, DERIVED by watching it run.

    Hand-listing the keys here would only restate the parser, and would drift
    from it silently. Recording them cannot.
    """
    top: set[str] = set()
    trig: set[str] = set()
    watched = _WatchedDict(MEASURED_LIVE_WATCHDOG, top)
    watched["triggers"] = [_WatchedDict(t, trig) for t in MEASURED_LIVE_WATCHDOG["triggers"]]
    facts = liveness.parse_facts(watched)
    assert facts.exists and len(facts.triggers) == 2, "the recording run must exercise the whole parser"
    return top, trig


class _TaskPick(typing.NamedTuple):
    status: str
    root: str | None
    deep: str | None
    deep_path: str | None
    detail: str


def _real_task_names() -> _TaskPick:
    """Ask the scheduler, read only, for one root task and one foldered task.

    A CONDITION THAT CANNOT DISTINGUISH "CHECKED AND FOUND NOTHING" FROM "COULD
    NOT CHECK" IS THE ROOT CAUSE THIS FILE HAS NOW BEEN REFUTED FOR THREE
    TIMES. The version this replaces ended

        if done.returncode != 0 or not done.stdout.strip():
            return None, None, None

    and its three callers all took a pytest.skip whose text blamed the machine.
    Measured 2026-09-08: making this enumeration exit 3 turned a run into 65
    passed, 3 skipped at exit 0, with every skip message asserting something
    about the machine that was false in that run.

    So it returns a STATUS. FAILED must fail; only NONE may skip.
    """
    exe = liveness._powershell_executable()
    script = (
        "$ErrorActionPreference='Stop';"
        "$all = @(Get-ScheduledTask);"
        "$u = $all | Group-Object TaskName | Where-Object { $_.Count -eq 1 } |"
        " ForEach-Object { $_.Group[0] };"
        "$ok = @($u | Where-Object { $_.TaskName -match '^[A-Za-z0-9 ._-]{1,200}$'"
        " -and @($_.Triggers).Count -gt 0 });"
        "$r = $ok | Where-Object { $_.TaskPath -eq '\\' } | Select-Object -First 1;"
        "$d = $ok | Where-Object { $_.TaskPath -ne '\\' } | Select-Object -First 1;"
        "[pscustomobject]@{ total = $all.Count; root = [string]$r.TaskName;"
        " deep = [string]$d.TaskName; deep_path = [string]$d.TaskPath }"
        " | ConvertTo-Json -Compress"
    )
    try:
        done = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _TaskPick("FAILED", None, None, None, f"could not be launched: {type(exc).__name__}")
    return _classify_task_pick(done.returncode, done.stdout)


def _classify_task_pick(returncode: int, stdout: str) -> _TaskPick:
    """The pure half of _real_task_names, so its FAILED arms are testable."""
    if returncode != 0:
        return _TaskPick("FAILED", None, None, None, f"the enumeration exited {returncode}")
    if not stdout.strip():
        return _TaskPick("FAILED", None, None, None, "the enumeration exited 0 but printed nothing")
    try:
        got = json.loads(stdout.strip())
    except ValueError:
        return _TaskPick("FAILED", None, None, None, "the enumeration printed something that is not JSON")
    if not isinstance(got, dict) or "total" not in got:
        return _TaskPick("FAILED", None, None, None, "the enumeration printed no task total")
    try:
        total = int(got["total"])
    except (TypeError, ValueError):
        return _TaskPick("FAILED", None, None, None, "the enumeration printed a total that is not a number")
    if total < _MIN_ENUMERATED_TASKS:
        return _TaskPick(
            "FAILED", None, None, None,
            "the enumeration saw no scheduled task at all, which is indistinguishable from an "
            "enumeration that did not run",
        )
    return _TaskPick(
        "RAN",
        got.get("root") or None,
        got.get("deep") or None,
        got.get("deep_path") or None,
        f"the enumeration saw {total} scheduled tasks",
    )


@_WINDOWS_ONLY
def test_the_real_probe_emits_every_key_the_parser_reads():
    pick = _real_task_names()
    assert pick.status != "FAILED", (
        f"the enumeration this arm selects its subject from did not run, so a skip here would "
        f"blame the machine for a tool failure: {pick.detail}"
    )
    root_name = pick.root
    if root_name is None:
        pytest.skip(
            f"{pick.detail}, and none of them is a uniquely named task at TaskPath \\ carrying a "
            "trigger and a name the module's own gate accepts"
        )

    payload = liveness.collect_facts(root_name)
    assert payload.get("exists") is True, f"{root_name} was enumerated a moment ago and must still exist"
    assert payload.get("ambiguous") is False, "the enumeration filtered to unique names"

    top_keys, trigger_keys = _keys_the_parser_reads()
    missing = sorted(k for k in top_keys if k not in payload)
    assert missing == [], f"the probe stopped emitting {missing}, which the parser reads"

    triggers = payload.get("triggers")
    assert isinstance(triggers, list) and triggers, "the enumeration required at least one trigger"
    for index, raw in enumerate(triggers):
        assert isinstance(raw, dict), f"trigger {index} came back as {type(raw).__name__}, not an object"
        gap = sorted(k for k in trigger_keys if k not in raw)
        assert gap == [], f"trigger {index} is missing {gap}, which the parser reads"

    # The probe must report the FIELDS it is asked for, not some other field
    # wearing their name. A ScheduledTaskState is one of five words, and no
    # task name of the shape we selected is among them.
    assert payload["state"] in ("Unknown", "Disabled", "Queued", "Ready", "Running"), (
        f"state came back as {payload['state']!r}, which is not a ScheduledTaskState"
    )
    assert payload["task_name"] == root_name
    assert payload["task_path"] == "\\"

    # And the whole payload must survive the parser and the verdict.
    result = liveness.verdict(liveness.parse_facts(payload))
    assert result.status in ("LIVE", "DORMANT", "UNKNOWN")


@_WINDOWS_ONLY
def test_the_real_probe_answers_for_a_task_outside_the_root_task_path():
    # Get-ScheduledTaskInfo -TaskName searches ONLY TaskPath '\' and throws
    # "The system cannot find the file specified" for anything in a folder,
    # which the refuted version reported as an account problem. -InputObject
    # does not. Measured 2026-09-08.
    pick = _real_task_names()
    assert pick.status != "FAILED", (
        f"the enumeration this arm selects its subject from did not run, so a skip here would "
        f"blame the machine for a tool failure: {pick.detail}"
    )
    deep_name, deep_path = pick.deep, pick.deep_path
    if deep_name is None:
        pytest.skip(
            f"{pick.detail}, and none of them is a uniquely named FOLDERED task carrying a trigger "
            "and a name the module's own gate accepts"
        )

    payload = liveness.collect_facts(deep_name, task_path=deep_path)
    assert payload.get("exists") is True, f"{deep_name} under {deep_path} must be answerable"
    assert payload.get("ambiguous") is False
    assert payload["task_path"] == deep_path
    result = liveness.verdict(liveness.parse_facts(payload))
    assert result.status in ("LIVE", "DORMANT", "UNKNOWN"), "a foldered task must reach a real verdict"


@_WINDOWS_ONLY
def test_the_real_probe_reports_a_name_nothing_holds_as_absent():
    # The negative control on the two arms above: the same real probe, the same
    # real PowerShell, a name that is not registered.
    payload = liveness.collect_facts("ResinCompute-NoSuchTask-20260908")
    assert payload.get("exists") is False
    assert liveness.verdict(liveness.parse_facts(payload)).status == "ABSENT"


# --- THE PROBE'S OWN AMBIGUITY BRANCH, not the parser's -------------------
#
# A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE, and every ambiguity
# arm above this line feeds MEASURED_AMBIGUOUS straight to parse_facts. That
# grades the PARSER. The decision that a name matched more than once is taken in
# PowerShell, at `if ($all.Count -gt 1)`, and nothing above tests it: the three
# real-probe arms deliberately select names that are UNIQUE, so they cannot
# reach it. Measured 2026-09-08 - changing that threshold to 99 makes the probe
# silently answer about $all[0] and the whole suite stays green.
#
# AND THE EXECUTION ARM ALONE STILL DID NOT CLOSE IT. It can only reach the
# branch on a machine that really holds a duplicated TaskName, and on a
# duplicate-free one it skips. Measured 2026-09-08 with that machine simulated:
# the -gt 99 mutant survived at 64 passed, 1 skipped, exit 0, while the skip
# text asserted "the machine, not the tool". So the threshold is ALSO pinned
# statically, in an arm that runs on every machine and names itself as static.
#
# This arm runs the REAL probe against a name the scheduler really does hold
# more than once. The name is DISCOVERED, never hardcoded: measured on this
# machine 2026-09-08, 'Backup', 'CreateObjectTask' and 'WiFiTask' each match two
# TaskPaths, and any of the three may be gone next week.
#
# READ ONLY. Get-ScheduledTask and nothing else.

# THE ENUMERATION NO LONGER DECIDES ANYTHING, and that is the repair. The
# version this replaces did the grouping and the `-gt 1` threshold IN
# POWERSHELL and reported only its own conclusion plus a `total` it also
# supplied. Both were mutable, and both were mutated on 2026-09-08: changing
# this script's group filter to `-gt 9` simulated a duplicate-free machine, the
# arm below took its skip, and the module's own ambiguity mutant survived while
# the run reported 67 passed, 1 skipped at exit 0. A test that asks a script it
# also controls whether it is allowed to skip has no independent footing.
#
# So the script now RETURNS RECORDS AND DRAWS NO CONCLUSION: one object per
# registered task, name and path. The grouping, the threshold and the total are
# all computed in Python from the records that actually arrived. There is no
# reported total left to lie about - the total IS the record count - and no
# PowerShell threshold left to move.
_DUPLICATE_NAME_DISCOVERY = """
$ErrorActionPreference='Stop'
$rows = @()
foreach ($t in @(Get-ScheduledTask)) {
    $rows += [pscustomobject]@{ name = [string]$t.TaskName; path = [string]$t.TaskPath }
}
[pscustomobject]@{ tasks = @($rows) } | ConvertTo-Json -Compress -Depth 5
"""

# ONE, and the previous value of TEN was refuted from BOTH sides on 2026-09-08.
#
# It could never fire. Measured over totals 0..39, the set of totals reaching
# the arm's own `assert found.total >= _MIN_PLAUSIBLE_TASK_COUNT` while being
# below the floor was EMPTY, because the classifier had already returned FAILED
# for every one of them. Deleting that assertion was an equivalent mutant.
#
# And it over-fired. A Server Core box or a Windows container that really does
# hold five scheduled tasks was classified FAILED and HARD-FAILED the arm. The
# floor was asked to separate a sparse machine from a broken enumeration and it
# picked the wrong side of that line.
#
# The separation is now structural rather than statistical. The total counts
# the records that ARRIVED, so a neutered enumeration cannot report a number it
# did not deliver, and the only count that stays ambiguous is zero: a scheduler
# that returns no task at all is indistinguishable from a call that did not
# run, so zero fails CLOSED. Every positive count is evidence the enumeration
# ran, and a sparse machine is no longer slandered.
_MIN_ENUMERATED_TASKS = 1

# The module's own task-name gate, restated here BY VALUE so discovery only
# offers names collect_facts will accept. Importing the gate a filter is
# supposed to model would make the filter unable to notice the gate moving.
_VALIDATOR_SHAPED_NAME = re.compile(r"^[A-Za-z0-9 ._\\-]{1,200}$")


class _Discovery(typing.NamedTuple):
    status: str
    name: str | None
    paths: list[str]
    total: int
    detail: str


def _classify_discovery(returncode: int, stdout: str) -> _Discovery:
    """Separate DISCOVERY-FAILED from DISCOVERY-RAN-AND-FOUND-NOTHING.

    The version before last returned (None, None) for THREE different reasons -
    non-zero exit, empty stdout, and found=false - and the caller skipped on all
    three. A discovery that failed was therefore indistinguishable from a
    machine that legitimately holds no duplicated name.

    This version additionally does the GROUPING here, in Python, over records
    the enumeration merely delivered. The previous one trusted a found/total
    conclusion computed inside the same PowerShell it was meant to be
    independent of. Only NONE may skip. FAILED must fail.
    """
    if returncode != 0:
        return _Discovery("FAILED", None, [], 0, f"discovery exited {returncode}")
    if not stdout.strip():
        return _Discovery("FAILED", None, [], 0, "discovery exited 0 but printed nothing")
    try:
        got = json.loads(stdout.strip())
    except ValueError:
        return _Discovery("FAILED", None, [], 0, "discovery printed something that is not JSON")
    if not isinstance(got, dict) or "tasks" not in got:
        return _Discovery(
            "FAILED", None, [], 0,
            "discovery printed no task records, so it cannot be shown to have run",
        )
    rows = got.get("tasks")
    # Windows PowerShell 5.1 collapses a one-element array to a scalar and an
    # empty one to $null. Normalised rather than trusted.
    if rows is None:
        rows = []
    elif not isinstance(rows, list):
        rows = [rows]
    if not all(isinstance(row, dict) for row in rows):
        return _Discovery(
            "FAILED", None, [], 0, "discovery printed task records of an unexpected shape"
        )

    total = len(rows)
    if total < _MIN_ENUMERATED_TASKS:
        return _Discovery(
            "FAILED", None, [], total,
            "discovery delivered no scheduled task at all. A scheduler holding nothing and a "
            "call that never enumerated look identical from here, so this fails closed",
        )

    by_name: dict[str, list[str]] = {}
    for row in rows:
        name = str(row.get("name") or "")
        if not _VALIDATOR_SHAPED_NAME.match(name):
            continue
        by_name.setdefault(name, []).append(str(row.get("path") or "").strip())

    for name in sorted(by_name):
        if len(by_name[name]) > 1:
            return _Discovery(
                "FOUND", name, sorted(by_name[name]), total,
                f"discovery enumerated {total} scheduled tasks and {name} is held more than once",
            )

    return _Discovery(
        "NONE", None, [], total,
        f"discovery enumerated {total} scheduled tasks, {len(by_name)} of them carrying a name the "
        "module's own gate accepts, and none of those is held under more than one TaskPath",
    )


def _a_name_registered_more_than_once() -> _Discovery:
    """Ask the scheduler, read only, for a TaskName held under two TaskPaths.

    Returns a _Discovery whose status is FOUND, NONE or FAILED. It never
    collapses the last two, which was the defect.
    """
    exe = liveness._powershell_executable()
    try:
        done = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _DUPLICATE_NAME_DISCOVERY],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _Discovery("FAILED", None, [], 0, f"discovery could not be launched: {type(exc).__name__}")
    return _classify_discovery(done.returncode, done.stdout)


_AMBIGUITY_BRANCH = "if ($all.Count -gt 1) {"
_ABSENCE_BRANCH = "if ($all.Count -eq 0) {"


def test_the_probe_keeps_its_ambiguity_threshold_at_more_than_one_match():
    # THE ARM THAT RUNS ON EVERY MACHINE, and the reason it exists.
    #
    # The execution arm below can only reach the probe's ambiguity branch on a
    # machine that really holds a duplicated TaskName, and it SKIPS otherwise.
    # Measured 2026-09-08 on a simulated duplicate-free machine: changing the
    # module's threshold from `-gt 1` to `-gt 99` - the exact mutant the comment
    # above says this section exists to kill - left the run at 67 passed, 1
    # skipped, exit 0. The skip is honest about the machine and says nothing
    # about the mutant, and that is precisely the hole.
    #
    # This arm is STATIC and says so in its name. It reads the two thresholds
    # out of the text that actually reaches PowerShell, so it kills the mutant
    # on a duplicate-free box, in a container, and on Linux CI where every
    # _WINDOWS_ONLY arm in this file is skipped outright.
    assert _AMBIGUITY_BRANCH in _ARGV_PROBE_TEXT, (
        f"the probe no longer carries {_AMBIGUITY_BRANCH!r}. Any other threshold makes it answer "
        "about a silently picked one of several matched tasks"
    )
    assert _ABSENCE_BRANCH in _ARGV_PROBE_TEXT, (
        f"the probe no longer carries {_ABSENCE_BRANCH!r}, which is what makes an unregistered "
        "name ABSENT rather than a crash"
    )


def test_non_vacuity_a_moved_ambiguity_threshold_is_caught_by_the_static_arm():
    # The same two membership tests over mutated copies of the SAME text. Both
    # mutants are the ones actually planted against this file.
    for mutant in ("if ($all.Count -gt 99) {", "if ($all.Count -gt 2) {"):
        moved = _ARGV_PROBE_TEXT.replace(_AMBIGUITY_BRANCH, mutant)
        assert moved != _ARGV_PROBE_TEXT, "the replacement did not change anything, so this proves nothing"
        assert _AMBIGUITY_BRANCH not in moved, f"the check would not have noticed {mutant!r}"
    collapsed = _ARGV_PROBE_TEXT.replace(_ABSENCE_BRANCH, "if ($all.Count -eq 1) {")
    assert _ABSENCE_BRANCH not in collapsed

    # POSITIVE CONTROL: the pristine text passes the same two tests, so they
    # are not simply failing on everything.
    assert _AMBIGUITY_BRANCH in _ARGV_PROBE_TEXT and _ABSENCE_BRANCH in _ARGV_PROBE_TEXT


@_WINDOWS_ONLY
def test_the_real_probe_answers_a_duplicated_name_as_ambiguous():
    found = _a_name_registered_more_than_once()

    # DISCOVERY THAT COULD NOT BE SHOWN TO HAVE RUN IS A FAILURE, NOT A SKIP.
    # The old arm skipped here, so on CI and in a fresh clone it asserted
    # nothing while still reporting a pass.
    assert found.status != "FAILED", (
        f"the duplicate-name discovery did not run, so this arm can say nothing about the probe's "
        f"ambiguity branch: {found.detail}"
    )
    # There is deliberately NO `assert found.total >= <floor>` here any more.
    # Measured 2026-09-08 over totals 0..39: the classifier already returns
    # FAILED for every total the assertion could have caught, so the line was
    # an equivalent mutant - deleting it changed nothing. The floor belongs to
    # the classifier, which is where it is tested.

    if found.status == "NONE":
        # The ONLY skip that remains. It says the enumeration ran and what it
        # saw, and it does NOT claim the tool is therefore sound: the static
        # arm above is what kills the threshold mutant on this machine.
        pytest.skip(
            f"{found.detail}, so the probe's ambiguity branch cannot be REACHED here. "
            "The threshold itself is still pinned by "
            "test_the_probe_keeps_its_ambiguity_threshold_at_more_than_one_match, which runs "
            "everywhere"
        )

    assert found.status == "FOUND", f"unexpected discovery status {found.status}: {found.detail}"
    name, paths = found.name, found.paths

    payload = liveness.collect_facts(name)
    assert payload.get("exists") is True, f"{name} was enumerated a moment ago and must still exist"
    assert payload.get("ambiguous") is True, (
        f"the scheduler holds {name} under {paths}, and the probe answered about a single one of them "
        "instead of refusing - a silently picked task is worse than no answer"
    )
    # The VALUES, not merely the flag: the probe must name every path it saw.
    assert sorted(payload.get("matches") or []) == sorted(paths)
    assert len(payload.get("matches") or []) > 1
    # The probe must NOT have answered as though it had resolved one task.
    assert "state" not in payload, "an ambiguous answer must carry no single task's State"

    result = liveness.verdict(liveness.parse_facts(payload))
    assert result.status == "AMBIGUOUS"
    assert result.status not in ("LIVE", "DORMANT", "UNKNOWN")

    # POSITIVE CONTROL, same probe, same command family, one field different:
    # the very same name WITH a TaskPath resolves to exactly one task. This is
    # also the proof that the advice the AMBIGUOUS report prints actually works.
    resolved = liveness.collect_facts(name, task_path=paths[0])
    assert resolved.get("exists") is True
    assert resolved.get("ambiguous") is False, "a name plus its TaskPath names exactly one task"
    assert resolved.get("task_path") == paths[0]
    assert liveness.verdict(liveness.parse_facts(resolved)).status != "AMBIGUOUS"

    print(f"\n[probe ambiguity arm] RAN against {name}, matched under {paths}")


# --- THE PROBE MUST REPORT THE ENDBOUNDARY VALUE, NOT MERELY THE KEY ------
#
# The arm above this one pins KEY PRESENCE and stops there. Measured twice on
# this machine 2026-09-08, and confirmed by the merger: change the single
# PowerShell line in _PS_TEMPLATE
#
#     end_boundary = [string]$tr.EndBoundary
#
# to
#
#     end_boundary = $null
#
# and ConvertTo-Json STILL EMITS THE KEY. Every fixture arm and every
# key-presence arm above stays green while the tool has stopped reading the one
# field it exists to read - the field whose expiry is the whole first finding.
#
# So this arm compares the VALUE the probe reports against what the scheduler
# independently reports for the same triggers, through a separate Get- of its
# own. Nulling the probe line makes the two disagree and this arm goes red.
#
# WHAT IT DISCOVERS RATHER THAN NAMES. A read-only census of 314 triggers
# across every registered task on this machine on 2026-09-08 found EXACTLY ONE
# carrying a non-empty EndBoundary: \\ResinCompute-Responder, with
# StartBoundary 2026-09-07T19:00:00, EndBoundary 2026-09-07T21:00:00,
# repetition PT5M for PT2H. The arm does NOT hardcode that name. A
# hand-maintained list of task names goes stale silently - measured twice in
# this tree - and that task is a trial the operator may unregister this week.
# It asks the scheduler which task carries an EndBoundary and asserts against
# whatever comes back.
#
# WHEN IT SKIPS. On a machine where no registered task carries an EndBoundary
# there is nothing to compare and the arm skips, naming that as the reason. A
# near-always-skipping arm would be close to the vacuous guarantee it replaces,
# so the non-vacuity arm below it runs EVERYWHERE, on no PowerShell at all, and
# demonstrates on the measured fixture that a nulled value walks straight
# through the key-presence check and is caught by the value check.
#
# READ ONLY, like everything else here. Get-ScheduledTask and nothing else. No
# task is registered, modified, enabled, disabled or unregistered.

_ENDBOUNDARY_DISCOVERY = """
$ErrorActionPreference='Stop'
$all = @(Get-ScheduledTask)
$uniq = @($all | Group-Object TaskName | Where-Object { $_.Count -eq 1 } | ForEach-Object { $_.Group[0] })
$hit = $null
foreach ($t in $uniq) {
    if ($t.TaskName -notmatch '^[A-Za-z0-9 ._-]{1,200}$') { continue }
    $has = $false
    foreach ($tr in @($t.Triggers | Where-Object { $null -ne $_ })) {
        if (([string]$tr.EndBoundary).Trim() -ne '') { $has = $true }
    }
    if ($has) { $hit = $t; break }
}
if ($null -eq $hit) {
    [pscustomobject]@{ total = $all.Count; found = $false } | ConvertTo-Json -Compress
    exit 0
}
$ebs = @()
foreach ($tr in @($hit.Triggers | Where-Object { $null -ne $_ })) { $ebs += [string]$tr.EndBoundary }
[pscustomobject]@{
    total = $all.Count
    found = $true
    name = [string]$hit.TaskName
    path = [string]$hit.TaskPath
    end_boundaries = @($ebs)
} | ConvertTo-Json -Compress -Depth 5
"""


def _end_boundaries_reported_by(payload):
    """The ordered EndBoundary VALUES a probe payload carries, one per trigger.

    Absent, null and empty all normalise to the empty string, which is exactly
    the collapse the value arm needs: a probe emitting the key with nothing in
    it must be indistinguishable here from a probe not emitting it at all.
    """
    triggers = payload.get("triggers") or []
    return [str((raw or {}).get("end_boundary") or "").strip() for raw in triggers]


class _EndBoundaryPick(typing.NamedTuple):
    status: str
    name: str | None
    path: str | None
    values: list[str]
    detail: str


def _a_task_carrying_an_end_boundary() -> _EndBoundaryPick:
    """Ask the scheduler, read only, for one task whose triggers carry one.

    THE SAME ROOT CAUSE AS _real_task_names, in the arm that matters most. The
    version this replaces collapsed a non-zero exit, an empty stdout and a
    genuine found=false into one (None, None, None), and its single caller
    skipped on all three with a message blaming the machine. This is THE ONLY
    ARM IN THIS FILE THAT PINS THE ENDBOUNDARY VALUE - the field whose expiry
    is the whole finding the tool exists for - so a discovery failure that
    reads as a skip silently retires the guarantee.

    FAILED must fail; only NONE may skip.
    """
    exe = liveness._powershell_executable()
    try:
        done = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", _ENDBOUNDARY_DISCOVERY],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _EndBoundaryPick("FAILED", None, None, [], f"could not be launched: {type(exc).__name__}")
    return _classify_end_boundary_pick(done.returncode, done.stdout)


def _classify_end_boundary_pick(returncode: int, stdout: str) -> _EndBoundaryPick:
    """The pure half, so every FAILED branch is testable off Windows."""
    if returncode != 0:
        return _EndBoundaryPick("FAILED", None, None, [], f"the census exited {returncode}")
    if not stdout.strip():
        return _EndBoundaryPick("FAILED", None, None, [], "the census exited 0 but printed nothing")
    try:
        got = json.loads(stdout.strip())
    except ValueError:
        return _EndBoundaryPick("FAILED", None, None, [], "the census printed something that is not JSON")
    if not isinstance(got, dict) or "total" not in got:
        return _EndBoundaryPick("FAILED", None, None, [], "the census printed no task total")
    try:
        total = int(got["total"])
    except (TypeError, ValueError):
        return _EndBoundaryPick("FAILED", None, None, [], "the census printed a total that is not a number")
    if total < _MIN_ENUMERATED_TASKS:
        return _EndBoundaryPick(
            "FAILED", None, None, [],
            "the census saw no scheduled task at all, which is indistinguishable from a census "
            "that did not run",
        )
    if not got.get("found"):
        return _EndBoundaryPick(
            "NONE", None, None, [],
            f"the census RAN and read the triggers of {total} scheduled tasks, and none of them "
            "carries a non-empty EndBoundary",
        )
    name = got.get("name") or None
    if name is None:
        return _EndBoundaryPick("FAILED", None, None, [], "the census reported found=true with no name")
    raw = got.get("end_boundaries")
    # ConvertTo-Json under Windows PowerShell 5.1 can collapse a one-element
    # array to a scalar. Normalising here rather than trusting the shape.
    if not isinstance(raw, list):
        raw = [raw]
    values = [str(value or "").strip() for value in raw]
    if not any(values):
        return _EndBoundaryPick(
            "FAILED", None, None, values,
            f"the census named {name} as carrying an EndBoundary and then reported none - it "
            "contradicted itself, which is not evidence about the probe",
        )
    return _EndBoundaryPick(
        "FOUND", name, got.get("path") or None, values,
        f"the census read {total} scheduled tasks and {name} carries EndBoundary values {values}",
    )


def test_non_vacuity_neither_selection_helper_can_report_a_failure_as_an_empty_machine():
    # THE TWO SIBLINGS OF THE SAME ROOT CAUSE, both measured on 2026-09-08 to
    # collapse a failed enumeration into the same answer as a machine that
    # simply holds no such task. Making both exit 3 gave 65 passed, 3 skipped,
    # exit 0, with every skip text blaming the machine.
    #
    # This arm runs EVERYWHERE, including where _WINDOWS_ONLY skips everything
    # else in this section, because the classifiers are pure.
    for returncode, stdout, why in (
        (3, "", "non-zero exit"),
        (0, "", "exit 0 with no output"),
        (0, "not json", "exit 0 with unparseable output"),
        (0, '{"root": "Alpha"}', "exit 0 with no task total"),
        (0, '{"total": "many"}', "exit 0 with a total that is not a number"),
        (0, '{"total": 0}', "exit 0 having enumerated nothing"),
    ):
        assert _classify_task_pick(returncode, stdout).status == "FAILED", (
            f"the task-selection helper reported {why} as something other than a failure"
        )
        assert _classify_end_boundary_pick(returncode, stdout).status == "FAILED", (
            f"the EndBoundary census reported {why} as something other than a failure"
        )

    # POSITIVE CONTROLS. A run that really happened must NOT read FAILED, or
    # both classifiers could return FAILED unconditionally and pass the above.
    ran = _classify_task_pick(0, '{"total": 265, "root": "Alpha", "deep": "Beta", "deep_path": "\\\\X\\\\"}')
    assert ran.status == "RAN"
    assert (ran.root, ran.deep, ran.deep_path) == ("Alpha", "Beta", "\\X\\")

    # RAN AND FOUND NOTHING SUITABLE is still RAN, and the caller skips on the
    # None rather than on the status - the two are now different facts.
    empty = _classify_task_pick(0, '{"total": 265, "root": "", "deep": "", "deep_path": ""}')
    assert empty.status == "RAN"
    assert empty.root is None and empty.deep is None

    census_none = _classify_end_boundary_pick(0, '{"total": 265, "found": false}')
    assert census_none.status == "NONE"

    census_hit = _classify_end_boundary_pick(
        0, '{"total": 265, "found": true, "name": "Alpha", "path": "\\\\", '
           '"end_boundaries": ["2026-09-07T21:00:00"]}'
    )
    assert census_hit.status == "FOUND"
    assert census_hit.values == ["2026-09-07T21:00:00"]

    # The 5.1 scalar collapse, and the self-contradiction case: a census that
    # names a task as carrying an EndBoundary and then reports none has not
    # found anything, whatever its own flag says.
    scalar = _classify_end_boundary_pick(
        0, '{"total": 265, "found": true, "name": "Alpha", "path": "\\\\", '
           '"end_boundaries": "2026-09-07T21:00:00"}'
    )
    assert scalar.status == "FOUND" and scalar.values == ["2026-09-07T21:00:00"]
    contradiction = _classify_end_boundary_pick(
        0, '{"total": 265, "found": true, "name": "Alpha", "path": "\\\\", "end_boundaries": [""]}'
    )
    assert contradiction.status == "FAILED"

    # And the three outcomes of each are genuinely distinct.
    assert len({_classify_task_pick(3, "").status, ran.status}) == 2
    assert len({_classify_end_boundary_pick(3, "").status, census_none.status, census_hit.status}) == 3


def test_non_vacuity_a_nulled_end_boundary_walks_through_the_key_presence_check():
    # This is the hole, demonstrated on the measured payload with no PowerShell
    # anywhere: the key survives, the value does not, and only one of the two
    # checks notices. It runs on every machine, so the guarantee below is not
    # carried entirely by an arm that may skip.
    _, trigger_keys = _keys_the_parser_reads()
    assert "end_boundary" in trigger_keys, "the parser must read the field this arm is about"

    real = json.loads(json.dumps(MEASURED_DORMANT))
    nulled = json.loads(json.dumps(MEASURED_DORMANT))
    for trig in nulled["triggers"]:
        trig["end_boundary"] = None

    # The key-presence check, run verbatim against the nulled payload: silent.
    for index, trig in enumerate(nulled["triggers"]):
        gap = sorted(k for k in trigger_keys if k not in trig)
        assert gap == [], f"trigger {index} still carries every key the parser reads, which is the point"

    # The value check, on the same two payloads: not silent.
    assert _end_boundaries_reported_by(real) == ["2026-09-07T21:00:00"]
    assert _end_boundaries_reported_by(nulled) == [""]
    assert _end_boundaries_reported_by(nulled) != _end_boundaries_reported_by(real)

    # And the consequence, which is what makes it a defect rather than a
    # cosmetic gap. On the measured responder the verdict happens to SURVIVE
    # the nulling, because that trigger's repetition Duration PT2H closes the
    # very same window from the other side - so the flip is shown on the shape
    # that carries no second signal: a repeating trigger with an expiry and no
    # repetition Duration behind it. Both are asserted, because a reader who
    # believes the responder flips will draw the wrong conclusion from the
    # value arm going red.
    assert _verdict(real).status == "DORMANT"
    assert _verdict(nulled).status == "DORMANT", (
        "on THIS fixture the repetition Duration PT2H independently closes the window"
    )

    bare = _payload(trigger_repetition_duration="")
    assert _verdict(bare).status == "DORMANT", "the expiry alone must still carry it"
    bare_nulled = _payload(trigger_repetition_duration="", trigger_end_boundary=None)
    assert _verdict(bare_nulled).status == "LIVE", (
        "with the EndBoundary value dropped and no repetition Duration behind it, a trigger that "
        "expired last night reads as a live 5-minute tick - the exact wrong answer of the finding"
    )


@_WINDOWS_ONLY
def test_the_real_probe_reports_the_end_boundary_value_and_not_just_the_key():
    pick = _a_task_carrying_an_end_boundary()
    assert pick.status != "FAILED", (
        "the EndBoundary census did not run, and this is the ONLY arm pinning the value the tool "
        f"exists to read - a skip here would retire that guarantee silently: {pick.detail}"
    )
    name, path, expected = pick.name, pick.path, pick.values
    if pick.status == "NONE":
        pytest.skip(
            f"{pick.detail}, so there is no value for the probe to be compared against. The census "
            "RAN - this is the machine and not a failed enumeration - and "
            "test_non_vacuity_a_nulled_end_boundary_walks_through_the_key_presence_check still "
            "runs here on the measured fixture"
        )
    try:
        liveness.validate_task_path(path or "")
    except ValueError:
        pytest.skip(f"the discovered task sits under TaskPath {path!r}, which the module's own gate refuses")

    payload = liveness.collect_facts(name, task_path=path)
    assert payload.get("exists") is True, f"{name} was enumerated a moment ago and must still exist"
    assert payload.get("ambiguous") is False, "the enumeration filtered to names unique across TaskPaths"

    observed = _end_boundaries_reported_by(payload)
    assert any(observed), (
        f"the scheduler independently reports EndBoundary values {expected} for {path}{name}, and the "
        "probe reported none at all - it is emitting the key and dropping the value"
    )
    # Multiset rather than ordered, so this is a statement about the VALUES and
    # never about the order two separate enumerations happened to list them in.
    assert sorted(observed) == sorted(expected), (
        f"the probe reported EndBoundary values {observed} for {path}{name} while the scheduler "
        f"independently reports {expected}"
    )

    # A value that reaches the payload and cannot be read is no better than one
    # that never arrived - _parse_dt returns None for both.
    for value in observed:
        if value:
            assert liveness._parse_dt(value) is not None, f"the probe reported {value!r}, which will not parse"

    # It must survive the parser onto the dataclass the verdict actually reads.
    facts = liveness.parse_facts(payload)
    assert sorted((t.end_boundary or "").strip() for t in facts.triggers) == sorted(expected)

    # And reach the operator's report, which is where an expiry is read from.
    report = liveness.render(liveness.verdict(facts))
    for value in expected:
        if value:
            assert value in report, f"EndBoundary {value} never reached the rendered report"

    print(f"\n[end-boundary value arm] RAN against {path}{name}, EndBoundary values {expected}")
