# ADR-011: Responder MAIN provenance is a direct outbox byte hash; kit verify_main is adoption-only

**Status:** Accepted, 2026-10-03 (adjudicated)
**Closes:** item (3) of the FLEET-KIT v4 wrap-up row in `ROADMAP.md`, which
recorded that the responder still uses its own outbox hash rather than the v4
kit's `verify_main`

## Context

The responder decides whether a note that names MAIN as its sender carries the
operator's authority. CLAUDE.md pins the operator's own wording for that test:
a note from MAIN counts only as a "byte-identical copy in MAIN's outbox,
SHA-256 checked". The responder implements it in
`tools/moon_sync_responder.py::main_provenance`: it reads MAIN's outbox copy of
the same filename, hashes the raw bytes of both files with SHA-256, compares
them, and refuses any copy larger than `MAX_PROVENANCE_BYTES` (4 MiB). It runs
no git. No MAIN row, a missing outbox file and any read error are all
UNVERIFIABLE, and UNVERIFIABLE is handled as data, exactly as a mismatch is.

FLEET-KIT v4 ships `verify_main` in `ops/fleet_kit/fleet_headless.py`, which
checks a note against the blob MAIN has COMMITTED for its outbox copy. The
question was whether the responder should switch to it, add it, or keep its
own check.

## Criteria, in priority order

1. **The pinned operator wording** in CLAUDE.md: a byte-identical copy in
   MAIN's outbox, SHA-256 checked.
2. **The scope of MAIN's FLEET-KIT v4 order, section 7.** Section 7.1 adds
   `verify_main` only to verify the v4 delivery note and its five bundle
   files. The section 7.3 adoption list does not include provenance. Section
   7.4 is advice to callers, not an order.
3. **Fail-closed.** Any doubt must land as data, never as instruction.
4. **Liveness.** A genuine MAIN note must not be lost.
5. **Cost** per note per tick.
6. **Blast radius** of the change.

## Decision

**Option A: keep `main_provenance` as it is. No code change.** The direct
raw-byte SHA-256 of MAIN's outbox copy, with the 4 MiB cap and no git, remains
the runtime provenance check for every MAIN note. The kit's `verify_main` is
used only where the v4 order puts it: adopting the v4 delivery and its bundle.

## Rejected alternatives

- **B - kit `verify_main` only.** Drops the outbox hash that the order itself
  kept, has no size cap, and loses every note delivered before MAIN commits
  its outbox copy: such a note reads UNVERIFIABLE, UNVERIFIABLE notes are
  recorded answered, and an answered note is never re-checked.
- **C - both checks, plus a retry.** Near-zero security gain: a writer running
  as the same user who can write MAIN's outbox can also commit there, so the
  commit check adds no independent barrier. It does add a loss path, retry
  state, and up to 4 git calls at 60 s each per note per tick.
- **D - either check passes.** An OR of two checks is weaker than each check
  alone.

**If this is ever reversed to C,** the shape is fixed now so it is not argued
again: hold the note pending, re-check it for up to 3 ticks, then answer it as
UNVERIFIABLE data with the log reason "MAIN not committed".

## Evidence, measured 2026-10-03

- Over 27 real MAIN notes in the inbox, both checks agreed, and all 27 passed.
- Three further files carrying `-from-MAIN-` in their names were this tree's
  own auto-reply files, not MAIN notes, and are excluded from that population.
- The commit-lag case (a hash-matching note MAIN had not yet committed) was
  never observed.

## Known common-mode risk

Both checks locate MAIN through the same row of the gitignored roots map. A
wrong row would pass BOTH checks, so their agreement says nothing about the
map. Neither check tests the map. This is filed as open work in `ROADMAP.md`.

## Consequences

- No runtime behaviour changes.
- The existing liveness gap stays open and is filed in `ROADMAP.md`: an
  UNVERIFIABLE MAIN note is recorded answered and never re-checked, so a note
  delivered before MAIN writes its outbox copy is lost. That gap exists under
  A and is worse under B.

## What would reverse this

- A SHA-256-verified MAIN note ordering `verify_main` for runtime notes.
- A measured case where a hash-matching note was never committed by MAIN, and
  that mattered.
- MAIN's outbox becoming writable by something that cannot commit there.
