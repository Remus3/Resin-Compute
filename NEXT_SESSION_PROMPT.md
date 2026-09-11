# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and
`tools/publish_next_session.py` reads it verbatim to write the Desktop backup.

```
RSC - next session, HEADLESS, operator MAY BE PRESENT.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS, LW and LL on ORDERED STANDBY - silence is NOT dissent, do not write into
their trees.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before a data source read docs/LICENSE_NOTES.md.
Before re-litigating read docs/adr/README.md.

DO NOT RE-DERIVE GACHA CONSTANTS. docs/SPEC_SCAFFOLD.md section 3, ADR-003.
50/50 is 55.000% consolidated since 5.0. Weapon soft-pity saturates at pull 77
under a 7% increment. 1.600% is 1/E[wishes per 5-star], NEVER per-wish
Bernoulli. BOTH WERE CONFIRMED BY THE LIVE CLIENT ON 2026-09-11 - see below.

NO BLOCKING QUESTIONS. Where you would escalate, dispatch an ADJUDICATOR and
record the ruling in ROADMAP.md MARKED PLAINLY AS AN ADJUDICATED CALL. TEN
STAND, UNCHANGED - 2026-09-10 and 2026-09-11 added NONE. Every disagreement was
settled by MEASUREMENT. An adjudicator is for a question measurement cannot
close. Find each by HEADING in ROADMAP.md, never by line number.

DO NOT ARM ANYTHING. Verified DORMANT via
`python ops/check_task_liveness.py ResinCompute-Responder`, exit 1, trigger
expired 2026-09-07T21:00.

*** STILL HALTED AND WAITING FOR THE OPERATOR - UNCHANGED, NOTHING NEW ***
RC's JOINT RE-PIN REQUEST. STEP 1 IS DONE AND ANSWERED: NO - RAW hits only
inside tests/test_no_sibling_names.py which is SELF-exempt, NORMALISED-ONLY hits
ZERO. AND RC'S PREMISE IS WRONG: our tests/test_loop_concurrency.py pins
ops/loop/slots.py and ops/loop/winmutex.py by SHA256 and DOES NOT PIN ITSELF, so
the two test modules legitimately diverge. STEPS 2-4 HALTED under ruling clause
(c). NOTHING IS BLOCKED ON US.

TWO OPERATOR DECISIONS OUTSTANDING, NEITHER BLOCKING:
  1. refusals_usable at tools/moon_sync_responder.py deliberately does NOT fail
     closed on corrupt content. That is now INCONSISTENT with the rule
     scripts/watch_inbox.py adopted on 2026-09-11. Defensible on cost rather
     than accidental. Rule on it; do not silently harmonise either side.
  2. Arming CS / LW / LL. Clause (c) needs bilateral agreement, they cannot
     reply, and the ADOPTED rule is halt-and-wait with NO TIMEOUT. Only the
     operator can lift standby or carve out clause (c).

GATES, in /done order, EACH AS ITS OWN COMMAND. Chaining with && reports only
the LAST link.
  python -m pytest tests/test_licence_posture.py
  python -m pytest tests/test_docs_consistency.py
  python -m pytest tests/test_docs_hook_commands.py
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
DO NOT PASS -q ON THE COMMAND LINE. pytest.ini sets it; a second makes it -qq.

STATE AS OBSERVED 2026-09-11 at 2dc0965, a reading not a promise. RE-MEASURE.
  pytest tests   2106 passed 1 skipped. COLLECTED AND PASSED ARE DIFFERENT
  POPULATIONS. agents/pity_engine 80 passed. node --test 52 tests 52 pass 0
  fail. licence 47, docs consistency 29, docs hook commands 17. qa 18 passed
  0 failed 1 skipped 3 noted. ruff / headless / mypy exit 0.
  mypy ADVISORY. Its 34 source files say NOTHING about scripts/, surface/,
  headless/, ops/ or tests/. Never cite its Success about those.
  git ls-files 218 paths. git ls-files -- '*.py' 135. BOTH DECAY.
  CHECK EVERY SESSION, FIRST: gh run list --limit 5
  CI at 2dc0965: `ci` GREEN, watched with `gh run watch --exit-status`, exit 0.
  docs-guards did NOT fire on that push and that is CORRECT - ci.yml carries
  paths-ignore '**/*.md' and docs-guards fires on exactly what ci declines.
  LOCAL GREEN IS OPTIMISTIC. qa_companion NOTEs local ruff 0.15.12 / pytest
  9.0.3 / mypy 2.1.0 are ALL OLDER than the CI pins, and the interpreter here is
  3.14 while CI runs 3.11.

WHAT LANDED 2026-09-11, DO NOT REDO.
  b3ff9fe scripts/watch_inbox.py - three degrade-to-empty-then-rewrite sites.
  3c4bcb5 surface/ - Plan rotation rows, Teams elemental identity, render ASCII
          fold, and the two ascii gates that could not fail.
  9f03062 five decayed doc pointers, and three sibling sites FILED not fixed.
  2dc0965 surface/model.py - the Resin panel projects instead of ignoring `now`.

THE OPERATOR'S ACCOUNT IS NOW A REAL INPUT. uid 692912734, xMoonbeam, NA, AR 7,
World Level 0, achievements 4, version 7.0. 9 characters, ALL ascension 0 and
C0; only Dehya 10000079 and Noelle 10000034 resolve, the other seven render as
unknown:<id> BY DESIGN. Dehya lvl 20 at ascension 0 is ON the first cap per
engines/objectives.py ASCENSION_LEVEL_CAPS. Primogems 288, Mora 34102,
Intertwined Fate 6, Starglitter 0, Stardust 165. Welkin ACTIVE with 26 days
left as of 2026-09-10. Character-banner pity 0, no guarantee, and zero pulls on
Weapon / Chronicled / Character Event. Original Resin observed 200/200 at
2026-09-11T01:39:48Z.
  DO NOT WRITE ANY OF THAT INTO data/. data/fixtures/ is HAND-AUTHORED only.
  DO NOT resolve the seven unknown avatarIds by guessing - that is vendoring,
  and the placeholder exists to prevent exactly it.

TWO EXTERNAL VALIDATIONS OF THIS TREE'S CONSTANTS, measured 2026-09-11 from the
live client, which this repo is licence-gated away from holding as a source.
Neither figure entered data/.
  1. The banner detail text states the consolidated 5-star event-exclusive
     probability is 1.103%. This tree predicts 1.1034% from 55.000% plus
     1.600% as 1/E[wishes per 5-star]. Four significant figures.
  2. A talent-material tooltip names its domain Tuesday/Friday/Sunday, which is
     exactly ROTATION_SLOT_WEEKDAYS[1] in core/domains.py.

OPEN ROWS. RE-PROBE EACH BEFORE SPENDING A SLICE.
  - tools/moon_sync_responder.py has THREE unfixed degrade-to-empty sites, filed
    2026-09-11 as applicable-and-not-done: _remember_answered, record_cycle, and
    a latent threefold-growth in _trim_invocations which reads errors="replace"
    but never folds U+FFFD while atomic_io encodes UTF-8. The adjudicated
    authorisation covers a BOUNDED rotate at the metrics ledger ONLY.
  - The metrics ledger at tools/moon_sync_responder.py:1135 trims rather than
    rotates. ADJUDICATED 2026-09-11: a BOUNDED rotate is AUTHORISED HEADLESS; an
    UNBOUNDED archive is NOT; extending to the other four trim sites is NOT,
    because ROADMAP.md:109 closed the invocation-log question.
  - The Resin panel has no automatic observation source. Original Resin is not
    in the Enka payload and never will be. Today an observation is typed in by
    hand. Same gap as the income-velocity item under Next.
  - Still unmeasured on the operator's account: Original Resin sinks available
    at AR 7, Daily Commission unlock status, Adventurer Handbook. One screen
    (F1) closes all three.
  - SIX split-name shapes NEITHER our sweep NOR RC's normalisation can see,
    enumerated at the site in tests/test_no_sibling_names.py. NOT closed.
  - Sender side is unguarded against editing a note after delivery. ALREADY
    FILED at ROADMAP.md and docs/INBOX_TRIAGE_2026-09-09.md, and the row that
    cited a digest at :1261 was REFUTED - that is refusal_key, hashing filename
    plus bounce codes on the REFUSAL path. The real blocker is that no artifact
    exists for a sender-side check to compare against.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating, self-adversarial
by DEFAULT, and SUBAGENT-FIRST ALWAYS. The agent that produced a thing NEVER
grades it. FREEZE THE CANDIDATE before dispatching a grader, and give every
grader THREE state assertions - HEAD sha, git status --porcelain, and the
candidate file's sha256 - so it can tell you the tree moved instead of grading
the wrong bytes. This caught a real mid-audit move on 2026-09-11.
DISPATCH REFUTERS WITH DISTINCT LENSES. AGREEMENT BETWEEN TWO AGENTS IS NOT
EVIDENCE - on 2026-09-11 two documents agreed about a metrics trim and were ONE
input counted twice, proven by the identical WRONG line number in both.

TRAPS THAT ACTUALLY BIT, every one measured.

- A GATE THAT CANNOT FAIL PASSES ON BOTH SIDES OF A REAL DEFECT. The ascii arm
  rendered an ASCII-ONLY fixture and qa_companion graded the EMPTY state, while
  render_html emitted 48 non-ASCII bytes for an externally supplied name. Ask
  what INPUT an arm feeds, not whether the arm exists.
- A SAMPLED NEGATIVE IS A STATEMENT ABOUT THE SAMPLE. Report the rate with it.
- AN EMPTY RESULT CAN BE A CLAIM ABOUT YOUR FILTER. A stability filter over
  frames the capture rule had SELECTED FOR INSTABILITY returned zero by
  construction.
- /tmp_x.txt UNDER GIT BASH LANDS IN C:\Program Files\Git\, NOT the C: drive
  root. cygpath -w it before claiming it was or was not created. Redirect to the
  session scratchpad by ABSOLUTE PATH.
- A LINE NUMBER IN A DOC DECAYS. Five had rotted by 2026-09-11. Cite by content
  and re-measure before citing.
- A NET-ZERO-BYTE-SIZE mutate-and-restore WITHIN THE SAME SECOND runs the
  MUTANT'S BYTECODE. Purge __pycache__ AND .pytest_cache on BOTH sides.
- NEVER `git checkout --` to restore a mutation. Save bytes, restore, verify by
  sha256, assert source.count(old) == 1 before substituting.
- COMPARING AN ENUM ACROSS TWO MODULE LOADS gives two distinct classes. A
  verifier reported 24 phantom diffs from `is not` before comparing .name.
- A QUOTED HEREDOC STILL MANGLES BACKSLASHES. Write .py with the editor tools.
- write_text EMITS CRLF ON WINDOWS and .gitattributes eol=lf hides it. tests/ is
  OUTSIDE test_no_crlf_writers.py's corpus.
- grep -c '[^\x00-\x7F]' IS NOT A CHARACTER CLASS. Check bytes IN PYTHON.
- NEVER TYPE A BANNED GLYPH AS A LITERAL, even in a test that enforces the rule.
  Build from chr(0x2014).
- A WORKTREE MATERIALISES AT AN ANCESTOR OF THE DECLARED FORK POINT. Put an
  explicit `git merge --ff-only <sha>` in every brief PLUS an assertion on
  content that EXISTS ONLY AT THE FORK POINT.
- UNCOMMITTED SLICE WORK IS INVISIBLE TO THE NEXT WORKTREE. Reuse the SAME
  worktree for a follow-on slice, or cp by ABSOLUTE PATH.
- EnterWorktree REFUSES for a subagent. Use `git worktree add`.
- TaskStop a finished agent once its report lands.
- An empty pytest parametrize is `1 skipped`, exit 0, NOT a failure.
- A PYTEST PROGRESS LINE IS 72 DOTS, NOT THE WHOLE RUN.
- exit=$? AFTER A PIPE READS THE LAST PIPE STAGE. Redirect to a file.
- NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. RC, CS, LW, LL, RSC.
- Never Stop-Process. taskkill //F //PID under Git Bash.
- NEVER ADD A Co-Authored-By TRAILER, and never file its absence as a defect.

CHECK TASK LIVENESS WITH THE CHECKER, NEVER A STATE STRING, NEVER THROUGH A
PIPE:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. Observed 1 DORMANT.
KILL SWITCH:
  powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

INBOX: 157 files, 0 unread, all triaged and MARKED. RE-MEASURE. Gitignored
wholesale - the guards derive their corpus from `git ls-files`, so an untracked
path is outside their reach BY CONSTRUCTION. Do NOT write the universal "no
guard reads it".

DO NOT REDO: everything at b3ff9fe, 3c4bcb5, 9f03062 and 2dc0965. The three
vacuous floors. The supervisor and responder argv graders. The lane-selection
pin. The _SOLO view asymmetry. The name-to-site binding table. The
undeclared-shape-grader detector. The atomic_io 0-byte temp leak. The census
prose decay. The eight gates exercised by nothing. slots.py re-pin.
Manifest-as-key (withdrawn). Caveman dialect (settled). Wenyan (reverted
2026-06-27). Only M12 exists. Do not re-derive the ceilings in docs/LEDGER.md.
Do not re-litigate the ten adjudicated calls without reading them. Do not
re-sweep the mkdir sites. Do not rebuild the git-reason hand-typed fixture. Do
not re-open the census REFERENT. Do not widen _READ_ATTRS, _FIRST, _SECOND,
_SOLO or _SEP - WIDENING A MATCHER is the response this tree has been defeated
by three times.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes.
```
