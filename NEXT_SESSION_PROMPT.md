# Next session prompt

Copy the block below verbatim into a new session. Everything above and below it
is context for a human; the block is what the agent needs.

---

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

THE TASK THIS SESSION: QA the repository for going PUBLIC, README first.

BOOTSTRAP, in this order:
  CLAUDE.md, README.md, ROADMAP.md, docs/LEDGER.md, docs/SPEC_SCAFFOLD.md,
  docs/adr/README.md, and `git log --oneline -12`.
SPEC_SCAFFOLD.md is the authoritative build contract and carries every verified
domain constant. Do NOT re-derive gacha numbers from memory or a web search, and
do not "fix" them against the originating brief, which was wrong in three places
that are now regression-tested.

READ THE "Session default" SECTION OF CLAUDE.md BEFORE DISPATCHING ANYTHING.
The default shape here is now orchestrated, multi-agent, self-adjudicating and
self-adversarial. The main thread reads, plans, dispatches, merges and reports;
it does NOT run long sweeps inline. Seven roles live in .claude/agents/. The
dispatch protocol is /orchestrated-run. The reasoning is ADR-007.
WORKTREE-ISOLATE EVERY AGENT THAT WRITES: pass isolation: "worktree" on the
Agent call. Measured last session - four slices dispatched into the shared tree
lost no work but produced three FALSE reports, including one agent reporting
another's suite red when it was green.

RUN THE THREE QA GATES FIRST, BEFORE ANY OTHER WORK. They exist because each one
already caught real defects on its first run, and they are cheap:

  1. LICENCE QA      python -m pytest tests/test_licence_posture.py -q
     Guards BOTH directions. OUTBOUND is GPL-3.0-or-later (ADR-006): the
     declaration must stay consistent across LICENSE, NOTICE, README and
     shell/package.json, and the LICENSE sha256 is pinned so the text cannot be
     reworded. INBOUND is ADR-002: no bulk data dump, no forbidden dependency.
     ADR-006 dissolved ONLY the copyleft objection to enka-py/ambr-py. They still
     wrap HoYoverse data, so they are still not vendorable. Do not relax those
     arms on the strength of ADR-006.

  2. PROJECT GOALS QA  python -m pytest tests/test_docs_consistency.py -q
     Every backticked path in a governing doc must resolve, every ADR indexed in
     both directions, ADR numbers unique and contiguous, and no ROADMAP line
     marked DONE may name an absent path. .claude/commands/done.md is a governing
     doc too. Docs are held to the same standard as code here.

  3. COMPANION VIEW QA  python scripts/qa_companion.py
     End-to-end on the real machine: ports, the JS/Python port contract, every
     surface route, the panel-readiness invariant, the drag strip, the snapshot,
     the Electron runtime and the desktop shortcut. Binds an EPHEMERAL port so it
     never contends with a dashboard you have open. Exit 0 means healthy.

Then the standard gates:
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
Run the two Python suites SEPARATELY. Never `pytest .` from the root.

WHAT "PUBLIC" ACTUALLY NEEDS. The licence is SETTLED and guarded; that is not
the same as ready to be read by a stranger. The open work, in order:

  - README.md opens for the operator, not for an outsider. First screen should
    say what this IS, what it deliberately does NOT do, and what state it is in.
    It currently assumes the reader already knows.
  - PER-FILE GPL HEADERS were deliberately deferred - ADR-006 Consequences.
    Going public is the trigger to DECIDE them, not to defer again. Decide, and
    if the answer is still "no", record why in the ADR rather than in chat.
  - A quickstart a fresh clone can actually follow, end to end, on a clean
    machine. FIRST action in a fresh clone is `python scripts/install_hooks.py`,
    because core.hooksPath is local config and is NOT cloned.
  - A leak sweep over tracked files: absolute paths under the user profile, the
    Windows account name, any real UID. scripts/make_shortcut.py and
    tools/publish_next_session.py already carry a no-directory-in-messages rule
    with tests pinning it; extend that discipline to the docs and the README.
  - REPO RELOCATION is a PREREQUISITE for the CI half: both workflows are
    written for `resin-compute/` as the repository root.

STATE, verified 2026-09-06 at commit b22c945 (report what YOU observe, never
these numbers):
  ruff                            All checks passed
  pytest tests                    697 passed, 1 skipped
  pytest agents/pity_engine        76 passed
  shell node --test                52 passed
  scripts/qa_companion.py          17 passed, 0 failed, 1 skipped
  headless --once --dry-run       exit 0
  python -m mypy                  RED, and it was red before any of this work.
                                  Environmental: _pytest/python_api.py imports
                                  numpy, mypy follows it into numpy 2.5.0's stub,
                                  which uses PEP 695 `type` statements invalid
                                  under the pinned python_version = 3.11. The
                                  interpreter here is 3.14. Advisory in CI
                                  (continue-on-error). Decide deliberately
                                  whether to fix mypy.ini, drop the stray numpy,
                                  or leave it.

SHIPPED LAST SESSION - DO NOT REDO ANY OF IT:
  - HISTORY WAS REWRITTEN and force-pushed. EVERY SHA CHANGED. Any note or doc
    pinned to an older SHA is stale. Two commits carried Co-Authored-By and
    Claude-Session trailers; both forms are gone from history and both are now
    stripped by .githooks/commit-msg and guarded from outside it by
    tests/test_commit_trailers.py.
  - /done is .claude/commands/done.md. /orchestrated-run and /ui-audit exist.
    .claude/agents/ holds seven roles. ADR-007 is the reasoning.
  - tools/publish_next_session.py writes Desktop/RSC-NEXT-SESSION.txt from the
    fenced block in NEXT_SESSION_PROMPT.md. NEVER hand-write that file. The
    inline block in chat is the hand-off; the Desktop file is its backup.
  - scripts/hook_python.sh is the single shared hook interpreter selector.
  - New guards: tests/test_line_endings.py, tests/test_commit_trailers.py,
    tests/test_agent_roster.py, tests/test_hook_interpreter.py.
  - .gitignore now TRACKS .claude/commands/*.md and .claude/agents/*.md.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - `taskkill /F /PID` DOES NOT WORK in the Bash tool. MSYS path conversion
    rewrites the lone /F into F:/. Write `taskkill //F //PID <pid>`. It fails
    SILENTLY when redirected to /dev/null, so a process you believe you killed is
    still running.
  - A heredoc plus a non-raw Python string will mangle backslashes. It put a
    literal BEL character into docs/LEDGER.md once, and it silently no-opped a
    str.replace last session - the write SUCCEEDED and did nothing. Use the
    Write/Edit tools for content with backslashes.
  - `python3` here resolves to the Microsoft Store shim, which redirects to a
    DIFFERENT interpreter with no ruff and no pytest. `command -v python3`
    SUCCEEDS, so any fallback guarded by EXISTENCE never fires. Probe
    CAPABILITY: `python3 -c "import pytest"`. This silently disabled the
    pre-push gate for the life of the repo until it was fixed.
  - `git check-attr --stdin -z` changes the INPUT separator as well as the
    output one. Newline-separated input makes git read the whole list as ONE
    path, and the sweep collapses to a single bogus entry that still passes a
    naive assertion.
  - `git update-index --refresh` does NOT clear stat drift after an eol
    normalisation. `git add --renormalize .` is what settles it.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. 8870 is Daemon Slayer's. Verify a band against the owning
    project's registry IN SOURCE, never against netstat.
  - computer-use minimizes all windows when it initialises, so the first
    screenshot after starting it misses app windows. Confirm a GUI process is
    alive out of band before concluding it failed to launch.

THE ONE THING THAT UNBLOCKS THE DOMAIN WORK: the account has not been played yet.
docs/GOAL_SPEC_SEED_TEAM.md section 3.1 is the gate on a real dated plan, and it
needs FIRST-HAND in-game observation of the seed-team cost table - Mora and
Hero's Wit per ascension threshold, plus material name and quantity at each.
data/costs/ is ready to take it with a `source` field per row.
tests/_parked/ holds the complete, TDD-first test file waiting for those numbers,
with a README saying how to unpark it.
The web-sourced figures in the goal spec are UNVERIFIED and must not enter data/.
tests/test_goal_spec.py fails if they do.

OPEN WORK after the public-repo QA, full list in ROADMAP.md:
  - Observe the cost table in game (above). Everything planning-related waits.
  - Check the TIME-SENSITIVE claims in GOAL_SPEC section 4 in game and date them.
  - Artifact scoring needs a stated model BEFORE implementation, not after.
  - Deferred deliberately, see ADR-007: the unattended lane-queue driver, a
    frozen-file list plus adjudicator grant route, and a lane mutex.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no en-dashes,
no smart quotes. Never add a Co-Authored-By or Claude-Session trailer. Verify
against ground truth before asserting anything is done, fixed, broken or missing,
and report the exact result observed with counts. Never trust a subagent's claim
about test counts, green CI or file existence without an independent probe -
that rule earned itself twice last session.

First action in a FRESH clone: python scripts/install_hooks.py
core.hooksPath is local config and is not cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.
```

---

## Why this prompt is shaped like this

The three QA gates lead because each found real defects the first time it ran:

- **Licence QA** was written alongside ADR-006, which reversed a posture that had
  never actually been decided. The README used to say the project was private
  with no licence granted, which is a default rather than a choice. The exact
  old wording is deliberately NOT reproduced here: the licence guard sweeps every
  root `.md` for that phrase, and it cannot tell a historical quote from a live
  claim. Describing a stale string beats quoting it.
- **Project goals QA** found five dead pointers immediately, including two ADRs
  that existed but had never been added to the index, and a README tree listing
  claiming a file that was not there.
- **Companion QA** found a false negative in its own first run, which led to a
  real bug: the shortcut installer matched by filename, so a renamed shortcut
  would have caused it to create a duplicate.

The traps section is not general advice. Every item is something that cost real
time in this tree and would cost it again. Three of them were added on
2026-09-06, and all three describe a gate that looked healthy while doing
nothing: an interpreter chosen by existence rather than capability, a trailer
policy enforced on one of its two forms, and a line-ending rule enforced in the
index but not on disk. That is the shape to watch for.
