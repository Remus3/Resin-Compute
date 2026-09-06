# ADR-009: No per-file licence headers and no SPDX identifiers

**Status:** Accepted, 2026-09-06
**Closes:** the deferral recorded in ADR-006's Consequences, which said per-file
headers were "deliberately NOT added yet"

## Context

ADR-006 chose GPL-3.0-or-later and then deferred one thing: whether every source
file should carry a short licence header or an SPDX identifier. It was deferred
honestly - the wording was that a header on every file is churn better done in
one deliberate pass than half-applied.

Going public is the trigger to settle it. A deferral that survives publication
stops being a deferral and becomes an unexamined default, and an unexamined
default is exactly what ADR-006 was written to replace when it found the README
saying "Private. No licence granted." So the answer here is a ruling, not another
"not yet".

### What was measured, in this worktree, on 2026-09-06

- **80 tracked `.py` files and 10 tracked `.js` files**, 90 together
  (`git ls-files '*.py' | wc -l`, and the same for `*.js`). Measured at commit
  `e95a71c`. An earlier draft of this ADR said 78 and 88; that was measured
  before this session's two new test modules landed, and it is corrected here
  rather than quietly - a stale count in a decision document is the same defect
  class this session spent its time removing.
- **Zero SPDX identifiers in any source file.**
  `git grep -n "SPDX-License-Identifier" -- '*.py' '*.js'` returns 0 matches.
  An earlier draft claimed zero matches TREE-WIDE, which was self-refuting: the
  sentence asserting it contained the string, so the grep returned that line.
  The only occurrences of the identifier anywhere in this repository are in this
  ADR, discussing it. Stated this way the claim survives being checked.
- `LICENSE` is 674 lines. **`END OF TERMS AND CONDITIONS` is at line 621**, and
  **"How to Apply These Terms to Your New Programs" is at line 623.** The
  header-recommending appendix sits AFTER the end of the terms. That placement
  makes it an ADVISORY APPENDIX, not a condition of the grant.
- Its own wording is advisory, at `LICENSE` lines 629 to 632: "It is safest to
  attach them to the start of each source file", and each file "should have at
  least" the copyright line and a pointer. Safest and should, not must.
- **GPL-3 section 5(b), at `LICENSE` lines 217 to 220, binds "the work", not each
  file** - and it binds a MODIFIER conveying a modified version, not the original
  author. This project is the original author and conveys no modified version of
  someone else's program.
- The FSF's own SPDX guidance positions the identifier as ACCOMPANYING the full
  notice, not replacing it. REUSE's per-file MUST is a condition of REUSE
  COMPLIANCE, which is a separate specification this project has not adopted, not
  a condition of GPL compliance.

### The conclusion those measurements support

**The project is BELOW BEST PRACTICE, NOT NON-COMPLIANT.** An independent licence
gate reached that conclusion twice, on separate passes. Two agreeing passes are
not evidence on their own - ADR-007 says so - but here the shared input is the
shipped `LICENSE` text itself, and re-reading that input at the line numbers above
is what actually settles it. The agreement did not change the decision; the line
numbers did, and they strengthen it.

The outbound licence attaches at the REPOSITORY level, through `LICENSE` and
`NOTICE`, both present and consistent. `tests/test_licence_posture.py` pins the
`LICENSE` sha256 and checks that the declaration agrees across `LICENSE`,
`NOTICE`, `README.md` and `shell/package.json`. Four files that must not
disagree, guarded by a test, is a stronger consistency property than 90 files
that must not disagree, guarded by nothing.

## Decision

**Do not adopt per-file GPL headers, and do not adopt per-file SPDX identifiers.
The licence attaches at the repository level through `LICENSE` and `NOTICE`, and
that is where it stays**, with the re-open triggers below naming the exact
circumstances that would change the answer. This is a ruling on the merits, not a
further deferral: the project is below best practice and is not non-compliant,
the appendix that recommends headers sits after `END OF TERMS AND CONDITIONS` and
recommends rather than requires, and section 5(b) binds the work and the modifier
rather than the file and the author. Nothing in GPL-3 conditions the grant on a
per-file notice for an original author distributing their own repository whole.

### Why, stated as the two costs that decide it

**The cost of adopting.** Roughly 90 files of churn, and the churn is not free
here: this tree runs on `file:line` citations. The docs, the ledger and the ADRs
all cite line numbers - this very ADR cites six of them - and a blanket header
insertion shifts every citation in every file it touches, in one commit, with no
test that would notice. It buys no compliance that `LICENSE` plus `NOTICE` do not
already provide.

**The cost of omitting, recorded honestly rather than argued away.** A single
file copied OUT of this tree carries no licence signal with it. Someone who
receives `core/atomic_io.py` alone, without the repository around it, has no
indication of its terms. That is a genuine loss. It is also narrow - this project
is distributed as a repository, not as loose files - but it is real, and it is
the reason this decision has re-open triggers rather than being closed for good.

## Re-open triggers

Any one of these makes per-file identifiers load-bearing and reopens this ADR.

- **The project seeks REUSE compliance or a REUSE badge.** Per-file identifiers
  are a condition of that specification. Adopting REUSE is a decision that
  carries this one with it.
- **Outside contributions start arriving at scale**, so that MODIFIERS other than
  the original author exist and section 5(b)'s obligation begins binding someone
  other than us.
- **Any file is routinely distributed on its own**, outside the repository - a
  snippet published as a gist, a module vendored into another project, a single
  script shipped by itself.
- **A downstream packager or distribution requires SPDX identifiers.** Several
  do. The requirement would arrive from outside and would not be negotiable.
- **The project ever dual-licenses.** Per-file identifiers stop being cosmetic
  the moment two licences coexist in one tree, because then the file is the only
  place the answer can live.

## Consequences

- ADR-006's Consequences section is now settled rather than open. Its wording
  stands as written - it recorded a deferral, and this is the ADR that ends the
  deferral. ADR-006 is not edited.
- The ROADMAP item asking for this decision is answered by this ADR rather than
  by a header sweep. No source file changes.
- Every `file:line` citation in the docs, the ledger and the ADRs stays valid.
  That is a benefit of the decision, and it is also the reason a future adoption
  pass must be a single deliberate commit that re-checks those citations.
- If a re-open trigger fires, the work is a one-pass sweep across all tracked
  source files, and per this tree's sweep rule it needs two guards: one asserting
  every file carries the identifier, and one asserting nothing that should NOT
  carry it was rewritten - vendored text, `LICENSE` itself, and generated files.

## Rejected

- **Full FSF header blocks in all 90 files.** The maximal option, and the one the
  appendix describes. Rejected on the cost above: it invalidates every `file:line`
  citation in the tree at once and buys no compliance the repository-level files
  do not already supply.
- **SPDX one-liners only, without the notice.** Cheaper, and it looks like the
  modern answer. Rejected because the FSF positions the identifier as
  accompanying the full notice, not replacing it, so a bare identifier is a
  half-measure that satisfies neither the appendix's stated purpose - warranty
  exclusion at the top of the file - nor REUSE, which needs copyright lines too.
- **Headers on a subset - entry points, or public modules only.** Rejected, and
  it is the worst option of the three. Partial coverage reads as a deliberate
  statement that the un-headered files are differently licensed or are not
  covered, which is a stronger and more damaging signal than the current
  consistent silence.
- **Deferring again.** ADR-006 deferred once, legitimately, before publication.
  Deferring past publication converts a decision into a habit, and the point of
  this directory is that a decision nobody made is the most expensive kind.
- **Treating "below best practice" as "non-compliant" and acting out of
  caution.** Rejected because it is factually wrong at the line numbers cited
  above, and a project that churns 90 files to fix a violation that does not
  exist has learned nothing it can reuse.
