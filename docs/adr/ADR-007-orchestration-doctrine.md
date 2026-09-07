# ADR-007: Orchestrated multi-agent sessions as the default session shape

**Status:** Accepted
**Date:** 2026-09-06
**Relates to:** the "Session default" section of CLAUDE.md, which is this
decision stated as a rule rather than argued

## Context

Until now a session here was one thread doing everything in line: reading,
planning, editing, running both suites, and grading its own output. Nobody
decided that. It is what happens when nobody decides.

The failure mode is not slowness. The thread that produced a change is the worst
available judge of whether it is correct, because it grades the result against
its own memory of what it intended rather than against the tree, and that
confirmation is free and worth what it costs. The same thread also accumulates
every detail it has touched, so its context is full of things that stopped
mattering by the time it merges, and the operator's session is blocked for the
duration of every suite run.

This tree already carries a rule that presupposes the fix: never trust a
subagent's claim about test counts, green CI or file existence without an
independent probe. That assumes subagents, an independent prober, and someone
holding the plan while they run. The shape it assumes was never written down. A
read-only investigation of Sibling-A and of Sibling-C on 2026-09-06
supplied the evidence below, including one measurement that reverses the obvious
conclusion about worktrees.

## Decision

**Every session is orchestrated, multi-agent, self-adjudicating and
self-adversarial by default.** Choosing that shape needs no justification.
Departing from it does, and the departure is recorded. The only exception is
genuinely trivial work - a one-line cosmetic edit, a doc typo, a conversational
answer - and substance decides, not file count.

**The main thread reads, plans, dispatches, merges and reports.** It does not run
long builds, long suites or wide sweeps in line. That is what keeps the
operator's session available for querying and redirection while work proceeds.

### The four properties, and why each is load-bearing

**ORCHESTRATED.** One merger holds the plan and the merge, and work decomposes
into disjoint slices BEFORE any of it starts. Decomposition after the fact is not
decomposition, it is conflict resolution. The merger's context stays small on
purpose: it holds the plan and the seams, never the implementations.

**MULTI-AGENT.** Slices run in parallel on non-overlapping files. The reason is
not throughput. Parallelism is what FORCES a write-list to be declared, and a
declared write-list is the only thing that makes disjointness checkable at all.
So disjointness is a precondition asserted before dispatch - print the union of
the write-lists, assert no path appears twice - not a hope. An undeclared
write-list is a merge conflict that has happened and not been noticed.

**SELF-ADJUDICATING.** A distinct agent decides between competing outputs against
criteria restated BEFORE the candidates are read. The agent that produced a thing
never grades it. Restating the criteria first is the anti-taste device: an
unstated criterion is how a decision becomes taste, and taste is unarguable. The
candidate is frozen before dispatch, pinned at a SHA or a worktree, because a
tree that edits itself mid-verdict makes the ruling a statement about no state at
all.

**SELF-ADVERSARIAL.** Findings and done-claims get an independent pass whose job
is to REFUTE them, defaulting to refuted when uncertain. Load-bearing because the
thing this shape exists to prevent is a confident wrong done-claim, and only an
agent rewarded for finding one will look. It is also the owner for the
independent probe the verification rule demands but never assigned to anybody.

### Agreement between two agents is not evidence

The least intuitive supporting rule and the one most worth writing down. Two
agents agreeing tells you they share a premise, not that the premise is true.
When two agree, the thing to test is their SHARED INPUT, not the conclusion they
both drew from it.

The consequence is a rule about how refuters are spawned. They get DISTINCT
LENSES - correctness, licence, does-it-reproduce, resource lifetime,
scope-and-siblings - and never N identical skeptics. N copies of one skeptic is
one skeptic at N times the cost, and worse, because the N agreements read as
corroboration and the rule above says they are not. The licence lens is not
optional in this tree specifically: ADR-002 and ADR-006 make
`docs/LICENSE_NOTES.md` the sharpest constraint on it.

### Independence is a prompt-level property, not a vendor-level one

Stated explicitly because the intuition runs the other way. If you want an
independent review, ask a different model. That is the obvious move and it is
wrong.

Sibling-C ran a two-vendor loop and then rejected it. Operator decision,
2026-08-01, recorded in that tree's adjudicator module: independence comes from
THE PRODUCER NOT GRADING ITS OWN WORK, and a second vendor supplies nothing else.
A second vendor grading its own output is exactly as dependent as the first. A
same-vendor agent that never saw the producer's reasoning is independent in the
only sense that matters here. **Do not re-add a second vendor for "independent
review".** It is a cost and a coordination surface that buys nothing this shape
does not already have. Read-only is enforced the same way, by mechanism rather
than promise: grading agents are defined WITHOUT edit tools, so one that decides
to help cannot.

### A proven-disjoint write-list does NOT make worktrees optional

The strongest single piece of evidence in this record, and it is measured rather
than argued. It is recorded in Sibling-A's own memory file and was read there on
2026-09-06.

A disjointness proof bounds where agents DECLARE they will write. It bounds
nothing about TRANSIENT mutation, and transient mutation is not a corner case, it
is what correct TDD looks like. A builder has to watch a test fail before it can
trust the test, and the cheapest way to see red is to break the thing under test.
So builders reach outside their write-list, break a file, observe the failure and
restore it - and they do not classify any of that as "writing", because when they
are finished nothing has changed.

**Two builders did exactly that in one Sibling-A session.** Both restored
correctly and left no residue, so the proof was never violated in the sense it
was written to mean. Both nonetheless turned an unrelated suite red WHILE A
VERIFIER WAS MEASURING IT, and that verifier's reading described a tree which had
already stopped existing.

Adopted consequence: **isolate by worktree wherever an agent WRITES.** Where a
shared tree is genuinely warranted the dispatch must say so, and must state that
every break-revert-observe cycle happens on a scratchpad COPY. Two corollaries,
both touching this tree's most-warned-about surface:

- `core.hooksPath` is SHARED git config, so inside a linked worktree it holds the
  MAIN checkout's absolute path. The rule that a fresh clone runs no hooks until
  `scripts/install_hooks.py` sets that path interacts with this directly, and the
  only valid test of a hook remains end to end.
- A worktree agent's commits often do not survive cherry-pick, so a
  `docs/LEDGER.md` entry cites the ITEM ID, the MERGED FILE and the TEST NAME.
  Never the slice SHA, which may not exist tomorrow.

## Consequences

- **Dispatch costs real overhead before any work happens:** a spec, a
  decomposition, an exact write-list per slice with no globs and no "and
  related", and the printed union asserted disjoint. Paying that afterwards is
  not cheaper; afterwards it is a conflict.
- **More files, and one block is deliberately duplicated.** The roster lives in
  `.claude/agents/`, the dispatch protocol beside it under `.claude/commands/`,
  and every agent definition repeats the doctrine inline, because **subagent
  context does NOT inherit the main thread's** - an agent that has never read
  CLAUDE.md will not honour a rule that only lives there. So changing the
  doctrine means sweeping the roster, and a sweep needs TWO guards: one asserting
  the old wording is gone, one asserting the legitimate neighbours SURVIVED. A
  sweep scoring full marks on the first by deleting the second guard's subjects
  has failed, which is what a blind find-and-replace does.
- **The suite is re-run AFTER the merge**, not only inside each slice. Slices
  that pass independently can fail together at the seam.
- **Verdicts are fixed strings, not prose**, so a claim can be matched rather
  than interpreted and an uncertain result cannot be rounded up. NOT REFUTED is
  the strongest thing an adversary may say; it never says confirmed.
- **This decision carries no runtime code.** `tests/test_docs_consistency.py`
  checks that this ADR is indexed and that its pointers resolve. Nothing else
  about the shape is machine-checked yet, which is stated rather than left to be
  discovered.

### Deliberately deferred, which is not the same as rejected

- **The unattended lane-queue driver.** Both sibling trees run one: a headless
  loop draining a queue of directives, one row per process so a crash costs one
  row, the driver owning every wait because an instruction a worker can
  rationalize past is not a mechanism. It is a whole subsystem and this tree has
  no queue to drain. Roadmap it; do not build it against a queue of one.
- **A frozen-file list plus an adjudicator grant route.** The candidates are
  obvious - `.githooks/`, `scripts/install_hooks.py`, `tools/precommit_gate.py`,
  `LICENSE` - but WHICH files are frozen is an operator decision rather than an
  agent's, and a freeze nobody agreed to is only an obstacle.
- **A lane mutex.** Sibling-C coordinates eight lanes and needs one. **This
  tree has one lane of work, and a lane registry with one entry is ceremony.**

## Rejected

- **Solo main-thread work, the status quo.** The producer grades its own output,
  the one arrangement guaranteed to miss the error class that matters most, and
  it parks the operator's session behind every long run.
- **A second vendor for "independent review".** Rejected on Sibling-C's
  measured 2026-08-01 finding above. Independence is prompt-level; a second
  vendor adds spend and a coordination surface and supplies none of it that the
  producer-does-not-grade rule has not already supplied.
- **Orchestration as an escalation, invoked when work looks big enough.** The
  judgement would be made by the very thread that would have to do the extra
  work, and it will reliably find the work small. Making the shape the default
  removes the discretion, which is the point; the trivial-work exception is
  deliberately narrow for the same reason.
- **A shared tree on the strength of a proven-disjoint write-list.** Refuted by
  the measurement above: the proof does not cover the mutation that caused the
  incident.
- **Adopting the sibling rosters and guards wholesale.** Both trees are larger
  and older, and several of their controls guard problems this one does not have
  yet. A copied control that guards nothing is indistinguishable, at a glance,
  from one that has stopped working.
