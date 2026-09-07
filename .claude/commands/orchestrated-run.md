---
description: The default session shape - recall, spec first, decomposition into provably disjoint slices, parallel dispatch, independent verification, adjudication, adversarial refutation, then merge and re-run the suites at the seam.
argument-hint: [the unit of work, e.g. "wire the teams panel to real roster data"]
---

# /orchestrated-run - the default session shape

Unit of work: $ARGUMENTS

Run EVERY phase, in order. Report the result you OBSERVE for each one. A phase
that produced nothing still gets a line saying so - a silently skipped phase is
indistinguishable from a phase that passed, which is the whole reason the
verdict vocabularies below are fixed strings rather than prose.

Per `CLAUDE.md` "Session default", this shape is the DEFAULT and needs no
justification. DEPARTING from it does, and the departure is recorded. The only
exception is genuinely trivial work: a one-line cosmetic edit, a doc typo, a
conversational answer. SUBSTANCE decides, not file count - a one-file change to
`engines/` is substantive, a five-file rename is not. The reasoning is recorded
in ADR-007.

**The main thread reads, plans, dispatches, merges and reports. It does NOT run
long builds, long suites or wide sweeps inline.** That is not a style
preference: the operator's session is the only place they can ask a question,
and a main thread blocked on a sweep is a session they cannot interrupt.
Background the long work, and never fabricate or predict a pending agent's
result - if the operator asks before it lands, say it is still running.

## The shape, and what was deliberately not ported

This is Sibling-A's dispatch protocol and Sibling-C's lane mechanism
adapted to this tree, not transcribed from either. Five things were dropped on
purpose, and each should stay dropped until the thing it guards exists here:

- **No frozen-file gate.** Sibling-A's phase 2 confirms that no slice touches a
  frozen file without an adjudicator grant. This tree has no frozen-file list,
  and declaring one is an operator decision rather than an agent's. The
  candidates are obvious - `.githooks/`, `scripts/install_hooks.py`,
  `tools/precommit_gate.py`, `LICENSE` - so when the operator names them, phase
  2 is where the check belongs.
- **No memory-projection recall tool.** Sibling-A phase 0 queries a projection
  tool over a memory store. Nothing of the kind exists here, so phase 0 names
  the four places that actually hold closed work in this tree. A phase that
  names a tool nobody has is a phase that gets skipped, and a skipped recall is
  how settled work gets rebuilt.
- **No lane registry and no mutex.** Sibling-C runs eight named lanes
  behind one mutual-exclusion lock. ResinCompute has one lane of work; a lane
  registry with a single entry is ceremony that then has to be kept accurate.
- **No machine truth-gate yet.** Sibling-C re-runs the suite from a claims
  JSON and exits non-zero on any claim it cannot reproduce, which is the right
  shape, because a verdict a machine computes cannot be rationalised by the
  agent claiming it. It is a tool, and a command doc cannot conjure one. Until
  it exists, phase 4's FIXED OUTPUT BLOCK is the substitute: a shape a reader
  can check at a glance, rather than prose a reader has to trust. Roadmap it.
- **No headless lane-queue driver.** Roughly 3400 lines over there, genuinely
  good, and it drains a queue this tree does not have yet.

What IS carried across, because it is the part that earns its keep: the
decomposition is PROVEN disjoint before anything starts, the agent that produced
a thing never grades it, and the suites run again after the merge.

## 0. Recall before building

Rediscovery - rebuilding closed work, re-pitching a settled decision, acting on
a stale doc - is the dominant failure mode of a cold session. This phase is the
defence, and it costs a minute.

- Read `NEXT_SESSION_PROMPT.md` if the operator pasted its block, then
  `git log --oneline -10`.
- Grep `docs/LEDGER.md` for the work in YOUR OWN WORDS, not in the words of the
  request. The ledger records what was MEASURED, so a hit there closes the
  question that a roadmap line only opens.
- Read `ROADMAP.md` for the open-work list, and `docs/adr/README.md` before
  re-litigating any past choice.
- Check the per-project memory directory named in `.claude/commands/done.md`
  section 8. A memory file with no index line is invisible; if you find one,
  say so.
- **If a ledger or ADR hit says this work is CLOSED, REFUTED or shipped, STOP
  and report that instead of building it.** That is the entire point of the
  phase.
- Read a decline reason before citing it. A decline reason goes stale faster
  than a count does, because the blocker it names may have been fixed.

## 1. Spec first, then act

- Dispatch `planner` from `.claude/agents/`. It emits the spec BEFORE any code
  exists, and it is read-only by construction rather than by promise.
- **Verify the spec against GROUND TRUTH before a single file is scaffolded.**
  Grep every cited `file:line`, list every cited file, run the code, hit the
  endpoint, read `git log`. Never scaffold against an assumed API surface; this
  tree already paid for one: an instruction to read a docs/ARCHITECTURE.md that
  has never existed survived in `CLAUDE.md` because nothing checked it, which is
  why `tests/test_docs_consistency.py` exists at all.
- Confirm the acceptance criterion is TESTABLE. "Works correctly" is not a
  criterion; "`tests/test_surface_render.py` gains an arm that fails on the old
  renderer" is.
- **If the work touches game data, a data source or anything outbound, dispatch
  `researcher` FIRST and treat its gate as blocking.** ADR-002 and ADR-006 make
  the licence posture this project's sharpest constraint, and
  `docs/LICENSE_NOTES.md` is the standing reference. Its vocabulary is
  `GATE: CLEARED` / `GATE: REFUSED` / `GATE: UNRESOLVED`, and **UNRESOLVED is
  treated as REFUSED downstream** - an unresolved licence question is not a
  reason to proceed carefully, it is a reason not to proceed.
- Do not re-derive gacha constants here or anywhere. They are verified in
  `docs/SPEC_SCAFFOLD.md` section 3, with the corrections in
  `docs/adr/ADR-003-forecaster-model.md`, and unverified cost figures are held
  out of `data/` by `docs/GOAL_SPEC_SEED_TEAM.md`.

## 2. Decompose into DISJOINT slices, BEFORE any work starts

This is the phase with teeth, and every item below is checkable rather than
aspirational. **An undeclared write-list is a merge conflict already** - it has
simply not happened yet.

- **Every slice declares an EXACT file write-list.** Literal paths only. No
  globs, no `surface/*`, no "and related files", no "plus its tests". A glob is
  a claim about files that do not exist yet, and two globs can overlap on a file
  neither author has thought about.
- **Every slice declares the seams it CONSUMES and the seams it PUBLISHES.** A
  seam is a name another slice depends on: a function signature, a JSON key, a
  dataclass field, a route, a port constant. `core/types.py` is the shared
  contract and is a merge surface, not a scratchpad - a slice that changes it
  publishes a seam that every other slice consumes, so it runs alone or first.
- **PRINT the union of all write-lists, and ASSERT that no path appears twice.**
  Print it in chat so the operator sees the same list you checked. Then check
  it mechanically rather than by eye - a twelve-path union is exactly the size
  at which reading is unreliable:

      sort <union-file> | uniq -d

  Written to a scratch file OUTSIDE the repository. **An empty result is the
  precondition. Any line it prints is an overlap, and the decomposition is
  wrong, not merely risky.** Fix it by merging the two slices, or by extracting
  the shared file into its own slice that runs FIRST and publishes a seam.
- **A seam consumer never starts before its producer publishes.** Sequence those
  slices explicitly and say why. Parallelism is the default, not the goal.
- **Record the decomposition before dispatching**, in the canonical block below.

### The canonical parallel block

The block is written in the dispatch directive, exactly this shape, one
`AGENT N: owns <paths>` line per slice:

```
CANONICAL PARALLEL BLOCK - BEGIN
AGENT 1: owns surface/model.py and tests/test_surface_model.py
AGENT 2: owns surface/render.py and tests/test_surface_render.py
AGENT 3: owns shell/lib/state.js and shell/test/lib.test.js
CANONICAL PARALLEL BLOCK - END
```

**PARALLEL FILE SETS ARE A CONTRACT, NOT A CLAIM.** The block is NORMATIVE. The
prose around it only DESCRIBES it, so when the two disagree the block wins and
the prose is the defect - fix the prose, and never quietly widen the block to
match a sentence.

- One line per agent, agents numbered from 1, paths joined by ` and `.
- Every path in the block is a path from that slice's write-list, and every path
  on that write-list is in the block. The block is the whole write-list or it is
  not a contract.
- If the block cannot be made disjoint, **do not silently sequence it.** Say in
  the report that the requested parallel shape was not disjoint, name the
  colliding path, and state what was run instead. A silent correction teaches
  the director nothing, and the same broken shape gets written next cycle.

## 3. Dispatch

- One `builder` per slice. **Worktree-isolate wherever an agent WRITES.**
- **The mechanism is `isolation: "worktree"` on the Agent tool call.** Naming
  the principle and then dispatching into the shared tree anyway is not a
  smaller version of following it - it is not following it. The parameter is
  the whole implementation; there is nothing else to do.
- **Measured HERE, on this protocol's first run (2026-09-06).** The four slices
  that built this file, the roster and ADR-007 were dispatched into the SHARED
  tree with no isolation. No work was lost and no write-list was violated, and
  it still cost accuracy in three of five agents: one reported a sibling slice's
  test suite RED when an independent probe showed it green (a mid-write
  snapshot), one measured a suite polluted by files it did not own, and one
  watched HEAD move and `CLAUDE.md` change underneath it mid-run. Every one of
  those is a FALSE report produced by the tree, not by the agent. An orchestrator
  that then believes any of them ships on a fiction.
- **A proven-disjoint write-list does NOT make worktrees optional, and this is
  measured rather than theoretical.** The proof bounds where agents DECLARE they
  will write. It bounds nothing about TRANSIENT mutation: a builder doing TDD
  properly has to watch a test fail, and the cheapest way to see red is to break
  something. Two builders in one sibling-tree session reached outside their
  write-lists, broke a file, observed the red and restored it. Both restored
  correctly and left no residue. Both nonetheless turned an unrelated suite red
  WHILE A VERIFIER WAS MEASURING IT.
- When a shared tree is genuinely warranted, **say in the dispatch that every
  break-revert-observe cycle happens on a scratchpad COPY**, never on the tracked
  file.
- **A fresh worktree has no hooks. `python scripts/install_hooks.py` is the
  first action in one**, per the `CLAUDE.md` hard rule: `core.hooksPath` is
  local config and is not cloned. Related trap: `core.hooksPath` is SHARED git
  config, so inside a linked worktree it holds the MAIN checkout's absolute
  path. Never treat a hook's PRESENCE as proof it fires.
- Each builder receives its slice goal, its EXACT write-list, its seams
  consumed and published, and its acceptance criterion. Nothing else. **The
  merger holds the plan and the seams, not the implementations** - that is what
  keeps its context small enough to hold the whole merge.

### The builder slice contract

Every builder dispatch carries these four, verbatim, because subagent context
does NOT inherit the main thread's:

1. **Restate the write-list before touching anything.** A builder that cannot
   restate it has not read it.
2. **If a change needs a file NOT on the list, STOP and report the seam
   collision.** Do not "just fix it" - the file belongs to another slice, and
   the fix lands as a conflict or, worse, as a silent overwrite at merge.
3. **Never `git add`, `git commit` or `git push` unless the orchestrator
   explicitly said to. The orchestrator merges.** A builder that commits has
   removed the merger's ability to sequence, to reject, or to hold a candidate
   frozen for adjudication.
4. **Follow TDD**: the failing characterization or regression test first, then
   the implementation, then both suites - `python -m pytest tests` and
   `python -m pytest agents/pity_engine`, separately, never `pytest .` from the
   root per `pytest.ini`.

Relay what matters from each agent's report. The operator does not see it.

## 4. Verify, independently

- Dispatch `verifier`. It re-runs the suites ITSELF and reports the counts IT
  observed this run. **A builder's own green report is an input to verification,
  never a substitute for it**, per the `CLAUDE.md` rule that a subagent's claim
  about test counts, green CI or file existence is not evidence.
- **Redirect the suite output to a FILE and read it back**, rather than reading a
  terminal tail. A wedged stdout pipe can feed you a stale tail that looks
  exactly like a fresh pass.
- Vocabulary, and **do not round any of these up to CONFIRMED**:
  `CONFIRMED` / `CONFIRMED WITH CORRECTIONS` / `REFUTED` / `UNVERIFIABLE`.
- Output is a FIXED BLOCK, not prose, so a reader can check it without parsing
  an argument:

```
VERDICT: <CONFIRMED | CONFIRMED WITH CORRECTIONS | REFUTED | UNVERIFIABLE>
tests:         <passed>/<failed>/<error>   (claimed <N>)
pity_engine:   <passed>/<failed>/<error>   (claimed <N>)
ruff:          <clean | N findings>
cited-files:   all-present | MISSING: <path>
git:           <clean|dirty>; HEAD <sha> <subject>
discrepancies: <one line each, or none>
```

- A count appears in that block and in the chat report. It does NOT get written
  into a doc: counts are not guarded, and a doc is not a source of truth.

## 5. Adjudicate with an agent that did not produce the work

- Dispatch `adjudicator`. **Its step 1 is to restate the CRITERIA, in priority
  order, BEFORE it looks at the candidates.** This is the anti-taste device: an
  unstated criterion is how a decision quietly becomes a preference.
- **Freeze the candidates before dispatch** - pin them at a SHA or in a
  worktree. A tree that edits itself mid-verdict makes the ruling a statement
  about no state at all.
- **The agent that produced a thing never grades it.** If only one candidate
  exists, the adjudicator still checks it against the criteria; it is not a
  rubber stamp.
- Ask explicitly for the COMMON-MODE risk: what shared doc, fixture or
  assumption do the candidates both depend on that neither of them tests?
- Output shape: `DECISION: <candidate>` plus the criteria table, `RUNNER-UP`
  plus its single best argument, `COMMON-MODE RISK`, `RESIDUAL`. **`SPLIT` and
  `NEITHER` are legal decisions** and are often the honest ones.

## 6. Adversarial refutation, with distinct lenses

- Dispatch `adversary` instances whose job is to REFUTE the finding or the
  done-claim, each **defaulting to REFUTED when uncertain**.
- Vocabulary: `REFUTED` / `NOT REFUTED` / `REFUTED (UNCERTAIN)`. **NOT REFUTED
  is the strongest thing an adversary may ever say. It never says confirmed.**
- **Spawn DISTINCT LENSES, never N identical skeptics.** Diversity catches
  failure modes redundancy cannot. The five that fit this tree:
  - **correctness** - does the change do what the spec said, on the edge cases;
  - **licence and data posture** - ADR-002, ADR-006, `docs/LICENSE_NOTES.md`.
    Nothing under `data/` came from a licensed source, `data/fixtures/` is
    hand-authored only with nothing vendored, and a real cost table or banner
    list appearing there is a
    stop-and-ask;
  - **does-it-reproduce** - run the cited command in a clean shell and read the
    exit code, do not read the claim;
  - **resource lifetime** - what binds a port, opens a file or starts a thread,
    and what closes it. `core/ports.py` owns every port this repo binds, and
    ADR-004 records why a band is verified against the owning project's registry
    in source rather than against a live scan;
  - **scope and siblings** - per `CLAUDE.md`, a bug is not fixed until every
    sibling case with the same root cause is fixed with it, and a data fix is
    not done until already-corrupted records are backfilled.
- **A sweep needs TWO guards, not one:** one asserting the bad thing is gone,
  and one asserting the LEGITIMATE neighbours SURVIVED. A sweep that scores
  100 percent on the first by deleting the second's subjects has failed, and
  that is exactly what a blind find-and-replace does.
- **Agreement between two agents is not evidence.** Two agents deriving from one
  stale doc or one fixture are wrong the same way. If two agree, go find their
  SHARED INPUT and test THAT.
- Independence is a PROMPT-LEVEL property, not a vendor-level one. It comes from
  the producer not grading its own work. Do not add a second vendor for
  "independent review".

## 7. Merge, re-run at the seam, and report

**The orchestrator merges.** Slice by slice, in seam order, reading each
builder's report rather than re-deriving its work.

- **Re-run the suites AFTER the merge.** This is the phase's reason to exist:
  slices that passed independently can fail TOGETHER at the seam, and the seam
  is the one place no builder was looking.

```
python -m ruff check .
python -m pytest tests
python -m pytest agents/pity_engine
```

- If any slice touched `surface/` or `shell/`, also run
  `python scripts/qa_companion.py` and `cd shell && node --test`, and confirm
  that `/ui-audit` already ran and returned `AUDIT: PASS` INSIDE that slice.
  Per `.claude/commands/ui-audit.md`, the audit runs before the commit, so
  discovering at merge time that it never ran is a process failure to report,
  not a step to run late.
- A `docs/LEDGER.md` entry cites the ITEM, the MERGED FILE and the TEST NAME -
  **never the slice SHA.** Worktree-agent commits frequently do not survive
  cherry-pick, so a SHA-based pointer is a citation that stops resolving.
- Report, in this order: what each slice delivered; the verifier's fixed block;
  the adjudicator's decision plus the runner-up's best argument; every adversary
  verdict; and every UNRESOLVED item.
- **Anything unverified is labelled unverified.** Do not round an uncertainty up
  to a claim, and do not report a subagent's number as your own observation.
- Finish with `/done`, which is the ritual in `.claude/commands/done.md`.

## Safety rails

- NEVER force-push, NEVER `--amend`, NEVER `--no-verify`. If a hook rejects a
  commit, fix it and make a NEW commit.
- 7-bit ASCII in everything authored, including the dispatch text and the chat
  report. No em-dashes, no en-dashes, no smart quotes. `tools/precommit_gate.py`
  is the backstop and `python tools/precommit_gate.py --scan-files <paths>`
  checks a file before it is staged.
- Under Git Bash write `taskkill //F //PID <pid>`. A lone `/F` is rewritten to
  `F:/` by MSYS path conversion, and it fails SILENTLY when redirected.
- Never `Stop-Process` on Windows, and always `py_compile` before a restart -
  a syntax error crashes silently under `pythonw.exe`.
- Never surface a raw API or error string on a user-facing surface. Catch it,
  render a friendly degraded state, log the raw error.
