"""The child-environment hardening every unattended `claude` spawn gets.

OPERATOR DIRECTIVE, 2026-10-02: every headless Claude run this tree starts
runs on a SECOND subscription through a local proxy, and fails closed.

SINCE FLEET-KIT v3 THE ROUTE ITSELF IS THE KIT'S. `ops/fleet_kit/fleet_headless.py`
reads the proxy URL (user store first, so deleting the variable is the kill
switch), refuses an unset, non-loopback or unreachable URL, and builds the
child's environment. This module's own URL reader, endpoint parser, probe and
`prepare_headless_env` were deleted when the responder moved onto the kit:
the kit replaces them fully, and two routes is one too many.

WHAT STAYS, AND WHY. The kit strips credentials and provider switches BY NAME.
This tree strips BY PREFIX - every `ANTHROPIC_`, `CLAUDE_CODE_` and
`CLAUDECODE` key - so a parent session's own plumbing (an OAuth token,
`CLAUDECODE`, a messaging socket) cannot reach the child under a name nobody
listed. The kit does not do that, so it is applied on top of the kit's env,
keeping only the keys the kit itself set.

No URL, account id or machine path is written into tracked code.
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping

#: The variable the operator sets user-wide. Its DELETION is the kill switch.
#: Read by the fleet kit; named here so the documentation has one spelling.
ENV_HEADLESS_BASE_URL = "CLAUDE_HEADLESS_BASE_URL"

#: The variable the CHILD reads. Set by the kit in the child's environment only.
ENV_CHILD_BASE_URL = "ANTHROPIC_BASE_URL"

#: THE CHILD ENV IS STRIPPED BY PREFIX, ruled 2026-10-02, case-insensitively on
#: Windows where environment keys are.
CHILD_ENV_STRIP_PREFIXES: tuple[str, ...] = ("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDECODE")

#: Exempt from the prefix strip. `claude` on Windows needs to find Git Bash.
#: FLEET-KIT v15: the kit's child_env sets CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
#: (a -p child that left a background agent running killed it at turn end), so
#: the strip must not undo it. It is a tool switch, neither auth nor provider.
CHILD_ENV_KEEP: tuple[str, ...] = (
    "CLAUDE_CODE_GIT_BASH_PATH",
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS",
)

#: The NAMED floor of the strip, kept as documentation and as a test target:
#: each one either authenticates directly or switches the provider, so any of
#: them inherited by the child would bypass the proxy - a billing bypass. Every
#: name here is covered by `CHILD_ENV_STRIP_PREFIXES`; the arms prove it.
CHILD_ENV_STRIPPED: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_VERTEX_PROJECT_ID",
)


#: Removed by EXACT name, beside the prefix strip (adversary C5 on a04f4c7).
#: `NODE_OPTIONS` can `--require` arbitrary code into the node-based CLI before
#: any of its own floors load. Other `NODE_` keys are left alone.
#:
#: RECORDED RESIDUALS, not stripped, each for a stated reason:
#: - `HTTPS_PROXY` / `HTTP_PROXY`: an inherited proxy could observe or reroute
#:   the child's traffic to the local headless proxy. Not stripped because the
#:   loopback base URL is the route, and a host that needs a proxy for other
#:   traffic would break; `NO_PROXY` handling is the CLI's.
#: - `CLAUDE_CONFIG_DIR`: points the child at another settings and credentials
#:   directory. Not stripped because `--bare` reads no OAuth and the floor is
#:   pinned on argv; a planted config dir is a write to this host already.
CHILD_ENV_STRIP_EXACT: tuple[str, ...] = ("NODE_OPTIONS",)


def _norm(key: str) -> str:
    return key.upper() if os.name == "nt" else key


def _stripped(key: str) -> bool:
    """Whether `key` is removed from the child env. See `CHILD_ENV_STRIP_PREFIXES`."""
    norm = _norm(key)
    if norm in CHILD_ENV_KEEP:
        return False
    return norm in CHILD_ENV_STRIP_EXACT or norm.startswith(CHILD_ENV_STRIP_PREFIXES)


def harden_child_env(env: Mapping[str, str], keep: Iterable[str] = ()) -> dict[str, str]:
    """A COPY of `env` with every prefix-stripped key removed, except `keep`.

    `keep` names the keys the spawner itself SET (the proxy URL, a placeholder
    key) and is matched the same way the strip is. `env` is never mutated.
    """
    kept = {_norm(k) for k in keep}
    return {k: v for k, v in env.items() if _norm(k) in kept or not _stripped(k)}
