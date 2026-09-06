"""HTTP service tests.

The load-bearing rule here is FAIL-SOFT (SPEC section 2, inherited verbatim
from Riot Commander): a malformed request returns a friendly 400 and the raw
exception goes to the log, never into the response body. `_RAW_ERROR_MARKERS`
below is the concrete form of that rule - if any of those strings ever reaches
a caller, the engine has leaked its internals.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import ThreadingHTTPServer

import pytest

from agents.pity_engine import ENGINE_VERSION
from agents.pity_engine.__main__ import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    build_server,
    forecast_payload,
    handle_request,
    health_payload,
    main,
)

# Substrings that would betray a raw exception or parser complaint. None of
# these may ever appear in a response body.
_RAW_ERROR_MARKERS = (
    "Traceback",
    "ValueError",
    "TypeError",
    "KeyError",
    "JSONDecodeError",
    "Expecting value",
    "line 1 column",
    "most recent call last",
    "File \"",
)


def _assert_no_raw_error_text(blob: str) -> None:
    for marker in _RAW_ERROR_MARKERS:
        assert marker not in blob, f"raw error text {marker!r} leaked into a response body"


@contextmanager
def _running_server() -> Iterator[str]:
    """Serve the real handler on an ephemeral port for the duration of a test."""
    server: ThreadingHTTPServer = build_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # server_address is typed as a union that admits bytes for the host, so
        # interpolating it directly would render b'127.0.0.1' rather than the
        # address. Decode explicitly instead of formatting whatever arrives.
        raw_host, port = server.server_address[0], server.server_address[1]
        host = raw_host.decode() if isinstance(raw_host, bytes) else str(raw_host)
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post(base: str, path: str, body: bytes) -> tuple[int, str]:
    request = urllib.request.Request(
        base + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _get(base: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


# ---------------------------------------------------------------------------
# Payload builders, exercised without a socket
# ---------------------------------------------------------------------------


def test_health_payload_carries_the_engine_version() -> None:
    payload = health_payload()
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["status"] == "ok"
    assert isinstance(payload["pid"], int)
    assert payload["pid"] > 0
    assert payload["uptime_seconds"] >= 0.0


def test_default_port_comes_from_the_registry_not_a_local_literal() -> None:
    """The number lives in `core/ports.py` and nowhere else.

    This deliberately does NOT restate the integer. The engine originally sat on
    a port inside Daemon Slayer's reserved block; a literal here is exactly what
    let that survive review. See ADR-004.
    """
    from core.ports import ENGINE, is_ours

    assert DEFAULT_PORT == ENGINE
    assert is_ours(DEFAULT_PORT)
    assert DEFAULT_HOST == "127.0.0.1"


def test_forecast_payload_round_trips_a_full_request() -> None:
    payload = forecast_payload(
        {
            "pity_5star": 89,
            "has_guarantee": True,
            "consecutive_5050_losses": 0,
            "fate_points": 0,
            "banner": "character_event",
            "target_count": 1,
            "pull_budget": 1,
        }
    )
    assert payload["probability"] == 1.0
    assert payload["banner"] == "character_event"
    assert payload["target_count"] == 1
    assert payload["pull_budget"] == 1
    assert payload["engine_version"] == ENGINE_VERSION
    assert sum(payload["distribution"]) == pytest.approx(1.0, abs=1e-9)
    assert payload["expected_pulls"] == pytest.approx(1.0, abs=1e-12)
    # The whole payload must survive a JSON round trip unchanged.
    assert json.loads(json.dumps(payload)) == payload


def test_forecast_payload_defaults_are_sane() -> None:
    payload = forecast_payload({})
    assert payload["banner"] == "character_event"
    assert payload["target_count"] == 1
    assert payload["pull_budget"] == 0
    assert payload["probability"] == 0.0


# ---------------------------------------------------------------------------
# Routing and fail-soft, exercised without a socket
# ---------------------------------------------------------------------------


def test_handle_request_serves_health() -> None:
    status, payload = handle_request("GET", "/health", b"")
    assert status == 200
    assert payload["engine_version"] == ENGINE_VERSION


def test_handle_request_unknown_route_is_404() -> None:
    status, payload = handle_request("GET", "/nope", b"")
    assert status == 404
    assert payload["status"] == "error"
    _assert_no_raw_error_text(json.dumps(payload))


@pytest.mark.parametrize(
    "body",
    [
        b"{not json",
        b"[]",
        b'"a string"',
        b'{"target_count": 0}',
        b'{"pull_budget": -5}',
        b'{"banner": "not_a_banner"}',
        b'{"pity_5star": "seventy"}',
        b'{"pity_5star": -1}',
        b'{"consecutive_5050_losses": 9}',
        b'{"fate_points": 7}',
        b'{"pity_5star": 95}',
    ],
)
def test_malformed_forecast_fails_soft(body: bytes) -> None:
    """Every one of these is a 400 with a friendly message and nothing else."""
    status, payload = handle_request("POST", "/forecast", body)
    assert status == 400
    assert payload["status"] == "error"
    assert payload["engine_version"] == ENGINE_VERSION
    blob = json.dumps(payload)
    _assert_no_raw_error_text(blob)
    assert "check the request fields" in payload["error"]


def test_handle_request_never_raises() -> None:
    """The routing boundary is total - it answers, whatever it is handed."""
    for method, path, body in (
        ("POST", "/forecast", b"\xff\xfe not utf-8"),
        ("DELETE", "/forecast", b""),
        ("GET", "/forecast", b""),
        ("POST", "/health", b""),
    ):
        status, payload = handle_request(method, path, body)
        assert status in (400, 404)
        _assert_no_raw_error_text(json.dumps(payload))


# ---------------------------------------------------------------------------
# Over a real socket
# ---------------------------------------------------------------------------


def test_live_health_endpoint() -> None:
    with _running_server() as base:
        status, blob = _get(base, "/health")
    assert status == 200
    payload = json.loads(blob)
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["status"] == "ok"


def test_live_forecast_endpoint() -> None:
    request = {
        "pity_5star": 76,
        "fate_points": 1,
        "banner": "weapon_event",
        "target_count": 1,
        "pull_budget": 1,
    }
    with _running_server() as base:
        status, blob = _post(base, "/forecast", json.dumps(request).encode("utf-8"))
    assert status == 200
    payload = json.loads(blob)
    assert payload["probability"] == 1.0
    assert payload["banner"] == "weapon_event"


def test_live_malformed_forecast_returns_400_without_raw_exception() -> None:
    with _running_server() as base:
        status, blob = _post(base, "/forecast", b"{this is not json at all")
    assert status == 400
    _assert_no_raw_error_text(blob)
    payload = json.loads(blob)
    assert payload["status"] == "error"
    assert payload["engine_version"] == ENGINE_VERSION


def test_live_unknown_route_returns_404() -> None:
    with _running_server() as base:
        status, blob = _get(base, "/does-not-exist")
    assert status == 404
    _assert_no_raw_error_text(blob)


def test_cli_rejects_an_unknown_argument() -> None:
    """argparse exits rather than binding a port on a typo."""
    with pytest.raises(SystemExit):
        main(["--nope"])
