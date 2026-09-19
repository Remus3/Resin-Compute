# Next session prompt

Paste the block below into a cold session. It is the hand-off, and
`tools/publish_next_session.py` reads it from this file rather than from a
retyped copy, so the printed block and the Desktop backup cannot disagree.

```
Read CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md, docs/LEDGER.md and
git log. Before planning any character build read docs/GOAL_SPEC_SEED_TEAM.md.
Before adding any data source read docs/LICENSE_NOTES.md. Before re-litigating a
past choice read docs/adr/README.md.

LANED LOOPING IS ARMED BUT NOT ACTIVE FOR THIS TREE. Operator instruction, late
2026-09-16, superseding the earlier instruction the same day: ONLY RC AND CS RUN
HEADLESS LOOPED LANES FOR NOW. RSC DOES NOT. The directive below is kept ready
verbatim so it can be switched on without being re-derived - DO NOT ACT ON IT
unless the operator says so in this session, in their own words. If they do not,
work the open items normally, one at a time, and keep the main thread quiet.

THE DIRECTIVE, HELD IN RESERVE: CONTINUE A
LANED, HEADLESS, ORCHESTRATED, PARALLEL LOOPING SESSION OVER THE OPEN ITEMS IN
ROADMAP.md, LOOPING UNTIL THE LANES ARE DRAINED OR THE OPERATOR INTERRUPTS.
Lane the open items into DISJOINT slices BEFORE dispatching any of them,
dispatch them in parallel to worktree-isolated subagents, refute every
done-claim with a DISTINCT LENS, merge at the seam, re-run both suites there,
then take the next batch. Do not stop to ask permission per cycle - a cycle that
stops to ask has defeated the directive. The main thread holds the plan, the
seams, the merge and the report, and stays quiet: no long builds, no long suites,
no wide sweeps inline.

HALT AND PING before, and only before: any write, delete or named-kernel-object
acquisition outside this repo root - explicitly the machine-wide bucket under
C:\ProgramData and the Global\ mutex namespace; any commit or push whose diff
touches ops/loop/slots.py or ops/loop/winmutex.py, or that trips
tests/test_no_sibling_names.py; and any arming, agreement or behaviour change in
another party's tree. An ordinary push that passes both suites and the
sibling-name sweep is NOT a halt point. Writes into moon_sync_inbox/ are
PRE-AUTHORIZED - never ask for send authorisation and never ask which position
to take; a contested call goes to an adjudicator.

DO NOT RE-DERIVE THE GACHA CONSTANTS from memory or a web search. They are
verified and recorded in docs/SPEC_SCAFFOLD.md section 3, with the three
corrections to the original brief in docs/adr/ADR-003-forecaster-model.md. The
50/50 has been 55.000 percent consolidated since version 5.0, not 50. The weapon
soft-pity ramp SATURATES AT PULL 77 under a 7 percent increment and any claim of
79 or 80 is arithmetically impossible. 1.600 percent is 1 / E[wishes per 5-star],
a long-run average, NEVER a per-wish Bernoulli parameter.

STATE OBSERVED 2026-09-19 at commit fadc5f6, AS A READING AND NOT A PROMISE.
main clean. Measured from the repo root:
  python -m pytest tests                      2924 passed, 4 skipped
  python -m pytest agents/pity_engine            80 passed
  python -m pytest tests/test_licence_posture.py 47 passed
  python -m pytest tests/test_docs_consistency.py 34 passed
  python scripts/qa_companion.py      17 passed, 0 failed, 2 skipped, 3 noted
  cd shell && node --test              52 pass, 0 fail
  python -m headless.runner --once --dry-run   exit 0, 0 pass 0 fail 6 skip
  python -m ruff check .               All checks passed
  python -m mypy                       Success, 36 source files - ADVISORY ONLY
core.hooksPath is ABSOLUTE here: C:\Resin Compute\.githooks. That matters - a
RELATIVE hooks path resolves against the working directory, so every worktree
would silently run NO hooks.
The host python reports 3.14.4 while CLAUDE.md says 3.11 and mypy.ini pins 3.11.
Observed 2026-09-19. Everything above is green on the host interpreter, so CI
and this host are NOT running the same semantics. Unresolved, in ROADMAP Now.

GATES, in the order /done runs them. Run the two Python suites SEPARATELY, never
pytest . from the root. READ PYTEST'S OWN EXIT CODE, never a pipeline's - a
| tail -2 masked a real exit 1 in this tree on 2026-09-16 and reported EXIT=0.
Use PIPESTATUS or no pipe. pytest prints NO summary line here, because pytest.ini
already carries -q and a command-line -q doubles it into -qq; judge by exit code.
A chained gate run reports ONLY its last command's status, so run each gate as
its own command.

TRAPS MEASURED IN THIS TREE. Every one of these has actually bitten.
  git add BEFORE running the suite. Several guards build their corpus from
    git ls-files and CANNOT SEE an unstaged file. That produced a false green
    twice on 2026-09-16, once hiding three real failures.
  A WORKTREE FORKS FROM THE PRE-DISPATCH HEAD. Three slices this session started
    up to 16 commits behind, one of them with no docs/CHANNEL.md in it at all.
    Check merge-base and fast-forward BEFORE working.
  AN ARM BUILT IN A WORKTREE MAKES CLAIMS ABOUT A WORKTREE. A gitignored
    directory exists exactly where somebody created it, so moon_sync_inbox/ is
    present in the primary tree and absent in every worktree. A pin measured in
    one shipped RED into the other on 2026-09-16. Ask what git IGNORES, not what
    is on disk - and KEEP THE TRAILING SLASH on the pathspec, because an ignore
    rule with a trailing slash is a DIRECTORY-ONLY pattern and a probe that
    strips it answers from the filesystem instead. Measured 5 runs each way.
  git check-ignore RETURNS ITS ANSWER IN THE EXIT CODE, not on stdout.
  EXIT 2 IS NOT SELF-EVIDENCING. A module syntax error and a tool deliberately
    refusing to start both land there. Carry the meaning in the message.
  A BARE GATE INVOCATION IS VACUOUS. tools/precommit_gate.py now REFUSES what it
    does not understand, but the only valid proof a hook fires is end to end:
    negative control first, then stage a banned glyph, attempt a REAL commit,
    assert HEAD is unchanged.
  BANNED-GLYPH LITERALS NEED chr(0x2014). Typing an em-dash into an ASCII test
    makes the test violate the rule it is testing.
  NEVER Stop-Process. Use taskkill, and under Git Bash write taskkill //F //PID.
  A /tmp REDIRECT UNDER GIT BASH LANDS IN THE GIT INSTALL DIRECTORY, not C:\.
    Use the session scratchpad.
  A SHELL LOOP OVER A PATH WITH A SPACE SPLITS THIS REPO ROOT. Measured
    2026-09-19: for w in $(git worktree list ...) split C:/Resin Compute at the
    space, so git -C "C:/Resin" ran against a path that does not exist, printed
    nothing, and wc -l reported 0 - which reads as NOT DIRTY for every row. Use
    while IFS= read -r. The tell was the same truncated first field on every
    line. The command did not fail; it answered about the wrong thing.
  Path.rglob AND Path.glob('**/...') CANNOT PRUNE. They always descend, so a
    skip-name set applied AFTER the walk yields a path still pays the full
    descent. Only os.walk with an in-place dirnames[:] assignment avoids it.
    tools/gate_mutation_runner.py and tools/first_run_capture.py carry the
    correct shape; copy one of them rather than re-deriving.
  A TEST THAT GREPS A MODULE'S SOURCE FOR os.walk IS A SHAPE ARM and pins
    format, not input. It survives the defect. Build a real tmp_path tree with a
    decoy inside the skip dir and a same-named sibling outside it, so the arm
    can fail in BOTH directions.
  mypy's Success covers only core/, engines/, ingest/, agents/pity_engine/ and
    tools/. It says NOTHING about scripts/ or tests/. Never cite it for those.

OPEN WORK, highest first, all detailed in ROADMAP.md under Now:
  0. NEW 2026-09-19 from the machine stray-work sweep: ops/runtime/outbox_drafts/
     has SIX files, oldest 2026-09-08, and ZERO code references anywhere in this
     repo. Classified UNKNOWN, not PRUNE - an undelivered draft reads as sent to
     whoever finds it. Establish what wrote it, then wire it or remove it. Do
     not delete it on size alone. shell/node_modules at 378 MiB is regenerable
     but live and is an operator call, not a sweep call.
  1. core/atomic_io.py logs raw OSError text with full filesystem paths to a
     console handler. CONTAINED at one call site; every other caller is exposed.
     The library-level fix is the one that covers them all.
  2. The shape-grader detector in tools/gate_mutation_runner.py cannot see a
     source read through a parametrize argument, a local variable or an f-string
     path. 16 of 20 reader modules are blind AND undeclared. A wider regex is
     NOT the answer.
  3. scripts/precommit_pycompile.py:33 spawns git unflagged in the hook lane -
     the fifth spawn there and the only one without CREATE_NO_WINDOW.
  4. A vendored file arriving with no byte pin is invisible to
     tests/test_vendored_provenance.py. Needs a convention, not a regex.
  5. This tree's deny-based arms verify the process TOKEN and not the PATH; the
     denial is a function of both.

DO NOT REDO, all settled 2026-09-16 and re-litigating them wastes a session:
  The vendored docs/CHANNEL.md is byte-pinned at sha256 899f6eb957cc26ee25993d
  83d65d8ca291841fe4eec24a48f729c2dc005f4c6b, 20633 bytes, 0 CR. Do not edit one
  byte; attribution lives BESIDE it in docs/LICENSE_NOTES.md because the bytes
  are a fleet pin. Its provenance is Apache-2.0 into this tree's
  GPL-3.0-or-later, compatible ONE-WAY, and verified file by file.
  tests/test_channel_doc_pin.py deliberately records NO COUNT of how many sweeps
  grade the doc - a count there moves with git add, and two instruments measured
  the same population as 6 and 8 with both right about different questions.
  The bare-filename case in its path arm is a PERMANENT RECORDED BLIND SPOT.
  The spawn census claim was NARROWED rather than the matcher widened a third
  time; its blind list is written as ARMS. Do not widen it.

THE CROSS-REPO INBOX IS NOT OPTIONAL READING. Review moon_sync_inbox/ AND its
subdirectories, then ingest, implement and respond. Reading the filename list is
not reviewing it. Verbatim bytes SUPERSEDE any prose describing them. Triage
every file into ingested, already-have-an-equivalent, not-applicable-because-X,
or applicable-and-not-done - the fourth bucket reaches the roadmap. SILENCE
READS AS DISSENT. A REVIEW- you originate MUST carry the first 12 hex of the
sha256 over its frozen subject in the filename; ours omitted it on 2026-09-16
and a sibling could not carry the token back. The inbox is gitignored, so NO
guard here can see it and a claim that must be guarded has to live in a TRACKED
file. Filename timestamps drift per sender by up to six hours - never sort by
name.
```
