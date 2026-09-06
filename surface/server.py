"""The local dashboard surface - stdlib HTTP on loopback.

THIN BY DESIGN. Everything this file could get wrong lives somewhere testable:
what the board contains is `surface/model.py`, what the page looks like is
`surface/render.py`, and which port it binds is `core/ports.py`. What is left is
socket plumbing, which is the part that needs a real bind to grade and is
therefore the part kept smallest.

LOOPBACK ONLY, AND THAT IS NOT A DEFAULT TO OVERRIDE CASUALLY. The page renders
account state and carries no authentication of any kind. ADR-005 records the
decision to serve plain HTTP rather than Clockspeed's pinned-certificate HTTPS,
and that decision rests entirely on never leaving 127.0.0.1.

EVERY HANDLER IS TOTAL. A state provider that raises, a model that raises, a
renderer that raises - all of them degrade to a rendered page that says the
surface could not read the account, and the raw exception goes to the log. Per
the hard rule, no raw error string reaches the response body. That includes the
404 page: the stdlib default `send_error` writes the request path into the body,
and a path is caller-controlled text, so this module renders its own.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from core.log_setup import get_logger
from core.ports import DASHBOARD
from core.types import AccountState
from surface.model import Dashboard, Panel, PanelState, build_dashboard
from surface.render import render_html, render_json

_log = get_logger(__name__)

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "DashboardServer", "main"]

DEFAULT_HOST = "127.0.0.1"

#: Owned by `core/ports.py`, never restated. See ADR-004.
DEFAULT_PORT = DASHBOARD

_START_TIME = time.monotonic()

#: Tight because the page loads nothing remote and runs no inline script beyond
#: the reload timer. `unsafe-inline` covers the inline <style> and that timer; it
#: is the one relaxation, and it is scoped rather than global.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)

_NOT_FOUND_MESSAGE = "No such page on this surface."
_DEGRADED_MESSAGE = (
    "The surface could not read the account state. It is still running; "
    "the details are in the log."
)

StateProvider = Callable[[], AccountState]


def default_state_provider() -> AccountState:
    """The account the surface renders when no provider is injected.

    Deliberately EMPTY rather than a fabricated demo account. Every panel then
    reports honestly that it has nothing behind it, which is the correct first
    impression for a tree whose cost tables are still gated.
    """
    return AccountState(uid="")


def _degraded_board(now: datetime) -> Dashboard:
    """A board that says the surface is alive but the state is unreadable."""
    return Dashboard(
        generated_at=now,
        panels=(
            Panel(
                panel_id="surface",
                title="Surface",
                state=PanelState.PARTIAL,
                waiting_on=_DEGRADED_MESSAGE,
            ),
        ),
    )


def build_board(provider: StateProvider) -> Dashboard:
    """Build the board from a provider, degrading rather than raising.

    The blind except is deliberate and matches the boundary calls in
    `headless/runner.py` and `ops/supervisor.py`: the provider is arbitrary
    caller code and the set of things it might raise is not enumerable.
    """
    now = datetime.now(UTC)
    try:
        return build_dashboard(provider(), now=now)
    except Exception as exc:  # noqa: BLE001 - the surface must stay up
        _log.error("dashboard state provider failed: %s: %s", exc.__class__.__name__, exc)
        return _degraded_board(now)


class _Handler(BaseHTTPRequestHandler):
    server_version = "ResinComputeSurface/0.1"
    sys_version = ""

    #: Set by DashboardServer before the server starts serving.
    state_provider: StateProvider = staticmethod(default_state_provider)

    def log_message(self, fmt: str, *args: object) -> None:
        """Route access logs to the project logger instead of stderr.

        The stdlib default writes the raw request line to stderr, which both
        bypasses the log file and prints caller-controlled text to a console.
        """
        _log.debug("surface %s", fmt % args)

    def _respond(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        route = urlsplit(self.path).path.rstrip("/") or "/"

        if route == "/":
            self._respond(200, render_html(build_board(self.state_provider)), "text/html")
            return
        if route == "/api/dashboard":
            self._respond(200, render_json(build_board(self.state_provider)), "application/json")
            return
        if route == "/health":
            payload = {
                "status": "ok",
                "pid": os.getpid(),
                "uptime_seconds": round(time.monotonic() - _START_TIME, 3),
            }
            self._respond(200, json.dumps(payload, sort_keys=True), "application/json")
            return

        # The stdlib `send_error` writes the requested path into the body. The
        # path is caller-controlled, so this renders fixed text instead.
        self._respond(404, json.dumps({"error": _NOT_FOUND_MESSAGE}), "application/json")


class DashboardServer:
    """Own the socket and the thread, so a caller and a test share one lifecycle.

    `port=0` binds an EPHEMERAL port and `self.port` then reports what the OS
    actually gave out. The suite uses that so running tests never contends with a
    dashboard the operator has open on the reserved port.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        state_provider: StateProvider | None = None,
    ) -> None:
        self.host = host
        self._requested_port = port
        self._provider: StateProvider = state_provider or default_state_provider
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        if self._httpd is None:
            return self._requested_port
        return int(self._httpd.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        if self._httpd is not None:
            return
        handler = type("_BoundHandler", (_Handler,), {"state_provider": staticmethod(self._provider)})
        self._httpd = ThreadingHTTPServer((self.host, self._requested_port), handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="resin-surface", daemon=True)
        self._thread.start()
        _log.info("dashboard surface listening on %s", self.base_url)

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._httpd = None
        self._thread = None

    def serve_forever(self) -> None:
        """Start and block. The entry point `main` uses."""
        self.start()
        thread = self._thread
        if thread is not None:
            try:
                while thread.is_alive():
                    thread.join(timeout=0.5)
            except KeyboardInterrupt:
                _log.info("dashboard surface interrupted, shutting down")
            finally:
                self.stop()


def main(argv: list[str] | None = None) -> int:
    """Run the surface until interrupted.

    Exit codes are a contract the Electron shell reads, because it discards the
    child's OUTPUT - a message can name a path and a path carries the Windows
    account name - and keeps only the code:

        0  clean shutdown
        2  the port is already held by something else
    """
    import argparse

    parser = argparse.ArgumentParser(prog="python -m surface", description="ResinCompute dashboard surface")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    server = DashboardServer(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except OSError as exc:
        _log.error("dashboard surface could not bind %s:%s: %s", args.host, args.port, exc)
        return 2
    return 0
