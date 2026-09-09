# Security policy

ResinCompute is a non-commercial, single-maintainer companion and analysis
project. It is not a service, it hosts nothing, and it stores no user accounts.
The realistic risk surface is therefore small but not empty, and this file says
what it is and how to report a problem in it.

## Reporting a vulnerability

**Please do not open a public issue, pull request or discussion for a security
problem.**

Report it privately through GitHub, which routes it to the maintainer without
publishing anything:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Or go straight there:
   https://github.com/Remus3/Resin-Compute/security/advisories/new

That opens a private security advisory draft visible only to you and the
maintainer. There is deliberately no email address in this file.

Helpful things to include, in whatever detail you have:

- What you did, what happened, and what you expected instead.
- The commit or branch you were on.
- Your operating system and Python version.
- A minimal reproduction if you have one, and the smallest input that triggers it.
- Whether you believe it is exploitable, and how.

**Please do not include real credentials, real account identifiers or personal
data in a report.** If a credential is part of the reproduction, describe its
shape rather than pasting it, and rotate it.

## What to expect

This is a one-person, unpaid project, so no response time is promised and it
would be dishonest to publish one. What is committed to:

- Reports are read, and you will get an acknowledgement rather than silence.
- A confirmed issue is fixed on the default branch, with a test where the defect
  is testable at all.
- You will be credited in the advisory if you want to be, and not if you do not.
- If a report turns out to describe intended behaviour, you will be told which
  behaviour and where it is documented, rather than having the report closed
  without explanation.

Please give a reasonable window before disclosing publicly. There are no users
downstream of a release to protect - see below - so the window exists to get the
fix right, not to manage an announcement.

## Supported versions

**There are no tagged releases.** Verified against the repository itself: it
carries no git tags, and it publishes no package from this tree - the runtime
declares no third-party dependency and the Node side declares only the window
toolkit, both pinned by `tests/test_licence_posture.py`. If you found this code
republished somewhere as a package, that copy is not this project's and is not
supported here.

| Version | Supported |
|---|---|
| `main`, at the current commit | Yes |
| Any older commit | No |

Fixes land on `main`. If you are running an older checkout, update it.

## Scope

**In scope** - the code in this repository:

- Path handling, file writes and the atomic-write path in `core/atomic_io.py`.
- The Enka client and mapper in `ingest/`, which parse a remote JSON payload.
- The local HTTP services: the engine on 8790 and the dashboard on 8791. Both are
  stdlib servers, both default their bind address to `127.0.0.1`, and neither
  authenticates. A host override is a command-line flag on each. **Do not expose
  either to a network you do not control.** If you find a way to make them
  reachable or exploitable in their default loopback configuration, that is in
  scope.
- The Electron companion in `shell/`.
- The supervisor and the Windows scheduled task in `ops/`.
- Anything in the tree that could disclose a credential, a machine identity or a
  local path belonging to the operator.

**Out of scope**, and please report these to the party that owns them:

- Genshin Impact itself, HoYoverse, miHoYo or Cognosphere. This project is not
  affiliated with, endorsed by, or connected to any of them. It does not
  automate, modify or touch the game client: no macros, no input injection, no
  packet capture, no memory reading and no file patching.
- Enka.Network's own service and infrastructure. This project is a client of
  their published API and follows their published policy - a required custom
  User-Agent, the response `ttl` honoured, and no UID enumeration.
- Any third-party dataset or wrapper library. None is vendored here; see
  `docs/LICENSE_NOTES.md`.
- Vulnerabilities in Python, Node, Electron or your operating system, unless this
  repository's code is what makes them reachable.

## Things that are documented rather than hidden

Two properties look alarming in a scan and are deliberate. Both are already
written down, so please read these before filing:

- **The Windows scheduled task.** `ops/install_scheduled_task.ps1` registers
  `ops/ResinCompute-Supervisor.xml`, which fires at every logon, runs at the
  highest privilege the account can obtain, is hidden from the default Task
  Scheduler view, and has no execution time limit. Nothing installs it for you
  and the quickstart does not need it. It is the one thing in this repository
  that OUTLIVES THE CLONE: deleting the checkout leaves the task behind, still
  firing at a path that has gone. `README.md` states all of that and gives the
  removal commands.
- **The Wish History credential tool.** `tools/wish_authkey.py` extracts a
  short-lived authkey that the game itself writes into its own webview cache on
  the operator's machine. It is split into separate scan, capture and pull verbs
  precisely so that reading is not the same act as saving, and a captured
  credential is written outside this git tree by design. A change that lets a
  captured authkey reach the repository, a log or a console IS a vulnerability -
  please report it.

## What this project already guards

Stated so a report can build on it rather than rediscover it:

- No tracked file may carry an API key or token as a literal, enforced by
  `tests/test_no_secret_literals.py` on vendor-prefixed token shapes and on known
  secret variable names bound to literals, rather than on a naive high-entropy
  rule that would have to be deleted.
- The operator's machine identity - account names and absolute user paths - must
  not appear in tracked files. `tests/test_machine_identity.py` is that guard.
- The commit-time gate is fail-closed: the hooks error rather than pass content
  they never scanned.

None of that makes a finding invalid. If one of these guards can be bypassed, the
bypass is exactly the kind of report this file is asking for.

## Conduct

Security reports are covered by `CODE_OF_CONDUCT.md` like any other
participation.
