"""Screen capture daemon for the first (unrepeatable) Genshin Impact launch.

WHY THIS EXISTS. The operator is about to launch Genshin Impact on this
machine for the very first time. `tools/first_run_capture.py` (not this file)
already watches the filesystem and the registry for that launch, because both
of those overwrite their own history in place. The screen is a THIRD surface
that first_run_capture.py does not touch at all: the first-run intro cinematic,
the initial character selection, the very first login prompt and any one-time
dialog are rendered pixels only, with no corresponding file or registry key.
Once the operator clicks past a screen it is gone forever, so this daemon's
job is to keep a screenshot cadence running through the whole first session
and never miss the two or three seconds that mattered.

THE TRAP THIS FILE DEFENDS AGAINST. A screenshot daemon that silently dies
mid-session is the single worst failure mode here, because the operator has no
way to notice - the game keeps running, nothing on screen changes, and the
absence only becomes visible hours later when someone goes looking for a frame
that was never written. Two design choices exist purely to make "the daemon
went quiet" distinguishable from "the daemon is alive and correctly doing
nothing":

  1. Every tick appends exactly one line to `screens_index.jsonl`, whether or
     not a PNG was written that tick. A run of "duplicate-skipped" lines with
     advancing timestamps IS evidence of life. A gap in the timestamps is not.
     A reader must never have to infer liveness from PNG file mtimes alone,
     because a dedupe streak or a quota stop can legitimately produce long
     stretches with no new PNG.
  2. `ImageGrab.grab()` can return `None` or raise, and Genshin runs
     fullscreen exclusive on some display modes, which is exactly the
     condition most likely to make a grab fail. A failed grab is caught,
     logged as `kind="grab-failed"`, and the loop continues rather than
     dying. A daemon that exits on the first bad grab defeats the entire
     point of running it unattended through a launch nobody can redo.

DEDUPE VS QUOTA VS KEEPALIVE, AND WHY ALL THREE ARE SEPARATE COUNTERS. Genshin
sits on a static loading screen or a static menu for long stretches, and
writing a fresh multi-megabyte PNG every `--interval` seconds during those
stretches would burn disk for no informational gain. So frames within a small
perceptual-hash distance of the last WRITTEN frame are skipped (dedupe), but:

  - `--keepalive-every` forces a write on a fixed tick cadence regardless of
    dedupe, so a reader can always find a frame within N ticks of "now" and
    confirm the daemon was not just alive but actually still grabbing usable
    pixels, not stuck returning the same cached frame object.
  - `--max-bytes-total` stops writing NEW png bytes once the capture root
    would exceed the cap, because a first-run session can run for hours and
    an unbounded PNG stream is how a scratch capture daemon fills a disk that
    the rest of the machine needs. The index keeps recording after the cap is
    hit (`kind="quota-reached"` once, then `kind="quota-skipped"` per tick),
    because going silent at the cap would reintroduce trap #1 above.

WHY PHASH IS COMPUTED WITH NUMPY AND NOT A LIBRARY. `imagehash` is not in this
machine's dependency set and this repository does not add dependencies for a
tools/ script. The hash here is the standard "mean hash": downsample to 8x8
grayscale, threshold every pixel against the block's own mean, and pack the 64
bits into an int. It is coarser than a DCT-based phash but it is exactly the
right sensitivity for this job - a static Genshin menu with a blinking cursor
or a slowly animating background should dedupe, and a scene change should not.

NOT A FILESYSTEM OR REGISTRY WATCHER. That is `tools/first_run_capture.py`.
NOT A WISH-HISTORY TOOL. That is `tools/wish_authkey.py`. This module only
grabs the primary screen, hashes it, and writes PNGs plus one JSON line per
tick to an index. It has no opinion about what is on screen.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wintypes
import hashlib
import io
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Guarded third-party import. PIL is the only third-party package this tool
# needs to do anything at all (grab a frame), so a missing dependency is a
# hard stop with a message that says exactly what to install - never a bare
# ImportError traceback, per the repository's "no raw error string reaches a
# user-facing surface" rule, which extends here to "no raw traceback reaches
# an operator running a CLI tool by hand".
# ---------------------------------------------------------------------------

try:
    from PIL import Image, ImageGrab
except ImportError as exc:  # pragma: no cover - depends on local environment
    raise SystemExit(
        "tools/screen_capture.py requires Pillow (PIL) for screen capture. "
        f"Install it with 'pip install pillow'. Import error: {exc}"
    ) from exc

# psutil is used only to answer "is the Genshin process running" for the
# index line. It is optional at import time - a missing psutil degrades that
# one field to False rather than crashing the whole daemon, because a screen
# capture daemon should keep capturing screens even if process detection is
# unavailable.
try:
    import psutil
except ImportError:  # pragma: no cover - depends on local environment
    # No `type: ignore` here, and that is measured rather than assumed.
    # `ignore_missing_imports = True` in mypy.ini makes psutil resolve to Any,
    # so the rebind is not an error and an ignore comment would be flagged as
    # unused under `warn_unused_ignores = True`.
    psutil = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ROOT = Path("C:/rsc-first-run")
DEFAULT_INTERVAL_S = 3.0
DEFAULT_DEDUPE_THRESHOLD = 3
DEFAULT_KEEPALIVE_EVERY = 100
DEFAULT_MAX_BYTES_TOTAL = 40 * 1024 * 1024 * 1024  # 40 GB

# Mirrors first_run_capture.py's GAME_PROCESS_NAMES. Duplicated rather than
# imported: this file is the sole owner of tools/screen_capture.py and must
# not create a coupling to a sibling tool's internals for one constant.
GAME_PROCESS_NAMES = {"GenshinImpact.exe", "YuanShen.exe", "launcher.exe"}

_user32 = ctypes.windll.user32 if sys.platform == "win32" else None
if _user32 is not None:
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat(timespec="microseconds")


def utc_day_stamp(ts: datetime) -> str:
    return ts.strftime("%Y%m%d")


def utc_time_stamp(ts: datetime) -> str:
    return ts.strftime("%H%M%S_%f")


def get_foreground_window_title() -> str:
    """Read the foreground window title via ctypes user32.

    No pywin32 dependency for this one call, per the requirement - ctypes
    against user32 is stdlib-adjacent (ctypes ships with CPython) and needs
    nothing installed. Returns "" on any non-Windows platform, on a null
    HWND (nothing is foreground, e.g. the desktop is locked) or on a zero
    length title, rather than raising - a title is cosmetic context for the
    index line, never something worth crashing the daemon over.
    """
    if _user32 is None:
        return ""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def is_genshin_running() -> bool:
    """Best-effort check whether a known Genshin process name is alive.

    Returns False (never raises) when psutil is unavailable or when process
    enumeration itself fails - the same fail-soft posture as the rest of this
    file. A False here is not proof the game is not running; it is only proof
    this check did not find it.
    """
    if psutil is None:
        return False
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in GAME_PROCESS_NAMES:
                return True
    except Exception:  # noqa: BLE001 - process enumeration must never crash the daemon
        return False
    return False


def compute_phash(img: Image.Image) -> int:
    """64-bit mean-hash perceptual hash, over 64 pixels and no array library.

    Downsample to 8x8 grayscale, threshold each pixel against the 8x8 block's
    own mean, pack the 64 booleans into an int MSB-first. See the module
    docstring for why mean-hash rather than a DCT-based phash was chosen here.

    THIS WAS NUMPY AND IS DELIBERATELY NOT ANY MORE. `tools/` is one of the
    `files=` roots in `mypy.ini`, and mypy follows a real import into numpy's
    shipped `__init__.pyi`, which uses a PEP 695 `type` statement that is a
    syntax error under the pinned `python_version = 3.11`. That single
    third-party stub error stops all further checking, so importing numpy from
    anywhere under a checked root silently turns the whole mypy gate off. The
    same trap is recorded in `mypy.ini` for a different entry path - a test
    directory - and the fix there was to stop checking the directory rather
    than to silence numpy. There is no directory to drop here, and sixty-four
    pixels do not need an array library, so the import goes instead.
    """
    small = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    mean = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | (1 if pixel > mean else 0)
    return value


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically: tmp file, then a same-dir replace.

    A PNG reader that opens this file mid-write would see a truncated, corrupt
    image; `Path.replace` is a single rename on the same filesystem, so a
    reader observes either the whole old state (nothing, here - the target is
    always new) or the whole new file, never a partial one. The tmp file is a
    sibling of the target for the same reason core/atomic_io.py gives: a temp
    file in a different directory can land on a different filesystem, where
    replace degrades to a copy and stops being atomic.
    """
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def append_index_line(index_path: Path, event: dict) -> None:
    """Append one JSON object as one line to the index.

    Deliberately a plain append with flush+fsync, not a tmp-then-replace - the
    index is an append-only log, not a state file that is read as a whole and
    could be observed half-written. The invariant that matters here is that a
    line, once written, is never rewritten in place; a crash can at worst cost
    the last unflushed line, never corrupt an earlier one.
    """
    line = json.dumps(event, ensure_ascii=True, sort_keys=True)
    with index_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_last_written_phash(index_path: Path) -> int | None:
    """Recover the last WRITTEN frame's phash by scanning the index.

    Lets the daemon resume dedupe correctly across a restart instead of
    treating the first post-restart frame as automatically novel. Only
    kind="frame" lines carry a written PNG, so duplicate-skipped and
    grab-failed lines are skipped while scanning backward.
    """
    if not index_path.exists():
        return None
    last: int | None = None
    with index_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("kind") == "frame" and isinstance(event.get("phash"), str):
                try:
                    last = int(event["phash"], 16)
                except ValueError:
                    continue
    return last


def dir_total_bytes(root: Path) -> int:
    """Sum the size of every regular file under `root`, ignoring .tmp files.

    Called once at startup so a restart resumes the quota with the real bytes
    already on disk rather than restarting the counter at zero and blowing
    past the operator's cap on the very next tick.
    """
    total = 0
    if not root.exists():
        return 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.name.endswith(".tmp"):
                total += path.stat().st_size
        except OSError:
            continue
    return total


# ---------------------------------------------------------------------------
# The tick
# ---------------------------------------------------------------------------


class DaemonState:
    """Mutable counters carried between ticks. Not persisted except via the
    index itself, which `load_last_written_phash` and `dir_total_bytes`
    reconstruct enough of on startup to behave correctly across a restart.
    """

    def __init__(self, last_phash: int | None, bytes_written_total: int) -> None:
        self.last_phash = last_phash
        self.bytes_written_total = bytes_written_total
        self.ticks_since_write = 0
        self.quota_reached_emitted = False
        self.frames_written = 0
        self.frames_skipped_dup = 0
        self.frames_grab_failed = 0
        self.frames_quota_skipped = 0


def run_tick(
    state: DaemonState,
    screens_dir: Path,
    index_path: Path,
    dedupe_threshold: int,
    keepalive_every: int,
    max_bytes_total: int,
) -> None:
    """Run exactly one capture tick: grab, hash, decide, write, index.

    Every code path through this function ends in exactly one call to
    `append_index_line` (or, on an unhandled exception, none - the caller in
    `run()` wraps this in a try/except per tick so one bad tick cannot end the
    whole session; see run()'s docstring).
    """
    ts = utc_now()
    ts_iso = ts.isoformat(timespec="microseconds")
    window_title = get_foreground_window_title()
    genshin_running = is_genshin_running()
    base_event: dict[str, Any] = {
        "ts": ts_iso,
        "window_title": window_title,
        "genshin_running": genshin_running,
    }

    try:
        img = ImageGrab.grab(all_screens=False)
    except Exception as exc:  # noqa: BLE001 - a failed grab must never end the session
        state.frames_grab_failed += 1
        append_index_line(index_path, {
            **base_event,
            "kind": "grab-failed",
            "error": str(exc)[:300],
        })
        return

    if img is None:
        state.frames_grab_failed += 1
        append_index_line(index_path, {
            **base_event,
            "kind": "grab-failed",
            "error": "ImageGrab.grab(all_screens=False) returned None",
        })
        return

    width, height = img.size
    phash = compute_phash(img)
    dist = None if state.last_phash is None else hamming_distance(phash, state.last_phash)

    state.ticks_since_write += 1
    forced_keepalive = state.ticks_since_write >= keepalive_every
    is_duplicate = (
        state.last_phash is not None
        and dist is not None
        and dist <= dedupe_threshold
        and not forced_keepalive
    )

    if is_duplicate:
        state.frames_skipped_dup += 1
        append_index_line(index_path, {
            **base_event,
            "kind": "duplicate-skipped",
            "width": width,
            "height": height,
            "phash": format(phash, "016x"),
            "hamming_distance_from_previous": dist,
            "dedupe_threshold": dedupe_threshold,
        })
        return

    if state.bytes_written_total >= max_bytes_total:
        if not state.quota_reached_emitted:
            state.quota_reached_emitted = True
            kind = "quota-reached"
        else:
            kind = "quota-skipped"
        state.frames_quota_skipped += 1
        append_index_line(index_path, {
            **base_event,
            "kind": kind,
            "width": width,
            "height": height,
            "phash": format(phash, "016x"),
            "hamming_distance_from_previous": dist,
            "bytes_written_total": state.bytes_written_total,
            "max_bytes_total": max_bytes_total,
        })
        return

    day_dir = screens_dir / utc_day_stamp(ts)
    day_dir.mkdir(parents=True, exist_ok=True)
    out_path = day_dir / (utc_time_stamp(ts) + ".png")
    png_bytes = image_to_png_bytes(img)
    sha256 = hashlib.sha256(png_bytes).hexdigest()
    atomic_write_bytes(out_path, png_bytes)

    state.bytes_written_total += len(png_bytes)
    state.ticks_since_write = 0
    state.last_phash = phash
    state.frames_written += 1

    append_index_line(index_path, {
        **base_event,
        "kind": "frame",
        "path": str(out_path),
        "sha256": sha256,
        "bytes": len(png_bytes),
        "width": width,
        "height": height,
        "phash": format(phash, "016x"),
        "hamming_distance_from_previous": dist,
        "forced_keepalive": forced_keepalive,
    })


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


def run(
    root: Path,
    interval: float,
    once: bool,
    dedupe_threshold: int,
    keepalive_every: int,
    max_bytes_total: int,
) -> int:
    """Run the capture loop. Never lets one bad tick end the session.

    A tick can fail for reasons `run_tick` does not itself guard - a full
    disk on the index append, a permissions error on the day directory, a
    Pillow internal error on an unusual frame. Per the module docstring's
    core trap, this daemon must never die silently, so every tick is wrapped
    here and a failure is logged to the index as kind="tick-error" rather
    than propagating out of the loop. `--once` still returns a non-zero-worthy
    signal only through the index; the process exit code stays 0 because a
    single tick error is not a reason to fail a scheduled run.
    """
    screens_dir = root / "screens"
    index_path = root / "screens_index.jsonl"
    root.mkdir(parents=True, exist_ok=True)
    screens_dir.mkdir(parents=True, exist_ok=True)

    last_phash = load_last_written_phash(index_path)
    bytes_written_total = dir_total_bytes(screens_dir)
    state = DaemonState(last_phash, bytes_written_total)

    append_index_line(index_path, {
        "ts": utc_now_iso(),
        "kind": "daemon-start",
        "pid": os.getpid(),
        "python": sys.version.split()[0],
        "interval_s": interval,
        "dedupe_threshold": dedupe_threshold,
        "keepalive_every": keepalive_every,
        "max_bytes_total": max_bytes_total,
        "resumed_bytes_written_total": bytes_written_total,
        "resumed_last_phash": None if last_phash is None else format(last_phash, "016x"),
        "window_title": get_foreground_window_title(),
        "genshin_running": is_genshin_running(),
    })

    tick = 0
    try:
        while True:
            tick += 1
            try:
                run_tick(
                    state, screens_dir, index_path,
                    dedupe_threshold, keepalive_every, max_bytes_total,
                )
            except Exception as exc:  # noqa: BLE001 - one bad tick must never end the daemon
                append_index_line(index_path, {
                    "ts": utc_now_iso(),
                    "kind": "tick-error",
                    "tick": tick,
                    "error": str(exc)[:300],
                })
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        append_index_line(index_path, {
            "ts": utc_now_iso(),
            "kind": "daemon-stop",
            "ticks": tick,
            "frames_written": state.frames_written,
            "frames_skipped_dup": state.frames_skipped_dup,
            "frames_grab_failed": state.frames_grab_failed,
            "frames_quota_skipped": state.frames_quota_skipped,
            "bytes_written_total": state.bytes_written_total,
        })
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="capture root; screens/ and screens_index.jsonl live here")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S,
                        help="seconds between capture ticks")
    parser.add_argument("--once", action="store_true",
                        help="run exactly one tick and exit, instead of looping")
    parser.add_argument("--dedupe-threshold", type=int, default=DEFAULT_DEDUPE_THRESHOLD,
                        help="max hamming distance from the last written frame "
                             "to be treated as a duplicate and skipped")
    parser.add_argument("--keepalive-every", type=int, default=DEFAULT_KEEPALIVE_EVERY,
                        help="force a write every N ticks regardless of dedupe")
    parser.add_argument("--max-bytes-total", type=int, default=DEFAULT_MAX_BYTES_TOTAL,
                        help="stop writing new PNGs once the capture root would "
                             "exceed this many bytes; the index keeps recording")
    args = parser.parse_args(argv)

    if args.dedupe_threshold < 0:
        parser.error("--dedupe-threshold must be >= 0")
    if args.keepalive_every < 1:
        parser.error("--keepalive-every must be >= 1")
    if args.max_bytes_total < 0:
        parser.error("--max-bytes-total must be >= 0")

    return run(
        args.root,
        args.interval,
        args.once,
        args.dedupe_threshold,
        args.keepalive_every,
        args.max_bytes_total,
    )


if __name__ == "__main__":
    raise SystemExit(main())
