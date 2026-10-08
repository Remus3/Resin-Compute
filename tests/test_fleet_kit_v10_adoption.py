"""FLEET-KIT v10 adoption: the SUBAGENT-FIRST hook in log mode, /done dispatched.

MAIN 0839 ORDER of 2026-10-08 (SHA-256 verified against MAIN's outbox),
section 3 items 2 to 5. `tests/test_fleet_kit.py` pins the vendored bytes;
this file pins what the tree must do AROUND the kit:

- the project settings declare ONE PreToolUse hook, matcher
  `Bash|PowerShell|Read|Edit|Write|Grep|Glob|NotebookEdit|MultiEdit`, running
  `ops/fleet_kit/fleet_subagent_first.py` through `$CLAUDE_PROJECT_DIR`,
  timeout 10;
- the mode file and the decision log are gitignored, and the mode file is
  never tracked (the merger writes `log` into the main checkout at merge);
- the hook's own behaviour as this tree relies on it: an absent mode file
  means DENY, `log` never denies, a sub-agent call is never denied;
- `/done` dispatches the whole ritual to ONE sub-agent and the main session
  relays only its final line;
- no tracked non-kit Python prints a checklist except through
  `fleet_checklist.emit()`.

Every detector has a non-vacuity arm fed a planted bad input.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = REPO_ROOT / "ops" / "fleet_kit"
HOOK = KIT_DIR / "fleet_subagent_first.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
GITIGNORE = REPO_ROOT / ".gitignore"
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"

#: The ORDER's matcher, verbatim.
MATCHER = "Bash|PowerShell|Read|Edit|Write|Grep|Glob|NotebookEdit|MultiEdit"

#: The ORDER says `python ops/fleet_kit/fleet_subagent_first.py` "(path
#: relative to the project dir)". Spelled through `$CLAUDE_PROJECT_DIR` and
#: double-quoted, as every other hook here is: a bare relative path resolves
#: against the CURRENT cwd, and a PreToolUse hook whose script is not found
#: exits 2 - which Claude Code treats as a BLOCKING error on every guarded
#: call. The quotes are load-bearing because the checkout path holds a space.
HOOK_COMMAND = 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_subagent_first.py"'
HOOK_TIMEOUT = 10

IGNORED = ("ops/loop/control/subagent_first.mode", "ops/loop/control/subagent_first.jsonl")

CHAT_LINE = "Done ritual complete, safe to clear"


def _pre_tool_use(settings: dict) -> list[tuple[object, object, object]]:
    """(matcher, command, timeout) for every PreToolUse command hook."""
    found = []
    for group in settings.get("hooks", {}).get("PreToolUse", []):
        for entry in group.get("hooks", []):
            if entry.get("type") == "command":
                found.append((group.get("matcher"), entry.get("command"), entry.get("timeout")))
    return found


def _settings() -> dict:
    return json.loads(SETTINGS.read_bytes().decode("ascii"))


# ---------------------------------------------------------------- the hook wiring


def test_the_pre_tool_use_hook_runs_the_kit_hook_on_the_order_matcher():
    rows = _pre_tool_use(_settings())
    assert rows == [(MATCHER, HOOK_COMMAND, HOOK_TIMEOUT)], f"PreToolUse hooks: {rows}"
    assert HOOK.is_file()


def test_wiring_the_hook_dropped_no_existing_hook():
    """The merge kept every event the tree already declared."""
    events = set(_settings()["hooks"])
    assert {"SessionStart", "Stop", "UserPromptSubmit", "PreToolUse"} <= events, events


def test_the_wiring_detector_fires_on_a_wrong_matcher_or_command():
    good = {"hooks": {"PreToolUse": [{"matcher": MATCHER, "hooks": [
        {"type": "command", "command": HOOK_COMMAND, "timeout": HOOK_TIMEOUT}]}]}}
    assert _pre_tool_use(good) == [(MATCHER, HOOK_COMMAND, HOOK_TIMEOUT)]
    for matcher, command, timeout in (
        ("Bash|Read", HOOK_COMMAND, HOOK_TIMEOUT),
        (MATCHER, "python ops/fleet_kit/fleet_subagent_first.py", HOOK_TIMEOUT),
        (MATCHER, HOOK_COMMAND, 5),
    ):
        planted = {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [
            {"type": "command", "command": command, "timeout": timeout}]}]}}
        assert _pre_tool_use(planted) != [(MATCHER, HOOK_COMMAND, HOOK_TIMEOUT)]
    assert _pre_tool_use({"hooks": {}}) == []


def test_the_order_matcher_names_exactly_the_kit_guarded_tools():
    sys.path.insert(0, str(KIT_DIR))
    try:
        import fleet_subagent_first as hook
    finally:
        sys.path.remove(str(KIT_DIR))
    assert frozenset(MATCHER.split("|")) == hook.GUARDED


# ---------------------------------------------------------------- gitignore


def test_the_mode_and_log_files_are_named_in_gitignore():
    lines = GITIGNORE.read_bytes().decode("ascii").splitlines()
    for rel in IGNORED:
        assert rel in lines, f".gitignore does not name {rel}"


def test_git_ignores_the_mode_and_log_files():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "--no-index", *IGNORED],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.decode("ascii").split()) == sorted(IGNORED)


def test_the_mode_file_is_never_tracked():
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", *IGNORED],
        capture_output=True, check=True,
    ).stdout
    assert out == b"", f"tracked runtime hook state: {out!r}"


# ---------------------------------------------------------------- hook behaviour


def _fire(project: Path, payload: dict, env_mode: str | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in __import__("os").environ.items() if k not in ("FLEET_SUBAGENT_FIRST",)}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    if env_mode is not None:
        env["FLEET_SUBAGENT_FIRST"] = env_mode
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode("ascii"),
        capture_output=True, cwd=str(project), env=env, timeout=30,
    )


def _log_rows(project: Path) -> list[dict]:
    path = project / IGNORED[1]
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines() if line]


def _write_mode(project: Path, word: str) -> None:
    path = project / IGNORED[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(word.encode("ascii") + b"\n")


MAIN_READ = {"tool_name": "Read", "tool_input": {"file_path": "x"}}


def test_an_absent_mode_file_means_deny(tmp_path):
    """Why the merger must write `log` before the settings land: the default is
    deny, so a main checkout with the hook and no mode file denies its own
    main thread every guarded call."""
    result = _fire(tmp_path, MAIN_READ)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.decode("ascii"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert [r["decision"] for r in _log_rows(tmp_path)] == ["deny"]


def test_log_mode_never_denies_and_records_a_would_deny_row(tmp_path):
    _write_mode(tmp_path, "log")
    result = _fire(tmp_path, MAIN_READ)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b""
    rows = _log_rows(tmp_path)
    assert [(r["tool"], r["thread"], r["decision"], r["mode"]) for r in rows] == [
        ("Read", "main", "would-deny", "log")
    ]


def test_a_sub_agent_call_is_never_denied_even_in_deny_mode(tmp_path):
    _write_mode(tmp_path, "deny")
    result = _fire(tmp_path, {**MAIN_READ, "agent_id": "a1", "agent_type": "builder"})
    assert result.returncode == 0, result.stderr
    assert result.stdout == b""
    assert [r["decision"] for r in _log_rows(tmp_path)] == ["allow"]


def test_the_headless_exemption_env_skips_even_the_log(tmp_path):
    """fleet_headless.child_env sets FLEET_SUBAGENT_FIRST=off for every spawn."""
    result = _fire(tmp_path, MAIN_READ, env_mode="off")
    assert result.returncode == 0 and result.stdout == b""
    assert _log_rows(tmp_path) == []


# ---------------------------------------------------------------- /done


def _done_text() -> str:
    return DONE_MD.read_bytes().decode("ascii")


def _dispatch_section(text: str) -> str:
    """The text before the first numbered or Pre-flight section: the preamble
    the main session reads before deciding how to run the ritual."""
    return text[: text.index("\n## ")]


def test_done_dispatches_the_whole_ritual_to_one_sub_agent():
    head = _dispatch_section(_done_text())
    assert "ONE sub-agent" in head, "done.md preamble does not dispatch to ONE sub-agent"
    assert "relays only" in head and "final line" in head
    assert CHAT_LINE in head


def test_the_done_dispatch_detector_fires_when_the_rule_is_late():
    planted = "# /done\n\nRun every section.\n\n## 1. Gate\n\nDispatch to ONE sub-agent; relays only its final line.\n"
    head = _dispatch_section(planted)
    assert "ONE sub-agent" not in head


#: Kit v10 item 4 reaches every command the main session runs, not only
#: /done: /orchestrated-run and /ui-audit each dispatch to ONE sub-agent and
#: the main session relays only its final line. Each entry names the final
#: line vocabulary the preamble must state.
DISPATCHED_COMMANDS = {
    "orchestrated-run.md": ("RUN: COMPLETE", "RUN: BLOCKED - "),
    "ui-audit.md": ("AUDIT: PASS", "AUDIT: BLOCKED - "),
}


@pytest.mark.parametrize("name", sorted(DISPATCHED_COMMANDS))
def test_command_dispatches_to_one_sub_agent(name):
    text = (REPO_ROOT / ".claude" / "commands" / name).read_bytes().decode("ascii")
    # Whitespace-normalised: a phrase reflowed across a line break still counts.
    head = " ".join(_dispatch_section(text).split())
    assert "ONE sub-agent" in head, f"{name} preamble does not dispatch to ONE sub-agent"
    assert "FLEET-KIT v10" in head and "item 4" in head, f"{name} preamble does not cite kit v10 item 4"
    assert "relays only" in head and "final line" in head, f"{name} preamble does not relay only the final line"
    for line in DISPATCHED_COMMANDS[name]:
        assert line in head, f"{name} preamble does not name the final line {line!r}"


def test_the_command_dispatch_detector_fires_on_a_preamble_without_it():
    planted = "# /ui-audit\n\nRun every phase.\n\n## 9. Verdict\n\nONE sub-agent; relays only its final line, AUDIT: PASS.\n"
    head = _dispatch_section(planted)
    assert "ONE sub-agent" not in head and "AUDIT: PASS" not in head


# ---------------------------------------------------------------- emit()

#: Where a headless path or hook could print a checklist. The kit and the tests
#: are out of scope: the kit owns emit(), and tests print nothing to a console.
SCAN_ROOTS = ("headless", "tools", "scripts", "ops", "core", "engines", "ingest", "agents")


def _direct_checklist_prints(source: str) -> list[int]:
    """Lines where `print(...)` or `<x>.write(...)` is handed an expression that
    names a checklist - the kit's `render`/`start`/`update`, or any identifier
    containing `checklist`. emit() is the sanctioned path and is not flagged."""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_print = isinstance(func, ast.Name) and func.id == "print"
        is_write = isinstance(func, ast.Attribute) and func.attr == "write"
        if not (is_print or is_write):
            continue
        for arg in node.args:
            for sub in ast.walk(arg):
                name = sub.id if isinstance(sub, ast.Name) else sub.attr if isinstance(sub, ast.Attribute) else ""
                if "checklist" in name.lower():
                    hits.append(node.lineno)
                    break
    return hits


def _tracked_python() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", *SCAN_ROOTS],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return sorted(
        p for p in out.split("\0")
        if p.endswith(".py") and not p.startswith("ops/fleet_kit/") and "/tests/" not in p
    )


def test_no_tracked_code_prints_a_checklist_except_through_emit():
    files = _tracked_python()
    assert len(files) >= 20, f"the emit() sweep saw only {len(files)} files"
    offenders = []
    for rel in files:
        source = (REPO_ROOT / rel).read_bytes().decode("utf-8")
        offenders.extend(f"{rel}:{n}" for n in _direct_checklist_prints(source))
    assert offenders == [], f"checklist printed without fleet_checklist.emit(): {offenders}"


def test_the_emit_detector_fires_on_a_direct_print_and_spares_emit():
    planted = (
        "import sys\n"
        "print(checklist.start())\n"
        "sys.stdout.write(fleet_checklist.render(1, rows))\n"
        "fleet_checklist.emit(checklist.start())\n"
        "print('unrelated')\n"
    )
    assert _direct_checklist_prints(planted) == [2, 3]
