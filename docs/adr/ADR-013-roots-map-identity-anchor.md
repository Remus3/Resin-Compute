# ADR-013: Roots-map identity anchor - an untracked random beacon pinned by digest, no git and no tracked identity material

**Status:** Proposed, 2026-10-04 (design only, not accepted)
**Relates to:** the ROADMAP row "TEST THE ROOTS-MAP COMMON-MODE RISK" in
`ROADMAP.md` and the Known common-mode risk section of
`docs/adr/ADR-011-main-provenance.md`

## Context

The responder decides whether a note naming MAIN as its sender carries the
operator's authority. `tools/moon_sync_responder.py::main_provenance` (line
2098) finds MAIN's tree through one row of a per-host, gitignored roots map:
`load_roots` (lines 1615-1638) reads the file named by `DEFAULT_ROOTS_CONFIG`
(line 673), that file is gitignored by design (.gitignore line 125, the only
file that resolves a codename to a real checkout), and `main_provenance` takes
the MAIN row at line 2119, derives the outbox as the sibling of MAIN's inbox
at line 2125, requires the outbox to list the exact filename (line 2135),
compares bytes and digests (line 2164) and checks that the verified bytes
address this tree (line 2170) before returning MATCH (line 2175). Only MATCH
is treated as verified downstream (`_verified`, lines 1412-1415). No git runs
anywhere on that path.

The failure this ADR is about is the VALUE of one row in a per-host file that
nothing tracked can see. ADR-011 filed it as a Known common-mode risk (lines
72-76): both MAIN provenance checks locate MAIN through the same row, so a
wrong row passes both, their agreement says nothing about the map, and
neither check tests the map.

One check runs at tick time. The kit's `verify_main`
(`ops/fleet_kit/fleet_headless.py` lines 562-585) is adoption-only under
ADR-011 (lines 40-43): it takes the outbox location as an argument, checks no
identity of the repository it is handed, and has no tracked call site - a
grep finds its definition and prose only. At tick time the row is a single
point and the second check is not a second opinion about it.

No test covers the map's integrity. `tests/test_responder_main_provenance.py`
pins the no-row, missing-directory, decoy-outbox (lines 518-553, driven
through a redirected map) and bundle cases - each about what happens UNDER a
given row. None asks whether the row is right.

Scope: this ADR concerns `main_provenance` only. It proposes no change to the
kit, to `verify_main`, or to how `verify_main` is used.

## Threat model, in two halves

Catchable - a row that names a location other than MAIN's real outbox:

- a typo or a stale row after MAIN moves: it points at nothing (already
  UNVERIFIABLE today) or at another tree's directory;
- a row pointing at another tree that happens to hold the same filename and
  the same bytes - today a MATCH by construction, the LIMIT the ROADMAP row
  records;
- a swapped or corrupted map, written by anything running as the same user;
- a git clone of MAIN. A clone carries MAIN's remote configuration and its
  root commit, so the example anchors the ROADMAP row names distinguish MAIN
  only from a non-MAIN repository, never from a clone of MAIN.

Uncatchable, and said plainly: No in-tree check distinguishes MAIN's tree from
a byte-identical filesystem copy of it; this ADR does not claim to. A copy
that carries every untracked file is indistinguishable from the original by
anything that reads files.

The same-user actor. ADR-011 lines 51-53: "Near-zero security gain: a writer
running as the same user who can write MAIN's outbox can also commit there,
so the commit check adds no independent barrier." An actor who can edit the
map, the pin and MAIN's outbox together is the case ADR-011 placed beyond any
independent in-tree barrier. That is settled and this ADR does not move it.

## Criteria, in priority order

1. **Scope.** `tools/moon_sync_responder.py::main_provenance` only; no change
   to the kit.
2. **ADR-011 stands.** Every candidate is weighed against ADR-011's own cost
   words, and ADR-011's option C is settled.
3. **Hygiene.** Zero leak in a public clone. A digest is ruled on as a
   possible confirmation oracle, not waved through because the sweeps cannot
   read it.
4. **Halt clause (c)** of the ruling in `CLAUDE.md`: anything MAIN must do is
   an operator ask, never a decision this tree takes.
5. **Status Proposed**, asks listed, design only, no code.
6. **The docs guards** in `tests/test_docs_consistency.py`: the ADR-011 header
   shape, a lowercase slug, a Status marker, backticked paths that exist and
   are tracked, contiguous numbering.

## What ADR-011 settled and this ADR does not reopen

ADR-011 rejected option C - both checks plus a retry - with these words
(lines 51-54), quoted word for word:

> Near-zero security gain: a writer running as the same user who can write
> MAIN's outbox can also commit there, so the commit check adds no independent
> barrier. It does add a loss path, retry state, and up to 4 git calls at 60 s
> each per note per tick.

This ADR adds no git call and never re-checks the note's commit status; the
shape ADR-011 fixed for option C is untouched (lines 58-62). None of ADR-011's
reversal triggers (lines 92-97) has fired, and this ADR is not one of them:
it asks WHO the tree is, not WHETHER the note is committed.

## Proposed target: an untracked random beacon pinned by digest

Mechanism, in four steps:

1. MAIN writes 32 random bytes to a fixed filename in its outbox and never
   adds that file to git. The filename is agreed with MAIN and is not fixed
   here.
2. This tree commits sha256 of those bytes in one tracked file - the pin. The
   pin is a digest of a random value and of nothing else. No path for the pin
   file is fixed here.
3. `main_provenance`, only when a MAIN note is queued and only after the
   existing byte match has succeeded, reads the beacon relative to the row -
   the same outbox directory derived at line 2125 - hashes it once and
   compares with the pin. One file read and one hash per tick, no git, and
   nothing at all on an idle tick.
4. A missing or different beacon makes the note UNVERIFIABLE and retryable,
   so it falls under the deferral ADR-011 was amended with (lines 85-90):
   `defer_unverified` (line 3035) re-checks it for 3 counted checks 240 s
   apart or 900 s (`DEFER_MAX_CHECKS`, `DEFER_CHECK_SPACING_S`,
   `DEFER_MAX_AGE_S`), then releases it as UNVERIFIABLE data. Fail closed;
   liveness through the deferral.

Defends against: a typo or stale row (no beacon there); a row at another tree
(no beacon, or a different one); a swapped or corrupted map (the row then
points where the beacon is not); a crafted directory holding a byte-identical
copy of a note; a git clone of MAIN, because an untracked file is not cloned.

Does not defend against: a byte-identical filesystem copy of MAIN's tree that
carries its untracked files; a same-user actor who edits map, pin and outbox
together (settled by ADR-011); anything about the CONTENT of a note - the
beacon proves the location, and content provenance remains the byte hash.

Why it never meets ADR-011's cost words: the check is a file read, not a git
call. There is no git loss path, no 60 s timeout, and no retry state beyond
the deferral that already exists for the byte hash.

Rotation: MAIN re-issues the beacon when it re-roots or chooses to; this tree
re-pins the digest and commits. Until the re-pin lands, every MAIN note reads
UNVERIFIABLE - fail closed, liveness through the deferral. The order is: MAIN
writes the new beacon, this tree pins it, then MAIN sends notes. A re-pin is
an ordinary commit here and is reviewable by its diff.

What the pin leaks: the digest of 32 random bytes. There is no candidate list
to confirm against; a 256-bit random preimage has nothing to confirm.

## Hygiene ruling: what may be pinned in a public clone

A tracked digest of MAIN identity material is NO for any preimage that exists
independently - a remote URL, a checkout path, a commit id. It is YES only
for a digest of a random value generated for the purpose. Three reasons:

1. **One-way is not enough.** SHA-256 is one-way, but a low-entropy preimage
   is a confirmation oracle: anyone holding a candidate list - a hosting owner
   plus a repository name, or a layout they already know - confirms a guess in
   one hash. `tests/test_no_sibling_names.py` (lines 9-13) states the severity
   as the operator did: the names are not secrets and the tree only needs to
   be ambiguous about them. A confirmation oracle is exactly a loss of that
   ambiguity.
2. **Permanence.** A tracked pin lives in every prior blob of a public clone,
   and prior blobs are outside every guard (`tests/test_no_sibling_names.py`
   lines 12-13). A pin that turns out to be an oracle cannot be un-published.
3. **Gate-invisible.** No tracked guard reads a digest for what it encodes.
   `tests/test_machine_identity.py` (line 14) names the failure class: "The
   leak was not tolerated; it was invisible." A digest of a path passes the
   sibling-name sweep and the identity sweep mechanically.

A root-commit digest is a special case: its leak class depends on whether
MAIN's repository is public, a fact this tree must not record. A design whose
safety rests on an unrecordable fact is rejected.

## Rejected and recorded as settled

- **a1 - tracked digest of MAIN's remote URL or root commit, read by git at
  tick time.** Best argument: it catches a row that was already wrong at pin
  time, because git reads the identity from MAIN's tree rather than from the
  row. It is NOT option C - it asks who the tree is, not whether the note is
  committed - so criterion 2 does not reject it. Rejected on criterion 3: a
  URL digest is a confirmation oracle, and a root-commit digest's safety rests
  on an unrecordable fact. Also: a same-user actor who can repoint the row can
  clone MAIN, so a1's gain over a no-git check is one case bought with git at
  tick time.
- **b2 - tracked digest of the normalised MAIN row value (runner-up).** Best
  argument: takeable now, zero git, zero cross-tree ask, and a path digest
  confirms nothing to anyone who does not already know the layout - whom the
  sibling-name guard says it never protected against. Lost because a tracked
  oracle in a public repo is permanent and gate-invisible (reasons 2 and 3
  above), and the same protection against accidental corruption is available
  without tracking anything (see the note below).
- **b1 - tracked digest of the whole map.** Same ground as b2; a multi-row
  preimage of paths and codenames is still identity material.
- **c - quorum between `main_provenance` and `verify_main` at runtime, fail
  closed on disagreement.** Settled by ADR-011: it is option C in substance
  (lines 51-54), its shape is fixed at lines 58-62 "so it is not argued
  again", and both checks read the same row so their agreement proves nothing
  about it (lines 72-76). Recorded as settled, not re-proposed. No reversal
  trigger has fired.
- **Note, not a candidate, not proposed.** A no-cross-tree tick-time check
  would have to keep its pin UNTRACKED and per host, written through
  `core/atomic_io.py` beside the map; it would catch a swapped or corrupted
  map at one sha256 per tick and nothing a same-user actor does. The operator
  may choose it (ask 4); this ADR does not propose it.

## Interim - d: status quo plus a read-only session-start probe

Until the asks below are answered: at session start, a read-only probe
reports whether the resolved MAIN outbox exists, its file count, its newest
filename, and the sha256 of the map's bytes; the operator compares these by
eye with the previous session's values, kept under the gitignored
ops/loop/control/ directory. Session cadence only - it catches drift when a
human looks and nothing between sessions. No responder change, no git, no
leak, no kit change. Where the ritual is encoded is the accepting session's
choice.

## Timing

Tick-time gate, run only when a MAIN note is queued and after the byte match,
so idle ticks pay nothing. A MATCH is a tick-time event and an instruction
acted on between sessions cannot be un-acted; a check that ran only at
session start would see the row after the note had been obeyed. A
session-time arm in the test suite that skips when the map is absent - as it
is in CI and in every fresh clone - is a complement, never a substitute.

## Operator asks

In the asks below, "ruling (1)" is the Hygiene ruling section above,
"ruling (2)" is the Timing section above, and "REJECTED" is the Rejected and
recorded as settled section above.

1. May this tree arrange a2 with MAIN - an untracked random 32-byte beacon at
   a fixed filename in MAIN's outbox, re-issued when MAIN re-roots? Halt
   clause (c): the ask goes to the operator or arrives as a verified MAIN
   note; this tree does not send it by note.
2. Confirm ruling (1): no tracked digest of a URL, path or commit id, ever;
   only a random beacon's digest may be tracked.
3. Confirm ruling (2): tick-time gate when a MAIN note is queued, plus a
   session-time arm as complement.
4. Pending 1: is interim d sufficient, or does the operator want the untracked
   per-host map pin described under REJECTED (operator's choice, not
   proposed)?
5. Numbering: this ADR takes the number after the ADR that lands with it or
   before it; if that one does not land, this file and its header line are
   renumbered to the next free number and nothing else changes.

## Consequences

- No runtime change while Proposed. `main_provenance` and its verdict set are
  unchanged.
- Nothing under `ops/fleet_kit/` changes under any outcome of this ADR;
  `verify_main` stays adoption-only per ADR-011.
- The ROADMAP row gains a pointer to this file. Its LIMIT stands, narrowed: a
  byte check cannot tell MAIN from a copy, and this design tells MAIN from a
  git clone, not from a filesystem copy.
- If accepted, one tracked file holding a single digest of random bytes is
  added here, and one re-pin commit follows each beacon rotation.
- Until an acceptance, the interim ritual is the only control, and it runs at
  session cadence.

## What would accept this, and what would reverse it

Accept: a yes on asks 1 and 2, then a TDD code slice behind the ADR-011
deferral - failing arms first in `tests/test_responder_main_provenance.py`
for a missing beacon, a different beacon and a matching beacon, plus a
non-vacuity arm proving the pin is read from the tracked file and never from
the map.

Reverse: MAIN's outbox becoming a tracked-only location, where an untracked
beacon cannot live; or a SHA-256-verified MAIN note ordering a different
identity mechanism.

Hygiene, stated for the next reader: this ADR names MAIN by codename only,
names no other tree, quotes no URL, commit id, machine path or map value,
and spells the gitignored map ops/moon_sync_repos.json and the control
directory without backticks because `tests/test_docs_consistency.py`
requires every backticked path to exist and to be tracked.
