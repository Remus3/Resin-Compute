# ResinCompute

Genshin Impact progression tracking, resource economics, goal planning and
roster optimization. Headless-lane first: every calculation runs non-interactively
from a CLI or a daemon, with no UI required.

Built on the Riot Commander blueprint - same lint, test, hook and CI discipline,
same supervisor and health-file operational model, same two-tier naming where the
repo holds a versioned pure compute engine inside it.

- **Repo:** ResinCompute
- **Compute engine:** PityEngine (`agents/pity_engine/`, HTTP `:8790`)

---

## Why the stack is Python

The brief that started this repo asked for TypeScript, Biome and Vitest while also
asking it to inherit Riot Commander's complete config and testing pipeline. Those
are mutually exclusive. Measured on 2026-09-06, Riot Commander is 2869 `.py` files
against 1 generated `.d.ts`, with no `package.json`, no `tsconfig.json`, no Biome,
no ESLint, no Prettier, no Vitest, no Jest and no Docker anywhere in the tree. Its
inherited config surface IS `ruff.toml`, `pytest.ini`, `mypy.ini` and `.githooks/`.

Python was chosen so the inheritance is real rather than nominal. The TypeScript
interfaces named in the brief are delivered as Python dataclasses in
`core/types.py`. See `docs/adr/ADR-001-stack.md`.

---

## Repository tree

```
resin-compute/
  README.md                     this file
  CLAUDE.md                     agent context, hard rules, session workflow
  ROADMAP.md                    open work
  ruff.toml                     lint config, ported from Riot Commander
  pytest.ini                    dual-suite config, never run `pytest .`
  mypy.ini                      type config
  conftest.py                   root sys.path hook, reaches BOTH suites
  requirements.txt              runtime deps (deliberately empty, stdlib only)
  requirements-dev.txt          ruff, pytest, mypy

  .githooks/                    AUTHORITATIVE gate. A fresh clone runs NONE of
    pre-commit                  these until install_hooks.py sets core.hooksPath
    commit-msg
    pre-push

  .github/workflows/
    ci.yml                      lint, py_compile, mypy, both suites, headless smoke
    docs-guards.yml             fires on exactly what ci.yml declines (.md only)

  core/                         shared contract and primitives
    types.py                    AccountState, CurrencyLedger, PityState,
                                ObjectiveNode, ResolutionPath, EnkaMappedProfile
    atomic_io.py                the ONLY sanctioned state-write path
    log_setup.py                single daily log file, no rotation
    config.py                   live-state-first env config
    ledger.py                   event-sourced currency operations
    resin.py                    resin regeneration, caps, condensed and fragile
    domains.py                  weekday rotation and weekly boss reset mechanics

  agents/pity_engine/           PityEngine - pure deterministic forecaster
    __init__.py                 ENGINE_VERSION, single source of truth
    banners.py                  hazard tables for all four banner families
    pity.py                     pity curve evaluation
    markov.py                   absorbing Markov chain DP
    forecast.py                 public API
    __main__.py                 stdlib HTTP service on :8790
    CHANGELOG.md
    tests/                      the engine validates itself

  engines/                      planning and optimization
    objectives.py               goal DAG, cycle detection, critical path
    scheduler.py                resin, weekday rotation and weekly lockout aware
    recommend.py                what to get / who to build solver

  ingest/                       external data, re-implemented from protocol
    enka_client.py              stdlib urllib, ttl-honouring, policy compliant
    enka_mapper.py              raw payload to EnkaMappedProfile
    static_data.py              id to name lookup over local fixtures

  headless/                     THE headless lane
    runner.py                   non-interactive entrypoint, CLI and daemon
    jobs.py                     job registry, per-job isolation

  ops/                          supervision and operational state
    supervisor.py               watchdog, restart_trigger.txt, bounded backoff
    health.py                   ops/runtime/health.json contract
    ResinCompute-Supervisor.xml Windows Scheduled Task, ONLOGON
    install_scheduled_task.ps1
    runtime/                    health.json lives here, gitignored

  scripts/
    bootstrap_data.py           runnable data bootstrap
    install_hooks.py            FIRST thing to run in a fresh clone
    precommit_pycompile.py
    precommit_msg_check.py

  tools/
    precommit_gate.py           banned-glyph and net-new-ruff gate

  data/fixtures/                SYNTHETIC test fixtures only, nothing vendored

  docs/
    SPEC_SCAFFOLD.md            the build contract, verified constants
    ARCHITECTURE.md
    LICENSE_NOTES.md            third-party posture, read before adding a source
    adr/                        architectural decisions

  tests/                        application suite
```

---

## Quickstart

Requires Python 3.11 or newer.

### 1. Clone and install the hooks

**Do this first.** `core.hooksPath` is local git config and is not cloned, so a
fresh clone runs **zero** hooks until you set it. The tracked `.githooks/`
directory is inert until then.

On Legion, the canonical checkout is `C:\Resin Compute`:

```powershell
git clone https://github.com/Remus3/Resin-Compute.git "C:\Resin Compute"
cd "C:\Resin Compute"
python scripts/install_hooks.py
```

The install path contains a space, deliberately, matching `C:\Riot Commander\`.
That is verified rather than assumed: the whole tree was run from a
space-containing path before this was written - ruff, both suites, the headless
smoke test, the bootstrap script and the supervisor dry-run all pass, and the
git hooks fire and block a banned glyph with HEAD unchanged.

The pieces that make it safe are load-bearing, so do not "simplify" them:

- `.githooks/*` quote every expansion (`"$ROOT/..."`, `"$PY"`), and `$ROOT`
  comes from `git rev-parse --show-toplevel`, which returns the space.
- `ops/supervisor.py` builds its child command as a LIST and never passes
  `shell=True`, so nothing re-parses the path.
- `ops/install_scheduled_task.ps1` uses `-LiteralPath` and `Join-Path`, and
  concatenates rather than interpolates.
- `ops/ResinCompute-Supervisor.xml` keeps `<Command>`, `<Arguments>` and
  `<WorkingDirectory>` as separate elements, so Task Scheduler handles the
  space natively and no manual quoting is needed.

Any new script that touches the install path must hold to the same rules.

### 2. Install dev dependencies

Runtime is stdlib only. Only the dev toolchain needs installing.

```bash
python -m pip install -r requirements-dev.txt
```

### 3. Run the test suites

Two suites, run **separately**. Never `pytest .` from the root.

```bash
python -m pytest tests                  # application suite
python -m pytest agents/pity_engine     # engine self-validation
```

Lint and types:

```bash
python -m ruff check .
python -m mypy
```

### 4. Bootstrap static data

Offline by default. It normalizes the local synthetic fixtures into the internal
schema without touching the network.

```bash
python scripts/bootstrap_data.py --offline --dry-run   # show what it would do
python scripts/bootstrap_data.py --offline             # write it
```

To pull a live profile you must set a User-Agent first, because upstream policy
requires one and the client refuses to send a default:

```bash
export ENKA_USER_AGENT="ResinCompute/0.1 (contact: you@example.com)"
python scripts/bootstrap_data.py --uid 618285856
```

### 5. Run the headless lane

One pass and exit:

```bash
python -m headless.runner --once
python -m headless.runner --once --dry-run     # compute and log, write nothing
python -m headless.runner --list-jobs
python -m headless.runner --job forecast_pity
```

Continuously, as a background worker:

```bash
python -m headless.runner --daemon --interval 300
```

Under supervision, with restart-on-crash and a heartbeat:

```bash
python -m ops.supervisor
```

Trigger a supervised restart the same way Riot Commander does - write any content
to the trigger file and the supervisor clears it and restarts within about five
seconds:

```bash
echo restart > restart_trigger.txt
```

Confirm it came back by reading the health file, not by looking at a window:

```bash
python -c "import json;print(json.dumps(json.load(open('ops/runtime/health.json')),indent=2))"
```

### 6. Run the PityEngine service

```bash
python -m agents.pity_engine --port 8790
curl -s http://127.0.0.1:8790/health
curl -s -X POST http://127.0.0.1:8790/forecast \
  -H 'Content-Type: application/json' \
  -d '{"banner":"character_event","pity_5star":74,"has_guarantee":false,
       "consecutive_5050_losses":0,"target_count":1,"pull_budget":30}'
```

On Windows, launch background daemons with `pythonw.exe` rather than
`python.exe` so no console window flashes.

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

Full derivations and sources are in `docs/SPEC_SCAFFOLD.md` section 3.

---

## Ports

Seven projects share the Legion box and every one of them runs concurrently, so
each reserves a block. **ResinCompute reserves 8790-8809** (`rsc`).

| Port | Purpose |
|---|---|
| 8790 | PityEngine HTTP |
| 8791 | Dashboard surface |
| 8792-8809 | unassigned |

`core/ports.py` is the single owner of these numbers - no other tracked file
restates them, and `tests/test_ports.py` pins each against the module that
really binds it rather than re-asserting the literal.

The scaffold originally put the engine on 8870, which sits inside Daemon
Slayer's reserved 8860-8879. Nothing was listening there, so nothing broke and
nothing warned. ADR-004 records the migration, and a guard test now fails on any
sibling port literal appearing anywhere in tracked Python source.

Verify a band against the owning project's registry in source, never against a
live scan. That rule is Clockspeed's, learned the hard way, and it is the one
this block was checked with.

---

## Third-party data posture

Read `docs/LICENSE_NOTES.md` before adding any data source. The short version, from
a verification pass on 2026-09-06:

- **No game data is vendored into this repo.** `data/fixtures/` is hand-authored
  synthetic content for tests only.
- `Dimbreath/GenshinData` is **404 and DMCA'd**; its live successor carries **no
  licence at all**. It is not an ingest target.
- `genshin-db` is MIT for its author's code, but its payload derives from a
  CC BY-SA wiki and unlicensed datamined files. The MIT badge does not clear the data.
- `enka-py` and `ambr-py` are both **GPL-3.0**. Vendoring either would relicense
  this repo, so the Enka client here is re-implemented from the published protocol.
  Protocol facts are not copyrightable; source is.
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

Private. No licence granted. See `docs/LICENSE_NOTES.md` for third-party obligations.
