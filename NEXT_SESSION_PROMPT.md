# Next session prompt

Copy the block below verbatim into a new session. Everything above and below it
is context for a human; the block is what the agent needs.

---

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

THE TASK THIS SESSION: LAND the public-repo fixes. The audit is DONE - findings
are written up in ROADMAP.md under "QA the repo for going public" and under "The
licence gate REFUSED publication". Do NOT re-run the audit. Read the findings,
fix them, and stop the repo being unpublishable. Then the three operator items
that follow them in ROADMAP.md.

BOOTSTRAP, in this order:
  CLAUDE.md, README.md, ROADMAP.md, docs/LEDGER.md, docs/SPEC_SCAFFOLD.md,
  docs/adr/README.md, and `git log --oneline -12`.
SPEC_SCAFFOLD.md is the authoritative build contract and carries every verified
domain constant. Do NOT re-derive gacha numbers from memory or a web search, and
do not "fix" them against the originating brief, which was wrong in three places
that are now regression-tested.

READ THE "Session default" SECTION OF CLAUDE.md BEFORE DISPATCHING ANYTHING.
The default shape is orchestrated, multi-agent, self-adjudicating and
self-adversarial. The main thread reads, plans, dispatches, merges and reports;
it does NOT run long sweeps inline. Seven roles live in .claude/agents/. The
dispatch protocol is /orchestrated-run. The reasoning is ADR-007.
WORKTREE-ISOLATE EVERY AGENT THAT WRITES: pass isolation: "worktree" on the
Agent call. Measured 2026-09-06 - four slices dispatched into the shared tree
lost no work but produced three FALSE reports, including one agent reporting
another's suite red when it was green.

RUN THE THREE QA GATES FIRST, BEFORE ANY OTHER WORK. Each caught a real defect
on its first run, and they are cheap:

  1. LICENCE QA      python -m pytest tests/test_licence_posture.py
     Guards BOTH directions. OUTBOUND is GPL-3.0-or-later (ADR-006): the
     declaration must stay consistent across LICENSE, NOTICE, README and
     shell/package.json, and the LICENSE sha256 is pinned so the text cannot be
     reworded. INBOUND is ADR-002: no bulk data dump, no forbidden dependency.
     ADR-006 dissolved ONLY the copyleft objection to enka-py/ambr-py. Both were
     RE-VERIFIED as GPL-3.0 on 2026-09-06 and both still wrap HoYoverse data, so
     they are still not vendorable. Do not relax those arms on the strength of
     ADR-006.
  2. PROJECT GOALS QA  python -m pytest tests/test_docs_consistency.py
     Every backticked path in a governing doc must resolve, every ADR indexed in
     both directions, ADR numbers unique and contiguous, and no ROADMAP line
     marked DONE may name an absent path. .claude/commands/done.md is a governing
     doc too. This guard caught a bad edit DURING the last session: writing
     "ADR-008" into ROADMAP.md before that ADR existed turned it red immediately.
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

DO NOT ADD -q TO ANY OF THOSE. pytest.ini addopts ALREADY carries -q. A second
-q makes -qq and SUPPRESSES the summary line, so you get a wall of dots and no
count, and you cannot report what you did not see. Measured 2026-09-06.

STATE, verified 2026-09-06 at commit 96a8c54 (report what YOU observe, never
these numbers):
  licence QA                      exit 0
  docs QA                         exit 0
  scripts/qa_companion.py         17 passed, 0 failed, 1 skipped
  ruff                            All checks passed
  pytest tests                    697 passed, 1 skipped
  pytest agents/pity_engine        76 passed
  shell node --test                52 passed
  headless --once --dry-run       exit 0
  python -m mypy                  RED, and it was red before any of this work.
                                  Environmental: _pytest/python_api.py imports
                                  numpy, mypy follows it into numpy's stub, which
                                  uses PEP 695 `type` statements invalid under the
                                  pinned python_version = 3.11. Advisory in CI
                                  (continue-on-error). Decide deliberately whether
                                  to fix mypy.ini, drop the stray numpy, or leave
                                  it.

THE REPOSITORY IS STILL PRIVATE. `gh repo view` returns visibility PRIVATE.
Flipping it is the LAST action and it is the OPERATOR'S, not yours. The licence
gate REFUSED publication as-is on four TEXT defects. All four are in ROADMAP.md
with evidence. Fix them, then ask.

THE HIGHEST-VALUE FIXES, in ROADMAP.md order. Read the entries, they carry the
evidence and the traps:
  - Two fixtures are labelled false. seed_roster.json and seed_materials.json
    say "_synthetic": true directly above a "_note" saying "Hand-authored". The
    directory README is titled "SYNTHETIC test data only" while its own body says
    hand-authored. Hand-authored is what ADR-002 requires and what NOTICE already
    says correctly. Synthetic means invented; verified avatarIds are not invented.
    The TRUE claim is the STRONGER one. tests/test_licence_posture.py asserts on
    a string that survives the edit - check which, do not guess.
  - Four public-facing files still give the reason ADR-006 DISSOLVED, saying
    vendoring enka-py or ambr-py "would relicense this repo". docs/LICENSE_NOTES.md
    has the same sentence and handles it correctly with a header stating the
    dissolution - copy that shape. The refusal itself STAYS: both wrap HoYoverse
    data and a licence on a wrapper cannot grant rights to the payload.
  - NOTICE omits the GPL-3 warranty-disclaimer paragraph. Two sentences, taken
    verbatim from the appendix in LICENSE.
  - No Genshin-specific fan-content policy could be retrieved from a first-party
    source; the HoYoverse Help Center routes Genshin questions to a Zenless Zone
    Zero document, and the Genshin merchandising guide covers physical goods only.
    That is an ABSENCE OF RETRIEVAL, not proof of absence. Either retrieve one or
    record an ADR saying none was locatable, what the posture is, and that it is
    revisited if one appears. Do not publish on an unrecorded assumption.
  - The docs guard tests .exists(), which is TRUE for a directory git does not
    store. Add an arm asserting a cited path is in `git ls-files`.
  - .claude/commands/done.md carries an absolute C:/Users/<account>/ path.
  - README opens for the operator, its repository tree is stale and unguarded,
    and its quickstart fences bash for PowerShell-only content on the one platform
    it names.
  - Per-file GPL headers: DECIDE in an ADR, do not defer again. The gate CLEARED
    the substance - GPL-3's "How to Apply These Terms" sits AFTER
    "END OF TERMS AND CONDITIONS" so it is advisory, and section 5(b) binds "the
    work" and binds a MODIFIER, not the original author. So: below best practice,
    NOT non-compliant. The recommendation is a decision NOT to adopt, with named
    re-open triggers.

DO NOT REDO THESE. All shipped or settled:
  - The audit itself. Findings are in ROADMAP.md; re-running it burns a session.
  - UID 618285856 IS NOT A LEAK. Two agents independently flagged it as a real
    account and BOTH WERE WRONG. It is Enka.Network's OWN published example UID,
    appearing twice in
    https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/api.md. Do not
    "fix" it in README.md or the three test modules. The only work is one line at
    the use site saying what it is.
  - Repo relocation. DONE. The tree is standalone, the remote is correct, ci.yml
    needs no working-directory and both workflows are green against it. The old
    claim that the workflows are inert was measured false and removed.
  - History was rewritten and force-pushed on 2026-09-06. EVERY SHA CHANGED. Any
    note pinned to an older SHA is stale. Both trailer forms are gone and are
    guarded by tests/test_commit_trailers.py.
  - /done is .claude/commands/done.md. /orchestrated-run and /ui-audit exist.
    .claude/agents/ holds seven roles. ADR-007 is the reasoning.
  - tools/publish_next_session.py writes Desktop/RSC-NEXT-SESSION.txt from the
    fenced block in NEXT_SESSION_PROMPT.md. NEVER hand-write that file.
  - scripts/hook_python.sh is the single shared hook interpreter selector.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - A SINGLE-LINE GREP MISSES A WRAPPED SENTENCE. Measured 2026-09-06: sweeping
    for "relicense this repo" returned eight files and did NOT return README.md,
    because the phrase wraps across two lines. The sweep scored clean by not
    looking. Any prose sweep must be multiline-aware.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. Measured 2026-09-06 on the UID
    above: two agents agreed and both were wrong, because they shared one premise.
    Find the SHARED INPUT and test THAT against the upstream source.
  - A SWEEP NEEDS TWO GUARDS: one that the bad thing is gone, one that the
    LEGITIMATE NEIGHBOURS SURVIVED. "Legion" names both the machine AND a sibling
    project in ADR-004, so a blind replace destroys a port-registry row. Same for
    the synthetic C:\Users\x\ path in tests/test_make_shortcut.py and the
    banned-trailer fixture strings in tests/test_commit_trailers.py.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool. MSYS path conversion
    rewrites the lone /F into F:/. Write `taskkill //F //PID <pid>`. It fails
    SILENTLY when redirected to /dev/null, so a process you believe you killed is
    still running.
  - A heredoc plus a non-raw Python string will mangle backslashes. It put a
    literal BEL character into docs/LEDGER.md once, and it silently no-opped a
    str.replace - the write SUCCEEDED and did nothing. Use the Write/Edit tools
    for content with backslashes.
  - `python3` here resolves to the Microsoft Store shim, which redirects to a
    DIFFERENT interpreter with no ruff and no pytest. `command -v python3`
    SUCCEEDS, so any fallback guarded by EXISTENCE never fires. Probe
    CAPABILITY: `python3 -c "import pytest"`.
  - `git check-attr --stdin -z` changes the INPUT separator as well as the output
    one. Newline-separated input makes git read the whole list as ONE path.
  - `git update-index --refresh` does NOT clear stat drift after an eol
    normalisation. `git add --renormalize .` is what settles it.
  - A FORCE-PUSH THAT REWRITES HISTORY TRIGGERED NO WORKFLOW AT ALL. Do not read
    "no red" as "green" after a force push - check `gh run list` for a run against
    the new SHA. Separately and NORMALLY: ci.yml carries paths-ignore '**/*.md',
    so a docs-only push fires docs-guards and NOT ci. That is correct, not a
    failure, and does not want a workflow_dispatch.
  - AN EMPTY DIRECTORY IS NOT IN THE REPOSITORY. Git stores no empty directories,
    so a path can resolve locally and be absent in every clone. `git ls-files
    <dir>` returning nothing while `ls` shows the directory is the tell.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. 8870 is Daemon Slayer's. Verify a band against the owning
    project's registry IN SOURCE, never against netstat.
  - computer-use minimizes all windows when it initialises, so the first
    screenshot after starting it misses app windows.

OPERATOR DECISIONS, surface them and do NOT act unilaterally:
  - Repository NAME. The operator wants it to read as "Resin Compute & Pity
    Engine". A GitHub repo NAME admits no space and no ampersand - both fold to
    hyphens - so the literal string is reachable as the DESCRIPTION and the README
    H1 only. A rename also flattens the two-tier convention in CLAUDE.md. No test
    pins the name; only README.md, NEXT_SESSION_PROMPT.md and
    .claude/commands/done.md cite it. DECIDE description-only versus a real
    rename first.
  - The VISIBILITY PASS in ROADMAP.md. Topics first, they are unset and free.
    Do NOT enable Discussions in the same pass - inviting users to paste raw Enka
    payloads farms other people's UIDs into a public repo.
  - Two commits on main carry an agent identity as AUTHOR and COMMITTER. Not the
    trailer rule; tests/test_commit_trailers.py reads subject and body only, never
    %an/%ae/%cn/%ce. A second history rewrite is the operator's call, and the
    guard extension cannot be written before it because it would fail at HEAD.
  - The author email on nineteen of twenty-one commits becomes public on the flip.

AFTER THE PUBLIC WORK, full list in ROADMAP.md:
  - Row-scoped provenance for data/costs/. Every record carries its own receipt:
    value, method, game version, date observed, and whether it is reconfirmed on
    the current version. Facts are not copyrightable, so a licence cannot make a
    measured table distinguishable from a wiki table - only the receipt travelling
    WITH the number can. Needs a stated schema BEFORE the first row lands.
  - Observe the seed-team cost table in game. docs/GOAL_SPEC_SEED_TEAM.md section
    3.1 is the gate on a real dated plan and needs FIRST-HAND observation - Mora
    and Hero's Wit per ascension threshold, plus material name and quantity.
    data/costs/ is ready to take it. tests/_parked/ holds the complete TDD-first
    test file with a README saying how to unpark it. The web-sourced figures in
    the goal spec are UNVERIFIED and must not enter data/; tests/test_goal_spec.py
    fails if they do.
  - Check the TIME-SENSITIVE claims in GOAL_SPEC section 4 in game and date them.
  - Artifact scoring needs a stated model BEFORE implementation, not after.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no en-dashes,
no smart quotes. Never add a Co-Authored-By or Claude-Session trailer. Verify
against ground truth before asserting anything is done, fixed, broken or missing,
and report the exact result observed with counts. Never trust a subagent's claim
about test counts, green CI or file existence without an independent probe - that
rule earned itself three times now, most recently by refuting a finding this
session's own main thread had already accepted.

First action in a FRESH clone: python scripts/install_hooks.py
core.hooksPath is local config and is not cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.
```

---

## Why this prompt is shaped like this

The three QA gates lead because each found real defects the first time it ran:

- **Licence QA** was written alongside ADR-006, which reversed a posture that had
  never actually been decided. The exact old wording is deliberately NOT
  reproduced here: the licence guard sweeps every root `.md` for that phrase, and
  it cannot tell a historical quote from a live claim. Describing a stale string
  beats quoting it.
- **Project goals QA** found five dead pointers immediately, including two ADRs
  that existed but had never been added to the index, and a README tree listing
  claiming a file that was not there. It earned its keep again on 2026-09-06 by
  going red on an edit made DURING the session that wrote this file.
- **Companion QA** found a false negative in its own first run, which led to a
  real bug: the shortcut installer matched by filename, so a renamed shortcut
  would have caused it to create a duplicate.

The traps section is not general advice. Every item is something that cost real
time in this tree and would cost it again. The two added on 2026-09-06 are both
about a sweep that scored clean by not looking - a grep that missed a sentence
because it wrapped, and two agents that agreed with each other because they
shared a premise neither had tested. That is the shape to watch for: the previous
three entries described a gate that looked healthy while doing nothing, and these
describe a search that looked thorough while doing less.
