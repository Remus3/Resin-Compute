# Completion ledger

Append-only, **newest first**, following the parent project's convention. One
entry per landed unit of work, with what was actually measured rather than what
was intended.

`ROADMAP.md` holds OPEN work. This holds CLOSED work. Neither belongs in
`CLAUDE.md`, and a test count belongs in neither: counts are not guarded and a
document is not a source of truth. Where a count appears below it is stamped with
the date it was measured, as a historical reading rather than as a claim about
now.

This file is now the INDEX. Each session writes its own entry to
`docs/ledger/session-<n>.md` (n is the `SESSION:` counter in
`RSC-NEXT-SESSION.txt`; highest n is newest) and adds one line for it under
"Session files" below, newest first. See `docs/ledger/README.md`.

---

## Session files

- `docs/ledger/session-67.md`
- `docs/ledger/session-66.md`
- `docs/ledger/session-65.md`
- `docs/ledger/session-64.md`

## Month archives (historic body, verbatim, newest first)

- `docs/ledger/archive-2026-10.md`
- `docs/ledger/archive-2026-09.md`

## Adjudicated rulings

- 0i(4b) dev-dep licence gate (adjudicated 2026-10-10).
  DECISION: B - pin pytest-timeout==2.4.0 in requirements-dev.in; defer
  pytest-xdist 3.8.0 and execnet 2.1.2.
  Licence ruling: execnet CLEARED for dev/CI install only. LICENSE is MIT
  text with no copyright line, but trap 2 targets an unrendered grant;
  holder is named in METADATA ("holger krekel and others", same lineage
  as pinned pytest/iniconfig/pluggy). Installing is not lifting: no bytes
  enter the tree, so MIT's notice duty never attaches.
  Alternatives rejected: (A) both - xdist risks the suite gate
  (fleet_suite_gate.py docstring: concurrent suites lost xdist workers),
  timing tests in tests/test_headless_runner_lock_budget.py, and the
  xdist exit-status notes in conftest.py; benefit unmeasured. (C) refuse
  both - no licence bar exists to justify it.
  Reversed by: an xdist run under the gate showing no worker loss and a
  green lock-budget module across repeated runs; or any execnet bytes
  vendored, or a dev dep reaching runtime.
