"""Client tests. NONE of these touch the network.

The transport, clock and sleeper are all injected, so the whole class is
exercised offline and deterministically. The single test that WOULD reach out is
marked `network` (declared in pytest.ini) and additionally skipped unless an
environment variable is set, so a CI run that forgets `-m "not network"` still
does not spend somebody's rate limit.
"""
from __future__ import annotations

import io
import json
import os
import urllib.error
import urllib.request

import pytest

from ingest.enka_client import (
    DEFAULT_TTL_SECONDS,
    MAX_BATCH_UIDS,
    MESSAGE_CACHED,
    MESSAGE_MALFORMED,
    MESSAGE_OK,
    MESSAGE_UNEXPECTED,
    STATUS_MESSAGES,
    STATUS_UNREACHABLE,
    EnkaClient,
    EnkaConfig,
    EnkaConfigError,
    EnkaUsageError,
    _urllib_transport,
    iter_status_messages,
)

UID = "000000000"

#: Substrings that would betray a raw error leaking into a user-facing message.
LEAK_MARKERS = (
    "Traceback",
    "HTTPError",
    "URLError",
    "urllib",
    "Errno",
    "http://",
    "https://",
    "<",
    "Exception",
)


class FakeTransport:
    """Scripted transport. Records every call so suppression can be proven."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        if not self.responses:
            raise AssertionError("transport called more times than the test scripted")
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _body(ttl: int = 60, **extra) -> bytes:
    payload = {"uid": UID, "ttl": ttl, "playerInfo": {"nickname": "SyntheticTraveler"}}
    payload.update(extra)
    return json.dumps(payload).encode("utf-8")


def _client(tmp_path, responses, *, user_agent="resin-compute/0.1 (test)", **config_kwargs):
    transport = FakeTransport(responses)
    clock = FakeClock()
    slept: list[float] = []
    config = EnkaConfig(user_agent=user_agent, cache_dir=tmp_path / "cache", **config_kwargs)
    client = EnkaClient(config=config, transport=transport, clock=clock, sleeper=slept.append)
    return client, transport, clock, slept


# ---------------------------------------------------------------------------
# User-Agent is required by upstream policy
# ---------------------------------------------------------------------------


def test_missing_user_agent_refuses_the_request(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())], user_agent="")

    with pytest.raises(EnkaConfigError) as excinfo:
        client.fetch_profile(UID)

    # The error names the config key so the fix is obvious.
    assert "user_agent" in str(excinfo.value)
    # And nothing was sent. A default User-Agent would be a silent policy breach.
    assert transport.calls == []


def test_whitespace_only_user_agent_is_still_refused(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())], user_agent="   ")
    with pytest.raises(EnkaConfigError):
        client.fetch_profile(UID)
    assert transport.calls == []


def test_custom_user_agent_is_sent(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())], user_agent="resin-compute/0.1 (test)")
    client.fetch_profile(UID)
    assert transport.calls[0][1]["User-Agent"] == "resin-compute/0.1 (test)"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def test_full_and_info_endpoints_are_well_formed(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())])
    client.fetch_profile(UID)
    client.fetch_profile(UID, force=True, info_only=True)

    assert transport.calls[0][0] == f"https://enka.network/api/uid/{UID}/"
    assert transport.calls[1][0] == f"https://enka.network/api/uid/{UID}/?info"
    # The brief's malformed "https://enka.network<uid>" must never be produced.
    for url, _headers, _timeout in transport.calls:
        assert "/api/uid/" in url
        assert f"enka.network{UID}" not in url


# ---------------------------------------------------------------------------
# Status codes degrade to friendly, constant messages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [400, 404, 424, 429, 500, 503, STATUS_UNREACHABLE])
def test_documented_status_maps_to_its_friendly_message(tmp_path, status):
    client, _transport, _clock, _slept = _client(tmp_path, [(status, b"raw upstream body")], max_retries=0)
    result = client.fetch_profile("111111111")

    assert result.ok is False
    assert result.profile_json is None
    assert result.status == status
    assert result.friendly_message == STATUS_MESSAGES[status]


@pytest.mark.parametrize("status", [400, 404, 424, 429, 500, 503, STATUS_UNREACHABLE, 418])
def test_no_raw_error_text_reaches_the_caller(tmp_path, status):
    raw = b"Traceback (most recent call last): urllib.error.HTTPError: <html>boom</html>"
    client, _transport, _clock, _slept = _client(tmp_path, [(status, raw)], max_retries=0)
    result = client.fetch_profile("111111111")

    for marker in LEAK_MARKERS:
        assert marker not in result.friendly_message
    assert "boom" not in result.friendly_message
    assert result.friendly_message.strip() != ""


def test_undocumented_status_gets_a_generic_friendly_message(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(418, b"")], max_retries=0)
    result = client.fetch_profile("111111111")
    assert result.ok is False
    assert result.status == 418
    assert result.friendly_message not in ("", None)
    # Exactly the documented constant, not merely something non-empty.
    assert result.friendly_message == MESSAGE_UNEXPECTED
    # And an undocumented status is not on the retry set, so no wait is advised.
    assert result.retry_after_seconds == 0.0


def test_bad_uid_is_answered_locally_without_spending_rate_limit(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())])
    result = client.fetch_profile("not-a-uid")

    assert result.ok is False
    assert result.status == 400
    assert result.friendly_message == STATUS_MESSAGES[400]
    assert transport.calls == []


def test_malformed_body_degrades_rather_than_raising(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(200, b"{not json")])
    result = client.fetch_profile(UID)
    assert result.ok is False
    assert result.friendly_message == MESSAGE_MALFORMED
    for marker in LEAK_MARKERS:
        assert marker not in result.friendly_message


def test_successful_fetch_returns_the_payload(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    result = client.fetch_profile(UID)

    assert result.ok is True
    assert result.status == 200
    assert result.friendly_message == MESSAGE_OK
    assert result.ttl_seconds == 300
    assert result.profile_json["playerInfo"]["nickname"] == "SyntheticTraveler"


def test_missing_ttl_falls_back_to_a_short_default(tmp_path):
    body = json.dumps({"uid": UID, "playerInfo": {}}).encode("utf-8")
    client, _transport, _clock, _slept = _client(tmp_path, [(200, body)])
    result = client.fetch_profile(UID)
    assert result.ttl_seconds == DEFAULT_TTL_SECONDS


# ---------------------------------------------------------------------------
# ttl cache SUPPRESSES the second request - cached data still burns rate limit
# ---------------------------------------------------------------------------


def test_ttl_cache_suppresses_a_second_request_inside_the_window(tmp_path):
    client, transport, clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])

    first = client.fetch_profile(UID)
    assert first.from_cache is False
    assert len(transport.calls) == 1

    clock.advance(299)
    second = client.fetch_profile(UID)

    assert second.ok is True
    assert second.from_cache is True
    assert second.friendly_message == MESSAGE_CACHED
    assert second.profile_json == first.profile_json
    # The whole point: no second request was made.
    assert len(transport.calls) == 1


def test_request_resumes_after_the_ttl_expires(tmp_path):
    client, transport, clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    client.fetch_profile(UID)
    clock.advance(301)
    third = client.fetch_profile(UID)

    assert third.from_cache is False
    assert len(transport.calls) == 2


def test_force_bypasses_the_cache_read(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    client.fetch_profile(UID)
    client.fetch_profile(UID, force=True)
    assert len(transport.calls) == 2


def test_cache_is_written_atomically_and_leaves_no_temp_file(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    client.fetch_profile(UID)

    cache_file = client.cache_path_for(UID)
    assert cache_file.exists()
    assert list(cache_file.parent.glob("*.tmp")) == []
    envelope = json.loads(cache_file.read_text(encoding="utf-8"))
    assert envelope["ttl"] == 300
    assert envelope["body"]["uid"] == UID


def test_corrupt_cache_file_is_ignored_not_fatal(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    cache_file = client.cache_path_for(UID)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{not json", encoding="utf-8")

    result = client.fetch_profile(UID)
    assert result.ok is True
    assert len(transport.calls) == 1


# ---------------------------------------------------------------------------
# Retries: 429 / 503 only, bounded, exponential
# ---------------------------------------------------------------------------


def test_retry_on_429_then_success(tmp_path):
    client, transport, _clock, slept = _client(tmp_path, [(429, b""), (200, _body())], backoff_base_seconds=2.0)
    result = client.fetch_profile(UID)

    assert result.ok is True
    assert result.retries == 1
    assert len(transport.calls) == 2
    assert slept == [2.0]


def test_retries_are_bounded_and_exponential(tmp_path):
    client, transport, _clock, slept = _client(
        tmp_path, [(503, b"")], max_retries=3, backoff_base_seconds=1.0
    )
    result = client.fetch_profile(UID)

    assert result.ok is False
    assert result.status == 503
    # 3 retries means 4 attempts total, then it stops. It does not loop forever.
    assert len(transport.calls) == 4
    assert slept == [1.0, 2.0, 4.0]
    assert result.retry_after_seconds == 8.0


def test_non_transient_statuses_are_not_retried(tmp_path):
    for status in (400, 404, 424, 500):
        client, transport, _clock, slept = _client(tmp_path, [(status, b"")], max_retries=3)
        result = client.fetch_profile("111111111")
        assert len(transport.calls) == 1, f"status {status} must not be retried"
        assert slept == []
        # Off the retry set there is no backoff to report either.
        assert result.retries == 0
        assert result.retry_after_seconds == 0.0


# ---------------------------------------------------------------------------
# The upstream no-bulk-collection prohibition is ENFORCED, not just documented
# ---------------------------------------------------------------------------


def test_batch_over_the_documented_limit_is_refused(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())])
    uids = [str(100000000 + n) for n in range(MAX_BATCH_UIDS + 1)]

    with pytest.raises(EnkaUsageError) as excinfo:
        client.fetch_profiles(uids)

    message = str(excinfo.value)
    assert "enumerate UIDs" in message
    assert transport.calls == []


def test_batch_at_the_limit_is_allowed(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=1))])
    uids = [str(100000000 + n) for n in range(MAX_BATCH_UIDS)]
    results = client.fetch_profiles(uids)

    assert len(results) == MAX_BATCH_UIDS
    assert all(r.ok for r in results)
    assert len(transport.calls) == MAX_BATCH_UIDS


def test_module_docstring_records_the_upstream_prohibition():
    from ingest import enka_client

    assert "don't try to enumerate UIDs" in enka_client.__doc__
    assert "massive query jobs" in enka_client.__doc__


# ---------------------------------------------------------------------------
# Boundary arms - each pins a branch the tests above leave unproven.
# ---------------------------------------------------------------------------


# -- local UID shape check: what is sent upstream and what is answered here --


def test_uid_shape_check_bounds_are_six_to_twelve_digits(tmp_path):
    """Pins the client's own band. A change here changes what spends rate limit.

    The 6..12 band is UNDOCUMENTED outside enka_client.py:268-269 - not in
    SPEC section 4 or 5, CLAUDE.md or the README. This arm is its only record;
    it pins the implementation, not a sourced fact about UID lengths.
    """
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=1))])

    assert client.fetch_profile("12345").status == 400
    assert client.fetch_profile("1234567890123").status == 400
    assert transport.calls == []  # both answered locally

    assert client.fetch_profile("123456").ok is True
    assert client.fetch_profile("123456789012").ok is True
    assert len(transport.calls) == 2


def test_int_and_padded_uids_are_normalised_before_the_request(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=1))])

    by_int = client.fetch_profile(100000005)
    assert by_int.ok is True
    assert by_int.uid == "100000005"
    assert transport.calls[-1][0] == "https://enka.network/api/uid/100000005/"

    padded = client.fetch_profile(" 100000004 ")
    assert padded.uid == "100000004"
    assert transport.calls[-1][0] == "https://enka.network/api/uid/100000004/"


def test_base_url_trailing_slash_is_normalised(tmp_path):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body())], base_url="https://example.invalid/")
    client.fetch_profile(UID)
    assert transport.calls[0][0] == f"https://example.invalid/api/uid/{UID}/"
    assert "//api" not in transport.calls[0][0]


# -- body handling edges ---------------------------------------------------


def test_json_body_that_is_not_an_object_is_malformed(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(200, b"[]")])
    result = client.fetch_profile(UID)
    assert result.ok is False
    assert result.status == 200
    assert result.profile_json is None
    assert result.friendly_message == MESSAGE_MALFORMED


def test_invalid_utf8_body_is_malformed_and_leaks_nothing(tmp_path):
    client, _transport, _clock, _slept = _client(tmp_path, [(200, b"\xff\xfe")])
    result = client.fetch_profile(UID)
    assert result.ok is False
    assert result.friendly_message == MESSAGE_MALFORMED
    for marker in LEAK_MARKERS:
        assert marker not in result.friendly_message


@pytest.mark.parametrize(
    ("raw_ttl", "expected"),
    [
        ("300", 300),
        (-5, DEFAULT_TTL_SECONDS),
        ("abc", DEFAULT_TTL_SECONDS),
        ([1], DEFAULT_TTL_SECONDS),
    ],
)
def test_ttl_coercion_edges(tmp_path, raw_ttl, expected):
    """A string-coded ttl is read; a negative or unreadable one falls back to the default.

    Not pinned: what a float ttl truncates to, and what a ttl of exactly 0
    becomes. Both are implementation choices at enka_client.py:346-349 with no
    documented contract (DEFAULT_TTL_SECONDS is documented as the fallback when
    upstream OMITS ttl, and SPEC section 4 says ttl is honoured as sent).
    """
    client, _transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=raw_ttl))])
    result = client.fetch_profile(UID)
    assert result.ok is True
    assert result.ttl_seconds == expected


# -- cache edges -----------------------------------------------------------


def test_force_still_rearms_ttl_suppression(tmp_path):
    """Docstring: force bypasses the cache READ, not the ttl WRITE."""
    client, transport, clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])

    client.fetch_profile(UID)  # expires at t+300
    clock.advance(200)
    forced = client.fetch_profile(UID, force=True)  # re-arms to t+500
    assert forced.from_cache is False
    clock.advance(200)  # t+400: past the FIRST expiry, inside the re-armed one

    third = client.fetch_profile(UID)
    assert third.from_cache is True
    assert third.ttl_seconds == 100
    assert len(transport.calls) == 2


def test_cache_expiry_at_exactly_zero_remaining_refetches(tmp_path):
    client, transport, clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    client.fetch_profile(UID)
    clock.advance(300)
    result = client.fetch_profile(UID)
    assert result.from_cache is False
    assert len(transport.calls) == 2


@pytest.mark.parametrize(
    "envelope",
    [
        "[]",
        json.dumps({"expires_at": "soon", "body": {}}),
        json.dumps({"expires_at": 2000, "body": []}),
        json.dumps({"expires_at": 2000}),
    ],
)
def test_malformed_cache_envelopes_are_ignored(tmp_path, envelope):
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    cache_file = client.cache_path_for(UID)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(envelope, encoding="utf-8")

    result = client.fetch_profile(UID)
    assert result.ok is True
    assert result.from_cache is False
    assert len(transport.calls) == 1


def test_unwritable_cache_dir_does_not_fail_the_fetch(tmp_path):
    """A cache that cannot be written is a degraded optimisation, never a failed fetch."""
    client, transport, _clock, _slept = _client(tmp_path, [(200, _body(ttl=300))])
    (tmp_path / "cache").write_text("a regular file where the cache dir should be", encoding="utf-8")

    result = client.fetch_profile(UID)
    assert result.ok is True
    assert result.friendly_message == MESSAGE_OK
    assert (tmp_path / "cache").is_file()  # nothing was clobbered to make room
    # And with no cache, the next call goes upstream again rather than failing.
    assert client.fetch_profile(UID).from_cache is False
    assert len(transport.calls) == 2


# -- retry edges -----------------------------------------------------------


def test_negative_max_retries_is_clamped_to_zero(tmp_path):
    client, transport, _clock, slept = _client(tmp_path, [(429, b"")], max_retries=-3, backoff_base_seconds=2.0)
    result = client.fetch_profile(UID)
    assert len(transport.calls) == 1
    assert slept == []
    assert result.retries == 0
    assert result.retry_after_seconds == 2.0  # base * 2**0


# -- the default transport, with urlopen monkeypatched: NO socket is opened --


class _FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b'{"ok": 1}'

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _UnreadableBody:
    """A response body whose read() fails, standing in for a dropped connection."""

    def read(self, *args):
        raise OSError("read failed")

    def close(self):
        return None


def test_urllib_transport_success_passes_url_headers_method_and_timeout(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    url = f"https://example.invalid/api/uid/{UID}/"
    result = _urllib_transport(url, {"User-Agent": "resin-compute/0.1 (test)"}, 7.5)

    assert result == (200, b'{"ok": 1}')
    assert seen["request"].full_url == url
    assert seen["request"].get_method() == "GET"
    assert seen["request"].get_header("User-agent") == "resin-compute/0.1 (test)"
    assert seen["timeout"] == 7.5


def test_urllib_transport_converts_http_error_to_its_code_and_body(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", None, io.BytesIO(b"rate limited"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _urllib_transport("https://example.invalid/", {}, 1.0) == (429, b"rate limited")


def test_urllib_transport_tolerates_an_unreadable_http_error_body(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", None, _UnreadableBody())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _urllib_transport("https://example.invalid/", {}, 1.0) == (503, b"")


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("name resolution failed"),
        TimeoutError("timed out"),
        ConnectionResetError("connection reset by peer"),
    ],
    ids=["URLError", "TimeoutError", "ConnectionResetError"],
)
def test_urllib_transport_converts_connection_failures_to_unreachable(monkeypatch, failure):
    """The exception text names the URL; only the sentinel status travels up."""

    def fake_urlopen(request, timeout):
        raise failure

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    status, body = _urllib_transport("https://example.invalid/", {}, 1.0)
    assert status == STATUS_UNREACHABLE
    assert body == b""


# -- the status table export -----------------------------------------------


def test_iter_status_messages_is_sorted_and_complete():
    listed = list(iter_status_messages())
    assert listed == sorted(STATUS_MESSAGES.items())
    assert listed[0][0] == STATUS_UNREACHABLE
    assert len(listed) == len(STATUS_MESSAGES)


# ---------------------------------------------------------------------------
# The only test that would touch the network. Marked AND skipped by default.
# ---------------------------------------------------------------------------


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("RESIN_ALLOW_NETWORK") != "1",
    reason="live fetch is opt-in: set RESIN_ALLOW_NETWORK=1 and it still needs a real UID",
)
def test_live_fetch_smoke(tmp_path):  # pragma: no cover - never runs in CI
    uid = os.environ.get("RESIN_TEST_UID", "")
    if not uid:
        pytest.skip("set RESIN_TEST_UID to run the live smoke test")
    client = EnkaClient(
        config=EnkaConfig(user_agent="resin-compute/0.1 (live smoke test)", cache_dir=tmp_path / "cache")
    )
    result = client.fetch_profile(uid)
    assert result.friendly_message
