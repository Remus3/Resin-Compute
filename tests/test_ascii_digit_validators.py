"""ASCII-only digit validators: the siblings of the UIGF numeric-string fix.

`str.isdigit` accepts superscripts and every Unicode Nd digit, backslash-d
accepts every Nd digit, and `^...$` under `re.match` accepts a trailing
newline. Each validator below must take ASCII [0-9] only, matched over the
whole string. Non-ASCII inputs are built with chr(), never typed as literals
(banned-glyph rule).
"""

from __future__ import annotations

import pytest

from core.provenance import (
    DataRow,
    ObservationStatus,
    ProvenanceError,
    ProvenanceRecord,
    ReadMethod,
    SourceKind,
    SourceRef,
    validate_row,
)
from ingest.enka_client import (
    MAX_BATCH_UIDS,
    STATUS_MESSAGES,
    EnkaClient,
    EnkaConfig,
    EnkaUsageError,
)

GOOD_SHA = "a" * 64
GOOD_WHEN = "2026-09-07T10:00:25Z"


class _NoCallTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url, headers, timeout):
        self.calls.append(url)
        return 404, b""


def _client(tmp_path) -> tuple[EnkaClient, _NoCallTransport]:
    transport = _NoCallTransport()
    config = EnkaConfig(user_agent="resin-compute-test/0.1", cache_dir=tmp_path)
    return EnkaClient(config=config, transport=transport), transport


@pytest.mark.parametrize(
    ("label", "uid"),
    [
        ("superscript two", "12345678" + chr(0x00B2)),
        ("Arabic-Indic digits", "".join(chr(0x0660 + n) for n in range(1, 10))),
        ("fullwidth digits", "".join(chr(0xFF10 + n) for n in range(1, 10))),
        ("Devanagari digit tail", "12345678" + chr(0x0969)),
    ],
)
def test_a_uid_with_non_ascii_digits_is_refused_locally(tmp_path, label: str, uid: str):
    client, transport = _client(tmp_path)
    result = client.fetch_profile(uid)
    assert result.friendly_message == STATUS_MESSAGES[400], label
    assert transport.calls == [], f"{label}: a bad UID must never reach the network"


def test_an_ascii_uid_still_reaches_the_transport(tmp_path):
    """Non-vacuity: the guard must not refuse a legitimate UID."""
    client, transport = _client(tmp_path)
    client.fetch_profile("123456789")
    assert len(transport.calls) == 1


@pytest.mark.parametrize("uid", ["12345", "1234567890123"])
def test_the_uid_length_rule_survives(tmp_path, uid: str):
    client, transport = _client(tmp_path)
    assert client.fetch_profile(uid).friendly_message == STATUS_MESSAGES[400]
    assert transport.calls == []


def test_the_no_enumeration_batch_cap_survives(tmp_path):
    client, transport = _client(tmp_path)
    with pytest.raises(EnkaUsageError):
        client.fetch_profiles([str(100000000 + n) for n in range(MAX_BATCH_UIDS + 1)])
    assert transport.calls == []


def _row(*, captured: str = GOOD_WHEN, observed: str = GOOD_WHEN, sha: str = GOOD_SHA) -> DataRow:
    source = SourceRef(
        kind=SourceKind.CROP, locator="evidence/detail_crop.png", sha256=sha, captured_utc=captured
    )
    record = ProvenanceRecord(
        record_id="rec-1",
        claim="the detail pane reads level 20",
        read_method=ReadMethod.HUMAN_EYE,
        source=source,
        observed_utc=observed,
        status=ObservationStatus.VERIFIED,
        reader="human",
    )
    return DataRow(row_id="row-1", table="roster", key="slot-1", payload={"level": 20}, provenance=(record,))


def test_a_clean_provenance_row_still_validates():
    """Non-vacuity: the legitimate neighbour survives the tightening."""
    validate_row(_row())


@pytest.mark.parametrize(
    ("label", "when"),
    [
        ("Arabic-Indic year digit", "202" + chr(0x0666) + "-09-07T10:00:25Z"),
        ("fullwidth seconds", "2026-09-07T10:00:" + chr(0xFF12) + chr(0xFF15) + "Z"),
        ("Arabic-Indic fraction", "2026-09-07T10:00:25." + chr(0x0661) + "Z"),
        ("trailing newline", GOOD_WHEN + "\n"),
    ],
)
@pytest.mark.parametrize("field", ["captured", "observed"])
def test_a_timestamp_with_non_ascii_digits_is_refused(label: str, when: str, field: str):
    with pytest.raises(ProvenanceError):
        validate_row(_row(**{field: when}))


def test_a_digest_with_a_trailing_newline_is_refused():
    with pytest.raises(ProvenanceError):
        validate_row(_row(sha=GOOD_SHA + "\n"))
