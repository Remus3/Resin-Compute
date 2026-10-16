# Session 74

## 2026-10-15 - /done ritual: gates at 1372540, push, CI, worktrees

- Gates measured 2026-10-15 by the /done agent at 1372540, Python 3.14
  (CI is 3.11): licence 52 passed; docs 46 passed; qa_companion 16 passed
  0 failed 2 skipped 4 noted; ruff clean; `python -m pytest tests -rs`
  4737 passed 6 skipped (collect-only 4743; the same six host skip
  reasons as session 73); `agents/pity_engine` 191 passed; `node --test`
  110 pass 0 fail; headless dry run 0 pass 0 fail 7 skip; mypy (advisory)
  no issues in 46 source files; kit check `17 []`. The three whole suites
  ran through `ops/fleet_kit/fleet_suite_gate.py`.
- Section 0: `git status -s` empty at /done start; `core.hooksPath` read
  the absolute `<main root>\.githooks` spelling, accepted under the 0z
  rule; nothing under `data/` tracked new.
- Worktrees: `agent-a355f4ed330f09ea7` (N4, was 5161d42),
  `agent-ad10c1a8127a6c276` (P4, was bfb2e07) and
  `agent-aef7464494f2ccf72` (P7b, was 558a714) were clean and merged; each
  removed with `git worktree remove` and its branch deleted with `git
  branch -d` (the delete printed the tip each time). LEFT, all merged into
  main: `agent-a0228dfee641cde39` (P5), `agent-a0956d3394e81b139` (P2),
  `agent-a60657c9d2bd57fd6` (P3) and `agent-ae36a4ecfadc15638` (F1), each
  LOCKED by the live claude.exe of this session (lock file read back), so
  not removable without force; `agent-aeb93e353071a9a9b` left by
  instruction. Four branches with no worktree, all merged into main, also
  remain: `worktree-agent-a085507de7edd09f5`,
  `worktree-agent-a52543d026422789f`, `worktree-agent-a902f3c3927fbb5bc`,
  `worktree-agent-af74f802de751d701`.
- Read back before the paperwork commit: `git ls-remote origin` main
  1372540, tag `v0.1.0` 5eab7d8 (annotated, peels to 6fb8a88). CI at
  1372540: ci 38850581182 success, codeql 38850581216 success. CI at
  6fb8a88: ci 38846798268 FAILURE and at 44c97ec ci 38845389790 FAILURE
  (the Pillow-less capture-root arm, fixed by F1), codeql 38846798266
  success. The paperwork push and its CI run
  follow this entry and are not predicted here.
- `python tools/send_note.py audit` printed nothing, exit 0; no backfill.
- Memory: no file under the project memory folders changed this session;
  nothing to index.
- Before the paperwork commit HEAD and origin/main both read 1372540, so
  section 3 had no code push; the paperwork push follows this entry.

## 2026-10-15 - A1 and I1: ONE ANSWER to MAIN, inbox marked

- `moon_sync_inbox/2026-10-15-2328-from-RSC-ANSWER-to-MAIN-pubpath-pubrepo-1372540-v0.1.0.md`
  (gitignored) re-hashed at /done: sha256
  d1235551333a5fa40ed0b6e932c3b3e203069f16c11b6cd906d1518d3cb16edc. The
  outbound ledger (gitignored) holds its ANSWER row stamped
  2026-10-15T23:28:57-05:00, plus an earlier ANSWER row of 19:30 the same
  day replying to the MAIN 1925 ORDER. The 2328 note carries the N1 kit
  defect (fleet_gitlock wraps only commit and push). Sent through
  `tools/send_note.py`, reached 2/2 (send result, not re-measured here).
- Inbox marked; `scripts/watch_inbox.py` read back at /done: `unread: none`.

## 2026-10-15 - F1: capture-root import arm runs without Pillow

- 55cc5b2, merge 1372540: `tests/test_capture_root.py` stubs PIL so the
  import arm runs on a CI image with no Pillow. Read back: ci 38850581182
  and codeql 38850581216 success at 1372540.

## 2026-10-15 - P7 and P7b: tag v0.1.0, pre-push peels annotated tags

- 558a714, merge 6fb8a88: `.githooks/pre-push` peels an annotated tag to
  its commit before the graded-HEAD check. Tag `v0.1.0` annotated, tag
  object 5eab7d8 peels to 6fb8a88; `git ls-remote origin` read back the
  tag at 5eab7d8 (pushed as a single ref).
- Residue: no pre-push test arm pushes several refs at once; the
  rev-parse raw error line on a blob tag is cosmetic.

## 2026-10-15 - P4: README "How this repo is built" and licence statement (MAIN 1925 item d)

- 1abed43, bfb2e07, merge 44c97ec: `README.md` section "How this repo is
  built"; GPL-3.0-or-later for the tree, Apache-2.0 for the vendored parts
  (`ops/fleet_kit/`, `ops/loop/slots.py`, `ops/loop/winmutex.py`,
  `docs/CHANNEL.md`); install docs use `--require-hashes`; CLAUDE.md
  glossary; ROADMAP session 73 residue (c) marked superseded.

## 2026-10-15 - P5: hashed runtime lockfile (MAIN 1925 item e)

- 5016724, 60c75df, 3f3d04c, merge 1db6c73: `requirements.in` compiled to a
  hashed `requirements.txt` (pip-tools 7.5.3); `tests/test_runtime_lock.py`;
  `docs/INSTALL_PROOF.md`; `scripts/prepush_select.py` forces FULL for
  `*.in`. Install proven (per the slice's record) on 3.11.9, 3.12.10, uv
  3.12.13, 3.13.13, 3.14.4 and embedded 3.11.9.
- DECISION B: no install.bat; the installer is the `pip install
  --require-hashes` pair. Rejected: A, a literal wrapper script; C, a
  partial wrapper. Reversed by: a MAIN ruling asking for a wrapper.

## 2026-10-15 - P3: merge-subject template `merge: <topic>` (MAIN 1925 item b)

- 7cd48ab, 5e76698, e5ac7d4, merge b888286:
  `scripts/precommit_msg_check.py` accepts `merge: <topic>` only when
  MERGE_HEAD exists or HEAD is a merge (an amend of a merge reads HEAD^2),
  and refuses `agent-<15+ hex>`, `worktree-agent-<hex>`,
  `.claude/worktrees` and live worktree names with a 6+ hex run.
- DECISION C. Rejected: A, ship as is (breaks an amend of a merge); B,
  amend detection (infeasible - the hook environment is identical on git
  2.53). Reversed by: git exposing an amend signal to commit-msg, or a
  MAIN ruling.

## 2026-10-15 - P2: machine-path scrub and guard (MAIN 1901, 1925 item f)

- 05cf286, b1d40f6, 370fef2, merge 1efb846: absolute machine paths
  scrubbed from tracked files; guard `tests/test_no_machine_paths.py`;
  `core/capture_root.py` resolves the capture root lazily from a validated
  SystemDrive; P3 test fixtures moved to `/srv/checkout` at the seam.
- Refute round 1 REFUTED (eager capture root, guard too narrow), fixed in
  b1d40f6. Refute round 2 REFUTED (drive not validated, masked scan),
  fixed in 370fef2. Adjudicated B: fix all findings, verifier only after
  that (no third adversary, per the 2-round cap). The verifier confirmed
  each new arm reds with its defect reinstated
  (`tests/test_no_machine_paths.py`, `tests/test_capture_root.py`).
- Residue: the `ValueError` branch in `core/capture_root.py` is
  unreachable (defence only); the guard's exemption list was never
  independently tested (adjudicator common-mode note).

## 2026-10-15 - N4: roots-map probe resolves the map via the git common dir

- 30ca08d, 5161d42, merge 303b839: `tools/roots_map_probe.py` resolves the
  map through the git common dir; from a linked worktree it is read-only
  (no baseline write) and prints a fallback line on stderr. Adversary
  round 2 NOT REFUTED. Closes session 73 residue (d) and hand-off N4.
- Residue: with no baseline in the main checkout and a run from a
  worktree, it prints "stored as the baseline" and then "baseline not
  updated".

## 2026-10-15 - W0, P1, P6: worktree and identity hygiene, GitHub sweep

- W0: session 72 leftover worktrees `agent-a056d...` and `agent-a1bf3...`
  removed, branches deleted with `-d`.
- P1: `git config --get-all fleet.operatorIdent` read back 1 value at
  /done (the noreply identity).
- P6: the session sweep found Dependabot alerts on (HTTP 204) and
  automated security fixes off. Re-measured at /done 2026-10-15: CodeQL
  open alerts 0; open PRs 0; failed Actions runs created since
  2026-09-15: 25 (ci 17, docs-guards 8; the sweep's own reading was 23,
  ci 15, before the ci reds at 44c97ec, 38845389790, and 6fb8a88, 38846798268,
  both the Pillow-less capture-root arm fixed by F1). No secrets or
  personal paths found in them by the sweep.
- Process trap: two slices' scratchpad helpers shared one generic script
  name and cross-wrote progress files `rsc-n4` / `rsc-p5`. Every slice
  helper needs a unique name.
