"""caveman_default.py - SessionStart hook: declare CAVEMAN ULTRA as the default
output dialect for every ResinCompute Claude Code session.

Adopted on operator instruction 2026-09-06. The body is Sibling-C's,
carried across from `moon_sync_inbox/from-RC-verbatim/tools/caveman_default.py`
rather than paraphrased: four repos each writing their own version of one shared
dialect is how the fleet ends up with four dialects. Only the docstring is
local. The banner below is BYTE-IDENTICAL to that sibling's and must stay that way - it is
the contract, not prose.

RSC FILED A DISSENT AGAINST THIS AND THE OPERATOR OVERRULED IT, which is
recorded here because the reasoning still bounds the scope. RSC argued CAVEMAN
is an operator output-dialect preference rather than a cross-repo protocol: it
has no interop surface and makes no shared artifact safer. That argument was
about whether a SIBLING may require it, and it stands. The operator asking for
it in their own tree settles the only question that mattered.

Wired in `.claude/settings.json` SessionStart hooks. stdout is injected as
session context. Must be fast (timeout 5) and must NEVER raise - a crashing hook
would noise every session start. Pairs with `tools/caveman.md`, the skill body,
which is a byte-exact copy of the same sibling's.

SCOPE, and it is the half that is easy to get wrong: terseness is for CHAT.
Committed repo artifacts are excluded by the banner itself - code, docstrings,
`.md`, commit messages, `.ps1` - because `CLAUDE.md` already governs those and a
compressed commit message is a worse artifact, not a cheaper one.

DIALECT HISTORY: a 2026-06-27 experiment layered WENYAN-FULL (classical Chinese)
on top of caveman for extra token economy; the operator reverted it the same day
(too lossy / hard to skim) back to CAVEMAN ULTRA - terse plain-ASCII caveman, no
classical Chinese. Do not re-derive that experiment.
"""
from __future__ import annotations

import sys

_BANNER = (
    "# Output dialect: CAVEMAN ULTRA (default, operator 2026-06-27)\n"
    "\n"
    "Default to CAVEMAN ULTRA for chat / prose output - maximum caveman terseness "
    "in plain 7-bit ASCII English: drop articles + filler, short clauses, no "
    "hedging, target 80-90 percent character reduction. NOT wenyan / classical "
    "Chinese (that experiment was reverted 2026-06-27). Keep BYTE-EXACT + strict "
    "7-bit ASCII (never paraphrased): file paths, shell commands, code, "
    "identifiers, machine-parsed tokens, and ALL committed repo artifacts (code / "
    "docstrings / .md / commit messages / .ps1 - the CLAUDE.md hard rule). Answer "
    "the operator's clarifying questions in plain English. Reference: "
    "tools/caveman.md.\n"
)


def main() -> int:
    try:
        sys.stdout.write(_BANNER)
    except Exception:  # noqa: BLE001 - a hook must never break session start
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
