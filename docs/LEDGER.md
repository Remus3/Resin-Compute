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

Also fixed: a test wrote a Windows path without a raw string, so `` became a
literal BEL and `\o` an invalid escape. The test still PASSED, because it only
asserted inequality, so the defect was invisible until a SyntaxWarning surfaced
it. And `test_a_stopped_server_releases_its_port_immediately` was flaky by
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
