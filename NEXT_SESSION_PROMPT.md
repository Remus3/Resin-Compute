# Next session prompt

The fenced block below is the hand-off. `tools/publish_next_session.py` reads it
out of this file and writes the Desktop backup, so this file is edited and the
block is never retyped anywhere else.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

VERIFY VISIBILITY BEFORE YOU BELIEVE ANYTHING HERE:
  gh repo view Remus3/Resin-Compute --json visibility
The flip to PUBLIC was the LAST action of 2026-09-06, after /done. Confirm it
rather than trusting this line - that is the same rule this tree applies to
every other claim.

THE REPOSITORY WAS DELETED AND RECREATED ON 2026-09-06. This is not a rename and
not a rewrite you can ignore: EVERY COMMIT SHA CHANGED. Anything you have from
before that - a SHA in a note, a bookmark, a local clone - points at objects that
no longer exist anywhere. The Actions run history and the original creation date
were spent deliberately to buy the purge. Description and all 17 topics were
restored. Discussions is OFF and must stay off until there is a redaction path
for outsiders pasting Enka payloads.

FIRST ACTION, and it can only be done now that the repo is public:
  gh api repos/Remus3/Resin-Compute/actions/permissions/fork-pr-contributor-approval
It returns 422 while a repo is private, so it could not be checked in advance. If
approval is NOT required, a stranger's first pull request editing
requirements-dev.txt gets code execution on the runner via pip install. Bounded -
permissions: contents: read, no secrets, PR-scoped cache, ephemeral runner - but
it is the one risk that opens AT the flip.

FIRST ACTION IN A FRESH CLONE: python scripts/install_hooks.py
core.hooksPath is local config and is NOT cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.

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
WORKTREE-ISOLATE EVERY AGENT THAT WRITES, and then read the worktree traps below,
because BOTH of them fired on 2026-09-06.

CHECK THE INBOX EARLY. A watcher now exists and it is the durable half:
  python scripts/watch_inbox.py            what is new since the last mark
  python scripts/watch_inbox.py --all      everything
  python scripts/watch_inbox.py --mark     record the current set as read
THE WATERMARK WAS DELIBERATELY LEFT UNMARKED. 42 notes are listed and roughly ten
were actually processed on 2026-09-06. Triage first, then --mark. An inflated
watermark is worse than none. Reading never marks; --mark is a separate act.

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

STATE, measured 2026-09-06 at commit dd1ac02 (report what YOU observe, never
these numbers):
  licence QA                      41 passed
  docs QA                         23 passed
  scripts/qa_companion.py         16 passed, 0 failed, 2 skipped
  ruff                            All checks passed
  pytest tests                    852 passed, 1 skipped
  pytest agents/pity_engine       80 passed
  shell node --test               52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 23 source files
  The single skip is the opt-in network test in tests/test_ingest_client.py.

  THE INTERPRETER HERE IS PYTHON 3.14.4, while CLAUDE.md, mypy.ini and ruff.toml
  all declare 3.11. Green means green on 3.14 ONLY. This predates the current
  work and was deliberately not touched - decide whether to align the
  declaration or the runtime, do not assume either.

THE CONCURRENCY GOVERNOR IS CURRENT AND STILL INERT ON PURPOSE.
Both shared files were re-pinned on 2026-09-06 in two joint rounds authored by
Legion Wallpaper:
  winmutex.py  0b112a4f...  mutex names ROTATED away from vendor-descriptive
  slots.py     629c3d51...  the hold() release-path leak FIXED
All three trees verified equal by hashing all three disks directly.
NOTHING IN THIS TREE ACQUIRES A SLOT - headless/runner.py is a job runner, not a
Claude-executor loop. This is a PARITY CONTRACT JOINED AHEAD OF NEED.
  - NEVER edit either shared file unilaterally, and NEVER regenerate the digests
    from local disk to make a test pass. That launders a drift into "agreed".
    The sanctioned round is: one side authors, hands the others the exact bytes
    AND the digest AND a demonstration, all three re-hash their OWN disks, and
    the pin stays PROVISIONAL until every tree hashes equal.
  - The leak fix was MEASURED here before adoption, 8 workers over 2 slots at
    backoff=0.02, 40 rounds: old 35-of-40 rounds leaking and 69 SlotTimeouts,
    new 0 and 0. If test_contending_threads_never_exceed_max_slots ever goes red
    with a SlotTimeout again, that is the leak returning, not a flake.
  - DEFAULT_ROOT stays C:\ProgramData\lw-loop\slots. A second bucket is worse
    than no governor: both look healthy and neither bounds the other.

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - The fork-PR approval check above. It is thirty seconds and it is the only
    thing that got riskier at the flip.
  - PROVE THE HOOK GATE FIRES, IN CI. Still open, but no longer blocked:
    Riot Commander sent a working "git hook gate armed and firing" step through
    the inbox, AND a correction saying its first version was vacuous. Use the
    corrected one. Needs BOTH directions - a banned glyph rejected AND a clean
    commit still succeeding - or a gate that rejects everything passes the first
    arm while broken.
  - Answer the charter rounds. v3 is ADOPTED with one dissent filed and
    accepted; v4 arrived at the very end of 2026-09-06 and is UNREAD. RC's rule
    is that SILENCE IS NOT AGREEMENT, so an unanswered charter reads as dissent.
  - agents/pity_engine/CHANGELOG.md needs an entry for the exclusive bind.
  - A guard for the ONE checkable shape of prose falsity: a document asserting a
    property of a file that the file itself contradicts. Three of this session's
    findings were exactly that and no gate saw any of them.
  - Close the fan-content evidence hole. Three first-party PDFs were never read
    and their URLs are recorded NOWHERE. pdftotext 4.00 IS on PATH. Watch for a
    "Genshin Impact Fan Creations Guide" on HoYoLAB; HSR and ZZZ have one,
    Genshin does not, and it would change ADR-008.
  - Two guards still claim more than they sweep. tests/test_ports.py scans only
    .py via ast.parse - correct mechanism, real gap for prose. tests/
    test_goal_spec.py denylists four literals plus one material name while
    GOAL_SPEC section 3 carries more; derive the forbidden set FROM the spec's
    own unverified stamps.
  - tests/test_docs_consistency.py derives its PREDICATE from git ls-files but
    still enumerates its CORPUS with rglob.
  - Row-scoped provenance for data/costs/. Schema BEFORE the first row.
  - Observe the seed-team cost table in game. The web-sourced figures are
    UNVERIFIED and must not enter data/.
  - Artifact scoring needs a stated model BEFORE implementation.

DO NOT REDO THESE. All shipped or settled:
  - The publish sweep, the history rewrite and the remote rebuild. Six
    adversaries, four builder slices, 12 files, all landed.
  - The unlicensed-lockfile contradiction, the two false compliance claims in
    LICENSE_NOTES, the SPEC_SCAFFOLD trademark overclaim, the phantom ASCII
    exemption, the CI space-splitting bug and its 14-file coverage gap, the
    engine exclusive bind and the scheduled-task removal docs. All fixed and
    guarded.
  - The ADR-004 sibling-contents redaction. Recorded IN the ADR, not silent.
  - Both governor rounds. Three-way equal, verified from three disks.
  - GitHub description and 17 topics. Restored after the recreate.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID.
    Two agents flagged it and BOTH WERE WRONG. Do not "fix" it.
  - Commit identity: publish as-is. Declined 2026-09-06 and unchanged by the
    rewrite, which scrubbed a path and a trailer, not authorship.
  - Publication rests on the VENDORING argument alone - zero vendored assets,
    zero vendored data, no game-client contact, one outbound host - NOT on any
    fan-content permission. ADR-008 records the COGNOSPHERE ToS 7(c) scraping
    clause honestly, as an open question it does NOT resolve.
  - winmutex/slots disclosure: NOT a publication issue. Legion Wallpaper has
    published both files since 2026-08-02. Verified independently.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - A FORCE-PUSH DOES NOT PURGE OBJECTS FROM GITHUB. Two commits force-pushed
    away were still served by SHA weeks later, with their SHAs published by the
    repo's own Events API and Actions run list. The ONLY procedure that works is
    rewrite locally, DELETE the remote, recreate, push clean - then verify from
    the server: the orphans must return 422 and the blob 404.
  - AN OBJECT PURGE IS TRUE ONLY AT THE INSTANT IT IS MEASURED. A purged blob
    came back THREE times on 2026-09-06: a FETCH_HEAD left by fetching a backup
    bundle, a refs/remotes/origin/main surviving inside .git/packed-refs after
    update-ref -d removed the loose ref, and agent worktrees checking out the
    pre-rewrite commit into the shared object store. gc --prune=now is powerless
    against a live reference. Re-verify after anything that can create a ref.
  - AGENT WORKTREES CAN FORK FROM A STALE HEAD. Measured twice. On 2026-09-06
    HEAD was d77db76 at dispatch and all four worktrees came up on 41e7184, two
    commits behind. ALWAYS run `git worktree list` after dispatching and check
    the SHA. If it is stale, either re-dispatch or PROVE no file on the
    write-list differs between the two commits.
  - A SCOPE THAT PROTECTS A NEIGHBOUR CAN BLIND THE CHECK. An adversary was told
    "do not read any sibling tree" so it would not rummage in other projects.
    That also made "is this content already public" unaskable, and a finding was
    escalated to the operator and two siblings on an untested premise. The
    question was answerable from public data alone.
  - A GUARD THAT PINS NAMES INSTEAD OF THE DIRECTORY CAN BE DISARMED BY DELETING
    A NAME. A guard whose expectation lives in the same structure it checks is
    one edit from vacuous.
  - A GUARD THAT OVERSTATES ITS REACH IS WORSE THAN A MISSING ONE. It tells the
    next session the surface is closed so nobody looks.
  - A GUARD CANNOT SEE WHAT IS ALREADY PUBLISHED. test_machine_identity.py reads
    git ls-files (current checkout) and test_commit_trailers.py walks git log on
    HEAD. Both stayed green for weeks while a leak was live on the remote.
  - MUTATION-TEST EVERY GUARD YOU ADD, and check the mutant is not EQUIVALENT. A
    corrupt-watermark mutant written on 2026-09-06 returned a sentinel no note
    is named, changed no behaviour, and "survived" - which proved nothing. Break
    it on a SCRATCHPAD COPY, never the tracked tree.
  - BEHAVIOUR ARMS ONLY CATCH WHAT THEY ASSERT. If you port a test from a
    sibling, DIFF THE ASSERTIONS, not just the test names.
  - A CROSS-REPO GUARD THAT READS A SIBLING TREE GOES SILENT, NOT RED. Pin
    against a constant in your own file. Absence must be RED, never a skip.
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS, silently, and
    .gitattributes eol=lf means the INDEX hides it. Write BYTES, or use
    Write/Edit, or cp for a byte-exact copy. To prove a byte pin survives a
    fresh clone, compare the INDEX BLOB to the disk bytes.
  - A QUOTED PATH INSIDE AN `sh -c` STRING IS MANGLED BY MSYS, but only when the
    path contains NO SPACE - a space suppresses the conversion.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - MSYS rewrites the lone
    /F into F:/. Write `taskkill //F //PID <pid>`. It fails SILENTLY when
    redirected, so a process you believe you killed is still alive.
  - AN EXIT CODE READ THROUGH A PIPE IS THE PIPE'S. Redirect to a file.
  - xargs SPLITS ON WHITESPACE. Two CI gates passed any path containing a space
    and reported "scanned, clean" while scanning nothing. Use -0 with ls-files
    -z, and assert the SCANNED count, never that the list was non-empty.
  - A LITERAL WORD-PROBE IS ONLY AS GOOD AS ITS MORPHOLOGY. Search the STEM, and
    a probe returning a CONVENIENT NEGATIVE deserves the scrutiny a convenient
    positive gets.
  - A SUMMARISED RETRIEVAL IS NOT A RETRIEVAL. Re-probe the raw bytes.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE. Find the SHARED INPUT and test
    THAT. Two siblings agreed LW was public and they were right - it was still
    checked directly before acting on it.
  - A SWEEP NEEDS TWO GUARDS: one that the bad thing is gone, one that the
    LEGITIMATE NEIGHBOURS SURVIVED.
  - FREEZE READ-ONLY PASSES AGAINST A COMMITTED SHA, and give each concurrent
    agent a uniquely named private scratch directory.
  - A GUARD THAT WALKS THE DISK IS NOT TESTING TRACKEDNESS. Ask git.
  - ASKING GIT CREATES ITS OWN DEPENDENCY. Use require_git_repository() or
    skip_module_without_git() from tests/conftest.py.
  - `python3` here is the Microsoft Store shim with no pytest, and
    `command -v python3` SUCCEEDS. Probe CAPABILITY.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. Verify a band against the owning project's registry IN SOURCE.
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
