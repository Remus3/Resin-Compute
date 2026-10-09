"""FLEET-KIT v12 adoption: race guards wired around the vendored kit.

MAIN 2031 ORDER of 2026-10-08 (SHA-256 verified against MAIN's outbox),
section 3. `tests/test_fleet_kit.py` pins the vendored bytes; this file pins
what the tree must do AROUND the kit:

- step 3: the tracked project settings run `fleet_claims.py hook` as a
  PreToolUse hook on `Edit|Write|NotebookEdit|MultiEdit|Bash|PowerShell`
  and `fleet_claims.py release-hook` as a SubagentStop hook, both timeout
  10, keeping the v10/v11 subagent-first entry;
- step 4: the five claims / lock runtime paths are gitignored;
- step 5: `/done` routes every commit and push through
  `fleet_gitlock.py run --owner` and the full suite through
  `fleet_suite_gate.py run --owner`;
- step 6: `tests/conftest.py` installs `fleet_test_guard` with the runtime
  root env vars this tree reads.

Every detector has a non-vacuity arm fed a planted bad input.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
CONFTEST = REPO_ROOT / "tests" / "conftest.py"
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"

#: The ORDER's matcher and commands, verbatim.
CLAIMS_MATCHER = "Edit|Write|NotebookEdit|MultiEdit|Bash|PowerShell"
CLAIMS_HOOK = 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_claims.py" hook'
RELEASE_HOOK = 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_claims.py" release-hook'
SUBAGENT_FIRST_HOOK = 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_subagent_first.py"'
TIMEOUT = 10

IGNORED = (
    "ops/loop/control/claims/x.json",
    "ops/loop/control/locks/git.lock",
    "ops/loop/control/claims.jsonl",
    "ops/loop/control/claims.mode",
    "ops/loop/control/gitlock.jsonl",
)

#: The env var `core/config.py` reads to locate the runtime root.
RUNTIME_ENV = "RESINCOMPUTE_RUNTIME_DIR"


def _rows(settings: dict, event: str) -> list[tuple[object, object, object]]:
    found = []
    for group in settings.get("hooks", {}).get(event, []):
        for entry in group.get("hooks", []):
            if entry.get("type") == "command":
                found.append((group.get("matcher"), entry.get("command"), entry.get("timeout")))
    return found


def _settings() -> dict:
    return json.loads(SETTINGS.read_bytes().decode("ascii"))


def test_the_claims_hook_is_wired_on_the_order_matcher():
    assert (CLAIMS_MATCHER, CLAIMS_HOOK, TIMEOUT) in _rows(_settings(), "PreToolUse")


def test_the_subagent_first_entry_is_kept():
    commands = [c for _m, c, _t in _rows(_settings(), "PreToolUse")]
    assert SUBAGENT_FIRST_HOOK in commands


def test_the_release_hook_is_wired_on_subagent_stop():
    rows = _rows(_settings(), "SubagentStop")
    assert [(c, t) for _m, c, t in rows] == [(RELEASE_HOOK, TIMEOUT)], rows


def test_the_wiring_detector_fires_on_a_planted_wrong_row():
    good = {"hooks": {"PreToolUse": [{"matcher": CLAIMS_MATCHER, "hooks": [
        {"type": "command", "command": CLAIMS_HOOK, "timeout": TIMEOUT}]}]}}
    assert (CLAIMS_MATCHER, CLAIMS_HOOK, TIMEOUT) in _rows(good, "PreToolUse")
    for matcher, command in (("Edit|Write", CLAIMS_HOOK), (CLAIMS_MATCHER, "python fleet_claims.py hook")):
        bad = {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [
            {"type": "command", "command": command, "timeout": TIMEOUT}]}]}}
        assert (CLAIMS_MATCHER, CLAIMS_HOOK, TIMEOUT) not in _rows(bad, "PreToolUse")


@pytest.mark.parametrize("path", IGNORED)
def test_the_race_guard_runtime_paths_are_gitignored(path):
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    assert probe.returncode == 0, f"{path} is not gitignored"


def test_the_gitignore_probe_reports_a_tracked_path():
    """Non-vacuity: a path that is NOT ignored reads as not ignored."""
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "core/types.py"],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    assert probe.returncode == 1


def _install_calls(source: str) -> list[ast.Call]:
    calls = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "install"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "fleet_test_guard"):
            calls.append(node)
    return calls


def _env_root_keys(call: ast.Call) -> set[str]:
    for kw in call.keywords:
        if kw.arg == "env_roots" and isinstance(kw.value, ast.Dict):
            return {k.value for k in kw.value.keys if isinstance(k, ast.Constant)}
    return set()


def test_the_conftest_installs_the_test_guard_with_the_runtime_root():
    calls = _install_calls(CONFTEST.read_text(encoding="ascii"))
    assert len(calls) == 1, "tests/conftest.py must call fleet_test_guard.install once"
    assert RUNTIME_ENV in _env_root_keys(calls[0])


def test_the_install_detector_fires_on_a_planted_conftest():
    assert _install_calls("import fleet_test_guard\n") == []
    planted = _install_calls("fleet_test_guard.install(globals(), root=1, env_roots={})\n")
    assert len(planted) == 1 and _env_root_keys(planted[0]) == set()


def test_done_routes_commit_push_and_suite_through_the_guards():
    text = DONE_MD.read_text(encoding="ascii")
    assert "fleet_gitlock.py run --owner" in text
    assert "fleet_suite_gate.py run --owner" in text
