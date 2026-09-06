"""Bootstrap CLI tests. Offline only - the live path is never exercised here.

The subprocess tests are deliberate: `--dry-run` writing nothing is a promise
about the PROCESS, and an in-process call could hide a write performed at import
time or by a helper that a test happens not to reach.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bootstrap_data.py"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_script_exists():
    assert SCRIPT.is_file()


def test_offline_dry_run_exits_zero_and_writes_nothing(tmp_path):
    out = tmp_path / "snapshot.json"
    proc = _run(["--offline", "--dry-run", "--out", str(out)])

    assert proc.returncode == 0, proc.stderr
    assert not out.exists()
    # Not even the parent directory is created.
    assert list(tmp_path.iterdir()) == []
    assert "DRY RUN" in proc.stdout


def test_dry_run_is_the_default_shape_of_the_summary(tmp_path):
    out = tmp_path / "snapshot.json"
    proc = _run(["--offline", "--dry-run", "--out", str(out)])

    assert "characters mapped : 3" in proc.stdout
    assert "unknown avatar ids: 0" in proc.stdout
    assert "seed entities     : 7" in proc.stdout  # 5 characters + 2 materials
    assert "writer" in proc.stdout


def test_bare_invocation_defaults_to_offline_and_does_not_fetch(tmp_path):
    out = tmp_path / "snapshot.json"
    proc = _run(["--dry-run", "--out", str(out)])

    assert proc.returncode == 0, proc.stderr
    assert "mode              : offline" in proc.stdout


def test_offline_write_produces_a_valid_snapshot(tmp_path):
    out = tmp_path / "nested" / "snapshot.json"
    proc = _run(["--offline", "--out", str(out)])

    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    document = json.loads(out.read_text(encoding="utf-8"))

    assert document["schema_version"] == 1
    assert document["source"].startswith("offline:")
    assert document["unknown_avatar_ids"] == []
    assert len(document["seed_characters"]) == 5
    assert len(document["seed_materials"]) == 2
    assert len(document["profile"]["characters"]) == 3
    assert document["profile"]["showcase_open"] is True
    # No temp file survives an atomic write.
    assert list(out.parent.glob("*.tmp")) == []


def test_seed_ids_in_the_snapshot_are_the_verified_ones(tmp_path):
    out = tmp_path / "snapshot.json"
    _run(["--offline", "--out", str(out)])
    document = json.loads(out.read_text(encoding="utf-8"))

    ids = {row["avatar_id"] for row in document["seed_characters"]}
    assert ids == {10000096, 10000079, 10000083, 10000032, 10000034}
    # Refuted during verification - these must never come back.
    assert 10000088 not in ids  # Charlotte, not Dehya
    assert 10000080 not in ids  # Mika, not Lynette

    materials = {row["material_id"]: row["name"] for row in document["seed_materials"]}
    assert materials == {
        113059: "Fragment of a Golden Melody",
        113039: "Light Guiding Tetrahedron",
    }


def test_conflicting_modes_fail_friendly_without_a_traceback(tmp_path):
    proc = _run(["--offline", "--uid", "000000000", "--out", str(tmp_path / "x.json")])

    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr
    assert "Traceback" not in proc.stdout
    assert "mutually exclusive" in proc.stderr


def test_live_mode_without_a_user_agent_fails_friendly(tmp_path):
    """The refusal happens before any socket is opened, so this makes no request."""
    proc = _run(["--uid", "000000000", "--out", str(tmp_path / "x.json"), "--cache-dir", str(tmp_path / "c")])

    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert "user_agent" in proc.stderr
    assert not (tmp_path / "x.json").exists()


def test_missing_fixture_fails_friendly(tmp_path):
    proc = _run(["--offline", "--fixture", str(tmp_path / "nope.json"), "--out", str(tmp_path / "x.json")])

    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert "bootstrap failed" in proc.stderr


def test_run_is_importable_and_returns_an_exit_code(tmp_path):
    """In-process check that main() is a normal callable, not just a __main__ block."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import bootstrap_data
    finally:
        sys.path.pop(0)

    out = tmp_path / "snapshot.json"
    assert bootstrap_data.main(["--offline", "--dry-run", "--out", str(out)]) == 0
    assert not out.exists()
