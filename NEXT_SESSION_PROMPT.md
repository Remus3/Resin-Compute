# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and it is
written by `/done` section 7 rather than by hand. `tools/publish_next_session.py`
reads this exact block to write the Desktop backup, so there must be exactly one
fenced block in this file.

```
RSC - next session, HEADLESS, operator MAY BE PRESENT.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS, LW and LL are on ORDERED STANDBY - SILENCE IS NOT DISSENT, and do not write
into their trees.

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
  BOTH WERE CONFIRMED BY THE LIVE CLIENT ON 2026-09-11: the banner detail text
  states 1.103% consolidated and this tree predicts 1.1034%; a talent-material
  tooltip named Tuesday/Friday/Sunday, exactly ROTATION_SLOT_WEEKDAYS[1] in
  core/domains.py. NEITHER FIGURE ENTERED data/ AND NEITHER MAY.

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

STATE AS OBSERVED 2026-09-14 AT 76ccdeb ON MAIN. A READING AT THAT COMMIT, NOT A
PROMISE ABOUT NOW. RE-MEASURE BEFORE CITING ANY OF IT.
  pytest tests 2155 passed 1 skipped. agents/pity_engine 80 passed.
  node --test in shell/ 52 tests 52 pass 0 fail.
  licence 47 passed, docs consistency 29 passed, docs hook commands 17 passed.
  qa_companion 18 passed 0 failed 1 skipped 3 noted.
  ruff exit 0. mypy exit 0, no issues found in 34 source files - ADVISORY.
  headless.runner --once --dry-run 0 pass 0 fail 6 skip, exit 0.
  COLLECTED AND PASSED ARE DIFFERENT POPULATIONS. Do not restate any of these as
  a live figure.
  LOCAL GREEN IS OPTIMISTIC AGAINST CI: the interpreter here is 3.14 while CI
  pins 3.11, and qa_companion NOTEs the local ruff, pytest and mypy as OLDER
  than the CI pins.
  CHECK CI FIRST, EVERY SESSION: gh run list --limit 5
  Responder task exit 1 DORMANT, sole trigger expired 2026-09-07T21:00.
  Inbox: no unread. Three LW notes were triaged AND marked last session. The
  whole inbox directory is gitignored, so no guard whose corpus comes from
  git ls-files can reach it - state the mechanism, never the universal claim.

DO NOT ARM ANYTHING. The ResinCompute-Responder task is DORMANT and is to stay
that way. Verify with the checker, never with a State string and never through a
pipe:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. A scheduled task reads
Ready forever once its triggers have expired, so Ready is not a capability.
KILL SWITCH:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

THE HALT RULING. Halt and PING THE OPERATOR before:
  (a) any write, delete, unlink or named-kernel-object acquisition whose target
      path or namespace is OUTSIDE this repo root - explicitly the machine-wide
      slot bucket under C:\ProgramData and the Global\ mutex namespace. The
      session scratchpad is IN SCOPE by operator ruling: delete its worktrees
      freely, no ping.
  (b) any commit or push whose diff touches ops/loop/slots.py or
      ops/loop/winmutex.py, or that trips tests/test_no_sibling_names.py.
  (c) any arming, agreement, or behaviour change in ANOTHER PARTY'S TREE.
EXPLICITLY NOT before an ordinary push that passes both suites and the
sibling-name sweep with RESIN_SKIP_PREPUSH unset.
WHY (b) EXISTS: tests/test_loop_concurrency.py pins those two files by sha256 as
byte-identical across three carriers, so hardening either one desynchronises
every carrier that has not moved.

WHAT LANDED 2026-09-14, ALL FIVE PUSHED AND CI GREEN ON EACH. DO NOT REDO.
  72c7041 The commit gate read an UNREADABLE CORPUS as a CLEAN one. _git in
          tools/precommit_gate.py returned stdout without consulting returncode,
          so a directory where git diff --cached exits 129 was BYTE-IDENTICAL to
          a clean tree with nothing staged - return 0, empty stderr, no
          banned-glyph scan, no py_compile, no net-new ruff. Fails closed now.
          THE TWELFTH ADJUDICATED CALL, CLOSED on 4 of 4 criteria. Proven by
          tests/test_precommit_gate_corpus.py plus an end-to-end hook attempt.
  0d1fa70 collect_facts in ops/check_task_liveness.py reported EVERY non-zero
          exit as a scheduler refusal. 0xFFFF0000 is ExitCodeInitFailure - the
          CLR never loaded and the script never ran, so the headline was false
          in every word. New branch precedes the generic one, detail string
          byte-identical. No CLI exit code changed.
  77408ad Two recorded figures REFUTED.
  f77c4ad Thirteen findings reached the roadmap.
  76ccdeb A gate whose verdict depends on FREE MEMORY, plus a correction to a
          row filed hours earlier the same session.

REFUTED FIGURES - DO NOT QUOTE THE OLD ONES FROM ANY COMMIT BODY.
  "Six arms" was wrong by roughly sevenfold. Deleting the one
  # GATE:answered-usable line in a clean clone gives exit 1 with 43 FAILURES of
  88 COLLECTED, against 89 collected and exit 0 at baseline in the SAME clone.
  89 IS NOT AN ARM COUNT - it is 69 plus len(_TAG_LINES), and _TAG_LINES is
  derived at import from the responder's own source, so DELETING A TAG DELETES A
  PARAMETRIZE CASE. Error, skip, xfail and xpassed buckets all measured empty; a
  restore control returned the clone to 89; surviving ids shift down by one.
  The replaceable "3 before" was also wrong - the pre-change bytes delivered 1.
  All four parametrized arms pass against 6c351b3^. The 3 was measured against a
  dispatch brief's ordered-then-REJECTED writer that was NEVER COMMITTED and
  exists nowhere in history.
  STILL UNRECONCILED: the unique-red-function count, 24 against 23, two passes
  disagreeing by one with NEITHER enumerating names. Enumerate once and retire
  it. The commit body of 6c351b3 carries the refuted figures and CANNOT be fixed
  - it is pushed and CI ran green on it, and rewriting published history to
  correct a number is worse than the number. docs/LEDGER.md holds the
  correction.

OPEN WORK, HIGHEST PRIORITY FIRST. RE-PROBE EACH BEFORE SPENDING A SLICE.
  1. THE PRE-PUSH GATE IS INTERMITTENT AND ITS VERDICT IS A FUNCTION OF FREE
     MEMORY. A push was refused at 2 failed, 2148 passed, 2 skipped; the same
     commit through a real pre-push hook into a scratch bare repo gave 2150
     passed, 2 skipped in 97.77s, exit 0. The environment hypothesis is REFUTED
     BY COUNTER-EXAMPLE - interpreter, PATH, powershell resolvability, user,
     timeout and cwd were each ruled out individually. Cause is load: the
     low-virtual-memory detector named a python process at about 10.4 GB and the
     refused run took 474.67s, spanning two events. Two arms in
     tests/test_task_liveness.py COLLAPSE "the census machinery is broken" with
     "powershell could not start just now". DO NOT SOFTEN THE ARMS - FAILED must
     fail and only NONE may skip, which is what kills a vacuous skip. The repair
     is a DISTINCT CLASS for a host-start failure. Collected total was 2152 in
     every run, so nothing was silently dropped.
  2. THE WHOLE-TREE FALSE-RED POPULATION IS UNKNOWN, AND THAT IS THE ROW. Both
     numbers this tree has quoted - 8 red arms over 7 modules, and a 5-module
     candidate list - came from NAME-BASED ONE-TERM FILTERS, and the second was
     measured to OVER-REPORT: only THREE of the five shell git at all.
     tests/test_ci_history_depth.py executes none, its only subprocess.run text
     being a STRING LITERAL fed to a regex; tests/test_guard_worktree_blindness.py
     has no subprocess call at all. A skip added to either would be a FALSE SKIP
     with no defect behind it. RUN THE AST ENUMERATION of every subprocess call
     whose argv[0] is git across tests/, tools/, ops/, headless/ and scripts/
     FIRST, publish the list, and only then size the work. Any "N to 0" claim
     before that inherits the defect found in LW's own 43.
  3. THE SKIP-then-RUN SITE-LEVEL ARM, genuinely new. tests/test_conftest_git_gate.py
     grades the HELPERS and nothing grades a repaired CALL SITE end to end: run
     the module with git absent and assert it SKIPS, run it with git present and
     assert it RUNS ITS ASSERTIONS. The RUN half is load-bearing - a skip-only
     arm is satisfied by a guard that never lets anything run.
  4. answered_usable and refusals_usable in tools/moon_sync_responder.py share a
     MISSING THIRD CLASS: readable-but-permanently-unwritable. Seeded with valid
     JSON and a read-only attribute, the real run_once delivered 3 files over 3
     cycles into a repo this one does not own. NOT LIVE while the task is
     dormant. Any fix must touch BOTH.
  5. LW'S schtasks/POWERSHELL BACKSLASH FINDING IS UNSWEPT HERE, and unswept is
     NOT clean. Candidate carriers: ops/install_responder_task.ps1,
     ops/install_scheduled_task.ps1, ops/ResinCompute-Responder.xml,
     ops/ResinCompute-Supervisor.xml, and the reader ops/check_task_liveness.py.
  6. A FIFTH DEGRADE-TO-EMPTY SITE IS IN A GUARD - scan_file in
     tests/test_task_state_claims.py returns [] on OSError, so an unreadable
     tracked file reports ZERO FINDINGS.
  7. core/provenance.py declares sha256 and parent_sha256 and contains NO
     hashlib. The only validation is a FORMAT REGEX - a shape arm pinning format
     and not input. Recompute-and-compare, or rename the field ADVISORY, BEFORE
     the first production writer lands.

NEEDS THE OPERATOR, NONE BLOCKING.
  - THE THREE-RECORD DISPOSITION ASYMMETRY IS THE OPERATOR'S CALL, ON THE SET
    AND NOT ON A PAIR. record_cycle fails closed on all unreadable metrics
    classes; answered_usable degrades on replaceable and fails closed only on
    structural; refusals_usable is fail-open on corrupt content. The defence is
    what the bytes are FOR, and that is an ARGUMENT, NOT A MEASUREMENT.
  - DOES AN INTERPRETER THAT NEVER STARTED DESERVE ITS OWN CLI EXIT CODE from
    ops/check_task_liveness.py? Today it lands on 3 UNKNOWN. For: a host-start
    failure is a retryable fact about this machine now. Against: the five
    existing codes HAVE CALLERS. A ruling here constrains open item 1.
  - ARMING CS / LW / LL. Clause (c) needs bilateral agreement, three of five
    cannot reply, and the adopted rule is HALT AND WAIT WITH NO TIMEOUT. The
    NO-ANSWER RULE is UNRULED, not policy: timeout-plus-default-deny was
    PROPOSED by an adjudicator and the operator has not ruled.
  - LW'S Q2 - whether the gate tag literal is RC's # GATE: spelling - is
    formally UNANSWERED BY THREE OF FIVE, because LW defers it to its own
    operator as a POLICY COMMITMENT rather than a measurement.
  - LW'S Q4 adds ONE WORD, "undigested", to a position we already hold: nobody
    copies a file unrequested AND UNDIGESTED. SILENCE IS NOT AGREEMENT, so an
    unanswered added word READS AS DISSENT. ANSWER IT.

INBOX VERDICTS FROM LAST SESSION, so they are not re-derived.
  LW's Q3 conftest claim is refuted and we had ALREADY retracted it, so no new
  correction is owed - what LW adds is a SECOND CARRIER, upgrading RETRACTED to
  DISPROVED. LW's "43 to 0" is HALF MEASURED: the AFTER was re-run, the BEFORE
  row is byte-identical to their earlier note and was carried forward, so the
  delta is ASSERTED - and their own disclosed box saturation, applied to the
  post-repair probe only, would inflate the 43 numerator by the same noise.
  Their R3, that a present-but-broken git must still FAIL, CONFLICTS with our
  shipped classify_git_probe, which SKIPs it, and tests/test_conftest_git_gate.py
  pins that question as deliberately OPEN - adopting their rule would SILENTLY
  CLOSE AN OPEN OPERATOR CALL. Their PATH-strip mirror is contraindicated here:
  shutil.which is PATHEXT-aware while subprocess.run goes through CreateProcess,
  which appends only .exe. Their third note offers NO digest at all, and their
  with-git passing count moved by twelve between notes, unstated.

TRAPS THAT ACTUALLY BIT, every one MEASURED.
  - UNDER GIT BASH THE SHELL STATUS IS 8-BIT, so an exit of 4294901760 reads as
    0 there. Only a returncode read IN PYTHON carries the full 32 bits, so that
    exit code CANNOT BE CHASED THROUGH A SHELL AT ALL.
  - A COMPOUND COMMAND'S EXIT STATUS IS ITS LAST ELEMENT. A trailing echo
    reported 0 and MADE A REFUSED PUSH LOOK LIKE IT HAD LANDED. Redirect each
    command to its own file and read the codes separately.
  - /tmp UNDER GIT BASH IS A DIRECTORY INSIDE THE GIT INSTALLATION, not the C:
    drive root, AND FILES THERE PERSIST ACROSS AGENTS. A stale file at a shared
    path reads exactly like fresh output: a subagent's leftover was misread as a
    hook blocking a commit that had NEVER RUN, because a failed python -c had
    short-circuited the && chain first. cygpath -w before claiming anything.
  - A GATE THAT CANNOT FAIL PASSES ON BOTH SIDES OF A REAL DEFECT. Ask what
    INPUT an arm feeds, never whether the arm exists.
  - FileNotFoundError WinError 2 IS RAISED AT EXEC, so check=True is IRRELEVANT
    to it. That kills the obvious wrong fix.
  - RED BY ABSENT API IS NOT RED BY MEASUREMENT. An arm dying on AttributeError
    for a symbol the fix introduces has graded its own scaffolding.
  - A LINE NUMBER IN A DOC DECAYS - three consecutive sessions here. CITE BY
    SYMBOL NAME and verify the symbol exists first.
  - tests/test_docs_consistency.py REJECTS A BACKTICKED POINTER AT AN UNTRACKED
    OR ABSENT RUNTIME PATH. Name such a path in PROSE, unbackticked, with the
    reason. ops/runtime/ and the inbox are the usual offenders.
  - write_text EMITS CRLF ON WINDOWS and .gitattributes eol=lf hides it from
    every diff. Write bytes explicitly and check for CR.
  - NEVER TYPE A BANNED GLYPH AS A LITERAL, even in a test enforcing the rule.
    Build it from chr(0x2014) or chr(0xFFFD).
  - grep -c on a hex escape range IS NOT A CHARACTER CLASS. It once found 1785
    non-ASCII lines in a file with zero non-ASCII bytes. Check bytes IN PYTHON.
  - A QUOTED HEREDOC STILL MANGLES BACKSLASHES. A FALSE CLEAN SWEEP is the
    failure mode, not an error.
  - A NET-ZERO-BYTE mutate-and-restore WITHIN THE SAME SECOND runs the MUTANT'S
    BYTECODE. Purge __pycache__ AND .pytest_cache on BOTH sides.
  - NEVER git checkout -- TO RESTORE A MUTATION, and it is far worse in a
    worktree holding uncommitted slice work. Save bytes, restore, verify by
    sha256, and assert source.count(old) == 1 before substituting.
  - A PYTEST PROGRESS LINE IS PER-LINE, NOT THE WHOLE RUN. Counting the last
    line once named the wrong module.
  - AN EMPTY PYTEST PARAMETRIZE IS 1 skipped, exit 0, NOT a failure.
  - A SCHEDULED TASK READS Ready FOREVER once its triggers expire. A State
    string names a state, not a capability.
  - NEVER Stop-Process. taskkill /F /PID, and under Git Bash taskkill //F //PID
    - MSYS rewrites a lone /F into a drive path and the call fails SILENTLY when
    redirected to /dev/null.
  - py_compile BEFORE ANY RESTART. A syntax error crashes silently under
    pythonw.exe. Restart with echo restart > restart_trigger.txt and verify by
    reading a NEW pid and alive=true out of the health file under ops/runtime/,
    never by looking at a window.
  - NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. RC, CS, LW, LL, RSC.
  - NEVER ADD A Co-Authored-By TRAILER, and never file its absence as a defect.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating and
self-adversarial BY DEFAULT, and SUBAGENT-FIRST ALWAYS. The main session is the
OPERATOR'S SURFACE and stays quiet and clear. THE AGENT THAT PRODUCED A THING
NEVER GRADES IT. FREEZE THE CANDIDATE before dispatching a grader, and give
every grader THREE state assertions - HEAD sha, git status --porcelain, and the
candidate file's sha256 - so it can tell you the tree moved instead of grading
the wrong bytes.
AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. If two agree, find their shared
input and test THAT - two documents once agreed about a metrics trim and were
ONE input counted twice, proven by the identical WRONG line number in both.
DISPATCH REFUTERS WITH DISTINCT LENSES, never N identical skeptics.
ADJUDICATE THE CONTESTED HALF BEFORE DISPATCH, NOT IN PARALLEL WITH IT.
SendMessage is DISABLED here, so a brief found wrong mid-run COSTS A WHOLE
SLICE - measured, three sequential slices where one was planned.
A BUILDER THAT STOPS AT A SEAM COLLISION IS WORKING CORRECTLY. Dispatch a slice
for the missing files; never widen a write-list mid-run.
TaskStop a finished agent once its report lands - one re-notified about twenty
times after reporting complete.
NEVER TRUST A SUBAGENT'S CLAIM about test counts, green CI or file existence.
Probe it independently, and report only counts observed THIS run.

DO NOT REDO. Everything at 72c7041, 0d1fa70, 77408ad, f77c4ad and 76ccdeb.
Everything at b3ff9fe, 3c4bcb5, 9f03062, 2dc0965, b128eb1 and 6c351b3. The
three vacuous floors. The supervisor and responder argv graders. The
lane-selection pin. The _SOLO view asymmetry. The name-to-site binding table.
The undeclared-shape-grader detector. The atomic_io 0-byte temp leak. The eight
gates exercised by nothing. The slots.py re-pin - RC's step 1 is ANSWERED NO and
RC's premise is wrong, steps 2-4 HALTED under clause (c), and NOTHING IS BLOCKED
ON US. The ledger-instance divergence check - ANSWERED, no divergence, and ZERO
M1-M6 rows have ever been written live. Manifest-as-key (withdrawn). Caveman
dialect (settled). Wenyan (reverted 2026-06-27). Do not re-litigate the twelve
adjudicated calls without reading them - find each by HEADING in ROADMAP.md,
never by line number. Do not widen _READ_ATTRS, _FIRST, _SECOND, _SOLO or _SEP:
WIDENING A MATCHER is the response this tree has been defeated by three times,
and after the second defeat the question is what claim the mechanism can support.

THE OPERATOR'S ACCOUNT IS A REAL INPUT, AND NONE OF IT MAY REACH data/.
uid 692912734, xMoonbeam, NA, AR 7, World Level 0, version 7.0. 9 characters,
all ascension 0 and C0; only Dehya and Noelle resolve and the other seven render
as unknown:<id> BY DESIGN - resolving them by guessing IS VENDORING. Primogems
288, Mora 34102, Intertwined Fate 6, Stardust 165, Starglitter 0. Welkin active.
Character-banner pity 0, no guarantee, zero pulls on Weapon / Chronicled /
Character Event. Original Resin observed 200/200 at 2026-09-11T01:39:48Z - and a
projection saturated at the cap carries no information, which is why the panel
prints no present-tense number there. data/fixtures/ is HAND-AUTHORED ONLY.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes. Terseness is for CHAT ONLY - paths, commands, code
and every committed artifact stay byte-exact.
```
