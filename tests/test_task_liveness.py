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
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys

import pytest

from ops import check_task_liveness as liveness

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

# Verbs whose presence ANYWHERE in the module - not merely in the probe - would
# mean this tool had grown a way to change the machine. Matched by SHAPE, so a
# verb nobody enumerated is still caught the moment it is used on a noun.
_MUTATING_VERB_RE = re.compile(
    r"\b(?:Set|Remove|New|Start|Stop|Register|Unregister|Enable|Disable|Add|Clear|Out|Write|"
    r"Move|Rename|Invoke|Restart|Suspend|Resume|Export|Import|Copy)-[A-Za-z][A-Za-z0-9]*\b"
)

# A PowerShell command is Verb-Noun. Case-insensitive because PowerShell is:
# `remove-item` runs exactly as well as `Remove-Item`.
_PS_COMMAND_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*-[A-Za-z][A-Za-z0-9]*")


def _commands_in(script: str) -> set[str]:
    """Every command-shaped token in EXECUTABLE position in a PowerShell script.

    Single-quoted literals are blanked first: they are inert data, and blanking
    them keeps the datetime format 'yyyy-MM-ddTHH:mm:sszzz' from reading as a
    command while leaving any injected command outside the quotes visible.
    """
    inert = re.sub(r"'[^']*'", "''", script)
    return set(_PS_COMMAND_RE.findall(inert))


def test_the_probe_is_built_only_from_sanctioned_read_only_commands():
    found = _commands_in(liveness._PS_TEMPLATE)
    assert found, "the scan found no command at all in the probe - it is not reading the template"
    assert "Get-ScheduledTask" in found, "the scan must see the probe's real content, not an empty haystack"

    unsanctioned = sorted(name for name in found if name not in _SANCTIONED_PROBE_CMDLETS)
    assert unsanctioned == [], (
        f"the probe carries {unsanctioned}, which is not in the sanctioned read-only set. "
        "A read-only liveness probe runs Get- and nothing else."
    )

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
    ]
    for line in injections:
        mutated = line + "\n" + liveness._PS_TEMPLATE
        unsanctioned = sorted(n for n in _commands_in(mutated) if n not in _SANCTIONED_PROBE_CMDLETS)
        assert unsanctioned, f"the allowlist scan let {line!r} through"

    # The positive control, through the same scan: the pristine template passes.
    assert sorted(n for n in _commands_in(liveness._PS_TEMPLATE) if n not in _SANCTIONED_PROBE_CMDLETS) == []


def test_the_module_never_stops_modifies_or_unregisters_anything():
    # The whole-file half, also by SHAPE rather than by a list of names: any
    # Verb-Noun built on a mutating verb, anywhere in the module.
    source = liveness.__file__
    with open(source, encoding="ascii") as handle:
        body = handle.read()
    found = sorted(set(_MUTATING_VERB_RE.findall(body)))
    assert found == [], f"a read-only liveness probe must never carry {found}"
    for token in ("Stop-Process", "taskkill"):
        assert token not in body, f"a read-only liveness probe must never carry {token}"


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
    ):
        body = f"subprocess.run(['powershell', '-Command', '{verb_noun} -TaskName x'])"
        assert _MUTATING_VERB_RE.findall(body) == [verb_noun], f"the shape scan missed {verb_noun}"


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


def _real_task_names():
    """Ask the scheduler, read only, for one root task and one foldered task.

    Returns (root_name, deep_name, deep_path); any element may be None. Only
    names matching the module's own validator and carrying at least one trigger
    are offered, and only names that are UNIQUE across paths, so the arms below
    are not accidentally testing the ambiguity branch.
    """
    exe = liveness._powershell_executable()
    script = (
        "$ErrorActionPreference='Stop';"
        "$u = Get-ScheduledTask | Group-Object TaskName | Where-Object { $_.Count -eq 1 } |"
        " ForEach-Object { $_.Group[0] };"
        "$ok = @($u | Where-Object { $_.TaskName -match '^[A-Za-z0-9 ._-]{1,200}$'"
        " -and @($_.Triggers).Count -gt 0 });"
        "$r = $ok | Where-Object { $_.TaskPath -eq '\\' } | Select-Object -First 1;"
        "$d = $ok | Where-Object { $_.TaskPath -ne '\\' } | Select-Object -First 1;"
        "[pscustomobject]@{ root = [string]$r.TaskName; deep = [string]$d.TaskName;"
        " deep_path = [string]$d.TaskPath } | ConvertTo-Json -Compress"
    )
    done = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if done.returncode != 0 or not done.stdout.strip():
        return None, None, None
    got = json.loads(done.stdout.strip())
    return (got.get("root") or None, got.get("deep") or None, got.get("deep_path") or None)


@_WINDOWS_ONLY
def test_the_real_probe_emits_every_key_the_parser_reads():
    root_name, _, _ = _real_task_names()
    if root_name is None:
        pytest.skip("no uniquely named scheduled task with a trigger was found at TaskPath \\ on this machine")

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
    _, deep_name, deep_path = _real_task_names()
    if deep_name is None:
        pytest.skip("no uniquely named foldered scheduled task with a trigger was found on this machine")

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
# This arm runs the REAL probe against a name the scheduler really does hold
# more than once. The name is DISCOVERED, never hardcoded: measured on this
# machine 2026-09-08, 'Backup', 'CreateObjectTask' and 'WiFiTask' each match two
# TaskPaths, and any of the three may be gone next week.
#
# READ ONLY. Get-ScheduledTask and nothing else.

_DUPLICATE_NAME_DISCOVERY = """
$ErrorActionPreference='Stop'
$hit = $null
foreach ($g in @(Get-ScheduledTask | Group-Object TaskName | Where-Object { $_.Count -gt 1 })) {
    if ($g.Name -notmatch '^[A-Za-z0-9 ._-]{1,200}$') { continue }
    $hit = $g
    break
}
if ($null -eq $hit) {
    [pscustomobject]@{ found = $false } | ConvertTo-Json -Compress
    exit 0
}
[pscustomobject]@{
    found = $true
    name = [string]$hit.Name
    paths = @($hit.Group | ForEach-Object { [string]$_.TaskPath })
} | ConvertTo-Json -Compress -Depth 5
"""


def _a_name_registered_more_than_once():
    """Ask the scheduler, read only, for a TaskName held under two TaskPaths.

    Returns (name, paths) or (None, None) when this machine holds no duplicated
    name or the enumeration could not be run.
    """
    exe = liveness._powershell_executable()
    done = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _DUPLICATE_NAME_DISCOVERY],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if done.returncode != 0 or not done.stdout.strip():
        return None, None
    got = json.loads(done.stdout.strip())
    if not got.get("found"):
        return None, None
    paths = got.get("paths")
    # Windows PowerShell 5.1 can collapse a one-element array to a scalar. This
    # group has at least two members, but the shape is normalised anyway rather
    # than trusted.
    if not isinstance(paths, list):
        paths = [paths]
    return got.get("name") or None, [str(p or "").strip() for p in paths]


@_WINDOWS_ONLY
def test_the_real_probe_answers_a_duplicated_name_as_ambiguous():
    name, paths = _a_name_registered_more_than_once()
    if name is None:
        pytest.skip(
            "no TaskName matching the module's own validator is registered under two TaskPaths on this "
            "machine, so the probe's ambiguity branch cannot be reached here - the machine, not the tool"
        )

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
    [pscustomobject]@{ found = $false } | ConvertTo-Json -Compress
    exit 0
}
$ebs = @()
foreach ($tr in @($hit.Triggers | Where-Object { $null -ne $_ })) { $ebs += [string]$tr.EndBoundary }
[pscustomobject]@{
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


def _a_task_carrying_an_end_boundary():
    """Ask the scheduler, read only, for one task whose triggers carry one.

    Returns (name, path, end_boundaries) with end_boundaries ordered as the
    scheduler lists the triggers, or (None, None, None) when nothing on this
    machine carries an EndBoundary or the enumeration could not be run.
    """
    exe = liveness._powershell_executable()
    done = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _ENDBOUNDARY_DISCOVERY],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if done.returncode != 0 or not done.stdout.strip():
        return None, None, None
    got = json.loads(done.stdout.strip())
    if not got.get("found"):
        return None, None, None
    raw = got.get("end_boundaries")
    # ConvertTo-Json under Windows PowerShell 5.1 can collapse a one-element
    # array to a scalar. Normalising here rather than trusting the shape.
    if not isinstance(raw, list):
        raw = [raw]
    return (
        got.get("name") or None,
        got.get("path") or None,
        [str(value or "").strip() for value in raw],
    )


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
    name, path, expected = _a_task_carrying_an_end_boundary()
    if name is None:
        pytest.skip(
            "no uniquely named registered task on this machine carries a non-empty EndBoundary on any "
            "trigger, so there is no value for the probe to be compared against - this arm asserts "
            "nothing here and the machine, not the tool, is why"
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
