# Next session prompt

Copy the block below verbatim into a new session. Everything above and below it
is context for a human; the block is what the agent needs.

---

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

BOOTSTRAP, in this order:
  CLAUDE.md, README.md, ROADMAP.md, docs/LEDGER.md, docs/SPEC_SCAFFOLD.md,
  docs/adr/README.md, and `git log --oneline -12`.
SPEC_SCAFFOLD.md is the authoritative build contract and carries every verified
domain constant. Do NOT re-derive gacha numbers from memory or a web search, and
do not "fix" them against the originating brief, which was wrong in three places
that are now regression-tested.

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
     marked DONE may name an absent path. Docs are held to the same standard as
     code here.

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

STATE, verified 2026-09-06 at commit d95dd98 (report what YOU observe, never
these numbers):
  ruff                            All checks passed
  pytest tests                    555 passed, 1 skipped
  pytest agents/pity_engine        76 passed
  shell node --test                52 passed
  scripts/qa_companion.py          17 passed, 0 failed, 1 skipped
  headless --once --dry-run       exit 0
  python -m mypy                  RED, and it was red before any of this work.
                                  Environmental: _pytest/python_api.py imports
                                  numpy, mypy follows it into numpy 2.5.0's stub,
                                  which uses PEP 695 `type` statements invalid
                                  under the pinned python_version = 3.11. The
                                  interpreter here is 3.14. Not caused by this
                                  code. Decide deliberately whether to fix
                                  mypy.ini, drop the stray numpy, or leave it.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - `taskkill /F /PID` DOES NOT WORK in the Bash tool. MSYS path conversion
    rewrites the lone /F into F:/. Write `taskkill //F //PID <pid>`. It fails
    SILENTLY when redirected to /dev/null, so a process you believe you killed is
    still running.
  - A heredoc plus a non-raw Python string will mangle backslashes. It put a
    literal BEL character into docs/LEDGER.md while writing the entry about that
    exact bug. Use the Write/Edit tools for content with backslashes.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. 8870 is Daemon Slayer's. Verify a band against the owning
    project's registry IN SOURCE, never against netstat.
  - computer-use minimizes all windows when it initialises, so the first
    screenshot after starting it misses app windows. Confirm a GUI process is
    alive out of band before concluding it failed to launch.

THE ONE THING THAT UNBLOCKS EVERYTHING ELSE: the account has not been played yet.
docs/GOAL_SPEC_SEED_TEAM.md section 3.1 is the gate on a real dated plan, and it
needs FIRST-HAND in-game observation of the seed-team cost table - Mora and
Hero's Wit per ascension threshold, plus material name and quantity at each.
data/costs/ is ready to take it with a `source` field per row.
tests/_parked/ holds the complete, TDD-first test file waiting for those numbers,
with a README saying how to unpark it.
The web-sourced figures in the goal spec are UNVERIFIED and must not enter data/.
tests/test_goal_spec.py fails if they do.

OPEN WORK, newest priorities first, full list in ROADMAP.md:
  - Observe the cost table in game (above). Everything planning-related waits.
  - Check the TIME-SENSITIVE claims in GOAL_SPEC section 4 in game and date them.
    Several may already be stale, and there is no banner calendar in this tree.
  - Repo relocation: the CI workflows assume `resin-compute/` as the repo root.
  - Per-file GPL headers were deliberately deferred - see ADR-006 Consequences.
  - Artifact scoring needs a stated model BEFORE implementation, not after.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no en-dashes,
no smart quotes. Never add a Co-Authored-By trailer. Verify against ground truth
before asserting anything is done, fixed, broken or missing, and report the exact
result observed with counts.

First action in a FRESH clone: python scripts/install_hooks.py
core.hooksPath is local config and is not cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.
```

---

## Why this prompt is shaped like this

The three QA gates lead because each found real defects the first time it ran:

- **Licence QA** was written alongside ADR-006, which reversed a posture that had
  never actually been decided. The README said "Private. No licence granted.",
  which is a default rather than a choice.
- **Project goals QA** found five dead pointers immediately, including two ADRs
  that existed but had never been added to the index, and a README tree listing
  claiming a file that was not there.
- **Companion QA** found a false negative in its own first run, which led to a
  real bug: the shortcut installer matched by filename, so a renamed shortcut
  would have caused it to create a duplicate.

The traps section is not general advice. Every item is something that cost real
time in this tree and would cost it again.
