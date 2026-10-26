---
description: End-of-session ritual - gates, commit, push, CI, ledger, roadmap, and the RSC-NEXT-SESSION.txt hand-off rewritten with every unworked item carried forward. Chat output is one line.
argument-hint: [optional one-line session topic]
---

# /done - end-of-session ritual

Run EVERY section, in order, quietly. Session topic, if given: $ARGUMENTS

**/done RUNS UNPROMPTED** once no session-checklist task remains (FLEET-COMMON
items 5 and 13 c, kit v7). The session invokes it itself the moment its
`Session <n> checklist` is down to the `/done` line - it does not wait for the
operator to type `/done`. In an interactive session the operator then clears.

**THE ONLY CHAT OUTPUT OF /done IS ONE LINE** (FLEET-COMMON rule 5 in
`CLAUDE.md`):

```
Done ritual complete, safe to clear
```

or, if a section stopped the ritual, one line naming the failure that stopped
it. Nothing else reaches chat: no banner, no gate table, no checklist, no
session review, no hand-off text, no next-session prompt. Every measured result
goes into the files below - `docs/LEDGER.md`, `ROADMAP.md` and
`RSC-NEXT-SESSION.txt` - never into chat. Never carry forward a count from
earlier in the session or from a subagent; record only what you observed in
this ritual.

**THE MAIN SESSION DISPATCHES THE WHOLE RITUAL TO ONE SUB-AGENT** (FLEET-KIT
v10, MAIN 0839 ORDER of 2026-10-08, section 3 item 4). The main session runs
no section itself: under the kit's SUBAGENT-FIRST PreToolUse hook every Bash,
PowerShell, Read, Edit, Write, Grep, Glob, NotebookEdit and MultiEdit call in
the main thread is denied (or, in log mode, logged as would-deny). It
launches ONE sub-agent, in the
foreground, whose prompt is this file's sections in order plus the session
topic, the session counter `n` and the list of checklist tasks the session
printed (the sub-agent cannot see the main thread's context, so the pre-flight
inputs travel in its prompt). The sub-agent runs every section below and ends
its reply with exactly one line: `Done ritual complete, safe to clear`, or the
one line naming the failure that stopped it. The main session relays only
that final line, byte-exact, and nothing else. A sub-agent that returns no
such line is a failure; the main session relays `/done failed - the ritual
sub-agent returned no final line` and does not retry.

## Pre-flight - the session checklist

Pre-flight: every checklist task done or carried into the hand-off.

Every task the session printed on its item-13 `Session <n> checklist` is
either DONE - and the ledger entry in section 5 says so - or CARRIED into
`RSC-NEXT-SESSION.txt` in section 7, verbatim or tighter. A task that is
neither stops the ritual, and the one line names it. This is the same carry-
forward rule as FLEET-COMMON item 5, applied to the list the session printed.

## 0. What this session touched

- `git status -s` and `git log --oneline -5`. Know the files YOU authored.
- Nothing unexpected staged: no `.env`, no runtime state, no game data. Per
  ADR-002 and `docs/LICENSE_NOTES.md` this tree vendors no game data, and
  `data/fixtures/` is hand-authored only. A real cost table or banner list in
  `data/` stops the ritual - report it as the failure line.
- `git config core.hooksPath` must RESOLVE to `<repo>/.githooks`. Either
  spelling is fine: the relative `.githooks` or the absolute
  `<main root>\.githooks` (Claude Code's worktree setup rewrites it to the
  absolute form in the shared `.git/config`; harmless). Run
  `python scripts/install_hooks.py` first only when it prints nothing or
  resolves elsewhere.

## 1. The gate - all of it, before any commit

Never pass `-q` on the command line; `pytest.ini` already carries it.

```
python -m pytest tests/test_licence_posture.py
python -m pytest tests/test_docs_consistency.py
python scripts/qa_companion.py
python -m ruff check .
python -m pytest tests
python -m pytest agents/pity_engine
cd shell && node --test
python -m headless.runner --once --dry-run
python -m mypy
```

- Two Python suites SEPARATELY - never `pytest .` from the root.
- FLEET-COMMON 16c (kit v12): each WHOLE suite above (`tests`,
  `agents/pity_engine`, `node --test`) runs through the machine-wide gate,
  `python ops/fleet_kit/fleet_suite_gate.py run --owner <id> -- <suite cmd>`,
  where `<id>` is the caller's own claims owner id (`<session_id>.<agent_id>`;
  the claims hook's deny reason names it). Pass the interpreter as an
  absolute path (`sys.executable`) after `--`. A gate timeout fails closed: a
  suite that did not run is not a passing suite.
- `python -m mypy` is ADVISORY: `.github/workflows/ci.yml` runs it with
  `continue-on-error: true` and `docs/SPEC_SCAFFOLD.md` section 7 leaves it out
  of slice acceptance. Record its result; do not block on it.
- RED that this session introduced: fix and re-run; never commit over it. A
  pre-existing failure unrelated to this session is recorded in the ledger and
  the hand-off, and the green-verified authored files still commit.
- A skipped suite is not a passing suite. Record what was skipped and why.
- DOCS-ONLY REUSE (S78f, adjudicated 2026-10-23). `python -m pytest tests`
  may reuse the last gated green ONLY when: (a) it ran THIS session, its file
  read back with `EXIT=0`, naming commit S; (b) S is an ancestor of HEAD;
  (c) every path in `git diff --name-only S` and `git status --porcelain`
  matches `*.md` - any other path, `RSC-NEXT-SESSION.txt` included, means no
  reuse. Then run, to a file, read back:
  `python tools/precommit_gate.py --expect-count <n> --scan-tracked docs`
  (n = `git ls-files -z -- '*.md'` count), `python -m pytest tests -m
  reads_docs`, and every other gate line above. The ledger cites S; a reuse
  without S is a skipped suite.
- Record each gate command's wall time and slot wait in the ledger entry.

## 1b. Reap merged linked worktrees (FLEET-KIT v22)

Before the commit, run once:

```
python ops/fleet_kit/fleet_done.py reap --apply
```

It removes a linked worktree only when nothing can be lost (never
`--force`, never `branch -D`); every other worktree is LISTED with its reason
and stays. Record its summary line (`reap: <n> removable, <n> kept, <n>
listed ...`) in `RSC-NEXT-SESSION.txt` in section 7.

## 2. Commit

Green gate means commit. Do not leave authored work uncommitted.

- Stage deliberately, file by file. Never `git add -A`.
- **NEVER add a `Co-Authored-By: Claude` trailer** or any other trailer.
  `.githooks/commit-msg` strips it per operator policy; never file its absence
  as a defect.
- 7-bit ASCII, imperative subject. Use `git commit -F <file in the session
  scratchpad>`; never a double-quoted here-string or a piped string.
- FLEET-COMMON 16a (kit v12): every commit runs through the per-tree git lock,
  `python ops/fleet_kit/fleet_gitlock.py run --owner <id> -- git commit -F <file>`.
  A bare `git commit` is denied by the claims hook.
- If a hook rejects the commit, fix it and make a NEW commit. Never `--amend`,
  never `--no-verify`.

## 3. Push

`python ops/fleet_kit/fleet_gitlock.py run --owner <id> -- git push origin main`
(FLEET-COMMON 16a; a bare `git push` is denied). The pre-push hook runs ruff
plus both suites. A push
that printed an error is not a push - that is the failure line.

`RESIN_SKIP_PREPUSH=1` exists for a docs-only push; using it makes CI the only
gate, and the ledger entry says so.

## 4. CI - know which workflow you triggered

- `.github/workflows/ci.yml` carries `paths-ignore: ['**/*.md']`, so a
  docs-only push fires no `ci` run. That is not a failure.
- `.github/workflows/docs-guards.yml` fires on exactly what `ci.yml` declines.

`gh run list --branch main --limit 3`, identify the run your push triggered, and
record it as green, red or pending in the ledger entry. Do not dispatch a second
run of something the push already started, and do not predict a running result.

## 4b. Outbound notes - `tools/send_note.py` is the only send path

Every note this session sends to another tree, including any note /done itself
sends, goes through the attended send path, `tools/send_note.py`:

```
python tools/send_note.py send <draft>
```

`tools/send_note.py send` validates the draft (the responder's own gate),
refuses a retired or unknown recipient, applies the FLEET-COMMON item 14c cap
(ORDER, FIX and RULING always pass), writes this tree's own copy first and the
recipient's second, re-hashes both, and only then appends the outbound-ledger
row `OutboundCap` counts. It prints one JSON result line: exit 0 is sent, exit
1 is refused and is the failure line. There is no other send path - a note
hand-placed in an inbox skips the ledger row, which is how both notes of
2026-10-12 went unrecorded (hand-off 0q). A result reason of
`over-cap-recorded` is NOT a failure: the note was delivered, so its row is
forced in and the cap overshoot is visible (0q ruling B; do not re-litigate -
reversed only by the kit locking `record` or a MAIN ruling that the ledger
must never exceed the cap).

Then, whether or not this session sent anything, run the audit:

```
python tools/send_note.py audit
```

It must print nothing (exit 0). Any line it prints is an own-sent note with no
ledger row. A line with no `reason` key is a delivered note: append its row
with `python tools/send_note.py audit --apply`, re-run the audit until it
prints nothing, and record the backfill in the section 5 ledger entry. A line
WITH a `reason` (`undelivered`, `recipient-mismatch`, `unknown-recipient`) is
never appended by `tools/send_note.py`; it stops the ritual and is the failure
line.

## 5. Write `docs/ledger/session-<n>.md` and index it in `docs/LEDGER.md`

n is this session's `SESSION:` counter from `RSC-NEXT-SESSION.txt`. Write the
session's entries to `docs/ledger/session-<n>.md`, newest first, in the
existing entry format (see `docs/ledger/README.md`). One entry per landed unit
of work: what changed and what was MEASURED, the verification pointer (file and
test name), any decision with its reasoning. A count appears only stamped with
its measurement date. Then add one line for the file at the TOP of the
"Session files" list in `docs/LEDGER.md`, which is an index only - never append
an entry body to it, and never rewrite an older session's file or a
`docs/ledger/archive-<YYYY-MM>.md` month archive. Never put a per-item entry in
`CLAUDE.md` - that file is loaded every turn.

## 6. Update `ROADMAP.md`

`ROADMAP.md` holds OPEN work only. Add items this session opened. An item this
session closed with no open residue MOVES, verbatim, to the top of
`docs/roadmap-archive/<YYYY-MM>.md` for the month of its closing date (create the
file with the same 3-line header the existing month files carry); an item with
residue stays, its closed sub-items may move with a one-line pointer left
behind. Cite the path that proves a closure (`tests/test_docs_consistency.py`
fails a DONE line in `ROADMAP.md` naming a missing path). An entry another file
points at by heading keeps a stub heading and a pointer. Do not touch items
nobody worked on.

## 7. Rewrite `RSC-NEXT-SESSION.txt` - CARRY FORWARD EVERY ITEM NOT ACTED ON

This tracked repo-root file is the ONLY continuity. The next session reads it
first. Rewrite it, then commit it with the rest of the paperwork.

- **Read the CURRENT file first.** Every item in it that this session did not
  act on is CARRIED FORWARD, verbatim or tighter. An item is never dropped
  because the session worked on something else. An item leaves the file only
  when it was done (and the ledger says so) or explicitly retracted (and the
  file says why).
- Contents: the bootstrap reading order (it includes running
  `python tools/roots_map_probe.py` from the main checkout and reading its
  DRIFT lines - ADR-013 interim d) and the standing warning not to
  re-derive gacha constants; the gates in section 1 order; the state observed
  THIS session, stamped with date and commit, labelled as a reading; traps that
  have actually bitten here; open work highest priority first; what must NOT be
  redone, each entry stating what would reverse it.
- A recorded act names what was READ BACK after it, never what was run.
- **The session counter (FLEET-COMMON item 13 a).** Read n from the ONE
  column-0 `SESSION: <n>` line of the CURRENT file before rewriting it, then
  write exactly one `SESSION: <n+1>` line, as the LAST line of the new file.
  Never two such lines, never a leading zero, never trailing text on the line.
  If the current file has no single readable counter line, stop: that is the
  failure line. The SessionStart hook `tools/session_checklist.py` reads this
  line to name the next session, and `tests/test_session_checklist.py` fails
  on a missing or duplicated one. The seed was 56, a COMMIT-COUNT PROXY (55
  commits had touched the hand-off under either name since 9e2bf0b), not a
  count of sessions.
- **Raw text, no markdown wrapper, no fence.** 7-bit ASCII, at least 2000 bytes,
  no credential or account path, one readable counter line - enforced by
  `tools/check_handoff.py`. Run it on the rewritten file; any refusal is the
  failure line - fix `RSC-NEXT-SESSION.txt` and re-run:

  ```
  python tools/check_handoff.py
  ```
- **The file is tracked and the repository is public.** It is swept by
  `tests/test_machine_identity.py`, `tests/test_no_sibling_names.py` and
  `tests/test_task_state_claims.py`. No real account, sibling project name or
  sibling absolute path - use the channel codes.

## 8. Memory

Check `~/.claude/projects/C--Resin-Compute/memory/` for anything written this
session and confirm `MEMORY.md` indexes it.

## 8b. The local status board render (FLEET-KIT v23, FLEET-COMMON 18)

After the hand-off and the commit are READ BACK and before the done marker,
render the board once, LOCAL ONLY. Pipe the last printed item-13 checklist
into the kit (n = the counter this session ran under):

```
python ops/fleet_kit/fleet_board.py render --final --session <n> --checklist <checklist file>
```

It writes status.json, state.json and board.html to the gitignored board dir
under ops/loop/control in the MAIN checkout and prints one JSON summary. No
claude.ai artifact, no Artifact or ArtifactData call, no `pushed` or
`account` step (v23 removed the push; operator order 2026-10-25). A headless
run renders nothing. A FAILED RENDER IS A HAND-OFF LINE, NEVER A RITUAL
FAILURE: add `board render failed: <reason>` to `RSC-NEXT-SESSION.txt`,
re-run `python tools/check_handoff.py`, commit that one file through
fleet_gitlock, read it back, and continue to section 9 with `--status done`.
The checklist file is the last printed checklist text, written to the
session scratchpad.

## 9. The done marker, then the one line

The LAST act of the ritual (FLEET-KIT v9, FLEET-COMMON item 15, MAIN 2354
ORDER of 2026-10-07). Only after the commit and the hand-off have been READ
BACK, write the marker, with n the counter the CURRENT session ran under (the
value read in section 7, not the n+1 just written):

```
python ops/fleet_kit/fleet_done.py mark --session <n> --status done
```

If any section stopped the ritual, still write the marker, naming the step:

```
python ops/fleet_kit/fleet_done.py mark --session <n> --status failed --reason "<step>"
```

The kit reads HEAD and hashes `RSC-NEXT-SESSION.txt` itself and writes its session_done marker under the
MAIN checkout's loop control directory (gitignored runtime state). Its
stdout line is NOT chat: it is the marker's receipt and is not repeated. The
project Stop hook (`fleet_done.py stop-hook` in `.claude/settings.json`) then
sets the tab title; any later commit or hand-off edit invalidates the marker,
which is correct.

Then print exactly `Done ritual complete, safe to clear`, or the one line
naming the failure that stopped the ritual. Nothing before it, nothing after it. Never
print the hand-off or a next-session prompt into chat; the operator opens
`RSC-NEXT-SESSION.txt` and types only "continue", "/done" or "/clear".

## Safety rails

- NEVER force-push, NEVER `--amend`, NEVER `--no-verify`.
- NEVER commit secrets, credentials, or anything under `data/` from a licensed
  source.
- Under Git Bash write `taskkill //F //PID <pid>`; a lone `/F` becomes `F:/`.
- A heredoc plus a non-raw Python string mangles backslashes; use the Write/Edit
  tools for content with backslashes.
- `/clear` is a harness built-in; the operator types it.
