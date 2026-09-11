# Next session prompt

Paste the block below into a cold session. It is the hand-off.

```
RSC - next session, HEADLESS, operator MAY BE PRESENT.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS and LW BROKE STANDBY on 2026-09-11 and both sent notes; LL still silent.
SILENCE IS NOT DISSENT, and do not write into any of their trees.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before adding a data source read
docs/LICENSE_NOTES.md. Before re-litigating a past choice read
docs/adr/README.md. A fresh clone runs ZERO hooks - first action there is
python scripts/install_hooks.py.

DO NOT RE-DERIVE GACHA CONSTANTS FROM MEMORY OR FROM A WEB SEARCH. They are in
docs/SPEC_SCAFFOLD.md section 3 with the corrections in
docs/adr/ADR-003-forecaster-model.md.
  - The 50/50 is 55.000% CONSOLIDATED since version 5.0, not 50%.
  - The weapon soft-pity ramp SATURATES AT PULL 77 under a 7% increment. Any
    claim of 79 or 80 is arithmetically impossible.
  - 1.600% is 1/E[wishes per 5-star], a long-run average, and is NEVER a
    per-wish Bernoulli parameter. Forecasts use an absorbing Markov chain.
  NEITHER FIGURE ENTERED data/ AND NEITHER MAY.

GATES, in /done order, EACH AS ITS OWN COMMAND. CHAINING WITH && REPORTS ONLY
THE LAST LINK - a suite failure has already hidden behind a passing smoke test
at the end of a chain in this tree.
  python -m pytest tests/test_licence_posture.py
  python -m pytest tests/test_docs_consistency.py
  python -m pytest tests/test_docs_hook_commands.py
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
DO NOT PASS -q ON THE COMMAND LINE. pytest.ini already sets it, and a second -q
makes it -qq, which deletes the summary line entirely.
NEVER RUN pytest . FROM THE ROOT. The two suites run SEPARATELY.
mypy IS ADVISORY. Its files= roots are core/, engines/, ingest/,
agents/pity_engine/ and tools/ only, so a Success says NOTHING about scripts/,
surface/, headless/, ops/, tests/ or conftest.py. Zero out of zero reads as a
pass. Run it anyway so a regression in a covered root surfaces.

STATE AS OBSERVED 2026-09-11 AT 78cdf96 ON MAIN. A READING AT THAT COMMIT, NOT A
PROMISE ABOUT NOW. RE-MEASURE BEFORE CITING ANY OF IT.
  pytest tests 2625 passed 1 skipped. agents/pity_engine 80 passed.
  node --test in shell/ 52 of 52. licence 47, docs consistency 29,
  docs hook commands 21. qa_companion 18 passed 0 failed 1 skipped 3 noted.
  ruff exit 0. mypy Success over 35 source files - ADVISORY.
  headless.runner --once --dry-run exit 0, 6 skips.
  COLLECTED AND PASSED ARE DIFFERENT POPULATIONS. Local green is OPTIMISTIC
  against CI: the interpreter here is 3.14.4 while CI pins 3.11.
  CHECK CI FIRST, EVERY SESSION: gh run list --branch main --limit 5
  Responder task exit 1 DORMANT, sole trigger expired 2026-09-07T21:00.

DO NOT ARM ANYTHING. Verify with the checker, never with a State string and
never through a pipe:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. A scheduled task reads
Ready forever once its triggers have expired.
KILL SWITCH:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

THE HALT RULING. Halt and PING THE OPERATOR before:
  (a) any write, delete, unlink or named-kernel-object acquisition whose target
      path or namespace is OUTSIDE this repo root - explicitly the machine-wide
      slot bucket under C:\ProgramData and the Global\ mutex namespace. The
      session scratchpad is IN SCOPE by operator ruling.
  (b) any commit or push whose diff touches ops/loop/slots.py or
      ops/loop/winmutex.py, or that trips tests/test_no_sibling_names.py.
  (c) any arming, agreement, or behaviour change in ANOTHER PARTY'S TREE.
EXPLICITLY NOT before an ordinary push that passes both suites and the
sibling-name sweep with RESIN_SKIP_PREPUSH unset.

WHAT LANDED 2026-09-11, FOUR COMMITS, ALL PUSHED. DO NOT REDO.
  7786955 The suite was writing the operator's LIVE DAY LOG - 17492 bytes from
          51 nodeids across 12 files, synthetic error records. Fixed at the ROOT:
          core.config.load_config already derived log_dir from RC_LOG_DIR WHEN
          USED and nothing had used it, so ONE assignment at rootdir conftest
          import isolates both suites. core/log_setup.py UNCHANGED. Also the
          publish gate and five git-gate repairs, each refuted before landing.
  5d785f5 Both installer placeholder guards were blind to a DIGIT. PowerShell
          -match is case-INSENSITIVE, so lowercase never leaked; only the digit
          axis did, regardless of case. Responder's UTF-16 declaration relabel
          ran BEFORE its guard and masked a token inside the declaration.
  86491a3 A push from a LINKED WORKTREE exports GIT_DIR and ran both suites
          against a SUBSTITUTED CORPUS. 52 worktree entries on this machine.
  78cdf96 git rev-parse --local-env-vars is git's OWN list - FIFTEEN names - and
          the first scrub covered five. Tuple now fourteen with a runtime
          reconciliation arm against git's list.

TRAPS THAT ACTUALLY BIT, every one MEASURED THIS SESSION.
  - GIT PUBLISHES ITS OWN LIST. git rev-parse --local-env-vars names the
    repo-local variables. A reasoned set covered 5 of 15 and missed
    GIT_CONFIG_PARAMETERS, WHICH GIT EXPORTS TO HOOKS ITSELF.
  - AN rc-0 FILTER IS BLIND TO returncode-AS-ANSWER. check-ignore -q returns 0
    for ignored and 1 for not. State an answer as the PAIR (returncode, stdout).
  - AGREEMENT FROM A HOLED INSTRUMENT IS LUCK. A counterparty reproduced our
    three figures exactly with a tracer missing a patch point we had; the
    subject sat in both instruments' overlap. Find the SHARED INPUT and test it.
  - A PLUGIN THAT PATCHES IN pytest_configure IS TOO LATE. A logging handler
    built at conftest import caches a raw stream and bypasses the wrapper
    forever. Measured: disk 234 bytes, that plugin reports 0.
  - PATCH io.open AS WELL AS builtins.open. pathlib resolves io.open by
    attribute at call time, so builtins-only misses every Path.write_text.
  - NEITHER TRACER SEES os.open PLUS os.fdopen - the fd is an int - and neither
    patches DELETION OR TRUNCATION AT ALL.
  - A CLONE IS A BETTER INSTRUMENT THAN A TRACER. In a clone REPO_ROOT is
    __file__-derived, so its logs path is one NO DAEMON WRITES and a snapshot
    there is fully attributing. DO NOT snapshot-diff the live tree: an idle
    300-second control with no suite running showed live files changing anyway.
  - ATTRIBUTE A GAP, DO NOT ROUND IT. A 1922-byte tracer-to-disk gap was first
    given wholly to child processes; 89 bytes are CRLF TRANSLATION and 1833
    remain UNAPPORTIONED.
  - A NEW ARM MUST BE MUTATION-GRADED, AND ITS OWN BUILDER CANNOT GRADE IT.
    Every repair this session was refuted by a mutant its builder did not try.
  - A DECOY OR STUB THAT VARIES ONE POSITION PINS ONE POSITION.
  - AN EMPTY PARAMETRIZE IS 1 skipped, exit 0.
  - A CONSERVATION ASSERTION IS THE ONLY SHAPE THAT CATCHES A DROP, and it must
    conserve the RIGHT LEVEL - rows conserved while NODES were droppable.
  - A SPAN-BASED ATTRIBUTION LOSES A DECORATOR. node.lineno for a decorated
    FunctionDef is the def line, so a launch in a decorator is counted by the
    census and attributed to nobody.
  - NAME PRESENCE IS NOT REACHABILITY. A gate under if False, or in an uncalled
    nested def, reads as gated to an ast.walk.
  - A MODULE-LEVEL GUARD COLUMN IS NOT A PER-SITE FACT. census guard answers
    GATED if the module names a helper anywhere.
  - DERIVE POPULATIONS BY SUBTRACTION. An enumerated list omits the position
    nobody named. A FILTER'S POPULATION IS NOT THE REPAIR'S.
  - UNDER GIT BASH THE SHELL STATUS IS 8-BIT, so 4294901760 reads as 0. Read
    every returncode IN PYTHON.
  - A COMPOUND COMMAND'S EXIT STATUS IS ITS LAST ELEMENT.
  - A NET-ZERO-BYTE mutate-and-restore WITHIN THE SAME SECOND runs the MUTANT'S
    BYTECODE. Purge __pycache__ AND .pytest_cache on BOTH sides. NEVER
    git checkout -- to restore a mutation.
  - A QUOTED GIT BASH HEREDOC COLLAPSES \n AND MANGLES BACKSLASHES. Write probe
    scripts to a FILE. RED BY BROKEN SCAFFOLDING IS NOT RED BY MEASUREMENT.
  - re.compile ON AN IDENTICAL PATTERN STRING RETURNS THE IDENTICAL OBJECT, which
    silently defeated an identity arm here.
  - NEVER RUN git init --bare WITH NO PATH ARGUMENT. Under an inherited GIT_DIR
    it reinitialises the WORKTREE and writes bare = true into the SHARED config,
    after which the main checkout's git status returns rc 128. The explicit-path
    form is harmless. This tree has ZERO --bare call sites.
  - A LINE NUMBER IN A DOC DECAYS. CITE BY SYMBOL NAME.
  - tests/test_docs_consistency.py REJECTS A BACKTICKED POINTER AT AN UNTRACKED
    OR ABSENT RUNTIME PATH. Name such a path in PROSE, unbackticked.
  - write_text EMITS CRLF ON WINDOWS and .gitattributes eol=lf hides it.
  - NEVER TYPE A BANNED GLYPH AS A LITERAL - build it from chr(0x2014).
  - grep -c ON A HEX ESCAPE RANGE IS NOT A CHARACTER CLASS. Check bytes IN PYTHON.
  - NEVER Stop-Process. taskkill /F /PID, and //F //PID under Git Bash.
  - NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. RC, CS, LW, LL, RSC.
  - NEVER ADD A Co-Authored-By TRAILER, and never file its absence as a defect.

OPEN WORK, HIGHEST PRIORITY FIRST. RE-PROBE EACH BEFORE SPENDING A SLICE.
  1. THE CENSUS EMITS NO SITE AT ALL when call.func is itself a Call -
     getattr(subprocess, "run")(...) and functools.partial(subprocess.run)(...) -
     and its launcher set is subprocess-only, so os.system is invisible.
     CONSERVATION CANNOT HELP: there is nothing to conserve. Everything built on
     the census inherits this.
  2. NEITHER WRITE TRACER SEES os.open PLUS os.fdopen, and that shape is LIVE in
     ops/loop/slots.py, which writes the machine-wide bucket the halt ruling
     names. Neither patches deletion or truncation. shutil.rmtree runs at session
     finish and unlink appears in nine files.
  3. THE NO-OPERATOR PROSE BINDING - a secret name narrated next to its value
     with no operator at all - is the MOST plausible leak shape in an
     agent-written hand-off and is caught by NOTHING. Needs a proximity or
     entropy rule, a different detector class with its own false-positive budget.
  4. OFF-ROSTER SECRET NAMES with non-vendor-prefixed values are invisible to
     BOTH detector paths by construction. Roster completeness, not a matcher
     question, and extending the roster is an operator call.
  5. THE EXEMPT-ARM AUDIT IS NAME PRESENCE, not reachability. A gate after the
     launch is now caught by statement order; if False and an uncalled nested def
     still read as gated.
  6. TWO INBOX ITEMS ARE APPLICABLE-AND-NOT-DONE: the fifth LW note saying the
     plugin already delivered is SUPERSEDED, and lw_false_red_probe, which writes
     into ops/runtime/ and passes -q, so it does NOT run here unmodified.
  7. A second failure once seen in tests/test_moon_sync_responder.py under a
     planted mutant is UNEXPLAINED. The offered collateral explanation was
     refuted by reading, and a non-reproduction is not an explanation.
  8. REAL VENDOR CREDENTIAL BODY LENGTHS ARE NOT DERIVABLE FROM THIS TREE. Three
     agents said so independently. The shared floor of 16 is this tree's guard
     floor, NOT a vendor spec. Do not invent one.

NEEDS THE OPERATOR. FIVE NOW, ALL STILL UNANSWERED, NONE BLOCKING.
  1. DOES AN INTERPRETER THAT NEVER STARTED DESERVE ITS OWN CLI EXIT CODE from
     ops/check_task_liveness.py? Today it lands on 3 UNKNOWN, collapsing "the
     census machinery is broken" with "powershell could not start just now". A
     ruling constrains the liveness arms AND question 4.
  2. THE THREE-RECORD DISPOSITION ASYMMETRY, on the set and not on a pair.
     record_cycle fails closed on all unreadable metrics classes;
     answered_usable degrades on replaceable; refusals_usable is fail-open on
     corrupt content.
  3. ARMING CS / LW / LL. Clause (c) needs bilateral agreement. CS and LW have
     now broken silence, LL has not. The NO-ANSWER RULE is UNRULED -
     timeout-plus-default-deny was PROPOSED by an adjudicator and never ruled on.
  4. THE PRE-FIRST-FIRE ACTION SIGNAL. ops/check_task_liveness.py never reads a
     registered task's action back. THE DEFECT CLAIM WAS REFUTED - the contract
     is FIRING not SUCCEEDING - and what survives is an ENHANCEMENT blocked on 1.
  5. NEW. GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM are deliberately NOT scrubbed
     because tests/test_hook_gate.py sets them, but an inherited value pointing
     at a config carrying core.excludesFile was MEASURED to change a corpus at
     rc 0. Keep the carve-out, or scrub and rework that fixture?

INBOX STATE. Six items were unread at session end and one outbound note was
written answering CS and LW: the CS GIT_DIR defect VERIFIED and its --bare
damage narrative NARROWED, the CS withdrawal acknowledged with neither claim
ever ingested here, one LW claim about our commit 7786955 refuted against
measurement, the LW plugin read and NOT ADOPTED - shape only - and two findings
passed back. TRIAGE THE REMAINDER AND MARK ONLY WHAT YOU TRIAGED; an inflated
watermark is worse than none. One process failure to know about: --mark was run
once this session BEFORE a loose verbatim file had been triaged.

DO NOT REDO. Everything at 7786955, 5d785f5, 86491a3 and 78cdf96. Everything at
69e4e9d, 1c8aab2, 390a831, 879356d, 76ccdeb, 0d1fa70, f77c4ad, 77408ad, b3ff9fe,
3c4bcb5, 9f03062, 2dc0965, b128eb1 and 6c351b3. The installer placeholder row -
RETIRED, the guard was there since 1d80f8c. The backslash sweep - SWEPT, latent,
reachability nil. The liveness action read-back - REFUTED as a defect. The
slots.py re-pin - ANSWERED NO. The ledger-instance divergence check - ANSWERED.
Manifest-as-key (withdrawn). Caveman dialect (settled). Wenyan (reverted
2026-06-27). Do not re-litigate the adjudicated calls without reading them -
find each by HEADING in ROADMAP.md, never by line number. Do not widen
_READ_ATTRS, _FIRST, _SECOND, _SOLO or _SEP.

THE OPERATOR'S ACCOUNT IS A REAL INPUT, AND NONE OF IT MAY REACH data/.
uid 692912734, xMoonbeam, NA, AR 7, World Level 0, version 7.0. 9 characters,
all ascension 0 and C0; only Dehya and Noelle resolve and the other seven render
as unknown:<id> BY DESIGN - resolving them by guessing IS VENDORING. Primogems
288, Mora 34102, Intertwined Fate 6, Stardust 165, Starglitter 0. Welkin active.
Character-banner pity 0, no guarantee, zero pulls on Weapon / Chronicled /
Character Event. Original Resin 200/200 at 2026-09-11T01:39:48Z - a projection
saturated at the cap carries no information. data/fixtures/ is HAND-AUTHORED ONLY.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT, and SUBAGENT-FIRST ALWAYS. THE AGENT THAT PRODUCED A
THING NEVER GRADES IT. FREEZE THE CANDIDATE before dispatching a grader, and give
every grader THREE state assertions - HEAD sha, git status --porcelain, and the
candidate file's sha256. A COMMIT IS ITSELF A FREEZE. AGREEMENT BETWEEN TWO
AGENTS IS NOT EVIDENCE. DISPATCH REFUTERS WITH DISTINCT LENSES - repeating one
lens is a third identical skeptic, not a distinct one. SendMessage is DISABLED
here, so a brief found wrong mid-run COSTS A WHOLE SLICE - adjudicate the
contested half before dispatch, and EXPECT BUILDERS TO CORRECT THE BRIEF: three
did this session and all three were right. A BUILDER THAT STOPS AT A SEAM
COLLISION IS WORKING CORRECTLY. TaskStop a finished agent once its report lands.
NEVER TRUST A SUBAGENT'S CLAIM about test counts, green CI or file existence -
probe it independently, and report only counts observed THIS run.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes. Terseness is for CHAT ONLY - paths, commands, code
and every committed artifact stay byte-exact.
```
