# ResinCompute roadmap

Open work, newest priorities first. Aspirational items live at the bottom.
Per-item completion history belongs in `docs/LEDGER.md` once that file exists,
never in `CLAUDE.md`.

## Status

Scaffold shipped 2026-09-06. The tree stands up, both suites run, the headless
lane smoke test passes, and the forecaster is correct for the current game
version. What follows is everything the scaffold deliberately did not do.

## Now

- **QA the repo for going public.** Next session's task. The outbound licence is
  settled (GPL-3.0-or-later, ADR-006) and `tests/test_licence_posture.py` guards
  the declaration in both directions, but "licence is correct" is not the same
  as "ready to be read by a stranger". Needs: a `README.md` that opens for an
  outsider rather than for the operator, a stated quickstart that a fresh clone
  can actually follow, the per-file GPL headers ADR-006 deliberately deferred,
  and a sweep for anything machine-specific or account-specific in tracked
  files. The repo-relocation item below is a prerequisite for the CI half.
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
- **Repo relocation.** The scaffold was built inside the Riot Commander
  repository because the session's GitHub integration could not create a new
  repository (`POST /user/repos` returned 403 Resource not accessible by
  integration). Create the private repo manually, move this tree to its root,
  and run `python scripts/install_hooks.py` in the new clone before the first
  commit. Until that happens the CI workflows are inert, because they are written
  for `resin-compute/` as the repository root.
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
- **A `docs/LEDGER.md`** with the per-item completion history, following the
  parent project's append-only newest-first convention.

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
