"""PityEngine local HTTP service.

Stdlib only. Serves the engine on 127.0.0.1:8790 by default, mirroring how
Sibling-C exposes Sibling-F on 8860 - a pure compute core with a thin,
boring transport bolted on that the compute core knows nothing about.

Routes:

    GET  /health     engine version, pid, uptime
    POST /forecast   {pity_5star, has_guarantee, consecutive_5050_losses,
                      fate_points, banner, target_count, pull_budget}
    POST /by-when    {as_of, schedule: [{start, end, label}], pulls_on_hand, pulls_per_day, confidence, + the /forecast fields minus pull_budget}

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
import socket
import sys
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from core.ports import ENGINE as ENGINE_PORT
from core.types import BannerKind, PityState

from . import ENGINE_VERSION
from .forecast import probability_of_success
from .timeline import BannerWindow, by_when

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


def _coerce_float(body: dict[str, Any], key: str, default: float = 0.0) -> float:
    raw = body.get(key, default)
    if isinstance(raw, bool):
        raise ValueError(f"{key} must be a number, not a boolean")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str) and raw.strip():
        return float(raw.strip())
    raise ValueError(f"{key} must be a number")


def _coerce_date(mapping: dict[str, Any], key: str) -> date:
    """Strict `YYYY-MM-DD`, required.

    `date.fromisoformat` also accepts `YYYYMMDD` and ISO week dates such as
    `YYYY-Www-D` (measured on 3.11), so parsing alone is not the check: the
    parsed value must render back to exactly the string that arrived.
    """
    raw = mapping.get(key)
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a YYYY-MM-DD string")
    parsed = date.fromisoformat(raw)
    if parsed.isoformat() != raw:
        raise ValueError(f"{key} must be a YYYY-MM-DD string")
    return parsed


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


def by_when_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Translate one `/by-when` request body into one response body.

    Same contract as `forecast_payload`: pure, raises `ValueError` on nonsense
    and never formats an error itself. The schedule is the caller's - the
    engine vendors no calendar - and `as_of` is required because the engine
    reads no clock. `weapon_increment` and `carry_radiance_through_guarantee`
    are library-only and deliberately not read from the body, matching
    `/forecast`. The four `by_date_*` keys are null exactly when `reachable` is
    false; the `best_*` keys are never null.
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
    target_count = _coerce_int(body, "target_count", 1)
    as_of = _coerce_date(body, "as_of")
    raw_schedule = body.get("schedule")
    if not isinstance(raw_schedule, list):
        raise ValueError("schedule must be a list of windows")
    schedule: list[BannerWindow] = []
    for entry in raw_schedule:
        if not isinstance(entry, dict):
            raise ValueError("each schedule window must be an object with start and end")
        label = entry.get("label", "")
        if not isinstance(label, str):
            raise ValueError("a window label must be a string")
        schedule.append(
            BannerWindow(start=_coerce_date(entry, "start"), end=_coerce_date(entry, "end"), label=label)
        )
    pulls_on_hand = _coerce_int(body, "pulls_on_hand", 0)
    pulls_per_day = _coerce_float(body, "pulls_per_day", 0.0)
    confidence = _coerce_float(body, "confidence", 0.9)
    result = by_when(
        state,
        target_count=target_count,
        schedule=schedule,
        as_of=as_of,
        pulls_on_hand=pulls_on_hand,
        pulls_per_day=pulls_per_day,
        confidence=confidence,
        banner=banner,
    )
    return {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "banner": banner.value,
        "target_count": target_count,
        "as_of": as_of.isoformat(),
        "confidence": confidence,
        "pulls_on_hand": pulls_on_hand,
        "pulls_per_day": pulls_per_day,
        "pulls_needed": result.pulls_needed,
        "reachable": result.reachable,
        "by_date": result.by_date.isoformat() if result.by_date is not None else None,
        "by_date_label": result.by_date_label,
        "by_date_pulls_available": result.by_date_pulls_available,
        "by_date_probability": result.by_date_probability,
        "best_date": result.best_date.isoformat(),
        "best_label": result.best_label,
        "best_pulls_available": result.best_pulls_available,
        "best_probability": result.best_probability,
        "pulls_short": result.pulls_short,
        "windows": [
            {
                "start": window.start.isoformat(),
                "end": window.end.isoformat(),
                "label": window.label,
                "pulls_available_at_end": window.pulls_available_at_end,
                "probability_at_end": window.probability_at_end,
            }
            for window in result.windows
        ],
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
        if method == "POST" and path == "/by-when":
            text = raw_body.decode("utf-8").strip() or "{}"
            body = json.loads(text)
            if not isinstance(body, dict):
                raise ValueError("request body must be a JSON object")
            return 200, by_when_payload(body)
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


class _ExclusiveHTTPServer(ThreadingHTTPServer):
    """A server that REFUSES a port something else already holds.

    MEASURED DEFECT, and this class is the fix. `socketserver.TCPServer` sets
    `allow_reuse_address = True`, which sets SO_REUSEADDR. On POSIX that only
    sidesteps TIME_WAIT and is exactly what you want. **On Windows it lets a
    completely separate process bind a port another process is already listening
    on**, leaving both sockets in LISTENING with no defined rule about which one
    receives a connection.

    THE SIBLING OF A DEFECT THIS TREE ALREADY PAID FOR ONCE. `surface/server.py`
    carries the same class for the dashboard on 8791, written after two surfaces
    bound that port simultaneously on 2026-09-06 and the OLDER one answered every
    request while a freshly started surface serving new code was silently
    ignored. That fix landed at ONE call site. The engine on 8790 kept the stock
    server and kept the defect.

    Reproduced against this engine on 2026-09-06: two engine processes both bound
    127.0.0.1:8790, both logged the byte-identical banner "PityEngine 0.1.0
    listening on http://127.0.0.1:8790", and six consecutive /health calls all
    returned the FIRST process's pid. That is the worst shape a bug can take -
    the second engine reports healthy, serves nothing, and a stranger following
    README section 6 is fed stale forecasts by code they already replaced.

    So SO_REUSEADDR is dropped, and on Windows SO_EXCLUSIVEADDRUSE is set in its
    place - the flag that actually means what SO_REUSEADDR means on POSIX.

    WHICH HALF IS LOAD-BEARING, measured rather than assumed. The full bind
    matrix was probed on this box on 2026-09-06 against a LISTENING first socket,
    and exactly one of its nine cells double-binds: SO_REUSEADDR on BOTH sockets,
    which is precisely what two stock `ThreadingHTTPServer` engines are. Every
    other pairing is already refused. `allow_reuse_address = False` is therefore
    the half that closes the defect, and the `first=none` and `first=exclusive`
    columns are IDENTICAL - so no test here pins the setsockopt, and none can on
    this platform. It is kept because it mirrors `surface/server.py`, the sibling
    fix this one is derived from, and because it is Microsoft's documented
    guidance for a server socket. The matrix is reproduced in the test file.

    The listening socket is closed on shutdown, so TIME_WAIT does not apply to it
    and an immediate restart still works; `agents/pity_engine/tests/test_service.py`
    pins that, because turning off address reuse is exactly the change that could
    break it, and the engine runs in the FOREGROUND so ctrl-C then restart is its
    ordinary edit loop.
    """

    allow_reuse_address = False

    def server_bind(self) -> None:
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Bind a server without serving it - the seam the service tests use.

    Returns a `ThreadingHTTPServer`, which `_ExclusiveHTTPServer` is, so every
    existing caller and annotation keeps working. It now RAISES `OSError` rather
    than quietly binding a port another process holds - see the class above.
    """
    return _ExclusiveHTTPServer((host, port), PityEngineHandler)


def main(argv: list[str] | None = None) -> int:
    """Run the engine until interrupted.

    Exit codes:

        0  clean shutdown
        2  the port it needs is already held by something else

    THE ENGINE DOCUMENTED NO EXIT CODE FOR A TAKEN PORT BEFORE THIS. It bound
    unconditionally and returned 0, which on Windows meant a second engine
    started successfully, logged the same banner as the first and then served
    nobody. 2 is not a new contract invented here - it is the number
    `surface/server.py`'s `main` already documents for exactly this condition,
    and the one `shell/lib/supervisor.js` renders refusal text from. Nothing
    spawns the engine, so naming it broke no existing caller; it makes the
    repository say one thing about a held port instead of two.

    The raw `OSError` goes to the log and never to the caller, per the fail-soft
    rule in SPEC section 2 - a bind message can name a host and a port, and the
    fixed exit code is what a supervisor can actually act on.
    """
    parser = argparse.ArgumentParser(
        prog="pity_engine",
        description=f"PityEngine {ENGINE_VERSION} - local deterministic gacha forecaster",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"bind address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"bind port (default {DEFAULT_PORT})")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        # build_server is what BINDS, so it is what can fail. Wrapping the whole
        # serve_forever call instead would swallow a later, unrelated failure as
        # though it had been a bind refusal.
        server = build_server(args.host, args.port)
    except OSError as exc:
        LOGGER.error("PityEngine could not bind %s:%s: %s", args.host, args.port, exc)
        return 2
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
