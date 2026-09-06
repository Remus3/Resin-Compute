"""Tests for core.atomic_io.

The claim under test is not "the file gets written" - it is that a CONCURRENT
READER can never observe a partial file, and that a failed write leaves the
previous state intact. Those are the two properties the atomic-write rule
exists for, so they are asserted directly rather than assumed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.atomic_io import atomic_write_json, atomic_write_text, read_json


def _sibling_temps(directory: Path) -> list[Path]:
    """Every temp file atomic_io could have left in `directory`."""
    return sorted(p for p in directory.iterdir() if p.name.endswith(".tmp"))


def test_atomic_write_text_creates_file_and_parents(tmp_path):
    target = tmp_path / "nested" / "deeper" / "state.txt"
    assert atomic_write_text(target, "hello") is True
    assert target.read_text(encoding="utf-8") == "hello"


def test_target_is_never_observed_in_a_partial_state(tmp_path, monkeypatch):
    """The target holds the OLD bytes right up to the rename, then the NEW ones.

    Path.replace is spied on so the moment just before the swap is observable.
    That instant is exactly when a polling reader would be at risk.
    """
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    payload = "NEW-" + ("x" * 8192)
    observed: dict[str, str] = {}
    real_replace = Path.replace

    def spy(self: Path, other):
        observed["target_before_swap"] = Path(other).read_text(encoding="utf-8")
        observed["temp_before_swap"] = self.read_text(encoding="utf-8")
        return real_replace(self, other)

    monkeypatch.setattr(Path, "replace", spy)
    assert atomic_write_text(target, payload) is True

    # The target still held the complete previous document at swap time.
    assert observed["target_before_swap"] == "OLD"
    # The temp already held the complete new document at swap time.
    assert observed["temp_before_swap"] == payload
    # And the swap published it whole.
    assert target.read_text(encoding="utf-8") == payload


def test_no_temp_file_is_left_behind_after_a_successful_write(tmp_path):
    target = tmp_path / "state.json"
    assert atomic_write_json(target, {"a": 1}) is True
    assert atomic_write_json(target, {"a": 2}) is True
    assert _sibling_temps(tmp_path) == []
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_unserializable_payload_leaves_the_previous_file_intact(tmp_path):
    target = tmp_path / "state.json"
    assert atomic_write_json(target, {"kept": True}) is True

    assert atomic_write_json(target, {"bad": object()}) is False
    # Previous document survives byte for byte, and no temp is orphaned.
    assert json.loads(target.read_text(encoding="utf-8")) == {"kept": True}
    assert _sibling_temps(tmp_path) == []


def test_failed_rename_leaves_previous_content_and_removes_the_temp(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    def boom(self: Path, other):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "replace", boom)
    assert atomic_write_text(target, "NEW") is False
    assert target.read_text(encoding="utf-8") == "OLD"
    assert _sibling_temps(tmp_path) == []


def test_read_json_returns_default_for_a_missing_file(tmp_path):
    sentinel = {"default": True}
    assert read_json(tmp_path / "absent.json", sentinel) is sentinel
    assert read_json(tmp_path / "absent.json") is None


def test_read_json_returns_default_on_corruption_and_does_not_raise(tmp_path):
    target = tmp_path / "corrupt.json"
    target.write_text('{"half": ', encoding="utf-8")
    try:
        result = read_json(target, {"fallback": 1})
    except Exception as exc:  # noqa: BLE001 - the whole point is that none escapes
        pytest.fail(f"read_json raised {exc.__class__.__name__} instead of degrading")
    assert result == {"fallback": 1}


def test_read_json_returns_default_on_undecodable_bytes(tmp_path):
    target = tmp_path / "binary.json"
    target.write_bytes(b"\xff\xfe\x00\x01not utf-8")
    assert read_json(target, []) == []


def test_json_roundtrip_preserves_the_document(tmp_path):
    target = tmp_path / "state.json"
    payload = {"uid": "700000000", "pity": {"character_event": 42}, "list": [1, 2, 3]}
    assert atomic_write_json(target, payload) is True
    assert read_json(target, None) == payload


def test_write_to_an_unwritable_path_degrades_to_false(tmp_path):
    # A directory occupies the target name, so the rename cannot succeed.
    target = tmp_path / "occupied"
    target.mkdir()
    assert atomic_write_text(target, "nope") is False
    assert target.is_dir()
    assert _sibling_temps(tmp_path) == []
