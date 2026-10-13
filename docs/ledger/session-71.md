# Session 71

Mostly unattended (operator away). Checklist: 0v, 0r, 0q, 0u, 0s, MERGE,
/done. Item 0 (responder renewal) and the rest carried forward.

## 2026-10-12 - /done gate run at d142bd8 (Python 3.14; CI is 3.11)

- Measured 2026-10-12 by the /done ritual, whole suites through
  `ops/fleet_kit/fleet_suite_gate.py` (FLEET_SUITE_SLOTS=1, machine policy):
  licence 52 passed; docs consistency 46 passed; `scripts/qa_companion.py`
  16 passed 0 failed 2 skipped 4 noted (account snapshot none yet; nothing
  listening on 8791); ruff clean; tests 4479 passed 6 skipped (read with -rs: the same six host skip
  reasons); agents/pity_engine 191 passed; shell node --test 110 pass 0 fail;
  `python -m headless.runner --once --dry-run` 0 pass 0 fail 7 skip; mypy
  (advisory) 44 files clean.
- The app suite waited about 720 s for the single suite slot (other
  trees' suites ahead). Kit check `fleet_headless` printed 17 [].
- Sections 2-4: the tree was clean at /done start and origin/main already
  read back d142bd8, so the only /done commit is this paperwork.
- core.hooksPath read back `.githooks` at /done start (no drift at /done).
- Inbox at /done: `scripts/watch_inbox.py` read back `unread: none`.

## MERGE - seam gate and push d142bd8

- Read back at /done: `git ls-remote origin refs/heads/main` =
  d142bd8f27c0fc929d235b0762139d1a39b25d57 (before the paperwork commit).
- CI read back with `gh run list` at /done: ci 38337579557, docs-guards
  38337579717 and codeql 38337579576 success at 20d9d29; docs-guards
  38337658754 success at d142bd8 (docs-only, no ci run by paths-ignore).
- Session-70 paperwork push read back: ci 38289666845 FAILURE at bac5edc
  (the item 0v test, fixed this session); docs-guards 38289666824
  cancelled (superseded by 38289726135 success at d62ac73).
- Seam gate figures reported by the session (not re-measured here; the
  /done gate above is the measurement of record): tests 4479 passed 6
  skipped, pity_engine 191, node 110, mypy 44 files.
- d142bd8 added the ROADMAP "Session 71 residue" entry: (a) the OutboundCap
  lockless-append kit defect, (b) `.claude/agents/builder.md:43-44` should
  defer to `.claude/commands/ui-audit.md:77-85`, (c) hooksPath drift
  recurrence.
- INCIDENTS: the harness killed background suite runs twice for host low
  memory; the single machine-wide suite slot was contended (about 15-30 min
  queue waits).

## 0s - CS codename confirmed

- 960ef34 changes one line of `docs/ledger/session-70.md` naming "CS
  (sibling tree, by codename)". Read at /done: `CS` is a key of
  `channel_codes` in the gitignored codename map (14 entries). Confirmed.
- core.hooksPath had drifted to an absolute path again during session 71;
  `python scripts/install_hooks.py` restored it; /done read back
  `.githooks`. Root cause still open (ROADMAP session 71 residue (c)).

## 0u - electron 44.5.1 -> 44.7.0 in shell (merge 8fe0ce4)

- Slice 476e7e5 bumps `shell/package.json` and `shell/package-lock.json`;
  merge 8fe0ce4.
- ui-auditor WAIVED by the adjudicator: the dependency-bump exemption in
  `.claude/commands/ui-audit.md` (line 84) governs over the general path rule
  at `.claude/agents/builder.md:43-44`. Reversed by: narrowing the
  exemption, a MAIN ruling, or a rendered regression.
- Dependabot PR #5 read back CLOSED at 2026-10-13T02:37:49Z (`gh pr view 5`),
  closed by Dependabot after the bump reached main. Unverified: the Chromium
  delta between the two electron versions.

## 0q - attended send path writes the outbound-ledger row (merge 20d9d29)

- Root cause: the only writers of the outbound-notes ledger were
  `tools/moon_sync_responder.py` (`_send_batch`, `_record_work_reply`);
  hand-written attended sends had no writer, so the kit OutboundCap
  undercounted.
- New `tools/send_note.py` (`send` and `audit`, audit `--apply` backfills a
  row only after verifying the recipient copy hash) and
  `tests/test_send_note.py`. Commits ce22520, 2bc6237 (round 1 fixes:
  partial failure, hyphen classes, retired codes, validate_draft), 6257479
  (adjudicated B: audit proposes a row only for a delivered note).
- Two adversary rounds REFUTED (r1 as above; r2 P1 audit rows an
  undelivered note, P2 concurrent double row, P3 forced over-cap row).
  Adjudicator ruled B: fix P1; keep P3 (an over-cap row is recorded, since
  undercount is the 0q defect); P2 filed as a kit defect
  (`OutboundCap.record` / `_append` lockless) for MAIN's next batched note.
  Reversed by: the kit locking `record`, or a MAIN ruling that the ledger
  must never exceed the cap.
- Backfill read back at /done: the last 9 rows of the gitignored ledger are
  2026-10-03 x2, 10-05, 10-07 x2, 10-08 x2, 10-12 x2 (the 0900 ANSWER and
  1258 INFORMATION notes among them); `python tools/send_note.py audit`
  printed nothing, exit 0.
- NOT DONE: nothing yet forces attended sessions or `/done` to send through
  `tools/send_note.py`. Carried (hand-off 0w).

## 0r - adversary git rule (merge dec5217)

- Commit 08e1352: `.claude/agents/adversary.md` line 18 and
  `.claude/commands/orchestrated-run.md` lines 338-339 now require mutating
  git only as `git -C <clone>` after `git -C <clone> rev-parse
  --show-toplevel` prints the clone. Read back at /done by grep.

## 0v - CI red test fixed (merge f1a2121)

- Failing test:
  `tests/test_conftest_git_gate_sites.py::test_control_the_outside_trap_fires_for_an_unconfined_stub_child`.
- Root cause: pytest's rootdir fallback lands on the stub dir when the
  common ancestor of cwd and stub is a filesystem root (`/` on Linux, /tmp
  vs the checkout), so the default confcutdir excluded the trap conftest.
  NOT the pytest 9.0.3 -> 9.1.1 difference (findpaths identical).
- Fix: `_unconfined_stub_selection` pins `--rootdir <repo>`;
  `_stub_selection` pins `--rootdir` and `--confcutdir`; the control and
  confined arms are parametrized repo-root-cwd / filesystem-root-cwd.
  Commits a9cd2d0, f02c92c (adversary round 1 REFUTED on scope: the sibling
  confined arm was vacuous on Linux; fixed with red proof).
- CI read back: ci 38337579557 success at 20d9d29.
