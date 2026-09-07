"""First-run provenance capture for Genshin Impact on this machine.

WHY THIS EXISTS. A Genshin account can only be created once, and several of the
artefacts it produces are OVERWRITTEN rather than appended:

  - `output_log.txt` is truncated at every launch. The previous generation
    survives one launch as `output_log_last.txt` and then is gone. The FIRST
    launch's log is the only place several one-time facts appear.
  - The Chromium cache under `GenshinImpact_Data/webCaches/<ver>/Cache/` is a
    ring buffer. The wish-history authkey URL lands there and is evicted.
  - `HKCU\\Software\\miHoYo\\Genshin Impact` is rewritten in place on exit.

So a snapshot taken after the session is not the same fact as a capture taken
DURING it. This module polls the write surfaces and content-addresses every
distinct generation of every file, so an overwrite adds a blob rather than
replacing one.

WHERE IT WRITES, AND WHY IT IS NOT THE REPO. The capture store lives OUTSIDE
this git tree. Genshin's own logs carry the account UID and the miHoYo registry
subtree carries a login token; neither belongs in a tracked file, and this
repository's licence posture forbids vendoring game data regardless. The repo
keeps the TOOL and a redacted manifest; the bytes stay on local disk.

NOT AN OCR TOOL AND NOT A SCREEN TOOL. Screen capture is `tools/screen_capture.py`.
Wish history is `tools/wish_authkey.py`. This module only watches the filesystem
and the registry.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wintypes
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Where things are
# ---------------------------------------------------------------------------

DEFAULT_CAPTURE_ROOT = Path("C:/rsc-first-run")

LOCALLOW = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow"
APPDATA_ROAMING = Path(os.environ.get("APPDATA", ""))
APPDATA_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
USERPROFILE = Path(os.environ.get("USERPROFILE", ""))

GAME_DIR = Path("C:/Program Files/HoYoPlay/games/Genshin Impact game")
LAUNCHER_DIR = Path("C:/Program Files/HoYoPlay")

# Directory roots polled recursively. Each entry is (label, path, max_bytes).
# max_bytes guards against hoovering up a multi-gigabyte asset blob if a root is
# mis-specified; a file larger than the cap is RECORDED as skipped rather than
# silently ignored, because a silent skip and a clean sweep look identical.
WATCH_TREES: list[tuple[str, Path, int]] = [
    ("locallow-mihoyo", LOCALLOW / "miHoYo", 256 * 1024 * 1024),
    ("locallow-cognosphere", LOCALLOW / "Cognosphere", 64 * 1024 * 1024),
    ("roaming-cognosphere", APPDATA_ROAMING / "Cognosphere", 64 * 1024 * 1024),
    ("roaming-mihoyo", APPDATA_ROAMING / "miHoYo", 64 * 1024 * 1024),
    ("local-hoyoplay", APPDATA_LOCAL / "HoYoPlay", 64 * 1024 * 1024),
    ("game-screenshots", GAME_DIR / "ScreenShot", 64 * 1024 * 1024),
    ("user-screenshots", USERPROFILE / "Pictures" / "Genshin Impact", 64 * 1024 * 1024),
]

# Individual files polled by exact path.
WATCH_FILES: list[tuple[str, Path]] = [
    ("game-config", GAME_DIR / "config.ini"),
    ("game-pkg-version", GAME_DIR / "pkg_version"),
    ("game-audio-pkg-version", GAME_DIR / "Audio_English(US)_pkg_version"),
    ("launcher-config", LAUNCHER_DIR / "config.ini"),
]

# Registry subtrees exported to .reg text on a slower cadence.
WATCH_REGISTRY: list[tuple[str, str]] = [
    ("reg-mihoyo", r"HKCU\Software\miHoYo"),
    ("reg-cognosphere", r"HKCU\Software\Cognosphere"),
    ("reg-hoyoverse", r"HKCU\Software\HoYoverse"),
]

GAME_PROCESS_NAMES = {"GenshinImpact.exe", "YuanShen.exe", "launcher.exe"}


# ---------------------------------------------------------------------------
# Reading a file the game currently holds open
# ---------------------------------------------------------------------------

_GENERIC_READ = 0x80000000
_FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004  # read | write | delete
_OPEN_EXISTING = 3
_INVALID_HANDLE = ctypes.c_void_p(-1).value


def read_bytes_shared(path: Path) -> bytes | None:
    """Read a file even while another process holds a write handle to it.

    Unity writes `output_log.txt` with a handle that permits shared reads, so
    plain `open()` usually succeeds. It does NOT always: the launcher and the
    anti-cheat driver both touch files here with narrower sharing. Falling back
    to CreateFileW with FILE_SHARE_DELETE set is what makes the read survive a
    concurrent rotation, and a rotation is exactly the moment worth capturing.

    Returns None when the file cannot be read at all, so the caller can record
    an explicit unreadable event rather than treat it as absent.
    """
    try:
        return path.read_bytes()
    except (PermissionError, OSError):
        pass

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    handle = kernel32.CreateFileW(
        str(path), _GENERIC_READ, _FILE_SHARE_ALL, None, _OPEN_EXISTING, 0, None
    )
    if handle == _INVALID_HANDLE or handle is None:
        return None
    try:
        fd = -1
        try:
            fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_BINARY", 0))
            return os.read(fd, 1 << 30)
        except OSError:
            return None
        finally:
            if fd >= 0:
                os.close(fd)
    finally:
        kernel32.CloseHandle(handle)


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class CaptureStore:
    """Content-addressed blob store plus an append-only event log.

    A file that is overwritten produces a SECOND blob and a second event; the
    first is never replaced. That is the whole point of the design, and it is
    why the store is addressed by sha256 rather than by path.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.blobs = root / "blobs"
        self.events_path = root / "events.jsonl"
        self.manifest_path = root / "manifest.json"
        self.blobs.mkdir(parents=True, exist_ok=True)
        # path -> sha256 of the generation most recently recorded
        self.seen: dict[str, str] = {}
        self._load_seen()

    def _load_seen(self) -> None:
        if not self.events_path.exists():
            return
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("kind") == "content" and event.get("sha256"):
                    self.seen[event["path"]] = event["sha256"]

    def emit(self, event: dict) -> None:
        event.setdefault("ts", utc_now())
        line = json.dumps(event, ensure_ascii=True, sort_keys=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def offer(self, label: str, key: str, data: bytes, meta: dict | None = None) -> bool:
        """Record `data` under logical `key`. Returns True when it was new."""
        digest = hashlib.sha256(data).hexdigest()
        if self.seen.get(key) == digest:
            return False
        blob = self.blobs / digest[:2] / digest
        if not blob.exists():
            blob.parent.mkdir(parents=True, exist_ok=True)
            tmp = blob.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(blob)
        previous = self.seen.get(key)
        self.seen[key] = digest
        event = {
            "kind": "content",
            "label": label,
            "path": key,
            "sha256": digest,
            "bytes": len(data),
            "previous_sha256": previous,
            "generation": 1 if previous is None else 2,
        }
        if meta:
            event.update(meta)
        self.emit(event)
        return True


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------


def poll_tree(store: CaptureStore, label: str, root: Path, max_bytes: int) -> int:
    if not root.exists():
        return 0
    new = 0
    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            size = path.stat().st_size
        except OSError:
            continue
        key = str(path)
        if size > max_bytes:
            if store.seen.get(key) != "OVERSIZE":
                store.seen[key] = "OVERSIZE"
                store.emit({"kind": "skipped-oversize", "label": label,
                            "path": key, "bytes": size, "cap": max_bytes})
            continue
        data = read_bytes_shared(path)
        if data is None:
            if store.seen.get(key) != "UNREADABLE":
                store.seen[key] = "UNREADABLE"
                store.emit({"kind": "unreadable", "label": label, "path": key})
            continue
        if store.offer(label, key, data):
            new += 1
    return new


def poll_files(store: CaptureStore) -> int:
    new = 0
    for label, path in WATCH_FILES:
        if not path.exists():
            continue
        data = read_bytes_shared(path)
        if data is None:
            continue
        if store.offer(label, str(path), data):
            new += 1
    return new


def poll_registry(store: CaptureStore) -> int:
    new = 0
    for label, key in WATCH_REGISTRY:
        try:
            proc = subprocess.run(
                ["reg", "query", key, "/s"],
                capture_output=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        if store.offer(label, "registry:" + key, proc.stdout):
            new += 1
    return new


def poll_processes(store: CaptureStore) -> None:
    """Record when the game process appears and disappears.

    An arrival timestamp is what lets a later reader align a screenshot index,
    an OBS recording and a log generation onto one timeline. Without it the
    three are three separate clocks.
    """
    try:
        import psutil
    except ImportError:
        return
    running = set()
    for proc in psutil.process_iter(["name", "pid", "create_time"]):
        try:
            name = proc.info.get("name")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in GAME_PROCESS_NAMES:
            running.add((name, proc.info.get("pid"), proc.info.get("create_time")))
    key = "process:genshin"
    payload = json.dumps(sorted(str(item) for item in running)).encode("ascii")
    store.offer("process", key, payload, {"running": sorted(str(i) for i in running)})


def write_manifest(store: CaptureStore, started: str) -> None:
    counts: dict[str, int] = {}
    total = 0
    for blob in store.blobs.rglob("*"):
        if blob.is_file() and not blob.name.endswith(".tmp"):
            total += 1
    for _key, digest in store.seen.items():
        bucket = "special" if digest in {"OVERSIZE", "UNREADABLE"} else "content"
        counts[bucket] = counts.get(bucket, 0) + 1
    manifest = {
        "generated": utc_now(),
        "started": started,
        "capture_root": str(store.root),
        "distinct_blobs": total,
        "tracked_paths": len(store.seen),
        "path_states": counts,
        "watch_trees": [str(p) for _, p, _ in WATCH_TREES],
        "watch_files": [str(p) for _, p in WATCH_FILES],
        "watch_registry": [k for _, k in WATCH_REGISTRY],
    }
    tmp = store.manifest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(store.manifest_path)


def run(root: Path, interval: float, registry_every: int, once: bool) -> int:
    store = CaptureStore(root)
    started = utc_now()
    store.emit({"kind": "daemon-start", "interval_s": interval,
                "pid": os.getpid(), "python": sys.version.split()[0]})
    tick = 0
    try:
        while True:
            tick += 1
            new = 0
            for label, path, cap in WATCH_TREES:
                new += poll_tree(store, label, path, cap)
            new += poll_files(store)
            poll_processes(store)
            if tick % registry_every == 1:
                new += poll_registry(store)
            if new or tick % 30 == 1:
                write_manifest(store, started)
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        write_manifest(store, started)
        store.emit({"kind": "daemon-stop", "ticks": tick})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--registry-every", type=int, default=15,
                        help="poll the registry once every N ticks")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    args.root.mkdir(parents=True, exist_ok=True)
    return run(args.root, args.interval, args.registry_every, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
