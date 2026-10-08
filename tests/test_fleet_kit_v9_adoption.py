"""FLEET-KIT v9 adoption: the /done marker, the Stop hook, zero display keys.

MAIN 2354 ORDER of 2026-10-07 (SHA-256 verified against MAIN's outbox),
section 2 items 2 to 4. `tests/test_fleet_kit.py` pins the vendored bytes and
the embedded FLEET-COMMON block; this file pins what the tree must do AROUND
the kit:

- `/done`'s LAST act is `fleet_done.py mark ... --status done`, with a failed
  path that marks `--status failed --reason`, and its only chat line stays
  `Done ritual complete, safe to clear`;
- a project Stop hook runs `fleet_done.py stop-hook` through
  `$CLAUDE_PROJECT_DIR`, so it survives a drive move;
- no tracked `.claude/settings*.json` sets any key the kit's
  `cli_display.json` lists under `tree_forbidden`, top level or nested;
- the marker and its dedupe file are gitignored.

Every detector here has a non-vacuity arm that feeds it a planted bad input.
The forbidden-key list is READ from the vendored `cli_display.json`, never
restated, so a kit that adds a key re-arms this file without an edit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = REPO_ROOT / "ops" / "fleet_kit"
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
GITIGNORE = REPO_ROOT / ".gitignore"

#: The exact Stop hook command. Project-relative through the variable Claude
#: Code expands, double-quoted because the checkout path holds a space - the
#: same spelling every other hook in the settings file uses.
STOP_HOOK_COMMAND = 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_done.py" stop-hook'

#: The ORDER's mark invocations, as `/done` must spell them.
MARK_DONE = "python ops/fleet_kit/fleet_done.py mark --session <n> --status done"
MARK_FAILED = 'python ops/fleet_kit/fleet_done.py mark --session <n> --status failed --reason "<step>"'
CHAT_LINE = "Done ritual complete, safe to clear"

IGNORED = ("ops/loop/control/session_done.json", "ops/loop/control/session_done.seen")


def _tree_forbidden() -> list[str]:
    raw = json.loads((KIT_DIR / "cli_display.json").read_bytes().decode("ascii"))
    keys = raw["tree_forbidden"]
    assert isinstance(keys, list) and len(keys) >= 8, f"cli_display.json tree_forbidden is {keys!r}"
    return keys


def _forbidden_paths(blob: object, forbidden: list[str], prefix: str = "") -> list[str]:
    """Every dotted path in `blob` whose last key is forbidden, at any depth."""
    found: list[str] = []
    if isinstance(blob, dict):
        for key, value in blob.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(_forbidden_paths(value, forbidden, path))
    elif isinstance(blob, list):
        for i, value in enumerate(blob):
            found.extend(_forbidden_paths(value, forbidden, f"{prefix}[{i}]"))
    return found


def _tracked_settings_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", ".claude"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return sorted(
        p for p in out.split("\0")
        if p and Path(p).parent.as_posix() == ".claude" and Path(p).name.startswith("settings")
        and p.endswith(".json")
    )


def _stop_commands(settings: dict) -> list[tuple[str, object]]:
    found = []
    for group in settings.get("hooks", {}).get("Stop", []):
        for entry in group.get("hooks", []):
            if entry.get("type") == "command":
                found.append((entry.get("command"), entry.get("timeout")))
    return found


# ---------------------------------------------------------------- display keys


def test_no_tracked_settings_file_sets_a_display_key():
    files = _tracked_settings_files()
    assert ".claude/settings.json" in files, f"the sweep saw no tracked settings file: {files}"
    forbidden = _tree_forbidden()
    offenders = []
    for rel in files:
        blob = json.loads((REPO_ROOT / rel).read_bytes().decode("utf-8"))
        offenders.extend(f"{rel}: {p}" for p in _forbidden_paths(blob, forbidden))
    assert offenders == [], f"tree-level display keys (kit v9 item 15 forbids them): {offenders}"


def test_the_display_key_detector_fires_top_level_and_nested():
    forbidden = _tree_forbidden()
    planted = {
        "statusLine": {"type": "command"},
        "env": {"X": "1"},
        "nested": {"deep": [{"outputStyle": "x"}]},
        "permissions": {"allow": ["Bash(git:*)"]},
    }
    assert _forbidden_paths(planted, forbidden) == ["statusLine", "nested.deep[0].outputStyle"]
    # Neighbours survive: the real settings keys are not forbidden.
    assert _forbidden_paths({"env": {}, "hooks": {}, "permissions": {}}, forbidden) == []


# ---------------------------------------------------------------- Stop hook


def test_the_stop_hook_runs_the_kit_done_hook_project_relative():
    settings = json.loads(SETTINGS.read_bytes().decode("utf-8"))
    stops = _stop_commands(settings)
    assert [c for c, _ in stops] == [STOP_HOOK_COMMAND], f"Stop hook commands: {stops}"
    timeout = stops[0][1]
    assert isinstance(timeout, int) and not isinstance(timeout, bool) and 1 <= timeout <= 5, timeout
    assert (KIT_DIR / "fleet_done.py").is_file()


def test_the_stop_hook_detector_fires_on_a_missing_or_absolute_hook():
    assert _stop_commands({"hooks": {}}) == []
    planted = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python E:/x/fleet_done.py stop-hook"}]}]}}
    assert [c for c, _ in _stop_commands(planted)] != [STOP_HOOK_COMMAND]


def test_the_stop_hook_is_silent_without_a_marker(tmp_path):
    """STANDARD s5: silent by default, exit 0, never blocks. A tmp dir that is
    not a git checkout holds no marker, so the hook must print nothing."""
    result = subprocess.run(
        [sys.executable, str(KIT_DIR / "fleet_done.py"), "stop-hook"],
        input=json.dumps({"cwd": str(tmp_path), "session_id": "x"}).encode("ascii"),
        capture_output=True, cwd=str(tmp_path), timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == b"", result.stdout


# ---------------------------------------------------------------- /done


def _done_text() -> str:
    return DONE_MD.read_bytes().decode("ascii")


def _section_before_safety(text: str) -> str:
    """The last numbered section: everything from the last `## <digit>` heading
    up to the `## Safety rails` appendix, which is reference, not an act."""
    body = text[: text.index("\n## Safety rails")]
    return body[body.rindex("\n## ") :]


def test_done_marks_the_session_as_its_last_act():
    text = _done_text()
    assert MARK_DONE in text, "done.md does not call fleet_done.py mark --status done"
    assert MARK_FAILED in text, "done.md has no failed-path mark with --reason"
    final = _section_before_safety(text)
    assert MARK_DONE in final, f"the mark is not in /done's final section: {final[:200]!r}"
    assert CHAT_LINE in final
    # The mark comes after every other act: the hand-off and the shortcut.
    assert text.index(MARK_DONE) > text.index("python tools/publish_next_session.py")
    assert text.index(MARK_DONE) > text.index("## 7. Rewrite `RSC-NEXT-SESSION.txt`")


def test_the_done_section_detector_fires_when_the_mark_is_early():
    planted = (
        "# /done\n\n## 1. Mark\n\n" + MARK_DONE + "\n\n## 10. The one line\n\n"
        + CHAT_LINE + "\n\n## Safety rails\n\n- x\n"
    )
    assert MARK_DONE not in _section_before_safety(planted)


# ---------------------------------------------------------------- gitignore


def test_the_done_marker_files_are_named_in_gitignore():
    lines = GITIGNORE.read_bytes().decode("ascii").splitlines()
    for rel in IGNORED:
        assert rel in lines, f".gitignore does not name {rel}"


def test_git_ignores_the_done_marker_files():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "--no-index", *IGNORED],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.decode("ascii").split()) == sorted(IGNORED)


def test_check_ignore_reports_a_path_nothing_ignores():
    """Non-vacuity: check-ignore exits 1 for a tracked, unignored path."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "--no-index", "CLAUDE.md"],
        capture_output=True,
    )
    assert result.returncode == 1
