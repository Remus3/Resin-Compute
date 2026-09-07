"""Wish History authkey race - extract, save, and pull, before the ring buffer wins.

THE RACE THIS TOOL EXISTS TO WIN
---------------------------------
Genshin's in-game Wish History page is a webview. Opening it makes the game
navigate an embedded Chromium instance to a URL carrying a short-lived
`authkey` query parameter, and that navigation is written into the game's own
Chromium disk cache at:

    %USERPROFILE%\\AppData\\LocalLow\\miHoYo\\Genshin Impact\\
        GenshinImpact_Data\\webCaches\\<version>\\Cache\\Cache_Data\\data_2

Two facts make this a race rather than a lookup. First, `data_2` is a RING
BUFFER - later cache writes overwrite earlier ones, so the URL is evicted as
the player keeps playing. Second, the authkey itself expires (observed
informally at roughly 24h; not independently reverified here). So this tool
must run WHILE the operator is still in the Wish History page, or shortly
after, not on some later convenient schedule.

THREE VERBS, ONE FILE
----------------------
  --scan     read the cache, report whether an authkey-bearing gacha URL is
             present, print nothing secret.
  --capture  do the same extraction, but SAVE the raw URL (the credential)
             to a file under --out, outside this git tree.
  --pull     read that saved URL back, turn it into an API endpoint, and page
             through every banner's history, writing raw responses and a
             flattened `wishes.jsonl`.

Deliberately three separate steps rather than one. `--capture` can be re-run
safely to refresh a stale authkey without re-running the (slow, rate-limited)
pull; `--pull` can be re-run against the same captured URL if a page fails
partway, without re-touching the cache.

THE HOSTS BELOW ARE UNVERIFIED - READ THIS BEFORE TRUSTING build_api_url()
----------------------------------------------------------------------------
Two candidate API hosts are hardcoded below (`_HOST_NEW`, `_HOST_OLD`).
Neither has been exercised against a live response by this tool as of
writing - there was no authkey available at the time this file was written
to test against. `build_api_url()` picks between them from the captured
webview URL's own host where it can, and falls back to `_HOST_NEW` on any
URL shape it does not recognise. The CLI prints this caveat again at the
moment `--pull` is about to make a real request, on purpose: a silent wrong
guess here would look like a hang or a string of 404s with no explanation.
Once a `--pull` run actually returns HTTP 200, this comment is stale and
should be corrected in place rather than trusted as still-accurate.

WHY THIS IS SECURITY-CRITICAL, NOT JUST FRAGILE
--------------------------------------------------
An authkey is a live bearer credential for the operator's own account for as
long as it is valid. It is treated the same way a password or API token
would be everywhere else in this codebase:

  - NEVER printed to stdout, NEVER logged, in full, anywhere.
  - Every human-readable rendering redacts it as `authkey=<REDACTED len=NNN>`
    (see `_redact_url`). `--scan` and `--capture`'s console output are built
    from the redacted form only; the unredacted URL exists in memory just
    long enough to be written to the one file under `--out` that holds it.
  - `--out` is REFUSED outright when it resolves inside this git tree
    (`assert_outside_repo`). A credential committed to source control is a
    much worse failure than a slightly less convenient CLI, and this repo's
    own hard rule already says no secret is ever written inside it.
  - Raw HTTP failure detail (status codes, upstream retcodes and messages)
    goes to a local log file next to the output, never to stdout, matching
    the inherited rule that a raw API or error string never reaches a
    user-facing surface. Stdout gets a friendly, generic line plus a pointer
    to the log.

WHY THIS IS NOT `data/fixtures/` AND DOES NOT TOUCH `docs/LICENSE_NOTES.md`
------------------------------------------------------------------------------
That document governs THIRD-PARTY game data this project might vendor into
`data/`. This tool does something different in kind: it pulls the OPERATOR'S
OWN account history, with the operator's own credential, to a location the
operator chose outside the repo. Nothing it produces is committed, vendored,
or shared. It is mentioned here only to be explicit that the two questions
are separate and this file answers neither by accident.

WHY THE CACHE IS SCANNED AS RAW BYTES, NOT DECODED AS ONE ENCODING
-----------------------------------------------------------------------
`data_2` is a Chromium disk-cache block file: a mix of binary index
structures, raw ASCII HTTP headers, and UTF-16LE-encoded strings (Windows
Chromium stores some cached string fields in UTF-16LE). Attempting to decode
the whole file as one encoding either throws immediately or silently mangles
the very substrings being searched for. `extract_urls()` therefore never
decodes the file as a whole - it scans the raw bytes for the two BYTE-LEVEL
encodings of the literal `https://` marker (ASCII, and UTF-16LE) and decodes
only the narrow candidate run that follows each hit, one byte or code unit at
a time, stopping the instant a byte cannot be part of a URL.

STDLIB ONLY, CUSTOM USER-AGENT ALWAYS SET
---------------------------------------------
Matching `ingest/enka_client.py`'s posture: `urllib.request` sets a custom
header perfectly well, so a third-party HTTP library buys nothing and would
break the zero-runtime-dependency rule. Unlike the Enka client, HoYoverse's
gacha-log API does not publish a documented User-Agent requirement (nothing
was found to cite), so this tool does not hard-refuse an unset one the way
`ingest/enka_client.py` does - instead it always sends a non-default,
self-identifying `User-Agent` (`DEFAULT_USER_AGENT`, overridable with
`--user-agent`) as the same defensive posture, proactively rather than
because a documented policy demands it.

RATE LIMITING IS REAL AND THIS IS THE OPERATOR'S ACTUAL ACCOUNT
--------------------------------------------------------------------
`pull_history()` sleeps at least `SLEEP_SECONDS` between every request, no
exceptions, because the endpoint is known informally to rate-limit and a
banned or throttled account credential is a much worse outcome than a slow
export.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

# ---------------------------------------------------------------------------
# Where things are
# ---------------------------------------------------------------------------

#: Repository root, computed from this file's own location so the guard below
#: does not depend on the current working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: WHERE webCaches ACTUALLY LIVES, MEASURED 2026-09-07 ON A REAL FIRST RUN.
#:
#: This module was first written against the LocalLow path, which is where
#: most public write-ups put it. That is WRONG for the current HoYoPlay
#: layout and it failed in the worst possible way: `--scan` reported
#: "no webCaches directory found yet" while the operator had the Wish
#: History page open in front of them, so a missing directory and a wrong
#: directory produced the same sentence. The real location on this machine
#: is under the GAME INSTALL, not the user profile:
#:
#:   <install>\Genshin Impact game\GenshinImpact_Data\webCaches\2.54.0.0\
#:       Cache\Cache_Data\data_2
#:
#: 15 ASCII occurrences of "authkey" were grepped out of that data_2 while
#: the LocalLow path did not exist at all.
#:
#: So candidates are TRIED IN ORDER and the first one that exists wins. The
#: LocalLow form is kept last rather than deleted, because an older install
#: may still use it and this tool must not become correct for exactly one
#: layout the way it just was. `RSC_WEBCACHES_ROOT` overrides everything,
#: which is what makes the resolution testable without a game install.
_WEBCACHES_ENV = "RSC_WEBCACHES_ROOT"

#: Install roots to probe, relative to which `_WEBCACHES_TAIL` is appended.
_INSTALL_ROOTS: tuple[str, ...] = (
    "C:/Program Files/HoYoPlay/games/Genshin Impact game",
    "C:/Program Files/Genshin Impact/Genshin Impact game",
    "D:/Program Files/HoYoPlay/games/Genshin Impact game",
    "D:/Genshin Impact/Genshin Impact game",
)

_WEBCACHES_TAIL: tuple[str, ...] = ("GenshinImpact_Data", "webCaches")

#: The legacy user-profile location, kept as the LAST candidate.
_WEBCACHES_PARTS: tuple[str, ...] = (
    "AppData",
    "LocalLow",
    "miHoYo",
    "Genshin Impact",
    "GenshinImpact_Data",
    "webCaches",
)

DEFAULT_USER_AGENT = "resin-compute-wish-authkey/0.1 (local operator tool)"

#: Genshin's gacha_type values and their human labels, as documented in the
#: task brief. "100" (Novice/Beginners) is included even though many accounts
#: have nothing in it, because a banner with zero pages is a normal, cheap
#: result, not a reason to skip the request.
GACHA_TYPES: dict[str, str] = {
    "100": "Novice / Beginners",
    "200": "Standard / Permanent",
    "301": "Character Event",
    "400": "Character Event-2",
    "302": "Weapon Event",
    "500": "Chronicled",
}

PAGE_SIZE = 20

#: Minimum delay between requests. Never reduced at runtime; see the module
#: docstring on rate limiting.
SLEEP_SECONDS = 1.0

TIMEOUT_SECONDS = 15.0

# UNVERIFIED - see the module docstring section on this. `_HOST_NEW` is the
# fallback used whenever the captured URL's host is not recognised.
_HOST_NEW = "https://public-operation-hk4e-sg.hoyoverse.com/gacha_info/api/getGachaLog"
_HOST_OLD = "https://hk4e-api-os.hoyoverse.com/event/gacha_info/api/getGachaLog"

_OLD_HOST_MARKER = "hk4e-api-os.hoyoverse.com"
_NEW_HOST_MARKER = "public-operation-hk4e-sg.hoyoverse.com"

#: Query parameters carried forward from the captured webview URL into the
#: API request, in the order the task brief lists them.
_PRESERVED_PARAMS: tuple[str, ...] = (
    "authkey",
    "authkey_ver",
    "sign_type",
    "lang",
    "game_biz",
    "region",
)


class RepoPathError(ValueError):
    """`--out` resolved inside this git tree. Never caught silently - see main()."""


# ---------------------------------------------------------------------------
# 1. Locating the cache
# ---------------------------------------------------------------------------


def _web_caches_candidates() -> list[Path]:
    """Every place webCaches could be, in the order they are tried.

    The environment override comes first so a test can point this at a
    fixture directory. Then the game installs, because that is where the
    current HoYoPlay layout really puts it. The user-profile form is last.
    """
    out: list[Path] = []
    override = os.environ.get(_WEBCACHES_ENV, "").strip()
    if override:
        out.append(Path(override))
    for install in _INSTALL_ROOTS:
        root = Path(install)
        for part in _WEBCACHES_TAIL:
            root = root / part
        out.append(root)
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        root = Path(userprofile)
        for part in _WEBCACHES_PARTS:
            root = root / part
        out.append(root)
    return out


def _web_caches_root() -> Path:
    """The first candidate that exists, or the first candidate if none do.

    Returning a non-existent path rather than None keeps every caller's
    shape unchanged: `find_web_caches` already treats a missing directory
    as the empty list, which is the correct answer to "has this machine
    ever opened Wish History".
    """
    candidates = _web_caches_candidates()
    for candidate in candidates:
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    return candidates[0]


def find_web_caches() -> list[Path]:
    """Every webCaches version subdirectory, newest (by mtime) first.

    Returns an empty list - never raises - when the game has never run, when
    USERPROFILE is unset, or when the directory is unreadable for any other
    reason. An empty list is the correct, unremarkable answer to "has this
    machine ever opened Wish History", not an error condition.
    """
    root = _web_caches_root()
    try:
        if not root.is_dir():
            return []
        candidates = [entry for entry in root.iterdir() if entry.is_dir()]
    except OSError:
        return []

    def _mtime(entry: Path) -> float:
        try:
            return entry.stat().st_mtime
        except OSError:
            return 0.0

    candidates.sort(key=_mtime, reverse=True)
    return candidates


def data_2_path(version_dir: Path) -> Path:
    """The cache data file inside one version directory."""
    return version_dir / "Cache" / "Cache_Data" / "data_2"


# ---------------------------------------------------------------------------
# 2. Extracting candidate URLs from the raw cache bytes
# ---------------------------------------------------------------------------

#: Bytes that may appear inside a URL, per RFC 3986 unreserved + reserved
#: characters plus "%" for percent-encoding. Deliberately excludes control
#: bytes, whitespace, quotes, angle brackets and backslash - none of those are
#: valid unescaped URL characters, and cutting on them is what stops the scan
#: from running away into unrelated binary noise.
_URL_CHARS: frozenset[int] = frozenset(
    ord(c)
    for c in (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-._~:/?#[]@!$&'()*+,;=%"
    )
)

_ASCII_MARKER = b"https://"
_UTF16LE_MARKER = "https://".encode("utf-16-le")

#: Hard ceiling on one candidate's length, in bytes of the SOURCE encoding.
#: A real gacha URL is well under a kilobyte; this only exists to stop a
#: pathological run of URL-legal bytes in unrelated binary data from being
#: read as one enormous "URL".
_MAX_CANDIDATE_BYTES = 4096


def _scan_ascii_urls(data: bytes) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    search_from = 0
    length = len(data)
    while True:
        start = data.find(_ASCII_MARKER, search_from)
        if start == -1:
            break
        end = start
        while end < length and data[end] in _URL_CHARS and end - start < _MAX_CANDIDATE_BYTES:
            end += 1
        if end > start + len(_ASCII_MARKER):
            try:
                found.append((start, data[start:end].decode("ascii")))
            except UnicodeDecodeError:  # pragma: no cover - _URL_CHARS is ASCII-only
                pass
        search_from = start + 1
    return found


def _scan_utf16le_urls(data: bytes) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    search_from = 0
    length = len(data)
    while True:
        start = data.find(_UTF16LE_MARKER, search_from)
        if start == -1:
            break
        end = start
        while end + 1 < length and end - start < _MAX_CANDIDATE_BYTES * 2:
            low_byte, high_byte = data[end], data[end + 1]
            if high_byte != 0 or low_byte not in _URL_CHARS:
                break
            end += 2
        if end > start + len(_UTF16LE_MARKER):
            try:
                found.append((start, data[start:end].decode("utf-16-le")))
            except UnicodeDecodeError:  # pragma: no cover - byte pairs pre-filtered above
                pass
        search_from = start + 1
    return found


def extract_urls(data_2_bytes: bytes) -> list[str]:
    """Every distinct URL-shaped run following an `https://` marker.

    Scans for BOTH the raw ASCII marker and its UTF-16LE encoding - see the
    module docstring on why the file is not decoded as one encoding. Distinct
    strings only; when the same URL text appears at more than one offset
    (common in a ring buffer that has wrapped), only its EARLIEST offset
    decides its position in the result, and the result is ordered by that
    offset ascending - so the LAST entry is the most recently written
    candidate, feeding `select_gacha_urls`' "newest-last" contract directly.
    """
    first_offset: dict[str, int] = {}
    for offset, url in _scan_ascii_urls(data_2_bytes) + _scan_utf16le_urls(data_2_bytes):
        if url not in first_offset:
            first_offset[url] = offset
    return [url for url, _ in sorted(first_offset.items(), key=lambda pair: pair[1])]


# ---------------------------------------------------------------------------
# 3. Selecting the gacha-log URLs out of everything found
# ---------------------------------------------------------------------------

_GACHA_MARKERS: tuple[str, ...] = ("getGachaLog", "gacha", "e20190909gacha")


def select_gacha_urls(urls: list[str]) -> list[str]:
    """Keep only URLs that carry an authkey AND look like a gacha-log page.

    Order is inherited from `urls` unchanged - `extract_urls` already returns
    its list oldest-offset-first, so this stays newest-last: `result[-1]` is
    the best candidate to act on.
    """
    return [
        url
        for url in urls
        if "authkey=" in url and any(marker in url for marker in _GACHA_MARKERS)
    ]


def _redact_url(url: str) -> str:
    """Human-readable form of `url` with the authkey VALUE removed.

    Every other query parameter is left as-is; only the key named `authkey`
    is replaced. This is the ONLY form of a captured URL that may reach
    stdout, a print(), or a log line.
    """
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted_pairs = [
        (key, f"<REDACTED len={len(value)}>" if key == "authkey" else value) for key, value in pairs
    ]
    redacted_query = urllib.parse.urlencode(redacted_pairs, safe="<>=")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, redacted_query, ""))


# ---------------------------------------------------------------------------
# 4. Turning a captured webview URL into an API endpoint
# ---------------------------------------------------------------------------


def build_api_url(raw_url: str) -> str:
    """Normalise a captured webview URL into the gacha-log API endpoint.

    UNVERIFIED - see the module docstring. Host selection is by substring
    match against the captured URL's own netloc, falling back to `_HOST_NEW`
    (the first-listed host) when neither marker is present, per the task
    brief's instruction to fall back to the first when the host cannot be
    derived.
    """
    parsed = urllib.parse.urlsplit(raw_url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    kept: dict[str, str] = {}
    for key, value in pairs:
        if key in _PRESERVED_PARAMS and key not in kept:
            kept[key] = value

    if _OLD_HOST_MARKER in parsed.netloc:
        base = _HOST_OLD
    elif _NEW_HOST_MARKER in parsed.netloc:
        base = _HOST_NEW
    else:
        base = _HOST_NEW

    ordered = {key: kept[key] for key in _PRESERVED_PARAMS if key in kept}
    return base + "?" + urllib.parse.urlencode(ordered)


# ---------------------------------------------------------------------------
# 5. Paging through every banner
# ---------------------------------------------------------------------------

#: Transport contract, matching `ingest/enka_client.py`'s shape:
#: (url, headers, timeout) -> (status_code, body_bytes). Injectable so this
#: module never needs a socket to be exercised directly.
Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


def _urllib_get(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except OSError:
            body = b""
        return int(exc.code), body
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` via a same-directory temp file plus rename.

    Matches `core/atomic_io.py`'s pattern; not imported directly so this
    stdlib-only CLI tool stays runnable with nothing but `tools/` on the path,
    the same posture `tools/first_run_capture.py` and `tools/precommit_gate.py`
    already take.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        tmp.replace(path)
    except OSError:
        pass


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _append_wishes(path: Path, items: list[object], gacha_type: str) -> None:
    """Append flattened records to `path`, rewritten atomically as a whole.

    `path` is small (thousands of wish records at most), so read-modify-
    atomic-rewrite is cheap and gives the same "a reader never sees a partial
    file" guarantee `core/atomic_io.py` states the reason for, without
    depending on it.
    """
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            record = dict(item)
            record.setdefault("gacha_type", gacha_type)
            lines.append(json.dumps(record, ensure_ascii=True, sort_keys=True))
    if not lines:
        return
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError:
        existing = ""
    _atomic_write_text(path, existing + "".join(line + "\n" for line in lines))


def assert_outside_repo(out_path: Path) -> Path:
    """Resolve `out_path` and refuse it when it falls inside this git tree.

    The authkey is a live credential for the operator's real account. Every
    path this module is allowed to write it to must be checked here first -
    both CLI entry points call this before touching disk.
    """
    resolved = out_path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise RepoPathError(
            f"refusing to write to {resolved} - it is inside this git tree "
            f"({REPO_ROOT}). The wish-history authkey is a live account "
            "credential and this repo's hard rule is that no secret is ever "
            "written inside it. Pick a path outside the repository, for "
            "example C:/rsc-first-run/wish."
        )
    return resolved


def _configure_logger(out_dir: Path) -> logging.Logger:
    """A file-only logger for raw error detail. Never attached to stdout.

    Raw HTTP status detail and upstream retcode messages are logged here, not
    printed, matching the inherited rule that a raw API or error string never
    reaches a user-facing surface.
    """
    logger = logging.getLogger("wish_authkey")
    logger.setLevel(logging.ERROR)
    if not logger.handlers:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(out_dir / "wish_authkey.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.NullHandler())
    return logger


def pull_history(
    api_url: str,
    out_path: Path,
    *,
    transport: Transport = _urllib_get,
    sleeper: Callable[[float], None] = time.sleep,
    user_agent: str = DEFAULT_USER_AGENT,
    log: logging.Logger | None = None,
) -> dict[str, int]:
    """Page through every banner in `GACHA_TYPES`, writing raw and flattened output.

    Writes every raw response body verbatim to `<out>/raw/<gacha_type>_<page>.json`
    - including a non-200 or malformed one, so a failed banner is still on
    disk to inspect - and every parsed record to `<out>/wishes.jsonl`. A
    non-zero `retcode` in an otherwise-200 response STOPS that banner and is
    recorded (raw file plus a log line); it is never silently swallowed.

    Sleeps at least `SLEEP_SECONDS` before every request after the first, no
    exceptions - see the module docstring on rate limiting.
    """
    logger = log if log is not None else logging.getLogger("wish_authkey")
    resolved = assert_outside_repo(out_path)
    parsed = urllib.parse.urlsplit(api_url)
    base_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    raw_dir = resolved / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    wishes_path = resolved / "wishes.jsonl"
    headers = {"User-Agent": user_agent, "Accept": "application/json"}

    summary: dict[str, int] = {}
    made_a_request = False

    for gacha_type in GACHA_TYPES:
        end_id = "0"
        page = 0
        total = 0
        while True:
            page += 1
            if made_a_request:
                sleeper(SLEEP_SECONDS)
            made_a_request = True

            query = dict(base_query)
            query.update({"gacha_type": gacha_type, "size": str(PAGE_SIZE), "end_id": end_id, "page": "1"})
            url = base + "?" + urllib.parse.urlencode(query)
            status, body = transport(url, headers, TIMEOUT_SECONDS)
            _atomic_write_bytes(raw_dir / f"{gacha_type}_{page}.json", body)

            if status != 200:
                logger.error("gacha_type %s page %s returned HTTP %s", gacha_type, page, status)
                print(f"wish_authkey: pull - {gacha_type} page {page} got HTTP {status}, stopping this banner (see wish_authkey.log)")
                break

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                logger.error(
                    "gacha_type %s page %s body did not parse: %s", gacha_type, page, type(exc).__name__
                )
                print(f"wish_authkey: pull - {gacha_type} page {page} returned an unreadable body, stopping this banner")
                break

            if not isinstance(payload, dict):
                logger.error("gacha_type %s page %s body was not a JSON object", gacha_type, page)
                print(f"wish_authkey: pull - {gacha_type} page {page} returned an unexpected shape, stopping this banner")
                break

            retcode = payload.get("retcode")
            if retcode != 0:
                logger.error(
                    "gacha_type %s page %s retcode %s message %s",
                    gacha_type, page, retcode, payload.get("message", ""),
                )
                print(f"wish_authkey: pull - {gacha_type} stopped, upstream retcode {retcode} (see wish_authkey.log)")
                break

            data = payload.get("data")
            items = data.get("list") if isinstance(data, dict) else None
            if not items:
                break

            _append_wishes(wishes_path, items, gacha_type)
            total += len(items)

            last = items[-1]
            last_id = last.get("id") if isinstance(last, dict) else None
            if not isinstance(last_id, str) or not last_id or len(items) < PAGE_SIZE:
                break
            end_id = last_id

        summary[gacha_type] = total

    return summary


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------


def _do_scan() -> int:
    versions = find_web_caches()
    if not versions:
        print(
            "wish_authkey: scan - no webCaches directory found yet. Has Genshin "
            "Impact ever been launched on this machine?"
        )
        return 0

    total_candidates = 0
    total_gacha = 0
    newest_redacted = ""
    for version_dir in versions:
        try:
            raw = data_2_path(version_dir).read_bytes()
        except OSError:
            continue
        urls = extract_urls(raw)
        gacha = select_gacha_urls(urls)
        total_candidates += len(urls)
        total_gacha += len(gacha)
        if gacha and not newest_redacted:
            newest_redacted = _redact_url(gacha[-1])

    print(
        f"wish_authkey: scan - checked {len(versions)} cache version dir(s), "
        f"{total_candidates} URL candidate(s) total"
    )
    if total_gacha:
        print(f"wish_authkey: scan - authkey present: True ({total_gacha} candidate(s))")
        print(f"wish_authkey: scan - newest candidate (redacted): {newest_redacted}")
    else:
        print(
            "wish_authkey: scan - authkey present: False. Open Wish History in-game "
            "while this is running, then scan again."
        )
    return 0


def _do_capture(out_dir: Path) -> int:
    resolved = assert_outside_repo(out_dir)
    for version_dir in find_web_caches():
        try:
            raw = data_2_path(version_dir).read_bytes()
        except OSError:
            continue
        gacha = select_gacha_urls(extract_urls(raw))
        if not gacha:
            continue

        captured_url = gacha[-1]
        payload = {
            "captured_at_epoch": time.time(),
            "source_version_dir": version_dir.name,
            "url": captured_url,
        }
        target = resolved / "captured_url.json"
        _atomic_write_text(target, json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        print(f"wish_authkey: capture - saved 1 URL to {target}")
        print(f"wish_authkey: capture - redacted: {_redact_url(captured_url)}")
        return 0

    print(
        "wish_authkey: capture - no gacha authkey URL found in any cache dir yet. "
        "Open Wish History in-game, then run --capture again before the cache evicts it."
    )
    return 1


def _do_pull(out_dir: Path, user_agent: str) -> int:
    resolved = assert_outside_repo(out_dir)
    captured_path = resolved / "captured_url.json"
    try:
        payload = json.loads(captured_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"wish_authkey: pull - could not read a captured URL from {captured_path}. Run --capture first.")
        return 1

    raw_url = payload.get("url") if isinstance(payload, dict) else None
    if not isinstance(raw_url, str) or not raw_url:
        print(f"wish_authkey: pull - {captured_path} carries no usable url field. Run --capture again.")
        return 1

    api_url = build_api_url(raw_url)
    print(
        "wish_authkey: pull - CAVEAT: the gacha-log API host guessed here is UNVERIFIED "
        "against a live response as of when this tool was written. A non-200 status or "
        "an unreadable body below may mean the host or path guess is wrong, not that the "
        "authkey is bad."
    )

    log = _configure_logger(resolved)
    summary = pull_history(api_url, resolved, user_agent=user_agent, log=log)
    for gacha_type, label in GACHA_TYPES.items():
        print(f"wish_authkey: pull - {label} ({gacha_type}): {summary.get(gacha_type, 0)} record(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wish_authkey",
        description="Capture and pull Genshin Wish History via the webview authkey race.",
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="scan the webCaches ring buffer, report whether an authkey is present, print nothing secret",
    )
    parser.add_argument(
        "--capture", action="store_true",
        help="extract the newest gacha authkey URL and save it under --out",
    )
    parser.add_argument(
        "--pull", action="store_true",
        help="page through wish history using the URL --capture saved under --out",
    )
    parser.add_argument("--out", type=str, default=None, help="output directory, must be outside this git tree")
    parser.add_argument(
        "--user-agent", type=str, default=DEFAULT_USER_AGENT,
        help="custom User-Agent sent on every request during --pull",
    )
    args = parser.parse_args(argv)

    if args.scan:
        return _do_scan()

    if args.capture:
        if not args.out:
            print("wish_authkey: --capture requires --out <path outside the repo>")
            return 2
        try:
            return _do_capture(Path(args.out))
        except RepoPathError as exc:
            print(f"wish_authkey: refused - {exc}")
            return 2

    if args.pull:
        if not args.out:
            print("wish_authkey: --pull requires --out <path outside the repo>")
            return 2
        try:
            return _do_pull(Path(args.out), args.user_agent)
        except RepoPathError as exc:
            print(f"wish_authkey: refused - {exc}")
            return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
