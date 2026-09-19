---
description: End-of-session ritual - gates, commit, push, CI, ledger, roadmap, and the next-session hand-off printed inline as the last thing in the message.
argument-hint: [optional one-line session topic]
---

# /done - end-of-session ritual

Run EVERY section, in order. Report the result you OBSERVE for each one, with
counts. Do not skip a section because it "looks clean", and never carry forward
a count from earlier in the session or from a subagent - per CLAUDE.md a filed
count is a hypothesis, not a fact. Session topic, if given: $ARGUMENTS

## The shape, and what was deliberately not ported

This is Sibling-C's ritual adapted to this tree, not transcribed from it.
Three things were dropped on purpose, and each should stay dropped:

- **No four-phase CI overlap.** Sibling-C pushes early so ~15 minutes of
  paperwork can run against a ~27-minute suite. This tree's suites finish in
  seconds, so the overlap optimises a cost that does not exist here and would
  only add ordering rules to get wrong.
- **No `WAKEUP_NOTES.md`.** Sibling-C and Sibling-B keep a rolling session log
  plus an archive. Here `RSC-NEXT-SESSION.txt` is the hand-off,
  `docs/LEDGER.md` is the closed-work history and `ROADMAP.md` is the open-work
  list. Three files already cover it; a fourth would just be a fourth place to
  go stale.
- **No drift guard script.** `tests/test_docs_consistency.py` is this tree's
  equivalent and it already runs in both CI workflows and in section 1.

What IS carried across, because it is the part that earns its keep: the gate
runs before the commit, the paperwork is not optional, and the session ends by
handing the next one a running start.

## 0. What this session touched

- `git status -s` and `git log --oneline -5`. Name the files YOU authored.
- Check nothing unexpected is staged: no `.env`, no runtime state, no game data.
  Per ADR-002 and `docs/LICENSE_NOTES.md` this tree vendors no game data, and
  `data/fixtures/` is hand-authored only, nothing vendored. A real cost table or banner list appearing
  in `data/` is a stop-and-ask, not a commit.
- **Hooks are the authoritative gate and a fresh clone has NONE.** Confirm with
  `git config core.hooksPath` - it must print `.githooks`. If it prints nothing,
  run `python scripts/install_hooks.py` before going further. Never treat a
  hook's presence as proof it fires.

## 1. The gate - all of it, before any commit

The three QA gates lead because each one found a real defect on its first run.
They are cheap. Run them first.

```
python -m pytest tests/test_licence_posture.py -q
python -m pytest tests/test_docs_consistency.py -q
python scripts/qa_companion.py
```

Then the standard gates. Run the two Python suites SEPARATELY - never
`pytest .` from the root, per `pytest.ini`:

```
python -m ruff check .
python -m pytest tests
python -m pytest agents/pity_engine
cd shell && node --test
python -m headless.runner --once --dry-run
```

- **`python -m mypy` is ADVISORY here, not a gate.** `.github/workflows/ci.yml`
  carries `continue-on-error: true` on it, and `docs/SPEC_SCAFFOLD.md` section 7
  defines slice acceptance as py_compile + ruff + the slice's own pytest + no
  banned glyph, with mypy deliberately absent. Run it, report what you see, and
  do not block the commit on it. If it is red for the known environmental
  reason - mypy following `_pytest` into a numpy stub that uses PEP 695 syntax
  invalid under the pinned `python_version = 3.11` - say so and move on.
- GREEN: proceed. RED: fix and re-run. A pre-existing failure unrelated to this
  session's work gets named ABOVE the banner and the green-verified authored
  files still commit; never commit over a regression you introduced.
- A skipped suite is not a passing suite. Say what was skipped and why.

## 2. Commit

Versioning is cheap and lost work is not, so the default is: green gate means
commit. Do not leave authored work uncommitted because it feels small.

- Stage deliberately, file by file. Never `git add -A`.
- **NEVER add a `Co-Authored-By: Claude` trailer, or any other trailer.**
  `.githooks/commit-msg` strips it per operator policy, so adding one is a
  silent no-op rather than a choice. A harness whose own standing instructions
  inject that trailer by habit does not change this: the repo policy wins and
  the hook absorbs it either way. Do not spend a line of the message on it, and
  do not file its absence from an earlier commit as a defect - that absence is
  the policy working.
- 7-bit ASCII, imperative subject. No em-dashes, no en-dashes, no smart quotes.
- **For a message with special characters use `git commit -F <tmpfile>` or a
  SINGLE-quoted here-string.** Never a double-quoted here-string and never a
  piped string.
- If a hook rejects the commit, fix it and make a NEW commit. Never `--amend`,
  never `--no-verify`.

## 3. Push

`git push origin main`. The pre-push hook runs ruff plus both suites before
anything leaves the machine, so a push is slower than a commit and that is the
design. Read the output: a push that printed an error is not a push.

`RESIN_SKIP_PREPUSH=1` exists for a docs-only push. Using it means CI is your
only gate - say so in the banner if you use it.

## 4. CI - know which workflow you actually triggered

This tree has TWO workflows and they are complementary. Getting this wrong
means watching a run that was never going to start:

- `.github/workflows/ci.yml` carries `paths-ignore: ['**/*.md']`. **A docs-only
  push fires no `ci` run at all.** That is not a failure and it is not
  something to fix with a `workflow_dispatch`.
- `.github/workflows/docs-guards.yml` fires on exactly what `ci.yml` declines,
  and runs the ASCII scan plus the guards that read tracked `.md`.

So: `gh run list --branch main --limit 3`, identify the run your push actually
triggered, and report it as green, red or pending. Do not dispatch a second run
of something the push already started. If it is still running, say so - do not
predict the result.

## 5. Append to `docs/LEDGER.md`

Newest first, at the TOP of the body, in the existing entry format. One entry
per landed unit of work.

- What changed, and what was MEASURED rather than intended.
- The verification pointer: the file and the test name that prove it.
- Any decision made, stated with its reasoning, so it is not re-litigated.
- A count may appear only stamped with the date it was measured, as a
  historical reading rather than a claim about now.
- **Never put a per-item entry in `CLAUDE.md`.** That file is loaded every turn.

## 6. Update `ROADMAP.md`

- Flip anything that shipped, and cite the path that proves it. Note that
  `tests/test_docs_consistency.py` fails if a line marked DONE names a path that
  does not exist, so a premature tick is caught rather than believed.
- Add new items for what this session opened up.
- Do not touch items nobody worked on.

## 7. Rewrite `RSC-NEXT-SESSION.txt` - the RAW hand-off, no wrapper

This file is the SOURCE OF TRUTH for the hand-off. Sections 9 and 11 both read
from it, so it is written once here and never retyped afterwards.

The fenced block must be self-contained - the next session boots cold and has
only what the operator pastes into it:

- The bootstrap reading order, and the standing warning not to re-derive gacha
  constants from memory or a web search.
- The gates, in the order section 1 runs them.
- The state you observed THIS session, stamped with the date and commit, and
  labelled as a reading rather than a promise.
- The traps that have actually bitten in this tree. Every entry measured, none
  hypothetical.
- Open work, highest priority first, and anything that must NOT be redone.

**THE FILE IS THE HAND-OFF, RAW - NO MARKDOWN WRAPPER AND NO FENCE.** Changed
2026-09-19 on operator ruling. It used to be `NEXT_SESSION_PROMPT.md`, a
markdown page wrapping the hand-off in one fenced block. It is now
`RSC-NEXT-SESSION.txt`, the bare text and nothing else, which is what the
sibling trees keep and what the Desktop shortcut opens in Notepad - a wrapper
and a pair of fences are noise in that window. Write the hand-off straight into
the file; do not add a heading, a preamble or a fence.

Mechanical constraints, enforced by `tools/publish_next_session.py`:

- **7-bit ASCII, and at least 2000 bytes.** A truncated hand-off reads as
  current, which is worse than a stale one. These now cover the WHOLE file
  rather than one block of it.
- **A fenced source is still accepted and still unwrapped**, so the tool stays
  usable across the fleet while the other trees migrate. MORE than one fenced
  block is still refused, because that file is ambiguous about which block is
  the hand-off.
- **THE FILE IS TRACKED AND THE REPOSITORY IS PUBLIC.** It is swept by
  `tests/test_machine_identity.py`, `tests/test_no_sibling_names.py` and
  `tests/test_task_state_claims.py`. MEASURED 2026-09-19: a first draft of this
  hand-off named a sibling repo's absolute path and the account short-name, and
  all three guards fired. Do not write a real account, a sibling project name,
  or a sibling's absolute path into it - use the channel codes.

## 8. Memory

Check `~/.claude/projects/C--Resin-Compute/memory/` for
anything written this session, and confirm `MEMORY.md` indexes it. A memory
file with no index line is invisible to the next session.

## 9. Publish the Desktop backup - BEFORE the banner, not after

```
python tools/publish_next_session.py --check
```

**DO NOT RUN THE BARE PUBLISH UNTIL THE PUBLISHER IS CONVERTED.** Operator
ruling 2026-09-19: the Desktop no longer holds a detached COPY of the hand-off,
it holds `RSC-NEXT-SESSION.lnk` POINTING AT the tracked repo-root
`RSC-NEXT-SESSION.txt` - the shape the sibling trees already use. A bare
`python tools/publish_next_session.py` still writes the old detached copy and
would recreate exactly the stale artifact that ruling removed. `--check` reports
drift and writes nothing, so it is safe and is what this section now runs.

The conversion of the publisher to converge the shortcut instead of writing a
copy is an OPEN ROADMAP ROW. Until it lands, this section verifies rather than
publishes.

- There is now only ONE copy of the hand-off text anywhere: the tracked
  `RSC-NEXT-SESSION.txt` in the repo root. The inline block in section 11 is
  read out of that same file, so the printed block and the file cannot
  disagree - not because a guard compares them, but because there is nothing
  left to disagree with.
- The Desktop is shared with five sibling projects that own the `CS-`, `LL-`,
  `LW-`, `RC-` and `RM-` prefixes - those five basenames are observed on disk
  and are deliberately not codenamed, because a guard that compares against
  invented filenames is vacuous. `RSC-` is unconfusable with any of them.
- If `--check` refuses, that is a failure of the ritual - fix
  `RSC-NEXT-SESSION.txt` and re-run. Never hand-write anything onto the Desktop.

## 10. Banner

Everything you want the operator to read goes HERE, above the block:

```
==================================================================
  /done complete
==================================================================
  - commits this session : <count> (pushed: <range>)
  - three QA gates       : licence <r> / docs <r> / companion <r>
  - ruff                 : <result>
  - pytest tests         : <observed counts>
  - pytest pity_engine   : <observed counts>
  - shell node --test    : <observed counts>
  - headless smoke       : exit <code>
  - mypy (advisory)      : <result>
  - CI                   : ci | docs-guards | none - <status>
  - ledger / roadmap     : <updated | skipped>
  - desktop backup       : RSC-NEXT-SESSION.txt, <N> bytes
==================================================================
```

Anything that failed is surfaced ABOVE the banner, not folded into it.

## 11. Print the hand-off inline - THE LAST THING IN THE MESSAGE

Print the fenced block from `RSC-NEXT-SESSION.txt` verbatim, in chat, in one
fence. This is the continuity mechanism, not a courtesy: rediscovery - redoing
closed work, re-pitching a settled decision, acting on a stale doc - is the
dominant failure mode, and this block is the defence against it.

- **Inline, in full, every time.** Writing it to `RSC-NEXT-SESSION.txt` in
  section 7 does NOT satisfy this, and neither does summarising it or pointing
  at the file. The operator pastes out of the chat.
- **No language tag on the fence.** A `bash` tag puts a Run button on it.
- **Emphasise with CAPS, not asterisks.** Nothing renders inside a fence, so
  `**` reaches the operator as two literal asterisks.
- **Nothing follows the closing fence. Nothing.** No "what was done this
  session" review, no summary, no sign-off, no offer to continue. Operator
  instruction, 2026-09-06: the block is selected by hand, and trailing prose is
  text they have to select around. Everything you wanted to say went in the
  banner at section 10.
- This applies whether `/done` was invoked explicitly or the ritual was merely
  inferred from the operator wrapping up.

## Safety rails

- NEVER force-push, NEVER `--amend`, NEVER `--no-verify`.
- NEVER commit secrets, credentials, or anything under `data/` that came from a
  licensed source. When in doubt, stop and ask.
- Under Git Bash write `taskkill //F //PID <pid>`. A lone `/F` is rewritten to
  `F:/` by MSYS path conversion, and it fails SILENTLY when redirected.
- A heredoc plus a non-raw Python string mangles backslashes. It has already
  put a BEL byte into `docs/LEDGER.md` once, and it silently no-opped a
  string replacement during the session that wrote this file. Use the
  Write/Edit tools for content with backslashes.
- `/clear` is a harness built-in. Print the block and let the operator type it.
