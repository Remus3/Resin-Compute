"""PityEngine local HTTP service.

Stdlib only. Serves the engine on 127.0.0.1:8790 by default, mirroring how Riot
Commander exposes Daemon Slayer on 8860 - a pure compute core with a thin,
boring transport bolted on that the compute core knows nothing about.

Routes:

    GET  /health     engine version, pid, uptime
    POST /forecast   {pity_5star, has_guarantee, consecutive_5050_losses,
                      fate_points, banner, target_count, pull_budget}

FAIL-SOFT is a hard rule, inherited verbatim (SPEC section 2): a malformed
request returns HTTP 400 with a friendly JSON message and the raw exception goes
to the log, never into the response body. A caller must never be shown a
traceback, an exception class name or a parser's internal complaint. The
request-boundary `except Exception` that makes this true is the reason
`ruff.toml` scopes a BLE001 carve-out to this one file - a bad query must
degrade to a 400, never take the daemon down.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from core.ports import ENGINE as ENGINE_PORT
from core.types import BannerKind, PityState

from . import ENGINE_VERSION
from .forecast import probability_of_success

DEFAULT_HOST = "127.0.0.1"

#: Owned by `core/ports.py`, never restated. See ADR-004 for why the engine
#: moved off its original port.
DEFAULT_PORT = ENGINE_PORT

LOGGER = logging.getLogger("pity_engine")

_START_TIME = time.monotonic()

_BANNER_BY_VALUE = {kind.value: kind for kind in BannerKind}

# Deliberately generic. These strings are the ONLY thing a caller ever sees on a
# failure; the detail lives in the log.
_BAD_REQUEST_MESSAGE = "forecast request could not be processed - check the request fields and try again"
_NOT_FOUND_MESSAGE = "no such route on this engine"


def health_payload() -> dict[str, Any]:
    """Liveness plus the single source of truth for the engine revision."""
    return {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "pid": os.getpid(),
        "uptime_seconds": round(time.monotonic() - _START_TIME, 3),
    }


def _error_payload(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message, "engine_version": ENGINE_VERSION}


def _coerce_int(body: dict[str, Any], key: str, default: int = 0) -> int:
    raw = body.get(key, default)
    if isinstance(raw, bool):
        raise ValueError(f"{key} must be an integer, not a boolean")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip():
        return int(raw.strip())
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    raise ValueError(f"{key} must be an integer")


def _coerce_banner(body: dict[str, Any]) -> BannerKind:
    raw = body.get("banner", BannerKind.CHARACTER_EVENT.value)
    if isinstance(raw, BannerKind):
        return raw
    if isinstance(raw, str) and raw in _BANNER_BY_VALUE:
        return _BANNER_BY_VALUE[raw]
    raise ValueError(f"banner must be one of {sorted(_BANNER_BY_VALUE)}")


def forecast_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Translate one request body into one response body.

    Pure: it reads the mapping, calls the engine and returns plain JSON-ready
    types. It raises `ValueError` on nonsense and never formats an error itself,
    so the friendly-message rule is enforced in exactly one place.
    """
    banner = _coerce_banner(body)
    state = PityState(
        banner=banner,
        pity_5star=_coerce_int(body, "pity_5star"),
        pity_4star=_coerce_int(body, "pity_4star"),
        has_guarantee=bool(body.get("has_guarantee", False)),
        consecutive_5050_losses=_coerce_int(body, "consecutive_5050_losses"),
        fate_points=_coerce_int(body, "fate_points"),
    )
    result = probability_of_success(
        state,
        target_count=_coerce_int(body, "target_count", 1),
        pull_budget=_coerce_int(body, "pull_budget", 0),
        banner=banner,
    )
    return {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "probability": result.probability,
        "pull_budget": result.pull_budget,
        "target_count": result.target_count,
        "banner": result.banner.value,
        "distribution": list(result.distribution),
        "expected_pulls": result.expected_pulls,
    }


def handle_request(method: str, path: str, raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Route one request and guarantee a JSON answer for every input.

    Never raises. Anything that goes wrong becomes a 400 with a friendly message
    while the real exception is logged at exception level.
    """
    try:
        if method == "GET" and path == "/health":
            return 200, health_payload()
        if method == "POST" and path == "/forecast":
            text = raw_body.decode("utf-8").strip() or "{}"
            body = json.loads(text)
            if not isinstance(body, dict):
                raise ValueError("request body must be a JSON object")
            return 200, forecast_payload(body)
        return 404, _error_payload(_NOT_FOUND_MESSAGE)
    except Exception:
        LOGGER.exception("pity_engine request failed: %s %s", method, path)
        return 400, _error_payload(_BAD_REQUEST_MESSAGE)


class PityEngineHandler(BaseHTTPRequestHandler):
    """Thin transport. All behaviour lives in `handle_request`."""

    server_version = f"PityEngine/{ENGINE_VERSION}"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler dispatch name
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler dispatch name
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        raw_body = self.rfile.read(length) if length > 0 else b""
        status, payload = handle_request(method, urlsplit(self.path).path, raw_body)
        blob = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, format: str, *args: Any) -> None:
        # Route access logs through the module logger instead of stderr, so a
        # test harness or a supervisor sees one stream rather than two.
        LOGGER.debug("%s %s", self.address_string(), format % args)


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Bind a server without serving it - the seam the service tests use."""
    return ThreadingHTTPServer((host, port), PityEngineHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pity_engine",
        description=f"PityEngine {ENGINE_VERSION} - local deterministic gacha forecaster",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"bind address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"bind port (default {DEFAULT_PORT})")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    server = build_server(args.host, args.port)
    LOGGER.info("PityEngine %s listening on http://%s:%d", ENGINE_VERSION, args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("PityEngine shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
