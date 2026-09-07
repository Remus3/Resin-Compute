# Next session prompt

Paste the fenced block below into a cold session. It is the SOURCE OF TRUTH for
the hand-off; `tools/publish_next_session.py` reads this file rather than a
retyped copy, so the Desktop backup and the printed block cannot disagree.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

FIRST ACTION IN A FRESH CLONE: python scripts/install_hooks.py
core.hooksPath is local config and is NOT cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires.

THE INBOX IS SESSION READING, AND SO ARE ITS SUBDIRECTORIES.
  python scripts/watch_inbox.py            what is new since the last mark
  python scripts/watch_inbox.py --all      everything
  python scripts/watch_inbox.py --mark     record the current set as read
THE WATCHER NOW FIRES TWICE: at SessionStart AND on every operator message via
UserPromptSubmit, so a note landing MID-SESSION appears in your context without
you running anything. It prints nothing when nothing is unread.
THE WATERMARK IS HONEST AS OF 2026-09-07. Keep it that way: mark only what you
actually triaged. Notes arrive DURING a session - three did on 2026-09-07 - so
re-check the listing immediately before you --mark, or you will mark a note you
never read. That happened twice on 2026-09-07 and was corrected retroactively.

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
    paths, commands, code, identifiers and every committed artifact stay
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
DO NOT ADD -q TO ANY OF THOSE. pytest.ini addopts ALREADY carries -q. A second -q
makes -qq and SUPPRESSES the summary line, so you get a wall of dots and no count
and cannot report what you did not see.

STATE, measured 2026-09-07 at commit 2b8fcbe (report what YOU observe, never
these numbers):
  licence QA                      41 passed
  docs QA                         23 passed
  scripts/qa_companion.py         16 passed, 0 failed, 2 skipped
  ruff                            All checks passed
  pytest tests                    1087 passed, 1 skipped
  pytest agents/pity_engine       80 passed
  shell node --test               52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 27 source files
  RSC_REQUIRE_HOOK_GATE=1 pytest tests/test_hook_gate.py    12 passed
  git worktree list | tail -n +2 | wc -l                    0
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. CI pins 3.11 and passes, so
  the tree is not unverified on 3.11 - the LOCAL reading is the narrow one. The
  3.11 declaration is load-bearing rather than cosmetic: it is what makes numpy's
  PEP 695 stub a syntax error, which is what mypy.ini's exclude= exists for.

  MYPY CHECKS 27 OF 92 TRACKED .py AND ITS Success IS NOT EVIDENCE ABOUT THE
  REST. files= covers core/ engines/ ingest/ agents/pity_engine/ tools/ only.
  tests/, scripts/, surface/, ops/, headless/ and conftest.py are DARK. Never
  cite its Success as evidence about code outside those roots.
  tests/test_mypy_scope.py goes red if a root leaves the list.

SETTLED. DO NOT REDO:
  - THE FORK-PR RISK IS CLOSED. approval_policy is "first_time_contributors".
  - THE HOOK GATE IS PROVEN ON A REAL RUNNER, 12 passed, ran not skipped.
  - THE WATCHER FIRES, at SessionStart AND UserPromptSubmit, and is proven to
    fire by a test that EXECUTES each declared command.
  - CAVEMAN ULTRA adopted on operator instruction. _BANNER is a FLEET CONTRACT
    and its sha256 is pinned in tests/test_session_hooks.py.
  - EVERY API KEY IS A MACHINE ENV VAR. tests/test_no_secret_literals.py keeps it
    that way over 160+ tracked files.
  - THE GOVERNOR IS CURRENT AND STILL INERT ON PURPOSE. NOTHING HERE ACQUIRES A
    SLOT. Never edit either shared file unilaterally and never regenerate the
    digests from local disk to make a test pass.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents flagged it and BOTH WERE WRONG. Do not "fix" it.
  - THE VERBATIM DROP IS GONE AND THAT IS CORRECT. RC deleted
    moon_sync_inbox/from-RC-verbatim/ from all four sibling trees after 19 of its
    48 files were found carrying the operator's account name. Containment here
    was MEASURED: 0 tracked files, 0 commits by pickaxe, 0 additions. Do not go
    looking for it and do not ask for a re-drop of FILES - Lanternlight asked the
    channel for prose instead and this tree agreed.
  - THE PICKAXE CHECK WAS RUN, ARMED, 2026-09-07. Account name 0 across every
    ref. The C:\Users, AppData and Claude-Session hits are all this tree's own
    detectors and the hook that strips the trailer; every UUID-shaped id in them
    was intersected with the 1567 real session ids on this machine, giving 0.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - THE CLAIM GATE IS LANDED BUT DELIBERATELY UNWIRED. tools/stop_claim_gate.py,
    115 arms, no Stop hook declared, .claude/settings.json untouched. Three build
    rounds and three adversarial passes; the producer's own un-adjudicated
    measurement is 55.5 PERCENT FALSE over 317 real transcripts. Before arming
    it: (1) an INDEPENDENT pass must measure the rate, because 55.5 was measured
    by the agent that wrote the chaining, (2) somebody must CLASSIFY the residual
    false positives - nobody has, and that decides whether a fourth mechanism is
    warranted or the gate is at its ceiling, (3) TRANSCRIPT_PATH_KEY and
    BLOCK_EXIT_CODE are GUESSES recorded in the module's OPEN section, and arming
    on an unverified stdin key gives you a gate that exits cleanly and checks
    nothing.
  - RC OWES THE CLAIM-GATE SPEC, asked by note 2026-09-07, unanswered. Six
    questions: taxonomy, evidence model, recognisers, what it reads and how, the
    verdict contract, and its two published lessons restated.
  - BRING ONE MORE ROOT INTO MYPY. Cost measured by adding each alone:
    surface/ 1 error, headless/ 3, ops/ 8, scripts/ BLOCKED by a
    duplicate-module-name refusal needing an __init__.py first. mypy.ini records
    each. A small self-contained slice.
  - A guard for the ONE checkable shape of prose falsity: a document asserting a
    property of a file that the file itself contradicts.
  - tests/test_goal_spec.py denylists four literals plus one material name while
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

  - A HEREDOC MANGLES BACKSLASHES EVEN WHEN QUOTED. It bit FIVE times on
    2026-09-07. Once it silently turned a regex character class [\\/] into [\/],
    a class matching forward slash only, so a leak sweep scanned every Windows
    path and reported CLEAN. The positive control caught it and nothing else
    would have. Use a real file for any script containing backslashes.
  - WITHOUT A POSITIVE CONTROL, A CLEAN RESULT AND AN UNARMED CHECK LOOK
    IDENTICAL. Prove every category fires on a planted line BEFORE you trust a
    zero. This is the single most productive rule in this tree.
  - MUTATION-TEST EVERY GUARD, AND EXPECT EQUIVALENT MUTANTS. Four were found on
    2026-09-07. Dropping a leading ^ is equivalent when the code calls re.match.
    A mutant nothing catches means DEAD CODE - delete it rather than document it.
    One such piece of dead code had a docstring calling it load-bearing.
  - A GUARD CAN BE WRONG IN THE DIRECTION OF FALSE RED. tests/test_mypy_scope.py
    compared mypy's FILESYSTEM walk against a git-tracked corpus, so any unstaged
    .py under a covered root reddened it. A guard that reddens for honest work in
    progress is one a contributor learns to wave through.
  - ZERO OUT OF ZERO READS AS A PASS. Every checker returns (checked, offenders)
    and every test asserts the CHECKED COUNT before the offender list.
  - A CHECK THAT CANNOT FIRE IS WORSE THAN A MISSING ONE. A finding name in the
    claim gate's own contract tuple emitted 0 findings over 1877 checked claims
    across 316 transcripts. It was deleted.
  - A WRONG RATIONALE OUTLIVES A WRONG LINE OF CODE, because it answers the next
    reader's question before they ask it. Clockspeed's watcher carried a
    paragraph defending the name key whose central claim was exactly inverted.
    Delete such a paragraph rather than rewording it - a reword keeps the
    authority of the original.
  - A CONFIG COMMENT CAN EXPLAIN THE WRONG LINE. mypy.ini's reasoned comment
    covered exclude= (5 files) while files= (64 files) had no rationale at all, so
    a reader found reasoning beside the wrong mechanism and stopped looking.
  - BYTES-EQUAL IS NOT THE SAME FACT AS DID-NOT-WRITE. An atomic write producing
    identical content still moves the mtime. Assert both.
  - THE WATCHER'S STDOUT IS A PRIVILEGED SURFACE. It is injected into a session
    with the harness's authority before any judgement is applied, so it may carry
    names, counts and digests and NEVER a payload byte.
  - THE STANDING REF CHECK IS `git branch -a`, NOT `git worktree list`. Two stale
    worktree branches were found as refs with no worktree. The branch outlives
    the worktree, and such a branch is exactly what resurrects a purged blob.
  - A FORCE-PUSH DOES NOT PURGE OBJECTS FROM GITHUB, and an object purge is true
    only at the instant it is measured. Rewrite locally, DELETE the remote,
    recreate, push clean, verify FROM THE SERVER.
  - NOTE FILENAME TIMESTAMPS ARE FICTIONAL and drift per sender by up to SIX
    HOURS. Sort by `stat -c '%y'` when order decides anything.
  - AN UNWIRED SCRIPT IS NOT A WATCHER. Ask what FIRES a thing, then prove it by
    EXECUTING the declared command, not by resolving its path.
  - NEVER ADOPT A SIBLING'S CONFIG UNREAD. RC's .claude/settings.json carries 11
    hardcoded account paths. Adopt the SHAPE; copy bytes only where the bytes ARE
    the contract, as with the CAVEMAN _BANNER.
  - A DETECTOR'S OWN PATTERN TRIPS ITS OWN SWEEP, and a fixture planting the REAL
    account name is the leak it tests for. Use an obviously invented one.
  - A GATE THAT QUOTES WHAT IT CAUGHT PUBLISHES IT.
  - A SKIPPED TEST IS A GREEN TICK. RSC_REQUIRE_HOOK_GATE=1 turns an UNMEASURABLE
    MACHINE into a failure - NOT an unconfigured clone, which passes 12 of 12.
  - AGENT WORKTREES FORK FROM THE PRE-DISPATCH HEAD. Run `git worktree list`
    after dispatching and check the SHA. A builder will not see a commit you made
    seconds before dispatching it.
  - SendMessage MAY BE DISABLED. If a constraint arrives after you dispatch, you
    cannot forward it - write it to a MERGE_TODO file and apply it at the seam.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS silently, and
    .gitattributes eol=lf means the INDEX hides it. Write BYTES, or use
    Write/Edit, or cp for a byte-exact copy.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. Redirect to a file.
  - xargs SPLITS ON WHITESPACE and this repo's path contains a space. Use -0 with
    ls-files -z, and assert the SCANNED count.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - MSYS rewrites the lone
    /F into F:/. Write `taskkill //F //PID <pid>`. It fails SILENTLY when
    redirected.
  - `python3` here RUNS but has NO pytest - it is the Store alias. Probe
    CAPABILITY, not existence.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. Find the SHARED INPUT and test
    THAT. Two agents were both wrong about the Enka example UID.
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
without an independent probe - two subagent claims were refuted on 2026-09-07 by
a probe that took one command each.
```
