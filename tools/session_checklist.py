"""session_checklist.py - SessionStart hook: name this session's item-13 counter.

FLEET-COMMON item 13 a (kit v7, MAIN order 2026-10-05) opens every session
with `Session <n> checklist`, where n is this tree's session counter. The
counter lives in the tracked hand-off `RSC-NEXT-SESSION.txt` as exactly one
column-0 line `SESSION: <n>`, and `/done` (`.claude/commands/done.md`) rewrites
it to n+1. This hook reads that line and prints ONE 7-bit line naming the
counter, so the session's first reply prints the checklist under the right
number instead of re-deriving it. The task list itself is the session's to
print: a hook that fires before the operator has typed cannot know the tasks.

PROPERTIES, each guarded in `tests/test_session_checklist.py`:

- READ-ONLY. It opens one file for reading and writes nothing, anywhere.
- RESOLVED FROM __file__, never from the cwd. A session's working directory
  drifts while inbox notes are read, and a cwd-relative read would then report
  a missing counter that is not missing.
- NEVER RAISES, ALWAYS EXITS 0. A missing, duplicated or garbled counter, or an
  unreadable or non-ASCII hand-off, prints the fixed DEGRADED line. That line
  names no number: a guessed counter is worse than an admitted gap, because the
  next `/done` would write guess+1 and make the guess permanent.
- 7-BIT OUTPUT, NO BOX GLYPH. Item 13 draws the box as U+2610 in chat; this
  hook names the code point and never emits it, because hook stdout passes
  through a console that may not be UTF-8 and this tree is ASCII-only.
- STDLIB ONLY, AND IT IMPORTS NO KIT FILE. `ops/fleet_kit/` is vendored by a
  separate slice and pinned byte-for-byte; this hook does not depend on it.

`render(text)` is the pure core; `main()` is the hook entry point.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDOFF = REPO_ROOT / "RSC-NEXT-SESSION.txt"

#: The counter line, whole-line. No leading zero, no zero, no trailing text.
_COUNTER = re.compile(r"SESSION: ([1-9][0-9]{0,8})")

#: Any line that LOOKS like a counter line is a candidate. A candidate that is
#: not exactly `_COUNTER` is garbled, and garbled degrades rather than being
#: skipped - skipping it would let a mangled second line hide behind a good one.
_CANDIDATE_PREFIX = "SESSION:"

DEGRADED = (
    "Session ? checklist - RSC-NEXT-SESSION.txt has no single readable "
    "SESSION: <n> line; repair it before /done writes n+1 "
    "(FLEET-COMMON item 13)"
)


def session_number(text: str) -> int | None:
    """The counter in `text`, or None when it is missing, duplicated or garbled."""
    candidates = [
        line.rstrip("\r")
        for line in text.split("\n")
        if line.lstrip().startswith(_CANDIDATE_PREFIX)
    ]
    if len(candidates) != 1:
        return None
    match = _COUNTER.fullmatch(candidates[0])
    return int(match.group(1)) if match else None


def render(text: str | None) -> str:
    """The one line the hook prints for hand-off `text` (None = unreadable)."""
    number = session_number(text) if text is not None else None
    if number is None:
        return DEGRADED
    return (
        f"Session {number} checklist - first reply prints it per FLEET-COMMON "
        "item 13: one line per task, <box> <ID>: <task>, last line <box> /done, "
        "<box> is U+2610"
    )


def read_handoff(path: Path) -> str | None:
    """The hand-off as 7-bit text, or None if it cannot be read as such."""
    try:
        return path.read_bytes().decode("ascii")
    except (OSError, UnicodeDecodeError):
        return None


def main(handoff: Path = HANDOFF) -> int:
    try:
        line = render(read_handoff(handoff))
    except Exception:  # noqa: BLE001 - a hook must never break session start
        line = DEGRADED
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:  # noqa: BLE001 - pythonw has no stdout; still exit 0
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
