# ResinCompute

**Gacha arithmetic for Genshin Impact - wish and pity forecasting, resin
budgeting and goal planning, off your own public Enka profile. Headless-first,
stdlib-only Python, no game data vendored.**

[![ci](https://github.com/Remus3/Resin-Compute/actions/workflows/ci.yml/badge.svg)](https://github.com/Remus3/Resin-Compute/actions/workflows/ci.yml)
[![docs-guards](https://github.com/Remus3/Resin-Compute/actions/workflows/docs-guards.yml/badge.svg)](https://github.com/Remus3/Resin-Compute/actions/workflows/docs-guards.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Licence GPL-3.0-or-later](https://img.shields.io/badge/licence-GPL--3.0--or--later-blue)](LICENSE)

**Contents.**
[See it work](#see-it-work) - [Status](#status-at-a-glance) -
[Roadmap](#where-it-is-going) -
[The model](#what-the-forecaster-models) -
[What it does not do](#what-it-deliberately-does-not-do) -
[Quickstart](#quickstart) -
[Scheduled tasks](#the-windows-scheduled-tasks-and-how-to-remove-them) -
[Repository tree](#repository-tree) -
[Ports](#ports) - [Data posture](#third-party-data-posture) -
[Why Python](#why-python) - [Conventions](#conventions) -
[Contributing](#contributing-security-and-conduct) - [Licence](#licence)

ResinCompute turns the parts of Genshin Impact that are arithmetic rather than
opinion into answers you can check. The compute core is **PityEngine**
(`agents/pity_engine/`, HTTP `:8790`), a pure deterministic gacha forecaster
with its own test suite. Roster data comes from a player's own public
Enka.Network showcase, through a client re-implemented from the published
protocol. This is a developer tool: there is no installer, no app and no hosted
page, everything runs non-interactively from a CLI or a daemon, and the
dashboard is optional. Questions it is built to answer:

- I am 74 pulls in with no guarantee. What are my odds of landing the featured
  5-star inside my next 30 wishes?
- I want two constellations and the signature weapon. How many wishes should I
  expect to spend, and how much does a guarantee change that?
- I want this character at 90 with 9/9/9 talents. What does that cost in resin,
  and in what order should the work happen?

**The first two are answered today. The third is not.** `data/costs/` holds zero
material rows, so the resin-and-ordering answer is unavailable: the goal DAG and
the scheduler emit correct shapes with empty costs. See
[Status](#status-at-a-glance).

**Not affiliated with, endorsed by, or connected to HoYoverse / miHoYo /
Cognosphere.** "Genshin Impact" and all associated names and material are their
property. This is an independent, non-commercial companion tool that vendors
none of their data.

---

## See it work

Start the engine in one console:

```powershell
# console A
python -m agents.pity_engine --port 8790
```

Both local servers - the engine on 8790 and the dashboard on 8791 - default
their bind address to `127.0.0.1`, and **neither authenticates**. A host
override is a command-line flag on each. Do not expose either to a network you
do not control.

Now ask it the first question above from a second console - 74 pity, no
guarantee, a budget of 30 wishes:

```powershell
# console B
$body = @{
  banner                  = 'character_event'
  pity_5star              = 74
  has_guarantee           = $false
  consecutive_5050_losses = 0
  target_count            = 1
  pull_budget             = 30
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Body $body `
  -Uri http://127.0.0.1:8790/forecast `
  -ContentType 'application/json'
```

The same two calls on a POSIX shell, which is what the project's own CI runs:

```bash
curl -s http://127.0.0.1:8790/health
curl -s -X POST http://127.0.0.1:8790/forecast \
  -H 'Content-Type: application/json' \
  -d '{"banner":"character_event","pity_5star":74,
       "has_guarantee":false,"consecutive_5050_losses":0,
       "target_count":1,"pull_budget":30}'
```

The answer, captured verbatim from a live run of that request:

```json
{
  "status": "ok",
  "engine_version": "0.1.0",
  "probability": 0.5904331542650183,
  "pull_budget": 30,
  "target_count": 1,
  "banner": "character_event",
  "distribution": [
    0.40956684573498164,
    0.5904331542650183
  ],
  "expected_pulls": 33.82161353538069
}
```

Read that as a 59.0% chance of at least one copy inside 30 pulls, a 41.0% chance
of none, and an expectation of about 34 pulls to the first copy from this state;
`distribution[k]` is the probability of exactly `k` copies. `GET /health`
returns the engine version, pid and uptime. A malformed request returns HTTP 400
with a friendly message - the raw exception goes to the log, never into the body.

## Status at a glance

[`ROADMAP.md`](ROADMAP.md) is the live source. This table is its shape.

| Status | Area | Where it stands |
|---|---|---|
| **[SHIPPED]** | Wish forecaster | Absorbing Markov chain over (copies, pity, guarantee, loss streak) for the character, weapon, standard and Chronicled banners. Correct for the current game version, and the three easy-to-get-wrong constants are regression-tested. |
| **[SHIPPED]** | PityEngine service | Local HTTP on 8790, `GET /health` and `POST /forecast`, stdlib only. All four banner kinds are accepted over HTTP, Chronicled included, and an unknown banner returns 400 - though no HTTP-layer test covers the Chronicled route specifically. |
| **[SHIPPED]** | Headless lane | Six registered jobs - `sync_profile`, `reconcile_state`, `persist_state`, `recompute_plan`, `forecast_pity`, `emit_health` - with a daemon mode and a supervisor. |
| **[SHIPPED]** | Enka ingest | Re-implemented from the published protocol and exercised against a real live profile. Custom User-Agent required, `ttl` honoured, UID enumeration refused. |
| **[SHIPPED]** | State persistence | The headless lane writes the reconciled account state, and the surface cold-starts from it showing how old the reading is. |
| **[SHIPPED]** | Goal DAG | Correct dependency graph with cycle detection and a critical path - 30 nodes across four chains for one character at level 60, 6/6/6 talents and a weapon at 60. |
| **[SHIPPED]** | Provenance schema | Row-scoped receipts landed before the first data row exists. A NOT_FOUND row carrying no sampling rate is refused. |
| **[PARTIAL]** | Dashboard | Six panels on 8791 - resin, today, wishes, roster, plan, teams. Each declares READY, PARTIAL or NOT_WIRED, and an unwired panel says what it is waiting on instead of showing a placeholder number. Measured in `surface/model.py`: a fresh clone with no state snapshot renders 2 READY and 4 NOT_WIRED. |
| **[PARTIAL]** | Material costs | `data/costs/` holds its contract README and ZERO data rows. Needs first-hand observed ascension, talent and weapon quantities. |
| **[PARTIAL]** | Objective DAG costs | `engines/objectives.py` takes materials as a caller-supplied argument and nothing supplies them, so every material quantity it emits is ZERO. Correct shapes, empty costs. |
| **[PARTIAL]** | Scheduler | Resin-aware, rotation-aware and weekly-lockout-aware, but it has no dating layer: it emits day offsets and nothing turns one into a calendar date. |
| **[PARTIAL]** | Resin panel | Projects forward from a recorded observation, and that observation has to be typed in by hand. Nothing records one automatically. |
| **[PARTIAL]** | Provenance producer | The schema has no writer yet, so it has never met a real value. |
| **[PARTIAL]** | Constellation talents | Exact only when the caller supplies a skill-group mapping. Without a licensed skill depot the mapper reports what it could not resolve instead of guessing - a product limitation, not a bug. |
| **[LIVE]** | Concurrency governor | `ops/loop/` is vendored and digest-pinned, and since `1a6d8da` it is also LIVE: `run_daemon` in `headless/runner.py` holds a slot around each pass. No loop was invented to justify the vendored file - the daemon loop already existed and gained the governor it was always meant to have. A dry run takes no slot, and a slot timeout is a failed pass rather than permission to proceed unslotted. |
| **[PLANNED]** | Artifact scoring | Artifacts parse cleanly, but nothing scores a substat roll and the scoring model has to be stated before it is built. |
| **[PLANNED]** | Banner calendar | The forecaster answers "given N pulls" but not "by when", because nothing knows when a banner runs. |
| **[PLANNED]** | Income velocity | Velocity estimation folds observed ledger entries, but nothing populates the ledger automatically. |
| **[PLANNED]** | Team solver | Elemental reaction modelling, held back until the resource layer is complete. The shipped Teams panel states elemental IDENTITY only - nothing ranks or recommends. |

## Where it is going

The largest unlock is unglamorous: first-hand observed cost tables. The
objective DAG, the scheduler and the plan panel are built and emit zeros until
those rows exist.

[`ROADMAP.md`](ROADMAP.md) is the live list and is not reproduced here. The
direction:

**Near-term, and user-visible.** Artifact scoring, once the scoring model is
stated. A banner calendar, so the forecaster can answer "by when" and not only
"given N pulls". Income velocity estimated from real ledger history instead of a
typed-in figure. Row-scoped provenance enforced on `data/costs/` by a guard that
rejects a row missing any receipt field, landing before the first row does. And
a worked end-to-end goal emitting a DATED task list rather than today's correct
DAG with empty costs and bare day offsets.

**Later.** A team-composition solver with elemental reaction modelling, held
until the resource layer is complete. Multi-account support - everything is
keyed to a single UID today. Containers, as a fresh decision with its own ADR.
A visibility pass once the repository is public: topics, a citation file, a
first tagged release, and an issue template that demands provenance fields.
Discussions are excluded on purpose, because inviting pasted payloads farms
other people's personal data into a public repository.

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

## Quickstart

Requires Python 3.11 or newer; runtime is stdlib only, so only the dev toolchain
needs installing. Every block is PowerShell, because this is developed and
operated on Windows. Two POSIX habits bite: `export VAR=...` is not PowerShell,
and `curl` there is an alias for `Invoke-WebRequest` whose `-s` binds silently
to `-SessionVariable`, so the console appears to hang instead of erroring.

### 1. Clone, install the hooks, install the dev dependencies

**Install the hooks first.** `core.hooksPath` is local git config and is not
cloned, so a fresh clone runs **zero** hooks - `.githooks/` is inert until then.
There are three: `pre-commit` gates banned glyphs and net-new lint, `commit-msg`
shapes the message, and `pre-push` runs both suites before anything leaves the
machine.

```powershell
git clone https://github.com/Remus3/Resin-Compute.git
cd Resin-Compute
python scripts/install_hooks.py
python -m pip install -r requirements-dev.txt
```

#### A path with a space in it is supported and tested

Clone anywhere. `C:\Resin Compute` is itself a working checkout, exercised with
ruff, both suites, the headless smoke test and the supervisor dry-run. Four
pieces make that work, so do not "simplify" them:

- `.githooks/*` quote every expansion, and `$ROOT` comes from
  `git rev-parse --show-toplevel`, which returns the space.
- `ops/supervisor.py` builds its child command as a LIST, never `shell=True`.
- `ops/install_scheduled_task.ps1` uses `-LiteralPath` and `Join-Path`.
- `ops/ResinCompute-Supervisor.xml` keeps `<Command>`, `<Arguments>` and
  `<WorkingDirectory>` as separate elements.

### 2. Run the gates

Two suites, run **separately**. Never `pytest .` from the root.

```powershell
python -m pytest tests                  # application suite
python -m pytest agents/pity_engine     # engine self-validation
python -m ruff check .
python -m mypy
```

`ruff` sweeps every tracked `.py` while `mypy` sweeps only the `files=` roots in
`mypy.ini`, so its `Success` is not a statement about the rest of the tree;
`tests/test_mypy_scope.py` keeps the two honest.

### 3. Bootstrap static data

Offline by default: it normalizes the local hand-authored fixtures without
touching the network. A live profile needs a User-Agent, because upstream policy
requires one and the client refuses to send a default.

```powershell
python scripts/bootstrap_data.py --offline --dry-run   # show what it would do
python scripts/bootstrap_data.py --offline             # write it

$env:ENKA_USER_AGENT = "ResinCompute/0.1 (contact: you@example.com)"
python scripts/bootstrap_data.py --uid 618285856
```

On a POSIX shell that third line is `export ENKA_USER_AGENT="..."`. The UID is
Enka.Network's published example from their API documentation, not a real
player's, so the block is copy-pasteable.

### 4. Run the lane, the supervisor and the dashboard

The first four run and exit, so they share a console. **The last three run in
the FOREGROUND until you stop them**, so each needs its own.

```powershell
python -m headless.runner --once
python -m headless.runner --once --dry-run       # compute and log, write nothing
python -m headless.runner --list-jobs
python -m headless.runner --job forecast_pity

python -m headless.runner --daemon --interval 300
python -m ops.supervisor                         # the same worker, supervised
python -m surface --port 8791                    # the dashboard
```

Under the supervisor, writing any content to `restart_trigger.txt` triggers a
restart within about five seconds. Confirm it came back by reading the health
file for a new pid, never by looking at a window:

```powershell
python -c "import json;print(json.dumps(json.load(open('ops/runtime/health.json')),indent=2))"
```

On Windows, launch background daemons with `pythonw.exe` rather than
`python.exe` so no console window flashes.

---

## The Windows scheduled tasks, and how to remove them

Nothing in the Quickstart installs either of these and nothing needs them. But
this repository ships TWO scheduled-task installers, and a registered task
OUTLIVES THE CLONE: the definition lives in the Windows Task Scheduler store,
not in the checkout, so **deleting the repository does not remove it.** The
desktop shortcut written by `scripts/make_shortcut.py` outlives it too, and is
the only other thing here that does.

**`ops/install_scheduled_task.ps1` registers `ResinCompute-Supervisor`** from
`ops/ResinCompute-Supervisor.xml`, so the supervisor comes up unattended. Read
off the XML, not from memory:

- **It fires at EVERY LOGON**, its only trigger, at the **HIGHEST AVAILABLE
  privilege** the account can obtain.
- **It is HIDDEN.** Task Scheduler does not list it until "Show hidden tasks" is
  on, so it is easy to look past when auditing what starts with your session.
- **It has NO execution time limit.** The field is `PT0S`, which for this
  setting means unlimited rather than zero.
- **It restarts itself on failure**, three times, a minute apart.
- **Its working directory is baked in at install time**, so moving or deleting
  the checkout leaves it firing at a path that is no longer there.

**`ops/install_responder_task.ps1` registers `ResinCompute-Responder`** from
`ops/ResinCompute-Responder.xml`, a cross-repo responder armed for one agreed
window. It is also HIDDEN, runs at LEAST privilege, carries a 30-minute
execution limit, and repeats on a five-minute interval until the trigger's
`EndBoundary`. **Its definition survives the window.** Past the boundary the
task never fires again, but it is still sitting in the scheduler store, so it
has to be removed as explicitly as the other one.

Remove the supervisor task, elevating the console if any of these is denied:

```powershell
Get-ScheduledTask -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'ResinCompute-Supervisor' -Confirm:$false
```

The responder installer carries its own kill switch, which is the shortest path
and the one to prefer:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove
```

Failing that, the same three cmdlets work against
`-TaskName 'ResinCompute-Responder'`. Both names are the installers' defaults;
if you passed your own `-TaskName`, these commands need it instead. If a
supervised process survives, take its pid from the health file and use
`taskkill /F /PID <pid>`. Never `Stop-Process` - see
[Conventions](#conventions).

---

## Repository tree

Guarded by `tests/test_readme_tree.py`: every path named here must exist on
disk AND be stored by git, because a directory that resolves on one machine but
holds nothing git tracks is absent from every clone.

Two things in this tree surprise people reading it cold, and both are
deliberate. `shell/` is an **Electron** companion window with a system tray
(ADR-005); it is the only part of the repository that pulls `node_modules`, and
`SECURITY.md` puts it in scope. And `tools/screen_capture.py`,
`tools/first_run_capture.py` and `tools/capture_supervisor.py` are a capture
lane for an unrepeatable first launch of the game - the first of those runs a
screenshot cadence that writes FULL-SCREEN images to disk. Separately,
`scripts/make_shortcut.py` writes a shortcut to the Desktop, which is OUTSIDE
the checkout. Nothing in the Quickstart runs any of them.

<details>
<summary>Expand the tree</summary>

```
Resin-Compute/
  README.md                        this file
  CLAUDE.md                        agent context, hard rules, session workflow
  ROADMAP.md                       open work, newest priorities first
  CONTRIBUTING.md                  the gates, and what may not be vendored
  LICENSE                          GPL-3.0-or-later, verbatim and hash-pinned
  pytest.ini                       dual-suite config, never run pytest . at root
  .claude/                         the agent roster and the session commands
  .githooks/                       AUTHORITATIVE gate, inert until installed
    pre-commit                     banned glyphs, py_compile, net-new ruff
    commit-msg                     subject shape and the trailer policy
    pre-push                       runs BOTH suites before a push leaves
  .github/
    workflows/                     ci.yml, and docs-guards.yml for what it declines

  core/                            the shared contract and the primitives
    types.py                       every dataclass the other packages agree on
    atomic_io.py                   the ONLY sanctioned state-write path
    state_io.py                    AccountState snapshot serialization
    resin.py                       resin regeneration, caps, condensed, fragile
    domains.py                     weekday rotation and weekly boss resets
    ports.py                       the single owner of this project's port block
    provenance.py                  the row-scoped receipt every data/ value carries
  agents/
    pity_engine/                   PityEngine - pure deterministic forecaster
      banners.py                   hazard tables and soft-pity ramps, all four
      markov.py                    absorbing Markov chain DP
      forecast.py                  public API
      __main__.py                  stdlib HTTP service on 8790
      tests/                       the engine validates itself
  engines/                         planning and optimization, mechanism only
    objectives.py                  goal DAG, cycle detection, critical path
    scheduler.py                   resin, rotation and weekly lockout aware
    recommend.py                   what to get / who to build solver
  ingest/                          external data, re-implemented from protocol
    enka_client.py                 stdlib urllib, ttl-honouring, policy bound
    enka_mapper.py                 raw payload to EnkaMappedProfile
    static_data.py                 the ONLY place character and material ids live
  headless/                        THE headless lane
    runner.py                      non-interactive entrypoint, CLI and daemon
    jobs.py                        job registry, per-job isolation

  surface/                         the dashboard, served on 8791
    model.py                       pure model, decides panel readiness
    render.py                      HTML rendering
  shell/                           Electron companion with a tray, ADR-005
    main.js                        window, tray and supervisor lifecycle
    lib/                           endpoint, geometry, state, supervisor, tray
  ops/                             supervision and operational state
    supervisor.py                  watchdog, restart trigger, bounded backoff
    ResinCompute-Supervisor.xml    hidden ONLOGON task, elevated, no time limit
    install_scheduled_task.ps1     registers it - removal is documented above
    ResinCompute-Responder.xml     hidden windowed task, least privilege, PT30M
    install_responder_task.ps1     registers it - -Remove is its kill switch
    loop/                          sha256-pinned; two separately measured carrier populations, never edit alone
  scripts/
    install_hooks.py               FIRST thing to run in a fresh clone
    bootstrap_data.py              runnable data bootstrap
    make_shortcut.py               writes a Desktop shortcut OUTSIDE the checkout
  tools/
    precommit_gate.py              banned-glyph and net-new-ruff gate
    wish_authkey.py                Wish History capture, credential-aware
    screen_capture.py              screenshot cadence, writes FULL-SCREEN images
    first_run_capture.py           watches the one-time first-launch artefacts
    capture_supervisor.py          keeps the capture lane alive, reports to a file
  data/
    fixtures/                      hand-authored fixtures, nothing vendored
    costs/                         empty on purpose, first-hand tables only
  docs/
    SPEC_SCAFFOLD.md               the build contract, verified constants
    LEDGER.md                      append-only completion history, newest first
    GOAL_SPEC_SEED_TEAM.md         the seed-team goal, every claim stamped
    LICENSE_NOTES.md               inbound posture, read before adding a source
    PROVENANCE_SCHEMA.md           the receipt every data/ value carries
    adr/                           architectural decisions, indexed
  tests/                           the application suite
    _parked/                       quarantined tests, deliberately not collected
```

**On `ops/loop/` and its two carrier populations.** Each module is pinned across
ITS OWN population, and the two are measured by separate sweeps at separate
instants, so a single numeral over the directory is the wrong summary however it
is counted. Both populations currently hold FIVE roots and those five are the
same roots, which is a coincidence of two snapshots and not a directory-wide
fact - what still separates them is BYTES, not membership: every carrier of
`ops/loop/slots.py` is at the pinned digest, while on `ops/loop/winmutex.py` one
root holds a different file and another is still at a superseded digest. A sixth
fleet root carries neither module. Those rows are a SNAPSHOT OF OTHER
REPOSITORIES' DISKS and they decay - one of them flipped inside a single day
when a root committed a file it had been holding untracked - and nothing in this
tree can poll a foreign disk. **The stamped rows live in exactly one place:
`tests/test_loop_concurrency.py`, in the populations block above
`SLOTS_CARRIERS`.** It carries the per-name status, the instant and the sweep
commands, and only a person re-running that sweep refreshes them. Read them
there rather than trusting the summary here; a second copy of a decaying row is
a second thing to re-measure.

</details>

---

## Ports

**ResinCompute reserves 8790-8809** (`rsc`), and binds two of them.

| Port | Purpose |
|---|---|
| 8790 | PityEngine HTTP |
| 8791 | Dashboard surface |
| 8792-8809 | unassigned |

`core/ports.py` is the single owner of these numbers in CODE, and
`tests/test_ports.py` pins each against the module that really binds it rather
than re-asserting the literal. No guard sweeps Markdown, so `core/ports.py`
wins whenever a document and the module disagree. ADR-004 records why the engine
sits on 8790 and not where the original scaffold put it.

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

## Conventions

- **ASCII only**, anywhere in authored text including code, comments, docs and
  commit messages. The hooks enforce it. A UTF-8 em-dash inside a double-quoted
  PowerShell string ANSI-decodes into a smart quote that terminates the string
  and cascades into a parse failure.
- **Atomic writes only.** `tmp.write_text(...); tmp.replace(target)` via
  `core/atomic_io.py`. Readers poll mid-write.
- **`py_compile` before restart.** A syntax error crashes silently under
  `pythonw.exe`.
- **Never `Stop-Process` on Windows.** Use `taskkill /F /PID`.
- **Live-state-first.** Derive state from the current response only.
- **Never surface a raw API or error string** in a user-facing surface. Catch
  it, render a friendly degraded state, log the raw error.

## Contributing, security and conduct

- **CONTRIBUTING.md** - the gates, the ASCII rule, the TDD loop, the commit
  message shape, and the rule against vendoring game data, which is the one a
  well-meaning pull request is most likely to break. Install the hooks FIRST.
- **SECURITY.md** - how to report a vulnerability privately, through the
  repository's Security tab rather than a public issue. It also names the
  properties that look alarming in a scan and are deliberate: the hidden
  elevated logon task, the Wish History credential tool, and the loopback
  services that do not authenticate.
- **CODE_OF_CONDUCT.md** - Contributor Covenant 2.1, transliterated to ASCII.

Issue and pull request templates live under `.github/`.

## Licence

**GPL-3.0-or-later.** See `LICENSE` for the full text and `NOTICE` for the
copyright line; ADR-006 records why. You may use, study, modify and redistribute
this, including commercially, but any derivative you distribute must carry the
same licence and its source must be available. It cannot be taken closed-source.

That is an OUTBOUND licence covering this project's own code only. It grants
nothing over Genshin Impact's data, names, statistics or assets, which belong to
HoYoverse. For the INBOUND question - what this project may consume - see
`docs/LICENSE_NOTES.md`, which is a separate matter.

<sub>Two workflow badges, because `ci` ignores Markdown-only pushes and
`docs-guards` covers exactly those.</sub>
