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
PowerShell, Read, Edit, Write, Grep and Glob call in the main thread is denied
(or, in log mode, logged as would-deny). It launches ONE sub-agent, in the
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
- `git config core.hooksPath` must print `.githooks`. If it prints nothing, run
  `python scripts/install_hooks.py` first.

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
- `python -m mypy` is ADVISORY: `.github/workflows/ci.yml` runs it with
  `continue-on-error: true` and `docs/SPEC_SCAFFOLD.md` section 7 leaves it out
  of slice acceptance. Record its result; do not block on it.
- RED that this session introduced: fix and re-run; never commit over it. A
  pre-existing failure unrelated to this session is recorded in the ledger and
  the hand-off, and the green-verified authored files still commit.
- A skipped suite is not a passing suite. Record what was skipped and why.

## 2. Commit

Green gate means commit. Do not leave authored work uncommitted.

- Stage deliberately, file by file. Never `git add -A`.
- **NEVER add a `Co-Authored-By: Claude` trailer** or any other trailer.
  `.githooks/commit-msg` strips it per operator policy; never file its absence
  as a defect.
- 7-bit ASCII, imperative subject. Use `git commit -F <file in the session
  scratchpad>`; never a double-quoted here-string or a piped string.
- If a hook rejects the commit, fix it and make a NEW commit. Never `--amend`,
  never `--no-verify`.

## 3. Push

`git push origin main`. The pre-push hook runs ruff plus both suites. A push
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

## 5. Append to `docs/LEDGER.md`

Newest first, at the TOP of the body, in the existing entry format. One entry per
landed unit of work: what changed and what was MEASURED, the verification
pointer (file and test name), any decision with its reasoning. A count appears
only stamped with its measurement date. Never put a per-item entry in
`CLAUDE.md` - that file is loaded every turn.

## 6. Update `ROADMAP.md`

Flip what shipped and cite the path that proves it
(`tests/test_docs_consistency.py` fails a DONE line naming a missing path). Add
items this session opened. Do not touch items nobody worked on.

## 7. Rewrite `RSC-NEXT-SESSION.txt` - CARRY FORWARD EVERY ITEM NOT ACTED ON

This tracked repo-root file is the ONLY continuity. The next session reads it
first. Rewrite it, then commit it with the rest of the paperwork.

- **Read the CURRENT file first.** Every item in it that this session did not
  act on is CARRIED FORWARD, verbatim or tighter. An item is never dropped
  because the session worked on something else. An item leaves the file only
  when it was done (and the ledger says so) or explicitly retracted (and the
  file says why).
- Contents: the bootstrap reading order and the standing warning not to
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
  enforced by `tools/publish_next_session.py`.
- **The file is tracked and the repository is public.** It is swept by
  `tests/test_machine_identity.py`, `tests/test_no_sibling_names.py` and
  `tests/test_task_state_claims.py`. No real account, sibling project name or
  sibling absolute path - use the channel codes.

## 8. Memory

Check `~/.claude/projects/C--Resin-Compute/memory/` for anything written this
session and confirm `MEMORY.md` indexes it.

## 9. Converge the Desktop shortcut

```
python tools/publish_next_session.py
```

It converges `RSC-NEXT-SESSION.lnk` onto the tracked `RSC-NEXT-SESSION.txt` - a
pointer, never a second copy (operator ruling 2026-09-19; the one sanctioned
write outside the repo root). Run it from the canonical checkout: from a linked
worktree `main()` refuses by exit code, which is correct and not a ritual
failure. `--check` reports drift and writes nothing. Any other refusal is the
failure line - fix `RSC-NEXT-SESSION.txt` and re-run. Never hand-write anything
onto the Desktop.

## 10. The done marker, then the one line

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
