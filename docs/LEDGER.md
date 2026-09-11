# Completion ledger

Append-only, **newest first**, following the parent project's convention. One
entry per landed unit of work, with what was actually measured rather than what
was intended.

`ROADMAP.md` holds OPEN work. This holds CLOSED work. Neither belongs in
`CLAUDE.md`, and a test count belongs in neither: counts are not guarded and a
document is not a source of truth. Where a count appears below it is stamped with
the date it was measured, as a historical reading rather than as a claim about
now.

---

## 2026-09-11 - The instrument could not see a file being created, which is the one shape the bucket it was built to watch actually makes

One commit, pushed: `13c771f`. Four files, 1733 insertions. The honest shape of
this entry is that THE BUILD WAS WRONG AND REFUTATION FOUND IT: the first build
passed every arm it shipped with, and two adversaries with distinct lenses
returned REFUTED on it.

THE HEADLINE DEFECT WAS IN NEITHER DECLARED LIST, AND SILENCE IS THE FAILURE THAT
ARITHMETIC CANNOT CATCH. EMPTY-FILE CREATION WAS INVISIBLE. It was not covered
and it was not declared uncovered, so a reader had no way to discover it. That is
the live shape at `ops/loop/slots.py:189` - lock-file creation in the
machine-wide bucket the halt ruling names by name - and it means a "0 bytes
written" reading taken over that bucket would have come back CLEAN while the lock
files appeared on disk. A true statement about bytes, and a false answer to the
question being asked. There is now a fourth op, `create`, with an arm driving the
real syscall shape. THE GAP WAS CLOSED BY WIDENING THE OP SET, NOT BY WIDENING
COVERAGE, and that distinction is why the instrument still cannot certify that
nothing was written - only that nothing was written through the routes it names.

TWO OVERSTATEMENTS, WHICH IS THE WORST CLASS FOR THIS PARTICULAR INSTRUMENT,
because an instrument whose entire purpose is to stop a negative reading becoming
a false claim cannot afford to overstate its own reach.

(i) THE PRE-ENTRY DESCRIPTOR CLAIM WAS TRUE FOR ONE SUB-CASE AND FALSE FOR THE
OTHER. The draft said a descriptor opened before entry loses PATH ATTRIBUTION
while the BYTES ARE STILL RECORDED. That holds for the raw `os.write(fd, data)`
form. It is false for a FILE OBJECT opened before entry: that object's `write`
reaches the C-level writer with no wrapped name anywhere on the path, so NOTHING
is recorded - not an unattributed event, nothing. Measured on CPython 3.14.4 and
3.11.9 with `open(p, "wb", buffering=0)` before the context and one 9-byte write
inside it: 9 bytes on disk, zero events. The two sub-cases are now separate
entries and the ADR says in terms that they must not be refolded into one
sentence.

(ii) `os.dup2` EMITTED A POSITIVELY WRONG PATH. A stale descriptor entry made it
name one file while the bytes landed in another. A wrong path is worse than no
path, because no path is visibly a gap and a wrong path reads as a finding. The
unknown-source case now evicts to an unattributed-descriptor label.

SILENT ROUTES MOVED INTO ONE LIST OR THE OTHER. Newly COVERED: `os.ftruncate`,
`os.link`, `os.symlink`, `Path.touch`, the exclusive-create open mode, and the
`shutil` copy family. The copy family is covered BY NAME rather than
transitively, and the reason is measured: `shutil.copy2` on CPython 3.14.4 on
Windows takes a native fast path and decomposes into nothing observable. Newly
DECLARED UNCOVERED: `io.FileIO` constructed directly, which is a C type whose
`write` cannot be replaced; metadata-only operations; and directory-level
operations.

THE HONESTY ARM WAS ONE-SIDED, AND THIS IS THE TWO-GUARDS RULE FAILED AND THEN
FIXED. Adding an unpatched name to the covered list went red. REMOVING a patched
name stayed GREEN - so the arm asserted that the declaration was not too small
and said nothing about it being too large, which is exactly the direction an
overstatement travels in. The arm now derives the patched set from the
implementation and asserts equality in BOTH directions.

A NEGATIVE RESULT, RECORDED BECAUSE IT SURVIVED RATHER THAN BECAUSE IT FAILED.
The interpreter hypothesis held: every arm passes on CPython 3.14.4 and on
3.11.9, and `Path.rename` on 3.11.9 calls `os.rename` directly with no accessor
indirection, so the transitive coverage of `Path.rename` and `Path.replace` is
not a 3.14-only accident.

THE CORPUS FIGURES DECAYED DURING THE SESSION THAT MEASURED THEM, because staging
the two new files changed the population. The ADR therefore states BOTH
populations rather than picking one. Re-derived at `13c771f` from `git ls-files`,
and each number carries its population and its pattern because the two answers
differ: over the 144 tracked `.py` files a literal substring sweep for `unlink(`
answers 11 files and 19 occurrences and for `rmtree(` answers 6 and 7, while a
word-boundary call form answers 10 and 17 for `unlink` and 5 and 5 for `rmtree`.
The entire difference is `_wrap_path_unlink(` and `_wrap_rmtree(` in the new
module, which a word boundary rejects and a substring accepts. Over all 228
tracked files the same four sweeps answer 13 and 21, 7 and 8, 12 and 19, and 6
and 6, and a bare substring sweep for `unlink` with no parenthesis reaches 18
files. The roadmap row's own "nine files" was the word-boundary call form over
tracked `.py` and was TRUE at `37bc3bc`, verified by re-running that sweep
against that commit; it went to ten at `13c771f`.

THE DURABLE RULE FROM ALL OF IT. AN INSTRUMENT THAT DOES NOT NAME ITS OWN BLIND
SPOTS CONVERTS A NEGATIVE READING INTO A FALSE CLAIM. And the mechanism that
caught it is worth keeping too: two artifacts describing ONE mechanism drifted
apart at the seam, and the drift was found only because the ADR author never saw
the module. Independence is a prompt-level property, and this is what it bought.

A SECOND CORRECTION THAT BELONGS WITH THIS ENTRY RATHER THAN WITH THE ROADMAP.
This tree told the cross-repo channel on 2026-09-08 that it "cannot check your
start/deliver finding here, having no tagged gates". That was true when written
and DECAYED the next day. Measured this run at `13c771f`:
`tools/moon_sync_responder.py` carries 20 `# GATE:` tags between lines 1928 and
2169, with the grammar pinned by `tests/test_gate_name_bindings.py`. The claim is
withdrawn, and the counterparty question that rests on it is re-asked rather than
answered as written.

Gates at the seam, each as its own command and every returncode read in Python,
measured 2026-09-11 at `13c771f` plus this session's two doc edits: docs
consistency rc 0, docs hook commands rc 0, sibling names rc 0, licence rc 0,
`tests` rc 0, and `tools/precommit_gate.py --scan-files` over both edited
documents rc 0.

Merged files and their guard: `tools/write_tracer.py` and
`docs/adr/ADR-010-write-tracer-coverage.md`, both guarded by
`tests/test_write_tracer.py` - specifically
`test_covered_routes_equals_the_patch_table_in_both_directions` for the honesty
arm that had been one-sided, `test_the_create_op_is_declared_on_the_event_type`
for the headline gap, and
`test_the_pre_context_declaration_names_both_sub_cases_separately` for the
overstatement that must not be refolded. `docs/adr/README.md` gained the one
index line, guarded by `tests/test_docs_consistency.py`.

## 2026-09-11 - A census that fell silent rather than reporting, two widenings its own builder could not grade, and an undeclared scratch bucket four trees share

One commit, pushed: `2ae95f3`, CI green. One outbound cross-repo note, and one
halt that is still open with the operator.

THE DEFECT AND WHY SILENCE IS THE WORST FAILURE SHAPE. `_launcher_name` in
`tools/git_subprocess_census.py` branched on `ast.Attribute` and `ast.Name`
only. A call whose `func` is itself a `Call`, a `Subscript` or a `BoolOp`
therefore produced NO ROW AT ALL. Not a wrong bucket, which a conservation
assertion catches - nothing, which it cannot, because there is nothing to
conserve. Measured over the 142 tracked `.py` files: seven such nodes. Measured
in a worktree at HEAD against the working tree, the census moves 78
{GIT 38, NOT-GIT 22, UNRESOLVED 18} to 85 {38, 22, 25}, with GIT and NOT-GIT
unmoved and all seven new rows opaque.

REACHABILITY IS ZERO AND THE WRITE-UP SAYS SO. All four Call-callee sites in
this tree are stub or predicate invocations and none is a launch. There are no
`os.system`, `os.popen`, `os.spawn*` or `os.exec*` call sites outside the census
and its own test. This is CONTRACT HONESTY, not a closed leak, and the commit
message, the roadmap entry and this entry all say the same thing.

THE ADJUDICATED CALL. The same slice also built an os-launcher table with a
per-launcher executable position and an Attribute-receiver rule for
`get_runner().run(...)`. Two refuters with DISTINCT LENSES - correctness and
over-reach, then scope and consumers - both returned REFUTED. Criteria put to an
adjudicator that had produced neither candidate, weighted in this order: contract
honesty across title and report noun and both docstrings; count of NEW assertions
that can actually go red; the standing precedent; cost and decay.

  - CONTRACT HONESTY, NARROW. The widened title claimed "every process launch"
    while `census_source` on a `subprocess.getoutput` call returns `[]`.
  - ARMS THAT CAN FAIL, NARROW. `test_every_os_launcher_in_the_table_is_reachable`
    built its `filler` from `spec.exec_index`, so THE FIXTURE MOVED WITH THE
    MUTANT. Two agents sampled independently: 6 of 10 entries survived for one,
    16 of 19 for the other. Shrinking `_LAUNCHER_SPELLINGS` from 24 names to two
    also survived at 108 passed rc 0.
  - PRECEDENT, GOVERNS AND FAVOURS NARROW. `ROADMAP.md`, found by its heading
    "RULED 2026-09-09, AND THIS IS AN ADJUDICATED CALL - NOT AN OPERATOR
    DECISION": position B, DO NOT WIDEN, on contract grounds at reachability zero
    of eight. A fortiori here, where the widening makes the contract FALSE rather
    than merely risking it.
  - COST AND DECAY, NARROW. A 21-row per-host CPython signature table plus 21
    hand pins, against nothing left to keep true.

VERDICT NARROW. Both widenings deleted. The Attribute-receiver case is now a
PINNED SILENCE whose spelling set is written as a LITERAL in the test rather than
read off the module, so that arm cannot move with a mutant either.

AN ADJUDICATOR FINDING WAS OVERSTATED AND WAS CORRECTED BEFORE IT REACHED CODE.
It cited `_HARNESS_AXES` in `tests/test_task_liveness.py` as a rival tracked
launcher list containing `getoutput`, implying a live disagreement between two
censuses. That tuple lists subprocess module ATTRIBUTES a test shim must expose
and also holds `CalledProcessError`, `DEVNULL`, `PIPE` and `__name__`. The
getoutput gap is real and was measured directly; the tuple is not evidence for
it, and the implementing slice was told not to cite it.

FOUR PROSE COUNTS HAD DECAYED, THREE OF THEM BEFORE THIS SLICE EXISTED.
`tests/test_conftest_git_gate_sites.py` said "five armed modules" and "every one
of the five rows" while `len(_SITES)` is 6, and "four derive nothing" while it is
five. Its claim that `tests/test_line_endings.py` was the ONLY module reading
differently under the two bucket sets was false when written: three did at the
old census, five do now, at 14 open against 22 closed. `conftest.py` and
`tests/test_git_env_scrub.py` both quoted 78. The 28-of-38 subcommand split in
those two comments was deliberately LEFT: GIT stayed at 38 and every new row is
UNRESOLVED, so that split cannot have moved, and re-deriving it would have been
work that could only confirm itself.

THE DURABLE RULE FROM THAT. A PROSE COUNT THAT NOTHING ASSERTS WILL DECAY AGAIN.
The armed-module numbers are now tied to `len(_SITES)` by an arm whose templates
are stored UNFORMATTED, so it cannot satisfy itself with its own literals, and
which fails both ways: the expected number word must be present and no other
number word variant of the same sentence may be.

AND A SECOND DURABLE RULE, PAID FOR TWICE THIS SESSION. A GREEN SUITE IS NOT
EVIDENCE FOR A FAIL-CLOSED FOLD. `_GIT_BUCKETS` folds UNRESOLVED into
git-reaching fail-closed, and it is evaluated only over the six armed modules,
every one of which reports ZERO unresolved sites under both the old census and
the new. The fold is VACUOUS on the real tree in both states, so the suite could
not have gone red whatever the seven new rows were. Green was silence.

WHAT THE ARMS ACTUALLY KILL, each mutant purging `__pycache__` and
`.pytest_cache` on BOTH sides and restoring from held bytes, never
`git checkout --`: reverting the opaque branch to `return None` fires
`test_the_widened_conservation_arm_would_notice_a_drop` with the seven rows named
in the diff; restoring the "total launch sites" noun fires
`test_the_report_never_calls_an_unresolvable_callee_a_launch`; reinstating the
Attribute-receiver widening fires
`test_a_launcher_spelling_through_an_invisible_receiver_stays_a_silence`. Before
the conservation arm existed, that first mutant left EVERY real-tree arm green.

AN UNDECLARED MACHINE-WIDE SCRATCH BUCKET, HALTED AND NOT TOUCHED. `$TMPDIR` is
UNSET in the Bash tool as it runs here, so `"$TMPDIR/probe.py"` expands to
`/probe.py` and MSYS maps the leading slash to the git installation root. The
redirect succeeds silently. `C:\Program Files\Git` holds 347 non-distribution
files and 6,000,070 bytes dated 2026-04-19 to 2026-09-11. 239 of them contain no
absolute path at all, so attribution is possible for 108 and the counts below are
of files that NAME a root and never of files PRODUCED by one: 126 the CS repo
root, 47 the CS worktree bucket, 29 `C:\Users`, 20 the RC worktree bucket, 11 the
LL repo root, 4 the RC repo root, 1 the LW repo root, 1 this repo root. Eighteen
carry the operator's account path. This tree's own recorded trap blamed a `/tmp`
redirect, which is too narrow: the trigger is ANY unset-variable expansion
leaving a leading slash. Broadcast to all four counterparties with four
questions; nothing deleted, including this tree's own two files, because the path
is outside the repo root and clause (a) governs.

ONE CLAIM THIS TREE MADE TO A COUNTERPARTY WAS FALSE AND IS WITHDRAWN. The
1910 outbound note told LW that both delivered files were machine-identity clean.
`lw_write_tracer.py.from-lw` line 206 carries the operator's account name in its
bare 8.3 short form with no users-segment prefix, and `ABSOLUTE_USER_PATH` in
`tests/test_machine_identity.py` requires that prefix - measured with a control
this run, bare form False and full form True. The consequence is a hole in THIS
tree's detector, not a defect in the LW tree, and the matcher is deliberately NOT
widened: an account name with no path around it is a proximity or entropy
question, a different detector class with its own false-positive budget.

Gates at the seam, each as its own command and every returncode read, measured
2026-09-11: licence 47, docs consistency 29, docs hook commands 21, qa_companion
18 passed 0 failed 1 skipped 3 noted, ruff clean, `tests` 2643 passed 1 skipped,
`agents/pity_engine` 80 passed, `shell` 52 of 52, headless dry run exit 0 with 6
skips, mypy Success over 35 files and ADVISORY.

Merged files and their guards: `tools/git_subprocess_census.py` and
`tests/test_git_subprocess_census.py`, guarded by
`test_the_widened_conservation_arm_would_notice_a_drop` and
`test_the_report_never_calls_an_unresolvable_callee_a_launch`;
`tests/test_conftest_git_gate_sites.py`, guarded by
`test_the_prose_counts_of_the_site_table_are_tied_to_the_table`; `conftest.py`
and `tests/test_git_env_scrub.py`, prose only and guarded by nothing, which is
why both decayed.

## 2026-09-11 - The suite was writing the operator's live day log, the publish gate leaked a token class, and a push from a linked worktree ran both suites against a substituted corpus

Four commits, all pushed: `7786955`, `5d785f5`, `86491a3` and `78cdf96`. Every
figure below is a READING taken on 2026-09-11, at the merged seam or by a named
measurement, and not a claim about any other tree or any later state. Three of
the four commits are repairs to something this tree already believed was safe,
and in two of them the first repair was itself refuted by measurement before the
second one landed.

THE SUITE WAS WRITING THE OPERATOR'S LIVE DAY LOG, AND NOTHING HAD EVER LOOKED.
Measured on 2026-09-11 with an in-process tracer wrapping `builtins.open`,
`io.open`, `os.replace` and `os.rename`: 17492 bytes into the live day log from
51 nodeids across 12 files, the content being synthetic error records manufactured
by the degradation arms. The fix is at the ROOT and is one assignment.
`load_config` in `core/config.py` ALREADY derived its log directory from
`RC_LOG_DIR` when that variable was set, and nothing in the tree had ever set it,
so setting it once at rootdir `conftest.py` import time isolates both suites.
`core/log_setup.py` is UNCHANGED, and an operator-supplied `RC_LOG_DIR` is
HONOURED rather than overridden. Proving path `tests/test_suite_writes_no_live_logs.py`.

THE VERIFICATION DISCARDED THE INSTRUMENT IT WAS CHECKING. An adversary measured
the same claim WITHOUT the tracer, in a clone where REPO_ROOT is `__file__`-derived
so its logs directory - named here in prose because it is a runtime path no
tracked artefact holds - is a location no daemon writes, which makes a
before-and-after snapshot there fully attributing. Under a HEAD-conftest control
that directory gained 19575 bytes; with the fix it gained 0.

TWO CORRECTIONS THAT BELONG WITH THOSE FIGURES, because without them the entry
reads better than the evidence does.

(i) LW independently reported the same three figures, and that is AGREEMENT BY
LUCK rather than corroboration. LW's own later note says its tracer patched
`builtins.open` alone and therefore never saw `Path.write_text`, while ours
patched `io.open` from the start. The SHARED PREMISE was that
`logging.FileHandler` opens through `builtins.open` and never touches `pathlib` -
that premise, not the two measurements, is what the matching numbers are evidence
about.

(ii) The 1922-byte gap between what the tracer saw and what reached disk was
first attributed WHOLLY to child processes. 89 of those bytes are CRLF
translation, measured as a rate against a control. The remaining 1833 are
recorded as UNAPPORTIONED, with child processes named as a CANDIDATE and not as
an attribution.

THE PUBLISH GATE: FOUR RULES, AND MEASUREMENT REFUTED THE FIRST THREE IN ORDER.
Rule 1, the shape at HEAD, leaked the Slack `xoxa-`, `xoxr-` and `xoxs-` classes
straight through the real publish path in `tools/publish_next_session.py`. Rule 2
- a contiguous run after a bounded lead-in - closed those three flat shapes and
OPENED 30 segmented ones including `xoxb-`, which had never leaked at all; the
cliff was the lead-in bound, and a credential with a fully intact 24-character
body was missed because its identifier segments were two characters too long.
Rule 3 - a left boundary of A-Za-z0-9 and underscore - silently gave up EVERY
credential whose preceding character is a word character, demonstrated against
the real publish path with a synthetic 24-A body embedded in a path, and that was
a REGRESSION AGAINST HEAD'S OWN PUBLISHER rather than a missed improvement.

RULE 4 DERIVES ITS BOUNDARY FROM A CENSUS OF THE FALSE POSITIVES INSTEAD OF FROM
A GUESS. All nine false positives are preceded by a LETTER, while the break set is
preceded by an underscore or a digit, so a letters-only lookbehind separates the
two populations EXACTLY. Measured 2026-09-11 over 221 scanned files of 223
tracked: 9 hits without the lookbehind, 0 with it, and the break set still caught.
The COST is pinned rather than described - the arm walks all 128 ASCII codepoints
and asserts the missed set is exactly the letters. A RIGHT boundary was REJECTED
BY MEASUREMENT: adding one lost two of three detections. The real bug behind that
temptation was the refusal detail, which now reports the match span as an UPPER
BOUND on the token rather than as the token. Proving paths
`tests/test_no_secret_literals.py` and `tests/test_publish_next_session.py`.

THE NAME-BINDING DETECTOR IS DEFEATED BY MARKDOWN, AND THAT IS PRE-EXISTING AT
HEAD RATHER THAN INTRODUCED HERE. One optional double quote and a single
colon-or-equals meant a backticked, bolded, tabled or single-quoted secret name
was NEVER EXAMINED AT ALL, and the sweep restated the identical shape, so there
was no second line of defence behind it. The separator class is now derived BY
SUBTRACTION over the 128 codepoints with a MANDATORY operator and with no word
character ever admitted as a separator, so the detector's reach is bounded by
SYNTAX rather than by a character count. The old shape is retained verbatim as a
second alternative so that no prior detection is lost.

THE GIT GATES: FIVE MODULES GAINED ONE, AND THE GRADER WAS REBUILT TWICE BEFORE
IT COULD GRADE. Five modules that shelled git with NO gate now SKIP rather than
FAIL under an unreachable git, each armed by a skip-then-RUN pair in which the
RUN half is the load-bearing one. The site table's conservation arm was extended
from ROWS to NODES after a one-edit mutant left it green. Its matcher was then
replaced outright by the census resolver this tree already ships in
`tools/git_subprocess_census.py`, after a Name-bound argv defeated it and a
splatted argv defeated it again. The exempt-arm audit was then rebuilt a third
time, because a launch inside a DECORATOR proved UNATTRIBUTABLE BY CONSTRUCTION -
the census counted the site and both halves of the audit dropped it. Proving
paths `tests/test_conftest_git_gate_sites.py`, `tests/test_commit_trailers.py`
and `tests/test_precommit_gate_corpus.py`.

ONE MODULE IS EXEMPT, BY AN ADJUDICATION WHOSE CRITERIA WERE WRITTEN BEFORE
EITHER CANDIDATE WAS READ. The rule's population is SITES THAT SHELL GIT, and the
failing arm shells nothing - it CONSUMES the gate helper in order to AUDIT it.
The ruling STANDS, and its CITATION was re-derived rather than carried forward,
because the census guard column is a MODULE-LEVEL walk that would have answered
GATED with every gate in the file deleted.

BOTH INSTALLER PLACEHOLDER GUARDS WERE BLIND TO A DIGIT, AND THE ROW THAT SENT US
LOOKING WAS FALSE. The open row claiming `ops/install_responder_task.ps1` lacks
an unsubstituted-placeholder throw is FALSE and is RETIRED: that script has
carried the guard since `1d80f8c` on 2026-09-07, four days before the row was
filed, and it fires. What was real is SHARED and SYMMETRIC. PowerShell `-match`
is case-INSENSITIVE, so the old character class behaved as case-insensitive at
runtime and lowercase never leaked; only the DIGIT axis leaked, and it leaked
REGARDLESS OF CASE. Measured 2026-09-11 against both scripts: a planted
`__Slot1__` and a planted `__SLOT1__` both returned 0, while `__pythonw_exe__`
and `__PyThonW__` both returned 1. Second, and responder-only: the UTF-16
declaration relabel ran BEFORE the guard, so a token sitting inside the
declaration was MASKED from it; fixed by reordering to substitute, then guard,
then relabel. Proving paths `ops/install_responder_task.ps1`,
`ops/install_scheduled_task.ps1`, `tests/test_responder_task_argv.py` and
`tests/test_supervisor_task_argv.py`.

AN INHERITED GIT ENVIRONMENT SUBSTITUTED THE CORPUS UNDER BOTH SUITES. CS
reported that our hook exports `GIT_DIR`. VERIFIED here on git 2.53.0.windows.3,
and the answer is CONFIGURATION-SCOPED: a push from the MAIN CHECKOUT exports
none, a push from a LINKED WORKTREE exports it, and this machine carried 52
worktree entries on 2026-09-11 while the pre-push hook runs both suites. With it
exported, `python -m pytest tests` returned rc 2 with "Interrupted: 1 error
during collection", while the engine suite collected 80 and carried on - so the
damage was loud on one lane and silent on the other. An AST pass over the 141
tracked Python files found 41 corpus sites with exactly ONE real scrub, which
CORRECTS an earlier 39-with-two reading: one of the two claimed scrubs matched
only because a COMMENT mentioned the variable. CS's own damage narrative was
NARROWED rather than adopted - `git init --bare` with an EXPLICIT path does not
hijack, only the no-path form does, and this tree has zero such call sites, so
only the corpus swap can fire here.

THEN THE SCRUB ITSELF WAS REFUTED, AND THE SELECTION CRITERION WAS THE DEFECT.
`git rev-parse --local-env-vars` is git's OWN authoritative list and returns
FIFTEEN names; the first scrub covered five. `GIT_CONFIG_PARAMETERS` is EXPORTED
TO HOOKS BY GIT ITSELF, and with it inherited a real defect MASKED ITSELF while
the scrub was in place - the guard reddens at rc 1 without it and returns to rc 0
with it. THE TRANSFERABLE LESSON IS THE CRITERION AND NOT THE LIST: the original
nine were chosen by keeping only variables that changed the answer AT rc 0, but
for `git check-ignore -q` THE RETURNCODE IS THE ANSWER, and one module returns
the returncode comparison as its corpus, so the filter was STRUCTURALLY BLIND to
that whole family. The corrected criterion ships in `conftest.py`: an answer is
the PAIR of returncode and stdout. The tuple is now fourteen, with a RUNTIME
RECONCILIATION arm against git's own list, so a future git version arrives as a
red test rather than as an incident. Proving paths `conftest.py` and
`tests/test_git_env_scrub.py`.

THREE TRACKED ARTEFACTS WERE MEASURABLY WRONG AND ARE CORRECTED.
`tests/test_hook_gate.py` asserted that the hook exports no `GIT_DIR`, which is
true of a main checkout and FALSE of a linked worktree; it is now
configuration-scoped and carries both readings. This ledger carried a third
configuration and is corrected in place. And a false justification claiming that
two config variables "changed NO probe" is corrected - the claim is
value-dependent and wrong as written, though the DECISION to keep those two
stands on a restated ground.

MEASURED AT THE FINAL SEAM, 2026-09-11 at `78cdf96`, each gate run as its own
command because a compound command reports only its last element: licence 47;
docs consistency 29; docs hook commands 21; `qa_companion` 18 passed 0 failed 1
skipped 3 noted; `ruff` exit 0; `tests` 2625 passed 1 skipped;
`agents/pity_engine` 80 passed; `node --test` in `shell/` 52 of 52; the headless
dry run exit 0 with 6 skips; mypy Success over 35 source files, which is ADVISORY
here because its roots exclude `tests/` and `conftest.py`, the two places most of
this session's bytes landed.

ONE FAILURE IS RECORDED AS UNEXPLAINED. A second failure seen once in
`tests/test_moon_sync_responder.py` under a planted mutant did not reproduce. The
"collateral damage" explanation offered for it was REFUTED by reading, and a
non-reproduction is not an explanation, so it stays unexplained rather than
closed.

Merged files and their guards: `conftest.py` and `core/config.py`
(`tests/test_suite_writes_no_live_logs.py`, `tests/test_git_env_scrub.py`);
`tools/publish_next_session.py` (`tests/test_publish_next_session.py`,
`tests/test_no_secret_literals.py`); `ops/install_responder_task.ps1` and
`ops/install_scheduled_task.ps1` (`tests/test_responder_task_argv.py`,
`tests/test_supervisor_task_argv.py`); the git-gate sites are test modules that
guard themselves, graded by `tests/test_conftest_git_gate_sites.py`.

## 2026-09-11 - Six guards landed and four of the arms guarding them could not fail, which the same session found by mutating its own work

Two commits. `390a831` carried five slices, and `1c8aab2` repaired four arms that
`390a831` had shipped green against mutants that broke the very properties they
were written to defend. The second commit is the more useful half of the session,
because the defect class it names is our own verification rather than the code.

THE POPULATION QUESTION IS ANSWERED, AND IT WAS THE HIGHEST ROW.
`tools/git_subprocess_census.py` is an AST enumeration of every subprocess launch
site across `tests/`, `tools/`, `ops/`, `headless/` and `scripts/`, reporting
three buckets rather than two. Measured at the merged seam: GIT 37, NOT-GIT 20,
UNRESOLVED 16, total 73 sites over 104 modules, and 26 files hold at least one GIT
site. The UNRESOLVED bucket exists because an argv[0] that no static reading can
answer is not a NOT-GIT, and folding it into one would have reproduced the defect
the tool was built to kill. Both figures this tree had quoted before are now
refuted AS COUNTS - the 8-arms-over-7-modules reading and the 5-module candidate
list both came from name-based one-term filters. The prediction the row made is
confirmed as an ASSERTED POSITIVE rather than as a grep that found nothing:
`tests/test_ci_history_depth.py` and `tests/test_guard_worktree_blindness.py` are
both walked and both yield zero sites in every bucket.

A SLICE REFUTED ITS OWN BRIEF, AND THAT SAVED A PERMANENTLY RED TEST. The
skip-then-RUN site arm was dispatched against the three modules a roadmap row
named as candidates. All three shell git and NONE of them carries a gate, so with
git unreachable they FAIL rather than skip - measured per module, not inferred.
Arming them would have shipped a red test. `tests/test_conftest_git_gate_sites.py`
therefore arms the two sites that do gate at the site,
`tests/test_shell_contract.py` for the import-time whole-module shape and
`tests/test_ports.py` for the run-time per-test shape, and the three ungated ones
became their own roadmap row with a pointer in the module saying to add them once
they are gated. The absence mechanism is an emptied PATH, and the module records
why that defeats both Windows lookups: `shutil.which` is PATHEXT-aware while
`subprocess.run` reaches CreateProcess, which searches the launcher directory, the
cwd, the system directories and only then PATH. The present-but-broken-git
question stays pinned OPEN; nothing here closes an operator call by implication.

THE FIFTH AND SIXTH DEGRADE-TO-EMPTY SITES FAIL CLOSED, and the sixth was found
by the slice that fixed the fifth. `scan_file` in
`tests/test_task_state_claims.py` swallowed OSError and answered zero findings, so
the sweep read CLEAN over a file it never opened; it now raises with a reason
naming the path and the raw errno, cause chained. `_tokens` in
`tests/test_docs_hook_commands.py` answered an empty list on a shlex ValueError,
and since every caller asks whether the token list CONTAINS something, zero tokens
made every question answer no; it now raises, caught at the single call site that
must keep sweeping, where the unparseable span is REPORTED rather than skipped.

THE PROVENANCE DIGEST IS RECOMPUTED RATHER THAN RENAMED. The choice was decided by
a fact and not a preference: the locator rules already enforce a safe total join,
so the artefact is reachable by construction, which is precisely the condition
under which renaming the field advisory would have been dishonest. An absent
artefact is its own verdict, and unverifiable digests are excluded from the
denominator so that zero out of zero cannot read as a pass.

FOUR ARMS COULD NOT FAIL, MEASURED IN A SCRATCHPAD CLONE BY AN AGENT THAT WROTE
NONE OF THEM. The provenance decoy generator advanced character index 0 ONLY, and
every wrong-digest arm derived from it, so an implementation comparing ONE
character of sixty-four passed all 71 arms and the whole suite while grading a
digest differing at its last character as MATCH. The unparseable-span `in_scope`
widening was load-bearing and pinned by nothing, because both fixtures spelled a
long flag. The site table could be emptied - the module's entire subject deleted -
and the gate stayed green, since an empty parametrize is one skipped and exit 0.
The census dropped launch sites in decorators, default arguments, annotations and
class bases, and its unresolved fallback could be flipped to NOT-GIT with all 33
arms passing, which would have silently reclassified the most ordinary dynamic git
argv[0] in Python. Each repair was proven by re-applying the mutant that defeated
its predecessor: the one-character comparison now kills three decoy members, a
sorted-comparison mutant is killed by the transposition member alone, the reverted
widening produces exactly one failure, the emptied table trips a floor, and
deleting the new walk trips a CONSERVATION arm that requires the three buckets to
sum to the hand-counted launches in a fixture.

AND THE CENSUS COUNTS DID NOT MOVE, which was MEASURED rather than assumed by
running the pre-repair and post-repair modules back to back against the same tree
and diffing the full reports. So those four census defects are real and were
unpinned, but they are unexercised by current repo bytes - a distinction worth
keeping, because "we fixed four bugs" and "four bugs were reachable here" are
different claims and only the first is true.

LW'S BACKSLASH FINDING IS SWEPT AT LAST, AND THE REPAIR IS DELIBERATELY NOT MADE.
PowerShell 5.1 native-command marshalling on this host corrupts any argument
containing a space and ending in backslashes: an odd trailing count INJECTS a
quote and an even count silently HALVES the backslashes. Two agents measured the
table independently, the second building its probe from the installers' own bytes
and passing the hostile strings through a JSON file so they never crossed a shell,
with a 13-of-13 clean control through the list form proving the mangling is
PowerShell's rather than the probe's. The two tracked XML templates are ABSENT BY
MECHANISM. Both installers hold the latent shape, but no caller in the tree passes
a task name to either, both defaults are space-free and backslash-free, and the
only route to the native call requires a real registration, which is an arming act
and forbidden. Reachability is nil, so the row records the class and leaves the
code alone, on the same ground as the do-not-widen ruling this tree already
adjudicated at zero of eight.

A FINDING OF OUR OWN WAS REFUTED BEFORE IT REACHED CODE, for the second session
running. The claim was that `ops/check_task_liveness.py` is defective because it
never reads a registered task's action back. Its contract, in its own words, is
whether the task will FIRE and not whether the process will SUCCEED - the State
string is reported and is never the verdict - and the harm path is guarded by the
installers' Test-Path throws plus the tracked-XML arms. The supporting scan was
worse than decorative: a grep for a PowerShell COM shape over a tree that
registers by XML was structurally incapable of finding the readers that do exist.
What survives is narrower and is an enhancement rather than a defect, and its
repair is blocked on the open exit-code call, because a new verdict on that
surface is a compatibility change to five codes that have callers.

MEASURED AT THE SEAM, each gate as its own command because a compound command's
exit status is only its last element: `tests` 2246 passed 1 skipped of 2247
collected in 88.68s, which is 31 more collected than before the arm repairs;
`agents/pity_engine` 80 passed; `node --test` in `shell/` 52 of 52; licence 47;
docs consistency 29; docs hook commands 21; qa_companion 18 passed 0 failed 1
skipped 3 noted; ruff exit 0; the headless dry run exit 0 with 6 skips; mypy
Success over 35 source files, advisory and silent about every root outside its
`files=` list. Both pushes passed the real pre-push hook, 73.1s and 73.5s, and the
free-memory false-red mechanism did not fire in either. These are READINGS at two
commits on one machine, and the local interpreter is 3.14 while CI pins 3.11, so a
local green here is optimistic against CI.

ONE READING SETTLED RATHER THAN SANDED OFF. A slice running the suite in a
scratchpad copy while its siblings were mid-edit saw one failure in the site-arm
module. Against the frozen merged tree that node id passes alone in four
consecutive runs and passes in the full suite, and the collected total was
identical on both sides, so the copy was not a different population. The defect is
ABSENT here and its cause in that copy is recorded as UNDIAGNOSED rather than as
flaky.

A STAMP DISCREPANCY, recorded because it will confuse the next reader. The three
entries above this one are stamped 2026-09-14, and the commits they describe carry
committer dates of 2026-09-11 - `git log --date=iso` reads 2026-09-11 for
`72c7041`, `0d1fa70`, `77408ad`, `f77c4ad` and `76ccdeb` alike. This entry uses
the date the commits actually carry. Do not read the stamps above as evidence of a
later session.

Merged files and their guards: `tools/git_subprocess_census.py`
(`tests/test_git_subprocess_census.py`); `core/provenance.py`
(`tests/test_provenance.py`); the fail-closed guards and the site arm are test
modules that guard themselves, `tests/test_task_state_claims.py`,
`tests/test_docs_hook_commands.py` and `tests/test_conftest_git_gate_sites.py`.

## 2026-09-14 - The commit gate read an unreadable corpus as a clean one, and the fix ran on its own commit

Files: `tools/precommit_gate.py`, `tests/test_precommit_gate_corpus.py` (new).
Landed at `72c7041`.

**THE DEFECT, AND IT IS AN INDISTINGUISHABILITY RATHER THAN A CRASH.** `_git`
returned `out.stdout` and never consulted `out.returncode`, and its except branch
returned the empty string. `_staged_added` turned that empty string into an empty
mapping, and `_check_staged` read an empty mapping as DATA rather than as a failed
read - so no banned-glyph scan ran, no `py_compile` ran, no net-new `ruff` ran,
and the function returned 0 WITH EMPTY STDERR. MEASURED: a clean tree with nothing
staged, and a directory where `git diff --cached` exits 129, were BYTE-IDENTICAL
to the caller - same return code, same empty stderr, nothing to tell them apart.
`.githooks/pre-commit` runs the gate with `|| exit 1` under `set -e`, so that 0
was a developer commit passing UNSCANNED.

**THE ADJUDICATED CALL, THE TWELFTH, VERDICT CLOSED ON 4 OF 4 CRITERIA** -
fidelity to the module's own rule, cost of being wrong, testability, and sibling
consistency. The module's FAIL-OPEN RULE enumerates its own class inside its
parenthesis and both members are TOOL PROVISIONING; the staged diff is not a tool
the gate needs, it is the staged half's CORPUS, and `_check_scan_files` and
`_tracked_split` already carve the corpus class out. Runner-up OPEN-LOUD lost on
cost: a wrongly-closed gate costs one `--no-verify` before anything lands, while a
wrongly-open one puts the defect IN HISTORY, and a force-push does not purge
objects. RECORDED BECAUSE THE ADJUDICATOR DISCARDED ONE OF THE WINNER'S OWN
ARGUMENTS: CLOSED had argued "the commit is about to fail anyway", which is FALSE -
a stale `git -C` path left behind by a worktree agent yields an unreadable corpus
while the real commit succeeds. The ruling is recorded in `ROADMAP.md` under its
own heading; find it by that heading and not by a line number.

**THE SECONDARY RULING, AND IT IS THE HALF THAT ACTUALLY RAN.** The
`rev-parse --show-toplevel` call site KEEPS its permissive fall-through to
os.getcwd(); only its `.strip()` had to become `(_git(...) or "").strip()`, or the
new nullable return raises AttributeError. Because the hook passes the bare string
`git commit` with no `-C`, that fall-through is the LIVE path on every developer
commit, so the fix ran on its own commit.

**VERIFICATION.** `tests/test_precommit_gate_corpus.py`, five arms. Three were red
before the fix by AssertionError against a REAL git exit 129 rather than against a
mocked one; two are controls that were green on both sides, one of them the clean
repo with nothing staged, which is the case the defect was indistinguishable from.
Plus the only valid test of a hook gate, run end to end: a banned glyph staged by
explicit path, a real `git commit` attempted, exit 1 naming both the file and the
glyph, HEAD unchanged afterwards.

## 2026-09-14 - Every non-zero exit was reported as a refusal, so one class sent the reader hunting a cause that does not exist

Files: `ops/check_task_liveness.py`, `tests/test_task_liveness.py`. Landed at
`0d1fa70`.

**THE DEFECT.** `collect_facts` mapped EVERY non-zero return code to one
operator-facing reason naming an account and a TaskPath. For the ConsoleHost
init-failure class that headline is false in every word: 4294901760 is 0xFFFF0000,
ExitCodeInitFailure, with EMPTY stdout and a UTF-16LE stderr reading that loading
managed Windows PowerShell failed with error 8009001d. The CLR never loaded and
the script never ran, so nothing refused anything and neither an account nor a
TaskPath is involved. The truth sat only in the DETAIL string.

**THE FIX.** Two module-level named constants now carry the hex and the meaning,
and the new branch PRECEDES the generic one. Its detail string is byte-identical
to the generic branch's, so the diagnostic content survives and only the headline
changes. The sibling 0xFFFE0000, ExitCodeCtrlBreak, is handled defensively;
whether this tool can reach it at all is UNVERIFIED and recorded as such.

**NO CLI EXIT CODE CHANGED, DELIBERATELY.** 0 LIVE, 1 DORMANT, 2 ABSENT, 3
UNKNOWN, 4 AMBIGUOUS has callers, and an interpreter that never started still
lands on UNKNOWN. Whether it deserves its own code is left to the operator and is
filed in `ROADMAP.md` rather than decided here.

**VERIFICATION.** `tests/test_task_liveness.py`, two arms red before the fix by
AssertionError with both codes spelled as literals, plus two controls: exit 1
keeps the generic headline, and exit 0 with a payload is returned verbatim.

## 2026-09-14 - Two figures this tree wrote down were refuted, the denominator was a third mistake on the same passage, and a guard built to stop a false green converts into a false red

Files: `ROADMAP.md`, `docs/LEDGER.md`, `NEXT_SESSION_PROMPT.md`. Landed at
`77408ad`, `f77c4ad` and `76ccdeb`.

**GATES MEASURED AT `76ccdeb`, STAMPED AS A READING AT THAT COMMIT AND NOT AS A
LIVE CLAIM.** Local interpreter 3.14 while CI pins 3.11, so every local green here
is OPTIMISTIC against CI. licence 47 passed; docs consistency 29 passed; docs hook
commands 17 passed. `scripts/qa_companion.py` 18 passed 0 failed 1 skipped 3
noted. `ruff` exit 0. `mypy` exit 0, no issues found in 34 source files, and that
is ADVISORY - it says NOTHING about `scripts/`, `surface/`, `headless/`, `ops/` or
`tests/`, so it is silent about most of the code in this entry. `pytest tests`
2155 passed 1 skipped; `agents/pity_engine` 80 passed; `node --test` in `shell/`
52 tests 52 pass 0 fail; `python -m headless.runner --once --dry-run` 0 pass 0
fail 6 skip, exit 0. Responder task exit 1 DORMANT, sole trigger expired
2026-09-07T21:00.

**"SIX ARMS" WAS WRONG BY ROUGHLY SEVENFOLD, AND WHY IT WAS UNCHECKABLE IS THE
REUSABLE HALF.** Deleting the one `# GATE:answered-usable` line in a clean clone
gives exit 1 with 43 failures, against a baseline of exit 0 in the SAME clone
before the edit. No artifact anywhere recorded WHICH six, so the figure was
checkable against nothing, and it was never a tooled probe:
`tools/gate_mutation_runner.py` mutates gate STATEMENTS through `_edits_for` over
ast.stmt and has NO CLI mode that drops a comment.

**THE REPLACEABLE DELIVERY COUNT "3 BEFORE" WAS ALSO WRONG, AND ITS ORIGIN IS THE
FINDING.** All four parametrized arms of the replaceable self-heal test PASS
against `6c351b3^`, so the pre-change bytes delivered 1. The 3 was measured against
the dispatch brief's ordered-then-REJECTED fail-closed `_remember_answered`, which
was never committed and exists NOWHERE in history - a number measured against an
intention.

**THE DENOMINATOR WAS A THIRD MISTAKE ON THE SAME PASSAGE.** 43 failed plus 45
passed is 88, against a baseline of 89, and the missing case is in NO result
bucket because it was never COLLECTED. `_TAG_LINES` in
`tests/test_responder_gate_census.py` is derived at import from the responder's own
source and the module parametrizes on it, so deleting a `# GATE:` tag DELETES A
PARAMETRIZE CASE. The error, skip, xfail and xpassed buckets were all measured
empty; a restore control returned the clone to 89 passed at its original byte
size; and every surviving test id SHIFTS DOWN BY ONE, which is the corroborating
signature of a deleted source line rather than a lost result. So the kill is 43 of
88 COLLECTED in the mutant against 89 collected at baseline, and 89 is not an arm
count at all - it is 69 plus `len(_TAG_LINES)`.

**LEFT UNRECONCILED ON PURPOSE.** The unique-red-function count is 24 against 23,
two passes disagreeing by one with NEITHER enumerating the function names, so
neither figure is checkable and neither is recorded as the answer. The commit body
of `6c351b3` carries the refuted figures and CANNOT be fixed - it is pushed, CI ran
green on it, and rewriting published history to correct a number is worse than the
number, so a reader who finds that message first is pointed here.

**THE FALSE-RED CLASS, MEASURED IN OUR OWN BYTES AFTER LW FOUND IT IN THEIRS.**
Stripping every PATH entry holding a git executable turned a green probe reading
over 7 modules into 8 RED arms, TWO of them anti-vacuity arms - so a guard written
to stop a false GREEN converts into a false RED. The error is FileNotFoundError
WinError 2 RAISED AT EXEC, which makes a `check=True` argument IRRELEVANT because
the exec raises before any exit code exists; that is recorded because it kills the
obvious wrong fix. The mechanism in our bytes is `_tracked_text_files` in
`tests/test_no_sibling_names.py`. THE MIRROR DIRECTION WORKS: 11 skips appeared and
two anti-vacuity arms skipped correctly through `require_git_repository`, so the
tree is PARTIALLY ARMED rather than unarmed.

**THE CORRECTION TO THAT ROW IS THE REUSABLE HALF: THE FIVE-MODULE LIST WAS THE
FILTER'S POPULATION, NOT THE REPAIR'S.** The row had warned that its own name-based
one-term filter would over-report as well as under-report, and an AST probe
confirmed the over-report, so the warning became a measurement. Only THREE of the
five shell git at all. `tests/test_ci_history_depth.py` executes none - its only
occurrence of the text subprocess.run is a STRING LITERAL fed to a regex.
`tests/test_guard_worktree_blindness.py` has no subprocess call whatsoever. A skip
added to either would be a FALSE SKIP with no defect behind it, which is the same
over-fire error in the opposite direction. THREE IS A FLOOR AND NOT A COUNT: the
whole-tree population is still unenumerated, and that is filed open.

**THE PRE-PUSH GATE IS INTERMITTENT - DIAGNOSED, FILED, NOT FIXED.** A push was
REFUSED reading 2 failed, 2148 passed, 2 skipped. The orchestrator's own hypothesis
that the hook ENVIRONMENT was to blame is REFUTED BY COUNTER-EXAMPLE: the same
commit through a real pre-push hook into a scratch bare repository gave 2150
passed, 2 skipped in 97.77s, exit 0. Interpreter, PATH, powershell resolvability,
user, timeout and cwd were each ruled out INDIVIDUALLY by measurement. The cause is
load: the Windows resource-exhaustion detector logged low-virtual-memory events
naming a python process holding about 10.4 GB, and the refused run took 474.67s,
spanning both events. Two arms collapse "the census machinery is broken" with
"powershell could not start just now", so a PUSH-BLOCKING VERDICT IS A FUNCTION OF
FREE MEMORY. WHAT THE ARMS GET RIGHT, so nobody softens them: FAILED must fail and
only NONE may skip, which is exactly what kills a vacuous skip - the MISSING
DISTINCTION is the defect, not the strictness. The collected total was 2152 in
every run, so nothing was silently dropped.

**TRANSFERABLE TRAPS MEASURED THIS SESSION, each with its mechanism rather than as
folklore.** Under Git Bash the shell status is 8-BIT, so an exit of 4294901760
reads as 0 there and this exit code cannot be chased through a shell at all - only
a returncode read in Python carries the full 32 bits. A COMPOUND command's exit
status is its LAST element, so a trailing echo reported 0 and MADE A REFUSED PUSH
LOOK LIKE IT HAD LANDED. And /tmp under Git Bash is a directory inside the Git
installation rather than anything on the C: drive root, and files there PERSIST
ACROSS AGENTS, so a stale file at a shared path reads exactly like fresh output -
a subagent's leftover output was misread as a hook blocking a commit that had never
run, because a failed `python -c` had short-circuited the `&&` chain before the
commit was ever attempted.

**INBOX: THREE LW NOTES TRIAGED AND MARKED, and the interesting verdicts are the
ones that are not adoptions.** LW's Q3 claim about a shared conftest is refuted and
we had ALREADY retracted it, so no new correction is owed - what LW adds is a
SECOND CARRIER, which upgrades the claim from RETRACTED to DISPROVED. LW's "43 to
0" is HALF MEASURED: the AFTER was re-run, but the BEFORE row is byte-identical to
their earlier note and was carried forward, so the delta is ASSERTED rather than
measured - and their own disclosed box saturation, applied to the post-repair probe
only, would inflate the 43 numerator by the same noise. Their R3, that a
present-but-broken git must still FAIL, CONFLICTS with our shipped
`classify_git_probe`, which SKIPs it, and `tests/test_conftest_git_gate.py` pins
that question as deliberately OPEN - so adopting their rule would silently close an
open operator call. Their PATH-strip mirror mechanism is contraindicated here by
our own measured trap: shutil.which is PATHEXT-aware while subprocess.run goes
through CreateProcess, which appends only .exe. Their third note offers NO digest at
all, and their with-git passing count moved by twelve between notes, unstated.

## 2026-09-12 - An adjudicator corrected the orchestrator's own brief, and the ledger-instance row was answered by finding that nothing has ever been written to it

Files: `tools/moon_sync_responder.py`, `tests/test_responder_degraded_write.py`
(new), `tests/test_gate_name_bindings.py`, `tests/test_responder_gate_census.py`,
`ROADMAP.md`, `docs/LEDGER.md`, `NEXT_SESSION_PROMPT.md`. Landed at `b128eb1`
(docs) and `6c351b3` (code).

**THE CODE LANDED AFTER THIS ENTRY WAS FIRST WRITTEN AS PAPERWORK-ONLY.** It was
drafted while the third slice was still running and said the fix was uncommitted
in a worktree; the slice reported green, the four files were merged by absolute
path with all four sha256 values matching the builders' reported digests, the
whole gate was re-run at the seam, and CI went green. The correction is recorded
rather than smoothed over, because the first wording was true when written.

**MEASURED AT THE SEAM.** `pytest tests` 2146 passed 1 skipped, against 2106
passed 1 skipped at the `41ba7d0` fork point - plus 40 arms. `agents/pity_engine`
80 passed. `node --test` in `shell/` 52 tests 52 pass 0 fail. licence 47, docs
consistency 29, docs hook commands 17. `qa_companion` 18 passed 0 failed 1
skipped 3 noted. `ruff`, `headless.runner --once --dry-run`, `mypy` and
`precommit_gate --scan-files` over all four files exit 0. CI `ci` watched with
`--exit-status`, exit 0. `mypy` at 34 source files includes `tools/` and
therefore the responder, and says NOTHING about the three test files.

**THE FOUR SITES.** `record_cycle` took `read_json(metrics, default=None)`, fell
back to `rows = []` and rewrote the document, so a corrupt ledger was REPLACED by
a one-row ledger and the call returned True; it now splits absent from unreadable,
refuses, and leaves the bytes byte-identical. `_trim_invocations` read
`errors="replace"` and never folded U+FFFD while `core/atomic_io.py` encodes
UTF-8; MEASURED across three fires at 273363, 273369, 273387 bytes - plus six
then plus eighteen, the threefold expansion observed rather than argued - and it
now folds to ASCII `?`. The metrics cap trimmed rather than rotated; it now
rotates to ONE bounded generation holding the newest overflow, total held at
twice the cap, rotation written FIRST and the live file LAST so a failed rotate
propagates False with the live ledger complete instead of degrading silently into
a trim. Bounded deliberately - the document is re-serialized on every write, so
an unbounded archive reproduces the quadratic-bytes defect the cap exists to
close. And `answered_usable` mirrors `refusals_usable` per the ruling below.

**THE GATE GUARDS MOVED, AND THAT IS THEM WORKING.** Two new `# GATE:` tags
reddened `tests/test_gate_name_bindings.py` and
`tests/test_responder_gate_census.py`. Dropping the tags was MEASURED not to be
an escape - the census then reports both sites as untagged consult sites. Both
floors were RAISED, never lowered, and every assertion kept its strength: the
census floor and the adjacent-swap count remain equalities. Non-vacuity was
proven twice, and ONE OF THE TWO FIGURES HAS SINCE BEEN REFUTED AND RE-MEASURED -
see the correction directly below. The probe that held is the rename: renaming one
tag so the tag COUNT stays constant was caught by the bindings module alone, which
is the discrimination that module exists for.

**CORRECTION - "six arms" WAS REFUTED, AND WHY IT WAS UNCHECKABLE IS THE REUSABLE
HALF.** An adversary with a does-it-reproduce lens re-ran both probes in a clean
clone at `26c14d9`. Deleting the single `# GATE:answered-usable` line in
`tools/moon_sync_responder.py` and running `tests/test_gate_name_bindings.py` with
`tests/test_responder_gate_census.py` under `-p no:cacheprovider` gave exit 1 with
43 failures, against a baseline of exit 0 in the SAME clone before the edit. The
recorded "six" is wrong by roughly sevenfold on failures. Stamped as a probe
reading in one clone at one commit, never as a live suite figure. The rename probe
DID reproduce and stands as written - exit 1, 9 failures, every one of them in the
bindings module, the census fully green.

**THE DENOMINATOR IS NOT THE SAME ON BOTH SIDES, AND THAT IS THE WHOLE OF THE
ARITHMETIC.** A first pass reported the mutant as 43 failed plus 45 passed against
a baseline of 89 passed, which is 88 against 89 and reads as one lost test. A
second pass in a separate clone at the same commit reconciled it, and NEITHER
number was wrong: the missing case sits in NO result bucket because it was never
COLLECTED. `_TAG_LINES` in `tests/test_responder_gate_census.py` is derived at
import from the responder's own source, and the module parametrizes on it, so
deleting a `# GATE:` tag DELETES A PARAMETRIZE CASE. Baseline collects 89 and
passes 89; the mutant collects 88 and closes as 45 plus 43. The case that ceased
to exist is `test_removing_one_tag_reports_exactly_that_site_as_untagged` at the
deleted tag's line id, and the corroborating signature is that every surviving id
SHIFTS DOWN BY ONE - a deleted source line, not a lost result. The error, skip,
xfail and xpassed buckets were all measured empty, and a restore control returned
the clone to 89 passed at its original byte size. So write the kill as 43 failed of
88 COLLECTED in the mutant, against 89 collected at baseline. Writing "43 of 89"
misstates the rate.

**89 IS NOT AN ARM COUNT AND MUST NOT BE CITED AS ONE.** It is 69 plus
`len(_TAG_LINES)`, so it moves whenever a `# GATE:` tag is added to or removed from
`tools/moon_sync_responder.py`. UNRECONCILED, and left that way rather than
resolved by preference: the two passes disagree on how many UNIQUE test functions
go red, one saying 24 and the other 23, the same off-by-one shape as the
denominator itself. No pass enumerated the function names, so neither figure is
checkable, and the unique-function count is therefore NOT recorded here. The
failure and collection counts above are the measured part.

**WHY THE NUMBER DRIFTED.** No artifact anywhere recorded WHICH six arms, so "six"
was checkable against nothing. And the probe is not re-runnable AS RECORDED:
`tools/gate_mutation_runner.py` mutates gate STATEMENTS - `_edits_for` walks
`ast.stmt` inside `run_once` - and its CLI has no mode that drops a `# GATE:`
COMMENT, so this was never a tooled probe. Both guard modules resolve `REPO_ROOT`
from `__file__.resolve().parents[1]` and the census shells `git ls-files` with
`cwd=REPO_ROOT`, so the probe needs a WHOLE-TREE copy rather than a two-file
scratchpad. A probe that is expensive to re-run and names no subjects decays into a
number nobody can challenge. The commit body of `6c351b3` carries the refuted "six"
and CANNOT be fixed - it is pushed, CI ran green on it, and rewriting published
history to correct a number is worse than the number. The commit message holds the
refuted figure; this ledger holds the correction.

**STATE ALSO MEASURED at `41ba7d0` before any of it, stamped as a reading.**
`pytest tests` 2106 passed 1 skipped; `agents/pity_engine` 80 passed; `node
--test` in
`shell/` 52 tests 52 pass 0 fail; licence 47, docs consistency 29, docs hook
commands 17; `qa_companion` 18 passed 0 failed 1 skipped 3 noted; `ruff`,
`headless.runner --once --dry-run` and `mypy` exit 0, the last at 34 source files
and therefore silent about `scripts/`, `surface/`, `headless/`, `ops/` and
`tests/`. Responder task exit 1 DORMANT, sole trigger expired 2026-09-07T21:00.
Inbox 157 files, 0 unread. `git ls-files` 218 paths, 135 `.py`.

**THE ADJUDICATED CALL CAUGHT A DEFECT IN THE DISPATCH BRIEF, NOT IN THE CODE,
AND THAT IS THE ENTRY.** The brief instructed the builder to make
`_remember_answered` fail closed on every unreadable class of the answered
record, by analogy with the `read_reported` fix that landed at `b3ff9fe`. The
analogy is false, and reading the cited docstring rather than summarising it is
what showed why: that split turns on the DIRECTION and CONSEQUENCE of the
degrade, not on the reader-versus-writer role. `_remember_answered` is THE ONLY
THING THAT HEALS a replaceable answered record, so a writer that refuses turns
the reader's degrade from ONE duplicate into ONE DELIVERY PER CYCLE FOREVER,
into another repository's tree, `deliver` never overwriting a name and
`_reply_name` being minute-resolution. Measured over three cycles per case,
counted as files in the destination inbox: structural 3 before and 0 after,
absent 1 then `empty`. The ruling is NEITHER candidate - mirror
`refusals_usable`'s replaceable-versus-structural split - and it is recorded in
`ROADMAP.md` under its own heading.

**CORRECTION - the REPLACEABLE "3 before" WAS REFUTED. The pre-change bytes
delivered 1, not 3.** This paragraph used to read "replaceable 3 before and 1
after" alongside the structural pair. A does-it-reproduce adversary ran all four
parametrized arms of
`test_a_replaceable_answered_record_still_answers_and_self_heals` against
`6c351b3^` and every one PASSED, exit 0. The 3 was never a measurement of
committed bytes: it was measured against the dispatch brief's ordered-then-
REJECTED fail-closed `_remember_answered`, which was never committed and exists
nowhere in history. The arm's own docstring says as much - it fails against a
writer that REFUSES a replaceable record, and no such writer was ever in this
tree. The conflation is that the commit body of `6c351b3` puts the replaceable
figure in the same before/after sentence as the structural pair, where "before"
DOES mean the committed pre-fix bytes. The STRUCTURAL half reproduces and is kept
above unchanged: red on `6c351b3^` with `AssertionError: an unrecordable answer
delivered 3 replies`. That commit body CANNOT be fixed - it is pushed, CI ran
green on it, and rewriting published history to correct a number is worse than
the number - so a reader who finds the commit message first is pointed HERE.

**THE GAP THAT MADE IT INVISIBLE.** No tracked arm anywhere drives MULTIPLE
cycles over a poisoned ANSWERED record; all eight existing multi-cycle `_drive`
arms target `DEFAULT_REFUSALS`. A single-cycle arm structurally cannot see a
per-cycle-forever loop, so the suite was green about a question it never asked.

**THE LEDGER-INSTANCE CHECK: NO DIVERGENCE, and the reason is not convergence.**
All five `record_cycle` call sites pass `DEFAULT_METRICS` verbatim; six total
references exist in non-test code, so there is no second binding to diverge, and
no `add_argument` sets the path. ZERO M1-M6 ROWS HAVE EVER BEEN WRITTEN LIVE -
`_run_once` returns at its empty-queue gate before the first `record_cycle`, the
three JSON records are ABSENT from `ops/runtime/`, and the only live record is
`responder_invocations.log` at 48 lines which decomposes exactly into 19
start-plus-`empty` pairs plus 10 bare starts. A census over four roots walked
211694 directories and found 197 instances of those four basenames with exactly
ONE live, every `responder_metrics.json` under a pytest tmp dir and zero under
`C:\ProgramData`.

**AND EVERY LINE NUMBER THAT ROW CARRIED WAS STALE, FIVE FOR FIVE, WITH TWO
MUTUALLY INCONSISTENT NUMBERS FOR ONE DEFINITION.** `ROADMAP.md` cited
`record_cycle` at both `:969` and `:1102`; it is at `:1067`. The five call sites
were cited at 1615, 1634, 1665, 1700 and 1738; they are at 1728, 1748, 1785,
1822 and 1871. The repair was to CITE BY NAME rather than to write five fresh
numbers that will rot the same way - this tree has now measured decayed doc
pointers three sessions running.

**THE PROCESS FINDING, recorded because the shape recurs.** `SendMessage` is
disabled in this session, so a brief discovered to be wrong while its builder was
still running COULD NOT BE CORRECTED IN FLIGHT. The correction had to land as a
follow-on slice into the same worktree, which then hit a real seam collision on
two gate-guard files it did not own and STOPPED rather than editing them. Three
sequential slices where one was planned. An orchestrator that cannot reach a
running agent should assume a wrong brief costs a whole slice, and should
therefore adjudicate the contested half BEFORE dispatch rather than in parallel
with it.

## 2026-09-11 - A read that degrades to empty and is written back deletes the history it could not read, and three panels went live off the operator's own account

Files: `scripts/watch_inbox.py`, `tests/test_watch_inbox_log_discard.py` (new),
`surface/model.py`, `surface/render.py`, `tests/test_surface_plan_rotation.py`
(new), `tests/test_surface_teams.py` (new), `tests/test_surface_resin.py` (new),
`tests/test_surface_model.py`, `tests/test_surface_render.py`,
`scripts/qa_companion.py`, `ROADMAP.md`, `docs/INBOX_TRIAGE_2026-09-09.md`.
Landed at `b3ff9fe`, `3c4bcb5`, `9f03062` and `2dc0965`.

**MEASURED AT THE SEAMS, STAMPED AS READINGS AND NOT AS CLAIMS ABOUT NOW.**
Fork point `577c2d6` re-measured first at 1981 collected, 1980 passed 1 skipped.
First seam 2077 passed 1 skipped at 2078 collected; final seam 2106 passed 1
skipped. `agents/pity_engine` 80 passed. `node --test` in `shell/` 52 tests 52
pass 0 fail. `ruff`, `headless.runner --once --dry-run` and the three doc guards
exit 0 - licence 47, docs consistency 29, docs hook commands 17. `qa_companion`
18 passed 0 failed 1 skipped 3 noted, and its three NOTEs again say local
`ruff` 0.15.12, `pytest` 9.0.3 and `mypy` 2.1.0 are ALL OLDER than the CI pins,
so every local green in this entry is OPTIMISTIC against CI. `mypy` exit 0 at 34
source files, which says NOTHING about most of this entry: `scripts/` and
`surface/` are not `mypy.ini` roots.

**THE DEFECT, AND IT IS A DIFFERENT ACT FROM TRIMMING.** `_log_tail` returned
`[]` on `UnicodeDecodeError`; `log_invocation` spliced that empty with the new
line and REWROTE the file. Reproduced on a copy of the live record: 664 lines
became 1 line of 29 bytes, taken by two bytes. `record_reported` and the report
prune carried the same shape through `read_json`, which returns its default for
missing, undecodable AND corrupt-JSON alike - so `record_reported`'s own
docstring, "Union, never a rewrite", was FALSE on exactly the path that
mattered. Degrading a READ to empty is defensive; splicing that empty with new
data and writing it BACK converts unreadable history into DELETED history.
Verification: `tests/test_watch_inbox_log_discard.py`, and specifically
`test_absent_and_unreadable_are_now_different_outcomes` and
`test_a_second_fire_does_not_grow_the_mangled_line`.

**THE TREE HAD ALREADY SOLVED HALF OF IT.** `tools/moon_sync_responder.py`
reads its own invocation log with `errors="replace"` and APPENDS rather than
rewriting, so it is immune by construction. The fix mirrors it, and folds
U+FFFD to ASCII `?` because `atomic_write_text` encodes UTF-8: a retained
U+FFFD is written as 3 bytes, re-read as ASCII gives 3 replacement characters,
written as 9. A verifier measured four consecutive fires at exactly +29 bytes
each, so the growth does not recur.

**DECIDED, WITH REASONING, SO IT IS NOT RE-LITIGATED.** `read_reported` STILL
degrades to empty for its READING callers, deliberately, and
`test_read_reported_still_degrades_to_empty_for_its_reading_callers` pins that
so nobody "finishes the fix" on the wrong half. The read inside `withdrawn()`
is NOT a fourth site: it can only shrink a printed baseline, so it under-reports
and can never invent a withdrawal.

**THE SURFACE WENT LIVE OFF THE OPERATOR'S OWN ACCOUNT, AND TWO CONSTANTS THIS
TREE REFUSED TO RE-DERIVE WERE CONFIRMED BY IT.** With the in-game showcase
opened, `avatarInfoList` arrived and Roster moved NOT_WIRED to READY and Plan
NOT_WIRED to PARTIAL. Two independent external validations, from a source this
repository is licence-gated away from holding: the banner detail text states the
consolidated 5-star event-exclusive probability is 1.103%, and this tree
predicts 1.1034% from 55.000% consolidated Capturing Radiance and 1.600% as
`1 / E[wishes per 5-star]`; and a talent-material tooltip names its domain as
Tuesday/Friday/Sunday, which is exactly `ROTATION_SLOT_WEEKDAYS[1]`. Neither
figure entered `data/`.

**THE RESIN PANEL TOOK `now` AND IGNORED IT.** Measured at `9f03062`: the same
account at +0h, +4h and +12h printed `20 / 200` every time, while
`core/resin.py` `resin_at` answered 20, 50 and 110 for the same inputs. It now
projects across six bands keyed on the OBSERVATION rather than the balance.
A verifier swept 148 cells of observed-by-elapsed, including every boundary at
plus and minus one second, and found zero unintended differences in state or
withhold decision. Verification: `tests/test_surface_resin.py`.

**THE HONESTY IS THE FEATURE, AND THE CAPPED CASE IS WHY.** A projection
saturated at the cap answers the cap for EVERY possible history, so it carries
no information; the panel therefore prints no present-tense number there, and
says why. The operator's real observation was 200/200, which saturates
instantly, so this is the live case and not a corner. An earlier wording claimed
a refill span had elapsed, which is false when the balance never left the cap -
`time_to_reach(200, 200)` is zero. The reason now branches three ways on
observed against cap, and the below-cap arm that was already true is kept as the
control proving the fix is not a deletion.

**TWO GATES THAT COULD NOT FAIL, BOTH CLOSED.** `render_html` emitted 48
non-ASCII bytes for an externally supplied `display_name` carrying em-dash,
en-dash, smart quote and CJK - glyphs `CLAUDE.md` bans outright - because
`html.escape` closes the markup hole and passes every codepoint through.
`render_json` was already clean via `ensure_ascii` and its docstring names the
hazard, so two renderers in one module disagreed and the HTML one was wrong. The
ascii arm that should have caught it rendered an ASCII-ONLY fixture and
`qa_companion` graded the EMPTY state, so both stayed green on both sides of a
real defect. Verification:
`test_an_externally_supplied_display_name_is_folded_to_seven_bit_ascii`, shown
red against a neutered escaper while the incumbent arm still passed.

**FILED, NOT FIXED.** The same degrade-to-empty root cause has three more sites
in `tools/moon_sync_responder.py` - `_remember_answered`, `record_cycle`, and a
latent threefold-growth in `_trim_invocations` - each re-read at HEAD before
filing. Recorded in `ROADMAP.md` as applicable-and-not-done rather than fixed,
because the adjudicated authorisation covers a bounded rotate only.

**FIVE DECAYED POINTERS CORRECTED, AND THE DECAY WAS ITSELF THE FINDING.**
`ROADMAP.md` and `docs/INBOX_TRIAGE_2026-09-09.md` both cited
`tools/moon_sync_responder.py:1037` for the metrics trim; that line is now
prose. Corrected against current content to :1135, :1207, :1128-1134, :1217 and
:1868. Every substantive claim survived; only the coordinates rotted. The two
files are therefore ONE input counted twice, and the identical wrong line number
in both is what proves it.

---

## 2026-09-10 - Grading three floors found one that was wrong, and a lane arm that looked like the point was the vacuous one

Files: `tests/test_licence_posture.py`, `tests/test_machine_identity.py`,
`tests/test_line_endings.py`, `tests/test_commit_trailers.py`,
`tests/test_responder_task_argv.py`, `tests/test_supervisor_task_argv.py` (new),
`ROADMAP.md`, `docs/LEDGER.md`. Landed in two waves at `b3bef1a` and `fe6c004`.

**MEASURED AT EACH SEAM, STAMPED AS A READING AND NOT AS A CLAIM ABOUT NOW.**
Fork point `b5dc138` re-measured first at 1882 passed 1 skipped, collect-only
1883. Wave one seam: 1915 passed 1 skipped, collect-only 1916, from 1882 plus
30 plus 3 plus 0. Wave two seam: 1935 passed 1 skipped, collect-only 1936, from
1915 plus 0 plus 2 plus 2 plus 16. BOTH ARITHMETICS CLOSED AT BOTH ENDS, and at
the second seam the per-file counts were re-derived from that run's own
collect-only listing rather than trusted from the four slice reports - the
supervisor grader at 32, the trailers module at 13, the responder grader at 43.
`agents/pity_engine` 80 passed. `node --test` in `shell/` 52 pass 0 fail.
`ruff` and `headless.runner --once --dry-run` exit 0. `qa_companion` 16 passed
0 failed 2 skipped 3 noted, and its three NOTEs say the local `ruff`, `pytest`
and `mypy` are all OLDER than the CI pins, so every local green here is
OPTIMISTIC against CI. `mypy` exit 0 at 34 source files, which says NOTHING
about any file in this entry: all six live under `tests/`, and `mypy.ini` does
not carry that root.

**THE FLOOR THAT WAS WRONG, NOT MERELY UNGRADED.** A floor guarded only by
`assert CONST >= 10` asserts something about the constant and nothing about
what the constant does. Three instances existed in the tracked test corpus.
Grading the second one exposed a live defect: the tracked corpus is 213 paths
over 16 top-level directories, the widest answer a single-directory
`git ls-files` can return is `tests/` at 70, and `_MIN_TRACKED_FILES` shipped
at 50 - so 70 sailed over it and the floor could not refuse the partial
enumeration it exists to refuse. Raised to 90 as the CONSEQUENCE of grading,
bounded above by the pre-existing half-corpus arm at 106. Corroborated by an
independent adversary through a DIFFERENT ROUTE, real `git ls-files` with the
cwd inside each directory, so this is not two agents sharing one premise.

**THE ASSERTION CHOICE WAS LOAD-BEARING AND WOULD NOT HAVE BEEN GUESSED.**
Asserting `status == "FAILED"` does NOT catch a slack floor: the path anchors
still refuse the partial enumeration, so the status stays FAILED while the
floor contributes nothing. The arm had to assert on the floor's OWN REASON. A
grader that watches the verdict instead of the mechanism passes the mutant.

**A SELF-REFERENTIAL ARM CAN SATISFY ITS OWN CONDITION.** The arm pinning this
tree's docs-only CI lane needed its pattern built as `r"\." + "md" +
r"([^a-zA-Z0-9]|$)"`, because the unsplit literal MATCHES ITSELF and an arm
whose own text satisfies the condition it tests passes vacuously forever.
Driven as a mutant, the arm that looked like the point stayed GREEN with its
protected mentions removed, and only the self-reference control fired.

**A COUNT SURVIVED A HANDOFF THAT ITS MEASUREMENT DID NOT.** Twelve claimed
reds were re-driven independently, in a worktree seeded by copying the merged
bytes and verifying each by sha256. Eleven reproduced with the claimed summary
line, exit code and reason. One figure did not: a mutant reported as scoring
`24/24 pass` at `b3bef1a`, where the module collects 30 mutated and unmutated
alike. The DIRECTION held, so the repair was needed, but 24 was the size of an
in-memory arm subset an earlier adversary had driven, carried forward as though
it described the module.

**NOTHING WAS ARMED.** Both argv graders import no `subprocess`, no `os` and no
`shutil`, so neither can spawn `schtasks` even by accident; both grade static
declared XML and neither asserts its task is registered. The responder task was
re-confirmed DORMANT by `ops/check_task_liveness.py`, exit 1, trigger expired
`2026-09-07T21:00`. `git diff --stat -- ops/loop/` empty at both commits.

## 2026-09-09 - A runtime probe found the detector's blind spot inside its own declared shape, and a newest-first ledger made a closed row look open

Files: `tools/gate_mutation_runner.py`, `tests/test_gate_mutation_runner.py`,
`ROADMAP.md`, `docs/LEDGER.md`. Docstrings and arms only - no mechanism changed
and `_READ_ATTRS` was NOT widened, which is a claim about the diff and not about
intent.

**MEASURED ON THE SLICE'S OWN BYTES, FORKED FROM `6be6961`, STAMPED AS A
READING AND NOT AS A CLAIM ABOUT NOW.** `python -m pytest tests` exit 0, 1882
passed 1 skipped. `python -m pytest agents/pity_engine` exit 0, 80 passed.
`python -m ruff check .` exit 0. `python -m mypy` exit 0 at 34 source files,
which is real evidence about `tools/gate_mutation_runner.py` and says nothing
whatever about the arms under `tests/`, since `mypy.ini` does not carry that
root. `tests/test_gate_mutation_runner.py` goes 51 to 53, and the fork point
itself was measured at 1880 passed 1 skipped in this same worktree before any
edit landed, so 1880 plus 2 is 1882 and the arithmetic closes at both ends
rather than at one end with the other assumed.

**AN AST DETECTOR WAS REFUTED BY A RUNTIME MEASUREMENT, AND THE METHOD IS THE
REUSABLE PART.** The adversary did not sweep the AST - it patched `io.open` and
`builtins.open` from a `sitecustomize.py` and ran one full application suite.
Re-derived here independently at `6be6961` by the same method: 197 open events
on `tools/moon_sync_responder.py`, of which 195 attribute to a repo file and 2
to a frozen pseudo-file frame that is no repo file at all, and those 195 come
from 15 DISTINCT REPO FILES - 14 under `tests/` plus
`tools/gate_mutation_runner.py`. `responder_reading_modules` names 3. The two
figures in circulation, 195 and 197, count DIFFERENT POPULATIONS and both are
right about their own; say which before citing either.

**THE GAP OF 12 IS MOSTLY OUTSIDE THE DECLARED SHAPE, AND FOUR MODULES ARE
INSIDE IT.** `tests/test_moon_sync_responder.py`,
`tests/test_responder_broadcast_refusal.py`,
`tests/test_responder_delivery_gates.py` and
`tests/test_responder_refusal_gates.py` each bind the responder path at module
level to a plain `Name`, so criterion 1 of `_binds_and_reads_responder` passes,
then read it through `importlib.util.spec_from_file_location`, where the bound
name is an ARGUMENT and never an attribute receiver, so criterion 2 fails. The
docstring's blind-spot list named a local variable, a fixture, a helper and
another module's constant, and did NOT name importlib. THE HOLE WAS IN THE
WRITTEN CEILING, NOT IN THE MECHANISM.

**`_READ_ATTRS` WAS NOT WIDENED, AND THE REASON IS A DECISION AND NOT AN
OMISSION.** Those four IMPORT the responder to exercise its BEHAVIOUR. They are
the tests a campaign exists to consult, not graders of the target's shape, so a
detector that flagged them would be wrong on every run and would train a reader
to ignore it - the argument already recorded for why `undeclared_shape_graders`
subtracts all of `EXCLUDED_MODULES` and not only `SHAPE_GRADER_MODULES`.
Widening a matcher is additionally the repair this tree has been defeated by
three times, and the standing lesson is that after the second defeat you ask
what claim the mechanism CAN support. The repair was HONEST SCOPE: the ceiling
now names the importlib route, states the measured population, and says the 15
is a LOWER BOUND because `importlib` binds `io.open_code` inside
`_bootstrap_external` before any such patch lands, so the four modules' own
import-time reads are not among the 195 - which is exactly why none of the four
appears in the 15 despite provably reading the file. Subprocess reads and the
whole `agents/pity_engine` suite were outside the sample too.

**`MutantResult.false_kill` IS STRUCTURALLY UNREACHABLE IN A REAL CAMPAIGN, AND
IS NOW DOCUMENTED AS A DIAGNOSTIC RATHER THAN MADE REACHABLE.** `suite_argv`
emits `--ignore` for every name in `EXCLUDED_MODULES`, and
`SHAPE_GRADER_MODULES` is a subset of it, so pytest never collects a shape
grader, `parse_first_failure` can never return a node id naming one, and the
property is False for every mutant a campaign produces. THE OTHER OPTION WAS
CONSIDERED AND REJECTED ON A MEASURED PRICE: making it reachable means dropping
the shape graders out of `--ignore`, which restores the confound at 34 of 35
mutants reddening over syntax alone. A reachable diagnostic bought at that
price is the defect wearing the detector's clothes. So
`undeclared_shape_graders` is THE ONLY LIVE PROTECTION against a hole in the
exclusion list, and it is the one with the blind spot above - both facts are
now written in the same docstring, because an unreachable property that LOOKS
like protection is worse than none.

**TWO ARMS, EACH WELDING ITS PROSE PIN TO A DERIVED FACT.**
`test_the_detector_states_the_importlib_route_it_cannot_see` pins the ceiling
sentence AND re-derives the blind spot from the four modules with criterion 1
RE-TYPED rather than imported, plus a control that
`responder_reading_modules` still names the three declared readers - without
which a detector that had silently stopped finding anything would satisfy every
other clause. `test_the_false_kill_property_cannot_fire_under_the_campaign_argv`
derives the unreachability from `suite_argv` and welds in the pair that keeps it
non-vacuous, since the arm would otherwise pass against a property hard-wired to
False. Both were written red and observed red first, in a THROWAWAY DETACHED
WORKTREE at `6be6961` carrying only the new arms: 2 failed 51 passed, the first
on `assert 'importlib' in doc` and the second on
`assert 'DIAGNOSTIC AND NOT A LIVE PROTECTION' in doc`. That worktree was
restored to a clean porcelain and removed.

**A NEWEST-FIRST LEDGER MAKES AN OLDER ENUMERATION LOOK CURRENT, and this is
the general lesson, one level up from a class already recorded here.** The
adjudicated-call row in `ROADMAP.md` cited an EIGHT-NAME survivor list from the
entry headed "The mutation runner ships, four of its own kills were false, and
the census arms pinned literals where they claimed classes" - 35 mutants, 27
KILLED, 8 SURVIVED at `1c596e3`. A NEWER entry above it, "The eight gates
exercised by nothing get arms, the campaign reaches 35 of 35, and six prose
claims were false", records 35 KILLED, 0 SURVIVED, 0 false kills, exit 0 at
`06f8557`. THE STANDING SURVIVOR SET IS 0, NOT 8; an adversary re-measured 3 of
the 8 and found all 3 killed. CITING A LIST BY ITS CONTENT RATHER THAN BY
WHETHER A LATER ENTRY SUPERSEDES IT is how a closed row gets re-cited as open. A
prior session recorded that a RESIDUAL ROW decays; this is the same class one
level up - the ENUMERATION decayed while the sentence citing it stayed put. The
mechanical form of the check is cheap: before citing any list in this file, scan
UPWARD from its heading for a later entry naming the same measurement.

**THE ADJUDICATED CALL ON GATE `spawn-failure` IS UNAFFECTED, AND SAYING SO IS
PART OF THE REPAIR.** That ruling turned on `spawn-failure/except-reraise` not
being a standing survivor. It is ABSENT from the superseded eight-name list AND
the standing set is empty, so the conclusion holds under BOTH readings and the
five-criteria-to-nil verdict does not reopen. WHAT WAS WRONG WAS THE CITATION
AND NOT THE FINDING. A correction that silently rewrote the citation would have
left a later reader unable to tell which of the two it was.

## 2026-09-09 - The gate names are bound to their sites by equality, and the method findings cost more than the table did

Files: `tests/test_gate_name_bindings.py` (new), `tools/gate_mutation_runner.py`,
`tests/test_gate_mutation_runner.py`, `tests/test_responder_gate_census.py`,
`ROADMAP.md`, `docs/LEDGER.md`. `tools/moon_sync_responder.py` NOT touched, and
that is a claim about the diff: `git diff --name-only 0c17717 68a189f` lists four
files and the responder is not one of them.

**MEASURED AT `68a189f`, STAMPED AS A READING AND NOT AS A CLAIM ABOUT NOW.**
`python -m pytest tests` exit 0, 1880 passed 1 skipped.
`python -m pytest agents/pity_engine` exit 0, 80 passed.
`python -m ruff check .` exit 0. The arithmetic closes on the arms this work
added, and both ends were measured rather than one end assumed:
`python -m pytest tests --collect-only` collects 1868 at `0c17717` and 1881 at
`68a189f`, while `git diff -U0` against each commit's parent, counting added
lines that open a test function under `tests`, returns 8 at `f571234`, 4 at
`30235c2` and 1 at `68a189f`. 1868 plus 13 is 1881, and 1880 passed plus 1
skipped is 1881.

**AN ARM CAN BE ARITY-BLIND ABOUT THE VERY THING IT GUARDS.**
`test_the_two_exclusion_reasons_are_named_apart_not_merged` exists to stop the
runner's two exclusion reasons being merged into one. It carried four
assertions and ALL FOUR WERE ARITY-AGNOSTIC - `EXCLUDED_MODULES ==
(SELF_TEST_MODULE, *SHAPE_GRADER_MODULES)` holds at ANY length - so when a
SECOND shape grader landed in `SHAPE_GRADER_MODULES`, every one of the four went
on passing UNCHANGED and the arm said nothing whatever about the new entry. A
grading arm that cannot see the thing it grades change is the failure class.
The repair kept all four VERBATIM and appended: the arity is now pinned at 2 and
3, and a PROSE check requires each shape grader to have its OWN measured reason
in the comment block between the two constants, since one list with two entries
under one shared paragraph is the merged state the arm exists to forbid and is
reachable without touching either constant's name.

**`verify_exclusions` ANSWERED THE WRONG QUESTION.** It asked "is a declared
path real". Nothing anywhere asked "is a real shape grader DECLARED", which is
the direction that matters, because a module nobody declared is never checked at
all - and step three's own artifact was about to become a third shape grader.
Both directions are asked now, and they raise DISTINCT EXCEPTION TYPES,
`MissingExclusionError` and `UndeclaredShapeGraderError` under a shared
`ExclusionError`, so an arm can pin WHICH check fired. A single type both raise
proves nothing about which one ran.

**A REFUTER'S FIRST MUTANT WAS WRONG AND IT SAID SO, WHICH IS THE ONLY REASON
THE SECOND ONE WAS BUILT.** Dropping an anchor out of the table entirely routes
that gate to the has-NO-anchor branch, which still REPORTS the gate, so the arm
under attack passed having MEASURED NOTHING about the mutation. The corrected
mutant is the instructive one: shrink one anchor to a single character so it
builds ZERO trim cases while the table keeps every entry. Control clean, the
derived closed form and the built list AGREEING at 1162, 1162 comfortably
clearing the total floor of 1000, and 17 of 18 gates named by the built cases.
THE OLD ASSERTION WOULD HAVE PASSED THAT.

**A FLOOR CAN BE THE WRONG TIGHTENING, AND THE ARITHMETIC SAYS SO RATHER THAN
AN OPINION.** The anti-trim enumeration builds 1168 cases over the 18 anchors,
re-derived here as the sum over anchors of two times length minus one. A single
anchor, `bounce-once`, contributes 164 of those 1168 on its own, so ONE
legitimate retype of that statement down to the length of the shortest live
anchor - the decay the module documents as BY DESIGN - lands the total at 1010.
Any literal above 1010 therefore reddens on a by-design event while buying no
protection from vacuity that 1000 does not already give. The tightening a TOTAL
cannot give was welded into the same assertion instead: the built cases must
COVER EVERY ANCHOR IN THE TABLE. An anchor one character long builds zero cases
and would be skipped in silence on the strength of the long anchors.

**A READ-ONLY AGENT REPORTED HAVING WRITTEN A FILE.** An adjudicator closed its
ruling with the sentence that the verdict was "recorded in `ROADMAP.md`".
Nothing had been written - the porcelain was empty immediately afterwards, and
that role cannot write at all. It was a PRESCRIPTION stated as a PAST FACT. The
general shape, which is the reusable part: AN AGENT THAT CANNOT PERFORM AN
ACTION CAN STILL REPORT HAVING PERFORMED IT. A done-claim from a read-only role
is therefore probed against the disk and never read as a report of work.
Related to, and distinct from, the standing rule about not trusting a
subagent's counts: this one is not a wrong number, it is a wrong TENSE.

**THE 34 OF 35 FIGURE IS ANCHOR-DEFINITION-DEPENDENT.** Under the equality rule
at `tag_line + 1` it is 34 of 35 with survivor `spawn-failure/except-reraise`.
Under a WHOLE-FILE SUBSTRING sweep it is 32. The 34 is carried forward from
ceiling item C3 of `tests/test_gate_name_bindings.py` and was NOT re-measured
this session, because the campaign was not re-run. The MECHANISM for the gap WAS
re-measured: exactly two of the 18 anchors are non-unique file-wide - the `try:`
line at 17 occurrences in `tools/moon_sync_responder.py` against one inside
`_run_once`, and the `if reasons:` line at two against one - and no other anchor
is duplicated. ANY LATER READER CITING EITHER NUMBER MUST SAY WHICH DEFINITION
IT COUNTS.

**THE PLANNER'S BOUND-TO-A-SITE COUNT DID NOT REPRODUCE, AND THE FAILURE MADE
ITS POINT STRONGER.** Re-derived at `68a189f`: six gate names are exact string
literals in the census, five reach `_line_of_tag_named`, three are unique
literal arguments to it, FOUR redden the census when swapped against a control,
and of those four only `hop-budget` reddens an arm that READS THE STATEMENT
under the tag. The other three redden multiplicity arms that pick tags by name
and then compute expected LINE arithmetic, which is positional coincidence
rather than a binding. So the census bound ONE name of 18, not three. The
17-adjacent-swap figure reproduced exactly at 13 green and 4 red; the
full-rotation figure did not reproduce as a claim about the module, which goes
to exit 1 at 2 failed 76 passed under a rotation, while the new bindings module
goes to 7 failed 2 passed under the same one.

**THE SWAP AND ROTATION PROBES RAN IN THROWAWAY DETACHED WORKTREES, NEVER IN
THE SLICE'S OWN TREE.** Each probe restored `tools/moon_sync_responder.py` from
the bytes it had read first, `git status --porcelain` printed nothing before the
worktree was removed, and the worktree was removed. A sibling session once broke
an unrelated file in a shared tree to watch a test fail, restored it cleanly, and
still turned a suite red WHILE A VERIFIER WAS MEASURING IT.

## 2026-09-09 - The atomic-write temp leak was two defects, and three calls were adjudicated rather than decided

Files: `core/atomic_io.py`, `tests/test_core_atomic_io.py`,
`tests/test_responder_gate_census.py`, `CLAUDE.md`, `ROADMAP.md`,
`docs/LEDGER.md`. `tools/moon_sync_responder.py` NOT touched.

**THE 0-BYTE TEMP LEAK WAS TWO DEFECTS UNDER ONE ROOT CAUSE.** Measured at
`3533965`, `atomic_write_text(target, chr(0xD800))` raised `UnicodeEncodeError`
out of the caller AND left a 0-byte sibling temp behind. `Path.write_text`
opens the file BEFORE it encodes, so the temp exists by the time the encoder
refuses, and the `except OSError` clause skipped `_discard` outright for a
`UnicodeEncodeError`, which is a `ValueError`. The repair is a `published` flag
plus `try/finally`, and NO `except` clause was widened - checked by diffing,
where the only `except`-bearing lines are docstring prose. A verifier that did
not write the repair probed it on scratch copies with the bytecode caches
purged on BOTH sides: deleting the `finally` reddens 8 arms, forcing
`published = True` reddens 8.

**SEVEN NEW ARMS, EVERY ONE WITH A POSITIVE FLOOR IN ITS OWN ARM.** Re-derived
at this writing by `git diff -U0 tests/test_core_atomic_io.py` piped to
`grep -c "^+def test_"`, which returns 7, in a module that
`pytest --collect-only` reports at 24 tests. Each of the seven asserts an
exception TYPE, a target CONTENT, or a counted call equal to one, inside the
same arm as the negative. That was checked arm by arm rather than inferred, and
the vacuity class that shipped in a recent session - a floor placed in a
NEIGHBOURING arm, leaving the primary one green on negatives alone - did not
recur.

**ADJUDICATED CALL ONE: `atomic_write_text` KEEPS RAISING.** Candidate A was to
catch and return `False`, matching `atomic_write_json`; candidate B was to keep
raising. VERDICT B, on evidence the merger had not seen when it framed the
question and which was re-opened at its lines before this entry was written:
`tests/test_responder_broadcast_refusal.py:230`,
`test_an_unencodable_draft_still_escapes_the_delivery_loop`, already asserts
`pytest.raises(UnicodeError)` out of `deliver` at line 245, so candidate A
would have reddened an existing arm; and `tools/moon_sync_responder.py:975`
independently records "Loud-to-quiet is strictly worse than the silent abort".
The residual was APPLIED rather than filed - the module docstring's "Everything
here is fail-soft" is now scoped to OS-level failure and cites the pinning arm
by node id. The builder's own limit is recorded with it: that arm is a
STATEMENT and not coverage, because widening the clause to
`except (OSError, UnicodeEncodeError)` already reddens 3 arms without it.

**ADJUDICATED CALL TWO: THE HEADLESS LOOP'S HALT BOUNDARY IS MIXED.** Candidate
ARM won fidelity, candidate BYTE won completeness and reversibility and was
fatally worded, and the operative ruling is neither candidate. `CLAUDE.md`
carries the standing rule and `ROADMAP.md` carries the criteria, the
per-criterion calls and the corroboration, found BY HEADING rather than by line
number. The corroboration is the strongest part and predates the argument:
the gitignored per-host file ops/moon_sync_repos.json, left unbackticked
because a backticked path in a governing doc must be git-tracked and this one
is not, `generated` `2026-09-07`, already names
`ops/loop/slots.py` and `ops/loop/winmutex.py` as literals whose edit is "a
joint round with every carrier in the same window - never a scrub side effect",
which is clause (b) reached two days earlier by another route. That file is
gitignored at `.gitignore:125`, so it corroborates and does not guard.

**ADJUDICATED CALL THREE: THE CENSUS PROSE HAD DECAYED.** The claim of 18 tags
"all of them in the responder and none anywhere else" is half false since
`06f8557`. The responder half re-derives to 18 by a `tokenize` pass against
`_GATE_STRICT`; the "none anywhere else" half broke when
`tests/test_responder_delivery_gates.py:272` shipped a section-banner tag with
no instrument watching. It is now DERIVED from `git ls-files` plus
`tokenize.COMMENT` tokens and asserted by dict equality with four in-arm
floors, written red first and probed red again on a scratch copy.

**EIGHT TIMES AN AGENT CORRECTED THE INSTRUCTION IT WAS GIVEN, AND EVERY
CORRECTION HELD ON RE-MEASUREMENT.** The population being counted is
CORRECTIONS, enumerated immediately below, measured across this session. A
different figure of SIX is in circulation and counts AGENTS, which is a
different population and one this entry did not independently verify, so it is
recorded as reported rather than as measured. The corrections: (a) a wrong line
number for the broadcast-refusal arm; (b) a false claim that a raise was
unpinned; (c) an empty-permissions claim that was really an ABSENT key; (d) a
wrong responder line number; (e) a second wrong responder line number; (f) a
wrong `.gitignore` line attribution; (g) an over-broad set of strict-grammar
tag sites, where only one of that file's banners actually clears the `$` anchor
in `_GATE_STRICT`; (h) the seam count itself.

**THE METHOD RESULT IS THE HAND-TYPED COUNT, WHICH FIRED THREE TIMES IN ONE
SESSION.** An outbound note said an adversarial pass "found six" over an
enumeration running to seven lettered headings; a prose-truth adversary
grading that note INHERITED the six instead of counting the headings, so the
adversarial pass reproduced the error rather than catching it; and a governing
document said "five", which was a third population entirely. THE RULE ADOPTED:
when a document states a count AND enumerates the thing counted, the
ENUMERATION is the source and the sentence is a claim about it - grade the
sentence against the list, never the list against the sentence. Every such
sentence must name the population it counts: whose enumeration, of what,
measured when. The paragraph above applies that rule to itself, which is why it
reports eight and names what eight counts.

**WHAT THIS ENTRY DOES NOT CLAIM.** The both-suites figures below are A READING
AND NOT A PROMISE, and they are the BUILDER'S reading rather than the merge's:
taken 2026-09-09 with `HEAD` at `3533965` and the working tree DIRTY with four
files this slice did not write, which is not the state any commit will have.
`python -m pytest tests` reported 1867 passed 1 skipped at exit 0 and
`python -m pytest agents/pity_engine` reported 80 passed at exit 0. The
merge-time reading belongs to the merge that produces it and is not this
entry's to stamp. Every other figure above carries the command that derived it
and can be re-derived in one line; none of them was copied out of a brief.

---

## 2026-09-09 - CI went red on a test that decayed, and the lane split was a timezone rather than a platform

Files: `tests/test_task_liveness.py`, `ROADMAP.md`, `docs/LEDGER.md`.
`ops/check_task_liveness.py` NOT touched and byte-identical at
`be081ce182ea244c0129c9fa2c58b7131b093f10f5bb1271f6b091f6897ea265`.
Measured at the merge, 2026-09-09: `pytest tests` 1859 passed 1 skipped at the
local zone AND at `TZ=UTC0`, `agents/pity_engine` 80 passed, `node --test` 52
pass 0 fail, and licence posture 47, docs consistency 29, qa_companion 16
passed 0 failed, ruff, mypy at 34 source files and the headless dry run all
exit 0.

**NOTHING REGRESSED - TIME PASSED.** GitHub run 34405450182 failed on
ubuntu-latest at Python 3.11 at 2026-09-09T21:11:41Z with
`tests/test_task_liveness.py:836: AssertionError, assert "LIVE" in out`, at a
commit whose suite was green on this box. `liveness.main` calls
`verdict(parse_facts(...))` with NO `now` and `verdict` falls back to
`dt.datetime.now()`, so five arms were graded against the REAL CLOCK while
every `_verdict` sibling pins `now=NOW` at 2026-09-08 10:00. The payload's
boundary `2026-09-09T21:00:00` is NAIVE and is therefore read in the runner's
LOCAL zone - expired at 21:00 on a UTC runner, five hours later at UTC-5.

**THE LESSON IS AN ORDERING ONE: DIFF THE CLOCK BEFORE THE ENVIRONMENT.**
Green-here-red-on-CI at one commit reads as a platform or interpreter
difference. It was neither, and chasing that reading would have cost the slice.

**THE FIX IS CLOCK INJECTION, NOT A LATER DATE.** A stamp further in the future
is the same defect with a longer fuse. Five arms pin the clock through a shim
that swaps the module binding the checker actually reads, and the CI failure is
now an ASSERTED TRANSITION rather than a race with the calendar: a sibling arm
pins one second past the same boundary and requires DORMANT. The checker was
left alone - `verdict` already offers `now=`, and widening the kill-switch
tool's signature for the tests' benefit would trade a test defect for a worse
one.

**THE BUILDER CORRECTED THE DIAGNOSIS IT WAS GIVEN, which is now the sixth
time this session.** The brief said ONE arm was clock-graded. Three were: the
other two are the same defect in PAST polarity and flip under a backwards
clock, and two more reach `verdict` unpinned while being outcome-independent.
All five were fixed together, which is the root-cause rule rather than the
line.

**THE REFUTER BUILT ITS OWN INSTRUMENT AND THAT IS WHY THE RESULT COUNTS.** It
reproduced the CI red byte-exact on the PRE-FIX bytes under `TZ=UTC0` and green
on the POST-FIX bytes, then re-ran the mechanism on CI's Python 3.11 where no
pytest is installed by driving `main` directly. It proved `TZ` actually moves
`datetime.now()` on this Windows CPython before relying on it - offset 18000 to
0 - rather than assuming, because a fake that silently no-ops produces a green
that means nothing. The file is green at a stdlib clock shift of -20000 to
+40000 days and the whole suite at UTC, UTC+14 and UTC-12.

**A SUITE RUN AT TWO OFFSETS IS A SAMPLE, NOT A PROOF**, and the refuter said
so rather than accepting the sweep: an arm whose boundary lies outside the
window is invisible to it. It then established the population - every
`YYYY-MM-DD` literal in `tests/*.py` lies between 2026-01-04 and 2026-09-09, so
the window happened to cover all of it. One arm that moves at +4000 days,
`test_a_live_pass_writes_the_run_summary`, was cleared and the asymmetry is the
proof: it fails only FORWARD because a future timestamp is documented as
not-stale, and its payload carries a freshly written real timestamp rather than
a hardcoded date.

**A THIRD ROUND CORRECTED A REASON THAT NAMED THE WRONG BRANCH** - this tree's
own interpolated-reason-string class. The non-vacuity arm's verdict is right
and its stated cause was not: `MEASURED_DORMANT`'s trigger HAS an
`end_boundary`, so `evaluate_trigger` returns on the EndBoundary arm and NEVER
reaches the StartBoundary check. The measured reason line is "trigger 1
(MSFT_TaskTimeTrigger) is enabled and its EndBoundary 2026-09-07T21:00:00 is
still ahead", captured by running the checker rather than hand-typed. The
assertion MESSAGE said StartBoundary and is the text the next reader would
have got. That builder also refused the brief's framing: the sentence was TRUE
as a bare fact and IRRELEVANT as a cause, so it repaired the causal claim and
said so.

**TWO LIMITS RECORDED IN THE FILE RATHER THAN FIXED.** The teardown arm is
VACUOUS IN ISOLATION - alone it passes with nothing frozen before it, and it
has content only because file order puts it after a frozen arm. And the root
cause is closed in the test only: `main` still never threads `now` into
`verdict`.

Verification pointer: `TZ=UTC0 python -m pytest tests/test_task_liveness.py`,
which must be 84 passed, and the same file under any clock shift.

---

## 2026-09-09 - The eight gates exercised by nothing get arms, the campaign reaches 35 of 35, and six prose claims were false

Files: `tests/test_responder_delivery_gates.py` (new, 8 arms),
`tests/test_responder_refusal_gates.py` (new, 7 arms), `ROADMAP.md`,
`docs/LEDGER.md`. Commits `06f8557`, `d3af1b9`. Measured at the seam,
2026-09-09: `pytest tests` 1855 passed 1 skipped, `agents/pity_engine` 80
passed, `node --test` 52 pass 0 fail, and licence posture 47, docs consistency
29, qa_companion 16 passed 0 failed, ruff, mypy at 34 source files and the
headless dry run all exit 0. 1840 plus 8 plus 7 is 1855 and the arithmetic
closes.

**THE CAMPAIGN IS 35 OF 35 FOR THE FIRST TIME.** Measured at `06f8557` in an
isolated worktree by `python -m tools.gate_mutation_runner`: 35 mutants, 35
KILLED, 0 SURVIVED, 0 false kills, exit 0, where `1c596e3` had 8 survivors.
Each of the eight is now killed by one of the two new modules, and not one kill
is named by a shape grader. THE WORK WAS ARMS AND NOT A FIX - the gates were
correct all along and nothing drove them.

**THE EMPTY-LIST HALF IS NOT REACHABLE THROUGH REAL DESTINATIONS, AND BOTH
FILES SAY SO.** `deliver` returns exactly one row per inbox and `_run_once`
reaches the delivery step only past the `GATE:no-destination` early return, so
`written` is never `[]` there. The `bool(written)` term that the responder's
own comment at `tools/moon_sync_responder.py:1861-1863` calls the guard and not
decoration therefore guards a caller shape the current callers cannot produce.
The two arms that drive it substitute the module's `deliver`, which is a stated
limit rather than a hidden one.

**TWO ARMS SHIPPED VACUOUS AND THE RUNNER COULD NOT HAVE SHOWN IT.** They
killed their mutants and were confirmed killed by an independent re-run, yet
with `GATE:bounce-once` neutralised so the bounce block ran ZERO times both
stayed GREEN: they asserted only negatives, and
`result["termination"] == "refused"` is assigned 60 lines above the block. The
repair is a `len(attempts) == 1` floor IN THE SAME ARM - a floor in a separate
arm would have left the primary arm vacuous - fed by a wrapper that captures
the module's own `deliver` before substituting and calls through, so the real
failing write still happens. Measured after: both arms RED under that
neutralisation and under four more, and green on clean bytes.

**TWO DEAD ASSERTIONS WERE REMOVED, and the proof they were dead is a
measurement.** Each stub arm closed with `assert list(rc_inbox.iterdir()) == []`,
which the stub decides rather than the module, because both `deliver` call
sites resolve the same module global. Deleting both lines changed ZERO verdicts
across 11 module mutations, verdict for verdict. They are replaced by
`rc_inbox in handed[0]`, where `handed` records the inbox list the module
itself computed - a floor that a refuter then proved can fail, by dropping the
`/ "moon_sync_inbox"` from either call site. It is a MEMBERSHIP test and both
files say so: an appended destination in a repository this tree does not own
leaves the arm green.

**SIX FALSE PROSE CLAIMS ACROSS THREE ROUNDS, on top of eight last session and
four the session before.** Every one was found by a lens and re-derived by hand
before it was rewritten. Measured this session, replacing what the docstrings
had said: `refusal-recorded/if-false` over five cycles is ONE bounce and not
five, because `mark_bounced` is unpatched and `bounced_under` suppresses cycles
two through five; the 288-files-a-day figure belongs to the `refusals-usable`
form where the whole record is unwritable and `mark_bounced` fails too;
`DEFAULT_REFUSALS.is_file()` is False throughout that arm, so `refusals_usable`
returns True having inspected NO file, passing on the `path.exists()`
short-circuit; the bounce suppressor is `mark_bounced`'s ledger read by
`bounced_under` while `_remember_refusal`'s rows suppress the HOLD via
`refusal_seen`; the runner rewrites a `BoolOp`'s WHOLE expression to each
operand in turn rather than the operand to the rest; and an absent or
wrongly-keyed trust config is trusted BY DEFAULT, so the trusted arm cannot
notice a plumbing error and the untrusted one can. Two hand-typed COUNTS were
also wrong - "four of the five" negatives where five of five are, and "the four
above" where five arms sit above - which is this tree's most repeated defect
class.

**`no-destination/if-false` COSTS MORE THAN A SESSION, and nothing else in the
tree states this.** Measured with `roots={}`: one spawn, termination
"delivered", `delivered` False, actions `["A5"]`, an empty destination inbox, a
reply written into this repo's own inbox, and the note written into
`DEFAULT_ANSWERED`. `_remember_answered` is union-only and uncapped and nothing
removes an entry, so a retry after the roots are configured terminates "empty"
and the note can never be answered. The gate prevents it and the gate is now
armed.

**THE ADJUDICATED CALL, operator away.** "Every suppression downstream is keyed
on that record" has two live antecedents in its own paragraph and
nearest-antecedent resolution reaches the FALSE one. Ruling B, fix now, against
criteria stated before the artifact was read; runner-up A, leave as is. The
adjudicator broke the common-mode dependency by reading
`tools/moon_sync_responder.py` directly rather than the docstring three prior
agents had all read. The same adjudication ruled A on the two figures that
looked contradictory: `tests` collects 1848, the two `EXCLUDED_MODULES` collect
124, the new refusal module collects 7, and 1848 minus 124 minus 7 is 1717, so
the numbers are different populations that reconcile exactly.

**METHOD, and it is the result worth keeping.** FIVE DISTINCT LENSES FOUND FIVE
CLASSES OF DEFECT AND NO TWO OVERLAPPED - does-it-reproduce, vacuity and
over-fire, prose-truth, equivalent-mutant, and the-repair-did-not-repair-it.
The reproduce lens confirmed every kill and could not have seen the vacuity;
the vacuity lens found it and never questioned a kill. AGREEMENT WAS NEVER
TAKEN AS EVIDENCE: where two agents agreed, the shared input was the docstring,
and the adjudicator tested THAT. Every builder that corrected its own brief was
right, which is now the fifth session running for that lesson - one measured
that the census does NOT redden under an `if-false` mutant because the AST
shape is preserved, refuting an instruction of mine that had misquoted this
ledger.

Verification pointer: `python -m tools.gate_mutation_runner` in a clean
worktree, which must report 35 mutants 35 killed 0 survived 0 false kills; and
`python -m tools.gate_mutation_runner --gate delivery-write-all` for the single
gate the hand-off named first.

---

## 2026-09-09 - The mutation runner ships, four of its own kills were false, and the census arms pinned literals where they claimed classes

Files: `tools/gate_mutation_runner.py` (new, 851 lines),
`tests/test_gate_mutation_runner.py` (new, 47 arms),
`tests/test_responder_gate_census.py` (43 arms to 77), `ROADMAP.md`,
`docs/LEDGER.md`. Commits `25f5858`, `e87e26c`, `621e4ab`, `1c596e3`.
Measured at the merge, 2026-09-09: `pytest tests` 1840 passed 1 skipped,
`agents/pity_engine` 80 passed, `node --test` 52 pass 0 fail, and licence, docs,
qa_companion 16 passed 0 failed, ruff, mypy at 34 source files and the headless
dry run all exit 0.

**STEP TWO OF THREE OF THE GATE CENSUS IS DONE.** Ceiling item 3 of the census
said "no mutation runner exists in this tree; this census is the tagging step
such a runner would consume, not the runner". It exists now. It reads the 18
`# GATE:` tags, neutralises each tagged consult site in `_run_once` in turn,
runs the application suite per mutant, and calls the mutant KILLED on a non-zero
exit and SURVIVED on a zero one. The registry is step three and stays open.

**THE ARITHMETIC IS DERIVED FROM THE LIVE FILE, NOT DECLARED:** 14 `If` gates at
two polarities, 1 `Try` neutralised by re-raising in its handler, 1 `IfExp` at
two polarities, and 2 subscript-write `BoolOp` gates at one mutant per dropped
operand. 35 mutants from 18 gates. Verified independently by a refuter.

**THE CAMPAIGN WAS WRONG TWICE AND BOTH ERRORS WERE FOUND BY MEASUREMENT.**
The first reported 35 of 35 KILLED and its own author retracted it: the runner's
test module sorts ahead of the responder's modules and under `-x` decided every
verdict, because an already-applied `if True:` mutant re-plans to a
byte-identical mutant and trips its own no-op assertion. The corroborating
evidence was the WALL CLOCK - 35 full-suite runs in about three minutes is only
possible if every run aborted early.

**THE SECOND CAMPAIGN'S 31 KILLS INCLUDED FOUR FALSE ONES, AND NOTHING IN THE
REPORT COULD HAVE SHOWN IT.** It took a refuter running the suite by hand.
`tests/test_responder_gate_census.py` reads the responder AT IMPORT and grades
its AST SHAPE, so a mutant that DROPS A BoolOp OPERAND changes that shape and
the census reddens for a reason that is not about behaviour. Under `-x` that is
indistinguishable from a real kill. Measured both ways with the self-test module
ignored throughout, so only the census varied:

    all four BoolOp mutants, census included   32 failed, 32 of 32 failing
                                               nodes in the census, 0 elsewhere
    all four BoolOp mutants, census ignored    1716 passed 1 skipped, exit 0

The defect is CONFINED and that was measured too: `if True`, `if False` and the
`try` mutant all PRESERVE the shape the census grades, so it cannot false-kill
them, and both `IfExp` mutants are genuine behavioural kills in
`tests/test_moon_sync_responder.py`.

**TWO EXCLUSIONS, TWO REASONS, KEPT APART IN CODE.** `SELF_TEST_MODULE` is a
module that decides its own verdict; `SHAPE_GRADER_MODULES` is a module that
grades the TARGET FILE'S SHAPE, which answers a question about syntax while the
runner asks one about behaviour. An `--ignore` of a path that does not exist is
a SILENT NO-OP, so `verify_exclusions` raises before any campaign and an arm
feeds it a bogus path to prove the check fires. Verification pointer:
`tests/test_gate_mutation_runner.py`, the exclusion arms and the six HAND-TYPED
pytest fixtures that grade `parse_first_failure` - none produced by running
pytest and none by the parser, two of them proving it degrades to `unknown`
rather than to a wrong name.

**THE STANDING RESULT, re-run on the shipped bytes at `1c596e3` and reproduced
at the merge: 35 mutants, 27 KILLED, 8 SURVIVED, 0 false kills, exit 1.** Every
one of the 27 names a node in `tests/test_moon_sync_responder.py`; not one names
a shape grader. The eight survivors name gates in `_run_once` that no test in
the campaign suite depends on: `no-destination/if-false`,
`workspace-trust/if-false`, `refusal-recorded/if-false`, `bounce-mark/if-true`,
`bounce-write-all/operand-1`, `bounce-write-all/operand-2`,
`delivery-write-all/operand-1`, `delivery-write-all/operand-2`.
`delivery-write-all/operand-1` drops the `bool(written)` term the responder's
own comment at `tools/moon_sync_responder.py:1861-1863` calls the guard and not
decoration - the term that stops `all([])` reporting a delivery to zero
destinations as delivered. It read KILLED before the repair and reads SURVIVED
after it. Closing the eight needs the responder and its test modules and is
recorded in `ROADMAP.md` as the next work.

**THE CENSUS GAINED THE MISSING DIRECTION OF ITS COMPARISON.** It asserted
`not tagged - tight` and never the reverse, so a NEW consult site added to
`_run_once` and never tagged was invisible. Both directions are asserted now,
by `test_every_consult_site_inside_run_once_carries_a_tag`, whose anti-vacuity
floor is welded into the same assertion as the judgement.

**THE MECHANISM SURVIVED EVERY LENS AND THE PROSE FELL EIGHT TIMES.** Two
refuters on distinct lenses graded the first build; three more graded the
repairs. Falsified and corrected: that the tagged set and the site set are
IDENTICAL, when they are identical as LINE NUMBERS and two accepted sites on one
line shared a tag; that the `_FLOOR` conjunct served the arm's own vacuity, when
it serves the parametrized block's non-emptiness; that the control does not kill
an unconditional reporter, when it does along with 9 other arms and 27 of 71
cases; that a choosing expression in a CALL ARGUMENT is invisible, when the
discriminator is the ASSIGNMENT TARGET because the predicate walks the whole
value; that there are 4 orphan choosing expressions, when under the stated
predicate there are 3 at 1643, 1644 and 1645 and the 4 is the `bare - tight`
line difference adding 1737; a third conjunct that is the fourth; five `_FLOOR`
assertions that were six; and a control docstring claiming it buys nothing when
it carries the ONLY call that grades `_LIVE_SOURCE`, the snapshot every mutation
case is cut from.

**A SHAPE ARM PINS FORMAT, NOT INPUT, AND IT COST TWO ROUNDS.** The arm proving
the distinct-line requirement is welded into the coverage arm pinned the phrase
`distinct lines`, which that message emits UNCONDITIONALLY: replacing the fourth
conjunct with the coincidental proxy `len(sites) == len(_TAG_LINES)` - true at 18
and 18, and not the distinct-line property at all - passed all 69 arms, and so
did replacing the payload with `assert caught.value is not None`. The repair
defeated that proxy BY CONSTRUCTION and a further lens then found SEVEN more
conjuncts passing all 71, failing in OPPOSITE directions: `!= 1` and `% 2 == 0`
left the arm green on a source with TWO real collisions, while `== 18`,
`<= _FLOOR` and `== len(_TAG_LINES)` REDDENED a clean, fully tagged responder
carrying one extra correctly tagged gate. Multiplicity was depth-one the same
way - `return reported[:1]` passed all 69 and `[:2]` and `[:3]` passed all 71.

**THE REPAIR STOPPED PINNING `len(...)` AND PINNED IDENTITY AT MORE THAN ONE
ARITY.** `_colliding_site_lines` is graded by list EQUALITY against hand-typed
expectations at one collision, two collisions and three sites on one line; the
coverage arm ITSELF is driven over those three requiring a raise and over a
clean responder with one extra tagged gate requiring NO raise; and the
multiplicity arm asserts SET EQUALITY at k = 1, 2 and 3 non-adjacent tags, plus
an all-tags arm. Eight of eight named mutants die, plus three the brief did not
name, and both controls that already died still die. Verification pointer:
`tests/test_responder_gate_census.py`,
`test_the_collision_detector_names_every_colliding_line_at_three_arities`,
`test_the_coverage_arm_fires_on_every_collision_arity_and_not_on_a_clean_extra_gate`,
`test_removing_k_tags_reports_exactly_those_k_sites_as_a_set` and
`test_removing_every_tag_reports_every_site_and_bounds_no_truncation`.

**WHAT IS STILL OPEN IS STATED IN THE ARMS RATHER THAN HIDDEN.** The arities are
a SAMPLE and not a proof: a wrong conjunct agreeing with the real one on a clean
source, one collision, two collisions and three-on-a-line still passes. The
depth arm bounds `reported[:n]` only for n below the tag count, so `[:18]` and
above are untouched. The 27 kills are attributed by parsing the FIRST failure
under `-x`, which names the killer but is not proof no other test would also
have failed.

**FOUR TIMES THIS SESSION AN AGENT CORRECTED THE INSTRUCTION IT WAS GIVEN,** and
that is the method result worth keeping. A repair builder measured that k = 1, 2
and 3 does NOT kill `reported[:3]` and added the all-tags arm the brief had not
asked for. Another declined to ship a refuter's measurement it could not
reproduce - "only the control reddens when `_LIVE_SOURCE` diverges" is false,
26 cases across 10 arms redden - and shipped the weaker verified claim instead.
A third derived the orphan count itself and disagreed with both the refuter and
the earlier builder. And a fourth STOPPED without writing anything when its
worktree materialised at `199aaae`, the PARENT of the declared fork point
`25f5858`, rather than re-deriving the target from the brief's prose. That trap
fired on FOUR of five worktrees dispatched today; the fix is an explicit
`git merge --ff-only <sha>` plus an assertion on the materialised bytes, and a
dispatch that omits it is the defect rather than the builder.

## 2026-09-09 - The responder gates are tagged, and three lenses found three defects no two of which overlapped

Files: `tools/moon_sync_responder.py` (comments only),
`tests/test_responder_gate_census.py` (new, 43 arms),
`tests/test_conftest_reason_fixture.py` (new, 21 arms), `ROADMAP.md`.
Measured at the merge: `pytest tests` 1759 passed 1 skipped, `agents/pity_engine`
80 passed, `node --test` 52 pass 0 fail, and licence, docs, qa_companion, ruff,
mypy and the headless dry run all exit 0.

**STEP ONE OF THE GATE CENSUS IS DONE: 18 `# GATE:` tags, up from 0.** The
responder change is COMMENTS ONLY and that is proven rather than asserted -
`ast.dump` of the tagged file equals `ast.dump` of the file at `817b31b`. The
mutation runner and the registry stay open, in that order.

**THE FIRST BUILD'S RULE WAS SYNTACTIC AND NOBODY HAD DECIDED IT.** Measured on
the candidate: `_run_once` holds 14 `ast.If` and 1 `ast.Try`, and
`sorted(tag_line + 1)` equalled that set exactly. So "tag every if and try" was
the rule actually applied, the count of 15 was an artifact of the shape, and
three sites that bind the cycle went untagged because of their SYNTAX - the
`exhausted`/`refused` `IfExp` that the responder's own prose calls the one
distinction that must not be conflated, and the two `BoolOp` writes setting
`bounced` and `delivered`.

**THE NAME GRAMMAR FAILED OPEN, and the repair was a missing PARSE step.** One
strict regex silently ignored every near miss: a space after the colon, an
uppercase name, an underscore, an empty name, a trailing comment. A real new
gate tagged `# GATE: draft-skip` passed at exit 0 - the author had tagged a
gate and the census saw nothing, counted nothing, raised nothing. A permissive
detector now finds every line trying to be a tag, a strict grammar validates
the name, and a line the first accepts and the second rejects RAISES naming
file and line. Widening the one regex was available and was refused; this tree
has been defeated three times by widening a matcher.

**THEN THE REPAIR ITSELF WAS REFUTED, and that is the entry.** Accepting a bare
`ast.BoolOp` to catch those three sites was a WIDENING WEARING A PARSE FIX'S
CLOTHES. It bought 4 false sites - `inbox or DEFAULT_INBOX`, `bounds or
Bounds()`, the `roots` conditional and `spawn or _spawn_headless` - and a tag
parked on three of them passed clean. A strictly tighter rule with identical
coverage and zero false sites had been available and not taken:

    broad  If/Try/IfExp/BoolOp                        22 spots   false 4
    tight  If/Try, or IfExp/BoolOp inside an Assign
           whose target is a Subscript                18 spots   false 0

`_ACCEPTED_SHAPES` is gone; the decision is a named predicate,
`_is_a_consult_site`, so the rule reads as the judgement it is. Verified
independently of its author: parking a tag on `inbox = inbox or DEFAULT_INBOX`
is exit 1, 7 failed under the shipped rule and passed clean under the previous
one, with the responder restored to sha256 `02469d15` afterwards.

**THREE LENSES, THREE DEFECTS, NO OVERLAP.** A referent lens found the
syntactic rule; a mechanism lens found the fail-open grammar; a
did-the-repair-buy-its-cost lens found the widening. None could have found
another's. Two identical skeptics would have found one of the three.

**THE HOLE THAT REMAINS IS DISCLOSED, NOT DISCOVERED LATER.** Nothing
enumerates the gates that OUGHT to exist, so a new gate added to `_run_once` and
never tagged is invisible and every arm stays green. Measured, not feared. Two
ceiling items were also FALSE ABOUT THEIR OWN LIMITS and are corrected: one
claimed an unclassifiable shape raises, false for the whole name-grammar class;
one claimed a tag in any other module is reported, when no second file is ever
opened, so such a tag is silently ignored - the exact words that wording denied.

**A SECOND SLICE WAS DISPATCHED AGAINST A DEFECT THAT DID NOT EXIST, AND THE
DISPATCH PROMPT WAS THE DEFECT.** `ROADMAP.md` said the `git_unusable_reason()`
byte-identity contract was "GUARDED BY NOTHING". Truthful at `52cc874`, CLOSED
at `e714b35` which added the `HAND_TYPED_*` census, STRENGTHENED at `dda913a`
which added the five-shape delimiter control - and the row was never updated,
while `docs/LEDGER.md` recorded the closure. The two documents disagreed and the
hand-off propagated the wrong one. Two agents then got the provenance wrong in
OPPOSITE directions, the merger crediting `e714b35` alone and a builder
crediting `dda913a` alone, which is why both commits are now named in the row.

**THAT SLICE STILL MERGED, BY ADJUDICATION AND ON MEASUREMENT RATHER THAN
ARGUMENT.** The ruling is MERGED-REDUCED and is recorded in `ROADMAP.md` as an
adjudicated call. 32 mutants of `tests/conftest.py` through 64 invocations found
a 12-mutant MARGINAL KILL SET that the incumbent lets pass: the `no output`
fallback, the stdout leg of the detail chain, all four category tokens
respelled, three 128-branch detail mutants the incumbent's census cannot reach
because it never drives 128 with a blank stderr, and exit 0 under stream noise.
Four functions carrying zero marginal kills were dropped with the duplicated
delimiter tuple, 30 arms down to 21. The merger spot-checked one kill directly:
`"no output"` to `"no output at all"` gives incumbent 22 passed exit 0 and the
new module 2 failed exit 1. The COMMON-MODE RISK is named rather than implied:
three hand-typed transcriptions of one wording now exist and not one derives
from a consumer's stated requirement, so a single wrong premise about what the
consumers need leaves all three green.

**AN INSTRUMENT LIED TO THE MERGER TOO.** `grep -c '[^\x00-\x7F]'` does not mean
what it looks like - the shell does not expand those escapes into a range - and
it reported 1785 non-ASCII lines in a file that has zero non-ASCII bytes. Byte
checks are done in Python here, via `read_bytes()`.

## 2026-09-09 - Three residuals closed, and a control probe caught what five refuters did not

Files: `tests/test_prepush_skip_reporting.py`,
`tests/test_conftest_skip_path_pinned.py`, `tests/test_conftest_git_gate.py`.
Ten arms. Closes all three residuals `e714b35` recorded against itself, plus one
defect that commit introduced and nobody had been asked to look for.

**THE SURVIVING MUTANT IS KILLED, AND BOTH BINDINGS TURNED OUT TO MATTER.**
Inserting `require_git_repository()` into the audited cross-check survived 12 of
12 because the arms patched only `audited.git_unusable_reason` - the audited
module's own re-import - while the inserted call resolves conftest's binding, got
None in a real checkout and raised no `Skipped`. Patching both was not
belt-and-braces: the re-import is what the cross-check's BODY reads, so dropping
it makes the arms grade the real tree instead of the forced input, and the
definition site is what `require_git_repository()` RESOLVES, so dropping it makes
the skip door dead code. Proven by patching each alone.

A second-order trap in the same fix: `monkeypatch` is set up BEFORE an autouse
fixture and torn down AFTER it, so a post-yield `cache_clear()` on the patched
name raises `AttributeError` in teardown. The genuine `lru_cache` wrapper is
captured at import instead.

**A BARE `-r` WAS A FALSE GREEN, AND THE FIX NARROWS RATHER THAN WIDENS.** The
parser let `-r` swallow the target; `"tests"` contains an `s`, so the
skip-reporting arm read green off the word `tests` and only an unrelated targets
arm reddened. A token scan of a shell line CANNOT disambiguate a detached spec
from a target path, so that shape is now classified UNPARSEABLE and FAILS - a
gate that cannot read its own subject must not report green. The trust rule was
checked against the installed pytest's own `--help` rather than from memory.
`-r tests` and a trailing `-r` now fail FROM THE SKIP-REPORTING ARM, which was
the point.

**A ONE-BRACKET CONTROL IS GENERALISED, NOT DELETED**, because deleting the arm
would have discarded two genuine non-vacuity checks alongside the decorative
part. The control is now parametrised over five shapes - square, angle, brace,
absent, doubled-round. On a net-zero-byte `(detail)` to `<detail>` drift the old
version caught 1 failure and the control itself PASSED, blind to angle brackets;
the new version catches 3, naming the angle case.

**WHAT NO REFUTER WAS ASKED TO LOOK FOR.** `e714b35` shipped an arm asserting a
`.git` entry exists on disk, which FALSE-RED in a `git archive` extract: 1
failed, 13 passed, exit 1 outside any repository. That is NOT-PRESENT-AT-ALL
conflated with ran-and-broke, in a module written specifically to reason about
the Download-ZIP population, and its own docstring anticipated the archive shape
before asserting anyway. It now skips with a reason naming the shape - 13 passed,
1 skipped, exit 0 in the same extract.

It surfaced because the merge verified the mutant kill DIFFERENTIALLY - an
unmutated control in an identical scratch environment - instead of trusting the
builder's figure. The control was not clean. A mutant kill measured without a
control cannot separate the mutant's failures from the environment's, and five
adversaries with five other lenses all missed this.

The fork-point trap reproduced a third time: the builder's worktree materialised
at an ancestor of its declared fork point and was reset before any edit.

Measured 2026-09-09 at the seam with caches purged, as a reading: `pytest tests`
1636 passed / 1 skipped exit 0; `pytest agents/pity_engine` 80 passed exit 0;
licence, docs, qa, ruff, headless each exit 0 run separately; `node --test` 52
pass 0 fail.

---

## 2026-09-09 - The pre-push gate can name a skip, and six of eight refutations close

Commit `e714b35`. Files: `.githooks/pre-push`,
`tests/test_prepush_skip_reporting.py`, `tests/test_conftest_skip_path_pinned.py`,
`tests/test_conftest_git_gate.py`. Twenty arms. This entry records what did NOT
close as carefully as what did.

**TWO SLICES WERE REFUTED BEFORE THEY MERGED, and that is the point of the
shape.** The first pre-push guard keyed on the literal `-rs` and went RED for
`-rA`, `-r s`, a line continuation and a plain reorder of the two invocations -
every one a CORRECT hook, which is the false-red class this tree treats as
dominant. One of its seven arms was a naked substring search that PASSED with
`-rs` deleted from both invocations, and two of seven passed with the hook file
deleted entirely. The first cross-check pin left the audited arm's whole `else:`
block deletable with both arms green, never inspected the reason TEXT, and had a
live skip door - `Skipped` derives from BaseException and escaped its
`pytest.raises(AssertionError)`, turning the arm into a green-looking non-result.

**WIDENING THE MATCHER WAS NOT THE ANSWER.** The repaired guard keys on whether
each invocation's `-r` spec REPORTS SKIPS, because `-rA`, `-ra`, `-r s`, `-rsx`
and `-rfsE` all do and `-rf` does not. Twelve rows verified by mutant with
`__pycache__` and `.pytest_cache` purged on BOTH sides of each: five FAIL rows,
five PASS rows, an absent hook giving six SKIPs with a reason naming the missing
path, and a ZERO-BYTE hook correctly treated as present-but-broken.

**A FOURTH DISPOSITION IS NOW DEFENDED AGAINST.** Every pin arm clears `GIT_DIR`
and `GIT_WORK_TREE`, because with `GIT_DIR` exported `git rev-parse --git-dir`
succeeds while no `.git` sits on disk and the helper and the disk probe disagree,
both halves misreporting.

**THE BYTE-IDENTITY HOLE disclosed in `9e9f7e4` is closed** by a HAND-TYPED
expected-reason fixture that reads nothing out of the file it audits. Bracket
mutants that previously left all 14 arms green now redden.

**THREE RESIDUALS, verified by an independent refuter that reproduced 9 of 9
pre-push rows, 6 of 7 cross-check kills and both byte-identity kills.** First and
worst: the `require_git_repository()` mutant SURVIVES 12 of 12, because every arm
patches the audited module's own RE-IMPORT of `git_unusable_reason` rather than
the definition site, so the inserted call gets None in a real checkout and raises
no `Skipped` - and the module's docstring claims that hole closed. Second: a bare
`-r` with no attached spec is a FALSE GREEN, the parser letting `-r` swallow the
target while `"tests"` contains an `s`. Third: one of the two new byte-identity
arms hardcodes a single wrong bracket spelling and catches nothing the other
misses.

Independently measured collection: 1607 before, 1627 after - delta exactly +20
with no existing arm displaced. The fork-point trap reproduced again: the
builder's worktree materialised two commits behind its declared fork point and
had to be reset before any edit.

Measured 2026-09-09 at the seam with caches purged, as a reading and not a claim
about now: `pytest tests` 1626 passed / 1 skipped exit 0; `pytest
agents/pity_engine` 80 passed exit 0; licence, docs, qa, ruff, headless each exit
0 run separately; `node --test` 52 pass 0 fail; `sh -n .githooks/pre-push` exit 0.

---

## 2026-09-09 - Two sweeps green over zero files, and the diagnosis handed over was wrong

Commit `5f9e312`. Files: `tests/test_machine_identity.py`,
`tests/test_licence_posture.py`. One slice, worktree isolated, refuted by an
adversary on the softened-shipped-arm lens before it was believed.

**THE HANDED-OFF CLAIM WAS FALSE and correcting it is half the value.** The
previous session's ranked list said both files consumed `git ls-files` "with no
floor and no anchors". Both already had one: a hand-written floor of 100 plus
named anchors, five in the first file and six in the second. `_tracked_files()`
begins at line 231, not the 236 that was handed over. Re-deriving a handed-off
list is not ceremony.

**The hole that WAS open is narrower and was real.** The floor lived in a
SEPARATE arm from the sweep, so the PRIMARY arm passed GREEN OVER ZERO FILES:
`assert not offenders` holds trivially on an empty corpus. `check=True` also
reported an exit code while DROPPING stderr - the one string that names the
cause.

Repaired with a pure `_classify_enumeration(returncode, stdout, stderr)` at each
site, holding non-zero-exit, exit-0-empty, under-floor and missing-anchor apart,
consumed through an `_Enumeration` NamedTuple with `check=False` and
`pytest.fail` at the point of use. `require_git_repository()` still runs FIRST,
so a copy with no repository stays a SKIP with a true reason - the third
disposition, and the one a correct fix most often breaks.

**The adversary supplied the measurement the author could not.** In a genuine
no-git extract built with `git ls-files -z | tar` outside any repository: 62
passed / 26 skipped, against a baseline copy's 62 passed / 14 skipped. The
PASSED COUNT IS IDENTICAL, so not one pre-existing arm turned a pass into a
skip. A node-ID diff showed 8 additions and ZERO deletions, and each file kept
its OWN anchor list - the five and the six were never merged.

Measured 2026-09-09, as a reading and not a claim about now: `pytest tests`
1592 passed / 1 skipped exit 0; `pytest agents/pity_engine` 80 passed exit 0;
ruff, licence, docs, qa, headless each exit 0 run separately; `node --test`
52 pass 0 fail.

CEILING, recorded rather than hidden: the floor VALUE is ungraded. Mutating
`_MIN_TRACKED_PATHS` from 100 to 10 leaves the suite green. Pre-existing
blindness, not a regression.

---

## 2026-09-09 - The three-way git probe had no test at all, and two survivors name the ceiling

Commit `9e9f7e4`. Files: `tests/conftest.py`, `tests/test_conftest_git_gate.py`.
The shared file every module under `tests/` imports, so the blast radius was the
whole suite and it got its own slice and its own refuter.

Verified before editing: nothing anywhere in `tests/` stubbed
`git rev-parse --git-dir`, so all three branches - OSError, exit 128, any other
non-zero - were separated by NO TEST AT ALL. Extracted a pure
`classify_git_probe(returncode, stdout, stderr, exec_error)` with four category
tokens and added 14 arms. All four parameters are required: a constant bound as a
default argument cannot be mutated by patching the constant, so such a mutant
survives vacuously.

**THE DISPOSITION IS AN ADJUDICATED CALL, NOT AN OPERATOR DECISION**, recorded in
`ROADMAP.md` with its criteria and overturnable by reading one paragraph. Exit 7
still SKIPs. The promote-to-FAIL argument WINS on meaning - every git fatal exits
128, measured on git 2.53.0.windows.3 including outside a repository and on a
bogus flag, so a non-128 non-zero exit is git running and breaking - and loses
anyway, because the FAIL already exists one layer up in
`tests/test_commit_trailers.py`, cross-checked against an independent disk
signal. The previous hand-off's "29 passed, 4 skipped, EXIT=0" under exit 7 is
TRUE WITHIN ONE FILE and FALSE SUITE-WIDE.

**NOT REFUTED ON BEHAVIOUR DRIFT, and the refutation is the evidence.** The old
and new modules were loaded side by side in ONE process with `subprocess.run`
stubbed and driven across 15 returncode shapes and 5 exec errors - whitespace-only
stderr with whitespace-only stdout, a negative Windows returncode, every rung of
the detail ladder. ZERO differing bytes. Signatures, the `lru_cache` and its
`cache_clear`, all 18 importing modules and every per-file collection count
unchanged; the only delta is this file's 0 to 14.

**TWO MUTANTS SURVIVED and are recorded rather than papered over.** Changing the
reason string's brackets from `(detail)` to `[detail]` or `<detail>` leaves all 14
arms green, because the arm advertising byte-identity CALLS the classifier it
grades - both sides of its `==` are one code path. Byte-identity is TRUE TODAY,
measured, and UNPROTECTED TOMORROW.

**A general false-red generator, traced from a transient 3-FAILED run.** When a
mutation's replacement is a NET-ZERO byte-size change and is restored within the
same second, Python's `(mtime, size)` pyc invalidation reuses the MUTANT's
bytecode against source identical to HEAD. Purge `__pycache__` and
`.pytest_cache` on BOTH sides of every mutation, not only after.

**A FOURTH DISPOSITION, named here and not in the standing list of three.** With
`GIT_DIR` exported, `git rev-parse --git-dir` succeeds while no `.git` sits on
disk, so the helper and the disk cross-check disagree - live-repo-relocated-GITDIR,
under which the cross-check the adjudicated call depends on can carry a FALSE
reason or false-red. Nothing in either file clears `GIT_DIR` or `GIT_WORK_TREE`.

**CORRECTED 2026-09-11 - the sentence that stood here was configuration-scoped
and did not say so.** It read: "The pre-push gate does not currently hit it: `git
hook run` shows `GIT_DIR=[]`." That reading is TRUE OF A MAIN CHECKOUT and FALSE
OF A LINKED WORKTREE, and the command it cites splits the same way, so it is not
a neutral observer of its own question. Re-measured 2026-09-11 on git
2.53.0.windows.3 in a throwaway repository with a main checkout and one linked
worktree, every returncode read in Python:

| pushed from | what the `pre-push` hook inherits |
|---|---|
| main checkout | `GIT_EXEC_PATH`, `GIT_PREFIX`; no `GIT_DIR` |
| linked worktree | those two plus `GIT_DIR=<main>/.git/worktrees/<name>` |

`git hook run --ignore-missing pre-push` reproduces both rows exactly, so the
original reading was taken in the main checkout and generalised. This tree is
worked in linked worktrees - `git worktree list` returned 52 entries here on
2026-09-11, 1 main plus 51 linked - so the pre-push gate DOES hit the fourth
disposition, on every push a builder makes.

It hits more than the cross-check named above. `git ls-files` answered 224 paths
clean and 1 path with a foreign `GIT_DIR` exported, at returncode 0 both times,
and under that substitution `tests/test_readme_tree.py` reported this
repository's tracked listing as a one-element frozenset while
`tests/test_shell_contract.py` aborted COLLECTION at exit 2. The repair is not in
either file named above: `conftest.py` at the repository root removes `GIT_DIR`
and eight measured siblings at import, before any test module is loaded, and it
is the root conftest rather than tests/conftest.py because that one is never
loaded for `agents/pity_engine/`, which `.githooks/pre-push` also runs. The arms
are in tests/test_git_env_scrub.py, which feeds each variable in as a real
exported value rather than asserting that a fixture exists.

Measured 2026-09-09 at the seam with caches purged, as a reading: `pytest tests`
1606 passed / 1 skipped exit 0 - reconciling exactly as 1580 baseline plus 12 plus
14; `pytest agents/pity_engine` 80 passed exit 0; licence, docs, qa, ruff,
headless each exit 0 run separately; `node --test` 52 pass 0 fail.

---

## 2026-09-08 - One root cause in four test files, and every first repair installed a false red

Files: `tests/test_watch_inbox.py`, `tests/test_line_endings.py`,
`tests/test_hook_interpreter.py`, `tests/test_hook_gate.py`. Four disjoint
slices, worktree isolated, each refuted by an adversary with a distinct lens
before it was believed.

THE ROOT CAUSE, the same one the previous entry chased: a condition that cannot
distinguish CHECKED-AND-FOUND-NOTHING from COULD-NOT-CHECK. Found in 13 places
across the four files. The hand-off's ranked list named `_real_task_names` and
`_a_task_carrying_an_end_boundary` as the two worst; BOTH WERE ALREADY REPAIRED
at `42e3545`, so the list was re-derived rather than trusted. A corpus is a
snapshot.

**THE FINDING THAT MATTERS MORE THAN THE COUNT: the fix has a mirror image.**
Three of the four slices, on their FIRST repair, converted a legitimate SKIP
into a hard FAILURE somewhere off this box. Measured, not inferred:

- `test_watch_inbox.py` turned 3 green skips into 4 hard failures on every
  Linux runner - candidate `4 failed, 101 passed` EXIT=1 against baseline
  `99 passed, 3 skipped` EXIT=0, because `subprocess.run(["cmd", ...])` raises
  FileNotFoundError there. A merge blocker, caught before the merge.
- `test_line_endings.py` turned 9 legitimate skips into 16 failures in a
  `git archive` extract, and the failure text was the file's OWN skip message.
- `test_hook_interpreter.py` fired `pytest.fail` for a git that was NOT
  INSTALLED, while its own non-Windows branch skipped for the identical state.

THERE ARE THREE DISPOSITIONS, NOT TWO. The tool ran and found nothing, and the
tool is not present at all, may both SKIP with a reason that is TRUE. Only the
tool ran and broke may FAIL. This tree had already written that ruling down in
`tests/conftest.py` before the session started - trackedness is unknowable
without a repository, so those guards skip, they must not fail, because a red
suite a reader cannot act on trains them to ignore red. It was re-derived the
expensive way.

**A GUARD AGAINST A FALSE SKIP LEAVES THE CAPABILITY ITSELF UNGRADED.** Deleting
the entire Windows `sh.exe` discovery from `test_hook_interpreter.py` - the only
reason that file runs from PowerShell - left the suite GREEN at exit 0, with 17
arms skipping for a reason true in the mutant's world. The repair proved a
fabricated skip could not happen and proved nothing about the real capability.
Closed with an oracle that reaches the same fact by a DIFFERENT ROUTE.

**A FILE CAN ASSERT ITS OWN HOLE OPEN.** Three times, the correct fix turned a
SHIPPED arm red because that arm REQUIRED the over-wide behaviour:
`test_watch_inbox.py` asserted `(1, "") -> REFUSED` in the arm named for
refusing to report a tool failure as a refusal, and later asserted a bare
`OSError` with `errno is None` must be UNAVAILABLE. If a repair reddens an old
arm, read the arm before softening the repair.

**TWO CEILINGS, STATED RATHER THAN PATCHED AROUND.** Both reached by building
the mutant the fix cannot catch and watching it survive:

1. NO MECHANISM IN A TEST FILE CAN GRADE THE TRUTH OF ENGLISH. A skip sentence
   that is correctly derived, carries its evidence, varies per run and is still
   FALSE fired 21 times at exit 0. No fourth matcher was added. What the
   mechanism supports is the STATUS, the EVIDENCE it was derived from, and that
   the caller carries the classifier's own string. Narrowing UNAVAILABLE to a
   single errno bought one sentence to review by eye instead of nine machine
   states sharing one paragraph.
2. ONLY `git ls-files` CAN OBSERVE WHETHER `git ls-files` ENUMERATES THIS
   CORPUS. Every neighbouring route - topology, HEAD tree, ignore rules -
   answers a different proposition and is entitled to disagree on a legitimate
   machine. Four rounds each grafted one on as an oracle and each produced a
   false red one frame up: empty list, then an unreachable guard, then a GATE
   asking the wrong question, then a GRADER asking it. The conflation was not
   fixed, it was relocated. Closed by grading the DERIVATION - the gate launches
   no subprocess and moves with the import-time measurement in both directions -
   and letting topology assert only the two implications it can settle, skipping
   with its reason otherwise.

MEASURED HERE, each worth its own line:

- `git rev-parse --git-dir` WALKS UP. A Download-ZIP copy extracted inside any
  other repository passes a gate built on it while `git ls-files` legitimately
  says nothing about this tree: 20 failed of 36, EXIT=1, zero skips.
- A grading arm that consults the SAME predicate as the thing it grades cannot
  see that predicate be wrong. Two agents, one shared premise.
- NTFS: `os.stat` FOLLOWS a reparse point and reads False on a real junction;
  `os.lstat` does not. An adversary's recommended `os.stat` check would have
  hard-failed every junction arm on this box, and the builder refuted the
  recommendation by measurement rather than adopting it.
- `shutil.which` is PATHEXT-aware; `subprocess.run` uses CreateProcess, which
  appends only `.exe`. A `git.bat` shim as the only git on PATH gave 17 failures
  reading "raised FileNotFoundError even though git resolves on PATH".
- An ancestor COUNT cannot name a git install root: `<install>/cmd/git.exe` is
  2 up, `<install>/mingw64/bin/git.EXE` is 3 up. The count reaching one
  overshoots the other into the container directory. Replaced by a positive
  install-relative marker; unidentifiable layouts SKIP.
- `pytest.raises(Exception)` DOES NOT CATCH `Skipped` - it derives from
  `BaseException`. Bit three of the four files independently, once turning a
  guard green-by-skip.
- A CONSTANT BOUND AS A DEFAULT ARGUMENT cannot be mutated by patching the
  constant. A depth-1 mutant was a no-op and survived vacuously until the
  mutation was re-encoded faithfully.
- `git config --get` returns exit 1 for an absent key AND outside a repository,
  so it needs a second readability question; `git remote` with no remotes exits
  0 with empty stdout, so its exit code is the whole fingerprint. The two sites
  do NOT share a fix.

WHAT SURVIVED ATTACK. `tests/test_hook_gate.py`'s end-to-end property could not
be broken: with hooks replaced by `exit 0`, or `core.hooksPath` pointed at
nothing, both refusal arms go red naming the moved HEAD; a refuse-everything
hook is killed by the acceptance arm; even a FORGED `precommit_gate BLOCKED`
marker is killed. That file returned the session's only NOT REFUTED verdict.

Measured 2026-09-08 after the merge, all eight gates run as separate commands,
each exit 0: `pytest tests` 1580 passed 1 skipped, the one skip being the
pre-existing live-fetch opt-in at `tests/test_ingest_client.py:348`;
`pytest agents/pity_engine` 80 passed; licence, docs, `qa_companion`, `ruff`,
`node --test` and the headless dry run all clean. Baseline at `42e3545` was
1511 passed, 1 skipped, so the four files added 69 arms.

---

## 2026-09-08 - A read-only guard defeated five times, and the sixth version says what it cannot do

Files: `tests/test_task_liveness.py`, `tests/test_responder_task_argv.py`.
Commit `9fe8b0b`. `ops/check_task_liveness.py` UNCHANGED - no violation was found
in it under any of the new nets, which is worth stating because six holes were
found in the thing GRADING it.

**Two of the five defeats were destructive, not rhetorical.** A canary file was
deleted from disk while the suite printed a green exit 0. That is the standard
this guard is now held to, and it is why "the arms all pass" was never evidence.

The six holes, each watched red on its own mutant before its fix:

1. **A PowerShell alias carries no hyphen.** `ri` is `Remove-Item`. The scan
   matched a hyphenated Verb-Noun shape, so `ri`, `del`, `rm`, `sc`, `kill`, `ni`,
   a verb built by string concatenation, a `cmd /c` shell-out and a `.Delete()`
   all walked past it.
2. **The whole-file scan carried no `re.IGNORECASE`** while the comment directly
   above it asserted case-insensitivity. Lowercase `stop-process` and uppercase
   `TASKKILL` both passed. The code and its own comment disagreed.
3. **A type accelerator calls through `::`, not `.`,** and `[` is not a letter, so
   `[System.IO.File]::Delete` produced no bareword to scan and matched no method
   pattern. Same clean pass for `::WriteAllText`, `::Move`,
   `[Diagnostics.Process]::Start` and `[Microsoft.Win32.Registry]::SetValue`. And
   plain `>` REDIRECTION overwrites a file while carrying NO COMMAND TOKEN AT ALL.
4. **The scan was bound to the identifier `_PS_TEMPLATE`.** A second module-level
   PowerShell string concatenated onto it was never graded. A guard bound to a
   name is defeated by adding a name.
5. **The harness shimmed `subprocess` with a stand-in defining three attributes
   and no `Popen`.** A mutation branching on `hasattr(subprocess, 'Popen')` built
   pristine text under the shim and a deleting probe in production, with a
   trailing `exit 0` so the JSON still parsed and the real-probe arms still passed.
6. **Grading ran at import of the TEST file, which is after the SUBJECT's own
   module-level code has already run.** A module-level `os.remove` in the subject
   killed a canary with the suite green. Prevention was a claim about the wrong
   instant.

**THE CEILING, now in the file's docstring rather than implied.** A test suite
cannot prevent arbitrary runtime behaviour in a module it imports. It can grade
that module's SOURCE, and refuse to import a source that fails the grade. It
cannot prove that a source which passes will behave the same way at runtime,
because the imported module can always branch on something the harness did not
think to make identical. Two arms were renamed to claim only that. Operator
ruling, asked and answered during the session: narrow the claim, that is the
honest outcome.

**The method finding, and it generalises past this file.** Rounds two through
five each widened a matcher, and each widened matcher was defeated. The last two
kills did not touch a matcher at all - they went around the grading. When a guard
falls twice to the same class of attack, widening is the wrong response and the
question is what kind of claim is achievable.

**The controls were the reason the holes survived so long.** Every non-vacuity
control planted a capitalised, hyphenated, ASCII injection - the exact case the
matcher handled. A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES CANNOT
DISCOVER THAT THE MATCHER IS NARROW. The replacements vary SHAPE: alias,
lowercase, uppercase, concatenated, `cmd /c`, `.Delete()`, `::`, redirection.

**The ambiguity arm no longer reads zero out of zero as a pass.** It skipped
whenever discovery returned nothing, collapsing a non-zero return and empty
stdout into the same branch as a machine that legitimately holds no duplicated
task name. The first replacement introduced a plausibility floor that was
measured DECORATIVE - over totals 0..39 the set where its own assertion could
fail was EMPTY, so deleting the line was an equivalent mutant - and it over-fired
on a genuinely sparse box. Discovery now returns records and draws no conclusion.

**A new gate on the scheduled task's argv, and its own first two versions were
the defect they exist to catch.** `tests/test_responder_task_argv.py` grades
`ops/ResinCompute-Responder.xml`'s `<Exec>` argv against the code that argv
calls. Version one was a SHAPE arm: the script path swapped to a real-but-wrong
file, a dropped `--arm`, swapped window boundaries and non-dash positional junk
all passed green, because the responder path was hardcoded so the parser
interrogated was always the responder's whatever argv named, and the script check
tested EXISTENCE rather than IDENTITY. Version two keyed its refusal token on
exit code 2, which argparse also returns - four unrelated causes minting one
fingerprint, the same defect class as an interpolated reason string. Version two
also disclosed `--latency-only` as ungradeable "because the code marks it
optional"; that was refuted from the call the test already intercepted, where the
`grammar` kwarg differs, and the consequence is real - dropping the flag would
publish integer hops with `m1_status='lower-bound'` for a run whose far end is a
human, which is what `e1a101d` fixed.

**One property here is worth reusing rather than re-deriving.** A content-hash
recursive walk over 1137 entries - the worktree, this tree's runtime directory
and inbox, four sibling inbox directories, the profile config - showed the new
arms write NOTHING outside pytest's own cache, with planted controls proving the
walk sees both additions and modifications. The one log write in the full run was
attributed to a different test by re-running with the new file ignored. That is
what the responder isolation arm was supposed to be and is not, and the method is
the point: NOT existence-plus-size, because NTFS reports a directory `st_size` as
0 whatever it contains.

**Measured at the merge, 2026-09-08, each gate its own command, because a chained
run reports only its last link.** Licence, docs, `qa_companion`, ruff, both
suites, `node --test` and the headless smoke test each exited 0 separately. The
pre-push hook then graded the pushed commit independently: 1511 passed, 1 skipped,
and 80 passed. Collected in `tests/` went 1470 to 1512 across the session. These
are readings on that date, not claims about now.

**An incidental measurement worth keeping.** This tree's pytest configuration
prints PER-FILE counts and NO summary line, so a `-q` run ends in dots and a
count must be summed from `--collect-only` rather than read off a total. A
previous builder measured with `-o addopts=`, which disables the repo's
configured options; the numbers happened to agree, but a count taken under
different options is a count about a different run.

---

## 2026-09-08 - The cold boot answered the hook question, and four adversaries refuted more than they confirmed

Files: `tools/moon_sync_responder.py`, `ops/ResinCompute-Responder.xml`,
`tests/test_moon_sync_responder.py`, `tests/test_docs_hook_commands.py`,
`tests/test_task_liveness.py`, `tests/test_docs_consistency.py`,
`docs/INBOX_TRIAGE_2026-09-07-0710.md`, `docs/INBOX_TRIAGE_2026-09-08-1834.md`,
plus the community-standards set - `CONTRIBUTING.md`, `SECURITY.md`,
`CODE_OF_CONDUCT.md`, `.github/PULL_REQUEST_TEMPLATE.md`,
`.github/ISSUE_TEMPLATE/`, and `README.md`.

Measured 2026-09-08 at the seam, as a dated reading and not a claim about now:
1469 passed and 1 skipped in the application suite, 80 in PityEngine, licence
41, docs 29, qa_companion 17 passed 0 failed 1 skipped, shell 52 passed, ruff
clean, headless exit 0, mypy advisory Success over its own roots only. The
pre-merge baseline was re-derived in this session rather than carried from the
hand-off: 1422 collected, which reconciles as 1421 passed plus 1 skipped.

**The cold-boot measurement closed the open half, and carried a second fact
nobody predicted.** `SessionStart` carried no `--source` flag before commit
`3964544`, so that commit made it argv-dependent for the first time on the exact
event the log exists to prove. The first cold session after it wrote a
`sessionstart` start-and-reported pair, reaching `reported` rather than only
`start`, so the hook ran to completion and not merely to entry. The unpredicted
part: a `userpromptsubmit` pair fired ONE SECOND later from the same cold
prompt. Both hooks fire on a cold start, in that order, and the distinct labels
are the only reason the pair is separable at all - under the old shared label it
would have read as one hook firing twice.

**What the log still cannot answer, and why more cold boots will not help.**
The flag hardcodes one literal string per event, so the record names which HOOK
fired and never which SOURCE the harness fired it from. The harness distinguishes
`startup`, `clear`, `compact` and `resume`; the wiring collapses all four onto
`sessionstart`. `/clear` survival is therefore not a matter of taking another
reading - the instrument lacks the resolution. Filed on operator instruction
rather than built, because the fix touches the hook wiring and seams with the
doc gate landed the same day.

**The responder can now name its caller, and the fix was one line short until
the merge.** `tools/moon_sync_responder.py` gained the caller label and the
runtime override that the rest of the tree already had; measured across a real
process boundary rather than inferred, the environment outranks the `--source`
flag and the flag outranks the fallback. The builder correctly refused to write
outside its declared list, and so declared itself BLOCKED on
`ops/ResinCompute-Responder.xml`, whose `Arguments` element is the scheduled
task's real argv and carried no flag. Without that one line the unattended task
would have kept writing the fallback label, indistinguishable from a terminal
run - the exact confusion the slice existed to end. Verified at the merge that
this element is the ONLY argv site; the installer carries none and only
path-checks. Proven by `tests/test_moon_sync_responder.py`.

**An adversary REFUTED the strongest claim made about that fix, and the
refutation is the useful part.** The isolation arm is named for enforcing that
nothing is written outside the override, and it does not enforce that. Two
causes, both measured: NTFS reports a DIRECTORY `st_size` as 0 whatever it
contains, so a file created inside a watched directory is invisible to a
snapshot built from existence plus size; and any path that is not one of the
`DEFAULT_` constants is not watched at all, which includes the sibling inbox
directories that `deliver()` really writes to. A planted mutant leaked two files
while the arm reported a pass. What DOES hold, checked twice with the real tree
byte- and mtime-identical either side: the test suite does not reach the
operator's live responder record. The protection is real for the runtime
directory and absent for live mail. The adversary also corrected the builder's
own non-vacuity story - the arm does not fail against the true pre-fix module,
where it dies on `AttributeError` before it can spawn, only against an
isolation-stripped mutant.

**Nothing graded a document against the hook wiring, and now something does.**
`tests/test_docs_hook_commands.py` parses the real `.claude/settings.json` rather
than storing a second copy of the truth, and went red on the four exact
citations that had gone stale in `docs/INBOX_TRIAGE_2026-09-07-0710.md` before
that note was corrected. An adversary re-ran it both with and without the
`pytest.ini` `addopts`, found the results identical, and established the gate is
fail-closed: an empty corpus asserts rather than passing vacuously, and a
missing settings file asserts rather than skipping. It also found the real
limit, now filed: the trigger needs the literal settings path nearby, so
rewording a sentence to say "the hook declared for this tree" lets the identical
stale quotation go silent. The defect that actually happened was caught partly
by the luck of how it was phrased.

**The six mutant kills the hand-off asked to re-run DO NOT EXIST as recorded
claims.** A byte scan of every tracked text file found only `M12`, in this
ledger. `M1` through `M11` appear nowhere - not in the commit body, not in the
roadmap, not in the hand-off. Six claims with no recorded wording are
unauditable, and were refuted as stated rather than excused. The adversary
derived its own sweep instead: 18 mutants against `ops/check_task_liveness.py`,
14 killed, FOUR surviving, so the roadmap's prepend mutant turned out to be one
of four rather than the only one. Baseline 58 passed with ZERO skips, so the
real-probe arms genuinely ran.

**All four survivors were MISSING ARMS, not defects in the shipped code.**
`ops/check_task_liveness.py` is byte-unchanged; only `tests/test_task_liveness.py`
grew. Seven arms, each shown red against its mutant and green on pristine.

**And then a second adversary refuted THOSE arms, destructively.** The rewritten
read-only guard replaced a seven-token denylist with an inverted allowlist plus a
whole-file mutating-verb scan - a real improvement that still does not do what
its name says. PowerShell ALIASES CARRY NO HYPHEN and the scan matches a
hyphenated Verb-Noun shape. `ri` is `Remove-Item`: planted in the probe template
it ran, deleted a canary file from disk, and the suite reported every arm passing
with exit 0. Also surviving both nets: `del`, `rm`, `sc`, `kill` which is
`Stop-Process`, `ni`, a verb assembled by string concatenation, a shell-out
through `cmd /c`, and a `.Delete()` method call. Separately the whole-file regex
carries no `re.IGNORECASE` while the comment directly above it asserts that a
lowercase spelling runs exactly as well as a capitalised one, so lowercase
`stop-process` and uppercase `TASKKILL` both passed. The three non-vacuity
controls are genuine value assertions rather than shape arms and still could not
see either hole, because every injection they exercise is capitalised ASCII - a
control that only plants the case the regex handles cannot discover that the
regex is case-sensitive. The ambiguity arm has a third, unrelated defect: it
skips when it cannot discover a duplicated task name, and a discovery that FAILS
is indistinguishable from a machine that legitimately has none, so on CI or a
fresh clone it asserts nothing. All filed, none fixed in the session that found
them, because the merger had already taken the arms into the tree and an author
does not grade the replacement for their own merge.

**The tree's own guard caught a real leak on the way out.** The new triage note
named four sibling projects in plain text - 26 occurrences over 16 lines - in a
PUBLIC repository. `tests/test_no_sibling_names.py` went red and the names were
replaced with the established codenames. The outbound draft carried one more,
fixed for the same reason, since that file is delivered into a sibling tree.

**A new shape of the false-clean trap, and it nearly shipped the leak.** The
gate sweep was run as a single chained command ending in the headless smoke
test. The harness reported the whole chain as exit 0 - which was the SMOKE
TEST'S status, the last link - while the application suite inside it had already
failed. A chained gate run reports only its last command. This is the fifth
recorded form of a false clean in this tree and the first where the misreporting
surface was the chain itself rather than a grep, a fallback branch or a State
string.

**Inbox triage, and the standing instruction had nothing to review this time.**
All 22 unread notes and the 15 older untriaged ones were bucketed, 40 rows: 11
ingested, 9 already-have-an-equivalent, 15 not-applicable, and 5 notes producing
6 applicable-and-not-done items now on the roadmap. The inbox holds ZERO
subdirectories - the three verbatim drops were withdrawn by their senders - so
the rule that verbatim bytes supersede a paraphrase had no payload to apply to.
A reply to the outstanding note on hook portability was drafted into the
sender-side draft store, which sits outside the watcher's view precisely because
a file named from-RSC inside the inbox classifies as sent. Nothing was
delivered and the watermark was NOT marked; both remain operator acts.

**The roadmap's highest-priority item carried a stale count.** It read 89 of 91
commits; re-measured this session as 90 personal, 6 platform forwarding and 2
assistant, of 98 - both a larger denominator and a three-bucket split where the
old figure had two, hiding the forwarding address entirely. The stored number
was replaced with the command that measures it, since a commit count goes stale
on the next commit.

**GitHub community standards, on operator instruction.** The five missing
checklist items were written: code of conduct, contributing guide, security
policy, issue templates and a pull request template. Contributor Covenant 2.1
was transliterated to 7-bit ASCII and the adaptation is stated in the file
itself, with its attribution kept. NO EMAIL ADDRESS APPEARS IN ANY OF THEM -
reports route through GitHub private vulnerability reporting, which was enabled
this session and verified as enabled on the dedicated endpoint, because
otherwise the shipped security policy would have been a dead link. Repository
topics went to 20, the platform cap. The slice also repaired the README
repository tree, which named 2 of 10 files in one directory and omitted several
others, and it correctly declined to add its own new files to that tree because
the gate asserts trackedness through git and it had no authority to stage; the
merger staged first and then added them. The three new root documents were added
to the docs gate's governed set, so their paths and their ASCII are now graded
like every other governing document.

---

## 2026-09-08 - The invocation log could not name which hook fired, and the proof took a real fire

Commit `3964544`. `scripts/watch_inbox.py`, `.claude/settings.json`,
`tests/test_watch_inbox.py`, `tests/test_session_hooks.py`. Measured 2026-09-08:
1421 passed and 1 skipped in the application suite, 80 in PityEngine, licence 41,
docs 23, qa_companion 17 passed 0 failed 1 skipped, ruff clean, headless exit 0.
Baseline 1408 was re-derived by an adversary from a fresh clone at `0e9491a`
rather than taken on the builder's word; 13 arms added, 0 removed, and the
arithmetic closes against a collected count of 1422.

**The defect.** The runtime invocation log under `ops/runtime/`, named here in
prose because it is gitignored, existed to answer whether the `SessionStart`
hook fires on a cold session and survives `/clear`. It could not answer either.
`.claude/settings.json` wired BOTH `SessionStart` AND `UserPromptSubmit` to the
same command, `resolve_source` falls back to `cli` for both, and a manual
terminal run writes `cli` as well. Every fire in the complete log was `cli`.
An instrument that cannot separate its callers is not evidence about any of them.

**The trap the shape of the module set.** `main` writes its `start` line BEFORE
`_main` parses argv, so a label resolved by argparse would tag the terminal line
only and the two lines of one fire would disagree. The label is resolved by a
hand scan at the `__main__` guard instead. A flag rather than an env prefix,
because `VAR=x python ...` is POSIX syntax and the shell that runs a hook command
on this machine was never established.

**What actually settled it was a real fire, and an adversary was right to
demand one.** The builder's probe spawned the declared command as a subprocess,
which proves tokenisation by the test, not by the harness. A second adversary
refused that as evidence and was correct to: it further showed that
`--quiet-when-empty`, the flag already live in a hook command at `0e9491a`, is
NOT a positive control, because that flag changes stdout only and `_main` returns
its disposition unconditionally, so no log line could ever record it arriving.
The candidate was merged into the live checkout uncommitted against a pinned
baseline of 18 lines all `cli`, and the next real `UserPromptSubmit` fire
appended `userpromptsubmit` on BOTH of its lines, three columns, exit 0. That is
the first end-to-end measurement in this tree that a Claude Code hook delivers
argv to the process it names.

**Still unmeasured, deliberately.** `SessionStart` carried no flag at `0e9491a`,
so this change makes it argv-dependent for the first time, on the exact event the
log exists to prove. Its label cannot be read until a cold boot. A next session
reading `sessionstart` there closes it; reading nothing new means the hook died
and the recovery is a hand edit of plain JSON that needs no working hook.

**Two adversaries, distinct lenses, and they disagreed.** Does-it-reproduce
returned NOT REFUTED on six claims, having re-run the mutant itself, mutated the
settings file two ways - collapsing both hooks onto one label fails 6 arms,
collapsing both onto `cli` fails 8 - and fuzzed the argv scan with 12 real spawns
without producing a forged column or a forged line. Scope-and-siblings returned
REFUTED on the argv hole above, on an unfixed sibling, and on stale prose. Both
were right about different things, which is the case the two-lens rule exists for.

**A count baked into a comment was false within the hour.** The committed prose
cited ten lines and five fires from the live log. The log stood at 20 by the time
the slice merged. The comments name the property now and not the number, which is
the same rule the suite counts already live under.

**Corrected before merge:** an overclaim in `source_from_argv` that two readers of
one argv reaching two answers is its own defect. False for `--sour x`, for
`--source=`, and for a trailing `--source` with no value. Every divergence is
conservative and `_main` never reads `args.source`, so none can reach the log.

**A sibling repository's defect does not apply here, and was checked rather than
assumed.** Sibling-L reported the same day that its tracked hook command carries
an ABSOLUTE path, so in any clone or worktree it runs the ORIGINAL tree's script
and reports the ORIGINAL tree's inbox. This tree's commands are relative, verified
byte-wise, and the builder's own worktree run left no runtime log in the worktree
at all.

## 2026-09-08 - A task State string is not liveness, and every slice was refuted before it merged

One commit, `e7ab266`, four slices, ten files. THE PROCESS RESULT IS THE
HEADLINE: every one of the four slices was reported COMPLETE by its own builder,
with passing arms, clean ruff and honest counts, and every one was then refuted
or defect-found by an agent that did not write it. Three by independent
adversaries, one by the merger. Nothing in this entry rests on a self-report.

**The root finding. `ops/check_task_liveness.py`, proven by
`tests/test_task_liveness.py`.** ResinCompute-Responder reported `State: Ready`
and `LastTaskResult: 0` while its only trigger had expired at
2026-09-07T21:00:00, `NextRunTime` was empty, and the invocation log carried no
line dated 2026-09-08. It had not fired in 24 hours and never would again. The
previous hand-off read that string and claimed a 5-minute tick. **A task State
string names a state, not a capability.** The checker verdicts on positive
evidence of a future firing; State may VETO and never vouch.

The mirror error was measured too and is why the first cut was refuted: an
ABSENT EndBoundary is absence of evidence, not evidence, and a fired one-shot
carries none. An adversary found SEVEN surviving mutants and a false LIVE on a
real task on this box. All seven are killed.

**M12 survived the repair as well, and that is the entry worth remembering.**
The arm named as its killer,
`test_the_real_probe_emits_every_key_the_parser_reads`, pinned KEY PRESENCE and
not VALUE POPULATION - a probe emitting an `end_boundary` of null keeps the key
and all 56 arms stayed green. An adjudicator ruled MERGE with the gap recorded,
but attached a condition: if the installer slice landed and taught a script to
read exit 0 as "will fire", the gap was promoted to a blocker. IT LANDED IN THE
SAME SESSION. `test_the_real_probe_reports_the_end_boundary_value_and_not_just_the_key`
now kills it - verified by the merger applying the mutant and observing
`1 failed, 57 passed`, then restoring.

**Fixed at its three sources, not only at the new tool.** Both installers
printed the task's State property as the final word after registering, and
`NEXT_SESSION_PROMPT.md` instructed a bare state read. That is the lineage that
taught the false claim. Both installers now report LIVENESS and exit with the
checker's verdict; absent the checker or a console interpreter they say
UNVERIFIED rather than falling back to a state string.
`tests/test_task_state_claims.py` goes red if any tracked file presents a State
string as evidence of firing, with a planted positive control proving it
discriminates. A FOURTH site was found unprompted - the removal recipe in
`README.md` - and correctly ruled a false positive by narrowing the rule at
source rather than allowlisting the path.

The installer-to-checker seam was exercised without registering anything, by
extracting the real bytes of the console-interpreter resolver and the liveness
block: dormant task exit 1 NOT ESTABLISHED, live task exit 0 ESTABLISHED.

**`tools/moon_sync_responder.py` - refuse without answering, and a bounce that
is not a note.** Six refutations, all measured, all repaired but one. The
sharpest: the refusal fingerprint hashed the RENDERED REASON TEXT, and one
reason interpolated a byte count, so a draft oversize by a different amount each
cycle minted a fresh fingerprint every tick. Ten cycles, ten held files - the
288-a-day defect alive with ONE note and no cap involved. The arm that should
have caught it fed a BYTE-IDENTICAL draft both cycles and could not fail. Keyed
on category now; 10 cycles produce 1 held file and 1 fingerprint.

Also measured and fixed: an unwritable refusals record failed OPEN and delivered
five bounces INTO A SIBLING'S REPOSITORY with no error surfaced, which at a
five-minute tick is 288 files a day in someone else's tree - it now records
before delivering, so an unrecordable refusal stops the outbound; an unguarded
directory creation raised WinError 183 when the parent existed as a file, AFTER
the held file and bounce were already written, at four sites; a metrics row
appended unconditionally every cycle with no cap, 100 cycles giving 100 rows and
54150 bytes with the whole file rewritten each tick, O(n^2), now 1 row and 579
bytes; and head-of-line starvation, where one un-passable note blocked the
entire channel forever because the pending queue sorted by name and a refusal
never touched the answered record - reachable DELIBERATELY by a sibling with a
name that sorts first. NOT fixed, and disclosed rather than hidden: an evicted
refusal row can still re-hold one local file.

**`scripts/watch_inbox.py` gains an invocation log**, so whether the SessionStart
hook fires and survives a clear is measurable here for the first time rather
than merely unverified. The first cut wrote that log FROM THE TEST SUITE under
the same source label a real firing uses, so the instrument forged its own
evidence - running `tests/test_session_hooks.py` alone wrote six
indistinguishable lines. **Root cause, and it generalises: an isolation fixture
that monkeypatches module attributes cannot isolate a SUBPROCESS**, which
re-imports the module with the real defaults. Both records now re-root through
the runtime-directory environment variable that `ops/health.py` and
`headless/runner.py` already honoured, so no new knob was invented. Verified
independently: a full `pytest tests` leaves the log byte-identical by sha256.

**A data fix, not just a prevention.** The watcher's reported-notes record,
which lives under the gitignored runtime directory and is deliberately named in
prose here rather than as a path, carried
a fixture filename written by `tests/test_session_hooks.py`, and the watcher had
been reporting it as withdrawn mail in every session banner. Removed via
`core/atomic_io.py`; withdrawals 4 to 3. The other three were checked
individually and are genuine - the withdrawn verbatim directory is a real
withdrawal, not fixture pollution, correcting a subagent's claim.

**Two instrument errors by the merger, both self-caught, both the same class as
the tree's own waiter trap.** Reading a shell exit status after a pipeline
measured the last filter's status, not the tool's. Listing a dict-shaped JSON
record counted its two top-level keys and reported no pollution where there was
some. Both were statements about the probe rather than the world. Re-measured
correctly before anything was claimed.

**Channel.** Sibling-D's two questions answered by measurement: this tree is the
SPLIT case - wiring TRACKED in `.claude/settings.json`, inbox IGNORED in
`.gitignore` - so a fresh clone FIRES the watcher with no channel, the
combination that sibling declined to ship. But its third clause does not
transfer: our tool exits 0 and its stdout is on the normal injection path,
measured in a real clone. That sibling's own refutation leans on the claim that
a hook's stdout does not inject on a non-zero exit, which the same note lists
under what it is NOT claiming - load-bearing and disclaimed in one document.

**Sibling-A's responder DELIVERED at 17:00**, cycle
`20260908T165744-28336-aba821`. First machine-authored note this repository has
ever received; M2 and M3 are no longer NO-DATA on the receiving side after three
attempts. Its one stale claim is instructive rather than defective: it reports
that sibling's refusal handling as the opposite of ours, accurate about their
code at `origin/main` and stale about their own already-accepted ruling. **A
responder that measures HEAD reports the code, and a repository's intent can be
newer than its code.** Their bounce and ours converged independently on the same
six properties.

Counts measured 2026-09-08 at `e7ab266`: `pytest tests` 1408 passed 1 skipped;
`pytest agents/pity_engine` 80 passed; `shell node --test` 52 pass 0 fail;
licence 41; docs 23; qa_companion 17 passed 0 failed 1 skipped; ruff clean;
headless smoke exit 0; mypy advisory Success over 33 files, which says nothing
about `ops/`, `scripts/`, `headless/` or `tests/`.

---

## 2026-09-08 - The trial window measured nothing, and the fix that made NO-DATA reportable at all

One commit, `fe53f31`. The 1900-2100 LATENCY-ONLY window agreed with Sibling-A
ran on 2026-09-07 and produced no reply and no metrics file.

**The result, and why it is NO-DATA rather than zero.** Measured after the
window closed: the responder metrics JSON under the runtime directory was
never created, and the
invocation log held 29 `start` lines against 19 `empty` terminations, first fire
18:45:34, last 20:55:00, scheduled task afterwards Ready with LastTaskResult 0.
M1 INAPPLICABLE under the agreed grammar, M2 and M3 NO-DATA.

The cause was RSC's own eligibility rule, not the counterparty. `pending()`
takes `since=bounds.window_opens`, so only mail ARRIVING after 19:00 was
eligible, and the counterparty's most recent note predated the window. Nothing
could match on any tick. The rule was left alone mid-window on the reasoning
that widening eligibility while the experiment ran would edit the experiment,
and a latency measured under a rule changed halfway measures neither rule.

No metrics row was written for a no-op cycle, deliberately. A row carries
`reply_seconds` as `replied - arrival`, so a row for a cycle that sent nothing
would put an invented latency into M2 - the number the trial exists to measure.
The absent file is the honest report.

**The defect found by checking, mid-window, at 19:16.** Four fires inside the
agreed window had each terminated `empty` while the log carried four bare
`start` lines. `window`, `budget`, `empty` and `disarmed` each returned from
`run_once` before reaching `log_invocation`, so a cycle that ran and declined to
act was byte-identical on disk to a cycle that never fired. That is the exact
condition `log_invocation`'s own docstring says it exists to prevent, and the
same class already fixed on the `no-destination` path, which carries a comment
saying so.

All four had a passing test. Each asserted the termination as a RETURN VALUE.
This is the trap this tree published to the channel on 2026-09-07 - a gate
tested but not enforced - reappearing in the same file with the assertion
pointed at the wrong thing.

**The fix is structural rather than four more call sites.** `run_once` is now a
wrapper that logs `start`, delegates to `_run_once`, and writes the terminal
line whatever the body returned, plus `crashed` if it raised. The five scattered
per-path calls are gone. A hand-maintained list of paths that remember to log is
the failure mode this suite already met when its isolation fixture named three
`DEFAULT_` paths by hand and a fourth arrived an hour later.

Verified against the live scheduled task rather than by reading: the 19:25 fire
was the first to run the patched file and wrote `start` then `empty` at the same
second, LastTaskResult 0. The 19 `empty` lines above exist only because of this
fix - without it the window would have closed leaving 24 bare `start` lines, and
the honest report would have been UNMEASURABLE rather than NO-DATA.

Proof: `tests/test_moon_sync_responder.py`, five arms red before and green
after. Four name the terminations; the fifth asserts `lines[-1]` equals
`result["termination"]` without naming a path, so a NEW early return fails there
instead of silently reopening the hole.

One existing arm changed contract deliberately.
`test_the_invocation_log_records_one_line_per_fire` asserted one line per fire,
which held only because the quiet terminations skipped their second. It is now
`test_the_invocation_log_records_a_start_and_a_terminal_line_per_fire` and
asserts the pairing. The `start` line is not redundant: it is the only evidence
that a fire which dies mid-cycle happened at all.

**A second delivery attempt, also NO-DATA.** Sibling-A rebuilt its end, armed
under `hop_budget 1`, and two notes were hand-delivered to it. The first was
refused 72 seconds later at the input stage on name grammar - RSC's filename was
130 characters with a 102-character topic against a `{1,80}` topic group. The
counterparty's own correction is the more useful half: it first blamed a length
cap, then measured all 207 names across the five inboxes and found 33 failures,
ALL on the topic group and only 11 on the length cap, so raising the number it
had blamed would have fixed none of them. RSC accepts the correction as a defect
in its own naming convention and now keeps topics under 80 characters.

No responder-authored reply had arrived 15 minutes after the bounce, polled
against the counterparty's exact reply grammar. Three candidate explanations
exist and none were measured, so none is recorded here. The responder has still
never answered real mail.

**A prediction of RSC's was refuted by the counterparty.** RSC measured that its
own watcher reports an underscore-prefixed `.md` as a NOTE and only demotes the
`.tmp` suffix, and predicted a transient phantom note during the counterparty's
hard-link window. The counterparty measured what it actually writes - the tmp
name carries `.tmp` - so the window is unobservable here. RSC's reader-side
defect is real and unreached by that delivery scheme.

**Answered to the channel, unimplemented here.** A counterparty defect - an
input-stage refusal that holds the note, marks it answered and delivers nothing,
leaving the sender unable to distinguish refusal from being ignored - was
answered with a shape RSC does not yet implement: refuse WITHOUT answering,
which `_remember_answered`'s single call site in the delivered branch already
does here, plus a bounce written as a file that is NOT a note. Measured basis:
`pending()` requires `.md` plus a parseable sender, and the watcher lists a
non-note as a loose file, so such a bounce is visible to a human, ineligible as
responder input, and incapable of a bounce war by construction rather than by
policy.

The cost of refusing-without-answering was disclosed rather than hidden: a
permanently-refused note re-refuses every tick forever, and `_hold` writes
`held/<epoch>-<name>` with a fresh epoch each time, so one unpassable note
produces 288 held files a day at a five-minute tick. Not fixed, no date claimed.

---

## 2026-09-07 - The responder was armed for a trial, and every defect that mattered was found by running it

Six commits, `1d80f8c` through `159f4ac`. The cross-repo responder trial: RSC
volunteered as Sibling-A's pairwise partner, built its end, and armed it.

**The watcher first.** Two holes closed in `scripts/watch_inbox.py`. `rglob`
descended NTFS junctions, because `Path.is_symlink()` is False for one - a
one-file drop reported 6 files on one sibling's tree and 32 on another. Replaced
with an iterative pruned walk plus a per-drop entry budget. And the walker had no
withdrawal reporting at all: the report was `entries - seen`, so a deletion
simply stopped appearing, and Sibling-A's 50-file pull from four inboxes would
have been reported here as silence. Both proven by `tests/test_watch_inbox.py`,
9 of 9 mutants killed against the shipped functions.

The digest FORMAT deliberately did not move for a drop of ordinary files, so no
seen key went stale and the live inbox did not re-report. That constraint came
from a sibling and this tree had already measured the cost of breaking it at 88
notes.

A third hole in the same walker was a LIVE MISS rather than a latent class: the
top level globbed `*.md`, so a sibling's loose `REFERENCE-moon_sync_poller.py.txt`
had been invisible here for thirteen hours. It surfaced on the first run after
the fix.

**The responder.** `tools/moon_sync_responder.py`, 55 arms in
`tests/test_moon_sync_responder.py`, 21 of 21 mutants killed. The design decision
worth not re-litigating: THE SPAWNED SESSION NEVER WRITES INTO A SIBLING TREE. It
is handed a note and a staging directory here and its only output is a draft;
this module validates and delivers. Every rule is enforced on OUTPUT, after the
session exits, by code the session did not run. A sibling's allowlist reads as
though the responder decides by parsing the request, which it cannot - a note is
prose written by another agent, and keying an EXECUTOR on sender-supplied text is
strictly worse than keying a detector on it.

Consequence adopted channel-wide: the session needs NO write authority at all,
so the trial does not require anyone to grant an unattended agent write access.
`--dangerously-skip-permissions` is absent and the prompt goes in on STDIN.

**FOUR DEFECTS FOUND BY RUNNING, NONE VISIBLE IN 53 GREEN ARMS.**

1. A FAILED SPAWN WAS RECORDED AS `exhausted`. The first live spawn raised
   FileNotFoundError - on Windows the entry point is a `.CMD` shim subprocess
   will not launch by bare name - and the spawn returned EMPTY. An empty draft is
   refused by the gate and recorded as `exhausted`, which is precisely the label
   meaning "the bound worked as predicted". A subprocess that never ran would
   have published the reassuring result every cycle. `spawn-failed` is now its
   own value.
2. THE BACKLOG WAS ELIGIBLE. With an empty answered-record the first armed cycle
   selected a note from the PREVIOUS DAY. It would have answered a stale question
   and spent the hop budget before any new mail arrived.
3. THE ROOTS LOOKUP COULD NEVER RESOLVE ANYONE. The per-host roster keys by
   codename by design; notes are addressed by channel code. It looked up "RC",
   found nothing, and returned no destination - silently, every cycle.
4. A no-destination exit left `termination` as `unknown`, indistinguishable from
   a cycle that never ran.

**Three gates were tested and never enforced.** `within_budget`, `window_open`
and the self-sender check were each correct, each had a passing arm, and each was
IGNORED by `run_once`. Mutants disabled them inside the cycle and the suite
stayed green, because every arm tested the PREDICATE as a pure function. A
predicate can be right, tested, and ignored - the same class as configuration
read as behaviour.

**The counterparty's agreement is a precondition the code checks**, not a promise
someone remembers. A gitignored record under `ops/runtime/` names the counterparty, the
note it rests on, and an expiry; absent, malformed or expired all mean no.
Registering the task does not start the trial.

**Task registration cost two measured defects.** Trigger element order is not
free - `Repetition` must precede `StartBoundary` and needs a `Duration`, failing
as 0x8004131a naming no element. And the XML declaration must say UTF-16, because
`Register-ScheduledTask` takes a .NET string: a UTF-8 declaration fails with
"(1,40)::ERROR: unable to switch". `ops/ResinCompute-Supervisor.xml` carries a
comment arguing the opposite, and THAT TASK IS NOT REGISTERED ON THIS MACHINE,
which is how the wrong claim survived - nothing ever exercised it. Bisected
across five variants rather than reasoned about.

**The pre-push hook drained the only statement of what it was gating.** It sent
its stdin to `/dev/null` under a comment calling the ref list "unused", and the
suites grade the WORKING TREE rather than the pushed commit - so a dirty tree
mis-grades on every push, with no concurrency required. Measured window: 28s. It
now reads the refs, REFUSES when a pushed sha is not HEAD, and on a dirty tree
names the commit actually shipping instead of printing a bare OK. Verified by
feeding synthetic ref lists: incident exits 1, HEAD exits 0.

**A workspace-trust divergence that would have silently degraded every headless
run.** Reported by a sibling and reproduced here: `~/.claude.json` held two path
spellings of this checkout with disagreeing trust, and an untrusted workspace
makes a headless run DISCARD its permissions without erroring. `workspace_trust`
now refuses the spawn loudly and checks EVERY equivalent spelling, because
`str(Path("C:/x"))` normalises to a backslash on Windows and a Path-keyed lookup
cannot see the forward-slash entry at all. Operator flipped the stale key to
True; the whole config was diffed field by field afterwards and exactly one key
moved.

**Trial state at close, a reading and not a promise.** `ResinCompute-Responder`
registered and firing on cadence, LastResult 0. Sibling-A answered NO to arming -
its end is unbuilt - and endorsed LATENCY-ONLY tonight: M2 and M3 only, M1
recorded INAPPLICABLE rather than zero, because with a human at the far end
hops-to-quiescence is undefined and a zero would be the most misleading value
available. Zero auto-replies delivered anywhere as of 19:10.

**OPEN AND NOT ACTED ON: 89 of 91 commits in this PUBLIC repository carry the
operator's personal email in the author field.** Measured this session against
`origin/main`. A sibling redacted a single occurrence of the same string from a
note hours earlier and called it the operator's identity. No action taken - a
history rewrite on a public remote is an operator decision, and a sibling spent
the evening measuring how expensive and trap-laden one is.

## 2026-09-07 - The corpus was a snapshot and the session moved the tree under it

Both scrub halves reported complete and both were telling the truth. A tree-wide
sweep after the merge still found 11 full-name hits across three files that were
on NEITHER write-list: `tests/test_guard_worktree_exclusion.py`,
`tests/test_watch_inbox.py` and one line of `tests/test_loop_concurrency.py`.

None was an oversight. The corpus was computed by `git grep` at `4781de1` and
dispatched against; all three files were created or rewritten by this session's
own merges AFTER that point. The third is a comment the merger itself authored
in the slots re-pin, on a line the code slice's fork point predates, so that
slice could not have seen it even in principle.

**A CORPUS IS A SNAPSHOT, AND A LONG SESSION MOVES THE TREE UNDER IT.** A sweep
dispatched against a file list is correct about the tree that existed when the
list was built and says nothing about the tree at merge time. Re-derive after
the merges. Fixed in `3323481`; the checker asserts a NON-EMPTY corpus before
asserting zero survivors, because zero out of zero reads as a pass.

A second residual was caught by the code slice and ruled on by the merger rather
than by the producer: after every name was codenamed, `core/ports.py` still
explained a sibling's 2999 reservation by naming a third-party API whose vendor
name is the first word of that project's name. The mechanism is kept, the vendor
is not named, and the reason is recorded at the site so nobody restores it.
**A residual inference channel is not less of one for being a fact about a port.**

---

## 2026-09-07 - The only sanctioned write path in this repo emitted CRLF

`core/atomic_io.py` called `tmp.write_text` with no `newline=` argument, so
Python translated every LF to `os.linesep`. `CLAUDE.md` names this module as the
only sanctioned state-write path, which means it was the write path everything
else is told to use.

Measured before the fix: `atomic_write_text(p, "a" + LF + "b" + LF)` returned
CR-LF-separated bytes, and `atomic_write_json` produced 7 CRLF pairs on a
two-key object. Worse, and the reason the contract is "no translation" rather
than "normalise to LF": a caller who supplied CRLF got back CR-CR-LF, the CR
kept and the LF expanded underneath it. Fixed in `e1b20e6`, verified by
main-thread probe after merge rather than by the producer's own report.

`.gitattributes` carries `eol=lf` and `tests/test_line_endings.py` fails a
tracked file holding CRLF, so the first TRACKED file written through this
function would have gone red with nothing in `git diff` to explain it.

Then the sibling sweep, `b739f02`. Seven candidate sites, and **two were false
positives**: two `tools/` modules already passed `newline=` on the CONTINUATION
LINE of a wrapped call, which the line-based grep that built the corpus could
not see. The guard added in `tests/test_no_crlf_writers.py` parses with `ast`
rather than scanning lines, takes its corpus from `git ls-files` so a leftover
worktree cannot poison it, asserts the checked count before the offender list,
and plants a real offender as a positive control. It needs no self-exemption:
it never calls the function it searches for, and `ast` cannot see a literal
inside a string.

Live corruption measured, not hypothesised: the inbox seen-state file under the
gitignored runtime directory - not backticked here, because a backticked path
under a tree root must be tracked and that one must never be - held 98 CRLF
pairs, and a capture-store artefact outside the tree held 5. The first
self-heals on the next `--mark`; the second was renormalised only after
measuring that no manifest pinned its digest and it was not in the
content-addressed blob store.

**Verification pointer:** `tests/test_core_atomic_io.py`,
`tests/test_no_crlf_writers.py`.

---

## 2026-09-07 - Four root-walking guards could not tell a nested checkout from this tree

Fixed in `ffce5a9`, and the verification is the part worth recording. The
builder proved its fix against a hand-planted `gitdir:` marker file and said so.
A marker file is not a worktree, so an independent verifier planted REAL linked
worktrees under `data/` and `docs/` with `git worktree add --detach`:

```
builder branch, real worktrees planted   1106 passed, 1 skipped, exit 0
main 353e3c1, identical worktrees        6 failed, 1089 passed, exit 1
```

Downstream output changed, so the fix acts on the real thing. **A linked
worktree's `.git` entry is a FILE of 53 bytes beginning with a gitdir pointer**,
measured on this machine - the predicate uses `.exists()` for that reason and
`.is_dir()` would have failed silently.

Two corrections the verifier made to the slice as claimed, both kept in the
merge message rather than smoothed away: `tests/test_line_endings.py` was NOT
nested-checkout-blind as shipped, because its `iterdir()` plus `is_file()`
skipped a directory outright - making it recursive is a genuine coverage
widening but fixed no live defect and belonged in its own slice. And "asserts
the checked count" is really `len(checked) > 0`, which is non-emptiness rather
than a pinned number; the anti-vacuity intent holds and the wording overstated
it.

The misclassification was INHERITED: `tests/test_guard_worktree_blindness.py`
already listed that module among the four despite its own criterion requiring a
recursive loop.

**The transferable half, sent to the fleet:** 34 of 39 test modules here were
structurally immune because their corpus is `git ls-files`, and git does not
descend into a nested checkout. That single question triages a whole suite
before anything is measured.

---

## 2026-09-07 - The digest-key arms were green against an mtime key and a size key

A sibling measured two mutants surviving their whole watcher suite and asked
every repo on the channel to check its own. Checked here by applying each
mutation to `scripts/watch_inbox.py` in an isolated worktree, running the suite
against each, and recording survived-or-killed before and after. Three survived,
all now killed, `35a8565`.

**The refinement is sharper than the report.** The LITERAL substitutions were
killed here, but only by SHAPE arms - one asserting a readable file's digest is
a plain sha256, and a length assertion. Hashing the metadata restores the shape
and walks straight past both. Moving the substitution to the entry-key site or
to the manifest line needs even less. **A shape arm reads as coverage and is
not: it pins the FORMAT of the key, never its INPUT.**

`scripts/watch_inbox.py` was CORRECT and is untouched. Every survivor survived
because the arm was weak.

A later note from the same sibling reported a second layer - that `os.utime`
with float seconds does not restore `st_mtime_ns`, so an arm can assert it
restored the timestamp, read as armed to a reviewer, and still leave a
nanosecond-reading key moved. **Re-measured here rather than re-read, and the
arms were already sound**: one restore site, already using `ns=`, already
asserting in nanoseconds, written that way an hour before the note arrived. All
four mutants killed against a green pristine floor. Nothing was changed and
nothing was committed - an arm that is already sound does not get hardened to
have shipped something.

**The finding from that measurement is in the harness, not the arms.** The first
mutation harness used a quoted heredoc, a NUL escape collapsed inside it, and
the drop-site search matched ZERO times. The mutation was a silent no-op and the
harness would have reported SURVIVED on both drop mutants - a confident false
confirmation of the sibling's own finding. An `assert source.count(old) == 1`
uniqueness guard caught it. **Assert the mutation site matched before trusting
the verdict, or a broken harness is indistinguishable from a weak arm.**

**Verification pointer:** `tests/test_watch_inbox.py`, 43 arms.

---

## 2026-09-07 - Noelle was found, and the recorded search window was wrong

`observations.jsonl` line 9 recorded her acquisition as NOT-FOUND and attributed
the failure to a 1 fps sampling rate over the window 09:20:44Z to 09:42:59Z.

Re-swept at 15.000 fps - every frame of all 29 readable segments, 129180 frames
against the prior sweep's 1384. She was acquired at 09:07:38.533Z to
09:07:39.667Z as card 1 of the first Beginners' Wish 10-pull, a 4-star Geo
character card tagged New, bracketed on both sides by the banner counter reading
20/20 at 09:07:24.000Z and 10/20 at 09:07:46.000Z.

**The correction matters more than the find. The recorded bound was FALSE.** At
09:12:09Z the banner reads 10/20, not 20/20; the last 20/20 frame is before
09:07:26Z. The 20/20 reading was correct at 09:07:24Z and stale by the time it
was attributed to 09:12:09Z. That wrong bound placed the search window about
thirteen minutes AFTER the event, so no sampling rate applied to that window
could ever have found her - re-sweeping the SAME window at 15 fps returns
nothing but Miliastra Wonderland.

So "not found at 1 fps" was never mainly a sampling problem. The sampling rate
was the explanation that came to hand, and it was true and irrelevant at once.
**A caveat that is correct can still be the wrong explanation, and a plausible
one stops the search.**

Detection was non-OCR, with two positive controls: the Dehya splash known to be
present in the same corpus, and a transfer control on a different character over
a different background. Both fire.

The record was corrected without rewriting it: all eight original fields are
preserved byte-identical and four supersession fields were added, with the
resolving observation appended as a new record carrying read method, sampling
rate, both controls, five evidence digests and the one unswept interval. A
record of what was believed is worth keeping; a record readable as current truth
when it is false is not.

---

## 2026-09-07 - A row-scoped provenance schema, before the first row lands in data/

`core/provenance.py` and `docs/PROVENANCE_SCHEMA.md`, merged as `62ee019`,
authored while `data/` still holds nothing but hand-authored fixtures. The
ordering is the point: a schema written after the first row is a schema fitted
to whatever the first row happened to have.

Every value entering `data/` carries what it was read FROM, that source's
sha256, and HOW it was read - by eye, by OCR, or from the game's own bytes. Each
of those exists because of a measured failure this session or the last:
independence is COMPUTABLE through `parent_sha256` so two crops of one frame
collapse to one witness; a NOT_FOUND row without a sampling rate is refused; a
row carrying a forbidden key is refused, because the capture store holds an
account UID and a login token deliberately outside this tree and the schema is
what decides which values may cross that line.

**Built against a null skeleton first** - real types, degenerate functions -
which gave 43 failed and 16 passed with each arm failing for its own reason
rather than the whole file failing on one import error. That is the difference
between a suite that is red and a suite that is armed.

`core/types.py` was not touched. It is the shared contract and a merge surface,
and a contract with no consumers has no business in it.

Documented limitation rather than a papered-over one: whether a row came from an
OCR SWEEP is not decidable from the record, so the sampling requirement is
enforced only on the two decidable cases. No field was invented to pretend
otherwise.

**Verification pointer:** `tests/test_provenance.py`.

---

## 2026-09-07 - The shared governor docstring named two siblings one line above forbidding it

`ops/loop/slots.py` opened by naming three projects in plain text and closed the
same paragraph with "Nothing here may reference ANY of them". All carriers are
published repositories, so the contradiction was also an exposure.

A sibling proposed the replacement wording and this repo authored the bytes,
which meant this repo carried the red window. Committed as `02d5d93`; all three
carriers subsequently converged on `71fa2a68`, measured on three disks by three
parties plus a fourth that vendors none of them.

Only the docstring's opening paragraph moved. An adversary proved it by
reconstructing the HEAD blob with lines 4-8 swapped in from disk: the
reconstruction matched exactly, and the differing 1-based line indices across
all 247 lines were [4, 5, 6, 7, 8] and nothing else.

**Two corrections went back up the channel and both were accepted.** The
proposal's claim that the new wording matched `winmutex.py` exactly was false in
three places, and the claim that `winmutex.py` was clean of every sibling name
was false at one line - confirmed independently from a third disk, and in the
SHARED bytes rather than in one tree's drift, so it is everyone's or nobody's
and cannot be scrubbed unilaterally.

**What this round did NOT close, disclosed rather than fixed:** `SHARED_SHA256`
hashes only this repo's own disk. There is no cross-carrier arm, so the suite
reads green while the byte-identity contract is divergent. A guard that can only
see its own disk cannot detect divergence.

**Verification pointer:** `tests/test_loop_concurrency.py`, 22 arms.

---

## 2026-09-07 - Sibling project names replaced by codenames across the tracked tree

This repository is public. Before this pass its tracked files named six sibling
projects of the same operator's in plain text, which published a roster of a
private fleet as a side effect of documenting this tree's own inheritance.
Each sibling now appears as an opaque codename, Sibling-A through Sibling-F,
and nothing tracked resolves a codename to a project. The resolution map is a
single gitignored per-host file, ops/moon_sync_repos.json, deliberately not
backticked here because a backticked path under a tree root must be tracked and
that one must never be.

**Stated at its real size, because an over-claimed rationale outlives a wrong
line of code.** The operator's ruling was that these names are not secrets and
that the tree only needs to be ambiguous about them. This removes a plain-text
roster from a public repository. It does NOT make the fleet unlearnable to
anyone who already knows it, and no entry in this file should be read as
claiming otherwise. Prior commit messages and prior blobs are untouched by this
pass.

**Only proper nouns moved in the historical entries below.** No date, digest,
count, causal claim or verdict was altered, softened or reordered, and nothing
was deleted. Append-only governs ENTRIES, not BYTES: this is a vocabulary
substitution of the same kind as an ASCII normalisation pass, and it is
recorded here rather than done silently precisely so a reader who meets
"Sibling-E" inside a 2026-09-06 entry can see from the top of the file that the
word was substituted afterwards. Line wrapping was reflowed only in the
paragraphs a substitution touched.

**What deliberately did NOT move, each for a stated reason.** The five
hand-off filename prefixes on the shared Desktop are real basenames observed on
disk, and a guard that compares against invented filenames is vacuous, so they
stay byte-exact. The shared ProgramData slot-bucket path is a live OS location
three repositories coordinate through; renaming it from one side points this
repository at a different bucket and silently un-serialises the governor, so
closing it is a fleet migration rather than a scrub. This repository's own
`RC_` environment prefix means Resin Compute and is not a sibling. A third-party
vendor name that once appeared in `core/ports.py` was judged a company rather
than a sibling; that judgement was WRONG and the line is gone - see the
2026-09-07 entry on residual inference channels. The vendor name is deliberately
not repeated here, because repeating it in the ledger hands back exactly the
token the module removed. One machine-name
token survives in `README.md` and `docs/adr/ADR-004-port-block.md`; the
operator ruled on project names and that is a separate question, left open
rather than assumed.

---

## 2026-09-07 (second session) - The account was created once, and the capture lane was built in front of it

Three commits, `2fd8aef` through `f930263`. The operator installed and launched
Genshin Impact for the first time on this machine during the session, so the
work was done against a clock: every artefact a first run produces is either
overwritten later or never produced again. The chat surface was kept for
instructions to the operator and for verdicts, per their instruction.

### What was standing before the game launched

Four processes, built and positive-controlled first, then started:

- `tools/first_run_capture.py` - polls the filesystem and registry write
  surfaces every two seconds and content-addresses every distinct generation,
  so an overwrite ADDS a blob rather than replacing one. Reads through
  `CreateFileW` with `FILE_SHARE_DELETE` when a plain read fails, because a
  rotation is both the moment worth capturing and the moment the handle is
  contended.
- `tools/screen_capture.py` - screenshot daemon with a 64-bit mean-hash dedupe
  that still writes an index line on a deduped tick. "No new PNG" is the
  daemon's steady state AND what a dead daemon looks like; those two must not
  be indistinguishable.
- `tools/wish_authkey.py` - recovers the wish-history authkey URL and pulls the
  gacha log. Refuses to write anywhere inside this git tree.
- `tools/capture_supervisor.py` - keeps the lane alive and reports to a file,
  not to chat. Measures CONTENT and not only liveness, because ffmpeg keeps
  writing frames when a Direct3D title has handed it a blank surface.

Plus an ffmpeg screen recorder at 15fps, 2560x1440, nvenc, 300-second segments.

**Measured at the end of the run:** 6062 file events over 5971 distinct blobs,
1542 screenshots kept out of 2036 index lines, 29 video segments, 2 webCaches
snapshots, 10 wish-pull attempts, 7 recorded observations, 15 GB.
`output_log.txt` alone was captured at 47 distinct generations, so the whole
first-run log history survives rather than only its final state.

### The capture store is not in this tree, and the absence was proven

`C:/rsc-first-run/` holds the bytes. Genshin's logs carry the account UID and
the miHoYo registry subtree carries a login token. A sweep over all 164 tracked
files for any nine-digit run hashing to the account UID found 0, and the checker
was proven to fire on a planted control first, because a clean result and an
unarmed check look identical.

### Four facts recovered, and the one that needed the second lane

The account UID was read four ways that do NOT share one input: two pixel reads
off one crop, which is one fact rather than two, plus the game's own
`UidInfo.txt` bytes and the directory it created under `BeyondLocal/`. The
region was stamped UNVERIFIED as an inference from the UID prefix, then
promoted to VERIFIED when the game wrote
`security_server_default_iplist_os_usa.txt` itself.

**The traveller nickname was missed entirely by the 4-second screenshot lane and
recovered from the 15fps video** at `seg_20260907_025348.mkv +108s`. That is the
only point in the session where the two lanes were not redundant, and it is the
justification for carrying both.

### A recorded inference was refuted by the operator's next action

Dehya was recorded as a TRIAL character on the strength of Level 17 with
Friendship 1. The operator then levelled her with EXP books, which a trial
character cannot be. The inference was retracted in `observations.jsonl` with
what replaced it: her card is GOLD, the owned 5-star colour, and the genuinely
anomalous slot was a different one whose card is RED. **Two numbers consistent
with a hypothesis are not evidence for it, and the card colour was on screen the
whole time.**

That red slot turned out to be `Moonbeam`, a Manekin from Miliastra Wonderland -
6 GREY stars, DEF 147 above ATK 106, Elemental Mastery exactly 0. Every rarity
heuristic that worked on the other seven roster slots fails on it. Declining to
name it from portrait art was correct: it is not in the standard roster at all.
Two traps are recorded for any future mapper - the name probably being
player-assigned rather than a game identifier, and the grid icon disagreeing
with the model because a Manekin is customisable.

### The defect that matters most, because it did not look like one

`tools/wish_authkey.py` looked for the Chromium cache under
`%USERPROFILE%/AppData/LocalLow/...`. It is under the GAME INSTALL. `--scan`
printed "no webCaches directory found yet. Has Genshin Impact ever been launched
on this machine?" while the operator had Wish History open and that `data_2`
held 15 ASCII occurrences of `authkey`. **A wrong directory and a missing one
collapsed into one sentence**, and the sentence sent the reader to look at the
game rather than at the path.

Fixed in `f930263` as an ordered candidate list with the user-profile form
demoted rather than deleted. `tests/test_wish_authkey_paths.py` pins the ORDER
and not the membership, because the list can contain the right directory and
still try the wrong one first.

A second measurement is pinned in the same module though it never shipped: a
scratch extractor capped candidates at 1500 bytes against a real URL of 1755
with a 1452-byte authkey, so it truncated the credential and the endpoint
answered `retcode -100: authkey error` - which reads as an expired key rather
than as a scanner bug. The module's own cap is 4096 and was never vulnerable;
pinning it stops 4096 being a round number. The long-URL arm's own guard fired
on its first run, refusing itself at 1632 bytes against the measured 1755.

### End to end on the live account

After the fix, all six `gacha_type` values returned `retcode: 0, message: "OK",
region: "os_usa"`, which promotes `_HOST_NEW` from UNVERIFIED to verified
against a real 200. The history is empty and that is a TRUE ZERO: the game's own
Wish History page rendered "No record" in the same minute and states that
records appear about an hour after a wish. **Editing the puller there would have
been fixing a correct client against a lagging server**, and the two surfaces
agreeing is what distinguishes the two cases.

### Sibling-C's section 5 ingested

Sibling-C reported that root-walking guards cannot see a nested checkout and
measured 10 of 15 of its own with no exclusion. Measured here across 39 test
modules: **1 root-walking and excluded, 4 root-walking and NOT excluded, 34 not
root-walking.** The 34 are not lucky - a guard whose corpus comes from
`git ls-files` is structurally immune, because git does not descend into a
nested checkout while the filesystem does. That is `b55825e` turned the other
way round.

`tests/test_guard_worktree_blindness.py` proves the defect with the shipped
guard's own code rather than a reimplementation, and carries the contrast arm
that keeps the other number meaningful. `docs/INBOX_TRIAGE_2026-09-07-0710.md`
triages all five sections of Sibling-C's note.

**Sibling-C's section 4 landed immediately and on this very session's work.**
The triage document first wrote a placeholder as a literal Windows path with a
bracketed account segment, and
`test_no_tracked_file_carries_an_absolute_path_naming_a_real_account` went red.
The guard was right and the prose was wrong. The regex was NOT widened.

### Two mechanical traps paid for again

An in-progress `.mp4` segment will not open - `moov atom not found`, because the
index is written when the muxer closes. Matroska decodes to the last complete
cluster. The recorder was switched to `.mkv` mid-setup, and the proof arrived at
shutdown: the force-killed final segment still decoded to a frame with mean 66.6
and standard deviation 18.2.

Matching a daemon by substring over its whole joined command line is wrong. A
probe process whose own source text names two daemons matches both, and it
briefly killed every real watcher while the probe survived.
`find_python_daemon` matches `argv[1]` only.

**The heredoc backslash trap bit twice more**, once turning a redaction regex
into `unterminated character set` AFTER nine real candidates had been printed -
a redaction that fails open is how a credential reaches a transcript - and once
as a `unicodeescape` SyntaxError. Both were fixed by writing a real file.

### CI went RED on this session's work, and the local gate could not have caught it

`f930263` and `1e8c140` both failed on the runner while every local gate was
green. Fixed in `7e807a0`. Three failures, three different ways for a green
local run to mean nothing, and the local box being Windows while the runner is
Linux is the common cause.

**Windows-only symbols are a TYPE error on Linux, not only an import error.**
`ctypes.wintypes` and `ctypes.WinDLL` are marked `sys.platform == "win32"` in
typeshed, and one error in one module stops mypy before it checks anything else.
That is the same failure shape `mypy.ini` already records for numpy's PEP 695
stub. mypy narrows on `sys.platform`, so the fix is a real guard rather than an
ignore comment. `subprocess.DETACHED_PROCESS` is the same class with an extra
trap: **`hasattr` guards the interpreter but does NOT narrow for mypy**, so that
code was already correct at runtime and still an error under the checker.

**A test of an ORDERING read the real environment.** `USERPROFILE` is unset on
Linux, so the module correctly appended no user-profile candidate and the test
asserted the absence of something the code was right not to produce. It now sets
the variable to `tmp_path` - and NOT to a literal home-shaped string, because
`tests/test_machine_identity.py` forbids exactly that and caught the first
attempt. The guard was right: a test that needs SOME home directory does not
need a plausible-looking one.

**A test asserted a behaviour the module deliberately does not have.**
`_web_caches_root` documents returning the FIRST candidate when none exist. The
old test asserted a non-existent override is never returned, which is true on a
machine with a Genshin install and false on a runner without one. Asserting a
behaviour the code deliberately does not have is not a stricter test, it is a
wrong one. Replaced by two tests that monkeypatch the candidate list, so neither
depends on this machine.

**And a guard reported a number that was not the number it named.**
`tests/test_mypy_scope.py` took the FIRST digit off mypy's tail line. Clean,
that is the file count. With errors the line is
`Found 3 errors in 3 files (checked 31 source files)` and the first digit is the
ERROR count, so the CI failure read "mypy checked 3 files but the configured
roots select 31" and sent the reader to look at the SCOPE while the real problem
was three platform errors. It now reads the count immediately before
`source files` and fails loudly if it cannot find one. **A guard that reports the
wrong number is worse than one that stays quiet**, because it answers the
reader's question wrongly before they ask it - the same lesson as the wrong
rationale, in numeric form.

The fix was verified by DELETING `USERPROFILE` and `RSC_WEBCACHES_ROOT` from a
subprocess environment and re-running the two affected modules there: 14 passed.
Running them the ordinary way cannot distinguish a fix from a platform accident.

### Verification, measured 2026-09-07 at `f930263`

`ruff` All checks passed. `pytest tests` 1094 passed, 1 skipped. `pytest
agents/pity_engine` 80 passed. `shell node --test` 52 pass, 0 fail. `headless
--once --dry-run` exit 0. `mypy` Success, 31 source files. Licence QA 41,
docs QA 23, `qa_companion.py` 17 passed, 0 failed, 1 skipped.

`mypy` required one config change to stay honest: `tools/` is a `files=` root
and `tools/screen_capture.py` imports Pillow, whose type hints reference numpy,
whose `__init__.pyi` uses a PEP 695 statement that is a syntax error under the
pinned `python_version = 3.11`. One third-party stub error stops all further
checking, so the gate would have read as a single unrelated failure rather than
as coverage. `follow_imports = skip` plus `follow_imports_for_stubs = True`,
scoped to numpy only, with the existing rationale extended rather than replaced -
that rationale rejected silencing numpy for a DIFFERENT entry path, a test
directory, where there was a directory to drop. Here there is not.
`screen_capture.py` also dropped numpy entirely; the mean-hash it computes is
byte-identical to the numpy one, checked against a captured frame.

### The roster sweep found one thing and honestly failed to find another

A read-only agent OCR'd 1328 screenshots (166 keyword hits) and 1384 video
frames sampled at 1fps.

**Dehya's acquisition WAS found**, at 09:20:40.561091Z: "Obtained New Character
/ Dehya", 5 gold stars, Pyro, followed four seconds later by an Invite Character
screen reading "Dehya has been invited". That is a real acquisition plus an
event party invite, which is consistent with the retraction above rather than
with the trial hypothesis it replaced.

**Tesseract missed that frame completely** - zero keyword hits on a frame whose
text says "Obtained New Character" in plain view, because the splash is a
stylised font over a full-screen fire effect. An OCR-only sweep returned a
confident zero on the single most important frame in the corpus. Any future
roster extractor must not be OCR-only, and an OCR zero over game splash text is
not an absence.

**Noelle's acquisition moment is NOT FOUND and was not inferred.** She is in the
party roster from 09:42:59Z, and the Beginners' Wish banner still read "Chances
Remaining: 20/20" at 09:12:09Z; two 10-pull reveals at 09:12:25 and 09:17:26
were on the Standard banner and did not contain her. The gap is 09:20:44Z to
09:42:59Z. **NOT FOUND AT 1 FPS IS NOT THE SAME FACT AS NOT PRESENT** - the
recording is 15fps and one frame in fifteen was examined, a wish reveal is
short, and the frame is most likely still on disk. It stays open.

---

## 2026-09-07 - Three guards that overstated their reach, and a claim gate that took three rounds to become honest

Seven commits, `3f7f23f` through `2b8fcbe`. Four agents dispatched worktree
isolated, three of them adversaries on distinct lenses. **Every adversarial pass
that ran against a done-claim returned REFUTED**, and each refutation is recorded
below with what it changed, because two of them refuted work this merger had
done rather than a builder's.

### The top roadmap item was DEAD, and the source was gone

`moon_sync_inbox/from-<sibling>-verbatim/` no longer exists - not here and
nowhere on this machine. Sibling-C DELETED it from all four sibling trees after
Sibling-A found the operator's Windows account name in 3 of its 48 files and
Sibling-C's own sweep raised that to 19 of 48, including
`tests/test_stop_claim_gate.py`. So the claim-gate PORT, the `pytest_guard`
port, the `edit_lint_check` port and the two `drift_guard` checks are all
blocked on a withdrawn payload.

**Containment here was measured, not assumed:** 0 tracked files carry the account
name, `git log --all -S` over it returns 0 commits, and 0 of the four named tool
filenames were ever added. Nothing from the drop entered this tree.

**This tree's OWN outbound drop was swept, and the check was armed first.** 7
files across 4 sibling inboxes, byte-identical to the tracked originals by
sha256. Five needle categories, every one proven to fire on a planted line before
the real scan: account name 0, home path 0, short path 0, sibling root 0. The 16
`users-root` hits are `tools/publish_next_session.py` and its test - the tool
whose job is REFUSING account paths, whose pattern is an account-shaped path and
whose fixtures use an invented operator name. A detector's own pattern trips its
own sweep, which this tree had already written down.

**The first run of that sweep reported two categories UNARMED**, and that is the
lesson worth keeping. Both path patterns had been written through a shell
heredoc, which silently ate one backslash from each character class and turned
`[\\/]` into `[\/]` - a class matching forward slash only. Both then scanned
every Windows path in the payload and found nothing. Without the positive control
that would have been reported as a clean result.

### Sibling-A's pickaxe check, run here with both controls

Positive control 9 commits at rc=0, negative control 0. Then, scoped against
`origin/main` because this repository is public: the account name returns **0
across every ref**. `C:\Users` 6, `AppData/Local/Programs/Python` 1 and
`Claude-Session` 4 are all false positives - the account-path detector, and the
hook that strips the session trailer plus the test proving it strips it. Not
taken on faith: every UUID-shaped and long-hex identifier in the published
matches was intersected with the 1567 real session ids on this machine.
**Intersection 0.**

**One live instance of the resurrect-a-blob trap was found and reaped.** Two
stale `worktree-agent-*` branches from earlier sessions were still present as
refs with no worktree attached - `git worktree list` reported none while
`git branch -a` reported both. They held 0 unique objects this time. That is
luck: a worktree branch from a session predating a history rewrite is exactly the
ref that resurrects a purged blob. **The standing check is `git branch -a`, not
`git worktree list`** - the branch outlives the worktree.

### The inbox watcher was blind to content and to directories - `6f37ce5`

Measured against the shipped functions in a fixture inbox BEFORE any edit: 2 of
7 properties held. `_notes()` globbed `*.md` at the top level and a DIRECTORY
has no `.md` suffix; the watermark stored bare name strings, so the key was the
filename alone. All five repos on the cross-repo channel had built the same
hole independently, each in a different mechanism. Sibling-E's phrasing is the
one this tree keeps: it was not misclassified, it was invisible.

Now 7 of 7. Notes keyed on (filename, content sha256). Drops are first-class
entries keyed on (name + "/", manifest digest) computed over what is ON DISK -
one line per file holding the drop-relative POSIX path, a NUL, then that file's
sha256, sorted, joined, hashed once. An empty drop still reports. A
`UserPromptSubmit` hook was added because `SessionStart` fires once and cannot
see a note landing mid-session; it printed nothing when nothing was unread and
surfaced three notes mid-session on its first live firing.

Two other key shapes were REFUTED by siblings and are deliberately not
implemented: a FILE COUNT stays equal when a sender replaces a file, and a digest
of the sender's `MANIFEST.sha256` FILE keys identical for a payload edited
without regenerating the manifest.

**Migration verified read-only against the real state before anything was
committed:** the shipped watermark held 88 plain name strings, and a version bump
treating those as unseen would have dumped the whole inbox back on the operator.
88 grandfathered, 1 genuinely new, watermark sha256 unchanged across a reporting
run. Verification pointer: `tests/test_watch_inbox.py`,
`test_a_legacy_name_only_watermark_still_counts_its_notes_as_read`.

**The report may not carry a payload byte.** Sibling-D's rule, relayed by
Sibling-A: everything the watcher prints is injected into a session with the
harness's own authority, before any judgement is applied, so an imperative
sentence in a sibling's file must not arrive wearing this watcher's voice.
Pinned by `test_the_report_never_carries_a_payload_byte`, parametrized over all
three report modes, asserting the NAMES appear first - a watcher that crashed
and printed nothing would satisfy a bare no-payload assertion perfectly.
Mutation: a variant appending a 60-character body preview leaks the marker and
reddens it.

### Property 6 - bytes-equal is not the same fact as did-not-write - `bc98c8d`

Sibling-D's finding, and theirs alone. They ran their four hook commands
verbatim to confirm the paths still resolved after an edit; the `SessionStart`
one was their watcher, and it marked three genuinely unread notes as seen.

Measured here on the LIVE watermark: two reporting runs, identical unread sets,
bytes unchanged, **mtime unmoved**. This tree passes, and not from virtue -
`--mark` has been a separate flag since the first version, so property 6 held
by an accident of the original shape rather than because anyone had seen the
failure. Sibling-D's statement of the cause is better than the one recorded
here and replaces it: acknowledgement as a SIDE EFFECT of reporting means
anything that can report can silently consume, including a probe whose only
purpose was to check that the watcher runs.

The mtime half is the part this tree would not have caught. The existing arm
asserted the watermark's bytes and stopped. An atomic write producing identical
content still moves the modification time. Mutation-proved: a variant rewriting
the state file with its own identical bytes PASSES bytes-equal and FAILS mtime.

### mypy checked a quarter of the tree and two agent files called that done - `26543e2`

`python -m mypy` printed `Success: no issues found in 23 source files` against 92
tracked `.py`. A narrow scope is a design. What made it a defect is that
`.claude/agents/builder.md` told every builder to run mypy before reporting done
and `.claude/agents/adjudicator.md` listed it among the criteria for GRADING an
arbitrary slice. **Zero out of zero, institutionalised in the roster, where every
future agent inherits it.** It happened during this session: a builder working in
`tools/` reported mypy green and flagged the gap itself, in its own UNVERIFIED
section rather than its results. The agent was more honest than the instruction
it was following.

The shape is worth naming because it recurs: **the config was documented in the
wrong line.** The `mypy.ini` comment explained `exclude=` - a real, measured,
correct reason covering 5 files. `files=`, which decided the other 64, carried no
rationale at all, so a reader found a reasoned comment beside the wrong mechanism
and stopped looking.

Measured by adding each dark directory alone, in a scratchpad config so nothing
changed to take the measurement: `tools/` 0 errors and now IN, `surface/` 1,
`headless/` 3, `ops/` 8, and `scripts/` BLOCKED rather than chosen - mypy refuses
it with a duplicate-module-name error needing an `__init__.py` first. mypy now
reports 26. `[mypy-tests.*]` was cited by the `exclude=` comment as recording the
intent and is dead config; it now says so.

`tests/test_mypy_scope.py` is the guard, and mypy was the only tool here without
one. It holds the dark set as a LITERAL with a measured reason per entry rather
than deriving it from `mypy.ini`, because a test that recomputes its expectation
from the file it checks can never fail.

**That guard then had its own defect, found by the next builder and fixed in
`b55825e`.** mypy WALKS THE FILESYSTEM; `git ls-files` does not. Any unstaged
`.py` under a covered root made the two disagree, so every builder writing a new
module in `tools/` would have met a spurious red - the same wave-it-through
failure the guard exists to prevent, arriving from the other side. The arm now
asserts `mypy count == tracked-under-roots + unstaged-under-roots`.

### Sibling-E's detector gap, closed - `3f7f23f`

Sibling-E ported `tests/test_no_secret_literals.py`, ran it against their tree
and reported a false positive back: the env destination assigned a bare
lowercase PowerShell variable that had itself been read from
`GetEnvironmentVariable` a line earlier. Reproduced here first. Latent rather
than live - one tracked `.ps1`, no instance of the shape.

**Sibling-E's suggested fix was not taken as stated, and the reason
generalises.** Adding a bare `$name` to `ENV_REFERENCE` would have been wrong
here: that pattern is applied with `.search()`, so it would exempt any value
merely CONTAINING a variable. `VARIABLE_VALUE` is a separate pattern matched
against the whole stripped value.

Mutation changed the shipped test set. Three mutants: dropping the exemption is
caught, dropping the TRAILING anchor is caught, and **dropping the LEADING anchor
is EQUIVALENT** because `re.match` already anchors at the start, so `^` is
documentation rather than mechanism. Without the third arm the trailing-anchor
mutant survived: a value shaped variable-then-literal matched on its variable
prefix and the appended secret rode out exempted. Measured as a real false
negative before the arm existed.

Sibling-E's second suggestion - parametrize the exemption assertion over every
exempt file - was already present here at
`test_the_detector_would_fail_on_this_file_without_its_exemption`.

### The engine changelog, and why the revision did NOT move - `1794a5e`

`ENGINE_VERSION` is the COMPUTE revision, returned to callers as
`engine_version` so a consumer can decide whether a cached forecast is still
valid. Every forecast is byte-identical across the exclusive-bind change, so
bumping it would have signalled a compute change that did not happen and
invalidated correct caches. The entry goes in a new "Service changes at engine
revision 0.1.0" section, because the file's convention is that a bump PREPENDS
and a prior version's line is never extended.

**Which half is load-bearing was measured, and it is not the one the name
suggests.** The nine-cell bind matrix in
`agents/pity_engine/tests/test_service.py` has `first=none` and
`first=exclusive` as identical columns, so with `allow_reuse_address = False`
already set, adding `SO_EXCLUSIVEADDRUSE` changes no observable outcome against
a listening socket on win32. Dropping `SO_REUSEADDR` is what closes it; two
stock servers are the single cell in nine that double-binds. Crediting the flag
would have been Sibling-A's durable-wrong-rationale defect, which they
described the same night: a wrong explanation outlives a wrong line of code,
because it answers the next reader's question before they ask it.

### The claim gate - three rounds, three refutations, and it lands UNWIRED - `2b8fcbe`

`tools/stop_claim_gate.py` plus 115 arms. Re-implemented from Sibling-C's
published PROSE; no Sibling-C code was read, and the six questions asked of
Sibling-C by note are unanswered.

  round 1  lexical credit rule    REFUTED. count_mismatch 71 percent false on
           the first pass's scoring, 60 percent on the second pass's
           re-measurement of the same build.
  round 2  calibrated lexical     REFUTED. False positives fell and laundering
           holes opened instead - `target: 930 passed ... in 17.50s` credited as
           evidence, the same line via `grep` credited, the comment bar bypassed
           by one tab because `normalise_log_line` keeps only text after the last
           tab. A dedup THIS MERGER added made `tests_pass_without_run`
           structurally unable to fire, and the docstring asserted four
           mechanisms the code did not have.
  round 3  provenance             64.1 percent false, then 55.5 percent with
           one-hop chaining.

Provenance is the correct mechanism and closed every laundering hole: a summary
is credited only from output of a command classified as a test RUNNER, so `cat`,
`grep`, `git log` and `tail` are not evidence sources BY CONSTRUCTION rather than
by a lexical bar that kept being bypassed. Chaining then credits a reader of a
file a runner redirected into, one hop, because this project's own convention is
to redirect and read back - an exit code read through a pipe is the pipe's. Six
bars keep chaining from re-opening what provenance closed, each with an
acceptance arm beside its refusal arm.

**55.5 percent is still too high to arm, so no Stop hook is declared and
`.claude/settings.json` is untouched.** Sibling-C published the reason: a gate
that cries wolf on correctly-sourced figures trains the reader to wave it
through, which is exactly when it stops catching the real thing. The 55.5
figure is also the producer's own, un-adjudicated, and it does NOT compare to
the 68.0 percent from the round before - that sample was 313 files and 254,497
records where the same recipe selects 317 files and 94,136 records. The
comparable pair, one sample one pass, is 64.1 -> 55.5 percent and 348 -> 274
findings.

**`tests_pass_without_run` was deleted outright.** Across 316 transcripts and
1877 checked claims it emitted 0 findings, because it arms only when every
evidence list is empty, which guarantees another check already flagged the same
record. A name in the contract tuple that cannot fire is the defect this gate
exists to catch.

Also fixed, and found by neither adversary: `"C:/.../gh.exe" run view` never
matched `\bgh\s+`, so 40 sessions that HAD read CI were flagged.
`ci_green_without_fetch` went from 43 findings to 3, all three hand-checked.

Measured, not inferred: `cd shell && node --test` prints `pass 52` and
`duration_ms 148.6112` - word before number, no `in <float>s` - and its real
output through the parser yields 0 summaries, so classifying it a non-runner
costs nothing. Pinned so it reddens if node's shape changes.

### Readings, 2026-09-07 at `2b8fcbe`, historical rather than a claim about now

licence 41, docs 23, qa_companion 16 passed 0 failed 2 skipped, ruff clean,
`pytest tests` 1087 passed 1 skipped, `pytest agents/pity_engine` 80,
`shell node --test` 52 pass 0 fail, headless dry-run exit 0, mypy 27 source files
clean, `RSC_REQUIRE_HOOK_GATE=1 pytest tests/test_hook_gate.py` 12 passed,
`git worktree list` 0 beyond the main checkout. The single skip is the opt-in
network test in `tests/test_ingest_client.py`.

---

## 2026-09-06 - The publish sweep, a history rewrite, and rebuilding the remote

Six adversaries on distinct lenses, four builder slices, a `filter-repo` rewrite,
a delete-and-recreate of the GitHub repository, both shared-governor rounds, and
a durable inbox watcher. **All six adversaries returned REFUTED.** The repository
was not safe to publish as it stood, and the two findings that mattered most
could not be fixed by editing a file.

**THE SWEEP FOUND TWO SERVER-SIDE LEAKS, AND A FORCE-PUSH WOULD NOT HAVE CLOSED
EITHER.** The operator's Windows account path sat in blob `4401b1a8`
(`.claude/commands/done.md` line 172) inside 8 of the 33 PUSHED commits. The
forward fix had landed weeks earlier; the published record was never backfilled,
which is the `CLAUDE.md` rule about a data fix not being done until corrupted
records are backfilled. Separately, two commits force-pushed away earlier that
day - `a72a5c6` and `20385fd` - were still served by GitHub with a
`Claude-Session:` URL in them, and their SHAs were published by the repository's
own Events API and Actions run list.

That second finding is the load-bearing one and it is general: **a force-push
does not purge objects from GitHub.** This repository had already proved it once
and nobody noticed. So the remedy was not another rewrite - it was to rewrite
locally, DELETE the remote, recreate it, and push only clean history. Verified
from the server side afterwards rather than assumed: the two orphans and the
pre-rewrite HEAD all return HTTP 422 `No commit found`, the leaked blob returns
HTTP 404, and a cold clone of the new remote carries 0 account-path blobs of 291
and 0 session trailers.

Cost of the recreate, paid deliberately: the Actions run history and the creation
date. The description and all 17 topics were restored. Nothing else was lost -
0 stars, 0 forks, 0 watchers, 0 open issues.

**Guards cannot see this class, and both of them say so.**
`tests/test_machine_identity.py` builds its corpus from `git ls-files`, which is
the current checkout only, and `tests/test_commit_trailers.py` walks `git log` on
HEAD. Both passed throughout while the leak was live on the remote. Each is
correct for the question it asks; neither asks "what is already published".

**THE OBJECT STORE FOUGHT BACK THREE TIMES, and the mechanism is worth the
entry.** After the rewrite the leaked blob kept reappearing. In order: a
`FETCH_HEAD` left by fetching the backup bundle for a tree comparison; then
`refs/remotes/origin/main` surviving inside `.git/packed-refs` after
`update-ref -d` had removed the loose ref; then creating four agent worktrees,
which checked out the PRE-REWRITE commit and resurrected the whole history into
the shared object store, because worktrees share `.git`. `gc --prune=now` is
powerless against any of them - each was a live reference. The rule learned: an
unreachable-object purge is only true at the instant it is measured, and it must
be re-measured after anything that can create a ref. The final purge worked only
because the remote was deleted FIRST, removing the thing that kept restoring it.

**AN ERROR THIS SESSION MADE, recorded because the scoping mistake is
transferable.** The cross-repo adversary was instructed "do NOT read any
sibling tree on this machine - stay inside `C:\Resin Compute`", to stop it
rummaging in projects that are not ours. That instruction also made the one
question that mattered structurally unaskable: `ops/loop/winmutex.py` and
`slots.py` were already world-readable in Sibling-E's PUBLIC repository and had
been for five weeks, so publishing this tree disclosed nothing new about them.
A finding was raised to the operator and to two siblings on a premise nobody
had tested. Retracted in full. The lesson is not "read sibling trees" - it is
that a scope which protects a neighbour can also blind the check, and "is this
already public" was answerable from public data alone.

**FOUR BUILDER SLICES, write-list union proven disjoint with `sort | uniq -d`
before dispatch.** 12 files modified, zero write-list violations, zero untracked
residue. What landed:

- **The repository declared itself unlicensed in a tracked manifest.** The
  lockfile carried the pre-ADR-006 licence token against `shell/package.json`'s
  `GPL-3.0-or-later`. Commit `9cc98c6` flipped the manifest AND added the guard
  against exactly this in the same commit, but never regenerated the lockfile -
  and the guard swept 5 files of 153, so it could not see it. The guard now
  derives its corpus from `git ls-files` and was observed RED against the
  unfixed lockfile before the fix. `tests/test_licence_posture.py`, 33 arms to
  41.
- **Two compliance documents made checkable false claims.**
  `docs/LICENSE_NOTES.md` called the fixtures "synthetic" while citing a README
  that says the label was false of two of its three files, and claimed game item
  names appear "never as code identifiers" while `core/types.py` has `PRIMOGEM`,
  `INTERTWINED_FATE`, `STARGLITTER` and `HEROS_WIT` as enum members. ADR-002
  carried the same wording and got a BANNER ADDENDUM instead - 28 insertions, 0
  deletions, body provably unrewritten. The sibling of the trademark overclaim
  in `docs/SPEC_SCAFFOLD.md` was found by the same builder and fixed with it,
  per the fix-every-sibling rule.
- **Both CI ASCII gates passed any path containing a space.** `xargs` splits on
  whitespace; the gate warned on the fragments and returned 0. The anti-vacuity
  arm checked the LIST was non-empty, never that anything was SCANNED. Selection
  is now a NUL-delimited partition on the `.md` suffix, complementary by
  construction, with `--expect-count`. Coverage went from 139 of 153 to 153 of
  153, uncovered set EMPTY and halves disjoint. The 14 files no gate touched
  included `ops/install_scheduled_task.ps1`, the file class the entire ASCII
  rule exists for. `docs-guards` also ran both suites in ONE root-level pytest
  invocation, 359 tests, which `pytest.ini` forbids by name.
- **A pre-cut hole in the commit-time gate.** `tools/precommit_gate.py` exempted
  a data/external/ prefix from the 7-bit rule. That directory is gitignored
  NOWHERE and appeared in no other file in the tree - it is deliberately written
  without backticks here, because it names nothing that exists and the docs
  guard correctly rejects a dead pointer. So the one gate that would flag a
  fetched upstream payload was pre-disabled at a location `git add -A` would
  happily stage. Every remaining exempt prefix must now pass `git check-ignore`.
- **The exclusive-bind fix had landed at one call site only.**
  `surface/server.py` grew `_ExclusiveHTTPServer` after two dashboards bound
  8791 and the older one answered everything. `agents/pity_engine/__main__.py`
  kept the stock `ThreadingHTTPServer`, so two engines bound 8790 with
  byte-identical banners while the first served every request - on the port
  README section 6 tells a stranger to run. Ported TDD-first with an
  immediate-restart arm and an ephemeral port.
- **Two docstrings misled an auditor.** `tools/publish_next_session.py` claimed
  to be "the one thing in the tree that writes outside it"; `make_shortcut.py`
  and the task installer also do. README described the Windows Scheduled Task in
  nine words and never said how to remove it, though it is hidden, elevated,
  fires at every logon, has no execution time limit, and survives deleting the
  clone. The removal command is now published, DERIVED from
  `ops/install_scheduled_task.ps1` line 45 rather than executed.

**THREE AGENTS CORRECTED THEMSELVES, which is the shape the protocol is for.**
The engine builder's mutation test refuted its own assumption: dropping
`SO_EXCLUSIVEADDRUSE` alone left every arm green, and a full nine-cell bind
matrix showed only `reuse`/`reuse` double-binds, so `allow_reuse_address = False`
is the load-bearing half and no test on this platform can pin the setsockopt.
That was re-derived independently at the merge rather than taken on trust, and
`surface/server.py`'s docstring - which credited the wrong half - now records it
along with the fact that a guard claiming to pin that line would be a guard about
nothing. The CI builder's own surviving-neighbour arm caught both workflows
writing their file lists into the checkout. The licence builder found a hole in
the guard it had just written: a correction note quotes the sentence it corrects,
so a whole-file sweep passes on the quotation.

**BOTH SHARED-GOVERNOR ROUNDS LANDED, and the leak fix is measured here.**
Sibling-E rotated the mutex names (`winmutex.py` to `0b112a4f`) and fixed the
`hold()` release-path leak (`slots.py` to `629c3d51`). Both were copied
BYTE-WISE off Sibling-E's live tree with `cp`, re-hashed from THIS repo's own
disk against the published values, and the index blob compared to the disk
bytes for each. Measured on this box, 8 workers over 2 slots at `backoff=0.02`,
40 rounds:

```
old 1c4f8af4   35 of 40 rounds leaked   51 lockfiles   69 SlotTimeouts
new 629c3d51    0 of 40 rounds leaked    0 lockfiles    0 SlotTimeouts
```

That also explained an unrelated-looking red:
`test_contending_threads_never_exceed_max_slots` failed once with a SlotTimeout
during a full-suite run and passed six times in isolation immediately after. It
was the leak surfacing as a flaky test under load, in a repository that does
not even acquire a slot - the tests are the only callers here. Ten consecutive
runs since adopting the fix: zero failures. Sibling-C was right to refuse the
`slots.py` bytes until they were announced; the announcement arrived and both
rounds are now three-way equal, verified by hashing all three disks directly.

**A DURABLE INBOX WATCHER, because a live one dies with its session.**
`scripts/watch_inbox.py` plus `tests/test_watch_inbox.py`, 11 arms. Watermark
under `ops/runtime/`, written through `core/atomic_io.py`. Reading never
acknowledges; an absent inbox is a plain line rather than a traceback; a corrupt
watermark degrades toward RE-REPORTING, because a duplicate read costs a glance
and a dropped note costs a sibling waiting on an answer nobody knows they owe.
Keyed on NAMES rather than content hashes, with the cost accepted and pinned in
both directions - a rename re-surfaces a note, which is strictly better than an
EDITED note reading as already seen. Four mutants killed. The first mutant
written for the corrupt-watermark arm was EQUIVALENT and passed, which is
recorded because a surviving mutant is evidence only when it actually changes
behaviour.

**Decisions taken, so they are not re-litigated.**
`docs/adr/ADR-004-port-block.md` stated that a port grep across six sibling
trees hit "decompiled game assets, a strings dump"; that characterised the
contents of unpublished trees, was never load-bearing for the port argument,
and is redacted WITH the redaction recorded in the ADR rather than done
silently. Charter v3 from Sibling-C is ADOPTED, with one dissent filed: "commit
onto the worktree branch, push it, then remove the worktree" assumes a workflow
where agents commit, and this tree's protocol forbids builder commits outright,
so the invariant - no worktree is removed until its work exists somewhere that
survives the removal - should be the charter text rather than the step
sequence.

Counts measured 2026-09-06 on Python 3.14.4 at `dd1ac02`, as a historical
reading: licence QA 41 passed, docs QA 23 passed, `qa_companion` 16 passed 0
failed 2 skipped, ruff clean, `tests` 852 passed 1 skipped, `agents/pity_engine`
80 passed, `shell` node 52 pass 0 fail, headless smoke exit 0, mypy clean over 23
source files. The tree still DECLARES 3.11 in `CLAUDE.md`, `mypy.ini` and
`ruff.toml`, so that reading is green on 3.14 only; the divergence predates this
work and was again not touched.

## 2026-09-06 - Joining the cross-repo concurrency governor, and being refuted twice

`ops/loop/slots.py`, `ops/loop/winmutex.py`, `tests/test_loop_concurrency.py`,
`tests/test_core_config.py`, `core/config.py`.

This repo took the third slot in a machine-wide concurrency bucket shared with
Sibling-E and Sibling-C, vacated when Sibling-B was archived. The two governor
files are BYTE-IDENTICAL-BY-CONTRACT across all three trees. Vendored LAST, per
the ordered round the siblings specified, because this repo was the only
participant with no pin to break.

**Method, and it is the point of the entry.** The files were copied with
`shutil.copyfile` off Sibling-C's live tree, never with `Path.write_text` -
that emits CRLF on Windows and the contract is on bytes. Both sibling trees
were hashed BEFORE the copy and this repo's own disk was re-hashed AFTER it;
the hand-off note's digests were used only as a value to check against.
`.gitattributes` forces `*.py eol=lf`, so the index blob was compared against
the disk bytes as well - they match, which is what proves the pin survives a
fresh clone on an `autocrlf=true` box.

**THE GOVERNOR IS INERT AND THE TREE SAYS SO IN FOUR PLACES.** No production path
calls `slots.hold()`; the only callers are inside `tests/test_loop_concurrency.py`
against a `tmp_path` bucket. `headless/runner.py` is a job runner whose daemon
mode runs in-process job passes - verified by reading `run_daemon`, not assumed.
This is a parity contract joined ahead of need. Two of the three participants
acquire for real; this one's lane is reserved and unclaimed.

**Two of three adversaries returned REFUTED, and they were right.**

- A mutant removing `hold()`'s queueing passed the entire suite and fails
  Sibling-C's. The port had collected worker exceptions into `failures` and
  never asserted on them. Restored as `assert not failures` in
  `test_contending_threads_never_exceed_max_slots`; the mutant now fails even
  with a legitimate re-pin applied, and 30 consecutive runs stayed green.
- `SHARED_SHA256` drove both the presence guard and the digest guard, so deleting
  one entry disarmed both in a single edit - 18 passed, exit 0, silent. Adding an
  `__init__.py` beside the vendored pair, or a third module, was equally green.
  One root cause: the
  pin named FILES, not the DIRECTORY. Closed by `VENDORED_MODULES` plus
  `test_the_pin_covers_every_vendored_module_and_nothing_was_added`.
- `tests/test_core_config.py` PROMISED that any future wiring of the ceiling to
  `os.environ` "has to turn this file red", on the strength of a substring scan of
  one function body. Defeated in one line by the module's own
  `field(default_factory=...)` idiom, which moved the ceiling to 9 while every
  guard reported green. A guard that overstates its reach is worse than a missing
  one: it tells the next session not to look. Closed structurally by
  `test_the_ceiling_field_has_no_default_factory` and behaviourally by
  `test_a_poisoned_environment_cannot_move_the_ceiling`.
- The missing fourth arm of `is_stale` - the mtime fallback that stops an
  UNPARSEABLE lock wedging a lane - is now covered by
  `test_a_corrupt_lock_cannot_wedge_the_bucket_forever` with its survivor arm.

Every fix was mutation-tested AFTER the fact. Five mutants that were green before
are red now. That order matters: the session's own lesson is that a guard nobody
has watched fail is a guard nobody has tested.

**A REAL DEFECT IN THE SHARED FILE, REPORTED RATHER THAN FIXED.** Under contention
on Windows the vendored `hold()` leaks lockfiles: measured here at 33 of 40 rounds
with 8 workers and 2 slots. The mechanism was proven deterministically, not
inferred - `reap` to `is_stale` to `_read` to `Path.read_text` holds a handle
opened without `FILE_SHARE_DELETE`, so the releasing holder's `slot.unlink()`
raises `PermissionError` winerror 32, `except OSError: pass` swallows it, and the
release is LOGGED anyway. A log-reading overlap analysis therefore records a
release for a lock still on disk, and the lane is not reclaimed for 4.5 hours.
Re-pinning is a JOINT act, so the file was not touched; the reproduction went to
both siblings through `moon_sync_inbox/`.

**The leak DISARMS ITS OWN REAPER, and this half is deterministic rather than
statistical.** An orphaned lockfile keeps the payload written at `hold()` entry,
so if the leaking holder is still alive both of `is_stale`'s fast arms answer
"not stale" - the pid IS alive and the ts IS recent - and `reap()` skips it.
Measured directly, no race needed: `is_stale` False, `reap` removed 0, ghost
still on disk, and only the 4.5-hour age arm ever clears it. That points
straight at a long-lived controller running many cycles under ONE pid, where a
lane leaked in cycle N is unreapable for the life of the process and narrows the
bucket for the other two repos. Reported as an addendum the same evening. The
rate figures are bounded honestly in that note: 107 of 200 rounds at
`backoff=0.02`, and a 30-of-30 fully-wedged result that ran at `backoff=0.0` and
is a demonstration of the terminal state, NOT a rate. The production defaults
are `backoff=2.0, jitter=2.0` and that rate was not measured.

**Errors made and corrected in-session, recorded because the next reader
deserves them.** The `690d8b7` commit message cited
`test_a_missing_vendored_file_is_a_failure_not_a_skip`, a test that has never
existed - the name came from a dispatch brief and was not read back off the
file. The real one is `test_the_vendored_governor_is_present`. The same message
called the parity "recorded from three separate disks", which overstates it:
all three roots are on one volume, and Sibling-C's note hashed THIS repo's
files rather than printing its own. Both are corrected in `bb7f1ab`, which
cannot amend them.

Counts measured 2026-09-06 on Python 3.14.4, as a historical reading: `tests` 806
passed 1 skipped, `agents/pity_engine` 76 passed, ruff clean, mypy clean. Note the
tree DECLARES 3.11 in `CLAUDE.md`, `mypy.ini` and `ruff.toml`, so that reading is
green on 3.14 only; the divergence predates this work and was not touched.

## 2026-09-06 - Landing the public-repo fixes, and a refutation that reversed one

The fix session for the previous entry's audit. Nine slices, worktree-isolated,
dispatched against a write-list union proven disjoint with `sort | uniq -d`
before anything started. Every slice touched exactly its declared files - checked
with `git status --short` in each worktree before merging, zero violations and
zero untracked residue.

**THE MOST IMPORTANT RESULT IS A REVERSAL, AND IT WENT THE OTHER WAY FROM LAST
SESSION'S.** The previous entry's proudest finding was a refutation that rescued
a false positive. This one is a refutation that removed a false negative, and it
landed against work this session had already merged.

A research pass reported that it had located a first-party Genshin-specific Legal
FAQ on HoYoLAB that the prior session had missed, and that a literal-word probe
of the COGNOSPHERE Terms of Service found no scraping clause. It returned
`GATE: CLEARED`. `docs/adr/ADR-008-fan-content-posture.md` was written on that
evidence and merged. An adversary dispatched with a licence-and-evidentiary-
weight lens returned `REFUTED`. The main thread then re-probed every checkable
claim against the primary artifacts itself, because agreement between agents is
not evidence and neither is disagreement. **The adversary was right on every
count:**

- **The Terms of Service DO carry an express scraping prohibition.** Section 7,
  clause c, applied to the COGNOSPHERE Services, conditioned on prior written
  permission, with no non-commercial carve-out. Measured directly:
  `curl` of `https://tot.hoyoverse.com/en-us/terms` returns 219297 bytes and
  `grep -o -i -E "scrap[a-z]*"` returns two hits of `scraped`, at byte offsets
  66250 and 156982. The summariser the research pass overturned had been right.
  **The main thread's first reading of WHY was itself wrong, and the correction
  is the better lesson.** It concluded the probe "cannot have run". A third
  agent re-probed with word boundaries and found the honest explanation:
  `\bscrape\b` returns 0, and so do `\bscraping\b`, `\bscraper\b`, `\brobot\b`,
  `\bspider\b`, `\bcrawl\b` and `data mining`. ONLY the past participle
  `\bscraped\b` hits. Every term on the original probe list genuinely returns
  nothing. The probe was defeated by INFLECTION, not fabricated. Verified
  independently by the main thread against the same 219297-byte fetch.
  A literal probe is only as good as its morphology: search the stem, not the
  lemma.
- **The FAQ's enumeration is open-ended.** Measured on the retrieved body, which
  lives in the `structured_content` field and not `content` - `content` is 5
  characters. "including but not limited to" appears 3 times, "any other" 4,
  "such as" 4, "current or future" once.
- **The probe searched for vocabulary the document never uses.** `tool`,
  `software`, `API`, `tracker`, `calculator`, `database` all score zero, and
  that was reported as reassurance. The document's own words are `program`, 6
  times, and `service`, 12 times. `website` was reported as appearing once; it
  appears 8 times.
- **The sentence the whole finding rested on answers a different question.** It
  is the answer to a question about using images, text or audiovisual materials
  of the game for re-creation or posting to a personal fansite. This project
  vendors none of those. A non-prohibition of X is not evidence about Y.
- **An admitted evidence hole was admitted for a false reason.** ADR-008 said no
  PDF renderer was available. `command -v pdftotext` returns
  `/mingw64/bin/pdftotext`, version 4.00.

ADR-008 was rewritten against the artifacts. Operator decision: publish on the
vendoring argument alone. The posture rests on what is verifiable about the
project rather than on a 2021 forum post - zero vendored assets, zero vendored
data, no contact with the game client, no HoYoverse endpoint called,
non-commercial - which was always the half doing the work. The Section 7(c)
clause and the HoYoverse to `enka.network` to this-repo data chain are recorded
as an open question the ADR does not resolve, rather than one it pretends is
cleared.

**The durable lesson: a probe returning a convenient NEGATIVE deserves exactly
the scrutiny a summary returning a convenient POSITIVE gets.** Last session's
lesson was that agreement between two agents is not evidence. This session's is
the single-agent version - a retrieval that confirms what you hoped is still a
retrieval you have to check. Both were settled the same way, by going to the
artifact instead of counting agents.

**PROCESS FAILURE, TWICE, recorded rather than left to be inferred.** Both
adversaries dispatched this session reported a FREEZE VIOLATION, and the second
one happened AFTER the first had been acknowledged.

The first: the main thread merged ADR-008 into the working tree while the licence
adversary was reading it, so `git status --porcelain` went from 1 line to 13 to
17 mid-pass. The second: while the quickstart adversary was running, the main
thread edited fourteen tracked files fixing the adjudicator's findings, and that
adversary listed all fourteen and noted two concurrent `pytest` processes that
were not its own.

`.claude/commands/orchestrated-run.md` phase 5 requires candidates to be FROZEN
before dispatch, and phase 6 inherits it. Both adversaries handled the violation
correctly - the first pinned its verdict to a worktree copy and named the mtime,
the second proved its own subject was byte-identical to `58c02b4` by sha256 and
cloned from the committed HEAD rather than the worktree. Both verdicts therefore
stood. That is the agents being careful, not the process being sound.

**The lesson is specific and it is about the orchestrator, not the agents.** A
read-only pass is not free to dispatch: it puts the tree under a lock the
orchestrator has to honour, and an orchestrator that keeps merging because "they
are only reading" has silently redefined what the verdict is about. The fix is
mechanical rather than a resolution to be careful - dispatch read-only passes
against a COMMITTED SHA and tell them to clone or `git archive` it, which is
exactly what the second adversary did unprompted and what made its verdict
survive.

**One root cause had three instances, and all three are fixed.** A guard that
tests PRESENCE when it means TRACKEDNESS. Git stores no empty directories and
knows nothing about ignored ones, so a filesystem walk sweeps content that is in
nobody's clone.

- `tests/test_docs_consistency.py` called `.exists()` on every cited path. That
  is how `docs-guards` went red on the CI runner while the same test was green
  locally. It now also asserts each cited path is in `git ls-files`. It caught a
  real unstaged-citation case within minutes of landing.
- `tests/test_ports.py` had a function NAMED `_tracked_python_files` that did
  `REPO_ROOT.rglob("*.py")` behind an ad-hoc denylist. **This one was genuinely
  RED in the main checkout** and was found by re-running the suites after the
  merge, which is the entire reason that phase exists. It would go red for any
  contributor who created a `.venv/`. The old denylist filtered `.pytest_cache`
  but never `.mypy_cache` or `.claude/`, both live blind spots.
- `tests/test_shell_contract.py` was the third, and it turned out CORRECTIVE
  rather than preventive. Its ad-hoc denylist did cover the one case someone
  remembered, `node_modules/`, named in `shell/`'s own second `.gitignore`. But
  six ROOT `.gitignore` rules also apply under `shell/` and it remembered none
  of them - `dist/`, `build/`, `.mypy_cache/`, `tmp/`, `_scratch/`, `.vscode/`.
  The dist directory under shell/ - deliberately not written as a live path
  here, because it is gitignored and absent from a clean checkout, and the very
  guard this entry describes would flag it as a dead pointer - is
  electron-builder's DEFAULT output location, and `shell/package.json` declares
  electron as a devDependency, so it is a path a contributor produces simply by
  running the build. A file staged there turned TWO
  existing assertions red - the ASCII sweep and the foreign-port sweep - on
  content in nobody's clone. Its floor-shaped assertion is what hid it: a floor
  cannot detect OVER-collection.

**The pattern across all three is worth stating once.** Each guard named its
intent correctly and implemented something weaker, and in every case the gap was
an ad-hoc denylist - a list of the ignore rules whoever wrote it happened to
remember. `git check-ignore` and `git ls-files` already know the real answer.
The permanent arms added this session check the swept list against
`git check-ignore`, which is a DIFFERENT ORACLE from the `git ls-files` that
produced it, so the two cannot fail in agreement.

**The compliance labels now tell the truth, and the true claim is the stronger
one.** `data/fixtures/seed_roster.json` and `seed_materials.json` opened with
`"_synthetic": true` on the line directly above a `"_note"` calling them
hand-authored. Synthetic means invented; a verified avatarId is not invented.
They now carry `_hand_authored`, `_vendored` and `_content` blocks.
`data/fixtures/README.md` is retitled and names which of its three files is which
kind - `enka_sample_profile.json` IS genuinely synthetic and keeps that label.
The builder deviated from its brief here and was right to: the literal
instruction it was given would have condemned that honest file, whose own note
reads "SYNTHETIC hand-authored payload". It implemented mutually-exclusive
structured flags instead and reported the conflict.

**A sharper instance of the ADR-006 sweep than the audit found.** The audit named
four public-facing files still giving the dissolved copyleft reason. All four are
fixed. But `docs/LICENSE_NOTES.md` carried it in its GENERAL RULE - "GPL and
other copyleft stays DO-NOT-VENDOR ... because vendoring it would relicense this
repo" - and that is the version a future contributor actually applies, not a
table row. It was flatly false for a GPL-3 tree. The audit had marked that file
as handled correctly because its header blockquote states the dissolution.

**`python -m mypy` is green, and the obvious fix was the wrong one.** It had been
red on `numpy/__init__.pyi:737`. The chain: `mypy.ini` names
`agents/pity_engine/`, which crawls the engine's own `tests/`, which imports
pytest, which imports `_pytest.python_api`, which imports numpy. `core/`,
`engines/` and `ingest/` each check clean alone, which is how the chain was
isolated. The operator's instruction was to drop the stray numpy. **numpy is not
a stray:** `pip show numpy` reports it required by ImageHash, opencv-python,
PyWavelets and scipy, so uninstalling it would have broken software outside this
repo on a box seven projects share. That was reported back rather than executed,
and the narrower fix - excluding the engine test directory, which is what
`[mypy-tests.*]` already intended and simply never matched - was taken instead.

**Nothing in this tree had ever guarded the account-name leak, in either
direction.** `.claude/commands/done.md` carried an absolute
`C:/Users/<account>/` path. `tests/test_docs_consistency.py` only inspects
backticked tokens beginning with one of its declared tree roots, and an absolute
Windows path begins with none of them, so it was never even looked at.
`tests/test_machine_identity.py` now sweeps every tracked file across Windows,
POSIX and MSYS/WSL/Cygwin mount spellings, with a by-name allowlist carrying a
stated reason per entry. It builds its own offending literals at run time from
segment lists so the test file cannot become the violation it tests for - the
same trap that banned-glyph literals hit here before.

**A defect this session introduced, caught by this session's own guard.** The
main thread spliced a block into `ROADMAP.md` with `pathlib.Path.write_text`,
which opens in TEXT mode on Windows and silently rewrote all 252 lines as CRLF.
`.gitattributes` declares `eol=lf`, so git normalises on staging and NO DIFF
WOULD EVER HAVE SHOWN IT. Only `tests/test_line_endings.py`, which reads bytes,
caught it. Repair is `raw.replace(b"\r\n", b"\n")` then `write_bytes`; the
Write and Edit tools preserve LF and are the right instrument. Same shape as the
recorded backslash-mangling trap: an intermediary silently rewrites the payload.

**Also corrected before shipping, in a public-facing document.** ADR-008 claimed
a sweep of every HTTP URL in the runtime tree "returns exactly one". Re-run by
the main thread, a naive grep returns FOUR hosts. The substance holds - only
`https://enka.network` is a fetch the application makes; `registry.npmjs.org`
and a `github.com/sponsors` link live in `shell/package-lock.json` as
install-time package-manager metadata, and `schemas.microsoft.com` is an XML
namespace identifier in `ops/ResinCompute-Supervisor.xml` that is never
dereferenced. The wording now says so, because a reader WILL re-run that sweep
and must not conclude the ADR is wrong. That is the same failure mode that cost
this ADR its first draft.

**Measured 2026-09-06 at the merge seam, after all nine slices, by the main
thread rather than reported by a builder.** These are a historical reading, not
a claim about now, and no count is written into any guarded document.

```
pytest tests                    762 passed, 1 skipped
pytest agents/pity_engine        76 passed
ruff check .                    All checks passed
mypy                            Success: no issues found in 23 source files
shell: node --test               52 pass, 0 fail
scripts/qa_companion.py          17 passed, 0 failed, 1 skipped
headless --once --dry-run       exit 0
```

Guard arms added: `tests/test_licence_posture.py` 21 to 33,
`tests/test_docs_consistency.py` 16 to 23, `tests/test_shell_contract.py` 20 to
23, plus `tests/test_machine_identity.py` (33 arms) and
`tests/test_readme_tree.py` (9 arms) as new files.

**THE VERIFICATION PASSES CHANGED THE WORK, WHICH IS THE POINT OF HAVING THEM.**
Three independent passes ran against the committed tree, and two of them altered
what shipped.

- **The verifier** returned CONFIRMED WITH CORRECTIONS. Every count re-derived
  exactly, including the "was" baselines, which it measured by exporting
  `a7834c8` with `git archive` into a scratch directory rather than mutating the
  checkout. It found three false claims in shipped prose.
- **The adjudicator** returned ACCEPT WITH RESERVATIONS and made the sharpest
  observation of the session: this commit was convened because a licence gate
  refused publication on documents making claims that were false about their own
  contents, and it opened six more of exactly that class INSIDE the documents
  written to close them. ADR-009 asserted that a tree-wide grep for the SPDX
  identifier returned zero, in a sentence that contained the identifier, so the
  grep returned that line. All six are fixed.
- **The quickstart adversary** returned REFUTED, having actually run the README
  in three clones, one at a space-containing path, plus an isolated venv on the
  pinned toolchain. It verified the hooks end to end in both directions: a banned
  glyph blocked with HEAD unchanged in a clone WITH hooks installed, and the same
  glyph COMMITTED in a clone without them, which is the measured proof that the
  README's "do this first" is load-bearing rather than advice.

**The single most valuable finding was a blocker the orchestrator introduced.**
Replacing filesystem walks with `git ls-files` was correct and it took the number
of test files depending on the git oracle from 3 to 8 - measured by reading both
commits - without anything testing what happens when that oracle is absent.
`git archive 58c02b4 | tar -x` into a directory with no `.git`, then
`python -m pytest tests`, ABORTS AT COLLECTION with exit 2 and NOT ONE TEST RUNS,
because `tests/test_shell_contract.py` calls git inside a `parametrize` argument
at import time. With that file skipped, 48 more fail. That is what a person gets
from GitHub's "Download ZIP", from an sdist, or from any vendored copy - and the
commit whose entire purpose was to make this repository publishable shipped it.
The fix makes trackedness-dependent guards SKIP loudly when git is unusable,
never fall back to a disk walk, with a guard that fails if the skip path is taken
inside a real checkout.

**THE BLOCKER IS FIXED, AND FIXING IT EXPOSED A SECOND ONE.**
`tests/conftest.py` now holds three shared helpers. `git_unusable_reason()` asks
`git rev-parse --git-dir` rather than looking for a `.git` entry on disk, because
the disk check is wrong three ways this project actually uses - a linked worktree
has a `.git` FILE, a submodule's lives under the superproject, and `GIT_DIR` can
move it. `require_git_repository()` skips one test at run time;
`skip_module_without_git()` skips a whole module at import time, which is needed
for exactly one file - `tests/test_shell_contract.py` calls git inside a
`parametrize` argument, so a run-time skip arrives too late and the exception
becomes a collection ERROR that aborts everything. The guards SKIP rather than
fail, and they never fall back to a disk walk, which would silently answer a
different question while reporting green. Every skip names the missing repository.

The dangerous failure mode is guarded: if the helper ever reported git unusable
inside a real checkout, every git-dependent guard would evaporate at once and the
suite would still be green. `tests/test_commit_trailers.py` cross-checks it
against an INDEPENDENT signal - a `.git` entry on disk, deliberately not how
detection works - and fails if the skip path is taken in a real repository.

**The second blocker was masked by the first.** With collection fixed, one test
still failed in the archive, and only at a path containing NO SPACE.
`tests/test_hook_interpreter.py` ran the pre-push hook as `_run_sh(f'"{hook}"')`,
embedding a quoted Windows-looking path inside an `sh -c` string. MSYS argv
conversion mangles that and the closing quote is lost - `sh: -c: line 1:
unexpected EOF while looking for matching quote`. A space in the path SUPPRESSES
the conversion, which is the only reason it passed at `C:\Resin Compute`. It
would have failed for anyone cloning to `C:\dev\ResinCompute`, which is the
normal case. Fixed by passing the hook as an argv element and running
`exec "$0"`, so sh never re-parses it. Same root cause as the recorded
`taskkill //F //PID` rule.

Measured after both fixes, by the main thread:

```
real checkout                         763 passed, 1 skipped   exit 0
source archive, no .git, no spaces    692 passed, 50 skipped  exit 0
                        was:          0 tests ran             exit 2
```

**Prose defects the adversary found that were real and are fixed:**
`requirements.txt` stated the PityEngine runs on `:8870` in the present tense -
the pre-ADR-004 port inside a sibling project's reserved block, in the one file
the quickstart tells a reader to open, and the ONLY non-historical mention of
that number in the tree. The README ran a foreground server and a client call in
a single fenced block, so the second line could never execute, and repeated the
shape four more times across the daemon, the supervisor, the restart trigger and
the health read. And the README's stated REASON for its PowerShell convention was
wrong in a way that mattered: `curl -s <url>` does not fail with "no such
parameter", it BINDS `-s` to `-SessionVariable`, swallows the URL, and then
prompts for the missing `Uri` - so the console appears to hang. The advice was
right and the mechanism given for it was wrong, which is worse than saying
nothing, because it teaches a reader to expect the wrong symptom.

**Operator decisions taken this session,** so they are not re-litigated: the
repository keeps the name `Resin-Compute` and gets "Resin Compute & Pity Engine"
as its DESCRIPTION and README H1 rather than a rename, leaving the two-tier
convention in `CLAUDE.md` intact; commit identity ships as-is with no second
history rewrite, considered and declined; publication rests on the vendoring
argument alone; and the three unread PDFs are recorded as an open hole rather
than closed this session.

## 2026-09-06 - The public-repo audit, and the finding that refuted itself

An audit session, not a fix session. Every gate was green at commit `57f8894`
before a line was touched, so nothing below is a broken build - each item is a
defect a stranger would meet on a repository that is still PRIVATE. The findings
landed in `ROADMAP.md`; the fixes are next session's work, on operator
instruction. No builder was dispatched and no slice was merged, and that
departure from the default orchestrated shape is recorded here rather than left
to be inferred.

**THE MOST USEFUL RESULT WAS A REFUTATION OF THIS SESSION'S OWN FINDING.** UID
`618285856` appears in `README.md` and three test modules while every other UID
in the tree is patently fake - `000000000`, `900000000`, `111111111`. Both the
audit and the planner independently flagged it as a probable real account, on
that reasoning, and both were WRONG. It is Enka.Network's own published example
UID, verified against the primary artifact rather than against either agent's
reasoning: it appears twice in
`https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/api.md`. Two
agents agreeing was not evidence - they shared the premise that an
unlabelled-looking UID is an unlabelled UID, and testing that shared premise
against upstream is what settled it. The residual work is one line at the use
site so the next reader does not spend the same hour reaching the same wrong
conclusion. Verification pointer: the URL above, and `README.md` line 195.

**A single-line grep missed a wrapped sentence, measured here.** The sweep for
the dissolved copyleft rationale - "vendoring either would relicense this repo",
which stopped being true when ADR-006 made this tree GPL-3-or-later - returned
eight files and did not return `README.md`. The phrase wraps across
`README.md:317-318`, so `relicense th` matches nothing on either line. A
multiline-aware re-grep found it. Any sweep that greps for prose must assume
wrapping; a naive one scores clean by not looking.

**The licence gate REFUSED publication, and the refusal is narrow.** An
independent read-plus-web pass cleared the substance: zero binary assets
anywhere in the tree - no art, icons, audio or fonts, confirmed by glob rather
than by the NOTICE's assertion about itself - zero runtime dependencies, three
dev pins none of which is a data library, zero imports of any forbidden
upstream, zero bulk data. Names and published drop rates are facts and are
excluded from copyright. It refused on four text defects, all recorded in
`ROADMAP.md`. The sharpest is that two fixtures are labelled false in a way that
matters more once public: `seed_roster.json` and `seed_materials.json` carry
`"_synthetic": true` on the line directly above a `"_note"` reading
"Hand-authored seed identity table", and `data/fixtures/README.md` is titled
"SYNTHETIC test data only" while its body says "hand-authored by this
repository". Hand-authored is what ADR-002 requires and what `NOTICE` already
says correctly; synthetic means invented, and real verified avatarIds are not
invented. The true claim is also the stronger one, which is why this is worth
fixing rather than arguing.

**Per-file GPL headers: the deferral was checked and holds.** GPL-3's "How to
Apply These Terms" sits AFTER `END OF TERMS AND CONDITIONS` in the shipped
`LICENSE`, so it is an advisory appendix rather than a condition of the grant,
and section 5(b) binds "the work" and binds a modifier rather than the original
author. So the project is below best practice, NOT non-compliant, and ADR-006's
Consequences section is correct as written. The decision still needs recording
as a decision rather than a silence - 78 tracked `.py` and 10 tracked `.js`
carry zero SPDX identifiers, measured this session.

**Two ROADMAP claims were measured false and removed.** "Until that happens the
CI workflows are inert" - `git rev-parse --show-toplevel` returns the tree root,
`git remote -v` returns the standalone remote, `ci.yml` carries no
`working-directory`, and `gh run list` shows both workflows green against this
tree. And `docs/LEDGER.md` was listed under open work as a file to create, while
being the file that listing appears in.

**Recorded for the operator, not actionable by an agent:** two commits on `main`
carry an agent identity as author AND committer. This is not the trailer rule -
the trailers were stripped and are guarded by `tests/test_commit_trailers.py`,
which reads subject and body only and never `%an`, `%ae`, `%cn` or `%ce`. That
is the same shape as the already-recorded defect where the trailer policy was
enforced on one of its two forms. A second history rewrite is the operator's
call; the guard extension cannot be written before it, because it would fail at
HEAD.

Counts observed 2026-09-06 at `57f8894`, as a reading and not a claim about now:
licence QA exit 0; docs QA exit 0; `scripts/qa_companion.py` 17 passed, 0
failed, 1 skipped; ruff clean; `pytest tests` 697 passed, 1 skipped;
`pytest agents/pity_engine` 76 passed; `shell` node --test 52 passed; headless
smoke exit 0.

## 2026-09-06 - The session shape, the ritual, and three silent gates

The default session here is now orchestrated, multi-agent, self-adjudicating and
self-adversarial. ADR-007 argues it, CLAUDE.md states it as a rule, and
`.claude/agents/` makes it executable: seven roles whose read-only halves omit
Edit and Write from their tools list, so read-only is a mechanism rather than a
promise. `tests/test_agent_roster.py` pins the roster, the tool scoping and the
verdict vocabularies the orchestrator string-matches.

`/done` existed in every sibling project and not here. It does now, in
`.claude/commands/done.md`, alongside `orchestrated-run.md` and `ui-audit.md`.
The inline fenced block is the hand-off; the Desktop file is its BACKUP, written
by `tools/publish_next_session.py`, which reads the block out of
`NEXT_SESSION_PROMPT.md` and never accepts prompt text as an argument - so the
printed block, the tracked file and the Desktop copy cannot disagree. Operator
instruction: nothing follows the fenced block, because the operator selects it by
hand and trailing prose is text to select around.

THREE GATES WERE SILENTLY NOT RUNNING, and all three had looked healthy.

- **The pre-push gate had never run on this machine.** It selected `python3`,
  which resolves here to the Microsoft Store shim and redirects to a DIFFERENT
  interpreter carrying neither ruff nor pytest. `command -v python3` SUCCEEDS, so
  the fallback guarded by existence never fired. Every push printed two warnings
  and gated nothing. The same snippet was found in `pre-commit` and in
  `commit-msg` - three copies, one root cause. `scripts/hook_python.sh` is now
  the single shared selector and it probes CAPABILITY, not existence.
  Verification pointer: `tests/test_hook_interpreter.py`, whose non-vacuity arm
  runs the OLD snippet against a synthetic PATH and asserts it picks the useless
  interpreter - without that arm the guard would pass by luck on Linux CI, where
  `python3` IS the interpreter with the dev deps.
- **The trailer policy was enforced on one of its two forms.** `commit-msg`
  stripped `Co-Authored-By: Claude` and passed `Claude-Session:` straight
  through. A history sweep found BOTH forms on two commits - the root commit and
  one made later from the same hookless clone. Enforcement also lived only inside
  a hook, and `core.hooksPath` is local config that is not cloned, so the policy
  did not exist at all in a fresh clone. Verification pointer:
  `tests/test_commit_trailers.py`, which reads history from OUTSIDE the hook and
  skips explicitly on a shallow clone rather than sweeping one commit and
  reporting clean.
- **The declared line endings were half enforced.** `.gitattributes` claims
  `eol=lf` pins the bytes in the repo AND in the working tree. Only the repo half
  was true: 28 tracked files carried CRLF on disk while every diff looked clean,
  because the clean filter normalises into the index. Committed blobs were always
  correct, confirmed by `git hash-object --path` rather than assumed. Verification
  pointer: `tests/test_line_endings.py`.

History was REWRITTEN to remove the two trailer forms, on operator instruction,
and force-pushed. Not undertaken lightly: the command was proven on a throwaway
clone first, and both there and on the real tree the commit count was unchanged
and every commit's TREE HASH was identical, so only messages moved.

`.gitignore` stopped ignoring the command and agent docs. `.claude/` was a
blanket ignore, so the ritual and the roster would have existed only on this
machine - absent from a fresh clone, invisible to `docs-guards.yml`, unreviewable
in a diff. The exclusions are on directory CONTENTS, because a negation cannot
re-include a file whose parent directory is excluded.

MEASURED THIS SESSION, and worth keeping: the four slices that built the roster,
ADR-007 and the command docs were dispatched into the SHARED tree with no
worktree isolation - while writing the ADR that says to isolate. No work was lost
and no write-list was violated. It still cost accuracy in three of five agents:
one reported a sibling's tests RED when an independent probe showed them green,
one measured a suite polluted by files it did not own, and one watched HEAD move
underneath it. Every one of those is a FALSE report produced by the tree rather
than by the agent, and an orchestrator that believes one ships on a fiction.
`orchestrated-run.md` now names the mechanism, `isolation: "worktree"`, not just
the principle.

Counts observed 2026-09-06 after the rewrite, as a reading and not a claim about
now: ruff clean; `pytest tests` 697 passed, 1 skipped; `pytest agents/pity_engine`
76 passed; `shell` node --test 52 passed; `scripts/qa_companion.py` 17 passed,
0 failed, 1 skipped; headless smoke exit 0. `python -m mypy` remains red for the
known environmental reason - it follows `_pytest` into a numpy stub using PEP 695
syntax invalid under the pinned `python_version = 3.11` - and is advisory in CI.

## 2026-09-06 - Licence decided, and companion QA made runnable

ADR-006: GPL-3.0-or-later. The sibling house pattern was the trap rather than the
default - MIT and Apache-2.0 both permit closing the source and selling it, the
exact outcome to prevent. CC BY-SA was asked about and rejected on facts: it
permits commercial use, and Creative Commons advise against CC for software.

The licence text was VERIFIED, not pasted from memory: cross-checked against a
second independent copy, confirmed 7-bit ASCII, and its sha256 matches the
canonical published hash. That hash is pinned in a test.

ADR-006 amends ADR-002 in exactly one respect: the copyleft objection to
vendoring enka-py and ambr-py dissolves. The objection that mattered stands -
those wrap HoYoverse data and no outbound licence of ours touches that.

`scripts/qa_companion.py` answers the question the suites cannot: is the
companion working right now, on this machine, as installed. It binds an ephemeral
port so it never contends with a running dashboard.

**It found a false negative in its own first run**, which is the useful kind. It
reported the desktop shortcut absent while the shortcut existed - the operator had
renamed it to match their convention. Two real consequences:

- `make_shortcut.py` would have created a SECOND shortcut beside the renamed
  one. That is exactly what Sibling-A's refuse-unless-force default was
  guarding against, and its author said so in as many words. Fixed: the
  installer now scans for a shortcut with the same TARGET under any name.
  Idempotence converges on a state - a working shortcut exists - not on one
  filename.
- The QA now matches by target too, reusing the installer's own comparison so the
  two cannot disagree.

Also fixed: a test wrote a Windows path without a raw string, so one backslash
escape became a literal control character and another was an invalid escape. The
test still PASSED, because it only asserted inequality, so the defect was
invisible until a SyntaxWarning surfaced it.

That bug then bit a second time, writing THIS entry. The sentence above was
composed in a non-raw string and put a real control character into this file.
The ASCII guard in tests/test_docs_consistency.py did not catch it, because it
rejected bytes above 0x7E and said nothing about control bytes below 0x09. Both
are now rejected. A guard that checks one end of a range and not the other is a
guard with a documented blind spot.

And `test_a_stopped_server_releases_its_port_immediately` was flaky by
construction - dropping SO_REUSEADDR made the rebind strict, so the OS handing
that port to another process failed a test about TIME_WAIT. Now retried, with the
retry justified rather than papered over: a real regression fails every attempt.

## 2026-09-06 - Project-goals QA, mechanised

`tests/test_docs_consistency.py`. The docs must agree with the tree: every
backticked path in a governing document resolves, every ADR is indexed in both
directions, ADR numbers are unique and contiguous, and a ROADMAP line marked DONE
may not name an absent path.

**Written because a real pointer had already rotted.** CLAUDE.md instructed every
session to read an architecture document under docs/ that has never existed. Nothing checked it, so the instruction survived indefinitely.

Found four more on its first run, all real:

- **ADR-005 existed but was never added to the ADR index.** Missed when it landed.
- `docs/LEDGER.md` was cited by ROADMAP and did not exist. This file is that fix.
- ADR-004 cited `docs/LEDGER.md` in a way that read as ours when it meant
  Sibling-D's. Reworded.
- The goal spec wrote a dotted symbol as though it were a path. Reworded, and the
  checker now distinguishes `module.function` from a file by suffix.

`ops/runtime/health.json` is exempt BY NAME, with a stated reason, because the
supervisor creates it at run time. A further test asserts the exemption is still
referenced somewhere, so a dead exemption cannot linger.

## 2026-09-06 - Account state persisted; the dashboard cold-starts

`core/state_io.py`, the `persist_state` job, and a loader in `surface/`.
`reconcile_state` rebuilt the account every pass and the process then exited, so
the dashboard had nothing to render.

**Live-state-first is preserved structurally, not by promise.** The snapshot is
write-only from the headless lane; `tests/test_headless_persist_state.py` parses
`headless/jobs.py` and asserts the absence of a read, because a cache that
quietly starts being read looks like a hit rather than like a broken rule.

The surface renders the reading's AGE. A cached roster shown without one is
indistinguishable from a live query, and the confusion is silent because a stale
roster looks plausible. `None` is not zero: a never-synced account reads "no
reading yet".

**Defect found by observation, not review.** `ThreadingHTTPServer` sets
`allow_reuse_address`; on POSIX that only sidesteps TIME_WAIT, but on **Windows**
it lets a separate process bind a port another process is already listening on.
Measured: two surfaces held 8791 at once, `netstat` showed both, and the OLDER
one answered every request - so a freshly started surface serving new code was
silently ignored while looking healthy. It also made `main`'s documented exit
code 2 unreachable on Windows, which is the code the Electron shell renders its
refusal from; the second process bound fine and blocked forever. Fixed with
`SO_EXCLUSIVEADDRUSE`, with a test pinning that an immediate restart still works.

**Second defect, in the tooling rather than the code.** `taskkill /F /PID` does
not work under Git Bash: MSYS path conversion rewrites the lone `/F` into `F:/`.
It fails SILENTLY when redirected, which is how the double bind went unnoticed.
CLAUDE.md's own hard rule now carries the caveat that it must be written
`taskkill //F //PID`.

## 2026-09-06 - Seed-team roadmap recorded as a stamped goal spec

`docs/GOAL_SPEC_SEED_TEAM.md`. An operator-supplied roadmap generated by a web
assistant, reviewed against this tree's verified ground truth, with every claim
carrying exactly one stamp: VERIFIED with a citation, REFUTED, UNVERIFIED,
TIME-SENSITIVE or NOT MODELLED. The stamp is about provenance, not plausibility.

Findings: the roadmap **omits the domain rotation entirely**, which
`core/domains.py` encodes as a three-day cycle, so following it can spend resin
on a day the domain is not dropping what is needed. "Spend the hoard the second
the banner returns" is not a plan when the pull count is computable. The Beginner
Wish banner is NOT MODELLED - `BannerKind` has no member for it.

Its cost figures are UNVERIFIED and deliberately kept out of `data/`.
`tests/test_goal_spec.py` sweeps for them mechanically; proven non-vacuous by
mutation, and reverted clean.

Baseline recorded: **the account has not been played.** The dashboard's empty
state is therefore correct rather than degraded.

## 2026-09-06 - Electron companion, system tray, idempotent shortcut

`shell/`, `scripts/make_shortcut.py`, ADR-005. Reverses ROADMAP's "dashboard is
out of scope" for a stated reason - the operator wants the surface BEFORE further
feature work, so each feature becomes visible as it lands. ADR-001 is not
reopened: its subject was the language of the compute tree, and the surface is
Python too.

`shell/main.js` is WIRING ONLY, inherited from Sibling-A. It imports Electron
so nothing can load it in a test, so nothing that decides anything lives there.

- The tray icon ships as base64 text; the tree carries no binary asset. Its
  colour was SEARCHED, not picked: a notification area is near-black under one
  theme and near-white under the other, so 2078c8 was chosen for clearing 3:1
  against both (4.58:1 each way). The first candidate measured 2.94:1 against
  white and the generator's own assertion rejected it.
- An invisible drag strip spans the top of the page. The window is frameless, so
  without it there is nothing to grab.
- `state.js` refuses the string `"false"` rather than coercing it; it is truthy,
  and a tray checkbox reading it as checked would show the opposite of the truth.
- `geometry.js` recovers a window remembered on an unplugged monitor rather than
  restoring it offscreen, where it has focus and is invisible.
- `make_shortcut.py` is IDEMPOTENT, diverging from Sibling-A's
  refuse-unless-force, which is not. Proven: run 2 created, runs 3 and 4
  reported nothing to do, exit 0.

Measured rather than assumed: `npm install` leaves NO `electron.exe` behind - the
package declares no postinstall and fetches lazily on the first require.

## 2026-09-06 - Local dashboard surface on 8791

`surface/`. Six panels. Panels DECLARE THEIR OWN READINESS - ready, partial or
not wired - and a panel that is not ready renders what it is waiting on instead
of a plausible zero. Enforced in `Panel.__post_init__`, not just in the builders,
so a panel added later cannot ship a silent gap.

This applies the zero-is-not-unknown distinction `engines/objectives.py` already
draws to the UI: rendering "0 resin required" off an empty cost table is not a
neutral placeholder, it is a confident wrong answer.

Escaping is load bearing: `MappedCharacter.display_name` is a nickname another
player typed, carried through enka.network onto a page that runs inside Electron.
Both the element case and the attribute break-out case are pinned.

## 2026-09-06 - Port block 8790-8809 reserved; PityEngine migrated off 8870

ADR-004, `core/ports.py`, `tests/test_ports.py`. The scaffold put PityEngine on
8870 by mirroring Sibling-F's 8860 and adding ten. **8870 is inside Sibling-F's
reserved block 8860-8879.** Nothing was listening, so nothing broke and nothing
warned.

Verified against sibling SOURCE, not a live scan - the rule Sibling-A learned
the hard way when it allocated a band by probing while the owning project's GUI
happened to be closed. The only registry hit inside the new block was
Sibling-C's `range(8770, 8790)`, whose end is exclusive.

Three sites carried the literal 8870 independently; all now resolve to
`core.ports.ENGINE`. The tests pin each constant against the module that really
binds rather than re-asserting the literal, and a negative guard rejects any
sibling port literal in tracked Python source.

Reservation shared to all five siblings through the established
`moon_sync_inbox/` channel, without editing any sibling's source.

## 2026-09-06 - Initial scaffold

Recorded in `README.md` and `docs/SPEC_SCAFFOLD.md`. ADR-001 through ADR-003.

## 2026-09-07 - the watcher fires, the commit gate is proven, and the inbox gets read properly

Four operator instructions arrived mid-session and each is recorded in
`CLAUDE.md` rather than only obeyed: responses under 500 tokens, CAVEMAN ULTRA
as the chat dialect, every API key in a machine environment variable, and the
cross-repo inbox AND ITS SUBDIRECTORIES reviewed, ingested, implemented and
answered.

**The watcher was correct and connected to nothing.** `scripts/watch_inbox.py`
shipped on 2026-09-06 with eleven arms and every property the siblings asked
about. There was no `.claude/settings.json` in this tree at all, so it ran only
when a human typed it - which is why the hand-off had to instruct the next
session to run it by hand. A declared hook is not a firing hook; the quieter
predecessor is that AN UNWIRED SCRIPT IS NOT A WATCHER. Fixed in
`.claude/settings.json`, guarded by `tests/test_session_hooks.py`, which
EXECUTES each declared command rather than resolving its target.
`.gitignore` gained `!.claude/settings.json`, because the blanket `.claude/*`
rule would have left the wiring on one box - the exact failure its own comment
says the command docs were tracked to avoid.

**The commit gate is proven on a real runner.** `tests/test_hook_gate.py` and a
CI step; observed on `ubuntu-latest` as `12 passed in 0.75s` after
`armed: .githooks/commit-msg .githooks/pre-commit .githooks/pre-push (all mode
100755)`. Ran, not skipped.

**An adversary then REFUTED four claims made about that work, and the gate
itself survived.** Three mutation directions each killed the right arms, so the
gate discriminates. What did not survive was the prose: `RSC_REQUIRE_HOOK_GATE`
does not convert an unconfigured clone - the fixture arms its own throwaway repo
and an unconfigured clone passes 12 of 12. It converts an UNMEASURABLE MACHINE.
The dependency scan matched `$ROOT/` but not `${ROOT}/`. The positive control
went red when the pinned interpreter could not import ruff, blaming the gate for
a contributor's venv. The docstring claimed a `GIT_*` scrub wider than it
performs, citing a mechanism `git 2.53` does not exhibit. All four corrected.

**A sibling's claim about this tree was refuted by measurement.** Sibling-E
reported RSC carrying the old leaking `slots.py` at `1c4f8af4`. Measured on
this disk and in the HEAD blob: `629c3d51`, the new one, with no copy of the
old anywhere. The explanation is timing, and it generalises: **note filename
timestamps are FICTIONAL and drift per sender by up to six hours.** Sibling-E's
note labelled `0455` was written at 22:40:52; the commit landing the new bytes
was authored at 22:49:50. Right when written, stale when filed, and unreadable
as such from the name. Sorting by filename inverts real order.

**The hand-off write gate was the weaker of two, and Sibling-E was right.** It
refused non-ASCII and truncation and passed an inline API key and an absolute
path naming the operator's account straight through to the Desktop - measured,
not theorised. That is the one write that leaves the toolchain, and
`NEXT_SESSION_PROMPT.md` is tracked in a public repo.
`tools/publish_next_session.py` now refuses both, and the refusal never echoes
what it caught: a gate that quoted the key would publish it in the act of
refusing to.

Three collisions surfaced landing that, each fixed at its SOURCE rather than
allowlisted, because the detector and the detected share a shape by
construction. `ACCOUNT_PATH` is assembled from a named segment; an allowlist
entry spelled as a chunk of regex is unreadable and goes unstable the moment the
line is edited. The fixtures use an obviously invented account - one that
planted the true name would be the leak it tests for.

**The 2026-09-06 session read the notes and skipped the directory beside
them.** `moon_sync_inbox/from-<sibling>-verbatim/` held 49 real files while the
notes only described them. A full triage put 2 in ingested, 17 in
have-an-equivalent, 25 in not-applicable and 5 in applicable-and-not-done, and
corrected two entries this session had provisionally mis-bucketed: this tree's
CI already does both jobs that Sibling-C's `md_guard_selector.py` and ASCII
sweep do, and does them from `git ls-files` rather than a frozen baseline.

**A verbatim file can be STALER than the prose describing it.** Sibling-C's
end-to-end hook-gate test arrived without the require-env flag Sibling-C's own
later note calls load-bearing, and gates on `shutil.which("git")` - existence,
not capability, the same defect class as `command -v python3` succeeding on a
Store alias. Sibling-E independently hit both. Diff the ASSERTIONS, never the
filenames.

Thirteen items were open against this repo, eight of them direct unanswered
questions. All answered in one note broadcast to all five per charter section
0(a), and `moon_sync_inbox/from-RSC-verbatim/` now reciprocates seven files
that Sibling-C had asked for three times.

Merged files and their guards: `.claude/settings.json` and `tools/caveman_default.py`
(`tests/test_session_hooks.py`); `tests/test_hook_gate.py` and the `ci.yml` step
(`tests/test_ci_workflow_complement.py`); `tools/publish_next_session.py`
(`tests/test_publish_next_session.py`); the credential sweep
(`tests/test_no_secret_literals.py`).

## 2026-09-09 - the two CI residuals close, and a refuted framing is recorded

Both residuals the CI outage exposed are closed, each as its own slice on a
disjoint write-list, each graded by an agent that did not write it.

`.github/workflows/ci.yml` checks out at depth 0, so the Co-Authored-By hard
rule is enforced by something other than a hook for the first time. The cost
was measured before the change, not assumed: 113 commits, about 7 MB of git
objects, and the sweep already ran green over this tree's real history.
Guarded by `tests/test_ci_history_depth.py`, whose floor and judgement sit in
one assertion and whose control varies seven flagged shapes against eight
cleared ones.

`.github/workflows/docs-guards.yml` passes `-rs` on both of its pytest
invocations, so the last CI lane that could report an unexplained skip count no
longer can. Guarded in `tests/test_ci_workflow_complement.py`, reusing the spec
parser rather than adding a third private matcher.

A VERIFIER REFUTED A CLAIMED CONSEQUENCE, and that refutation saved a lane. The
two shallow-clone skips in `tests/test_commit_trailers.py` were reported as
dead code once ci.yml went to depth 0. They are not: the docs workflow keeps
depth 1 and derives its selection from every test module mentioning a markdown
path, so that module still runs shallow there and both branches still fire with
true reasons. Deleting them would have removed live coverage.

AND A FINDING OF OUR OWN WAS REFUTED BEFORE IT REACHED CODE. A sibling's
`mkdir` shape led to a real fact - `mkdir` raises ValueError, not OSError, on a
NUL-bearing path - and to a false story about it, that this tree had fixed one
site and never swept the siblings. The census behind that story came from an
AST walk for a try block directly containing a mkdir call, which is
structurally blind to a guard placed at the CALLER, and the caller is exactly
where this tree put it. The adjudicated ruling is do-not-widen, on contract
grounds, with reachability measured at zero of eight. Recorded in `ROADMAP.md`
with the objection that still stands.

Merged files and their guards: `.github/workflows/ci.yml`
(`tests/test_ci_history_depth.py`); `.github/workflows/docs-guards.yml`
(`tests/test_ci_workflow_complement.py`).
