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
used here: it writes inside the repository, and this writes outside it. It is
NOT the only thing in the tree that does. An earlier version of this docstring
claimed it was, which made an audit-by-docstring miss two real siblings:

- `scripts/make_shortcut.py` writes a `.lnk` under the Desktop, building a
  PowerShell script that drives the `WScript.Shell` COM object and calls
  `.Save()`, then running it.
- `ops/install_scheduled_task.ps1` writes into the Windows Task Scheduler store
  via `Register-ScheduledTask`. That one OUTLIVES THE CHECKOUT - deleting the
  clone does not remove the task - so README carries the removal command next
  to the install.

A third route opens only when an operator asks for it: `RC_DATA_DIR` can point
`data/` anywhere, through `_env_path` in `core/config.py`.

Those are what a sweep for Desktop, `USERPROFILE` and scheduler writes turned
up. Treat the list as the known set, not as a proof of exhaustiveness - the
mistake corrected here was precisely a claim of exhaustiveness that nothing
checked.

The temp file must be created in the DESTINATION directory because
`os.replace` is only atomic within a filesystem, and the Desktop need not share
one with the repo.

Usage:
    python tools/publish_next_session.py            # publish
    python tools/publish_next_session.py --check    # report drift, write nothing
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

#: THE HAND-OFF IS A PUBLICATION SURFACE, and until 2026-09-07 this gate did
#: not treat it as one. It refused non-ASCII and truncation - both real - and
#: passed a live API key and an absolute path naming the operator's account
#: straight through to the Desktop. Measured, not theorised: a block carrying
#: an inline Nimble key, and one carrying
#: `C:\Users\<account>\AppData\...` were each published clean.
#:
#: Why that matters more here than in an ordinary file. The hand-off is pasted
#: by hand into a cold session, quoted into notes to four sibling repos, and
#: `NEXT_SESSION_PROMPT.md` is TRACKED in a PUBLIC repository. Legion Wallpaper
#: raised exactly this and asked whether anyone gated PII more widely; this
#: tree's honest answer was no. `tests/test_machine_identity.py` sweeps tracked
#: files and `tests/test_no_secret_literals.py` sweeps them for credentials,
#: but both run over the COMMITTED tree - neither sees a block on its way out
#: to the Desktop, which is the one path that leaves the toolchain.
#:
#: Vendor prefixes only, deliberately. A digest, a git SHA and a base64 blob
#: all look random; only a real credential carries one of these. The same
#: reasoning, and the same list, as `tests/test_no_secret_literals.py` - stated
#: in both places because a hand-off gate that imported from the test suite
#: would be a tool depending on tests to run.
SECRET_PREFIXES = (
    "sk-ant-",
    "sk-",
    "ghp_",
    "github_pat_",
    "AIza",
    "RGAPI-",
    "xoxb-",
    "xoxp-",
)

#: Secret-bearing variable names bound to a literal. The NAME is the evidence;
#: the value's entropy is irrelevant, which is what catches a short key.
SECRET_NAMES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_USAGE_KEY",
    "NIMBLE_API_KEY",
    "GEMINI_API_KEY",
    "RIOT_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
)

#: An absolute path under a Windows user profile, in the three spellings this
#: box actually produces: native, MSYS/Git-Bash, and WSL. `<account>` and other
#: angle-bracket placeholders are legal - the hand-off is allowed to SHOW the
#: shape it is refusing.
#: ASSEMBLED FROM PARTS, and that is not style. Written as one literal, this
#: pattern's own source is an account-shaped path, so
#: `tests/test_machine_identity.py` sweeps it up, and the only remedies then
#: are to allowlist a regex fragment or to loosen that guard. Both are worse
#: than a constant: an allowlist entry spelled as a chunk of regex is
#: unreadable and goes unstable the moment this line is edited, and loosening
#: the sweep is how it stops catching a real account. Naming the segment
#: removes the collision instead of negotiating with it.
_USERS = "Users"
ACCOUNT_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]" + _USERS + r"[\\/]"
    r"|/c/" + _USERS + r"/"
    r"|/mnt/c/" + _USERS + r"/)"
    r"(?P<who>[^\\/\s\"']+)",
    re.IGNORECASE,
)

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

    for leak in scan_for_leaks(block):
        raise Refusal(*leak)

    return block


def scan_for_leaks(block: str) -> list[tuple[str, str]]:
    """`(reason, detail)` for every credential or account path in `block`.

    A LIST rather than a raise, so the arms that prove this has teeth can call
    it directly on a planted string without building a whole hand-off, and so a
    caller can report every offender rather than only the first.

    THE DETAIL NEVER ECHOES THE SECRET. It names the prefix or the variable and
    stops. A refusal message is printed to a terminal and pasted into notes, so
    a gate that quoted the key it caught would publish it in the act of
    refusing to publish it.
    """
    found: list[tuple[str, str]] = []

    for prefix in SECRET_PREFIXES:
        for match in re.finditer(re.escape(prefix) + r"[A-Za-z0-9_\-]{16,}", block):
            found.append(
                (
                    "secret_literal",
                    f"the block carries what looks like a live credential "
                    f"(prefix {prefix!r}, {len(match.group(0))} chars). Move it to a "
                    "machine environment variable and reference it by name.",
                )
            )

    for name in SECRET_NAMES:
        for match in re.finditer(
            re.escape(name) + r"\"?\s*[:=]\s*(?P<v>\"[^\"]*\"|'[^']*'|[^\s,}]+)", block
        ):
            value = match.group("v")
            # An environment REFERENCE is the destination of the rule, not a
            # violation of it. `${NAME}`, `%NAME%`, `$env:NAME`, `os.environ[...]`
            # and an angle-bracket placeholder all stay legal.
            if re.search(r"\$\{?[A-Z_]+\}?|%[A-Z_]+%|environ|getenv|<[^>]*>", value):
                continue
            found.append(
                (
                    "secret_literal",
                    f"the block binds {name} to a literal value. Reference the "
                    "machine environment variable instead.",
                )
            )

    for match in ACCOUNT_PATH.finditer(block):
        who = match.group("who")
        if who.startswith("<") or who.upper() in {"PUBLIC", "DEFAULT", "ALL USERS"}:
            continue
        found.append(
            (
                "account_path",
                f"the block names a real user profile ({match.group(0)!r}). The "
                "hand-off is pasted into cold sessions and quoted into sibling "
                "repos, and this tree is public - use <account> instead.",
            )
        )

    return found


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
