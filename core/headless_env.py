"""The headless route: the ONE gate every unattended `claude` spawn goes through.

OPERATOR DIRECTIVE, 2026-10-02. Every headless Claude run this tree starts - an
inbox responder, a lane, a loop, a watchdog, anything that spawns `claude`
without an open session - runs on a SECOND subscription through a local proxy.

THE CONTRACT, clause by clause:

- The proxy's base URL is read AT SPAWN TIME from the USER environment store
  (`HKCU\\Environment`, through `winreg`) under `CLAUDE_HEADLESS_BASE_URL`,
  falling back to the process environment. The store comes first because a
  process started before the variable was set did not inherit it.
- It is set as `ANTHROPIC_BASE_URL` in the CHILD's environment only. This
  module never writes `os.environ` and never writes any persistent store.
- FAIL CLOSED. Unset, empty, malformed, or a refused TCP connect to the host
  and port the value names: refuse, log why, spawn nothing. There is no
  fallback to a direct `claude` - a fallback would bill the operator's
  interactive subscription, which is the thing the route exists to avoid.
- No URL, account id or machine path is written into tracked code. The probe
  target is derived from the variable at run time.

THE KILL SWITCH. Deleting the variable stops every tree at once. That only
works if a stale copy cannot outlive the deletion, so the precedence is: when
the user store CAN be read, it is AUTHORITATIVE - an absent value there refuses
even if this process inherited the variable before it was deleted. The process
environment is consulted only when the store cannot be read at all (not
Windows, or the key unreadable). This is a reading of "falling back to the
process env" chosen so the kill switch keeps working, and it is stated here
rather than left implicit.

A refusal reason never carries the value itself: reasons reach held files,
metrics rows and logs.
"""
from __future__ import annotations

import logging
import os
import socket
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

#: The variable the operator sets user-wide. Its DELETION is the kill switch.
ENV_HEADLESS_BASE_URL = "CLAUDE_HEADLESS_BASE_URL"

#: The variable the CHILD reads. Set in the child's environment only - never
#: user-wide, never machine-wide, never in this process.
ENV_CHILD_BASE_URL = "ANTHROPIC_BASE_URL"

#: Removed from the CHILD's environment, never from this process. Each one
#: either authenticates directly or switches the provider, and any of them
#: inherited by the child outranks or bypasses the proxy - a billing bypass.
#: A later addition is one line here.
CHILD_ENV_STRIPPED: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_VERTEX_PROJECT_ID",
)

#: The connect probe's ceiling. Short: the proxy is expected to be local.
PROBE_TIMEOUT_SECONDS = 2.0

REFUSE_UNSET = (
    f"{ENV_HEADLESS_BASE_URL} is unset - headless spawn refused (fail closed, "
    "no direct fallback)"
)
REFUSE_MALFORMED = (
    f"{ENV_HEADLESS_BASE_URL} is not an http(s) URL with a host and port - "
    "headless spawn refused (fail closed)"
)
REFUSE_UNREACHABLE = (
    "the headless proxy refused a TCP connection - headless spawn refused "
    "(fail closed, no direct fallback)"
)


class StoreUnavailable(Exception):
    """The user environment store cannot be read here at all."""


class Decision(NamedTuple):
    """Whether a headless spawn may proceed, and with which environment."""

    ok: bool
    #: The CHILD's environment: a copy of the parent plus the one key. None on
    #: refusal, so a caller cannot spawn with it by accident.
    env: dict[str, str] | None
    #: Empty on success, one of the `REFUSE_*` constants otherwise.
    reason: str


def read_user_store(name: str) -> str | None:
    """`name` from `HKCU\\Environment`. None means ABSENT from the store.

    Raises `StoreUnavailable` when there is no store to read - not Windows, or
    the key exists and cannot be opened - which is the only case in which the
    caller falls back to the process environment.
    """
    if os.name != "nt":
        raise StoreUnavailable("no user environment store on this platform")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise StoreUnavailable(exc.__class__.__name__) from None
    if not isinstance(value, str):
        return None
    if kind == winreg.REG_EXPAND_SZ:
        value = winreg.ExpandEnvironmentStrings(value)
    return value


def resolve_base_url(
    read_store: Callable[[str], str | None] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """The configured base URL, or None. The store is authoritative when readable."""
    reader = read_user_store if read_store is None else read_store
    env = os.environ if environ is None else environ
    try:
        value = reader(ENV_HEADLESS_BASE_URL)
    except StoreUnavailable:
        value = env.get(ENV_HEADLESS_BASE_URL)
    if value is None or not value.strip():
        return None
    return value.strip()


def endpoint_of(url: str) -> tuple[str, int] | None:
    """`(host, port)` from an http(s) URL, or None when it does not name one."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    return parts.hostname, port


def probe(
    host: str,
    port: int,
    timeout: float = PROBE_TIMEOUT_SECONDS,
    connect: Callable[..., Any] | None = None,
) -> bool:
    """Whether a TCP connection to `host:port` is accepted. Never raises."""
    dial = socket.create_connection if connect is None else connect
    try:
        conn = dial((host, port), timeout=timeout)
    except OSError:
        return False
    try:
        conn.close()
    except OSError:
        pass
    return True


def _refuse(reason: str) -> Decision:
    log.warning("headless route: %s", reason)
    return Decision(False, None, reason)


def prepare_headless_env(
    read_store: Callable[[str], str | None] | None = None,
    environ: Mapping[str, str] | None = None,
    connect: Callable[..., Any] | None = None,
    timeout: float = PROBE_TIMEOUT_SECONDS,
) -> Decision:
    """Decide one headless spawn. Every argument is injectable for tests.

    Called with no arguments in production, so every read is live at the
    instant of the spawn - nothing is cached across calls.
    """
    url = resolve_base_url(read_store, environ)
    if url is None:
        return _refuse(REFUSE_UNSET)
    target = endpoint_of(url)
    if target is None:
        return _refuse(REFUSE_MALFORMED)
    if not probe(target[0], target[1], timeout=timeout, connect=connect):
        return _refuse(REFUSE_UNREACHABLE)
    child = {
        k: v
        for k, v in (os.environ if environ is None else environ).items()
        if k not in CHILD_ENV_STRIPPED
    }
    child[ENV_CHILD_BASE_URL] = url
    return Decision(True, child, "")
