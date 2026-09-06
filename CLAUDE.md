# ResinCompute - Agent Context

Genshin Impact progression, resource economics, goal planning and roster
optimization. Headless-lane first. Python 3.11, stdlib-only at runtime.
Built on the Riot Commander blueprint (ADR-001).

Two-tier naming, mirroring Riot Commander / Daemon Slayer:
**ResinCompute** is the repo, **PityEngine** (`agents/pity_engine/`, HTTP `:8790`)
is the pure deterministic compute engine inside it.

> **Read at session start:** `README.md` - `docs/SPEC_SCAFFOLD.md` - `ROADMAP.md`
> **Before planning any character build:** `docs/GOAL_SPEC_SEED_TEAM.md` - it
> stamps every claim verified / unverified / time-sensitive, and the unverified
> cost figures must not reach `data/`.
> **Before adding any data source:** `docs/LICENSE_NOTES.md`
> **Before re-litigating a past choice:** `docs/adr/README.md`

## Hard rules

- **Always `py_compile` before restart.** Syntax errors crash silently under
  `pythonw.exe`.
- **Atomic writes only:** `tmp.write_text(...); tmp.replace(target)`. Use
  `core/atomic_io.py`; it is the only sanctioned state-write path. Readers poll
  mid-write.
- **Never `Stop-Process` on Windows.** Use `taskkill /F /PID`.
  **Under Git Bash write `taskkill //F //PID <pid>`.** MSYS path conversion
  rewrites a lone `/F` into `F:/` and the command fails with
  `Invalid argument/option - 'F:/'`. Measured 2026-09-06, and it fails SILENTLY
  when the call is redirected to /dev/null, so a process you believe you killed
  is still running. Same root cause as the quoting rule below.
- **No em-dashes or en-dashes, ever.** 7-bit ASCII in all authored text: code,
  comments, docstrings, `.md`, commit messages, chat output. Use ` - ` for a
  clause break. Also no smart quotes (U+2018 U+2019 U+201C U+201D).
  **Why:** Windows PowerShell 5.1 ANSI-decodes a no-BOM `.ps1`, turning a UTF-8
  em-dash inside a double-quoted string into a smart quote that the tokenizer
  treats as a string terminator, cascading into a parse failure. It is also a
  standing operator style rule.
- **Never add a `Co-Authored-By: Claude` trailer**, and never file its absence as
  a defect. `.githooks/commit-msg` strips it per operator policy.
- **Git hooks are the AUTHORITATIVE gate, and a fresh clone has NONE.**
  `core.hooksPath` is local config and is not cloned, so a new clone runs zero
  hooks until someone sets it, which defeats the tracked `.githooks/` directory
  entirely. **First action in any fresh clone: `python scripts/install_hooks.py`.**
  Never treat a hook's PRESENCE as proof it fires; the only valid test is
  end-to-end - stage a banned glyph, attempt a real commit, assert HEAD unchanged.
- **Commit messages with special characters:** use `git commit -F <tmpfile>`
  (ASCII-only) or a single-quoted here-string. Never a double-quoted here-string
  or a piped string - BOM and ANSI-mangle risk, same root cause as the dash rule.
- **State assumptions explicitly before coding.**
- **Live-state-first.** Derive state from the current response only. No
  hardcoding, no stale cache treated as truth.
- **Never surface a raw API or error string** in any user-facing surface. Catch
  it, render a friendly degraded state, log the raw error.
- **Vendor no game data.** See `docs/LICENSE_NOTES.md`. `data/fixtures/` is
  HAND-AUTHORED only - nothing upstream is vendored. Do not call it "synthetic":
  two of its three files are verified public game facts typed in by hand, and
  only `enka_sample_profile.json` is invented. Corrected 2026-09-06; the old
  wording was false about two of the three files.

## Layout

| Path | Role |
|---|---|
| `core/types.py` | The shared contract. Changing it affects every slice - treat as a merge surface, not a scratchpad |
| `core/` | Primitives: atomic io, logging, config, ledger, resin, domains |
| `agents/pity_engine/` | PityEngine. Pure, deterministic, versioned. Own test suite |
| `engines/` | Objective DAG, scheduler, recommendation solver. Mechanism, not data |
| `ingest/` | Enka client and mapper, re-implemented from protocol |
| `headless/` | The headless lane: `runner.py` and the job registry |
| `ops/` | Supervisor, health file, Windows scheduled task |
| `tests/` | Application suite |

## Testing

Two suites, run **separately**. Never `pytest .` from the root.

```
python -m pytest tests
python -m pytest agents/pity_engine
python -m ruff check .
python -m mypy
```

Do not restate a suite count in any doc. Counts are not guarded and a doc is not
a source of truth. Measure with `python -m pytest tests --collect-only -q`.

## TDD

Feature work and bug fixes follow TDD: write the failing characterization or
regression test first, implement, then verify both suites before committing.

## Verification discipline

Verify against ground truth before asserting anything is done, fixed, broken or
missing. Re-probe the live source: run the code, read the file, hit the endpoint.
Never trust a stale doc, an assumption, or another agent's unverified output.
Before using any API, field or file shape, confirm it exists and cite where.
Report the exact result observed, with counts or output. No hedging, no
"should work".

Never trust a subagent's claim about test counts, green CI, or file existence
without an independent probe.

## Bugs and data

Root-cause first: reproduce with a failing test where practical, grep for every
sibling case with the same root cause and fix them together, then make the
minimal fix. A data fix is not done until already-corrupted records are
backfilled, not just future ones prevented.

## Python conventions

When adding a required field to a dataclass, append it at the END with a default.
A mid-class required field breaks every existing positional construction and its
tests.

## Domain constants

**Do not re-derive gacha constants from memory or from a web search.** They are
verified and recorded in `docs/SPEC_SCAFFOLD.md` section 3, with the three
corrections to the original brief recorded in `docs/adr/ADR-003-forecaster-model.md`.
Three things are easy to get wrong and are regression-tested:

1. The 50/50 has been **55.000% consolidated** since version 5.0 (Capturing
   Radiance), not 50%. The engine models 0.52106 per roll plus a forced win at
   three consecutive losses.
2. The weapon soft-pity ramp **saturates at pull 77** under a 7% increment. Any
   claim it runs to 79 or 80 is arithmetically impossible.
3. 1.600% is `1 / E[wishes per 5-star]`, a long-run average. It is **never** a
   per-wish Bernoulli parameter. Forecasts use an absorbing Markov chain.

## Enka upstream policy

Enforced in code, not just prose, in `ingest/enka_client.py`:
custom User-Agent required, `ttl` honoured on every response, no UID enumeration.
Real endpoint is `https://enka.network/api/uid/{uid}/`.

Payload traps, each with a regression test: `avatarInfoList` is absent when the
showcase is closed; `talentIdList` is a **missing key** at C0 rather than an empty
list; `skillLevelMap` excludes constellation-granted levels which live in
`proudSkillExtraLevelMap`; `affixMap` sits at `equipList[].weapon.affixMap` with
range 0..4, so presented refinement is that plus one.

## Restart workflow

```
echo restart > restart_trigger.txt
```

Verify by reading `ops/runtime/health.json` and confirming a new `pid` and
`alive=true`. Do not verify by looking at a window.

## Session default - the shape, not an escalation

**Every session is orchestrated, multi-agent, self-adjudicating and
self-adversarial by default.** Choosing this shape needs no justification.
Departing from it does, and the departure is recorded. The only exception is
genuinely trivial work: a one-line cosmetic edit, a doc typo, a conversational
answer. Substance decides, not file count.

- **Orchestrated.** One merger holds the plan and the merge. Work decomposes
  into disjoint slices BEFORE any of it starts. The merger's context stays
  small: it holds the plan and the seams, not the implementations.
- **Multi-agent.** Slices run in parallel on non-overlapping files, worktree
  isolated wherever they write. Disjointness is a PRECONDITION checked before
  dispatch, not a hope. An undeclared write-list is a merge conflict already.
- **Self-adjudicating.** A distinct agent decides between competing outputs
  against stated criteria. **The agent that produced a thing never grades it.**
  Freeze the candidate before dispatch - a tree that edits itself mid-verdict
  makes the ruling a statement about no state at all.
- **Self-adversarial.** Findings and done-claims get an independent pass whose
  job is to REFUTE them, defaulting to refuted when uncertain.

**Agreement between two agents is not evidence.** Two agents can share one wrong
premise. If two agree, find their shared input and test THAT. Spawn refuters
with DISTINCT LENSES - correctness, licence, does-it-reproduce, resource
lifetime, scope-and-siblings - never N identical skeptics.

**The main thread reads, plans, dispatches, merges and reports.** It does not
run long builds, long suites or wide sweeps inline. The operator's session stays
free for querying and redirection.

Independence is a PROMPT-LEVEL property, not a vendor-level one: it comes from
the producer not grading its own work. Do not add a second vendor for
"independent review".

The roster lives in `.claude/agents/`, the dispatch protocol in
`.claude/commands/orchestrated-run.md`, and the reasoning in ADR-007. Every
agent definition repeats this section inline, because subagent context does NOT
inherit the main thread's.

## Session workflow

Scoped sessions - each focused task is one session.
- **Start:** read this file, `README.md`, `ROADMAP.md`, `docs/LEDGER.md`,
  and `git log`.
- **End:** run both suites, commit, push, update `ROADMAP.md`, then print
  the next-session prompt inline in a fenced block.
- **That fenced block is the LAST thing in the message.** No "what was done
  this session" review after it, no sign-off, no offer to continue. Any
  banner or shipped-summary goes BEFORE the block. The operator selects it
  by hand to paste into a cold session, so trailing prose is text they have
  to select around. Operator instruction, 2026-09-06.
