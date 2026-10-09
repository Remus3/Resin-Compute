"""Archive finished FLEET-COMMON item-12 progress files; close a stale one.

MAIN 2246 ORDER section 2, PERF-AUDIT item 8. Two acts, both on the progress
directory of the MAIN checkout of `--root` (the kit's `main_checkout`, so a
run from a linked worktree reaches the directory the lane widget reads):

  archive (default)  every `<task>.json` whose `status` is `done` or `failed`
                     and whose `updated` is older than `--max-age-hours`
                     (default 24) MOVES into `progress/archive/`. A move,
                     never a delete; a name already in the archive gets a
                     numeric suffix rather than overwriting it.
  --close TASK       a `running` file is rewritten through the kit's
                     `fleet_headless.write_progress` with status `failed`
                     and step `closed stale`, keeping its `pct`. That also
                     gives it the kit's one `updated` format. A file that is
                     missing, unreadable or not `running` is left alone and
                     the exit code is 1.

Left in place, by design: running files, files whose `updated` is missing or
unparsable, unreadable JSON, and any non-`.json` name (a `.tmp` may be a
write in flight). An `updated` with no offset is read as local time, the
convention every naive writer on this host used. `--dry-run` lists what an
archive would move and moves nothing.

    python scripts/progress_archive.py [--root DIR] [--max-age-hours H] [--dry-run]
    python scripts/progress_archive.py --close TASK [--root DIR]
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")

ARCHIVE_DIR = "archive"
FINISHED = ("done", "failed")
DEFAULT_MAX_AGE_S = 24 * 3600
CLOSE_STEP = "closed stale"


def progress_dir(root: Path | str) -> Path:
    """The progress directory the kit writes for `root`."""
    return Path(kit.main_checkout(root)) / kit.PROGRESS_REL


def _read(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _parse(value: object) -> dt.datetime | None:
    """`updated` as an aware datetime; naive is local time; None if unparsable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        try:
            parsed = parsed.astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    return parsed


def _free_name(folder: Path, name: str) -> Path:
    target = folder / name
    stem, suffix = os.path.splitext(name)
    n = 1
    while target.exists():
        target = folder / f"{stem}.{n}{suffix}"
        n += 1
    return target


def archive(
    folder: Path,
    now: dt.datetime | None = None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    dry_run: bool = False,
) -> list[Path]:
    """Move every finished file older than `max_age_s` into `folder/archive`.

    Returns the ORIGINAL paths of the files moved (or, on a dry run, that
    would be moved)."""
    folder = Path(folder)
    current = now if now is not None else dt.datetime.now(dt.UTC)
    cutoff = current - dt.timedelta(seconds=max_age_s)
    picked: list[Path] = []
    try:
        entries = sorted(folder.iterdir())
    except OSError:
        return []
    for path in entries:
        if not path.is_file() or path.suffix != ".json":
            continue
        doc = _read(path)
        if doc is None or doc.get("status") not in FINISHED:
            continue
        stamp = _parse(doc.get("updated"))
        if stamp is None or stamp >= cutoff:
            continue
        picked.append(path)
    if dry_run or not picked:
        return picked
    dest = folder / ARCHIVE_DIR
    dest.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []
    for path in picked:
        try:
            os.replace(path, _free_name(dest, path.name))
        except OSError as exc:
            print(f"skip {path.name}: {exc.__class__.__name__}", file=sys.stderr)
            continue
        moved.append(path)
    return moved


def close(root: Path | str, task: str) -> dict | None:
    """Mark a stale `running` task `failed` / `closed stale` via the kit.

    None, with nothing written, when the file is missing, unreadable or not
    running."""
    path = progress_dir(root) / f"{task}.json"
    doc = _read(path) if path.is_file() else None
    if doc is None or doc.get("status") != "running":
        return None
    try:
        pct = int(doc.get("pct") or 0)
    except (TypeError, ValueError):
        pct = 0
    return dict(
        kit.write_progress(root, task, pct, CLOSE_STEP, 0, "failed", checklist=[])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_S / 3600)
    parser.add_argument("--close", metavar="TASK")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.close:
        try:
            done = close(args.root, args.close)
        except (OSError, ValueError) as exc:
            print(f"close {args.close}: {exc.__class__.__name__}", file=sys.stderr)
            return 1
        if done is None:
            print(f"close {args.close}: refused - missing, unreadable or not running")
            return 1
        print(f"closed {args.close}: failed / {CLOSE_STEP} at {done.get('updated')}")
        return 0
    folder = progress_dir(args.root)
    moved = archive(folder, max_age_s=args.max_age_hours * 3600, dry_run=args.dry_run)
    verb = "would move" if args.dry_run else "moved"
    for path in moved:
        print(f"{verb} {path.name} -> {ARCHIVE_DIR}/")
    print(f"{verb} {len(moved)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
