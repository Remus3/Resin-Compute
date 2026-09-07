# ADR-006: GPL-3.0-or-later as the outbound licence

**Status:** Accepted
**Date:** 2026-09-06
**Amends:** ADR-002, in one specific respect recorded below
**Supersedes:** README's "Private. No licence granted."

## Context

Two different licence questions exist in this repository and they had been
collapsed into one.

**INBOUND** - what may this project consume? Answered by ADR-002 and
`docs/LICENSE_NOTES.md`: nothing upstream is vendorable, the Enka client is
re-implemented from published protocol, and no game data is carried.

**OUTBOUND** - what may others do with this project? Never actually decided. The
README said "Private. No licence granted.", which is the default and is not a
choice.

The operator stated the requirement plainly: they do not intend to commercialize
it, and do not want it "downloaded + altered + commercialized by someone else."

### What the sibling projects do, and why that was the wrong pattern to copy

Measured 2026-09-06 on this machine: Sibling-A ships MIT, Sibling-D and
Sibling-B ship Apache-2.0. **Both permit commercial use and both permit closing the
source.** Following the house pattern would have delivered the exact outcome the
operator asked to prevent, which is worth recording because a house pattern is
normally the safe default and here it was the trap.

### CC BY-SA was asked about and does not do the job

The operator asked about CC BY-SA "or something close". Two problems, both
factual:

1. **CC BY-SA explicitly permits commercial use.** Attribution plus ShareAlike
   requires credit and requires derivatives to carry the same terms. It does not
   restrict selling. It would not have prevented the stated concern.
2. **Creative Commons themselves advise against CC licences for software.** They
   carry no patent grant, they draw no source/binary distinction, and they were
   not drafted for code.

The software licence that actually behaves the way CC BY-SA behaves - credit,
share-alike, commercial permitted, closing prohibited - is the GPL.

## Decision

**GPL-3.0-or-later.** `LICENSE` carries the verbatim text, `NOTICE` carries the
copyright line, and `shell/package.json` declares `GPL-3.0-or-later`.

Its practical effect, which is a deliberate compromise rather than exactly what
was first asked for:

- Someone MAY sell a product built on this.
- They MAY NOT close the source. Any distributed derivative carries GPL-3 and
  its source must be available.
- They MUST credit and MUST preserve the licence.

The operator chose this over PolyForm Noncommercial after seeing the tradeoff
stated. PolyForm would have barred commercialization outright, which is closer to
the literal request, at the cost of not being OSI-approved. GPL is universally
understood, and "they cannot take it closed" was judged the more valuable
protection than "they cannot sell it".

### "or-later" rather than "only"

Following the FSF's own recommendation. A GPL-3.0-only project cannot have its
licence updated without contacting every contributor; "or any later version"
leaves that door open. There is no downside for a project with one author.

### The verbatim text was verified, not pasted from memory

`LICENSE` was taken from a package on this machine, cross-checked against a
second independent copy from a different package - identical across all 674
lines except the FSF's own boilerplate year - and confirmed to be 7-bit ASCII so
it satisfies this tree's hard glyph rule. Its SHA-256 is
`8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`, which matches
the canonical published hash of the GPL-3.0 text.

## What this AMENDS in ADR-002, and what it does not

ADR-002 refuses to vendor `enka-py` and `ambr-py` and gives two reasons. This
decision dissolves exactly one of them.

**DISSOLVED: the copyleft-incompatibility objection.** ADR-002 says vendoring
either "would relicense this repo". That was true of a proprietary or permissive
tree. This tree is now GPL-3-or-later, so incorporating GPL-3 code is
straightforward and relicenses nothing that is not already so licensed.

**STANDING, and it is the reason that actually mattered:** every one of those
projects wraps HoYoverse-copyright game assets, statistics, text and item names.
A licence on a wrapper grants rights to that author's own code and compilation.
**It cannot grant rights to the underlying game data**, and no choice of outbound
licence here changes that by one word. `docs/LICENSE_NOTES.md` states this as the
blanket caveat and it survives untouched.

**Consequence, stated precisely so nobody over-reads this ADR:** the CODE of a
GPL-3 upstream is now legally combinable with this tree. The DATA it carries is
not, and the data was always the actual gate. ADR-002's chosen posture - vendor
no game data, re-implement the client from protocol - is unchanged and remains
correct. Nothing is to be vendored on the strength of this ADR alone.

## Consequences

- The repository may be published. Previously "no licence granted" meant nobody
  had any right to use it at all, which was the strongest protection available
  and also made the repo useless to anyone else.
- The GPL's obligations attach on DISTRIBUTION, not on private use. An operator
  running this on their own machine takes on nothing.
- **Per-file licence headers are deliberately NOT added yet.** The FSF recommends
  a short header in every source file. `LICENSE`, `NOTICE`, the README statement
  and the package metadata together make the licence unambiguous, and adding a
  header to every file is churn better done in one deliberate pass than
  half-applied. Recorded in ROADMAP rather than left implicit.
- `tests/test_licence_posture.py` guards both directions: that the outbound
  declaration stays consistent across `LICENSE`, `NOTICE`, README and
  `package.json`, and that the inbound posture from ADR-002 has not quietly
  eroded.

## Rejected

- **MIT or Apache-2.0**, the sibling house pattern. Permits closed
  commercialization, which is the specific outcome to prevent.
- **PolyForm Noncommercial 1.0.0.** Closest to the literal request and genuinely
  viable. Rejected by the operator in favour of copyleft after the tradeoff was
  laid out: not OSI-approved, so it is avoided on principle by some people and
  some corporate policies.
- **CC BY-SA / CC BY-NC-SA.** Not drafted for software; Creative Commons say so
  themselves. BY-SA also permits the commercialization at issue.
- **AGPL-3.0.** Its extra clause covers use over a network. This is a local
  loopback tool with no hosted surface, so the clause would add obligation
  without addressing anything the operator raised. Revisit only if a hosted
  version is ever built.
- **Staying "no licence granted".** Strongest protection, but it makes the
  project unusable and unshareable by anyone else, and the operator wanted a
  licence rather than silence.
