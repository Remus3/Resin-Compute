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
THE ACCOUNT NOW EXISTS. THIS IS THE BIG CHANGE SINCE THE LAST HAND-OFF.
=====================================================================

Genshin Impact was installed and launched for the FIRST TIME on 2026-09-07,
and a capture lane was standing before it launched. Everything it produced is
in C:\rsc-first-run\ - OUTSIDE this git tree, on purpose, because the game's
logs carry the account UID and the miHoYo registry subtree carries a login
token.

WHAT IS IN THE STORE, measured 2026-09-07 at shutdown:
  events.jsonl              6062 file events
  blobs/                    5971 distinct content-addressed blobs
  screens/                  1542 screenshots kept of 2036 index lines
  video/                    29 mkv segments, 15fps, 2560x1440
  observations.jsonl        10 recorded observations, each with evidence
  evidence/                 9 stamped PNGs with sha256 recorded
  webcache_snapshots/       2
  wish/                     the gacha URL, raw bodies, 10 pull attempts
  account.json              UID, region, nickname, traveller
  TOTAL                     15 GB

ACCOUNT FACTS, all verified from capture, all recorded in account.json:
  UID           692912734, read FOUR ways that do not share one input - two
                pixel reads of one crop (that is ONE fact), plus the game's own
                UidInfo.txt bytes and the BeyondLocal/<uid> directory it made
  region        os_usa (America, UTC-5), VERIFIED from the game writing
                security_server_default_iplist_os_usa.txt itself
  traveller     Lumine, female. OCR caught "the god took away my brother"
  nickname      xMoonbeam, recovered from the VIDEO at seg_20260907_025348.mkv
                +108s. The 4-second screenshot lane missed that screen entirely
  roster        8 slots. Moonbeam (Manekin, Miliastra Wonderland, 6 GREY stars,
                red card, DEF 147 > ATK 106, EM 0), Amber, Noelle, Dehya,
                Traveler, Sucrose, Kuki Shinobu, Yaoyao

THE UID MUST NEVER ENTER THIS TREE. A sweep over all 164 tracked files for any
nine-digit run hashing to it found 0, and the checker was proven to fire on a
planted control first.

THE CAPTURE LANE IS STOPPED. All four processes were shut down cleanly at the
end of the session and the game is closed. To bring it back up:
  python tools/first_run_capture.py --root C:/rsc-first-run --interval 2
  python tools/screen_capture.py --root C:/rsc-first-run --interval 4
  python tools/capture_supervisor.py --root C:/rsc-first-run --interval 15
  ffmpeg -f gdigrab -framerate 15 -offset_x 0 -offset_y 0 -video_size 2560x1440
    -i desktop -c:v h264_nvenc -preset p4 -cq 28 -g 30 -pix_fmt yuv420p
    -f segment -segment_time 300 -reset_timestamps 1 -strftime 1
    "seg_%Y%m%d_%H%M%S.mkv"

STATE, measured 2026-09-07 at commit 7e807a0 (report what YOU observe, never
these numbers):
  licence QA                      41 passed
  docs QA                         23 passed
  scripts/qa_companion.py         17 passed, 0 failed, 1 skipped
  ruff                            All checks passed
  pytest tests                    1095 passed, 1 skipped
  pytest agents/pity_engine       80 passed
  shell node --test               52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 31 source files
  git worktree list | tail -n +2 | wc -l                    0
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. CI pins 3.11 and passes.
  The 3.11 declaration is load-bearing rather than cosmetic: it is what makes
  numpy's PEP 695 stub a syntax error.

  MYPY NOW CHECKS 31 FILES AND ITS Success IS STILL NOT EVIDENCE ABOUT THE REST.
  files= covers core/ engines/ ingest/ agents/pity_engine/ tools/ only. tests/,
  scripts/, surface/, ops/, headless/ and conftest.py are DARK.
  tests/test_mypy_scope.py goes red if a root leaves the list.

  MYPY NEEDED A NUMPY OVERRIDE THIS SESSION AND IT IS NOT THE THING mypy.ini
  ALREADY REJECTED. tools/screen_capture.py imports Pillow, whose type hints
  reference numpy, whose __init__.pyi is a syntax error under python_version
  3.11, and one third-party stub error stops all further checking. The fix is
  follow_imports = skip PLUS follow_imports_for_stubs = True, scoped to numpy.
  skip alone does NOT apply to .pyi files - that was measured. The earlier
  rationale in mypy.ini rejected silencing numpy for a DIFFERENT entry path, a
  test directory, where there was a directory to drop. Here there is not.

SETTLED. DO NOT REDO:
  - THE FORK-PR RISK IS CLOSED. approval_policy is "first_time_contributors".
  - THE HOOK GATE IS PROVEN ON A REAL RUNNER, 12 passed, ran not skipped.
  - THE WATCHER FIRES, at SessionStart AND UserPromptSubmit.
  - CAVEMAN ULTRA adopted on operator instruction. _BANNER is a FLEET CONTRACT
    and its sha256 is pinned in tests/test_session_hooks.py.
  - EVERY API KEY IS A MACHINE ENV VAR. tests/test_no_secret_literals.py.
  - THE GOVERNOR IS CURRENT AND STILL INERT ON PURPOSE.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents flagged it and BOTH WERE WRONG. Do not "fix" it. It is NOT the
    operator's UID, which is a different number and is not in this tree at all.
  - THE VERBATIM DROP IS GONE AND THAT IS CORRECT. Containment was MEASURED.
  - THE PICKAXE CHECK WAS RUN, ARMED, 2026-09-07. Account name 0 across refs.
  - WEBCACHES IS UNDER THE GAME INSTALL, NOT THE USER PROFILE. Fixed in
    f930263 and pinned by tests/test_wish_authkey_paths.py, which pins the
    candidate ORDER and not merely the membership. Do not "restore" the
    LocalLow path to the front.
  - _HOST_NEW IS NO LONGER UNVERIFIED. public-operation-hk4e-sg.hoyoverse.com
    /gacha_info/api/getGachaLog answered retcode 0 on the live account.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - ROW-SCOPED PROVENANCE SCHEMA FOR data/, BEFORE THE FIRST ROW LANDS. Every
    value must carry what it was read from, its sha256, and whether it was read
    by eye, by OCR, or from the game's own bytes. That distinction already
    earned its keep: two pixel reads of one crop are ONE fact.
  - RE-SWEEP FOR NOELLE'S ACQUISITION FRAME AT FULL RATE. NOT FOUND AT 1 FPS IS
    NOT NOT PRESENT. Window 09:20:44Z to 09:42:59Z on 2026-09-07, recording is
    15fps, only one frame in fifteen was examined. Do it before any segment is
    pruned.
  - ENKA IS NOW REACHABLE IN PRINCIPLE and ingest/enka_client.py has never met
    a real profile. It needs Adventure Rank 10 AND an OPEN showcase, neither of
    which is true yet. It is the only route to a real roster payload rather
    than an OCR'd one.
  - FIX THE FOUR ROOT-WALKING GUARDS that cannot see a nested checkout:
    test_docs_consistency.py, test_goal_spec.py, test_licence_posture.py,
    test_line_endings.py. Measured across 39 modules - 1 excluded, 4 not, 34
    structurally immune because their corpus is git ls-files. The cheapest fix
    is the exclusion tests/test_loop_concurrency.py already has.
  - THE CLAIM GATE IS LANDED BUT DELIBERATELY UNWIRED. tools/stop_claim_gate.py,
    no Stop hook declared. Before arming it: an INDEPENDENT pass must measure
    the false rate (55.5 percent was measured by the agent that wrote the
    chaining), somebody must CLASSIFY the residual false positives, and
    TRANSCRIPT_PATH_KEY and BLOCK_EXIT_CODE are GUESSES.
  - RC OWES THE CLAIM-GATE SPEC, asked 2026-09-07, unanswered.
  - BRING ONE MORE ROOT INTO MYPY. surface/ 1 error, headless/ 3, ops/ 8,
    scripts/ BLOCKED by a duplicate-module-name refusal needing __init__.py.
  - Close the fan-content evidence hole. Three first-party PDFs were never read
    and their URLs are recorded NOWHERE. pdftotext 4.00 IS on PATH.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - A WRONG PATH AND A MISSING ONE CAN PRINT THE SAME SENTENCE. wish_authkey
    said "no webCaches directory found yet. Has Genshin Impact ever been
    launched on this machine?" while the operator had Wish History open and the
    cache held 15 occurrences of "authkey". The message was accurate about what
    it checked and wrong about what it implied, which sent the reader to look
    at the game rather than at the path.
  - A TRUNCATED CREDENTIAL LOOKS LIKE AN EXPIRED ONE. A 1500-byte cap on a
    1755-byte URL cut a 1452-byte authkey in half and the endpoint answered
    "retcode -100: authkey error". The instinct was to go get a fresh key
    rather than to look at the scanner.
  - OCR RETURNS A CONFIDENT ZERO ON STYLISED GAME TEXT. Tesseract found 166
    hits across 1328 frames and MISSED "Obtained New Character / Dehya"
    entirely. Use OCR to NARROW a corpus, never to conclude an absence from it.
  - NOT FOUND AT 1 FPS IS NOT NOT PRESENT. Report the sampling rate in the same
    sentence as any negative taken over a recording.
  - AN IN-PROGRESS .mp4 WILL NOT OPEN - "moov atom not found", the index is
    written when the muxer closes. Matroska decodes to the last complete
    cluster. Proven at shutdown: a FORCE-KILLED mkv segment still decoded to a
    frame with mean 66.6 and stdev 18.2.
  - THE GAME HOLDS ITS CACHE FILES LOCKED. Direct reads of Cache_Data/data_2
    get Permission denied while a filesystem COPY of the same file succeeds.
    Snapshot first, scan the snapshot.
  - MATCHING A DAEMON BY SUBSTRING OVER ITS WHOLE COMMAND LINE IS WRONG. A
    probe process whose own source names two daemons matches both. It briefly
    killed every real watcher while the probe survived. Match argv[1] only.
  - A HEREDOC MANGLES BACKSLASHES EVEN WHEN QUOTED. It bit THREE more times on
    2026-09-07, once turning a redaction regex into "unterminated character
    set" AFTER nine real candidates had printed - a redaction that fails open
    is how a credential reaches a transcript - and once as a unicodeescape
    SyntaxError. Use a real file for any script containing backslashes.
  - A GREEN LOCAL GATE ON WINDOWS SAYS NOTHING ABOUT THE LINUX RUNNER.
    `ctypes.wintypes`, `ctypes.WinDLL`, `subprocess.DETACHED_PROCESS` and
    `CREATE_NEW_PROCESS_GROUP` are all `sys.platform == "win32"` in typeshed, so
    a bare reference is a mypy ERROR on Linux and one error stops mypy checking
    anything else. mypy NARROWS on `sys.platform`, so an `if sys.platform ==
    "win32":` guard is the fix. `hasattr` guards the INTERPRETER and does NOT
    narrow for the checker - use `getattr(mod, "NAME", 0)`.
  - A TEST OF AN ORDERING MUST NOT READ THE REAL ENVIRONMENT. USERPROFILE is
    unset on Linux, so a candidate-order test asserted the absence of something
    the code was right not to produce. Set it to tmp_path - NOT to a literal
    home-shaped string, which test_machine_identity.py forbids and caught.
  - A GUARD CAN REPORT A NUMBER THAT IS NOT THE NUMBER IT NAMES.
    test_mypy_scope.py read the FIRST digit off mypy's tail line. Clean that is
    the file count; with errors the line is "Found 3 errors in 3 files (checked
    31 source files)" and the first digit is the ERROR count. The failure read
    "mypy checked 3 files but the roots select 31" and sent the reader to the
    scope while the real problem was three platform errors.
  - VERIFY AN ENVIRONMENT FIX BY DELETING THE ENVIRONMENT. Re-running the two
    affected modules in a subprocess with USERPROFILE and RSC_WEBCACHES_ROOT
    removed is what distinguished a fix from a platform accident.
  - WITHOUT A POSITIVE CONTROL, A CLEAN RESULT AND AN UNARMED CHECK LOOK
    IDENTICAL. This is the single most productive rule in this tree.
  - TWO NUMBERS CONSISTENT WITH A HYPOTHESIS ARE NOT EVIDENCE FOR IT. Dehya was
    recorded as a TRIAL character on Level 17 plus Friendship 1. She was not.
    The card colour answered it directly and was on screen the whole time.
  - ZERO OUT OF ZERO READS AS A PASS. Every checker returns (checked, offenders)
    and every test asserts the CHECKED COUNT before the offender list.
  - A GUARD CAN BE WRONG IN THE DIRECTION OF FALSE RED.
  - A ROOT-WALKING GUARD CANNOT SEE A NESTED CHECKOUT, but one whose corpus is
    git ls-files is structurally immune, because git does not descend into one.
  - A DOCUMENT DESCRIBING A PATH SHAPE DOES NOT NEED TO RENDER THE PATH. A
    triage doc wrote a bracketed account segment inside a literal Windows path
    and the machine-identity guard went red. The guard was right. The regex was
    NOT widened.
  - A WRONG RATIONALE OUTLIVES A WRONG LINE OF CODE.
  - A CONFIG COMMENT CAN EXPLAIN THE WRONG LINE.
  - BYTES-EQUAL IS NOT THE SAME FACT AS DID-NOT-WRITE.
  - THE WATCHER'S STDOUT IS A PRIVILEGED SURFACE. Names, counts and digests -
    NEVER a payload byte.
  - THE STANDING REF CHECK IS `git branch -a`, NOT `git worktree list`.
  - A FORCE-PUSH DOES NOT PURGE OBJECTS FROM GITHUB.
  - NOTE FILENAME TIMESTAMPS ARE FICTIONAL and drift by up to SIX HOURS.
  - AN UNWIRED SCRIPT IS NOT A WATCHER. Prove it by EXECUTING the command.
  - NEVER ADOPT A SIBLING'S CONFIG UNREAD.
  - A DETECTOR'S OWN PATTERN TRIPS ITS OWN SWEEP.
  - A GATE THAT QUOTES WHAT IT CAUGHT PUBLISHES IT.
  - A SKIPPED TEST IS A GREEN TICK. RSC_REQUIRE_HOOK_GATE=1.
  - AGENT WORKTREES FORK FROM THE PRE-DISPATCH HEAD.
  - SendMessage MAY BE DISABLED. Write a MERGE_TODO file instead.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS silently.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. Redirect to a file.
  - xargs SPLITS ON WHITESPACE and this repo's path contains a space.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - write `taskkill //F
    //PID <pid>`. But inside a PYTHON subprocess call it is `/F` again, because
    that does not go through MSYS. Getting this backwards silently killed
    nothing on 2026-09-07 while printing "killing <pid>".
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
