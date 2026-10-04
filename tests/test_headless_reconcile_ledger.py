"""Tests for the reconcile_ledger job.

THE JOB EXISTS TO CLOSE ONE GAP: `core.ledger.estimate_velocity` folds observed
ledger entries, but `reconcile_state` rebuilds `AccountState` with an EMPTY
ledger every pass, so nothing ever populated it and every persisted snapshot
carried `sampled_over_days: 0`. This job folds an operator-typed observations
file into that fresh ledger and re-estimates the velocity before `persist_state`
writes the snapshot.

THE RULES IT MUST NOT BREAK:

- DEFAULT-OFF. No observations file means SKIP, so a tree that never heard of
  this job behaves exactly as before. The CI smoke test (`--once --dry-run`)
  changes by one SKIP line and nothing else.
- INPUT ONLY FROM THE CALLER OR A HAND-AUTHORED FILE. Never a HoYoverse
  endpoint, never `tools/wish_authkey.py`, never `data/account_state.json`.
- A DRY RUN WRITES NOTHING. A dry run with the file present reports how many
  rows it WOULD fold and leaves the ledger, the file and the directory alone.
- VALIDATE EVERYTHING BEFORE APPENDING ANYTHING. A bad row anywhere leaves the
  ledger empty, never half-folded; the raw error goes to the log, never to the
  message.
- IDEMPOTENT. The ledger is rebuilt per pass from the whole file, so there is no
  watermark to read back; a second call inside one pass SKIPs instead of
  doubling the entries.

Every test monkeypatches BOTH `RESINCOMPUTE_RUNTIME_DIR` and `RC_DATA_DIR` to
`tmp_path` (the pattern from tests/test_headless_persist_state.py and
tests/test_headless_runner_orphan_temps.py), so nothing here can touch the live
runtime directory or the repo's `data/`. No test takes a slot: `run_pass` takes
none, and no test runs a live `--once`.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from core.state_io import read_state
from core.types import AccountState, CurrencyKind
from headless import jobs as jobs_mod
from headless import runner as runner_mod
from headless.jobs import JobContext, get_job, persist_state, reconcile_ledger

UID = "900000000"
FILENAME = "income_observations.json"

MESSAGE_NO_STATE = "no reconciled state in this pass - nothing to fold into"
MESSAGE_NO_FILE = (
    "no observations file - add income_observations.json to the data dir or set observations_path"
)
MESSAGE_CORRUPT = "observations file is not valid JSON - see the log"
MESSAGE_SHAPE = (
    "observations file has an unexpected shape - expected schema_version 1 with an observations list"
)
MESSAGE_EMPTY = "observations file is empty - nothing to fold"
MESSAGE_ALREADY = "observations already folded into this pass - nothing to add"


# ---------------------------------------------------------------------------
# Fixtures and builders
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Both env vars point at tmp_path so no test can reach the live tree."""
    runtime = tmp_path / "runtime"
    data = tmp_path / "data"
    runtime.mkdir()
    data.mkdir()
    monkeypatch.setenv("RESINCOMPUTE_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("RC_DATA_DIR", str(data))
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "1")
    return {"runtime": runtime, "data": data}


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _rows(now: datetime | None = None) -> list[dict[str, Any]]:
    """Three hand-typed observations inside the default 30-day window.

    Two primogem incomes (60 + 540 = 600, so 20.0 per day over 30 days) and one
    fate SPEND, which the ledger must record and the velocity must ignore.
    """
    now = now or _now()
    return [
        {
            "id": "dailies-1",
            "at": (now - timedelta(days=1)).isoformat(),
            "currency": "primogem",
            "delta": 60,
            "note": "daily commissions",
        },
        {
            "id": "event-shop",
            "at": (now - timedelta(days=5)).isoformat(),
            "currency": "primogem",
            "delta": 540,
        },
        {
            "id": "ten-pull",
            "at": (now - timedelta(days=2)).isoformat(),
            "currency": "intertwined_fate",
            "delta": -10,
            "note": "ten wishes on the character banner",
        },
    ]


def _write(path: Path, rows: list[Any] | Any, schema_version: Any = 1, wrapper: Any = None) -> Path:
    payload = wrapper if wrapper is not None else {"schema_version": schema_version, "observations": rows}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _state() -> AccountState:
    return AccountState(uid=UID, adventure_rank=58, world_level=7)


def _context(**kwargs: Any) -> JobContext:
    context = JobContext(uid=UID, **kwargs)
    context.state = _state()
    return context


# ---------------------------------------------------------------------------
# Registration and ordering
# ---------------------------------------------------------------------------


def test_the_job_is_registered_between_reconcile_state_and_persist_state() -> None:
    spec = get_job("reconcile_ledger")
    assert spec is not None
    assert spec.depends_on == ("reconcile_state",)
    assert spec.cadence == jobs_mod.CADENCE_PER_PASS
    assert spec.description

    names = jobs_mod.job_names()
    assert names.index("reconcile_state") < names.index("reconcile_ledger") < names.index("persist_state")


def test_persist_state_waits_for_the_fold() -> None:
    """The fold must land in the snapshot, so persist_state depends on it."""
    spec = get_job("persist_state")
    assert spec is not None
    assert "reconcile_ledger" in spec.depends_on


# ---------------------------------------------------------------------------
# SKIP arms - the default-off contract
# ---------------------------------------------------------------------------


def test_no_reconciled_state_skips_before_the_file_is_opened(isolated_dirs: dict[str, Path]) -> None:
    """State None is checked FIRST. A corrupt file proves the file was never read:
    opening it would have been a FAIL."""
    (isolated_dirs["data"] / FILENAME).write_text("{not json", encoding="utf-8", newline="\n")
    context = JobContext(uid=UID)
    context.state = None

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == MESSAGE_NO_STATE


def test_an_absent_file_skips_with_the_default_off_message() -> None:
    context = _context()

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == MESSAGE_NO_FILE
    assert context.state.ledger.entries == []
    assert context.state.velocity.sampled_over_days == 0


def test_an_empty_observations_list_skips(isolated_dirs: dict[str, Path]) -> None:
    _write(isolated_dirs["data"] / FILENAME, [])
    context = _context()

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == MESSAGE_EMPTY
    assert context.state.ledger.entries == []


def test_a_dry_run_counts_the_rows_and_writes_nothing(isolated_dirs: dict[str, Path]) -> None:
    """The count is only reported AFTER a successful parse, and nothing moves."""
    target = _write(isolated_dirs["data"] / FILENAME, _rows())
    before_bytes = target.read_bytes()
    before_listing = sorted(p.name for p in isolated_dirs["data"].iterdir())
    context = _context(dry_run=True)

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == "dry run - would fold 3 observations into the ledger"
    assert context.state.ledger.entries == []
    assert context.state.velocity.sampled_over_days == 0
    assert target.read_bytes() == before_bytes
    assert sorted(p.name for p in isolated_dirs["data"].iterdir()) == before_listing
    assert list(isolated_dirs["runtime"].iterdir()) == []


def test_a_dry_run_with_a_corrupt_file_still_reports_the_fail(isolated_dirs: dict[str, Path]) -> None:
    """Precondition checks precede the dry-run check, as every other job does."""
    (isolated_dirs["data"] / FILENAME).write_text("{not json", encoding="utf-8", newline="\n")
    context = _context(dry_run=True)

    result = reconcile_ledger(context)

    assert result.failed
    assert result.message == MESSAGE_CORRUPT


# ---------------------------------------------------------------------------
# FAIL arms - present and broken
# ---------------------------------------------------------------------------


def test_corrupt_json_fails_with_a_friendly_message(isolated_dirs: dict[str, Path]) -> None:
    (isolated_dirs["data"] / FILENAME).write_text('{"schema_version": 1, "observations": [', encoding="utf-8", newline="\n")
    context = _context()

    result = reconcile_ledger(context)

    assert result.failed
    assert result.message == MESSAGE_CORRUPT
    # The raw parser text stays in the log.
    assert "Expecting" not in result.message
    assert "JSONDecodeError" not in result.message
    assert "Traceback" not in result.message
    assert context.state.ledger.entries == []


@pytest.mark.parametrize(
    "wrapper",
    [
        pytest.param([{"id": "x"}], id="list-not-object"),
        pytest.param({"schema_version": 2, "observations": []}, id="future-schema"),
        pytest.param({"observations": []}, id="no-schema-version"),
        pytest.param({"schema_version": 1, "observations": {"id": "x"}}, id="observations-not-a-list"),
        pytest.param({"schema_version": 1}, id="no-observations"),
        pytest.param("just a string", id="scalar"),
    ],
)
def test_an_unexpected_wrapper_fails(isolated_dirs: dict[str, Path], wrapper: Any) -> None:
    _write(isolated_dirs["data"] / FILENAME, [], wrapper=wrapper)
    context = _context()

    result = reconcile_ledger(context)

    assert result.failed
    assert result.message == MESSAGE_SHAPE
    assert context.state.ledger.entries == []


#: Passed as an override value to DELETE that key from the row.
_ABSENT = object()


def _bad_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "bad-row",
        "at": (_now() - timedelta(days=1)).isoformat(),
        "currency": "primogem",
        "delta": 60,
    }
    row.update(overrides)
    for key in [k for k, v in overrides.items() if v is _ABSENT]:
        del row[key]
    return row


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(_bad_row(id=_ABSENT), id="missing-id"),
        pytest.param(_bad_row(id=""), id="empty-id"),
        pytest.param(_bad_row(id=7), id="non-string-id"),
        pytest.param(_bad_row(id="dailies-1"), id="duplicate-id"),
        pytest.param(_bad_row(delta=0), id="zero-delta"),
        pytest.param(_bad_row(delta=60.5), id="non-int-delta"),
        pytest.param(_bad_row(delta="60"), id="string-delta"),
        pytest.param(_bad_row(delta=True), id="bool-delta"),
        pytest.param(_bad_row(currency="primogems"), id="bad-currency"),
        pytest.param(_bad_row(currency=_ABSENT), id="missing-currency"),
        pytest.param(_bad_row(at="yesterday"), id="bad-timestamp"),
        pytest.param(_bad_row(at=_ABSENT), id="missing-timestamp"),
        pytest.param(_bad_row(note=42), id="non-string-note"),
        pytest.param("not an object", id="row-not-an-object"),
    ],
)
def test_one_invalid_row_fails_the_file_and_appends_nothing(
    isolated_dirs: dict[str, Path], bad: Any
) -> None:
    """VALIDATE ALL BEFORE APPENDING ANY. The bad row comes LAST, after three
    good ones, so a fold that appended as it went would leave three entries."""
    _write(isolated_dirs["data"] / FILENAME, [*_rows(), bad])
    context = _context()

    result = reconcile_ledger(context)

    assert result.failed, result.message
    assert result.message == "observations file has 1 invalid rows - see the log"
    assert result.details["invalid_rows"] == 1
    assert context.state.ledger.entries == [], "a bad row after good ones left a partial fold"
    assert context.state.velocity.sampled_over_days == 0


def test_every_invalid_row_is_counted(isolated_dirs: dict[str, Path]) -> None:
    _write(
        isolated_dirs["data"] / FILENAME,
        [_bad_row(id="a", delta=0), _bad_row(id="b", currency="gold"), _bad_row(id="c", at="never")],
    )
    context = _context()

    result = reconcile_ledger(context)

    assert result.failed
    assert result.message == "observations file has 3 invalid rows - see the log"
    assert result.details["invalid_rows"] == 3


def test_the_invalid_row_log_names_the_index_the_id_and_the_reason(
    isolated_dirs: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    _write(isolated_dirs["data"] / FILENAME, [*_rows(), _bad_row(id="zero-one", delta=0)])
    context = _context()

    with caplog.at_level("ERROR", logger="headless.jobs"):
        result = reconcile_ledger(context)

    assert result.failed
    text = caplog.text
    # The index is the JSON array position, written the way the file reads.
    assert "observations[3]" in text
    assert "zero-one" in text
    assert "delta" in text


# ---------------------------------------------------------------------------
# PASS arm - the fold
# ---------------------------------------------------------------------------


def test_the_fold_lands_in_the_ledger_with_source_observation(isolated_dirs: dict[str, Path]) -> None:
    now = _now()
    _write(isolated_dirs["data"] / FILENAME, _rows(now))
    context = _context()

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert result.message == "folded 3 observations into the ledger"
    assert result.details["observations"] == 3
    entries = context.state.ledger.entries
    assert len(entries) == 3
    assert {e.source for e in entries} == {"observation"}
    assert [(e.currency, e.delta) for e in entries] == [
        (CurrencyKind.PRIMOGEM, 60),
        (CurrencyKind.PRIMOGEM, 540),
        (CurrencyKind.INTERTWINED_FATE, -10),
    ]
    # The reason is the note when given, else the row id.
    assert [e.reason for e in entries] == [
        "daily commissions",
        "event-shop",
        "ten wishes on the character banner",
    ]
    assert entries[0].occurred_at == now - timedelta(days=1)
    assert entries[0].occurred_at.tzinfo is not None
    # Every entry carries its own generated id; none is empty or repeated.
    ids = [e.entry_id for e in entries]
    assert all(ids) and len(set(ids)) == 3


def test_a_naive_timestamp_is_read_as_utc(isolated_dirs: dict[str, Path]) -> None:
    moment = datetime(2026, 9, 30, 12, 0, 0)
    _write(
        isolated_dirs["data"] / FILENAME,
        [{"id": "naive", "at": moment.isoformat(), "currency": "mora", "delta": 1000}],
    )
    context = _context()

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert context.state.ledger.entries[0].occurred_at == moment.replace(tzinfo=UTC)


def test_a_negative_delta_is_a_spend_the_velocity_ignores(isolated_dirs: dict[str, Path]) -> None:
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert context.state.ledger.balance_of(CurrencyKind.INTERTWINED_FATE) == -10
    assert context.state.velocity.intertwined_fates_per_day == 0.0


def test_velocity_is_re_estimated_from_the_folded_ledger(isolated_dirs: dict[str, Path]) -> None:
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()
    assert context.state.velocity.sampled_over_days == 0

    result = reconcile_ledger(context)

    assert result.ok, result.message
    velocity = context.state.velocity
    assert velocity.sampled_over_days == 30
    assert velocity.primogems_per_day == pytest.approx(600 / 30)
    assert velocity.resin_per_day == 180
    assert result.details["sampled_over_days"] == 30


def test_an_observation_outside_the_window_is_recorded_but_not_sampled(
    isolated_dirs: dict[str, Path],
) -> None:
    old = _now() - timedelta(days=90)
    _write(
        isolated_dirs["data"] / FILENAME,
        [{"id": "old", "at": old.isoformat(), "currency": "primogem", "delta": 1600}],
    )
    context = _context()

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert context.state.ledger.balance_of(CurrencyKind.PRIMOGEM) == 1600
    assert context.state.velocity.sampled_over_days == 0
    assert result.details["sampled_over_days"] == 0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_two_passes_produce_the_same_ledger_length(isolated_dirs: dict[str, Path]) -> None:
    """Rebuild-per-pass: a fresh state each pass, the whole file each time."""
    _write(isolated_dirs["data"] / FILENAME, _rows())

    first = _context()
    second = _context()
    assert reconcile_ledger(first).ok
    assert reconcile_ledger(second).ok

    assert len(first.state.ledger.entries) == 3
    assert len(second.state.ledger.entries) == 3


def test_a_second_call_in_one_pass_skips_and_adds_nothing(isolated_dirs: dict[str, Path]) -> None:
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()
    assert reconcile_ledger(context).ok
    velocity = context.state.velocity

    again = reconcile_ledger(context)

    assert again.skipped
    assert again.message == MESSAGE_ALREADY
    assert len(context.state.ledger.entries) == 3
    assert context.state.velocity == velocity


def test_entries_from_another_source_do_not_block_the_fold(isolated_dirs: dict[str, Path]) -> None:
    """Only an OBSERVATION entry marks the pass as already folded."""
    from core.ledger import record

    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()
    record(context.state.ledger, CurrencyKind.MORA, 500, "seed", source="manual")

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert len(context.state.ledger.entries) == 4


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def test_the_default_path_is_the_data_dir_file(isolated_dirs: dict[str, Path]) -> None:
    """RC_DATA_DIR / income_observations.json, the same resolution persist_state uses."""
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert len(context.state.ledger.entries) == 3


def test_the_observations_path_option_overrides_the_data_dir(
    tmp_path: Path, isolated_dirs: dict[str, Path]
) -> None:
    # A decoy in the data dir with one row; the override holds three.
    _write(isolated_dirs["data"] / FILENAME, _rows()[:1])
    override = _write(tmp_path / "elsewhere.json", _rows())
    context = _context(options={"observations_path": str(override)})

    result = reconcile_ledger(context)

    assert result.ok, result.message
    assert len(context.state.ledger.entries) == 3


def test_an_absent_override_skips_rather_than_falling_back(
    tmp_path: Path, isolated_dirs: dict[str, Path]
) -> None:
    """An explicit path that is missing is "not configured", not a fallback."""
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context(options={"observations_path": str(tmp_path / "missing.json")})

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == MESSAGE_NO_FILE
    assert context.state.ledger.entries == []


def test_a_directory_at_the_path_counts_as_absent(isolated_dirs: dict[str, Path]) -> None:
    (isolated_dirs["data"] / FILENAME).mkdir()
    context = _context()

    result = reconcile_ledger(context)

    assert result.skipped
    assert result.message == MESSAGE_NO_FILE


# ---------------------------------------------------------------------------
# Messages name the file, never a directory
# ---------------------------------------------------------------------------


def test_no_message_names_a_directory(tmp_path: Path, isolated_dirs: dict[str, Path]) -> None:
    """A path under the user profile carries the account name. Every status."""
    messages: list[str] = []

    absent = _context()
    messages.append(reconcile_ledger(absent).message)

    (isolated_dirs["data"] / FILENAME).write_text("{bad", encoding="utf-8", newline="\n")
    messages.append(reconcile_ledger(_context()).message)

    _write(isolated_dirs["data"] / FILENAME, [*_rows(), _bad_row(delta=0)])
    messages.append(reconcile_ledger(_context()).message)

    _write(isolated_dirs["data"] / FILENAME, _rows())
    folded = _context()
    messages.append(reconcile_ledger(folded).message)
    messages.append(reconcile_ledger(folded).message)
    messages.append(reconcile_ledger(_context(dry_run=True)).message)

    assert len(messages) == 6
    for message in messages:
        assert message
        assert "/" not in message, message
        assert "\\" not in message, message
        assert str(tmp_path) not in message, message


# ---------------------------------------------------------------------------
# End to end: a live pass persists the folded ledger and velocity
# ---------------------------------------------------------------------------


class _Profile:
    uid = UID
    adventure_rank = 58
    world_level = 7
    characters = ()
    ttl_seconds = 60
    fetched_at = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


class _Client:
    """Stands in for ingest.enka_client so the pass has a profile without a fetch."""

    @staticmethod
    def fetch_profile(uid: str) -> _Profile:
        return _Profile()


def test_a_live_pass_persists_the_folded_ledger_and_velocity(
    isolated_dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run_pass(dry_run=False, ...)` in-process: it takes no slot and writes only
    under the two monkeypatched directories. The profile comes from a stub
    client, not the network, so sync_profile produces state and the whole
    chain - fold, velocity, snapshot - is exercised for real."""
    real_import = jobs_mod._try_import

    def _stubbed(dotted: str) -> Any:
        return _Client if dotted == "ingest.enka_client" else real_import(dotted)

    monkeypatch.setattr(jobs_mod, "_try_import", _stubbed)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "0")
    _write(isolated_dirs["data"] / FILENAME, _rows())
    cwd_before = sorted(os.listdir(os.getcwd()))

    outcome = runner_mod.run_pass(uid=UID, dry_run=False, runtime_dir=str(isolated_dirs["runtime"]))

    by_name = {r.name: r for r in outcome.results}
    assert by_name["sync_profile"].ok, by_name["sync_profile"].message
    assert by_name["reconcile_state"].ok, by_name["reconcile_state"].message
    assert by_name["reconcile_ledger"].ok, by_name["reconcile_ledger"].message
    assert by_name["persist_state"].ok, by_name["persist_state"].message
    assert not any(r.failed for r in outcome.results), [r.message for r in outcome.results if r.failed]

    snapshot = isolated_dirs["data"] / "account_state.json"
    assert snapshot.is_file()
    restored = read_state(snapshot)
    assert restored is not None
    assert restored.uid == UID
    assert len(restored.ledger.entries) == 3
    assert {e.source for e in restored.ledger.entries} == {"observation"}
    assert restored.ledger.balance_of(CurrencyKind.PRIMOGEM) == 600
    assert restored.velocity.sampled_over_days == 30
    assert restored.velocity.primogems_per_day == pytest.approx(20.0)

    # The pass was live: the run summary landed in the runtime dir, and nothing
    # landed anywhere else - in particular no slot bucket in the cwd.
    assert (isolated_dirs["runtime"] / "health.json").is_file()
    assert sorted(os.listdir(os.getcwd())) == cwd_before
    assert not any(name.startswith("C:") for name in os.listdir(os.getcwd()))


def test_persist_state_carries_the_fold_when_driven_directly(isolated_dirs: dict[str, Path]) -> None:
    """The two jobs back to back with state set, the way the ordered pass runs them."""
    _write(isolated_dirs["data"] / FILENAME, _rows())
    context = _context()

    assert reconcile_ledger(context).ok
    assert persist_state(context).ok

    restored = read_state(isolated_dirs["data"] / "account_state.json")
    assert restored is not None
    assert len(restored.ledger.entries) == 3
    assert restored.velocity.sampled_over_days == 30
