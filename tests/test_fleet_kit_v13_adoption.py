"""FLEET-KIT v13 adoption: the identity hooks (FLEET-COMMON 17).

MAIN 2246 ORDER of 2026-10-08 (SHA-256 verified against MAIN's outbox),
section 1 steps 4 and 5. `tests/test_fleet_kit.py` pins the vendored bytes;
this file pins the tree-side wiring:

- `.githooks/commit-msg` runs `fleet_identity.py commit-msg` (strip, never
  reject) and `.githooks/pre-push` runs `fleet_identity.py pre-push` FIRST,
  before the tree's own gates and before the `RESIN_SKIP_PREPUSH` escape,
  so a docs-only skip can never push a non-operator identity;
- `ops/loop/control/identity.jsonl` is gitignored.

The wiring detector is MAIN's drift check (f) regex, so a row this file
accepts is a row MAIN's sweep reads as wired. Each detector has a
non-vacuity arm.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS = REPO_ROOT / ".githooks"

#: MAIN tools/fleet_kit.py identity_hook_problems(), check (f).
def _wired(text: str, name: str) -> bool:
    return bool(re.search(re.escape("fleet_identity.py") + r"[\"']?\s+" + re.escape(name), text))


@pytest.mark.parametrize("name", ("commit-msg", "pre-push"))
def test_each_identity_hook_is_wired(name):
    assert _wired((HOOKS / name).read_text(encoding="ascii"), name)


def test_the_wiring_detector_rejects_a_planted_hook():
    assert not _wired('"$PY" "$ROOT/tools/precommit_gate.py" "$1"\n', "commit-msg")
    assert not _wired('"$PY" fleet_identity.py commit-msg "$1"\n', "pre-push")
    assert _wired('"$PY" "$ROOT/ops/fleet_kit/fleet_identity.py" pre-push "$@"\n', "pre-push")


def test_the_commit_msg_identity_step_never_rejects():
    text = (HOOKS / "commit-msg").read_text(encoding="ascii")
    line = next(ln for ln in text.splitlines() if _wired(ln, "commit-msg"))
    assert line.rstrip().endswith("|| true"), line


def _first_line(text: str, needle: str) -> int:
    for i, ln in enumerate(text.splitlines()):
        if needle in ln and not ln.lstrip().startswith("#"):
            return i
    return -1


def test_the_pre_push_identity_check_runs_before_the_skip_and_the_gates():
    text = (HOOKS / "pre-push").read_text(encoding="ascii")
    ident = next(i for i, ln in enumerate(text.splitlines()) if _wired(ln, "pre-push")
                 and not ln.lstrip().startswith("#"))
    skip = _first_line(text, "RESIN_SKIP_PREPUSH")
    gates = _first_line(text, "-m ruff check")
    assert skip > 0 and gates > 0, "anchors absent - this arm would be vacuous"
    assert ident < skip < gates
    assert "|| exit 1" in text.splitlines()[ident]


def test_the_identity_log_is_gitignored():
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "ops/loop/control/identity.jsonl"],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    assert probe.returncode == 0
