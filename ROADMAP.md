# ResinCompute roadmap

Open work, newest priorities first. Aspirational items live at the bottom.
Per-item completion history belongs in `docs/LEDGER.md`, never in `CLAUDE.md`.

## Status

Scaffold shipped 2026-09-06. The tree stands up, both suites run, the headless
lane smoke test passes, and the forecaster is correct for the current game
version. What follows is everything the scaffold deliberately did not do.

## Now

- **STATE AS MEASURED 2026-09-09 AT `1c596e3`, a reading and not a promise.**
  `python -m pytest tests` 1840 passed 1 skipped. `agents/pity_engine` 80
  passed. `node --test` 52 pass 0 fail. ruff, mypy at 34 source files,
  qa_companion 16 passed 0 failed, licence posture, docs consistency 29 and the
  headless dry run all exit 0. The census is at 77 arms, up from 43 at the start
  of the session; `tests/test_gate_mutation_runner.py` is new at 47.
  1793 plus 47 is 1840 and the arithmetic closes.

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

  **STEP TWO OF THREE OF THE GATE CENSUS IS DONE.** `tools/gate_mutation_runner.py`
  consumes the 18 tags, neutralises each tagged consult site in `_run_once`, and
  runs the application suite per mutant. STANDING RESULT, reproduced on the
  shipped bytes at the merge: 35 mutants, 27 KILLED, 8 SURVIVED, 0 false kills,
  exit 1. The REGISTRY is step three and is still unstarted.

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

- **OPEN, AND THE HIGHEST-VALUE ROW IN THIS FILE. EIGHT GATES IN `_run_once`
  ARE EXERCISED BY NOTHING.** Measured 2026-09-09 at `1c596e3` by
  `python -m tools.gate_mutation_runner`, 35 mutants, and reproduced on the
  shipped bytes. Each name below is a mutant that left the whole application
  suite GREEN, so no test depends on that gate doing its job:

      no-destination/if-false        workspace-trust/if-false
      refusal-recorded/if-false      bounce-mark/if-true
      bounce-write-all/operand-1     bounce-write-all/operand-2
      delivery-write-all/operand-1   delivery-write-all/operand-2

  `delivery-write-all/operand-1` IS THE ONE TO FIX FIRST. It drops the
  `bool(written)` term that the responder's own comment at
  `tools/moon_sync_responder.py:1861-1863` calls the guard and not decoration -
  the term that stops `all([])` reporting a delivery to ZERO DESTINATIONS as
  delivered. The comment has been right about its importance and wrong about it
  being covered, for as long as it has existed.

  THE WORK IS ARMS, NOT A FIX: the gates are correct, nothing drives them. Each
  needs a test in `tests/test_moon_sync_responder.py` or a sibling that fails
  when the gate is neutralised. VERIFY EACH ONE WITH THE RUNNER RATHER THAN BY
  EYE - `python -m tools.gate_mutation_runner --gate delivery-write-all` runs a
  single gate, and a survivor that becomes a kill is the proof the arm lands.
  Re-probe this row before spending a slice on it; it is a claim with a
  measurement date and it decays.

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
     `tools/moon_sync_responder.py:1037` is `rows = rows[-MAX_METRICS_ROWS:]`,
     the constant at `tools/moon_sync_responder.py:322`. That DROPS the oldest
     rows outright, and a metrics row carries five distinct measurements for one
     cycle, so deleting a row deletes evidence. Our own comment above it calls
     the cap THE BACKSTOP, NOT THE FIX and then considers only suppression,
     never rotation. The repair shape offered by RC is to rotate to an archive
     with the live file replaced LAST, so every failure leaves the live file
     complete rather than short. SCOPED: the invocation log trimmed at
     `tools/moon_sync_responder.py:1090` is correct as it stands, its lines not
     being evidence rows.

  2. WHICH LEDGER INSTANCE IS LIVE HAS NOT BEEN CHECKED HERE, and this row asks
     for a CHECK rather than naming a defect. `record_cycle` at
     `tools/moon_sync_responder.py:969` takes the ledger path as a PARAMETER
     from five call sites - lines 1615, 1634, 1665, 1700 and 1738. RC shipped
     two plausible bindings for its own live agreement and BOTH produced an
     identical failure, trial rows going 30 to 0, for two different reasons. No
     divergence has been measured in this tree. Deriving identity from the
     artifact being protected is the shape to reach for IF the check finds one.

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

- **OPEN. A FOURTH DISPOSITION, named 2026-09-09 and not in the standing list
  of three.** With `GIT_DIR` exported, `git rev-parse --git-dir` SUCCEEDS while
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
     `tools/moon_sync_responder.py:1119` and has EXACTLY ONE call site, at
     `tools/moon_sync_responder.py:1735`, inside the delivered branch and
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
