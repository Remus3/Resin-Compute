# Next-session prompt

The fenced block below is the hand-off. It is the SOURCE OF TRUTH: the `/done`
ritual prints it inline and `tools/publish_next_session.py` reads it to write
the Desktop backup, so it is written here once and never retyped. Exactly one
fenced block, 7-bit ASCII, self-contained - the next session boots cold.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

THE REPOSITORY IS STILL PRIVATE. `gh repo view` returns visibility PRIVATE.
Flipping it is the OPERATOR'S action and it is the LAST one. Description and 17
topics were set 2026-09-06 and CI/README are ready, so the next thing to happen
is the operator's decision, not more fixing. Badges are live in README.md and
will render broken to anyone without access until the flip - that is expected.

BOOTSTRAP, in this order:
  CLAUDE.md, README.md, ROADMAP.md, docs/LEDGER.md, docs/SPEC_SCAFFOLD.md,
  docs/adr/README.md, and `git log --oneline -12`.
SPEC_SCAFFOLD.md is the authoritative build contract and carries every verified
domain constant. Do NOT re-derive gacha numbers from memory or a web search, and
do not "fix" them against the originating brief, which was wrong in three places
that are now regression-tested. The three: the 50/50 has been 55.000%
consolidated since 5.0, the weapon soft-pity ramp saturates at pull 77 under a
7% increment, and 1.600% is 1/E[wishes] rather than a per-wish Bernoulli value.

READ THE "Session default" SECTION OF CLAUDE.md BEFORE DISPATCHING ANYTHING.
The default shape is orchestrated, multi-agent, self-adjudicating and
self-adversarial. The main thread reads, plans, dispatches, merges and reports.
Seven roles live in .claude/agents/, the protocol is /orchestrated-run, the
reasoning is ADR-007. WORKTREE-ISOLATE EVERY AGENT THAT WRITES: pass
isolation: "worktree" on the Agent call - then READ THE WORKTREE TRAP BELOW,
because it cost 32 wasted minutes on 2026-09-06.

RUN THE THREE QA GATES FIRST, then the standard ones. Each QA gate caught a real
defect on its first run and they are cheap:

  1. python -m pytest tests/test_licence_posture.py
  2. python -m pytest tests/test_docs_consistency.py
  3. python scripts/qa_companion.py

  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run

Run the two Python suites SEPARATELY. Never `pytest .` from the root.
DO NOT ADD -q TO ANY OF THOSE. pytest.ini addopts ALREADY carries -q. A second
-q makes -qq and SUPPRESSES the summary line, so you get a wall of dots and no
count, and you cannot report what you did not see. Bitten AGAIN on 2026-09-06.

STATE, verified 2026-09-06 at commit a326851 (report what YOU observe, never
these numbers):
  licence QA                      33 passed
  docs QA                         23 passed
  scripts/qa_companion.py         16 passed, 0 failed, 2 skipped
  ruff                            All checks passed
  pytest tests                    813 passed, 1 skipped
  pytest agents/pity_engine        76 passed
  shell node --test                52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 23 source files
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. Nothing has been verified
  under 3.11. This predates the current work and was deliberately not touched -
  decide whether to align the declaration or the runtime, do not assume either.

THE CONCURRENCY GOVERNOR LANDED, AND IT IS INERT ON PURPOSE.
ops/loop/slots.py and ops/loop/winmutex.py are BYTE-IDENTICAL-BY-CONTRACT with
Legion Wallpaper and Riot Commander, pinned by digest in
tests/test_loop_concurrency.py. core.config.MAX_CONCURRENT_LANES = 3.
NOTHING IN THIS TREE ACQUIRES A SLOT. headless/runner.py is a job runner, not a
Claude-executor loop. This is a PARITY CONTRACT JOINED AHEAD OF NEED.
  - NEVER edit either shared file unilaterally, and NEVER regenerate the digests
    from local disk to make a test pass. That launders a drift into "agreed".
    Change on one side, hand the other two the exact bytes, all three re-hash
    their OWN disks, pin everywhere in the same round.
  - When you build an executor loop, wrap each cycle in
    slots.hold(...) and treat SlotTimeout as a FAILED CYCLE, never as permission
    to proceed unslotted. The width comes from core.config, not from a literal.
  - DEFAULT_ROOT stays C:\ProgramData\lw-loop\slots. A second bucket is worse
    than no governor: both look healthy and neither bounds the other.

OPEN WITH THE SIBLINGS - awaiting replies in moon_sync_inbox/:
  - THE hold() RELEASE-PATH LEAK. A real defect in the byte-identical shared
    file, found here and reported to both siblings 2026-09-06. Under Windows
    contention slot.unlink() loses an ERROR_SHARING_VIOLATION race against a
    waiter's read, `except OSError: pass` swallows it, AND THE RELEASE IS LOGGED
    ANYWAY. Worse and deterministic: a leaked lock whose holder is STILL ALIVE
    is UNREAPABLE, because both of is_stale's fast arms answer "not stale" - so
    the fail-open valve is disarmed by exactly the case that causes the leak,
    and only the 4.5-hour age arm clears it. RSC does not acquire, so RSC is not
    exposed; LW and RC both call hold() against the live bucket. Their call.
  - Amberstone's "git hook gate armed and firing" CI step, requested. See below.
  - The repo= short code: the brief said "rsc", this tree's tests pass
    "resin-compute", and live locks carry full paths. Three conventions, one
    field that only works if everyone agrees. Adopt whatever they answer.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - THE OPERATOR'S CALL: flip visibility. Do NOT enable Discussions in the same
    pass - inviting users to paste raw Enka payloads farms other people's UIDs
    into a public repo.
  - PROVE THE HOOK GATE FIRES, IN CI. CLAUDE.md says a hook's PRESENCE is never
    proof. tests/test_hook_interpreter.py proves interpreter selection and
    tests/test_commit_trailers.py proves no trailer reached history - a clean
    history is equally consistent with "the hook stripped it" and "nobody added
    one". The end-to-end check was run BY HAND on 2026-09-06 and passed; that
    expires the moment someone edits a hook. Needs BOTH directions: a banned
    glyph rejected AND a clean commit still succeeding.
  - Close the fan-content evidence hole. Three first-party PDFs were never read
    (zh-CN Terms of Service, Genshin Creator Program Official Rules, HoYoPlay
    Terms of Service) and their URLs are recorded NOWHERE, so the gap is not
    reproducible. pdftotext 4.00 IS on PATH at /mingw64/bin/pdftotext. Watch for
    a "Genshin Impact Fan Creations Guide" on HoYoLAB; HSR has one (17883171)
    and ZZZ has one (30075725), Genshin does not, and it would change ADR-008.
  - Two guards claim more than they sweep. tests/test_ports.py scans only .py
    via ast.parse - correct mechanism, real gap: requirements.txt stated the
    engine was on :8870 in the PRESENT TENSE and nothing saw it.
    tests/test_goal_spec.py denylists four literals plus one material name while
    GOAL_SPEC section 3 carries more. Derive the forbidden set FROM the spec's
    own unverified stamps instead of restating it by hand.
  - tests/test_docs_consistency.py derives its PREDICATE from git ls-files but
    still enumerates its CORPUS with rglob. Mild: the exposure is that an
    untracked scratch .md under docs/ gets graded.
  - Row-scoped provenance for data/costs/. Every record carries its own receipt:
    value, method, game version, date observed, reconfirmed-on-current-version.
    Facts are not copyrightable, so only the receipt travelling WITH the number
    distinguishes a measured table from a wiki table. Schema BEFORE the first row.
  - Observe the seed-team cost table in game. docs/GOAL_SPEC_SEED_TEAM.md 3.1
    gates a dated plan on FIRST-HAND observation. tests/_parked/ holds the
    TDD-first test file and a README saying how to unpark it. The web-sourced
    figures are UNVERIFIED and must not enter data/.
  - Artifact scoring needs a stated model BEFORE implementation, not after.

DO NOT REDO THESE. All shipped or settled:
  - The governor vendoring, pin, lane width and the adversarial fixes. Commits
    2a9d6c3, db3f767, 35140ee, adcfacc.
  - GitHub description and 17 topics, set 2026-09-06. CI and docs-guards badges
    are in README.md. Repository NAME: description and H1 only, no rename.
  - Banned-glyph enforcement in ci.yml and the ci/docs-guards complement guard
    (tests/test_ci_workflow_complement.py). Commit a326851.
  - The public-repo audit AND its fixes (e95a71c, 89fb813).
  - ADR-004's Lanternlight premise, corrected on LL's advice: their block is
    8810-8819 and has been since 2026-08-27. The ADR table was always right;
    only the prose was stale.
  - Legion Wallpaper's root is C:\Legion Wallpaper WITH A SPACE; the GitHub repo
    is Remus3/Legion-Wallpaper with a hyphen. Both deliberate. A spelling
    anchored on C: is a path and takes the space; a bare token is the name.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents independently flagged it and BOTH WERE WRONG. Do not "fix" it.
  - Commit identity: publish as-is, no second history rewrite. Declined 2026-09-06.
  - Publication rests on the VENDORING argument alone - zero vendored assets,
    zero vendored data, no game-client contact, one outbound host - NOT on any
    fan-content permission. ADR-008 records the COGNOSPHERE ToS section 7(c)
    scraping clause honestly, as an open question it does NOT resolve.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - AGENT WORKTREES CAN FORK FROM THE PREVIOUS HEAD, NOT YOURS. Measured
    2026-09-06: HEAD was 2a9d6c3 at dispatch and `git worktree list` showed both
    agents on ef4ff80, the commit BEFORE it. The builder whose whole job was to
    hash ops/loop/*.py had no ops/loop/ at all and burned 32 minutes iterating
    against an impossible precondition. ALWAYS run `git worktree list` after
    dispatching and check the SHA. Worktrees share .git, so any committed SHA is
    reachable: `git checkout <sha> -- <paths>`. A growing file mtime means the
    agent is iterating, not hung.
  - A GUARD THAT PINS NAMES INSTEAD OF THE DIRECTORY CAN BE DISARMED BY DELETING
    A NAME. SHARED_SHA256 drove both the presence and digest arms, so removing
    one entry silently disarmed both: 18 passed, exit 0, no skips, with a drifted
    file on disk. Fixed with an independent VENDORED_MODULES literal. The general
    lesson: a guard whose expectation lives in the same structure it checks is
    one edit from vacuous.
  - A GUARD THAT OVERSTATES ITS REACH IS WORSE THAN A MISSING ONE. It tells the
    next session the surface is closed so nobody looks. tests/test_core_config.py
    PROMISED any env-wiring of the ceiling "has to turn this file red" on the
    strength of a substring scan of one function; one line of the module's own
    field(default_factory=...) idiom moved the value to 9 with every guard green.
  - BEHAVIOUR ARMS ONLY CATCH WHAT THEY ASSERT. A mutant that removed hold()'s
    queueing entirely passed this suite and failed Riot Commander's, because the
    port collected worker exceptions and never asserted on them. If you port a
    test from a sibling, DIFF THE ASSERTIONS, not just the test names.
  - MUTATION-TEST EVERY GUARD YOU ADD. A guard nobody has watched fail is a
    guard nobody has tested. Break it on a SCRATCHPAD COPY, never the tracked
    tree, and confirm it goes red for the RIGHT reason.
  - A CROSS-REPO GUARD THAT READS A SIBLING TREE GOES SILENT, NOT RED. Riot
    Commander's guards held a stale C:\LegionWallpaper path after LW renamed;
    they SKIPPED and the suite read green while checking nothing. Pin against a
    constant in your own file. Absence must be RED, never a skip.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS, silently, and
    .gitattributes eol=lf means the INDEX hides it so no diff shows it. Only
    tests/test_line_endings.py caught it. Write BYTES, or use Write/Edit. To
    prove a byte pin survives a fresh clone, compare the INDEX BLOB to the disk
    bytes: `git cat-file blob :<path> | sha256sum`.
  - A QUOTED PATH INSIDE AN `sh -c` STRING IS MANGLED BY MSYS, but only when the
    path contains NO SPACE - a space suppresses the conversion. Pass the path as
    argv and run `exec "$0"`.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - MSYS rewrites the lone
    /F into F:/. Write `taskkill //F //PID <pid>`. It fails SILENTLY when
    redirected, so a process you believe you killed is still alive.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. `cmd | tail` then `$?` gives
    tail's status. Redirect to a file and check the real code.
  - A LITERAL WORD-PROBE IS ONLY AS GOOD AS ITS MORPHOLOGY. A probe for
    \bscrape\b returned 0 on a document containing "scraped" twice. Search the
    STEM - and a probe returning a CONVENIENT NEGATIVE deserves exactly the
    scrutiny a summary returning a convenient positive gets.
  - A SUMMARISED RETRIEVAL IS NOT A RETRIEVAL. Two summarising fetches invented
    clauses this tree acted on. Re-probe the raw bytes.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE, and neither is disagreement.
    Find the SHARED INPUT and test THAT.
  - A SWEEP NEEDS TWO GUARDS: one that the bad thing is gone, one that the
    LEGITIMATE NEIGHBOURS SURVIVED. "Legion" names both the machine AND a
    sibling project.
  - FREEZE READ-ONLY PASSES AGAINST A COMMITTED SHA, and expect scratchpad
    collisions: two adversaries running concurrently contaminated each other's
    copy on 2026-09-06. Give each a uniquely named private directory.
  - A GUARD THAT WALKS THE DISK IS NOT TESTING TRACKEDNESS. Git stores no empty
    directories. Ask git, never an ad-hoc denylist.
  - ASKING GIT CREATES ITS OWN DEPENDENCY. `git archive` plus `pytest tests`
    ABORTED AT COLLECTION, exit 2, ZERO TESTS RUN - what a reader gets from
    Download-ZIP. Use require_git_repository() or skip_module_without_git().
  - A heredoc plus a non-raw Python string mangles backslashes. Use Write/Edit.
  - `python3` here is the Microsoft Store shim with no pytest, and
    `command -v python3` SUCCEEDS. Probe CAPABILITY: `python3 -c "import pytest"`.
  - `git check-attr --stdin -z` changes the INPUT separator too. Join on NUL.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. 8870 is Daemon Slayer's. Verify a band against the owning
    project's registry IN SOURCE, never against netstat.
  - computer-use minimizes all windows when it initialises.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no
en-dashes, no smart quotes. Never add a Co-Authored-By or Claude-Session trailer.
Put the EXPECTED DURATION in every background task name, shorthand, e.g.
"Watch the CI fix run (22m)" - elapsed time alone cannot say whether a task is
stuck. Verify against ground truth before asserting anything is done, fixed,
broken or missing, and report the exact result observed with counts. Never trust
a subagent's claim about test counts, green CI or file existence without an
independent probe.

First action in a FRESH clone: python scripts/install_hooks.py
core.hooksPath is local config and is not cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.
```
