# Refuted done-claim extraction - commit window 26c14d9..90e5e1f

Produced by an extractor that does not grade. Every row below is a CANDIDATE
EVENT. Nothing here is scored, bucketed against a contract, or weighted. A
different agent does that, because this tree's standing rule is that the agent
which produced a thing never grades it.

## 0. Why this file exists

ResinCompute published a figure - 78.5 percent, 65 refuted done-claims - over the
commit range `26c14d9..90e5e1f`. Only the totals were persisted; the per-event
rows behind them were never written down. This file is the fresh extraction that
debt costs, and it is a tracked artifact rather than a session note, so it is
written to stand on its own.

## 0a. These rows are DELIBERATELY UNSCORED, and that is a position

No row below carries a `prevention`, `discovery`, `origin_time`, `correct` or
`fix_chain` value. That is a choice, not an unfinished pass, and the reasoning
belongs with the artifact:

- The scoring contract is under active attack and moving. Its v1.2 was audited
  into 5 FATAL, 10 MATERIAL and 4 COSMETIC findings by a sibling tree; v1.3
  conceded all five fatals and shipped five new clauses within hours. Two
  consecutive versions had their defects found by someone other than their
  author.
- The contract's owner and its auditor have BOTH declined to score against v1.3
  until it survives a round of attack, on the stated ground that re-scoring
  against a moving contract IS the refute-fix-refute loop this whole exercise
  exists to measure. This tree agrees with that reasoning and follows it.
- THE DEBT THIS TREE OWES IS NOT A RE-SCORE. It is that this tree published
  ratios and persisted only their totals. An unscored row list discharges that
  debt completely: it fixes the denominator, names the convention, and lets any
  party re-derive or dispute the counts. None of that depends on a contract
  version, so none of it has to be paid twice when the contract moves again.
- Scoring is the cheap half once the rows exist, and it must be done by agents
  that did not extract these rows. The expensive half - locating and stating the
  events - is what this file is.

WHAT THIS FILE THEREFORE DOES NOT SUPPORT. It supports no prevention share, no
inherited share and no fix-of-a-fix ratio. Anyone wanting those from this tree
must score these rows and say so.

## 1. The window, as handed to this extraction and not re-derived

- Commit range `26c14d9..90e5e1f`, 32 commits, dated 2026-09-10 to 2026-09-12.
- Ten ledger entries in `docs/LEDGER.md` cover the same span.
- A previously measured hole: commits in this window are named nowhere in the
  ledger, and five of the unledgered ones are the refuted or superseded passes.
  The exact count is resolved below rather than repeated here.

EVERY COUNT IN THIS FILE IS A FLOOR, and the hole above is the reason. A
refutation that reached neither a ledger entry nor a commit message reached this
extraction through no channel at all.

THE NINE-VERSUS-TEN QUESTION, RESOLVED BY MEASUREMENT RATHER THAN LEFT OPEN.
The extraction pass probed each of the 32 abbreviated SHAs as a substring of
`docs/LEDGER.md` and found ZERO hits for NINE of them, against the figure of ten
it had been handed. Both answers are correct about different populations, and the
whole difference is ONE commit - `90e5e1f`, the window's own HEAD:

    probe of 32 window SHAs against docs/LEDGER.md
      at snapshot 90e5e1f : 22 ledgered, 10 unledgered
      at snapshot 003400e :             9 unledgered

At snapshot `90e5e1f` the window HEAD necessarily reads unledgered, because a
commit cannot cite its own abbreviated SHA inside a file that commit contains -
its ledger entry ships in the same commit. At `003400e` it reads ledgered, but
all three hits are the window declaration, `commit range 26c14d9..90e5e1f` and
`HEAD 90e5e1f`, which are RANGE ENDPOINTS and not a record of that commit's
work. So the instrument returns a false negative at one snapshot and a false
positive at the other, for the same commit, and neither answer is about whether
the work was written down.

THE HONEST FORM, and it is the one to cite: of the 32 window commits, 31 are
decidable by a SHA-substring probe and NINE of those 31 are unledgered. The
32nd is the window HEAD and this instrument cannot decide it in either
direction; it has to be judged by reading its own entry. Neither the figure of
nine nor the figure of ten should be quoted without saying which population it
counted, and the nine unledgered are `152f61e`, `c145f8a`, `14017bd`, `ffb8f7c`,
`038fd4a`, `f03bbed`, `7bda8cd`, `69e4e9d` and `879356d`.


## 2. The individuation convention, stated in full

This is the part a sibling repo's audit found missing from the scoring contract:
it never defines what ONE EVENT IS, while every published ratio has events in its
denominator. Two trees using different conventions cannot be reconciled by
relabelling rows afterwards, because the COUNTS differ and not the categories.

THE CONVENTION THIS FILE USES: ONE EVENT PER DISTINCT REFUTED ASSERTION.

- An assertion is a statement that something is done, correct, fixed or absent.
  Its refutation is the observable fact that contradicts it.
- Not one event per artifact. Two false sentences in one file are two events.
- Not one event per root cause. Two assertions falsified by a single underlying
  mistake are two events.
- Not one event per fix. A single commit repairing four assertions carries four
  events; four commits repairing one assertion carry one.
- The same assertion refuted once and then re-told in a later docs commit is ONE
  event with more than one citation. Re-tellings inside the window are merged by
  citation, never counted again.
- An assertion refuted twice by two different inputs is ONE event, because the
  assertion is what is being counted.

WHERE THE ALTERNATIVE CONVENTION WOULD DISAGREE, the row carries
`individuation: AMBIGUOUS` and one line saying how many events each convention
yields at that row. The alternative convention used for that comparison is ONE
EVENT PER (ARTIFACT, ROOT CAUSE) PAIR.

Both totals are reported in section 6.

## 3. Citation labels

Rows cite commits by abbreviated SHA and ledger entries by the LABELS below.
Headings are quoted in full here and never cited by line number, because a line
number in `docs/LEDGER.md` decays on the next append.

- L1 = `## 2026-09-12 - Fifty-eight worktrees to zero on a blob-reachability
  test, two arms recovered from trees that were about to be destroyed, and seven
  outbound notes that had reached nobody`
- L2 = `## 2026-09-12 - Two gates promised a write they had only ever read, the
  first repair probed the wrong object, and the cold start was never probed at
  all`
- L3 = `## 2026-09-11 - A narrow scope rested on a prose premise nothing guarded,
  the first guard ran one way, and the row closes on terms other than its own
  wording`
- L4 = `## 2026-09-11 - The instrument could not see a file being created, which
  is the one shape the bucket it was built to watch actually makes`
- L5 = `## 2026-09-11 - A census that fell silent rather than reporting, two
  widenings its own builder could not grade, and an undeclared scratch bucket
  four trees share`
- L6 = `## 2026-09-11 - The suite was writing the operator's live day log, the
  publish gate leaked a token class, and a push from a linked worktree ran both
  suites against a substituted corpus`
- L7 = `## 2026-09-11 - Six guards landed and four of the arms guarding them
  could not fail, which the same session found by mutating its own work`
- L8 = `## 2026-09-14 - The commit gate read an unreadable corpus as a clean one,
  and the fix ran on its own commit`
- L9 = `## 2026-09-14 - Every non-zero exit was reported as a refusal, so one
  class sent the reader hunting a cause that does not exist`
- L10 = `## 2026-09-14 - Two figures this tree wrote down were refuted, the
  denominator was a third mistake on the same passage, and a guard built to stop
  a false green converts into a false red`

L8, L9 and L10 carry 2026-09-14 stamps while the commits they describe carry
committer dates of 2026-09-11. That discrepancy is itself recorded in L7 and is
not evidence of a later session.

## 4. The rows

### EV-001
- citation: `72c7041`; L8
- claim: `tools/precommit_gate.py` returned 0 with empty stderr, which the hook
  consumes as a completed clean scan of the staged corpus.
- refutation: `_git` never consulted `out.returncode` and its except branch
  returned the empty string, `_staged_added` turned that into an empty mapping
  and `_check_staged` read the empty mapping as data. A clean tree with nothing
  staged and a directory where `git diff --cached` exits 129 were BYTE-IDENTICAL
  to the caller. No banned-glyph scan, no `py_compile`, no net-new `ruff` ran.
- artifact: `tools/precommit_gate.py`, `.githooks/pre-commit`
- ledgered: YES
- individuation: AMBIGUOUS - one event here under both conventions, but see
  EV-002 and EV-003, which the alternative convention folds into this one.

### EV-002
- citation: `72c7041`; L8
- claim: the winning CLOSED candidate argued that an unreadable corpus does not
  matter because "the commit is about to fail anyway".
- refutation: the adjudicator discarded that argument as FALSE - a stale `git -C`
  path left behind by a worktree agent yields an unreadable corpus while the real
  commit succeeds.
- artifact: `tools/precommit_gate.py` (the adjudicated decision behind it)
- ledgered: YES
- individuation: AMBIGUOUS - 1 under this convention, 0 additional under
  one-per-(artifact, root cause), which folds it into EV-001.

### EV-003
- citation: `72c7041`; L8
- claim: the fail-closed repair as drafted was safe at every call site of `_git`.
- refutation: the `rev-parse --show-toplevel` call site applied `.strip()` to the
  now-nullable return, so the fix would have raised AttributeError on EVERY
  developer commit - the hook passes the bare string `git commit` with no `-C`,
  which makes that permissive fall-through the live path rather than an edge.
  Corrected to `(_git(...) or "").strip()` by a secondary ruling.
- artifact: `tools/precommit_gate.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 under this convention; the alternative folds it
  into EV-001 as the same artifact.

### EV-004
- citation: `77408ad`; L10
- claim: deleting the single `# GATE:answered-usable` line reddens SIX arms, as
  recorded for `6c351b3`.
- refutation: the same deletion in a clean clone gives exit 1 with 43 failures
  against a same-clone baseline of exit 0 - wrong by roughly sevenfold. No
  artifact recorded WHICH six, so the figure was checkable against nothing, and
  `tools/gate_mutation_runner.py` mutates gate STATEMENTS with no CLI mode that
  drops a `# GATE:` comment, so it was never a tooled probe.
- artifact: the commit body of `6c351b3`; `tools/gate_mutation_runner.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; the alternative folds EV-004, EV-005 and
  EV-006 into one (artifact, root cause) pair, a probe that named no subjects.

### EV-005
- citation: `77408ad`; L10
- claim: the replaceable-record delivery count was "3 before and 1 after".
- refutation: all four parametrized arms of the replaceable self-heal test PASS
  against `6c351b3^`, so the pre-change bytes delivered 1. The 3 was measured
  against the dispatch brief's ordered-then-rejected fail-closed writer, which
  was never committed and exists nowhere in history - a number measured against
  an intention.
- artifact: the commit body of `6c351b3`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-004 by the alternative.

### EV-006
- citation: `77408ad`; L10
- claim: the first refutation's own arithmetic - 43 failed plus 45 passed, with
  the gap to the baseline unexplained.
- refutation: 43 plus 45 is 88 against a baseline of 89, and the missing case is
  in no result bucket because it was never COLLECTED. `_TAG_LINES` is derived at
  import from the responder's own source and the module parametrizes on it, so
  deleting a tag deletes a parametrize case. Error, skip, xfail and xpassed
  buckets measured empty; a restore control returned 89 passed at the original
  byte size. The kill is 43 of 88 collected, and 89 is not an arm count at all -
  it is 69 plus `len(_TAG_LINES)`.
- artifact: `tests/test_responder_gate_census.py`; the refuting pass's own report
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-004 by the alternative.

### EV-007
- citation: `f77c4ad`; `411ba14`; L2
- claim: `answered_usable` and `refusals_usable` each return the sentence "the
  record is readable and writable".
- refutation: each probes `exists`, `is_file`, the parent and `read_bytes` -
  four READS - and attempts no write. A record that is readable and permanently
  unwritable passed both gates; the seed is three lines, write valid JSON then
  `os.chmod(path, stat.S_IREAD)`. The consequence is unbounded: `_run_once` uses
  the answered gate to decide whether a reply it is about to deliver can be
  suppressed afterwards, so pass, deliver, fail to record, and the next cycle
  selects the same note - one new minute-stamped file per tick in a repository
  this one does not own.
- artifact: `tools/moon_sync_responder.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 under this convention (one assertion text, stated
  twice for two records); a per-SITE convention yields 2; one-per-(artifact,
  root cause) yields 1.

### EV-008
- citation: `f77c4ad`; L2
- claim: a tracked test docstring said every real structural route was stopped
  one level up, and that what remained was a race no arm could schedule.
- refutation: the readable-but-unwritable class is DETERMINISTIC and three lines
  to construct, so the arm could have been written against real bytes. The
  mislabel is what stopped the defect from being found.
- artifact: the responder degraded-write test docstring
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; the alternative folds it with EV-007 as one
  (artifact, root cause) pair.

### EV-009
- citation: `f77c4ad`; `390a831`; L7
- claim: `core/provenance.py` declares `sha256` and `parent_sha256` and validates
  them.
- refutation: the module contained no `hashlib` at all, so the only validation
  was a format regex - a shape arm pinning FORMAT and not INPUT. It now
  recomputes and compares, with the absent artefact as its own verdict and
  unverifiable digests excluded from the denominator.
- artifact: `core/provenance.py`
- ledgered: YES
- individuation: distinct.

### EV-010
- citation: `f77c4ad`; `390a831`; L7
- claim: the task-state-claims sweep reported zero findings, read as CLEAN.
- refutation: `scan_file` returned `[]` on OSError, so the sweep read clean over
  a tracked file it never opened. It now raises `UnreadableCorpusFile` naming the
  path and the raw errno, cause chained.
- artifact: `tests/test_task_state_claims.py`
- ledgered: YES
- individuation: distinct.

### EV-011
- citation: `f77c4ad`; L10
- claim: the git-shelling guards in this tree are armed and green.
- refutation: stripping every PATH entry holding a git executable turned a green
  probe reading over 7 modules into 8 RED arms, TWO of them anti-vacuity arms -
  so a guard written to stop a false GREEN converts into a false RED. The error
  is FileNotFoundError WinError 2 raised AT EXEC, which makes `check=True`
  irrelevant and kills the obvious wrong fix. The mirror direction works: 11
  skips appeared and two anti-vacuity arms skipped correctly, so the tree is
  partially armed rather than unarmed.
- artifact: `tests/test_no_sibling_names.py` (`_tracked_text_files`) and the six
  other probed modules
- ledgered: YES
- individuation: distinct.

### EV-012
- citation: `76ccdeb`; L10
- claim: a roadmap row filed hours earlier listed FIVE modules as carrying an
  `ls-files` corpus with no git guard.
- refutation: that list was the FILTER's population, not the REPAIR's. Only
  THREE of the five shell git at all. `tests/test_ci_history_depth.py` executes
  none - its only occurrence of the text `subprocess.run` is a string literal fed
  to a regex assertion. `tests/test_guard_worktree_blindness.py` has no
  subprocess call whatsoever. A skip added to either would be a FALSE SKIP with
  no defect behind it. Three is recorded as a FLOOR and not a count.
- artifact: `ROADMAP.md` row; `tests/test_ci_history_depth.py`;
  `tests/test_guard_worktree_blindness.py`
- ledgered: YES
- individuation: distinct.

### EV-013
- citation: `76ccdeb`; L10
- claim: the orchestrator's own diagnosis that the HOOK ENVIRONMENT caused a
  refused push reading 2 failed, 2148 passed, 2 skipped.
- refutation: refuted by counter-example - the same commit through a real
  pre-push hook into a scratch bare repository gave 2150 passed, 2 skipped in
  97.77s, exit 0. Interpreter, PATH, powershell resolvability, user, timeout and
  cwd were each ruled out individually. The cause is load: the Windows
  resource-exhaustion detector logged low-virtual-memory events naming a python
  process holding about 10.4 GB, and the refused run took 474.67s, spanning both.
- artifact: `.githooks/pre-push`; `tests/test_task_liveness.py`
- ledgered: YES
- individuation: distinct.

### EV-014
- citation: `76ccdeb`; L10
- claim: a push had landed, read off the exit status of a compound command.
- refutation: a compound command's exit status is only its LAST element, so a
  trailing `echo` reported 0 and made a REFUSED push look like it had landed.
  Related and separately measured: under Git Bash the shell status is 8-bit, so
  an exit of 4294901760 reads as 0 there and cannot be chased through a shell at
  all.
- artifact: the session's own shell invocations; recorded as a transferable trap
- ledgered: YES
- individuation: distinct.

### EV-015
- citation: L10
- claim: a hook had blocked a commit, read off output found at a shared path.
- refutation: `/tmp` under Git Bash is a directory inside the Git installation
  rather than anything on the C: drive root, and files there PERSIST ACROSS
  AGENTS, so a subagent's stale leftover read exactly like fresh output. The
  commit had never been attempted - a failed `python -c` had short-circuited the
  `&&` chain before it.
- artifact: the session's own shell invocations; recorded as a transferable trap
- ledgered: YES
- individuation: distinct.

### EV-016
- citation: `0d1fa70`; L9
- claim: `collect_facts` reported, for every non-zero return code, that the
  scheduler refused the query and may need a different account or TaskPath.
- refutation: false in every word for one measured class. PowerShell's
  ConsoleHost returns 4294901760, which is 0xFFFF0000 ExitCodeInitFailure, with
  empty stdout and a UTF-16LE stderr reading that loading managed Windows
  PowerShell failed with error 8009001d. The CLR never loaded and the script
  never ran, so nothing refused anything and no account or TaskPath is involved.
  The truth sat only in the detail string.
- artifact: `ops/check_task_liveness.py`
- ledgered: YES
- individuation: distinct.

### EV-017
- citation: `76ccdeb`; L10
- claim: two arms in the liveness suite report FAILED when the census machinery
  is broken.
- refutation: they collapse that fact with "PowerShell could not start on this
  machine just now". There is no retry and no distinct class for a host-start
  failure, so a PUSH-BLOCKING verdict became a function of free memory on the
  box. Measured: the ConsoleHost returned 0xFFFF0000 with empty stdout and the
  arm saw a FAILED status with an empty values list. What the arms get right is
  recorded with the defect - FAILED must fail and only NONE may skip; the missing
  DISTINCTION is the defect, not the strictness.
- artifact: `tests/test_task_liveness.py`
- ledgered: YES
- individuation: distinct.

### EV-018
- citation: `390a831`; L7
- claim: the false-red population reading of eight arms over seven modules.
- refutation: refuted AS A COUNT. It came from a name-based one-term filter. The
  AST enumeration answers GIT 37, NOT-GIT 20, UNRESOLVED 16, total 73 sites over
  104 modules, 26 files holding at least one GIT site.
- artifact: `ROADMAP.md` row; `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-019
- citation: `390a831`; L7
- claim: the docs-hook-commands sweep answered its containment questions
  correctly.
- refutation: `_tokens` returned `[]` when `shlex` raised ValueError, and every
  caller asks whether the token list CONTAINS something, so zero tokens made
  every question answer NO. It now raises `UnparseableCommand`, caught at the one
  call site that must continue sweeping, where the unparseable span is REPORTED
  rather than skipped.
- artifact: `tests/test_docs_hook_commands.py`
- ledgered: YES
- individuation: distinct.

### EV-020
- citation: `390a831`; L7
- claim: a roadmap row named three modules as the sites to arm with the
  skip-then-RUN pair.
- refutation: all three shell git and NONE of them carries a gate, so under an
  unreachable git they FAIL rather than skip - measured per module. Arming them
  as briefed would have shipped a permanently red test. The arm covers the two
  sites that do gate at the site instead.
- artifact: `ROADMAP.md` row; `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct.

### EV-021
- citation: `390a831` (disclosed); `1c8aab2` (repaired); L7
- claim: the provenance digest arms grade the digest comparison.
- refutation: the decoy generator advanced CHARACTER INDEX 0 ONLY, and every
  wrong-digest arm derived from that one generator, so an implementation
  comparing `computed[:1]` - one character of sixty-four - passed all 71 arms and
  the whole suite while grading a digest that differs at its last character as
  MATCH. Repaired with a decoy FAMILY, and the mutant now kills three members.
- artifact: `tests/test_provenance.py`
- ledgered: YES
- individuation: distinct.

### EV-022
- citation: `390a831`; `1c8aab2`; L7
- claim: the `in_scope` widening for unparseable spans is load-bearing and
  covered.
- refutation: reverting `in_scope` to its pre-repair form left 20 passed and the
  whole suite green, because both new fixtures spelled a long flag and the
  unparseable-reason term was never the reason any arm passed.
- artifact: `tests/test_docs_hook_commands.py`
- ledgered: YES
- individuation: distinct.

### EV-023
- citation: `390a831`; `1c8aab2`; L7
- claim: the git-gate site table's arms grade the table.
- refutation: emptying the site table - the module's entire subject - left the
  module GREEN, because an empty parametrize is one skipped and exit 0. A floor
  and a two-shapes-by-label assertion were added.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct.

### EV-024
- citation: `390a831`; `1c8aab2`; L7
- claim: the census enumerates every subprocess launch site in its roots.
- refutation: its scope walk recursed into node BODIES only, so a subprocess call
  in a decorator, in a default argument, in an annotation or in a class base
  produced NO ROW in any bucket. The walk now derives the non-body positions by
  SUBTRACTION from the child nodes.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-025
- citation: `1c8aab2`; L7
- claim: the census buckets each launch site by its executable.
- refutation: a `shell=True` list head was read as an executable path and
  bucketed NOT-GIT. The shell flag is now tri-state and a disagreement between
  the two readings is UNRESOLVED rather than a guess.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-026
- citation: `390a831`; `1c8aab2`; L7
- claim: the census's UNRESOLVED bucket is pinned by its arms.
- refutation: the unresolved fallback could be flipped to NOT-GIT with all 33
  arms still passing, which would have silently reclassified the most ordinary
  dynamic git argv[0] in Python.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-027
- citation: `7bda8cd`; `7786955`; L6
- claim: the roadmap row's population of ungated git-shelling modules was THREE.
- refutation: it was FIVE, and the two extra were found by an adversary mutating
  the site table rather than by the row's own reasoning. Five modules gained a
  gate.
- artifact: `ROADMAP.md` row; `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct. Note this is the OPPOSITE direction from EV-012, over
  a different population; neither withdraws the other.

### EV-028
- citation: `86491a3`; `7bda8cd`; L6
- claim: `tests/test_hook_gate.py` asserted that `.githooks/pre-push` exports no
  `GIT_DIR`.
- refutation: configuration-scoped and false as written. Verified on git
  2.53.0.windows.3 with every returncode read in Python: a push from the MAIN
  CHECKOUT exports none, a push from a LINKED WORKTREE exports
  `GIT_DIR=<main>/.git/worktrees/<name>`, and this machine carried 52 worktree
  entries while the hook runs both suites. With it exported, `pytest tests`
  returned rc 2 "Interrupted: 1 error during collection" while
  `agents/pity_engine` collected 80 and carried on - loud on one lane and silent
  on the other.
- artifact: `tests/test_hook_gate.py`; `conftest.py`; `.githooks/pre-push`
- ledgered: YES
- individuation: distinct.

### EV-029
- citation: `86491a3`; L6
- claim: `docs/LEDGER.md` recorded a third configuration for the same `GIT_DIR`
  question.
- refutation: that configuration is wrong and was corrected in place; the
  correct reading is the two-row main-checkout versus linked-worktree table.
- artifact: `docs/LEDGER.md`
- ledgered: YES
- individuation: distinct.

### EV-030
- citation: `7bda8cd`; L6
- claim: a counterparty independently reproduced our three day-log figures, which
  corroborates them.
- refutation: AGREEMENT BY LUCK rather than corroboration. Their tracer patched
  `builtins.open` alone and therefore never saw `Path.write_text`, while ours
  patched `io.open` from the start. The shared premise - that
  `logging.FileHandler` opens through `builtins.open` and never touches `pathlib`
  - is what the matching numbers are evidence about.
- artifact: `docs/LEDGER.md`; `tests/test_suite_writes_no_live_logs.py`
- ledgered: YES
- individuation: distinct.

### EV-031
- citation: `86491a3`; `7bda8cd`; L6
- claim: the 1922-byte gap between what the tracer saw and what reached disk was
  child-process logging.
- refutation: 89 of those bytes are CRLF translation, measured as a rate against
  a control. The remaining 1833 are recorded as UNAPPORTIONED with child
  processes named as a candidate rather than as an attribution.
- artifact: `tests/test_suite_writes_no_live_logs.py`
- ledgered: YES
- individuation: distinct.

### EV-032
- citation: `7786955`; L6
- claim: the publish gate's credential rule at HEAD catches the credential
  classes it names.
- refutation: Rule 1 leaked the Slack `xoxa-`, `xoxr-` and `xoxs-` classes
  straight through the real publish path in `tools/publish_next_session.py`.
- artifact: `tools/publish_next_session.py`;
  `tests/test_no_secret_literals.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds
  EV-032, EV-033 and EV-034 into a single boundary-rule event.

### EV-033
- citation: `7786955`; L6
- claim: Rule 2, a contiguous run after a bounded lead-in, closed the leak.
- refutation: it closed those three flat shapes and OPENED 30 segmented ones
  including `xoxb-`, which had never leaked at all. The cliff was the lead-in
  bound, and a credential with a fully intact 24-character body was missed
  because its identifier segments were two characters too long.
- artifact: `tools/publish_next_session.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-032 by the alternative.

### EV-034
- citation: `7786955`; L6
- claim: Rule 3, a left boundary of A-Za-z0-9 and underscore, closed the leak.
- refutation: it silently gave up EVERY credential whose preceding character is
  a word character, demonstrated against the real publish path with a synthetic
  24-A body embedded in a path - a REGRESSION against HEAD's own publisher rather
  than a missed improvement. Rule 4 derives the boundary from a census of the
  false positives instead: all nine are preceded by a letter while the break set
  is preceded by an underscore or a digit, so a letters-only lookbehind separates
  them exactly, pinned by walking all 128 ASCII codepoints.
- artifact: `tools/publish_next_session.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-032 by the alternative.

### EV-035
- citation: `7786955`; L6
- claim: the name-binding detector examines secret-name bindings.
- refutation: one optional double quote and a single colon-or-equals meant a
  backticked, bolded, tabled or single-quoted name was NEVER EXAMINED AT ALL, and
  the sweep restated the identical shape, so there was no second line of defence
  behind it. Pre-existing at HEAD rather than introduced. The separator class is
  now derived by subtraction over the 128 codepoints with a mandatory operator.
- artifact: `tools/publish_next_session.py`;
  `tests/test_no_secret_literals.py`
- ledgered: YES
- individuation: distinct.

### EV-036
- citation: `7786955`; L6
- claim: the git-gate site table's conservation arm catches a dropped site.
- refutation: a one-edit mutant left it green, so the conservation was extended
  from ROWS to NODES.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct.

### EV-037
- citation: `7786955`; L6
- claim: the site table's own matcher resolves the launched argv at each site.
- refutation: a Name-bound argv defeated it, and the matcher was replaced
  outright by the census resolver this tree already ships in
  `tools/git_subprocess_census.py`.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-037
  and EV-038 into one matcher event.

### EV-038
- citation: `7786955`; L6
- claim: the replaced matcher resolves the launched argv at each site.
- refutation: a SPLATTED argv defeated it again.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-037 by the alternative.

### EV-039
- citation: `7786955`; L6
- claim: the exempt-arm audit attributes every launch in the file.
- refutation: rebuilt a third time, because a launch inside a DECORATOR proved
  UNATTRIBUTABLE BY CONSTRUCTION - the census counted the site and both halves of
  the audit dropped it.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct.

### EV-040
- citation: `7786955`; L6
- claim: the census guard column was cited as evidence that a module is GATED.
- refutation: the census guard column is a MODULE-LEVEL walk that would have
  answered GATED with every gate in the file DELETED, so it cannot carry that
  citation. The adjudicated exemption's citation was re-derived rather than
  carried forward. Related shapes recorded and not fixed: a gate placed after a
  launch, under `if False`, or in an uncalled nested def also reads as named.
- artifact: `tools/git_subprocess_census.py`;
  `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: distinct.

### EV-041
- citation: `5d785f5`; `7bda8cd`; L6
- claim: an open roadmap row asserted that `ops/install_responder_task.ps1` lacks
  an unsubstituted-placeholder throw.
- refutation: FALSE and retired. That script has carried the guard since
  `1d80f8c` on 2026-09-07, four days BEFORE the row was filed, and it FIRES -
  proven by running the real script with `-WhatIfOnly` against a scratchpad
  mirror install root, returncode read in Python: control 0, planted
  `__NEW_TOKEN__` 1. It dominates both downstream exits and the `-Remove` branch
  exits before the XML path is built.
- artifact: `ROADMAP.md` row; `ops/install_responder_task.ps1`
- ledgered: YES
- individuation: distinct.

### EV-042
- citation: `5d785f5`; L6
- claim: both installer placeholder guards match `__[A-Z_]+__`, i.e. they catch
  unsubstituted placeholders.
- refutation: PowerShell `-match` is case-INSENSITIVE - `-cmatch` is the
  case-sensitive operator - so the class behaved as `__[A-Za-z_]+__` at runtime
  and lowercase never leaked. Only the DIGIT axis leaked, and it leaked
  regardless of case: planted `__Slot1__` and `__SLOT1__` both returned 0 in both
  scripts, while `__pythonw_exe__` and `__PyThonW__` both returned 1. The class
  is now written out as `__[A-Za-z0-9_]+__` rather than using `\w`, because .NET
  `\w` is Unicode-aware.
- artifact: `ops/install_responder_task.ps1`; `ops/install_scheduled_task.ps1`
- ledgered: YES
- individuation: distinct.

### EV-043
- citation: `5d785f5`; L6
- claim: the responder installer's guard polices the whole substituted template.
- refutation: the UTF-16 declaration relabel ran BEFORE the guard, so a token
  inside the declaration was MASKED from it - `encoding="__ENC_TOKEN__"` returned
  0 in the responder and 1 in the supervisor, while a token just after the
  declaration returned 1 in both. Fixed by reordering to substitute, guard, then
  relabel.
- artifact: `ops/install_responder_task.ps1`
- ledgered: YES
- individuation: distinct.

### EV-044
- citation: `86491a3`; L6
- claim: the inherited figure of 39 corpus sites with TWO existing scrubs.
- refutation: an AST pass over the 141 tracked `.py` files finds 41 corpus sites
  with exactly ONE real scrub. One of the two claimed scrubs does not scrub:
  `_measure_baseline` in `tests/test_line_endings.py` matches only because a
  COMMENT mentions `GIT_DIR`, and its `_launch_git` passes no env at all.
- artifact: `tests/test_line_endings.py`; the inherited dispatch figure
- ledgered: YES
- individuation: distinct.

### EV-045
- citation: `78cdf96`; L6
- claim: the nine-variable environment scrub shipped at `86491a3` covers the
  repo-local git variables.
- refutation: `git rev-parse --local-env-vars` is git's OWN list and returns
  FIFTEEN names on git 2.53.0.windows.3. The scrub covered FIVE. Seven were never
  considered anywhere in `conftest.py` or its arm, and `GIT_CONFIG_PARAMETERS` is
  EXPORTED TO HOOKS BY GIT ITSELF - reproduced end to end, the tree's own guard
  reddens at rc 1 without it and returns to rc 0 with it inherited, while nothing
  anywhere reddened and `tests/test_git_env_scrub.py` was 17 of 17 green in
  exactly that state.
- artifact: `conftest.py`; `tests/test_git_env_scrub.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-045
  and EV-046 into one event.

### EV-046
- citation: `78cdf96`; L6
- claim: the selection criterion for the scrub set - keep a variable only if it
  changes git's answer AND at rc 0.
- refutation: the criterion was the real defect. For `git check-ignore -q` THE
  RETURNCODE IS THE ANSWER - 0 ignored, 1 not - and `tests/test_agent_roster.py`
  literally returns `completed.returncode == 0` as its corpus, so an rc-0-only
  filter is STRUCTURALLY BLIND to that whole family. The corrected criterion
  ships in `conftest.py`: an answer is the PAIR of returncode and stdout.
- artifact: `conftest.py`; `tests/test_agent_roster.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-045 by the alternative.

### EV-047
- citation: `78cdf96`
- claim: a tracked justification in `conftest.py` said `GIT_CONFIG_GLOBAL` and
  `GIT_CONFIG_SYSTEM` "changed NO probe".
- refutation: value-dependent and wrong - pointed at a config carrying
  `core.excludesFile`, each took `check-ignore -v --stdin` from 39 to 200 bytes
  at rc 0. The DECISION to keep them stands on a restated ground.
- artifact: `conftest.py`
- ledgered: NO
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-047
  and EV-048 into one event.

### EV-048
- citation: `78cdf96`
- claim: the second clause of that same justification - that scrubbing those two
  would have risked the `tests/test_hook_gate.py` fixture.
- refutation: wrong too. `tests/test_hook_gate.py` builds its child environment
  by dropping every `GIT_`-prefixed name and then setting those two explicitly,
  so scrubbing could never have risked that fixture.
- artifact: `conftest.py`; `tests/test_hook_gate.py`
- ledgered: NO
- individuation: AMBIGUOUS - 1 here, folded into EV-047 by the alternative.

### EV-049
- citation: `78cdf96`
- claim: the report that found the scrub gap enumerated the uncovered variables.
- refutation: it missed `GIT_NO_REPLACE_OBJECTS` and `GIT_REPLACE_REF_BASE`,
  which are also in git's own `--local-env-vars` list and were also never
  considered in `conftest.py` or its arm.
- artifact: the refuting report; `conftest.py`
- ledgered: NO
- individuation: distinct.

### EV-050
- citation: `78cdf96`
- claim: the existing probe rows were the right population for deciding the
  scrub set.
- refutation: re-derived from `tools/git_subprocess_census.py` rather than from
  taste - `ls-tree` has ZERO call sites in this tree and two of the old probe
  rows tested it, while `rev-parse`, which IS the git gate itself at
  `tests/conftest.py::git_unusable_reason`, was never probed at all.
- artifact: `conftest.py`; `tests/test_git_env_scrub.py`
- ledgered: NO
- individuation: distinct.

### EV-051
- citation: `2ae95f3`; L5
- claim: the census emits a row in one of its buckets for every call it walks.
- refutation: `_launcher_name` branched on `ast.Attribute` and `ast.Name` only,
  so a call whose `func` is itself a `Call`, a `Subscript` or a `BoolOp` produced
  NO ROW AT ALL - silence, not a wrong bucket, which a conservation assertion
  cannot catch because there is nothing to conserve. Seven such nodes exist over
  `DEFAULT_ROOTS`; the census moves 78 {GIT 38, NOT-GIT 22, UNRESOLVED 18} to 85
  {38, 22, 25}, with every new row opaque. Repaired subtractively.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-052
- citation: `2ae95f3`; L5
- claim: `test_every_os_launcher_in_the_table_is_reachable` grades the
  os-launcher table's per-launcher executable position.
- refutation: it built its `filler` FROM `spec.exec_index`, so THE FIXTURE MOVED
  WITH THE MUTANT. Two agents sampled independently: 6 of 10 position mutants
  survived for one, 16 of 19 for the other.
- artifact: `tools/git_subprocess_census.py`;
  `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-052
  and EV-053 into one event.

### EV-053
- citation: `2ae95f3`; L5
- claim: the same table's arms pin its launcher spelling set.
- refutation: shrinking `_LAUNCHER_SPELLINGS` from 24 names to TWO survived at
  108 passed rc 0.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-052 by the alternative.

### EV-054
- citation: `2ae95f3`; L5
- claim: the Attribute-receiver rule for `get_runner().run(...)` earns its place
  in the census.
- refutation: it found ZERO launcher-spelled receivers among 980 candidates. Both
  widenings were adjudicated OUT and deleted; the case is now a PINNED SILENCE
  whose spelling set is written as a literal in the test so that arm cannot move
  with a mutant either.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-055
- citation: `2ae95f3`; L5
- claim: the widened module title claimed the census covers "every process
  launch".
- refutation: `subprocess.getoutput` and `getstatusoutput` launch a process and
  are absent from `LAUNCHERS` - `census_source` on such a call returns `[]`. The
  title is reverted and the gap is a DECLARED blind spot rather than an implied
  completeness.
- artifact: `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-055
  and EV-056 into one contract-honesty event.

### EV-056
- citation: `2ae95f3`
- claim: `format_report` printed "total launch sites", and both `CallSite` and
  `census_source` docstrings said "launch".
- refutation: the population includes rows the module's own docstring says launch
  nothing, so the report was calling non-launches launches. The noun is now
  bucket-neutral, with an arm feeding an opaque fixture and asserting the word
  does not appear over it.
- artifact: `tools/git_subprocess_census.py`
- ledgered: NO
- individuation: AMBIGUOUS - 1 here, folded into EV-055 by the alternative.

### EV-057
- citation: `2ae95f3`; L5
- claim: `tests/test_conftest_git_gate_sites.py` said "five armed modules" and
  "every one of the five rows".
- refutation: `len(_SITES)` is 6. Already wrong before the slice that exposed it.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds
  EV-057, EV-058 and EV-059 into one event for this file.

### EV-058
- citation: `2ae95f3`; L5
- claim: the same file said "four derive nothing".
- refutation: it is five.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-057 by the alternative.

### EV-059
- citation: `2ae95f3`; L5
- claim: the same file said `tests/test_line_endings.py` was the ONLY module
  reading differently under the two bucket sets.
- refutation: FALSE WHEN WRITTEN - three did at the old census and five do now,
  at 14 open against 22 closed.
- artifact: `tests/test_conftest_git_gate_sites.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-057 by the alternative.

### EV-060
- citation: `2ae95f3`; L5
- claim: `conftest.py` and `tests/test_git_env_scrub.py` both quoted 78 launch
  sites.
- refutation: the census answers 85 after the silent-callee repair. The 28-of-38
  subcommand split in those same comments was deliberately LEFT, because GIT
  stayed at 38 and every new row is UNRESOLVED, so that split cannot have moved.
- artifact: `conftest.py`; `tests/test_git_env_scrub.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) yields 2,
  one per file.

### EV-061
- citation: `2ae95f3`; L5
- claim: the suite stayed green across the census change, read as evidence that
  the `_GIT_BUCKETS` fail-closed fold is correct.
- refutation: A GREEN SUITE IS NOT EVIDENCE FOR A FAIL-CLOSED FOLD.
  `_GIT_BUCKETS` is evaluated only over the six armed modules, every one of which
  reports zero unresolved sites under both the old census and the new, so the
  fold is VACUOUS on the real tree in both states and the suite could not have
  gone red whatever the seven new rows were. Green was silence.
- artifact: `tests/test_conftest_git_gate_sites.py`;
  `tools/git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-062
- citation: `2ae95f3`; L5
- claim: an adjudicator finding cited `_HARNESS_AXES` in
  `tests/test_task_liveness.py` as a rival tracked launcher list containing
  `getoutput`, implying a live disagreement between two censuses.
- refutation: OVERSTATED, and corrected before it reached code. That tuple lists
  subprocess module ATTRIBUTES a test shim must expose and also holds
  `CalledProcessError`, `DEVNULL`, `PIPE` and `__name__`. The `getoutput` gap is
  real and was measured directly; the tuple is not evidence for it.
- artifact: `tests/test_task_liveness.py`; the adjudicator's report
- ledgered: YES
- individuation: distinct.

### EV-063
- citation: `2ae95f3`; L5
- claim: our 1910 outbound note told LW that both delivered files were
  machine-identity clean.
- refutation: FALSE and withdrawn. `lw_write_tracer.py.from-lw` line 206 carries
  the operator's account name in its bare 8.3 short form with no users-segment
  prefix, while `ABSOLUTE_USER_PATH` in `tests/test_machine_identity.py` requires
  that prefix - measured with a control, bare form False and full form True. The
  consequence is a hole in THIS tree's detector, and the matcher is deliberately
  NOT widened.
- artifact: the 1910 outbound note; `tests/test_machine_identity.py`
- ledgered: YES
- individuation: distinct.

### EV-064
- citation: `2ae95f3`; L5
- claim: this tree's own recorded trap blamed a `/tmp` redirect for the
  machine-wide scratch litter.
- refutation: too narrow. `$TMPDIR` is UNSET in the Bash tool as it runs here, so
  `"$TMPDIR/probe.py"` expands to `/probe.py` and MSYS maps the leading slash to
  the git installation root. The trigger is ANY unset-variable expansion leaving
  a leading slash. `C:\Program Files\Git` holds 347 non-distribution files and
  6,000,070 bytes.
- artifact: the recorded trap; `C:\Program Files\Git` (outside the repo root)
- ledgered: YES
- individuation: distinct.

### EV-065
- citation: `13c771f`; `7bda8cd`; L4
- claim: the two ad-hoc write tracers used on 2026-09-11 measured what was
  written, and their negative readings stand.
- refutation: both were measured BLIND in ways that made their negative readings
  worthless - neither saw the `os.open` plus `os.fdopen` route, because the
  descriptor is an int and no path ever matches, and neither patched deletion or
  truncation at all. Neither was ever a tracked artifact.
- artifact: the two untracked ad-hoc tracers; `tools/write_tracer.py`
- ledgered: YES
- individuation: distinct.

### EV-066
- citation: `13c771f`; L4
- claim: `tools/write_tracer.py` covers the write routes it names, and declares
  the ones it does not.
- refutation: EMPTY-FILE CREATION WAS INVISIBLE AND DECLARED NOWHERE - in
  neither list, so a reader had no way to discover it. That is the live shape at
  `ops/loop/slots.py:189`, lock-file creation in the machine-wide bucket the halt
  ruling names, so a "0 bytes written" reading over that bucket would have come
  back CLEAN while the lock files appeared on disk. A fourth op, `create`, was
  added with an arm driving the real syscall shape.
- artifact: `tools/write_tracer.py`; `docs/adr/ADR-010-write-tracer-coverage.md`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-066
  and EV-067 into one silent-route event.

### EV-067
- citation: `13c771f`; L4
- claim: the same partition of covered against declared-uncovered routes.
- refutation: six further routes sat in NEITHER list - `os.ftruncate`, `os.link`,
  `os.symlink`, `Path.touch`, `open(mode="x")` and the `shutil` copy family. The
  copy family is now covered BY NAME rather than transitively, because
  `shutil.copy2` on this platform takes a native fast path and decomposes into
  nothing observable. `io.FileIO`, metadata-only and directory-level operations
  are DECLARED instead. Every route now sits in exactly one list.
- artifact: `tools/write_tracer.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-066 by the alternative.

### EV-068
- citation: `13c771f`; L4
- claim: a descriptor opened before entry loses only path attribution, with the
  bytes still recorded.
- refutation: true for the raw `os.write(fd, data)` form and FALSE for a file
  object opened before entry - that object's `write` reaches the C-level writer
  with no wrapped name anywhere on the path, so NOTHING is recorded. Measured on
  CPython 3.14.4 and 3.11.9 with `open(p, "wb", buffering=0)` before the context
  and one 9-byte write inside it: 9 bytes on disk, ZERO events. The two sub-cases
  are now separate entries which the ADR says must not be refolded.
- artifact: `tools/write_tracer.py`; `docs/adr/ADR-010-write-tracer-coverage.md`
- ledgered: YES
- individuation: distinct.

### EV-069
- citation: `13c771f`; L4
- claim: the tracer's path attribution is either right or absent.
- refutation: `os.dup2` emitted a POSITIVELY WRONG PATH from a stale descriptor
  entry, naming one file while the bytes landed in another. A wrong path is worse
  than no path, because no path is visibly a gap and a wrong path reads as a
  finding. The unknown-source case now evicts and reports
  `<unattributed fd N>`.
- artifact: `tools/write_tracer.py`
- ledgered: YES
- individuation: distinct.

### EV-070
- citation: `13c771f`; L4
- claim: the write tracer's honesty arm pins the declared coverage list.
- refutation: it was ONE-SIDED and could only fail in one direction - adding a
  name that was not patched went RED, removing a name that WAS patched stayed
  GREEN, which is exactly the direction an overstatement travels in. The arm now
  derives the patched set from the implementation and asserts equality both ways.
- artifact: `tests/test_write_tracer.py`
- ledgered: YES
- individuation: distinct.

### EV-071
- citation: `13c771f`; L4
- claim: `docs/adr/ADR-010-write-tracer-coverage.md` and `tools/write_tracer.py`
  describe one mechanism consistently.
- refutation: TWO DRIFTS between the two documents were found at the seam rather
  than shipped, and they were found only because the ADR author never saw the
  module.
- artifact: `docs/adr/ADR-010-write-tracer-coverage.md`; `tools/write_tracer.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; a strict per-assertion reading of the two
  named drifts yields 2; one-per-(artifact, root cause) yields 1. The record does
  not name the two drifts individually, so this row is a floor.

### EV-072
- citation: `13c771f`; `d6437a9`; L4
- claim: this tree told the cross-repo channel on 2026-09-08 that it "cannot
  check your start/deliver finding here, having no tagged gates".
- refutation: true when written and DECAYED the next day.
  `tools/moon_sync_responder.py` carries 20 `# GATE:` tags between lines 1928 and
  2169, with the grammar pinned by `tests/test_gate_name_bindings.py`. The claim
  is withdrawn and the counterparty question resting on it is re-asked rather
  than answered as written. No tracked file asserted the premise, so nothing went
  red, which is the point: a prose premise decays silently and takes a later
  question's foundation with it.
- artifact: the 2026-09-08 outbound note; `tools/moon_sync_responder.py`
- ledgered: YES
- individuation: distinct.

### EV-073
- citation: `d6437a9`
- claim: the census roadmap row was ready to close.
- refutation: only its FIRST HALF was done - the no-site-emitted class was
  repaired at `2ae95f3` - while its second half is LIVE, because the census
  launcher set is still subprocess-only and `os.system` stays invisible for an
  independent reason. Closing the row on the repaired half would have silently
  retired a defect nobody had fixed.
- artifact: `ROADMAP.md` row
- ledgered: NO
- individuation: distinct.

### EV-074
- citation: `c514ca7`; L3
- claim: the out-of-scope launcher honesty arm pins the 22 declared names.
- refutation: IT RAN ONE WAY. Removal was pinned for 5 of 22 and only because a
  hand fixture happened to spell those five: dropping `spawnve` alone stayed
  GREEN at 77 passed, and dropping all 17 non-fixture names in ONE edit also
  stayed GREEN, so 17 of 22 were decoration. Addition was pinned by a single
  string literal - adding `abort`, a real `os` attribute the docstring never
  declares, stayed GREEN. Three pins now hold it.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-075
- citation: `c514ca7`; L3
- claim: the new out-of-scope sweep grades the census over the launch shapes it
  walks.
- refutation: THE GRADER WAS WEAKER THAN THE MODULE IT GRADES, on the one shape
  that module was repaired for at `2ae95f3`. `census_source` returns
  `CallSite(bucket='UNRESOLVED', callee='<unresolved:Call>')` for
  `getattr(os, "system")(...)` while the sweep returned NOTHING. Seventeen shapes
  were measured GREEN against the sweep while genuinely launching a process or
  naming a real launch API. All 17 are now declared and pinned as SILENCES.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-076
- citation: `c514ca7`; L3
- claim: the arm's assertion message said an `Attribute` on a DOTTED `Name`
  receiver was counted.
- refutation: it names a population the sweep does not walk.
  `shim.os.system(...)` and `os.path.system(...)` both yielded no offenders, and
  collapsing the nine-line dotted resolver to the `Name`-only form killed NO test
  - it was BEHAVIOUR-DEAD, because the receiver map is keyed on single-segment
  module names only. The dead logic is deleted and the message now says a plain
  single-segment `Name` receiver.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-077
- citation: `c514ca7`; L3
- claim: `tests/test_gate_mutation_runner.py` said
  `tests/test_gate_name_bindings.py` "binds each of the 18 `# GATE:` tags".
- refutation: it is 20. Measured over one tracked file,
  `tools/moon_sync_responder.py`, with the per-line byte-level pattern
  `#\s*GATE:([A-Za-z0-9_.-]+)`: 20 hits, 20 distinct tags, lines 1928 to 2169,
  and `_FLOOR` is 20 in both judging tables.
- artifact: `tests/test_gate_mutation_runner.py`
- ledgered: YES
- individuation: distinct.

### EV-078
- citation: `f03bbed`
- claim: `c514ca7`'s own commit message stated the gate-tag population.
- refutation: imprecise on that point. The 20 tags are 20 hits and 20 distinct in
  `tools/moon_sync_responder.py` ALONE; the same pattern over the whole
  `git ls-files` corpus answers 67 hits and 39 distinct across 8 files. Quote the
  single-file population or quote the corpus, never the corpus count as the
  production figure.
- artifact: the commit body of `c514ca7`
- ledgered: NO
- individuation: distinct.

### EV-079
- citation: `038fd4a`
- claim: `test_no_invisible_receiver_in_this_tree_is_spelled_like_a_launcher`
  grades which receivers the census cannot resolve.
- refutation: it decides that by calling `census._dotted` - the module under test
  - and its only coupling guard is `assert seen > 100`, which goes red if
  `_dotted` is GUTTED and stays GREEN if `_dotted` grows a NARROWER blind spot,
  because a narrowing makes more receivers look unresolvable so `seen` RISES and
  the threshold is satisfied harder. Proved by mutation: `_dotted` returning None
  for any chain deeper than two segments reddened the new independent arm with
  850 disagreements while `seen > 100` stayed GREEN on the same bytes.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: NO
- individuation: distinct.

### EV-080
- citation: `14017bd`; `6216a82`; L2
- claim: `411ba14` closed the readable-but-unwritable class by adding
  `_writable_in_place(path)`.
- refutation: it fixed the WRONG OBJECT. Every state write here goes through
  `core/atomic_io.atomic_write_text`, whose `_temp_path` returns a SIBLING of the
  target in the PARENT DIRECTORY, so the right exercised is CREATE A FILE IN THIS
  DIRECTORY. Measured with the record's parent denied `(WD,AD)` via `icacls`: an
  absent record gave `answered_usable -> (True, ...)` and
  `refusals_usable -> (True, ...)` with `_remember_answered -> False`, and a
  PRESENT and itself-writable record in that same directory gave the same. The
  absent half could not be reached by the first repair at all, because the call
  was gated on `path.is_file()` - so the COLD START, the state every first run is
  in, was never probed.
- artifact: `tools/moon_sync_responder.py`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here (one assertion, that the class was closed,
  refuted by two measured halves); a per-measured-half reading yields 2;
  one-per-(artifact, root cause) yields 1.

### EV-081
- citation: `14017bd`; L2
- claim: `_ensure_dir`'s own sentence says the directory "will be written into",
  and it returns True after a `mkdir`.
- refutation: `mkdir(exist_ok=True)` on an EXISTING directory attempts nothing,
  so it returned success for a directory that refuses every file. All six call
  sites - rotation, metrics, invocation log, both records, `_remember_refusal`'s
  record and the held-file directory - create a FILE inside immediately
  afterwards and read the bool as permission to do so. Not one caller merely
  wants the directory to exist. The verdict was taken by enumerating callers
  rather than by reading the docstring.
- artifact: `tools/moon_sync_responder.py`
- ledgered: YES
- individuation: distinct.

### EV-082
- citation: `14017bd`; L2
- claim: `411ba14`'s non-vacuity arm asserted that an ABSENT record implies
  usable.
- refutation: it ENCODED THE DEFECT - an unqualified claim about the RECORD, when
  the deciding object is the DIRECTORY. Kept rather than deleted, because it is
  still the half that stops an unconditional False from passing, and narrowed:
  the bed now proves the directory accepts a file before the absent record is
  called usable, with two litter assertions.
- artifact: `tests/test_moon_sync_responder.py`
- ledgered: YES
- individuation: distinct.

### EV-083
- citation: `ffb8f7c`; `bb704a5`; L1
- claim: the suite pins `classify_git_probe()`'s detail chain,
  `stderr.strip() or stdout.strip() or "no output"`.
- refutation: the STRIP of the stream the chain CHOOSES was asserted by nothing,
  because every fixture in the tree fed that chain a stderr that was already
  clean or blank. Measured: applying
  `detail = stderr if stderr.strip() else (stdout.strip() or "no output")` left
  `python -m pytest tests` entirely green at exit 0 with 2700 passed and the
  pycache purged on both sides. That mutant puts git's own trailing newline
  inside a reason handed to `pytest.skip()`, splitting the one-line short summary
  a reader scans.
- artifact: `tests/conftest.py`; `tests/test_conftest_reason_fixture.py`
- ledgered: YES
- individuation: distinct.

### EV-084
- citation: `c145f8a`; `7987aee`; L1
- claim: the agreement arm added at `038fd4a` re-derives dotted receiver names
  independently of the module it grades.
- refutation: it re-derived through `ast.unparse` plus the character class
  `[A-Za-z_][A-Za-z0-9_]*`, and Python identifiers are NOT ASCII. Over every
  receiver named with a non-ASCII letter that half answered None while
  `census._dotted` correctly answered the name, so the grader was STRICTLY WEAKER
  than the module it grades over exactly that class and the arm's polarity
  INVERTED there. Reproduced against a two-line probe file whose receiver carried
  one non-ASCII letter: correct `_dotted` plus probe gave RED with 3
  disagreements, and an `isascii` narrowing gave GREEN - the narrowing was
  rewarded with a pass. The fix asks Python what an identifier is,
  `str.isidentifier` per segment.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-085
- citation: `c145f8a`; L1
- claim: the census sweep's population floors of 5000 / 1000 / 500 catch a
  collapsed corpus.
- refutation: they carried 14.3x, 68.8x and 5.0x headroom against measured 71347
  / 68845 / 2502 and let FOUR OF THE FIVE corpus roots be dropped while staying
  green. Raised to 39000 / 37000 / 1300, about 55 percent of measured, so all
  three now bind on the loss of the dominant root.
- artifact: `tests/test_git_subprocess_census.py`
- ledgered: YES
- individuation: distinct.

### EV-086
- citation: `152f61e`; `6216a82`; L2
- claim: the in-code sentence said the directory probe file "is removed in a
  `finally` on every exit".
- refutation: FALSE. A `finally` does not run under `taskkill /F`, this repo's
  own sanctioned kill - a process spawned holding an open probe was killed,
  `taskkill //F //PID 33784` reported SUCCESS, and
  `.rsc-responder-dirprobe.33784.deadbeef.tmp` was still there. The worse leak
  needed no kill: the `finally` swallowed with `except OSError: pass`, so a
  Windows PermissionError from a concurrent open handle on a just-created file -
  the ORDINARY case - left the file AND returned True, so a directory that would
  not release its own probe was reported HEALTHY. A failed removal is now the
  verdict. Related and recorded in the same ledger table: there was NO REAPER
  ANYWHERE, the files land under `ops/runtime/` gitignored at `.gitignore:31`, so
  no tracked guard could see them - one file per kill, unbounded.
- artifact: `tools/moon_sync_responder.py`; `docs/LEDGER.md`
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; the ledger presents the removal and the
  litter as two rows of a three-row table, so a per-ledger-row reading yields 2;
  one-per-(artifact, root cause) yields 1.

### EV-087
- citation: `152f61e`; `6216a82`; L2
- claim: the same in-code sentence said the probe "carries a name no reader in
  this module can select", with a proof.
- refutation: THE PROOF WAS RUN ON THE WRONG POPULATION. It checked `pending` and
  `hops_used`, both of which enumerate the INBOX, a directory the probe never
  enters. Re-derived against `RUNTIME_DIR` and `RUNTIME_DIR/responder/held`, the
  two it does enter: those inbox walks remain the module's only production
  enumerators, and the four test-side enumerators of the probed directories are
  safe because the probe is created and removed inside one single-threaded call
  that returns before any of them runs.
- artifact: `tools/moon_sync_responder.py`
- ledgered: YES
- individuation: distinct.

### EV-088
- citation: `bd9f48f`; L1
- claim: an adjudicator ruled fourteen of the fifteen remaining worktrees
  SUPERSEDED and one LOST-WORK, with the tie-break stated in advance.
- refutation: an adversary sent at the destroy-list with the single lens "is
  anything actually lost" REFUTED one SUPERSEDED ruling and produced the
  surviving mutant to prove it. Two were recovered and thirteen pruned.
- artifact: the worktree destroy-list; the adjudicator's ruling
- ledgered: YES
- individuation: distinct.

### EV-089
- citation: `bd9f48f`; L1
- claim: one of three claimed relocations - that an arm already exists at a named
  path.
- refutation: refuted OUTRIGHT.
- artifact: the relocation claims behind the worktree destroy-list
- ledgered: YES
- individuation: AMBIGUOUS - 1 here; one-per-(artifact, root cause) folds EV-089
  and EV-090 into one event, since both rest on the same unverified
  pointer-is-not-proof mistake. The record does not name which arms, so both rows
  are floors.

### EV-090
- citation: `bd9f48f`; L1
- claim: a second of the three claimed relocations.
- refutation: refuted IN PART - a pointer to a file and line is not proof the arm
  is there. The third was confirmed.
- artifact: the relocation claims behind the worktree destroy-list
- ledgered: YES
- individuation: AMBIGUOUS - 1 here, folded into EV-089 by the alternative.

### EV-091
- citation: `bd9f48f`; L1
- claim: two worktrees holding the same path were two artifacts in agreement.
- refutation: byte-identity was checked FIRST and one such pair proved to be a
  SINGLE ARTIFACT COUNTED TWICE.
- artifact: the worktree census
- ledgered: YES
- individuation: distinct.

### EV-092
- citation: `33ab1c6`; L1
- claim: this tree had answered RC's joint re-pin question on 2026-09-10.
- refutation: the answer never left our own directory. Measured across all four
  sibling trees: ZERO copies, and six other notes in the same state, everything
  from `2026-09-09-2200` onward, the last note to reach RC being stamped
  `2026-09-09-2100`. The mechanism is that a note written into our own inbox is
  INDISTINGUISHABLE from a note we sent, because the watcher classifies by
  filename. Silence reads as dissent, so four counterparties were entitled to
  count seven of our positions as dissent.
- artifact: `moon_sync_inbox/` outbound notes (gitignored, and therefore reachable
  by no guard that derives its corpus from `git ls-files`)
- ledgered: YES
- individuation: distinct.

### EV-093
- citation: `33ab1c6`; `90e5e1f`; L1
- claim: this session's own first count of the undelivered backlog - NINE notes.
- refutation: nine was "not present in RC" and two of those had legitimately
  reached their own addressee elsewhere. Against the right population, "present in
  ZERO sibling inboxes", the answer is SEVEN.
- artifact: `docs/LEDGER.md`; `ROADMAP.md`
- ledgered: YES
- individuation: distinct.

### EV-094
- citation: L6
- claim: a "collateral damage" explanation was offered for a failure seen once in
  `tests/test_moon_sync_responder.py` under a planted mutant.
- refutation: REFUTED BY READING, and the failure did not reproduce. A
  non-reproduction is not an explanation, so it stays UNEXPLAINED rather than
  closed.
- artifact: `tests/test_moon_sync_responder.py`
- ledgered: YES
- individuation: distinct.

### EV-095
- citation: L7
- claim: a finding of this tree's own - that `ops/check_task_liveness.py` is
  defective because it never reads a registered task's action back.
- refutation: REFUTED BEFORE IT REACHED CODE. The tool's contract, in its own
  words, is whether the task will FIRE and not whether the process will SUCCEED -
  the State string is reported and is never the verdict - and the harm path is
  guarded by the installers' Test-Path throws plus the tracked-XML arms. The
  supporting scan was worse than decorative: a grep for a PowerShell COM shape
  over a tree that registers by XML was STRUCTURALLY INCAPABLE of finding the
  readers that do exist. What survives is narrower and is an enhancement rather
  than a defect.
- artifact: `ops/check_task_liveness.py`
- ledgered: YES
- individuation: distinct.

### EV-096
- citation: `7786955`; L6
- claim: the test suites do not write the operator's live state.
- refutation: the suite WAS writing the operator's live day log, and nothing had
  ever looked. Measured in-process with a tracer wrapping `open`, `io.open`,
  `os.replace` and `os.rename`: 17492 bytes into `logs/2026-09-11.log` from 51
  nodeids across 12 files, the content synthetic error records manufactured by
  the degradation arms. Fixed at the root - `core.config.load_config` already
  derived `log_dir` from `RC_LOG_DIR` and nothing had ever set it, so one
  assignment at rootdir conftest import time isolates both suites. Verified in a
  clone where REPO_ROOT is `__file__`-derived and no daemon writes: 19575 bytes
  under the control, 0 with the fix.
- artifact: `conftest.py`; `core/config.py`;
  `tests/test_suite_writes_no_live_logs.py`
- ledgered: YES
- individuation: distinct. RECORDED WITH A CAVEAT RATHER THAN SILENTLY: no prior
  EXPLICIT done-claim about this property is recorded anywhere in the window, so
  a stricter reading of "refuted done-claim" would exclude this row. It is
  included because the suite's silence was read as evidence of not writing, and
  the grader should rule on it rather than have the choice made here.

## 5. The exclusions

The contract pins five things that are NOT events. Every item this extraction
set aside is listed below with its citation and its class.

### Class 1 - recital: a refutation from outside the window re-told

1. `f77c4ad` - an earlier retraction of ours upgraded from WITHDRAWN to DISPROVED
   on a second carrier's measurement. The retraction predates the window; only
   its status changed.
2. `879356d` - the three refuted figures of `6c351b3` re-told in a docs commit
   after `77408ad` had already refuted them in-window. Counted once at EV-004,
   EV-005 and EV-006.
3. L10 - LW's Q3 claim about a shared conftest, refuted and already retracted by
   this tree before the window. Also external in origin.

Count: 3.

Note on in-window re-tellings, which are NOT listed as exclusions: `69e4e9d`,
`7bda8cd`, `37bc3bc`, `bd9f48f`, `f03bbed` and `90e5e1f` re-tell refutations that
happened inside this window. The convention handles those by adding a citation to
the existing row, not by excluding or re-counting them.

### Class 2 - external-origin claims this tree never adopted

1. L6 and `86491a3` - CS's damage narrative for an inherited git environment,
   NARROWED rather than adopted: `git init --bare` with an explicit path does not
   hijack, only the no-path form does, and this tree has zero such call sites.
2. `33ab1c6` - RC's line-number claim, corrected outbound.
3. L10 - LW's "43 to 0" figure, HALF MEASURED: the AFTER was re-run but the
   BEFORE row was carried forward byte-identical from an earlier note.
4. L10 - LW's R3, that a present-but-broken git must still FAIL, which conflicts
   with this tree's shipped `classify_git_probe` and would silently close an open
   operator call.
5. L10 - LW's PATH-strip mirror mechanism, contraindicated here because
   `shutil.which` is PATHEXT-aware while `subprocess.run` reaches CreateProcess.
6. L10 - LW's third note offering no digest, with a with-git passing count that
   moved by twelve between notes, unstated.
7. `69e4e9d` and L7 - LW's backslash finding, where the half the original report
   omitted was measured here (an odd trailing count injects a quote, an even count
   silently halves the backslashes) and the repair was deliberately NOT made
   because reachability is nil.
8. `f77c4ad` - a counterparty's finding about a printed scheduler command,
   recorded as UNSWEPT here rather than as clean, because nobody looked.
9. `c514ca7` and L3 - CS's five numbered questions, answered CORRECT AND
   INCOMPLETE on Q1, Q2 and Q5 and as an operator item on Q3.

Count: 9.

### Class 3 - RED-first TDD failures

A test written to fail first is not a refutation. Every instance of the phrase in
this window, by citation:

1. `72c7041` - three arms red before the fix by AssertionError against a real git
   exit 129, two controls green on both sides.
2. `0d1fa70` - two arms red before the fix with both exit codes spelled as
   literals, two controls.
3. `411ba14` - the probe arm RED first on `assert True is False`.
4. `14017bd` - all four parametrizations RED first on `assert True is False`.
5. `152f61e` - both arms RED first: `assert True is False` for the swallowed
   removal, AttributeError on the absent `_DIR_PROBE_STALE_SECONDS`.
6. `ffb8f7c` - the new strip arm, red under the mutant and green on revert.
7. `390a831` - the fail-closed arms proving the input is genuinely unreadable
   before grading the guard.
8. `5d785f5` - eight mutants, eight killed.
9. `038fd4a` - "PROVED IT CAN FAIL rather than asserting it", by mutating
   `census._dotted` in a worktree.
10. `c145f8a` - correct resolver RED with the probe, `isascii` narrowing GREEN,
    then the inverse after the fix.
11. `2ae95f3` - three named mutants each firing their own arm, pycache purged on
    both sides.

Count: 11.

### Class 4 - a hypothesis opened by a probe whose stated purpose was to test it, cleared as that probe's intended output

An approach that was adopted, worked on, then abandoned on evidence IS an event
and is in section 4. These are not that.

1. `13c771f` and L4 - the interpreter hypothesis, which HELD: every arm passes on
   CPython 3.14.4 and 3.11.9, and `Path.rename` on 3.11.9 calls `os.rename`
   directly, so the transitive coverage is not a 3.14-only accident.
2. `7786955` and L6 - a RIGHT boundary for the credential detector, rejected by
   measurement because adding one lost two of three detections.
3. `bd9f48f` and L1 - the "does this dirty file differ from main" disposition
   test, rejected in favour of blob reachability: 51 worktrees held a differing
   file but only 15 held a blob main's history had never contained.
4. `c514ca7` and L3 - `os.startfile`, `asyncio.create_subprocess_shell`,
   `asyncio.create_subprocess_exec`, `pty.spawn`, `os.fork` and `os.forkpty`
   measured at ZERO call sites over the 108-file population, so every gap is a
   contract gap and not a live leak.
5. `2ae95f3` and L5 - reachability of the silent callee class measured at zero:
   all seven nodes are stub or predicate invocations and none is a launch.
6. `1c8aab2` and L7 - the census counts did not move, measured by running the
   pre-repair and post-repair modules back to back and diffing the full reports.
7. `1c8aab2` and L7 - the one failure seen in a scratchpad copy, ABSENT against
   the frozen merged tree in four consecutive runs and in the full suite, with the
   collected total identical on both sides; its cause is recorded as UNDIAGNOSED.

Count: 7.

### Class 5 - cross-repo falsification, where this tree's correct action made a true record in another tree false

1. `33ab1c6` and L1 - delivering eleven or twelve held notes to their addressees
   on operator instruction made each counterparty's then-true record of our
   SILENCE, which the charter reads as dissent, false. The delivery was the
   correct action; the falsified records were theirs.

Count: 1. No other instance was found in this window.

### Items considered and set aside as not refuted done-claims at all

Listed separately from the five classes, and NOT counted in them, so that the
exclusion arithmetic above stays exactly the contract's five.

1. `f77c4ad` - a branch in `answered_usable` that cannot fire from its own
   probes. A defect finding, with no prior assertion to refute.
2. `f77c4ad` - the splice in the loop slot reader, FLAGGED and deliberately not
   fixed under ruling clause (b).
3. `77408ad` and L10 - the unique-red-function count, 24 against 23, left
   UNRECONCILED with neither pass enumerating the names. No refutation was
   established in either direction.
4. `69e4e9d` and L7 - the 2026-09-14 stamp discrepancy on three ledger entries
   whose commits carry 2026-09-11. A false record, not a done-claim.
5. `13c771f` and `d6437a9` - the roadmap row's "nine files calling unlink". TRUE
   when measured and ten at `13c771f` because staging two new files changed the
   population. Decay, not falsity.
6. `c145f8a` - the `len(parts) > 4` narrowing, green here and green against any
   re-derivation whatever because the corpus holds zero five-segment chains.
   Disclosed as a limit rather than shipped as a claim.
7. `f03bbed` - the correction that the adjudicated-out ruling lives in a ledger
   entry BODY rather than a heading. A citation-form correction.
8. `f03bbed` - the census row closing on terms other than its own wording,
   disclosed at the time of closing rather than refuted afterwards.
9. L1 - a background task blocked for two hours on a stray
   `cat > "$TMPDIR/cmp.py"` with `TMPDIR` unset, reading stdin forever.
10. L1 and L3 - the pre-push hook reporting three skips where the local run
    reported two, and the skip split moving twice in one session. Both readings
    are real and belong to different machine states; neither withdraws the other.

Count: 10.

## 6. Totals

- UNDER THIS FILE'S CONVENTION, one event per distinct refuted assertion:
  96 events, EV-001 to EV-096.
- UNDER THE ALTERNATIVE CONVENTION, one event per (artifact, root cause) pair:
  76 events.
- Rows flagged `individuation: AMBIGUOUS`: 32 - EV-001 to EV-008, EV-032 to
  EV-034, EV-037, EV-038, EV-045 to EV-048, EV-052, EV-053, EV-055 to EV-060,
  EV-066, EV-067, EV-071, EV-080, EV-086, EV-089 and EV-090.
- Items excluded under the five pinned classes: 31 - class 1 three, class 2
  nine, class 3 eleven, class 4 seven, class 5 one.
- Items set aside as not refuted done-claims at all, counted separately: 10.

BOTH TOTALS ARE FLOORS. Nine of the 31 decidable commits in this window are named
nowhere in the ledger - see section 1 for why the 32nd is not decidable by that
probe - five of the unledgered are the refuted or superseded passes, and a
refutation that reached neither a ledger entry nor a commit message reached this
extraction through no channel at all. Several rows are additionally floors in
themselves, and say so: EV-071, EV-089 and EV-090 rest on records that do not
name their individual subjects.

COMPARISON WITH THE PUBLISHED FIGURE. The published count was 65 refuted
done-claims over this same range. This extraction finds 96 under its stated
convention and 76 under the alternative. Both differ from 65, and the difference
is NOT reconciled here - the convention was fixed before the rows were counted
and was not adjusted to reach any particular total. Anyone comparing the two
figures should first establish which individuation convention produced the 65,
because nothing published with it says.
