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

STATE AS OBSERVED 2026-09-08 at commit e7ab266, a reading and not a promise:
  pytest tests            1408 passed, 1 skipped
  pytest agents/pity_engine  80 passed
  shell node --test       52 pass, 0 fail
  licence / docs gates    41 passed / 23 passed
  qa_companion            17 passed, 0 failed, 1 skipped
  ruff                    all checks passed
  mypy (advisory)         Success, 33 source files
  headless smoke          exit 0
Counts are not guarded and a doc is not a source of truth. Re-measure with
python -m pytest tests --collect-only -q before citing any of them.

CHECK TASK LIVENESS WITH THE CHECKER, NEVER WITH A STATE STRING:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. Exit 0 means and only
means the task is positively established to fire again. Do NOT read State or
LastTaskResult to answer that question - that is the defect this tool exists for.
  cat ops/runtime/responder_invocations.log
KILL SWITCH: powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

THE RESPONDER IS DORMANT AND ITS AGREEMENT IS EXPIRED, both at
2026-09-07T21:00:00. Measured 2026-09-08: State reads Ready and LastTaskResult
reads 0, while the only trigger's EndBoundary is in the past, NextRunTime is
empty, and the invocation log holds ZERO lines dated 2026-09-08. Rearming is an
OPERATOR act and re-running the installer produces another BOUNDED window, not
a standing responder. A gitignored agreement record under ops/runtime/ must
name the counterparty, cite the note it rests on, and not have expired.

THE TRIAL FINALLY PRODUCED DATA, ON THE RECEIVING SIDE ONLY. Sibling-A's
responder delivered a machine-authored note at 17:00 on 2026-09-08, cycle
20260908T165744-28336-aba821, the first this repository has ever received. M2
and M3 are no longer NO-DATA inbound. The REPLY path is dormant, so this tree
still cannot answer automatically. Do not read our silence as their defect.

TRAPS THAT HAVE ACTUALLY BITTEN IN THIS TREE. Every one measured here.

- A TASK State STRING NAMES A STATE, NOT A CAPABILITY. Ready is reported forever
  once every trigger has expired. A hand-off written from that string claimed a
  5-minute tick and was wrong by 24 hours. The mirror error is just as real: an
  ABSENT EndBoundary is absence of evidence, not evidence, and a fired one-shot
  carries none. Use ops/check_task_liveness.py.
- A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE, AND IT HAS NOW
  RECURRED FOUR TIMES. Three responder bounds; then four terminations each
  returning before reaching log_invocation; then a name validator whose only
  caller was stubbed by every main() arm. If you have a budget, a window, a kill
  switch or a log line with a unit test, assert that something CALLS it.
- A SHAPE ARM PINS FORMAT, NOT VALUE. An arm asserting the probe emits every KEY
  the parser reads stayed green while the probe emitted null for all of them.
  Assert the VALUE for a case known to carry one.
- AN ISOLATION FIXTURE THAT MONKEYPATCHES MODULE ATTRIBUTES CANNOT ISOLATE A
  SUBPROCESS. The subprocess re-imports with the real defaults. The watcher's
  own test suite wrote six real lines into the operator's live invocation log,
  under the same source label a genuine hook firing uses.
- AN INTERPOLATED REASON STRING DEFEATS ITS OWN FINGERPRINT. A dedupe key hashed
  reason TEXT and one reason carried a byte count, so a draft oversize by a
  different amount each cycle minted a fresh key every tick. The guarding arm
  fed a byte-identical draft and could not fail. Key on CATEGORY.
- A FAIL-OPEN STATE RECORD WRITES INTO SOMEONE ELSE'S REPOSITORY. An unwritable
  refusals record produced five bounces delivered into a sibling's inbox with no
  error surfaced - 288 files a day at a five-minute tick. Record before
  delivering, so an unrecordable refusal stops the outbound.
- A WAITER BASELINED FROM THE WRONG NUMBER REPORTS A FALSE NEGATIVE, AND IT HITS
  THE MERGER TOO. Reading exit=$? after a pipeline measures the last filter.
  Calling list() on a dict-shaped JSON record counts its top-level keys. Both
  produced confident wrong readings in one session. Baseline with the same
  command you poll with, and re-measure before claiming.
- THE DOCS GATE CATCHES A BACKTICKED PATH GIT DOES NOT STORE. A ledger entry
  citing a gitignored runtime record failed test_docs_consistency.py, correctly.
  Name such a file in PROSE, never as a backtick path.
- A FIXTURE SIZED FROM THE VALUE UNDER TEST IS AN AMPLIFIER. An arm sized
  MAX_DROP_ENTRIES + 5 met a mutation setting that constant to 10**9 and wrote
  492674 files before it was killed. Cap fixtures with a LITERAL.
- A FAILED SPAWN LOOKED LIKE A SUCCESSFUL BOUND. subprocess could not launch
  `claude` by bare name on Windows (the entry point is a .CMD shim), the spawn
  returned empty, the gate refused the empty draft, and it was recorded as
  `exhausted` - the label meaning "the bound worked as predicted".
- AN EMPTY MODEL RESPONSE IS NOT EXHAUSTION. A counterparty measured that the
  CLI returns subtype success with {"actions": []} for an unsatisfiable schema
  rather than an error.
- A RESPONDER THAT MEASURES HEAD REPORTS THE CODE, AND A REPOSITORY'S INTENT CAN
  BE NEWER THAN ITS CODE. Sibling-A's responder correctly described its own tree
  while being stale about a ruling its operator had already accepted.
- SCHEDULED TASK XML: `Repetition` must precede `StartBoundary` and needs a
  `Duration` (else 0x8004131a, naming no element), and the declaration must say
  UTF-16 because Register-ScheduledTask takes a .NET string.
  ops/ResinCompute-Supervisor.xml asserts the opposite in a comment and has
  NEVER been registered on this machine.
- THE PRE-PUSH HOOK GRADES THE PUSHED COMMIT, not just the working tree. It
  reads the ref list and refuses when a pushed sha is not HEAD. Do not re-drain
  stdin "because the content is unused".
- WORKSPACE TRUST HAS TWO SPELLINGS. ~/.claude.json keys projects by exact path
  string; an untrusted workspace makes a headless run DISCARD permissions
  SILENTLY. str(Path("C:/x")) normalises to a backslash on Windows.
- HEREDOC PLUS A NON-RAW PYTHON STRING MANGLES BACKSLASHES, and a heredoc
  carrying apostrophes broke a ledger splice this session. Use Write/Edit for
  content with backslashes or quoting.
- taskkill under Git Bash needs //F //PID. A lone /F becomes F:/ and fails
  SILENTLY when redirected. Never Stop-Process. Never blanket-kill by image
  name: this box runs five sibling projects.
- A MEASURED NEGATIVE NEEDS A POSITIVE CONTROL IN THE SAME COMMAND FAMILY. This
  tree's refs/pull count is ZERO, armed by refs/heads returning 1.
- BACKGROUND TASK NAMES MUST CARRY AN EXPECTED DURATION, e.g. "(3 min)". Hard
  rule, operator 2026-09-07.

THE SESSION SHAPE EARNED ITSELF ON 2026-09-08 AND IS NOT OPTIONAL. Four slices
ran; all four were reported COMPLETE by their own builders with passing arms,
clean ruff and honest counts; all four were then refuted or defect-found by an
agent that did not write them. Two independent adversaries found six and seven
findings respectively. The agent that produced a thing never grades it.

OPEN WORK, highest priority first. Full list in ROADMAP.md.

1. OPERATOR DECISION, NOT A SESSION'S. 89 of 91 commits in this PUBLIC repo
   carry the operator's personal email in the author field. DO NOT rewrite
   history without an explicit instruction: a sibling measured four traps doing
   one, including that a mirror clone fetches refs/pull/*/head and that a
   content scrub can be complete and still publish names because a filename is
   not content.
2. OPERATOR ACT. Rearm the responder if the trial is to continue - see the
   dormancy note above. State the eligibility rule IN the agreement record and
   assert a non-zero pending count at arming time. Both failure directions are
   measured: a since bound that admits nothing, and an empty answered record
   that makes the ENTIRE backlog eligible.
3. Six of seven mutant kills in the task-liveness slice rest on the builder's
   own word. The merger re-ran exactly one, M12, and the builder's KILLED was
   WRONG as stated. Re-run the other six.
4. One task-liveness mutant survives by construction and was never graded:
   PREPENDING a failing command to the PowerShell probe rather than replacing
   it, because a non-terminating error leaves exit 0. Its author declined to
   grade its own work; nobody has ruled since.
5. An evicted refusal row can still re-hold one local file. Bounded and
   disclosed, not closed.
6. Whether the SessionStart watcher fires on a COLD session and survives /clear
   is now measurable for the first time - ops/runtime/inbox_invocations.log.
   Taking the measurement needs a future cold session. THIS IS THAT SESSION:
   read the log before doing anything else and report what a cold boot wrote.
7. A sibling's refutation rests on a premise it declines to assert - that a
   hook's stdout does not inject on non-zero exit. Unmeasured here too; this
   tree has only the adjacent positive control that exit 0 DOES inject.
8. Nothing writes a provenance row yet. A schema with no producer has never met
   a real value.
9. ops/ResinCompute-Supervisor.xml has never been registered on this machine.

DO NOT REDO: the slots.py re-pin (closed, three carriers hash equal at
71fa2a68), the manifest-as-key proposal (withdrawn by its own author), the
caveman dialect question (settled), and the wenyan experiment (run and reverted
2026-06-27 as too lossy to skim). Do not re-predict a phantom underscore note
during a counterparty's hard-link window - REFUTED by measurement.

THE CROSS-REPO INBOX IS NOT OPTIONAL READING. Review moon_sync_inbox/ AND its
subdirectories, then ingest, implement and respond. Verbatim bytes SUPERSEDE any
paraphrase of them. Triage every file into one of four buckets - ingested,
already-have-an-equivalent, not-applicable-because-X, or
applicable-and-not-done - and the fourth reaches the roadmap. SILENCE IS NOT
AGREEMENT. Reading is not acknowledging: --mark is a separate deliberate act and
an inflated watermark is worse than none. THE 2026-09-08 SESSION DID NOT MARK -
it triaged that day's Sibling-A and Sibling-D notes only, leaving fourteen
older ones untriaged. Outbound drafts live in ops/runtime/outbox_drafts/,
deliberately OUTSIDE the watcher's view: a file named from-RSC-* inside
moon_sync_inbox/ is classified [sent], so an undelivered draft parked there
reads as already sent.

Session shape is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT. Agreement between two agents is not evidence - find
their shared input and test THAT. Keep chat under 500 output tokens, CAVEMAN
ULTRA dialect, 7-bit ASCII everywhere, no em-dashes or smart quotes ever.
```
