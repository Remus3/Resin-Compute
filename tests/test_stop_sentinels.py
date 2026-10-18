"""FLEET-KIT v19 stop sentinels: this tree declares ops/runtime/HALT.

The kit's `fleet_headless.spawn()` refuses, code "halted", while a path the
tree declares in `ops/stop_sentinels.json` {"paths": [...]} exists. No file
means no sentinels, so the operator's HALT (`headless/runner.py`
HALT_SENTINEL_NAME in the runtime dir, `tools/moon_sync_responder.py`
halt_sentinel()) would not stop a kit spawn unless it is declared here.

Every arm runs the kit's own `stop_sentinel_hit()` against a scratch COPY of
the declaration, never the live tree, so a HALT file on the host can never
decide a test.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINELS = REPO_ROOT / "ops" / "stop_sentinels.json"
HALT_REL = "ops/runtime/HALT"


def _load_kit() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "fleet_headless_sentinels_under_test", REPO_ROOT / "ops" / "fleet_kit" / "fleet_headless.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KIT = _load_kit()


def _scratch(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "ops").mkdir(parents=True)
    shutil.copyfile(SENTINELS, root / "ops" / "stop_sentinels.json")
    return root


def test_the_declaration_is_ascii_lf_and_names_exactly_the_halt_file():
    raw = SENTINELS.read_bytes()
    assert all(b < 0x80 for b in raw)
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert json.loads(raw.decode("ascii")) == {"paths": [HALT_REL]}
    assert KIT.SENTINELS_REL.as_posix() == "ops/stop_sentinels.json"


def test_the_declared_path_is_where_runner_and_responder_look():
    runner = (REPO_ROOT / "headless" / "runner.py").read_text(encoding="utf-8")
    responder = (REPO_ROOT / "tools" / "moon_sync_responder.py").read_text(encoding="utf-8")
    assert 'HALT_SENTINEL_NAME = "HALT"' in runner
    assert 'HALT_SENTINEL_NAME = "HALT"' in responder
    assert 'RUNTIME_DIR / "responder_runs.json"' in responder
    assert HALT_REL.rsplit("/", 1) == ["ops/runtime", "HALT"]


def test_the_kit_reads_the_declaration_and_fires_only_on_halt(tmp_path):
    root = _scratch(tmp_path)
    assert KIT.stop_sentinel_hit(root) is None
    halt = root / "ops" / "runtime" / "HALT"
    halt.parent.mkdir(parents=True)
    halt.write_bytes(b"")
    assert KIT.stop_sentinel_hit(root) == HALT_REL
    # A neighbour in the runtime dir is not a sentinel.
    halt.unlink()
    (halt.parent / "health.json").write_bytes(b"{}")
    assert KIT.stop_sentinel_hit(root) is None


def test_a_corrupt_declaration_fails_closed(tmp_path):
    root = _scratch(tmp_path)
    (root / "ops" / "stop_sentinels.json").write_bytes(b'{"path": ["ops/runtime/HALT"]}\n')
    with pytest.raises(KIT.Refused):
        KIT.stop_sentinel_hit(root)
