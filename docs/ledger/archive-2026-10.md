# Ledger archive - 2026-10

Historic `docs/LEDGER.md` entries headed 2026-10, moved here verbatim in their
original order (newest first). New sessions write `docs/ledger/session-<n>.md`.

## 2026-10-08 - MAIN 2246 ORDER section 1: kit v13 identity hooks wired

- Provenance: the 2246 ORDER matched MAIN's outbox (sha256 7ccc71ff...);
  its delivered bundle is byte-identical to the 2128 bundle already
  vendored (23 of 23 files). It arrived after the ANSWER 2301 had gone and
  is the reversal condition of ruling C below, so the deferred wiring is
  done now.
- `.githooks/commit-msg` runs `fleet_identity.py commit-msg "$1" || true`
  after the tree's own strip; `.githooks/pre-push` runs
  `fleet_identity.py pre-push "$@" || exit 1` FIRST, before the
  RESIN_SKIP_PREPUSH escape and the gates, feeding it the ref lines the
  hook had read. `ops/loop/control/identity.jsonl` gitignored.
  `tests/test_hook_gate.py` HOOK_DEPENDENCIES gains fleet_identity.py.
  Test first: `tests/test_fleet_kit_v13_adoption.py` (MAIN's check (f)
  regex) went red 4 of 6 before the wiring.
- Local git config `fleet.operatorIdent`: 2 values, both `Name <address>`,
  the two operator identities in main's history (the 4 Claude rows
  excluded). Not in any tracked file or note. Read back: `check` over
  aa9bbea..HEAD reads clean; over the Claude commit it refuses 2
  violations (non-vacuity).
- Measured 2026-10-08 on Python 3.14 through `fleet_suite_gate.py run`:
  `tests` 4369 passed 6 skipped (same six host reasons); `agents/pity_engine`
  191 passed; kit check `13 []`.
- NOT done here, filed in ROADMAP: s1 Desktop shortcut removal and
  sections 2-8 (perf, README, history rewrite, review driver).

## 2026-10-08 - FLEET-KIT v12 (MAIN 2031 ORDER) and v13 (staged bundle) vendored

- Provenance: the v12 ORDER matched MAIN's outbox (sha256 3bad46b1...) and
  its 21-file bundle matched both the outbox twin and its manifest, 21 of
  21. The responder's 2035 auto-reply only reported status; it took none
  of the ORDER's steps. v13: MAIN committed the kit (its b25cbf9,
  2b6b2f6) and staged bundle 2128 (manifest 1311801a...74e0, 22 of 22
  files matching it) but sent NO v13 ORDER; MAIN's roadmap reads "staged,
  NO note sent".
- v12 (commit 89fe0d9, through `fleet_gitlock.py run`): 21 files
  byte-for-byte; v12 FLEET-COMMON block embedded; claims PreToolUse hook
  (`Edit|Write|NotebookEdit|MultiEdit|Bash|PowerShell`) and SubagentStop
  release-hook wired in `.claude/settings.json`, timeout 10, subagent-first
  entry kept; five runtime paths gitignored; `tests/conftest.py` installs
  `fleet_test_guard` with env_roots `RESINCOMPUTE_RUNTIME_DIR` (RC_DATA_DIR
  not declared: it locates fixtures, not runtime state); `/done` routes
  commit, push and each whole suite through gitlock and the suite gate.
  Tests first: `tests/test_fleet_kit_v12_adoption.py` and the v12 pins went
  red before the vendoring. Four arms that measure the unredirected live
  default (`test_ops_health`, `test_responder_uniform_budget` `_live`,
  `test_watch_inbox_session`, `test_session_hooks` live-records arm) now
  drop the guard's redirect themselves; the guard is why the hand-off's
  "do not export RESINCOMPUTE_RUNTIME_DIR" warning had 7 red arms here.
  No responder, runner or script in this tree commits or pushes, so /done
  is the only commit route to re-point.
- v13 (commit 3438a82, census fix bb51879). RULING, distinct adjudicator,
  DECISION C: vendor the 22 manifest-verified files and the v13 block now;
  DEFER the identity hooks (`fleet_identity.py` commit-msg / pre-push) and
  the local `fleet.operatorIdent` until the SHA-256-verified v13 ORDER.
  Alternatives rejected: (A) wire identity now - guesses an operator ident
  MAIN has not ruled on, and with no value set pre-push refuses every push;
  (B) v12 only - the operator ordered v13 and it was found. Why: the
  operator order covers the bytes and the manifest verifies them; tree-side
  settings are what an ORDER specifies. Reversed by: the v13 ORDER arriving
  (wire per it, re-check the manifest), the bundle differing from
  1311801a...74e0, or the operator.
- Halt boundary: the suite gate writes slots under %LOCALAPPDATA%, outside
  this root (clause a); cleared by the verified v12 ORDER, which requires
  the gated suite. `ops/loop/slots.py` and `ops/loop/winmutex.py` untouched.
- ruff.toml: per-file ignores, measured: fleet_claims.py UP032 x1 BLE001
  x1; fleet_gitlock.py UP032 x4; fleet_suite_gate.py UP032 x2;
  fleet_identity.py UP032 x4; fleet_rewrite.py UP032 x4. Interpreter
  census rows added for gitlock (3), suite gate (2), identity (1), rewrite
  (2); every head is FLEET_GIT-or-git or a caller argv, never a Python.
- Measured 2026-10-08 on Python 3.14, both suites through
  `fleet_suite_gate.py run` at bb51879: `tests` 4363 passed 6 skipped (the
  six known host reasons); `agents/pity_engine` 191 passed; ruff clean;
  mypy clean over 43 files; kit check `13 []`. The first gated run at
  3438a82 read 1 failed (the census) - fixed in bb51879. A machine slot
  was held 45+ min by another tree's suite; our wait was about 21 min.
- For MAIN (in the ONE ANSWER): fleet_identity/fleet_rewrite heads trip an
  interpreter census once tracked; the claims hook default is deny with no
  mode file.

## 2026-10-08 - Session 63 /done: checklist closure, PR #1 merged, gates at afa7fc7

- Item 15 (task_liveness) DONE at merge 89528a4 (fix 8c9e35c): the
  liveness probe in `ops/check_task_liveness.py` cast `LastTaskResult`
  (a UInt32) with `[int]`, which threw for any HRESULT above Int32.MaxValue
  and read as "the scheduler refused the query". Now `[int64]`; regression
  arms in `tests/test_task_liveness.py`. An adversary did not refute it and
  found no siblings. Consequence: the pre-push hook no longer trips on this
  host, so the session-62 `RESIN_SKIP_PREPUSH=1` workaround is retired;
  every session-63 push ran the hook.
- Item 0d DONE at merge 5e4e525 (ab1e9d8, then 10cff26 after an adversary
  REFUTED the one-orchestrator-sub-agent shape: a sub-agent has no Agent
  tool). `.claude/commands/orchestrated-run.md` keeps the main session as
  orchestrator dispatching every tool call; `.claude/commands/ui-audit.md`
  dispatches one ui-auditor. Pinned in `tests/test_fleet_kit_v10_adoption.py`.
- Item 0a DONE: the 14 MIG-1 residue dirs (42 files, 411,097 bytes, 0 unique
  files) went to the Recycle Bin via Microsoft.VisualBasic SendToRecycleBin.
  Read back at /done: the gitignored mig1_residue dir under the runtime
  directory is absent.
- Item 2 (MAIN 0300) DONE at merge 70e031d (entry below); OpenSSF Scorecard
  after the push read 6.6, up from 4.7.
- ANSWER 2026-10-08-1925 to MAIN (0300 and 1840) delivered 1/1; read back at
  /done: sha256 7fb22a61ad943b11f37bfa787903d97abec24e851e672f1fce6b4ec0ccda269f.
  OutboundCap 3 of 6 for the day.
- Item 3 DONE: cloud PR #1 landed as the real merge commit afa7fc7 (no
  squash, no rebase); resolutions recorded in its message. GitHub reads the
  PR MERGED. Its subject is 106 characters, over the 100 warning (warn only).
- Item 13: inbox triaged and marked; unread none.
- Item 16 RETRACTED, no change: the `_MIN_TRACKED_*` floors were already
  raised to 135 in c3bed4a. Read at /done: tracked corpus 317 paths, widest
  directory `tests/` 124, so 135 exceeds the widest dir and 135*2 = 270 sits
  within the corpus.
- 0e reading: `ops/loop/control/subagent_first.jsonl` (gitignored) holds 621
  rows, 534 after the session-62 /done commit; every row is
  `decision allow`, `thread sub`. Would-deny rows this session: 0. Session 63
  counts as log-mode session 2 of 3.
- Gates measured 2026-10-08 at afa7fc7 on Python 3.14: licence 52 passed;
  docs 42 passed; qa_companion 17 passed 0 failed 2 skipped 3 noted; ruff
  clean; `tests` 4344 passed 6 skipped (the six known host reasons);
  `agents/pity_engine` 191 passed; node 110 pass 0 fail; dry run 0 pass 0
  fail 7 skip; mypy clean over 43 files (advisory); kit check `11 []`.
- CI at afa7fc7: ci 37865404279 success, docs-guards 37865404256 success,
  codeql 37865404240 success. This /done commit is docs-only.

## 2026-10-08 - MAIN 1840 ORDER: FLEET-KIT v11 vendored (session 63)

- Provenance: the order and its 17-file bundle matched MAIN's outbox,
  18 of 18 SHA-256. All 17 files copied byte-for-byte into
  `ops/fleet_kit/` (commit 8e675fe); read back: MANIFEST.json sha256
  c1dcf5a613b7d765bc1f917d7844ad58e272dd7984f97a632c62f911072259a7 and
  16 of 16 listed files matching it. Seven files differ from v10:
  MANIFEST.json, fleet_done.py, fleet_headless.py, fleet_inbox.py,
  fleet_lanes.py, fleet_subagent_first.py and fleet_watch.py.
  FLEET-COMMON.md is unchanged (9dfb40e3), so `CLAUDE.md` is untouched.
- Hook (order section 4 step 2): `.claude/settings.json` already carried
  the anchored `$CLAUDE_PROJECT_DIR` command since the v10 adoption, so
  there was nothing to rewire. The mode file progression (log, then deny)
  is unchanged.
- Triage (ruling R1): `tools/moon_sync_responder.py` now builds the triage
  shape from `fleet_inbox.triage_spawn_kwargs(not SPAWN_BARE)` and passes
  `floors_in_hooks` to `spawn()`. No floor lives in a hook here, so triage
  stays bare. The test was written first and went red on
  `KeyError: 'floors_in_hooks'`. A new arm proves the helper's answer
  reaches `spawn()`.
- Pins: `tests/test_fleet_kit.py` constants were renamed to version-neutral
  names and moved to v11. The v11 `fleet_done.py` git resolution
  (`find_git()`, an absolute PATH entry) is a new unresolvable launch head.
  It now has a triaged row in `UNRESOLVED_CENSUS` in
  `tests/test_interpreter_pinning.py`. `ruff.toml` needed no change.
- Measured 2026-10-08 on Python 3.14: `tests` 4205 passed, 6 skipped;
  `agents/pity_engine` 80 passed; ruff clean; mypy clean over its 41 files.
- Owed: ONE ANSWER to MAIN (HOP: 2) giving the vendoring commit, the
  manifest sha256, the conformance result and the hook command string as
  wired.

## 2026-10-08 - Session 63: responder run ledger retired (0f), cap-hold label (0c), item-14 minors (4)

- RULING 0f, decided by a distinct adjudicator, DECISION C (shrink). The
  responder-local RUN ledger is retired from `tools/moon_sync_responder.py`.
  Why: kit v10's `RunBudget._lock` (`ops/fleet_kit/fleet_headless.py`) is an
  OS byte-range lock on a never-unlinked file that a dead holder frees at
  once, and `kit.spawn` counts every start under it - the ROADMAP
  "/120 COUNTER" REVERSE IF. Keeping both drifted: the responder reserved
  BEFORE `kit.spawn`, so a failed spawn cost a responder run and no kit run.
  Alternatives rejected: (A) retire everything - loses the per-sender
  loop-breaker floor, since the kit OutboundCap is per tree at 6 a day;
  (B) keep both - a second counter that drifts. Reversed by: a kit version
  dropping the OS-held lock, or the kit not counting every spawn in this
  tree. Removed: `MAX_RUNS_PER_DAY`, `RUNS_WINDOW_SECONDS`,
  `RUN_BUDGET_REASON`, `RUN_RECORD_REASON`, `RUN_LOCK_REASON`, `_run_rows`,
  `run_lock_path`, `reserve_run`, `RunLockBusy`, `CAP_RUNS`,
  `_binding_run_budget`, `RunBudgetSpent` and the `run-budget` termination.
  `HaltedBeforeSpawn`, `KitRunBudgetSpent` and `KitBudgetUnreadable` are
  re-parented onto `NoSessionStarted`; the kit's "budget lock busy" maps to
  the new `KitBudgetLockBusy` (`run-locked`). `_acquire_run_lock` and
  `_release_run_lock` are renamed `_acquire_os_lock`/`_release_os_lock`
  (progress lock, outbound lock). KEPT: `DEFAULT_RUNS` as a path anchor,
  `MAX_REPLIES_PER_SENDER`/`senders_at_cap`, `MAX_HOPS`. The responder test
  arms that pinned the retired ledger were re-pinned to the kit ledger.
- 0c, the cap-hold label. Root cause: `_write_tick_status` read `limit` /
  Turn Limit Reached whenever MAIN was at `MAX_REPLIES_PER_SENDER` and the
  fire took no note, whether or not any MAIN note was waiting. Fix:
  `pending` gained `held_out` (appended, defaulted), `_run_once` records
  `cap_held` (senders whose otherwise-eligible notes only the cap kept out),
  and the label reads `limit` only when `cap_held` names MAIN. Failing arm
  first: `test_a_main_cap_with_nothing_held_reads_idle_not_limit` read
  `limit` before the fix.
- Item-14 minors: (1) the MAIN retry bound is the kit's 120 alone - a full
  legacy record no longer refuses a spawn (red before: `RunBudgetSpent`).
  (2) `test_r5_minor2_*` pins the triage-lane `_release_outbound`; a mutant
  deleting the call turned it red. (3) `_safe_note_label` removed;
  `_log_safe` now replaces non-ASCII too - before, `log_invocation` returned
  False and dropped the whole line for a name with one non-ASCII character.
  (4) `record_outbound` and `_release_outbound` run under an OS lock
  (`outbound_lock_path`, 2 s wait, fail closed); before, 4 contending
  interpreters reported 83 reservations landed and 27 rows survived.

## 2026-10-08 - MAIN ORDER 0300 supply-chain hardening, builder slice (session 63)

- Repo visibility read back PUBLIC (`gh repo view`), so the CodeQL upload is
  not guarded; the reason sits in the workflow header.
- Actions SHA-pinned with the tag as a trailing comment, each SHA resolved
  from the release tag via the commits API and cross-read from git/ref:
  actions/checkout v6.1.0 d23441a48e516b6c34aea4fa41551a30e30af803,
  actions/setup-python v6.3.0 ece7cb06caefa5fff74198d8649806c4678c61a1,
  github/codeql-action v4.38.3 24c54180a607b1449ed407dd24f251e4e9147c8d
  (annotated tag dereferenced). Majors kept at v6; Dependabot proposes v7.
- Dev deps are a pip-compile pair. requirements-dev.in holds the human `==`
  pins (ruff, pytest, mypy) and is what tests/test_dev_pin_declaration.py
  grades; requirements-dev.txt is pip-tools 7.5.3 `pip-compile
  --generate-hashes` output at Python 3.11, the closure with a sha256 per
  distribution. Both workflows install it with `--require-hashes`; the
  `pip install --upgrade pip` lines are dropped. Re-verified in a fresh 3.11
  venv (pip 26.2.1): install exit 0, and a one-version edit is refused with
  a hash mismatch. No unhashed pip line remains.
- Why the pair and not a separate `.lock`: an adversary refuted the first
  cut, which kept requirements-dev.txt unhashed beside a hashed
  requirements-dev.lock. Dependabot's pip updater would bump only the .txt
  and leave the lock stale. Evidence that the pair is the shape Dependabot
  maintains: GitHub lists pip-compile as a supported package manager
  (https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories),
  and dependabot-core at 0286aa0868b1f0de1b908ce3358bbf994e5272c1 matches an
  .in to its .txt by name in
  python/lib/dependabot/python/file_updater/pip_compile_file_updater.rb
  (`compiled_files_for_filename`), re-adds `--generate-hashes` when the .txt
  contains `--hash=sha`, and takes the Python version from the header
  "autogenerated by pip-compile with Python 3.11"
  (file_parser/python_requirement_parser.rb). tests/test_supply_chain.py
  pins the header and the .in-to-.txt version match. Caveat: this file was
  compiled on Windows, so colorama (a win32-only pytest dependency) is
  listed unconditionally. Dependabot's Linux recompile will drop it, and
  after that a Windows `pip install -r requirements-dev.txt` will need
  `requirements-dev.in` instead.
- `.github/dependabot.yml` (github-actions, pip at the root, npm at shell/,
  weekly, one group each) and `.github/workflows/codeql.yml` (python,
  javascript-typescript, actions; build-mode none; security-events write at
  job level only). Every workflow keeps top-level `contents: read`.
- tests/test_supply_chain.py pins those properties; five arms were red
  before the change, each with a non-vacuity arm.
- FUZZING RULED OUT (MAIN adjudication in the same order): these are
  single-user local tools whose parsers read the operator's own files and
  pinned upstream data, not untrusted network input, so a fuzzer buys
  Scorecard points rather than risk reduction. Reversed by: the tree parsing
  untrusted input (network-facing service, third-party files, a published
  parser library) or an operator order.
- Scorecard v5.5.0 linux binary, checksum-verified, run in WSL before any
  push at d6bce85: aggregate 4.7. Pinned-Dependencies 0, SAST 0,
  Dependency-Update-Tool 0, Token-Permissions 10, Security-Policy 10,
  Vulnerabilities 10. The after run follows the merger's push.

## 2026-10-08 - Session 62 /done: worktree housekeeping, inbox watermark, gates

- Worktrees: the four merged session-62 worktrees (agent-af2a0f85823855fa5,
  rsc-roster-fix, agent-a975dc7a0b2da117f, agent-a1e9b30d680cc4883) each had
  `git merge-base --is-ancestor <branch> main` true and an empty
  `git status -s`; directories sent to the Recycle Bin
  (Microsoft.VisualBasic DeleteDirectory, SendToRecycleBin), then
  `git worktree prune`. Read back: each path absent, `git worktree list` 1
  entry (main). Branches kept.
- Inbox: session 62 triage (gitignored runtime file inbox_triage_s62.txt
  under ops/runtime: 460 entries, 323 ingested, 5 equivalent, 125 n/a, 7
  applicable-not-done, all handled except MAIN 0300 supply chain) covered
  the listed batch; the only newer entries were our own sent 1425 and 1454.
  The inbox watcher's mark mode was run; its listing read back `unread:
  none`.
- Hand-off items closed: 0a.d (kit v9 vendored), 0d (kit v10 vendored), 1
  (roster 0230/2305) - see the entry below. Item 0b: the 1454 ANSWER asked
  MAIN for the 2354 and 0020 stamps; awaiting reply.
- Gates at 1caa1a9, 2026-10-08, Python 3.14: licence 52; docs 42; qa 17
  passed 2 skipped 3 noted; ruff clean; tests 1 failed 4184 passed 6
  skipped (the failure is
  `tests/test_task_liveness.py::test_the_real_probe_answers_for_a_task_outside_the_root_task_path`,
  "the scheduler refused the query" - the host-dependent hand-off item 15,
  pre-existing, not this session's code); pity_engine 80; node 52 pass 0
  fail; dry run 0 pass 0 fail 6 skip; mypy 41 files clean (advisory); kit
  check `10 []`. Six skip reasons: no exec bit, live fetch opt-in, bare
  python is 3.14, POSIX half, 8.3 names off on E:, denied dir still lists.
- CI at 1caa1a9 (pushed with RESIN_SKIP_PREPUSH=1, docs-only, item 15
  reproduced solo): docs-guards run 37837137253 success; no ci run (docs
  only, paths-ignore). At fd4fb42: ci 37835448263 success, docs-guards
  37835448162 success.
- Read at /done: `ops/loop/control/inbox_status.json` state limit,
  runs_in_window 6, runs_cap 3, cap_frees_at 22:51 - the cap-hold label
  item on the roadmap. Hook mode file holds `log`.
- This paperwork commit is docs-only and was pushed with
  RESIN_SKIP_PREPUSH=1 (item 15 blocks the pre-push hook on this host), so
  CI is its only gate; its docs-guards run was pending when this entry was
  written - read it with `gh run list --branch main --limit 3`.

---

## 2026-10-08 - Kit v9+v10 vendored, roster landed, ONE ANSWER to MAIN (session 62)

MAIN 0839 (v10), 2354 (v9), 0230 and 2305 (roster). Provenance read back:
all four notes MATCH MAIN's outbox by sha256; v10 payload 17/17 MATCH the
outbox and 17/17 MATCH the vendored bytes.
- Merges: e475a09 (kit branch tip c3bed4a, v9 then v10) and e39a065 (roster
  branch tip c1a0ecd). One conflict, `tests/test_headless_env.py`, the
  sibling quoted-marker test: kept the v10 test, sender switched LL -> CS so
  it proves v10 behaviour, not retirement; the roster-side "still damped"
  variant dropped. Follow-ups 6db7e17 (hook command-form decision in
  CLAUDE.md, done.md tool list, ROADMAP v10 residue) and fd4fb42 (the
  rejected command form re-worded in prose after
  `tests/test_docs_hook_commands.py` went red on it).
- Kit check read back `10 []`; vendored MANIFEST.json sha256 ae3c91ad.
  Hook mode file holds `log`; `ops/loop/control/subagent_first.jsonl`
  exists and its last row reads mode log, decision allow.
- Gates at fd4fb42, Python 3.14: licence 52; docs 42; qa 17 passed 2
  skipped 3 noted; ruff clean; tests 4185 passed 6 skipped (a first run had
  2 failed: the docs hook guard above, fixed, and
  `tests/test_conftest_git_gate_sites.py::test_the_run_half_reports_a_module_welded_to_skip_unconditionally`,
  which passed solo and in the re-run - unexplained, recorded as a flake);
  pity_engine 80; node 52 pass 0 fail; dry run 0 pass 0 fail 6 skip; mypy
  41 files clean (advisory).
- Push fd4fb42 (pre-push hook ran, OK). CI at fd4fb42: ci run 37835448263
  success; docs-guards run 37835448162 success.
- `python ops/check_task_liveness.py RSC-InboxResponder` rc 0.
  `inbox_status.json` read: kit 10, state limit, runs_in_window 6 against
  runs_cap 3, frees 22:51 - the label item already on the roadmap.
- ANSWER delivered: `2026-10-08-1454-from-RSC-ANSWER-to-MAIN-0839-2354-0230-2305-kit-v10-vendored-conformance-10-clean-hook-on-log-roster-landed.md`,
  sha256 6aba8fe7 for MAIN's inbox copy and our sent copy, 1/1 reached.
  The gitignored runtime answered-ledger already listed all four stamps with
  their sha256 (written by the responder's auto-replies); left unchanged.
- Not done: supply chain 0300; orchestrated-run and ui-audit one-subagent
  dispatch.

---

## 2026-10-08 - /done-only session, gates re-measured (session 61)

No open item was acted on; every hand-off item is carried forward. The MAIN
0839 FLEET-KIT v10 ORDER arrived and is filed untriaged as hand-off item 0d.
- Gates at 1988b41, 2026-10-08, Python 3.14: licence 52; docs 42; qa 17
  passed 2 skipped 3 noted; ruff clean; tests 4134 passed 6 skipped; pity_engine
  80; node 52 pass 0 fail; dry run 0 pass 0 fail 6 skip; mypy 41 files clean
  (advisory). The host scheduler probe (hand-off item 15) passed this run.
- CI read at 1988b41: ci push run 37735387706 success, scheduled ci run
  37800142367 success. This paperwork push is docs-only.

## 2026-10-08 - E: move steps b and c: C: copy retired behind a junction, responder re-armed from E: (session 60)

Hand-off item 0a. Step a: this session ran from `E:\Resin Compute`.
- Step b. No file under the C: inbox was newer than 2026-10-08T00:13. No
  process command line named the repo path. The C: copy was sent to the
  Recycle Bin (VisualBasic FileSystem.DeleteDirectory, SendToRecycleBin), and
  `mklink /J "C:\Resin Compute" "E:\Resin Compute"` was run. Read back:
  LinkType Junction, Target `E:\Resin Compute`, and the hand-off file
  resolves through it. This keeps the sibling roots maps delivering until
  MAIN updates them.
- Step c, which also renews item 0. `ops/install_responder_task.ps1` was run
  with -TaskName RSC-InboxResponder and InstallRoot E: after a WhatIf pass.
  A fresh gitignored agreement record was written, OPERATOR shape, expiring at
  the window close. Read back by schtasks: Status Ready, Start In
  `E:\Resin Compute`, window 2026-10-08T00:45:00 to 2026-11-07T00:45:00.
  `python ops/check_task_liveness.py RSC-InboxResponder` read rc 0.
  The first fire at 00:45 read back as progress rsc-responder "fire ended
  empty", status done. `inbox_status.json` read state limit, 7 runs against a
  cap of 3, frees at 09:36. Known trap: the PT43200M repeat may end about an
  hour before EndBoundary because of the Nov 1 DST change.
- core.hooksPath read the absolute `E:\Resin Compute\.githooks` at /done.
  `python scripts/install_hooks.py` was re-run and the value read back as
  `.githooks`. The cause is filed in ROADMAP.md.
- Gates at 8a1907d plus paperwork, 2026-10-08, Python 3.14: licence 52;
  docs 42; qa 17 passed 2 skipped 3 noted; ruff clean; tests 1 failed 4133
  passed 6 skipped; pity_engine 80; node 52 pass 0 fail; dry run 0 pass
  0 fail 6 skip; mypy 41 files clean; kit `8 []`.
  - The one failure is the host-dependent
    `tests/test_task_liveness.py::test_the_real_probe_answers_for_a_task_outside_the_root_task_path`
    ("the scheduler refused the query"). It reproduced in a solo re-run, and
    this session changed no code.
  - The new sixth skip is `tests/test_responder_uniform_budget.py:705`: 8.3
    names are disabled on E:. That is a property of the volume after the move.
  - The paperwork push used RESIN_SKIP_PREPUSH=1 because the push is
    docs-only, so CI is the only gate on it. Pushed 7f1915d, and origin/main
    read back at 7f1915d. CI runs: ci 37734244001 and docs-guards
    37734243906, both QUEUED when recorded. Read back at the second /done:
    ci 37734244001 success. docs-guards 37734243906 was cancelled because
    640bc0c superseded it, and docs-guards 37734264014 on 640bc0c succeeded.
    ci 37734886978 on 1e03c24 (hand-off note of the v9 builder result)
    succeeded.
- Step d (kit v9) and MAIN ORDER 0230 (roster) were dispatched to builders in
  worktrees and were still running at /done. Neither is merged. The hand-off
  carries both.

## 2026-10-08 - Repo copied to E: and MIG-1 worktree prune (session 59)

Operator order in chat. MIG-1 per MAIN 2354 ORDER item 5: `git worktree list`
read 36 lines with 1 prunable before, 1 line after. The 34 agent worktree
directories went to the Recycle Bin; the 14 with uncommitted residue were
archived first to a gitignored runtime folder named in ROADMAP.md (one
folder per worktree holding a tracked diff, an untracked tar and its HEAD). Every pruned
branch was an ancestor of main; branches kept. The repo was then copied with
robocopy to `E:\Resin Compute` (4579 files, 0 failed), `git fsck` clean there,
README, docs/OPERATIONS.md and tests/test_machine_identity.py moved to the E:
canonical path in one commit. The C: checkout stays until the hand-off item
0a steps retire it; the responder task is disabled until re-armed from E:.
Measured 2026-10-08 at E: under Python 3.14 before this entry: pity_engine 80
passed, ruff clean; tests red only on this undocumented residue path.

## 2026-10-07 - Responder: verified MAIN ORDER/FIX/RULING bypass the per-sender reply cap

Defect (diagnosed read-only): `pending()` in `tools/moon_sync_responder.py`
dropped every note from a sender at `MAX_REPLIES_PER_SENDER` (3 per rolling
24 h) before looking at its class. MAIN held 3 rows (auto-replies to
superseded kit orders), so MAIN's 2155 ORDER was parked; the fire log read
`triage-work` then `empty`. Same refusal in the `record_outbound` re-check.
- Fix, merged at a487d15 (slice commits 4cdef6f, a640bf8, 0bc14ad): the cap
  is bypassed only when ONE parse of the filename gives sender MAIN and class
  ORDER, FIX or RULING AND the note's provenance is MATCH against MAIN's
  outbox. The exemption flows through `pending()` and `_reserve_targets` /
  `record_outbound(..., exempt=...)`. The 6/day outbound accounting is
  unchanged.
- Basis: the item-14 hard constraint "nothing may make a note wait" plus
  FLEET-COMMON 6 and 14b. NOT 14c, which exempts the OUTBOUND class
  (4cdef6f's message cites 14c in error; a640bf8 corrects it).
- Ruling: MAIN only. Alternative rejected: every sender's ORDER/FIX/RULING
  (reopens the sibling loop breaker). Reversed by: a MAIN ruling, or a
  sibling ORDER parked over 24 h in a way that blocks real work.
- Adversary passes: round 1 REFUTED (split parse let
  `x-from-main-ANSWER-from-LW-ORDER-y.md` past the cap; 14c misread), round 2
  REFUTED (siblings exempt), round 3 (provenance, behaviour diff) NOT
  REFUTED. Residual: an unverified capped MAIN ORDER is now hashed each fire
  before it is dropped (cost only).
- Tests: `tests/test_responder_loop_breakers.py` (cap-exemption cases); 4
  existing tests in `tests/test_headless_env.py` and
  `tests/test_responder_main_provenance.py` retargeted to a non-exempt
  CORRECTION note.
- Gate at a487d15, measured 2026-10-07 by /done (Python 3.14): licence 52;
  docs 42; qa 17 passed 2 skipped 3 noted; ruff clean; tests 4135 passed 5
  skipped; pity_engine 80; node 52 pass 0 fail; dry run 0 pass 0 fail 6
  skip; mypy 41 files clean.
- Observed after the merge: the live responder sent auto-reply 2251 (an ACK)
  to MAIN 2026-10-04 0020 ORDER, which the cap had been holding. The held
  MAIN backlog now drains, bounded by the 6/day outbound cap.
- Pushed 010bae0..77efd4c (pre-push hook OK, remote main read back
  77efd4c). CI on 77efd4c: ci 37725259629 and docs-guards 37725259618 were
  PENDING when recorded. A second auto-reply, 2256, went to MAIN 0230 ROSTER
  ORDER (still open work here, hand-off item 1). The follow-up push recording
  this line used RESIN_SKIP_PREPUSH=1 (docs only, CI the gate).
- `core.hooksPath` read back as an absolute path at /done; re-ran
  `scripts/install_hooks.py`, read back `.githooks`.

## 2026-10-07 - MAIN 2155 ORDER: C: path inventory before the move to E:, answered

MAIN 2026-10-07 2155 ORDER (operator authority), INVENTORY ONLY. Provenance
MATCH by `main_provenance`, sha256 16b0d10c...f544. Nothing in the tree,
task scheduler, registry or shortcuts was changed.
- Tracked corpus (292 files, `git ls-files`), 155 C: or ProgramData hits:
  0 HARDCODED (no tracked code or config names this repo's own root),
  9 HARDCODED* (absolute literal off any repo root: the shared slot bucket in
  `ops/loop/slots.py:40` and its test pin, the first-run capture default x3,
  game-install probe candidates x4), 1 DERIVED (`ops/fleet_kit/fleet_lanes.py`
  env lookup; plus the two task-XML templates, placeholders only), 145 DOC.
- EXTERNAL 56, 49 must change: `core.hooksPath` in `.git/config` (absolute),
  the RSC-InboxResponder task working directory, 5 Desktop shortcut fields, 35
  agent-worktree pointer pairs, 6 rows of the gitignored per-host roots
  map, and the harness trust key. RSC's
  `workspace_trust` passes a MISSING key, so after the move it would not catch
  an untrusted E: workspace; flagged to MAIN as a runbook operator step.
- Worktrees: 35 under `.claude/worktrees/`, every branch an ancestor of main;
  34 not needed (14 with uncommitted residue to review before prune), 1 locked
  (live session). One prunable registration whose folder is already gone.
- Reply: one ANSWER, HOP 2, TERMINAL
  `2026-10-07-2225-from-RSC-ANSWER-to-MAIN-2155-C-path-inventory-0-tracked-HARDCODED-9-HARDCODED-star-off-root-56-EXTERNAL-worktree-admin-and-trust-key-are-the-hazard.md`
  written to MAIN's inbox and this inbox through the responder's `deliver`;
  both copies read back with sha256 039d48d0...a562, 1/1 destination reached.
  2155 recorded answered (name plus sha256) in the responder's gitignored
  answered record through `_remember_answered` and `_remember_answered_sha`, so the responder does not send a duplicate.

## 2026-10-07 - MAIN 1927 FIX: superseded MAIN orders get no reply, marked TERMINAL

MAIN 2026-10-07 1927 FIX (operator authority): the unattended responder kept
auto-replying, one per fire, to 2026-10-03 MAIN orders already superseded by
kit v8 (MAIN 2026-10-05 0310). Every MAIN note went to the work lane with no
supersession test.
- Code, `tools/moon_sync_responder.py`: `superseded_main()` and the tracked
  `SUPERSEDED_MAIN_STAMPS` (the 14 stamps of FIX section 2). A superseded
  MAIN note is acked with one seen-ledger line, action skip, verdict
  `terminal-superseded`, and no session. Listed-stamp notes already seen as
  work are backfilled once and leave the work set the same fire; the
  triage-off legacy path drops them too. Unlisted MAIN notes (0230 roster,
  0300 supply chain, 0020 designs) still reach the work lane, pinned by arm.
- NO KIT-VERSION INFERENCE. A first cut (f610a34) also inferred "FLEET-KIT
  vN superseded by a vendored, announced vM > N". The adversary REFUTED it
  (correctness lens): it dropped a live MAIN FIX naming an older kit and a
  `v8-to-v9` migration order, and its backfill pulled queued live FIXes out
  after a manifest bump. The adjudicated narrow shape would match none of
  MAIN's real v6/v7/v8 order names, so the inference was deleted and only
  the tracked stamp list remains; arms pin both refutation names as live.
- Data: 15 lines appended to the live seen ledger via `fleet_inbox.mark_seen`
  (609 -> 624 lines, read back 2026-10-07): the 14 FIX notes as
  `terminal-superseded`, the 1927 FIX itself as `handled-by-session`.
- Suites 2026-10-07 on host python 3.14, after the round-2 fix: tests 4113
  passed 11 skipped (host-reason skips: no POSIX sh, no exec bit, network
  opt-in, bare python already pinned, POSIX-only guard); agents/pity_engine
  80 passed; ruff clean; mypy clean.
- Merged e16c9ae, pushed. /done gate 2026-10-07 on main, host python 3.14:
  tests 4119 passed 5 skipped; agents/pity_engine 80 passed; licence 52,
  docs-consistency 42; qa_companion 17 passed 2 skipped; shell node 52
  passed; runner dry-run 0 fail 6 skip; ruff clean; mypy 41 files clean. CI
  for e16c9ae: ci 37717123175 success, docs-guards 37717123176 success.
- Reply: one-line TERMINAL ANSWER
  `2026-10-07-2113-from-RSC-ANSWER-to-MAIN-1927-v8-FIX-applied-TERMINAL-no-reply.md`
  written to MAIN's inbox and this inbox; both copies read back with the
  same sha256 4d0c1471...f292, 1/1 destination reached.

## 2026-10-05 - FLEET-KIT v8 adopted (v6 lanes, v7 item 13, v8 item 14); responder flipped live

MAIN orders 2237 (v6), 0215 (v7) and 0310 (v8) each verified by sha256
against MAIN's outbox (MATCH, bundles 10/10, 11/11, 12/12). v8 supersedes v6
and v7 and was adopted directly, in four disjoint slices built in worktrees,
each refuted by an agent that did not build it, merged with real merge
commits and fast-forwarded to main at bed3725.
- Kit: all 12 v8 files vendored byte-for-byte (177857c v7, 2e07ce1 v8),
  FLEET-COMMON block re-embedded, `tests/test_fleet_kit.py` re-pinned to v8
  plus a manifest digest pin and a directory-listing arm (a762966) that fails
  on a rogue kit file. Kit v8 `fleet_inbox.py` fails ruff UP031 x8; one rule
  on one file is per-file-ignored in `ruff.toml`, never patched.
- Item 13: `tools/session_checklist.py` SessionStart hook, `SESSION: <n>`
  counter (seed 56, a commit-count proxy), /done pre-flight and unprompted
  run (2f1a9fc); responder progress task rsc-responder (parent-owned) and
  runner progress task rsc-runner with bounded retry (7d7b7e0, 5bd7771).
- v6 lanes: `core.config.LANE_CAP = 3`, AST-pinned literal; no lane driver
  exists, so it binds nothing yet; governor=None for every responder class
  (read-only child), runner keeps one slots.hold per live pass.
- Item 14 in `tools/moon_sync_responder.py`: fleet_inbox triage before any
  spawn, OutboundCap, batch_note, HOP in the head, per-note may_reply, kind
  labels (fda1c04). Four refutation rounds found 24 defects, all fixed
  (d82d639, 11458ff, 8fa6f3e, 75d72b2, 4b08f0e); round 5 NOT REFUTED with 4
  minors filed in ROADMAP. Bounds: 3 triage attempts per note, 3 work
  attempts per non-MAIN note then parked, a MAIN note never parked but cooled
  6 h (item 14 section 0), failed sends release their cap reservation.
- Flip: responder task disabled and drained, main fast-forwarded, gates green
  on the main checkout, task re-enabled, liveness rc 0. First fire read back
  at 05:16: ended empty, 228 backlog notes acked or skipped with no run, one
  triage run, progress rsc-responder done with an empty checklist, status
  file kit 8. Pushed bed3725; CI ci success run 37295880509, docs-guards
  success run 37295880492.
- ANSWER to MAIN delivered 05:23, recipient copy re-hashed, 1/1 reached;
  the three kit orders recorded answered so the responder does not re-answer.
Verification pointers: `tests/test_fleet_kit.py`,
`tests/test_session_checklist.py`, `tests/test_headless_runner_checklist.py`,
`tests/test_fleet_lanes_adoption.py`, `tests/test_responder_checklist.py`,
`tests/test_responder_inbox_v8.py`.
Gate run at bed3725, 2026-10-05, Python 3.14, private --basetemp outside
the repo, RESINCOMPUTE_RUNTIME_DIR unset: licence 52 passed; docs 42 passed; qa 17
passed 2 skipped 3 noted; ruff clean; tests 4108 passed 5 skipped (same five
host reasons); pity_engine 80 passed; node --test 52 pass 0 fail; dry run 0
pass 0 fail 6 skip; mypy 41 source files clean; kit v8 conformance [].

## 2026-10-04 - README landing page and the OVERVIEW / OPERATIONS split; cloud PR #1 recorded open

Landed as 1287b84 (2026-10-03 22:18 local) and 3fc4f81 (2026-10-04 00:04
local), both docs-only. `README.md` became a landing page with the social
preview card shown as a centered banner; the depth it carried moved to
`docs/OVERVIEW.md` and `docs/OPERATIONS.md`. Verification pointer:
`tests/test_docs_consistency.py` and `tests/test_readme_tree.py`; CI
docs-guards green on 1287b84 (run 37174107533) and on 3fc4f81 (run
37179092455), ci green on 1287b84 (run 37174107535) and the scheduled ci run
37206929329 on main green.
Also recorded, NOT landed: a cloud session is working 9 product items
against GitHub and opened ONE pull request, #1 (branch
claude/new-session-19dmsr, 14 commits, 40 files, +6217 -145, mergeable, both
PR checks pass as read 2026-10-04). Nothing from it is on main. The next local
session reviews it and lands it with a real merge commit, re-runs the gates,
and records each landed item here.
Two MAIN notes verified by sha256 against MAIN's outbox (2/2 match): the 0020
ORDER (kit v5 will carry the watcher, secret references and dashboard tokens;
do not build divergent local versions) and the 0905 INFORMATION (shared
scratchpad hazard; bare python3 is the Store stub).
Gate run at 3fc4f81, 2026-10-04, Python 3.14, private --basetemp outside the
repo, RESINCOMPUTE_RUNTIME_DIR unset: licence 52 passed; docs 42 passed; qa 17
passed 2 skipped 3 noted; ruff clean; tests 3946 passed 5 skipped (same five
host reasons); pity_engine 80 passed; node --test 52 pass 0 fail; dry run 0
pass 0 fail 6 skip; mypy 40 source files clean; kit v4 conformance [].

## 2026-10-04 (second ritual) - /done over an empty session: the gate re-measured at 2e5a610, paperwork only

A cloud session on PR #1 (branch claude/new-session-19dmsr) was opened,
cleared and closed with /done. Nothing was built; no file changed except the
ritual's own three (this ledger, `ROADMAP.md` untouched in the end because no
row was worked on, and `RSC-NEXT-SESSION.txt`); the inbox does not exist in
the clone and nothing was fired. This entry exists so the ritual's reading has
a dated home. It closes no ROADMAP row.

Gate, this ritual, Linux, Python 3.11.15, PYTHON unset, tree at 2e5a610:
`tests/test_licence_posture.py` 52 passed; `tests/test_docs_consistency.py`
42 passed; `scripts/qa_companion.py` 15 passed 0 failed 4 skipped 3 noted;
ruff clean; tests 4051 passed 39 skipped 0 failed in 166.12 s (collect-only
4090); `agents/pity_engine` 191 passed in 9.16 s; shell node --test 110 pass
0 fail; headless dry run rc 0, 0 pass 0 fail 7 skip; mypy clean over 42
source files (advisory). Glyph gates: source selected 236 scanned 235 exempt
1, docs 56 of 56, both 7-bit ASCII clean. The kit check printed 4 [].
The 39 skips, listed with -rs: 31 reasons shared with CI's run on 2e5a610
(ubuntu, Python 3.11.16, 4059 passed 31 skipped), plus 8 that belong to this
account and host - six in `tests/test_moon_sync_responder.py` and one in
`tests/test_session_hooks.py` because this account cannot be denied file
access, and one in `tests/test_publish_next_session.py` because no PowerShell
resolves here. Passed plus skipped is 4090 in this reading and in the previous
ritual's 4052 plus 38, so the one extra skip is a pass turned skip and not a
lost test. Named by diffing the two -rs lists over the same tree: the pre-push
hook's own run, launched through `scripts/hook_python.sh`, read 4052 passed 38
skipped in 165.21 s and `agents/pity_engine` 191 passed in 9.87 s, and the one
skip present only under python -m pytest is the bare-python arm in
`tests/test_interpreter_pinning.py`, which skips whenever a bare python
resolves to sys.executable - true under python -m pytest here and on CI, false
under the hook's interpreter. Environment, not tree.
`tools/publish_next_session.py --check` refused with reason no_desktop (this
host has no Desktop), the same environmental refusal the previous ritual
recorded; the hand-off cleared `extract_prompt` and `scan_for_leaks` with no
leak. No memory directory exists for this project on this host, so there was
nothing to index. CI: green on 2e5a610 (ci 37192046597, docs-guards
37192046590); the paperwork pushed as 08da213 fired ci 37208549885 and
docs-guards 37208549898, in progress when this sentence was written, and the
follow-up commit naming the skip fires its own pair. The push goes to the PR
branch, not main, per the cloud-run ruling in the entry below; the local
session merges PR #1.

## 2026-10-04 - cloud run: by-when route, reconcile_ledger, artifact scoring (ADR-012), ADR-013, hermeticity fixes, four rows closed by measurement

Sits on PR #1, branch claude/new-session-19dmsr, head f85d39b, PENDING THE
LOCAL MERGE: the cloud session that built it does not merge, and this
paperwork commit lands on that same branch, so main carries none of it until
the local session merges the PR. Every figure below is a Linux, Python
3.11.15 reading from a fresh public clone; nothing was measured on Windows or
on 3.14. One orchestrated run: each ROADMAP row was gap-analysed first, built
TDD-first in an isolated worktree, refuted by independent agents with
distinct lenses, and amended until no refutation stood. Shas are branch shas;
the proving pointers are merged files and test names.

WHAT LANDED, in branch order.
(1) ce64007 - the Chronicled remainder. Two socket-level arms in
`agents/pity_engine/tests/test_service.py`:
`test_live_chronicled_forecast_is_byte_identical_to_the_library_call` and
`test_live_bogus_banner_returns_400_without_raw_exception`. Measured at a
discriminating state (pity 89, budget 1: chronicled 0.5, character 0.52106,
standard 1.0); requesting "standard" instead reds the byte comparison, and
the bogus arm posting a valid banner reds. Engine suite 80 -> 82.
(2) 715caf0 and 5739a89 - the shell lib. Five files under `shell/test/` (57
arms over endpoint, state, geometry, window and supervisor degraded paths);
five lib mutants each red exactly the named test; node --test 52 -> 109 ->
110. The adjudicated fix shrinks `isLoopback` in `shell/lib/endpoint.js` to
127.0.0.1 and localhost, because `surface/server.py` binds AF_INET only: a
bare ::1 built an invalid URL into an un-caught promise and [::1] misreported
as "port held". Bracketing was rejected. D2, D3 and D4 are recorded under
Known gaps, not fixed.
(3) 389506a - hook-test hermeticity. `_run_sh` in
`tests/test_hook_interpreter.py` scrubs an ambient PYTHON and
RESIN_SKIP_PREPUSH; with PYTHON exported, the pre-push arms had run the real
full suite recursively (11 nested pytest processes observed). Pinned by
`test_an_ambient_python_never_reaches_the_selector_under_test` and two
siblings. Residual recorded: on a host whose sh is bash, an exported shell
function can shadow the stubbed PATH.
(4) e7f1982 and 6587582 - Enka and objectives coverage, then the fix the arms
exposed. 62 arms proven missing by a coverage matrix
(`tests/test_ingest_mapper.py` 30 -> 50, `tests/test_ingest_client.py` 35 ->
59 plus the opt-in skip, `tests/test_engines_objectives.py` 42 -> 60); a
scope refuter cut ten pins of undocumented defaults before landing. The fix:
`fold_talent_levels` in `ingest/enka_mapper.py` fired its opt-in positional
fallback after a direct hit, bonusing one skill twice and laundering two
unresolved bonuses; it now fires only when nothing was placed directly and
the nonzero maps are the same length, the docstring's own contract. The
default-off path is byte-identical before and after on a 22-input table.
(5) 1020fb0 - liveness arms. Five argv-shape arms in
`tests/test_task_liveness.py` take a lookup stub (the file's own precedent)
instead of needing a PowerShell binary they never run;
`test_the_lookup_stub_is_load_bearing_for_the_argv_arms` proves the stub is
what puts the sentinel in argv[0]. `ops/check_task_liveness.py` is
byte-identical. The full suite went from 5 host failures to 0 here, and CI no
longer rests on the runner image shipping pwsh.
(6) b1ead74 - citation guard part (1).
`test_the_bare_path_sweep_walked_a_real_corpus` in
`tests/test_docs_consistency.py` gains a per-suffix non-vacuity floor: one
independent probe per declared suffix, and the probe's finds minus the
extractor's finds must be empty. Of the 1820 four-branch subsets of the 16
declared branches (the row's "13" matched no committed state), 4 survived the
old floor and 0 survive the new. Refuted once - the probe lookahead admitted
a slash, so a dir-dot-json over file-dot-py token false-redded - and fixed;
the re-check's formal argument plus a 946,000-case fuzz found no over-see.
(7) ebf2942 - `reconcile_ledger` in `headless/jobs.py`, between
`reconcile_state` and `persist_state`, default-off. Reads the operator-typed,
gitignored data/income_observations.json (schema_version 1: id, at,
currency, delta, note; an `observations_path` option overrides), validates
every row before appending any, rebuilds per pass for idempotency with an
in-pass double-call guard, re-estimates the velocity; `persist_state` now
depends on it. The dry-run output changed by one SKIP line and the job count
only, and both runtime dirs stayed empty (builder and refuter). 45 arms in
`tests/test_headless_reconcile_ledger.py`; mutants red for a partial fold, a
dry run that appends, the guard off, and velocity not re-estimated. The
whole-tree conflation census in `tests/test_task_state_claims.py` moved 76
-> 107 (31 new Python lines naming a `state` attribute) and was re-measured
at the seam.
(8) 40a4b31 - POST /by-when. New `agents/pity_engine/timeline.py`
(`BannerWindow`, `WindowOutcome`, `ByWhenResult`, `by_when`) and one new
branch in `agents/pity_engine/__main__.py`, zero lines removed. The caller
supplies the schedule; no calendar, banner name, date or duration lives in
the tree (test dates are 2099 and 2100). Proven by
`agents/pity_engine/tests/test_timeline.py` -
`test_the_end_date_is_inclusive`, `test_accrual_is_floored_not_rounded`,
`test_a_flat_curve_breaks_the_tie_on_the_earliest_eligible_day` - and
`agents/pity_engine/tests/test_service_by_when.py`. ENGINE_VERSION stays
0.1.0: a 23-case golden diff of every existing `/health`, `/forecast`, 400
and 404 body is empty, by two independent scripts. Mutants: exclusive end 7
red; overlap check off 3; unreachable raises 10; strict date dropped 5;
latest-day tie-break 3; round for floor 3; `end <= as_of` 2; overflow guard
off 1. Refuted once (three one-token mutants survived) and amended with four
pins and a finiteness guard.
(9) f23ad34 - `engines/artifact_score.py` with
`docs/adr/ADR-012-artifact-scoring-model.md` (Status Proposed; operator
confirmation pending). A weighted substat sum over caller-supplied weights,
roll counts over caller-supplied magnitudes as floor((value + tolerance) /
magnitude), a deterministic rank key; every numeral in the module is 0.0, no
string literal, no I/O import, and an AST arm pins that. 20 arms in
`tests/test_engines_artifact_score.py`, among them
`test_both_weights_at_one_return_the_sum`. Refuted twice and amended three
times: NaN in any sort-key field and a non-finite quotient are refused by
name; the ADR states fold start, check order, absent-key validation,
main-stat handling and the signed-zero tie rule; the roll example uses an
opaque hand-built artifact with a magnitude labelled arbitrary in-sentence.
(10) ebf89d4 - `docs/adr/ADR-013-roots-map-identity-anchor.md`, Status
Proposed, design only, no code. Target: an untracked random beacon in MAIN's
outbox, pinned here by digest, read only when a MAIN note is queued and after
the byte match, no git. Rejected: any tracked digest of a URL, path or commit
id, a confirmation oracle in a public clone; quorum with the kit's
`verify_main` recorded as settled by ADR-011. Proven by the four ADR guards
in `tests/test_docs_consistency.py`: `test_every_adr_file_appears_in_the_index`,
`test_adr_numbers_are_unique_and_contiguous`,
`test_every_adr_declares_a_status` and
`test_every_path_the_docs_directory_points_at_is_tracked_by_git`. A hygiene
refuter found no URL, hash, row value, sibling name or machine path after
three rewordings. Five operator asks are listed in the ADR.
(11) f85d39b - the merger: ADR index rows 012 and 013, README tree rows for
`agents/pity_engine/timeline.py`, `engines/artifact_score.py` and
`shell/test/`, the `agents/pity_engine/CHANGELOG.md` service section for
POST /by-when (no revision bump), seven-job wording across `README.md` and
`docs/OVERVIEW.md`, and the census constant re-measured at the seam (107,
unchanged).

CLOSED BY MEASUREMENT, NO CODE, each reproduced cold by a second agent.
"THREE SILENT OVER-EXCLUSIONS IN core/repo_sweep.py": the prefix mutant reds
`test_the_foreign_name_rule_is_exact_and_never_a_prefix_or_a_substring` in
`tests/test_guard_worktree_exclusion.py` with 40 collateral names; the
name-contains-marker mutant reds 9 arms across 5 modules (47ac112 said six;
the sixth now derives its corpus from git ls-files and does not red); the
literal-union mutant reds 2 arms in `tests/test_walkprune.py`. "A HAND-LIST
OF DERIVING SITES": a staged fifth importer of `core/walkprune.py` reds
`test_no_unregistered_module_imports_the_owner` naming the path; untracked
it is invisible by design. "TWO TEST-INSTRUMENT GAPS", the open half:
439bcc2 added the message lane to `tools/gate_mutation_runner.py`; its two
recorded survivors are in MESSAGE_MUTANTS, KNOWN_MESSAGE_SURVIVORS is empty,
17 kill instances pinned; `tests/test_gate_mutation_runner.py` read 87
passed, re-measured by this ritual. Scope: the lane grades the -F path, the
editor flow is graded in `tests/test_hook_gate.py`. "Prove the git hook gate
FIRES, in CI": the ci.yml step "git hook gate armed and firing" runs
`tests/test_hook_gate.py` under RSC_REQUIRE_HOOK_GATE=1 and covers both
directions (staged glyph refused with HEAD unchanged; message glyph refused;
clean commit lands with HEAD advanced); 60 passed, 0 skipped under the flag.

ADJUDICATED (decision; why), one line each.
- by-when as a new module and route, over fields on /forecast (edits the one
  function every service test exercises) or a dashboard computation (outside
  the engine's versioning); inclusive ends, overlap 400, closed window 400,
  as_of required and strict, confidence 0.9, floor of the float product,
  unreachable is a 200 with reachable=false; no ENGINE_VERSION bump because
  no returned number changed.
- reconcile_ledger reads a hand-authored file under RC_DATA_DIR with an
  options override, over a CLI flag (runner changes behind AST guards) or a
  tracked fixture (licence surface); rebuild-per-pass over a watermark
  (lane-read state the AST guard forbids); `.json` not `.jsonl` because the
  provenance sweep grades every `.jsonl` under data/ as a receipted row.
- artifact scoring is a weighted sum with roll-count optional and rank
  sort-only, over roll-count alone (nothing without unverifiable magnitudes)
  or percentile-vs-reference; weights required, weight 0.0 is weighted,
  unknown keys ignored but validated, NaN refused, signed zero equal; Status
  Proposed because the operator asked for local confirmation.
- roots map: a2 (untracked random beacon pinned by digest) as target, d
  (status quo plus a session-start ritual) interim, b2 (tracked digest of the
  gitignored map) runner-up, lost on hygiene - a tracked oracle in a public
  repo is permanent and gate-invisible; c settled by ADR-011.
- shell: fix D1 only; D2 is the safer side of an asymmetry, D3 is
  unreachable from main.js, D4's root cause spans state.isBounds.
- mapper: FIX the positional-fallback double bonus (the docstring is the
  contract; the fix returns more unresolved, never a guess); RECORD the
  weapon missing-level default (1 against the character's 0, contract silent)
  and the swallowed unreadable bonus (surfacing it moves SPEC 5.1 text).
- liveness: stub the lookup in the five argv arms, over planting a fake pwsh
  (a bypass in spirit; the tree already recorded a CI incident of that shape)
  or leaving the push blocked; the SKIP LIST's "check_task_liveness" was read
  as the ritual, not its unit tests.
- commit identity: the environment injects the repository's own author
  identity; signing was turned off for this clone so the branch matches the
  unsigned history, rather than re-authoring under an identity no commit here
  carries.
- baseline: taken with the ambient PYTHON unset after the recursion was
  found, and recorded as such.

REFUTED AND AMENDED. by-when: three one-token mutants survived -> four pins
and a finiteness guard. Artifact scoring: ADR under-specification, a "no
number ships" over-claim, a NaN rank-order leak and a floor overflow -> three
amends, licence re-check CLEARED. Citation floor: the lookahead admitted a
slash -> fixed, re-check NOT REFUTED. Hook hermeticity: the claim wording ->
both asks implemented. Enka arms: ten pins of undocumented defaults -> cut.
Endpoint fix: one stale comment reference -> corrected, behaviour held. The
operator's SKIP LIST held: no responder, scheduled task, live fire, inbox,
worktree housekeeping, PowerShell 5.1 or network act was attempted, and
citation guard parts (2) to (4) were not touched.

SEAM FIGURES, 2026-10-04, Python 3.11.15, Linux. Builder gate on f85d39b:
tests 4052 passed 38 skipped 0 failed; engine 191 passed; ruff clean; mypy 42
source files (base 40); node --test 110 pass; headless dry run rc 0, 0 pass 0
fail 7 skip; `tests/test_hook_gate.py` 60 passed 0 skipped under
RSC_REQUIRE_HOOK_GATE=1. Baseline at 3fc4f81 on the same host: tests 5 failed
(host-only, no PowerShell) 3908 passed 38 skipped; engine 80; mypy 40; node
52; dry run 6 skip. CI: the single job "lint, types, dual suite, headless
smoke" passed on 1020fb0 (run 37187295913), 40a4b31 (run 37187819688) and
f85d39b (run 37189991580); the docs-guards workflow passed on f85d39b (run
37189991592). THIS PAPERWORK'S OWN GATE, same host, 2026-10-04, over the tree
carrying these three edits: `python -m pytest tests` -> 4052 passed, 38
skipped, 0 failed (121.89 s); `python -m pytest agents/pity_engine` -> 191
passed (9.06 s); ruff clean; mypy 42 source files;
`tests/test_docs_consistency.py` 42 passed; `tests/test_licence_posture.py` 52
passed; `tests/test_no_sibling_names.py` with `tests/test_machine_identity.py`
75 passed; `tests/test_task_state_claims.py` with `tests/test_readme_tree.py`
and `tests/test_ci_workflow_complement.py` 95 passed;
`tests/test_gate_mutation_runner.py` 87 passed; glyph gates selected=236
scanned=235 exempt=1 over tracked non-md files and selected=56 scanned=56 over
tracked md; the hand-off cleared the publisher's own extractor - size floor,
ASCII rule, leak scan - with no leak (the publisher's --check itself refuses
inside a linked worktree, which is its contract, not a finding). The headless
dry run re-read 0 pass 0 fail 7 skip.

## 2026-10-03 (night) - two recorded gaps closed: the editor --cleanup= hole and the orphan runner .tmp

Merged as db634b1 (branches ending ed2f4a0/ba8aaa0 and b982c90/ada50f9).
(1) COMMIT-MSG GATE: git passes the hook no cleanup flag but writes the
EFFECTIVE mode into the editor template ("will be ignored" vs "will be
kept"). `.githooks/commit-msg` exports `RESIN_COMMIT_MSG_FILE` and
`scripts/precommit_msg_check.py` skips `#` lines in an editor commit only on
the exact strip sentence; keep sentence, no sentence and the `merge --edit`
template fail closed. Eight end-to-end arms in `tests/test_hook_gate.py`, each
with a hooks-off twin, red before the fix. An adversary REFUTED the first cut
on one new false block (a `--no-status` editor commit after a conflict on a
non-ASCII path); adjudicated KEEP fail-closed, recorded as a residual and
pinned BLOCKED. Exec bit read back 100755 in the index for all three hooks.
(2) ORPHAN TEMPS: `_die_holding_slot` ends with `os._exit`, skipping
the `finally` in `core/atomic_io.py`. `headless/runner.py` `sweep_orphan_temps` now
removes, on each live pass, only a regular file of the exact atomic_io temp
shape whose pid is not ours, not alive and within 1..2**32-1, aged at least
3600 s, inside the repo root; one bad entry is logged and skipped and the
sweep can never fail a pass. Arms in
`tests/test_headless_runner_orphan_temps.py`. Round 1 REFUTED (a pid of 2**32
crashed the daemon via ctypes), round 2 NOT REFUTED.
Also this session: RSC 1540 (kit v5 gap list, four gaps reproduced in
`ops/fleet_kit/fleet_headless.py`) and RSC 1657 (ANSWER to MAIN 1325, live
status sample written by d8695e7) delivered and read back 2/2 by sha256.
Seam verify at db634b1, 2026-10-03, Python 3.14: tests 3902 passed 5
skipped; CI ci and docs-guards green on db634b1.

## 2026-10-03 (night) - a retryably UNVERIFIABLE MAIN note is deferred, boundedly, instead of lost

Closes the liveness gap ADR-011 filed. Before: a MAIN note that arrived
before MAIN wrote its outbox copy read UNVERIFIABLE on its first tick, was
answered as data, went into the answered record, and was never re-checked.
Now `Provenance` carries `retryable` (appended at the end, default False),
True only for an absent or unlistable outbox copy or bundle twin and a copy
that raised on read. `defer_unverified`, one plain assignment in `_run_once`
between `drop_redrops` and `bypass_queue`, takes such a note out of the queue
and records it by name in `responder_provenance_deferred.json` under the
runtime dir (gitignored by `ops/runtime/*`). Released as data after 3 counted
checks at least 240 s apart or 900 s after first seen; a later MATCH or
MISMATCH drops the entry. Every failure of the record releases rather than
holds. `_empty_termination` gained a defaulted parameter and returns
`provenance-deferred`, which `_TICK_STATES` leaves at idle/Idle. The gate
census floor and the gate name bindings are unchanged. Failing-first: 31 arms
in `tests/test_responder_main_provenance.py` red against db634b1 (adversary
measurement; the builder's own first run read 30, taken before the
malformed-entry arm was added), with the behavioural ones reading `delivered`
where `provenance-deferred` was wanted.

REFUTED ON f132394 BY TWO ADVERSARIES, fixed in the follow-up commit. (1) The
deferral's expiry line was written under the fire's own label mid-fire, and
the root conftest's `_live_fire_windows` ends a scheduled fire at the next
line under that label, so the window collapsed to [start, start] and the live
session's later writes read as a leak (false drift in the armed checkout).
Same hazard, pre-existing, in `provenance_for`'s unverifiable-class line and
`deliver`'s three skip/fail lines: all now go through `_log_fire_detail`. The
first fix, 3a75d47, held them in memory until the terminal line; a round-2
adversary REFUTED it: a hard kill during the spawn lost them, a regression
from db634b1 where the unverifiable-class line reached the log first.
Adjudicated and landed in the next commit: each detail line is written AT
ONCE under the label `firedetail` (`FIRE_DETAIL_SOURCE`), the caller's label
carried as `<caller>:<outcome>`, and the root `conftest.py` lists
`firedetail` in `_LIVE_WRITER_SOURCES` only, so it opens and closes no
window. A child-interpreter arm kills the spawn with `os._exit` and finds both
detail lines in the log; against the 3a75d47 module the same child found
neither. The `fail-closed:provenance-deferred-*` lines carry `failclosed`,
which opens and closes no window; pinned. A round-3 adversary REFUTED that
commit's leak guard: `_test_shaped` read only the label column, so a test
child's `firedetail ... cli:<outcome>` line inside a live fire was excused,
where db634b1 caught the equivalent `cli` line. Fixed next: a `firedetail`
line is test-shaped unless its caller prefix is in `_LIVE_FIRE_SOURCES`, and
one with no prefix is test-shaped; arms for `cli`, `run_once`, `suite`, no
prefix and empty prefix (flagged), `scheduledtask` (excused), and the real
`deliver` reproducer, all red before the fix. (2) `provenance-deferred` joined
`TERMINATIONS`. (3) A released entry is pruned 24 h after `first_seen`
(`DEFER_PRUNE_AGE_S`), so never-answered notes cannot fill the 64 slots; the
inbox-file-gone prune branch gained an arm. Each of the three fixes was
mutated on a scratch copy and its arm went red. (4) ADR-011's hypothetical C
log reason now names the real line.
Not done: the roots-map common-mode item stays open in `ROADMAP.md`, noted
there as only partly feasible.

## 2026-10-03 (late) - MAIN provenance adjudicated: the outbox byte hash stays (ADR-011)

DECISION RECORDED, NO CODE CHANGE. FLEET-KIT v4 item (3) asked whether the
responder should replace `tools/moon_sync_responder.py::main_provenance` (raw-
byte SHA-256 of MAIN's outbox copy, 4 MiB cap `MAX_PROVENANCE_BYTES`, no git)
with the kit's `verify_main` (committed blob). An adjudicator chose A, keep it,
against the pinned operator wording in CLAUDE.md and the v4 order's section 7
scope (7.1 adds `verify_main` for the v4 delivery note and its five bundle
files only; the 7.3 adoption list excludes provenance; 7.4 is advice).
Rejected: B kit-only, C both plus retry, D either. Evidence, measured
2026-10-03: over 27 real MAIN notes in the inbox both checks agreed and all
passed; three other `-from-MAIN-` named files were this tree's own auto-reply
files; the commit-lag case was never observed. Two items filed in
`ROADMAP.md`: the UNVERIFIABLE-recorded-answered liveness gap, and the
untested roots-map common-mode risk. See
`docs/adr/ADR-011-main-provenance.md`.

## 2026-10-03 (late) - the /120 counter settled: the binding ledger reports, kit refusals included

RESIDUAL CLOSED. A refusal by the fleet kit's own `RunBudget` (the read-only
pre-check, or `kit.spawn`'s own "budget" refusal) raised plain
`RunBudgetSpent`, so the tick status counted from and named `cap_frees_at`
from the RESPONDER ledger - the wrong ledger, or null and a Backing Off
when that ledger was empty. Now `KitRunBudgetSpent` ends the fire
`kit-run-budget` and `_status_budget` reads the kit ledger through its own
`RunBudget` API. Failing first in `tests/test_headless_env.py`: no
`KitRunBudgetSpent`, and termination `run-budget` where `kit-run-budget` was
expected. Mutant (kit branch routed back to the responder ledger) observed
red on the free time: responder row + 24 h instead of the kit's oldest
start + 24 h. Neighbour kept: a kit "budget lock busy" still maps to
`run-locked`. Also `window_s`/`runs_cap` now ship as ints (86400.0 observed
before). ADVERSARY REFUTED the first cut with two counterexamples, both
ported fail-first: with BOTH run ledgers full the status named the kit's
free time about 2 h before the responder ledger freed (now the later of the
two, with that ledger's counts); and a transient kit read refusal shipped
"limit" at 5/120 (now Backing Off - a limit needs a full ledger on re-read -
and an unreadable kit ledger is `KitBudgetUnreadable`, termination
`usage-backoff`, matched by type before the "budget" string match). Two
older arms that expected "limit" over a partial ledger were reseeded full.
ROUND 2 REFUTED two more, ported fail-first: an unreadable kit ledger left
no durable fail-closed line (now `fail-closed:kit-run-budget-unreadable`);
and the pre-check read the kit file twice (`readable()` then `can_start()`),
so a second-read failure reported "(120/120)" at a real 5/120 - now one read
through the kit's `_load`, then decide. The round-2 probe, run against this
tree, reads usage-backoff with the fail-closed line on both cases. ROUND 3
REFUTED the status path: `_status_budget` read the kit ledger twice
(`used()` then `frees_at()`), so one transient failure shipped a 120/120 kit
limit at a real 5/120 freeing about 22 h late. Now one `_load` per decision
there too, and one snapshot of each run ledger per tick; fail-first arms
counted 2 reads where 1 is required. The wrong-ledger mutant
(`_status_budget` forced onto the responder ledger), applied in source, was
killed by 10 arms in `tests/test_headless_env.py`; source restored and
cmp-identical. ROUND 4 REFUTED one crash: a full kit
ledger of Infinity stamps made `kit._iso` raise OverflowError out of
`run_once` every tick, and (pre-existing sibling) one epoch-ms responder row
crashed the idle write. Ported fail-first (6 arms, all OverflowError or
OSError escaping); now unprintable stamps make a ledger unreadable and both
status writers catch OverflowError as a backstop.
Decision on separate fields and on unifying ledgers recorded in
`ROADMAP.md` under "THE /120 COUNTER". Uncommitted at writing.

---

## 2026-10-03 (evening) - FLEET-KIT v4 adopted, the responder spawns through the kit, six backlog slices landed, and a Linux-only CI red closed

FLEET KIT. Every MAIN kit file was hashed against MAIN's outbox at the same
relative path before use: v3 3/3 plus the 1016 and 1029 notes MATCH; v4 the
1204 note plus five files 6/6 MATCH. `65cca9a` vendored v3, `49c06f2`
replaced it with all five v4 files in one commit (`ops/fleet_kit/`), Apache-2.0
recorded in `docs/LICENSE_NOTES.md` as one-way compatible into GPL-3.0 with
NOTICE preserved. `tests/test_fleet_kit.py` failed first on the missing
CLAUDE.md markers and reads `conformance('.') == []` at v4. `CLAUDE.md` went
29605 -> 21856 bytes with FLEET-COMMON embedded byte-for-byte; the old text
is verbatim in `docs/claude-md-history.md`; an adversary found ten rules the
condense dropped and `ee2cb73` restored them. `/done` now prints one line
(`.claude/commands/done.md`); roster agents write progress files
(`tests/test_agent_roster.py` Guard 8). `68c3a54` made the pre-commit gate's
ruff half pass `--force-exclude` so it honours ruff.toml excludes as CI does.

RESPONDER ON THE KIT. The one headless spawn, `_spawn_headless` in
`tools/moon_sync_responder.py`, goes through `fleet_headless.spawn` with
bare, stdin, cwd, halt_file and note, and extra carrying `--permission-mode
dontAsk` and a Read,Grep,Glob floor. Adversary rounds found and the builder
fixed fail-first: an error JSON accepted as a draft; a kit refusal burning a
responder run; a Bash floor escape (`git log --output=` then `python -m
pytest`), so Bash left the child floor and the parent passes git facts in a
nonce-delimited block a note cannot forge; drafts scrubbed for credential
shapes; a quoted TERMINAL line silencing MAIN notes once the MAIN bypass was
dropped (restored in `2ecc226`). Proven by `tests/test_headless_env.py` and
`tests/test_responder_main_provenance.py`. LIVE PROBE, 2 runs: the local
proxy accepted the kit placeholder key; Write and Bash were never offered to
the child and no probe file was written; about 1748 and 1413 input tokens per
run; `dontAsk` itself was never exercised.

STATUS FILE. `850bd79` keeps every task name in the MAIN 0915 set (the
widget had shown [?] for "MAIN Reply Limit"); `46c2b3e` makes a limit tick
carry counts and `cap_frees_at` from the cap that binds, never null. Read
back live 2026-10-03T14:31:01-05:00: limit, Turn Limit Reached, 3/3, frees
2026-10-03T23:11:00-05:00. MAIN 1325 answered, 1/1 reached by hash.

BACKLOG SLICES. S2 `227712b`: slots.py pin comments re-derived (290cbf80,
11426 B) and the arm-A live-holder test in `tests/test_loop_concurrency.py`,
which kills an age-first `is_stale` mutant 12 other arms let through. S3
`50d25c3`..`22a5472`: provenance tokens matched on a canonical whole-draft
form, re-drop dedupe on MATCH-only content hashes, HALT via lstat and
re-checked before the run is reserved and before spawn, the root
`conftest.py` fence expands 8.3 names and attributes drift by appended LINES.
S4 `4828eba`..`1280bde`: `headless/runner.py` bounds each job
(`JOB_DEADLINE_SECONDS`), exits holding the slot when a job is abandoned,
quarantines a job abandoned twice (`headless/quarantine.py`), HALT via lstat;
`tests/test_headless_runner_quarantine.py`; the merger re-ran the
second-holder arm 30/30. S5 `439bcc2`: a commit-message lane in
`tools/gate_mutation_runner.py`. S6 `7e52ada`..`4b739c0`: the commit-msg
gate judges the bytes git will keep (`#` lines under -F/-m), three adversary
passes, `tests/test_precommit_gate_message.py`.

CI RED, CLOSED. `ci` failed from `65c1622` to `22a5472`: on Linux the
message lane's hook copies had no exec bit, git ignored the hooks and every
mutant read SURVIVED; Windows has no exec bit, so every local run was green.
The fix commit after `22a5472` sets the bit on disk and raises on git's
ignored-hook hint. Readings at `22a5472`, 2026-10-03: tests 3816 passed 4
skipped, pity_engine 80, node 52, licence 52, docs 42, qa 17 passed 2
skipped, mypy 40 files clean, kit v4 conformance [].

---

## 2026-10-03 (close) - CI was red from 9061eb4 to 7551604; 2d108ee and 14b1ee5 turned it green

The live-runtime fence from `9061eb4` passed on Windows and failed on Linux CI
(both `ci` and `docs-guards`). Cause, measured from the CI log and reproduced
with synthetic events: Linux `shutil.rmtree` removes entries by name relative
to an open directory handle, so pytest's own `tmp_path` cleanup raised
`('os.rmdir', ('moon_sync_inbox', fd))`; the fence joined the bare name onto
the cwd (the repo root) and reported the live inbox. Windows never emits that
event. `2d108ee` resolves every fenced path through `_resolve_event_path(path,
dir_fd)` in `conftest.py`, pinned by `tests/test_live_runtime_fence.py`, and
replaces a Windows-only `0x100` literal with `os.O_CREAT` in
`tests/test_responder_uniform_budget.py`. The pre-push run then caught a second
defect: the empty-parametrize probe child walked the shared temp directory up
to the drive root; `14b1ee5` confines it with `--confcutdir`, pinned by a
trap-conftest arm in `tests/test_empty_parametrize_policy.py`. Readings,
2026-10-03 at `14b1ee5`: pre-push tests 3479 passed 4 skipped, pity_engine 80;
CI `ci` success.

---

## 2026-10-03 (second half) - C4 landed, a HALT sentinel and lock budget, MAIN provenance in the responder, and a test leak fenced

Landed as `bcbabc7`, `a875e48`, `9f49813`, `be03565`, `3d62942`, `1829b9d`
and `9061eb4`, all on `main`.

WHAT CHANGED. `bcbabc7` sets `empty_parameter_set_mark = fail_at_collect` in
`pytest.ini`, so an empty parametrize list fails at collection instead of
skipping (LL 0930); proven by `tests/test_empty_parametrize_policy.py`,
verified on 3.11.9 with pytest 9.1.1 as well as the host interpreter.
`a875e48` names the Anthropic admin and api03 key families in `VENDOR_TOKENS`
in `tools/publish_next_session.py` rather than catching them incidentally
through the shared prefix (CS 1820 item 2); proven by
`tests/test_no_secret_literals.py`. `9f49813` teaches the git-install oracle
in `tests/test_hook_interpreter.py` the hook-shaped `git-core` PATH, so it
grades instead of skipping; the extra pre-push-only skip is gone (reading
under a real push: 3348 passed 4 skipped).

`be03565` gives `headless/runner.py` a durable HALT sentinel in the runtime
directory, consulted before `hold()`, failing closed on an `os.stat` error and
never deleted by the runner; a slot-wait cap `MAX_SLOT_WAIT_SECONDS` of 300;
and a monotonic pass deadline `PASS_DEADLINE_SECONDS` of 3600. Proven by
`tests/test_headless_runner_halt.py` and
`tests/test_headless_runner_lock_budget.py`; it also adds the zero-hit worker
ack arm in `tests/test_headless_runner_slots.py`, closing the S1 test-strength
gap. Answers RC 1330 s3 and SS 0000. RESIDUALS, recorded in `ROADMAP.md`: a
hung job is unbounded (the deadline is checked between jobs), and a dangling
HALT symlink reads as go.

`3d62942` lands C4 `290cbf80` in `ops/loop/slots.py` under the
sha256-verified MAIN 0815 clause (b) ruling: one commit, the `SHARED_SHA256`
pin moved, `ops/loop/winmutex.py` untouched. `is_stale` now consults liveness
below a hard ceiling of twice the stale window, so the 2026-09-20
"SHORT-CIRCUITS ON AGE" row is superseded. Attestation note 0826 delivered to
six codes, 6 of 6 recipient copies sha256-matched; RSC's row of the C4 round
is CLOSED. LL's age-only reaper hazard (LL 2136) was closed on LL's side by
LL `474a165` (LL 0815).

`1829b9d` puts MAIN provenance inside `tools/moon_sync_responder.py`: each
MAIN note grades MATCH, MISMATCH, UNVERIFIABLE or NOT-ADDRESSED against MAIN's
outbox sha256, with one deterministic `[RSC-PROVENANCE]` line and an
addressing rule (`tests/test_responder_main_provenance.py`). It adds one
`MAX_RUNS_PER_DAY` budget of 120 under an OS lock per MAIN 0855
(`tests/test_responder_uniform_budget.py`), restores the 0845 knobs, bypasses
the exhausted hop budget for MATCH MAIN notes only (adjudicated), and damps
TERMINAL / no-reply notes. MEASURED: user-scope settings default to
`bypassPermissions`, so the child's tool floor held only by the child's own
choice; `SPAWN_COMMAND` now carries `--permission-mode dontAsk
--strict-mcp-config --tools Read,Grep,Glob,Bash`, and the floor was measured
harness-denied live. Three adversary rounds. The responder then answered
MAIN 0815 (as 0921) and MAIN 0830 (as 0926) unattended.

`9061eb4` fixes a test leak: the contention arm in
`tests/test_responder_uniform_budget.py` spawned children without
`RESINCOMPUTE_RUNTIME_DIR`, and the `rsp` fixture in
`tests/test_responder_no_console_window.py` redirected no `DEFAULT_` path, so
each suite run wrote this checkout's live runtime and spent real budget rows.
Both now use tmp dirs. `conftest.py` gains an audit-hook fence on the live
responder records plus a per-test drift check, excused only by a real
scheduled-task fire window. BACKFILLED: the gitignored run record was
rewritten from 8 rows to the 2 real ones.

DECISIONS. The MAIN provenance check was built by MAIN 0830 order, closing the
"only if the operator wants" row. The hop-budget bypass applies to MATCH MAIN
notes only, by adjudication. Residuals are stated in `ROADMAP.md` rather than
fixed: lookalike provenance tokens, a re-dropped MAIN note answered again
(bounded three per day), 8.3 short paths past the fence, and leaks during a
real fire excused by the drift check.

READINGS, 2026-10-03, at `9061eb4` under pre-push: tests 3467 passed 4
skipped; pity_engine 80. Earlier seam readings the same day: node 52, licence
47, docs 42, qa 17 passed 2 skipped 3 noted, mypy 40 source files.

---

## 2026-10-03 - one spawn cwd, a widened env-render detector, a governed --once, and the inbox triaged

Landed as `662ee0a`, `8f892b2` and `6f7a629`, all on `main`.

WHAT CHANGED. `662ee0a` makes one constant, `SPAWN_CWD` in
`tools/moon_sync_responder.py`, feed both `workspace_trust` and the headless
spawn's working directory, so the directory trusted and the directory spawned
in cannot drift apart. Proven by `tests/test_responder_spawn_cwd.py`; an
adversary reverted each of the two sites separately and both arms went red.

`8f892b2` widens the env-render detector in `tests/test_session_hooks.py`: it
now flags ANY `environ`, `environb` or `getenv` reference in an assert's test
expression or message, except the right-hand side of `in` / `not in` inside
the message. The forms previously treated as safe - `get(key) is None`,
`environ[key] == x`, `set(os.environ)` - were MEASURED leaking their operands
into the rendered assertion on pytest 9.0.3. Reported by four sibling notes:
LL 2140, LL 2320, RC 0940/1030 and SS 1930.

`6f7a629` makes a live `--once` pass hold a machine-wide slot: `run_once` in
`headless/runner.py` routes through `_run_governed_pass`, a dry run takes no
slot, and a `SlotTimeout` becomes `EXIT_JOB_FAILED`. Proven by
`tests/test_headless_runner_slots.py`. The suite is fenced by an audit hook in
`conftest.py` on `ops.loop.slots.DEFAULT_ROOT`: a hit fails the test from any
thread, and `SlotFenceLedger.acknowledge` acks by exact count from the main
thread only. NOT fenced, stated rather than implied: child processes, alias
spellings of the path, sqlite3/ctypes access, and xdist workers. Four
adversary rounds refuted earlier versions before merge - a shape guard blind
to 11 of 13 shapes, worker-thread hits that only warned, scope comments that
overclaimed, and an ack hidden by thread-ident reuse measured at about 3424
cycles. RESIDUAL, recorded in `ROADMAP.md`: verifier mutant A (dropping the
refusal record in `acknowledge`) does not turn
`test_acknowledging_from_a_worker_thread_fails` red.

DECISIONS. Spawn cwd: KEEP the repo cwd - the child is meant to load this
tree's rules and hooks, and trust must cover the same directory. Teardown
digests (MAIN 2320 ruling): audited rather than built - zero of the 13
responder write targets is covered by any before/after digest guard (AST walk
and grep agree), because `conftest.py` deliberately refuses live-directory
snapshots that concurrent daemons would falsify; protection is prevention via
the `rsp` fixture's `DEFAULT_*` redirection and `RESINCOMPUTE_RUNTIME_DIR`.

INBOX. About 420 files triaged in five batches into the four buckets, per-file
verdicts in the session scratchpad and not tracked; NOT `--mark`ed. All nine
MAIN notes dated 10-02/03 sha256-verified against MAIN's outbox. Five ANSWER
notes stamped 2026-10-03-0704 (to LW, RC, CS, SS and LL) were each delivered
to all six codes, 30 copies, every recipient copy sha256-matched; an
adversary refuted three drafts first (a wrong guard count, an overstated
`reap()` - it loops `range(max_slots)`, three lanes - and an incomplete Q3)
and they were fixed before send. LW acknowledged with TERMINAL no-reply notes.

HALT. Clause (b) is OPEN: LW 0700 reports C4 `290cbf80` landed on LW and asks
RSC to copy it by 2026-10-09. That diffs `ops/loop/slots.py` (RSC at
`71fa2a68`, 9627 bytes) and `SHARED_SHA256`; MAIN 2320 does not rule it.
Parked pending the operator or a sha256-verified MAIN note.

READINGS, 2026-10-03, at the staged `6f7a629` content: tests 3284 passed 4
skipped (the same four reasons as baseline); pity_engine 80; ruff clean; docs
42; headless dry-run rc 0; precommit gate clean. Baseline at `513d2d0`: tests
3263 passed 4 skipped, node 52, licence 47, qa 17 passed 2 skipped 3 noted,
mypy 40 source files.

---

## 2026-10-02/03 - MAIN speaks for the operator, headless spawns go through the local proxy, and the responder is armed

Landed as `dca30eb` (docs) and `2e22d80` (the responder merge), both on `main`
and pushed. Operator directive of 2026-10-02, pasted into the session and
confirmed by the operator in chat, in four parts: run headless claude on the
SECOND ACCOUNT through the LOCAL PROXY and fail closed; arm autonomous inbox
handling; MAIN speaks for the operator; report to MAIN.

WHAT CHANGED. `dca30eb` records in `CLAUDE.md` that MAIN speaks for the
operator, quoting the operator paragraph verbatim and superseding the scoped
assent. `2e22d80` adds `core/headless_env.py`: `prepare_headless_env` reads
the proxy base URL from the per-user registry environment AT SPAWN TIME, falls
back to the process environment only when that store is unreadable, refuses
when the value is unset or the port is closed, and builds the child
environment by dropping every `ANTHROPIC_`, `CLAUDE_CODE_` and `CLAUDECODE`
key except `CLAUDE_CODE_GIT_BASH_PATH` before setting `ANTHROPIC_BASE_URL`.
`tools/moon_sync_responder.py` gained a usage-limit backoff record (24 hour
cap, fail closed on an unreadable or non-finite value), the opted-in set
widened from RC alone to CS, LL, LW, MAIN, RC and SS (never RSC), an
auto-reply loop-breaker `is_auto_reply` (BOM and UTF-16 tolerant; NUL,
UTF-32 or undecodable input is skipped), and an outbound cap of three replies
per sender per rolling 24 hours, reserved atomically BEFORE delivery, with a
corrupt record capping everyone and a failed reserve terminating the pass.
Proven by `tests/test_headless_env.py`, `tests/test_responder_audience.py`,
`tests/test_responder_loop_breakers.py` and
`tests/test_responder_no_console_window.py`. The test floors in
`tests/test_licence_posture.py`, `tests/test_line_endings.py` and
`tests/test_machine_identity.py` moved from 100 to 110.

REFUTED FOUR TIMES BEFORE MERGE, each fixed fail closed: an environment leak
into the child; one agreement arming six senders plus an unbounded ping-pong;
a NaN backoff read as "not backed off"; and UTF-16 notes plus an overflowing
record number. Seam gates at merge, measured 2026-10-02: 3263 passed 4
skipped, pity_engine 80 passed, ruff and mypy clean. Re-measured at `/done`
2026-10-03 on `2e22d80`: identical figures, the four skip REASONS unchanged.

MEASURED END TO END, not inferred. One spawn of a one-word prompt through
`_spawn_headless` at 2026-10-03T04:04:19Z returned `ok`, and the local proxy's
activity log gained two lines pinned to the second account with status 200
and zero on the interactive account.

ARMED. The scheduled task RSC-InboxResponder fires every 5 minutes inside a
window of 2026-10-02T22:56 to 2026-11-01T22:56 local; the liveness checker
`ops/check_task_liveness.py` exited 0. The gitignored agreement record
ops/runtime/trial_confirmed.json was rewritten with `confirmed_by` OPERATOR
and an expiry at window close. The first fire at 23:06 ended no-destination
because MAIN was missing from the channel codes in the gitignored per-host
file ops/moon_sync_repos.json; it was added, and the 23:11 fire delivered an
auto-reply to MAIN whose recipient copy hash-matched. THIS CLOSES the old
"responder has never answered real mail" item for the auto-reply path.

DECISIONS, so they are not re-litigated. The module has NO unbounded mode; a
lapsed window is renewed by re-running `ops/install_responder_task.ps1` with a
fresh agreement record, deliberately. RSC never opts itself in. The machine
paths, the proxy address and the account identity stay out of every tracked
file; the tracked record says "second account" and "local proxy".

INBOX, for the record: RSC's 2026-10-02 2350 reply (re-derived `da35f8b1`,
attested; blocking objection that three inherited sentences in
`ops/loop/slots.py` are false about frozen code) reached six siblings with the
sha256 matched at `2c8a7f37`; LW upheld it at 2355. A plugin census was
answered: all 15 plugins unused in 60 days. MAIN's 2320 ruling was verified by
its outbox sha256 (`eeb42923`). A report note to MAIN and every sibling was
delivered with the sha matched at `0330e11b`.

## 2026-10-02 - Nine units, and every one of them was refuted at least once before it landed

Landed across `a65cbff`, `250a4c8`, `8f93a35`, `02ab2be`, `e193f98`, `a1ee3d3`,
`b8f2932`, `9aaf177`, `83d8b1a` and `e9cbc62`. The suite moved from 3122 passed
4 skipped to 3162 passed 4 skipped, with the four skip REASONS byte-identical
throughout - every delta is a pass delta, which is a statement about the tree,
and no skip reason changed, which is what says the environment held still.

THE SESSION'S ONE REUSABLE FINDING, stated first because it outranks any
individual fix: NOT ONE PRODUCER CLAIM SURVIVED ITS FIRST ADVERSARIAL PASS
INTACT. Every slice was refuted at least once and three were refuted twice. The
refutations were not stylistic - they were wrong figures, arms that could not
fail, and twice a remedy measured over the population it was DERIVED from
rather than the population it ACTS on.

FOUR FIGURES ROTTED INSIDE ONE FILE IN ONE DAY, and the fourth was introduced
by the edit that fixed the third. A token breakdown in
`tests/test_docs_consistency.py` read 39 / 21 / 13 / 5 against a measured
47 / 25 / 13 / 9, having rotted inside the very commit that wrote it, because a
fourteen-name table added by that same commit introduced eight new path-shaped
tokens. The remedy adopted, three times over, was to DROP the count rather than
restate it: restating buys one edit of accuracy and then rots again, and a
count was never what the floor needed. A stale 39-module figure elsewhere and a
present-tense table of 4 / 1 / 39 that nothing guarded were dropped on the same
reasoning. Where a reading is kept it is STAMPED with its date and commit.

THE IGNORED HALF OF THE BARE-PATH CITATION RULE IS NARROWED AND NOT CLOSED. It
used to accept a gitignored path unconditionally and forever; it now requires a
tracked file to NAME the path, with the guard module excluded from its own
corpus through a `GUARD_MODULE` derived from `__file__`, so no safe list
remains. There is still no existence check anywhere, so a path named once is
accepted for good. The worked example is stronger than the one first written:
`ops/runtime/health.json` is named by FOURTEEN tracked files, is the
most-vouched ignored path in the tree, and does not exist on disk. The first
remedy's price was computed over the seven specimens it was derived from rather
than the 62 paths it acts on - excluding `tests/` wholesale would have cost 22
paths their only voucher, including a runtime log that exists.

AN ASSERT WAS RENDERING THE PROCESS ENVIRONMENT INTO A PUBLISHED CI ARTIFACT.
Measured by forcing the failure rather than by reasoning: 3 of 103 variables
with their values at default verbosity and 42 of 103 under `-vv`, the mapping
printed twice because the `where` clause repeats it, and a credential-shaped
host variable leaking even at default verbosity. The byte delta is NOT the
measure and the fix says so - the function's docstring dominates both captures,
so the measure is the variable count, now zero at both verbosities.

A WORKING HOOK GATE WAS REPORTED AS BROKEN. Exit path 4 of
`scripts/install_hooks.py` compared `core.hooksPath` as a STRING. With the
value set worktree-scoped to `.githooks` with a trailing slash, the script
exited 1 saying hooks were not installed while a real commit of a banned glyph
WAS refused and HEAD did not move. The control is the load-bearing half and it
holds: a genuinely wrong directory still exits 1 AND lets the glyph through.

THE ASCII EXEMPTION HAD NEVER BEEN MEASURED, only reasoned, which is this
tree's own definition of a hole with a comment over it. It now has both halves:
a non-ASCII payload under the exempt prefix commits through the real hooks and
survives byte-intact in `HEAD`, and the byte-identical payload under a
non-exempt path is refused. An adversary then showed the vacuity guard was
weaker than its own text - hardcoding the gate's corpus line as a constant left
all four arms green, so it proved a one-file corpus line was PRINTED rather
than that the planted file was READ. The arm now stages two files and asserts
counts derived from payload bytes.

SEVEN REPOSITORY-ROOT WALKERS SWEPT NESTED CHECKOUTS, three of them found after
the first four were repaired, and one was LIVE RED through the full suite - a
planted checkout's malformed JSONL became a real offender in
`core/provenance.py`. The predicate's home was decided by a MECHANICAL fact
rather than taste: `tests/test_guard_worktree_exclusion.py` imports `pytest` at
module scope, so binding from there would have given production code a runtime
dependency on pytest. `core/repo_sweep.py` now owns it and mypy's root count
moved 38 to 39. FOUR SWEEPS DISAGREED ABOUT THE WALKER POPULATION - 24 by AST,
then 10 plus 2 by a frame tracer whose first pass said 8 and was wrong because
crediting the innermost frame attributes a walk to whoever DEFINES the helper,
then an audit hook over 16 roots, and finally a poison sentinel planted in
every non-dot directory with no attribution machinery at all. The last is the
method to reuse: marked, the suite matches baseline exactly; unmarked as a
positive control, seven arms red and name the walkers.

A COMMIT CITATION DESTROYED BY THIS TREE'S OWN 2026-09-06 REWRITE was repointed
after a sibling's discriminator found it. No guard was landed for the class and
the refusal is a ruling rather than an oversight: six tokens are cited AS
COMMITS and must never resolve, only one has a spelling discriminator, and two
appear in NEITHER column of the commit-map, so no translating guard could ever
reach them.

A DOCSTRING CLAIMED A CALLER IT DOES NOT HAVE. `tools/corpus_statement.py` has
no caller anywhere and said four times that a gate module invokes it. The guard
now derives claimed callers and real importers and requires them equal, so it
reds in BOTH directions - a docstring that lies in the safe direction still
gets the module deleted as dead. Its first version missed 20 of 20 synthetic
caller claims, including the single most likely word a maintainer reaches for,
and the safe-list problem was then answered structurally rather than with more
rows: the partner arm asserts every verb family has a planted specimen, so a
family added without one reds.

THREE SILENT OVER-EXCLUSIONS are filed against `core/repo_sweep.py` - a prefix
match, a name-contains-marker match, and a hand-list replacing the derivation
each pass the entire suite unchanged. `core/walkprune.py`'s own docstring names
the prefix defect and has an arm for it at its layer; the new layer has none.

FIVE NOTES WERE DELIVERED to six repositories each, every copy read back from
the recipient's own directory and verified at one digest, because an outbound
note in one's own outbox is not delivery. The channel work produced three
corrections against this tree: a hold corpus described as tracked when it is
gitignored, a read-and-unanswered figure whose 398 denominator does not
reproduce against later readings of 483 and 486, and a published account-name
count of 29 that re-derived to 24 and was withdrawn without a replacement being
offered. A reported gap of 46 unread inbound notes was a POPULATION COLLISION -
the watcher reports 311 unread as 265 received plus 46 SENT.
