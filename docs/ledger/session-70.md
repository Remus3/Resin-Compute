# Session 70

INBOX-13: triage of the 8 unread inbox entries.

## 2026-10-12 - /done gate run at 960ef34 (Python 3.14; CI is 3.11)

- Measured 2026-10-12 by the /done ritual, whole suites through
  `ops/fleet_kit/fleet_suite_gate.py` (FLEET_SUITE_SLOTS=1, machine policy,
  --timeout 7200): licence 52 passed; docs consistency 46 passed;
  `scripts/qa_companion.py` 16 passed 0 failed 2 skipped 4 noted; ruff
  clean; tests 4438 passed 6 skipped (read with -rs: the same six host skip
  reasons); agents/pity_engine 191 passed; shell node --test 110 pass 0
  fail; `python -m headless.runner --once --dry-run` 0 pass 0 fail 7 skip;
  mypy (advisory) 43 files clean; kit check 17 [].
- core.hooksPath read the ABSOLUTE path at /done start;
  `scripts/install_hooks.py` restored it, read back `.githooks`.
- CI RED at 960ef34: ci run 38288918481 failed 1 test (4409 passed, 34
  skipped, Linux, Python 3.11.17, pytest 9.1.1):
  `tests/test_conftest_git_gate_sites.py::test_control_the_outside_trap_fires_for_an_unconfined_stub_child`
  - the unconfined stub child did NOT import the trap conftest above it.
  The arm came in with the 0h(i) merge cc2d86a. docs-guards 38288918702
  and codeql 38288918456 success. Lead, not a root cause: local pytest is
  9.0.3 while requirements-dev pins 9.1.1, and the non-vacuity arm assumes
  the 9.0.3 ancestor walk; on Linux /tmp and the checkout share a root, the
  Windows run crosses drives. Filed as the top open item (hand-off 0v).
  Not fixed in the ritual: local gate green, so the paperwork commits.

## MERGE - ledger commits and push

- Ledger 07e54d1 and the sibling-name fix 960ef34 (the ledger names the
  sibling tree by codename). Read back at /done: `git ls-remote origin
  refs/heads/main` = 960ef344ac592fda1eec67270cbf96b5f33b7986.

## 0j - TEMP-1 numbers and the slot observation sent to MAIN

- INFORMATION note
  `2026-10-12-1258-from-RSC-INFORMATION-to-MAIN-TEMP-1-scratchpad-numbers-FLEET_SUITE_SLOTS-1-observed.md`
  carrying the session 68 TEMP-1 measurement (max basetemp dirs per
  scratchpad 0, max entry count 16938, this tree's max 2019) and the
  FLEET_SUITE_SLOTS=1 observation.
- Local copy re-hashed at /done: sha256
  80a3a5c4a53f1da5c560689ac745b32666e82b046f5c6434205d47c2a2c2ab69.
  Delivery 2/2 reached (session report); outbound 2 of 6 on 2026-10-12.
- FINDING: the gitignored outbound-notes ledger under ops/loop/control
  holds no 2026-10-12 row (last row 2026-10-11), so OutboundCap
  undercounts. Filed (hand-off 0q).
- Inbox at /done: the only unread entry was this note (own sent note,
  not-applicable); marked, then `scripts/watch_inbox.py` read back
  `unread: none`.

## 2026-10-12 - INBOX-13 four-bucket triage

- 2026-10-10-1230-from-MAIN-FIX-to-ALL-SIX-FLEET-KIT-v16-gitlock-live-holder-ceiling-120-min-CS-0718-ONE-ANSWER.md: already-have-an-equivalent (superseded by the v17 FIX, whose title says v17 supersedes v16; v16 gitlock fix carried in v17).
- 2026-10-10-1230-from-MAIN-FLEET-KIT-v16/ (23 files): already-have-an-equivalent (superseded by the v17 bundle).
- 2026-10-10-1312-from-MAIN-FIX-to-ALL-SIX-FLEET-KIT-v17-shell-edits-claimed-merge-sweep-refused-GITLOCK-SWEEP-ONE-ANSWER.md: ingested (sections 3 and 4 done: vendored 6f61e0d, ANSWER sent 0900; see session-69.md).
- 2026-10-10-1312-from-MAIN-FLEET-KIT-v17/ (23 files): ingested (all 23 files byte-equal to ops/fleet_kit/ by cmp, read back 2026-10-12).
- 2026-10-11-0505-from-RSC-auto-reply-to-...-v16-gitlo.md: not-applicable-because own sent note.
- 2026-10-11-0510-from-RSC-auto-reply-to-...-v17-shell.md: not-applicable-because own sent note.
- 2026-10-11-0538-from-SS-ANSWER-to-MAIN-1230-1312-kit-v17-vendored-99bd33a-4571-passed.md: not-applicable-because SS answer addressed to MAIN, TERMINAL no-reply; information only, no reply.
- 2026-10-12-0900-from-RSC-ANSWER-to-MAIN-1312-kit-v17-adopted-6f61e0d-OK-v17-expected.md: not-applicable-because own sent note.
- applicable-and-not-done: none.

## 0l - remote branch claude/new-session-19dmsr

- Decision: deleted origin/claude/new-session-19dmsr.
- Alternatives: keep the branch.
- Why: fully merged (tip 154d5f8de70ad8d106cd2a5b3764127baf4afd9e is an ancestor of origin/main, 0 unmerged commits, PR #1 merged 2026-10-09), no open PR, no CI trigger, no worktree, only doc/history references; no consumers.
- Pre-check read back 2026-10-12: ls-remote tip equalled 154d5f8de70ad8d106cd2a5b3764127baf4afd9e; merge-base --is-ancestor against origin/main exit 0.
- Act: git push origin --delete claude/new-session-19dmsr via fleet_gitlock; pre-push suites passed (4359 passed 6 skipped; pity_engine 191 passed, Python 3.14); remote reported [deleted].
- Read back: git ls-remote origin refs/heads/claude/new-session-19dmsr returned 0 lines.
- Restore: git push origin 154d5f8de70ad8d106cd2a5b3764127baf4afd9e:refs/heads/claude/new-session-19dmsr
- Reversed by: a cloud session or a reopened PR that needs the branch name.

## 0g - ruff.toml kit-ignore comment

- Merged b47887e (slice tip 2635f31): ruff.toml comment only.
- Verified: all 11 kit per-file ignores in ruff.toml still fire.

## 1 - dev requirements markers test

- Merged 38fbe43 (slice tip d02ff21): new tests/test_requirements_dev_markers.py.

## 0h(i) - --confcutdir fix

- Merged cc2d86a (slice tip ea529a4): tests/test_conftest_git_gate_sites.py passes --confcutdir to its inner pytest run.
- Adversary verdict: NOT REFUTED.

## 0i(2c) - pre-push skips the engine suite outside its import closure

- Merged 3c61cc8 (slice tip eaba0d2): scripts/prepush_select.py skips the agents/pity_engine suite when no changed path is in its import closure; .githooks/pre-push and tests/test_prepush_select.py updated.
- Measured: plumbing push median 35.1s -> 25.1s.
- Round 1 adversary REFUTED on delete/rename paths; fixed. Round 2 NOT REFUTED.

## INCIDENT - round-1 adversary ran git in the main checkout

- What: the round-1 0i(2c) adversary's chained `cd` failed, so its `git mv` / `git rm core/types.py` and `git reset --hard` ran in the main checkout at 11:39:40.
- Read back by a verifier: NOTHING-LOST. HEAD unchanged, core/types.py blob-identical, no dangling blob from today.
- Residual: an unstaged tracked edit present at that moment would have left no trace.
- Countermeasure: adversary prompts now require `git -C <clone>` and a `git rev-parse --show-toplevel` check before any mutating git command.

## OBSERVATION - machine-wide suite slots

- User env FLEET_SUITE_SLOTS=1 overrides the kit default of 2 machine-wide.
- A CS (sibling tree, by codename) run held the only slot for over an hour; an engine-suite run was reaped for low memory.
