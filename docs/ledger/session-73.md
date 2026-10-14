# Session 73

## 2026-10-14 - /done ritual: gates at f6234b3, push, CI, worktrees

- Gates measured 2026-10-14 by the /done agent at f6234b3, Python 3.14
  (CI is 3.11): licence 52 passed; docs 46 passed; qa_companion 16 passed
  0 failed 2 skipped 4 noted; ruff clean; `python -m pytest tests -rs`
  4570 passed 6 skipped (collect-only 4576; the same six host skip
  reasons as session 72); `agents/pity_engine` 191 passed; `node --test`
  110 pass 0 fail; headless dry run 0 pass 0 fail 7 skip; mypy (advisory)
  no issues in 45 source files; kit check `17 []`. The three whole suites
  ran through `ops/fleet_kit/fleet_suite_gate.py`, no slot wait. A first
  attempt passed a guessed interpreter path and the gate raised
  FileNotFoundError (the known trap); re-run with the real
  `sys.executable` path.
- Section 0: `git status -s` empty at /done start; `core.hooksPath` read
  the absolute `<main root>\.githooks` spelling, accepted under the 0z
  rule; nothing under `data/` tracked new.
- Push: `ops/fleet_kit/fleet_gitlock.py run -- git push origin main` pushed
  991b455..f6234b3; pre-push selected 13 modules, 435 passed 1 skipped,
  engine suite skipped outside its closure; `git ls-remote origin
  refs/heads/main` read back f6234b3. CI at f6234b3 (ci 38572023498,
  docs-guards 38572023501, codeql 38572023519) read back success, all
  three. The paperwork push and its CI run follow this entry and are not
  predicted here.
- `python tools/send_note.py audit` printed nothing, exit 0. No outbound
  note this session. `scripts/watch_inbox.py` read `unread: none`.
- `python tools/roots_map_probe.py` (first run from the main checkout):
  outbox present, 144 entries, map digest stored as the first baseline,
  exit 0.
- Worktrees: `agent-a38699d28b84db36d` (merged, clean) removed with `git
  worktree remove` and its branch deleted with `git branch -d` (was
  b5fad62). LEFT: `agent-aeb93e353071a9a9b` (merged, clean, but locked by
  a live claude.exe); `agent-a056d111e3e273eda` and
  `agent-a1bf330e32d985af6` (session 72 leftovers, merged and clean, not
  in this ritual's scope). `git worktree list` read back 4 entries.

## 2026-10-14 - 8-D: ADR-013 interim d, read-only roots-map probe

- Adjudicated: a distinct adjudicator ruled interim D now and A2 (an
  untracked random beacon in MAIN's outbox) as the target. Criteria in
  order: fits ADR-011 (no git call); leaks nothing in a public clone; halt
  clause (c), no change in another tree; catches a wrong MAIN row at verify
  time; no new false-accept or lose path. Rejected: A2 now (needs MAIN's
  cooperation = operator ask 1 and halt clause c); E (A2 check built but
  dormant - silent skip while the pin is missing, and the Proposed ADR says
  no code). Reversed by: an operator or verified MAIN yes to asks 1 and 2
  (then build A2 test-first); MAIN's outbox becoming tracked-only makes A2
  unworkable. Asks 1, 2 and 4 stay unanswered. Common-mode risk: nothing
  tests that MAIN's outbox can hold an untracked file.
- Landed d58aa93, merge f6234b3: `tools/roots_map_probe.py`,
  `tests/test_roots_map_probe.py` (14 tests; the drift tests red with
  `compare()` stubbed), the interim-d note and corrected line references
  in `docs/adr/ADR-013-roots-map-identity-anchor.md`, and the bootstrap
  line in `.claude/commands/done.md`. Leak-lens adversary NOT REFUTED.
- Known gaps: the probe locates the map relative to its own file, so a
  worktree copy prints "map not present" (false negative; run it from the
  main checkout); the newest filename it prints is MAIN-chosen free text;
  importing `core/atomic_io.py` opens the day log under `logs/`.

## 2026-10-14 - 0i-A: pre-push selector residue (session 70 residue b)

- 3257ee6: untracked non-ignored files join the changed-path list;
  `pytest.toml` and `.pytest.toml` force FULL; a force-push adds a direct
  `git diff <base> HEAD` to the merge-base diff.
- Adversary round 1 REFUTED; fixed in b5fad62: pytest config names
  directly under `tests/` or `agents/pity_engine/` and `conftest.py`
  anywhere force FULL; a non-zero base sha missing from the local object
  store forces FULL instead of falling back to `@{u}`.
- Adversary round 2 (does-it-reproduce and resource-lifetime lenses) NOT
  REFUTED on both claims through the real `.githooks/pre-push` path; the
  new tests red with the old selector (18 failed). Merged as 72b2336.
  Files: `scripts/prepush_select.py`, `tests/test_prepush_select.py`.
- Decisions: gitignored files stay out of the changed-path list (they would
  push most runs past the 40-path FULL limit); `conftest.py` anywhere means
  FULL (a slower push over missed coverage); a missing base means FULL,
  never a fetch (no network in the selector).
- Residue: 2c-b push-run cancellation stays watch-only; no git call in the
  selector has a timeout (pre-existing); in a partial clone the
  missing-sha rev-parse could reach the network.

## 2026-10-14 - session notes (merger observations, filed)

- N1 kit defect for the next batched note to MAIN: `ops/fleet_kit/fleet_gitlock.py`
  wraps only `git commit` and `git push`, so a bare `git merge` is refused;
  the merger used `git merge --no-ff --no-commit` and then a gitlock
  commit. Never patch the kit.
- N2 a stale empty `.git/index.lock` (826 s old, no git process) blocked
  the first merge; the gitlock dry-run commit cleared it and logged it to
  its jsonl. Watch for a repeat.
- N3 the commit-msg hook rejects a `merge:` subject; the repo form is
  `Merge slice ...`.
- N4 the roots-map probe's worktree false negative; resolving the map via
  the git common dir is a plumbing slice of its own.
