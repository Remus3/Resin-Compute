"""scripts/precommit_msg_check.py - commit-msg hook (Conventional Commits).

Validates the commit's SUBJECT line against the Conventional Commits shape:
`<type>(<scope>)?!?: <description>`. Body and trailers are unrestricted.

Auto-generated subjects (Merge / Revert / Reapply / fixup! / squash! / amend!)
are skipped - git writes those itself and rejecting them would break a rebase.

Runs LAST in .githooks/commit-msg, after the trailer strip and the glyph gate,
so it validates the message that will actually be committed rather than a
draft of it.

`#` LINES ARE CONTENT UNLESS GIT PROVABLY STRIPS THEM. Git runs commit-msg on
the PRE-cleanup bytes, and `git commit -F` / `-m` default to cleanup=whitespace,
which keeps `#` lines - so a `#` first line IS the landed subject there.
Measured 2026-10-03; `hash_lines_are_stripped` holds the decision and the
measured table. Every unknown fails closed, with one exception.

KNOWN GAP: an explicit `--cleanup=whitespace` or `--cleanup=verbatim` on an
EDITOR commit. Git does not pass the flag to the hook, so this module assumes
the editor default (strip) and skips a `#` first line that will in fact land
as the subject. The glyph half in `tools/precommit_gate.py` is unaffected,
because it scans every line. The same gap is recorded beside
`KNOWN_MESSAGE_SURVIVORS` in `tools/gate_mutation_runner.py`.

Bypass with `--no-verify` if absolutely necessary; please do not make a habit
of it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
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


class ConfigUnreadable(RuntimeError):
    """git could not answer a config question. Never read as "unset"."""


def _git_config_get(key: str) -> str | None:
    """The value of `key`, None when git positively answers it is unset.

    `git config --get` exits 1 for an absent key; anything else non-zero, or a
    git that cannot be run, raises - "could not check" is not "unset".
    """
    try:
        proc = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigUnreadable(key) from exc
    if proc.returncode == 1:
        return None
    if proc.returncode != 0:
        raise ConfigUnreadable(key)
    return proc.stdout.decode("utf-8", "replace").strip()


def hash_lines_are_stripped(
    env: Mapping[str, str] | None = None,
    config_get: Callable[[str], str | None] | None = None,
) -> bool:
    """True only when git provably strips `#` lines from THIS commit.

    MEASURED 2026-10-03 on git 2.53.0.windows.3: commit-msg is handed the
    PRE-cleanup bytes in every mode, the editor flow included. `-F` and `-m`
    default to cleanup=whitespace and KEEP `#` lines; the editor flow defaults
    to cleanup=strip. The one signal git gives the hook is `GIT_EDITOR=:`,
    exported exactly when no editor was used, and `GIT_INDEX_FILE`, exported to
    every commit hook. A `--cleanup=` flag on the command line is INVISIBLE
    here; see the residual in the module docstring.

    Fails CLOSED - False, so `#` lines are judged as content - whenever the
    answer is not known: outside a commit hook, a config git cannot read, an
    unknown cleanup mode, or a comment character other than `#`.
    """
    env = os.environ if env is None else env
    config_get = _git_config_get if config_get is None else config_get
    if "GIT_INDEX_FILE" not in env:
        return False
    editor_used = env.get("GIT_EDITOR") != ":"
    try:
        for key in ("core.commentString", "core.commentChar"):
            value = config_get(key)
            if value is not None and value != "#":
                return False
        mode = (config_get("commit.cleanup") or "default").strip().lower()
    except ConfigUnreadable:
        return False
    if mode == "strip":
        return True
    if mode == "default":
        return editor_used
    # whitespace, verbatim and scissors KEEP `#` lines - scissors truncates at
    # its marker line and keeps every `#` line above it, measured in editor
    # mode. Anything else is a mode this function does not know: fail closed.
    return False


def _read_subject(msg_file: Path, *, hash_is_content: bool = True) -> str:
    """The first line git will keep: the first non-blank line, skipping `#`
    lines only when the caller has shown git strips them. Default: content."""
    raw = msg_file.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        if not hash_is_content and line.startswith("#"):
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

    subject = _read_subject(msg_file, hash_is_content=not hash_lines_are_stripped())
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
