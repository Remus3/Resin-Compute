# ResinCompute roadmap

Open work, newest priorities first. Aspirational items live at the bottom.
Per-item completion history belongs in `docs/LEDGER.md`, never in `CLAUDE.md`.

## Status

Scaffold shipped 2026-09-06. The tree stands up, both suites run, the headless
lane smoke test passes, and the forecaster is correct for the current game
version. What follows is everything the scaffold deliberately did not do.

## Now

- **HALTED 2026-09-11 UNDER CLAUSE (a), AND THE SURFACE IS SHARED BY AT LEAST
  FOUR TREES. `C:\Program Files\Git` IS AN UNDECLARED MACHINE-WIDE SCRATCH
  BUCKET HOLDING 347 FILES AND 6,000,070 BYTES.** Nothing has been deleted,
  including this tree's own two files.

  THE MECHANISM, and it is one line to reproduce. `$TMPDIR` is UNSET in the Bash
  tool as it runs here, so `cat > "$TMPDIR/probe.py"` expands to `/probe.py` and
  MSYS maps the leading slash to the git installation root. The redirect
  SUCCEEDS. There is no error, the script runs, and the litter is invisible from
  every repo root. This tree had the trap recorded as a `/tmp` redirect problem
  and that framing was TOO NARROW: the trigger is any unset-variable expansion
  leaving a leading slash, so `"$TMP/x"` and `"$SCRATCH/x"` do it too.

  ATTRIBUTION, WITH THE INSTRUMENT'S LIMIT STATED FIRST. 239 of the 347 files
  contain NO absolute path at all - mostly bare pytest or ruff output - so what
  follows counts files that NAME a root, never files PRODUCED by one. Occurrences
  across the whole set: 126 the CS repo root, 47 the CS worktree bucket, 29
  `C:\Users`, 20 the RC worktree bucket, 11 the LL repo root, 4 the RC repo root,
  4 `C:\ProgramData`, 4 `C:\Program Files`, 1 the LW repo root, 1 the LL capture
  directory, 1 this repo root. Do NOT read the 126 as authorship.

  WHY IT IS THE SAME CLASS AS THE SLOT BUCKET. The directory is machine-scope,
  not gitignored, and reachable by no sweep any of the five trees runs, because
  every such sweep derives its corpus from `git ls-files` and an untracked path
  outside the repo is beyond that corpus by construction. Eighteen of the files
  carry the operator's account path in their content; none of those eighteen
  names this repo root, so this tree cannot say who wrote them and has not
  guessed. One party's cleanup silently destroys another party's state, which is
  exactly the property the halt ruling names for `C:\ProgramData` and `Global\`.

  BROADCAST, NOT DECIDED. Asked of CS, RC, LW and LL in
  `moon_sync_inbox/2026-09-11-2015-from-RSC-a-shared-scratch-bucket-nobody-declared-347-files-in-the-git-install-directory.md`:
  delete, archive or leave; who owns the 239 unattributable files; should all
  five add the path to their own clause (a); and is a guard worth sharing as
  bytes. This tree's stated position is that each party removes ONLY what it can
  positively attribute to itself, nobody touches the 239, and the directory is
  re-measured afterwards so the residue is a known number rather than an assumed
  zero. SILENCE READS AS DISSENT on all four.

- **CLOSED 2026-09-11 AT `2ae95f3` - A SILENT CALLEE CLASS BECAME ROWS, AND TWO
  WIDENINGS BUILT IN THE SAME SLICE WERE ADJUDICATED BACK OUT.** `_launcher_name`
  branched on `ast.Attribute` and `ast.Name` only, so a call whose `func` is
  itself a `Call`, a `Subscript` or a `BoolOp` produced NO ROW AT ALL. Silence,
  not a wrong bucket, and a conservation assertion is powerless against it
  because there is nothing to conserve. Repaired SUBTRACTIVELY, so a future
  `IfExp` or `Lambda` callee is covered by construction. Census moves
  78 {GIT 38, NOT-GIT 22, UNRESOLVED 18} to 85 {38, 22, 25}; GIT and NOT-GIT do
  not move and every new row is opaque. Reachability of the silent class is ZERO
  today - all seven nodes are stub or predicate invocations - so this is CONTRACT
  HONESTY and not a closed leak, and it must not be written up as one.

  THE ADJUDICATED CALL, and the criteria and per-criterion verdicts are in
  `docs/LEDGER.md` under this session's heading. The same slice also added an
  os-launcher table with a per-launcher executable position and an
  Attribute-receiver rule. Two refuters with DISTINCT LENSES refuted both. The os
  table's flagship arm built its fixture FROM the value it pinned, so the fixture
  MOVED WITH THE MUTANT: 6 of 10 sampled position mutants survived for one agent
  and 16 of 19 for the other, and shrinking the spelling set from 24 names to two
  also survived. An adjudicator that produced neither candidate ruled NARROW on
  CONTRACT grounds, governed by the standing do-not-widen ruling under the
  2026-09-09 heading in this file. Both widenings are deleted. The
  Attribute-receiver case is now a PINNED SILENCE whose spelling set is a literal
  in the test, so that arm cannot move with a mutant either.

  TWO CLAIMS THIS TREE MADE ABOUT ITS OWN CENSUS WERE FALSE. The widened title
  said "every process launch" while `subprocess.getoutput` and `getstatusoutput`
  launch a process and are absent from `LAUNCHERS` - `census_source` on such a
  call returns `[]`. And `format_report` printed "total launch sites" over a
  population the module's own docstring says launches nothing. The title is
  reverted with the gap DECLARED, the report noun is bucket-neutral, and an arm
  feeds an opaque fixture and asserts the word does not appear over it.

  ONE ADJUDICATOR FINDING WAS OVERSTATED AND IS CORRECTED HERE rather than
  carried. It cited `_HARNESS_AXES` in `tests/test_task_liveness.py` as a rival
  tracked launcher list including `getoutput`. That tuple lists subprocess module
  ATTRIBUTES a test shim must expose and also contains `CalledProcessError`,
  `DEVNULL`, `PIPE` and `__name__`. It is not a launcher population. The
  getoutput gap is real and was measured directly; the tuple is not evidence for
  it.

  FOUR PROSE COUNTS HAD DECAYED AND THREE WERE ALREADY WRONG BEFORE THIS SLICE
  TOUCHED ANYTHING. `tests/test_conftest_git_gate_sites.py` said "five armed
  modules" while `len(_SITES)` is 6, and "four derive nothing" while it is five.
  Its claim that `tests/test_line_endings.py` was the ONLY module reading
  differently under the two bucket sets was false when written: three did at the
  old census and five do now. `conftest.py` and `tests/test_git_env_scrub.py`
  both quoted 78. The 28-of-38 subcommand split in those two comments is
  UNCHANGED and was deliberately left - GIT stayed at 38 and every new row is
  UNRESOLVED, so that split cannot have moved.

  THE DURABLE RULE: A PROSE COUNT THAT NOTHING ASSERTS WILL DECAY AGAIN. The
  armed-module numbers are now tied to `len(_SITES)` by an arm whose templates
  are stored UNFORMATTED, so it cannot satisfy itself with its own literals, and
  which fails both ways - the expected number word must be present and no other
  number word variant of the same sentence may be.

- **CLOSED 2026-09-11 AT `7786955`, `5d785f5`, `86491a3` AND `78cdf96` - FOUR
  COMMITS, ALL PUSHED, AND THREE OF THEM REPAIR SOMETHING THIS TREE ALREADY
  BELIEVED WAS SAFE.** The detail is in `docs/LEDGER.md` under this session's
  heading. What belongs here is what FLIPS and what it LEAVES OPEN.

  THE SUITE WAS WRITING THE OPERATOR'S LIVE DAY LOG. Measured 2026-09-11 with an
  in-process tracer over `builtins.open`, `io.open`, `os.replace` and
  `os.rename`: 17492 bytes from 51 nodeids across 12 files, all of it synthetic
  error records from the degradation arms. Fixed at the ROOT - `load_config` in
  `core/config.py` already derived its log directory from `RC_LOG_DIR` and
  nothing had ever set it, so one assignment at rootdir `conftest.py` import time
  isolates both suites. `core/log_setup.py` is UNCHANGED and an operator-supplied
  `RC_LOG_DIR` is honoured. An adversary DISCARDED the tracer and measured
  differently, in a clone whose REPO_ROOT is `__file__`-derived: 19575 bytes
  under a HEAD-conftest control, 0 with the fix. Guard
  `tests/test_suite_writes_no_live_logs.py`. TWO CORRECTIONS TRAVEL WITH IT - LW
  reporting our three figures is AGREEMENT BY LUCK, since its tracer patched only
  `builtins.open` and missed `Path.write_text`, and the shared premise was that
  `logging.FileHandler` never touches `pathlib`; and of the 1922-byte
  tracer-to-disk gap, 89 bytes are CRLF translation measured as a rate with a
  control while the remaining 1833 are UNAPPORTIONED, with child processes named
  as a candidate rather than as an attribution.

  THE PUBLISH GATE LEAKED A TOKEN CLASS, AND THREE OF FOUR RULES WERE REFUTED BY
  MEASUREMENT BEFORE THE FOURTH LANDED. Rule 1 at HEAD leaked Slack `xoxa-`,
  `xoxr-` and `xoxs-` through the real publish path. Rule 2 closed those three
  and OPENED 30 segmented shapes including `xoxb-`, which had never leaked. Rule
  3 gave up EVERY credential preceded by a word character - a regression against
  HEAD's own publisher. Rule 4 derives the boundary from a CENSUS of the false
  positives: all nine are preceded by a LETTER and the break set by underscore or
  digit, so a letters-only lookbehind separates them exactly. Measured 2026-09-11
  over 221 scanned files of 223 tracked - 9 hits without it, 0 with it, break set
  still caught - and the cost is pinned by walking all 128 ASCII codepoints and
  asserting the missed set is exactly the letters. A RIGHT boundary was REJECTED
  BY MEASUREMENT: adding one lost two of three detections. Guards
  `tests/test_no_secret_literals.py` and `tests/test_publish_next_session.py`
  over `tools/publish_next_session.py`.

  FIVE MODULES THAT SHELLED GIT WITH NO GATE NOW SKIP, and the grader was rebuilt
  twice before it could grade: the site table's conservation went from ROWS to
  NODES after a one-edit mutant left it green, then its matcher was replaced by
  the census resolver in `tools/git_subprocess_census.py` after a Name-bound argv
  and then a splatted argv each defeated it, then the exempt-arm audit was rebuilt
  because a decorator launch is UNATTRIBUTABLE BY CONSTRUCTION. Guards
  `tests/test_conftest_git_gate_sites.py`, `tests/test_commit_trailers.py` and
  `tests/test_precommit_gate_corpus.py`.

  A PUSH FROM A LINKED WORKTREE RAN BOTH SUITES AGAINST A SUBSTITUTED CORPUS, and
  the scrub that fixed it was then refuted in turn. `git rev-parse
  --local-env-vars` is git's OWN authoritative list and returns FIFTEEN names; the
  first scrub covered five, and `GIT_CONFIG_PARAMETERS` is exported to hooks BY
  GIT ITSELF. THE SELECTION CRITERION WAS THE DEFECT: the nine were chosen by
  keeping only variables that changed the answer AT rc 0, but for
  `git check-ignore -q` THE RETURNCODE IS THE ANSWER. The corrected criterion in
  `conftest.py` treats an answer as the PAIR of returncode and stdout, the tuple
  is now fourteen, and a runtime reconciliation arm against git's own list makes a
  future git version a red test rather than an incident. Guard
  `tests/test_git_env_scrub.py`.

  GATES AT THE FINAL SEAM, all READINGS taken 2026-09-11 at `78cdf96`, each run
  as its own command: licence 47; docs consistency 29; docs hook commands 21;
  `qa_companion` 18 passed 0 failed 1 skipped 3 noted; `ruff` exit 0; `tests`
  2625 passed 1 skipped; `agents/pity_engine` 80 passed; `node --test` in
  `shell/` 52 of 52; the headless dry run exit 0 with 6 skips; mypy Success over
  35 source files, ADVISORY because its roots exclude `tests/` and `conftest.py`,
  which is where most of this session's bytes landed.

- **OPEN 2026-09-11, AND IT IS A HOLE THE CENSUS CANNOT CONSERVE ITS WAY OUT
  OF.** `tools/git_subprocess_census.py` emits NO SITE AT ALL when `call.func` is
  itself a Call - `getattr(subprocess, "run")(...)` and
  `functools.partial(subprocess.run)(...)` are both invisible - and its launcher
  set is `subprocess`-only, so `os.system` is invisible for a second and
  independent reason. THE CONSERVATION ARM CANNOT HELP HERE, and that is the
  point worth keeping: conservation compares emitted rows against hand-counted
  launches, and a shape that emits nothing leaves nothing to conserve. The repair
  is a resolver that walks a Call in func position and a launcher set derived
  rather than enumerated.

- **OPEN 2026-09-11, AND THE ROW IS THAT THE EXEMPT-ARM AUDIT CHECKS NAME
  PRESENCE RATHER THAN REACHABILITY.** A gate placed AFTER the launch is now
  caught by statement order, which is the half that shipped. What is still
  uncaught is a gate under `if False:` and a gate inside an uncalled nested
  `def` - both read as GATED. Reachability is a different analysis from presence
  and should be scoped as one, not bolted onto the name walk.

- **OPEN 2026-09-11, AND IT IS THE MOST PLAUSIBLE LEAK SHAPE IN AN AGENT-WRITTEN
  HAND-OFF.** The no-operator PROSE binding - a secret name narrated next to its
  value with NO operator at all between them - is invisible to the name-binding
  detector by construction, because that detector's whole premise is a mandatory
  operator. Catching it needs a PROXIMITY-OR-ENTROPY rule, which is a different
  detector CLASS with its own false-positive budget, and it must be sized as such
  rather than bolted onto the existing regex.

- **OPEN 2026-09-11, AND IT IS A ROSTER QUESTION RATHER THAN A MATCHER
  QUESTION.** An off-roster secret NAME carrying a non-vendor-prefixed VALUE is
  invisible to BOTH detector paths in `tests/test_no_secret_literals.py` by
  construction: the prefix path needs the vendor prefix and the name path needs
  the name on the roster. No widening of either regex reaches it. The work is
  roster COMPLETENESS, and widening a matcher is the response this tree has been
  defeated by three times.

- **OPEN 2026-09-11, AND THE HONEST ANSWER IS THAT WE CANNOT DERIVE IT HERE.**
  Real vendor credential body LENGTHS are NOT derivable from this tree; three
  agents said so independently on 2026-09-11. The shared floor of 16 in the
  publish gate is THIS TREE'S GUARD FLOOR and is not a vendor specification. Do
  not let a later reader promote it into one - if a vendor length is ever needed,
  it has to come from the vendor's published documentation and be cited as such.

- **OPEN 2026-09-11, A RESIDUAL OF THE SCRUB AND DELIBERATELY NOT CLOSED.** The
  `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` carve-out is KEPT, but the ground
  it was first justified on was wrong: an inherited value pointing at a config
  carrying `core.excludesFile` was MEASURED on 2026-09-11 to change a corpus AT
  rc 0. So these two are not inert, they are merely judged worth inheriting. The
  residual is recorded rather than closed, and it is the FIFTH item in the
  operator row below.

- **OPEN 2026-09-11, AND IT IS ABOUT THE INSTRUMENT RATHER THAN ABOUT ANY
  FINDING IT PRODUCED.** Neither write tracer used this session sees
  `os.open` plus `os.fdopen` - the descriptor is an int, so no path ever matches -
  and that shape is LIVE in `ops/loop/slots.py`, which writes the machine-wide
  bucket the halt ruling names by name. Neither tracer patches DELETION or
  TRUNCATION at all, and this tree calls `shutil.rmtree` at session finish and
  `unlink` in nine files, measured 2026-09-11. So every "0 bytes written" reading
  taken with either tracer is a statement about the shapes it patched.

- **OPEN 2026-09-11, INBOX, BUCKET APPLICABLE-AND-NOT-DONE, two items.** The
  fifth LW note saying the plugin has already been sent is SUPERSEDED and needs a
  reply saying so, because silence reads as dissent. And a counterparty probe file
  in the inbox - named in prose, since the whole inbox directory is gitignored and
  a backticked pointer there would be a pointer at an untracked path - writes into
  the runtime directory and passes `-q`, which doubles this tree's `pytest.ini`
  `-q` into `-qq` and deletes the summary line. It therefore does NOT run here
  unmodified, and adopting it means adapting it.

- **OPEN 2026-09-11, AND IT IS RECORDED AS UNEXPLAINED RATHER THAN AS FLAKY.** A
  second failure was seen ONCE in `tests/test_moon_sync_responder.py` under a
  planted mutant and did not reproduce. The "collateral damage" explanation
  offered for it was REFUTED by reading. A non-reproduction is not an
  explanation, so the row stays open with no cause attached to it.

- **NEEDS THE OPERATOR 2026-09-11, FIVE ITEMS, NON-BLOCKING, AND NOTHING BELOW IS
  ANSWERED HERE.** The four carried questions all STAY OPEN and none of them was
  touched by this session's work: the exit code owed to an interpreter that NEVER
  STARTED; the three-record disposition asymmetry; arming the three standby
  parties under the UNRULED no-answer rule; and the pre-first-fire action signal,
  whose DEFECT claim was refuted and which survives only as an ENHANCEMENT
  blocked on the first question. A FIFTH arose on 2026-09-11 and is the config
  carve-out row above - `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` are kept in
  the inherited set, but an inherited value pointing at a config with
  `core.excludesFile` was measured to change a corpus at rc 0, so the carve-out
  is a judgement rather than an inertness finding.

- **CLOSED 2026-09-11 at `390a831` AND `1c8aab2` - FIVE ROWS FLIP, AND ONE OF THEM
  FLIPS WITH ITS PREMISE CORRECTED.** Each slice ran on a disjoint write-list and
  was graded by an agent that did not write it. Every figure here was observed at
  the merged seam rather than carried forward from a slice report.

  THE GIT-CALL POPULATION IS NOW COUNTED RATHER THAN FILTERED.
  `tools/git_subprocess_census.py` walks every subprocess launch site across
  `tests/`, `tools/`, `ops/`, `headless/` and `scripts/` and reports THREE buckets:
  GIT 37, NOT-GIT 20, UNRESOLVED 16, total 73 sites over 104 modules, 26 files
  holding at least one GIT site. The UNRESOLVED bucket is the honest part - an
  argv[0] no static reading can answer is not a NOT-GIT. Both figures this tree
  previously quoted are REFUTED AS COUNTS, the 8-arms-over-7-modules reading and
  the 5-module candidate list alike, because both came from name-based one-term
  filters. The row's own prediction is CONFIRMED AS AN ASSERTED POSITIVE:
  `tests/test_ci_history_depth.py` and `tests/test_guard_worktree_blindness.py` are
  both WALKED and both produce zero launch sites in any bucket, so a skip on either
  would have been a false skip with no defect behind it.

  THE SKIP-then-RUN SITE ARM LANDED, AND IT REFUTED ITS OWN BRIEF.
  `tests/test_conftest_git_gate_sites.py` runs a module with git unreachable and
  asserts it SKIPS, then runs it with git present and asserts it RUNS ITS
  ASSERTIONS. THE THREE SITES THE EARLIER ROW NAMED AS CANDIDATES CARRY NO GATE AT
  ALL - `tests/test_no_sibling_names.py`, `tests/test_ci_workflow_complement.py`
  and `tests/test_responder_gate_census.py` each shell git with no gate, and under
  an unreachable git they FAIL rather than skip, measured. Arming them as briefed
  would have shipped a permanently red test, so the arm covers the two sites that
  gate AT the site - `tests/test_shell_contract.py` for the import-time
  whole-module shape and `tests/test_ports.py` for the run-time per-test shape.
  The absence mechanism is an emptied PATH, and why that defeats BOTH Windows
  lookups is recorded in the module: `shutil.which` is PATHEXT-aware while
  `subprocess.run` reaches CreateProcess, which searches the launcher directory,
  the cwd, the system directories and then PATH. The present-but-broken-git
  question is STILL PINNED OPEN and nothing here closes it.

  TWO DEGRADE-TO-EMPTY GUARDS FAIL CLOSED. `scan_file` in
  `tests/test_task_state_claims.py` swallowed OSError and reported ZERO FINDINGS on
  an unreadable tracked file; it now raises with a reason naming the path and the
  raw errno, cause chained. Its sibling `_tokens` in
  `tests/test_docs_hook_commands.py` answered an empty list on a shlex ValueError,
  and every caller asks whether the token list CONTAINS something, so zero tokens
  made every question answer no; it now raises, caught at the one call site that
  must keep sweeping, where the unparseable span is REPORTED rather than skipped.

  THE PROVENANCE DIGEST IS RECOMPUTED. `core/provenance.py` declared `sha256` and
  `parent_sha256` with no hashlib, so a format regex was the only validation.
  RECOMPUTE-AND-COMPARE was chosen over renaming the field advisory, and the reason
  is a fact rather than a preference: the locator rules already enforce a safe
  total join, so the artefact is reachable by construction. An absent artefact is
  its OWN verdict, and unverifiable digests are kept out of the denominator so zero
  out of zero cannot read as a pass.

- **THE CLASS THAT MATTERS MOST FROM 2026-09-11, AND IT IS ABOUT OUR OWN ARMS.
  FOUR OF THE FIVE ARMS THAT LANDED AT `390a831` COULD NOT FAIL, AND A MUTATION
  PASS FOUND EACH ONE BEFORE CI DID. REPAIRED AT `1c8aab2`.** Every one was green
  against a mutant that broke the exact property the arm was written to defend, so
  every one had pinned a SHAPE rather than an INPUT.

  The provenance decoy generator advanced CHARACTER INDEX 0 ONLY, and every
  wrong-digest arm derived from it, so an implementation comparing one character of
  sixty-four passed all 71 arms while grading a digest differing at its last
  character as MATCH. The repair is a decoy FAMILY - index 0, index 63, a middle
  index, an adjacent transposition that moves only the order - plus a structural arm
  that no prefix or suffix shortcut survives for any k in 1..63.

  The unparseable-span `in_scope` widening was load-bearing and pinned by nothing:
  reverting it left the module and the whole suite green, because both fixtures
  spelled a long flag and the reason term was never why any arm passed.

  The site table could be emptied and the gate stayed green, because AN EMPTY
  PARAMETRIZE IS ONE SKIPPED AND EXIT 0 - the module's own docstring named that trap
  and then nothing asserted a floor.

  The census DROPPED launch sites in decorators, default arguments, annotations and
  class bases, which is worse than misbucketing because a missing row is invisible;
  and its unresolved fallback could be flipped to NOT-GIT with all 33 arms passing,
  which would have silently reclassified the most ordinary dynamic git argv[0] in
  Python. The walk now derives its non-body positions BY SUBTRACTION from the child
  nodes rather than from an enumerated list, so a grammar position nobody named is
  still walked, and a CONSERVATION arm asserts the three buckets sum to the
  hand-counted launches in a fixture.

  THE CENSUS COUNTS DID NOT MOVE, and that was MEASURED rather than assumed, by
  running the pre-repair and post-repair modules back to back against this tree and
  diffing the full reports. So those four census defects are real and unpinned but
  UNEXERCISED BY CURRENT REPO BYTES.

  THE DURABLE RULE, and it is cheap to lose: ASK WHAT INPUT AN ARM FEEDS, NEVER
  WHETHER THE ARM EXISTS - and when the arm is new, mutate the implementation it
  defends before believing it.

- **SWEPT 2026-09-11 AND THE ANSWER IS A LATENT CLASS, NOT A DEFECT. LW'S
  BACKSLASH FINDING IS MEASURED HERE AT LAST, AND THE REPAIR IS DELIBERATELY NOT
  MADE.** PowerShell 5.1 native-command marshalling on this host corrupts any
  argument containing a SPACE and ending in BACKSLASHES: an odd trailing count
  INJECTS a quote, and an even count silently HALVES the backslashes. The table was
  measured twice by two agents, the second building its probe from the installers'
  own bytes and passing the hostile strings through a JSON file so they never
  crossed a shell - and a 13-of-13 clean control through the list form proves the
  mangling is PowerShell's and not the probe's.

  PER CARRIER. `ops/ResinCompute-Responder.xml` and
  `ops/ResinCompute-Supervisor.xml` are ABSENT BY MECHANISM rather than by
  inspection: the first substitutes only two DateTime placeholders whose value space
  is digits, hyphen, colon and T, and the second's arguments are a literal constant.
  Both installers hold the LATENT shape - each passes an unvalidated task-name
  string to one native command - but `git grep` finds ZERO callers passing a task
  name to either installer, both defaults are space-free and backslash-free, and the
  only route to the native call requires a real registration, which is an arming act
  and forbidden. `ops/check_task_liveness.py` accepts a trailing backslash through
  `_TASK_NAME_RE` and rejects an injected quote, so the odd case fails closed at
  exit 3 while the even case reaches exit 2.

  WHY NO REPAIR. Reachability is nil, and this tree has already adjudicated a
  do-not-widen ruling on a class whose reachability measured zero of eight. A
  hardening with no reachable defect behind it is ceremony that then has to be kept
  accurate. IF A CALLER EVER PASSES A NON-DEFAULT TASK NAME, THIS ROW BECOMES LIVE
  AND THE VALIDATION GOES IN THEN.

- **CLOSED 2026-09-11 at `7786955`, AND THE POPULATION WAS FIVE RATHER THAN THE
  THREE THIS ROW NAMED.** All five now SKIP under an unreachable git instead of
  failing, each armed by a skip-then-RUN pair in
  `tests/test_conftest_git_gate_sites.py` where the RUN half is the load-bearing
  one. The three named below were gated, and `tests/test_commit_trailers.py` and
  `tests/test_precommit_gate_corpus.py` were gated with them. One further module
  was ruled EXEMPT by an adjudicator working from criteria written before either
  candidate was read: the rule's population is SITES THAT SHELL GIT, and that
  module's failing arm shells nothing - it CONSUMES the gate helper in order to
  AUDIT it. The ruling STANDS, and its citation was RE-DERIVED rather than carried
  forward, because the census guard column is a MODULE-LEVEL walk that would have
  answered GATED with every gate in the file deleted. The original row text
  follows unaltered.

  `tests/test_no_sibling_names.py`, `tests/test_ci_workflow_complement.py`
  and `tests/test_responder_gate_census.py` shell git and carry no gate at the site,
  so on a host without a reachable git they FAIL rather than skip - measured, not
  inferred, with the failing counts observed per module. Gating them is a separate
  slice because it touches files the arm slice did not own, and the arm that would
  grade the repair already exists in `tests/test_conftest_git_gate_sites.py`, which
  carries a pointer saying to add them to its site table once they are gated. DO NOT
  ARM THEM IN THAT TABLE FIRST - that ships a permanently red test.

- **OPEN 2026-09-11, SMALL, A RESIDUAL OF THE FAIL-CLOSED REPAIR AND NAMED SO IT IS
  NOT MISTAKEN FOR CLEANLINESS.** `scan_tree` in
  `tests/test_task_state_claims.py` skips a path whose `is_file()` is False, and
  `Path.is_file()` SWALLOWS OSError INTERNALLY and answers False. So a real file
  whose PARENT directory denies traversal is still dropped from the sweep as absent,
  and the fail-closed repair covers open failures rather than stat failures. The
  current arm PINS that skip as intended behaviour, so changing it is a deliberate
  decision and not a bug fix - hard-failing there would break a partial checkout.

- **RETIRED 2026-09-11 - THIS ROW'S PREMISE IS FALSE, AND THE REAL DEFECT WAS
  SHARED RATHER THAN ASYMMETRIC. FIXED AT `5d785f5`.** The claim below - that
  `ops/install_responder_task.ps1` carries no unsubstituted-placeholder throw -
  IS FALSE. That script has carried the guard since `1d80f8c` on 2026-09-07, four
  days BEFORE this row was filed, and it fires. What was real is SHARED and
  SYMMETRIC: PowerShell `-match` is case-INSENSITIVE, so the old character class
  behaved as case-insensitive at runtime and lowercase never leaked. Only the
  DIGIT axis leaked, and it leaked REGARDLESS OF CASE - measured 2026-09-11
  against both scripts, a planted `__Slot1__` and a planted `__SLOT1__` both
  returned 0 while `__pythonw_exe__` and `__PyThonW__` both returned 1. Second,
  and responder-only: the UTF-16 declaration relabel ran BEFORE the guard, so a
  token sitting inside the declaration was MASKED from it, fixed by reordering to
  substitute, then guard, then relabel. Guards
  `tests/test_responder_task_argv.py` and `tests/test_supervisor_task_argv.py`.
  The false text follows, kept so the next reader sees what was refuted.

  `ops/install_scheduled_task.ps1` throws on an unsubstituted placeholder left in
  the task XML; `ops/install_responder_task.ps1` performs the same substitution
  family and carries NO such throw. Found while refuting a different claim, so it is
  recorded rather than fixed, and it is the kind of gap that only shows up when a
  template gains a placeholder nobody wired.

- **NEEDS THE OPERATOR 2026-09-11, NON-BLOCKING, AND IT IS THE NARROW CLAIM THAT
  SURVIVED A REFUTATION.** `ops/check_task_liveness.py` never reads a registered
  task's ACTION back - its probe collects nine fields and none of them is the
  command, the arguments or the working directory. THE CLAIM THAT THIS IS A DEFECT
  WAS REFUTED: the tool's contract is FIRING and not SUCCEEDING, in its own words
  the State string is reported but is never the verdict, and the harm path is
  guarded by the installers' own Test-Path throws plus the tracked-XML arms in
  `tests/test_responder_task_argv.py` and `tests/test_supervisor_task_argv.py`.
  WHAT SURVIVES IS NARROWER: between registration and first fire there is no action
  signal at all, because `LastTaskResult` only exists after a run. That is an
  ENHANCEMENT REQUEST against an out-of-contract question, and its repair is BLOCKED
  ON THE OPEN EXIT-CODE CALL below, because any new verdict on that surface is a
  compatibility change to the five codes that have callers.

- **NOW DONE AT THE THREE SITES TOO, 2026-09-11 at `7786955` - the row below was
  DONE at `390a831` and HARDENED at `1c8aab2` everywhere EXCEPT the three sites it
  named, and those three plus two more are now gated and armed. The site table's
  conservation went from ROWS to NODES, and its matcher was replaced by the census
  resolver in `tools/git_subprocess_census.py` after a Name-bound argv and then a
  splatted argv each defeated the hand-written one. Nothing below is repealed; the
  RUN half is still the load-bearing half.** `tests/test_conftest_git_gate.py`
  grades the HELPERS - `classify_git_probe`, `require_git_repository`,
  `skip_module_without_git` - and it grades them well. What no arm does is take a
  module that shells git, run it with git ABSENT, and assert the module SKIPS, then
  run it with git PRESENT and assert the same module RUNS ITS ASSERTIONS rather
  than skipping. That SKIP-then-RUN pair at the SITE is the arm that would catch a
  repair which skips unconditionally, and a helper-level arm structurally cannot
  see it. Candidate sites are the three that actually shell git:
  `tests/test_no_sibling_names.py`, `tests/test_ci_workflow_complement.py` and
  `tests/test_responder_gate_census.py`. THE RUN HALF IS THE LOAD-BEARING HALF - a
  skip-only arm is satisfied by a guard that never lets anything run.

- **SWEPT 2026-09-11, AND THE VERDICT IS A LATENT CLASS WITH REACHABILITY NIL -
  THE MEASURED TABLE AND THE PER-CARRIER VERDICTS ARE IN THE TOP BLOCK.** LW reported a
  backslash-handling finding on the schtasks and PowerShell argument path, where a
  Windows path separator inside a quoted argument can be consumed before the task
  ever sees it, so an argv element reaches the registered task mangled. NO SWEEP
  HAS BEEN RUN AGAINST THIS TREE FOR IT. The candidate carriers here are
  `ops/install_responder_task.ps1`, `ops/install_scheduled_task.ps1`,
  `ops/ResinCompute-Responder.xml` and `ops/ResinCompute-Supervisor.xml`, and the
  reader half is `ops/check_task_liveness.py`. Record the verdict as UNSWEPT until
  somebody runs it: a class reported by another carrier and never looked for here
  is an open question, not a negative result. This tree's own measured trap is
  adjacent and explains why a shell probe is the wrong instrument - under Git Bash
  MSYS path conversion rewrites a lone `/F` into a drive path, which is the same
  root cause in the opposite tool.

- **DONE 2026-09-11 at `390a831` - THE POPULATION IS NOW COUNTED AND THE TOOL IS
  TRACKED. THE COUNTS ARE IN THE TOP BLOCK AND THEY SUPERSEDE EVERY FIGURE IN
  THIS ROW.**
  Both false-red figures this tree has quoted - the 8 red arms over 7 modules, and
  the 5-module candidate list - came from NAME-BASED ONE-TERM FILTERS, and the
  second was already measured to over-report by roughly a factor of two thirds. An
  AST ENUMERATION OF EVERY subprocess CALL WHOSE argv[0] IS git, across `tests/`,
  `tools/`, `ops/`, `headless/` and `scripts/`, HAS NEVER BEEN RUN. Until it is,
  three is a FLOOR and not a count, and any future "N to 0" claim here inherits
  exactly the defect found in LW's own 43: a denominator produced by a filter
  nobody validated. THE ROW IS THE ENUMERATION, not the repair - run it first,
  publish the list, and only then size the work.

- **NEEDS THE OPERATOR 2026-09-14, NON-BLOCKING, one question.** Does an
  interpreter that NEVER STARTED deserve its own CLI exit code from
  `ops/check_task_liveness.py`? Today it lands on 3 UNKNOWN alongside every other
  genuinely-unknown outcome, and the shipped branch fixed only the REASON STRING,
  not the code. The argument for a distinct code is that a host-start failure is a
  fact about THIS MACHINE RIGHT NOW and is retryable, while UNKNOWN is a fact about
  the scheduler's answer and is not. The argument against is that 0 LIVE, 1
  DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS HAS CALLERS, so a sixth code is a
  compatibility change to every one of them. NOT DECIDED HERE, deliberately. This
  is the same distinction the intermittent pre-push row needs, so a ruling here
  constrains that repair.

- **OPEN 2026-09-14, AND IT IS THE WORSE-SHAPED OF THE TWO BECAUSE IT MAKES A
  PUSH-BLOCKING VERDICT NON-REPEATABLE.** Two arms in
  `tests/test_task_liveness.py` -
  test_the_real_probe_reports_the_end_boundary_value_and_not_just_the_key and the
  `_real_task_names` arm - COLLAPSE TWO DIFFERENT FACTS INTO ONE: "the census
  machinery is broken" and "powershell could not start on this machine just now".
  There is no retry and no distinct class for a HOST-START FAILURE, so a
  push-blocking verdict becomes a function of FREE MEMORY ON THE BOX.

  THE MECHANISM, measured. PowerShell's ConsoleHost returned 4294901760, which is
  0xFFFF0000, its ExitCodeInitFailure, with EMPTY stdout and a UTF-16LE stderr
  reading "Loading managed Windows PowerShell failed with error 8009001d". The CLR
  never loaded and the script never ran, which is why the arm saw status FAILED
  with an EMPTY values list. `collect_facts` and `ProbeError` in
  `ops/check_task_liveness.py` are the probe side of it, and
  `DEFAULT_TIMEOUT_SECONDS` is NOT implicated - nothing timed out.

  THE TRIGGER, established by CORRELATION PLUS INDEPENDENT EVIDENCE rather than by
  replay. The Windows Resource-Exhaustion-Detector logged low-virtual-memory
  events at 23:28:33 and at 23:34:36 naming a python.exe holding about 10.4 GB,
  and the refused hook run took 474.67s, so it SPANS BOTH EVENTS. A later run of
  the SAME commit through a REAL pre-push hook into a scratch bare repository gave
  2150 passed, 2 skipped in 97.77s, exit 0 - a PROBE READING at one commit on one
  machine, not a live baseline. So the ORCHESTRATOR'S OWN HYPOTHESIS, that the
  hook's environment was to blame, is REFUTED BY COUNTER-EXAMPLE, and the 4.9x
  time difference is the LOAD SIGNATURE.

  WHAT THE ARMS GET RIGHT, and nobody is to soften them. They were deliberately
  built so that FAILED MUST FAIL and only NONE may skip, to kill a vacuous skip.
  That intent is CORRECT. The defect is the MISSING DISTINCTION, not the
  strictness. SOFTENING AN ARM WHOSE INTENT IS RIGHT is the response this tree has
  been defeated by three times, so the repair is a DISTINCT CLASS for a host-start
  failure, never a relaxed assertion.

  THE CONSEQUENCE TO RECORD. A green pre-push on this machine is NOT REPEATABLE
  EVIDENCE, and the next docs-only push may be refused for the same reason. The
  refused run read 2 failed, 2148 passed, 2 skipped - again a PROBE READING at one
  commit on one machine, and the COLLECTED TOTAL WAS 2152 IN EVERY RUN, so nothing
  was silently dropped. Two pushes earlier the same evening passed because the
  machine had memory then. The latency is NOT NEW - it has existed since the
  real-probe arms landed - and nothing in this session's commits caused it: the
  refused commit was ROADMAP.md only, plus 299 insertions and zero deletions,
  which cannot make a scheduler probe fail.

  ADJACENT AND DELIBERATELY NOT MERGED INTO IT. The older row that already names
  `_real_task_names` is about a VACUOUS SKIP across `tests/`, ranked by an AST
  sweep; this row is about a NON-REPEATABLE PUSH-BLOCKING VERDICT and names its
  mechanism. Find that one by its SAME ROOT CAUSE IN SEVEN MORE PLACES heading,
  and do not cite it by line number.

- **THE INSTANCE IS DONE 2026-09-14 AT `0d1fa70`, proven by
  `tests/test_task_liveness.py`. THE CLASS QUESTION STAYS OPEN, small.** This row
  was filed as the class and not as the instance, and that split is why only half
  of it flips. `collect_facts` in
  `ops/check_task_liveness.py` mapped EVERY non-zero return code to ONE reason:
  that the scheduler refused the query and may need a different account or a
  different TaskPath. For the ConsoleHost init-failure class that headline is
  FALSE - nothing refused anything, and neither an account nor a TaskPath is
  involved. The truth sat only in the DETAIL string.

  THE BRANCH LANDED. Two module-level named constants now carry 0xFFFF0000 and
  its sibling 0xFFFE0000, which is ExitCodeCtrlBreak; the new branch PRECEDES the
  generic one and its detail string is byte-identical, so the diagnostic content
  survived and only the false headline changed. Two arms went red before the fix
  with both codes spelled as literals, and two controls held. UNVERIFIED AND
  RECORDED AS SUCH: whether this tool can reach 0xFFFE0000 at all. THE CLASS is
  the durable finding: a probe that collapses every failure mode into one
  OPERATOR-FACING reason sends a reader hunting a cause that does not exist. WHAT
  REMAINS OPEN IS THE QUESTION AND NOT THE INSTANCE - whether any other non-zero
  code from this probe also deserves its own class. That is UNMEASURED.

  THE REPRODUCTION, recorded because it is what makes the class checkable.
  Invoking powershell.exe with a BAD SystemRoot returns 0xFFFF0000
  DETERMINISTICALLY. A control set returned 0 in every case: no PATH, no APPDATA,
  no USERPROFILE, no COMSPEC, no windir, and TEMP pointing at a nonexistent
  directory. A parse error, a command-not-found and a `throw` all returned 1.

  A TRANSFERABLE TRAP, recorded here because it is cheap to lose. UNDER GIT BASH
  `$?` IS 8-BIT, so an exit of 4294901760 reads as 0 in a shell - only Python's
  returncode carries the full 32 bits, so THIS EXIT CODE CANNOT BE CHASED THROUGH
  A SHELL AT ALL. Measured the same evening and the same family: a COMPOUND
  command's exit code is its LAST element, so a trailing echo reported 0 and made
  a REFUSED PUSH LOOK SUCCESSFUL. Redirect each command to its own file.

- **AN ADJUDICATED CALL, 2026-09-13 - AN UNREADABLE STAGED DIFF IS A CORPUS
  FAILURE AND THE GATE FAILS CLOSED ON IT. VERDICT CLOSED, 4 OF 4 CRITERIA.**
  NOT AN OPERATOR DECISION. Overturnable by reading this entry. Find it by this
  heading; do not cite it by line number. ELEVEN ADJUDICATED CALLS STOOD BEFORE
  THIS ONE, SO IT IS THE TWELFTH.

  THE QUESTION. When `tools/precommit_gate.py` cannot read the staged diff, does
  `_check_staged` fail CLOSED - return 1 and block the commit - or FAIL OPEN
  LOUD, saying so on stderr and returning 0? RULING: CLOSED, on all four stated
  criteria - fidelity to the module's own rule, cost of being wrong, testability,
  and sibling consistency.

  WHY CLOSED WON. The module's FAIL-OPEN RULE enumerates its own class inside its
  parenthesis, and both members are TOOL PROVISIONING: ruff missing, message file
  unreadable. The staged diff is not a tool the gate needs, it is the staged
  half's CORPUS. The module already carves the corpus class out twice -
  `_check_scan_files` and `_tracked_split` - and the second says it in words:
  callers must fail CLOSED on that, never report a clean sweep they did not
  perform. WHY OPEN-LOUD LOST: a wrongly-closed gate costs one `--no-verify`
  before anything lands, while a wrongly-open one puts the defect IN HISTORY, and
  a force-push does not purge objects.

  THE SECONDARY RULING, and it is the half that actually ran. The
  `rev-parse --show-toplevel` call site KEEPS its permissive fall-through to
  os.getcwd(); only its `.strip()` had to become `(_git(...) or "").strip()`, or
  the new return type raises AttributeError. Because the hook pipes the bare
  string `git commit` with no `-C`, that fall-through is the LIVE path on every
  developer commit, so the fix ran on its own commit. Landed at `72c7041`.

  **DONE 2026-09-14, proven by `tests/test_precommit_gate_corpus.py`** - five
  arms, three of them red before the fix by AssertionError against a REAL git exit
  129 rather than a mocked one, and two controls green on both sides, one of which
  is the clean-repo-nothing-staged case the defect was BYTE-IDENTICAL to. Plus the
  end-to-end check, which is the only valid test of a hook gate: a banned glyph
  staged by explicit path, a real commit attempted, exit 1 naming file and glyph,
  HEAD unchanged. RECORDED BECAUSE THE ADJUDICATOR DISCARDED ONE OF THE WINNER'S
  OWN ARGUMENTS: CLOSED had also argued "the commit is about to fail anyway", and
  that is FALSE - a stale `git -C` path left by a worktree agent yields an
  unreadable corpus while the real commit succeeds.

  THE ADJUDICATOR'S OWN STATED COMMON-MODE RISK, recorded because agreement is
  not evidence: both candidates argued from the SAME inherited docstring without
  checking it against the RC upstream it claims to be inherited verbatim from. If
  RC has amended that paragraph, both were arguing from a stale quote.

- **OPEN 2026-09-13, A REAL DEFECT WITH A MEASURED UNBOUNDED CONSEQUENCE, AND IT
  SHARPENS THE THREE-RECORD ASYMMETRY ROW BELOW RATHER THAN DUPLICATING IT.**
  `answered_usable` in `tools/moon_sync_responder.py` has a MISSING THIRD CLASS:
  readable-but-permanently-unwritable. It probes exists, is_file, parent and
  read_bytes, NEVER attempts or infers a WRITE, and then returns the string "the
  answered record is readable and writable". The seed is three lines - write
  valid JSON, then os.chmod(path, stat.S_IREAD).

  MEASURED with the real `run_once`, three cycles, no logic monkeypatched,
  against two controls seeded the same way:
  - structural-dir: far-inbox deliveries 0, terminations answered-unusable x3.
  - replaceable-corrupt: far-inbox deliveries 1, terminations delivered, empty,
    empty.
  - readonly-attribute: far-inbox deliveries 3, terminations delivered x3, and
    the record still holds only the OLD name.

  That is ONE DELIVERY PER CYCLE FOREVER into a repo this one does not own. At a
  five-minute tick it is 288 minute-stamped files a day - verbatim the shape the
  structural branch exists to prevent.

  NOT LIVE. The scheduled task is DORMANT, verified this session by
  `python ops/check_task_liveness.py ResinCompute-Responder` exiting 1, trigger
  expired 2026-09-07T21:00.

  FAIR TO THE SHIPPED FIX: this class ALSO looped before `6c351b3`, silently. So
  the VISIBILITY half of that work survives and only its fail-closed half does
  not. `refusals_usable` carries the IDENTICAL hole - the new function was
  specified to mirror it and mirrored the defect too - so any fix must touch
  BOTH, and the rotation gate should be checked on the same class.

- **OPEN 2026-09-13. A TEST DOCSTRING SAID NO ARM COULD BE WRITTEN, AND THAT
  MISLABEL IS WHAT STOPPED THE ROW ABOVE FROM BEING FOUND.** The docstring of
  test_a_failed_answered_write_is_reported_rather_than_discarded in
  `tests/test_responder_degraded_write.py` is FALSE as written: it says every real
  structural route is stopped by the reader gate one level up and that what
  remains is a race no arm can schedule. The read-only class above is STABLE AND
  DETERMINISTIC, not a race, and an arm could have been written against real
  bytes. The arm itself survives as a CALL-SITE WIRING PIN - it pins that
  `_run_once` reads the return value - but a mutant that hardcodes a true return
  inside `answered_usable` leaves it GREEN, because that mutant replaces the
  function whose classification is the thing at risk. CORRECT THE DOCSTRING
  CLAIM; DO NOT DELETE THE ARM.

- **OPEN 2026-09-13, small, three items in one row. A BRANCH WITH NO INPUT, PLUS
  AN UNDOCUMENTED SILENT DROP.** In `answered_usable` the
  `except (OSError, ValueError)` arm CANNOT FIRE FROM ITS OWN PROBES: all four
  guarded calls route through os.path.exists or os.path.isfile, which swallow
  both internally. Its reason string is therefore a branch with no input - the
  same cannot-fail shape this tree already records elsewhere. PROOF IT DOES NOT
  FIRE: a path containing a NUL makes `_remember_answered` RAISE ValueError from
  the WRITER rather than return False. Third item, undocumented today: non-str
  members of the answered list are SILENTLY DROPPED on rewrite by the isinstance
  filter. Distinct from the `_ensure_parent` naming row further down, which is
  about the same function and a different defect.

- **DONE 2026-09-11 at `390a831` - THE FIFTH SITE AND THE SIXTH SIBLING NAMED
  BELOW BOTH FAIL CLOSED NOW, WITH ONE RESIDUAL RECORDED IN THE TOP BLOCK.** Same
  root cause as the six fixed at `b3ff9fe` and `6c351b3`. `scan_file` in
  `tests/test_task_state_claims.py` does `except OSError: return []`, so an
  unreadable tracked file is reported as ZERO FINDINGS, and `scan_tree` only
  extends - the sweep reports clean over a file it could not open.
  LOWER-SEVERITY SIBLING OF THE SAME SHAPE: `_tokens` in
  `tests/test_docs_hook_commands.py` returns an empty list on a shlex ValueError,
  so an unparseable hook command asserts VACUOUSLY. NOTE THE SWEEP'S OWN REACH:
  it covered 136 of 219 tracked paths, the .py half only, so the negative outside
  .py is ZERO COVERAGE and not cleanliness.

- **FLAGGED FOR THE OPERATOR 2026-09-13, AND DELIBERATELY NOT A FIX.** `release`
  in `ops/loop/slots.py` does `_read`, which degrades to an empty dict, then
  update, then an IN-PLACE write-back. That is the aggravated splice form of the
  same root cause as the row above, and it DESTROYS the `repo` field that `reap`
  logs - so a neutralised orphan is reaped with its owner unnamed. NO CHANGE IS
  PROPOSED AND NONE SHOULD BE MADE WITHOUT THE OPERATOR: halt ruling clause (b)
  names that file, and `tests/test_loop_concurrency.py` pins it by sha256 as
  byte-identical across three carriers, so hardening it DESYNCHRONISES every
  carrier that has not moved. The same file's `is_stale` is explicitly GUARDED by
  a documented mtime fallback, so only `release` is implicated.

- **INBOX TRIAGE 2026-09-13 OF LW'S NOTE OF 2026-09-10 22:35 - FOUR-BUCKET
  VERDICTS RECORDED, AND ONE OF OUR OWN RETRACTIONS IS NOW DISPROVED RATHER THAN
  MERELY WITHDRAWN.** The note is
  `moon_sync_inbox/2026-09-10-2235-from-LW-positions-on-Q1-Q5-your-conftest-claim-refuted-on-a-second-tree-and-four-measured-findings.md`.

  ITS SECTION 0 refutes RSC's Q3 claim that a skip-path ruling was already latent
  in the conftest all five of us share. THE REFUTATION HOLDS, measured directly:
  LW's own tests/conftest.py is 56 lines with ZERO subprocess, which or Popen
  hits and LW has no root conftest. NO NEW CORRECTION IS OWED - we already
  retracted that claim in our own note of 2026-09-08 22:45. What LW adds is a
  SECOND CARRIER'S MEASUREMENT, which upgrades the claim from RETRACTED to
  DISPROVED. LW overstates exactly one line: "the only conftest in the tree" is
  false, since 10-plus exist under LW's generated virtualenv site-packages, none
  LW-authored. LW's CONCLUSION survives; that SENTENCE does not.

  OUR NARROW CLAIM STANDS AND LW DOES NOT CONTEST IT. The ruling IS in RSC's
  tests/conftest.py, whose classify_git_probe returns four distinct categories
  each carrying the literal "is SKIPPED rather than passed", while OUR root
  `conftest.py` has zero external-binary calls. LW's own probe template aimed at
  our root would therefore have reported nothing and been WRONG ABOUT THE TREE.

  BUCKETS. Section 5.2, SILENT IS NOT DEAD: ALREADY-HAVE-AN-EQUIVALENT.
  Section 5.3, the IGNORED-TRACKED TRAP: NOT-APPLICABLE - we ran LW's probe,
  `git ls-files` piped into `git check-ignore --no-index --stdin`, and got exit 1
  with ZERO lines. ONE LATENT OVER-FIRE LINE WORTH KEEPING: `.gitignore` carries
  unanchored build/, tmp/, logs/ and env/, so a future docs/build/ or
  engines/tmp/ would be hidden. No such directory exists today. All four LW
  digests reproduce BYTE-EXACT, and that proves TRANSPORT ONLY - we hashed LW's
  own bytes and we are the same carrier. We carry none of those four files.

- **DONE 2026-09-11 at `390a831`, RECOMPUTE-AND-COMPARE CHOSEN OVER ADVISORY, AND
  THE ARM THAT PROVED IT WAS ITSELF DEFECTIVE UNTIL `1c8aab2`.** `core/provenance.py` declares `sha256` and
  `parent_sha256`, writes both into the record, and contains NO hashlib at all -
  `grep -n hashlib core/provenance.py` returns nothing. The only validation is a
  FORMAT REGEX, which is exactly this tree's recorded trap that a shape arm pins
  FORMAT and not INPUT. The only importer is `tests/test_provenance.py` and the
  only `SourceRef` construction site is provenance's own deserializer, so the
  field is UNFED AND UNGATED BY CONSTRUCTION. ACTION BEFORE THE FIRST PRODUCTION
  WRITER LANDS: either recompute-and-compare, or rename the field to say it is
  ADVISORY.

- **OPEN 2026-09-13, from LW section 5.4, bucket APPLICABLE-AND-NOT-DONE, SECOND
  QUESTION ONLY. FILED AS A REVIEW QUESTION, NOT AS CODE.** LW's first question -
  is the selector the reporter - is ALREADY OURS and needs no new row. The second
  is not present anywhere in this tree: IS THE REPORTED AXIS ONE THE TREATMENT
  COULD HAVE LOST ON? An axis on which the treatment cannot lose reports nothing
  about the treatment. It aims squarely at the corpus work just landed in
  `tools/precommit_gate.py`.

- **NEEDS THE OPERATOR 2026-09-13, two items, NON-BLOCKING.** LW's Q2 - whether
  the gate tag literal is RC's `# GATE:` spelling - is now formally UNANSWERED BY
  THREE OF FIVE, because LW defers it to its own operator as a POLICY COMMITMENT
  rather than a measurement, and three participants are on ordered standby. LW's
  Q4 adds ONE WORD to a position we already hold: nobody copies a file
  unrequested AND UNDIGESTED, meaning a request NAMES the file and the reply
  CARRIES a digest. SILENCE IS NOT AGREEMENT, so an unanswered added word reads
  as DISSENT - we must answer it.

- **OPEN 2026-09-13, housekeeping on this session's own correction.** The
  unique-red-function count for the tag-deletion probe is UNRECONCILED at 24
  against 23. Two passes disagree by one, NEITHER ENUMERATED THE FUNCTION NAMES,
  so neither is checkable; it is recorded as unreconciled in `docs/LEDGER.md`. THE
  ROADMAP ROW IS TO ENUMERATE THE NAMES ONCE AND RETIRE THE QUESTION. NOTE THE
  PROBE IS NOT TOOLED: `tools/gate_mutation_runner.py` mutates gate STATEMENTS
  via `_edits_for` over ast.stmt and has NO CLI mode that drops a `# GATE:`
  COMMENT, and both guard modules need a WHOLE-TREE COPY because they resolve
  REPO_ROOT from `__file__.resolve().parents[1]` and the census shells
  `git ls-files` at cwd=REPO_ROOT.

- **OPEN 2026-09-13, BUCKET APPLICABLE-AND-NOT-DONE, AND IT IS MEASURED IN OUR
  OWN BYTES. A GUARD THAT SHELLS GIT WITH NO CAPABILITY CHECK TURNS A MISSING
  GIT INTO A FALSE RED.** From triaging LW's note of 2026-09-10 22:56, which
  sits at
  moon_sync_inbox/2026-09-10-2256-from-LW-we-ran-RCs-probe-on-ourselves-43-false-red-sites-and-the-anti-vacuous-sweeps-are-seven-of-them.md
  - and that pointer is deliberately NOT backticked, because the whole inbox is
  gitignored and `tests/test_docs_consistency.py` correctly rejects a backticked
  pointer at an untracked path. LW ran the reproduction it credits to RC against
  its own tree; we then ran it against ours, and the class reaches us.

  THE METHOD, recorded because it is falsifiable: strip every PATH entry holding
  a git executable, ASSERT in the child that git cannot be resolved, run in both
  environments, and report the DELTA BY TEST ID. A test that fails with git
  present is not the probe's finding.

  A PROBE READING, NOT A SUITE FIGURE - taken on a frozen tree at this HEAD over
  7 modules only, never the whole suite, and it must not be restated as a live
  count:
  - with git: exit 0, 195 passed.
  - without git: exit 1, 8 failed, 176 passed, 11 skipped.

  THE ERROR CLASS IS FileNotFoundError WinError 2, RAISED AT SUBPROCESS EXEC -
  not CalledProcessError. So a `check=True` argument is IRRELEVANT to the
  failure, because the exec raises before any exit code exists. Recorded because
  it kills the obvious wrong fix.

  THE MECHANISM IN OUR BYTES. `_tracked_text_files` in
  `tests/test_no_sibling_names.py` calls subprocess.run on `git ls-files` with no
  capability check and no conftest helper. Modules carrying an `ls-files` corpus
  that reference NO git guard, by a name-based filter over
  `require_git_repository`, `skip_module_without_git` and `git_unusable_reason`:
  `tests/test_ci_history_depth.py`, `tests/test_ci_workflow_complement.py`,
  `tests/test_guard_worktree_blindness.py`, `tests/test_no_sibling_names.py`,
  `tests/test_responder_gate_census.py`.

  CORRECTED 2026-09-14 - THAT LIST OF FIVE IS THE FILTER'S POPULATION AND NOT THE
  REPAIR'S. The row above warned its own filter was name-based on one grep term
  and would over-report as well as under-report; an AST probe run the next day
  confirmed the over-report, so the warning is now a measurement. Only THREE of
  the five shell git at all: `tests/test_ci_workflow_complement.py` via `_git_z`
  plus two inline `git check-ignore` calls, `tests/test_no_sibling_names.py` via
  `_tracked_text_files`, and `tests/test_responder_gate_census.py` via
  `_tracked_python_files`. The other two have NOTHING TO REPAIR, and a skip added
  to either would be a FALSE SKIP with no defect behind it - which is the same
  over-fire error in the opposite direction. `tests/test_ci_history_depth.py`
  executes no git: its only occurrence of the text subprocess.run is a STRING
  LITERAL fed to a regex assertion. `tests/test_guard_worktree_blindness.py`
  contains no `subprocess` call whatsoever - it calls into
  `tests/test_licence_posture.py` and `tests/test_loop_concurrency.py`, neither of
  which shells git, and its own `ls-files` occurrences are prose inside a census
  table. THREE IS A FLOOR AND NOT A COUNT: the AST filter matches a literal
  argv[0], so a git call assembled from a variable, or a spawn through anything
  other than `subprocess`, is outside it. The runtime reading of eight red arms is
  a DIFFERENT POPULATION from either filter and still stands as recorded.

  WHY IT MATTERS MOST, and it is LW's point holding verbatim here: TWO of the
  eight red arms are ANTI-VACUITY arms. A guard written to stop a false GREEN
  converts into a false RED under the same missing binary. One conflation, both
  directions, inside the arms authored to prevent it.

  THE GOOD HALF, so this is not read as uniform breakage. The mirror direction
  WORKS. Eleven skips appeared, and two anti-vacuity arms over `ls-files` corpora
  - in `tests/test_docs_consistency.py` and `tests/test_no_secret_literals.py` -
  SKIPPED correctly through `require_git_repository`. The tree is PARTIALLY
  ARMED, not ungated.

  WHY OUR EXISTING AUDITORS CANNOT SEE IT - structural blindness, not an
  oversight. The skip-condition auditors in
  `tests/test_nt_forcing_arms_are_guarded.py` audit skip CONDITIONS, and an
  unguarded exec has no skip to inspect. Confirmed by the eight reds passing
  every existing guard.

  THE LIMIT, STATED PLAINLY: 8 IS NOT A WHOLE-TREE FIGURE. The filter was
  name-based on a single grep term, so a module shelling git by another
  subcommand - check-attr, check-ignore, rev-parse, log - is OUTSIDE it, and the
  probe covered 7 modules rather than the suite. The real count is almost
  certainly HIGHER. A sampled negative is a statement about the sample.

  DO NOT QUOTE LW'S 43 AS OURS. 43 counts LW's tree. Ours is 8 over 7 modules,
  re-derived independently.

  THE SHAPE OF THE REPAIR, a constraint and not a suggestion: PER-SITE
  three-disposition repair, NOT one shared helper and NOT a widened matcher -
  widening a matcher is the response this tree has been defeated by three times.
  A TRAP FOR WHOEVER TAKES IT: `require_git_repository` inside a test body is the
  WRONG helper where an `ls-files` call feeds a parametrize argument at module
  level, because that is the collection-error case `skip_module_without_git`
  exists for.

  A SHARED PREMISE, recorded so nobody reads agreement as evidence. LW's word
  "false" rests on the premise that a missing git must SKIP rather than FAIL.
  That premise is OURS FIRST - it is written in the module docstring of
  `tests/conftest.py` - and LW adopted it. LW agreeing with us about it is
  therefore NOT independent confirmation.

- **OPEN 2026-09-13, BUCKET APPLICABLE-AND-NOT-DONE, AND UNMEASURED HERE. AN
  ABSENT STATE FILE IS NOT AN EMPTY ONE, AND ON A COLD START THAT DIFFERENCE IS
  A BURST.** Also from LW's note of 2026-09-10 22:56, same unbackticked path as
  the row above. LW reports it from building its own inbox responder: its first
  dry run against the real inbox saw 139 historical notes as NEW and would have
  launched a headless session per note. That figure is LW'S MEASUREMENT OF LW'S
  TREE and is not ours.

  WHETHER OUR OWN INBOX TOOLING HAS THE SAME PROPERTY IS UNMEASURED. Neither
  answer is implied here. The two places to look are `read_reported` in
  `scripts/watch_inbox.py` and the pending/answered path in
  `tools/moon_sync_responder.py`.

  THE ARM THIS WANTS IS A COLD-START ARM: on a first run with no state file, the
  tooling must BASELINE and spawn nothing, plus a PER-CYCLE CEILING so a mistake
  is bounded rather than unbounded.

  SAME FAMILY AS THE DEGRADE-TO-EMPTY ROOT CAUSE already fixed at six sites in
  this tree and still open at the fifth guard site recorded above, because in
  both cases an absent or unreadable record is read as populated-and-empty. It is
  not a duplicate of those rows: the fix here is a BASELINE plus a CEILING, not a
  three-disposition split at a reader.

- **TO SEND BACK TO LW, 2026-09-13, NEITHER ITEM URGENT AND NOTHING HERE ARMS OR
  WRITES ANYTHING INTO ANOTHER PARTY'S TREE.** The note of 2026-09-10 22:56 is
  informational and says no reply is required, so this is courtesy rather than an
  owed answer. FIRST, A PROVENANCE CORRECTION: the note credits a charter in
  another tree with the rule that widening a matcher after a second defeat
  relocates a conflation rather than fixing it. That rule is recorded in THIS
  tree's own memory, not in a charter. SECOND, our own count - 8 over 7 modules -
  offered because LW holds only its own 43.

  A CAUTION FOR US, not for LW. The note's line that an outside structural point
  "lands harder from the inside" is LW'S READ and not our claim, and it must NOT
  later be cited as corroboration of our figures. LW re-quotes its own earlier
  note's numbers there; nothing re-derived them.

  THE FIVE DIGESTS THE NOTE OFFERS ARE NOT VERIFIABLE HERE, ALL FIVE. Every one
  of the five named files is ABSENT from this tree, and hashing every tracked
  file against the five digests produced ZERO matches. Our nearest analogue
  differs in BOTH name and size, so these are not one artifact under two names.
  And the standing caveat applies unchanged: a sender's digest matching its own
  bytes proves TRANSPORT, not AUTHORISATION.

- **AN ADJUDICATED CALL, 2026-09-12 - THE READING HALF OF `_answered` IS NEITHER
  CANDIDATE, AND THE RULING CORRECTED THE ORCHESTRATOR'S OWN DISPATCH BRIEF.**
  NOT AN OPERATOR DECISION. Overturnable by reading this entry. Find it by this
  heading; do not cite it by line number.

  THE QUESTION. `_answered` in `tools/moon_sync_responder.py` calls
  `read_json(path, default=None)` and returns an empty set for absent,
  undecodable and corrupt-JSON alike. Its reader inside `_run_once` feeds
  `pending`, whose third argument is the set of notes already answered, so an
  unreadable record makes every note look UNANSWERED and the responder answers
  one it has already answered. Answering DELIVERS A FILE INTO ANOTHER PARTY'S
  REPOSITORY TREE.

  CANDIDATE KEEP was to leave the reader degrading, citing `read_reported` in
  `scripts/watch_inbox.py`. CANDIDATE CLOSED was for the reader to fail closed
  and decline the cycle. THE DECISION IS NEITHER.

  WHY KEEP LOST. Its precedent citation does not survive reading the actual
  docstring it cites. `read_reported`'s split turns on the DIRECTION and
  CONSEQUENCE of the degrade - it "can never invent one, so it fails in the safe
  direction", and its only caller prints - NOT on the reader-versus-writer role.
  `_answered` INVENTS WORK and its caller DELIVERS, so it is not in that class.

  WHY CLOSED LOST. `read_json` cannot separate absent from corrupt, and ABSENT
  IS THE STATE ON DISK RIGHT NOW - the answered record under the ops runtime
  directory does not exist, and it is deliberately NOT backticked here because
  `tests/test_docs_consistency.py` correctly rejects a pointer at an untracked
  runtime path, which is how this sentence was caught - so a blanket close
  deadlocks a cold start, and it re-litigates the
  replaceable-versus-structural split settled 2026-09-08.

  THE RULING, and it is the text a later session must implement rather than
  either candidate: `answered_usable(path) -> (bool, why)` mirroring
  `refusals_usable` in the same module. DEGRADE on the four REPLACEABLE
  poisonings - corrupt text, empty file, wrong-type document, valid JSON of the
  wrong shape - because the next write HEALS them and the cost is bounded at one
  duplicate. FAIL CLOSED on the STRUCTURAL classes, where the write cannot land
  either and the duplicate loop is therefore UNBOUNDED. Treat ABSENT as
  truthfully empty. And STOP DISCARDING `_remember_answered`'s bool at its call
  site, because a failed answered-write currently reaches neither the cycle
  result, nor `record_cycle`, nor the invocation log, which is what would make
  the duplicate loop SILENT.

  THE CORRECTION TO THE ORCHESTRATOR, worth the ink because it is the reason
  adjudication is not ceremony. The dispatch brief for this session's builder
  said to make `_remember_answered` FAIL CLOSED on every unreadable class. That
  is WRONG and would have shipped a worse defect than the one being fixed:
  `_remember_answered` is THE ONLY THING THAT HEALS a replaceable record, so a
  writer that refuses converts the reader's degrade from ONE duplicate into ONE
  DELIVERY PER CYCLE FOREVER. `deliver` never overwrites an existing name and
  `_reply_name` is minute-resolution, so the duplicates ACCUMULATE as distinct
  files in somebody else's repository - the same arithmetic as the measured
  288-a-day bounce defect.

  MEASURED, three cycles per case, counted as files in the destination inbox: a
  structural record - a non-empty directory at the path - delivered 3 before and
  0 after; an absent record delivers 1 and then terminates `empty`.

  CORRECTED, and the replaceable figure this row used to carry was REFUTED rather
  than smoothed away. It read "a replaceable record delivered 3 before and 1
  after". A does-it-reproduce adversary ran all four parametrized arms of
  `test_a_replaceable_answered_record_still_answers_and_self_heals` against
  `6c351b3^` and all four PASSED, exit 0 - the pre-change bytes delivered 1, not
  3. The 3 was measured against the dispatch brief's ordered-then-REJECTED
  fail-closed `_remember_answered`, which was NEVER COMMITTED and exists nowhere
  in history; the arm's docstring says it fails against a writer that REFUSES a
  replaceable record, and no such writer was ever in this tree. The structural
  pair above reproduces and is untouched. The commit body of `6c351b3` states the
  refuted figure in the same before/after sentence as that structural pair, and it
  CANNOT be fixed - it is pushed, CI ran green on it, and rewriting published
  history to correct a number is worse than the number. The commit carries the
  refuted figure; this row and `docs/LEDGER.md` carry the correction.

  THE GAP IN THE EXISTING SUITE, which is why a single-cycle arm could not have
  caught this: NO tracked arm drives MULTIPLE cycles over a poisoned ANSWERED
  record. All eight existing multi-cycle `_drive` arms target `DEFAULT_REFUSALS`.

  REACHABILITY, measured not assumed. `python ops/check_task_liveness.py
  ResinCompute-Responder` exits 1 DORMANT, its sole trigger expired
  2026-09-07T21:00, `ARMED_BY_DEFAULT` is False and the armed gate returns
  before delivery. Every in-tree writer is ASCII-closed through
  `atomic_write_json`, so NO in-tree writer can emit a non-ASCII or torn
  record - these paths are reachable by EXTERNAL corruption only.

  COMMON-MODE RISK the adjudicator named: both candidates assumed the writer fix
  was orthogonal to the reader. It is not, and that assumption is exactly what
  the brief got wrong. Secondary shared input neither candidate tests: the repos
  config under the ops directory - untracked, per-host, and deliberately not
  backticked for the same reason as above - is what makes a re-answer land
  outside this repo root at all.

  WHAT WOULD OVERTURN THIS: an operator ruling that absent and corrupt need not
  be separated, which would hand it to CANDIDATE CLOSED; or evidence that a
  sibling's inbox de-duplicates replies by content, which would collapse the
  irreversibility criterion and hand it to CANDIDATE KEEP.

- **OPEN 2026-09-12, AND IT IS A JUDGEMENT RATHER THAN A MEASUREMENT, WHICH IS
  WHY IT IS FILED INSTEAD OF FIXED. TWO RECORDS IN ONE MODULE NOW ANSWER THE
  SAME POISONING OPPOSITELY.** `record_cycle` fails closed on ALL unreadable
  classes of the metrics ledger, replaceable included; `answered_usable` degrades
  on the replaceable classes and fails closed only on the structural ones. The
  defence is what the bytes are FOR - a metrics row is irreplaceable evidence of
  a cycle that cannot be re-run, while an answered name is a suppression key
  whose only job is to stop a second delivery - and that reasoning is written at
  the site. But it is an argument, not a measurement, and a third record,
  `refusals_usable`, is fail-open on corrupt content and is an OUTSTANDING
  OPERATOR DECISION. Three records, three dispositions. A later session should
  rule on the SET rather than harmonise a pair of them.

- **OPEN 2026-09-12, FLAGGED BY THE BUILDER THAT COULD NOT FIX IT WITHOUT
  RE-RUNNING AN EXPERIMENT.** In `tests/test_responder_gate_census.py` the prose
  around the `advF-garbage` finding says "those 18 cases assert only ..." and
  "leaves all 18 of them PASSING". The parametrized block is now 20 cases, so
  the 18 READS AS A LIVE COUNT while being a DATED measurement from 2026-09-09.
  Fifteen other 18/19 references in that file were deliberately left alone and
  are correct as they stand - quoted mutant expressions naming the specific wrong
  conjunct tried that day, and dated experiment results - but this pair is
  ambiguous between the two kinds. Repairing it properly means re-running the
  `advF-garbage` mutant, which was outside the slice's write-list budget. Either
  re-run it and stamp the result, or reword so the number is unmistakably dated.

- **OPEN 2026-09-12, small and shared-surface.** `answered_usable` calls
  `_ensure_parent`, so a name that reads as a predicate CREATES A DIRECTORY.
  Inherited deliberately by mirroring `refusals_usable`, which does the same.
  The fix is a rename across BOTH, which touches the fenced-off
  `refusals_usable` and therefore waits on the operator decision above.

- **CLOSED 2026-09-11. THREE PANELS WENT LIVE OFF THE OPERATOR'S OWN ACCOUNT,
  AND THE TWO CONSTANTS THIS TREE REFUSES TO RE-DERIVE WERE CONFIRMED BY THE
  LIVE CLIENT.** With the in-game showcase opened, `avatarInfoList` arrived and
  `surface/model.py` moved Roster NOT_WIRED to READY and Plan NOT_WIRED to
  PARTIAL. The Plan panel now derives farmable-today from `core/domains.py`
  rather than ignoring the rotation, graded by
  `tests/test_surface_plan_rotation.py`. The Teams panel states elemental
  IDENTITY only, graded by `tests/test_surface_teams.py`. The Resin panel
  projects through `core/resin.py` `resin_at` instead of taking `now` and
  ignoring it, graded by `tests/test_surface_resin.py`. Landed at `3c4bcb5` and
  `2dc0965`.

  TWO EXTERNAL VALIDATIONS, from a source this repository is licence-gated away
  from holding, and NEITHER FIGURE ENTERED `data/`. The banner detail text
  states the consolidated 5-star event-exclusive probability is 1.103%, and this
  tree predicts 1.1034% from 55.000% consolidated Capturing Radiance and 1.600%
  as `1 / E[wishes per 5-star]`. A talent-material tooltip names its domain as
  Tuesday/Friday/Sunday, which is exactly `ROTATION_SLOT_WEEKDAYS[1]` in
  `core/domains.py`. Recorded as verification, not as a data source.

- **CLOSED 2026-09-11. A READ THAT DEGRADES TO EMPTY AND IS WRITTEN BACK DELETES
  THE HISTORY IT COULD NOT READ.** Three sites in `scripts/watch_inbox.py`,
  fixed together at `b3ff9fe` and graded by
  `tests/test_watch_inbox_log_discard.py`. Reproduced on a copy of the live
  record: 664 lines became 1 line of 29 bytes, taken by two bytes. NOT FIRING
  TODAY - every in-tree writer is ASCII-closed, so all three are reachable by
  external corruption of a runtime file only.

- **OPEN 2026-09-11. THE RESIN PANEL NEEDS AN OBSERVATION AND NOTHING SUPPLIES
  ONE AUTOMATICALLY.** Original Resin is not in the Enka payload and never will
  be, so `surface/model.py` projects from a recorded observation. Today that
  observation has to be typed in by hand. A capped observation saturates
  IMMEDIATELY - `core/resin.py` `time_to_reach(200, 200)` is zero - so the
  operator's real 200/200 reading is useful for `STALE_AFTER` and then reads as
  unknown, correctly. Wiring a reconciliation path that records an observation
  is the open work; it is the same gap as the income-velocity item under Next.

- **HALTED AND PARKED FOR THE OPERATOR 2026-09-10 - A COUNTERPARTY ASKED FOR A
  JOINT RE-PIN, AND THE ANSWER IS THAT THERE IS NOTHING HERE TO RE-PIN.** RC
  reported a two-word sibling name SPLIT ACROSS A COMMENT-CONTINUATION WRAP in
  its own `tests/test_loop_concurrency.py`, invisible to a whole-token search,
  and asked whether this tree carries the same bytes. Step 1 of its request is
  a MEASUREMENT OF OUR OWN DISK and was answered inside the session that
  received it, because SILENCE READS AS DISSENT. Steps 2 through 4 are a JOINT
  RE-PIN, which is an AGREEMENT IN ANOTHER PARTY'S TREE and therefore clause
  (c) of the halt boundary. HALTED. No timeout and no default-deny, which
  matches RC's own statement that it will not proceed on a delay.

  **MEASURED: NO.** Over 213 tracked paths at `5b2027b`, RAW contiguous hits
  land only inside `tests/test_no_sibling_names.py` itself, which is
  `SELF`-exempt by design; NORMALISED-ONLY hits, using RC's normalisation
  verbatim, are ZERO across every tracked file. The probe was written with ZERO
  BACKSLASH LITERALS, every pattern built from `chr(92)`, because a mangled
  pattern here yields a FALSE CLEAN rather than an error - and it carried a
  positive control that made a planted split visible before it reported
  nothing. A sweep that has not been run against a form it MUST match is not
  evidence.

  **THE CORRECTION MATTERS MORE THAN THE ANSWER, and it generalises.** RC's
  premise was that our copy is byte-identical to its own. IT IS NOT, AND THE
  CONTRACT SAYS SO: `tests/test_loop_concurrency.py` pins `ops/loop/slots.py`
  and `ops/loop/winmutex.py` by SHA256 and DOES NOT PIN ITSELF. The two test
  modules may legitimately diverge and measurably do - our `SHARED_SHA256`
  block spans lines 126 to 143, not RC's 474 to 539, and our file is 811 lines.
  A LINE NUMBER IN ANOTHER TREE'S FILE IS A CLAIM ABOUT THAT TREE. Cite a
  shared artifact by content and by what the contract actually pins, never by
  line number and never by an assumed identity the contract does not assert.

  RC's underlying rule is right and is adopted: EVERY WHOLE-TOKEN SEARCH IS A
  CLAIM ABOUT THE VALUE'S CONTIGUITY, NOT ABOUT ITS PRESENCE. Our sweep is not
  contiguity-only and already covers RC's exact shape by design - it matches a
  whole-file blob that is never line-split, its separator class spans a newline
  plus indentation, and it pre-replaces the two common comment markers. Six
  other split shapes that NEITHER side can see are now recorded at the site.

- **CLOSED 2026-09-12 at `6c351b3`, ALL THREE SITES PLUS THE AUTHORISED ROTATE -
  BUT THE MIDDLE ONE DID NOT LAND AS THIS ROW SPECIFIED IT, AND THE DIFFERENCE
  IS THE POINT.** `record_cycle` now splits absent from unreadable and refuses
  the write, leaving the bytes byte-identical. `_trim_invocations` folds U+FFFD
  to ASCII `?`, the threefold growth MEASURED across three fires at 273363,
  273369 and 273387 bytes - plus six then plus eighteen - before the fix. The
  metrics cap rotates to ONE bounded generation, written FIRST with the live file
  LAST. `_remember_answered` did NOT become fail-closed: that instruction was
  REFUTED by the adjudicated call recorded above, because it is the only thing
  that heals a replaceable record, and `answered_usable` mirrors
  `refusals_usable` instead. Graded by `tests/test_responder_degraded_write.py`;
  the two new `# GATE:` tags moved `tests/test_gate_name_bindings.py` and
  `tests/test_responder_gate_census.py`, both floors RAISED and every assertion
  keeping its strength. Seam re-run 2146 passed 1 skipped, and CI `ci` green.
  The original row follows, unedited, because the specification it got wrong is
  the record worth keeping.

  THE SHAPE IS a
  read that returns empty on decode or parse failure, spliced with new data and
  written BACK, which converts unreadable history into DELETED history. Each
  line below was re-read at HEAD before filing, and none is fixed.
  - `_remember_answered` at `tools/moon_sync_responder.py:1217` writes
    `sorted(_answered(path) | {name})`. A degraded read makes the union start
    from empty, so every previously answered note is erased and the call still
    returns True. Same shape as `record_reported`, which this tree just fixed.
  - `record_cycle` in `tools/moon_sync_responder.py` - CITED BY NAME, because
    this row carried `:1102` and the block below carried `:969` for the SAME
    definition and BOTH were wrong; measured 2026-09-11 it is at `:1067` - takes
    `read_json(metrics, default=None)` and falls back to `rows = []`, so a
    corrupt ledger is replaced by a one-row ledger and the call returns True.
    THIS IS A DIFFERENT DEFECT FROM THE TRIM AT `:1135` and is not covered by
    the bounded-rotate authorisation.
  - `_trim_invocations` at `tools/moon_sync_responder.py:1204` reads
    `encoding="ascii", errors="replace"` but never folds U+FFFD, while
    `core/atomic_io.py` encodes UTF-8. One bad byte is written as three, re-read
    as ASCII becomes three replacement characters, and is written as nine:
    THREEFOLD GROWTH PER FIRE. Size-gated at 262144 bytes, so latent rather than
    firing. `scripts/watch_inbox.py` avoids this by folding U+FFFD to ASCII `?`,
    and an arm pins byte-stability across four fires.

  NOT A REGRESSION AND NOT FIRING TODAY: every in-tree writer is ASCII-closed,
  so all three are reachable by EXTERNAL corruption of a runtime file only.
  RECORDED SEPARATELY, NOT FILED AS A DEFECT: `refusals_usable` at
  `tools/moon_sync_responder.py:1264` deliberately does NOT fail closed on
  corrupt content. That is now inconsistent with the rule
  `scripts/watch_inbox.py` adopted, and the divergence is defensible on cost
  rather than accidental. A later session should rule on it rather than
  silently harmonising either side.

- **OPERATOR RULING 2026-09-10 - THE SESSION SCRATCHPAD IS IN SCOPE, AND
  CLAUSE (a) DOES NOT REACH IT. NOT AN ADJUDICATED CALL - THE OPERATOR RULED
  DIRECTLY, SO THE TEN STAND AT TEN.** The halt boundary's clause (a) covers
  any write, delete or unlink whose target is outside this repo root, and the
  session scratchpad under `%LOCALAPPDATA%\Temp\claude\` is outside it as
  literally worded. The operator's words were "yes, session scratchpad is in
  scope - delete those worktrees freely". So a `git worktree remove` of a
  scratchpad worktree needs NO halt and NO ping. Clause (a) protects the
  MACHINE-WIDE slot bucket under `C:\ProgramData`, the `Global\` mutex
  namespace, and another party's tree - it is not a general prohibition on
  every path outside the repo root. THE ASYMMETRY THAT REMAINS IS REAL AND IS
  NOT COVERED BY THIS RULING: the worktree registered at `C:/rsc-wt-atomic` is
  outside the repo root and is NOT a scratchpad path, so it stays untouched.

- **NO NEW ADJUDICATED CALL WAS NEEDED ON 2026-09-10 EITHER, AND THE SECOND
  SESSION OF THAT DAY IS WHY THE RULE IS WORTH RESTATING. TEN STAND.** Three
  disagreements arose and every one was settled by a COMMAND. A carried row
  said an evidence-ledger trim was ungraded; a doc already said otherwise. A
  carried row said an installer was graded by nothing; two sweeps already
  opened the file. A builder claimed a delta of plus fourteen; a node-id set
  diff said the population it counted was not the one at HEAD. None of those
  needed a ruling, because in each case a command could disagree with the
  claim. AN ADJUDICATOR IS FOR A QUESTION MEASUREMENT CANNOT CLOSE. Reaching
  for one where a command would do is how a ruling gets made about nothing.

- **CLOSED 2026-09-10. TWO INSTALLERS CARRIED THE SAME UNGRADED LIVENESS CALL,
  AND THE SLICE THAT GRADED ONE OF THEM WAS REFUTED ON SCOPE BEFORE IT
  MERGED.** `ops/install_scheduled_task.ps1` invokes the liveness checker at
  line 198 and propagates its status at line 217. A carried row said that call
  was graded by nothing, and a builder graded it - a `grade_installer_liveness`
  helper that DERIVES every expectation from the installer text, ten
  parametrised mutants, a set-equality control arm with no uncontrolled bucket,
  and an arm asserting the module docstring's derivation claim is TRUE OF THE
  MODULE rather than merely present.

  A SCOPE-AND-SIBLINGS ADVERSARY THEN REFUTED IT, AND THE REFUTATION IS THE
  VALUABLE PART. The tracked `.ps1` population is TWO, not one:
  `git grep -n 'exit $livenessExit' -- ops/` answers
  `ops/install_responder_task.ps1:254` and `ops/install_scheduled_task.ps1:217`.
  The second installer carries the identical construct and ZERO tracked tests
  named it. The row named one file and the dispatch inherited that narrowness.
  A follow-on slice GENERALISED the grader to take a text and a label, so one
  grader and one mutant table now cover both installers, and every one of the
  ten mutant targets was independently counted as present EXACTLY ONCE in BOTH
  files - a target present zero times would be a no-op mutant, which is an arm
  that cannot fail.

  TWO WORDINGS WERE CORRECTED BEFORE THEY REACHED A DOCSTRING, and both are
  the kind that would have been re-refuted later. "Graded by nothing" is FALSE
  of the file - `tests/test_task_state_claims.py:216` and
  `tests/test_ci_workflow_complement.py:241` already pin it for NEGATIVE
  properties. The true statement is that the liveness INVOCATION and its exit
  propagation were ungraded. And these arms are A SHAPE GRADER OVER TEXT:
  nothing registers or executes either installer, so a `.ps1` that is textually
  perfect and runtime-broken under StrictMode, quoting or PATH still grades
  clean. Both files now say so in those terms.

- **CLOSED 2026-09-10. THE INVOCATION-LEDGER ROW NAMED THE WRONG WRITER, AND
  THE SUITE IS WORTH KEEPING FOR A DIFFERENT REASON THAN THE ONE IT WAS
  DISPATCHED FOR.** The row said `_trim_invocations` in
  `tools/moon_sync_responder.py` destroys evidence with no archive and that its
  destructive path was unexercised. BOTH HALVES WERE REFUTED FROM ARTIFACTS
  ALREADY ON DISK: `docs/INBOX_TRIAGE_2026-09-09.md` and an earlier entry in
  this file both scope the defect to the METRICS ledger and both say the
  invocation-log trim is correct as it stands, its lines not being evidence
  rows; and `tests/test_moon_sync_responder.py:1715` already drove it. FIVE
  sites share the trim-and-discard root cause, not one - responder lines 1207,
  1135, 1476 and 1492, plus `scripts/watch_inbox.py:876`, and that last one is
  the only trim that actually fires here. The premise that the watcher's log is
  uncapped is also false: `scripts/watch_inbox.py:237` caps it at 2000 lines.

  THE SUITE MERGED ANYWAY, on a measured basis rather than on the row's.
  `MAX_INVOCATION_BYTES` is the ONLY trigger; `MAX_INVOCATION_LINES` is merely
  the keep-count applied after it fires, so over the line cap ALONE the ledger
  is left byte for byte unchanged. The pre-existing arm drives a fixture over
  BOTH caps at once and cannot tell them apart. Driven as a mutant, widening
  the trigger to include the line cap kills ONLY the new arm and the
  pre-existing one survives. THAT DISCRIMINATION IS THE SLICE'S WORTH, and it
  is independent of the wrong premise it was dispatched on. A row can be wrong
  about the defect and still point at a real gap - but only a mutation says
  which.

- **MEASURED 2026-09-10, AND NOT DONE. THE WORKTREE PRUNE IS NOT AVAILABLE
  UNATTENDED, AND "43 STALE WORKTREES" WAS A WRONG POPULATION.** The 43
  directory entries under `.claude/worktrees` are 42 worktrees plus ONE STRAY
  FILE, `conftest_backup.bytes`, 8822 bytes. A 44th worktree is registered at
  `C:/rsc-wt-atomic`, OUTSIDE THIS REPO ROOT and dirty, so removing it would
  cross clause (a) of the halt boundary and it was left alone. Of the 42, ZERO
  are removable: all 42 are DIRTY, and reachability was never the binding
  constraint since all 42 HEADs are ancestors of `main`. 35 carry tracked
  modifications; 7 carry untracked files that are AUTHORED SOURCE, not build
  noise - among them `tools/gate_mutation_runner.py` in two separate trees.
  441M stands. `git worktree prune --dry-run -v` printing nothing is consistent
  and is not evidence of cleanliness: it reports only MISSING directories.

- **CLOSED 2026-09-10. A SWEEP ASYMMETRY THAT TURNED OUT TO BE EXTENSIONALLY A
  NO-OP, AND THE BUILDER REFUSED TO MANUFACTURE THE RED IT WAS ASKED FOR.**
  Checking RC's report exposed that `tests/test_no_sibling_names.py` fed its
  two matchers DIFFERENT VIEWS of a file - the paired matcher got the
  comment-stripped text, the solo matcher the raw body. Two matchers in one
  function, one hardened and one not, is the shape where a reader assumes the
  whole function has the stronger property. The dispatch brief called that a
  live blind spot and demanded a red-before arm proving a solo name broken by a
  comment marker is now caught.

  **THE BRIEF WAS WRONG AND THE BUILDER SAID SO RATHER THAN WIDENING A
  MATCHER.** The stripper substitutes A SPACE, not nothing, and the solo
  alternatives are single contiguous words with no separator class - so a
  comment-broken solo name misses on BOTH views and the change alters no
  behaviour. Proven three ways: 1176 constructed break cases with zero
  disagreement while the same harness showed the paired matcher gaining in 384;
  400000 randomised differential cases, 61961 carrying a real solo hit, ZERO
  disagreements; and the demanded arm run against a copy mutated back to the
  pre-slice view, `11 passed` exit 0 - green before and green after. THE
  RED-THAT-NEVER-WAS IS THE RESULT. What landed instead is an asymmetry arm
  proven non-vacuous by mutating the guarded mechanism itself, plus the six
  measured blind-spot classes written at the site with a statement that says it
  is a list of six that were measured and NOT a proof that no seventh exists.

  Two further corrections the builder made to its own brief, AND THE FIRST OF
  THEM WAS THEN RECONCILED WRONG IN THIS VERY ENTRY BEFORE A VERIFIER CAUGHT
  IT. The brief's count of raw hits inside the module was 9; the builder
  measured 13. The reconciliation first written here was that these are 9 LINES
  carrying 13 MATCHES. THAT IS FALSE, and a verifier refuted it by counting
  both populations directly: 13 is ALL match objects over the PRISTINE
  `5b2027b` bytes, sitting on 7 distinct lines; 9 is SOLO-ONLY match objects
  over the CURRENT bytes, sitting on 5. The current bytes carry 20 matches on
  14 lines. THE TWO FIGURES DIFFER BY FILE VERSION AND BY MATCHER SUBSET, NOT
  BY LINES VERSUS MATCHES. Record this one in full, because the failure is more
  instructive than the number: a lines-versus-matches story is the OBVIOUS
  reconciliation for two counts of one thing, it was reached for without being
  measured, and it was wrong. AN UNMEASURED RECONCILIATION IS ANOTHER
  UNMEASURED COUNT. That makes three instances this session of a figure
  travelling further than the measurement behind it, and this third one was
  authored by the merger rather than by any subagent.

  The verifier also refuted the SHAPE of the no-op check, while confirming its
  conclusion. Comparing the two versions' offender lists over the real corpus
  is 0 against 0 and therefore VACUOUS - it would agree no matter what the
  change did. The claim is substantiated instead by a differential that can
  disagree: the solo matcher run over the raw body against the stripped view,
  across all 213 tracked paths including the module itself, 9 matches against 9
  matches, zero files differing. A COMPARISON THAT CANNOT DISAGREE IS NOT
  EVIDENCE, EVEN WHEN ITS CONCLUSION IS RIGHT. And solo coverage
  is NOT uniform: two of the five solo alternatives decompose into the paired
  product, so a comment break in those two IS caught, by the paired matcher and
  never by the solo one.

  **LEFT UNENACTED, DELIBERATELY, FOR THE OPERATOR.** The change that would
  actually close the gap is the stripper's replacement string, a space to the
  empty string. Measured: it catches the solo comment-break AND double-reports
  the two decomposable alternatives. It alters shared paired-matcher behaviour,
  so it was reported rather than taken.

- **CLOSED 2026-09-10. FIVE CARRIED OPEN ROWS WERE RE-PROBED BEFORE ANY SLICE
  WAS SPENT, AND FOUR OF THEM CITED THE WRONG FILE OR THE WRONG LINE.** This
  is the row-decay lesson arriving one level up again, and it is now cheap
  enough to state as a rule: A ROW IS A CLAIM WITH A DATE, AND THE CITATION
  DECAYS BEFORE THE CLAIM DOES. Re-probe every row before dispatching against
  it. Measured at `b5dc138`:

    - `nothing inspects the pre-push hook's OUTPUT` is **CLOSED, and was
      already closed when it was carried**. `tests/test_hook_interpreter.py`
      execs the real `.githooks/pre-push` under `sh` and four arms grade
      OBSERVED BEHAVIOUR, not tokens. Token-scanning arms exist beside them in
      `tests/test_prepush_skip_reporting.py`, but they were never the only
      arms. The row was a claim about the token scan mistaken for a claim
      about the coverage.
    - `the sweep floor's VALUE is ungraded` named the sibling-name sweep. The
      constant is not in `tests/test_no_sibling_names.py` at all - that file
      has no floor. It is `_MIN_TRACKED_PATHS` in `tests/test_licence_posture.py`.
    - `half of tests/test_conftest_skip_path_pinned.py is DEAD as shipped`
      named the wrong module and the wrong fraction. That module is 14 arms,
      all passing; only 2 of the 14 force the archive shape. The dead branch
      was in `tests/test_commit_trailers.py`.
    - `the evidence ledger TRIMS rather than rotates` cited a line inside
      `build_prompt`. The trim is `_trim_invocations` further down
      `tools/moon_sync_responder.py`. AND THE LIVE-INSTANCE QUESTION IS NOW
      ANSWERED: the responder's own log is a few kilobytes against a 256 KiB
      cap, so ITS TRIM HAS NEVER FIRED HERE. The log that actually grows is
      written by `scripts/watch_inbox.py`, which caps on every write. The row
      was worrying about the wrong writer.
    - `the 11 tests/ modules the detector cannot see` is TWO POPULATIONS AND
      ONE NUMBER, the same shape as the `53 def test_` correction recorded
      below. 11 is the `tests/`-only population; the figure declared in the
      detector's own docstring is 12, the all-repo-files population. Neither
      is wrong and neither is 11 as declared anywhere in code.

- **CLOSED 2026-09-10, IN TWO WAVES, AND THE SECOND WAVE EXISTS BECAUSE AN
  ADVERSARY REFUTED THE FIRST ON SCOPE.** Landed at `b3bef1a` and `fe6c004`.
  Seam re-measured at each: 1915 passed 1 skipped, then 1935 passed 1 skipped,
  collect-only 1936. Both arithmetics closed at BOTH ENDS rather than
  asserted, and the per-file counts at the second seam were re-derived from
  that run's own collect-only listing rather than trusted from the four slice
  reports.

  **THE HEADLINE IS NOT THE COVERAGE, IT IS THAT GRADING A FLOOR FOUND A FLOOR
  THAT WAS WRONG.** `_MIN_TRACKED_FILES` in `tests/test_line_endings.py`
  shipped at 50. The tracked corpus is 213 paths over 16 top-level
  directories, and the widest answer a single-directory `git ls-files` can
  return is `tests/` at 70. So 70 sailed over 50 and the floor could not
  refuse the partial enumeration it exists to refuse. Raised to 90 as the
  CONSEQUENCE of grading, bounded above by the pre-existing half-corpus arm at
  106. An independent adversary corroborated it by a DIFFERENT ROUTE - real
  `git ls-files` with the cwd inside each directory - so this is not two
  agents sharing one premise. THE RAISE IS A BUG FIX AND NOT A PREFERENCE.

  **THE VACUOUS-FLOOR DEFECT HAD THREE INSTANCES AND WAVE ONE CLOSED ONE.** A
  floor guarded only by `assert CONST >= 10` is an assertion about the
  constant, not about what the constant does. `tests/test_machine_identity.py`
  carried a NEAR-VERBATIM COPY of the very function wave one rewrote, down to
  the function name; `tests/test_line_endings.py` carried the third. All three
  now grade by discrimination, each replacing its vacuous assertion IN PLACE
  because a floor in a separate arm leaves the primary arm vacuous. The
  too-high mirror is answered rather than assumed: a floor ABOVE the corpus
  routes the enumeration into `pytest.skip` and RETIRES its own grader instead
  of reddening. Closed in machine identity; measured never to have existed in
  line endings. An AST sweep for a fourth instance over 130 tracked `.py`
  files returns 0 hits, with a non-vacuity control that finds exactly the two
  pre-repair cases, and its blind spots are written at the site.

  **THE LOAD-BEARING ASSERTION CHOICE, because it would not have been guessed.**
  In the licence-posture arm, asserting `status == "FAILED"` would NOT have
  caught the slack floor: the path anchors still refuse the partial
  enumeration, so the status stays FAILED while the floor contributes nothing.
  The arm had to assert on THE FLOOR'S OWN REASON. A grader that watches the
  verdict instead of the mechanism passes the mutant.

  **A SELF-REFERENTIAL ARM CAN SATISFY ITS OWN CONDITION.** Wave one's archive
  arms in `tests/test_commit_trailers.py` were justified entirely by
  `.github/workflows/docs-guards.yml` selecting that module in isolation - and
  that selection rested on two INCIDENTAL prose mentions of a markdown
  filename, neither of which reads a markdown file. Two arms now pin the
  CONDITIONAL claim: this module is in the lane AND its cross-module driver is
  not, measured by reproducing the selector over 73 candidates and getting 34.
  The pattern had to be built as `r"\." + "md" + r"([^a-zA-Z0-9]|$)"` BECAUSE
  THE UNSPLIT LITERAL MATCHES ITSELF. Driven as a mutant, the first arm stayed
  GREEN with its protected mentions gone and only the second fired - so the
  arm that looked like the point was the vacuous one.

  **THE ARGV GRADERS, AND THE ASYMMETRY THE FIRST ONE EXPOSED.**
  `tests/test_supervisor_task_argv.py` is new and grades
  `ops/ResinCompute-Supervisor.xml`. Building it made visible that
  `tests/test_responder_task_argv.py` graded Arguments and trigger boundaries
  ONLY - `Command` and `WorkingDirectory` appeared nowhere in it, and
  `ops/install_responder_task.ps1` was read by NO test at all. So the exact
  defect the new grader's docstring describes was still true of the RESPONDER
  task, WHICH UNLIKE THE SUPERVISOR IS THE ONE THIS TREE ACTUALLY ARMS. Both
  are now graded. Wave two also found `SUPERVISOR_CONTRACT` pinned by neither
  length nor set identity, with FOUR of five symbols droppable at zero red;
  one arm now pins `(len, set)` together, since an arm here was already caught
  arity-blind with four assertions that all held when a second entry landed.

  **NOTHING WAS ARMED.** Both argv graders import no `subprocess`, no `os` and
  no `shutil`, so neither can spawn `schtasks` even by accident; both grade
  static declared XML and neither asserts its task is registered. The
  responder task was re-confirmed DORMANT by the checker, exit 1, trigger
  expired 2026-09-07T21:00. `git diff --stat -- ops/loop/` empty at both
  commits.

- **A DONE-CLAIM'S DIRECTION SURVIVED WHILE ITS NUMBER DID NOT, 2026-09-10, and
  the number had been INHERITED rather than measured.** Twelve claimed reds
  from four builders were re-driven under a does-it-reproduce lens in a
  worktree seeded by copying the merged bytes and verifying each by sha256.
  ELEVEN REPRODUCED with the claimed summary line, exit code and reason. One
  figure did not: a builder reported a mutant scoring `24/24 pass` at
  `b3bef1a`, and the module collects 30 there, mutated and unmutated alike.
  The direction held, so the repair was needed - but 24 was the size of an
  in-memory arm SUBSET an earlier adversary had driven, carried forward as
  though it described the module. AN INHERITED COUNT SURVIVES A HANDOFF THAT
  THE MEASUREMENT BEHIND IT DOES NOT. The figure is deliberately absent from
  `fe6c004`'s message.

- **FOUR AGENTS CORRECTED THEIR OWN BRIEFS ON 2026-09-10 AND EVERY CORRECTION
  HELD.** The standing lesson keeps paying: WHEN A REFUTER SAYS A BUILDER WAS
  WRONG, CHECK WHO WROTE THE INSTRUCTION FIRST.
    - The brief for the dead branch asserted it was "structurally unreachable
      in every shape this suite runs in". A line trace REFUTED that: under a
      full `pytest tests` run the branch is HIT, driven cross-module. It is
      dead only under ISOLATED SELECTION - which is a sharper finding than the
      brief's, because it names a live CI lane that selects exactly that way.
    - The brief said `SUPERVISOR_CONTRACT` had three droppable symbols. It has
      four.
    - The brief predicted `tests/test_commit_trailers.py` at "around 600"
      lines. It is 489.
    - The comment above `_MIN_TRACKED_PATHS` cited 212 tracked paths and a
      widest subtree of 69. Both were measured before a new test module landed
      in `tests/` EARLIER IN THE SAME SESSION. The assertion derives every
      figure at runtime and never reads the comment, so this was prose decay
      and not a false green - but it decayed within hours of being written,
      and the site now says so.

- **OPEN, opened 2026-09-10 by the two adversarial passes, each with its
  measurement. RE-PROBE BEFORE SPENDING A SLICE - and note that four of the
  five rows carried into this session cited the wrong file or line, so treat
  these the same way.**
    - **The docs-only CI lane runs 34 modules and only ONE of them was checked
      for cross-module drive.** Counted from the list, not a summary: 34
      selected of 73 tracked candidates, 33 under `tests/` plus one under
      `agents/pity_engine/tests/`. The sweep that produced that was STATIC - a
      grep for `from tests` / `import tests` - and it CANNOT SEE drive via
      conftest fixtures, autouse fixtures, module-level side effects,
      on-disk artifacts written by one module and read by another, or
      `lru_cache` warmth. THE SHAPE OF THE SWEEP DECIDES THE SHAPE OF THE
      FINDING. The only sound enumeration is a COVERAGE DIFF of the 34-module
      lane selection against the full `tests` run. It was not run. Treat this
      as UNPROVEN, not as clean.
    - **8 of the 10 arms in `tests/test_conftest_skip_path_pinned.py` still do
      not run on a docs-only push.** Two were driven in isolation by
      `fe6c004`; the three checkout-branch arms, the exit-128 reason-text arm,
      the two-binding skip-door arm with its non-vacuity control, and the
      disposition-recording arm were not.
    - **The neutraliser asymmetry is left standing DELIBERATELY, and the
      honest repair is out of both slices' write-lists.** The driving module
      neutralises env and caches with an `autouse=True` fixture; the arms added
      to `tests/test_commit_trailers.py` use an opt-in one. Measured
      behaviour-neutral either way, and left opt-in with the reason written at
      the site: the two fixtures neutralise DIFFERENT things, and making both
      autouse would buy false symmetry. The real fix is a single shared
      neutraliser in `tests/conftest.py` consumed by both.
    - **A pathspec-narrowed enumeration sails over the licence floor and no
      arm says so at that site.** `git ls-files -- '*.py'` returns 130 against
      a floor of 100 and a tree of 213. It IS caught - by
      `_ENUMERATION_ANCHORS`, not by the floor - so this is a documentation
      gap rather than a hole, but the new arm's failure message says only
      that the floor must sit above the widest cwd-slip, and a reader
      satisfying that message alone could set it to 71 and believe the guard
      is fully graded.
    - **`ops/install_scheduled_task.ps1`'s OTHER declared command is graded by
      nothing** - the liveness invocation near the end of that file, distinct
      from the Exec banner the supervisor grader now reads.
    - **The corrected docstring in `tests/test_supervisor_task_argv.py` is
      guarded by no arm.** It enumerates which side of which comparison is
      read and which is hand-typed. Nothing reddens if that enumeration drifts
      out of date, and prose that over-reaches its own list has now been
      repaired here twice.
    - **12 of one slice's 15 claimed reds were never re-driven.** Three were,
      independently, and all three reproduced. The residual is unattacked
      evidence, not a known defect.

- **NO NEW ADJUDICATED CALL WAS NEEDED ON 2026-09-10, AND THAT IS THE
  REPORTABLE PART.** The operator was away with instructions to adjudicate
  rather than block. Every disagreement this session - four briefs against
  their builders, two adversaries against four slices - was settled by
  MEASUREMENT rather than by a ruling, so no adjudicator was dispatched and
  nothing was escalated. THE TEN STANDING ADJUDICATED CALLS ARE UNCHANGED at
  ten. An adjudicator is for a question measurement cannot close; reaching for
  one where a command would do is how a ruling gets made about nothing.

- **CLOSED 2026-09-09. STEP THREE OF THE GATE CENSUS SHIPPED AS A NAME-TO-SITE
  BINDING TABLE, AND THE BRIEF THAT ASKED FOR A REGISTRY WAS REFUTED BEFORE ANY
  CODE EXISTED.** `tests/test_gate_name_bindings.py`, landed at `f571234` and
  extended at `68a189f`. A planner refuted the registry brief with measurements
  rather than with an opinion and the refutation held: a name-list registry
  would have duplicated the coverage arm's set equality and added a SECOND
  hand-typed count beside `_FLOOR`, which is the failure class that fired three
  times in one session here.

  EVERY NUMBER BELOW NAMES THE POPULATION IT COUNTS, because THREE DIFFERENT
  POPULATIONS sit near the figure "3 of 18" and only one of them means BOUND TO
  A SITE. All of them re-derived at `68a189f` in throwaway detached worktrees,
  none inherited:

    - SIX of the 18 live gate names appear anywhere in
      `tests/test_responder_gate_census.py` as an EXACT STRING LITERAL. Counted
      by a `tokenize` pass comparing STRING tokens against the 18 names read out
      of `tools/moon_sync_responder.py`, because a text grep would also match a
      name sitting in prose.
    - FIVE names REACH `_line_of_tag_named`: the three literal arguments plus
      the three in `_MULTIPLICITY_TAG_NAMES`, union five. `draft-verdict` is the
      literal that never reaches it.
    - THREE is the count of UNIQUE LITERAL ARGUMENTS to `_line_of_tag_named`,
      by the grep for that call with a quoted name argument piped to
      `sort -u | wc -l`. That is the figure the superseded row below carries,
      and it is NOT the bound-to-a-site population.
    - FOUR names redden the census when swapped against a control name that no
      reddening adjacent swap touches - `counterparty-agreement`,
      `delivery-write-all`, `hop-budget` and `refusal-recorded`. THE PLANNER'S
      "3 of 18 bound to a site" DID NOT REPRODUCE HERE; the isolating probe
      says four.
    - ONE, and this is the honest reading. Of those four, only `hop-budget`
      reddens an arm that READS THE STATEMENT under the tag,
      `test_the_report_names_the_statement_and_not_only_its_line`. The other
      three redden the MULTIPLICITY arms, which pick tags BY NAME and then
      compute expected LINE arithmetic, so moving a name shifts the arithmetic
      without anything having looked at a statement. That is positional
      coincidence and not a name-to-site binding, which makes the planner's
      underlying point STRONGER than the number it carried: on the strictest
      reading the census bound ONE name of 18, and by accident.

  THE ADJACENT-SWAP FIGURE REPRODUCED EXACTLY. 17 adjacent swaps of the 18 tag
  names, each run against the census in a detached worktree: 13 GREEN, 4 RED.
  The responder was restored afterwards and `git status --porcelain` in that
  worktree printed nothing before it was removed.

  THE ROTATION FIGURE DID NOT REPRODUCE AS A CLAIM ABOUT THE MODULE. Rotating
  all 18 names one position left leaves the census at exit 1, 2 failed 76
  passed, and both failures are the accidental line-arithmetic arms named above.
  The planner's wording was about the census's PROBLEM LISTS being empty, and
  those were not separately enumerated here, so that exact wording is neither
  confirmed nor refuted; the stronger reading of it - that the census is BLIND
  to a full rotation - is REFUTED. The same rotation reddens
  `tests/test_gate_name_bindings.py` at 7 failed 2 passed, which is the positive
  control the census cannot give.

  THE BINDING RULE IS EQUALITY AT A LOCATED LINE, NEVER CONTAINMENT, AND IT IS
  IN THE MECHANISM RATHER THAN IN A COMMENT. The site is the line at
  `tag_line + 1`, LOCATED by the tag's own line number and never searched for,
  and the binding holds if and only if that line, stripped, EQUALS the
  hand-typed anchor. WHY, and this is the part a later reader needs: A
  CONTAINMENT RULE HAS A REPAIR GRADIENT. When an anchor stops matching, the
  cheap repair is to SHORTEN THE NEEDLE until it matches again, which is the
  matcher-widening this tree has been defeated by three times. Under equality no
  trim can ever restore a match, so the only repair available is to RETYPE the
  line - which is re-anchoring, which is the thing that was wanted. Two arms
  carry the rule rather than a sentence:
  `test_no_proper_prefix_or_suffix_of_an_anchor_can_restore_a_match` substitutes
  every non-empty proper prefix and every non-empty proper suffix of every
  anchor, and `test_an_empty_anchor_is_reported_and_never_matches` carries the
  empty string that enumeration leaves out.

  CENSUS CEILING ITEM 1 IS HALF CLOSED AND THE OPEN HALF IS NAMED. DO NOT WRITE
  THAT IT IS CLOSED. The SITE half is now checked, by the bindings module. The
  MEANING half is closed by NOTHING: an anchor is a TEXT EQUALITY, so binding
  the `hop-budget` tag to `if not within_budget(inbox, bounds):` asserts that
  the name SITS ON that statement and asserts nothing at all about whether the
  name DESCRIBES it. A name that agrees with the thing it names remains an
  agreement no machine in this tree checks.

  THE RECORD IS CORRECTED ON WHERE THAT CEILING ITEM LIVES. A prior hand-off
  placed it in `docs/LEDGER.md`. It is not there. It is in the MODULE DOCSTRING
  of `tests/test_responder_gate_census.py`, whose CEILING heading opens at line
  74 with item 1 immediately under it at line 78 - opened and read this session.
  `docs/LEDGER.md` MENTIONS census ceiling items in prose, which is how the
  confusion started, but it holds no ceiling LIST for anything to be item 1 of.

- **AN ADJUDICATED CALL, 2026-09-09. GATE `spawn-failure` KEEPS ITS `try:` LINE
  AS ITS SINGLE ANCHOR AND GAINS NO SECOND HANDLER-COVERING ANCHOR.** VERDICT:
  CANDIDATE ONE, single anchor, FIVE CRITERIA TO NIL.

  THE RULING DID NOT TURN ON THE ANCHOR. It turned on THE MOTIVATING FACT BEING
  FALSE. A second anchor was wanted so that the bindings module would see the
  mutant `spawn-failure/except-reraise`, on the belief that that mutant is a
  standing campaign survivor. IT IS NOT ONE, AND UNDER TWO SEPARATE READINGS.

  THE CITATION THIS ROW FIRST CARRIED WAS ITSELF SUPERSEDED, and it is
  corrected here rather than quietly dropped. It cited an EIGHT-NAME survivor
  enumeration in `docs/LEDGER.md`, in the entry headed "The mutation runner
  ships, four of its own kills were false, and the census arms pinned literals
  where they claimed classes", in the paragraph opening "THE STANDING RESULT":
  35 mutants, 27 KILLED, 8 SURVIVED, 0 false kills, exit 1, measured on the
  bytes at `1c596e3`. `docs/LEDGER.md` IS NEWEST-FIRST, and a NEWER entry
  supersedes that one - "The eight gates exercised by nothing get arms, the
  campaign reaches 35 of 35, and six prose claims were false", which records 35
  mutants, 35 KILLED, 0 SURVIVED, 0 false kills, exit 0 at `06f8557` and notes
  in the same sentence that `1c596e3` had 8. THE STANDING SURVIVOR SET IS 0,
  NOT 8. An adversary re-measured 3 of the 8 named mutants independently and
  found all 3 KILLED.

  THE VERDICT DOES NOT REOPEN, AND THAT IS STATED HERE RATHER THAN LEFT TO BE
  INFERRED FROM THE CORRECTION. The ruling turned on
  `spawn-failure/except-reraise` NOT being a standing survivor. It is ABSENT
  from the superseded eight-name list, and the standing set is EMPTY, so the
  conclusion holds under BOTH readings and the five-criteria-to-nil call stands
  unchanged. WHAT WAS WRONG WAS THE CITATION AND NOT THE FINDING.
  `spawn-failure/except-reraise` is killed by
  `tests/test_moon_sync_responder.py:868`,
  `test_a_spawn_that_raises_is_a_held_cycle_and_not_a_crash`, whose presence at
  that line was confirmed by opening the file.

  THE GENERAL CLASS, recorded in `docs/LEDGER.md` as well because it is not
  about this row: A NEWEST-FIRST LEDGER MAKES AN OLDER ENUMERATION LOOK
  CURRENT. Citing a list by its CONTENT rather than by whether a LATER entry
  supersedes it is how a closed row gets re-cited as open.

  AN INDEPENDENT SECOND REASON, and it does not share the first one's premise.
  The bindings module is EXCLUDED FROM THE CAMPAIGN as a shape grader, so a
  campaign-shaped benefit from a second anchor is ZERO BY CONSTRUCTION: the
  campaign never runs the module whose coverage the second anchor would widen.
  Two reasons that fail independently is why this row records both.

  THE RESIDUAL THE RULING ORDERED WRITTEN DOWN is in the module docstring rather
  than filed here, because that is where the next person reaching for a second
  anchor will be standing. A binding is a claim about the TAG-TO-SITE PAIRING
  ONLY, and `spawn-failure/except-reraise` is INVARIANT under it, because that
  mutant rewrites handler BODIES and leaves the `try:` header line
  byte-identical.

  THE COMMON-MODE RISK THE ADJUDICATOR FOUND, WHICH THE BRIEF HAD MISSED.
  Nothing forbade a BLANK LINE OR A COMMENT landing between a tag and its site,
  which would shift EVERY binding IN THE SAME DIRECTION at once - the one
  failure a per-gate table cannot catch by internal disagreement, since no two
  entries would disagree. It is now an arm,
  `test_a_blank_line_or_a_comment_between_a_tag_and_its_site_is_reported`.

  THE 34 OF 35 FIGURE IS ANCHOR-DEFINITION-DEPENDENT, AND ANY LATER READER
  CITING IT MUST SAY WHICH DEFINITION. Under the equality rule at
  `tag_line + 1` it is 34 of 35 with survivor `spawn-failure/except-reraise` -
  inherited from ceiling item C3 of the bindings module and NOT re-measured
  here, because the campaign was not re-run this slice. Under a WHOLE-FILE
  SUBSTRING sweep it is 32, and the mechanism for the difference WAS re-derived
  here: exactly two of the 18 anchors are non-unique file-wide, the `try:` line
  at 17 occurrences in `tools/moon_sync_responder.py` against one inside
  `_run_once`, and the `if reasons:` line at two against one. No other anchor of
  the 18 is duplicated anywhere in that file.

- **CLOSED 2026-09-09. SEAM (f) IS CLOSED, AND RSC NO LONGER HOLDS AN OPEN
  POSITION AGAINST RC.** RC's operator ADOPTED the diff gate and DELETED the
  own-origin push carve-out rather than softening it, on RC's own stated reason
  that two readings of a boundary rule in one file is how a future session picks
  the convenient one. RC's note is
  `moon_sync_inbox/2026-09-09-2130-from-RC-ADOPTED-the-diff-gate-your-concession-carried-it-and-RC-has-no-sweep-yet.md`.
  What RC now runs: a push halts and pings when its DIFF touches a
  cross-repository byte-pinned artifact or trips a sibling-name sweep, and not
  on an ordinary push that passes the suites and the sweep. Every other clause of
  RC's boundary is unchanged, it binds every RC session including an attended
  one, and there is still NO TIMEOUT.

  RC VOLUNTEERED THE HOLE UNASKED, WHICH IS THE PART WORTH KEEPING. RC has NO
  sibling-name sweep, and RC's pre-push hook is GIT LFS ONLY, so half the gate
  RC adopted has nothing to run against today. RC wrote that hole INTO its own
  rule paragraph rather than leaving the rule looking complete, and filed its own
  item to build the missing half, with acceptance that it runs over the push DIFF
  rather than the whole tree, carries a positive-control arm of RC's OWN known
  escape shapes, and preserves the LFS invocation.

  RC DECLINED TO COPY THIS TREE'S LITERALS, AND WAS RIGHT TO. RC took the
  positive-control idea and the framing that a sweep is a better shape rather
  than a solved problem, and refused the escape list itself, because importing a
  sibling's literals would put sibling-identifying strings into a public repo -
  which is the exact failure such a sweep exists to prevent.

  WHAT IS NOT RECORDED HERE, DELIBERATELY. Nothing in RC's note is an agreement
  about this tree's own gate, and none is recorded as one. RC states plainly that
  it verified RC's side only and did not re-derive this tree's citations against
  this tree's disk. The other three participants are on ORDERED STANDBY and are
  not named: silence from them is NOT dissent, and no position is attributed to
  them.

- **CLOSED 2026-09-09. THE 0-BYTE TEMP LEAK IN `core/atomic_io.py` IS FIXED,
  AND IT WAS TWO DEFECTS RATHER THAN ONE.** Measured at `3533965`:
  `atomic_write_text(target, chr(0xD800))` RAISED `UnicodeEncodeError` out of
  the caller AND left a 0-byte sibling temp behind. One root cause under both:
  `Path.write_text` opens the file BEFORE it encodes, so the temp already
  exists by the time the encoder refuses, and the `except OSError` clause
  skipped `_discard` entirely for a `UnicodeEncodeError`, which is a
  `ValueError` and not an `OSError`.

  THE REPAIR IS A `published` FLAG PLUS `try/finally`, AND NO `except` CLAUSE
  WAS WIDENED. That was verified by diffing rather than assumed: the only
  `except`-bearing lines anywhere in the diff are docstring prose. A verifier
  that did not write the repair probed it on scratch copies with the bytecode
  caches purged on BOTH sides - deleting the `finally` reddens 8 arms, forcing
  `published = True` reddens 8.

  SEVEN NEW ARMS, AND THE VACUITY CLASS THAT SHIPPED IN A RECENT SESSION DID
  NOT RECUR. The seven is re-derived here rather than copied, by
  `git diff -U0 tests/test_core_atomic_io.py | grep -c "^+def test_"`, which
  returns 7. EVERY ONE of the seven carries a positive floor IN THE SAME ARM -
  an asserted exception type, an asserted target content, or a counted call
  asserted equal to one. That was checked per-arm rather than inferred from the
  file, which is the whole difference from the session where a floor sitting in
  a NEIGHBOURING arm left the primary arm vacuous.

- **AN ADJUDICATED CALL, 2026-09-09. `atomic_write_text` KEEPS RAISING
  `UnicodeEncodeError`, AND DOES NOT BECOME FAIL-SOFT FOR A PAYLOAD THE ENCODER
  REJECTS.** Candidate A was to catch it and return `False`, matching
  `atomic_write_json`'s shape. Candidate B was to keep raising. VERDICT:
  CANDIDATE B.

  THE DECISIVE EVIDENCE WAS NOT IN FRONT OF THE MERGER WHEN THE QUESTION WAS
  FRAMED, and both citations were re-opened at their lines before this row was
  written. `tests/test_responder_broadcast_refusal.py:230`,
  `test_an_unencodable_draft_still_escapes_the_delivery_loop`, ALREADY asserts
  `pytest.raises(UnicodeError)` out of `deliver`, at line 245. Candidate A
  would have reddened it. Independently and about a different guard,
  `tools/moon_sync_responder.py:975` records "Loud-to-quiet is strictly worse
  than the silent abort". Two authors reached the same posture by two routes.

  RESIDUAL APPLIED RATHER THAN FILED. The module docstring claimed "Everything
  here is fail-soft", a sentence the ruling made measurably false. It is now
  scoped to OS-LEVEL failure and states that a payload the ENCODER refuses is a
  programmer error that propagates untouched, and it cites the pinning arm by
  node id rather than by line:
  `tests/test_core_atomic_io.py::test_an_unencodable_payload_raises_rather_than_returning_false`.

  THE HONEST LIMIT, measured by a builder and recorded rather than rounded up
  into a claim: that new arm is a STATEMENT and not coverage. Widening the
  clause to `except (OSError, UnicodeEncodeError)` already reddens 3 arms
  WITHOUT it, so the arm pins the intent and is not what would catch the
  regression.

- **AN ADJUDICATED CALL, 2026-09-09. THE HEADLESS LOOP'S HALT BOUNDARY IS
  MIXED, AND NEITHER CANDIDATE WON OUTRIGHT.** `CLAUDE.md` carries the standing
  rule; THIS entry carries the reasoning, and `CLAUDE.md` points at it BY
  HEADING. Do not cite it by line number - a line number in this file decays on
  the next append, which is why the pointer is worded the way it is.

  CANDIDATE ARM, proposed by the counterparty repo RC: halt only at ARMING a
  scheduled task. It WON FIDELITY. "Include the other projects" is an active
  verb naming the moment another project must ACT, and the same operator
  message says "keep main session quiet and clear", which penalises any
  boundary that pings on every push.

  CANDIDATE BYTE, proposed by an adversary in this tree: halt before any byte
  leaves the working tree. It WON COMPLETENESS and REVERSIBILITY and was
  FATALLY WORDED. As literally written it halts on EVERY push, including a
  docs-only one. That is fatal to the wording and not to the principle, which
  is why the ruling below keeps the principle and discards the wording.

  THE OPERATIVE RULING, and this is the text a loop must actually encode. Halt
  and ping before: (a) any write, delete, unlink or named-kernel-object
  acquisition whose target path or namespace is OUTSIDE this repo root -
  explicitly the machine-wide slot bucket under `C:\ProgramData` and the
  `Global\` mutex namespace; (b) any commit or push whose diff touches
  `ops/loop/slots.py` or `ops/loop/winmutex.py`, or that trips the sibling-name
  sweep; (c) any arming, agreement, or behaviour change in another party's
  tree. And explicitly NOT before an ordinary push that passes both suites and
  the sibling-name sweep with `RESIN_SKIP_PREPUSH` unset.

  THE INDEPENDENT CORROBORATION IS THE STRONGEST THING IN THIS ROW, AND IT WAS
  WRITTEN BEFORE THE ARGUMENT EXISTED. The gitignored per-host file
  ops/moon_sync_repos.json - deliberately not backticked, because a backticked
  path in a governing doc must be git-tracked and this one is not - whose
  `generated` field reads `2026-09-07`, carries a block named
  `functional_literals_that_must_not_be_renamed`. It names `lw-loop`,
  `ops/loop/slots.py` and `ops/loop/winmutex.py`, and says of the first that
  renaming it from one side "silently un-serialises every loop that has not
  moved, so it is a joint round with every carrier in the same window - never a
  scrub side effect", and of `ops/loop/winmutex.py` that its one sibling
  initial "needs a joint round, not a unilateral edit". That is clause (b),
  reached by a different route two days before the adjudication. VERIFIED HERE
  by opening the block. NOTE WHAT THAT COSTS: git check-ignore -v on that path
  resolves to `.gitignore:125`, so the file is untracked and NO GUARD IN THIS
  TREE WATCHES IT. It is corroboration, not a guard - and the docs-consistency
  sweep proved the point on this very row by refusing the backticks.

  RESIDUAL, UNRULED, AND THE OPERATOR HAS NOT DECIDED IT: THE NO-ANSWER RULE.
  Three of the five participants are on ORDERED STANDBY and cannot reply, so a
  bilateral arming agreement under clause (c) is unreachable by construction.
  The proposed shape, recorded as PROPOSED and NOT ADOPTED, is a timeout plus
  default-deny: park the item, record STANDBY and explicitly NOT DISSENT, and
  continue the unblocked work. Nothing in the tree implements this and nothing
  should, until it is ruled. **WITHDRAWN LATER THE SAME DAY - SEE THE APPENDED
  PARAGRAPHS BELOW. The timeout-plus-default-deny shape is no longer proposed.
  It is left standing here, struck rather than deleted, so a later reader sees
  the change of position and not only the outcome.**

  APPENDED 2026-09-09 AFTER THE COUNTERPARTY ANSWERED. RC's operator ADOPTED
  this boundary. The ARMING candidate is WITHDRAWN BY ITS OWN AUTHOR, which is
  the strongest disposition it could have got, since RC offered it for
  refutation and it was refuted. RC's note is
  `moon_sync_inbox/2026-09-09-2030-from-RC-ADOPTED-halt-before-any-byte-leaves-the-tree-and-your-seventh-seam-is-re-derived-here.md`.

  RC'S ADOPTED FORM IS STRICTER THAN THIS ONE IN ONE DIRECTION AND CARRIES ONE
  NAMED EXCEPTION. Stricter: it binds EVERY RC session, an attended one as much
  as a loop, rather than only an unattended loop. The exception: a push to RC's
  OWN origin stays PRE-AUTHORISED, because that was already a standing operator
  instruction in RC's tree.

  RSC'S POSITION ON THAT EXCEPTION, STATED AS AN OPEN DISAGREEMENT AND NOT AS A
  SETTLED THING. That exception IS seam (f). Seam (f) was never about pushing to
  a foreign remote; it is about a tree's own public remote publishing
  sibling-identifying bytes irreversibly. A carve-out naming exactly the act the
  seam names removes the seam rather than narrowing it. THE REPAIR RSC OFFERED
  IS TO GATE THE DIFF CONTENT AND NOT THE DESTINATION, which is what clause (b)
  above already does - and clause (b) was adjudicated here BEFORE RC's carve-out
  was known, so it is not a rebuttal built to fit. RSC has not read RC's tree and
  cannot say whether a content rule is cheap there; the offer is a better shape,
  not a solved problem. RSC's reply is
  `moon_sync_inbox/2026-09-09-2100-from-RSC-your-push-carve-out-is-seam-f-and-the-repair-is-to-gate-the-diff-not-the-destination.md`.

  THE UNRULED RESIDUAL IS NOW ANSWERED ON ONE SIDE, AND THE ANSWER IS ADOPTED
  HERE: **NO TIMEOUT. HALT AND WAIT.** RC answered that its loop does not
  proceed after a delay, and RSC adopts it. A bilateral rule that auto-proceeds
  is a unilateral rule with extra steps. RSC changed position and RC did not,
  and that is the part a later reader needs.

- **SUPERSEDED 2026-09-09 - STEP THREE HAS SHIPPED AND IS CLOSED IN THE ROW AT
  THE TOP OF THIS SECTION. LEFT STANDING RATHER THAN DELETED, SO A LATER READER
  SEES THE POSITION AND NOT ONLY THE OUTCOME. STEP THREE OF THE GATE CENSUS IS
  NOT THE REGISTRY THE EARLIER BRIEF ASKED FOR.** A planner refuted that brief with measurements
  rather than with an opinion, and the refutation held. Its figures, recorded
  as THE PLANNER'S readings of 2026-09-09 and not re-derived in this row: 13 of
  17 adjacent gate-name swaps leave the census GREEN, and rotating all 18 names
  leaves every problem list empty. One figure IS re-derived here, by
  `grep -o '_line_of_tag_named("[a-z0-9-]*")' tests/test_responder_gate_census.py`
  piped to `sort -u | wc -l`, which returns 3 against a `_FLOOR` of 18: only
  `counterparty-agreement`, `delivery-write-all` and `hop-budget` are bound to
  a site at all, and all three by accident, through `_line_of_tag_named` in
  arms that wanted a line number for another purpose.

  A NAME-LIST REGISTRY WOULD MAKE THINGS WORSE. It would duplicate the coverage
  arm's set equality and add a SECOND hand-typed count beside `_FLOOR`, which
  is the exact failure class this session logged three times. THE RIGHT
  ARTIFACT IS A NAME-TO-SITE BINDING TABLE, closing CEILING item 1, naming.

  THE TRAP THAT MUST REACH THE NEXT SESSION, and it is the reason this row
  exists rather than a one-line backlog item. 34 of 35 mutants DESTROY THEIR
  OWN ANCHOR. A binding table shipped as a test module therefore becomes a
  THIRD SHAPE GRADER, reporting 34 syntax reddenings as KILLED at exit 0 - and
  `verify_exclusions` in `tools/gate_mutation_runner.py` is BLIND to it,
  because it iterates the DECLARED list only and a module nobody declared is
  never checked at all.

  THE TWO EXISTING EXCLUSIONS HAVE TWO DIFFERENT REASONS AND MUST NOT BE
  MERGED. `SELF_TEST_MODULE`, `tests/test_gate_mutation_runner.py`, is excluded
  because it decides its own verdict. `SHAPE_GRADER_MODULES`, currently
  `tests/test_responder_gate_census.py`, is excluded because it grades the
  TARGET FILE'S SHAPE, which is a syntax question, where the runner is asking a
  behaviour one. Same exclusion, different arguments; collapsing them loses the
  test that tells a future module which bucket it is in.

  THE ANCHOR PROPOSAL AND ITS FAILURE MODE, stated honestly rather than sold. A
  hand-typed substring is required to be PRESENT and UNIQUE inside `_run_once`
  for each of the 18 names, and all 18 are unique there today. It DECAYS when a
  statement is rewritten, and the repair temptation at that moment is to TRIM
  THE ANCHOR UNTIL IT MATCHES again - which is the widening this tree has lost
  to three times, and the reason the decay must fail loudly instead.

  THE SIX-SLICE DECOMPOSITION THE PLANNER PRODUCED IS IN A SCRATCH SPEC UNDER
  the session temp directory and WILL NOT SURVIVE. It must be re-derived. Do
  not cite a path under `Temp` as if it were durable; it is not, and a row that
  did would be worse than this one.

  WHICH OF THIS ROW'S FIGURES SURVIVED RE-MEASUREMENT, checked at `68a189f` and
  not taken on trust. The 13-of-17 adjacent-swap figure REPRODUCED EXACTLY. The
  3-of-18 figure is a real count of a real population - the unique literal
  arguments to `_line_of_tag_named` - but it is NOT the bound-to-a-site
  population this row used it as, which is four under an isolating swap and one
  under the strictest reading. The rotation figure did not reproduce as a claim
  about the module. All three are set out in the closed row above.

- **CLOSED 2026-09-09. A PROSE CLAIM IN THE GATE CENSUS DECAYED AND NOTHING
  WATCHED IT.** `tests/test_responder_gate_census.py` claimed 18 tags "all of
  them in the responder and none anywhere else". The first half still holds -
  re-derived here with a `tokenize` pass over `tools/moon_sync_responder.py`
  against `_GATE_STRICT`, which returns 18. THE SECOND HALF HAS BEEN FALSE
  SINCE `06f8557`, which shipped `tests/test_responder_delivery_gates.py`
  carrying a section-banner tag at its line 272 with no instrument watching.
  False by DECAY rather than by error: it was true when it was written.

  A BUILDER CORRECTED THE MERGER TWICE ON THIS ROW AND BOTH CORRECTIONS ARE THE
  ROW'S REAL CONTENT. First, only that ONE site is strict-grammar. The other
  banners in that file carry trailing prose and therefore fail the `$` anchor
  in `_GATE_STRICT`, so a row claiming a set of strict sites would have been
  over-broad. Second, the tag-shaped text in the runner's own self-test is
  STRING-LITERAL FIXTURE DATA fed to the matcher, which is a different case
  entirely - a `tokenize` pass distinguishes it by token type and a text grep
  cannot.

  THE REPAIR IS AN ARM THAT DERIVES THE POPULATION RATHER THAN ASSERTING IT.
  It enumerates from `git ls-files`, reads `tokenize.COMMENT` tokens, and
  asserts a dict BY EQUALITY, with four in-arm floors, so a tag appearing in
  any new tracked file reddens it by name and line. Written RED FIRST against
  the old claim, and probed red a second time by appending a runtime-built tag
  to another tracked file on a scratch copy.

- **OPEN, AND IT IS ABOUT THE CHANNEL RATHER THAN ABOUT THE CODE.**
  `moon_sync_inbox` IS GITIGNORED WHOLESALE. Both figures re-derived here:
  `git check-ignore -v moon_sync_inbox` resolves to `.gitignore:115`, and
  `git ls-files moon_sync_inbox | wc -l` returns 0.

  STATE THE MECHANISM AND NOT THE SLOGAN. The glyph gate, the licence gate, the
  line-ending gate and the docs guards all DERIVE THEIR CORPUS FROM
  `git ls-files`, so an untracked path is outside their reach BY CONSTRUCTION.
  It follows that every green gate cited on either side of that channel, about
  any note inbound or outbound, is green about the TREE and says nothing about
  the NOTE. What does NOT follow, and must not be written, is the universal "no
  guard reads it" - that is a claim about every guard that exists, and it is
  not checkable.

- **OPEN, AND IT IS THIS SESSION'S OWN METHOD RESULT RATHER THAN A DEFECT IN
  THE TREE. THE HAND-TYPED COUNT CLASS FIRED THREE TIMES IN ONE SESSION, AND AN
  ADVERSARIAL PASS REPRODUCED THE ERROR INSTEAD OF CATCHING IT.** An outbound
  note's prose said an adversarial sweep "found six" while the note's own
  enumeration ran to SEVEN lettered headings. A prose-truth adversary grading
  that note INHERITED the six from the summary sentence rather than counting
  the headings underneath it. And a governing-document sentence said "five",
  which was a THIRD population altogether - the adjudicator's list of what one
  candidate failed to cover. Three numbers, one list, and the disagreement was
  never a disagreement about arithmetic.

  THE RULE ADOPTED, and it is the payload of this row. WHEN A DOCUMENT STATES A
  COUNT AND ALSO ENUMERATES THE THING COUNTED, THE ENUMERATION IS THE SOURCE
  AND THE SENTENCE IS A CLAIM ABOUT IT. Grade the sentence against the list,
  never the list against the sentence. And every such sentence must NAME THE
  POPULATION IT COUNTS: whose enumeration, of what, measured when. A count with
  no population attached cannot be checked and cannot be wrong, which is why it
  keeps surviving review.

- **CLOSED 2026-09-09. CI WENT RED ON A TEST THAT DECAYED, AND THE LANE SPLIT
  WAS A TIMEZONE.** GitHub run 34405450182 failed at 21:11:41Z on
  `tests/test_task_liveness.py:836`, `assert "LIVE" in out`, while the same
  commit was GREEN here. Nothing regressed - time passed. `liveness.main` calls
  `verdict(parse_facts(...))` with NO `now`, and `verdict` at
  `ops/check_task_liveness.py:388` falls back to `dt.datetime.now()`, so five
  arms were graded against the REAL CLOCK while every `_verdict` sibling pins
  `now=NOW`. The boundary `2026-09-09T21:00:00` is NAIVE, so it is read in the
  runner's LOCAL zone: expired at 21:00 UTC on CI, five hours later here.

  DIFF THE CLOCK BEFORE THE ENVIRONMENT. Green-here-red-on-CI at one commit
  reads as a platform difference and was not one.

  FIXED IN THE ARMS, NOT THE CHECKER. `ops/check_task_liveness.py` is
  byte-identical - `verdict` already offers `now=`, and adding a parameter to
  the kill-switch checker for the tests' benefit would be worse. Five arms now
  pin the clock through a shim, and the CI failure is an ASSERTED TRANSITION -
  a sibling arm pins one second past the same boundary and requires DORMANT.

  MEASURED, and the refuter built its own instrument rather than the builder's:
  pre-fix bytes under `TZ=UTC0` reproduce the CI red byte-exact, post-fix are
  green, both re-confirmed on CI's Python 3.11. The file is green at a stdlib
  clock shift of -20000 to +40000 days, and the whole suite is green at UTC,
  UTC+14 and UTC-12. Baseline moved 1855 to 1859 on four new arms.

  TWO LIMITS RECORDED IN THE FILE RATHER THAN FIXED. The teardown arm is
  VACUOUS IN ISOLATION - run alone it passes with nothing frozen before it, and
  it has content only because file order puts it after a frozen arm. And the
  root cause is closed in the test only: `main` still never threads `now` into
  `verdict`, so any future caller of `main` is non-deterministic at that seam.

  ONE SITE FLAGGED AND DELIBERATELY NOT EDITED, for a later reading: a comment
  says "StopAtDurationEnd applies", a scheduler field the payload does not
  carry and the checker never reads. It is domain rationale rather than a claim
  about a branch, so it fell outside the defect class being repaired.

- **STATE AS MEASURED 2026-09-09 AT `d3af1b9`, a reading and not a promise.**
  `python -m pytest tests` 1855 passed 1 skipped. `agents/pity_engine` 80
  passed. `node --test` 52 pass 0 fail. ruff, mypy at 34 source files,
  qa_companion 16 passed 0 failed, licence posture 47, docs consistency 29 and
  the headless dry run all exit 0. `tests/test_responder_delivery_gates.py` is
  new at 8 arms and `tests/test_responder_refusal_gates.py` at 7.
  1840 plus 8 plus 7 is 1855 and the arithmetic closes.

  THE GATE CAMPAIGN IS 35 OF 35 FOR THE FIRST TIME. Measured at `06f8557` in an
  isolated worktree: 35 mutants, 35 KILLED, 0 SURVIVED, 0 false kills, exit 0,
  where `1c596e3` had 8 survivors. `d3af1b9` moved docstring bytes only, and
  its three refusal gates were re-run there to prove it - 6 mutants, 6 killed,
  0 survived, 0 false kills. Six false prose claims were corrected across three
  rounds on the way, every one found by a lens and re-derived by hand.

  THE SAME SUITE REPORTS A DIFFERENT SKIP COUNT UNDER THE PRE-PUSH HOOK, and
  it is NOT a regression. Measured at `9be52cc`: 1840 passed 1 skipped from an
  ordinary shell, 1839 passed 2 SKIPPED under pre-push, same commit, seconds
  apart. The extra skip is `tests/test_hook_interpreter.py:1802` - under the
  hook, git is invoked as the git-core shim at
  `Git\mingw64\libexec\git-core\git.exe`, which sits at no layout that oracle
  recognises as an install, so it SKIPS rather than guessing. That is the arm
  behaving correctly on a lane its author anticipated. Do not reconcile the two
  counts by editing either one; they are two environments and the skip reason
  says which.

  **STEP TWO OF THREE OF THE GATE CENSUS IS DONE, AND ITS SURVIVORS ARE NOW
  CLOSED.** `tools/gate_mutation_runner.py` consumes the 18 tags, neutralises
  each tagged consult site in `_run_once`, and runs the application suite per
  mutant. The result at `1c596e3` was 35 mutants, 27 KILLED, 8 SURVIVED, exit
  1. STANDING RESULT NOW, measured at `06f8557` in an isolated worktree: 35
  mutants, 35 KILLED, 0 SURVIVED, 0 false kills, exit 0. The REGISTRY is step
  three and is still unstarted; building companions before it ships a
  VACUOUSLY GREEN apparatus, so the order stays strictly sequential.

  WHAT THIS SESSION DID NOT TOUCH, so the next one does not re-derive it: the
  registry, nothing inspects the pre-push hook's OUTPUT, the sweep floor's VALUE
  is still ungraded, and `ops/ResinCompute-Supervisor.xml` has still never been
  registered. `core/atomic_io.py` still leaks a 0-byte temp on a non-OSError
  write failure - filed, not fixed, and not a regression. The responder task was
  re-confirmed DORMANT by the checker, exit 1, and NOTHING WAS ARMED. The inbox
  was re-measured at zero unread and ZERO subdirectories, 146 files.

  THE WORKTREE TRAP FIRED ON FOUR OF FIVE DISPATCHES. A worktree here
  materialises at an ANCESTOR of the declared fork point. One builder STOPPED
  and wrote nothing rather than re-deriving its target from the brief's prose,
  which was the right call and cost only a re-dispatch. The fix that worked is
  an explicit `git merge --ff-only <sha>` in the brief PLUS an assertion on the
  materialised bytes - a line count and a grep for a symbol that only exists at
  the intended commit. A dispatch that omits it is the defect rather than the
  builder, which is the third session running for that lesson.

  FOUR TIMES AN AGENT CORRECTED THE INSTRUCTION IT WAS GIVEN, and that is the
  method result worth keeping. One measured that the brief's k = 1, 2, 3 does
  NOT kill `reported[:3]` and added the arm the brief had not asked for. One
  declined to ship a refuter's measurement it could not reproduce and shipped
  the weaker verified claim. One derived a disputed count itself and disagreed
  with both the refuter and the earlier builder. WHEN A REFUTER SAYS A BUILDER
  WAS WRONG, CHECK WHO WROTE THE INSTRUCTION FIRST.

- **CLOSED 2026-09-09. THE EIGHT GATES EXERCISED BY NOTHING NOW HAVE ARMS, AND
  THE CAMPAIGN IS 35 OF 35.** Measured at `06f8557` by
  `python -m tools.gate_mutation_runner` in an isolated worktree: 35 mutants,
  35 KILLED, 0 SURVIVED, 0 false kills, exit 0. The eight that survived at
  `1c596e3` are each now killed by one of two new modules -
  `tests/test_responder_delivery_gates.py` at 8 arms takes
  `delivery-write-all/operand-1` and `operand-2`,
  `bounce-write-all/operand-1` and `operand-2`, and `bounce-mark/if-true`;
  `tests/test_responder_refusal_gates.py` at 7 arms takes
  `no-destination/if-false`, `workspace-trust/if-false` and
  `refusal-recorded/if-false`. Not one kill is named by a shape grader.

  THE EMPTY-LIST HALF IS NOT REACHABLE THROUGH REAL DESTINATIONS, and that is
  a STATED limit rather than a hidden one. `deliver` returns exactly one row
  per inbox and `_run_once` reaches the delivery step only past the
  `GATE:no-destination` early return, so `written` is never `[]` there. The
  `bool(written)` term that the responder's own comment at
  `tools/moon_sync_responder.py:1861-1863` calls the guard and not decoration
  therefore guards a caller shape the current callers cannot produce, and the
  two arms that drive it substitute the module's `deliver`.

  TWO ARMS SHIPPED VACUOUS AND A LENS CAUGHT THEM, NOT THE RUNNER. With
  `GATE:bounce-once` neutralised so the bounce block ran ZERO times, both
  bounce arms stayed GREEN on negatives alone -
  `result["termination"] == "refused"` is assigned 60 lines above the block.
  The repair puts a `len(attempts) == 1` floor IN THE SAME ARM, fed by a
  wrapper that captures the module's own `deliver` before substituting and
  calls through, so the real failing write still happens. Both arms then go RED
  under that neutralisation and under four more. A FLOOR IN A SEPARATE ARM
  WOULD HAVE LEFT THE PRIMARY ARM VACUOUS, which is why it is one assertion.

  KNOWN LIMIT, recorded rather than fixed: `rc_inbox in handed[0]` is a
  MEMBERSHIP test, so an extra destination appended to the list the module
  computes leaves the arm green. Both files say so where a reader will find it.

- **CLOSED 2026-09-09, AND THE DISPOSITION IS AN ADJUDICATED CALL - NOT AN
  OPERATOR DECISION.** It is overturnable by reading this entry. The sentence
  in `tests/test_responder_refusal_gates.py` reading "Every suppression
  downstream is keyed on that record" has TWO live antecedents in its own
  paragraph: the refusals FILE, which makes it true, and what
  `_remember_refusal` writes, which makes it false. Nearest-antecedent
  resolution steers the reader to the false one, and the correcting text sits
  ten lines further down.

  The adjudicator restated the criteria before reading the artifact - truth
  outranks minimal change, and no assertion may move - then verified the true
  reading in the responder rather than in the docstring three prior agents had
  all read: `refusal_seen` at line 1359 reads the `refusals` rows,
  `bounced_under` at 1405 reads the `bounced` ledger and says so itself,
  `bounce_capacity` at 1417 reads the same ledger, and all key on the one path
  `DEFAULT_REFUSALS` written by the single writer `_write_refusals` at 1345.

  RULING: B, FIX NOW. A claim repaired ten lines later is not checkable at the
  point it is made. RUNNER-UP was A, leave as is, on the argument that a reader
  who finishes the docstring cannot end up wrong. Shipped at `d3af1b9`,
  docstring bytes only.

  THE SAME ADJUDICATION RULED A, NOTHING TO FIX, on the two figures that looked
  like a contradiction. They are different populations and reconcile exactly:
  `tests` collects 1848 at `f92500f`, the two `EXCLUDED_MODULES` collect 124,
  `tests/test_responder_refusal_gates.py` collects 7, and 1848 minus 124 minus
  7 is 1717. So 2 failed plus 1845 passed plus 1 skipped is the full suite with
  the file present, and 1716 passed plus 1 skipped is the campaign suite with
  it absent. Both numbers already carry their population in the prose.

- **OPEN, and it is a REAL defect in the responder rather than in a test.**
  Measured 2026-09-09 while building the `no-destination` arm: with the gate
  neutralised and `roots={}` the cycle spawns a session, terminates
  "delivered", writes a reply into THIS repo's own inbox, and writes the note
  into `DEFAULT_ANSWERED`. `_remember_answered` is union-only and uncapped and
  NOTHING in `tools/`, `scripts/` or `ops/` ever removes an entry, so a retry
  after the roots are configured terminates "empty" - the note can never be
  answered. The gate currently prevents that, and the gate is now armed, so
  this is not reachable today. It is recorded because the answered record's
  permanence is a property nothing else in the tree states.

- **OPEN, small, and named by the adjudicator as out of its own scope.** The
  assert message in `test_a_refusal_whose_record_write_fails_delivers_no_bounce`
  still says a bounce whose record did not land "goes out again on every cycle
  forever". The docstring twelve lines above it now measures ONE bounce, not
  one per cycle, because `mark_bounced` is unpatched and `bounced_under`
  suppresses the repeats. Criterion three of that adjudication forbade touching
  an assertion, so the message was left. It is a message, not a predicate, so
  nothing is green that should be red.

- **OPEN, and it is a question about the CAMPAIGN POPULATION rather than a
  defect.** The two new modules add 15 arms that no prior campaign figure
  includes, and neither is excluded. That is correct as it stands - they grade
  BEHAVIOUR, not the target file's shape, which is what `SHAPE_GRADER_MODULES`
  is for - but the survivorship figures quoted in older entries were taken
  against a smaller population and do not transfer. Re-derive rather than
  compare.

- **CLOSED 2026-09-09, AND THE DISPOSITION IS AN ADJUDICATED CALL - NOT AN
  OPERATOR DECISION.** It is overturnable by reading this entry. The question
  carried by four hand-offs was that NOTHING compared INSTALLED dev tools
  against DECLARED pins, and that a naive equality test would be GREEN on CI
  and RED here, which is backwards. The SHAPE was the open question, not the
  typing.

  MEASURED FIRST, and every figure re-probed by two agents independently:
  `requirements-dev.txt` pins exactly three tools, all with `==`. Installed on
  this box - ruff 0.15.12, pytest 9.0.3, mypy 2.1.0, all OLDER than the pins.
  Both workflows `pip install -r requirements-dev.txt` on ubuntu-latest at
  Python 3.11, so CI is AT the pin BY CONSTRUCTION. That is why equality is
  near-vacuous where it is green: it would assert that pip works, ninety
  seconds after pip ran.

  RULING: MIXED, and both halves shipped. The criteria, in the order used:
  what the mechanism can CLAIM on BOTH lanes; truthfulness of the disposition;
  feasibility as measured; blast radius, since a guard that only ever reddens
  locally is a guard the operator disables; loudness of a future regression;
  and non-vacuity. REJECTED: assert-equality, assert-floor, skip-off-CI, and
  do-nothing. Skip-off-CI lost on the tree's own hard-won finding that a SKIP
  is exactly how a red hid for five pushes.

  PART D, `tests/test_dev_pin_declaration.py`: a claim about the DECLARATION -
  every tool the gates INVOKE is PINNED - which is host-independent and true on
  both lanes, with the anti-vacuity floor and the judgement in ONE assertion.
  PART C, `scripts/qa_companion.py`: a non-failing NOTE row per tool reporting
  the drift AND ITS DIRECTION, because "differs" alone does not tell a reader
  whether a local green is optimistic or pessimistic. It is exit-0 on both
  lanes and appears in the gate output the operator already reads.

  THE FIRST BUILD WAS REFUTED WITH TWO FALSE GREENS, and the first of them
  defeated the very reason part D was chosen over doing nothing.
  FALSE GREEN ONE: the invoked-tool set was derived by looking up a CLOSED dict
  of the three known names, so a fourth unpinned tool could never appear in it
  and the equality was structurally satisfied. MEASURED: adding two unpinned
  tools to a workflow left the test GREEN, while the module's own name promised
  "every tool the CI gates invoke". The ruling had justified D by saying only D
  would redden for a fourth unpinned tool - so as first shipped, D could not
  make the one claim it was selected for.
  FALSE GREEN TWO: trailing comments were not stripped, so rewriting a gate as
  `echo lint step deleted  # ruff check .` - with ruff no longer invoked at all
  - kept the guard green. A comment could satisfy it.

  THE REPAIR INVERTS THE POLARITY, and that is the load-bearing decision. The
  allow-lists now name what is NOT a tool, and an UNKNOWN word IS a tool, so a
  new unpinned tool is caught by DEFAULT rather than by being anticipated. A
  shape the scanner cannot classify RAISES and names the file and line, rather
  than being quietly skipped - this tree has twice been defeated by widening a
  matcher, and the standing lesson is that an unparseable shape must FAIL.

  THE CEILING IS STATED HERE AND IN THE FAILURE MESSAGE rather than discovered
  later. Invocation by path, through a variable, from inside a shell script, or
  as `python -m dotted.module` is NOT credited, which leaves the invoked set
  short and is caught by the floor. And adding an ordinary new shell utility to
  a workflow REDDENS this module until that word joins the shell-word list -
  a deliberate false red, and the message says so. The floor's message was
  separately repaired: retiring a tool used to print two IDENTICAL lists under
  an equality-shaped assert, and now names the floor and asks for a same-commit
  constant update.

  ALSO REPAIRED, and it was a live staleness rather than a hypothetical: the
  stop-claim gate's fixture still pinned the DEAD three-word tally line after
  the reporter began emitting a fourth count. A new arm reads the emitter's own
  format out of the script and compares WORD SEQUENCES, so the fixture cannot
  drift again. Its ceiling, stated honestly: it compares the count WORDS and
  not the numbers, which differ per host, so it cannot see the two being wrong
  together in the same way.

  WHAT WOULD OVERTURN THIS: bringing this box to the pins, which makes plain
  equality cheap and true and demotes part C to noise. Or a measured case where
  the version drift caused a real local-green-with-CI-red, which promotes part
  C from a report to an assertion.

  THEN A THIRD REFUTER DEFEATED IT AGAIN, and the third defeat is the most
  instructive of the three because the module had WRITTEN DOWN a false claim
  about its own limits.
  FALSE GREEN THREE: a QUOTED YAML scalar hid the command entirely.
  `run: "pip-audit --strict"` derived the empty set, as did the single-quoted
  form and a leading `!`. A quoted scalar is ordinary valid workflow YAML and
  is MANDATORY when a command opens with a YAML-reserved character, so an
  unpinned tool added that way stayed invisible. Meanwhile the docstring
  asserted that a GitHub expression "is the one shape that could hide a tool
  name silently". That sentence was measured FALSE and is deleted, with the
  measurement recorded in its place.
  THE REPAIR IS A MISSING PARSE STEP, NOT A WIDER MATCHER, and the distinction
  was made deliberately: a quoted scalar is now unwrapped at the YAML level
  BEFORE the shell scan runs, and the shell heuristic is untouched. Malformed
  or unterminated quoting RAISES and names file and line rather than guessing.
  This tree has been defeated three times on this one derivation and its
  standing lesson is that widening a matcher is the wrong answer after the
  second defeat - so the answer here was to parse the input correctly and to
  let an unparseable shape FAIL.
  THE WORKFLOW SET WAS ALSO HARDCODED to two filenames, so a THIRD workflow
  would have been entirely ungraded, and that was not in the stated ceiling. It
  is now enumerated from disk with the census floor welded into both consuming
  assertions.
  AND A COMMITTED ARTIFACT CARRIED A FALSE PROVENANCE COMMENT. The tally
  fixture claimed to be COPIED VERBATIM from the script on 2026-09-09 while the
  script on this box prints different numbers. The counts are HOST-DEPENDENT -
  the reporter probes a listening port, an Electron runtime, a desktop shortcut
  and an account snapshot - so no verbatim capture can stay true. It is now
  labelled a SHAPE fixture with illustrative numbers, and the companion arm was
  RENAMED to say it pins the count WORDS IN ORDER and claims nothing about the
  numbers, because the refuter killed nothing by swapping the passed and failed
  placeholders. The mechanism overclaiming was the defect, not the mechanism.

  MUTATION TABLE AT THE MERGE, control GREEN and all five arms RED: an unpinned
  tool added as a double-quoted, single-quoted or plain scalar; a pin removed
  while the gate still invokes it; and every workflow file removed so the
  enumeration is empty, which reddens the floor rather than passing over zero
  files.

  THE CEILING, STATED IN SIX NUMBERED ITEMS in the module rather than
  discovered later. A tool is credited only when its BARE NAME stands in
  COMMAND POSITION in workflow text. Not seen: invocation by path or glob,
  invocation through a shell variable, a tool run from inside a script or
  composite action the workflow merely calls, `python -m dotted.module`,
  `python foo.py`, and a tool in ARGUMENT position - `xargs -0 ruff check` is
  deliberately uncredited, because deciding argument position from text needs a
  per-tool table of which arguments are commands, which is precisely the closed
  dict this module removed. All six leave the invoked set empty or short and
  are caught by the floor.

  THE COMMON-MODE RISK IS NAMED RATHER THAN LEFT IMPLIED, in the module
  docstring and here: both halves read `requirements-dev.txt` as truth about
  what CI installs, and assert that the install happens only by reading the
  workflow TEXT. No runner was ever observed. A cached wheel or a later
  upgrade step would be invisible to both.

- **CLOSED 2026-09-09, AND THIS IS AN ADJUDICATED CALL THAT OVERTURNS A
  PREVIOUS ADJUDICATED CALL FOR EXACTLY ONE SITE. NOT AN OPERATOR DECISION.**
  It is overturnable by reading this entry. The standing ruling recorded below
  is DO NOT WIDEN, all eight OSError-only sites. SEVEN OF THE EIGHT STAND
  UNCHANGED. The eighth, the delivery loop in `tools/moon_sync_responder.py`,
  is overturned, and the overturn condition is the one the original ruling
  NAMED for itself: a Path built from parsed JSON reaching one of the eight.
  MEASURED, not argued - `DEFAULT_ROOTS_CONFIG` names a repos JSON file under
  the ops directory, the payload is read and its values become Paths, and those
  Paths reach the delivery loop through the roots loader. Reachability at that
  site is therefore ONE of eight, not zero, and the ruling's own stated door is
  open. That config file is deliberately NOT backticked here and is deliberately
  UNTRACKED - it carries machine-local sibling paths - which sharpens the point
  rather than weakening it: the Path is built at runtime from a payload no
  reviewer of this repository ever sees.

  WHAT SHIPPED. A private `_DraftRefused(ValueError)` raised for the draft
  refusal ABOVE the loop, so a refused draft and a malformed path are now
  distinct TYPES rather than one signal doing two jobs - which is the
  prerequisite the original ruling named and the reason it said widening could
  not fix this alone. The loop then absorbs `(OSError, ValueError)` and appends
  its `(False, target)` row, so a broadcast no longer aborts mid-loop leaving
  some inboxes written and no record. Measured before and after on two inboxes
  with the first malformed: the second inbox goes from unwritten to written.

  THE PATH TO THIS RULING IS THE ENTRY, because the first attempt was REFUTED
  BY BOTH INDEPENDENT REFUTERS, on DIFFERENT grounds rather than a shared one.

  REFUTATION ONE, scope lens: the builder widened a site the record forbade
  widening, on its own authority, while ROADMAP and LEDGER still said DO NOT
  WIDEN. A prerequisite is not a permission. That is why this entry exists at
  all - the fix is defensible but performing the overturn SILENTLY was not, and
  the cure is writing it down rather than reverting.

  REFUTATION TWO, correctness lens, and it is the one that made the first
  attempt genuinely unmergeable: `UnicodeEncodeError` IS a `ValueError`
  subclass. A bare `except ValueError` therefore absorbed a whole FAMILY, not
  the NUL case it was aimed at, turning a formerly LOUD encode failure into a
  plausible-looking False row with no exception and no log. Repaired with a
  TYPE test - the loop re-raises immediately when the exception is a
  `UnicodeError` - never a message match, because widening a matcher has been
  the wrong answer twice in this tree.

  AND THE THIRD MEANING IS NOW SEPARATED IN THE LOG. `(False, target)` could
  mean the target already existed, the OS refused, or the caller passed
  garbage, and callers reduce the list with `all(...)`, so a False had an
  undiagnosable third cause. Three distinct outcomes are now logged -
  `skipped-existing`, `delivery-failed-atomic-write`, and a
  `delivery-failed-<ClassName>` row for the absorbed case. The atomic-write row
  deliberately names no exception class: that layer swallowed and already
  logged it, so naming one here would be a guess written down as a record.

  TWO CORRECTIONS TO THIS SESSION'S OWN AGENTS, both measured, both worth the
  ink because each was an agent grading a claim it had not produced.
  FIRST: a refuter filed the 0-byte temp-file leak as a regression of this
  change. It is NOT - it reproduces identically on the baseline tree, and it is
  the pre-existing `core/atomic_io.py` defect filed as its own row above. What
  this change added was the SILENCE that hid it, and that half is repaired.
  SECOND: the adjudicator justified deleting a false docstring sentence by
  saying the sibling `log_invocation` was NOT widened. That is false. Verified
  against b1a3eab directly: `except (OSError, ValueError)` already existed at
  five sites in that module at baseline, one of them inside `log_invocation`.
  The deletion was still correct - the sentence named `_record_invocation`,
  which exists NOWHERE in the tree - but it was correct for the NAME and not
  for the reason given.

  WHAT WOULD OVERTURN THIS OVERTURN: proof that the roots loader's output
  cannot reach the delivery loop on any armed path - an upstream validator
  rejecting non-existent roots would restore reachability zero and put this
  site back with the other seven. Or a decision that `atomic_write_text` should
  promise never to raise, which remains an ADR and not an except clause.

  STILL UNGRADED AND HONEST ABOUT IT: the three repair arms and the `source`
  label threaded through the delivery function were added AFTER the last
  adversarial pass, so they carry the suites' green and no refuter's attention.

- **OPEN, PRE-EXISTING, AND FOUND BY A REFUTER LOOKING AT SOMETHING ELSE.**
  `core/atomic_io.py` leaks a 0-byte temp file when the write fails with
  anything that is not an `OSError`. `_discard(tmp)` at
  `core/atomic_io.py:100` sits INSIDE the `except OSError` handler, so a
  `UnicodeEncodeError` out of `tmp.write_text` - a lone surrogate in the text -
  escapes the function with the temp file still on disk. MEASURED on BOTH the
  baseline tree and a candidate, so it is NOT a regression introduced by any
  slice this session; a first reading filed it as one and was corrected by an
  adjudicator who measured both trees.

  IT IS WORTH THE ENTRY BECAUSE THE SIBLING FUNCTION IS ALREADY RIGHT AND SAYS
  SO. `atomic_write_json`'s own docstring states that serialization happens
  BEFORE the temp file is opened precisely so an unserializable object cannot
  leave a stray temp behind. The text variant has no equivalent protection and
  its docstring makes no such claim, so the two halves of one module disagree
  about a property one of them advertises.

  NOT FIXED HERE ON PURPOSE. `atomic_io.py` is the only sanctioned state-write
  path in this tree and every writer depends on it, so a change to its failure
  handling is a merge surface rather than a patch, and the ruling in flight
  above already turns on what that function does and does not promise. Whether
  `atomic_write_text` should promise never to raise is explicitly recorded
  elsewhere in this file as an ADR question rather than an except clause.

- **THE INBOX TRIAGE ADVANCED 2026-09-09 AND IS NOW COMPLETE FOR THE BACKLOG,
  which four previous hand-offs carried as PARTIAL.** All 28 unread notes were
  READ IN FULL, not listed, and every one carries a verdict in
  `docs/INBOX_TRIAGE_2026-09-09.md`. Tally: INGESTED 23, ALREADY-HAVE-AN-
  EQUIVALENT 1, NOT-APPLICABLE 2, APPLICABLE-AND-NOT-DONE 2 notes carrying 4
  items. Measured rather than assumed: 145 `.md` files and ZERO subdirectories,
  by `find -mindepth 1 -type d`, so no verbatim payload is being skipped.

  THE WATERMARK MOVED, and that is the part four hand-offs could not do. The
  watcher now reports `unread: none`. It was moved ONLY after every note had a
  verdict in a committed file and every applicable item had reached this one,
  because an inflated watermark is worse than none and reading is not
  acknowledging. The 3 withdrawn-after-being-shown entries are carried away
  with it and are accounted for in the triage file: two are this tree's OWN
  self-copies renamed after the watcher had reported them, which is the
  sender-side gap filed as item 3 below.

  THE 23 IS HIGH FOR A STATED REASON RATHER THAN A GENEROUS ONE. 22 of the 28
  were already bucketed on 2026-09-08 and their applicable rows already reached
  this file; they read as unread only because the watermark never moved. The
  convention is stated in the triage file: a note filed as an OPEN roadmap row
  counts INGESTED, and APPLICABLE-AND-NOT-DONE is reserved for content that
  reached NOTHING.

  THE FOUR ITEMS, each verified against OUR code before filing, not carried on
  a sibling's assertion. One of them, the second gate-tag census hazard, is
  filed on the gate-census row below rather than here, because it is a
  precondition of that slice.

  1. THE EVIDENCE LEDGER TRIMS RATHER THAN ROTATES.
     `tools/moon_sync_responder.py:1135` is `rows = rows[-MAX_METRICS_ROWS:]`,
     the constant at `tools/moon_sync_responder.py:322`. That DROPS the oldest
     rows outright, and a metrics row carries five distinct measurements for one
     cycle, so deleting a row deletes evidence. Our own comment above it calls
     the cap THE BACKSTOP, NOT THE FIX and then considers only suppression,
     never rotation. The repair shape offered by RC is to rotate to an archive
     with the live file replaced LAST, so every failure leaves the live file
     complete rather than short. SCOPED: the invocation log trimmed at
     `tools/moon_sync_responder.py:1207` is correct as it stands, its lines not
     being evidence rows.

  2. CHECKED AND ANSWERED 2026-09-11 - NO DIVERGENCE. The row asked for a CHECK
     rather than naming a defect, and the check was run. `record_cycle` takes
     the ledger path as a PARAMETER from five call sites, and all five pass the
     module global `DEFAULT_METRICS` verbatim. `grep -rn "DEFAULT_METRICS"` over
     `tools ops headless scripts engines core agents` returns SIX hits: the
     definition and those five arguments. THERE IS NO SECOND BINDING TO DIVERGE.
     No argparse flag sets it - none of the eight `add_argument` calls names a
     metrics or runtime path - and the registered task sets no environment, so
     it inherits `REPO_ROOT/ops/runtime`. A sibling repo shipped two plausible
     bindings and BOTH failed; that failure mode is not reachable here.

     EVERY LINE NUMBER THIS ROW ORIGINALLY CARRIED WAS STALE, five for five,
     which is why they are gone rather than corrected. It cited the definition
     at `:969` and the call sites at 1615, 1634, 1665, 1700 and 1738; measured
     at 41ba7d0 they are `:1067` and 1728, 1748, 1785, 1822, 1871 - deltas of
     +98 and +113 to +133. All five calls are inside ONE function, `_run_once`.

     AND THE LOAD-BEARING FINDING, which is not what the row went looking for:
     ZERO M1-M6 ROWS HAVE EVER BEEN WRITTEN LIVE. `responder_metrics.json`,
     `responder_answered.json` and `responder_refusals.json` are ABSENT from
     `ops/runtime/`; the only live record is `responder_invocations.log` at 48
     lines. A whole-disk census over four roots, 211694 directories walked,
     found 197 instances of those four basenames and exactly ONE live - every
     `responder_metrics.json` sits under a pytest tmp dir, and ZERO sit under
     `C:\ProgramData`. The mechanism is measured: `_run_once` returns at its
     empty-queue gate BEFORE the first `record_cycle`, and the invocation log
     decomposes exactly - 19 start-plus-`empty` pairs at five-minute boundaries
     is 38 lines, plus 10 bare `start` lines, is 48. The log's transition minute
     matches `fe53f31`, the commit that added terminal-outcome logging.

     RESIDUAL, stated so the negative is not read as wider than it is: the 10
     bare `start` lines have unrecoverable terminations, and five of them are
     off-boundary, so the live 48 is not provably 48 task fires - the `rsp`
     fixture docstring records that the suite once wrote real lines into this
     exact live log, and a leaked fixture line is indistinguishable from a
     manual dry run. The census covered four roots and says nothing about other
     drives, network paths, or any sibling tree.

  3. NOTHING GUARDS THE SENDER SIDE AGAINST EDITING A NOTE AFTER DELIVERY.
     MEASURED: the watcher reports 3 entries under WITHDRAWN after being shown
     and TWO OF THEM ARE OUR OWN self-copies, renamed after the watcher had
     already reported them. The RECEIVING side detects this; nothing on the
     SENDING side prevents or records it. It compounds with the already-filed
     finding that outbound mail leaves zero tracked trace: there is no artifact
     a sender-side check could even compare against, so the guard needs the
     trace first. RC's own framing is the transferable part - running an
     adversarial pass AFTER the irreversible act converts its findings into a
     contract violation rather than a correction.

  WHAT THE TRIAGE DECLINED TO MEASURE, stated so a gap is not read as a clean
  bill: no sibling tree was read, so every figure about a sibling's disk is
  THEIR measurement and not our verification; the slowed-pre-push reproduction
  was not run because it needs a real push; whether a SessionStart hook's stdout
  reaches the transcript on a NON-ZERO exit is still unmeasured, this tree
  holding only the adjacent exit-0 positive control.

- **CLOSED 2026-09-09, AND CLOSED BY READING THE RUN RATHER THAN BY REASONING
  ABOUT IT.** CI is GREEN at 6c6ab9d, both workflows, after SIX consecutive red
  pushes: 0aef4f4, dda913a, 460bda5, e66babb, 9d6db70 and ca59c8e. All local
  gates were green throughout, which is exactly how it stayed invisible.
  Check every session with a `gh run list` call. Four stacked defects, not the
  three the first reading found, and the fourth was only visible once the first
  had been fixed.

  DEFECT ONE, the renderer. pytest builds a phase report while a test's
  monkeypatch is STILL LIVE. Several arms force os.name to nt to reach a
  Windows-only branch, and under Python 3.11 pathlib dispatches Path on that
  flag, so on Linux the report builder's own Path of the cwd raised
  NotImplementedError and pytest died with INTERNALERROR instead of naming the
  failing test. Fixed by a makereport wrapper in the repo-root conftest, which
  holds os.name at its import-time real value while the report is built and
  puts the test's value back for teardown. Only that one hook is wrapped, and
  the reasoning for not wrapping the neighbours is in the file.

  DEFECT TWO, the test that was failing behind it. The 42 dots in the log are
  the FOURTH progress line, not the first - three full lines of 72 precede it,
  so the failing item is the 259th and not the 43rd. That is the oracle arm in
  `tests/test_hook_interpreter.py`, which constructs a Path inside the forced
  window. A first reading that put it in the roster module was arithmetic, not
  measurement, and was refuted the same hour.

  DEFECT THREE, and it was in no previous hand-off: mypy exits 1 on Linux. Four
  errors, in `tools/screen_capture.py` and in `tools/first_run_capture.py`.
  typeshed marks the two ctypes Windows surfaces win32-only, so Linux mypy
  prunes the platform guard and the binding disappears. The 2026-09-07 fix
  recorded in the second file converted attr-defined into name-defined rather
  than closing it. Both now put the import below a platform early-return so
  mypy prunes the USE as well.

  MEASURED, not reasoned: mypy takes a platform flag. Against a git archive
  extract of HEAD it reproduces CI's red exactly - the same four errors, the
  same line numbers, the same 33 files - and the fixed tree passes. Two
  builders had both filed this as unverifiable locally. It was not.

  ALSO MEASURED: a Python 3.11 interpreter is installed on this box and is
  reachable through the py launcher. The dispatch is demonstrable locally in
  mirror polarity, forcing posix on a Windows host. Earlier sessions assumed no
  3.11 was available.

  THIS IS AN ADJUDICATED CALL AND NOT AN OPERATOR DECISION. It can be
  overturned by reading this paragraph. The question was how to repair the arms
  that force os.name. Position A was to skip them off Windows; position B was
  to make them pathlib-safe and keep them running everywhere. The criteria, in
  priority order, were truthfulness of the disposition, what the mechanism can
  still claim, feasibility as MEASURED rather than argued, blast radius, and
  whether a future regression is loud. RULING: MIXED. The four nt-forcing sites
  in `tests/test_hook_gate.py` change NOT AT ALL - they patch the subprocess
  call to a non-zero return or an OSError, so the classifier returns before it
  builds a Path, and CI corroborates it by passing all 25 of that module's
  items. The three sites in the interpreter module take position A, because B
  was measured IMPOSSIBLE there: the test-local oracle helpers construct a Path
  at four points inside the forced window. The skip reason must LEAD with the
  Windows-only branch and name pathlib second, because a reason blaming only
  pathlib is false-implying, and a skip whose stated reason names the wrong
  cause is worse than a failure. The adjudicator's own strongest objection is
  recorded and stands: a skip is exactly how this red hid for five pushes. The
  mitigation is `tests/test_nt_forcing_arms_are_guarded.py`, an AST scan with a
  seven-site non-vacuity floor in the same assertion as its judgement, so a
  future bare nt-forcing arm fails loudly.

  DEFECT FOUR, found only because defect one was fixed first. The first push
  went green on the docs workflow and the other named its one remaining
  failure: the renderability file's OWN positive control. It simulated the
  inverse by patching os.name to the literal posix, which IS the real value on
  Linux, so both of its two conditions observed the same string. On that host
  the control was not merely failing, it was INCAPABLE of separating a
  protected run from an unprotected one, and the Windows green was the accident
  rather than the Linux red. The patched value is now a runtime sentinel that
  is neither nt nor posix, so it differs from the real name on every host while
  never selecting the unsupported flavour. Patching it to nt would have
  produced the difference and reintroduced the outage.

  NOW OBSERVED RATHER THAN DERIVED. The three ruled arms are recorded above as
  skipping on Linux by derivation. The run at 6c6ab9d shows them skipping, with
  the reason leading with the Windows-only branch exactly as the ruling
  required. The mypy result is likewise confirmed on the real gate and not only
  through the platform flag.

  AND THE REASON THE FOURTH DEFECT WAS FINDABLE AT ALL IS WORTH THE ENTRY. That
  run reported 19 skips and named NONE of them, where this box reports one, so
  18 arms did not run on the machine that decides red and the log said nothing
  about which or why. All three of the workflow's pytest invocations now report
  their skips, and the 19 read as: four for an unavailable symlink privilege,
  five for the Windows Task Scheduler, two for Win32 named-mutex semantics, two
  more Windows-only interpreter arms, one opt-in network fetch, the three ruled
  arms, and two for a shallow clone. Every reason is true. The guard reuses the
  spec parser hardened at e714b35 rather than adding a second matcher, because
  a literal-flag matcher was defeated twice and widening it was the wrong answer
  both times.

  BOTH RESIDUALS ABOVE ARE CLOSED 2026-09-09, each by its own slice, each
  graded by an agent that did not write it.

  THE TRAILER RULE IS ENFORCED IN CI FOR THE FIRST TIME. Two of those 19 skips
  said `tests/test_commit_trailers.py` declines a full-history sweep under a
  shallow clone, which left the Co-Authored-By HARD RULE resting entirely on a
  hook that a fresh clone does not run. The cost of a full fetch was MEASURED
  before the change rather than assumed: 113 commits, about 7 MB of git
  objects, noise beside the pip install in the same job. The sweep also runs
  GREEN over this tree's real history, so the change could not arrive red.
  `.github/workflows/ci.yml` now checks out at depth 0 and
  `tests/test_ci_history_depth.py` reddens if it returns to a shallow value
  while that sweep still ships, with its census and its judgement in ONE
  assertion so a workflow carrying no checkout step at all cannot pass
  vacuously.

  AND THE SKIP BRANCHES WERE NOT DELETED, because a verifier refuted the claim
  that they had become dead code. `.github/workflows/docs-guards.yml`
  deliberately stays at depth 1, and its selection is DERIVED at CI time from
  every test module mentioning a markdown path - which is that module. So it is
  still collected and run SHALLOW on every docs-only push, both branches fire
  there, and both reasons are true there. The follow-up was a comment fix, not
  a deletion, and the first reading of it would have broken a lane.

  THE DOCS WORKFLOW NOW NAMES ITS SKIPS TOO. It invoked pytest twice with no
  short-summary spec, the same blind spot ci.yml carried until 6c6ab9d. Both
  invocations now pass `-rs`. The guard REUSES the spec parser hardened at
  e714b35 rather than adding a third private matcher; a literal-flag matcher
  was written and defeated twice in this tree, and widening it was the wrong
  answer both times. Its floor and its judgement are one assertion.

  THE NEW GUARD'S CEILING, stated rather than discovered later. That workflow's
  pytest targets are SHELL ARRAY EXPANSIONS and not literal paths, so the floor
  pins the operand TEXT. Renaming the arrays is therefore a FALSE RED needing a
  same-commit constant update, and the failure message says so. Measured: the
  guard does NOT degrade to a silent green when the invocations are moved into
  a script, and does not pass with the parser welded to an empty list.

  AND READING THE GREEN RUN FOUND A DEFECT THAT NO LOCAL REASONING HAD. Both
  workflows passed at ef295f2, CI skips fell 19 to 17, and none of the 17
  mentions a shallow clone - so the trailer sweep genuinely runs there now. The
  DOCS lane log then showed those same two arms still skipping, by name, with a
  reason ending "raise fetch-depth in the workflow to make this arm meaningful".
  On the only lane where that reason still fires, it is WRONG ADVICE: that lane
  is depth 1 on purpose and raising it would be a regression. A skip naming a
  fix that must not be applied is the failure this tree calls worse than a
  failure.

  THE FIRST REPAIR OF IT WAS REFUTED, and the refutation is the entry. The new
  wording dropped the words "in the workflow" and told the reader not to raise
  a fetch-depth at all, which is FALSE in a hand-made shallow clone where
  `git fetch --unshallow` is exactly the right move. Reproduced cold in a
  depth-1 clone. The repair had WIDENED the false implication rather than
  narrowing it, and it had fixed only one of the two arms sharing the root
  cause. It also asserted the docs lane skip is the CORRECT disposition, which
  overclaims: that lane selects any module MENTIONING a markdown path, and this
  module reads none, so it is collected by an over-approximating heuristic
  rather than by design. Both arms now state the condition and the
  per-population remedy, and name no file they do not read.

  A SENTENCE WRITTEN EARLIER THE SAME DAY WAS MEASURED FALSE. It claimed a
  `git archive` extract and a shallow clone are one population. They are not:
  an extract never reaches the shallow branch, being stopped one layer earlier
  by the not-a-git-repository skip in the repo-root conftest. Measured 4 passed
  and 4 skipped in a real extract.

  THE UNGUARDED HALF IS NOW GUARDED. Nothing pinned the docs lane at depth 1,
  so raising it would have made the new reason text quietly false with no test
  going red. `tests/test_ci_history_depth.py` now asserts the OPPOSITE of its
  ci.yml arm for that lane, with the census in the same assertion, verified red
  under mutation and green restored with both caches purged on each side.

  STILL UNGRADED, and it is the third reason a local green says nothing about
  CI. Every pinned dev tool is OLDER on this box than what CI installs - ruff
  0.15.12 against a 0.16.6 pin, pytest 9.0.3 against 9.1.1, mypy 2.1.0 against
  2.3.1, re-measured 2026-09-09. Nothing compares installed against declared. A
  test asserting equality would be GREEN on CI and RED here, which is backwards
  from useful, so the shape of that guard is an open question rather than an
  unwritten test.

- **RULED 2026-09-09, AND THIS IS AN ADJUDICATED CALL - NOT AN OPERATOR
  DECISION.** It is overturnable by reading this entry. A sibling offered a
  shape: `mkdir(parents=True)` under a parent that is a FILE. Measured here on
  Python 3.14.4 it raises FileExistsError, errno 17, winerror 183, where POSIX
  raises NotADirectoryError, errno 20 - but every handler in this tree catches
  no narrower than OSError, so that half is NOT-APPLICABLE-HERE.

  THE SWEEP FOUND A DIFFERENT AND REAL FACT. `mkdir` can raise ValueError,
  which is NOT an OSError, when the path carries a NUL byte. Reproduced on both
  3.14.4 and the 3.11 on this box, CI's minor.

  THE FIRST FRAMING OF THIS ITEM WAS WRONG AND IS RECORDED AS WRONG. It claimed
  the tree had fixed one site and never swept the siblings, resting on an AST
  walk for a try block directly containing a mkdir call. That method is
  STRUCTURALLY BLIND to a guard placed at the caller, and the caller is where
  this tree put it: twelve sites catch `(OSError, ValueError)`, and
  `scripts/watch_inbox.py` names the OSError-only catch in `core/atomic_io.py`
  explicitly as known and absorbed one layer up. Two agents agreed on the
  nine-site census because they shared that one sweep as their input.

  RULING: POSITION B, DO NOT WIDEN, all eight OSError-only sites. The
  discriminator is the stated CONTRACT and not the call: the widened sites are
  exactly the functions whose docstrings promise never to raise. A False return
  from `atomic_write_text` currently means the OS refused; widening would make
  it also mean the caller passed garbage, and a silent False is the quieter
  failure. Reachability was measured rather than argued and is zero of eight -
  environment variables and argv both REJECT a NUL at the boundary and cannot
  carry one, no filesystem permits it in a name, and Path.parent strips a
  NUL-bearing final component. JSON is the only external carrier and the one
  Path built from parsed JSON is unguarded anyway.

  THE ADJUDICATOR'S OWN STRONGEST OBJECTION STANDS. `tools/moon_sync_responder.py`
  wraps an `atomic_write_text` call at line 928 without the caller-side absorb,
  so a ValueError there aborts a broadcast mid-loop with some inboxes written
  and no record - the ordering that function's own docstring names as the worst
  available. Widening cannot fix it, because line 915 already uses ValueError
  as the refusal signal, so absorbing it would make a refused draft and a
  malformed path indistinguishable. Closing it needs a private exception type
  for the refusal first. SUPERSEDED FOR THIS ONE SITE 2026-09-09 - see the
  overturn recorded at the top of this file. The other seven stand. WHAT WOULD OVERTURN THE RULING: a Path built from
  parsed JSON or an upstream response body reaching one of the eight, or a
  decision that `atomic_write_text` should promise never to raise - which is an
  ADR, not an except clause.

  A THIRD REASON A LOCAL GREEN SAYS NOTHING ABOUT CI, and it is new. Every
  pinned dev tool is OLDER on this box than the version CI installs: pytest
  9.0.3 against a 9.1.1 pin, mypy 2.1.0 against 2.3.1, ruff 0.15.12 against
  0.16.6. CI installs the dev requirements on every run. Nothing in the suite
  grades installed against declared. That is alongside the OS difference and
  the interpreter difference, 3.14.4 here against 3.11.16 there.

  This is a DIFFERENT item from the git archive extract red already recorded
  below - that one is about a no-git copy, this one is about Linux.

- **DIAGNOSED AND CLOSED THE SAME EVENING, and the answer is not a defect.**
  The pre-push hook reports `1579 passed, 2 skipped` where every other
  invocation reports `1580 passed, 1 skipped`. First filed as transient and
  unnameable; BOTH OF THOSE WERE WRONG and the correction is the entry. It is
  deterministic under a real `git push` and absent under the hook run by hand,
  which is why four reproduction attempts missed it - none of them was a push.
  Named by pushing to a scratch bare repository under a scratch
  `core.hooksPath` whose hook ran the suite with `-rs`, touching no tracked
  file and not origin.

  The extra skip is `tests/test_hook_interpreter.py:1774`, and it is CORRECT.
  Git puts `mingw64/libexec/git-core` on PATH for its hooks, so
  `shutil.which("git")` resolves to `git-core\git.exe`, which is not an install
  root. The oracle added this session says so and skips with a TRUE reason -
  the exact ceiling its author disclosed: a layout outside the marker set reads
  as unidentifiable and skips rather than guessing.

  HALF-CLOSED 2026-09-09 by commit `e714b35`, the preferred half. The hook now
  runs `-m pytest -rs` for BOTH suites, so a future skip is nameable from the
  hook's own output without a scratch bare repository. Guarded by
  `tests/test_prepush_skip_reporting.py`, whose matcher keys on whether each
  invocation's `-r` spec REPORTS SKIPS rather than on the literal `-rs` - the
  first attempt keyed on the literal and was REFUTED for going RED on `-rA`,
  `-r s`, a line continuation and a plain reorder, all of which are correct
  hooks. Widening the matcher was not the answer; asking what the mechanism can
  claim was.

  STILL OPEN, and it is the other half: nothing inspects hook OUTPUT. The arms
  are a token scan of a shell script. No push was run and no scratch remote
  created, so the 2-versus-1 skip figure is carried as prose rather than
  re-measured. The remaining candidate closure - teach the oracle the `git-core`
  layout by measuring it - is untouched.

  ALSO OPEN, verified by a refuter against `e714b35`: a bare `-r` with no
  attached spec is a FALSE GREEN, because the parser lets `-r` swallow the
  target and `"tests"` contains an `s`. A token scan cannot disambiguate a
  detached spec from a target path, so the honest repair is to report that shape
  UNPARSEABLE and fail rather than to widen anything.

- **CLOSED 2026-09-08 for 13 sites across four files, and OPEN for three more
  places.** The condition that cannot tell CHECKED-AND-FOUND-NOTHING from
  COULD-NOT-CHECK is repaired in `tests/test_watch_inbox.py`,
  `tests/test_line_endings.py`, `tests/test_hook_interpreter.py` and
  `tests/test_hook_gate.py`, each slice refuted by an adversary before it was
  believed. Full account in `docs/LEDGER.md`. THE RANKED LIST IN THE PREVIOUS
  HAND-OFF WAS STALE - its two worst entries were already fixed - so re-derive
  rather than trusting any list, including this one.

- **CLOSED 2026-09-09 for the coverage, and the disposition is an ADJUDICATED
  CALL - NOT AN OPERATOR DECISION.** `tests/conftest.py` routed all three
  outcomes of `git rev-parse --git-dir` with NO TEST AT ALL on any of them.
  Commit `9e9f7e4` extracts a pure `classify_git_probe(returncode, stdout,
  stderr, exec_error)` and adds 14 arms.

  THE ADJUDICATED CALL, overturnable by reading this paragraph. The non-128
  non-zero branch STAYS A SKIP and was NOT promoted to a FAIL. Criteria the
  adjudicator ruled against, stated before it read the candidate: which of the
  three dispositions the exit code names; whether a false red could be NAMED in
  a real environment; whether a shipped arm required the current behaviour;
  blast radius; and separability. Findings: every git FATAL exits 128 -
  measured, git 2.53.0.windows.3, including outside a repository and on a bogus
  flag - so a non-128 non-zero exit IS git running and breaking, the second
  disposition, and the promote-to-FAIL argument WINS on meaning. It loses
  anyway, because the FAIL already exists ONE LAYER UP:
  `tests/test_commit_trailers.py` cross-checks the helper against an
  INDEPENDENT signal, a `.git` entry on disk, and reddens the suite for any
  non-None reason inside a checkout. Firing inside the helper would move the red
  into the archive-shaped population this file was written to serve. The
  adjudicator could NOT NAME a healthy-repo environment producing a non-128
  non-zero exit; that is a finding, not a gap, and a measured case would reopen
  this. WHAT WOULD OVERTURN IT: showing that
  `tests/test_commit_trailers.py::test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout`
  can be skipped or deselected inside a real checkout, at which point the helper
  is the only door.

  THE PREVIOUS HAND-OFF'S FIGURE WAS SCOPED WRONG. "Injecting exit 7 gives 29
  passed, 4 skipped, EXIT=0" is TRUE WITHIN ONE FILE and FALSE SUITE-WIDE.

- **CLOSED, AND THE ROW ABOVE IT WAS STALE FOR TWO SESSIONS - the staleness is
  the entry.** This row previously read OPEN and said the byte-identity contract
  was "GUARDED BY NOTHING" and that a bracket change "leaves all 14 arms green".
  Both sentences were TRUE WHEN WRITTEN and FALSE when read. Provenance, from
  `git log -S` against `tests/test_conftest_git_gate.py` rather than from memory:

    - authored at `52cc874`, truthful at that commit;
    - CLOSED at `e714b35`, which added `HAND_TYPED_NOT_RUNNABLE`,
      `HAND_TYPED_NOT_A_REPOSITORY` and `HAND_TYPED_DID_NOT_ANSWER` to
      `tests/test_conftest_git_gate.py`. THE ROW WAS NOT UPDATED.
    - STRENGTHENED at `dda913a`, which added the five-shape
      `WRONG_DELIMITER_SHAPES` control to the same file. Still not updated.

  MEASURED ON THE SHIPPED TREE at `817b31b`, control first: the incumbent file
  is 22 passed exit 0, and the mutant `({detail})` to `[{detail}]` in the 128
  branch is 3 failed 19 passed exit 1. The row's own example mutant dies.

  WHY IT MATTERS MORE THAN ITS SUBJECT. `docs/LEDGER.md` recorded the closure at
  `dda913a` while this file still said OPEN, so the two documents disagreed and
  the hand-off propagated THIS one. A whole slice was dispatched against a
  defect that did not exist. The merger dispatched it, so the DISPATCH PROMPT
  was the defect, not the builder - the same lesson this tree recorded one
  session earlier and did not apply. A residual row is a claim with a
  measurement date, and it decays; re-probe a row before spending a slice on it.

  TWO AGENTS GOT THE PROVENANCE WRONG IN OPPOSITE DIRECTIONS, which is why the
  commits are named here. The merger credited `e714b35` alone; a builder
  credited `dda913a` alone. The fixture is `e714b35`, the delimiter control is
  `dda913a`, and neither agent had both until the pickaxe was run against the
  file rather than against the tree.

- **HALF-CLOSED 2026-09-09 by commit `e714b35`, and ONE CLAIMED CLOSURE IS
  FALSE.** The adjudicated call that keeps `tests/conftest.py`'s non-128 SKIP
  rests entirely on `tests/test_commit_trailers.py` reddening for any non-None
  reason inside a checkout, and nothing pinned that. Twelve arms in
  `tests/test_conftest_skip_path_pinned.py` now do, asserting on the REAL shipped
  function with the exception MESSAGE matched, and clearing `GIT_DIR` and
  `GIT_WORK_TREE` in every arm. Killed: the `else:` block deleted,
  truthiness-only `not reason`, a message that drops the reason, the conftest 128
  branch stubbed, welded-to-fail, and an arm that raises `Skipped`.

  CLOSED 2026-09-09 in the same session that opened it. Inserting
  `require_git_repository()` into the audited arm SURVIVED 12 of 12, because
  every arm patched only the audited module's OWN re-import of
  `git_unusable_reason` while the inserted call resolves conftest's binding, got
  None in a real checkout, raised no `Skipped` and was invisible. BOTH bindings
  are now patched, and both are load-bearing for DIFFERENT reasons, proven rather
  than assumed: the audited re-import is what the cross-check's body reads, so
  without it the arms grade the real tree instead of the forced input; the
  definition site is what `require_git_repository()` resolves, so without it the
  skip door is dead code. Independently re-probed at the merge by differential
  measurement in an identical scratch environment - unmutated control 1 failed,
  mutant 8 failed - rather than by trusting the builder's figure. The overstating
  docstring is rewritten to name the hole it had.

  A SECOND CEILING, honest but worth naming: every pin arm reaches the archive
  `else:` half only by rewriting the audited module's `REPO_ROOT`. That half is
  DEAD in both a worktree and the main checkout, so it is graded under forced
  inputs rather than as shipped behaviour.

- **CLOSED 2026-09-09, and it was ours, caught by a control probe rather than by
  any refuter.** `tests/test_conftest_skip_path_pinned.py` shipped in `e714b35`
  with an arm that ASSERTED a `.git` entry exists on disk, so it FALSE-RED in a
  `git archive` extract - measured 1 failed, 13 passed, exit 1 outside any
  repository. An extract has nothing to report, which is NOT-PRESENT-AT-ALL, the
  third disposition, and the arm's own docstring anticipated the archive shape
  and then asserted anyway. It now SKIPS with a reason naming the shape:
  measured 13 passed, 1 skipped, exit 0 in the same extract.

  WORTH KEEPING as method rather than as fact: no refuter was assigned an
  archive-shape lens, and five were dispatched. The defect surfaced only because
  a mutant kill was verified DIFFERENTIALLY against an unmutated control in the
  same environment, and the control was not clean. A mutant kill measured without
  a control cannot distinguish the mutant's failures from the environment's.

- **CLOSED 2026-09-11 at `86491a3` AND `78cdf96`, AND THE LAST SENTENCE OF THIS
  ROW WAS THE WRONG READING.** The row's final measurement - that the pre-push
  gate does not hit this, because `git hook run` shows an empty `GIT_DIR` - is
  CONFIGURATION-SCOPED and was reported as universal. Verified 2026-09-11 on git
  2.53.0.windows.3: a push from the MAIN CHECKOUT exports none, a push from a
  LINKED WORKTREE exports it, and this machine carried 52 worktree entries that
  day while the pre-push hook runs both suites. With it exported,
  `python -m pytest tests` returned rc 2 with "Interrupted: 1 error during
  collection" while the engine suite collected 80 and carried on. An AST pass over
  the 141 tracked Python files found 41 corpus sites with exactly ONE real scrub,
  correcting an earlier 39-with-two reading in which one claimed scrub matched
  only because a COMMENT mentioned the variable. CS's damage narrative was
  NARROWED rather than adopted: `git init --bare` with an EXPLICIT path does not
  hijack, only the no-path form does, and this tree has zero such call sites, so
  only the corpus swap can fire here. The scrub now lives in `conftest.py`, sized
  from `git rev-parse --local-env-vars` - git's OWN list, fifteen names - with a
  runtime reconciliation arm, and `tests/test_hook_gate.py` is now
  configuration-scoped with both readings. Guard `tests/test_git_env_scrub.py`.
  The original text follows.

  With `GIT_DIR` exported, `git rev-parse --git-dir` SUCCEEDS while
  no `.git` sits on disk, so `tests/conftest.py` and the disk cross-check in
  `tests/test_commit_trailers.py` DISAGREE - one reports a usable repository and
  the other reports none. That state is neither ran-and-found-nothing,
  ran-and-broke, nor not-present-at-all: it is live-repo-relocated-GITDIR, and
  under it the cross-check that the adjudicated call above depends on can carry
  a FALSE reason or false-red. Nothing in either file clears `GIT_DIR` or
  `GIT_WORK_TREE`. Measured separately: the pre-push gate does not currently hit
  this, `git hook run` shows `GIT_DIR=[]`.

- **CLOSED 2026-09-09 by commit `5f9e312`, AND THE CLAIM THIS ITEM MADE WAS
  FALSE.** The previous wording said `tests/test_machine_identity.py` and
  `tests/test_licence_posture.py` consumed `git ls-files` "with no floor and no
  anchors". BOTH ALREADY HAD ONE: a hand-written floor of 100 plus named
  anchors, five in the first file and six in the second, and the `_sweep()`
  docstring's claim that the count is asserted separately was TRUE. The
  coordinates were also off - `_tracked_files()` begins at line 231, not 236.
  This is what re-deriving a handed-off list is for.

  THE HOLE THAT WAS ACTUALLY OPEN is narrower and was real: the floor lived in a
  SEPARATE arm from the sweep, so the PRIMARY arm passed GREEN OVER ZERO FILES -
  `assert not offenders` holds trivially on an empty corpus - and `check=True`
  reported an exit code while DROPPING stderr. Repaired with a pure
  `_classify_enumeration(returncode, stdout, stderr)` at each site holding four
  outcomes apart, `check=False`, and `pytest.fail` at the point of use, with
  `require_git_repository()` still first so a no-repository copy stays a SKIP.

  An adversary supplied the measurement the author could not: in a genuine
  no-git extract the tree gives 62 passed / 26 skipped against a baseline copy's
  62 passed / 14 skipped. The PASSED COUNT IS IDENTICAL, so no pre-existing arm
  turned a pass into a skip and no false red was installed.

- **OPEN, low severity, and a PRE-EXISTING blindness rather than a regression.**
  The sweep floor's VALUE is ungraded in both files above. Mutating
  `_MIN_TRACKED_PATHS` from 100 to 10 leaves the suite green, because the arm
  that checks the floor is reachable asserts only `>= 10`. The pre-change inline
  literals were equally free to be edited, so this is a gap in a new arm's
  advertised claim.

- **OPEN, pre-existing, and NOT from this session.** In a `git archive` extract
  the whole suite is EXIT=1 for the BASELINE as well as the current tree, with
  an identical 6-failure set in `tests/test_ci_workflow_complement.py` and
  `tests/test_no_sibling_names.py`. The Download-ZIP population that
  `tests/conftest.py` exists to serve is already red before any of this
  session's work.

- **STEP ONE OF THREE CLOSED 2026-09-09. THE GATES ARE TAGGED AND THE CENSUS
  GUARDS THEM. The mutation runner and the registry remain OPEN, and the order
  is still strictly sequential.** `tools/moon_sync_responder.py` carries **18**
  `# GATE:` tags, up from 0, and `tests/test_responder_gate_census.py` guards
  them. The responder change is COMMENTS ONLY, proven not asserted: `ast.dump`
  of the tagged file equals `ast.dump` of the file at `817b31b`.

  THE REFERENT IS RECORDED AS AN ADJUDICATED CALL, NOT AN OPERATOR DECISION,
  and it is overturnable by reading this entry and changing the predicate
  `_is_a_consult_site` in the census module. It is a PREDICATE and not a set of
  node types, and that is itself the third defect's repair rather than a
  detail - see below. THE BROAD READING WON: a gate is ANY consult site inside
  `_run_once` whose value binds the cycle, whatever syntax carries it. The
  NARROW reading - only statement-level branches count - was what the first
  build actually shipped, and it shipped a measurable hole rather than a
  judgement. Measured on that build:

      _run_once:  ast.If = 14   ast.Try = 1   tags = 15
      sorted(tag_line + 1) == sorted(If lines + Try lines)   ->   True

  The rule applied was therefore SYNTACTIC - tag every if and try - so the 15
  was an artifact of the shape and "each tag marks a gate" was never a decision
  anybody made. Three sites that bind the cycle were untagged BECAUSE OF THEIR
  SYNTAX: the `exhausted`/`refused` `IfExp`, which the responder's own prose
  calls the one distinction that must not be conflated, and the two `BoolOp`
  writes that set `bounced` and `delivered`.

  THREE REFUTERS ON THREE DISTINCT LENSES FOUND THREE DEFECTS, and no two of
  them could have found each other's. That is the session's own evidence for
  distinct lenses over N identical skeptics.

  DEFECT ONE, referent lens: the syntactic rule above.
  DEFECT TWO, mechanism lens: the tag NAME GRAMMAR FAILED OPEN. A single strict
  regex silently ignored every near miss - `# GATE: name` with one space after
  the colon, an uppercase name, an underscore, an empty name, a trailing
  comment. A real new gate tagged `# GATE: draft-skip` passed at exit 0. The
  repair is a MISSING PARSE STEP AND NOT A WIDER MATCHER, which is this tree's
  standing lesson after three defeats on one derivation: a PERMISSIVE detector
  finds every line trying to be a tag, a STRICT grammar validates the name, and
  a line the first accepts and the second rejects RAISES naming file and line.
  DEFECT THREE, and it refuted the REPAIR rather than the original: accepting a
  bare `ast.BoolOp` to catch those three sites was itself A WIDENING WEARING A
  PARSE FIX'S CLOTHES. It bought 4 FALSE SITES - the dependency-injection
  defaults `inbox or DEFAULT_INBOX`, `bounds or Bounds()`, the `roots` `IfExp`
  and `spawn or _spawn_headless` - and a tag parked on three of them passed
  clean. A strictly tighter rule with IDENTICAL coverage and ZERO false sites
  was available and had not been taken: an `If` or a `Try`, or an `IfExp` or
  `BoolOp` inside an assignment whose target is a subscript, which is to say a
  value computed INTO the cycle's own result. Re-measured by the merger:

      broad  If/Try/IfExp/BoolOp   22 spots   false: 4
      tight  the rule above        18 spots   false: 0   covers all 18 tagged

  THE TIGHTENING SHIPPED. `_ACCEPTED_SHAPES` is gone and the decision is now a
  named predicate, `_is_a_consult_site`, so the rule reads as the judgement it
  is rather than as a tuple of node types. Verified by the merger independently
  of its author: parking a tag on `inbox = inbox or DEFAULT_INBOX` passed clean
  under the broad rule and is exit 1, 7 failed under the shipped one, with the
  responder restored to sha256 `02469d15` afterwards.

  THE HOLE THAT REMAINS IS DISCLOSED RATHER THAN DISCOVERED LATER. Nothing
  enumerates the gates that OUGHT to exist, so a NEW gate added to `_run_once`
  and never tagged is invisible and every arm stays green. That is measured,
  not feared, and it is the reason the mutation runner is step two rather than
  an optional companion.

  SUPERSEDED IN PART, 2026-09-09, and the paragraph above is kept because a
  reader arriving at the entry it belongs to should see what was true when it
  was written. The census now asserts BOTH directions of the comparison, so an
  untagged consult site in a shape `_is_a_consult_site` accepts is no longer
  invisible. What survives of the hole is narrower and is stated at its own
  entry above, in the census module's ceiling item 2, and nowhere else.

  STEP TWO CLOSED 2026-09-09 at `1c596e3`: `tools/gate_mutation_runner.py`.
  STILL OPEN: the REGISTRY and its companions. Building the companions first
  still ships a vacuously green apparatus. The two census hazards below are now CLOSED IN CODE - the
  strict pattern anchors the whole line, captures the name, and every
  comparison is between captured groups for EQUALITY - but they are kept in
  this entry because a later rewrite can reintroduce either one.

- **OPEN, unverified here, offered by RC as a shape to check rather than a
  finding about this tree.** `mkdir(parents=True)` under a parent that is a
  FILE raises WinError 183; RC found nine sites and exactly one had the
  partial-write half. Check this tree's own sites.


- **CLOSED 2026-09-08 by the cold-boot measurement the previous session left as
  its first instruction.** The runtime invocation log under `ops/runtime/`,
  gitignored and so named in prose, records which hook fired: commit `3964544`
  gives `SessionStart` and `UserPromptSubmit` distinct `--source` labels. The
  prior half was a real `UserPromptSubmit` fire writing `userpromptsubmit` on
  both of its lines. `SessionStart` carried no flag before that commit, so the
  commit made it argv-dependent for the first time, on the exact event the log
  exists to prove. The next cold session wrote a `sessionstart` pair, both
  columns, reaching `reported` and not merely `start` - so the hook ran to
  completion rather than only to entry. BOTH hooks deliver argv on this machine.
  Recorded here because it was the open question, not because a passing hook is
  news.

  Second fact from the same reading, unpredicted: a `userpromptsubmit` pair
  fired one second after the `sessionstart` pair, from the same cold prompt.
  Both hooks fire on a cold session start, in that order. The distinct labels
  are what make them separable at all - under one shared label the pair reads as
  a single hook firing twice, which is what the log said for every earlier line.

- **OPEN, AND IT IS THE REASON THE ITEM ABOVE COULD NOT CLOSE `/clear`.** The
  `--source` flag as wired hardcodes ONE LITERAL STRING PER EVENT, so the log
  records which HOOK fired and never which SOURCE the harness fired it from.
  The harness distinguishes `startup`, `clear`, `compact` and `resume`; the
  wiring collapses all four onto `sessionstart` and discards the difference.
  So a cold-boot `sessionstart` pair is not evidence about `/clear` survival and
  cannot be made into evidence by taking more cold boots - the instrument does
  not have the resolution. Closing it means reading the harness's own source
  value rather than restating a constant we chose, which is the same defect
  class as a shape arm pinning format instead of value. Filed rather than built
  on operator instruction 2026-09-08, and it touches `scripts/watch_inbox.py`
  and `.claude/settings.json`, so it seams with any doc gate that grades quoted
  hook commands.

- **DONE 2026-09-08, with a remainder disclosed rather than closed.**
  `tools/moon_sync_responder.py` now carries the caller label and the runtime
  override, proven by `tests/test_moon_sync_responder.py`. Measured across a
  real process boundary rather than inferred: the environment outranks the
  `--source` flag, the flag outranks the fallback. The env-routing property went
  from absent to present and the hardcoded `run_once` call sites went to none;
  re-measure with the greps rather than trusting either number here.
  `ops/ResinCompute-Responder.xml` gained the matching `--source scheduledtask`
  at the merge, because the builder correctly refused to write outside its
  declared list and the argv element was the one line that made the fix real.

- **OPEN, AND IT IS THE OVERSTATED HALF OF THE ITEM ABOVE.** The isolation arm
  is named for enforcing that nothing is written outside the override, and it
  does not enforce that. An adversary broke it with a planted mutant that leaked
  two files while the arm reported a pass. Two causes, both measured:
  **NTFS reports a DIRECTORY `st_size` as 0 whatever it contains**, so a file
  created inside one of the watched directories is invisible to a snapshot built
  from existence plus size; and any path that is not one of the `DEFAULT_`
  constants is not watched at all, which includes the sibling inbox directories
  that `deliver()` really writes to. What IS measured and does hold: the test
  suite does not reach the operator's live responder record, checked twice with
  the real tree byte- and mtime-identical either side. So the protection is real
  for the runtime directory and ABSENT for live mail. Fix the arm or rename it -
  an arm whose name claims more than it checks is worse than no arm, because the
  next reader stops looking.

- **CLOSED 2026-09-08 by `tests/test_responder_task_argv.py`, and it took three
  rounds because the first two were shape arms.** The task XML's `<Exec>` argv is
  now graded against the code that argv calls. Nothing is written down: the
  script's identity comes from a byte scan for the file declaring
  `SOURCE_SCHEDULED_TASK`, flag spellings from that script's own `parser._actions`,
  and MEANING from running `main` with `run_once` intercepted and grading the
  `Bounds` it builds.

  Recorded because the failures are the instructive part. Version one graded
  SHAPE and let four meaning-changing mutants through green: the script path
  swapped to a real-but-different file, `--arm` dropped so the task never spawns,
  the window boundaries swapped so it closes before it opens, and non-dash
  positional junk that `parse_known_args` binned unasserted. Version two keyed its
  refusal token on the EXIT CODE 2, which argparse also returns - four unrelated
  causes minting one fingerprint, the same defect as an interpolated reason
  string. Version two also disclosed `--latency-only` as ungradeable "because the
  code marks it optional"; an adversary refuted that from the call the test was
  already intercepting, where the `grammar` kwarg differs. Dropping the flag would
  publish integer hops with `m1_status='lower-bound'` for a run whose far end is a
  human - exactly what `e1a101d` fixed.

  One property here is worth reusing rather than re-deriving: a content-hash
  recursive walk over 1137 entries - this worktree, this tree's runtime directory
  and inbox, four sibling inbox directories, the profile config - showed these
  arms write NOTHING outside pytest's own cache, with planted controls proving the
  walk sees additions and modifications. That is what the responder isolation arm
  below was supposed to be and is not. Note the method: NOT existence-plus-size.

- **OPEN, and narrower than it looks. `--latency-only` presence is still
  ungraded in the argv gate.** The grammar the intercepted call receives IS now
  asserted, which covers the consequence; what remains unasserted is the flag
  itself. Left deliberately rather than pinned as a literal.

- **CLOSED 2026-09-08 AS TO ITS SIX MEASURED HOLES, AND THE CLAIM IT COULD NEVER
  KEEP IS NOW WRITTEN DOWN INSTEAD.** The read-only guard over
  `ops/check_task_liveness.py` was defeated FIVE times in one session, twice
  destructively - a canary file deleted from disk while the suite printed a green
  exit 0. Commit `9fe8b0b`. `ops/check_task_liveness.py` itself needed no change:
  no violation was found in it under any of the new nets.

  The six, each watched red on its own mutant before the fix:
  a PowerShell ALIAS CARRIES NO HYPHEN, so `ri`, `del`, `rm`, `sc`, `kill`, `ni`
  and a concatenated verb all walked past a hyphenated Verb-Noun scan;
  the whole-file scan carried no `re.IGNORECASE` while the comment above it
  asserted case-insensitivity;
  a TYPE ACCELERATOR CALLS THROUGH `::`, NOT `.`, and `[` is not a letter, so
  `[System.IO.File]::Delete` reached neither scan - nor did plain `>` REDIRECTION,
  which overwrites a file while carrying no command token at all;
  the scan was BOUND TO THE IDENTIFIER `_PS_TEMPLATE`, so a second module-level
  PowerShell string concatenated onto it was ungraded;
  the harness SHIMMED `subprocess` WITH A STAND-IN THAT HAD NO `Popen`, so a
  mutation branching on `hasattr(subprocess, 'Popen')` built pristine text under
  the shim and a deleting probe in production;
  and grading ran at import of the TEST file, which is AFTER the SUBJECT's own
  module-level code has already run.

  **THE CEILING, and it is the durable finding rather than the fixes.** A test
  suite CANNOT prevent arbitrary runtime behaviour in a module it imports. It can
  grade that module's SOURCE, and it can refuse to import a source that fails the
  grade. It cannot prove that a source which passes will behave the same way at
  runtime, because the imported module can always branch on something the harness
  did not think to make identical. That paragraph is now in the file's docstring,
  and two arms were renamed to claim only it. Rounds two through five each
  widened a matcher; the last two kills did not touch a matcher at all. If a
  sixth attack lands, widening is the wrong response.

  Also closed: the ambiguity arm no longer collapses "checked and found nothing"
  into "could not check". Discovery returns records and draws no conclusion,
  FAILED is an error rather than a skip, and only the genuinely-empty case skips,
  saying which case it is. The plausibility floor that replaced it was measured
  DECORATIVE first - over totals 0..39 the set where its own assertion could fail
  was empty - and rebuilt.

- **OPEN, AND IT IS WHAT THE ITEM ABOVE BOUGHT CI: NOTHING.** `_WINDOWS_ONLY` is
  a `skipif`, so on a Linux runner every real-probe arm in
  `tests/test_task_liveness.py` never executes. The import-time source gate, the
  static arms and the discovery classifier do run there; the arms that talk to a
  scheduler do not. Measured, not assumed: the same file gives different
  pass/skip splits under simulated machines, so a zero-skip reading is a property
  of THIS BOX and not of the arm.

- **OPEN, AND IT IS THE SAME ROOT CAUSE IN SEVEN MORE PLACES.** A condition that
  cannot distinguish CHECKED-AND-FOUND-NOTHING from COULD-NOT-CHECK. An AST sweep
  over `tests/` - 51 files, 21 `pytest.skip` call sites, positive control planted
  and caught - ranked these, and the two worst are in the file just repaired:
  `_real_task_names` collapses a non-zero return and empty stdout into one return;
  and `_a_task_carrying_an_end_boundary`, which is THE ONLY ARM PINNING THE
  EndBoundary VALUE, the tool's whole purpose. Then
  `tests/test_hook_interpreter.py` twice, `tests/test_watch_inbox.py` three
  times, `tests/test_line_endings.py` once, and lower-ranked sites in
  `tests/test_commit_trailers.py`, `tests/conftest.py`, `tests/test_readme_tree.py`,
  `tests/test_ingest_client.py`. Proved by making the discoveries exit 3: the run
  reported a pass with skip texts falsely blaming the machine. Re-derive the list
  rather than trusting this one - a corpus is a snapshot.

- **OPEN, AND IT IS A LIMIT OF THE GATE SHIPPED THE SAME DAY.** The
  hook-command gate in `tests/test_docs_hook_commands.py` grades a quoted command
  only when it carries a long flag, or when the surrounding claim block spells
  the literal settings path. An adversary measured the consequence: reword the
  sentence to say "the hook declared for this tree" instead of naming the file,
  and the identical stale quotation goes silent. The real defect was caught
  partly by the luck of how it was phrased. Its live enforcement surface is five
  citations in one of the tracked documents.

- **OPEN. Nothing grades a document against `.claude/settings.json`.**
  `docs/INBOX_TRIAGE_2026-09-07-0710.md` quotes both hook commands without the
  flags they now carry. The docs gate catches a backticked path that git does not
  store; it does not catch a quoted command that no longer matches the wiring.


- **OPEN, OPERATOR DECISION, HIGHEST PRIORITY. The overwhelming majority of
  commits in this PUBLIC repository carry the operator's personal email in the
  author field.** Do not cite a stored number here - a commit count goes stale
  the moment anyone commits, and the figure that stood in this item until
  2026-09-08 had already drifted. Re-measure instead, and the tally is three
  buckets rather than two:

  ```
  git rev-list --count HEAD
  git log --format='%ae' | sort | uniq -c | sort -rn
  ```

  Read 2026-09-08 as a dated reading and not a promise: 90 personal, 6 platform
  forwarding, 2 assistant, of 98. The prior entry said 89 of 91 as of
  2026-09-07, which was both a smaller denominator and a two-bucket split that
  hid the forwarding address entirely. A sibling redacted the same string from a
  single note hours earlier and treated it as the operator's identity. Nothing
  has been done: a history rewrite on a public remote is an operator decision,
  and a sibling measured four separate traps doing one - a mirror clone fetches
  `refs/pull/*/head`, a ref-pattern check can fail GREEN, a content scrub can be
  complete and still publish names because a filename is not content, and
  deleting a repository deletes its LFS store. This tree's own `refs/pull` count
  is ZERO with a positive control, so that trap does not apply here.

- **DONE 2026-09-08. The LATENCY-ONLY window ran and its result was reported to
  the channel as NO-DATA.** `tools/moon_sync_responder.py`, proven by
  `tests/test_moon_sync_responder.py`. Measured after the window closed:
  `responder_metrics.json` never created, 29 `start` against 19 `empty` in the
  invocation log, M1 INAPPLICABLE, M2 and M3 NO-DATA. The cause was RSC's own
  `since=bounds.window_opens` eligibility rule admitting no mail, not the
  counterparty. Left alone mid-window deliberately: widening eligibility while
  the experiment ran would have edited the experiment.

- **OPEN. The responder has STILL never answered real mail, after two
  attempts.** Every measurement in `tests/test_moon_sync_responder.py` is
  against a stub or a scratch inbox. Attempt one terminated `empty` on every
  tick. Attempt two, on 2026-09-08, was refused by the counterparty 72 seconds
  after delivery at its input stage on name grammar, and no responder-authored
  reply had arrived 15 minutes later when polling stopped. Three candidate
  explanations, none measured.

- **OPEN. An eligibility rule that makes a trial measure nothing is invisible
  until the trial ends.** `pending()` in `tools/moon_sync_responder.py` takes
  `since=bounds.window_opens`, and a window whose backlog predates it has zero
  eligible notes on every tick. The counterparty independently hit the mirror of
  this from the other side - an empty answered record makes the ENTIRE backlog
  eligible, so a budget of one is spent on the oldest note in the inbox. Both
  directions argue for the same fix: state the eligibility rule IN the agreement
  record, and assert the pending count is non-zero at arming time rather than
  discovering it was zero afterwards. `tests/test_moon_sync_responder.py` already
  has an arm proving that without a `since` bound the backlog is eligible.

- **DONE 2026-09-08. A refused note no longer grows one held file per tick, and
  the fix was not the one first written.** `tools/moon_sync_responder.py`,
  proven by `tests/test_moon_sync_responder.py`. The first suppression hashed
  the RENDERED REASON TEXT, and one reason interpolated a byte count, so a draft
  oversize by a different amount each cycle minted a fresh fingerprint every
  tick - ten cycles, ten held files, with the guarding arm feeding a
  byte-identical draft and structurally unable to fail. Keyed on reason CATEGORY
  now: ten cycles give one held file. Found by an adversary AFTER the builder
  reported the slice complete and green.
- **DONE 2026-09-08. A refusal now tells the sender, via a file that is not a
  note.** `tools/moon_sync_responder.py`, proven by
  `tests/test_moon_sync_responder.py`. Template-only, runner-authored with an
  arm asserting no model byte reaches it, one allowance per note per agreement,
  and excluded from the budget and from M1/M2/M5. Sibling-A converged on the
  same six properties independently, neither copying the other. REMAINING, and
  disclosed rather than closed: an evicted refusal row can still re-hold one
  local file.
- **OPEN. Note filenames here are long enough to be refused by a sibling's
  grammar.** RSC's 2026-09-08 note was 130 characters with a 102-character
  topic and was refused. The counterparty measured all 207 names across the five
  inboxes: 33 fail its grammar, ALL on the topic group, only 11 on the length
  cap. Nothing in this tree enforces a note-name length, so the convention is
  habit rather than a guard.

- **OPEN. The watcher reports an underscore-prefixed `.md` as a note.**
  `scripts/watch_inbox.py` demotes only the `.tmp` suffix, so a partial file
  written during another repo's hard-link window would be listed as unread mail.
  Not reachable through the one counterparty whose delivery scheme was measured
  - its tmp names carry `.tmp` - but it is a reading-side defect regardless.

- **OPEN, AND IT IS AN OPERATOR ACT. The responder is DORMANT and its agreement
  EXPIRED, both at 2026-09-07T21:00:00.** Measured 2026-09-08: the task reports
  `State: Ready` and `LastTaskResult: 0` while its only trigger's EndBoundary is
  in the past, NextRunTime is empty, and the invocation log holds no line dated
  2026-09-08. `ops/check_task_liveness.py` reads it DORMANT with exit 1.
  Sibling-A's responder DELIVERED a machine-authored note at 17:00 that day, so
  the receiving side finally has M2/M3 data, but the REPLY path cannot run.
  Re-running the installer produces another BOUNDED window, not a standing
  responder - the window bound is a deliberate choice, and a gitignored
  agreement record naming the counterparty must exist first.

- **OPEN. One mutant survives the task-liveness suite by construction, and the
  eighth variant was never graded.** Prepending a failing command to the
  PowerShell probe rather than replacing it survives, because a non-terminating
  error leaves exit 0 and the contract is the payload rather than the script
  text. Its author judged it a non-defect and correctly declined to grade its
  own work. Nobody has ruled on it since.

- **OPEN. Six of seven mutant kills in the task-liveness slice rest on the
  builder's own word.** The merger independently re-ran exactly one, M12, and
  the builder's KILLED was WRONG as stated - it survived in the value-nulling
  form and needed a second arm. The other six were not re-run. Treat the
  seven-of-seven claim as one verified and six unaudited.

- **OPEN. A sibling's refutation rests on a premise that sibling declines to
  assert.** Sibling-D refuted its own tracked-wiring proposal partly on "a
  SessionStart hook that exits non-zero does not get its stdout injected", and
  lists that same proposition under what it is NOT claiming. Unmeasured here
  too. This tree has the adjacent positive control only - exit 0 DOES inject,
  measured in a real fresh clone - which says nothing about the non-zero branch.

- **OPEN. `ops/ResinCompute-Supervisor.xml` has never been registered on this
  machine**, and its comment about XML encoding is wrong - measured 2026-09-07
  while registering the responder task. `Register-ScheduledTask` takes a .NET
  string, so the declaration must say UTF-16. The supervisor task would fail to
  register today for the same reason the responder task first did.

- **DONE 2026-09-08. The SessionStart watcher has an invocation log, so whether
  it fires and survives a clear is MEASURABLE here for the first time.**
  `scripts/watch_inbox.py`, proven by `tests/test_watch_inbox.py`. The first cut
  wrote that log FROM THE TEST SUITE under the same source label a real firing
  uses, so the instrument forged its own evidence. Root cause, and it
  generalises: an isolation fixture that monkeypatches module attributes cannot
  isolate a SUBPROCESS, which re-imports the module with the real defaults.
  REMAINING: taking the measurement needs a future cold session; the log makes
  it possible and does not itself answer it.
- **DONE 2026-09-07 (third session). The row-scoped provenance schema landed
  BEFORE the first row.** `core/provenance.py`, `docs/PROVENANCE_SCHEMA.md`,
  `data/README.md`, proven by `tests/test_provenance.py`. Independence is
  computable rather than asserted, a NOT_FOUND row without a sampling rate is
  refused, and a row carrying a forbidden key is refused. `core/types.py` was
  not touched. THE REMAINING WORK is the first real consumer: nothing writes a
  row yet, and a schema with no producer has never met a real value.
- **DONE 2026-09-07 (third session). Noelle was found, and the recorded window
  was the reason she was not.** 09:07:38.533Z to 09:07:39.667Z, card 1 of the
  first Beginners' Wish 10-pull, swept at 15.000 fps over 129180 frames with
  two non-OCR positive controls. `observations.jsonl` line 9 claimed the banner
  read 20/20 at 09:12:09Z; it reads 10/20. That false bound put the search
  window about thirteen minutes AFTER the event, so no sampling rate could have
  found her. The record was superseded in place with all eight original fields
  preserved byte-identical. **A CAVEAT THAT IS CORRECT CAN STILL BE THE WRONG
  EXPLANATION, and a plausible one stops the search.**
- **NEW 2026-09-07 (third session). The remaining capture-store work is the
  OTHER nine observations.** Only line 9 was re-measured. The store is still
  15 GB at `C:/rsc-first-run/` outside this tree, 6062 file events over 5971
  blobs, 1542 screenshots, 29 video segments. Every other observation was
  recorded by the same process that got line 9 wrong and none has been
  re-checked against the full-rate sweep. Do that before any of them is trusted
  into `data/`, and do it before any segment is pruned.
- **NEW 2026-09-07 (second session). An OCR-only extractor returns a confident
  zero on the most important frame in the corpus.** Tesseract missed
  "Obtained New Character / Dehya" entirely - stylised font over a full-screen
  fire effect. Any roster or acquisition extractor built from here must combine
  OCR with something else, and an OCR zero over game splash text must never be
  reported as an absence.
- **NEW 2026-09-07 (second session). The wish-history API lags about an hour and
  the roster does not.** Both were pulled and both were right; editing the
  puller to chase the lag would have been fixing a correct client against a
  lagging server. Any future ingest must model the two as separate lanes with
  separate freshness, and must record `retcode 0 with total 0` as a measured
  zero rather than as a missing file.
- **DONE 2026-09-07 (third session). The four root-walking guards can see a
  nested checkout now**, proven by `tests/test_guard_worktree_exclusion.py`
  against REAL `git worktree add` checkouts rather than a planted marker file.
  On main without the fix, identical worktrees drove 6 failures; with it, none.
  A linked worktree's `.git` is a FILE, so the predicate uses `.exists()`.
  REMAINING: the shared `swept_files` predicate lives in a TEST MODULE and four
  guards import it from there. `tests/conftest.py` is its right home and that is
  a small self-contained slice.
- **NEW 2026-09-07 (third session). A guard that asks "does everything EXIST?"
  fails GREEN on a leftover worktree, and nobody here has swept for that
  direction.** A sibling measured it: a duplicate tree only ever ADDS files, so
  a guard asking "does anything match?" goes falsely RED and announces itself,
  while a guard asking "does everything exist?" goes falsely GREEN and never
  does. Only one of the two is caught by leaving a worktree in place and running
  the suite. This tree has not been triaged in that direction.
- **NEW 2026-09-07 (third session). `SHARED_SHA256` hashes only this repo's own
  disk, so the suite reads green while the byte-identity contract is
  divergent.** There is no cross-carrier arm at all. A guard that can only see
  its own disk cannot detect divergence, and the whole point of that pin is a
  property of three disks. A sibling's arm reads carrier roots from a gitignored
  per-host config and SKIPS when none is present - which still reads as green,
  so the shape needs care rather than copying.
- **NEW 2026-09-07 (third session). The un-clearable-withdrawal check has NOT
  been run here.** A sibling shipped a withdrawal report whose four arms all
  passed and which could never be CLEARED, because the acknowledgement pruned
  the seen record and not the report record the withdrawal set derives from.
  Their arms asserted a withdrawal REPORTS and never that it STOPS reporting.
  The check is one command rather than a test: report, acknowledge, report
  again. **AN ARM THAT PROVES A THING APPEARS IS NOT THE ARM THAT PROVES IT CAN
  GO AWAY.**
- **NEW 2026-09-07 (second session). Enka is now reachable in principle.** The
  UID is known and verified four ways, the region is `os_usa` verified from the
  game's own iplist filename. Enka still needs Adventure Rank 10 and an OPEN
  showcase, neither of which is true yet, so `ingest/enka_client.py` remains
  unexercised against a real profile. That is the first thing to try next
  session, and it is the only route to a real roster payload rather than an
  OCR'd one.
- **NEW 2026-09-07 (third session). THE DELETE-AND-RECREATE IS PLANNED, AGREED
  BY THE OPERATOR, AND NOT YET RUN.** This repository is public and was flipped
  public without a name scrub. The tracked tree is now codenamed and carries 0
  full-name hits, but that is only the working tree: 27 of 64 commit MESSAGES
  still name a sibling, and prior blobs stay retrievable by SHA. Measured here:
  0 `refs/pull/*/head` on the remote, 0 stars, 0 forks, 0 issues. **THE ORDERING
  TRAP: the scrub commit publishes a diff that IS the mapping.** Scrub, push,
  then delete would publish the key and deleting afterwards would not unpublish
  it. The order is: rewrite history so no commit ever held a sibling name AND no
  commit is the scrub itself, then delete the remote, recreate, push once. The
  round was put to the fleet and has not answered yet.
- **NEW 2026-09-07 (third session). THE CODENAME LETTERS ARE A ONE-GUESS RULE.**
  The assignment is not monotonic by port or by alphabet, which is what was
  claimed - but an adversary observed the permutation of letter indices is
  even-letters-ascending then odd-letters-ascending. Recorded rather than
  re-shuffled, because re-lettering now rewrites 74 files to buy ambiguity the
  operator has already ruled is not the point. If the delete-and-recreate goes
  ahead, re-letter in the SAME pass - it is free there and expensive later.
- **NEW 2026-09-07 (third session). One guessable token survives the scrub and
  needs an operator ruling**: the shared machine is called "the Legion box" in
  `README.md` and `docs/adr/ADR-004-port-block.md`. That is a MACHINE name, not
  a project name, so it was outside both scrub slices' stated instruction.
  Widening a scrub past its stated scope is how a guard's regex gets quietly
  broadened, so this was raised rather than done. The comment in
  `tests/test_machine_identity.py` that used to spell out WHY the word is
  ambiguous has been removed: an explanation of why a token was kept
  republishes the token, which is the same defect as a gate quoting the
  credential it caught.
- **NEW 2026-09-07 (third session). The bootstrap output directory under `data/`
  is not gitignored.** `.gitignore` excludes only the cache directory, the tmp
  glob and the account-state file - none of them named here with backticks,
  because a backticked path under a tree root must be tracked and these must
  never be. `scripts/bootstrap_data.py` writes its default account snapshot into
  a bootstrap directory under `data/`. The CRLF half of that hazard is fixed and
  guarded,
  but the file is still TRACKABLE, and an account snapshot is exactly the shape
  of thing that must never be committed. Decide whether it is ignored or whether
  the writer is forced outside the tree the way `tools/wish_authkey.py` is.


- **NEW 2026-09-07. Two guards were fixed and a THIRD class was opened: a guard
  whose scope is narrower than the scope its instructions imply.** `mypy` checked
  26 of 92 tracked `.py` while `.claude/agents/builder.md` told every builder to
  run it before reporting done and `adjudicator.md` listed it among the criteria
  for grading an arbitrary slice. Both corrected, `tests/test_mypy_scope.py`
  added. **The remaining work is the other four dark roots**, whose cost was
  measured by adding each alone: `surface/` 1 error, `headless/` 3, `ops/` 8, and
  `scripts/` BLOCKED by a duplicate-module-name refusal that needs an
  `__init__.py` first. `mypy.ini` records each. Bringing one in is a small,
  self-contained slice.
- **NEW 2026-09-07. The standing ref check is `git branch -a`, not
  `git worktree list`.** Two stale `worktree-agent-*` branches from earlier
  sessions were found as refs with no worktree attached; `git worktree list`
  reported none. They held 0 unique objects this time, which is luck - a worktree
  branch from a session predating a history rewrite is exactly the ref that
  resurrects a purged blob. Worth a guard, or at minimum a line in the wrap
  ritual.
- **NEW 2026-09-07. Sibling-A asked every repo to re-read the rationale beside
  its own watcher fix.** Sibling-A's own module carried a paragraph DEFENDING
  the name key whose central claim was exactly inverted - it said a content
  hash would hide an edit, when an edit changes the content and therefore the
  hash. This tree's equivalent paragraph was checked and is sound. The
  generalisation is worth adopting as a review habit: **a wrong rationale is
  more durable than a wrong line of code, because it answers the next reader's
  question before they ask it**, and Sibling-A's conclusion that such a
  paragraph must be DELETED rather than reworded is right - a reworded
  rationale keeps the authority of the original.

- ~~**The publish sweep, the history rewrite and the remote rebuild.**~~
  **DONE 2026-09-06.** Six adversaries on distinct lenses, ALL SIX REFUTED. Four
  builder slices on a proven-disjoint write-list, 12 files, zero violations.
  Full detail in `docs/LEDGER.md`; the parts that change what a future session
  should do:
  - **A force-push does NOT purge objects from GitHub.** Two commits
    force-pushed away still served a `Claude-Session:` URL, and the account path
    sat in 8 of 33 pushed commits. The fix was rewrite locally, DELETE the
    remote, recreate, push clean. Verified server-side: HTTP 422 on the orphans,
    404 on the blob, and a cold clone carrying 0 account-path blobs of 291. If
    anything must ever leave this history again, that is the only procedure that
    works.
  - **An object purge is true only at the instant it is measured.** The leaked
    blob returned three times - a `FETCH_HEAD` from a bundle fetch, a
    `refs/remotes/origin/main` surviving in `.git/packed-refs`, and agent
    worktrees checking out the pre-rewrite commit into the shared object store.
    Re-verify after anything that can create a ref.
  - `shell/package-lock.json` had declared the project unlicensed since the
    GPL-3 switch, and the guard added in that same commit swept 5 files of 153.
    Now derived from `git ls-files`; that file went 33 arms to 41.
  - Both CI ASCII gates passed any path containing a space, and 14 tracked files
    were scanned by neither gate. Coverage is now 153 of 153, uncovered set
    empty, halves disjoint.
  - The exclusive-bind fix was ported to `agents/pity_engine/__main__.py`, which
    had kept the stock server since the surface fix landed at one call site.
- ~~**Check the fork-PR approval setting the moment the repo goes public.**~~
  **DONE 2026-09-07. The risk was already closed.**
  `gh api repos/Remus3/Resin-Compute/actions/permissions/fork-pr-contributor-approval`
  returns `{"approval_policy":"first_time_contributors"}`. A stranger's first
  pull request requires manual approval before any workflow runs, so the
  `pip install -r requirements-dev.txt` route to runner code execution is gated
  by a human click rather than open at the flip. Re-check it if anyone ever
  loosens it: the setting is invisible while a repo is private (422), which is
  why this could not be verified in advance.
- ~~**Prove the hook gate fires, in CI.**~~ **DONE 2026-09-07, and it ran on a
  real runner.** `tests/test_hook_gate.py` stands up a throwaway `git init`,
  copies the real hook bodies plus the four dependencies they source, and
  asserts on HEAD: a clean ASCII commit LANDS, a banned glyph in staged content
  is REFUSED, a banned glyph in the commit message is REFUSED. Without the
  positive control a gate that refused everything would pass both negatives.
  Observed on `ubuntu-latest`:
  `armed: .githooks/commit-msg .githooks/pre-commit .githooks/pre-push (all mode 100755)`
  then `12 passed in 0.75s` - ran, not skipped.
  - **An adversarial pass then REFUTED four claims made ABOUT that work, and all
    four are corrected in the tree.** `RSC_REQUIRE_HOOK_GATE` does NOT convert
    an unconfigured clone: the fixture arms its own throwaway repo and never
    reads the host checkout's `core.hooksPath`, so an unconfigured clone passes
    12 of 12. What the flag converts is an UNMEASURABLE MACHINE - no POSIX `sh`,
    no git, or a missing hook file to copy. The dependency scan matched `$ROOT/`
    but not `${ROOT}/`, so a brace-form dependency would have gone uncopied while
    the rot guard stayed green. The positive control went RED when the pinned
    interpreter could not `import ruff`, blaming the gate for a contributor's
    venv layout. And the docstring claimed a `GIT_*` scrub wider than it
    performs, citing a mechanism `git 2.53` does not exhibit.
- ~~**Wire the inbox watcher so it actually fires.**~~ **DONE 2026-09-07.**
  `scripts/watch_inbox.py` was correct and connected to NOTHING - there was no
  `.claude/settings.json` in this tree at all, so it ran only when a human typed
  it. A declared hook is not a firing hook, and the quieter predecessor is that
  an unwired script is not a watcher. Now a `SessionStart` hook, with
  `.gitignore` gaining `!.claude/settings.json` so the wiring reaches a fresh
  clone rather than living on one box. `tests/test_session_hooks.py` EXECUTES
  each declared command rather than resolving its target.
- ~~**CAVEMAN ULTRA as the default chat dialect.**~~ **DONE 2026-09-07**, on
  operator instruction, after RSC filed a dissent that the operator overruled.
  `tools/caveman_default.py` and `tools/caveman.md` are Sibling-C's bytes,
  not a paraphrase; the `_BANNER` string is a FLEET CONTRACT and its sha256 is
  pinned as a literal in `tests/test_session_hooks.py` rather than diffed
  against the copy in `moon_sync_inbox/`, which is gitignored and would take the
  guard silent in every fresh clone. Terseness is CHAT ONLY - committed
  artifacts stay byte-exact.
- ~~**Gate the hand-off write for credentials and account paths.**~~
  **DONE 2026-09-07.** Sibling-E asked whether anyone gated the hand-off
  more widely than ASCII and truncation; this tree's honest answer was no, and
  it was MEASURED: a block carrying an inline API key and a block naming the
  real account each published clean to the Desktop. That is the one write that
  leaves the toolchain - pasted into cold sessions, quoted into four sibling
  repos, from a public repo. `tools/publish_next_session.py` now refuses both,
  and the refusal never echoes what it caught.
- ~~**No tracked file may carry a credential.**~~ **DONE 2026-09-07.**
  `tests/test_no_secret_literals.py` sweeps 160 tracked files for
  vendor-prefixed tokens and for known secret names bound to literals. It
  deliberately does NOT flag the sha256 governor pins, the base64 tray icon or
  an environment lookup - a guard that flagged those would be deleted within a
  day. All five repos were swept and were already clean; the one real key lived
  in the user-level `~/.claude/settings.json` and is now a Machine environment
  variable.

- ~~**Port Sibling-C's claim gate.**~~ **SUPERSEDED 2026-09-07 - THE SOURCE IS
  GONE AND IT WAS REBUILT INSTEAD.** Sibling-C DELETED its verbatim
  subdirectory, `moon_sync_inbox/from-<sibling>-verbatim/`, from all four
  sibling trees after Sibling-A found the operator's account name in 3 of its
  48 files and Sibling-C's own sweep raised that to 19 of 48, including
  `tests/test_stop_claim_gate.py`. Containment here was measured: 0 tracked
  files, 0 commits by pickaxe, 0 additions of any of the four named tool
  filenames. `tools/stop_claim_gate.py` now exists, re-implemented from
  Sibling-C's published PROSE with no Sibling-C code read. Detail in
  `docs/LEDGER.md`.
- **ARM THE CLAIM GATE, once its false-positive rate is low enough to deserve
  it.** It landed at `2b8fcbe` DELIBERATELY UNWIRED - no `Stop` hook is
  declared and `.claude/settings.json` is untouched - because the producer's
  own un-adjudicated measurement is **55.5 percent false** over 317 real
  transcripts. Sibling-C published the reason not to arm it: a gate that cries
  wolf on correctly-sourced figures trains the reader to wave it through, which
  is exactly when it stops catching the real thing. Three things must happen
  first, in this order:
  1. **An INDEPENDENT pass must measure the rate.** 55.5 was measured by the
     agent that wrote the chaining, which is the one grading arrangement this
     tree does not accept.
  2. **Characterise the residual.** The 64.1 -> 55.5 improvement came from
     one-hop chaining. Nobody has yet classified what the remaining false
     positives ARE, and that classification is what decides whether a fourth
     mechanism is warranted or whether the gate is at its ceiling.
  3. **Verify the Stop-hook contract against this harness.**
     `TRANSCRIPT_PATH_KEY = "transcript_path"` and `BLOCK_EXIT_CODE = 2` are
     both GUESSES, recorded in the module's `OPEN` section. Arming on an
     unverified stdin key produces a gate that exits cleanly and checks nothing.
- **Sibling-C still owes the claim-gate spec, asked by note 2026-09-07 and
  unanswered.** Six questions: the full finding taxonomy, the evidence model,
  the recognisers, what the gate reads and how, the verdict contract, and the
  two lessons Sibling-C has already published restated so they are implemented
  rather than rediscovered. Three build rounds have now mapped the failure
  modes precisely enough that an answer would land on prepared ground.
- **The three smaller ports are BLOCKED on the same withdrawn payload.**
  `pytest_guard.py` (a `PostToolUse` py_compile - this tree still has ZERO
  PostToolUse hooks and its only compile gate fires at commit time),
  `edit_lint_check.py` (whose glyph half must CALL `tools/precommit_gate.py`
  rather than restate the six codepoints), and two checks out of
  `drift_guard.py` - `check_counted_claims` and `check_untracked_authored`.
  Sibling-D has asked the channel to stop sending source and send descriptions,
  and this tree AGREED, so the route is a prose spec rather than a redacted
  re-drop.
  - **Do NOT port Sibling-C's `md_guard_selector.py` or its ASCII source
    sweep.** Triaged and rejected: this tree's `docs-guards.yml` already
    derives the md-reading guard set from `git ls-files` with an unbucketed
    hard-fail, and `ci.yml` already sweeps tracked source through
    `precommit_gate.py --expect-count --scan-tracked source`. Sibling-C's ASCII
    file is a ratchet over a frozen 50-file baseline, strictly weaker than what
    runs here, and Sibling-C's own docstring credits this tree for the shape.
- **Answer the reserved-slot design once RSC actually acquires a slot.** RSC
  concurred with a stated reservation on 2026-09-07: nothing in this tree
  acquires, `headless/runner.py` is a job runner rather than a Claude-executor
  loop, so a guaranteed lane reserved for RSC is capacity removed from the four
  repos that really contend. Revisit if that changes.
- **`moon_sync_inbox/` and its SUBDIRECTORIES are session reading now**, per
  operator instruction 2026-09-07 recorded in `CLAUDE.md`. The 2026-09-06
  session read notes and skipped the verbatim subdirectory, which held 49 real
  files while the notes beside it only described them.
- **Prose accuracy is structurally unguarded, and three of this session's
  findings were prose.** `tests/test_docs_consistency.py` says so in its own
  header: it checks that pointers RESOLVE, never that a sentence is TRUE. The
  false unlicensed-lockfile claim, the false "synthetic fixtures" claim and the
  "one thing that writes outside the tree" claim were all caught by a human-shaped
  read, not by a gate. No test can express "this sentence is false" in general,
  but the specific shape that recurs here IS checkable: a document asserting a
  property of a file that the file itself contradicts. Worth one guard over the
  claims that name a path.
- ~~**`agents/pity_engine/CHANGELOG.md` needs an entry for the exclusive
  bind.**~~ **DONE 2026-09-07**, `1794a5e`. A new "Service changes at engine
  revision 0.1.0" section, because the file's convention is that a bump PREPENDS
  and a prior version's line is never extended. `ENGINE_VERSION` deliberately
  does NOT move: it is the COMPUTE revision, every forecast is byte-identical
  across the change, and bumping it would have invalidated correct caches. The
  entry also records which half is load-bearing, which was MEASURED and is not
  the one the name suggests - `first=none` and `first=exclusive` are identical
  columns in the nine-cell matrix, so dropping `SO_REUSEADDR` is what closes the
  defect and `SO_EXCLUSIVEADDRUSE` changes no observable outcome here.
- **Answer Sibling-C's charter, round by round.** v3 is ADOPTED with one
  dissent filed and accepted; v4 arrived at the end of this session and is
  UNREAD. `scripts/watch_inbox.py` exists now, so the next session can see what
  is genuinely new: `python scripts/watch_inbox.py`. The watermark was
  deliberately NOT marked at the end of this session - 42 notes are listed and
  roughly ten were actually processed, and an inflated watermark is worse than
  none. Triage, then `--mark`.
- ~~**QA the repo for going public.**~~ **DONE 2026-09-06.** The audit ran at
  commit `57f8894` and every gate was green before a line was touched, so none of
  it was a broken build - each item was a defect a stranger would meet. Every one
  is now fixed and guarded. What landed, with the guard that holds it:
  - **Two fixtures were labelled false, and the label WAS the compliance claim.**
    `data/fixtures/seed_roster.json` and `seed_materials.json` opened with
    `"_synthetic": true` on the line directly above a `"_note"` calling them
    hand-authored. They now carry `_hand_authored`, `_vendored` and `_content`
    blocks stating what they are: publicly known game facts, independently
    verified, typed in one row at a time. `data/fixtures/README.md` is retitled
    and now names which of its three files is which kind -
    `enka_sample_profile.json` IS genuinely synthetic and keeps that label.
    Synthetic means invented, and a verified avatarId is not invented. The true
    claim was also the stronger one. Guarded in
    `tests/test_licence_posture.py`, which went from 21 arms to 33.
  - **The dissolved ADR-006 reason is qualified everywhere it appears.**
    `README.md`, `ingest/enka_client.py`, `docs/SPEC_SCAFFOLD.md` and
    `data/fixtures/README.md` each stated that vendoring `enka-py` or `ambr-py`
    "would relicense this repo" - void since this tree became GPL-3-or-later.
    Each now carries the dissolution note in the shape `docs/LICENSE_NOTES.md`
    already used, and the refusal STANDS: both wrap HoYoverse data and a licence
    on a wrapper cannot grant rights to the payload.
    **A sharper instance the audit missed was found and fixed in the same pass:**
    the GENERAL RULE in `docs/LICENSE_NOTES.md` - "GPL and other copyleft stays
    DO-NOT-VENDOR ... because vendoring it would relicense this repo" - was the
    version a future contributor actually applies, and it was flatly false for a
    GPL-3 tree. It now says what replaced it: the question is no longer the
    licence but the PAYLOAD, and a GPL-2-only library remains an automatic bar
    on incompatibility grounds.
  - **`NOTICE` gained the GPL-3 warranty disclaimer**, taken verbatim from the
    appendix in `LICENSE` rather than retyped, plus a trademark acknowledgement
    naming the marks and a statement that this is a non-commercial companion
    tool. A guard matches the disclaimer against the text READ FROM `LICENSE` at
    run time, so the two can never drift.
  - **The docs guard now tests TRACKEDNESS, not just presence.**
    `tests/test_docs_consistency.py` called `.exists()`, which is true for a
    directory git does not store - exactly how `docs-guards` went red on the CI
    runner while the same test was green locally. It now also asserts every cited
    path is in `git ls-files`, with non-vacuity proven at the predicate level and
    no tree mutation. 16 arms to 23. It caught a real unstaged-citation case
    within minutes of landing.
  - **The same root cause had two siblings, and both are fixed.**
    `tests/test_ports.py` had a function NAMED `_tracked_python_files` that did a
    filesystem `rglob` behind an ad-hoc denylist. It was GENUINELY RED in the
    main checkout, and it would go red for any contributor who created a
    `.venv/`. It now derives its list from `git ls-files`. The third sibling was
    `tests/test_shell_contract.py`, latent rather than red because its assertions
    were floor-shaped and so could not detect over-collection.
  - **The Windows account name is out of `.claude/commands/done.md`** and can no
    longer come back: `tests/test_machine_identity.py` sweeps every tracked file
    for an absolute path naming a real account, across Windows, POSIX and
    MSYS/WSL/Cygwin mount spellings. It carries BOTH guards - the leak is gone
    AND the legitimate neighbours survived - with a by-name allowlist for the
    synthetic `x` fixture in `tests/test_make_shortcut.py` and the `<account>`
    documentation placeholder. Nothing in the tree had ever guarded that line in
    either direction.
  - **The README now opens for a stranger.** What it is, what state it is in,
    what it deliberately does NOT do, and the non-affiliation disclaimer on the
    first screen instead of the last. The repository tree is refreshed and
    guarded by `tests/test_readme_tree.py` - one-directional by design, so an
    added ADR cannot turn it red. The quickstart is PowerShell throughout, since
    `export VAR=...` is not PowerShell and `curl -s` resolves to
    `Invoke-WebRequest`. The machine name is gone and the space-containing path
    is reframed as the deliberately exercised test case it actually is. The
    Enka example UID is annotated at the use site.
  - **`docs/SPEC_SCAFFOLD.md` no longer says a slice is done "from
    `resin-compute/`".** The relocation premise is gone from the build contract.
  - **Per-file licence headers: DECIDED, in `docs/adr/ADR-009-per-file-licence-headers.md`.**
    The answer is NO, on the merits, with named re-open triggers. Measured at
    `58c02b4`: 80 tracked `.py`, 10 tracked `.js`, and zero SPDX identifiers in
    any source file - the only occurrences anywhere are in ADR-009 itself,
    discussing them. GPL-3's
    "How to Apply These Terms" sits at LICENSE line 623, AFTER
    `END OF TERMS AND CONDITIONS` at line 621, so it is advisory; section 5(b)
    binds the work and a modifier rather than the file and the author. Below
    best practice, NOT non-compliant. The one real cost of omitting is recorded
    honestly: a single file copied out of the tree carries no licence signal.
- ~~**The licence gate's four text defects.**~~ **DONE 2026-09-06,** except that
  the fan-content arm turned into something much more interesting - see the entry
  below, which supersedes it. The other three are closed above.
- **Close the fan-content evidence hole, and watch for a Genshin guide.** The
  posture is decided and recorded in `docs/adr/ADR-008-fan-content-posture.md`
  (operator decision 2026-09-06: publish on the vendoring argument alone). Two
  residuals stay open. FIRST, three first-party PDFs were never read - a zh-CN
  Terms of Service, the Genshin Creator Program Official Rules, and the HoYoPlay
  Terms of Service - and their URLs are recorded nowhere, so the hole is not even
  reproducible. `pdftotext` version 4.00 IS on PATH, so the earlier claim that no
  renderer was available was false; re-derive the URLs and read them. SECOND,
  ADR-008's re-open triggers are live, and the likeliest is a "Genshin Impact Fan
  Creations Guide" appearing on HoYoLAB - Honkai: Star Rail has one and Zenless
  Zone Zero has one, and Genshin, the oldest title, does not.
  **Read ADR-008's method warning before doing either.** The research pass this
  supersedes was wrong in three separately checkable ways and was caught only
  because something was dispatched to refute it.
- ~~**The suite could not run for anyone who received the repo without git.**~~
  **DONE 2026-09-06.** `git archive` plus `pytest tests` aborted at COLLECTION,
  exit 2, zero tests run - what a reader gets from Download-ZIP, an sdist or a
  vendored copy. Introduced by this session's own trackedness fixes, which took
  the number of git-dependent test files from 3 to 8 with nothing testing the
  absent-git case. `tests/conftest.py` now provides the skip helpers, and a
  cross-check in `tests/test_commit_trailers.py` fails if the skip path is ever
  taken inside a real checkout. Fixing it exposed a second, pre-existing defect:
  `tests/test_hook_interpreter.py` embedded a quoted path in an `sh -c` string,
  which MSYS mangles at any path WITHOUT a space - so it passed here and would
  have failed for anyone cloning to `C:\dev\ResinCompute`. Both fixed and
  measured: archive now 692 passed, 50 skipped, exit 0.
- **Two guards claim more than they sweep. Found by the quickstart adversary at
  `58c02b4`, both measured.**
  - `tests/test_ports.py` sweeps ONLY `.py` files, because it uses `ast.parse` to
    tell a live integer literal from one inside a comment - which is the right
    mechanism and the reason it cannot simply be widened. The gap it leaves is
    real: `requirements.txt` stated the engine was on `:8870` in the PRESENT
    TENSE, the pre-ADR-004 port inside a sibling project's block, and no guard
    saw it because a `.txt` has no AST. The text is fixed; the gap is not. A
    prose-level sweep for sibling port literals in non-Python tracked files needs
    its own mechanism and its own two guards - the legitimate neighbours here are
    the many DELIBERATELY historical mentions of 8870 in `docs/adr/ADR-004-port-block.md`,
    `docs/LEDGER.md`, `core/ports.py` and `README.md`, which must survive.
  - `tests/test_goal_spec.py` keeps unverified cost figures out of `data/` with a
    denylist of four numeric literals plus one material name. It fires correctly -
    proven by probe - but `docs/GOAL_SPEC_SEED_TEAM.md` section 3 carries more
    unverified figures than the denylist names. A denylist of remembered values
    is the same shape as the ad-hoc ignore lists this session removed. The
    durable fix is to derive the forbidden set FROM the goal spec's own
    unverified stamps rather than restating it by hand.
- **One instance of the trackedness root cause is left, and it is the mild one.**
  `tests/test_docs_consistency.py` now derives its trackedness PREDICATE from
  `git ls-files`, but it still enumerates its docs CORPUS - which `.md` files to
  read - with `rglob`, at lines 172, 200, 231, 295, 306, 326 and 381. Found by
  the verification pass at `58c02b4`. This is NOT a blind spot in the dangerous
  direction: a tracked file in a clean checkout is always present, so the walk is
  a superset and nothing tracked escapes it. The exposure is the opposite one - a
  contributor with an untracked scratch `.md` under `docs/` gets it graded, and a
  red suite for a file that is in nobody's clone. Same fix as the other three:
  ask git. Left open deliberately rather than swept in at the end of a long
  session, because the other three were each done TDD-first with a staged red and
  this one deserves the same.
- **A visibility pass, once the repo is public.** Adapted from a sibling
  project's own pass, NOT copied: its topic names and its game are not ours, and
  a lever list is transferable where a keyword list is not. Ranked by leverage:
  set repository TOPICS, which are currently unset and are the highest-value
  free action; add a `CITATION.cff` so GitHub renders a "Cite this repository"
  button; cut a first tagged release as a dated, quotable snapshot; surface a CI
  badge, because the suite counts are the fastest signal that this is an
  engineering project rather than a wiki scrape; add an issue template that
  demands provenance fields on any observation report; and a social preview
  image, which is web-UI only and not scriptable. GitHub's community-health
  score will read low until `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and the
  templates exist - decide which of those earn their place rather than adding
  ceremony. **Do NOT enable Discussions in the same pass.** The sibling's
  reasoning transfers exactly: inviting users to paste raw payloads farms other
  people's PII into a public repo, and here the payload is an Enka response
  carrying a real UID and roster. That needs a redaction path for outsiders
  first.
- **Row-scoped provenance for `data/costs/`, not document-scoped.** The
  directory contract today asks for a `source` field per row. That is the right
  instinct and it is not sufficient, and the argument comes from a sibling
  project that hit it first. Facts are not copyrightable - there is no
  sweat-of-the-brow right in a measured number - so a cost table derived
  first-hand has exactly the same copyright status as one a wiki invented. What
  distinguishes it is not a licence and cannot be one. It is that the RECEIPT
  travels with the number. A table lifted out of a document arrives downstream
  with no method, no date and no game version, at which point it is
  indistinguishable from fandom content and a stranger is right to treat it so -
  and worse, it gets laundered back as an uncited claim the original has to
  compete with. The fix is a machine-readable emission where every record
  carries its own receipt: the observed value, the method, the game version it
  was read on, the date, and whether it has been reconfirmed on the current
  version. Three things fall out of it that prose cannot give: the consuming
  engine can treat provenance as load-bearing input, so "unmeasured" stays
  distinguishable from "measured zero"; a staleness warning stops being a
  paragraph and becomes a query; and freshness becomes the durable advantage,
  because a wiki number is stale by construction and cannot know it. Needs a
  stated schema BEFORE the first row lands, on the same principle as artifact
  scoring. Acceptance: the schema, plus a guard that rejects a row missing any
  receipt field. This does NOT relax
  `docs/GOAL_SPEC_SEED_TEAM.md` section 3.1 - first-hand observation is still
  the only acceptable source and the unverified web figures still must not
  enter `data/`.
- ~~**Session shape and the agent roster.**~~ **DONE 2026-09-06.** The default
  session is orchestrated, multi-agent, self-adjudicating and self-adversarial;
  the reasoning is in ADR-007 and the roster lives in `.claude/agents/`. The
  `/done` ritual is `.claude/commands/done.md`, and
  `tools/publish_next_session.py` publishes the Desktop backup of the hand-off
  from `NEXT_SESSION_PROMPT.md` so the printed block and the file cannot
  disagree.
- **Observe the seed-team cost table in game.** `docs/GOAL_SPEC_SEED_TEAM.md`
  records the operator's roadmap with every claim stamped verified, unverified,
  time-sensitive or refuted, and section 3.1 is the gate on a real dated plan.
  The account has not been played yet, so no first-hand observation exists and
  the three cost figures that arrived from a web assistant are deliberately NOT
  in `data/` - `tests/test_goal_spec.py` fails if they get copied in.
- ~~**Persist the reconciled account state.**~~ **DONE 2026-09-06.**
  `core/state_io.py` serializes `AccountState`, the `persist_state` job writes it
  through `core/atomic_io.py`, and `surface/` cold-starts from it and renders how
  old the reading is. The snapshot is WRITE-ONLY from the headless lane so
  live-state-first still holds, and a test asserts that structurally rather than
  documentarily.
- ~~**Repo relocation.**~~ **DONE, verified 2026-09-06.** The scaffold was built
  inside the Sibling-C repository because the session's GitHub integration
  could not create a new repository (`POST /user/repos` returned 403 Resource
  not accessible by integration). It now stands alone and the claim that "the
  CI workflows are inert" was measured false and removed:
  `git rev-parse --show-toplevel` returns the tree root, `git remote -v` returns
  `github.com/Remus3/Resin-Compute`, `.github/workflows/ci.yml` carries no
  `working-directory` and its paths are already repo-root relative, and
  `gh run list` shows `ci` and `docs-guards` both green against this tree. One
  stale premise survives the move and is listed under the public-repo QA item
  above: `docs/SPEC_SCAFFOLD.md` still says a slice is done "from
  `resin-compute/`".
- **Wire the objective DAG to real material costs.** `engines/objectives.py` is
  mechanism only and takes materials as a caller-supplied argument. Nothing
  currently supplies them. This needs a licensed or first-party cost table, which
  is gated on the data-source question in ADR-002.
- **Ascension and talent cost tables.** Same gate. The level-cap table (20, 40,
  50, 60, 70, 80, 90) is encoded; the Mora and material quantities behind each
  step are not.
- **A real end-to-end goal.** The brief's worked example - ascend a character to
  60 with 6/6/6 talents and a weapon at 60 - should run start to finish and emit a
  dated task list. It currently decomposes into a correct DAG with empty costs.
  Verified 2026-09-06: the expansion produces exactly 30 nodes for Arlecchino at
  level 60 with 6/6/6 and a weapon at 60, in four dependency chains, and the
  character chain reaches ascension phase 4 because the talent gate demands it
  rather than because level 60 does. The scheduler has no dating layer yet, so
  `ScheduledTask.earliest_day` is a day offset and nothing turns it into a date.

- **OPEN, SIX ITEMS FROM THE 2026-09-08 INBOX TRIAGE.** The full bucketing is in
  `docs/INBOX_TRIAGE_2026-09-08-1834.md`; these are the applicable-and-not-done
  rows, which are the only bucket that belongs here. An untriaged file is
  indistinguishable from a rejected one, so the other three buckets are recorded
  there rather than dropped.
  1. **This roadmap claims twice that our `refs/pull` zero has "a positive
     control" and names no subject.** A sweep of the roadmap, the ledger and the
     README found zero named repositories and zero `ls-remote` commands behind
     that phrase. A positive control that names nothing is the false-clean
     pattern this tree has recorded five times, sitting in our own paperwork. A
     sibling retracted the identical defect in its own note.
  2. **The watcher names the tree only when the inbox is ABSENT.** Measured: run
     relatively from a worktree it reports no inbox and names the path; invoked
     by absolute path from that same worktree it reports the main tree's inbox
     and names no tree at all. So the one line that would disambiguate which
     checkout answered is printed only in the case where nothing was found.
  3. **Outbound mail leaves ZERO trace in tracked content.** 21 note names swept
     against every tracked file, whitespace-stripped, with a control that hit 16
     files: no outbound note is referenced anywhere in the repository. The
     sender-side draft store exists but is gitignored, so from a clone the
     outbound half of every conversation is invisible.
  4. **Two path spellings for this checkout sit in the machine config with no
     guard.** A sibling reported them carrying disagreeing trust values; that
     half does NOT reproduce - both read the same on 2026-09-08. The two
     spellings remain, and nothing asserts they agree.
  5. **CLOSED 2026-09-09 by the inbox triage, and the machine note's first
     half is the true one.** It asserted two contradictory facts about our own
     refusal handling. `_remember_answered` is defined at
     `tools/moon_sync_responder.py:1217` and has EXACTLY ONE call site, at
     `tools/moon_sync_responder.py:1868`, inside the delivered branch and
     immediately after the termination is set to delivered. So a refusal never
     touches the answered record and a refused note stays eligible - option (a),
     which is what this tree's own 2026-09-08-1530 note claimed. The note's
     other half, that we had implemented none of this, was already stale when it
     was written and is stale twice over now.
  6. **A sibling's un-clearable-withdrawal check has still never been RUN here.**
     Both halves exist in the code and the acknowledgement path calls them; the
     live report-acknowledge-report sequence was correctly not performed by a
     session with no authority to move the watermark.

## Next

- **Artifact scoring.** `MappedArtifact` parses cleanly but nothing scores a
  substat roll. Needs a stated scoring model before implementation, not after.
- **Banner calendar.** The forecaster answers "given N pulls" but not "by when",
  because nothing knows when a banner runs. A calendar source has the same licence
  gate as the cost tables.
- **Income velocity from real history.** `estimate_velocity` folds observed ledger
  entries, but nothing populates the ledger automatically yet. Wire it to a
  reconciliation job.
- **Chronicled Wish support in the service route.** The engine models it; the HTTP
  route does not expose it.
- **Prove the git hook gate FIRES, in CI.** `CLAUDE.md` says a hook's PRESENCE is
  never proof it fires, and that the only valid test is end-to-end: stage a
  banned glyph, attempt a real commit, assert HEAD unchanged. Nothing automates
  that. `tests/test_hook_interpreter.py` proves the hooks pick a working
  interpreter and `tests/test_commit_trailers.py` proves no trailer reached
  history, but a clean history is equally consistent with "the hook stripped it"
  and "nobody added one". The end-to-end check was run BY HAND on 2026-09-06 and
  passed; a manual pass expires the moment someone edits a hook. Sibling-C has
  a working `git hook gate armed and firing` CI step and has been asked for it
  through `moon_sync_inbox/`. Needs BOTH directions: a banned glyph must be
  rejected AND a clean commit must still succeed, or a gate that rejects
  everything passes the first arm while broken.
- **Acquire a slot when an executor loop exists.** `ops/loop/slots.py` is vendored
  and pinned but NOTHING IN THIS TREE CALLS IT - see the known gap below. When a
  Claude-executor loop is built, wrap each cycle in
  `with slots.hold(int(CFG.get("max_concurrent_lanes", 2)), repo="rsc", ...)`.
  A `SlotTimeout` is a FAILED CYCLE, never permission to proceed unslotted. The
  literal 2 in that snippet is the `dict.get` default, reached only when the key
  is absent; `slots.hold`'s own signature default happens to be 2 as well, but it
  is a different 2. Neither is the governing value, which is
  `core.config.MAX_CONCURRENT_LANES`, and that is 3.

## Later

- ~~**Dashboard.**~~ **DONE 2026-09-06, recorded in ADR-005.** The operator
  specified one and asked for it BEFORE further feature work, so that each
  feature becomes visible as it lands. `surface/` serves it on 8791 and `shell/`
  is the Electron companion with a system tray. ADR-001 was NOT reopened: its
  subject was the language of the compute tree, and the surface is Python too.
  Panels declare their own readiness and a panel that is not live says what it is
  waiting on rather than showing a placeholder number.
- **Containers.** Sibling-C has none, so there was nothing to inherit. If
  containers are wanted, that is a new decision with its own ADR.
- **Multi-account support.** Everything is keyed by a single UID today.
- **Team composition solver.** Elemental reaction modelling is a large piece of
  domain work and should not be started before the resource layer is complete.
  STILL HELD, and the Teams PANEL shipping on 2026-09-11 did not touch it. This
  entry governs the SOLVER and the reaction MODELLING; it never governed the
  panel, and elemental IDENTITY was never gated - `data/fixtures/seed_roster.json`
  is hand-authored and carries an element for all five seed characters, and
  `ingest/static_data.py` ships `element_for`. What `tests/test_surface_teams.py`
  grades is identity only: nothing ranks, scores or recommends.

## Known gaps, stated honestly

- **The concurrency governor is vendored but INERT, and that is deliberate.**
  `ops/loop/slots.py` and `ops/loop/winmutex.py` are byte-identical-by-contract
  with Sibling-E and Sibling-C, pinned by `tests/test_loop_concurrency.py`. NO
  PRODUCTION CODE PATH CALLS `slots.hold()` - the only callers are the five
  sites inside `tests/test_loop_concurrency.py` itself, which exercise the
  vendored module against a `tmp_path` bucket and never against the shared one.
  `headless/runner.py` is a job runner whose daemon mode runs in-process job
  passes on an interval - it is not a Claude-executor loop and it spawns no
  executor. So this is a PARITY CONTRACT JOINED AHEAD OF NEED, not a live
  throttle: the shared bucket is three wide with two real acquirers, and this
  repository's slot is reserved but unclaimed. No loop controller was invented to
  justify the file. Do not read the pinned digests as evidence that this repo
  throttles anything yet.
- **The weapon banner micro-curve is not pinned by public data.** Increments of
  7.0%, 6.6%, 6.0% and 5.8% all overshoot the published 1.850% consolidated rate.
  The increment is exposed as a tunable rather than hidden behind a constant. If a
  better-measured value appears, change the default and update ADR-003.
- **Capturing Radiance's per-loss ramp is unpublished.** Only the 55.000%
  aggregate is official. The engine uses the flat 0.52106 plus forced-win model
  that reproduces it. A published ramp would supersede this.
- **`fetchedProfile` freshness depends entirely on upstream `ttl`.** There is no
  push channel, so a roster change is invisible until the showcase refreshes.

- **Constellation talent bonuses are not always resolvable on a live profile.**
  `proudSkillExtraLevelMap` is keyed by `proudSkillGroupId` while `skillLevelMap`
  is keyed by `skillId`, and joining them needs the character's skill depot -
  exactly the bulk game data ADR-002 forbids vendoring. `fold_talent_levels`
  therefore resolves via a caller-supplied `skill_group_map` or an exact key hit,
  keeps its positional fallback DEFAULT-OFF, and RETURNS anything unresolved
  rather than guessing. Until a licensed depot source exists, a C3+ character's
  effective talent levels are exact only when the caller supplies the mapping.
  Recorded in SPEC 5.1. This is a product limitation, not a bug to fix in code.

- **Intermediate talent-ascension gates are interpolated, not sourced.** The
  contract pins only three points: talent level 1 needs no ascension, above 1
  needs at least A1, and level 10 needs A6. Everything between is derived by
  monotone ceiling interpolation in `min_ascension_for_talent` rather than
  smuggling in unverified per-level numbers.
  `expand_character_goal(talent_gate=...)` accepts a real table the moment one is
  available. Same licence gate as the cost tables. Weapon level caps default to
  the character cap table for the same reason.
