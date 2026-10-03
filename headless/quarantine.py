"""Durable per-job abandonment counter, and the quarantine it drives.

A LIVE pass that leaves a job abandoned ends the process holding its slot,
and the supervisor restarts the daemon. The supervisor's backoff resets after
a minute of uptime, which is shorter than a job's deadline, so without this
record a job that hangs on every run would be rerun on every restart forever,
repeating whatever upstream call it hangs in.

The record is a JSON object in the runtime directory, one entry per job:

    {"<job>": {"consecutive": <int>, "quarantined": <bool>, "since": "<iso>"}}

A job abandoned on `QUARANTINE_AFTER` consecutive passes is QUARANTINED: a
full pass SKIPs it and every health record the runner writes carries a
degraded flag naming it. The flag lifts only when the job completes once
successfully - asked for explicitly with `--job`, which is the operator's
retry - or when the record is removed.

Written ONLY through `core/atomic_io.py`, never on a dry run, and it never
raises: a corrupt or unreadable record reads as empty, so it degrades to "no
quarantine" rather than stopping the lane. The raw error goes to the log.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core import atomic_io as atomic_io_mod
from ops import health as health_mod

log = logging.getLogger(__name__)

RECORD_NAME = "job_abandonments.json"

#: Consecutive abandonments after which a job is quarantined.
QUARANTINE_AFTER = 2


def record_path(runtime_dir: str | None) -> Path:
    """Where the record lives: the same directory as the health file."""
    return health_mod.runtime_dir(Path(runtime_dir) if runtime_dir else None) / RECORD_NAME


def load(runtime_dir: str | None) -> dict[str, dict[str, Any]]:
    """The record, with every malformed entry dropped. Never raises."""
    try:
        raw = atomic_io_mod.read_json(record_path(runtime_dir), default={})
    except Exception:  # noqa: BLE001 - a bad record must not stop the lane
        log.exception("could not read the job abandonment record")
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        count = entry.get("consecutive")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            continue
        out[name] = {
            "consecutive": count,
            "quarantined": entry.get("quarantined") is True,
            "since": str(entry.get("since", "")),
        }
    return out


def save(runtime_dir: str | None, record: dict[str, dict[str, Any]]) -> bool:
    """Write the record atomically. Never raises; False means it was not written."""
    try:
        ok = atomic_io_mod.atomic_write_json(record_path(runtime_dir), record)
    except Exception:  # noqa: BLE001 - losing the record must not fail the pass
        log.exception("could not write the job abandonment record")
        return False
    if not ok:
        log.error("could not write the job abandonment record")
    return bool(ok)


def quarantined_jobs(runtime_dir: str | None) -> list[str]:
    """Names of quarantined jobs, sorted."""
    return sorted(name for name, entry in load(runtime_dir).items() if entry["quarantined"])


def apply_result(
    record: dict[str, dict[str, Any]], name: str, status: str, abandoned: bool
) -> bool:
    """Fold one job's outcome into `record` in place. True if it changed.

    Abandoned: the count goes up, and quarantine starts at QUARANTINE_AFTER.
    PASS: the entry goes, quarantine included. Anything else breaks the run
    of consecutive abandonments, so an unquarantined entry goes; a quarantined
    one stays until a PASS.
    """
    entry = record.get(name)
    if abandoned:
        count = (entry["consecutive"] if entry else 0) + 1
        quarantined = bool(entry and entry["quarantined"]) or count >= QUARANTINE_AFTER
        since = entry["since"] if entry and entry["quarantined"] else ""
        if quarantined and not since:
            since = datetime.now(UTC).isoformat()
        record[name] = {"consecutive": count, "quarantined": quarantined, "since": since}
        if quarantined and not (entry and entry["quarantined"]):
            log.error(
                "job %s was abandoned on %d consecutive passes and is now QUARANTINED: "
                "full passes skip it until it completes once (run it alone with "
                "--job %s) or %s is removed",
                name,
                count,
                name,
                RECORD_NAME,
            )
        return True
    if entry is None:
        return False
    if status == "PASS" or not entry["quarantined"]:
        del record[name]
        return True
    return False


def health_fields(runtime_dir: str | None) -> tuple[dict[str, Any], str]:
    """`(extra, message_suffix)` for every health record the runner writes."""
    names = quarantined_jobs(runtime_dir)
    extra: dict[str, Any] = {"degraded": bool(names), "quarantined_jobs": names}
    if not names:
        return extra, ""
    suffix = (
        f"; degraded - quarantined after hanging on repeated passes: {', '.join(names)}. "
        "It is skipped until it completes once when run alone with --job, or its "
        "record is removed"
    )
    return extra, suffix
