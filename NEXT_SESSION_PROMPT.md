# Next session prompt

The fenced block below is the hand-off. It is the SOURCE OF TRUTH for the
`/done` ritual sections 9 and 11, it is what `tools/publish_next_session.py`
reads to write the Desktop backup, and it is what the operator pastes into a
cold session. There must be exactly ONE fenced block in this file.

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

STATE AS OBSERVED 2026-09-07 at commit 159f4ac, a reading and not a promise:
  pytest tests            1266 passed, 1 skipped
  pytest agents/pity_engine  80 passed
  shell node --test       52 pass, 0 fail
  ruff                    all checks passed
  mypy (advisory)         Success, 33 source files
  headless smoke          exit 0
  CI                      ci workflow green on main
Counts are not guarded and a doc is not a source of truth. Re-measure with
python -m pytest tests --collect-only -q before citing any of them.

THE RESPONDER IS ARMED AND MAY STILL BE RUNNING. tools/moon_sync_responder.py
answers cross-repo mail unattended, via the ResinCompute-Responder scheduled
task, window 2026-09-07 19:00-21:00 local. CHECK IT FIRST:
  powershell -NoProfile -Command "Get-ScheduledTaskInfo -TaskName 'ResinCompute-Responder'"
  cat ops/runtime/responder_invocations.log
  cat ops/runtime/responder_metrics.json
KILL SWITCH: powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove
It refuses to act unless a gitignored agreement record under ops/runtime/ names
the counterparty, cites the note it rests on, and has not expired. Registering
the task does NOT start a trial. Tonight ran LATENCY-ONLY: M2 and M3 only, M1
recorded INAPPLICABLE rather than zero, because with a human at the far end
hops-to-quiescence is undefined and a zero is the most misleading value
available. Sibling-A's end is NOT built; it named a CONDITION rather than a date.

TRAPS THAT HAVE ACTUALLY BITTEN IN THIS TREE. Every one measured here.

- A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE. Three bounds in the
  responder were implemented correctly, each had a passing arm, and each was
  IGNORED by the function that runs the cycle. Mutants disabled them inside the
  cycle and the suite stayed green. If you have a budget, a window or a kill
  switch with a unit test, assert that something CALLS it.
- A FAILED SPAWN LOOKED LIKE A SUCCESSFUL BOUND. subprocess could not launch
  `claude` by bare name on Windows (the entry point is a .CMD shim), the spawn
  returned empty, the gate refused the empty draft, and it was recorded as
  `exhausted` - the label meaning "the bound worked as predicted". A negative
  that is a statement about the instrument, not the world.
- A FIXTURE SIZED FROM THE VALUE UNDER TEST IS AN AMPLIFIER. An arm sized
  `MAX_DROP_ENTRIES + 5` met a mutation setting that constant to 10**9 and wrote
  492674 files before it was killed. Cap fixtures with a literal; assert the
  ceiling separately.
- A HAND-MAINTAINED TEST-ISOLATION LIST GOES STALE SILENTLY. The responder
  fixture named three DEFAULT_ paths to redirect; a fourth was added an hour
  later and the suite wrote real lines into ops/runtime/. Discover them by
  enumerating the module, never by listing them.
- SCHEDULED TASK XML: `Repetition` must precede `StartBoundary` and needs a
  `Duration` (else 0x8004131a, naming no element), and the declaration must say
  UTF-16 because Register-ScheduledTask takes a .NET string (else
  "(1,40)::ERROR: unable to switch"). ops/ResinCompute-Supervisor.xml has a
  comment asserting the opposite and has NEVER been registered on this machine.
- THE PRE-PUSH HOOK GRADES THE WORKING TREE, NOT THE PUSHED COMMIT. It now reads
  the ref list and refuses when a pushed sha is not HEAD, and names the shipping
  commit on a dirty tree. Do not re-drain stdin "because the content is unused".
- WORKSPACE TRUST HAS TWO SPELLINGS. ~/.claude.json keys projects by exact path
  string; an untrusted workspace makes a headless run DISCARD permissions
  SILENTLY. str(Path("C:/x")) normalises to a backslash on Windows, so a
  Path-keyed lookup cannot see a forward-slash entry at all.
- HEREDOC PLUS A NON-RAW PYTHON STRING MANGLES BACKSLASHES. It has put a BEL
  byte into docs/LEDGER.md and silently no-opped a replacement. Use Write/Edit
  for content with backslashes.
- taskkill under Git Bash needs //F //PID. A lone /F becomes F:/ and fails
  SILENTLY when redirected. Never Stop-Process. Never blanket-kill by image
  name: this box runs five sibling projects and one of them was mid-suite.
- A MEASURED NEGATIVE NEEDS A POSITIVE CONTROL IN THE SAME COMMAND FAMILY. This
  tree's refs/pull count is ZERO, armed by refs/heads returning 1.
- BACKGROUND TASK NAMES MUST CARRY AN EXPECTED DURATION, e.g. "(3 min)". Hard
  rule, restated by the operator 2026-09-07. Elapsed time alone cannot say
  whether a task is stuck, and partial compliance is worse than none.

OPEN WORK, highest priority first. Full list in ROADMAP.md.

1. OPERATOR DECISION, NOT A SESSION'S. 89 of 91 commits in this PUBLIC repo
   carry the operator's personal email in the author field, measured against
   origin/main. A sibling redacted the same string from one note and called it
   the operator's identity. DO NOT rewrite history without an explicit
   instruction: a sibling measured four traps doing one, including that a mirror
   clone fetches refs/pull/*/head and that a content scrub can be complete and
   still publish names because a filename is not content.
2. Read the responder metrics after the window closes and report M2/M3 to the
   channel whatever they show, labelled LATENCY-ONLY with M1 INAPPLICABLE.
3. The responder has never answered real mail. Every arm is against a stub or a
   scratch inbox; only one live spawn was verified by hand.
4. scripts/watch_inbox.py has no invocation log, so /clear survival is
   UNMEASURABLE AS BUILT here. The responder has one; copy the shape.
5. Nothing writes a provenance row yet. A schema with no producer has never met
   a real value.

DO NOT REDO: the slots.py re-pin (closed, three carriers hash equal at
71fa2a68), the manifest-as-key proposal (withdrawn by its own author, refuted by
three trees - a payload digest is computed from files on THIS disk and a sender
manifest is never the key), the caveman dialect question (settled), and the
wenyan experiment (run and reverted 2026-06-27 as too lossy to skim).

THE CROSS-REPO INBOX IS NOT OPTIONAL READING. Review moon_sync_inbox/ AND its
subdirectories, then ingest, implement and respond. Reading the filename list is
not reviewing it. Verbatim bytes SUPERSEDE any paraphrase of them. Triage every
file into one of four buckets - ingested, already-have-an-equivalent,
not-applicable-because-X, or applicable-and-not-done - and the fourth reaches
the roadmap. SILENCE IS NOT AGREEMENT. Reading is not acknowledging: --mark is a
separate deliberate act and an inflated watermark is worse than none.

Session shape is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT. The agent that produced a thing never grades it.
Agreement between two agents is not evidence - find their shared input and test
THAT. Keep chat under 500 output tokens, CAVEMAN ULTRA dialect, 7-bit ASCII
everywhere, no em-dashes or smart quotes ever.
```
