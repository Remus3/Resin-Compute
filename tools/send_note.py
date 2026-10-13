"""The ATTENDED outbound-note send path, and the audit that keeps the ledger whole.

WHY THIS EXISTS (hand-off 0q, session 70). FLEET-COMMON item 14c caps this
tree at 6 outbound notes a local day, counted by the kit's `OutboundCap` from
`ops/loop/control/outbound_notes.jsonl`. Before this module the only writers
of that ledger were the responder's two `cap.record` calls
(`tools/moon_sync_responder.py`, `_send_batch` and `_record_work_reply`). An
attended session sent a note by writing the file into the recipient's inbox
and its own by hand, so the ledger row was a remembered manual step - and on
2026-10-12 it was skipped for both notes sent (the 0900 ANSWER and the 1258
INFORMATION to MAIN), leaving the cap undercounted.

    python tools/send_note.py send <draft.md>
        Cap check (exempt ORDER / FIX / RULING always pass), deliver to the
        recipient's inbox and this tree's own, never overwriting a name,
        re-hash every copy, THEN write the row. Prints one JSON result line.
        Exit 0 sent and recorded, 1 refused (nothing delivered, no row).

    python tools/send_note.py audit [--day YYYY-MM-DD] [--apply]
        Every own-sent note (`<stamp>-from-RSC-<CLASS>-to-<CODE>-...md`) in
        this tree's inbox with no ledger row, whatever path sent it, printed
        as the exact JSON row to append (ts and day from the copy's mtime).
        Exit 1 while any is missing; `--apply` appends them (idempotent).

Responder auto-replies (`-from-RSC-auto-reply-to-...`) are not matched: the
responder records those itself under `reply-to-<note>`.

Paths default to the MAIN checkout (the kit's `main_checkout`), so a linked
worktree reads and writes the live inbox and ledger, never a worktree copy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.atomic_io import atomic_write_text, read_json  # noqa: E402

#: The vendored kit, loaded by importlib and typed Any (same as the responder).
inbox_kit: Any = importlib.import_module("ops.fleet_kit.fleet_inbox")
headless_kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")

SELF_CODE = "RSC"
INBOX_DIRNAME = "moon_sync_inbox"
ROOTS_REL = Path("ops") / "moon_sync_repos.json"

#: An attended note's name: stamp, sender RSC, an UPPERCASE class, recipient.
#: The lowercase `auto-reply` the responder writes never matches.
_NAME = re.compile(
    r"^\d{4}-\d{2}-\d{2}-\d{4}-from-" + SELF_CODE + r"-([A-Z]+)-to-([A-Z][A-Z0-9]*)(?:-[^/\\]*)?\.md$"
)


def parse_name(name: str) -> tuple[str, str] | None:
    """(class, recipient code) from an own-sent note's file name, else None."""
    found = _NAME.match(name)
    return (found.group(1), found.group(2)) if found else None


def main_root() -> Path:
    return Path(headless_kit.main_checkout(REPO_ROOT))


def load_roots(config: Path) -> dict[str, Path]:
    """`{CODE: repo root}` from the per-host roster (gitignored). Missing is empty."""
    payload = read_json(config, default=None)
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("channel_codes", payload.get("repos", payload))
    if not isinstance(raw, dict):
        return {}
    return {str(k).upper(): Path(str(v)) for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _ledger_names(ledger_root: Path) -> set[str]:
    path = Path(ledger_root) / inbox_kit.OUTBOUND_REL
    return {str(d.get("note")) for d in inbox_kit._lines(path)}


def _refused(reason: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "reason": reason, "sha256": None, "reached": 0, "of": 0, "row": None, **extra}


def send(
    note: Path,
    *,
    roots: dict[str, Path],
    own_inbox: Path,
    ledger_root: Path,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Deliver one attended note and write its ledger row. Never partial-silent:
    no row unless the recipient's copy landed and re-hashed equal."""
    note = Path(note)
    parsed = parse_name(note.name)
    if parsed is None:
        return _refused("bad-name")
    cls, to = parsed
    dest_root = roots.get(to)
    if dest_root is None:
        return _refused("unknown-recipient")
    try:
        raw = note.read_bytes()
    except OSError:
        return _refused("unreadable")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return _refused("not-ascii")
    cap = inbox_kit.OutboundCap(ledger_root, clock=clock)
    if not cap.allow(cls):
        return _refused("over-cap", used=int(cap.used()), cap=int(cap.cap))
    want = hashlib.sha256(raw).hexdigest()
    targets = [Path(dest_root) / INBOX_DIRNAME / note.name, Path(own_inbox) / note.name]
    landed: list[bool] = []
    for target in targets:
        if target.exists():
            landed.append(False)
        else:
            landed.append(atomic_write_text(target, text) and _sha(target) == want)
        if not landed[0]:
            # The recipient's copy is the send. Without it nothing else is
            # written: no own copy, no row.
            return _refused("undelivered", sha256=want, of=len(targets))
    row = cap.record(note.name, cls, to)
    if row is None:
        # Over the cap between the check and the write (another sender). The
        # note IS delivered, so it is still counted: an undercount is the
        # defect this module closes.
        now = clock()
        row = {"ts": inbox_kit._iso(now), "day": inbox_kit._local_day(now), "note": note.name,
               "cls": cls, "to": to, "parts": 1}
        inbox_kit._append(Path(ledger_root) / inbox_kit.OUTBOUND_REL, row)
    return {"ok": True, "reason": "sent", "sha256": want, "reached": sum(landed), "of": len(targets), "row": row}


def audit(own_inbox: Path, ledger_root: Path, day: str | None = None) -> list[dict[str, Any]]:
    """The rows missing for own-sent notes in `own_inbox`, oldest first."""
    have = _ledger_names(ledger_root)
    out: list[dict[str, Any]] = []
    try:
        entries = sorted(Path(own_inbox).iterdir(), key=lambda p: p.name)
    except OSError:
        return out
    for entry in entries:
        parsed = parse_name(entry.name)
        if parsed is None or entry.name in have or not entry.is_file():
            continue
        try:
            epoch = entry.stat().st_mtime
        except OSError:
            continue
        row = {"ts": inbox_kit._iso(epoch), "day": inbox_kit._local_day(epoch), "note": entry.name,
               "cls": parsed[0], "to": parsed[1], "parts": 1}
        if day is None or row["day"] == day:
            out.append(row)
    out.sort(key=lambda r: (r["ts"], r["note"]))
    return out


def backfill(ledger_root: Path, rows: list[dict[str, Any]]) -> int:
    """Append each row whose note has no row yet. Returns the count appended."""
    have = _ledger_names(ledger_root)
    path = Path(ledger_root) / inbox_kit.OUTBOUND_REL
    n = 0
    for row in rows:
        if row["note"] in have:
            continue
        inbox_kit._append(path, row)
        have.add(row["note"])
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="send_note", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_send = sub.add_parser("send")
    p_send.add_argument("note", type=Path)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--day")
    p_audit.add_argument("--apply", action="store_true")
    for p in (p_send, p_audit):
        p.add_argument("--inbox", type=Path)
        p.add_argument("--ledger-root", type=Path)
    args = parser.parse_args(argv)
    root = args.ledger_root
    inbox = args.inbox
    if root is None or inbox is None:
        main_checkout = main_root()
        root = root or main_checkout
        inbox = inbox or main_checkout / INBOX_DIRNAME
    if args.cmd == "send":
        roots = load_roots(main_root() / ROOTS_REL)
        result = send(args.note, roots=roots, own_inbox=inbox, ledger_root=root)
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    missing = audit(inbox, root, day=args.day)
    for row in missing:
        print(json.dumps(row))
    if args.apply:
        print(f"appended {backfill(root, missing)}")
        return 0
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
