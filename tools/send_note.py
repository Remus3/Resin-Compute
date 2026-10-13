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
        Validate (the responder's `validate_draft`), refuse a retired or
        unknown recipient, cap check (exempt ORDER / FIX / RULING always
        pass), write this tree's OWN copy first, then the recipient's,
        re-hash both, THEN the row. Prints one JSON result line.
        Exit 0 sent (or already delivered and now recorded), 1 refused.

    python tools/send_note.py audit [--day YYYY-MM-DD] [--apply]
        Every own-sent note (`<stamp>-from-RSC-<CLASS>-to-<CODE>-...md`) in
        this tree's inbox with no ledger row, whatever path sent it, printed
        as the exact JSON row to append (ts and day from the copy's mtime).
        A row is proposed only when the recipient's copy hashes equal;
        others are listed with a `reason` and never appended.
        Exit 1 while any is listed; `--apply` appends the proposed rows
        (idempotent).

OWN COPY FIRST (refutation round 1, defect a). A send interrupted between
the two copies used to leave the recipient's copy delivered, no own copy
and no row: a retry said `undelivered` and the audit saw nothing. Now the
own copy lands first, so the audit always sees an interrupted send, and a
retry treats a destination copy that already hashes equal as delivered -
it finishes the send and writes the row exactly once (`already-delivered`
when no write was needed). A copy of the same name with DIFFERENT bytes is
never overwritten (`name-taken`).

THE CLASS is the kit's own `note_class`, so the row's `cls` means exactly
what `OutboundCap`'s EXEMPT test means. Hyphenated classes (POLL-ANSWER,
CORRECTION-ACCEPTED, NO-REPLY) are accepted. Responder auto-replies
(`-from-RSC-auto-reply-to-...`) are not matched: the responder records
those itself under `reply-to-<note>`.

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

from core.atomic_io import atomic_write_text  # noqa: E402

#: The vendored kit, loaded by importlib and typed Any (same as the responder).
inbox_kit: Any = importlib.import_module("ops.fleet_kit.fleet_inbox")
headless_kit: Any = importlib.import_module("ops.fleet_kit.fleet_headless")
#: The responder, REUSED for its draft gate, roster reader, retired codes and
#: channel code. Never copied: one gate, one roster rule.
responder: Any = importlib.import_module("tools.moon_sync_responder")

SELF_CODE: str = responder.SELF_CODE
INBOX_DIRNAME: str = responder.INBOX_DIRNAME
ROOTS_REL = Path("ops") / "moon_sync_repos.json"

#: An attended note's name: stamp, sender RSC, an UPPERCASE class (hyphenated
#: allowed), recipient. The lowercase `auto-reply` never matches.
_NAME = re.compile(
    r"^\d{4}-\d{2}-\d{2}-\d{4}-from-" + SELF_CODE
    + r"-([A-Z]+(?:-[A-Z]+)*)-to-([A-Z][A-Z0-9]*)(?:-[^/\\]*)?\.md$"
)


def parse_name(name: str) -> tuple[str, str] | None:
    """(class, recipient code) from an own-sent note's file name, else None.
    The class is the kit's `note_class`, the one `OutboundCap` judges."""
    found = _NAME.match(name)
    if not found:
        return None
    cls = inbox_kit.note_class(name)
    if not isinstance(cls, str) or not cls:
        return None
    return cls, found.group(2)


def recipient_root(to: str, roots: dict[str, Path]) -> tuple[Path | None, str]:
    """The recipient's repo root, or None and why. The responder's own
    destination rule (`destinations_for`): never self, never a RETIRED code,
    never a code the roster does not hold."""
    if to == SELF_CODE:
        return None, "self-recipient"
    if to in responder.RETIRED:
        return None, "retired-recipient"
    root = roots.get(to)
    return (None, "unknown-recipient") if root is None else (Path(root), "")


def draft_reasons(text: str) -> list[str]:
    """The responder's `validate_draft`, run on an attended note.

    An attended note must NOT carry the responder tag (that tag is how M5
    tells unattended traffic from human traffic), so the gate sees the tag
    prepended and every other rule - ascii, CRLF, size, traceback, account
    path, credential scan - runs on the note's own bytes."""
    return list(responder.validate_draft(responder.RESPONDER_TAG + "\n" + text, responder.Bounds()))


def main_root() -> Path:
    return Path(headless_kit.main_checkout(REPO_ROOT))


def load_roots(config: Path) -> dict[str, Path]:
    """`{CODE: repo root}` from the per-host roster, by the responder's reader."""
    return dict(responder.load_roots(config))


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


def _place(target: Path, text: str, want: str) -> str:
    """'present' (same bytes already there), 'written', 'taken' (other bytes
    under the name - never overwritten) or 'failed'."""
    if target.exists():
        return "present" if _sha(target) == want else "taken"
    if atomic_write_text(target, text) and _sha(target) == want:
        return "written"
    return "failed"


def send(
    note: Path,
    *,
    roots: dict[str, Path],
    own_inbox: Path,
    ledger_root: Path,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Deliver one attended note and write its ledger row exactly once.
    No row unless BOTH copies hold the note's bytes."""
    note = Path(note)
    parsed = parse_name(note.name)
    if parsed is None:
        return _refused("bad-name")
    cls, to = parsed
    dest_root, why = recipient_root(to, roots)
    if dest_root is None:
        return _refused(why)
    try:
        raw = note.read_bytes()
    except OSError:
        return _refused("unreadable")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return _refused("not-ascii")
    reasons = draft_reasons(text)
    if reasons:
        return _refused("invalid-draft", reasons=reasons)
    want = hashlib.sha256(raw).hexdigest()
    own_target = Path(own_inbox) / note.name
    dest_target = dest_root / INBOX_DIRNAME / note.name
    cap = inbox_kit.OutboundCap(ledger_root, clock=clock)
    for target in (own_target, dest_target):
        if target.exists() and _sha(target) != want:
            # Checked before ANY write, so a taken name never leaves a lone
            # own copy the audit would count.
            return _refused("name-taken", sha256=want, of=2)
    fresh = not (dest_target.exists() and _sha(dest_target) == want)
    if fresh and not cap.allow(cls):
        return _refused("over-cap", used=int(cap.used()), cap=int(cap.cap))
    states = []
    for target in (own_target, dest_target):
        state = _place(target, text, want)
        states.append(state)
        if state in ("taken", "failed"):
            reason = "name-taken" if state == "taken" else "undelivered"
            return _refused(reason, sha256=want, of=2, reached=states.count("present") + states.count("written"))
    result = {"ok": True, "sha256": want, "reached": 2, "of": 2}
    if note.name in _ledger_names(ledger_root):
        return {**result, "reason": "already-recorded", "row": None}
    row = cap.record(note.name, cls, to)
    if row is None:
        # Over the cap now (a past send being recorded, or another sender in
        # between). The note IS delivered, so it is still counted: an
        # undercount is the defect this module closes.
        now = clock()
        row = {"ts": inbox_kit._iso(now), "day": inbox_kit._local_day(now), "note": note.name,
               "cls": cls, "to": to, "parts": 1}
        inbox_kit._append(Path(ledger_root) / inbox_kit.OUTBOUND_REL, row)
        # Never silent (adjudicated B, P3): the result names the forced row.
        return {**result, "reason": "over-cap-recorded", "row": row}
    reason = "sent" if "written" in states else "already-delivered"
    return {**result, "reason": reason, "row": row}


def audit(
    own_inbox: Path, ledger_root: Path, day: str | None = None, *, roots: dict[str, Path]
) -> list[dict[str, Any]]:
    """The rows missing for own-sent notes in `own_inbox`, oldest first.

    AN OWN COPY ALONE IS NOT A SEND (adjudicated B, P1). Own copies are
    written first, so an interrupted send leaves one with no recipient copy.
    A row is PROPOSED only when `<recipient root>/moon_sync_inbox/<name>`
    hashes equal to the own copy. Anything else is still LISTED, with a
    `reason` - `undelivered`, `recipient-mismatch`, `unknown-recipient`
    (also a retired or self code) - and `backfill` skips it."""
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
        row: dict[str, Any] = {"ts": inbox_kit._iso(epoch), "day": inbox_kit._local_day(epoch),
                               "note": entry.name, "cls": parsed[0], "to": parsed[1], "parts": 1}
        dest_root, _why = recipient_root(parsed[1], roots)
        if dest_root is None:
            row["reason"] = "unknown-recipient"
        else:
            theirs = _sha(dest_root / INBOX_DIRNAME / entry.name)
            if theirs is None:
                row["reason"] = "undelivered"
            elif theirs != _sha(entry):
                row["reason"] = "recipient-mismatch"
        if day is None or row["day"] == day:
            out.append(row)
    out.sort(key=lambda r: (r["ts"], r["note"]))
    return out


def backfill(ledger_root: Path, rows: list[dict[str, Any]]) -> int:
    """Append each PROPOSED row (no `reason`) whose note has no row yet.
    Returns the count appended."""
    have = _ledger_names(ledger_root)
    path = Path(ledger_root) / inbox_kit.OUTBOUND_REL
    n = 0
    for row in rows:
        if "reason" in row or row["note"] in have:
            continue
        inbox_kit._append(path, row)
        have.add(row["note"])
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="send_note", description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_send = sub.add_parser("send")
    p_send.add_argument("note", type=Path)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--day")
    p_audit.add_argument("--apply", action="store_true")
    for p in (p_send, p_audit):
        p.add_argument("--inbox", type=Path)
        p.add_argument("--ledger-root", type=Path)
        p.add_argument("--roots", type=Path, help="per-host roster (default: the MAIN checkout's)")
    args = parser.parse_args(argv)
    root = args.ledger_root
    inbox = args.inbox
    if root is None or inbox is None:
        main_checkout = main_root()
        root = root or main_checkout
        inbox = inbox or main_checkout / INBOX_DIRNAME
    roots = load_roots(args.roots or main_root() / ROOTS_REL)
    if args.cmd == "send":
        result = send(args.note, roots=roots, own_inbox=inbox, ledger_root=root)
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    missing = audit(inbox, root, day=args.day, roots=roots)
    for row in missing:
        print(json.dumps(row))
    if args.apply:
        print(f"appended {backfill(root, missing)}")
        return 0
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
