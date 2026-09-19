"""Regression test for the pruned walkers in tools/first_run_capture.py.

Path.rglob("*") CANNOT prune - it always descends into every subdirectory,
including __pycache__, .git and friends. Post-filtering the yielded paths
still pays the full descent cost, and on a machine-wide root that descent is
what stalled logon. poll_tree and write_manifest must instead walk with
os.walk and an in-place dirnames[:] prune, matching the shape already proven
correct in tools/gate_mutation_runner.py.

This is a behaviour test, not a shape test: it does not grep the source for
"os.walk". It builds a real tree with a decoy skip-directory holding a file
that would otherwise match, and asserts poll_tree/write_manifest do not walk
into it - and, in the other direction, that a same-named file OUTSIDE the
skip directory IS found. A test that could only fail in one direction would
be worth nothing.
"""
from __future__ import annotations

from pathlib import Path

from tools import first_run_capture as frc


class _RecordingStore:
    """Minimal stand-in for CaptureStore, recording every offered key."""

    def __init__(self) -> None:
        self.seen: dict[str, str] = {}
        self.offered: list[str] = []
        self.blobs = Path()  # overwritten per-test where needed

    def offer(self, label: str, key: str, data: bytes, meta: dict | None = None) -> bool:
        self.offered.append(key)
        self.seen[key] = "deadbeef"
        return True

    def emit(self, event: dict) -> None:
        pass


def test_poll_tree_prunes_decoy_skip_dir_but_finds_sibling_file(tmp_path: Path) -> None:
    root = tmp_path / "watched"
    decoy_dir = root / "__pycache__"
    decoy_dir.mkdir(parents=True)
    decoy_file = decoy_dir / "trapped.log"
    decoy_file.write_bytes(b"should not be walked into")

    real_dir = root / "real"
    real_dir.mkdir()
    real_file = real_dir / "trapped.log"
    real_file.write_bytes(b"same name, outside the skip dir")

    store = _RecordingStore()
    new = frc.poll_tree(store, "test-label", root, 10 * 1024 * 1024)

    assert str(decoy_file) not in store.offered, (
        "poll_tree descended into a __pycache__ decoy directory"
    )
    assert str(real_file) in store.offered, (
        "poll_tree failed to find a same-named file outside the skip dir"
    )
    assert new == 1


def test_write_manifest_prunes_decoy_skip_dir_in_blob_count(tmp_path: Path) -> None:
    blobs = tmp_path / "blobs"
    decoy_dir = blobs / "node_modules"
    decoy_dir.mkdir(parents=True)
    (decoy_dir / "ab").mkdir()
    (decoy_dir / "ab" / "abcdef").write_bytes(b"decoy blob, must not be counted")

    real_bucket = blobs / "cd"
    real_bucket.mkdir()
    (real_bucket / "cdefgh").write_bytes(b"real blob, must be counted")

    class _Store:
        def __init__(self, blobs_dir: Path) -> None:
            self.blobs = blobs_dir
            self.seen: dict[str, str] = {}
            self.manifest_path = tmp_path / "manifest.json"
            self.root = tmp_path

        def emit(self, event: dict) -> None:
            pass

    store = _Store(blobs)
    frc.write_manifest(store, "2026-01-01T00:00:00Z")

    import json

    manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))
    assert manifest["distinct_blobs"] == 1, (
        "write_manifest counted a blob inside a node_modules decoy directory"
    )
