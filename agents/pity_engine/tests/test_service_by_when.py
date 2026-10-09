"""HTTP tests for `POST /by-when`.

Same rules as `test_service.py`, which is deliberately left untouched: FAIL-SOFT
(a malformed request is a friendly 400, the raw exception goes to the log), an
ephemeral port rather than the reserved one, and a marker list of strings that
must never reach a caller. The list is EXTENDED here, because this route parses
dates and `date.fromisoformat` complains in words the original list does not
know ("Invalid isoformat string: ...").

Every date below is invented - year 2100, labels like "window-a". The engine
ships no calendar; the schedule is the caller's.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from http.server import ThreadingHTTPServer

import pytest

import agents.pity_engine as engine
from agents.pity_engine import ENGINE_VERSION
from agents.pity_engine.__main__ import build_server, by_when_payload, forecast_payload, handle_request
from agents.pity_engine.timeline import BannerWindow, by_when
from core.types import PityState

# `test_service.py`'s list, plus the words a date parser uses when it fails.
_RAW_ERROR_MARKERS = (
    "Traceback",
    "ValueError",
    "TypeError",
    "KeyError",
    "OverflowError",
    "JSONDecodeError",
    "Expecting value",
    "line 1 column",
    "most recent call last",
    "File \"",
    "isoformat",
    "fromisoformat",
    "Invalid",
)

#: The frozen response shape, in order. A key added, dropped or moved is a
#: contract change and must fail here first.
_RESPONSE_KEYS = [
    "status",
    "engine_version",
    "banner",
    "target_count",
    "as_of",
    "confidence",
    "pulls_on_hand",
    "pulls_per_day",
    "pulls_needed",
    "reachable",
    "by_date",
    "by_date_label",
    "by_date_pulls_available",
    "by_date_probability",
    "best_date",
    "best_label",
    "best_pulls_available",
    "best_probability",
    "pulls_short",
    "windows",
]
_WINDOW_KEYS = ["start", "end", "label", "pulls_available_at_end", "probability_at_end"]

#: `/forecast`'s shape, pinned here so the new route cannot quietly move it.
_FORECAST_KEYS = [
    "status",
    "engine_version",
    "probability",
    "pull_budget",
    "target_count",
    "banner",
    "distribution",
    "expected_pulls",
]

AS_OF = "2100-01-01"
WINDOW_A = {"start": "2100-01-01", "end": "2100-01-10", "label": "window-a"}
WINDOW_B = {"start": "2100-03-01", "end": "2100-03-31", "label": "window-b"}


def _full_request() -> dict[str, object]:
    return {
        "pity_5star": 0,
        "has_guarantee": False,
        "consecutive_5050_losses": 0,
        "fate_points": 0,
        "banner": "character_event",
        "target_count": 1,
        "as_of": AS_OF,
        "schedule": [WINDOW_A, WINDOW_B],
        "pulls_on_hand": 10,
        "pulls_per_day": 1.0,
        "confidence": 0.5,
    }


def _encode(body: dict[str, object]) -> bytes:
    return json.dumps(body).encode("utf-8")


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
# Payload builder, exercised without a socket
# ---------------------------------------------------------------------------


def test_by_when_payload_round_trips_a_full_request() -> None:
    payload = by_when_payload(_full_request())
    assert list(payload) == _RESPONSE_KEYS
    assert payload["status"] == "ok"
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["banner"] == "character_event"
    assert payload["target_count"] == 1
    assert payload["as_of"] == AS_OF
    assert payload["confidence"] == 0.5
    assert payload["pulls_on_hand"] == 10
    assert payload["pulls_per_day"] == 1.0
    assert isinstance(payload["pulls_per_day"], float)
    assert payload["reachable"] is True
    assert [list(window) for window in payload["windows"]] == [_WINDOW_KEYS, _WINDOW_KEYS]
    assert [window["label"] for window in payload["windows"]] == ["window-a", "window-b"]
    # The whole payload must survive a JSON round trip unchanged.
    assert json.loads(json.dumps(payload)) == payload


def test_by_when_payload_agrees_with_the_library_call() -> None:
    """The route is a translation layer; the library is the answer."""
    payload = by_when_payload(_full_request())
    result = by_when(
        PityState(),
        1,
        [
            BannerWindow(date(2100, 1, 1), date(2100, 1, 10), "window-a"),
            BannerWindow(date(2100, 3, 1), date(2100, 3, 31), "window-b"),
        ],
        as_of=date(2100, 1, 1),
        pulls_on_hand=10,
        pulls_per_day=1.0,
        confidence=0.5,
    )
    assert result.by_date is not None
    assert payload["by_date"] == result.by_date.isoformat()
    assert payload["by_date_label"] == result.by_date_label
    assert payload["by_date_pulls_available"] == result.by_date_pulls_available
    assert payload["by_date_probability"] == result.by_date_probability
    assert payload["best_date"] == result.best_date.isoformat()
    assert payload["pulls_needed"] == result.pulls_needed
    assert payload["pulls_short"] == 0
    # Ten in hand plus one a day: the half-way answer lands inside window-b.
    assert payload["by_date"] == "2100-03-12"
    assert payload["by_date_pulls_available"] == 80


def test_by_when_payload_defaults_are_sane() -> None:
    payload = by_when_payload({"as_of": AS_OF, "schedule": [WINDOW_A]})
    assert payload["banner"] == "character_event"
    assert payload["target_count"] == 1
    assert payload["pulls_on_hand"] == 0
    assert payload["pulls_per_day"] == 0.0
    assert isinstance(payload["pulls_per_day"], float)
    assert payload["confidence"] == 0.9
    # Nothing in hand and no income: the answer is an honest "not reachable".
    assert payload["reachable"] is False
    assert payload["by_date"] is None
    assert payload["pulls_short"] == payload["pulls_needed"]
    assert payload["best_pulls_available"] == 0


def test_windows_come_back_sorted_by_start_whatever_the_input_order() -> None:
    body = _full_request()
    body["schedule"] = [WINDOW_B, WINDOW_A]
    payload = by_when_payload(body)
    assert [window["label"] for window in payload["windows"]] == ["window-a", "window-b"]
    assert [window["start"] for window in payload["windows"]] == ["2100-01-01", "2100-03-01"]


def test_a_missing_label_is_echoed_as_the_empty_string() -> None:
    body = _full_request()
    body["schedule"] = [{"start": "2100-01-01", "end": "2100-01-10"}]
    body["pulls_on_hand"] = 500
    payload = by_when_payload(body)
    assert payload["windows"][0]["label"] == ""
    assert payload["by_date_label"] == ""
    assert payload["best_label"] == ""


def test_library_only_arguments_are_not_exposed_over_http() -> None:
    """R14: `weapon_increment` and `carry_radiance_through_guarantee` stay library-only."""
    plain = by_when_payload(_full_request())
    decorated = _full_request()
    decorated["weapon_increment"] = 0.5
    decorated["carry_radiance_through_guarantee"] = False
    assert by_when_payload(decorated) == plain


@pytest.mark.parametrize("raw, expected", [(2, 2.0), (1.5, 1.5), ("1.5", 1.5), (" 0.25 ", 0.25)])
def test_pulls_per_day_accepts_int_float_and_numeric_string(raw: object, expected: float) -> None:
    body = _full_request()
    body["pulls_per_day"] = raw
    payload = by_when_payload(body)
    assert payload["pulls_per_day"] == expected
    assert isinstance(payload["pulls_per_day"], float)


def test_confidence_accepts_a_numeric_string() -> None:
    body = _full_request()
    body["confidence"] = "0.5"
    assert by_when_payload(body)["confidence"] == 0.5


def test_as_of_is_required() -> None:
    body = _full_request()
    del body["as_of"]
    with pytest.raises(ValueError):
        by_when_payload(body)
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 400
    assert "check the request fields" in payload["error"]


@pytest.mark.parametrize(
    "raw",
    [
        "21000105",
        "2100-W01-1",
        "2100-1-5",
        "2100-01-05T00:00:00",
        "2100/01/05",
        " 2100-01-05",
        "2100-01-05 ",
        "",
        21000105,
        None,
        True,
        ["2100-01-05"],
    ],
)
def test_as_of_accepts_only_a_strict_calendar_date(raw: object) -> None:
    """`date.fromisoformat` also takes `YYYYMMDD` and week dates; the route must not.

    The round trip `parsed.isoformat() == raw` is what closes that gap, and
    this arm is the one a mutant that drops the round trip turns red.
    """
    body = _full_request()
    body["as_of"] = raw
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 400, f"as_of {raw!r} was accepted"
    assert payload["status"] == "error"
    _assert_no_raw_error_text(json.dumps(payload))


def test_a_window_ending_on_as_of_is_a_200_and_one_ending_the_day_before_is_a_400() -> None:
    """R7 over HTTP: only `end < as_of` is rejected; `end == as_of` still has today."""
    body = {
        "as_of": AS_OF,
        "schedule": [{"start": "2099-12-25", "end": AS_OF, "label": "window-a"}],
        "pulls_on_hand": 200,
        "confidence": 1.0,
    }
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 200
    assert payload["reachable"] is True
    assert payload["by_date"] == AS_OF
    assert payload["by_date_label"] == "window-a"
    assert payload["windows"][0]["end"] == AS_OF
    body["schedule"] = [{"start": "2099-12-25", "end": "2099-12-31", "label": "window-a"}]
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 400
    assert payload["status"] == "error"
    _assert_no_raw_error_text(json.dumps(payload))


def test_the_earliest_day_wins_a_flat_tie_over_http() -> None:
    """Zero velocity across two windows: best_date is the first eligible day."""
    body = {
        "as_of": AS_OF,
        "schedule": [
            {"start": "2100-01-15", "end": "2100-01-20", "label": "window-b"},
            {"start": "2100-01-05", "end": "2100-01-08", "label": "window-a"},
        ],
        "pulls_on_hand": 10,
    }
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 200
    assert payload["reachable"] is False
    assert payload["best_date"] == "2100-01-05"
    assert payload["best_label"] == "window-a"
    assert payload["windows"][0]["probability_at_end"] == payload["windows"][1]["probability_at_end"]


def test_the_strict_date_control_is_accepted() -> None:
    """Non-vacuity for the arm above: the one spelling that IS legal goes through."""
    body = _full_request()
    body["as_of"] = "2100-01-05"
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 200
    assert payload["as_of"] == "2100-01-05"


@pytest.mark.parametrize("key", ["start", "end"])
def test_window_dates_are_held_to_the_same_strict_parse(key: str) -> None:
    body = _full_request()
    loose = dict(WINDOW_B)
    loose[key] = loose[key].replace("-", "")
    body["schedule"] = [WINDOW_A, loose]
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 400
    _assert_no_raw_error_text(json.dumps(payload))


# ---------------------------------------------------------------------------
# Routing and fail-soft, exercised without a socket
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        b"{not json",
        b"[]",
        b'"a string"',
        b"{}",
        b'{"as_of": "2100-01-01"}',
        b'{"as_of": "2100-01-01", "schedule": []}',
        b'{"as_of": "2100-01-01", "schedule": "window-a"}',
        b'{"as_of": "2100-01-01", "schedule": ["window-a"]}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01"}]}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-10", "end": "2100-01-09"}]}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10", "label": 7}]}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}, '
        b'{"start": "2100-01-10", "end": "2100-01-20"}]}',
        b'{"as_of": "2100-02-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}]}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_on_hand": -1}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_on_hand": true}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_on_hand": "ten"}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_on_hand": 1.5}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": -1}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": true}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": "fast"}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": "nan"}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": "1e400"}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pulls_per_day": 1e308}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "confidence": 1.5}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "confidence": true}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "target_count": 0}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "banner": "not_a_banner"}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "pity_5star": 95}',
        b'{"as_of": "2100-01-01", "schedule": [{"start": "2100-01-01", "end": "2100-01-10"}], "fate_points": 7}',
    ],
)
def test_malformed_by_when_fails_soft(body: bytes) -> None:
    """Every one of these is a 400 with a friendly message and nothing else."""
    status, payload = handle_request("POST", "/by-when", body)
    assert status == 400
    assert payload["status"] == "error"
    assert payload["engine_version"] == ENGINE_VERSION
    blob = json.dumps(payload)
    _assert_no_raw_error_text(blob)
    assert "check the request fields" in payload["error"]


def test_an_unreachable_schedule_is_a_200_with_reachable_false() -> None:
    """Unreachable is a RESULT, never an error - a short window is a real answer."""
    body = {"as_of": AS_OF, "schedule": [WINDOW_A], "pulls_per_day": 1.0, "confidence": 0.9}
    status, payload = handle_request("POST", "/by-when", _encode(body))
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["reachable"] is False
    assert payload["by_date"] is None
    assert payload["by_date_label"] is None
    assert payload["by_date_pulls_available"] is None
    assert payload["by_date_probability"] is None
    assert payload["best_date"] == "2100-01-10"
    assert payload["best_label"] == "window-a"
    assert payload["best_pulls_available"] == 9
    assert 0.0 < payload["best_probability"] < 1.0
    assert payload["pulls_short"] == payload["pulls_needed"] - 9
    assert payload["pulls_short"] > 0


def test_the_route_is_a_post_only_sibling_of_forecast() -> None:
    """R4: GET on it is the ordinary 404, and it is not nested under /forecast."""
    for method, path in (("GET", "/by-when"), ("POST", "/forecast/by-when"), ("POST", "/by_when")):
        status, payload = handle_request(method, path, _encode(_full_request()))
        assert status == 404, f"{method} {path} answered {status}"
        assert payload["status"] == "error"
        _assert_no_raw_error_text(json.dumps(payload))


def test_handle_request_never_raises_on_by_when() -> None:
    for body in (b"\xff\xfe not utf-8", b"", b"null", b"0"):
        status, payload = handle_request("POST", "/by-when", body)
        assert status == 400
        _assert_no_raw_error_text(json.dumps(payload))


def test_the_forecast_route_keeps_its_shape() -> None:
    """Adding a route must not move a byte of the existing one."""
    assert list(forecast_payload({})) == _FORECAST_KEYS
    status, payload = handle_request("POST", "/forecast", b"{}")
    assert status == 200
    assert list(payload) == _FORECAST_KEYS
    assert payload["probability"] == 0.0


def test_the_package_exports_the_timeline_api_without_moving_the_revision() -> None:
    assert ENGINE_VERSION == "0.1.0"
    for name in ("BannerWindow", "ByWhenResult", "WindowOutcome", "by_when"):
        assert name in engine.__all__
        assert getattr(engine, name) is not None


# ---------------------------------------------------------------------------
# Over a real socket
# ---------------------------------------------------------------------------


def test_live_by_when_endpoint() -> None:
    with _running_server() as base:
        status, blob = _post(base, "/by-when", _encode(_full_request()))
    assert status == 200
    _assert_no_raw_error_text(blob)
    payload = json.loads(blob)
    assert list(payload) == _RESPONSE_KEYS
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["reachable"] is True
    assert payload["by_date"] == "2100-03-12"
    assert [window["label"] for window in payload["windows"]] == ["window-a", "window-b"]


def test_live_malformed_by_when_returns_400_without_raw_exception() -> None:
    body = _full_request()
    body["as_of"] = "21000101"
    with _running_server() as base:
        status, blob = _post(base, "/by-when", _encode(body))
    assert status == 400
    _assert_no_raw_error_text(blob)
    payload = json.loads(blob)
    assert payload["status"] == "error"
    assert payload["engine_version"] == ENGINE_VERSION


def test_live_get_on_by_when_is_404() -> None:
    with _running_server() as base:
        status, blob = _get(base, "/by-when")
    assert status == 404
    _assert_no_raw_error_text(blob)
