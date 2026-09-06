"""Publish the next-session hand-off to the operator's Desktop, as a BACKUP.

THE INLINE FENCED BLOCK IS THE HAND-OFF. `/done` prints it in chat, and that
printed block is what the operator selects and pastes into a cleared session.
This file writes the same bytes to the Desktop so the hand-off survives the
chat scrolling away, a crashed client, or a session closed before the paste.
It is the backup, never the primary.

`NEXT_SESSION_PROMPT.md` is the source of truth. This module NEVER accepts
prompt text as an argument: it reads the fenced block out of that file or it
refuses, so the printed block, the tracked file and the Desktop copy cannot
disagree with each other. There is no code path that writes a retyped copy.

Everything here is a guard, because every failure mode is silent:

- The Desktop is SHARED with five sibling projects, which own the `CS-`, `LL-`,
  `LW-`, `RC-` and `RM-` prefixed hand-offs sitting beside ours. The target
  basename is a module constant and no function takes a filename parameter, so
  a path bug cannot reach a neighbour's file.
- A TRUNCATED block is refused. A stale hand-off and a truncated one both read
  as current; only one of them is missing the context that makes it useful.
- NON-ASCII is refused. This is the point where the text leaves the toolchain
  for Notepad, which is exactly where the CLAUDE.md hard rule earns itself.
- The write is ATOMIC - a temp file in the destination directory, then
  `os.replace` - and is read back before it is called done. A half-written
  hand-off is indistinguishable from a complete one until it is pasted.
- NO MESSAGE NAMES A DIRECTORY. The Desktop sits under the user profile, so its
  path carries the Windows account name. Reports carry the basename and a byte
  count. Same rule as `scripts/make_shortcut.py`, pinned by the same shape of
  test.

`core/atomic_io.py` is the sanctioned state-write path and is deliberately NOT
used here: it writes inside the repository, and this is the one thing in the
tree that writes outside it. The temp file must be created in the DESTINATION
directory because `os.replace` is only atomic within a filesystem, and the
Desktop need not share one with the repo.

Usage:
    python tools/publish_next_session.py            # publish
    python tools/publish_next_session.py --check    # report drift, write nothing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "NEXT_SESSION_PROMPT.md"

# Never derived from an argument. `RC-` is Riot Commander's on this same
# Desktop, so ResinCompute cannot have it; `RSC-` is the disambiguation.
TARGET_NAME = "RSC-NEXT-SESSION.txt"

# Hidden and ours, so a crashed run leaves litter that is identifiably from
# this project rather than something a neighbour has to guess about.
TEMP_PREFIX = ".rsc-next-"

FENCE = "`" * 3

# The hand-off has never been under a few thousand bytes. Anything near this
# floor is a truncation or a stub, not a prompt.
MIN_BYTES = 2000

# Fixed remedies. These are the strings a refusal shows the operator, and none
# of them may name a path.
NO_DESKTOP = (
    "the Desktop directory does not exist - pass --desktop to point at it, "
    "or run this on the machine that has one"
)


class Refusal(Exception):
    """A refusal to publish, carrying a machine-readable reason."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def extract_prompt(source_text: str) -> str:
    """Return the single fenced block of `source_text`, or refuse.

    Fences are matched as WHOLE LINES equal to the fence, so a backticked span
    inside the prose cannot be mistaken for one. Two fence lines exactly: fewer
    means there is no block, more means the file is ambiguous about which block
    is the hand-off, and a guess there publishes the wrong text.
    """
    lines = source_text.splitlines(keepends=True)
    fences = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == FENCE]

    if len(fences) < 2:
        raise Refusal("no_prompt_block", "the source has no fenced prompt block")
    if len(fences) > 2:
        raise Refusal(
            "multiple_prompt_blocks",
            f"the source has {len(fences) // 2} fenced blocks; "
            "the hand-off must be the only one",
        )

    block = "".join(lines[fences[0] + 1 : fences[1]])

    size = len(block.encode("ascii", errors="replace"))
    if size < MIN_BYTES:
        raise Refusal(
            "prompt_too_short",
            f"the block is {size} bytes, under the {MIN_BYTES}-byte floor - a "
            "truncated hand-off reads as current and is worse than a stale one",
        )

    offenders = sorted({ch for ch in block if ord(ch) > 127})
    if offenders:
        raise Refusal(
            "non_ascii",
            "the block carries non-ASCII characters "
            + ", ".join(f"U+{ord(ch):04X}" for ch in offenders),
        )

    return block


def target_path(desktop: Path) -> Path:
    """The one file this module may write. The basename is not negotiable."""
    return desktop / TARGET_NAME


def _require_desktop(desktop: Path) -> None:
    if not desktop.is_dir():
        raise Refusal("no_desktop", NO_DESKTOP)


def check(source_text: str, desktop: Path) -> dict:
    """Report whether the Desktop backup matches the source. Writes nothing."""
    _require_desktop(desktop)
    block = extract_prompt(source_text)
    target = target_path(desktop)
    current = target.read_text(encoding="utf-8") if target.is_file() else None
    return {
        "ok": True,
        "in_sync": current == block,
        "present": current is not None,
        "target": TARGET_NAME,
        "bytes": len(block.encode("ascii")),
    }


def publish(source_text: str, desktop: Path) -> dict:
    """Write the source's fenced block to the Desktop, atomically.

    Validation happens BEFORE any temp file is created, so a refused publish
    leaves the destination directory exactly as it found it.
    """
    _require_desktop(desktop)
    block = extract_prompt(source_text)
    target = target_path(desktop)

    handle, temp_name = tempfile.mkstemp(dir=desktop, prefix=TEMP_PREFIX, suffix=".tmp")
    temp = Path(temp_name)
    try:
        # newline="\n" so the operator does not paste stray CR into a session.
        with os.fdopen(handle, "w", encoding="ascii", newline="\n") as stream:
            stream.write(block)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise

    written = target.read_text(encoding="utf-8")
    if written != block:
        raise Refusal(
            "verify_failed",
            f"{TARGET_NAME} does not match the source after writing",
        )

    return {"ok": True, "target": TARGET_NAME, "bytes": len(block.encode("ascii"))}


def default_desktop() -> Path:
    return Path.home() / "Desktop"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish the next-session hand-off backup.")
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    parser.add_argument(
        "--desktop", type=Path, default=None, help="override the Desktop directory"
    )
    args = parser.parse_args(argv)

    desktop = args.desktop or default_desktop()
    source_text = SOURCE.read_text(encoding="utf-8")

    try:
        report = check(source_text, desktop) if args.check else publish(source_text, desktop)
    except Refusal as refusal:
        print(json.dumps({"ok": False, "reason": refusal.reason, "detail": refusal.detail}))
        return 1

    print(json.dumps(report))
    return 0 if report.get("in_sync", True) else 1


if __name__ == "__main__":
    sys.exit(main())
