"""The single owner of every TCP port number this repository binds.

WHY THIS FILE EXISTS. Seven projects share one Windows box and every one of them
runs concurrently. Until a project can answer "which ports are mine" without
grepping its own bind sites, it cannot prove it does not contend with a sibling,
and the failure mode is not a clean error - it is one process silently winning a
bind and another degrading in a way nobody attributes to a port for hours.

The pattern is Sibling-B's, adopted by Sibling-C, and now by this tree:
named constants, an `ALL` frozenset of what is actually bound, the block
reservations, and `tests/test_ports.py` pinning each constant against the
module that really binds it rather than re-asserting the literal here. That last
distinction is Sibling-C's improvement and it is the one that catches drift:
`assert ENGINE == 8790` passes forever while the server quietly moves.

THE MEASUREMENT THAT CREATED THIS FILE. ResinCompute shipped its scaffold with
PityEngine on 8870, chosen to mirror Sibling-F's 8860 by adding ten. 8870 is
INSIDE Sibling-F's reserved block 8860-8879, which is recorded in the
machine-wide registry and restated in Sibling-C's `core/ports.py` as that
sibling's own `range(8860, 8880)` constant. Nothing was bound there at the time,
so nothing broke and nothing warned. That is precisely how Sibling-A acquired its own
collision: it picked a band by PROBING for a free listener, and the owning
project's process happened not to be running. A band is verified against the
owning project's registry in source, never against a live scan.

ADR-004 records the block assignment and the migration off 8870.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Ports this repository binds
# ---------------------------------------------------------------------------

ENGINE = 8790
"""PityEngine, the pure deterministic forecaster, over plain local HTTP.

Bound by `agents/pity_engine/__main__.py` as `DEFAULT_PORT`, and connected to by
`core/config.py` as `DEFAULT_ENGINE_PORT`. Both are pinned against this constant
in `tests/test_ports.py`, so the three cannot drift apart.

HTTP and not HTTPS, deliberately, and it binds 127.0.0.1 only. The engine is a
pure function of its request body: it holds no credential, reads no account
state and writes nothing. There is no secret on the wire to protect.
"""

DASHBOARD = 8791
"""The local dashboard surface the Electron shell loads.

Bound by `surface/server.py`. Unlike the engine this one renders account state,
so it is the port that will grow a trust story if it ever leaves loopback.
"""


# ---------------------------------------------------------------------------
# Block reservations
# ---------------------------------------------------------------------------

RSC_BLOCK = range(8790, 8810)
"""ResinCompute's block: 8790 through 8809 inclusive.

A `range` with an EXCLUSIVE end, matching Sibling-C's spelling. The
exclusive end is worth stating out loud because it reads as a claim on the last
number and is not one: `range(8770, 8790)` is Sibling-B's block and it stops at
8789, which is the single fact that made 8790 available to this project at all.
"""

# Sibling blocks, carried so this tree can prove disjointness without reading
# six other repositories. Operator-declared 2026-08-29, verified against source
# on 2026-09-06 rather than against a live port scan.
#
# LISTING A SIBLING IS NOT A LICENCE TO BIND IN ITS RANGE, and it is not a claim
# that this repository knows what the sibling has allocated INSIDE its block.
# The only use of these is the disjointness proof in tests/test_ports.py.
#
# Sibling-B takes the opposite approach - it carries NO sibling literal in any
# tracked file and proves disjointness from the negative side with a FORBIDDEN
# set. Do not paste this repository's literals into that tree; cite the block.
#
# The codenames are deliberately opaque and this file does not resolve them. The
# per-host map lives in the GITIGNORED `ops/moon_sync_repos.json`; a reader on a
# machine that has one resolves a letter there, and nothing tracked here does.
SB_BLOCK = range(8770, 8790)
SD_BLOCK = range(8810, 8820)
SF_BLOCK = range(8860, 8880)
SC_BLOCK = range(8888, 8896)
SE_BLOCK = range(8900, 8920)
SA_BLOCK = range(8920, 8940)

BLOCKS = {
    "rsc": RSC_BLOCK,
    "sb": SB_BLOCK,
    "sd": SD_BLOCK,
    "sf": SF_BLOCK,
    "sc": SC_BLOCK,
    "se": SE_BLOCK,
    "sa": SA_BLOCK,
}
"""Every project's reserved range, keyed by short name.

`rsc` is THIS repository. The other six are siblings under opaque codenames; see
the note above the block constants for where a letter is resolved. Sibling-C
carries two project names in this tree's history, the second a rename of the
first, and both collapse to the one codename - so do not read them as two.

Sibling-C additionally reserves 2999, far outside the 88xx range, because
that is Riot's Live Client Data API and Riot owns the number. It is deliberately
NOT listed as a block here: it is not a reservation this project could ever
collide with by allocating inside 8790-8809.
"""

ALL = frozenset({ENGINE, DASHBOARD})
"""Every port THIS repository binds. Nothing else may be added without a block
entry above and a definition-site pin in tests/test_ports.py."""


def block_for(port: int) -> str | None:
    """Return the short name of the block owning `port`, or None if unassigned.

    The blocks are disjoint by construction, and that disjointness is ASSERTED in
    `tests/test_ports.py` rather than assumed here, so the iteration order of
    `BLOCKS` cannot change the answer.
    """
    for name, block in BLOCKS.items():
        if port in block:
            return name
    return None


def is_ours(port: int) -> bool:
    """True when `port` falls inside this project's reserved block.

    Note this asks about the BLOCK, not about `ALL`. A port inside the block that
    nothing binds yet is still ours to allocate; a port this repository binds
    that fell outside the block would be a defect, and is the exact condition
    `tests/test_ports.py` exists to catch.
    """
    return port in RSC_BLOCK


def next_free() -> int:
    """Lowest port in this project's block that nothing here binds yet.

    Refuses rather than guessing once the block is full: a caller that silently
    received a port from outside the block would reintroduce the 8870 defect
    that created this module.
    """
    for port in RSC_BLOCK:
        if port not in ALL:
            return port
    raise RuntimeError("the ResinCompute port block is fully allocated - request a wider block")
