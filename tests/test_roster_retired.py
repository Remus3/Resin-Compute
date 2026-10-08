"""The per-host roster's retired flags must agree with the responder's gate.

The gate that keeps a retired tree from being answered or routed to is the
hardcoded `RETIRED` tuple in `tools/moon_sync_responder.py`. The gitignored
per-host roster (`ops/moon_sync_repos.json`) records the same fact twice -
`retired_channel_codes` and `siblings.*.retired` - but nothing reads either. A
retirement recorded in one place and not the other is a silent drift: the
roster says a tree is retired while the responder still answers it, or the
reverse. This test pins the two together whenever the live roster exists.

The roster is per-host and gitignored, so CI has none; the live arm SKIPS with
a reason there. Inside a linked worktree the roster lives in the MAIN checkout,
which is found through git's common dir. The non-vacuity arms run everywhere
on synthetic rosters.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESPONDER_PATH = ROOT / "tools" / "moon_sync_responder.py"
ROSTER_REL = Path("ops") / "moon_sync_repos.json"


def _responder_retired() -> set[str]:
    spec = importlib.util.spec_from_file_location("responder_roster_retired", RESPONDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.RETIRED)


def _live_roster_path() -> Path | None:
    candidates = [ROOT / ROSTER_REL]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            candidates.append(Path(out.stdout.strip()).parent / ROSTER_REL)
    except (OSError, subprocess.SubprocessError):
        pass
    for path in candidates:
        if path.is_file():
            return path
    return None


def roster_retired(roster: dict) -> tuple[set[str], set[str]]:
    """(retired_channel_codes keys, initials of siblings carrying `retired`)."""
    codes = {str(k).upper() for k in (roster.get("retired_channel_codes") or {})}
    flagged = {
        str(s.get("initials", "")).upper()
        for s in (roster.get("siblings") or {}).values()
        if isinstance(s, dict) and s.get("retired")
    }
    return codes, flagged


def test_live_roster_retired_matches_responder_gate():
    path = _live_roster_path()
    if path is None:
        pytest.skip("per-host roster ops/moon_sync_repos.json absent (gitignored; CI has none)")
    roster = json.loads(path.read_text(encoding="ascii"))
    codes, flagged = roster_retired(roster)
    gate = _responder_retired()
    assert codes == gate, f"roster retired_channel_codes {sorted(codes)} != responder RETIRED {sorted(gate)}"
    assert flagged == gate, f"roster siblings.*.retired {sorted(flagged)} != responder RETIRED {sorted(gate)}"


def test_non_vacuity_detector_fires_on_drift():
    gate = _responder_retired()
    assert gate, "responder RETIRED is empty - the live arm would compare nothing"
    drifted = {
        "retired_channel_codes": {c: "x" for c in gate} | {"ZZ": "x"},
        "siblings": {"Sibling-Z": {"initials": "QQ", "retired": "2026-01-01"}},
    }
    codes, flagged = roster_retired(drifted)
    assert codes != gate
    assert flagged != gate
    missing = {"retired_channel_codes": {}, "siblings": {}}
    codes, flagged = roster_retired(missing)
    assert codes != gate and flagged != gate


def test_matching_synthetic_roster_passes():
    gate = _responder_retired()
    ok = {
        "retired_channel_codes": {c: "x" for c in gate},
        "siblings": {f"Sibling-{i}": {"initials": c, "retired": "d"} for i, c in enumerate(sorted(gate))}
        | {"Sibling-live": {"initials": "AA", "root": None}},
    }
    assert roster_retired(ok) == (gate, gate)
