"""Read-only session-start probe of the roots map's MAIN row (ADR-013 interim d).

`docs/adr/ADR-013-roots-map-identity-anchor.md` names the risk: both MAIN
provenance checks locate MAIN's outbox through ONE row of the per-host,
gitignored roots map, so a wrong row passes both. Until the beacon design (a2)
is accepted, the interim control is this probe: at session start it reports

- whether the outbox the MAIN row resolves to exists,
- how many entries that outbox holds (notes and bundle directories),
- the newest entry's filename, by mtime (FLEET-COMMON item 7: never by stamp),
- the sha256 of the roots map file's bytes,

and compares each with the previous session's reading, printing one DRIFT
line per field that moved. A human reads the drift; the probe decides nothing.

THE MAP IS LOCATED THE RESPONDER'S WAY, NEVER RESTATED. `load_roots`,
`DEFAULT_ROOTS_CONFIG`, `MAIN_CODE` and the inbox/outbox dirnames are imported
from `tools/moon_sync_responder.py`, and the outbox is derived exactly as
`main_provenance` derives it, so the probe watches the row the responder trusts.
The map and the baseline are anchored on the MAIN checkout, found through the
git common dir, so a run from a linked worktree reads the same map (slice N4).
A linked-worktree run is READ-ONLY: it compares against the main checkout's
baseline and prints DRIFT but stores nothing, so it never consumes drift the
operator's main session should see. A failed resolution prints one stderr line
saying it fell back to the invoking checkout.

NO IDENTITY IN OUTPUT OR STATE. No line and no persisted field names a
directory path, an account id or an email: the row's VALUE is never printed,
only facts about what it points at. A newest filename that looks like a path,
an account path or an email is printed as `(withheld)`.

READ-ONLY on everything except its own state file, written through
`core/atomic_io.py` under the gitignored ops/loop/control/ directory. One
scoped exception, measured 2026-10-14: importing `core/atomic_io.py` runs
`core/log_setup.py`, which opens the tree's shared day log under the
gitignored logs/ directory (creating it if absent), as every tool here does.
The probe itself logs nothing on any path it handles.

EXIT CODE: 0 always, including a missing or unreadable map; 2 only for invalid
arguments (argparse). Decision recorded (slice D, session 73): this is a
REPORTER, not a gate. A nonzero exit on drift would turn a legitimate MAIN
re-root or a new outbox note - both expected drift - into a red session start,
and the control ADR-013 describes is a human comparing by eye. Reversed by: an
accepted ADR-013 a2, whose tick-time beacon check is the gate.

Usage:
    python tools/roots_map_probe.py
    python tools/roots_map_probe.py --config <map> --baseline <baseline file>  # tests
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

# Run as `python tools/roots_map_probe.py`, sys.path[0] is tools/ and the
# package imports below would fail; see tools/check_handoff.py for the same
# bootstrap and why the import is by importlib (mypy "found twice").
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_responder: Any = importlib.import_module("tools.moon_sync_responder")
_atomic: Any = importlib.import_module("core.atomic_io")

#: The roots map and the baseline, relative to a checkout root. The map's
#: relative path is the responder's own, never restated.
_CONFIG_REL: Path = _responder.DEFAULT_ROOTS_CONFIG.relative_to(_responder.REPO_ROOT)
_BASELINE_REL = Path("ops") / "loop" / "control" / "roots_map_probe.json"


def main_checkout(repo: Path) -> Path:
    """The MAIN checkout for `repo`, even when `repo` is a linked worktree.

    Slice N4: both files are gitignored and live only in the MAIN checkout, so
    a worktree copy anchored on its own file printed "map not present" (a false
    negative). The main checkout is the parent of `git rev-parse
    --git-common-dir`. GIT_* variables are dropped so an inherited GIT_DIR
    (a hook, a wrapper) cannot redirect the answer. Anything that is not a git
    work tree, or any git failure, answers `repo` itself.
    """
    repo = Path(repo).resolve()
    found = _resolve_main(repo)
    return repo if found is None else found


def _resolve_main(repo: Path) -> Path | None:
    """The main checkout via the git common dir, or None when that fails
    (not a work tree, no git, git < 2.31 rejecting --path-format, a bare or
    separate-git-dir layout with no main work tree to name)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo, capture_output=True, text=True, timeout=30, check=False, env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    common = proc.stdout.strip()
    if proc.returncode != 0 or not common:
        return None
    common_dir = Path(common)
    if common_dir.name != ".git":
        return None
    return common_dir.parent.resolve()


def default_config(repo: Path) -> Path:
    return main_checkout(repo) / _CONFIG_REL


def default_baseline(repo: Path) -> Path:
    return main_checkout(repo) / _BASELINE_REL

PREFIX = "roots_map_probe:"

#: Fields compared between readings, in print order.
FIELDS = ("map_present", "main_row", "outbox_exists", "outbox_entries", "newest", "map_sha256")

_ACCOUNT_PATH = re.compile(
    r"(?:[A-Za-z]:\\Users\\[^\\\s]+)|(?:/home/[^/\s]+)|(?:/Users/[^/\s]+)",
)
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_name(name: str) -> str:
    """A filename fit to print, or `(withheld)`."""
    if not _SAFE_NAME.match(name) or "@" in name or _ACCOUNT_PATH.search(name):
        return "(withheld)"
    return name


def read_map(config: Path) -> dict[str, Any]:
    """One reading. Every value is a bool, an int, a hex digest or a safe name."""
    reading: dict[str, Any] = dict.fromkeys(FIELDS)
    try:
        raw = config.read_bytes()
    except FileNotFoundError:
        reading["map_present"] = False
        return reading
    except OSError:
        reading["map_present"] = True
        reading["note"] = "map not readable"
        return reading
    reading["map_present"] = True
    reading["map_sha256"] = hashlib.sha256(raw).hexdigest()
    # Parsed HERE first: `load_roots` goes through `read_json`, which logs the
    # raw parse error - with the map's path - to the console. A probe output
    # line must carry neither, so a map that does not parse never reaches it.
    try:
        json.loads(raw.decode("utf-8"))
    except ValueError:
        reading["note"] = "map not readable"
        reading["main_row"] = False
        return reading
    root = _responder.load_roots(config).get(_responder.MAIN_CODE)
    reading["main_row"] = root is not None
    if root is None:
        return reading
    outbox = (root / _responder.INBOX_DIRNAME).parent / _responder.OUTBOX_DIRNAME
    try:
        entries = list(outbox.iterdir())
    except OSError:
        reading["outbox_exists"] = False
        return reading
    reading["outbox_exists"] = True
    reading["outbox_entries"] = len(entries)
    newest: tuple[float, str] | None = None
    for entry in entries:
        try:
            stamp = entry.stat().st_mtime
        except OSError:
            continue
        if newest is None or (stamp, entry.name) > newest:
            newest = (stamp, entry.name)
    reading["newest"] = None if newest is None else _safe_name(newest[1])
    return reading


def _show(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def describe(reading: dict[str, Any]) -> list[str]:
    if not reading["map_present"]:
        return [f"{PREFIX} map not present on this host (nothing to check)"]
    lines: list[str] = []
    if reading.get("note"):
        lines.append(f"{PREFIX} {reading['note']} - treated as having no MAIN row")
    elif not reading["main_row"]:
        lines.append(f"{PREFIX} map present but has no MAIN row")
    lines.append(
        f"{PREFIX} outbox_exists={_show(reading['outbox_exists'])}"
        f" outbox_entries={_show(reading['outbox_entries'])}"
        f" newest={_show(reading['newest'])}"
        f" map_sha256={_show(reading['map_sha256'])}"
    )
    return lines


def compare(
    previous: dict[str, Any] | None, current: dict[str, Any], *, stores: bool = True
) -> list[str]:
    """One DRIFT line per field that moved since `previous`, else one quiet line.

    Every compared value is a bool, an int, a digest or a safe filename, so a
    DRIFT line can show both sides without naming a path. `stores` is False on
    a read-only run, which must never claim the reading becomes the baseline
    (session 74 residue N5(a): it printed "stored" then "not updated").
    """
    if previous is None:
        if not stores:
            return [f"{PREFIX} no previous reading"]
        return [f"{PREFIX} no previous reading; this one is stored as the baseline"]
    drift = [
        f"{PREFIX} DRIFT {field} {_show(previous.get(field))} -> {_show(current.get(field))}"
        for field in FIELDS
        if previous.get(field) != current.get(field)
    ]
    return drift or [f"{PREFIX} no drift since previous reading"]


def _load_previous(state: Path) -> dict[str, Any] | None:
    # Not `read_json`: a corrupt state file must not log a raw error with a
    # path to the console. A corrupt or missing baseline is simply no baseline.
    try:
        payload = json.loads(state.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    prior = payload.get("reading")
    return prior if isinstance(prior, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only roots-map MAIN-row probe (ADR-013 d).")
    parser.add_argument("--config", type=Path, default=None, help="roots map file")
    parser.add_argument("--baseline", type=Path, default=None, help="stored previous reading")
    args = parser.parse_args(argv)
    # Resolved here, not at import: REPO may be a linked worktree (slice N4).
    here = Path(REPO).resolve()
    resolved = _resolve_main(here)
    if resolved is None:
        print(f"{PREFIX} git common dir not resolved; fell back to this checkout", file=sys.stderr)
        resolved = here
    # Merger ruling, N4 refute round 1: drift belongs to the operator's main
    # session. From a linked worktree the probe compares against the MAIN
    # baseline and prints DRIFT, but stores nothing, so it never consumes it.
    # An explicit --baseline is the caller's own file and is written as before.
    read_only = resolved != here and args.baseline is None
    if args.config is None:
        args.config = resolved / _CONFIG_REL
    if args.baseline is None:
        args.baseline = resolved / _BASELINE_REL
    try:
        current = read_map(args.config)
    except Exception:  # noqa: BLE001 - a reporter never surfaces a raw error
        print(f"{PREFIX} the map could not be probed this session (no detail shown)")
        return 0
    lines = describe(current)
    lines += compare(_load_previous(args.baseline), current, stores=not read_only)
    stored = {k: current.get(k) for k in FIELDS}
    if read_only:
        lines.append(f"{PREFIX} linked worktree: read-only, baseline not updated")
    elif not _atomic.atomic_write_json(args.baseline, {"schema": 1, "reading": stored}):
        lines.append(f"{PREFIX} this reading could not be stored; next session sees no baseline")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
