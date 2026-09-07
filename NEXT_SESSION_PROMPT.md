# Next session prompt

The fenced block below is the hand-off. It is the SOURCE OF TRUTH for the
`/done` ritual sections 9 and 11, it is what `tools/publish_next_session.py`
reads to write the Desktop backup, and it is what the operator pastes into a
cold session. There must be exactly ONE fenced block in this file.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

FIRST ACTION IN A FRESH CLONE: python scripts/install_hooks.py
core.hooksPath is local config and is NOT cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires.

THE INBOX IS SESSION READING, AND SO ARE ITS SUBDIRECTORIES.
  python scripts/watch_inbox.py            what is new since the last mark
  python scripts/watch_inbox.py --all      everything
  python scripts/watch_inbox.py --mark     record the current set as read
The watcher fires at SessionStart AND on every operator message via
UserPromptSubmit, so a note landing MID-SESSION reaches you without running
anything. It prints nothing when nothing is unread. Mark only what you triaged.

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

OUTPUT RULES, all in CLAUDE.md:
  - Responses under 500 output tokens. Long output goes to a file.
  - CAVEMAN ULTRA is the default CHAT dialect. Terseness is for chat ONLY:
    paths, commands, code, identifiers and every committed artefact stay
    byte-exact. Answer clarifying questions in plain English.
  - Speak in chat only for something to RULE ON or be NOTIFIED of.

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
DO NOT ADD -q TO ANY OF THOSE. pytest.ini addopts ALREADY carries -q. A second
-q makes -qq and SUPPRESSES the summary line, so you get a wall of dots and no
count and cannot report what you did not see.

=====================================================================
THE TREE IS CODENAMED NOW. THIS IS THE BIG CHANGE SINCE THE LAST HAND-OFF.
=====================================================================

This repository is PUBLIC - the GitHub API returns "private": false, measured
2026-09-07. It had been flipped public with no name scrub, and its tracked files
named six sibling projects of the same operator's 451 times across 74 files.

Every one of them is now an opaque codename, Sibling-A through Sibling-F. The
resolution map is ops/moon_sync_repos.json, which is GITIGNORED, and NOTHING
TRACKED RESOLVES A CODENAME TO A PROJECT. Do not put the mapping in a tracked
file, a commit message, or a doc. The inbox is gitignored and is where sibling
correspondence lives.

STATE THE SEVERITY THE WAY THE OPERATOR DID, NOT HIGHER. The ruling was "they
are not secrets, it just needs to be altered to be ambiguous". This removed a
plain-text roster from a public repo. It does NOT make the fleet unlearnable to
anyone who already knows it. An over-claimed rationale outlives a wrong line of
code, and this tree tracks that failure class hardest.

LETTERS ARE DELIBERATELY NOT MONOTONIC. core/ports.py publishes four sibling
block ranges as literals, so an assignment ordered by port or alphabet would let
one confirmed hit de-anonymise the whole fleet. Do not "tidy" them into order.

THE DELETE-AND-RECREATE IS AGREED AND NOT YET RUN. The working tree is clean but
27 of 64 commit MESSAGES still name a sibling and prior blobs stay retrievable
by SHA. Measured here: 0 refs/pull/*/head, 0 stars, 0 forks, 0 issues.
THE ORDERING TRAP, and it is the whole point: THE SCRUB COMMIT PUBLISHES A DIFF
THAT IS THE MAPPING. Scrub, push, then delete would publish the key, and
deleting afterwards does not unpublish it. The order is: rewrite history so no
commit ever held a sibling name AND no commit is the scrub itself, then delete
the remote, recreate under the same name, push once. The round was put to the
fleet and had not answered when this was written.

STATE, measured 2026-09-07 at commit 06ce247 (report what YOU observe, never
these numbers):
  licence QA                      41 passed
  docs QA                         23 passed
  scripts/qa_companion.py         17 passed, 0 failed, 1 skipped
  ruff                            All checks passed
  pytest tests                    1195 passed, 1 skipped
  pytest agents/pity_engine       80 passed
  shell node --test               52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 32 source files
  git worktree list | tail -n +2 | wc -l                    0
  git branch -a                   main + remotes/origin/main only
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. CI pins 3.11 and passes.

  MYPY NOW CHECKS 32 FILES AND ITS Success IS STILL NOT EVIDENCE ABOUT THE REST.
  files= covers core/ engines/ ingest/ agents/pity_engine/ tools/ only. tests/,
  scripts/, surface/, ops/, headless/ and conftest.py are DARK.
  tests/test_mypy_scope.py goes red if a root leaves the list.

SETTLED. DO NOT REDO:
  - THE FORK-PR RISK IS CLOSED. approval_policy is "first_time_contributors".
  - THE HOOK GATE IS PROVEN ON A REAL RUNNER, ran not skipped.
  - THE WATCHER FIRES, at SessionStart AND UserPromptSubmit.
  - CAVEMAN ULTRA adopted. _BANNER is a FLEET CONTRACT, sha256 pinned in
    tests/test_session_hooks.py. All four sibling names near it were in the
    docstring ABOVE it; the banner bytes are unchanged.
  - EVERY API KEY IS A MACHINE ENV VAR. tests/test_no_secret_literals.py.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents flagged it and BOTH WERE WRONG. It is NOT the operator's UID.
  - THE OPERATOR UID MUST NEVER ENTER THIS TREE. A sweep for any nine-digit run
    hashing to it found 0, and the checker fired on a planted control first.
  - WEBCACHES IS UNDER THE GAME INSTALL, NOT THE USER PROFILE.
    tests/test_wish_authkey_paths.py pins the candidate ORDER, not membership.
  - THE FOUR ROOT-WALKING GUARDS ARE FIXED, proven against REAL worktrees.
  - THE SCRUB IS GUARDED NOW. tests/test_no_sibling_names.py asserts the
    property a one-off sweep could only assert once. Its corpus is git ls-files,
    it is case-insensitive, it strips comment markers so a WRAPPED name cannot
    hide, and its positive controls are the four real escapes.
  - THE SCRUB'S OWN COMPLETENESS CLAIM WAS REFUTED ONCE ALREADY. "Zero hits" was
    wrong by four, and they shipped green because nothing guarded the property.
    Do not restate a sweep as complete without a tracked guard behind it.
  - core/atomic_io.py NO LONGER TRANSLATES NEWLINES, and the five sibling
    writers are fixed with an ast guard against a sixth.
  - THE PROVENANCE SCHEMA EXISTS. core/provenance.py, before any row landed.
  - NOELLE IS FOUND. 09:07:38.533Z, and the old "not found" record is superseded
    in place rather than rewritten.
  - THE SLOTS RE-PIN IS CLOSED. All three carriers hash 71fa2a68, measured on
    three disks by three parties plus a fourth that vendors none of them.
  - THE WATCHER MUTATION ARMS ARE SOUND, including against the nanosecond key.
    Re-measured after a sibling warned about float os.utime; already correct.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - THE OTHER NINE OBSERVATIONS IN THE CAPTURE STORE HAVE NOT BEEN RE-CHECKED.
    Only line 9 was. Every other one was recorded by the same process that got
    line 9 wrong. Do it before any of them is trusted into data/, and before any
    video segment is pruned.
  - THE PROVENANCE SCHEMA HAS NO PRODUCER. Nothing writes a row yet, so it has
    never met a real value. The first consumer is the next real slice.
  - ENKA still needs Adventure Rank 10 AND an OPEN showcase. ingest/enka_client.py
    has never met a real profile. Only route to a real roster rather than an OCR'd one.
  - THE CROSS-CARRIER PARITY ARM DOES NOT EXIST. SHARED_SHA256 hashes only this
    repo's disk, so the suite reads green while the contract is divergent.
  - swept_files LIVES IN A TEST MODULE and four guards import it from there.
    tests/conftest.py is its home. Small, self-contained.
  - THE UN-CLEARABLE-WITHDRAWAL CHECK HAS NOT BEEN RUN HERE. One command, not a
    test: report, acknowledge, report again.
  - THE "Legion box" MACHINE NAME NEEDS AN OPERATOR RULING. Only guessable token
    left. It is a machine name, not a project name, so it was out of scope.
  - THE BOOTSTRAP OUTPUT DIRECTORY UNDER data/ IS NOT GITIGNORED, and an account
    snapshot is exactly the shape of thing that must never be committed.
  - BRING ONE MORE ROOT INTO MYPY. surface/ 1 error, headless/ 3, ops/ 8,
    scripts/ BLOCKED by a duplicate-module-name refusal needing __init__.py.
  - THE CLAIM GATE IS LANDED BUT DELIBERATELY UNWIRED. TRANSCRIPT_PATH_KEY and
    BLOCK_EXIT_CODE are GUESSES and the false rate was measured by the agent
    that wrote it.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - A CORPUS IS A SNAPSHOT, AND A LONG SESSION MOVES THE TREE UNDER IT. Two
    parallel scrub slices each reported their half complete and both were
    telling the truth; a tree-wide sweep after the merge still found 11 hits in
    three files that were on NEITHER write-list, because the session's own
    merges created or rewrote them after the corpus was built. One was a comment
    the merger itself had authored. RE-DERIVE THE CORPUS AT MERGE TIME.
  - A LINE-BASED GREP CANNOT SEE A WRAPPED CALL OR A WRAPPED NAME. Two of seven
    "CRLF offenders" were false positives that already passed newline= on the
    CONTINUATION LINE, and 16 sibling names hid across a wrap. Parse with ast,
    or use whitespace-tolerant patterns. A per-name grep also missed 183 BARE
    INITIALS and undercounted the corpus by 1.79x.
  - A SHAPE ARM READS AS COVERAGE AND IS NOT. It pins the FORMAT of a key, never
    its INPUT. A literal st_mtime_ns substitution died on a "digest is 64 hex"
    arm; hashing the metadata restored the shape and walked straight past it.
  - AN ARM THAT VARIES CONTENT VARIES MTIME, SIZE AND CONTENT AT ONCE, so it
    pins none of them. Edit IN PLACE at CONSTANT BYTE LENGTH and RESTORE the
    timestamp. Restore with os.utime(path, ns=(...)) - a FLOAT pair does not
    restore st_mtime_ns - and assert the mtime actually MOVED before restoring,
    or the arm is unarmed and passes for the wrong reason.
  - ASSERT THE MUTATION SITE MATCHED BEFORE TRUSTING A MUTANT VERDICT. A quoted
    heredoc collapsed a NUL escape, the search matched ZERO times, the mutation
    was a silent no-op, and the harness was about to report SURVIVED. A broken
    harness is indistinguishable from a weak arm.
  - A CAVEAT THAT IS CORRECT CAN STILL BE THE WRONG EXPLANATION. "Not found at
    1 fps" was true and irrelevant: the recorded window was 13 minutes past the
    event because a banner reading of 20/20 was attributed to a timestamp where
    it actually read 10/20. A plausible explanation stops the search.
  - A RESIDUAL INFERENCE CHANNEL IS NOT LESS OF ONE FOR BEING A FACT ABOUT A
    PORT. After every name was codenamed, core/ports.py still identified a
    sibling by naming a third-party API whose vendor name is the first word of
    that project's name.
  - A GUARD THAT ASKS "DOES EVERYTHING EXIST?" FAILS GREEN ON A LEFTOVER
    WORKTREE. A duplicate tree only ADDS files, so a "does anything match?"
    guard goes falsely RED and announces itself while an existence guard goes
    falsely GREEN and never does. Run the worktree test in BOTH directions.
  - A ROOT-WALKING GUARD CANNOT SEE A NESTED CHECKOUT, but one whose corpus is
    git ls-files is STRUCTURALLY IMMUNE, because git does not descend into one.
    34 of 39 modules here were immune for exactly that reason. A linked
    worktree's .git is a FILE, so test with .exists() and not .is_dir().
  - RENAMING A NEEDLE A TEST MATCHES ON TURNS A REAL GUARD VACUOUS. That is
    worse than the leak the rename was for.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS SILENTLY, and
    .gitattributes eol=lf HIDES it from every diff. read_text converts it BACK
    on the way in, so a broken writer looks correct - ASSERT ON RAW BYTES. A
    caller who supplies CRLF gets CR-CR-LF.
  - A HEREDOC MANGLES BACKSLASHES EVEN WHEN QUOTED. Use a real file, written
    with the Write tool, for any script containing one.
  - AGENT WORKTREES FORK FROM THE SESSION'S ORIGINAL HEAD, not from current
    main. An agent dispatched to measure recent work may not have the commit
    that carries it, and would measure an empty file as a pass. State the commit
    and have the agent verify it is on it.
  - core.hooksPath IS SHARED GIT CONFIG and points at the MAIN checkout, so a
    passing commit inside a worktree is NOT proof the hook ran on those bytes.
  - THE DOCS GUARD FIRES ON A BACKTICKED PATH THAT IS NOT TRACKED. It caught two
    of this session's own ledger and roadmap lines. Name a gitignored path in
    plain text.
  - TESSERACT RETURNS A CONFIDENT ZERO ON STYLISED GAME TEXT. Use OCR to NARROW
    a corpus, never to conclude an absence from it.
  - NOT FOUND AT A SAMPLED RATE IS NOT NOT PRESENT. Report the rate in the same
    sentence as any negative taken over a recording.
  - AN IN-PROGRESS .mp4 WILL NOT OPEN - "moov atom not found". Matroska decodes
    to the last complete cluster.
  - THE GAME HOLDS ITS CACHE FILES LOCKED. Snapshot first, scan the snapshot.
  - A TRUNCATED CREDENTIAL LOOKS LIKE AN EXPIRED ONE.
  - A WRONG PATH AND A MISSING ONE CAN PRINT THE SAME SENTENCE.
  - MATCHING A DAEMON BY SUBSTRING OVER ITS WHOLE COMMAND LINE IS WRONG. Match
    argv[1] only.
  - A GREEN LOCAL GATE ON WINDOWS SAYS NOTHING ABOUT THE LINUX RUNNER. Guard
    with `if sys.platform == "win32":` - mypy NARROWS on that and hasattr does
    not; use getattr(mod, "NAME", 0).
  - A TEST OF AN ORDERING MUST NOT READ THE REAL ENVIRONMENT.
  - A GUARD CAN REPORT A NUMBER THAT IS NOT THE NUMBER IT NAMES. mypy's tail
    line starts with the ERROR count when there are errors, not the file count.
  - VERIFY AN ENVIRONMENT FIX BY DELETING THE ENVIRONMENT.
  - WITHOUT A POSITIVE CONTROL, A CLEAN RESULT AND AN UNARMED CHECK LOOK
    IDENTICAL. This is the single most productive rule in this tree.
  - TWO NUMBERS CONSISTENT WITH A HYPOTHESIS ARE NOT EVIDENCE FOR IT.
  - ZERO OUT OF ZERO READS AS A PASS. Return (checked, offenders) and assert the
    CHECKED COUNT before the offender list.
  - A GUARD CAN BE WRONG IN THE DIRECTION OF FALSE RED.
  - A WRONG RATIONALE OUTLIVES A WRONG LINE OF CODE.
  - A FINDING SENT ONWARD IS NOT A FINDING APPLIED TO YOURSELF.
  - AN ARM THAT PROVES A THING APPEARS IS NOT THE ARM THAT PROVES IT CAN GO AWAY.
  - BYTES-EQUAL IS NOT THE SAME FACT AS DID-NOT-WRITE.
  - THE WATCHER'S STDOUT IS A PRIVILEGED SURFACE. Names, counts and digests -
    NEVER a payload byte. An absence assertion on ONE string is defeated by
    truncation; assert over every WINDOW of the payload.
  - THE STANDING REF CHECK IS `git branch -a`, NOT `git worktree list`.
  - A FORCE-PUSH DOES NOT PURGE OBJECTS FROM GITHUB, and refs/pull/N/head is
    PERMANENT and survives a rewrite. A sibling found 13 of them, one carrying a
    pre-rotation credential. This repo has 0, measured.
  - NOTE FILENAME TIMESTAMPS ARE FICTIONAL and drift by up to SIX HOURS.
  - AN UNWIRED SCRIPT IS NOT A WATCHER. Prove it by EXECUTING the command.
  - NEVER ADOPT A SIBLING'S CONFIG UNREAD. Adopt the SHAPE; copy bytes only
    where the bytes are the contract.
  - A DETECTOR'S OWN PATTERN TRIPS ITS OWN SWEEP.
  - A GATE THAT QUOTES WHAT IT CAUGHT PUBLISHES IT.
  - A SKIPPED TEST IS A GREEN TICK. RSC_REQUIRE_HOOK_GATE=1.
  - SendMessage MAY BE DISABLED. Report the file list in chat instead.
    MERGE_TODO.md is GITIGNORED now - it was committed once and then collided
    add/add with the next slice twice.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. Redirect to a file. A
    chained `cmd | grep && cd ..` silently skips the cd when grep matches
    nothing, and the next command runs in the wrong directory.
  - xargs SPLITS ON WHITESPACE and this repo's path contains a space.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - write `taskkill //F
    //PID <pid>`. Inside a PYTHON subprocess call it is `/F` again.
  - `python3` here RUNS but has NO pytest - it is the Store alias.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. Find the SHARED INPUT.
  - A SWEEP NEEDS TWO GUARDS: the bad thing is gone, the neighbours survived.
  - Ports are owned by core/ports.py. This project holds 8790-8809.
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
