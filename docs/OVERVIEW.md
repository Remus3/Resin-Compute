# ResinCompute - project overview in depth

The landing page is `README.md`. This file holds the detail that used to live
there: the full status table, the direction of travel, the forecaster's model,
what the project deliberately refuses to do, the third-party data posture and
the stack decision. Running and operating the tree is in `docs/OPERATIONS.md`.

`ROADMAP.md` is the live source for status and open work. Everything below is
its shape as of 2026-10-04, not a second source of truth.

## Status in full

| Status | Area | Where it stands |
|---|---|---|
| **[SHIPPED]** | Wish forecaster | Absorbing Markov chain over (copies, pity, guarantee, loss streak) for the character, weapon, standard and Chronicled banners. Correct for the current game version, and the three easy-to-get-wrong constants are regression-tested. |
| **[SHIPPED]** | PityEngine service | Local HTTP on 8790, `GET /health`, `POST /forecast` and `POST /by-when`, stdlib only. All four banner kinds are accepted over HTTP, Chronicled included, and an unknown banner returns 400. |
| **[SHIPPED]** | Headless lane | Seven registered jobs - `sync_profile`, `reconcile_state`, `reconcile_ledger`, `persist_state`, `recompute_plan`, `forecast_pity`, `emit_health` - with a daemon mode and a supervisor. `reconcile_ledger` is default-off: it folds the operator-typed data/income_observations.json into the ledger and re-estimates income velocity, and SKIPs when that file is absent. |
| **[SHIPPED]** | Enka ingest | Re-implemented from the published protocol and exercised against a real live profile. Custom User-Agent required, `ttl` honoured, UID enumeration refused. |
| **[SHIPPED]** | State persistence | The headless lane writes the reconciled account state, and the surface cold-starts from it showing how old the reading is. |
| **[SHIPPED]** | Goal DAG | Correct dependency graph with cycle detection and a critical path - 30 nodes across four chains for one character at level 60, 6/6/6 talents and a weapon at 60. |
| **[SHIPPED]** | Provenance schema | Row-scoped receipts landed before the first data row exists. A NOT_FOUND row carrying no sampling rate is refused. |
| **[SHIPPED]** | Cross-repo responder | `tools/moon_sync_responder.py`, fired every five minutes by a scheduled task inside an agreed window, answers notes from sibling repositories with nobody at the keyboard. It runs a headless agent through the vendored fleet kit, checks a supervisor note's provenance by SHA-256 against the sender's outbox copy (ADR-011), and validates and delivers the draft itself. |
| **[PARTIAL]** | Dashboard | Six panels on 8791 - resin, today, wishes, roster, plan, teams. Each declares READY, PARTIAL or NOT_WIRED, and an unwired panel says what it is waiting on instead of showing a placeholder number. Measured in `surface/model.py`: a fresh clone with no state snapshot renders 2 READY and 4 NOT_WIRED. |
| **[PARTIAL]** | Material costs | `data/costs/` holds its contract README and ZERO data rows. Needs first-hand observed ascension, talent and weapon quantities. |
| **[PARTIAL]** | Objective DAG costs | `engines/objectives.py` takes materials as a caller-supplied argument and nothing supplies them, so every material quantity it emits is ZERO. Correct shapes, empty costs. |
| **[PARTIAL]** | Scheduler | Resin-aware, rotation-aware and weekly-lockout-aware, but it has no dating layer: it emits day offsets and nothing turns one into a calendar date. |
| **[PARTIAL]** | Resin panel | Projects forward from a recorded observation, and that observation has to be typed in by hand. Nothing records one automatically. |
| **[PARTIAL]** | Provenance producer | The schema has no writer yet, so it has never met a real value. |
| **[PARTIAL]** | Constellation talents | Exact only when the caller supplies a skill-group mapping. Without a licensed skill depot the mapper reports what it could not resolve instead of guessing - a product limitation, not a bug. |
| **[LIVE]** | Concurrency governor | `ops/loop/` is vendored and digest-pinned, and since `1a6d8da` it is also LIVE: `run_daemon` in `headless/runner.py` holds a slot around each pass. No loop was invented to justify the vendored file - the daemon loop already existed and gained the governor it was always meant to have. A dry run takes no slot, and a slot timeout is a failed pass rather than permission to proceed unslotted. |
| **[PARTIAL]** | Artifact scoring | `engines/artifact_score.py` scores substats against caller-supplied weights and counts rolls against caller-supplied magnitudes (ADR-012, Proposed); nothing supplies either table and no panel renders it. |
| **[PARTIAL]** | Banner calendar | The forecaster now answers "by when" over `POST /by-when` (`agents/pity_engine/timeline.py`), but only from a schedule the CALLER supplies per request. No calendar source is vendored - that source still sits behind the same licence gate as the cost tables. |
| **[PARTIAL]** | Income velocity | `core/ledger.py` estimates velocity from ledger entries, and the default-off `reconcile_ledger` job now feeds it from the operator-typed data/income_observations.json; the job SKIPs until that file exists, and nothing records an observation automatically. |
| **[PLANNED]** | Team solver | Elemental reaction modelling, held back until the resource layer is complete. The shipped Teams panel states elemental IDENTITY only - nothing ranks or recommends. |

## Where it is going

The largest unlock is unglamorous: first-hand observed cost tables. The
objective DAG, the scheduler and the plan panel are built and emit zeros until
those rows exist.

**Near-term, and user-visible.** A banner calendar SOURCE, so the shipped "by
when" route does not depend on the caller typing the schedule in - gated behind
the same licence question as the cost tables. Income velocity from real ledger
history: the `reconcile_ledger` job exists and waits on the operator-typed
data/income_observations.json rather than on a figure typed into the snapshot.
Row-scoped provenance enforced on `data/costs/` by a guard that rejects a row
missing any receipt field, landing before the first row does. And a worked
end-to-end goal emitting a DATED task list rather than today's correct DAG with
empty costs and bare day offsets.

**Later.** A team-composition solver with elemental reaction modelling, held
until the resource layer is complete. Multi-account support - everything is
keyed to a single UID today. Containers, as a fresh decision with its own ADR.
A citation file and a first tagged release. Discussions are excluded on purpose,
because inviting pasted payloads farms other people's personal data into a
public repository.

## What the forecaster models

Three constants are easy to get wrong, so all three are regression-tested.
These are properties of the shipped model, not of any summary of it.

**The 50/50 has not been 50/50 since version 5.0.** Capturing Radiance converts
some non-guaranteed 5-stars to the promotional character, and HoYoverse
publishes a consolidated rate-up probability of 55.000%, with a hard cap making
four consecutive losses impossible. The engine models a per-roll probability of
0.52106 plus a forced win at three consecutive losses, the simple model that
reproduces the official aggregate. A flat 0.55 under the same cap overshoots to
57.35%.

**The weapon soft-pity ramp saturates at pull 77.** With a 7% per-pull
increment from pull 63, the probability reaches 0.987 at pull 76 and would be
1.057 at pull 77, so 77 is where it stops. A curve said to run to pull 79 is
arithmetically impossible. The increment is a tunable, because the exact
micro-curve is not pinned by public data.

**A probability of success needs a pull budget**, so the real signature takes
`pull_budget`. The result comes from an absorbing Markov chain over
`(copies, pity, guarantee, loss_streak)` and never from a binomial on 1.600% -
that figure is `1 / E[wishes per 5-star]`, a long-run average, and is not a
per-wish probability at any point.

Derivations are in `docs/SPEC_SCAFFOLD.md` section 3; ADR-003 records the
corrections.

## What it deliberately does not do

- **Vendors no game data.** Not one row. `data/fixtures/` is a small
  hand-authored set of publicly known identifiers, for tests. What was examined
  and refused is surveyed in `docs/LICENSE_NOTES.md` and ADR-002.
- **Does not scrape or mirror a wiki.** No upstream dataset is ingested.
- **Does not automate, modify or touch the game client.** No macros, no input
  injection, no packet capture, no memory reading, no file patching. The only
  external data it reads is a player's own public character showcase.
- **Does not enumerate UIDs.** Enforced in `ingest/enka_client.py` rather than
  merely promised here, with the required custom User-Agent and the `ttl`.
- **Does not let unverified numbers into `data/`.** A figure without first-hand
  provenance stays in prose where it can be argued with - see
  `docs/GOAL_SPEC_SEED_TEAM.md`, which stamps every claim verified, unverified,
  time-sensitive or refuted, and `tests/test_goal_spec.py`, which is the guard
  that enforces it.

## Third-party data posture

Read `docs/LICENSE_NOTES.md` before adding any data source. The short version,
from a verification pass on 2026-09-06:

- **Every candidate wraps HoYoverse-copyright game data, whatever its own
  licence says, and no licence on a wrapper can grant rights to that payload.**
  That is the governing rule, and it is why the projects below are not vendored
  even where the copyleft question has been settled.
- `Dimbreath/GenshinData` is **404 and DMCA'd**, and its live successor carries
  **no licence at all**. It is not an ingest target.
- `genshin-db` is MIT for its author's code, but its payload derives from a
  CC BY-SA wiki and from unlicensed datamined files. The MIT badge does not
  clear the data.
- `enka-py` and `ambr-py` are both **GPL-3.0**, and this tree is now
  GPL-3.0-or-later, so copyleft is no longer the objection - ADR-006 dissolved
  that one and no others. The blanket caveat above is what still bars them.

The Enka client is therefore re-implemented from the published protocol, because
protocol facts are not copyrightable and source is. It complies with published
policy: a required custom User-Agent, the `ttl` honoured on every response, and
bulk UID enumeration refused.

## Why Python

Recorded in ADR-001 (`docs/adr/ADR-001-stack.md`). The project inherits its
engineering discipline - lint config, dual-suite test layout, git hooks, CI
shape, and the supervisor and health-file model - from an existing Python tree
by the same author, and that inheritance is only real in Python. The interfaces
ship as Python dataclasses in `core/types.py`.
