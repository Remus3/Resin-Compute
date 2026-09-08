# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and
`tools/publish_next_session.py` reads it out of this file to write the Desktop
backup, so edit it HERE and never retype it.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

FIRST ACTION IN A FRESH CLONE: python scripts/install_hooks.py
core.hooksPath is local config and is NOT cloned, so a fresh clone runs zero
hooks and the tracked .githooks/ directory does nothing. Never treat a hook's
presence as proof it fires: the only valid test is end to end - stage a banned
glyph, attempt a real commit, assert HEAD did not move.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before planning any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before adding any data source read
docs/LICENSE_NOTES.md. Before re-litigating a past choice read docs/adr/README.md.

DO NOT RE-DERIVE GACHA CONSTANTS from memory or a web search. They are verified
in docs/SPEC_SCAFFOLD.md section 3, with three corrections recorded in
docs/adr/ADR-003-forecaster-model.md. The 50/50 is 55.000% consolidated since
5.0, not 50%. The weapon soft-pity ramp saturates at pull 77 under a 7%
increment - any claim of 79 or 80 is arithmetically impossible. 1.600% is
1/E[wishes per 5-star], a long-run average, NEVER a per-wish Bernoulli
parameter.

GATES, in the order /done runs them:
  python -m pytest tests/test_licence_posture.py -q
  python -m pytest tests/test_docs_consistency.py -q
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
Never `pytest .` from the root - the two suites run SEPARATELY, per pytest.ini.
mypy is ADVISORY, not a gate, and it traverses only the files= roots in
mypy.ini (core/, engines/, ingest/, agents/pity_engine/, tools/). Its "Success"
line says NOTHING about headless/, ops/, surface/, scripts/, tests/ or
conftest.py - citing it as evidence about those is zero out of zero read as a
pass.

STATE AS OBSERVED 2026-09-08 at commit fe53f31, a reading and not a promise:
  pytest tests            1271 passed, 1 skipped
  pytest agents/pity_engine  80 passed
  shell node --test       52 pass, 0 fail
  licence / docs gates    41 passed / 23 passed
  qa_companion            17 passed, 0 failed, 1 skipped
  ruff                    all checks passed
  mypy (advisory)         Success, 33 source files
  headless smoke          exit 0
Counts are not guarded and a doc is not a source of truth. Re-measure with
python -m pytest tests --collect-only -q before citing any of them.

THE RESPONDER TASK IS REGISTERED AND ITS AGREEMENT IS SPENT. The
ResinCompute-Responder scheduled task is Ready on a 5-minute tick.
ops/runtime/trial_confirmed.json names the 2026-09-07 counterparty agreement and
that window has CLOSED, so armed cycles now terminate on the window bound.
Rearming is an OPERATOR act - a gitignored agreement record under ops/runtime/
must name the counterparty, cite the note it rests on, and not have expired.
CHECK STATE FIRST:
  powershell -NoProfile -Command "Get-ScheduledTaskInfo -TaskName 'ResinCompute-Responder'"
  cat ops/runtime/responder_invocations.log
KILL SWITCH: powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

THE TRIAL HAS RUN TWICE AND MEASURED NOTHING BOTH TIMES. Window one, 2026-09-07
1900-2100 LATENCY-ONLY: no metrics file, 29 start against 19 empty, M1
INAPPLICABLE, M2 and M3 NO-DATA, because pending() takes
since=bounds.window_opens and the counterparty's mail predated the window.
Attempt two, 2026-09-08: two notes hand-delivered to the counterparty, the first
refused 72 seconds later on name grammar, no responder-authored reply 15 minutes
after the bounce. Three candidate explanations, NONE measured - do not repeat
them as if they were findings.

TRAPS THAT HAVE ACTUALLY BITTEN IN THIS TREE. Every one measured here.

- A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE, AND IT RECURS.
  First measured on three responder bounds. It then happened AGAIN in the same
  file: four terminations - window, budget, empty, disarmed - each returned
  before reaching log_invocation, and each had a passing arm asserting the
  termination as a RETURN VALUE. Fixed in fe53f31 by making run_once a wrapper
  that logs the terminal line whatever the body returned. If you have a budget,
  a window, a kill switch or a log line with a unit test, assert that something
  CALLS it.
- A HAND-MAINTAINED LIST OF PATHS THAT REMEMBER TO DO X GOES STALE SILENTLY.
  The isolation fixture named three DEFAULT_ paths and a fourth arrived an hour
  later. The invocation log had the same shape. Prefer a funnel or an
  enumeration over a list, and assert the PROPERTY without naming paths.
- A WAITER BASELINED FROM THE WRONG NUMBER REPORTS A FALSE NEGATIVE. A poll
  loop was baselined at 6 lines taken from a `tail -6` while the file held 10,
  so it exited on its first pass and reported "no new fire". A statement about
  the instrument, not the world. Baseline with the same command you poll with.
- A FAILED SPAWN LOOKED LIKE A SUCCESSFUL BOUND. subprocess could not launch
  `claude` by bare name on Windows (the entry point is a .CMD shim), the spawn
  returned empty, the gate refused the empty draft, and it was recorded as
  `exhausted` - the label meaning "the bound worked as predicted".
- AN EMPTY MODEL RESPONSE IS NOT EXHAUSTION. A counterparty measured that the
  CLI returns subtype success with {"actions": []} for an unsatisfiable schema
  rather than an error. Reading that as exhaustion is the trap this tree hit.
- A FIXTURE SIZED FROM THE VALUE UNDER TEST IS AN AMPLIFIER. An arm sized
  MAX_DROP_ENTRIES + 5 met a mutation setting that constant to 10**9 and wrote
  492674 files before it was killed. Cap fixtures with a literal.
- THE DOCS GATE CATCHES A CITED PATH THAT DOES NOT EXIST. Writing a ledger
  entry ABOUT an absent file failed test_docs_consistency.py, correctly. Name
  such a file in prose, not as a backtick path.
- SCHEDULED TASK XML: `Repetition` must precede `StartBoundary` and needs a
  `Duration` (else 0x8004131a, naming no element), and the declaration must say
  UTF-16 because Register-ScheduledTask takes a .NET string. Measured
  2026-09-07. ops/ResinCompute-Supervisor.xml asserts the opposite in a comment
  and has NEVER been registered on this machine.
- THE PRE-PUSH HOOK GRADES THE WORKING TREE, NOT THE PUSHED COMMIT. It now
  reads the ref list and refuses when a pushed sha is not HEAD. Do not re-drain
  stdin "because the content is unused". A sibling measured a commit reaching
  its remote without the hook ever grading it; the mechanism is UNMEASURED and
  this tree's check cannot see past its own return.
- WORKSPACE TRUST HAS TWO SPELLINGS. ~/.claude.json keys projects by exact path
  string; an untrusted workspace makes a headless run DISCARD permissions
  SILENTLY. str(Path("C:/x")) normalises to a backslash on Windows, so a
  Path-keyed lookup cannot see a forward-slash entry at all.
- HEREDOC PLUS A NON-RAW PYTHON STRING MANGLES BACKSLASHES. It has put a BEL
  byte into docs/LEDGER.md and silently no-opped a replacement. Use Write/Edit
  for content with backslashes.
- taskkill under Git Bash needs //F //PID. A lone /F becomes F:/ and fails
  SILENTLY when redirected. Never Stop-Process. Never blanket-kill by image
  name: this box runs five sibling projects.
- A MEASURED NEGATIVE NEEDS A POSITIVE CONTROL IN THE SAME COMMAND FAMILY. This
  tree's refs/pull count is ZERO, armed by refs/heads returning 1.
- BACKGROUND TASK NAMES MUST CARRY AN EXPECTED DURATION, e.g. "(3 min)". Hard
  rule, operator 2026-09-07. Elapsed time alone cannot say whether a task is
  stuck, and partial compliance is worse than none.

OPEN WORK, highest priority first. Full list in ROADMAP.md.

1. OPERATOR DECISION, NOT A SESSION'S. 89 of 91 commits in this PUBLIC repo
   carry the operator's personal email in the author field, measured against
   origin/main. DO NOT rewrite history without an explicit instruction: a
   sibling measured four traps doing one, including that a mirror clone fetches
   refs/pull/*/head and that a content scrub can be complete and still publish
   names because a filename is not content.
2. The responder has STILL never answered real mail, after two attempts. Every
   arm is against a stub or a scratch inbox.
3. State the eligibility rule IN the agreement record, and assert a non-zero
   pending count at arming time. Both failure directions are now measured: a
   since bound that admits nothing, and an empty answered record that makes the
   ENTIRE backlog eligible so a budget of one is spent on the oldest note.
4. A refused note re-refuses forever, and _hold writes held/<epoch>-<name> with
   a fresh epoch each cycle - 288 files a day at a 5-minute tick for one note
   that can never pass.
5. Our refusals tell the sender nothing. Answered to the channel with a shape
   NOT implemented here: a bounce written as a file that is not a note, so it is
   visible to a human, ineligible as responder input, and incapable of a bounce
   war by construction.
6. Note filenames here are long enough to be refused by a sibling's grammar.
   Nothing in this tree enforces a length; the convention is habit, not a guard.
7. scripts/watch_inbox.py has no invocation log, so /clear survival is
   UNMEASURABLE AS BUILT here. The responder has one; copy the shape.
8. Nothing writes a provenance row yet. A schema with no producer has never met
   a real value.

DO NOT REDO: the slots.py re-pin (closed, three carriers hash equal at
71fa2a68), the manifest-as-key proposal (withdrawn by its own author), the
caveman dialect question (settled), and the wenyan experiment (run and reverted
2026-06-27 as too lossy to skim). Do not re-predict a phantom underscore note
during a counterparty's hard-link window - that prediction was REFUTED by
measurement: their tmp names carry .tmp, which this reader demotes.

THE CROSS-REPO INBOX IS NOT OPTIONAL READING. Review moon_sync_inbox/ AND its
subdirectories, then ingest, implement and respond. Reading the filename list is
not reviewing it. Verbatim bytes SUPERSEDE any paraphrase of them. Triage every
file into one of four buckets - ingested, already-have-an-equivalent,
not-applicable-because-X, or applicable-and-not-done - and the fourth reaches
the roadmap. SILENCE IS NOT AGREEMENT. Reading is not acknowledging: --mark is a
separate deliberate act and an inflated watermark is worse than none. Outbound
drafts live in ops/runtime/outbox_drafts/, deliberately OUTSIDE the watcher's
view: a file named from-RSC-* inside moon_sync_inbox/ is classified [sent], so
an undelivered draft parked there reads as already sent.

Session shape is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT. The agent that produced a thing never grades it.
Agreement between two agents is not evidence - find their shared input and test
THAT. Keep chat under 500 output tokens, CAVEMAN ULTRA dialect, 7-bit ASCII
everywhere, no em-dashes or smart quotes ever.
```
