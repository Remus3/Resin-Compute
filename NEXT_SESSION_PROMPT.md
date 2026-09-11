# Next session prompt

Paste the block below into a cold session. It is the hand-off.

```
RSC - next session, HEADLESS, operator MAY BE PRESENT.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS and LW BROKE STANDBY 2026-09-11; LL still silent. SILENCE IS NOT DISSENT,
and do not write into any of their trees.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before adding a data source read
docs/LICENSE_NOTES.md. Before re-litigating a past choice read
docs/adr/README.md. A fresh clone runs ZERO hooks - first action there is
python scripts/install_hooks.py.

DO NOT RE-DERIVE GACHA CONSTANTS FROM MEMORY OR FROM A WEB SEARCH. They are in
docs/SPEC_SCAFFOLD.md section 3 with corrections in
docs/adr/ADR-003-forecaster-model.md. 50/50 is 55.000% CONSOLIDATED since 5.0.
Weapon soft-pity SATURATES AT PULL 77 under a 7% increment; 79 or 80 is
arithmetically impossible. 1.600% is 1/E[wishes per 5-star], a long-run average,
NEVER a per-wish Bernoulli parameter. NEITHER FIGURE MAY ENTER data/.

DO NOT USE "$TMPDIR" IN ANY BASH COMMAND. It is UNSET in that tool, so
"$TMPDIR/x" expands to /x and MSYS writes it into C:\Program Files\Git, OUTSIDE
the repo root, silently and with no error. Use the absolute session scratchpad
path.

GATES, in /done order, EACH AS ITS OWN COMMAND. CHAINING WITH && REPORTS ONLY
THE LAST LINK.
  python -m pytest tests/test_licence_posture.py
  python -m pytest tests/test_docs_consistency.py
  python -m pytest tests/test_docs_hook_commands.py
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
DO NOT PASS -q. pytest.ini already sets it; a second -q makes it -qq and deletes
the summary line. NEVER RUN pytest . FROM THE ROOT.
mypy IS ADVISORY - files= is core/, engines/, ingest/, agents/pity_engine/,
tools/ only. tests/ IS OUTSIDE IT, so mypy says NOTHING about the census test
module this session rewrote. Zero out of zero reads as a pass. Run it anyway.

STATE AS OBSERVED 2026-09-11 AT c514ca7 ON MAIN, plus the docs commit that
carries this block. A READING, NOT A PROMISE. RE-MEASURE BEFORE CITING ANY OF IT.
  tests TOTAL 2702, and the passed/skipped SPLIT MOVED TWICE IN ONE SESSION.
  NOW, after the disarm below: 2700 passed 2 skipped, the skips being
  tests/test_ingest_client.py:348 (network opt-in) and
  tests/test_task_liveness.py:2987 (the census RAN and read 265 scheduled tasks,
  none carrying a non-empty EndBoundary, so the probe has no value to compare
  against - THE DISARMED TASK WAS THAT VALUE). Before the disarm it read 2701
  passed 1 skipped in an ordinary shell, and 2700 passed 2 skipped UNDER THE
  PRE-PUSH HOOK where the second skip is tests/test_hook_interpreter.py:1802,
  which skips when git resolves to the git-core shim path. All three readings are
  real; they are different lanes and different machine states.
  COLLECTED AND PASSED ARE DIFFERENT POPULATIONS - measure collected with
  python -m pytest tests --collect-only, and do not quote one for the other.
  agents/pity_engine 80. shell node 52 of 52. licence 47, docs consistency 29,
  docs hook commands 21. qa_companion 18 passed 0 failed 1 skipped 3 noted.
  ruff exit 0. mypy Success over 36 files - ADVISORY.
  headless dry run exit 0, 6 skips.
  qa_companion NOTES local ruff / pytest 9.0.3 / mypy 2.1.0 are OLDER than the
  CI pins, and the interpreter here is 3.14 while CI pins 3.11. LOCAL GREEN IS
  OPTIMISTIC. CHECK CI FIRST: gh run list --branch main --limit 5

THE HEADLESS LANE IS DISARMED, BY OPERATOR INSTRUCTION 2026-09-11. The
scheduled task was REMOVED, not left expired.
  python ops/check_task_liveness.py ResinCompute-Responder
reads ABSENT exit 2, and a schtasks /Query cross-check matched 0 blocks. Zero
cron jobs, zero scheduled-task-MCP tasks, no responder or loop process live, and
ops/runtime/health.json does not exist. DO NOT RE-ARM IT WITHOUT AN EXPLICIT
OPERATOR INSTRUCTION. Verify with the checker, never a State string, never
through a pipe. Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS.
Re-arm, only if told to:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1
Kill switch:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

THE HALT RULING. Halt and PING before:
  (a) any write, delete, unlink or named-kernel-object acquisition whose target
      is OUTSIDE this repo root - explicitly C:\ProgramData, the Global\ mutex
      namespace, and C:\Program Files\Git. Session scratchpad IS IN SCOPE.
  (b) any commit or push whose diff touches ops/loop/slots.py or
      ops/loop/winmutex.py, or that trips tests/test_no_sibling_names.py.
  (c) any arming, agreement, or behaviour change in ANOTHER PARTY'S TREE.
EXPLICITLY NOT before an ordinary push that passes both suites and the
sibling-name sweep with RESIN_SKIP_PREPUSH unset.

OPEN HALT, OPERATOR HAS NOT RULED. C:\Program Files\Git holds 347
non-distribution files, 6,000,070 bytes. NOTHING WAS DELETED. 239 of the 347
carry no absolute path. Position taken: each party removes ONLY what it can
positively attribute to itself, nobody touches the 239, re-measure after.
AWAITING OPERATOR AND SIBLINGS.

WHAT LANDED 2026-09-11, ONE CODE COMMIT PLUS DOCS. DO NOT REDO.
  c514ca7 tests/test_git_subprocess_census.py now PINS A PROSE PREMISE. The
          census keeps LAUNCHERS narrow (5 subprocess entry points, line 134)
          and justifies it in its docstring at lines 55-65 by asserting none of
          the declared-uncovered launch names has a call site in DEFAULT_ROOTS
          (line 121). That premise was TRUE and GUARDED BY NOTHING. Population
          108 .py paths from git ls-files --cached --others --exclude-standard
          over tests tools ops headless scripts, 108 parsed, ZERO offenders.
          THE ROW CLOSED ON DIFFERENT TERMS THAN ITS OWN WORDING. It said
          "until the launcher set is DERIVED rather than enumerated". That is
          NOT what shipped and must not be read as done: widening the census
          was built, refuted twice and ADJUDICATED OUT, and this tree rules
          against widening a mechanism to a population measured at zero. The
          PREMISE is pinned, the POPULATION is not widened.
          TWO REFUTERS WITH DISTINCT LENSES BOTH RETURNED REFUTED on the first
          build and the repair is in the same commit.
          THE HONESTY ARM RAN ONE WAY - removal pinned for 5 of 22 names;
          dropping spawnve alone stayed GREEN, and dropping all 17 non-fixture
          names in ONE edit also stayed GREEN. Same trap as the write tracer at
          13c771f. Both directions now asserted per name.
          THE GRADER WAS WEAKER THAN THE MODULE IT GRADES on the one shape that
          module was repaired for at 2ae95f3: census_source emits
          UNRESOLVED / <unresolved:Call> for getattr(os,"system")(...) while the
          sweep emitted nothing. 17 blind-spot classes are now DECLARED and
          PINNED AS SILENCES. EVERY SHAPE IN EXACTLY ONE LIST.
          THE ASSERTION MESSAGE NAMED A POPULATION THE SWEEP DOES NOT WALK - it
          said dotted receiver; shim.os.system and os.path.system both yielded
          nothing, and collapsing the 9-line dotted resolver killed NO test.
          Dead logic deleted, message corrected, dotted shape declared silent.
  Also in c514ca7: tests/test_gate_mutation_runner.py said 18 GATE tags.
          Measured 20 - 20 hits, 20 distinct, in tools/moon_sync_responder.py
          lines 1928-2169, population git ls-files, pattern
          #\s*GATE:([A-Za-z0-9_.-]+) per line on bytes. _FLOOR is 20 in both
          judging tables.

DELIVERED OUTBOUND 2026-09-11, AND IT IS NOT A TRACKED ARTIFACT.
moon_sync_inbox/2026-09-11-2150-from-RSC-positions-on-CS-Q1-Q5-... carries
positions on all five CS questions: Q4 AGREE, Q1 Q2 Q5 CORRECT AND INCOMPLETE,
Q3 an OPERATOR ITEM because adopting it flips the shipped .githooks/pre-push
behaviour and tests/test_hook_interpreter.py's barren-PATH contract, which an
agent may not concede. The note also CORRECTS OUR OWN 2026-09-08 premise that
RSC ships zero gate tags. The whole inbox is GITIGNORED - .gitignore:115, and
git ls-files moon_sync_inbox returns 0 - so no guard polices that note. A claim
that must be guarded has to live in a TRACKED file.

TRAPS MEASURED THIS SESSION.
  - AN OPS ACTION MOVED THE SUITE'S SKIP POPULATION. Removing the responder task
    removed the only scheduled task on this box with a non-empty EndBoundary, so
    tests/test_task_liveness.py:2987 went from RUN to SKIP inside one session. A
    SKIP POPULATION IS MACHINE STATE. Not proven by re-arming - re-arming needs
    an operator instruction - so the claim is the mechanism plus before/after.
  - A COUNT'S POPULATION IS NOT THE CORPUS UNLESS YOU SAY SO. The 20 gate tags
    are 20 hits / 20 distinct in tools/moon_sync_responder.py ALONE. The same
    pattern over the whole git ls-files corpus answers 67 hits / 39 distinct
    across 8 files. c514ca7's commit message says "population git ls-files" for
    that 20 and is imprecise; this is the correction.
  - A GRADER CAN BE WEAKER THAN THE MODULE IT GRADES, and re-implementing the
    module's resolver in the test is how it happens. If a test re-implements
    logic the module already has, diff the two resolvers before trusting the
    green.
  - A ONE-SIDED HONESTY ARM, SECOND SIGHTING. A declared-name list whose removal
    direction is pinned only by the names that happen to appear in the fixtures
    is pinned for those names and nothing else. Assert BOTH directions PER NAME.
  - AN ASSERTION MESSAGE IS AN ARTIFACT THAT DRIFTS. It said dotted receiver and
    the code walked single-segment only; the dotted resolver was behaviour-dead
    and killing it killed no test. A reader who fails that arm would have
    believed a shape was checked.
  - A FLOOR AND A COLLAPSE ARE A PAIR, NOT ONE MUTANT. Neutering
    _POPULATION_FLOOR alone stays green; only collapse-with-floor versus
    collapse-with-floor-neutered separates a live floor from a dead one.
  - I BROKE MY OWN FREEZE. A one-word prose fix committed in the main tree while
    a grader was ruling against a worktree candidate. The candidate file stayed
    byte-frozen so the verdicts held, and the refuter CAUGHT the foreign edit
    and reported it. FREEZE MEANS THE WHOLE TREE, not just the candidate file.
  - ZERO CALL SITES IS A MEASUREMENT WITH A SHAPE. os.startfile, asyncio
    create_subprocess_shell / _exec, pty.spawn, os.fork and os.forkpty are all
    at 0 over the 108-file population, so every gap in that arm is a CONTRACT
    gap and not a live leak. State the population and the pattern with the zero.
  - .claude/worktrees/ HOLDS MANY STALE COPIES AND POLLUTES EVERY grep AND find.
    USE git ls-files AS THE POPULATION, ALWAYS.
  - UNDER GIT BASH SHELL STATUS IS 8-BIT. Read returncodes IN PYTHON.
  - A QUOTED GIT BASH HEREDOC COLLAPSES \n AND MANGLES BACKSLASHES. Write probe
    scripts to a FILE.
  - A NET-ZERO-BYTE mutate-and-restore WITHIN THE SAME SECOND runs the MUTANT'S
    BYTECODE. Purge __pycache__ AND .pytest_cache BOTH sides.
  - NEVER Stop-Process. taskkill /F /PID, //F //PID under Git Bash.
  - NEVER NAME A SIBLING IN PLAIN TEXT. RC, CS, LW, LL, RSC.
  - NEVER ADD A Co-Authored-By TRAILER.
  - COMMIT SUBJECTS OVER 100 CHARS draw a commit-msg warning. Keep them under.

OPEN WORK, HIGHEST FIRST. RE-PROBE EACH BEFORE SPENDING A SLICE.
  1. THE PRE-EXISTING ARMS IN tests/test_git_subprocess_census.py SOURCE THEIR
     POPULATION FROM rglob, not git ls-files - the real_sites fixture around
     line 585 and the opaque-callee walk. They rest on the unguarded premise
     that no DEFAULT_ROOTS directory holds a nested checkout. Same class this
     session just closed one file away. Measured, not hypothetical.
  2. os.startfile IS AN HONEST OMISSION AND A LIVE HOLE. The census docstring
     never declares it, so its absence from the arm's literal is honest, but it
     is a real Windows launch shape in an ops/ tree. Zero call sites today.
     Declaring it is a NEW decision, not a bug fix.
  3. THE 17 DECLARED BLIND SPOTS ARE THE HONEST FRONTIER, not defects: rebind,
     getattr, os.__dict__, dict dispatch, functools.partial, importlib,
     __import__, conditional-expression callee, dotted receiver, and the async
     and fork families. Static resolution cannot follow a rebind. Widening any
     of them is a NEW decision.
  4. THE NO-OPERATOR PROSE BINDING - a secret name narrated next to its value
     with no operator - is caught by NOTHING. Needs a proximity or entropy rule,
     a different detector CLASS with its own false-positive budget.
  5. OFF-ROSTER SECRET NAMES with non-vendor-prefixed values are invisible to
     BOTH detector paths. Roster completeness; extending it is an operator call.
  6. THE EXEMPT-ARM AUDIT IS NAME PRESENCE, not reachability. if False and an
     uncalled nested def still read as gated.
  7. THE WRITE TRACER'S DECLARED LIMITS ARE THE HONEST FRONTIER TOO: pre-context
     file objects and io.FileIO are C types whose write cannot be replaced;
     metadata-only and directory-level ops are declared.
  8. os.symlink and os.link ARMS RAN UNSKIPPED ONLY BECAUSE THIS HOST IS
     ADMINISTRATOR. They skip unprivileged, so CI exercises less than we did.
  9. A counterparty probe file in the inbox writes into ops/runtime/ and passes
     -q, so it does NOT run here unmodified. Adopting it means adapting it.
 10. A second failure once seen in tests/test_moon_sync_responder.py under a
     planted mutant is UNEXPLAINED. A non-reproduction is not an explanation.
 11. REAL VENDOR CREDENTIAL BODY LENGTHS ARE NOT DERIVABLE FROM THIS TREE. The
     shared floor of 16 is this tree's guard floor, NOT a vendor spec.

NEEDS THE OPERATOR. EIGHT, NONE BLOCKING. ROADMAP carries them as a NUMBERED
LIST so the count is read off the list, not asserted beside it.
  1. THE C:\Program Files\Git LITTER. Delete all, delete only ours, or leave?
  2. DOES AN INTERPRETER THAT NEVER STARTED DESERVE ITS OWN CLI EXIT CODE from
     ops/check_task_liveness.py? Today it lands on 3 UNKNOWN.
  3. THE THREE-RECORD DISPOSITION ASYMMETRY. record_cycle fails closed;
     answered_usable degrades; refusals_usable is fail-open on corrupt content.
  4. ARMING CS / LW / LL. Clause (c) needs bilateral agreement. LL still silent.
     The NO-ANSWER RULE is UNRULED.
  5. THE PRE-FIRST-FIRE ACTION SIGNAL. Defect claim REFUTED; enhancement
     blocked on 2.
  6. GIT_CONFIG_GLOBAL / GIT_CONFIG_SYSTEM carve-out. Keep, or scrub and rework
     tests/test_hook_gate.py's fixture?
  7. CS Q3 - their gate rule would change a SHIPPED gate: .githooks/pre-push
     warns and continues when ruff or pytest are unimportable, and
     tests/test_hook_interpreter.py asserts returncode 0 on a barren PATH. Our
     position was DELIVERED 2026-09-11 as CORRECT AND INCOMPLETE. The concession
     itself is still the operator's.
  8. CS Q5 - accepting their cross-check offer spends THEIR cycles, so it is an
     agreement under clause (c). Position DELIVERED; their premise is dead
     anyway, since we ship 20 gate tags and can reproduce it ourselves.

DO NOT REDO. Everything at c514ca7, d6437a9 and 13c771f. Everything at 37bc3bc,
2ae95f3, 7bda8cd, 78cdf96, 86491a3, 7786955, 5d785f5, 69e4e9d, 1c8aab2, 390a831,
879356d, 76ccdeb, 0d1fa70, f77c4ad, 77408ad, b3ff9fe, 3c4bcb5, 9f03062, 2dc0965,
b128eb1, 6c351b3. The os-launcher table - ADJUDICATED OUT. The
Attribute-receiver rule - ADJUDICATED OUT. The installer placeholder row -
RETIRED. The liveness action read-back - REFUTED. The slots.py re-pin - ANSWERED
NO. Manifest-as-key (withdrawn). Caveman dialect (settled). Wenyan (reverted
2026-06-27). Find each adjudicated call by HEADING in ROADMAP.md, never by line
number. Do not widen _READ_ATTRS, _FIRST, _SECOND, _SOLO, _SEP or
ABSOLUTE_USER_PATH, and do not widen LAUNCHERS.

THE OPERATOR'S ACCOUNT IS A REAL INPUT, AND NONE OF IT MAY REACH data/.
uid 692912734, xMoonbeam, NA, AR 7, World Level 0, version 7.0. 9 characters,
all ascension 0 and C0; only Dehya and Noelle resolve and the other seven render
as unknown:<id> BY DESIGN - resolving them by guessing IS VENDORING. Primogems
288, Mora 34102, Intertwined Fate 6, Stardust 165, Starglitter 0. Welkin active.
Character-banner pity 0, no guarantee, zero pulls on Weapon / Chronicled /
Character Event. data/fixtures/ is HAND-AUTHORED.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT, SUBAGENT-FIRST ALWAYS. THE AGENT THAT PRODUCED A
THING NEVER GRADES IT. FREEZE THE CANDIDATE before dispatching a grader and give
every grader THREE state assertions - HEAD sha, git status --porcelain, and the
candidate file's sha256. A COMMIT IS ITSELF A FREEZE, and THE FREEZE IS THE
WHOLE TREE - an unrelated one-word edit mid-verdict broke it this session and
the refuter caught it. AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE - if two
agree, find their SHARED INPUT and test THAT. DISPATCH REFUTERS WITH DISTINCT
LENSES; brief the lens and not the expected answer. EXPECT BUILDERS TO CORRECT
THE BRIEF - every builder did this session and every correction was right. A
BUILDER THAT STOPS AT A SEAM COLLISION IS WORKING CORRECTLY. NEVER TRUST A
SUBAGENT'S CLAIM about counts, green CI or file existence - probe it, and report
only counts observed THIS run.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes. Terseness is for CHAT ONLY.
```
