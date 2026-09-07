"""The health file contract.

Mirrors Riot Commander's `ops/runtime/health.json`, which is the single place
an operator (or another process) looks to answer "is it alive, and did the last
pass work". CLAUDE.md's "Where to find current state" section names that file
first for exactly this reason, so the shape is inherited rather than invented.

Three inherited rules are load-bearing here:

1. **Atomic writes only.** `tmp.write_text(...); tmp.replace(target)`. A reader
   polls this file while the writer is mid-write, so a partially written target
   is a real, observed failure mode - not a theoretical one. There is never a
   moment where `health.json` exists and is not complete JSON.
2. **A read never raises.** The file is absent on first boot and can be
   truncated by a hard kill. Both are ordinary states, not errors, so
   `read_health` answers with a default rather than an exception. A monitor
   that crashes on a missing health file is worse than no monitor.
3. **Never surface a raw exception string.** Failures are logged; the health
   payload carries a short friendly `message` instead.

`core.atomic_io` is the sanctioned atomic-write path for this tree. It is owned
by a parallel slice, so it is imported defensively and this module carries a
minimal local fallback that implements the identical tmp-then-replace contract.
The fallback is deliberately tiny: if it ever diverges from `core.atomic_io`,
the shared contract is the write-to-sibling-then-os.replace sequence, and that
sequence is what both must implement.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency: the sanctioned atomic writer.
# ---------------------------------------------------------------------------
# Imported by NAME probe rather than by a hard import, because core/atomic_io.py
# is written by a parallel slice and may not exist yet. When it lands, this
# module picks it up with no edit. Until then the local fallback below runs and
# implements the same tmp-then-replace contract.
_ATOMIC_WRITE_JSON = None
try:  # pragma: no cover - exercised implicitly by whichever branch is live
    from core import atomic_io as _core_atomic_io

    _ATOMIC_WRITE_JSON = getattr(_core_atomic_io, "atomic_write_json", None)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

#: Bump when a field is REMOVED or its meaning changes. Adding an optional
#: field is backwards compatible and does not need a bump, matching how RC
#: treats its own health payload.
SCHEMA_VERSION = 1

HEALTH_FILENAME = "health.json"
SUPERVISOR_HEALTH_FILENAME = "supervisor_health.json"

#: Test and deployment override for the runtime directory. Without this every
#: test would have to write into the real `ops/runtime/`, which makes the
#: "dry run writes nothing" assertion untestable.
ENV_RUNTIME_DIR = "RESINCOMPUTE_RUNTIME_DIR"

#: `ops/health.py` -> `ops/` -> repo root. Same `parent.parent` package-layout
#: rule CLAUDE.md pins for RC's `app/__init__.py`; getting it wrong silently
#: relocates every runtime path by one directory.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: Timestamp fields consulted by `is_stale`, newest wins.
_TIMESTAMP_FIELDS = ("heartbeat_at", "last_pass_at", "started_at")


def utc_now() -> datetime:
    """Timezone-aware now. Naive datetimes are banned in this file."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def runtime_dir(base: Path | None = None) -> Path:
    """Resolve the runtime directory.

    Precedence: explicit argument, then `RESINCOMPUTE_RUNTIME_DIR`, then
    `<repo root>/ops/runtime`. The directory is NOT created here - creation is
    a write-side concern, and a reader must not have the side effect of
    materialising the directory it is inspecting.
    """
    if base is not None:
        return Path(base)
    override = os.environ.get(ENV_RUNTIME_DIR)
    if override:
        return Path(override)
    return REPO_ROOT / "ops" / "runtime"


def health_path(base: Path | None = None, filename: str = HEALTH_FILENAME) -> Path:
    return runtime_dir(base) / filename


def default_health() -> dict[str, Any]:
    """The answer `read_health` gives when there is nothing trustworthy to read.

    `alive` is False and `last_pass_ok` is None rather than False: "we have
    never run" and "the last run failed" are different states and a monitor
    that conflates them raises false alarms on first boot.
    """
    return {
        "version": SCHEMA_VERSION,
        "pid": None,
        "alive": False,
        "started_at": None,
        "heartbeat_at": None,
        "last_pass_at": None,
        "last_pass_ok": None,
        "jobs": [],
        "engine_version": None,
        "role": None,
        "uid": None,
        "message": "no health file",
        "present": False,
    }


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _fallback_atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Minimal local implementation of the tmp-then-replace contract.

    Documented fallback for a missing `core.atomic_io`. The temp file is a
    sibling of the target so the replace is same-filesystem and therefore
    atomic; a temp in the system temp dir would make `os.replace` a cross
    device copy, which is exactly the non-atomic behaviour this guards against.

    Serialisation happens BEFORE the temp file is opened, so an unserialisable
    payload leaves no temp file and never touches the target.
    """
    text = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        # newline="\n" or the indent=2 payload above lands as CRLF on Windows.
        # This one manifests: health.json is multi-line by construction.
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    finally:
        # A crash between write_text and replace would otherwise leave a
        # partial sibling behind for the next reader to trip over.
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:  # pragma: no cover - best effort cleanup only
                pass


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically, preferring `core.atomic_io` when it is present."""
    if _ATOMIC_WRITE_JSON is not None:
        _ATOMIC_WRITE_JSON(path, payload)
        return
    _fallback_atomic_write_json(path, payload)


def write_health(
    *,
    pid: int | None = None,
    alive: bool = True,
    started_at: str | None = None,
    last_pass_at: str | None = None,
    last_pass_ok: bool | None = None,
    jobs: list[dict[str, Any]] | None = None,
    engine_version_value: str | None = None,
    role: str | None = None,
    uid: str | None = None,
    message: str = "",
    extra: dict[str, Any] | None = None,
    path: Path | None = None,
    base: Path | None = None,
    filename: str = HEALTH_FILENAME,
) -> Path:
    """Write the health payload atomically and return the path written.

    Every field is optional because a supervisor heartbeat and a runner pass
    summary share this one file shape but populate different halves of it.

    `engine_version_value` is passed in rather than probed here so a caller can
    record the version it actually talked to; `engine_version()` below is the
    best-effort probe for callers that have nothing better.
    """
    target = Path(path) if path is not None else health_path(base, filename)
    payload = default_health()
    payload.update(
        {
            "version": SCHEMA_VERSION,
            "pid": os.getpid() if pid is None else int(pid),
            "alive": bool(alive),
            "started_at": started_at,
            "heartbeat_at": utc_now_iso(),
            "last_pass_at": last_pass_at,
            "last_pass_ok": last_pass_ok,
            "jobs": list(jobs or []),
            "engine_version": engine_version_value,
            "role": role,
            "uid": uid,
            "message": message,
            "present": True,
        }
    )
    if extra:
        payload.update(extra)
    atomic_write_json(target, payload)
    return target


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_health(
    path: Path | None = None,
    base: Path | None = None,
    filename: str = HEALTH_FILENAME,
) -> dict[str, Any]:
    """Read the health payload. NEVER raises.

    Missing file, unreadable file, truncated JSON and a JSON document that is
    not an object all resolve to `default_health()` with a friendly `message`.
    The raw error goes to the log, never into the returned payload, per the
    inherited no-raw-error-strings rule.
    """
    target = Path(path) if path is not None else health_path(base, filename)
    result = default_health()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        result["message"] = "no health file"
        return result
    except OSError as exc:
        log.warning("health file unreadable at %s: %s", target, exc)
        result["message"] = "health file unreadable"
        return result

    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        log.warning("health file is not valid JSON at %s: %s", target, exc)
        result["message"] = "health file unreadable"
        return result

    if not isinstance(parsed, dict):
        log.warning("health file at %s is %s, expected an object", target, type(parsed).__name__)
        result["message"] = "health file unreadable"
        return result

    result.update(parsed)
    result["present"] = True
    return result


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # A naive timestamp is assumed UTC rather than local. Guessing local
        # would make staleness depend on the reader's timezone.
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def health_age_seconds(health: dict[str, Any], now: datetime | None = None) -> float | None:
    """Seconds since the newest usable timestamp in the payload.

    Returns None when the payload carries no parseable timestamp at all, which
    the caller must treat as "unknown", not as "fresh".
    """
    reference = now or utc_now()
    newest: datetime | None = None
    for field_name in _TIMESTAMP_FIELDS:
        parsed = _parse_timestamp(health.get(field_name))
        if parsed is not None and (newest is None or parsed > newest):
            newest = parsed
    if newest is None:
        return None
    return (reference - newest).total_seconds()


def is_stale(
    health: dict[str, Any],
    max_age_seconds: float,
    now: datetime | None = None,
) -> bool:
    """True when the payload is older than `max_age_seconds`.

    Boundary is EXCLUSIVE and that is deliberate: an age exactly equal to
    `max_age_seconds` is NOT stale, so a heartbeat written every N seconds and
    checked with `max_age_seconds=N` does not flap on the tick where the two
    coincide. Only `age > max_age_seconds` is stale.

    A payload with no parseable timestamp is stale - unknown freshness is not
    evidence of freshness. A timestamp in the future gives a negative age and
    is therefore not stale; clock skew must not manufacture an alert.
    """
    age = health_age_seconds(health, now=now)
    if age is None:
        return True
    return age > float(max_age_seconds)


def engine_version() -> str | None:
    """Best-effort PityEngine version probe.

    The engine package is a sibling slice. Absent engine is an ordinary state,
    not an error, so this answers None rather than raising.
    """
    try:
        # Lazy by design: a module-scope import would make this file fail to
        # import when the engine slice is absent.
        from agents import pity_engine
    except ImportError:
        return None
    value = getattr(pity_engine, "ENGINE_VERSION", None)
    return str(value) if value is not None else None
