"""check_task_liveness.py - does a Windows scheduled task ACTUALLY still fire?

    python ops/check_task_liveness.py ResinCompute-Responder
    python ops/check_task_liveness.py Backup --task-path '\\Microsoft\\Windows\\CloudRestore\\'

WHY THIS EXISTS, and it is a measurement rather than a preference. On
2026-09-08 this machine reported, for ResinCompute-Responder:

    Get-ScheduledTask      State          : Ready
    Get-ScheduledTaskInfo  LastTaskResult : 0
    Get-ScheduledTaskInfo  LastRunTime    : 2026-09-07 20:55
    Get-ScheduledTaskInfo  NextRunTime    : <empty>
    the only trigger       EndBoundary    : 2026-09-07T21:00:00

Two of those five read as a healthy task and three say it is finished. The
task's single trigger had expired the previous evening and it will never fire
again, yet State still said Ready and the last result was still 0. A session
hand-off read "Ready" and asserted a live 5-minute tick, and was wrong by
twenty-four hours.

    A TASK STATE STRING NAMES A STATE, NOT A CAPABILITY.

"Ready" means "not currently running and not disabled". It is reported forever
by a task whose every trigger has expired, and by a task nobody will ever start
again. It is therefore REPORTED by this tool and never used as the verdict.

THE VERDICT RESTS ONLY ON POSITIVE EVIDENCE OF A FUTURE FIRING:

  1. NextRunTime is present and lies in the future, OR
  2. at least one trigger is Enabled AND some reading of its own boundaries
     says a firing is still to come.

ABSENCE OF AN ENDBOUNDARY IS NOT RULE 2, AND THE EARLIER VERSION OF THIS FILE
GOT THAT WRONG. It read "EndBoundary absent or future" as live, which is
absence of evidence dressed as evidence. Measured on this machine 2026-09-08,
the scheduled task RunPlatformExperienceHelper_Metrics under TaskPath
'\\GoogleUserPEH\\' reported State Ready, NextRunTime EMPTY, one enabled
MSFT_TaskTimeTrigger with StartBoundary 2026-07-08T19:37:35-05:00, NO
EndBoundary and NO repetition interval. That is a one-shot that fired two
months ago and will never fire again, and the old rule called it LIVE.

So a trigger with no EndBoundary is read through its StartBoundary and its
repetition instead:

  - no StartBoundary either (a boot or logon trigger) -> LIVE, it fires again
    on every occurrence of its event
  - StartBoundary in the future                       -> LIVE, it has not run
  - StartBoundary in the past, no repetition interval -> SPENT one-shot
  - StartBoundary in the past, repetition interval    -> LIVE, unless the
    repetition Duration is present and StartBoundary + Duration is already
    past, in which case the repetition window has CLOSED and it is spent

AN UNREADABLE BOUNDARY IS NEVER LIVE. _parse_dt returns None on a value it
cannot parse, and the earlier version let that default to "not expired", so a
malformed EndBoundary in the past read LIVE. That is fail-open on exactly the
field the tool exists to read. An unreadable boundary or duration now removes
the trigger from the evidence AND, when nothing else carries the task, makes
the whole verdict UNKNOWN rather than DORMANT - we do not know, and saying
DORMANT would be the same mistake pointed the other way.

The State string is allowed to TAKE LIVE AWAY and never to grant it: a Disabled
task does not fire whatever its triggers say. Veto, never vouch.

FIVE OUTCOMES. A task that is not registered at all is ABSENT, which is a
different thing from a registered task that has gone quiet, and collapsing them
would hide the difference between "the trial was torn down" and "the trial died
with the installer still believing in it". A name that matches MORE THAN ONE
task across TaskPaths is AMBIGUOUS: Windows allows the same TaskName under two
paths - measured on this machine, 'Backup', 'CreateObjectTask' and 'WiFiTask'
each match two - and answering about a silently picked one of them is worse
than refusing. Pass --task-path to disambiguate. UNKNOWN covers a probe that
failed and a task whose own boundaries could not be read.

Get-ScheduledTaskInfo is called with -InputObject and never with -TaskName.
-TaskName searches only TaskPath '\\' and throws "The system cannot find the
file specified" for a task anywhere else, which the old code reported as
"the scheduler refused the query - the task may need a different account".
Measured 2026-09-08 against RunPlatformExperienceHelper_Metrics.

THIS TOOL IS READ ONLY. It never starts, stops, disables, registers or
unregisters anything, and tests/test_task_liveness.py scans this file for the
verbs that would. Stdlib only; Windows PowerShell supplies the facts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

EXIT_LIVE = 0
EXIT_DORMANT = 1
EXIT_ABSENT = 2
EXIT_UNKNOWN = 3
EXIT_AMBIGUOUS = 4

DEFAULT_TIMEOUT_SECONDS = 60

# PowerShell's ConsoleHost exit codes for "the host itself never got going".
# These are NOT this tool's exit codes - see EXIT_* above for those - and they
# are NOT a script's exit code either, because on these two the script never
# ran. Named because a bare 4294901760 in a conditional is unreadable and gets
# re-derived wrongly later.
#
# 0xFFFF0000 is ExitCodeInitFailure. Measured 2026-09-11: powershell.exe with a
# broken SystemRoot returns it with EMPTY stdout and a UTF-16LE stderr reading
# "Internal Windows PowerShell error.  Loading managed Windows PowerShell
# failed with error 8009001d" - the CLR never loaded. A control set (no PATH,
# no APPDATA, no USERPROFILE, no COMSPEC, no windir, TEMP pointing nowhere)
# each returned 0, while a parse error, a command-not-found and a `throw` each
# returned 1. So this code is specific to a host that could not start, and the
# generic account-or-TaskPath headline is FALSE for it.
#
# 0xFFFE0000 is the sibling ExitCodeCtrlBreak.
_PS_HOST_EXIT_INIT_FAILURE = 4294901760  # 0xFFFF0000
_PS_HOST_EXIT_CTRL_BREAK = 4294836224  # 0xFFFE0000

# A task name is interpolated into a PowerShell single-quoted literal, so it is
# validated rather than trusted. Letters, digits, space, and the four
# punctuation characters real task names use.
_TASK_NAME_RE = re.compile(r"^[A-Za-z0-9 ._\\-]{1,200}$")

# A TaskPath is a backslash-delimited folder path that always starts and ends
# with a backslash: '\' for the root, '\Microsoft\Windows\CloudRestore\' for a
# folder. Same interpolation, same reason for validating it.
_TASK_PATH_RE = re.compile(r"^\\(?:[A-Za-z0-9 ._-]+\\)*$")

# ISO 8601 durations as the Task Scheduler writes them: PT5M, PT2H, P1DT12H.
# Weeks and months are deliberately NOT accepted - a repetition interval is
# capped at 31 days, so anything carrying W or a month is a shape this tool has
# never seen and must not guess at. An unparsed duration fails CLOSED.
_DURATION_RE = re.compile(
    r"^P(?!$)(?:(\d+)D)?(?:T(?!$)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)

_NOT_SET = "(not set)"


class ProbeError(Exception):
    """The scheduler could not be read.

    Carries the raw diagnostic separately from the friendly message so a caller
    can print one and log the other - a raw scheduler error string must never
    reach an operator-facing surface.
    """

    def __init__(self, message: str, raw: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.raw = raw


@dataclass
class TriggerFacts:
    kind: str = "(unknown trigger)"
    enabled: bool = False
    start_boundary: str | None = None
    end_boundary: str | None = None
    repetition_interval: str | None = None
    repetition_duration: str | None = None


@dataclass
class TaskFacts:
    task_name: str = ""
    exists: bool = False
    state: str = _NOT_SET
    next_run_time: str | None = None
    last_run_time: str | None = None
    last_task_result: int | None = None
    triggers: list[TriggerFacts] = field(default_factory=list)
    task_path: str = ""
    ambiguous: bool = False
    matches: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    status: str = "UNKNOWN"
    task_name: str = ""
    state: str = _NOT_SET
    next_run_time: str | None = None
    last_run_time: str | None = None
    last_task_result: int | None = None
    triggers: list[TriggerFacts] = field(default_factory=list)
    live_trigger_indexes: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    friendly_error: str = ""
    task_path: str = ""
    matches: list[str] = field(default_factory=list)


def _names_disabled(state: str) -> bool:
    """Does this State string name Disabled ANYWHERE in it?

    Token-wise rather than by equality. If the array case in the probe were
    ever bypassed, PowerShell would render two matched tasks' states as the
    single string "Disabled Ready", and an equality veto would miss it and
    call the pair LIVE. The probe answers that shape as AMBIGUOUS and never
    lets it reach here, so this is the second lock on the same door.
    """
    return "disabled" in state.strip().lower().split()


def validate_task_name(task_name: str) -> str:
    """Return the name, or raise ValueError if it is not a plain task name."""
    if not isinstance(task_name, str) or not _TASK_NAME_RE.match(task_name):
        raise ValueError("task name must be letters, digits, space, dot, underscore, hyphen or backslash")
    return task_name


def validate_task_path(task_path: str) -> str:
    """Return the path, or raise ValueError if it is not a plain TaskPath.

    The empty string is allowed and means "do not filter by path".
    """
    if task_path == "":
        return ""
    if not isinstance(task_path, str) or not _TASK_PATH_RE.match(task_path):
        raise ValueError(
            "task path must start and end with a backslash, for example \\ or \\Microsoft\\Windows\\"
        )
    return task_path


def _parse_dt(value: object) -> dt.datetime | None:
    """Parse a scheduler timestamp into a NAIVE LOCAL wall-clock datetime.

    Returns None for an absent value AND for an unreadable one. Every caller
    must therefore distinguish "there was nothing to read" from "there was
    something and it could not be read" by checking the source string itself -
    conflating those two is the fail-open bug this module was refuted for.

    The offset, when one is present, is DISCARDED rather than converted. That
    is deliberate. StartBoundary and EndBoundary come out of the task XML with
    no offset at all and mean local wall-clock time; NextRunTime and LastRunTime
    come back from Get-ScheduledTaskInfo carrying the machine's current offset
    for the same wall-clock instant. Dropping the offset puts all four on one
    scale and keeps the comparison stable across a DST boundary, where
    converting would silently shift a boundary by an hour.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)


def _parse_duration(value: object) -> dt.timedelta | None:
    """Parse an ISO 8601 duration into a timedelta, or None if unreadable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = _DURATION_RE.match(text)
    if not match:
        return None
    days, hours, minutes, seconds = match.groups()
    return dt.timedelta(
        days=int(days or 0),
        hours=int(hours or 0),
        minutes=int(minutes or 0),
        seconds=float(seconds or 0),
    )


def parse_facts(payload: dict) -> TaskFacts:
    """Turn the PowerShell probe's JSON payload into facts.

    Pure - no subprocess, no clock. This is what makes the verdict unit
    testable from fixtures on a machine carrying no such task.
    """
    if not payload.get("exists", False):
        return TaskFacts(task_name=str(payload.get("task_name", "") or ""), exists=False)

    if payload.get("ambiguous", False):
        return TaskFacts(
            task_name=str(payload.get("task_name", "") or ""),
            exists=True,
            ambiguous=True,
            matches=[str(m) for m in (payload.get("matches") or [])],
        )

    triggers = []
    for raw in payload.get("triggers") or []:
        triggers.append(
            TriggerFacts(
                kind=str(raw.get("kind") or "(unknown trigger)"),
                enabled=bool(raw.get("enabled", False)),
                start_boundary=raw.get("start_boundary") or None,
                end_boundary=raw.get("end_boundary") or None,
                repetition_interval=raw.get("repetition_interval") or None,
                repetition_duration=raw.get("repetition_duration") or None,
            )
        )

    result = payload.get("last_task_result")
    return TaskFacts(
        task_name=str(payload.get("task_name", "") or ""),
        exists=True,
        state=str(payload.get("state") or _NOT_SET),
        next_run_time=payload.get("next_run_time") or None,
        last_run_time=payload.get("last_run_time") or None,
        last_task_result=int(result) if isinstance(result, int) else None,
        triggers=triggers,
        task_path=str(payload.get("task_path") or ""),
    )


def evaluate_trigger(trigger: TriggerFacts, now: dt.datetime) -> tuple[bool, str, bool]:
    """Read ONE trigger. Returns (is_live, why, was_unreadable).

    is_live is POSITIVE evidence that this trigger has a firing still to come.
    was_unreadable says a boundary or duration was present and could not be
    parsed, which is neither live nor safely dead.
    """
    if not trigger.enabled:
        return False, "is DISABLED", False

    if trigger.end_boundary:
        end = _parse_dt(trigger.end_boundary)
        if end is None:
            return (
                False,
                f"carries an UNREADABLE EndBoundary ({trigger.end_boundary}) - "
                "a boundary that cannot be read is not evidence of anything",
                True,
            )
        if end <= now:
            return False, f"EXPIRED at EndBoundary {trigger.end_boundary}", False
        return True, f"is enabled and its EndBoundary {trigger.end_boundary} is still ahead", False

    # No EndBoundary at all. Its ABSENCE says nothing - read the start and the
    # repetition instead.
    if not trigger.start_boundary:
        return (
            True,
            "is enabled with neither a StartBoundary nor an EndBoundary - "
            "a trigger of this shape fires again on every occurrence of its event",
            False,
        )

    start = _parse_dt(trigger.start_boundary)
    if start is None:
        return (
            False,
            f"carries an UNREADABLE StartBoundary ({trigger.start_boundary}) - "
            "with no EndBoundary either, nothing about it can be read as evidence",
            True,
        )
    if start > now:
        return True, f"is enabled and its StartBoundary {trigger.start_boundary} has not arrived yet", False

    interval = _parse_duration(trigger.repetition_interval)
    if trigger.repetition_interval and interval is None:
        return (
            False,
            f"carries an UNREADABLE repetition interval ({trigger.repetition_interval})",
            True,
        )
    if interval is None:
        return (
            False,
            f"is a ONE-SHOT whose StartBoundary {trigger.start_boundary} is already past and which "
            "repeats on no interval - it has fired and is SPENT",
            False,
        )

    if trigger.repetition_duration:
        window = _parse_duration(trigger.repetition_duration)
        if window is None:
            return (
                False,
                f"carries an UNREADABLE repetition duration ({trigger.repetition_duration})",
                True,
            )
        closes = start + window
        if closes <= now:
            return (
                False,
                f"repeated every {trigger.repetition_interval} for {trigger.repetition_duration} from "
                f"{trigger.start_boundary}, and that window CLOSED at {closes.isoformat()} - it is SPENT",
                False,
            )
        return (
            True,
            f"repeats every {trigger.repetition_interval} until {closes.isoformat()}, which is still ahead",
            False,
        )

    return True, f"repeats every {trigger.repetition_interval} with no closing boundary", False


def verdict(facts: TaskFacts, now: dt.datetime | None = None) -> Verdict:
    """LIVE, DORMANT, ABSENT, AMBIGUOUS or UNKNOWN, from positive evidence only."""
    now = now or dt.datetime.now()

    out = Verdict(
        task_name=facts.task_name,
        state=facts.state,
        next_run_time=facts.next_run_time,
        last_run_time=facts.last_run_time,
        last_task_result=facts.last_task_result,
        triggers=list(facts.triggers),
        task_path=facts.task_path,
        matches=list(facts.matches),
    )

    if not facts.exists:
        out.status = "ABSENT"
        out.reasons.append("the scheduler holds no task by this name - it is not registered")
        return out

    if facts.ambiguous:
        out.status = "AMBIGUOUS"
        out.reasons.append(
            f"{len(facts.matches)} registered tasks share this name, under different TaskPaths - "
            "no single one of them can be answered about"
        )
        for path in facts.matches:
            out.reasons.append(f"  matched under TaskPath {path}")
        out.reasons.append("re-run with --task-path set to exactly one of the paths above")
        return out

    # Evidence 1: a NextRunTime the scheduler itself has committed to.
    next_run = _parse_dt(facts.next_run_time)
    next_run_is_future = next_run is not None and next_run > now
    if next_run_is_future:
        out.reasons.append(f"NextRunTime {facts.next_run_time} is in the future")
    elif facts.next_run_time and next_run is None:
        out.reasons.append(f"NextRunTime {facts.next_run_time} could not be read at all")
    elif next_run is not None:
        out.reasons.append(f"NextRunTime {facts.next_run_time} has already passed - not evidence of a future firing")
    else:
        out.reasons.append("NextRunTime is empty - the scheduler names no upcoming run")

    # Evidence 2: a trigger that reads as having a firing still to come.
    unreadable = False
    for index, trigger in enumerate(facts.triggers):
        is_live, why, was_unreadable = evaluate_trigger(trigger, now)
        unreadable = unreadable or was_unreadable
        if is_live:
            out.live_trigger_indexes.append(index)
        out.reasons.append(f"trigger {index + 1} ({trigger.kind}) {why}")

    if not facts.triggers:
        out.reasons.append("the task carries NO triggers at all - only a manual start would run it")

    live = next_run_is_future or bool(out.live_trigger_indexes)

    # The State string may VETO. It may never vouch.
    if live and _names_disabled(facts.state):
        live = False
        out.reasons.append("the task State is Disabled, which overrides any trigger that still looks live")

    if live:
        out.status = "LIVE"
    elif unreadable:
        out.status = "UNKNOWN"
        out.reasons.append(
            "nothing readable says this task will fire again, but a boundary could not be read - "
            "an unreadable boundary is reported as UNKNOWN and never rounded down to DORMANT"
        )
    else:
        out.status = "DORMANT"

    if unreadable and out.status == "LIVE":
        out.caveats.append(
            "one or more triggers carry a boundary that could not be read - the LIVE verdict rests "
            "only on the triggers that could be"
        )
    if out.live_trigger_indexes and not next_run_is_future:
        out.caveats.append(
            "a trigger still looks live but the scheduler reports no NextRunTime - "
            "check whether that trigger is a one-shot that has already fired"
        )
    if len(out.live_trigger_indexes) not in (0, len(facts.triggers)):
        out.caveats.append("some triggers are live and some are not - read the per-trigger lines above")
    if out.status in ("DORMANT", "UNKNOWN") and "ready" in facts.state.strip().lower().split():
        out.caveats.append(
            "State reads Ready and LastTaskResult may read 0 - neither says the task will fire again"
        )

    return out


def render(result: Verdict) -> str:
    """The report, in 7-bit ASCII. The evidence travels with the verdict."""
    name = result.task_name or "(unnamed)"
    lines = [
        "=" * 72,
        f"  {result.status}  -  {name}",
        "=" * 72,
    ]

    if result.friendly_error:
        lines.append(f"  {result.friendly_error}")
        lines.append("")
        lines.append("  No verdict was reached. The raw diagnostic was written to stderr.")
        lines.append("=" * 72)
        return "\n".join(lines)

    if result.status == "ABSENT":
        lines.append("  Not registered. This is NOT the same as a task that has gone quiet -")
        lines.append("  nothing here has expired, there is simply nothing here.")
        lines.append("=" * 72)
        return "\n".join(lines)

    if result.status == "AMBIGUOUS":
        lines.append("  More than one registered task carries this name. Windows allows that,")
        lines.append("  and answering about a silently chosen one of them would be worse than")
        lines.append("  refusing to answer at all.")
        lines.append("")
        for reason in result.reasons:
            lines.append(f"    - {reason}")
        lines.append("=" * 72)
        return "\n".join(lines)

    result_text = _NOT_SET if result.last_task_result is None else str(result.last_task_result)
    lines.extend(
        [
            "",
            "  REPORTED, not the verdict:",
            f"    State          : {result.state}",
            f"    LastTaskResult : {result_text}",
            f"    TaskPath       : {result.task_path or _NOT_SET}",
            "",
            "  Evidence:",
            f"    NextRunTime    : {result.next_run_time or _NOT_SET}",
            f"    LastRunTime    : {result.last_run_time or _NOT_SET}",
        ]
    )

    if not result.triggers:
        lines.append("    Triggers       : none")
    else:
        lines.append(f"    Triggers       : {len(result.triggers)}")
        for index, trigger in enumerate(result.triggers):
            mark = "LIVE   " if index in result.live_trigger_indexes else "DEAD   "
            lines.append(f"      [{mark}] {index + 1}. {trigger.kind}")
            lines.append(f"                 Enabled       : {trigger.enabled}")
            lines.append(f"                 StartBoundary : {trigger.start_boundary or _NOT_SET}")
            lines.append(f"                 EndBoundary   : {trigger.end_boundary or _NOT_SET}")
            lines.append(f"                 Repeats every : {trigger.repetition_interval or _NOT_SET}")
            lines.append(f"                 Repeats for   : {trigger.repetition_duration or _NOT_SET}")

    lines.append("")
    lines.append("  Why:")
    for reason in result.reasons:
        lines.append(f"    - {reason}")

    if result.caveats:
        lines.append("")
        lines.append("  Read also:")
        for caveat in result.caveats:
            lines.append(f"    ! {caveat}")

    lines.append("=" * 72)
    return "\n".join(lines)


# --- The PowerShell probe -------------------------------------------------
#
# Read-only by construction: Get-ScheduledTask and Get-ScheduledTaskInfo and
# nothing else. Timestamps are formatted in PowerShell rather than left to
# ConvertTo-Json, because Windows PowerShell 5.1 serialises a DateTime as
# "/Date(1757...)/" while PowerShell 7 emits ISO 8601 - formatting here makes
# the payload identical under both. The 'o' round-trip format is avoided in
# favour of a second-resolution pattern: 'o' emits seven fractional digits and
# datetime.fromisoformat does not accept seven.
#
# Get-ScheduledTaskInfo takes -InputObject and NEVER -TaskName. -TaskName looks
# only in TaskPath '\' and throws for a task in any folder; -InputObject
# resolves the task object that Get-ScheduledTask already found, wherever it
# lives. Measured 2026-09-08.
#
# Get-ScheduledTask -TaskName can return MORE THAN ONE task, because a name is
# unique only within a TaskPath. The array case is answered explicitly rather
# than collapsed with [string], which would render two states as "Disabled
# Ready" and defeat the Disabled veto outright.

_PS_TEMPLATE = """
$ErrorActionPreference = 'Stop'
$n = '{task_name}'
$p = '{task_path}'
$all = @(Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue)
if ($p -ne '') {{ $all = @($all | Where-Object {{ $_.TaskPath -eq $p }}) }}
if ($all.Count -eq 0) {{
    [pscustomobject]@{{ exists = $false; task_name = $n }} | ConvertTo-Json -Depth 5 -Compress
    exit 0
}}
if ($all.Count -gt 1) {{
    [pscustomobject]@{{
        exists = $true
        ambiguous = $true
        task_name = $n
        matches = @($all | ForEach-Object {{ [string]$_.TaskPath }})
    }} | ConvertTo-Json -Depth 5 -Compress
    exit 0
}}
$t = $all[0]
$i = Get-ScheduledTaskInfo -InputObject $t
$fmt = 'yyyy-MM-ddTHH:mm:sszzz'
$next = $null
if ($null -ne $i.NextRunTime) {{ $next = $i.NextRunTime.ToString($fmt) }}
$last = $null
if ($null -ne $i.LastRunTime) {{ $last = $i.LastRunTime.ToString($fmt) }}
$trigs = @()
foreach ($tr in @($t.Triggers | Where-Object {{ $null -ne $_ }})) {{
    $ri = ''
    $rd = ''
    if ($null -ne $tr.Repetition) {{
        $ri = [string]$tr.Repetition.Interval
        $rd = [string]$tr.Repetition.Duration
    }}
    $trigs += [pscustomobject]@{{
        kind = [string]$tr.CimClass.CimClassName
        enabled = [bool]$tr.Enabled
        start_boundary = [string]$tr.StartBoundary
        end_boundary = [string]$tr.EndBoundary
        repetition_interval = $ri
        repetition_duration = $rd
    }}
}}
[pscustomobject]@{{
    exists = $true
    ambiguous = $false
    task_name = [string]$t.TaskName
    task_path = [string]$t.TaskPath
    state = [string]$t.State
    next_run_time = $next
    last_run_time = $last
    last_task_result = [int]$i.LastTaskResult
    triggers = @($trigs)
}} | ConvertTo-Json -Depth 5 -Compress
"""


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        found = shutil.which(candidate)
        if found:
            return found
    raise ProbeError(
        "no PowerShell interpreter was found on PATH",
        "shutil.which found none of: powershell.exe, powershell, pwsh.exe, pwsh",
    )


def collect_facts(task_name: str, timeout: int | None = None, task_path: str = "") -> dict:
    """Ask the Windows scheduler for the facts. Raises ProbeError on failure.

    The name and path gates run HERE, before the interpolation and before any
    subprocess, because this is the only caller of the PowerShell template.
    Deleting either line lets a shell metacharacter reach a PowerShell literal.
    """
    name = validate_task_name(task_name)
    path = validate_task_path(task_path)
    script = _PS_TEMPLATE.format(task_name=name, task_path=path)
    exe = _powershell_executable()
    argv = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]

    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout or DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("the scheduler did not answer in time", f"{type(exc).__name__}: {exc}") from exc
    except OSError as exc:
        raise ProbeError("the scheduler could not be reached", f"{type(exc).__name__}: {exc}") from exc

    if completed.returncode in (_PS_HOST_EXIT_INIT_FAILURE, _PS_HOST_EXIT_CTRL_BREAK):
        # The host never got going, so the query was never put to the scheduler
        # at all. Saying "refused" here, or naming an account or a TaskPath,
        # sends the operator hunting a privilege problem that does not exist.
        raise ProbeError(
            "the PowerShell interpreter failed to start, so the query never reached the scheduler",
            f"exit {completed.returncode}; stderr={completed.stderr.strip()}; stdout={completed.stdout.strip()}",
        )

    if completed.returncode != 0:
        raise ProbeError(
            "the scheduler refused the query - it may need a different account, or a different TaskPath",
            f"exit {completed.returncode}; stderr={completed.stderr.strip()}; stdout={completed.stdout.strip()}",
        )

    body = (completed.stdout or "").strip()
    if not body:
        raise ProbeError("the scheduler returned nothing to read", f"empty stdout; stderr={completed.stderr.strip()}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProbeError("the scheduler's answer could not be understood", f"{exc}; body={body[:400]}") from exc

    if not isinstance(payload, dict):
        raise ProbeError("the scheduler's answer had an unexpected shape", f"top level was {type(payload).__name__}")
    return payload


EXIT_BY_STATUS = {
    "LIVE": EXIT_LIVE,
    "DORMANT": EXIT_DORMANT,
    "ABSENT": EXIT_ABSENT,
    "UNKNOWN": EXIT_UNKNOWN,
    "AMBIGUOUS": EXIT_AMBIGUOUS,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_task_liveness.py",
        description=(
            "Report whether a Windows scheduled task will actually fire again. "
            "The State string is reported but is never the verdict."
        ),
    )
    parser.add_argument("task_name", help="scheduled task name, for example ResinCompute-Responder")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"seconds to wait for the scheduler (default {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--task-path",
        default="",
        help="TaskPath folder to disambiguate a name registered more than once, for example \\GoogleUserPEH\\",
    )
    args = parser.parse_args(argv)

    try:
        payload = collect_facts(args.task_name, timeout=args.timeout, task_path=args.task_path)
    except ValueError as exc:
        # A rejected task name or path. The message is already friendly and
        # carries no scheduler internals.
        print(render(Verdict(status="UNKNOWN", task_name="(rejected)", friendly_error=str(exc))))
        return EXIT_UNKNOWN
    except ProbeError as exc:
        print(f"[check_task_liveness] raw scheduler error: {exc.raw}", file=sys.stderr)
        print(render(Verdict(status="UNKNOWN", task_name=args.task_name, friendly_error=exc.message)))
        return EXIT_UNKNOWN

    result = verdict(parse_facts(payload))
    print(render(result))
    return EXIT_BY_STATUS.get(result.status, EXIT_UNKNOWN)


if __name__ == "__main__":
    raise SystemExit(main())
