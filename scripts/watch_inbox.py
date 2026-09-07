#!/usr/bin/env python
"""Report which `moon_sync_inbox/` notes this repo has not read yet.

WHY A SCRIPT AND NOT A LIVE WATCHER. A session-scoped watcher dies with its
session. `moon_sync_inbox/` is gitignored on purpose - a note is correspondence,
not source - so a cold session inherits no record of what it already answered,
and an overnight note looks exactly like one dealt with hours ago. The failure
that costs real time is not a missed note; it is a note answered TWICE, or a
sibling's question left sitting while every agent assumes another took it. Riot
Commander's charter states the rule: silence is not agreement.

So the durable half is a WATERMARK on disk, and this script is how a session
reads and advances it.

  python scripts/watch_inbox.py            # what is new since the last mark
  python scripts/watch_inbox.py --all      # everything, new or not
  python scripts/watch_inbox.py --mark     # record the current set as read

READING IS NOT ACKNOWLEDGING. Listing never advances the watermark; `--mark` is
a separate, deliberate act, because "I saw it scroll past" and "I answered it"
are different states and only the second one is safe to forget.

DEGRADES TOWARD RE-REPORTING. A missing inbox is normal in a fresh clone and is
reported as a plain line, not a traceback. A corrupt watermark is treated as if
nothing had been read, which re-reports notes rather than dropping them: a
duplicate read costs a minute, a dropped note costs a sibling waiting on an
answer nobody knows they owe.

The watermark lives under `ops/runtime/`, which is gitignored, and is written
through `core/atomic_io.py` - the only sanctioned state-write path in this tree,
because readers poll mid-write.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.atomic_io import atomic_write_json, read_json  # noqa: E402

#: Correspondence lives here. Gitignored: see `moon_sync_inbox/README.md`.
DEFAULT_INBOX = REPO_ROOT / "moon_sync_inbox"

#: Runtime state, gitignored, never source.
DEFAULT_STATE = REPO_ROOT / "ops" / "runtime" / "inbox_seen.json"

#: This repo's own code in the `from-<CODE>-` naming convention. A note we sent
#: sits in the same directory as one we received, so direction is read off the
#: filename rather than guessed from mtime.
SELF_CODE = "RSC"


def direction(name: str) -> str:
    """`sent` if this repo wrote the note, `recv` otherwise.

    Outbound notes are LABELLED rather than hidden. A cold session wants to know
    what this repo said as well as what arrived - half a conversation reads as
    an unanswered question.
    """
    return "sent" if f"-from-{SELF_CODE}-" in name else "recv"


def _notes(inbox: Path) -> list[Path]:
    """Every note in the inbox, oldest name first. Absent directory is empty."""
    try:
        if not inbox.is_dir():
            return []
        return sorted((p for p in inbox.glob("*.md") if p.is_file()), key=lambda p: p.name)
    except OSError:
        # Unreadable directory degrades to "nothing to report" rather than
        # ending the run. The caller prints a friendly line; the raw error is
        # not a user-facing surface.
        return []


def _seen(state: Path) -> set[str]:
    """Names already marked read. Corrupt or missing state means none."""
    payload = read_json(state, default=None)
    if not isinstance(payload, dict):
        return set()
    names = payload.get("seen")
    if not isinstance(names, list):
        return set()
    return {n for n in names if isinstance(n, str)}


def unseen_notes(inbox: Path, state: Path) -> list[Path]:
    """Notes present in `inbox` that the watermark does not list.

    Pure read. This never advances the watermark - see the module docstring.
    """
    seen = _seen(state)
    return [p for p in _notes(inbox) if p.name not in seen]


def mark_seen(inbox: Path, state: Path) -> bool:
    """Record every note currently in `inbox` as read.

    Returns whether the write landed. The watermark stores NAMES rather than a
    timestamp: names are what the siblings agree on, and a clock that differs
    between two repos on one box has already caused a correction in this channel.

    NAMES RATHER THAN CONTENT HASHES, and the cost is known and accepted. Riot
    Commander measured it 2026-09-07: Clockspeed re-dated four notes, the
    filenames changed, and every seen-name watcher on the box reported four
    unread notes that had already been answered. Hashing content would fix that
    and buy something worse - an EDITED note would then read as already seen,
    and an edit is the case you most want surfaced. A false "new mail" costs one
    glance; a missed correction costs whatever the correction was for.

    THE SET IS REWRITTEN FROM THE CURRENT LISTING, NOT MERGED INTO. That is
    deliberate rather than incidental: a name that no longer exists drops out,
    so a re-dated batch cannot accumulate two entries per note forever. Riot
    Commander found the same property in its own implementation by accident and
    asked that it be kept on purpose. `test_the_seen_set_does_not_accumulate_
    renamed_notes` pins it.
    """
    state.parent.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(state, {"seen": sorted(p.name for p in _notes(inbox))})


def _render(notes: list[Path], heading: str) -> None:
    if not notes:
        print(f"{heading}: none")
        return
    print(f"{heading}: {len(notes)}")
    for path in notes:
        print(f"  [{direction(path.name)}] {path.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report unread moon_sync_inbox notes and advance the watermark.",
    )
    parser.add_argument("--dir", default=str(DEFAULT_INBOX), help="inbox directory")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="watermark file")
    parser.add_argument("--all", action="store_true", help="list every note, read or not")
    parser.add_argument("--mark", action="store_true", help="record the current set as read")
    args = parser.parse_args(argv)

    inbox = Path(args.dir)
    state = Path(args.state)

    if not inbox.is_dir():
        # Normal in a fresh clone. The directory is gitignored, so it does not
        # arrive with the repository.
        print(f"no inbox at {inbox} - nothing to report")
        return 0

    if args.all:
        _render(_notes(inbox), "all notes")
    else:
        _render(unseen_notes(inbox, state), "unread")

    if args.mark:
        if mark_seen(inbox, state):
            print(f"marked read: {state}")
        else:
            print("could not update the watermark - it stays where it was")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
