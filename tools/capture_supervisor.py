"""Keeps the first-run capture lane alive, and says so in a file rather than a window.

WHY THIS EXISTS. Three independent processes carry the first-run capture: the
filesystem and registry watcher (`tools/first_run_capture.py`), the screenshot
daemon (`tools/screen_capture.py`) and an ffmpeg screen recorder. A first run of
Genshin Impact happens exactly once, so any one of the three dying quietly is an
unrecoverable hole rather than an inconvenience, and the failure is invisible:
a dead daemon and an idle daemon produce the same thing, which is no new files.

THE TWO THINGS IT ACTUALLY CHECKS, AND WHY BOTH ARE NEEDED. Liveness alone is
not enough. A process can be running and capturing nothing useful:

  - ffmpeg keeps writing frames when the desktop composition path has handed it
    a blank surface, which is what happens when a Direct3D title takes exclusive
    fullscreen. The segment grows, the process is healthy, and every frame is a
    flat colour. So this module measures CONTENT, not just process presence,
    by reading the newest screenshot the screen daemon wrote and reporting its
    mean and standard deviation. A standard deviation at or near zero is a flat
    frame, and that is the alarm.
  - The screen daemon dedupes identical frames on purpose, so "no new PNG" is a
    legitimate steady state. Its index still gets a line per tick, so FRESHNESS
    is measured against the index rather than against the PNG directory.

WHAT IT DELIBERATELY DOES NOT DO. It does not restart ffmpeg into the same
segment file, and it does not try to repair a truncated recording. A segment
that was being written when its writer died is the recorder's problem, which is
why the recorder writes Matroska: an mp4 keeps its index in a trailing atom and
is unplayable until the muxer closes it, while a Matroska file that stops
mid-stream is still readable up to the last complete cluster. That choice was
measured on 2026-09-07 - an in-progress mp4 segment failed to open with
"moov atom not found" while an in-progress mkv segment decoded to the second.

IT REPORTS, IT DOES NOT SPEAK. Health goes to `<root>/capture_health.json`,
rewritten atomically each pass, because the operator is inside a game and the
chat surface belongs to them. A supervisor that narrates is a supervisor that
interrupts.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FILE_DAEMON = "first_run_capture.py"
SCREEN_DAEMON = "screen_capture.py"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def find_python_daemon(script: str) -> list[int]:
    """PIDs of python processes whose FIRST ARGUMENT is `script`.

    Matching on the whole joined command line was tried first and is wrong in a
    way that is easy to miss: a probe process whose own source text mentions two
    daemon names matches both, and on 2026-09-07 that mis-identification led to
    every real watcher being killed as a duplicate while the probe survived.
    Matching argv[1] only is what makes the answer about the daemon rather than
    about whatever happens to be quoting its name.
    """
    try:
        import psutil
    except ImportError:
        return []
    pids: list[int] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            argv = proc.info.get("cmdline") or []
            name = (proc.info.get("name") or "").lower()
        except Exception:  # noqa: BLE001 - enumeration must not kill the supervisor
            continue
        if name != "python.exe" or len(argv) < 2:
            continue
        if argv[1].replace("\\", "/").endswith(script):
            pids.append(proc.info["pid"])
    return pids


def find_ffmpeg() -> list[int]:
    try:
        import psutil
    except ImportError:
        return []
    out: list[int] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if (proc.info.get("name") or "").lower() != "ffmpeg.exe":
                continue
            argv = " ".join(proc.info.get("cmdline") or [])
        except Exception:  # noqa: BLE001 - enumeration must not kill the supervisor
            continue
        if "gdigrab" in argv:
            out.append(proc.info["pid"])
    return out


def spawn_detached(argv: list[str], cwd: Path, log: Path) -> int:
    """Start a process that outlives this supervisor, appending to `log`."""
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = log.open("ab")
    # getattr and not attribute access, and that is a type-checker fix rather
    # than a runtime one. `hasattr` guards the interpreter but does NOT narrow
    # for mypy, and both constants are Windows-only in typeshed, so a bare
    # `subprocess.DETACHED_PROCESS` is an error when mypy runs on Linux. CI runs
    # Linux. Measured 2026-09-07.
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    proc = subprocess.Popen(
        argv, cwd=str(cwd), stdout=handle, stderr=handle,
        stdin=subprocess.DEVNULL, creationflags=flags,
    )
    return proc.pid


def newest_frame(root: Path) -> tuple[Path | None, dict | None, str | None]:
    """The most recent `kind == frame` line in the screen index, and its file."""
    index = root / "screens_index.jsonl"
    if not index.exists():
        return None, None, "no screens_index.jsonl"
    last_frame: dict | None = None
    last_ts: str | None = None
    with index.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("ts"):
                last_ts = event["ts"]
            if event.get("kind") == "frame":
                last_frame = event
    if last_frame is None:
        return None, None, "index has no frame line yet"
    return Path(last_frame["path"]), last_frame, last_ts


def measure_flatness(png: Path) -> dict:
    """Mean and population standard deviation of a downsampled grayscale frame.

    Downsampled to 64x36 first, deliberately. A full 2560x1440 statistic is the
    same answer at roughly two thousand times the cost, and this runs on a loop
    beside a game that wants the CPU.
    """
    try:
        from PIL import Image
    except ImportError:
        return {"error": "pillow-missing"}
    try:
        img = Image.open(png).convert("L").resize((64, 36))
        # Pillow 12 deprecates Image.getdata in favour of get_flattened_data and
        # removes it in Pillow 14. Probe for the new name rather than pinning a
        # version, so this keeps working on both sides of that removal.
        reader = getattr(img, "get_flattened_data", None) or img.getdata
        pixels = list(reader())
    except OSError as exc:
        return {"error": f"unreadable: {exc.__class__.__name__}"}
    count = len(pixels)
    mean = sum(pixels) / count
    variance = sum((p - mean) ** 2 for p in pixels) / count
    return {"mean": round(mean, 2), "stdev": round(variance ** 0.5, 2), "pixels": count}


def newest_video(root: Path) -> dict:
    video_dir = root / "video"
    if not video_dir.is_dir():
        return {"present": False}
    segments = sorted(video_dir.glob("*.mkv"), key=lambda p: p.stat().st_mtime)
    if not segments:
        return {"present": False}
    newest = segments[-1]
    stat = newest.stat()
    return {
        "present": True,
        "path": str(newest),
        "bytes": stat.st_size,
        "age_s": round(time.time() - stat.st_mtime, 1),
        "segments": len(segments),
    }


def genshin_running() -> bool:
    # No psutil import here on purpose: proc_iter_names() owns the guarded
    # import and returns an empty list when psutil is missing, so a second
    # guard would be dead code that ruff flags as an unused import.
    for proc in proc_iter_names():
        if proc in {"GenshinImpact.exe", "YuanShen.exe"}:
            return True
    return False


def proc_iter_names() -> list[str]:
    try:
        import psutil
    except ImportError:
        return []
    names: list[str] = []
    for proc in psutil.process_iter(["name"]):
        try:
            names.append(proc.info.get("name") or "")
        except Exception:  # noqa: BLE001 - enumeration must not kill the supervisor
            continue
    return names


def write_health(root: Path, payload: dict) -> None:
    target = root / "capture_health.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(target)


def one_pass(root: Path, restart: bool, restarts: dict[str, int]) -> dict:
    file_pids = find_python_daemon(FILE_DAEMON)
    screen_pids = find_python_daemon(SCREEN_DAEMON)
    ffmpeg_pids = find_ffmpeg()

    if restart and not file_pids:
        pid = spawn_detached(
            [sys.executable, "tools/first_run_capture.py", "--root", str(root),
             "--interval", "2"],
            REPO_ROOT, root / "daemon_stdout.log",
        )
        restarts["file"] = restarts.get("file", 0) + 1
        file_pids = [pid]
    if restart and not screen_pids:
        pid = spawn_detached(
            [sys.executable, "tools/screen_capture.py", "--root", str(root),
             "--interval", "4", "--dedupe-threshold", "3",
             "--keepalive-every", "60"],
            REPO_ROOT, root / "screen_stdout.log",
        )
        restarts["screen"] = restarts.get("screen", 0) + 1
        screen_pids = [pid]

    png, frame, last_index_ts = newest_frame(root)
    flatness: dict = {}
    if png is not None and png.exists():
        flatness = measure_flatness(png)

    alarms: list[str] = []
    if not file_pids:
        alarms.append("file-daemon-down")
    if not screen_pids:
        alarms.append("screen-daemon-down")
    if not ffmpeg_pids:
        alarms.append("ffmpeg-down")
    if len(file_pids) > 1:
        alarms.append(f"file-daemon-duplicated x{len(file_pids)}")
    if len(screen_pids) > 1:
        alarms.append(f"screen-daemon-duplicated x{len(screen_pids)}")
    if flatness.get("stdev") is not None and flatness["stdev"] < 3.0:
        alarms.append("flat-frame-capture-may-be-blank")
    video = newest_video(root)
    if video.get("present") and video.get("age_s", 0) > 30:
        alarms.append("video-segment-stale")
    if not video.get("present"):
        alarms.append("no-video-segment")

    return {
        "ts": utc_now(),
        "supervisor_pid": os.getpid(),
        "genshin_running": genshin_running(),
        "file_daemon_pids": file_pids,
        "screen_daemon_pids": screen_pids,
        "ffmpeg_pids": ffmpeg_pids,
        "restarts": dict(restarts),
        "newest_frame": frame.get("path") if frame else None,
        "newest_frame_ts": frame.get("ts") if frame else None,
        "newest_frame_window": frame.get("window_title") if frame else None,
        "last_index_ts": last_index_ts,
        "frame_flatness": flatness,
        "video": video,
        "alarms": alarms,
        "healthy": not alarms,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("C:/rsc-first-run"))
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-restart", action="store_true",
                        help="report only, never spawn a replacement")
    args = parser.parse_args(argv)
    args.root.mkdir(parents=True, exist_ok=True)
    restarts: dict[str, int] = {}
    while True:
        payload = one_pass(args.root, not args.no_restart, restarts)
        write_health(args.root, payload)
        if args.once:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
            return 0 if payload["healthy"] else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
