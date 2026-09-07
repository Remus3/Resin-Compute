"""HTTP service tests.

The load-bearing rule here is FAIL-SOFT (SPEC section 2, inherited verbatim
from Sibling-C): a malformed request returns a friendly 400 and the raw
exception goes to the log, never into the response body. `_RAW_ERROR_MARKERS`
below is the concrete form of that rule - if any of those strings ever reaches
a caller, the engine has leaked its internals.
"""
from __future__ import annotations

import errno
import json
import socket
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
    a port inside Sibling-F's reserved block; a literal here is exactly what
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


# ---------------------------------------------------------------------------
# Exclusive bind
# ---------------------------------------------------------------------------
#
# THE SIBLING OF A DEFECT THIS TREE ALREADY PAID FOR. `surface/server.py` fixed
# it for the dashboard on 8791 and `tests/test_surface_render.py` pins it there.
# The engine on 8790 - the process README section 6 tells a stranger to start by
# hand - was left on the stock `ThreadingHTTPServer` and kept the defect.
#
# WHY THE ASSERTIONS BELOW ARE NOT THE SURFACE'S. Its version asserts a bare
# `pytest.raises(OSError)`, which any OSError at all satisfies - including one
# raised for a reason with nothing to do with the address. These pin the errno
# to an address refusal and then check the property that actually broke: the
# INCUMBENT stays the sole owner and keeps answering. The measured symptom was
# never a crash. It was two engines binding, both logging the byte-identical
# "listening on" banner, and six consecutive /health calls all coming back with
# the FIRST process's pid.


#: Errnos that mean "the operating system refused this address".
#:
#: MEASURED on this machine, 2026-09-06, Python on win32: two sockets that both
#: set SO_EXCLUSIVEADDRUSE give the challenger `errno.EADDRINUSE` (10048, which
#: is WSAEADDRINUSE under the same name). EACCES is carried too because Windows
#: answers WSAEACCES instead when the challenger sets SO_REUSEADDR against an
#: exclusive holder - a different refusal, still a refusal, and listing it keeps
#: a platform difference from reading as a spurious red. Neither can occur in
#: the defective build, which binds successfully and raises nothing at all.
_ADDRESS_REFUSED = frozenset({errno.EADDRINUSE, errno.EACCES})


@contextmanager
def _serving_engine() -> Iterator[tuple[str, int]]:
    """A real engine, serving, plus the port it actually got.

    EPHEMERAL, never the reserved 8790. `core/ports.py` owns that number and an
    operator may have the real engine running on it while the suite runs, so
    binding it here would make a green suite depend on nobody using the product.
    Port 0 asks the OS for a free one and `server_address` reports what it gave.
    """
    server: ThreadingHTTPServer = build_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        yield f"http://127.0.0.1:{port}", port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _main_exit_code(argv: list[str], timeout: float = 15.0) -> int | None:
    """Call `main` where a SUCCESSFUL bind cannot wedge the suite.

    `main` blocks in `serve_forever` the moment it binds, so calling it directly
    on a port it manages to take would hang pytest rather than fail it - and a
    hung run is the one failure mode that teaches people to kill the suite
    instead of reading it. On a daemon thread that outcome becomes a timeout,
    returned as None for the caller to assert against.

    The exception the thread caught is ASSERTED ON rather than merely collected.
    A list that gets filled and never read is exactly how a test ported into
    this tree came to pass against a mutant with the behaviour removed.
    """
    outcome: list[int] = []
    failure: list[BaseException] = []

    def run() -> None:
        try:
            outcome.append(main(argv))
        except BaseException as exc:  # noqa: BLE001 - surfaced through the assertion below
            failure.append(exc)

    thread = threading.Thread(target=run, name="engine-main-under-test", daemon=True)
    thread.start()
    thread.join(timeout)

    assert not failure, f"main raised instead of returning an exit code: {failure[0]!r}"
    if thread.is_alive():
        return None
    return outcome[0] if outcome else None


def test_a_second_engine_cannot_bind_a_port_the_first_already_holds() -> None:
    """MEASURED DEFECT, not a hypothetical, and the engine's own copy of it.

    `socketserver.TCPServer` sets `allow_reuse_address = True`, which sets
    SO_REUSEADDR. On POSIX that only sidesteps TIME_WAIT and is what you want.
    On WINDOWS it lets a completely separate process bind a port another process
    is already listening on, leaving both sockets LISTENING with no defined rule
    about which one receives a connection - and in practice the older one
    answers everything.

    Reproduced against this engine on 2026-09-06: two engine processes both
    bound 127.0.0.1:8790, both logged "PityEngine 0.1.0 listening on
    http://127.0.0.1:8790", and six consecutive /health calls all returned the
    FIRST process's pid. A stranger who edits the engine, restarts it and
    re-queries is served stale answers forever by a process that looks healthy.
    """
    with _serving_engine() as (base, port):
        try:
            intruder = build_server("127.0.0.1", port)
        except OSError as exc:
            assert exc.errno in _ADDRESS_REFUSED, (
                f"the second bind failed with errno {exc.errno!r} ({exc}), which is not "
                "an address refusal - it failed for some unrelated reason"
            )
        else:
            # Close it before failing. Leaving a second listener bound to the
            # incumbent's port is the defect itself, and it would leak into
            # every test that runs after this one.
            intruder.server_close()
            raise AssertionError(
                f"a second engine bound 127.0.0.1:{port} while the first was still "
                "listening - both sockets are now LISTENING and which one answers is undefined"
            )

        # The refusal must leave the incumbent untouched and still serving. This
        # is the property the measured symptom actually violated, and a test
        # that only asserted the raise would not notice losing it.
        status, blob = _get(base, "/health")

    assert status == 200
    assert json.loads(blob)["engine_version"] == ENGINE_VERSION


def test_main_refuses_a_held_port_with_the_documented_exit_code() -> None:
    """The exit code the engine's `main` docstring promises.

    The engine documented NO exit code for a taken port before this - it bound
    unconditionally and returned 0. 2 is taken from `surface/server.py`, which
    already documents exactly this meaning and whose value the Electron shell
    renders refusal text from, so the repository now says one thing rather than
    two. The shell does not spawn the engine, so nothing downstream was broken
    by naming it.
    """
    with _serving_engine() as (_base, port):
        code = _main_exit_code(["--host", "127.0.0.1", "--port", str(port)])

    assert code == 2, (
        "main did not refuse a held port with the documented exit code "
        f"(got {code!r}; None means it bound the port and blocked in serve_forever)"
    )


def test_a_stock_reuseaddr_socket_cannot_take_the_engine_port() -> None:
    """The intruder in its REAL shape - a stock server, not another exclusive one.

    The arm above pits two `build_server` instances against each other, so both
    sides carry the fix. That is not what happened. The intruder in the measured
    incident was a stock `ThreadingHTTPServer`, and `socketserver.TCPServer`
    sets SO_REUSEADDR on every one of those, so the real challenger was a plain
    SO_REUSEADDR socket - which is what this binds.

    MEASURED BIND MATRIX, this machine, win32, 2026-09-06. Every cell was probed
    against a LISTENING first socket, and exactly one of the nine double-binds:

        first=none   second=none  -> refused 10048    first=reuse second=none  -> refused 10048
        first=none   second=reuse -> refused 13       first=reuse second=reuse -> *** BOTH BIND ***
        first=none   second=excl  -> refused 10048    first=reuse second=excl  -> refused 10048
        first=excl   second=none  -> refused 10048
        first=excl   second=reuse -> refused 13
        first=excl   second=excl  -> refused 10048

    So the defect needs SO_REUSEADDR on BOTH sockets, which is exactly what two
    stock engines are, and `allow_reuse_address = False` is the half that closes
    it. Read the `first=none` column against the `first=excl` column: they are
    identical. SO_EXCLUSIVEADDRUSE changes no outcome here, so NO test in this
    file pins that call, and this docstring says so rather than implying
    otherwise. It is kept because it mirrors `surface/server.py`, which is the
    already-adjudicated sibling fix and not this slice's to change.

    On POSIX SO_REUSEADDR only sidesteps TIME_WAIT and never takes a LISTENING
    socket, which is why the setsockopt is guarded by `sys.platform == "win32"`.
    That POSIX claim is textbook but is NOT measured here - this box is Windows,
    and CI is the only place the arm runs on Linux.
    """
    with _serving_engine() as (base, port):
        intruder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        intruder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            intruder.bind(("127.0.0.1", port))
        except OSError as exc:
            assert exc.errno in _ADDRESS_REFUSED, (
                f"the intruding bind failed with errno {exc.errno!r} ({exc}), which is "
                "not an address refusal - it failed for some unrelated reason"
            )
        else:
            raise AssertionError(
                f"a stock SO_REUSEADDR socket took 127.0.0.1:{port} out from under a "
                "listening engine - which is the measured defect, verbatim"
            )
        finally:
            intruder.close()

        # Same as the arm above: the incumbent has to still be there afterwards.
        status, blob = _get(base, "/health")

    assert status == 200
    assert json.loads(blob)["engine_version"] == ENGINE_VERSION


def test_a_stopped_engine_releases_its_port_immediately() -> None:
    """The exclusive bind must not leave the port unusable afterwards.

    TIME_WAIT making a restart fail is the entire reason `allow_reuse_address`
    exists, so turning it off has to be checked for the regression it could
    cause. The engine runs in the FOREGROUND per README section 6, so ctrl-C
    then up-arrow-enter is its ordinary edit loop - a restart that refused its
    own port would be worse than the defect being fixed.

    DELIBERATELY BINDS AND CLOSES WITHOUT SERVING A REQUEST, and that is a
    correctness requirement rather than laziness. A served request leaves the
    server as the ACTIVE CLOSER, because `BaseHTTPRequestHandler` speaks
    HTTP/1.0 and closes after responding, so the connection sits in TIME_WAIT on
    the engine's own port. On POSIX a `bind()` without SO_REUSEADDR then refuses
    that port, correctly and by design - CI runs ubuntu-latest, so an arm that
    served first would assert something FALSE on the platform that gates merges
    while passing on the Windows box it was written on. The claim being pinned
    is about the LISTENING socket, which never enters TIME_WAIT at all.

    RETRIED, AND THE RETRY IS THE POINT rather than a papering-over. Dropping
    SO_REUSEADDR makes this rebind strict, which adds a second way to fail that
    has nothing to do with TIME_WAIT: the OS can hand the freed ephemeral port
    to another process in the gap. The two causes are distinguishable by shape.
    A TIME_WAIT regression fails EVERY attempt, deterministically; a third party
    taking one port fails that port and not a fresh one. So the claim asserted
    is "some just-released port can be rebound immediately", and it stays
    non-vacuous because a real regression fails all the attempts.
    """
    attempts = 5
    failures: list[str] = []

    for _ in range(attempts):
        first: ThreadingHTTPServer = build_server("127.0.0.1", 0)
        port = int(first.server_address[1])
        first.server_close()

        try:
            restarted = build_server("127.0.0.1", port)
        except OSError as exc:
            failures.append(f"{port}: {exc.__class__.__name__} errno={exc.errno}")
            continue
        try:
            assert int(restarted.server_address[1]) == port
            return
        finally:
            restarted.server_close()

    raise AssertionError(
        f"a just-released engine port could not be rebound on any of {attempts} "
        "attempts, which is a TIME_WAIT regression rather than a stolen port: "
        f"{failures}"
    )
