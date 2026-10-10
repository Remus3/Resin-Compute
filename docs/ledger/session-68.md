# Session 68

Hand-off chores and the MAIN 2246 ORDER section 2 residue (0i).

## 2026-10-10 - /done gate, push, CI

- /done gate 2026-10-10 at 0e8612a (working tree clean), Python 3.14
  (host figures; CI is 3.11): licence 52 passed; docs 46 passed; qa 16
  passed 0 failed 2 skipped 4 noted; ruff clean; tests 4385 passed 6
  skipped (six host skip reasons, read with -rs: no exec bit on Windows,
  live fetch opt-in, bare python already the pinned interpreter, POSIX
  half of the console guard, 8.3 names disabled on E:, denied-dir listing
  still succeeds); collect-only 4391; pity_engine 191 passed; node 110
  pass 0 fail; dry run 0 pass 0 fail 7 skip; mypy 43 files clean
  (advisory); kit check `15 []`. Whole suites ran through
  `ops/fleet_kit/fleet_suite_gate.py` with the absolute interpreter path;
  the app suite waited about 1291 s for a slot (2 of 2 held by other
  owners), the engine suite about 150 s.
- core.hooksPath read the absolute `E:\Resin Compute\.githooks` at /done
  start (the drift trap again); `python scripts/install_hooks.py` restored
  it, read back `.githooks`.
- Push of the 10 session commits (5538515..0e8612a) through
  `ops/fleet_kit/fleet_gitlock.py`: pre-push OK (application suite FULL on
  the requirements-dev.txt trigger, 4359 passed 6 skipped 26 deselected;
  engine 191 passed); origin/main read back 0e8612a with git fetch. CI at
  0e8612a (gh run list / gh run view): ci 38075193484, docs-guards
  38075193467, codeql 38075193499, all success. The paperwork commit
  carrying this file landed after it; its CI run is not recorded here.

## 2026-10-10 - 0i(2c): pre-push CI_ONLY deferral, PARTIAL

- `scripts/prepush_select.py` defers six slow modules to CI (CI_ONLY,
  read back at /done: test_hook_gate, test_conftest_git_gate_sites,
  test_git_subprocess_census, test_git_env_scrub,
  test_gate_mutation_runner, test_responder_gate_census). Commits 64d05a7,
  bedcb6c; merge 0127b26. Local plumbing pre-push 55-97 s -> 35-44 s
  (session report, 3.14 host, harness-timed; not re-measured at /done);
  the 30 s target is NOT met.
- Round-1 adversary REFUTED: a later push cancelled an earlier push's CI
  run, which would deselect the CI_ONLY plumbing guards for that commit.
  Fixed: `.github/workflows/ci.yml` `cancel-in-progress: ${{
  github.event_name != 'push' }}` (read back at /done, line 65) plus a test
  in `tests/test_prepush_select.py`.
- Adjudicated ruling (moved here verbatim from `docs/LEDGER.md`, which is
  an index only):

      0i(2c) pre-push trim merge (adjudicated 2026-10-10).
      DECISION: M - merge bedcb6c (CI_ONLY deferral of 6 slow modules; push
      runs in ci.yml not cancellable). Local gate 55-97 s -> 35-44 s (3.14
      host); 30 s target not met.
      Rejected: F (per-commit concurrency group) - gap never observed (133
      push runs since 2026-09-07, 0 cancelled, closest pushes 178 s apart vs
      213 s max run), nightly bounds delay to 24 h; R (reject CI_ONLY) -
      gives up the speed win for an unobserved case.
      Rejected: running the engine suite in parallel in the hook - takes a
      second suite slot, against FLEET-COMMON 16c.
      Reversed by: any cancelled push run in ci, or 3 pushes landing within
      one run duration.

- Residue (ROADMAP 2246 entry): (a) the remaining ~5-14 s to the 30 s
  target; (b) 3 pushes inside one CI run (~213 s) still replace the pending
  run.

## 2026-10-10 - 0i(4b): dev-dep licence gate, DECISION B

- `pytest-timeout==2.4.0` hash-pinned in `requirements-dev.in` and
  `requirements-dev.txt` (read back at /done: .in line 52, .txt line 293),
  recompiled with pip-tools 7.5.3 on py 3.11.9 (session report).
  pytest-xdist 3.8.0 and execnet 2.1.2 DEFERRED. Commit 3c4d44b, merge
  d57226d. Adversary NOT REFUTED (session report, not re-run at /done).
  Guard: `tests/test_dev_pin_declaration.py` (PLUGINS and DEFERRED sets).
- Adjudicated ruling (moved here verbatim from `docs/LEDGER.md`):

      0i(4b) dev-dep licence gate (adjudicated 2026-10-10).
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

- New open item: the colorama `; sys_platform == "win32"` marker in
  `requirements-dev.txt` (line 66 at /done) is a hand-edit no test
  guards; a Linux Dependabot recompile drops it with CI green. On main
  since 74a8710. Filed in ROADMAP.

## 2026-10-10 - 0i(2b): census tests one per invariant

- `tests/test_responder_gate_census.py`,
  `tests/test_responder_spawn_census.py` and
  `tests/test_git_subprocess_census.py` collapsed to one test per
  invariant: 190 -> 94 items (94 read back at /done with --collect-only
  over the three files; 190 is the session report). Commit 977f88f, merge
  079c7fa. Adversary (coverage lens) NOT REFUTED with 7 mutations
  (session report).

## 2026-10-10 - C1 chores: 0l, 0j, 13, 0p

- 0l DONE: remote branch rsc-v8-slice-a deleted (7be9b44 was an ancestor
  of origin/main, no consumer, no PR). Read back at /done: `git ls-remote
  origin` lists only main and claude/new-session-19dmsr (154d5f8, the
  merged PR #1 head, an ancestor of origin/main - filed, not deleted).
- 0j MEASURED: TEMP-1 read-back over 191 scratchpads - max basetemp dirs
  per scratchpad 0, max entry count 16938 (a scratchpad of another tree);
  this tree's max 2019 (mostly a pt311 venv). Session report, not
  re-measured at /done. The send to MAIN is OWED in the next batched note.
- 13 DONE: inbox marked; `python scripts/watch_inbox.py` at /done read
  `unread: none`.
- 0p DONE: stash@{0} (2026-09-21 hand-off draft) adjudicated item by item,
  8 of 9 resolved, codified or superseded; the open one (prove the arm
  reds) went into CLAUDE.md "TDD, verification, bugs" (commit 65dec49,
  merge 9cd50b7); 2 stale ROADMAP NOT DONE rows closed in place. Stash
  dropped: `git stash list` empty at /done.
- Follow-up commit 0e8612a: stale docstrings after the slices.

## 2026-10-10 - observation for 0h

- `tests/test_conftest_git_gate_sites.py::test_the_run_half_reports_a_module_welded_to_skip_unconditionally`
  failed twice this session, both under a concurrent suite, and passed
  solo 3 of 3 (session report). Root cause open; the module is now
  CI_ONLY locally, so local pushes no longer exercise it.
