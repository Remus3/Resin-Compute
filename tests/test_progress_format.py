"""Every progress-file writer in this tree's code writes ONE `updated` format.

MAIN 2246 ORDER section 2, PERF-AUDIT item 8: the live progress directory
held 48 files in several timestamp spellings (`Z`, `+00:00`, `-0500`, naive,
microseconds). The fix is one ISO-8601 format with a UTC offset, written via
the kit's `fleet_headless.write_progress`, whose `_iso` renders
`YYYY-MM-DDTHH:MM:SS+HH:MM`.

The code writers here are two: `headless/runner.py` (task `rsc-runner`) and
`tools/moon_sync_responder.py` (task `rsc-responder`). Each arm drives the
REAL writer into tmp and reads the file back. `test_the_canonical_check_*`
is the non-vacuity arm: the checker must reject every off-format spelling
measured in the live directory, so a green arm here means something.
"""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from headless import runner as runner_mod

kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")

ROOT = Path(__file__).resolve().parents[1]
RESPONDER = ROOT / "tools" / "moon_sync_responder.py"

#: The one format: seconds precision, a colon-separated numeric offset.
CANONICAL = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\Z")


def canonical(value: object) -> bool:
    if not isinstance(value, str) or not CANONICAL.match(value):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-08T05:42:00Z",
        "2026-10-08T05:42:00",
        "2026-10-08T05:42:00-0500",
        "2026-10-08T05:42:00.123456+00:00",
        "2026-10-08 05:42:00+00:00",
        "",
        None,
    ],
)
def test_the_canonical_check_rejects_every_off_format_spelling(value):
    assert not canonical(value), value


@pytest.mark.parametrize("value", ["2026-10-08T05:42:00+00:00", "2026-10-08T00:42:00-05:00"])
def test_the_canonical_check_accepts_the_kit_format(value):
    assert canonical(value)


def test_the_kit_writer_itself_writes_the_canonical_format(tmp_path):
    doc = kit.write_progress(tmp_path, "probe-task", 10, "probe", 5, "running")
    on_disk = json.loads(Path(doc["path"]).read_text(encoding="ascii"))
    assert canonical(on_disk["updated"]), on_disk


def test_the_runner_writes_the_canonical_format(tmp_path, monkeypatch):
    monkeypatch.setenv("RESINCOMPUTE_RUNTIME_DIR", str(tmp_path / "runtime"))
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    progress = runner_mod._PassProgress(str(runtime), 1, [SimpleNamespace(name="probe_job")])
    progress.begin()
    progress.finish(True, "pass ok")
    root = runner_mod.kit_root(str(runtime))
    assert tmp_path in root.parents, root
    path = root / kit.PROGRESS_REL / (runner_mod.PROGRESS_TASK + ".json")
    doc = json.loads(path.read_text(encoding="ascii"))
    assert doc["status"] == "done", doc
    assert canonical(doc["updated"]), doc


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("responder_progress_format", RESPONDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def test_the_responder_writes_through_the_kit_write_progress(rsp, tmp_path, monkeypatch):
    calls: list[tuple] = []
    real = rsp.kit.write_progress

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(rsp.kit, "write_progress", spy)
    rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    assert calls, "the responder wrote its progress file without kit.write_progress"
    assert all(args[1] == rsp.PROGRESS_TASK for args, _kw in calls), calls


def test_the_responder_writes_the_canonical_format(rsp, tmp_path):
    rsp.run_once(inbox=tmp_path / "empty-inbox", roots={}, bounds=rsp.Bounds())
    path = rsp._kit_root() / kit.PROGRESS_REL / (rsp.PROGRESS_TASK + ".json")
    assert tmp_path in path.parents, path
    doc = json.loads(path.read_text(encoding="ascii"))
    assert doc["status"] == "done", doc
    assert canonical(doc["updated"]), doc
