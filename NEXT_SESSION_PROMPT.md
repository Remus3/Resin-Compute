# Next session prompt

The fenced block below is the hand-off. It is published to the Desktop by
`python tools/publish_next_session.py`, which reads THIS file and refuses on
anything other than exactly one fenced block, on non-ASCII, or on a block under
2000 bytes. Edit the block here; never retype it anywhere else.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before planning any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before adding any data source read
docs/LICENSE_NOTES.md. Before re-litigating a past choice read docs/adr/README.md.

DO NOT RE-DERIVE GACHA CONSTANTS from memory or a web search. Verified in
docs/SPEC_SCAFFOLD.md section 3, corrections in docs/adr/ADR-003-forecaster-model.md.
The 50/50 is 55.000% consolidated since 5.0. Weapon soft-pity saturates at pull 77
under a 7% increment - 79 or 80 is arithmetically impossible. 1.600% is
1/E[wishes per 5-star], NEVER a per-wish Bernoulli parameter.

GATES, in the order /done runs them:
  python -m pytest tests/test_licence_posture.py -q
  python -m pytest tests/test_docs_consistency.py -q
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
Never `pytest .` from the root. mypy is ADVISORY and traverses only the files=
roots in mypy.ini - its Success line says NOTHING about scripts/, headless/, ops/,
surface/ or tests/.

RUN EACH GATE AS ITS OWN COMMAND. Chaining them with && and reading the final
exit code reports only the LAST link: on 2026-09-08 a chain ending in the
headless smoke test reported exit 0 while the application suite inside it had
already failed, and a real leak nearly shipped behind that false clean.

STATE AS OBSERVED 2026-09-08, a reading and not a promise:
  pytest tests            1469 passed, 1 skipped
  pytest agents/pity_engine  80 passed
  licence / docs gates    41 passed / 29 passed
  qa_companion            17 passed, 0 failed, 1 skipped
  shell node --test       52 passed
  ruff                    all checks passed
  headless smoke          exit 0
Pre-merge baseline 1422 collected was re-derived this session, not carried from
the previous hand-off. Re-measure before citing any of these.

CHECK TASK LIVENESS WITH THE CHECKER, NEVER WITH A STATE STRING:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS.
KILL SWITCH: powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove
THE RESPONDER IS DORMANT AND ITS AGREEMENT EXPIRED, both 2026-09-07T21:00:00.
Rearming is an OPERATOR act and re-running the installer produces another BOUNDED
window, not a standing responder.

OPEN WORK, highest priority first. Full list in ROADMAP.md.

1. THE READ-ONLY GUARD OVER ops/check_task_liveness.py DOES NOT DO WHAT ITS NAME
   SAYS, and this is the THIRD time this shape has been caught. It was rewritten
   2026-09-08 from a seven-token denylist to an inverted allowlist plus a
   whole-file mutating-verb scan. An adversary defeated it DESTRUCTIVELY:
   PowerShell aliases carry NO HYPHEN and the scan matches a hyphenated
   Verb-Noun shape, so `ri` (= Remove-Item) planted in the probe template RAN,
   deleted a canary file from disk, and every arm still reported green at exit 0.
   Also surviving: del, rm, sc, kill (= Stop-Process), ni, a verb built by string
   concatenation, cmd /c, and .Delete(). SEPARATELY the whole-file regex has no
   re.IGNORECASE while the comment above it asserts case-insensitivity, so
   lowercase stop-process and uppercase TASKKILL both pass. The three non-vacuity
   controls are real value assertions and STILL could not see either hole,
   because every injection they plant is capitalised ASCII.
2. OPERATOR DECISION, NOT A SESSION'S. The overwhelming majority of commits in
   this PUBLIC repo carry the operator's personal email. Do NOT cite a stored
   number and do NOT rewrite history without an explicit instruction; a sibling
   measured four traps doing one. Re-measure with:
     git rev-list --count HEAD
     git log --format='%ae' | sort | uniq -c | sort -rn
   Read 2026-09-08: 90 personal, 6 platform forwarding, 2 assistant, of 98. The
   figure that stood before that was 89 of 91 and hid the forwarding bucket.
3. OPERATOR ACT. Rearm the responder if the trial continues. State the
   eligibility rule IN the agreement record and assert a NON-ZERO pending count
   at arming.
4. The task-liveness ambiguity arm SKIPS when it cannot find a duplicated task
   name, and a discovery that FAILS is indistinguishable from a machine that
   legitimately has none. No positive control that discovery ran. On CI or a
   fresh clone that arm asserts nothing - zero out of zero reading as a pass.
5. The responder isolation arm is named for enforcing that nothing is written
   outside the override and does NOT enforce it. NTFS reports a DIRECTORY
   st_size as 0 whatever it contains, so a file created inside a watched
   directory is invisible to an existence-plus-size snapshot; and any path that
   is not a DEFAULT_ constant is unwatched, including the sibling inbox dirs
   deliver() really writes to. WHAT DOES HOLD, measured twice: the suite does not
   reach the operator's live responder record. Real for the runtime dir, ABSENT
   for live mail.
6. Nothing grades the scheduled task's argv against the code it calls.
   ops/ResinCompute-Responder.xml gained --source scheduledtask BY HAND at the
   2026-09-08 merge and no test asserts it is there.
7. /clear survival is UNMEASURABLE as instrumented, not merely unmeasured. The
   --source flag hardcodes one literal per event, so the log names which HOOK
   fired and never which SOURCE the harness fired it from. The harness
   distinguishes startup, clear, compact and resume; the wiring collapses all
   four. More cold boots cannot close it. Filed, not built, on operator
   instruction.
8. The hook-command doc gate needs the literal string .claude/settings.json near
   the citation. Reword a sentence to "the hook declared for this tree" and the
   identical stale quotation goes silent.
9. Six items from the 2026-09-08 inbox triage, in ROADMAP.md - including that
   this roadmap twice claims a "positive control" for our refs/pull zero while
   naming no subject and no command.
10. An evicted refusal row can still re-hold one local file. Bounded, not closed.
11. Nothing writes a provenance row yet. A schema with no producer has never met
    a real value.
12. ops/ResinCompute-Supervisor.xml has never been registered on this machine.

TRAPS THAT HAVE ACTUALLY BITTEN. Every one measured here.

- A CHAINED GATE RUN REPORTS ONLY ITS LAST COMMAND. Newest member of the
  false-clean family, 2026-09-08. Run each gate separately.
- A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE - FIVE recurrences.
- AN ARM WHOSE NAME CLAIMS MORE THAN IT CHECKS IS WORSE THAN NO ARM, because the
  next reader stops looking. Three instances found on 2026-09-08 alone.
- A NON-VACUITY CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES CANNOT
  DISCOVER THAT THE MATCHER IS CASE-SENSITIVE. Vary the shape, not just the value.
- A BUILDER'S SUBPROCESS PROBE OF A DECLARED COMMAND PROVES THE TEST, NOT THE
  HARNESS. When the question is "does the harness do X", make the harness write
  the artifact.
- A COUNT BAKED INTO A COMMITTED ARTIFACT GOES STALE WITHIN THE HOUR. Name the
  property, not the number.
- A `||` BRANCH AFTER A FAILING grep PRINTS A FALSE CLEAN. grep -P dies on locale.
  Prefer a Python byte scan and carry a POSITIVE CONTROL for every negative.
- exit=$? AFTER A PIPE READS THE LAST PIPE STAGE, not the command you cared about.
- A TASK State STRING NAMES A STATE, NOT A CAPABILITY. Use ops/check_task_liveness.py.
- A SHAPE ARM PINS FORMAT, NOT VALUE. Assert the VALUE for a case known to carry one.
- AN ISOLATION FIXTURE THAT MONKEYPATCHES MODULE ATTRIBUTES CANNOT ISOLATE A
  SUBPROCESS; it re-imports with the real defaults.
- NTFS REPORTS A DIRECTORY st_size AS 0 WHATEVER IT CONTAINS. A snapshot built
  from existence plus size cannot see a file created inside a watched directory.
- AN INTERPOLATED REASON STRING DEFEATS ITS OWN FINGERPRINT. Key on CATEGORY.
- A FAIL-OPEN STATE RECORD WRITES INTO SOMEONE ELSE'S REPOSITORY.
- THE DOCS GATE CATCHES A BACKTICKED PATH GIT DOES NOT STORE. Name a gitignored
  runtime file in PROSE, never as a backtick path.
- NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. This is a PUBLIC repo and
  tests/test_no_sibling_names.py enforces it - it caught 26 occurrences on the
  way out of the 2026-09-08 session. Use the codenames LL, LW, RC, CS.
- A GITIGNORED FILE DOES NOT SURVIVE A WORKTREE MERGE. Outbound drafts live under
  ops/runtime/ and must be copied BY PATH before a worktree is torn down.
- A FIXTURE SIZED FROM THE VALUE UNDER TEST IS AN AMPLIFIER. Cap with a LITERAL.
- HEREDOC PLUS A NON-RAW PYTHON STRING MANGLES BACKSLASHES. Use Write/Edit.
- write_text EMITS CRLF ON WINDOWS and eol=lf in .gitattributes hides it.
- taskkill under Git Bash needs //F //PID. Never Stop-Process. Never blanket-kill
  by image name: this box runs five sibling projects.
- THE PRE-PUSH HOOK GRADES THE PUSHED COMMIT and runs both suites.
- EVERY BACKGROUNDED CALL CARRIES AN EXPECTED DURATION IN ITS NAME, e.g. "(3 min)".
  This means AGENT DISPATCHES TOO, not only Bash. Elapsed time alone cannot say
  whether a task is stuck.

DO NOT REDO: the slots.py re-pin (closed, three carriers hash equal at 71fa2a68),
the manifest-as-key proposal (withdrawn by its author), the caveman dialect
question (settled), the wenyan experiment (reverted 2026-06-27). Do not re-predict
a phantom underscore note during a counterparty's hard-link window - REFUTED. Do
NOT hunt for mutants M1 through M11: a byte scan of every tracked text file on
2026-09-08 found they do not exist as recorded claims anywhere, only M12 does.

THE CROSS-REPO INBOX IS NOT OPTIONAL READING. 22 unread, and STILL NOT MARKED as
of 2026-09-08. A full triage landed in docs/INBOX_TRIAGE_2026-09-08-1834.md: 11
ingested, 9 have-an-equivalent, 15 not-applicable, 6 applicable-and-not-done now
on the roadmap. The inbox currently holds ZERO subdirectories - the three
verbatim drops were withdrawn by their senders - so re-check for them rather than
assuming either way. Reading is not acknowledging: --mark is a separate
deliberate act and an inflated watermark is worse than none. SILENCE IS NOT
AGREEMENT. A reply to the outstanding note on hook portability is DRAFTED AND
UNDELIVERED in the sender-side draft store under ops/runtime/, which sits outside
the watcher's view because a file named from-RSC inside moon_sync_inbox/
classifies as [sent] and would read as already delivered.

CODE_OF_CONDUCT.md carries one marked MAINTAINER PLACEHOLDER for a conduct
contact. No email address appears in any community-standards file; reports route
through GitHub private vulnerability reporting, which is enabled and verified.

Session shape is orchestrated, multi-agent, self-adjudicating and self-adversarial
BY DEFAULT. The agent that produced a thing never grades it. Agreement between two
agents is not evidence - find their shared input and test THAT. Spawn refuters with
DISTINCT LENSES; on 2026-09-08 four adversaries refuted more than they confirmed,
and the two most valuable findings came from lenses that went looking for a
mechanism rather than for a restatement. Keep chat under 500 output tokens,
CAVEMAN ULTRA dialect, 7-bit ASCII everywhere, no em-dashes or smart quotes ever.
Never add a Co-Authored-By trailer - .githooks/commit-msg strips it per operator
policy.
```
