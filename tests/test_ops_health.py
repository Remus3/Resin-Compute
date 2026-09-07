"""Tests for the health file contract.

Three properties are load-bearing and each has a dedicated test:

1. `write_health` is ATOMIC. There is never a moment where the target exists
   and is not complete JSON, and a failed write leaves the previous document
   intact rather than a truncated one.
2. `read_health` NEVER raises. Missing, unreadable and corrupt files are all
   ordinary states with a defined answer.
3. `is_stale` is correct AT the boundary, not merely near it. The equality
   case is the one that decides whether a heartbeat written every N seconds
   and checked at N flaps.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops import health as health_mod

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def test_runtime_dir_defaults_to_ops_runtime() -> None:
    """The default lives under the repo root, mirroring Sibling-C's ops/runtime."""
    assert health_mod.runtime_dir(None).parts[-2:] == ("ops", "runtime")


def test_runtime_dir_honours_the_environment_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(tmp_path))
    assert health_mod.runtime_dir(None) == tmp_path


def test_runtime_dir_argument_beats_the_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(health_mod.ENV_RUNTIME_DIR, str(tmp_path / "from_env"))
    assert health_mod.runtime_dir(tmp_path / "explicit") == tmp_path / "explicit"


def test_runtime_dir_does_not_create_the_directory(tmp_path: Path) -> None:
    """A reader must not materialise the directory it is inspecting."""
    target = tmp_path / "never_created"
    health_mod.runtime_dir(target)
    assert not target.exists()


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_write_then_read_round_trips_every_required_field(tmp_path: Path) -> None:
    written = health_mod.write_health(
        base=tmp_path,
        alive=True,
        started_at="2026-09-06T00:00:00+00:00",
        last_pass_at="2026-09-06T00:05:00+00:00",
        last_pass_ok=True,
        jobs=[{"name": "emit_health", "status": "PASS"}],
        engine_version_value="1.0.0",
        role="headless-runner",
        uid="900000000",
        message="pass complete",
    )
    assert written == tmp_path / health_mod.HEALTH_FILENAME

    payload = health_mod.read_health(base=tmp_path)
    for key in (
        "version",
        "pid",
        "alive",
        "started_at",
        "last_pass_at",
        "last_pass_ok",
        "jobs",
        "engine_version",
    ):
        assert key in payload, f"health payload is missing the required field {key}"

    assert payload["version"] == health_mod.SCHEMA_VERSION
    assert payload["pid"] == os.getpid()
    assert payload["alive"] is True
    assert payload["last_pass_ok"] is True
    assert payload["engine_version"] == "1.0.0"
    assert payload["jobs"] == [{"name": "emit_health", "status": "PASS"}]
    # heartbeat_at is stamped by the writer, never by the caller.
    assert payload["heartbeat_at"]


def test_write_health_creates_the_runtime_directory(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "runtime"
    health_mod.write_health(base=nested, message="first boot")
    assert (nested / health_mod.HEALTH_FILENAME).is_file()


def test_extra_fields_are_merged(tmp_path: Path) -> None:
    health_mod.write_health(base=tmp_path, extra={"child_pid": 4242, "restarts": 3})
    payload = health_mod.read_health(base=tmp_path)
    assert payload["child_pid"] == 4242
    assert payload["restarts"] == 3


def test_the_supervisor_uses_a_separate_file(tmp_path: Path) -> None:
    """Two roles, two files. A shared file makes each one clobber the other."""
    health_mod.write_health(base=tmp_path, role="headless-runner")
    health_mod.write_health(
        base=tmp_path, role="supervisor", filename=health_mod.SUPERVISOR_HEALTH_FILENAME
    )
    assert health_mod.read_health(base=tmp_path)["role"] == "headless-runner"
    supervisor = health_mod.read_health(
        base=tmp_path, filename=health_mod.SUPERVISOR_HEALTH_FILENAME
    )
    assert supervisor["role"] == "supervisor"


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


@pytest.fixture()
def force_local_writer(monkeypatch):
    """Pin the atomicity tests to THIS module's fallback writer.

    `core.atomic_io` is owned by a parallel slice and `write_health` prefers it
    the moment it lands. Without this pin, the three atomicity tests below
    would silently change subject from "our fallback is atomic" to "the other
    slice's writer is atomic" - which is their job to prove, in their own
    suite. The delegation itself is asserted separately.
    """
    monkeypatch.setattr(health_mod, "_ATOMIC_WRITE_JSON", None)


def test_a_present_core_atomic_io_is_preferred(tmp_path: Path, monkeypatch) -> None:
    """When the sanctioned writer exists, this module delegates to it."""
    calls: list[tuple[Path, dict]] = []

    def delegate(path, payload):  # type: ignore[no-untyped-def]
        calls.append((Path(path), dict(payload)))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(health_mod, "_ATOMIC_WRITE_JSON", delegate)
    health_mod.write_health(base=tmp_path, message="delegated")
    assert len(calls) == 1
    assert calls[0][1]["message"] == "delegated"


def test_write_health_is_atomic_target_is_never_partial(
    tmp_path: Path, monkeypatch, force_local_writer
) -> None:
    """At the instant of the rename, the source is already complete JSON.

    This is the property a polling reader depends on. It is asserted by
    intercepting `os.replace`: whatever it is handed must already parse, and
    the destination must still hold the PREVIOUS document, never a half-written
    one.
    """
    target = tmp_path / health_mod.HEALTH_FILENAME
    health_mod.write_health(base=tmp_path, message="first")
    first = target.read_text(encoding="utf-8")

    observed: dict[str, object] = {}
    real_replace = os.replace

    def spy_replace(src, dst):  # type: ignore[no-untyped-def]
        src_text = Path(src).read_text(encoding="utf-8")
        # Complete JSON before the rename, or the rename is not atomic.
        observed["src_parsed"] = json.loads(src_text)
        # The destination is untouched right up to the rename.
        observed["dst_before"] = Path(dst).read_text(encoding="utf-8")
        observed["src_is_sibling"] = Path(src).parent == Path(dst).parent
        return real_replace(src, dst)

    monkeypatch.setattr(health_mod.os, "replace", spy_replace)
    health_mod.write_health(base=tmp_path, message="second")

    assert observed["src_parsed"]["message"] == "second"
    assert observed["dst_before"] == first
    # A cross-filesystem temp turns os.replace into a copy, which is not atomic.
    assert observed["src_is_sibling"] is True
    assert health_mod.read_health(base=tmp_path)["message"] == "second"


def test_a_failed_write_leaves_the_previous_document_intact(
    tmp_path: Path, force_local_writer
) -> None:
    """An unserialisable payload must not damage what is already on disk."""
    target = tmp_path / health_mod.HEALTH_FILENAME
    health_mod.write_health(base=tmp_path, message="good document")
    before = target.read_text(encoding="utf-8")

    with pytest.raises(TypeError):
        health_mod.write_health(base=tmp_path, extra={"unserialisable": object()})

    assert target.read_text(encoding="utf-8") == before
    assert json.loads(target.read_text(encoding="utf-8"))["message"] == "good document"


def test_no_temp_file_survives_a_write(tmp_path: Path, force_local_writer) -> None:
    """A leftover .tmp sibling is litter the next reader can trip over."""
    health_mod.write_health(base=tmp_path, message="one")
    with pytest.raises(TypeError):
        health_mod.write_health(base=tmp_path, extra={"bad": object()})
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


# ---------------------------------------------------------------------------
# read_health never raises
# ---------------------------------------------------------------------------


def test_read_health_on_a_missing_file_returns_the_default(tmp_path: Path) -> None:
    payload = health_mod.read_health(base=tmp_path / "nothing_here")
    assert payload == health_mod.default_health()
    assert payload["present"] is False
    assert payload["alive"] is False
    # "never ran" and "last run failed" are different states.
    assert payload["last_pass_ok"] is None


def test_read_health_on_a_corrupt_file_does_not_raise(tmp_path: Path) -> None:
    target = tmp_path / health_mod.HEALTH_FILENAME
    target.write_text('{"pid": 12, "alive": tr', encoding="utf-8")
    payload = health_mod.read_health(base=tmp_path)
    assert payload["alive"] is False
    assert payload["message"] == "health file unreadable"
    assert payload["version"] == health_mod.SCHEMA_VERSION


def test_read_health_on_an_empty_file_does_not_raise(tmp_path: Path) -> None:
    (tmp_path / health_mod.HEALTH_FILENAME).write_text("", encoding="utf-8")
    assert health_mod.read_health(base=tmp_path)["message"] == "health file unreadable"


def test_read_health_on_a_json_array_does_not_raise(tmp_path: Path) -> None:
    """Valid JSON that is not an object is still not a health payload."""
    (tmp_path / health_mod.HEALTH_FILENAME).write_text("[1, 2, 3]", encoding="utf-8")
    assert health_mod.read_health(base=tmp_path)["message"] == "health file unreadable"


def test_read_health_never_leaks_a_raw_error_string(tmp_path: Path) -> None:
    """The friendly message goes in the payload; the raw error goes to the log."""
    (tmp_path / health_mod.HEALTH_FILENAME).write_text("{not json", encoding="utf-8")
    message = health_mod.read_health(base=tmp_path)["message"]
    for raw_marker in ("Expecting", "line 1 column", "Traceback", "JSONDecodeError"):
        assert raw_marker not in message


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def test_is_stale_is_false_exactly_at_the_boundary() -> None:
    """age == max_age is NOT stale. This is the flap-preventing case."""
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {"heartbeat_at": (now - timedelta(seconds=60)).isoformat()}
    assert health_mod.health_age_seconds(health, now=now) == 60.0
    assert health_mod.is_stale(health, 60, now=now) is False


def test_is_stale_is_true_one_second_past_the_boundary() -> None:
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {"heartbeat_at": (now - timedelta(seconds=61)).isoformat()}
    assert health_mod.is_stale(health, 60, now=now) is True


def test_is_stale_is_false_just_inside_the_boundary() -> None:
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {"heartbeat_at": (now - timedelta(seconds=59)).isoformat()}
    assert health_mod.is_stale(health, 60, now=now) is False


def test_a_payload_with_no_timestamp_is_stale() -> None:
    """Unknown freshness is not evidence of freshness."""
    assert health_mod.is_stale(health_mod.default_health(), 300) is True
    assert health_mod.is_stale({}, 300) is True


def test_an_unparseable_timestamp_is_stale() -> None:
    assert health_mod.is_stale({"heartbeat_at": "yesterday afternoon"}, 300) is True
    assert health_mod.is_stale({"heartbeat_at": 12345}, 300) is True


def test_a_future_timestamp_is_not_stale() -> None:
    """Clock skew must not manufacture an alert."""
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {"heartbeat_at": (now + timedelta(seconds=30)).isoformat()}
    assert health_mod.is_stale(health, 60, now=now) is False


def test_the_newest_timestamp_wins() -> None:
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {
        "started_at": (now - timedelta(hours=6)).isoformat(),
        "heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
    }
    assert health_mod.is_stale(health, 60, now=now) is False


def test_a_naive_timestamp_is_read_as_utc() -> None:
    """Guessing local time would make staleness depend on the reader's zone."""
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
    health = {"heartbeat_at": "2026-09-06T11:59:30"}
    assert health_mod.health_age_seconds(health, now=now) == 30.0


def test_a_freshly_written_file_is_not_stale(tmp_path: Path) -> None:
    """End to end, against the real writer rather than a hand-built dict."""
    health_mod.write_health(base=tmp_path, message="live")
    assert health_mod.is_stale(health_mod.read_health(base=tmp_path), 30) is False


def test_health_age_seconds_is_none_without_a_timestamp() -> None:
    assert health_mod.health_age_seconds({}) is None


# ---------------------------------------------------------------------------
# Engine probe
# ---------------------------------------------------------------------------


def test_engine_version_answers_none_when_the_engine_is_absent() -> None:
    """A missing sibling slice is an ordinary state, not an exception."""
    value = health_mod.engine_version()
    assert value is None or isinstance(value, str)


# ---------------------------------------------------------------------------
# Supervisor dry run
# ---------------------------------------------------------------------------


def test_supervisor_dry_run_exits_zero_and_spawns_nothing(tmp_path: Path) -> None:
    """`--dry-run` verifies configuration only. It must never start a child."""
    env = dict(os.environ)
    env["RESINCOMPUTE_RUNTIME_DIR"] = str(tmp_path / "runtime")
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", "ops.supervisor", "--dry-run"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "nothing was spawned" in proc.stdout
    assert "restart trigger" in proc.stdout
    # No health file: a dry run reports, it does not heartbeat.
    assert not (tmp_path / "runtime" / health_mod.SUPERVISOR_HEALTH_FILENAME).exists()
