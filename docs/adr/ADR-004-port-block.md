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
| SB | Sibling-B | 8770-8789 |
| SD | Sibling-D | 8810-8819 |
| SF | Sibling-F | 8860-8879 |
| SC | Sibling-C | 8888-8895 plus 2999 |
| SE | Sibling-E | 8900-8919 |
| SA | Sibling-A | 8920-8939 |

ResinCompute was scaffolded after that registry was drawn and was never given a
block. It picked `:8870` for PityEngine by mirroring Sibling-F's `:8860` and
adding ten, which SPEC_SCAFFOLD section 1 recorded as a deliberate convention.

**That number is inside Sibling-F's reserved block.** Verified against source
on 2026-09-06, not against a live scan: Sibling-C's `core/ports.py` carries
`SF_BLOCK = range(8860, 8880)`, and the operator registry says the same.
Sibling-F currently binds 8860 and 8861 only, so nothing was listening on 8870
and nothing ever failed. The collision was latent, not active.

A latent collision is the dangerous kind. Sibling-A acquired its own by
allocating 8900-8911 after PROBING for a free listener; the range sat wholly
inside Sibling-E's block, and Sibling-E's monitor is an operator-launched GUI
that is unbound most of the time, so a live scan reported the whole block free.
That incident is written into `Sibling-A/config/ports.json` as a standing
warning:
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
re-asserting the literal, which is Sibling-C's refinement of Sibling-B's pattern.

## Why 8790-8809 and not another gap

The unallocated gaps were 8790-8809, 8815-8859, 8880-8887 and 8896-8899.

- **8880-8887** and **8896-8899** are 8 and 4 ports, too narrow to match the
  20-port convention every other block follows.
- **8815-8859** is the largest gap but its low end abuts Sibling-D, whose
  block is **8810-8819**. Taking the bottom of that gap would sit directly on it.

  CORRECTED 2026-09-06 on Sibling-D's own advice. This clause originally read
  that Sibling-D's registry entry was "8810-8814, expanding to 8819", and
  reasoned about an ANNOUNCED expansion. That expansion had already landed: the
  operator widened the block to 8810-8819 on 2026-08-27, before this ADR was
  written. The decision
  below is unaffected, because 8815-8859 was rejected either way - but rejecting a
  range because it overlaps a LIVE claim is a different fact from rejecting it
  because it abuts a promised one, and the wrong premise would have been copied
  forward into the reasoning for an eighth block. The table at the top of this
  ADR always carried the correct 8810-8819; only this clause was stale, which is
  its own lesson about a document disagreeing with itself.
- **8790-8809** is exactly 20 ports, bounded by Sibling-B below and Sibling-D
  above, and both bounds are firm rather than announced-as-growing.

The availability of 8790 specifically rests on one detail worth writing down:
Sibling-B's block is spelled `range(8770, 8790)`, whose end is **exclusive**, so
Sibling-B stops at 8789. A reader who takes that as a claim on 8790 would
conclude this block starts one port into a sibling's range.

## Verification performed

A grep for `879[0-9]` and `880[0-9]` across all six sibling trees found
**no bind site and no registry claim** in 8790-8809. Every hit was incidental,
a number occurring inside unrelated non-source content, with the single
exception of Sibling-C's `range(8770, 8790)` - the exclusive end discussed
above, which is a real registry claim and does not reach 8790.

> **REDACTED 2026-09-06, before this repository was made public.** The paragraph
> above previously named the particular kinds of non-source file the incidental
> hits sat in, inside sibling trees that are NOT published and cannot answer for
> themselves. That detail was never load-bearing: "no bind site and no registry
> claim" carries the whole argument, and the count and location of unrelated
> matches are not this ADR's to publish. **The verification result is unchanged**
> and was not re-run - only the characterisation of other projects' contents is
> removed. Recorded rather than done silently, because an ADR that is edited
> without saying so stops being a record.

## Consequences

- Anything holding the old port fails to reach the engine. It is a loopback
  development service with no deployed consumer, so the migration is a rename.
- `tests/test_ports.py` adds a negative guard, borrowed from Sibling-B: no integer
  literal inside a sibling's block may appear anywhere in tracked Python source.
  `core/ports.py` is exempt by name, since carrying the blocks is how this tree
  proves disjointness at all. The guard is asserted non-vacuous.
- The registry entry must be carried back to the sibling projects, since none of
  them list a ResinCompute block. Sync notes were written to the established
  `moon_sync_inbox/` channel rather than by editing another project's source.

## Rejected

- **Staying on 8870 because nothing binds it.** This is the Sibling-A mistake
  restated. A reserved block is reserved whether or not a process is up.
- **Asking Sibling-F to cede 8870.** Sibling-F's block is contiguous and
  operator-declared; carving a hole in it to legitimise a squat is worse than
  moving one loopback service that has no consumers.
- **Taking a block without recording it anywhere.** The registry only works if
  every project can prove disjointness, which requires the seventh block to
  reach the other six.
