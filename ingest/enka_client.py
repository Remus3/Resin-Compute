"""Minimal Enka profile client, re-implemented from the published protocol.

LICENSE POSTURE - read this before adding a dependency here.
-----------------------------------------------------------
Nothing in this module is lifted from any upstream project. The Enka API-docs
repository carries NO LICENSE file, so only the PROTOCOL FACTS it publishes
(endpoint shapes, field names, status codes) are used, and facts are not
copyrightable. `enka-py` and `ambr-py` are both GPL-3.0 and vendoring either
would relicense this repository, so neither is used or copied. See
`docs/SPEC_SCAFFOLD.md` section 4 and `data/fixtures/README.md`.

Stdlib only, by design: `urllib.request` sets a custom header perfectly well, so
a third-party HTTP library buys nothing and would break the zero-runtime-
dependency rule in `requirements.txt`.

UPSTREAM POLICY, quoted verbatim from the published docs
--------------------------------------------------------
    "don't try to enumerate UIDs or try to do massive query jobs in an effort to
    fill a database"

That prohibition is enforced here, not merely documented: `fetch_profiles`
refuses a batch larger than MAX_BATCH_UIDS, and every response `ttl` is honoured
by an on-disk cache that SUPPRESSES a repeat request for the same UID until it
expires. Suppression is not an optimisation - upstream returns cached data until
`ttl` elapses and that response STILL burns the rate limit, so a client that
re-asks inside the window pays the full cost for zero new information.

A custom `User-Agent` is REQUIRED BY UPSTREAM POLICY. This client refuses to
make any request when it is unset rather than silently sending a default.

Every documented status code degrades to a friendly, constant message. No raw
exception text, URL or upstream body ever reaches the caller, matching the
inherited rule "never surface a raw API or error string in a user-facing
surface".
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Protocol constants - every one of these is verified in SPEC section 4 / 5.
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://enka.network"

#: Full profile: playerInfo + avatarInfoList.
PROFILE_PATH = "/api/uid/{uid}/"

#: playerInfo only, much faster. The trailing `?info` is part of the documented
#: path form, not a general query parameter.
INFO_PATH = "/api/uid/{uid}/?info"

#: The brief's "https://enka.network<uid>" is malformed and is deliberately not
#: reproduced anywhere in this module.

#: Hard ceiling on a single batch call. Deliberately small: the upstream
#: prohibition is against bulk collection, and a limit that would permit a
#: "massive query job" is not a limit.
MAX_BATCH_UIDS = 5

#: Only these two degrade transiently and are worth another attempt. A 400, 404
#: or 424 will return exactly the same answer on a retry, so retrying them just
#: spends rate limit.
RETRY_STATUSES = frozenset({429, 503})

#: Sentinel status for "the request never reached the service" (DNS failure,
#: connection refused, timeout). Not an upstream code.
STATUS_UNREACHABLE = 0

#: Friendly, CONSTANT degraded messages. These are string literals on purpose:
#: interpolating an exception, a URL or an upstream body here is exactly the
#: leak the error-handling rule forbids.
STATUS_MESSAGES: dict[int, str] = {
    400: "That UID does not look right - check the digits and try again.",
    404: "No player profile was found for that UID.",
    424: "The profile service is updating for a new game version - try again later.",
    429: "The profile service is rate limiting us - waiting before the next attempt.",
    500: "The profile service hit an internal error - try again in a few minutes.",
    503: "The profile service is temporarily unavailable - try again in a few minutes.",
    STATUS_UNREACHABLE: "Could not reach the profile service - check the network connection.",
}

MESSAGE_OK = "Profile loaded."
MESSAGE_CACHED = "Profile loaded from cache - upstream refresh is not due yet."
MESSAGE_UNEXPECTED = "The profile service returned an unexpected response - try again later."
MESSAGE_MALFORMED = "The profile service returned a response we could not read - try again later."

#: Fallback when upstream omits `ttl`. Short on purpose: a wrong-and-long ttl
#: suppresses real refreshes, a wrong-and-short one only costs one request.
DEFAULT_TTL_SECONDS = 60

#: Transport contract: (url, headers, timeout) -> (status_code, body_bytes).
#: Injected in tests so the suite never opens a socket.
Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


class EnkaConfigError(RuntimeError):
    """The client is misconfigured and must not make a request.

    Distinct from a degraded fetch on purpose. A degraded fetch is an expected
    runtime state that the caller renders as a friendly message; this is a
    programming or deployment mistake that a retry cannot fix, so it is raised
    rather than folded into a FetchResult. Callers at a user-facing boundary
    (see `scripts/bootstrap_data.py`) catch it and print the message.
    """


class EnkaUsageError(RuntimeError):
    """A call that would violate the upstream no-bulk-collection prohibition."""


@dataclass(frozen=True)
class EnkaConfig:
    """Client configuration.

    `user_agent` has NO default value on purpose. Upstream policy requires a
    custom User-Agent that identifies the caller, so a default would be a silent
    policy violation shipped as a convenience.
    """

    user_agent: str = ""
    cache_dir: Path = Path("data/cache/enka")
    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_base_seconds: float = 1.0
    base_url: str = DEFAULT_BASE_URL


@dataclass(frozen=True)
class FetchResult:
    """One fetch outcome, degraded or successful.

    Never carries raw error text. `friendly_message` is always one of the
    constants above, so a caller can render it directly in any surface.
    """

    ok: bool
    profile_json: dict | None
    status: int | None
    friendly_message: str
    uid: str = ""
    ttl_seconds: int = 0
    from_cache: bool = False
    retries: int = 0
    retry_after_seconds: float = 0.0


def _urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    """Default transport. Converts every failure mode into a status code.

    Deliberately swallows the exception objects rather than re-raising: the raw
    text of an HTTPError or URLError names the URL and sometimes the upstream
    body, and that must not travel further up. The status code carries all the
    information the caller is allowed to act on.
    """
    request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 - https literal, not user input
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except OSError:
            body = b""
        return int(exc.code), body
    except (urllib.error.URLError, TimeoutError, OSError):
        return STATUS_UNREACHABLE, b""


@dataclass
class EnkaClient:
    """Single-UID profile reader with a ttl-honouring on-disk cache.

    `transport`, `clock` and `sleeper` are injectable so the whole class is
    testable without a socket and without wall-clock waits.
    """

    config: EnkaConfig = field(default_factory=EnkaConfig)
    transport: Transport = _urllib_transport
    clock: Callable[[], float] = time.time
    sleeper: Callable[[float], None] = time.sleep

    # -- public API --------------------------------------------------------

    def fetch_profile(self, uid: str | int, *, info_only: bool = False, force: bool = False) -> FetchResult:
        """Fetch one profile, serving an unexpired cached copy when present.

        `force` bypasses the cache READ. It exists for an operator-driven manual
        refresh only. It does not bypass the ttl WRITE, so a forced call still
        re-arms suppression for the next caller.
        """
        uid_text = str(uid).strip()
        if not self._uid_looks_valid(uid_text):
            # Answered locally. Sending a known-bad UID upstream would spend
            # rate limit to be told what we already know.
            return FetchResult(
                ok=False,
                profile_json=None,
                status=400,
                friendly_message=STATUS_MESSAGES[400],
                uid=uid_text,
            )

        headers = self._headers()  # raises EnkaConfigError before any I/O

        if not force:
            cached = self._read_cache(uid_text)
            if cached is not None:
                body, ttl_left = cached
                return FetchResult(
                    ok=True,
                    profile_json=body,
                    status=200,
                    friendly_message=MESSAGE_CACHED,
                    uid=uid_text,
                    ttl_seconds=ttl_left,
                    from_cache=True,
                )

        path = INFO_PATH if info_only else PROFILE_PATH
        url = self.config.base_url.rstrip("/") + path.format(uid=uid_text)
        return self._fetch_with_retries(url, headers, uid_text)

    def fetch_profiles(self, uids: Sequence[str | int]) -> list[FetchResult]:
        """Fetch a SMALL batch. Refuses anything that looks like bulk collection.

        Upstream is explicit: "don't try to enumerate UIDs or try to do massive
        query jobs in an effort to fill a database". A batch call is therefore
        capped rather than merely discouraged.
        """
        uid_list = list(uids)
        if len(uid_list) > MAX_BATCH_UIDS:
            raise EnkaUsageError(
                f"refusing a batch of {len(uid_list)} UIDs - the limit is {MAX_BATCH_UIDS}. "
                "Upstream policy: do not enumerate UIDs or run massive query jobs to fill a database."
            )
        return [self.fetch_profile(uid) for uid in uid_list]

    def cache_path_for(self, uid: str | int) -> Path:
        """Where this UID's cached body lives. Public so ops can inspect it."""
        return Path(self.config.cache_dir) / f"{str(uid).strip()}.json"

    # -- internals ---------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Build request headers, refusing to proceed without a User-Agent."""
        agent = (self.config.user_agent or "").strip()
        if not agent:
            raise EnkaConfigError(
                "EnkaConfig.user_agent is not set. The profile service REQUIRES a custom "
                "User-Agent identifying the caller, so no request will be made. Set the "
                "user_agent config key (CLI flag: --user-agent) to something like "
                "'resin-compute/0.1 (contact: <your handle>)'."
            )
        return {"User-Agent": agent, "Accept": "application/json"}

    @staticmethod
    def _uid_looks_valid(uid: str) -> bool:
        """Cheap local shape check. Game UIDs are digit strings."""
        return uid.isdigit() and 6 <= len(uid) <= 12

    def _fetch_with_retries(self, url: str, headers: dict[str, str], uid: str) -> FetchResult:
        """Attempt the request, backing off on 429/503 only, bounded."""
        attempts = 0
        max_retries = max(0, int(self.config.max_retries))
        while True:
            status, body = self.transport(url, headers, self.config.timeout_seconds)

            if status == 200:
                return self._handle_ok(body, uid, attempts)

            if status in RETRY_STATUSES and attempts < max_retries:
                # Exponential, bounded: base * 2**n over at most max_retries.
                delay = self.config.backoff_base_seconds * (2**attempts)
                self.sleeper(delay)
                attempts += 1
                continue

            message = STATUS_MESSAGES.get(int(status), MESSAGE_UNEXPECTED)
            retry_after = 0.0
            if status in RETRY_STATUSES:
                retry_after = self.config.backoff_base_seconds * (2**max_retries)
            return FetchResult(
                ok=False,
                profile_json=None,
                status=int(status),
                friendly_message=message,
                uid=uid,
                retries=attempts,
                retry_after_seconds=retry_after,
            )

    def _handle_ok(self, body: bytes, uid: str, attempts: int) -> FetchResult:
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # The decoder's message quotes the payload; it is logged by the
            # caller if wanted, never surfaced.
            return FetchResult(
                ok=False,
                profile_json=None,
                status=200,
                friendly_message=MESSAGE_MALFORMED,
                uid=uid,
                retries=attempts,
            )
        if not isinstance(parsed, dict):
            return FetchResult(
                ok=False,
                profile_json=None,
                status=200,
                friendly_message=MESSAGE_MALFORMED,
                uid=uid,
                retries=attempts,
            )

        ttl = self._coerce_ttl(parsed.get("ttl"))
        self._write_cache(uid, parsed, ttl)
        return FetchResult(
            ok=True,
            profile_json=parsed,
            status=200,
            friendly_message=MESSAGE_OK,
            uid=uid,
            ttl_seconds=ttl,
            retries=attempts,
        )

    @staticmethod
    def _coerce_ttl(raw: object) -> int:
        # Narrowed rather than suppressed, same reasoning as _as_int in the
        # mapper: `raw` comes straight off untyped upstream JSON, so a bare
        # int() is a genuine call-overload error and an ignore would hide it.
        if not isinstance(raw, (int, float, str)):
            return DEFAULT_TTL_SECONDS
        try:
            ttl = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_TTL_SECONDS
        return ttl if ttl > 0 else DEFAULT_TTL_SECONDS

    def _read_cache(self, uid: str) -> tuple[dict, int] | None:
        """Return (body, seconds_left) when a cached copy is still inside ttl."""
        path = self.cache_path_for(uid)
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return None
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(envelope, dict):
            return None
        expires_at = envelope.get("expires_at")
        body = envelope.get("body")
        if not isinstance(expires_at, (int, float)) or not isinstance(body, dict):
            return None
        remaining = float(expires_at) - self.clock()
        if remaining <= 0:
            return None
        return body, int(remaining)

    def _write_cache(self, uid: str, body: dict, ttl: int) -> None:
        """Persist the body plus its expiry. Atomic write, per the hard rule."""
        path = self.cache_path_for(uid)
        envelope = {
            "uid": uid,
            "ttl": ttl,
            "expires_at": self.clock() + ttl,
            "body": body,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(envelope), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            # A cache that cannot be written is a degraded optimisation, never a
            # failed fetch. The profile in hand is still good.
            return


def iter_status_messages() -> Iterable[tuple[int, str]]:
    """Every documented status mapping. Used by tests and by ops docs."""
    return sorted(STATUS_MESSAGES.items())
