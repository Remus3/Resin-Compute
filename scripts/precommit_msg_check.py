"""scripts/precommit_msg_check.py - commit-msg hook (Conventional Commits).

Validates the commit's SUBJECT line against the Conventional Commits shape:
`<type>(<scope>)?!?: <description>`. Body and trailers are unrestricted.

Auto-generated subjects (Merge / Revert / Reapply / fixup! / squash! / amend!)
are skipped - git writes those itself and rejecting them would break a rebase.

Runs LAST in .githooks/commit-msg, after the trailer strip and the glyph gate,
so it validates the message that will actually be committed rather than a
draft of it.

Bypass with `--no-verify` if absolutely necessary; please do not make a habit
of it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

# <type>(<optional scope>)<optional !>: <space><non-space>...
SUBJECT_RE = re.compile(
    rf"^(?:{'|'.join(TYPES)})(?:\([\w./\- ]+\))?!?:\s+\S",
)

SKIP_PREFIXES = (
    "Merge ",
    "Revert ",
    "Reapply ",
    "fixup!",
    "squash!",
    "amend!",
)

SOFT_LINE_LIMIT = 100


def validate(subject: str) -> tuple[bool, str | None]:
    """Return (ok, error_message). error_message is None on success."""
    if not subject.strip():
        return False, "empty subject line"
    if any(subject.startswith(p) for p in SKIP_PREFIXES):
        return True, None
    if not SUBJECT_RE.match(subject):
        return False, "subject does not match <type>(<scope>)?: <description>"
    return True, None


def _read_subject(msg_file: Path) -> str:
    """First non-comment, non-blank line of the message file."""
    raw = msg_file.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        if line.startswith("#"):
            continue
        if not line.strip():
            continue
        return line.rstrip()
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        print("commit-msg: missing path argument", file=sys.stderr)
        return 1
    msg_file = Path(sys.argv[1])
    if not msg_file.exists():
        print(f"commit-msg: file not found: {msg_file}", file=sys.stderr)
        return 1

    subject = _read_subject(msg_file)
    ok, err = validate(subject)
    if not ok:
        print(
            "commit-msg: subject line rejected.\n"
            f"  reason:   {err}\n"
            f"  got:      {subject!r}\n"
            "  expected: <type>(<scope>)?: <description>\n"
            f"  types:    {', '.join(TYPES)}\n"
            "  example:  feat(engine): add weapon-banner fate point carry\n"
            "Bypass with --no-verify if absolutely necessary.",
            file=sys.stderr,
        )
        return 1

    if len(subject) > SOFT_LINE_LIMIT:
        # Warn-only: nudge, do not block.
        print(
            f"commit-msg: subject is {len(subject)} chars (>{SOFT_LINE_LIMIT}); "
            "consider tightening.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
