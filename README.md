# Resin Compute & Pity Engine

[![ci](https://github.com/Remus3/Resin-Compute/actions/workflows/ci.yml/badge.svg)](https://github.com/Remus3/Resin-Compute/actions/workflows/ci.yml) [![docs-guards](https://github.com/Remus3/Resin-Compute/actions/workflows/docs-guards.yml/badge.svg)](https://github.com/Remus3/Resin-Compute/actions/workflows/docs-guards.yml)

Both badges are load-bearing and neither is redundant: `ci` carries
`paths-ignore: ['**/*.md']` and `docs-guards` fires on exactly what `ci`
declines, so a docs-only push starts no `ci` run at all. Read alone, the `ci`
badge would show a stale green from the last code push while a docs push went
unverified. Together they cover every push.

A planning engine for Genshin Impact's resource economy. It answers questions
that are arithmetic rather than opinion: how many pulls until a character is
reasonably safe, what a build actually costs in resin and days, and which of
several goals to fund first.

Headless-lane first. Every calculation runs non-interactively from a CLI or a
daemon, and nothing requires a UI. There is a dashboard, but it reads the same
computed state everything else does.

- **Repo:** ResinCompute
- **Compute engine:** PityEngine (`agents/pity_engine/`, HTTP `:8790`)

**Not affiliated with, endorsed by, or connected to HoYoverse / miHoYo /
Cognosphere.** "Genshin Impact" and all associated names, characters and
material are their property. This is an independent, non-commercial companion
tool. It vendors none of their data - see
[What this deliberately does not do](#what-this-deliberately-does-not-do).

---

## What state it is in

Honest, and specific. The scaffold shipped 2026-09-06. Read `ROADMAP.md` for the
live version of this list; what follows is its shape.

**Real and tested:**

- **The forecaster.** Pity curves, soft-pity ramps, the 50/50 and its guarantee
  behaviour, and multi-copy targets, computed with an absorbing Markov chain
  rather than a binomial. It is correct for the current game version and its
  three easy-to-get-wrong constants are regression-tested. See
  [What the forecaster actually models](#what-the-forecaster-actually-models).
- **The scaffold around it.** Both suites run, lint and types are clean, the
  headless lane passes its smoke test, and the supervisor, health file and git
  hooks all work end to end.

**Real, but empty:**

- **The cost tables.** `data/costs/` holds its contract README and no data rows.
  Ascension, talent and weapon costs must come from first-hand observation, and
  the account behind this
  project has not been played yet, so no first-hand data exists. Figures that
  arrived from a web assistant are deliberately kept OUT of `data/`, and
  `tests/test_goal_spec.py` fails if anyone copies them in.
- **The objective DAG.** `engines/objectives.py` is mechanism only. It produces a
  structurally correct dependency graph - the right nodes, in the right order,
  with cycle detection and a critical path - and every material quantity in it is
  zero, because nothing supplies them yet. Correct shapes, empty costs.
- **The scheduler.** Resin-aware, weekday-rotation aware and weekly-lockout
  aware, but it has no dating layer: it emits day offsets, and nothing yet turns
  an offset into a calendar date.

**Exists, mostly not wired:**

- **The dashboard.** `surface/` serves it on 8791 and `shell/` is an Electron
  companion with a system tray (ADR-005). Several panels are not live yet.
  A panel that is not wired says what it is waiting on rather than showing a
  placeholder number, which is a deliberate design rule and not a stopgap.
- **The concurrency governor.** `ops/loop/` holds two files that bound how many
  headless Claude cycles run at once across three projects sharing this machine.
  They are byte-identical-by-contract with the other two participants and pinned
  by digest in `tests/test_loop_concurrency.py`, because a divergence there is
  not a merge conflict anyone notices - it is a silent concurrency bug.
  **Nothing in this repository acquires a slot yet.** `headless/runner.py` is a
  job runner, not a Claude-executor loop, so this is a parity contract joined
  ahead of need rather than a live throttle. It is listed here rather than under
  "real and tested" for exactly that reason: the guard is tested, the throttle
  is not in use. Of interest outside this project mainly as a worked example of
  keeping a file identical across repositories that cannot import each other.
  **If you copy it, read the leak note in `docs/LEDGER.md` first.** Under
  Windows contention `hold()` leaks lockfiles, and a leaked lock whose holder is
  still alive is unreapable until the 4.5-hour age arm clears it. Measured here
  and reported to both siblings; not fixed in this tree, because re-pinning a
  byte-identical file is a joint act across three repositories rather than a
  local edit.

---

## What this deliberately does not do

Load-bearing, not modesty. Each of these is a decision with a record behind it.

- **It vendors no game data.** Not one row. `data/fixtures/` is a small
  hand-authored set of publicly known identifiers for tests. The reasoning and
  the survey of what was rejected are in `docs/LICENSE_NOTES.md` and ADR-002.
- **It is not a wiki scrape, and it is not a wiki mirror.** No upstream dataset
  is ingested, and the projects that would have made that easy were examined and
  refused on licence grounds rather than overlooked.
- **It does not automate, modify, or touch the game client.** No macros, no input
  injection, no packet capture, no memory reading, no file patching. The only
  external data it reads is a player's own public character showcase through
  Enka.Network's published API.
- **It does not enumerate UIDs.** The Enka client refuses bulk enumeration, sends
  a required custom User-Agent, and honours the `ttl` on every response. That is
  enforced in `ingest/enka_client.py`, not just promised here.
- **It does not let unverified numbers into `data/`.** A figure without
  first-hand provenance stays in prose where it can be argued with. See
  `docs/GOAL_SPEC_SEED_TEAM.md`, which stamps every claim verified, unverified,
  time-sensitive or refuted.
- **It is not affiliated with HoYoverse**, and it is not commercial.

---

## Quickstart

Requires Python 3.11 or newer.

**Shell convention:** every block below is PowerShell, because this project is
developed and operated on Windows and PowerShell 5.1 is the shell that ships
with it. Where a command differs meaningfully on a POSIX shell, both are shown.
Two differences bite immediately and are the reason the convention is stated
rather than assumed. First, `export VAR=...` is not PowerShell - it errors with
"the term 'export' is not recognized". Second, `curl` in PowerShell 5.1 is an
alias for `Invoke-WebRequest`, and `curl -s <url>` fails in a way that is worse
than a clean error: `-s` is not rejected, it BINDS, resolving unambiguously to
`-SessionVariable` because that is the only parameter starting with "s". Your
URL is swallowed as the session-variable name, `Uri` is then missing, and an
interactive console PROMPTS for it - so the shell appears to hang rather than
telling you anything. Measured on PowerShell 5.1.19041.6456.

### 1. Clone and install the hooks

**Do this first.** `core.hooksPath` is local git config and is not cloned, so a
fresh clone runs **zero** hooks until you set it. The tracked `.githooks/`
directory is inert until then.

```powershell
git clone https://github.com/Remus3/Resin-Compute.git
cd Resin-Compute
python scripts/install_hooks.py
```

#### A path with a space in it is a supported, deliberately exercised case

Clone anywhere you like. One thing worth knowing if you pick a path containing a
space - `C:\Resin Compute`, say - is that this is a case the project treats as a
test rather than as a hazard to avoid. The whole tree has been run from a
space-containing path: ruff, both suites, the headless smoke test, the bootstrap
script and the supervisor dry-run all pass, and the git hooks fire and block a
banned glyph with HEAD unchanged.

The pieces that make that work are load-bearing, so do not "simplify" them:

- `.githooks/*` quote every expansion (`"$ROOT/..."`, `"$PY"`), and `$ROOT` comes
  from `git rev-parse --show-toplevel`, which returns the space.
- `ops/supervisor.py` builds its child command as a LIST and never passes
  `shell=True`, so nothing re-parses the path.
- `ops/install_scheduled_task.ps1` uses `-LiteralPath` and `Join-Path`, and
  concatenates rather than interpolates.
- `ops/ResinCompute-Supervisor.xml` keeps `<Command>`, `<Arguments>` and
  `<WorkingDirectory>` as separate elements, so Task Scheduler handles the space
  natively and no manual quoting is needed.

Any new script that touches the install path must hold to the same rules.

### 2. Install dev dependencies

Runtime is stdlib only. Only the dev toolchain needs installing.

```powershell
python -m pip install -r requirements-dev.txt
```

### 3. Run the test suites

Two suites, run **separately**. Never `pytest .` from the root.

```powershell
python -m pytest tests                  # application suite
python -m pytest agents/pity_engine     # engine self-validation
```

Lint and types:

```powershell
python -m ruff check .
python -m mypy
```

### 4. Bootstrap static data

Offline by default. It normalizes the local hand-authored fixtures into the
internal schema without touching the network.

```powershell
python scripts/bootstrap_data.py --offline --dry-run   # show what it would do
python scripts/bootstrap_data.py --offline             # write it
```

To pull a live profile you must set a User-Agent first, because upstream policy
requires one and the client refuses to send a default:

```powershell
$env:ENKA_USER_AGENT = "ResinCompute/0.1 (contact: you@example.com)"
python scripts/bootstrap_data.py --uid 618285856
```

On a POSIX shell the first line is `export ENKA_USER_AGENT="..."` instead.

The UID above is Enka.Network's own published example UID, taken from their API
documentation - it is not a real player's account and not an operator's, and it
is used here so the command is copy-pasteable. Substitute your own.

### 5. Run the headless lane

One pass and exit:

```powershell
python -m headless.runner --once
python -m headless.runner --once --dry-run     # compute and log, write nothing
python -m headless.runner --list-jobs
python -m headless.runner --job forecast_pity
```

The four commands above each run and exit, so they belong in one console.
**Everything from here on does not.** The daemon and the supervisor run in the
FOREGROUND until you stop them, so each of the blocks below is a separate
console. Read them as "leave this running, then open another window", not as a
script to paste in one go.

Continuously, as a background worker - console A:

```powershell
python -m headless.runner --daemon --interval 300
```

Or under supervision, with restart-on-crash and a heartbeat - also console A,
instead of the above:

```powershell
python -m ops.supervisor
```

Trigger a supervised restart from console B by writing any content to the
trigger file. The supervisor clears it and restarts within about five seconds.
Only existence is tested, never the bytes, so PowerShell's UTF-16LE redirect is
harmless here:

```powershell
echo restart > restart_trigger.txt
```

Confirm it came back by reading the health file, not by looking at a window -
console B again:

```powershell
python -c "import json;print(json.dumps(json.load(open('ops/runtime/health.json')),indent=2))"
```

#### The Windows Scheduled Task, and how to remove it

Nothing above installs it and the Quickstart does not need it. But
`ops/install_scheduled_task.ps1` is there, it registers
`ops/ResinCompute-Supervisor.xml` so the supervisor comes up unattended, and it
is the one thing in this repository that OUTLIVES THE CLONE. Know what it is
before you run it.

Read off the XML, not from memory:

- **It fires at EVERY LOGON.** A logon trigger is the only trigger it has.
- **It runs at the HIGHEST AVAILABLE privilege** the account can obtain.
- **It is HIDDEN.** Task Scheduler does not list it until "Show hidden tasks" is
  on, so it is easy to look straight past when auditing what starts with your
  session.
- **It has NO execution time limit.** The field is `PT0S`, which for this
  setting means unlimited rather than zero.
- **It restarts itself on failure**, three times, a minute apart.
- **Its working directory is baked in at install time.** Move or delete the
  checkout and the task keeps firing at a path that is no longer there.

**Deleting the repository does not remove it.** The definition lives in the
Windows Task Scheduler store, not in the clone, so `rm -rf` on the checkout
leaves a hidden elevated task starting at every logon against a directory that
has gone. Remove it explicitly:

```powershell
Get-ScheduledTask -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName 'ResinCompute-Supervisor' -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'ResinCompute-Supervisor' -Confirm:$false
```

Elevate the console if any of those is denied - the task is registered at the
highest available privilege. `ResinCompute-Supervisor` is the installer's
default `-TaskName`; if you passed your own, the task is under that name and
these commands need it instead.

If a supervised process is still running afterwards, take its pid from
`ops/runtime/health.json` and use `taskkill /F /PID <pid>`. Never `Stop-Process`
- see Conventions.

### 6. Run the PityEngine service

The engine runs in the FOREGROUND and does not return, so these are two
consoles, not two lines. Start it in the first:

```powershell
python -m agents.pity_engine --port 8790
```

Then, in a SECOND console:

```powershell
Invoke-RestMethod http://127.0.0.1:8790/health
```

A forecast is a POST. Building the body as a hashtable avoids quoting it by
hand, which is where the POSIX `curl` form does not survive translation:

```powershell
$body = @{
  banner                  = 'character_event'
  pity_5star              = 74
  has_guarantee           = $false
  consecutive_5050_losses = 0
  target_count            = 1
  pull_budget             = 30
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8790/forecast `
  -ContentType 'application/json' -Body $body
```

The POSIX equivalent, for reference:

```bash
curl -s http://127.0.0.1:8790/health
curl -s -X POST http://127.0.0.1:8790/forecast \
  -H 'Content-Type: application/json' \
  -d '{"banner":"character_event","pity_5star":74,"has_guarantee":false,
       "consecutive_5050_losses":0,"target_count":1,"pull_budget":30}'
```

### 7. Run the dashboard

```powershell
python -m surface --port 8791
```

On Windows, launch background daemons with `pythonw.exe` rather than
`python.exe` so no console window flashes.

---

## Repository tree

Guarded by `tests/test_readme_tree.py`, which asserts that every path named here
exists AND is stored by git. A directory that resolves on one machine but holds
nothing git tracks is absent from every clone, so existence alone is not enough.

```
Resin-Compute/
  README.md                        this file
  CLAUDE.md                        agent context, hard rules, session workflow
  ROADMAP.md                       open work, newest priorities first
  NEXT_SESSION_PROMPT.md           operator hand-off, republished each session
  LICENSE                          GPL-3.0-or-later, verbatim and hash-pinned
  NOTICE                           copyright line and the game-data disclaimer
  ruff.toml                        lint config, ported from Riot Commander
  pytest.ini                       dual-suite config, never run pytest . at root
  mypy.ini                         type config
  conftest.py                      root sys.path hook, reaches BOTH suites
  requirements.txt                 runtime deps, deliberately empty, stdlib only
  requirements-dev.txt             ruff, pytest, mypy
  .gitattributes                   pins eol=lf, guarded by a test
  .gitignore                       runtime state, caches, node_modules

  .claude/                         the agent roster and the session commands
    agents/                        planner, builder, verifier, adversary, others
    commands/                      orchestrated-run, done, ui-audit

  .githooks/                       AUTHORITATIVE gate, inert until installed
    pre-commit                     banned glyphs, py_compile, net-new ruff
    commit-msg                     trailer policy
    pre-push                       both suites

  .github/
    workflows/
      ci.yml                       lint, py_compile, mypy, both suites, smoke
      docs-guards.yml              fires on exactly what ci.yml declines

  core/                            the shared contract and the primitives
    types.py                       every dataclass the other packages agree on
    atomic_io.py                   the ONLY sanctioned state-write path
    state_io.py                    AccountState snapshot serialization
    log_setup.py                   single daily log file, no rotation
    config.py                      live-state-first env config
    ledger.py                      event-sourced currency operations
    resin.py                       resin regeneration, caps, condensed, fragile
    domains.py                     weekday rotation and weekly boss resets
    ports.py                       the single owner of this project's port block

  agents/
    pity_engine/                   PityEngine - pure deterministic forecaster
      __init__.py                  ENGINE_VERSION, single source of truth
      banners.py                   hazard tables and soft-pity ramps, all four
      markov.py                    absorbing Markov chain DP
      forecast.py                  public API
      __main__.py                  stdlib HTTP service on 8790
      CHANGELOG.md                 engine version history
      tests/                       the engine validates itself

  engines/                         planning and optimization, mechanism only
    objectives.py                  goal DAG, cycle detection, critical path
    scheduler.py                   resin, rotation and weekly lockout aware
    recommend.py                   what to get / who to build solver

  ingest/                          external data, re-implemented from protocol
    enka_client.py                 stdlib urllib, ttl-honouring, policy bound
    enka_mapper.py                 raw payload to EnkaMappedProfile
    static_data.py                 id to name lookup over local fixtures

  headless/                        THE headless lane
    runner.py                      non-interactive entrypoint, CLI and daemon
    jobs.py                        job registry, per-job isolation

  surface/                         the dashboard, served on 8791
    __main__.py                    entrypoint
    server.py                      stdlib HTTP, no framework
    model.py                       pure model, decides panel readiness
    render.py                      HTML rendering

  shell/                           Electron companion with a tray, ADR-005
    main.js                        window, tray and supervisor lifecycle
    preload.js                     the isolated bridge
    lib/                           endpoint, geometry, state, supervisor, tray
    test/                          node test runner, no browser
    package.json                   devDependency on electron and nothing else

  ops/                             supervision and operational state
    supervisor.py                  watchdog, restart trigger, bounded backoff
    health.py                      the health.json contract
    ResinCompute-Supervisor.xml    hidden ONLOGON task, elevated, no time limit
    install_scheduled_task.ps1     registers it - removal is in Quickstart 5
    runtime/                       health.json is written here, gitignored
    loop/                          shared cross-repo concurrency governor
      slots.py                     BYTE-IDENTICAL across three repos, never edit alone
      winmutex.py                  BYTE-IDENTICAL across three repos, never edit alone

  scripts/
    install_hooks.py               FIRST thing to run in a fresh clone
    bootstrap_data.py              runnable data bootstrap
    qa_companion.py                end-to-end probe of the companion surface
    make_shortcut.py               desktop shortcut for the companion
    hook_python.sh                 interpreter resolution shared by the hooks
    precommit_pycompile.py         syntax gate
    precommit_msg_check.py         commit message gate

  tools/
    precommit_gate.py              banned-glyph and net-new-ruff gate
    publish_next_session.py        publishes the hand-off backup

  data/
    fixtures/                      hand-authored fixtures, nothing vendored
    costs/                         empty on purpose, first-hand tables only

  docs/
    SPEC_SCAFFOLD.md               the build contract, verified constants
    LEDGER.md                      append-only completion history, newest first
    GOAL_SPEC_SEED_TEAM.md         the seed-team goal, every claim stamped
    LICENSE_NOTES.md               inbound posture, read before adding a source
    adr/                           architectural decisions, indexed

  tests/                           the application suite
    _parked/                       quarantined tests, deliberately not collected
```

---

## What the forecaster actually models

Three things in the originating brief were wrong, and the engine deliberately does
not implement them as written. All three are regression-tested.

**The 50/50 has not been 50/50 since version 5.0.** Capturing Radiance converts
some non-guaranteed 5-stars to the promotional character, and HoYoverse publishes a
consolidated rate-up probability of 55.000%, with a hard cap making four consecutive
losses impossible. The engine models a per-roll probability of 0.52106 plus a forced
win at three consecutive losses, which is the simple model that reproduces the
official aggregate. A flat 0.55 with the same cap overshoots to 57.35%.

**The weapon soft-pity curve cannot run to pull 79.** With a 7% per-pull ramp from
pull 63, the probability reaches 0.987 at pull 76 and would be 1.057 at pull 77, so
it saturates at 77. The brief's "increasing 7% per pull up to pull 79" is
arithmetically impossible. The increment is exposed as a tunable because the exact
micro-curve is not pinned by public data.

**A probability of success needs a pull budget.** The brief's
`calculateProbabilityOfSuccess(stats, targetCount)` has no answer without one, so
the real signature takes `pull_budget`. The result is computed with an absorbing
Markov chain over `(copies, pity, guarantee, loss_streak)`, never a binomial on
1.6% - that figure is `1 / E[wishes per 5-star]`, a long-run average, and is not a
per-wish probability at any point.

Full derivations and sources are in `docs/SPEC_SCAFFOLD.md` section 3, and the
corrections are recorded in ADR-003.

---

## Why the stack is Python

Recorded in ADR-001 (`docs/adr/ADR-001-stack.md`); this is a summary of the
decision, not an argument being had.

This project inherits its entire engineering discipline - lint config, dual-suite
test layout, git hooks, CI shape, the supervisor and health-file operational
model - from a sibling project of the same author's. That sibling is a Python
tree: its inherited config surface is `ruff.toml`, `pytest.ini`, `mypy.ini` and
`.githooks/`, with no `package.json`, no Biome, no ESLint and no Vitest anywhere
in it. Measured 2026-09-06.

An early draft specified a TypeScript toolchain while also asking for that
inheritance. The two are mutually exclusive, and Python was chosen so the
inheritance is real rather than nominal. The interfaces that draft named are
delivered as Python dataclasses in `core/types.py`.

ADR-001 was not reopened when the dashboard landed. Its subject is the language
of the compute tree, and the surface is Python too.

---

## Ports

Seven projects share the Legion box and every one of them runs concurrently, so
each reserves a block. **ResinCompute reserves 8790-8809** (`rsc`).

| Port | Purpose |
|---|---|
| 8790 | PityEngine HTTP |
| 8791 | Dashboard surface |
| 8792-8809 | unassigned |

`core/ports.py` is the single owner of these numbers in CODE: no other tracked
`.py` file restates them, and `tests/test_ports.py` pins each against the module
that really binds it rather than re-asserting the literal. Prose is a different
matter - this README quotes 8790 and 8791 in several places, and the guard does
not sweep Markdown, so treat `core/ports.py` as the authority whenever a
document and the module disagree.

The scaffold originally put the engine on 8870, which sits inside Daemon
Slayer's reserved 8860-8879. Nothing was listening there, so nothing broke and
nothing warned. ADR-004 records the migration, and a guard test now fails on any
sibling port literal appearing anywhere in tracked Python source.

Verify a band against the owning project's registry in source, never against a
live scan. That rule is Clockspeed's, learned the hard way, and it is the one
this block was checked with.

---

## Third-party data posture

Read `docs/LICENSE_NOTES.md` before adding any data source. The short version,
from a verification pass on 2026-09-06:

- **No game data is vendored into this repo.** `data/fixtures/` is a small
  hand-authored set of publicly known identifiers, for tests only.
- `Dimbreath/GenshinData` is **404 and DMCA'd**; its live successor carries **no
  licence at all**. It is not an ingest target.
- `genshin-db` is MIT for its author's code, but its payload derives from a
  CC BY-SA wiki and unlicensed datamined files. The MIT badge does not clear the data.
- `enka-py` and `ambr-py` are both **GPL-3.0**, and this tree is now
  GPL-3.0-or-later, so copyleft is no longer the objection - ADR-006 dissolved
  that one and no others. They still are not vendored, for the reason that
  always mattered: both wrap HoYoverse-copyright game data, and a licence on a
  wrapper cannot grant rights to its payload. The Enka client here is therefore
  re-implemented from the published protocol. Protocol facts are not
  copyrightable; source is.
- Every upstream wraps HoYoverse-copyright assets regardless of its own licence.

The Enka client complies with published policy: it sends a required custom
User-Agent, honours the `ttl` on every response, and refuses bulk UID enumeration.

---

## Conventions

- **ASCII only.** No em-dashes, no en-dashes, no smart quotes, anywhere in authored
  text including code, comments, docs and commit messages. The hooks enforce it.
  A UTF-8 em-dash inside a double-quoted PowerShell string ANSI-decodes into a
  smart quote that terminates the string and cascades into a parse failure.
- **Atomic writes only.** `tmp.write_text(...); tmp.replace(target)` via
  `core/atomic_io.py`. Readers poll mid-write.
- **`py_compile` before restart.** A syntax error crashes silently under `pythonw.exe`.
- **Never `Stop-Process` on Windows.** Use `taskkill /F /PID`.
- **Live-state-first.** Derive state from the current response only.
- **Never surface a raw API or error string** to a user-facing surface. Catch it,
  render a friendly degraded state, log the raw error.

## Licence

**GPL-3.0-or-later.** See `LICENSE` for the full text and `NOTICE` for the
copyright line. ADR-006 records why.

The short version: you may use, study, modify and redistribute this, including
commercially, but any derivative you distribute must carry the same licence and
its source must be available. It cannot be taken closed-source.

That is an OUTBOUND licence and it covers this project's own code only. It
grants nothing over Genshin Impact's data, names, statistics or assets, which
belong to HoYoverse. For the INBOUND question - what this project is allowed to
consume - see `docs/LICENSE_NOTES.md`, which is a separate matter.
