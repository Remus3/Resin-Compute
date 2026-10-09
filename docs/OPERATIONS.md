# ResinCompute - running and operating the tree

The landing page is `README.md` and its Quickstart is the short path. This file
is the long one: the full run recipes, the scheduled tasks and how to remove
them, the port block, the space-in-path guarantee and the house conventions.
Project status, the forecaster's model and the data posture are in
`docs/OVERVIEW.md`.

Every block is PowerShell, because this is developed and operated on Windows.
Two POSIX habits bite: `export VAR=...` is not PowerShell, and `curl` there is
an alias for `Invoke-WebRequest` whose `-s` binds silently to
`-SessionVariable`, so the console appears to hang instead of erroring.

## Hooks come first

`core.hooksPath` is local git config and is not cloned, so a fresh clone runs
**zero** hooks - `.githooks/` is inert until `python scripts/install_hooks.py`
has run. There are three: `pre-commit` gates banned glyphs and net-new lint,
`commit-msg` shapes the message, and `pre-push` runs both suites before anything
leaves the machine.

## A path with a space in it is supported and tested

Clone anywhere. A `<checkout>` whose path holds a space is exercised with
ruff, both suites, the headless smoke test and the supervisor dry-run. Four
pieces make that work, so do not "simplify" them:

- `.githooks/*` quote every expansion, and `$ROOT` comes from
  `git rev-parse --show-toplevel`, which returns the space.
- `ops/supervisor.py` builds its child command as a LIST, never `shell=True`.
- `ops/install_scheduled_task.ps1` uses `-LiteralPath` and `Join-Path`.
- `ops/ResinCompute-Supervisor.xml` keeps `<Command>`, `<Arguments>` and
  `<WorkingDirectory>` as separate elements.

## The gates

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

## Bootstrap static data

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

## The engine, the lane, the supervisor and the dashboard

Both local servers - the engine on 8790 and the dashboard on 8791 - default
their bind address to `127.0.0.1`, and **neither authenticates**. A host
override is a command-line flag on each. Do not expose either to a network you
do not control.

The first four commands below run and exit, so they share a console. **The last
three run in the FOREGROUND until you stop them**, so each needs its own.

```powershell
python -m headless.runner --once
python -m headless.runner --once --dry-run       # compute and log, write nothing
python -m headless.runner --list-jobs
python -m headless.runner --job forecast_pity

python -m headless.runner --daemon --interval 300
python -m ops.supervisor                         # the same worker, supervised
python -m surface --port 8791                    # the dashboard
```

A live `--once` pass holds a machine-wide lane slot, exactly as each daemon
pass does. When the bucket is full it waits roughly 300 seconds plus one retry
interval - the governor checks its deadline and then sleeps 2 to 4 seconds
before trying again, so the wait overruns the timeout by up to about 4 seconds -
and then fails with exit code 1; `--dry-run` takes no slot.

Under the supervisor, writing any content to `restart_trigger.txt` triggers a
restart within about five seconds. Confirm it came back by reading the health
file for a new pid, never by looking at a window:

```powershell
python -c "import json;print(json.dumps(json.load(open('ops/runtime/health.json')),indent=2))"
```

On Windows, launch background daemons with `pythonw.exe` rather than
`python.exe` so no console window flashes.

The engine's HTTP API is `GET /health` (engine version, pid and uptime) and
`POST /forecast`. A malformed request returns HTTP 400 with a friendly message -
the raw exception goes to the log, never into the body. The same forecast call
on a POSIX shell, which is what the project's own CI runs:

```bash
curl -s http://127.0.0.1:8790/health
curl -s -X POST http://127.0.0.1:8790/forecast \
  -H 'Content-Type: application/json' \
  -d '{"banner":"character_event","pity_5star":74,
       "has_guarantee":false,"consecutive_5050_losses":0,
       "target_count":1,"pull_budget":30}'
```

## The Windows scheduled tasks, and how to remove them

Nothing in the Quickstart installs either of these and nothing needs them. But
this repository ships TWO scheduled-task installers, and a registered task
OUTLIVES THE CLONE: the definition lives in the Windows Task Scheduler store,
not in the checkout, so **deleting the repository does not remove it.**

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

## On `ops/loop/` and its two carrier populations

Each module is pinned across ITS OWN population, and the two are measured by
separate sweeps at separate instants, so a single numeral over the directory is
the wrong summary however it is counted. Both populations currently hold FIVE
roots and those five are the same roots, which is a coincidence of two
snapshots and not a directory-wide fact - what still separates them is BYTES,
not membership: every carrier of `ops/loop/slots.py` is at the pinned digest,
while on `ops/loop/winmutex.py` one root holds a different file and another is
still at a superseded digest. A sixth fleet root carries neither module. Those
rows are a SNAPSHOT OF OTHER REPOSITORIES' DISKS and they decay - one of them
flipped inside a single day when a root committed a file it had been holding
untracked - and nothing in this tree can poll a foreign disk. **The stamped rows
live in exactly one place: `tests/test_loop_concurrency.py`, in the populations
block above `SLOTS_CARRIERS`.** It carries the per-name status, the instant and
the sweep commands, and only a person re-running that sweep refreshes them. Read
them there rather than trusting the summary here; a second copy of a decaying
row is a second thing to re-measure.

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
