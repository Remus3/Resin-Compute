# ADR-004: Reserve 8790-8809 and migrate PityEngine off 8870

**Status:** Accepted
**Date:** 2026-09-06
**Supersedes:** the `:8870` allocation in SPEC_SCAFFOLD section 1

## Context

Seven projects now share the Legion box and all of them run concurrently. A
machine-wide block registry has existed since 2026-08-29, operator-declared, with
one contiguous block per project:

| Code | Project | Block |
|---|---|---|
| RM | Red Moon | 8770-8789 |
| LL | Lanternlight | 8810-8819 |
| DS | Daemon Slayer | 8860-8879 |
| RC | Amberstone | 8888-8895 plus 2999 |
| LW | LegionWallpaper | 8900-8919 |
| CS | Clockspeed | 8920-8939 |

ResinCompute was scaffolded after that registry was drawn and was never given a
block. It picked `:8870` for PityEngine by mirroring Daemon Slayer's `:8860` and
adding ten, which SPEC_SCAFFOLD section 1 recorded as a deliberate convention.

**That number is inside Daemon Slayer's reserved block.** Verified against source
on 2026-09-06, not against a live scan: Amberstone's `core/ports.py` carries
`DS_BLOCK = range(8860, 8880)`, and the operator registry says the same. Daemon
Slayer currently binds 8860 and 8861 only, so nothing was listening on 8870 and
nothing ever failed. The collision was latent, not active.

A latent collision is the dangerous kind. Clockspeed acquired its own by
allocating 8900-8911 after PROBING for a free listener; the range sat wholly
inside LegionWallpaper's block, and LW's monitor is an operator-launched GUI that
is unbound most of the time, so a live scan reported the whole block free. That
incident is written into `Clockspeed/config/ports.json` as a standing warning:
**verify a band against the owning project's registry in source, never against
netstat.** This decision followed that rule.

## Decision

**ResinCompute reserves 8790-8809**, twenty ports, short code `rsc`.

Allocations inside it:

| Port | Purpose | Bound by |
|---|---|---|
| 8790 | PityEngine HTTP | `agents/pity_engine/__main__.py` |
| 8791 | Dashboard surface | `surface/server.py` |
| 8792-8809 | unassigned | - |

**PityEngine moves from 8870 to 8790.** The mirroring convention that produced
8870 is abandoned: an allocation rule that computes a port from a sibling's port
will keep landing inside a sibling's block, which is exactly what it did.

**The numbers live in `core/ports.py` and nowhere else.** Three sites previously
carried the literal 8870 independently - `core/config.py`, the service module and
the engine's own test. They now all resolve to `core.ports.ENGINE`, and
`tests/test_ports.py` pins each against the module that really binds rather than
re-asserting the literal, which is Amberstone's refinement of Red Moon's pattern.

## Why 8790-8809 and not another gap

The unallocated gaps were 8790-8809, 8815-8859, 8880-8887 and 8896-8899.

- **8880-8887** and **8896-8899** are 8 and 4 ports, too narrow to match the
  20-port convention every other block follows.
- **8815-8859** is the largest gap but its low end abuts Lanternlight, whose
  registry entry reads "8810-8814, expanding to 8819". Taking the bottom of that
  gap would sit on the expansion it has already announced.
- **8790-8809** is exactly 20 ports, bounded by Red Moon below and Lanternlight
  above, and both bounds are firm rather than announced-as-growing.

The availability of 8790 specifically rests on one detail worth writing down:
Red Moon's block is spelled `range(8770, 8790)`, whose end is **exclusive**, so
Red Moon stops at 8789. A reader who takes that as a claim on 8790 would conclude
this block starts one port into a sibling's range.

## Verification performed

A grep for `879[0-9]` and `880[0-9]` across all six sibling trees returned hits
only in vendored JavaScript, decompiled game assets, a strings dump and one
line of Lanternlight's own ledger document - plus Amberstone's
`range(8770, 8790)`, the exclusive end discussed above. **No bind site and no registry claim** in 8790-8809.

## Consequences

- Anything holding the old port fails to reach the engine. It is a loopback
  development service with no deployed consumer, so the migration is a rename.
- `tests/test_ports.py` adds a negative guard, borrowed from Red Moon: no integer
  literal inside a sibling's block may appear anywhere in tracked Python source.
  `core/ports.py` is exempt by name, since carrying the blocks is how this tree
  proves disjointness at all. The guard is asserted non-vacuous.
- The registry entry must be carried back to the sibling projects, since none of
  them list a ResinCompute block. Sync notes were written to the established
  `moon_sync_inbox/` channel rather than by editing another project's source.

## Rejected

- **Staying on 8870 because nothing binds it.** This is the Clockspeed mistake
  restated. A reserved block is reserved whether or not a process is up.
- **Asking Daemon Slayer to cede 8870.** DS's block is contiguous and
  operator-declared; carving a hole in it to legitimise a squat is worse than
  moving one loopback service that has no consumers.
- **Taking a block without recording it anywhere.** The registry only works if
  every project can prove disjointness, which requires the seventh block to
  reach the other six.
