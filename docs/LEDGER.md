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

- `docs/ledger/session-81.md`
- `docs/ledger/session-80.md`
- `docs/ledger/session-79.md`
- `docs/ledger/session-78.md`
- `docs/ledger/session-77.md`
- `docs/ledger/session-75.md`
- `docs/ledger/session-74.md`
- `docs/ledger/session-73.md`
- `docs/ledger/session-72.md`
- `docs/ledger/session-71.md`
- `docs/ledger/session-70.md`
- `docs/ledger/session-69.md`
- `docs/ledger/session-68.md`
- `docs/ledger/session-67.md`
- `docs/ledger/session-66.md`
- `docs/ledger/session-65.md`
- `docs/ledger/session-64.md`

## Month archives (historic body, verbatim, newest first)

- `docs/ledger/archive-2026-10.md`
- `docs/ledger/archive-2026-09.md`

## Adjudicated rulings

- The 0i(4b) and 0i(2c) rulings of 2026-10-10 live in
  `docs/ledger/session-68.md` (moved there verbatim; this file is an index).

## Hand-off blocks retired session 77

Moved verbatim out of `RSC-NEXT-SESSION.txt` on 2026-10-18 to bring it under
the FLEET-KIT v18 /done 30 KB limit (MAIN 1018 ORDER section 3 step 7). The
hand-off keeps a tightened DO NOT REDO list with every reversal condition;
the full wording, rejected alternatives and DONE blocks are below.

DONE blocks (sessions 64-75) and the full DO NOT REDO list:

```text
  DONE session 75 (see docs/ledger/session-75.md): P roots-map probe
  (no DRIFT); 0i session 73 residue (e) (merge 0c6a644); N5 a, b, d, e
  (merges 9791c2f, b50773d, 4865fc4, 069ba52) and c, f adjudicated
  (N5cf: c KEEP the core/capture_root.py defence, reversed if a regex or
  fallback change makes it reachable; f RECORD the AppData failure of
  tests/test_watch_inbox_session.py as environment, reversed by a false
  red from 'packages' outside AppData or runtime_dir() moving off the
  repo root); N6 worktrees and branches removed (four unlocked: their
  pid was dead, trees clean and merged; reversed by a lock whose pid is
  alive); M merged and pushed; 13 inbox read, nothing new, nothing
  marked (per-session triage stays a standing directive). Outbound
  notes: none. All other items carried forward.
  DONE session 74 (see docs/ledger/session-74.md): W0, P1, P2 (merge
  1efb846), P3 (merge b888286), N4 (merge 303b839), P5 (merge 1db6c73),
  P6, P4 (merge 44c97ec), P7 tag v0.1.0, P7b (merge 6fb8a88), F1 (merge
  1372540), A1 ONE ANSWER to MAIN (2328, carries N1), I1 inbox marked.
  Old item 13's per-session inbox triage done. All other items carried
  forward.
  DONE session 73 (see docs/ledger/session-73.md): 0i residue (b) merge
  72b2336; 8 adjudicated and interim d merge f6234b3 (A2 residue in 8);
  N3 recorded as a trap. Outbound notes: none. All other items carried
  forward.
  DONE session 72 (see docs/ledger/session-72.md): 0w send path wired
  (merge c921c5c); 0y ui-auditor skip-list routing (merge e2179b2, F1
  1fa7f3b); 0z hooksPath root cause (4fd8b9c); seam floors 135 -> 155;
  0x note sent (now a waiting item); inbox triage and mark. 0e: the
  subagent-first jsonl showed 0 main-thread rows on 2026-10-13, so no
  would-deny for undispatchable work; mode stays deny. All other items
  carried forward.
  DONE session 71 (see docs/ledger/session-71.md): 0v CI red test
  root-caused (rootdir fallback at a filesystem-root common ancestor, not
  the pytest pin) and fixed, merge f1a2121, ci 38337579557 green; 0r
  adversary git -C rule, merge dec5217; 0q tools/send_note.py and the
  9-row backfill, merge 20d9d29 (residue 0w, 0x); 0u electron 44.7.0,
  merge 8fe0ce4 (residue 0y); 0s CS codename confirmed in the codename
  map (residue 0z). All other items carried forward.
  DONE session 70 (see docs/ledger/session-70.md): INBOX-13 triage; 0g
  (ignores re-measured on v17, comment only); 0h(i) (--confcutdir); 1
  (colorama marker guard test); 0l (claude/new-session-19dmsr deleted on
  origin; restore with git push origin 154d5f8:refs/heads/
  claude/new-session-19dmsr); 0i(2c) target met (residue in 0i); 0j
  (TEMP-1 numbers sent to MAIN in the 1258 INFORMATION note). All other
  items carried forward.
  DONE session 69 (see docs/ledger/session-69.md): kit v17 adoption and
  its ANSWER to MAIN. All items above carried forward unchanged; 0g
  (residual kit ruff ignores) should be re-measured against v17 bytes.
  DONE session 68 (see docs/ledger/session-68.md): 0i(2b) census
  collapse; 0i(4b) DECISION B; 0i(2c) partial (residue in 0i); 0l
  rsc-v8-slice-a; 0j measurement (send still owed); 0p stash adjudicated
  and dropped, arm-proving rule in CLAUDE.md; 13 inbox marked.
  DONE session 67 (see docs/ledger/session-67.md): E1 kit v15 adoption
  and its ONE ANSWER to MAIN; A1 (old item 2, kit budget refusal codes);
  0o (HISTORY block moved); 0m (busy-lock check by Refused.code); the
  recovery, gate re-run and push; worktree and branch clean-up.
  DONE session 66 (see docs/ledger/session-66.md): B1 stale comments
  (merge aaa4d7d) and the old conftest backup recycled (old item 4); C1
  branch prune (old 0l); D1 2055 REPORT to MAIN (old 0c). RETRACTED
  session 66: old item 3 (the kit v14 ops/fleet_kit/fleet_inbox.py already tracks name
  plus sha256 via seen_index/_is_seen; reopen only if a kit version drops
  that); old 0n (the stray bytecode cache was this tree's own leftover,
  recycled; reopen only if a fresh bundle arrives with one).
  DONE session 65 (see docs/ledger/session-65.md): kit v14 vendoring;
  MAIN FIX TEMP-1 (retention 1, no basetemp in scratchpad); ANSWER 2020 to
  MAIN; inbox triage and mark; independent verification.
  DONE session 64 (see docs/ledger/session-64.md and
  docs/ledger/archive-2026-10.md): kit v12 and v13 adoption and
  verification; MAIN 2246 s1 rest, s2, s3, s4 Dependabot; ANSWERs 2301 and
  0019; old 1 (colorama marker); 0e criterion met and mode flipped. Desktop
  shortcut tooling removed per 2246 s1 (the hand-off shortcut is retired).
  16 RETRACTED (session 63): the _MIN_TRACKED_* floors were already 135
  since c3bed4a. Reopen only if tests/ grows past 134 tracked files or the
  corpus drops below 270.
  DO NOT REDO: v3/v4/v7/v8/v9/v10/v11/v12/v13/v14/v15/v16/v17 vendoring and provenance
  (reversed only by a new MAIN FLEET-KIT-vN note); the roster 0230/2305
  landing (reversed by a verified MAIN roster note); the CLAUDE.md condense
  (reversed only by a MAIN kit change); Bash removed from the responder
  child floor (reversed only by a live probe proving a Bash floor cannot
  write); the --once slot, the spawn cwd, the C4 landing, the test-leak
  fence; ruling 0f DECISION C, responder run ledger retired in favour of
  kit RunBudget, per-sender cap, MAX_HOPS and DEFAULT_RUNS kept (reversed by
  a kit version dropping the OS-held lock, or the kit not counting every
  spawn in this tree); the main session as orchestrator in
  .claude/commands/orchestrated-run.md (reversed by sub-agents gaining an
  Agent tool, or a
  MAIN ruling); the pip-compile pair for dev deps (reversed by Dependabot
  dropping pip-compile support); ADR-011 outbox-hash provenance (reversed
  by a verified MAIN note ordering verify_main for runtime notes, or a
  measured hash-match MAIN never committed that mattered); the firedetail
  log label (reversed only by a drift-check redesign that ends fires on
  terminals); the README landing page and the OVERVIEW/OPERATIONS split
  (reversed only by an operator or verified MAIN instruction to restore the
  long README); responder governor=None for every class (reversed by the
  child gaining a write tool, a MAIN ruling, or proxy 429s while acks
  overlap lanes); the parent owns the responder checklist (reversed by the
  child gaining a write tool and a non-draft output channel); the checklist
  block logged only on spawning fires (reversed by a MAIN ruling or a
  raised log cap); LANE_CAP 3 (reversed by a measured reason for fewer
  lanes or a MAIN order); a MAIN note cools 6 h instead of parking
  (reversed by a MAIN ruling); the kit per-file ruff ignores (reversed per
  rule when a kit version ships it clean); superseded MAIN notes by TRACKED
  STAMP ONLY, no kit-version inference (reversed by a MAIN ruling that
  defines supersession by version, plus a rule that can never drop a live
  FIX or RULING, refuter-tested); the per-sender cap exemption is
  MAIN-only, one-parse, provenance-MATCH-gated (reversed by a MAIN ruling,
  or a sibling ORDER parked over 24 h blocking real work); fuzzing ruled
  out (reversed by the tree parsing untrusted input or an operator order);
  docs/LEDGER.md kept as the index and per-session ledger files (reversed
  by a MAIN ruling); display name ResinCompute in one word (reversed by an
  operator or MAIN instruction); the nightly gated on new commits (reversed
  by plumbing tests moving back into the push path); the six CI_ONLY
  pre-push modules and never-cancelled push CI runs (reversed by any
  cancelled push run in ci, or 3 pushes landing within one run duration);
  dev-dep DECISION B, pytest-timeout only (reversed as in 0i); the
  claude/new-session-19dmsr deletion on origin (reversed by a cloud
  session or reopened PR needing the branch name; restore from 154d5f8);
  the pre-push engine-suite skip outside its import closure (reversed by a
  false SKIP that let an engine-breaking push through); 0v rootdir pins in
  tests/test_conftest_git_gate_sites.py, NOT a pytest-version cause
  (reversed by the arm going red again with the pins in place); 0u
  ui-auditor waiver for a pure dependency bump (reversed by narrowing the
  .claude/commands/ui-audit.md exemption, a MAIN ruling, or a rendered regression); 0q
  ruling B, an over-cap send still records its row (reversed by the kit
  locking record or a MAIN ruling that the ledger must never exceed the
  cap); 0y adjudicated A, accept the merge plus follow-up F1, rejecting
  B (block 0y until 0w merged) and C (roadmap only) (reversed if the
  tests/test_builder_ui_audit_rule.py guard never reds on the old text);
  0z keeps either hooksPath spelling and does NOT enable
  extensions.worktreeConfig, because agent worktrees would then get no
  hooks (reversed by Claude Code no longer rewriting the value, or a MAIN
  ruling); P2 adjudicated B, fix every refute finding and close with a
  verifier, no third adversary (reversed by a verifier finding an arm
  that does not red); P3 DECISION C, merge: <topic> accepted only with
  MERGE_HEAD or a merge HEAD, rejecting A (ship as is, breaks an amend of
  a merge) and B (amend detection, infeasible on git 2.53) (reversed by
  git exposing an amend signal to commit-msg, or a MAIN ruling); P5
  DECISION B, no install.bat, the installer is the pip --require-hashes
  pair, rejecting A (literal wrapper) and C (partial) (reversed by a MAIN
  ruling asking for a wrapper).
```

The session 75 STATE OBSERVED reading:

```text
STATE OBSERVED 2026-10-16 AT 069ba52 (session 75 /done gate run)
  Python 3.14.4 (CI is 3.11): every gate in the order above GREEN (counts
  in docs/ledger/session-75.md); mypy advisory clean; kit check 17 [].
  Whole suites ran through the suite gate (tests waited over 600 s for
  the single machine slot). core.hooksPath read the ABSOLUTE spelling (0z
  rule). tools/send_note.py audit printed nothing; scripts/watch_inbox.py
  read unread: none and no inbox file was newer than the session 74
  hand-off commit, so nothing was triaged or marked.
  tools/roots_map_probe.py from the main checkout: no drift, 153 outbox
  entries.
  CI at 069ba52 READ BACK success: ci 38961106089, codeql 38961106069.
  origin: main 069ba52 (git ls-remote) and annotated tag v0.1.0 (tag
  object 5eab7d8). Paperwork push and its CI: see
  docs/ledger/session-75.md.
  WORKTREES read back at /done: exactly four besides main, all merged and
  LOCKED by this session's live pid: agent-a2fcbd2a915e87790,
  agent-ae145f6da3153d16e, agent-a1fefe71ae6a4056e and
  agent-a6ee21a202bdbfc72, each on its worktree-agent-* branch (item N7).
  LANDED session 75: see docs/ledger/session-75.md.
```

DONE fragments tightened inside open items 0h, 0i and N7(e) and the
STATE OBSERVED LANDED line:

```text
  LANDED session 75 (details docs/ledger/session-75.md): 0i git-call
  timeouts merge 0c6a644; N5a merge 9791c2f; N5b merge b50773d; N5d
  merge 4865fc4; N5e merge 069ba52; N5cf adjudicated (c KEEP, f RECORD);
  N6 session 74 worktrees and branches removed.

  0h. FLAKY-TEST WATCH. (i) DONE session 70 (root-caused: a child pytest
     walked the temp dir across drives; --confcutdir fix, merge cc2d86a).
     (ii)
  0i. MAIN 2246 s2 residue (ROADMAP 2246 entry; 2b and 4b DONE session
     68). (2c) the 30 s target MET session 70 (merge 3c61cc8). Session 70
     residue (b) DONE session 73 (merge 72b2336). Session 73 residue (e)
     DONE session 75 (git-call timeouts, merge 0c6a644; its residue is
     N7 (a)). (2c-b)

     (e) N7e DONE session 76: tools/roots_map_probe.py exit 0. The 4
     session-75 worktrees were unlocked, then removed plainly, then
     git branch -d. Probe DRIFT outbox 153 -> 154; the newest note is the
     2026-10-17-0737 MAIN FIX to RC, not ours.
```
