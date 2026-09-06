# ResinCompute roadmap

Open work, newest priorities first. Aspirational items live at the bottom.
Per-item completion history belongs in `docs/LEDGER.md`, never in `CLAUDE.md`.

## Status

Scaffold shipped 2026-09-06. The tree stands up, both suites run, the headless
lane smoke test passes, and the forecaster is correct for the current game
version. What follows is everything the scaffold deliberately did not do.

## Now

- **QA the repo for going public - FINDINGS ARE IN, THE FIXES ARE NOT.** The
  audit ran 2026-09-06 at commit `96a8c54` and every gate was green, so nothing
  below is a broken build. Each item is a defect a stranger would meet. The repo
  is still PRIVATE; flipping it is the LAST action, after these land.
  - **The docs guard tests presence, not trackedness.** Every path check in
    `tests/test_docs_consistency.py` calls `.exists()`, which is true for a
    directory that git does not store. That is exactly how `docs-guards` went
    red on the CI runner while the same test was green locally. Zero live
    instances today, and it is one deletion away from recurring - remove
    `data/costs/README.md` and the guard still passes here and fails in every
    clone. Fix: an arm that asserts a cited path is in `git ls-files`, with
    non-vacuity proven at the predicate level rather than by mutating the tree.
  - **The Windows account name is in a tracked file.**
    `.claude/commands/done.md` carries an absolute
    `C:/Users/<account>/...` memory path. Sole hit in the tree.
  - **UID `618285856` is NOT a leak - this was raised and REFUTED in the same
    session, and the refutation is the useful part.** It reads as a real account
    because every other UID in the tree is patently fake (`000000000`,
    `900000000`, `111111111`), and both the audit and the planner flagged it on
    that basis. It is in fact Enka.Network's OWN published example UID, verified
    against the primary artifact: it appears twice in
    `https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/api.md`,
    retrieved 2026-09-06. Publishing it discloses nothing upstream does not
    already publish. **Do not "fix" it.** The residual is one line of work, not
    four files: say so at the use site, so the next reader does not spend the
    same hour reaching the same wrong conclusion.
  - **Per-file licence headers: DECIDE, do not defer again.** 78 tracked `.py`
    and 10 tracked `.js`, zero carrying any SPDX identifier. ADR-006
    Consequences defers them. Going public is the trigger to settle it in an
    new ADR with named re-open triggers, so the answer stops being a silence.
    Recommendation on the measured facts is NO: GPL-3 attaches at the repository
    level through `LICENSE` and `NOTICE`, its section 5 per-file notice
    obligation falls on a modifier rather than the original author, and 88 files
    of churn would invalidate the `file:line` citations this tree runs on.
  - **The README opens for the operator.** First screen is a description, then
    "Why the stack is Python" - an argument against an originating brief the
    reader has never seen, citing a repository they cannot open. No statement of
    what the project deliberately does NOT do, and no statement of what state it
    is in. The non-affiliation disclaimer does not appear until far down.
  - **The README repository tree is stale and unguarded.** It is a fenced block,
    so no test reads it. It omits `surface/`, `shell/`, `.claude/`, `LICENSE`,
    `NOTICE`, `data/costs/` and `tests/_parked/` among others, and roots itself
    at `resin-compute/`, which is not the repo name. A stranger reading it never
    learns the dashboard or the Electron companion exist.
  - **The quickstart cannot be followed on the platform it names.** One block is
    fenced `powershell` and eleven are fenced `bash`, on a documented Windows
    box: `export ENKA_USER_AGENT=...` is not PowerShell, and `curl -s` resolves
    to `Invoke-WebRequest` in PowerShell 5.1 where `-s` is not a parameter.
    Everything the README claims exists was probed and does work.
  - **`docs/SPEC_SCAFFOLD.md` still says a slice is done "from `resin-compute/`".**
    Same stale relocation premise, in the authoritative build contract.
  - **Machine-identity sweep, and the trap in it.** `README.md` presents a
    machine name and an absolute path as canonical. The sibling-project names
    are mostly load-bearing engineering rationale a stranger benefits from - the
    port registry in ADR-004 and the licence survey in ADR-006 are evidence, not
    chatter. Any sweep needs TWO guards per `CLAUDE.md`: the leak is gone AND
    the legitimate neighbours survived. Measured example of why - "Legion" names
    both the machine and a sibling project, so a blind replace destroys a
    port-registry row. The same applies to the synthetic
    `C:\Users\x\` path in `tests/test_make_shortcut.py` and the banned-trailer
    fixture strings in `tests/test_commit_trailers.py`.
  - **Operator decision, cannot be sliced: two commits on `main` carry `Claude`
    as author AND committer.** This is not the trailer rule - the trailers were
    stripped and are guarded. `tests/test_commit_trailers.py` reads only subject
    and body, never `%an`/`%ae`/`%cn`/`%ce`, which is the same shape as the
    already-recorded defect where the trailer policy was enforced on one of its
    two forms. Rewriting history a second time to fix it is the operator's call
    and nobody else's. If the answer is yes, extend that guard to the identity
    fields in the same pass - it cannot be written before the rewrite, because
    it would fail at HEAD.
  - **Also operator-only:** the author email on nineteen of twenty-one commits
    becomes public on the flip, and `NEXT_SESSION_PROMPT.md` is 216 lines of
    operator-shaped hand-off tracked at the repository root. Neither leaks a
    credential; both are judgement calls about what a stranger meets first.
- **The licence gate REFUSED publication, on four text defects.** An independent
  read-plus-web pass over ADR-002, ADR-006 and `docs/LICENSE_NOTES.md` cleared
  the substance and refused the paperwork, 2026-09-06. The substance is worth
  stating because it is the strong half: zero binary assets anywhere in the tree
  (no art, icons, audio, fonts), zero runtime dependencies, three dev pins none
  of which is a data library, zero imports of any forbidden upstream, zero bulk
  data. Names and published drop rates are facts, excluded from copyright. The
  four blockers are all text and none is arguable:
  - **Two fixtures are labelled false, and the label is the compliance claim.**
    `data/fixtures/seed_roster.json` and `seed_materials.json` open with
    `"_synthetic": true` on the line directly above a `"_note"` saying
    "Hand-authored seed identity table" - the file contradicts itself in two
    consecutive lines. `data/fixtures/README.md` is titled "SYNTHETIC test data
    only" while its own body says "hand-authored by this repository". The
    content is real, correct game fact - verified avatarIds and material ids -
    that is HAND-AUTHORED rather than VENDORED, which is what ADR-002 actually
    requires and what `NOTICE` already says correctly. Synthetic means invented,
    and these are not. Once public this file is what a takedown correspondent is
    pointed at, and a compliance document that is demonstrably false about its
    own contents is a worse position than the true claim - which is also the
    stronger one: no upstream dataset is vendored, and the identity data is a
    small hand-authored set of publicly known facts. Only
    `enka_sample_profile.json` is genuinely synthetic. The string
    `tests/test_licence_posture.py` asserts on survives the edit.
  - **Four public-facing files still give the reason ADR-006 dissolved.**
    `README.md`, `ingest/enka_client.py`, `data/fixtures/README.md` and
    `docs/SPEC_SCAFFOLD.md` all still say vendoring enka-py or ambr-py "would
    relicense this repo". That stopped being true when this tree became
    GPL-3-or-later. `docs/LICENSE_NOTES.md` carries the same sentence and is
    handled correctly - its header states the dissolution - so copy that shape.
    The refusal itself is unchanged and must stay: both wrap HoYoverse data, and
    a licence on a wrapper cannot grant rights to the payload. Left as-is, a
    public reader finds ADR-006, concludes the stated reason is void, and
    concludes the refusal has no basis. **Trap for whoever sweeps this:** the
    sentence WRAPS in `README.md`, so a single-line grep for the phrase misses
    it entirely. That is measured - the first sweep this session did miss it.
  - **`NOTICE` omits the warranty-disclaimer paragraph.** It carries the first
    of the GPL-3 appendix's three paragraphs and not the second. GPL-3 section 4
    requires a conveyor to keep intact all notices of the absence of warranty,
    and the appendix's own stated reason for per-file notices is warranty-
    exclusion effectiveness. `LICENSE` still disclaims warranty, so this is
    below best practice rather than non-compliant, and it is a two-sentence fix.
    Worth adding alongside: a trademark acknowledgement naming the marks, and a
    statement that this is a non-commercial companion tool - the second is
    load-bearing, because every HoYoverse fan-content permission that could be
    retrieved is conditioned on non-commercial use.
  - **UNRESOLVED, and UNRESOLVED is treated as REFUSED: no Genshin-specific
    fan-content policy could be retrieved from a first-party source.** The
    HoYoverse Help Center article on fan-made content routes to a Zenless Zone
    Zero guide, and the Genshin merchandising guide governs physical goods only
    and says nothing about software. That is an absence of retrieval, not proof
    of absence. The honest reading is that a non-commercial companion tool
    vendoring no assets sits OUTSIDE the scope of the published asset-use
    guidelines rather than inside their permission - it needs no permission they
    grant, and trips no prohibition that could be read. But outside-the-scope is
    not expressly-permitted and must not be rounded into it. Either retrieve a
    first-party Genshin policy, or record in an ADR that none was locatable on
    2026-09-06, what the posture therefore is, and that it is revisited if one
    appears. **Do not publish on an unrecorded assumption that this is settled.**
  - **Per-file headers: the gate CLEARED this one.** GPL-3's "How to Apply These
    Terms" sits AFTER `END OF TERMS AND CONDITIONS` in the shipped `LICENSE`, so
    it is an advisory appendix and not a condition of the grant; its own wording
    is "it is safest" and "should have". Section 5(b) binds "the work", not each
    file, and binds a modifier rather than the original author. The FSF's own
    SPDX guidance positions the identifier as accompanying the notice, not
    replacing it, and REUSE's per-file MUST is a condition of REUSE compliance,
    not of GPL compliance. So the project is below best practice, NOT
    non-compliant, and ADR-006's deferral is correct as written. This
    strengthens the recommendation above rather than changing it: the ADR to
    write is a decision NOT to adopt, with named re-open triggers. The one
    real cost of omission is narrow and should be recorded - a single file
    copied out of the tree carries no licence signal with it.
- **Name the repository for both tiers.** Operator instruction 2026-09-06: the
  repo should read as "Resin Compute & Pity Engine" or close to it. Two facts
  constrain how, and neither is a reason not to do it. A GitHub repository NAME
  admits no space and no ampersand - both are silently folded to hyphens - so
  the literal string is reachable as the repository DESCRIPTION and as the
  README H1, and only as something like `Resin-Compute-Pity-Engine` as a name.
  A rename also flattens the two-tier convention in `CLAUDE.md` where
  ResinCompute is the repo and PityEngine is the engine inside it, so the
  convention gets restated or amended in the same pass rather than left
  contradicted. Cheap in-tree: no test pins the name, and the only tracked
  citations are `README.md`, `NEXT_SESSION_PROMPT.md` and
  `.claude/commands/done.md`. GitHub redirects the old URL, but the clone line
  in `README.md` is the one a stranger actually uses, so it gets updated.
  DECIDE description-only versus a real rename before touching anything.
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
