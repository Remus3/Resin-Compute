# Next-session prompt

This file is the SOURCE OF TRUTH for the hand-off. `/done` prints the fenced
block below inline in chat, and `tools/publish_next_session.py` copies the same
bytes to the Desktop as `RSC-NEXT-SESSION.txt`. Never retype it in either place.

Exactly one fenced block, 7-bit ASCII, at least 2000 bytes. The publisher
refuses on zero blocks, on more than one, on non-ASCII, on a short block, on a
vendor-prefixed credential and on an absolute path naming a real user profile.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

FIRST ACTION IN A FRESH CLONE: python scripts/install_hooks.py
core.hooksPath is local config and is NOT cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires.

THE INBOX IS SESSION READING, AND SO ARE ITS SUBDIRECTORIES. Operator
instruction 2026-09-07, recorded in CLAUDE.md, broadcast to all five repos.
  python scripts/watch_inbox.py            what is new since the last mark
  python scripts/watch_inbox.py --all      everything
  python scripts/watch_inbox.py --mark     record the current set as read
THE WATERMARK IS HONEST AS OF 2026-09-07. All 66 notes were triaged and answered
and the mark was advanced, so anything it reports now is genuinely new. Keep it
that way: mark only what you actually triaged.
The watcher now FIRES ON ITS OWN as a SessionStart hook, so unread notes appear
in your context at session start without you running anything.

READ THE SUBDIRECTORY, NOT JUST THE NOTES. moon_sync_inbox/from-RC-verbatim/
holds 49 real files - hooks, guards, tools, tests - while the notes beside it
only describe them. The 2026-09-06 session read the notes and skipped the
directory, and re-derived by hand what had arrived working. Verbatim bytes
SUPERSEDE any paraphrase of them in a note.

BOOTSTRAP, in this order:
  CLAUDE.md, README.md, ROADMAP.md, docs/LEDGER.md, docs/SPEC_SCAFFOLD.md,
  docs/adr/README.md, and `git log --oneline -12`.
SPEC_SCAFFOLD.md is the authoritative build contract and carries every verified
domain constant. DO NOT re-derive gacha numbers from memory or a web search, and
do not "fix" them against the originating brief, which was wrong in three places
that are now regression-tested. The three: the 50/50 has been 55.000%
consolidated since version 5.0, the weapon soft-pity ramp saturates at pull 77
under a 7% increment, and 1.600% is 1/E[wishes] rather than a per-wish Bernoulli
value.

READ THE "Session default" SECTION OF CLAUDE.md BEFORE DISPATCHING ANYTHING.
Orchestrated, multi-agent, self-adjudicating, self-adversarial. Seven roles in
.claude/agents/, protocol in /orchestrated-run, reasoning in ADR-007.
WORKTREE-ISOLATE EVERY AGENT THAT WRITES.

OUTPUT RULES, operator instructions 2026-09-06/07, all in CLAUDE.md:
  - Responses under 500 output tokens. Long output goes to a file.
  - CAVEMAN ULTRA is the default CHAT dialect. Terseness is for chat ONLY:
    paths, commands, code, identifiers and every committed artifact stay
    byte-exact. Answer clarifying questions in plain English.
  - Speak in chat only for something to RULE ON or be NOTIFIED of. Progress
    commentary is noise; the tool calls already show the work.

RUN THE THREE QA GATES FIRST, then the standard ones:
  1. python -m pytest tests/test_licence_posture.py
  2. python -m pytest tests/test_docs_consistency.py
  3. python scripts/qa_companion.py

  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
  python -m mypy            (ADVISORY - ci.yml carries continue-on-error)

Run the two Python suites SEPARATELY. Never `pytest .` from the root.
DO NOT ADD -q TO ANY OF THOSE. pytest.ini addopts ALREADY carries -q. A second -q
makes -qq and SUPPRESSES the summary line, so you get a wall of dots and no count
and cannot report what you did not see.

STATE, measured 2026-09-07 at commit e2a3161 (report what YOU observe, never
these numbers):
  licence QA                      41 passed
  docs QA                         23 passed
  scripts/qa_companion.py         16 passed, 0 failed, 2 skipped
  ruff                            All checks passed
  pytest tests                    930 passed, 1 skipped
  pytest agents/pity_engine       80 passed
  shell node --test               52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 23 source files
  RSC_REQUIRE_HOOK_GATE=1 pytest tests/test_hook_gate.py    12 passed
  git worktree list | tail -n +2 | wc -l                    0
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. Still untouched - decide
  whether to align the declaration or the runtime, do not assume either.

SETTLED THIS SESSION. DO NOT REDO:
  - THE FORK-PR RISK WAS ALREADY CLOSED. approval_policy is
    "first_time_contributors", so a stranger's first PR needs a human click
    before any workflow runs. Re-check only if someone loosens it.
  - THE HOOK GATE IS PROVEN ON A REAL RUNNER. ubuntu-latest reported
    "armed: ... (all mode 100755)" then "12 passed in 0.75s". Ran, not skipped.
  - THE WATCHER FIRES. .claude/settings.json is TRACKED (.gitignore carries
    !.claude/settings.json) and declares two SessionStart hooks.
  - CAVEMAN ULTRA adopted on operator instruction after a dissent was overruled.
    tools/caveman_default.py carries RC's bytes; _BANNER is a FLEET CONTRACT and
    its sha256 is pinned in tests/test_session_hooks.py.
  - THE HAND-OFF WRITE GATE now refuses credentials and account paths.
  - EVERY API KEY IS A MACHINE ENV VAR. All five repos swept clean;
    tests/test_no_secret_literals.py keeps it that way over 160 tracked files.
  - ALL 66 INBOX NOTES ANSWERED, one note broadcast to all five, and
    from-RSC-verbatim/ reciprocated to four inboxes.
  - THE GOVERNOR IS CURRENT AND STILL INERT ON PURPOSE. winmutex 0b112a4f,
    slots 629c3d51, all three trees equal. NOTHING HERE ACQUIRES A SLOT.
    NEVER edit either shared file unilaterally and NEVER regenerate the digests
    from local disk to make a test pass. DEFAULT_ROOT stays
    C:\ProgramData\lw-loop\slots.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents flagged it and BOTH WERE WRONG. Do not "fix" it.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - PORT THE CLAIM GATE. RC's stop_claim_gate.py (550 lines) plus its 966-line
    test audit a session's claims against its own evidence. This tree has NO
    Stop hook and no claim gate - the one genuinely missing CLASS of guard.
    The tool is account-path clean; its TEST hardcodes an interpreter path at
    line 825 that must become sys.executable. Own session, 1500 lines.
  - Three smaller ports, all in moon_sync_inbox/from-RC-verbatim/tools/:
    pytest_guard.py (PostToolUse py_compile - this tree has ZERO PostToolUse
    hooks), edit_lint_check.py (but its glyph half must CALL
    tools/precommit_gate.py rather than restate the six codepoints), and two
    checks out of drift_guard.py - check_counted_claims and
    check_untracked_authored, about 60 lines, NOT the whole 481-line file.
  - DO NOT PORT md_guard_selector.py OR the ASCII source sweep. Triaged and
    rejected 2026-09-07: docs-guards.yml already derives its guard set from
    git ls-files with an unbucketed hard-fail, and ci.yml already sweeps tracked
    source with --expect-count. RC's ASCII file is a ratchet over a frozen
    50-file baseline, strictly weaker, and RC's own docstring credits this tree.
  - agents/pity_engine/CHANGELOG.md STILL needs an entry for the exclusive bind.
  - A guard for the ONE checkable shape of prose falsity: a document asserting a
    property of a file that the file itself contradicts.
  - Two guards still claim more than they sweep. tests/test_ports.py scans only
    .py via ast.parse - correct mechanism, real gap for prose. tests/
    test_goal_spec.py denylists four literals plus one material name while
    GOAL_SPEC section 3 carries more; derive the forbidden set FROM the spec's
    own unverified stamps.
  - tests/test_docs_consistency.py derives its PREDICATE from git ls-files but
    still enumerates its CORPUS with rglob over docs/.
  - Close the fan-content evidence hole. Three first-party PDFs were never read
    and their URLs are recorded NOWHERE. pdftotext 4.00 IS on PATH.
  - Row-scoped provenance for data/costs/. Schema BEFORE the first row.
  - Observe the seed-team cost table in game. The web-sourced figures are
    UNVERIFIED and must not enter data/.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - NOTE FILENAME TIMESTAMPS ARE FICTIONAL and drift per sender by up to SIX
    HOURS, growing through a session. Sorting by filename inverts real order. A
    sibling filed a claim that this tree carried the old slots.py; it was
    written nine minutes BEFORE the commit that fixed it. Right when written,
    stale when filed. Sort by `stat -c '%y'` when order decides anything.
  - AN UNWIRED SCRIPT IS NOT A WATCHER. A correct script connected to no hook is
    not the capability it looks like. Ask what FIRES a thing, then prove it by
    EXECUTING the declared command, not by resolving its path.
  - A VERBATIM FILE CAN BE STALER THAN THE PROSE DESCRIBING IT. RC's hook-gate
    test arrived without the require-env flag RC's own later note calls
    load-bearing. Diff the ASSERTIONS, never the filenames.
  - NEVER ADOPT A SIBLING'S CONFIG UNREAD. RC's .claude/settings.json carries 11
    hardcoded C:\Users\<account>\ paths. Copying it would have re-opened the
    machine-identity leak this tree closed. Adopt the SHAPE; copy bytes only
    where the bytes ARE the contract, as with the CAVEMAN _BANNER.
  - A DETECTOR'S OWN PATTERN TRIPS ITS OWN SWEEP. An account-path regex is an
    account-shaped path. Fix it at the SOURCE - assemble the pattern from a
    named segment - rather than allowlisting a chunk of regex, which is
    unreadable and goes unstable the moment the line is edited.
  - A FIXTURE THAT PLANTS THE REAL ACCOUNT NAME IS THE LEAK IT TESTS FOR. Use an
    obviously invented one.
  - A GATE THAT QUOTES WHAT IT CAUGHT PUBLISHES IT while refusing to publish it.
  - ZERO OUT OF ZERO READS AS A PASS. A checker that matches nothing reports
    "0 missing" and looks clean. Every checker must return (checked, offenders)
    and assert the CHECKED COUNT before the offender list.
  - A SKIPPED TEST IS A GREEN TICK. RSC_REQUIRE_HOOK_GATE=1 turns an
    UNMEASURABLE MACHINE into a failure - NOT an unconfigured clone, which
    passes 12 of 12 because the fixture arms its own throwaway repo.
  - WITHOUT A POSITIVE CONTROL, A GATE THAT REFUSES EVERYTHING PASSES BOTH
    REFUSAL TESTS, and the catastrophically broken version looks safest.
  - A FORCE-PUSH DOES NOT PURGE OBJECTS FROM GITHUB, and an object purge is true
    only at the instant it is measured. Rewrite locally, DELETE the remote,
    recreate, push clean, then verify FROM THE SERVER.
  - AGENT WORKTREES CAN FORK FROM A STALE HEAD. Run `git worktree list` after
    dispatching and check the SHA. Remove a worktree only after its work is
    merged AND pushed - charter v4: durable means it survives the removal.
  - MUTATION-TEST EVERY GUARD YOU ADD, and check the mutant is not EQUIVALENT.
    Break it on a SCRATCHPAD COPY, never the tracked tree.
  - A GUARD THAT OVERSTATES ITS REACH IS WORSE THAN A MISSING ONE, and a
    cross-repo guard that reads a sibling tree GOES SILENT, NOT RED. Pin against
    a constant in your own file.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS silently, and
    .gitattributes eol=lf means the INDEX hides it. Write BYTES, or use
    Write/Edit, or cp for a byte-exact copy.
  - A HEREDOC PLUS A NON-RAW PYTHON STRING MANGLES BACKSLASHES and can fail to
    parse, so NOTHING runs while the surrounding command still reports success.
    Use a real file for any script containing backslashes.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. Redirect to a file.
  - xargs SPLITS ON WHITESPACE. Use -0 with ls-files -z, and assert the SCANNED
    count, never that the list was non-empty.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - MSYS rewrites the lone
    /F into F:/. Write `taskkill //F //PID <pid>`. It fails SILENTLY when
    redirected.
  - `python3` here RUNS but has NO pytest - it is the Store alias.
    `command -v python3` SUCCEEDS. Probe CAPABILITY, not existence.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. Find the SHARED INPUT and test
    THAT.
  - A SWEEP NEEDS TWO GUARDS: one that the bad thing is gone, one that the
    LEGITIMATE NEIGHBOURS SURVIVED.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809.
  - computer-use minimizes all windows when it initialises.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no
en-dashes, no smart quotes. Never add a Co-Authored-By or Claude-Session trailer,
and never file its absence as a defect. Put the EXPECTED DURATION in every
background task name. Verify against ground truth before asserting anything is
done, fixed, broken or missing, and report the exact result observed with counts.
Never trust a subagent's claim about test counts, green CI or file existence
without an independent probe.
```
