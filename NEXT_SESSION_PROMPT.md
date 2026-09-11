# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and it is
written by `/done` section 7 rather than by hand. `tools/publish_next_session.py`
reads this exact block to write the Desktop backup, so there must be exactly one
fenced block in this file.

```
RSC - next session, HEADLESS, operator MAY BE PRESENT.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS, LW and LL on ORDERED STANDBY - silence is NOT dissent, do not write into
their trees.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before a data source read docs/LICENSE_NOTES.md.
Before re-litigating read docs/adr/README.md.

*** FIRST ACTION THIS SESSION - THERE IS UNCOMMITTED WORK IN A WORKTREE ***
A three-slice responder fix was built last session and NEVER MERGED. It is
uncommitted, and it was GREEN on its own suite but RED on two gate-guard files
when the session ended. The last slice was still running at /done time, so its
outcome is UNKNOWN TO THIS PROMPT - re-measure, do not assume.

  Worktree: C:\Resin Compute\.claude\worktrees\agent-a394cb6133a3bc0f4
  Branch:   worktree-agent-a394cb6133a3bc0f4
  Forked at 41ba7d05fd09fc32875e325f62ef38b83424fb9c

  Verify the worktree still exists, then measure IN IT, each command separately:
    git status --porcelain
    python -m pytest tests
  Last observed there: 11 failed, 2135 passed, 1 skipped, exit 1. All 11
  failures were in tests/test_gate_name_bindings.py and
  tests/test_responder_gate_census.py - the guards that a NEW `# GATE:` tag is
  BUILT to redden. A slice was dispatched to fix exactly those two files and had
  not reported.

  sha256 as last seen (WILL HAVE MOVED if that slice landed):
    tools/moon_sync_responder.py
      8baea0a779eeee0daeb74e55d0f607a75a1ab25387501097ee7a9e593e4a30e0
    tests/test_responder_degraded_write.py
      5f1da072ae866ecf9667db48041d46ed1d835c7e96bbe7480cff0b624a477fff

  IF THE SUITE IS GREEN IN THERE: verify independently, then merge to main and
  commit. IF IT IS STILL RED: the two guards need the two new gate anchors
  `answered-usable` and `answered-recorded`, the census `_FLOOR` equality
  bumped 18 -> 20 and its mutant-count literal 19 -> 21, plus the prose that
  restates those numbers. DROPPING THE TAGS IS NOT AN ESCAPE - measured, the
  census then reports both sites as UNTAGGED CONSULT SITES.
  DO NOT WEAKEN AN ASSERTION TO MAKE IT PASS. Three vacuous floors have already
  been found and fixed in this tree; a bumped floor is the obvious way to make
  this green and wrong. Prove non-vacuity: rename one tag on a SCRATCHPAD COPY
  and confirm both guards go red.

WHAT THAT WORKTREE CONTAINS, all four items, none of it on main:
  - record_cycle fails closed on an unreadable metrics ledger, bytes left
    byte-identical, returns False.
  - _trim_invocations folds U+FFFD to ASCII '?'. Pre-fix growth MEASURED at
    [273363, 273369, 273387] bytes across three fires - +6 then +18, the
    threefold expansion, caught live rather than argued.
  - The metrics cap BOUNDED-ROTATES to one `.1` file holding the newest overflow
    rows, total held at 2 * MAX_METRICS_ROWS. Rotation written FIRST, live file
    LAST; a failed rotate propagates False with the live ledger untouched, so it
    can never degrade into a trim. AUTHORISED by the 2026-09-11 adjudicated call.
  - answered_usable(path) -> (bool, why) mirroring refusals_usable, per the
    2026-09-12 adjudicated call. Replaceable poisonings DEGRADE and heal;
    structural ones FAIL CLOSED with a new termination `answered-unusable`;
    absent is truthfully empty. _remember_answered's bool is no longer discarded.

  ONE ARM SHAPE TO CHECK BEFORE TRUSTING IT: four of the five rotate arms went
  red by `AttributeError: no attribute '_rotation_path'` - RED BY ABSENT API,
  not by measurement. Only the fifth is behaviour-only. An arm that grades its
  own symbol rather than the defect is the shape this tree has been bitten by.

DO NOT RE-DERIVE GACHA CONSTANTS. docs/SPEC_SCAFFOLD.md section 3, ADR-003.
50/50 is 55.000% consolidated since 5.0. Weapon soft-pity saturates at pull 77
under a 7% increment. 1.600% is 1/E[wishes per 5-star], NEVER per-wish
Bernoulli. BOTH WERE CONFIRMED BY THE LIVE CLIENT ON 2026-09-11: the banner
detail text states 1.103% consolidated and this tree predicts 1.1034%, four
significant figures; and a talent-material tooltip named Tuesday/Friday/Sunday,
exactly ROTATION_SLOT_WEEKDAYS[1] in core/domains.py. Neither figure entered
data/ and neither may.

NO BLOCKING QUESTIONS. Where you would escalate, dispatch an ADJUDICATOR and
record the ruling in ROADMAP.md MARKED PLAINLY AS AN ADJUDICATED CALL. ELEVEN
NOW STAND - 2026-09-12 added ONE, the reading half of _answered. Find each by
HEADING in ROADMAP.md, never by line number. An adjudicator is for a question
measurement cannot close.

ADJUDICATE THE CONTESTED HALF BEFORE DISPATCH, NOT IN PARALLEL WITH IT. Measured
cost last session: SendMessage is DISABLED, so a brief discovered to be wrong
while its builder was running COULD NOT BE CORRECTED IN FLIGHT. Three sequential
slices where one was planned. The ruling REFUTED THE ORCHESTRATOR'S OWN BRIEF -
it had ordered a fail-closed writer that would have converted one duplicate
delivery into ONE PER CYCLE FOREVER, because _remember_answered is the only
thing that HEALS a replaceable record.

DO NOT ARM ANYTHING. Verified DORMANT via
`python ops/check_task_liveness.py ResinCompute-Responder`, exit 1, trigger
expired 2026-09-07T21:00.

*** STILL HALTED AND WAITING FOR THE OPERATOR - UNCHANGED, NOTHING NEW ***
RC's JOINT RE-PIN REQUEST. STEP 1 IS DONE AND ANSWERED: NO - RAW hits only
inside tests/test_no_sibling_names.py which is SELF-exempt, NORMALISED-ONLY hits
ZERO. AND RC'S PREMISE IS WRONG: our tests/test_loop_concurrency.py pins
ops/loop/slots.py and ops/loop/winmutex.py by SHA256 and DOES NOT PIN ITSELF, so
the two test modules legitimately diverge. STEPS 2-4 HALTED under ruling clause
(c). NOTHING IS BLOCKED ON US.

THREE OPERATOR DECISIONS OUTSTANDING, NONE BLOCKING. The third is NEW.
  1. refusals_usable at tools/moon_sync_responder.py deliberately does NOT fail
     closed on corrupt content. INCONSISTENT with the rule
     scripts/watch_inbox.py adopted on 2026-09-11. Defensible on cost rather
     than accidental. Rule on it; do not silently harmonise either side.
  2. Arming CS / LW / LL. Clause (c) needs bilateral agreement, they cannot
     reply, and the ADOPTED rule is halt-and-wait with NO TIMEOUT. Only the
     operator can lift standby or carve out clause (c).
  3. NEW 2026-09-12 - THREE RECORDS IN ONE MODULE, THREE DISPOSITIONS.
     record_cycle fails closed on ALL unreadable metrics classes;
     answered_usable degrades on the replaceable ones and fails closed only on
     the structural; refusals_usable is fail-open on corrupt content. The
     defence is what the bytes are FOR - a metrics row is irreplaceable
     evidence, an answered name is a suppression key - and that is an ARGUMENT,
     NOT A MEASUREMENT. Rule on the SET, not on a pair.

GATES, in /done order, EACH AS ITS OWN COMMAND. Chaining with && reports only
the LAST link - a suite failure has already hidden behind a passing smoke test
at the end of a chain.
  python -m pytest tests/test_licence_posture.py
  python -m pytest tests/test_docs_consistency.py
  python -m pytest tests/test_docs_hook_commands.py
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
DO NOT PASS -q ON THE COMMAND LINE. pytest.ini sets it; a second makes it -qq
and the summary line disappears entirely.

STATE AS OBSERVED 2026-09-12 at 41ba7d0 ON MAIN, a reading not a promise.
RE-MEASURE.
  pytest tests   2106 passed 1 skipped. COLLECTED AND PASSED ARE DIFFERENT
  POPULATIONS. agents/pity_engine 80 passed. node --test 52 tests 52 pass 0
  fail. licence 47, docs consistency 29, docs hook commands 17. qa 18 passed
  0 failed 1 skipped 3 noted. ruff / headless / mypy exit 0.
  mypy ADVISORY. Its 34 source files say NOTHING about scripts/, surface/,
  headless/, ops/ or tests/. Never cite its Success about those.
  git ls-files 218 paths. git ls-files -- '*.py' 135. BOTH DECAY.
  CHECK EVERY SESSION, FIRST: gh run list --limit 5
  CI at 41ba7d0: docs-guards GREEN. ci did NOT fire on that push and that is
  CORRECT - ci.yml carries paths-ignore '**/*.md' and docs-guards fires on
  exactly what ci declines.
  LOCAL GREEN IS OPTIMISTIC. qa_companion NOTEs local ruff 0.15.12 / pytest
  9.0.3 / mypy 2.1.0 are ALL OLDER than the CI pins, and the interpreter here is
  3.14 while CI runs 3.11.

WHAT LANDED 2026-09-12, DO NOT REDO. Docs only - the code is in the worktree.
  - The 2026-09-12 ADJUDICATED CALL on the reading half of _answered, in
    ROADMAP.md under its own heading, plus the correction it made to the
    orchestrator's brief.
  - ROADMAP item 2 of the four-item block, WHICH LEDGER INSTANCE IS LIVE, is
    now CHECKED AND ANSWERED: NO DIVERGENCE.
  - Two new open rows: the three-record disposition asymmetry, and
    answered_usable's _ensure_parent side effect.

THE LEDGER-INSTANCE ANSWER, so nobody re-runs it. NO DIVERGENCE, and the reason
is NOT convergence. All five record_cycle call sites pass DEFAULT_METRICS
verbatim; six total references in non-test code, so no second binding exists to
diverge; no add_argument sets it; the registered task sets no environment.
AND THE LOAD-BEARING FINDING: ZERO M1-M6 ROWS HAVE EVER BEEN WRITTEN LIVE.
_run_once returns at its empty-queue gate BEFORE the first record_cycle. The
three JSON records are ABSENT from the ops runtime directory; the only live
record is the invocation log at 48 lines, which decomposes exactly into 19
start-plus-empty pairs plus 10 bare starts, its transition minute matching
fe53f31. A census over four roots walked 211694 directories, found 197 instances
of those four basenames, exactly ONE live, every responder_metrics.json under a
pytest tmp dir, ZERO under C:\ProgramData.
  RESIDUAL: the 10 bare starts have unrecoverable terminations and five are
  off-boundary, so the live 48 is NOT provably 48 task fires - the rsp fixture
  once wrote real lines into that exact live log and a leaked fixture line is
  indistinguishable from a manual dry run. The census says nothing about other
  drives, network paths, or any sibling tree.

FIVE LINE NUMBERS IN ROADMAP.md WERE STALE AND ARE NOW GONE RATHER THAN
CORRECTED. It cited record_cycle at BOTH :969 and :1102 for one definition; it
is at :1067. The five call sites were cited 1615/1634/1665/1700/1738; they are
1728/1748/1785/1822/1871. Deltas +98 and +113..+133. CITE BY NAME. Doc pointers
have now decayed in three consecutive sessions.

OPEN ROWS. RE-PROBE EACH BEFORE SPENDING A SLICE.
  - The worktree merge at the top of this prompt. Highest priority.
  - The Resin panel has no automatic observation source. Original Resin is not
    in the Enka payload and never will be. Today an observation is typed in by
    hand. Same gap as the income-velocity item under Next.
  - Still unmeasured on the operator's account: Original Resin sinks available
    at AR 7, Daily Commission unlock status, Adventurer Handbook. One screen
    (F1) closes all three.
  - SIX split-name shapes NEITHER our sweep NOR RC's normalisation can see,
    enumerated at the site in tests/test_no_sibling_names.py. NOT closed.
  - Sender side is unguarded against editing a note after delivery. ALREADY
    FILED at ROADMAP.md and docs/INBOX_TRIAGE_2026-09-09.md, and the row that
    cited a digest at :1261 was REFUTED - that is refusal_key, hashing filename
    plus bounce codes on the REFUSAL path. The real blocker is that no artifact
    exists for a sender-side check to compare against.
  - NO TRACKED ARM DRIVES MULTIPLE CYCLES OVER A POISONED ANSWERED RECORD on
    main. All eight existing multi-cycle _drive arms target DEFAULT_REFUSALS.
    The worktree adds one. If the merge is abandoned, this gap stays open, and a
    single-cycle arm structurally CANNOT see a per-cycle-forever loop.

THE OPERATOR'S ACCOUNT IS A REAL INPUT. uid 692912734, xMoonbeam, NA, AR 7,
World Level 0, achievements 4, version 7.0. 9 characters, ALL ascension 0 and
C0; only Dehya 10000079 and Noelle 10000034 resolve, the other seven render as
unknown:<id> BY DESIGN. Dehya lvl 20 at ascension 0 is ON the first cap per
engines/objectives.py ASCENSION_LEVEL_CAPS. Primogems 288, Mora 34102,
Intertwined Fate 6, Starglitter 0, Stardust 165. Welkin ACTIVE with 26 days
left as of 2026-09-10. Character-banner pity 0, no guarantee, and zero pulls on
Weapon / Chronicled / Character Event. Original Resin observed 200/200 at
2026-09-11T01:39:48Z.
  DO NOT WRITE ANY OF THAT INTO data/. data/fixtures/ is HAND-AUTHORED only.
  DO NOT resolve the seven unknown avatarIds by guessing - that is vendoring,
  and the placeholder exists to prevent exactly it.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating, self-adversarial
by DEFAULT, and SUBAGENT-FIRST ALWAYS. The agent that produced a thing NEVER
grades it. FREEZE THE CANDIDATE before dispatching a grader, and give every
grader THREE state assertions - HEAD sha, git status --porcelain, and the
candidate file's sha256 - so it can tell you the tree moved instead of grading
the wrong bytes. This caught a real mid-audit move on 2026-09-11, and on
2026-09-12 the same three assertions let two follow-on slices extend an
uncommitted worktree safely.
DISPATCH REFUTERS WITH DISTINCT LENSES. AGREEMENT BETWEEN TWO AGENTS IS NOT
EVIDENCE - on 2026-09-11 two documents agreed about a metrics trim and were ONE
input counted twice, proven by the identical WRONG line number in both.

TRAPS THAT ACTUALLY BIT, every one measured.

- A WRONG DISPATCH BRIEF COSTS A WHOLE SLICE, because SendMessage is DISABLED
  and a running builder cannot be corrected. Adjudicate first.
- A BUILDER THAT STOPS AT A SEAM COLLISION IS WORKING CORRECTLY. One did, on two
  gate-guard files it did not own. Dispatch a slice for them; do not widen a
  write-list mid-run.
- A GATE THAT CANNOT FAIL PASSES ON BOTH SIDES OF A REAL DEFECT. Ask what INPUT
  an arm feeds, not whether the arm exists.
- RED BY ABSENT API IS NOT RED BY MEASUREMENT. An arm that dies on
  AttributeError for a symbol the fix introduces has graded its own scaffolding.
- A SAMPLED NEGATIVE IS A STATEMENT ABOUT THE SAMPLE. Report the rate with it.
- AN EMPTY RESULT CAN BE A CLAIM ABOUT YOUR FILTER. State the filter.
- tests/test_docs_consistency.py REJECTS A BACKTICKED POINTER AT AN UNTRACKED OR
  ABSENT RUNTIME PATH. It caught two in this session's own ROADMAP edit. Name
  such a path in prose, unbackticked, and say why.
- /tmp_x.txt UNDER GIT BASH LANDS IN C:\Program Files\Git\, NOT the C: drive
  root. cygpath -w it before claiming it was or was not created.
- A LINE NUMBER IN A DOC DECAYS. Cite by content and re-measure before citing.
- A NET-ZERO-BYTE-SIZE mutate-and-restore WITHIN THE SAME SECOND runs the
  MUTANT'S BYTECODE. Purge __pycache__ AND .pytest_cache on BOTH sides.
- NEVER `git checkout --` to restore a mutation, and it is far worse in a
  worktree holding UNCOMMITTED slice work - it would destroy it. Save bytes,
  restore, verify by sha256, assert source.count(old) == 1 before substituting.
- COMPARING AN ENUM ACROSS TWO MODULE LOADS gives two distinct classes.
- A QUOTED HEREDOC STILL MANGLES BACKSLASHES. Write .py with the editor tools.
- write_text EMITS CRLF ON WINDOWS and .gitattributes eol=lf hides it. tests/ is
  OUTSIDE test_no_crlf_writers.py's corpus.
- grep -c '[^\x00-\x7F]' IS NOT A CHARACTER CLASS. Check bytes IN PYTHON.
- NEVER TYPE A BANNED GLYPH AS A LITERAL, even in a test that enforces the rule.
  Build from chr(0x2014) / chr(0xFFFD).
- A WORKTREE MATERIALISES AT AN ANCESTOR OF THE DECLARED FORK POINT. Put an
  explicit `git merge --ff-only <sha>` in every brief PLUS an assertion on
  content that EXISTS ONLY AT THE FORK POINT.
- UNCOMMITTED SLICE WORK IS INVISIBLE TO THE NEXT WORKTREE. Reuse the SAME
  worktree for a follow-on slice - measured twice this session.
- EnterWorktree REFUSES for a subagent. Use `git worktree add`.
- TaskStop a finished agent once its report lands.
- An empty pytest parametrize is `1 skipped`, exit 0, NOT a failure.
- A PYTEST PROGRESS LINE IS 72 DOTS, NOT THE WHOLE RUN.
- exit=$? AFTER A PIPE READS THE LAST PIPE STAGE. Redirect to a file.
- NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. RC, CS, LW, LL, RSC.
- Never Stop-Process. taskkill //F //PID under Git Bash.
- NEVER ADD A Co-Authored-By TRAILER, and never file its absence as a defect.

CHECK TASK LIVENESS WITH THE CHECKER, NEVER A STATE STRING, NEVER THROUGH A
PIPE:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. Observed 1 DORMANT.
KILL SWITCH:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

INBOX: 157 files, 0 unread, all triaged and MARKED. RE-MEASURE. Gitignored
wholesale - the guards derive their corpus from `git ls-files`, so an untracked
path is outside their reach BY CONSTRUCTION. Do NOT write the universal "no
guard reads it".

DO NOT REDO: everything at b3ff9fe, 3c4bcb5, 9f03062 and 2dc0965. The three
vacuous floors. The supervisor and responder argv graders. The lane-selection
pin. The _SOLO view asymmetry. The name-to-site binding table. The
undeclared-shape-grader detector. The atomic_io 0-byte temp leak. The census
prose decay. The eight gates exercised by nothing. slots.py re-pin. The
ledger-instance divergence check - ANSWERED, no divergence. Manifest-as-key
(withdrawn). Caveman dialect (settled). Wenyan (reverted 2026-06-27). Only M12
exists. Do not re-derive the ceilings in docs/LEDGER.md. Do not re-litigate the
eleven adjudicated calls without reading them. Do not re-sweep the mkdir sites.
Do not rebuild the git-reason hand-typed fixture. Do not re-open the census
REFERENT. Do not widen _READ_ATTRS, _FIRST, _SECOND, _SOLO or _SEP - WIDENING A
MATCHER is the response this tree has been defeated by three times.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes.
```
