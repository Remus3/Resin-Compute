# ResinCompute roadmap

Open work, newest priorities first. Aspirational items live at the bottom.
Per-item completion history belongs in `docs/LEDGER.md`, never in `CLAUDE.md`.

## Status

Scaffold shipped 2026-09-06. The tree stands up, both suites run, the headless
lane smoke test passes, and the forecaster is correct for the current game
version. What follows is everything the scaffold deliberately did not do.

## Now

- ~~**QA the repo for going public.**~~ **DONE 2026-09-06.** The audit ran at
  commit `96a8c54` and every gate was green before a line was touched, so none of
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
    `e95a71c`: 80 tracked `.py`, 10 tracked `.js`, and zero SPDX identifiers in
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
  `e95a71c`, both measured.**
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
  the verification pass at `e95a71c`. This is NOT a blind spot in the dangerous
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
  inside the Riot Commander repository because the session's GitHub integration
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
- **Containers.** Riot Commander has none, so there was nothing to inherit. If
  containers are wanted, that is a new decision with its own ADR.
- **Multi-account support.** Everything is keyed by a single UID today.
- **Team composition solver.** Elemental reaction modelling is a large piece of
  domain work and should not be started before the resource layer is complete.

## Known gaps, stated honestly

- **The concurrency governor is vendored but INERT, and that is deliberate.**
  `ops/loop/slots.py` and `ops/loop/winmutex.py` are byte-identical-by-contract
  with Legion Wallpaper and Riot Commander, pinned by
  `tests/test_loop_concurrency.py`. NO PRODUCTION CODE PATH CALLS `slots.hold()`
  - the only callers are the five sites inside `tests/test_loop_concurrency.py`
  itself, which exercise the vendored module against a `tmp_path` bucket and
  never against the shared one.
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
