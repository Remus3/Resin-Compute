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

## 2026-09-06 - Joining the cross-repo concurrency governor, and being refuted twice

`ops/loop/slots.py`, `ops/loop/winmutex.py`, `tests/test_loop_concurrency.py`,
`tests/test_core_config.py`, `core/config.py`.

This repo took the third slot in a machine-wide concurrency bucket shared with
Legion Wallpaper and Riot Commander, vacated when Red Moon was archived. The two
governor files are BYTE-IDENTICAL-BY-CONTRACT across all three trees. Vendored
LAST, per the ordered round the siblings specified, because this repo was the
only participant with no pin to break.

**Method, and it is the point of the entry.** The files were copied with
`shutil.copyfile` off Riot Commander's live tree, never with `Path.write_text` -
that emits CRLF on Windows and the contract is on bytes. Both sibling trees were
hashed BEFORE the copy and this repo's own disk was re-hashed AFTER it; the
hand-off note's digests were used only as a value to check against. `.gitattributes`
forces `*.py eol=lf`, so the index blob was compared against the disk bytes as
well - they match, which is what proves the pin survives a fresh clone on an
`autocrlf=true` box.

**THE GOVERNOR IS INERT AND THE TREE SAYS SO IN FOUR PLACES.** No production path
calls `slots.hold()`; the only callers are inside `tests/test_loop_concurrency.py`
against a `tmp_path` bucket. `headless/runner.py` is a job runner whose daemon
mode runs in-process job passes - verified by reading `run_daemon`, not assumed.
This is a parity contract joined ahead of need. Two of the three participants
acquire for real; this one's lane is reserved and unclaimed.

**Two of three adversaries returned REFUTED, and they were right.**

- A mutant removing `hold()`'s queueing passed the entire suite and fails Riot
  Commander's. The port had collected worker exceptions into `failures` and never
  asserted on them. Restored as `assert not failures` in
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

**Errors made and corrected in-session, recorded because the next reader deserves
them.** The `db3f767` commit message cited
`test_a_missing_vendored_file_is_a_failure_not_a_skip`, a test that has never
existed - the name came from a dispatch brief and was not read back off the file.
The real one is `test_the_vendored_governor_is_present`. The same message called
the parity "recorded from three separate disks", which overstates it: all three
roots are on one volume, and Riot Commander's note hashed THIS repo's files rather
than printing its own. Both are corrected in `35140ee`, which cannot amend them.

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
the second proved its own subject was byte-identical to `e95a71c` by sha256 and
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
  `905fe24` with `git archive` into a scratch directory rather than mutating the
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
`git archive e95a71c | tar -x` into a directory with no `.git`, then
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

An audit session, not a fix session. Every gate was green at commit `96a8c54`
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

Counts observed 2026-09-06 at `96a8c54`, as a reading and not a claim about now:
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

- `make_shortcut.py` would have created a SECOND shortcut beside the renamed one.
  That is exactly what Clockspeed's refuse-unless-force default was guarding
  against, and its author said so in as many words. Fixed: the installer now
  scans for a shortcut with the same TARGET under any name. Idempotence converges
  on a state - a working shortcut exists - not on one filename.
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
  Lanternlight's. Reworded.
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

`shell/main.js` is WIRING ONLY, inherited from Clockspeed. It imports Electron so
nothing can load it in a test, so nothing that decides anything lives there.

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
- `make_shortcut.py` is IDEMPOTENT, diverging from Clockspeed's
  refuse-unless-force, which is not. Proven: run 2 created, runs 3 and 4 reported
  nothing to do, exit 0.

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
8870 by mirroring Daemon Slayer's 8860 and adding ten. **8870 is inside Daemon
Slayer's reserved block 8860-8879.** Nothing was listening, so nothing broke and
nothing warned.

Verified against sibling SOURCE, not a live scan - the rule Clockspeed learned
the hard way when it allocated a band by probing while the owning project's GUI
happened to be closed. The only registry hit inside the new block was
Amberstone's `range(8770, 8790)`, whose end is exclusive.

Three sites carried the literal 8870 independently; all now resolve to
`core.ports.ENGINE`. The tests pin each constant against the module that really
binds rather than re-asserting the literal, and a negative guard rejects any
sibling port literal in tracked Python source.

Reservation shared to all five siblings through the established
`moon_sync_inbox/` channel, without editing any sibling's source.

## 2026-09-06 - Initial scaffold

Recorded in `README.md` and `docs/SPEC_SCAFFOLD.md`. ADR-001 through ADR-003.
