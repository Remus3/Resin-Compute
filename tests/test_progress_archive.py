"""`scripts/progress_archive.py`: archive finished progress files, close a stale one.

MAIN 2246 ORDER section 2, PERF-AUDIT item 8. Every arm runs against a tmp
root; nothing here touches the live `ops/loop/control/progress/`. The archive
is a MOVE into `progress/archive/`, never a delete, so each arm that archives
also asserts the bytes arrived intact. The legitimate neighbours - fresh
finished files, running files, unparsable files - are asserted to SURVIVE in
place, so a sweep that archived everything would go red.
"""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "progress_archive.py"

NOW = dt.datetime(2026, 10, 8, 12, 0, 0, tzinfo=dt.UTC)


@pytest.fixture()
def pa():
    spec = importlib.util.spec_from_file_location("progress_archive_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dir(root: Path) -> Path:
    path = root / kit.PROGRESS_REL
    path.mkdir(parents=True, exist_ok=True)
    return path


def _put(root: Path, task: str, status: str, updated: str | None) -> Path:
    doc: dict[str, Any] = {"task": task, "pct": 40, "step": "s", "eta_s": 9, "status": status}
    if updated is not None:
        doc["updated"] = updated
    path = _dir(root) / f"{task}.json"
    path.write_bytes(json.dumps(doc).encode("ascii"))
    return path


def test_old_done_and_failed_files_move_and_the_neighbours_stay(pa, tmp_path):
    moved_expected = {
        "old-done": _put(tmp_path, "old-done", "done", "2026-10-06T10:00:00+00:00"),
        "old-failed": _put(tmp_path, "old-failed", "failed", "2026-10-06T10:00:00Z"),
        "old-basic": _put(tmp_path, "old-basic", "done", "2026-10-06T05:00:00-0500"),
        "old-micro": _put(tmp_path, "old-micro", "done", "2026-10-06T10:00:00.5+00:00"),
    }
    before = {name: p.read_bytes() for name, p in moved_expected.items()}
    stay = [
        _put(tmp_path, "fresh-done", "done", "2026-10-08T06:00:00+00:00"),
        _put(tmp_path, "old-running", "running", "2026-10-01T00:00:00+00:00"),
        _put(tmp_path, "garbled", "done", "not a time"),
        _put(tmp_path, "no-stamp", "done", None),
    ]
    (_dir(tmp_path) / "x.json.123.tmp").write_bytes(b"in flight")
    (_dir(tmp_path) / "broken.json").write_bytes(b"{not json")

    moved = pa.archive(_dir(tmp_path), now=NOW)

    archive = _dir(tmp_path) / "archive"
    assert sorted(p.name for p in moved) == sorted(f"{n}.json" for n in moved_expected)
    for name, data in before.items():
        assert not moved_expected[name].exists()
        assert (archive / f"{name}.json").read_bytes() == data
    for path in stay:
        assert path.exists(), path
    assert (_dir(tmp_path) / "x.json.123.tmp").exists()
    assert (_dir(tmp_path) / "broken.json").exists()


def test_a_name_already_in_the_archive_is_never_overwritten(pa, tmp_path):
    archive = _dir(tmp_path) / "archive"
    archive.mkdir()
    (archive / "dup.json").write_bytes(b"earlier")
    _put(tmp_path, "dup", "done", "2026-10-01T00:00:00+00:00")
    pa.archive(_dir(tmp_path), now=NOW)
    assert (archive / "dup.json").read_bytes() == b"earlier"
    assert len(list(archive.glob("dup*.json"))) == 2


def test_the_age_threshold_is_honoured(pa, tmp_path):
    _put(tmp_path, "edge", "done", "2026-10-07T13:00:00+00:00")  # 23 h old
    assert pa.archive(_dir(tmp_path), now=NOW) == []
    assert pa.archive(_dir(tmp_path), now=NOW, max_age_s=3600)[0].name == "edge.json"


def test_dry_run_moves_nothing(pa, tmp_path):
    path = _put(tmp_path, "old", "done", "2026-10-01T00:00:00+00:00")
    assert [p.name for p in pa.archive(_dir(tmp_path), now=NOW, dry_run=True)] == ["old.json"]
    assert path.exists()


def test_close_marks_a_running_file_failed_in_the_kit_format(pa, tmp_path):
    path = _put(tmp_path, "rsc-rearm", "running", "2026-10-08T05:42:00Z")
    doc = pa.close(tmp_path, "rsc-rearm")
    assert doc is not None
    on_disk = json.loads(path.read_text(encoding="ascii"))
    assert on_disk["status"] == "failed"
    assert on_disk["step"] == "closed stale"
    assert on_disk["pct"] == 40
    parsed = dt.datetime.fromisoformat(on_disk["updated"])
    assert parsed.utcoffset() is not None
    assert on_disk["updated"] != "2026-10-08T05:42:00Z"


@pytest.mark.parametrize("status", ["done", "failed"])
def test_close_refuses_a_file_that_is_not_running(pa, tmp_path, status):
    path = _put(tmp_path, "finished", status, "2026-10-08T05:42:00Z")
    data = path.read_bytes()
    assert pa.close(tmp_path, "finished") is None
    assert path.read_bytes() == data


def test_close_refuses_a_missing_task(pa, tmp_path):
    _dir(tmp_path)
    assert pa.close(tmp_path, "absent") is None
    assert not (_dir(tmp_path) / "absent.json").exists()


def test_the_cli_closes_then_archives(pa, tmp_path, capsys):
    _put(tmp_path, "stale", "running", "2026-10-01T00:00:00+00:00")
    _put(tmp_path, "old", "done", "2026-10-01T00:00:00+00:00")
    assert pa.main(["--root", str(tmp_path), "--close", "stale"]) == 0
    assert json.loads((_dir(tmp_path) / "stale.json").read_text())["status"] == "failed"
    assert pa.main(["--root", str(tmp_path)]) == 0
    assert (_dir(tmp_path) / "archive" / "old.json").exists()
    # just closed, so younger than 24 h: it stays
    assert (_dir(tmp_path) / "stale.json").exists()
    assert capsys.readouterr().out.isascii()


def test_the_cli_exits_nonzero_when_close_is_refused(pa, tmp_path):
    _dir(tmp_path)
    assert pa.main(["--root", str(tmp_path), "--close", "absent"]) == 1
