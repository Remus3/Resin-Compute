# Next-session prompt

The fenced block below is the hand-off. It is the SOURCE OF TRUTH: the `/done`
ritual prints it inline and `tools/publish_next_session.py` reads it to write
the Desktop backup, so it is written here once and never retyped. Exactly one
fenced block, 7-bit ASCII, self-contained - the next session boots cold.

```
Session start on ResinCompute (C:\Resin Compute, github.com/Remus3/Resin-Compute).

THE REPOSITORY IS STILL PRIVATE. `gh repo view` returns visibility PRIVATE.
Flipping it is the OPERATOR'S action and it is the LAST one. Everything that
blocked publication is now fixed, verified and pushed - so the next thing to
happen is the operator's decision, not more fixing.

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
isolation: "worktree" on the Agent call.

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
count, and you cannot report what you did not see. Measured 2026-09-06.

STATE, verified 2026-09-06 at commit 89fb813 (report what YOU observe, never
these numbers):
  licence QA                      33 passed
  docs QA                         23 passed
  scripts/qa_companion.py         17 passed, 0 failed, 1 skipped
  ruff                            All checks passed
  pytest tests                    763 passed, 1 skipped
  pytest agents/pity_engine        76 passed
  shell node --test                52 pass, 0 fail
  headless --once --dry-run       exit 0
  python -m mypy                  Success: no issues found in 23 source files.
                                  It was RED before this session. The cause was
                                  NOT a stray numpy - numpy is required by
                                  ImageHash, opencv-python, PyWavelets and scipy
                                  on this box. mypy.ini named agents/pity_engine/,
                                  which crawls the engine's own tests/, which
                                  imports pytest, which imports numpy. mypy.ini
                                  now excludes that test directory.
  CI at 89fb813                   ci success, docs-guards success

THE HIGHEST-VALUE WORK NOW, in ROADMAP.md order:
  - THE OPERATOR'S CALL: flip visibility, set the repository DESCRIPTION to
    "Resin Compute & Pity Engine" (decided 2026-09-06: description and H1 only,
    NO rename - the repo stays Resin-Compute and the two-tier convention in
    CLAUDE.md stays intact), then the visibility pass. Topics first, they are
    unset and free. Do NOT enable Discussions in the same pass - inviting users
    to paste raw Enka payloads farms other people's UIDs into a public repo.
  - Close the fan-content evidence hole. Three first-party PDFs were never read
    (zh-CN Terms of Service, Genshin Creator Program Official Rules, HoYoPlay
    Terms of Service) and their URLs are recorded NOWHERE, so the gap is not
    reproducible. pdftotext version 4.00 IS on PATH at /mingw64/bin/pdftotext -
    an earlier claim that no renderer existed was false. Watch also for a
    "Genshin Impact Fan Creations Guide" on HoYoLAB; Honkai: Star Rail has one
    (article 17883171) and Zenless Zone Zero has one (30075725), Genshin does
    not, and it is the likeliest event to change ADR-008.
  - Two guards claim more than they sweep. tests/test_ports.py scans only .py
    because it uses ast.parse to tell a live literal from a comment - correct
    mechanism, real gap: requirements.txt stated the engine was on :8870 in the
    PRESENT TENSE and nothing saw it. tests/test_goal_spec.py keeps unverified
    figures out of data/ with a denylist of four literals plus one material
    name, while GOAL_SPEC section 3 carries more than that. Derive the forbidden
    set FROM the spec's own unverified stamps instead of restating it by hand.
  - One trackedness instance is left and it is the mild one.
    tests/test_docs_consistency.py derives its PREDICATE from git ls-files but
    still enumerates its docs CORPUS with rglob at lines 172, 200, 231, 295,
    306, 326, 381. Not dangerous - a tracked file in a clean tree is always
    present, so the walk is a superset. The exposure is the opposite: an
    untracked scratch .md under docs/ gets graded.
  - Row-scoped provenance for data/costs/. Every record carries its own receipt:
    value, method, game version, date observed, and whether it is reconfirmed on
    the current version. Facts are not copyrightable, so only the receipt
    travelling WITH the number distinguishes a measured table from a wiki table.
    Needs a stated schema BEFORE the first row lands.
  - Observe the seed-team cost table in game. docs/GOAL_SPEC_SEED_TEAM.md
    section 3.1 gates a real dated plan on FIRST-HAND observation - Mora and
    Hero's Wit per ascension threshold, plus material name and quantity.
    data/costs/ is ready. tests/_parked/ holds the complete TDD-first test file
    with a README saying how to unpark it. The web-sourced figures in the goal
    spec are UNVERIFIED and must not enter data/.
  - Artifact scoring needs a stated model BEFORE implementation, not after.

DO NOT REDO THESE. All shipped or settled, 2026-09-06:
  - The public-repo audit AND its fixes. Findings and outcomes are in ROADMAP.md
    and docs/LEDGER.md. Two commits: e95a71c and 89fb813.
  - The fixtures no longer claim to be synthetic. seed_roster.json and
    seed_materials.json carry _hand_authored / _vendored / _content;
    enka_sample_profile.json IS genuinely synthetic and correctly keeps that
    label. Hand-authored is the STRONGER claim and it is what ADR-002 requires.
  - NOTICE carries the GPL-3 warranty disclaimer, a trademark acknowledgement,
    and the non-commercial statement as a FACT about the project rather than as
    reliance on any permission.
  - ADR-008 (fan-content posture) and ADR-009 (no per-file licence headers).
    Numbering runs 1..9 and contiguity is guarded.
  - UID 618285856 IS NOT A LEAK. It is Enka.Network's OWN published example UID,
    in their API-docs twice. Two agents independently flagged it and BOTH WERE
    WRONG. It is annotated at the use site in README.md. Do not "fix" it.
  - Repo relocation, the /done ritual, the agent roster, and the port migration.

TRAPS THAT HAVE ALREADY BITTEN IN THIS TREE. All measured, none hypothetical:

  - A GUARD THAT WALKS THE DISK IS NOT TESTING TRACKEDNESS. Git stores no empty
    directories and knows nothing about ignored ones. This root cause had FOUR
    instances; three are fixed and one is left (above). tests/test_ports.py was
    genuinely RED in the main checkout. Ask git, never an ad-hoc denylist - a
    denylist is a list of the ignore rules someone remembered.
  - ASKING GIT CREATES ITS OWN DEPENDENCY, AND IT BROKE THE SUITE. `git archive`
    plus `pytest tests` ABORTED AT COLLECTION, exit 2, ZERO TESTS RUN - what a
    reader gets from Download-ZIP or an sdist. tests/conftest.py now holds the
    skip helpers. If you add a git-dependent guard, use require_git_repository()
    at the call site, or skip_module_without_git() at module scope if git is
    called during import (a parametrize argument).
  - pathlib.Path.write_text CONVERTS LF TO CRLF ON WINDOWS, silently, and
    .gitattributes eol=lf means the INDEX hides it so no diff shows it. Only
    tests/test_line_endings.py caught it. Write BYTES, or use the Write/Edit
    tools. Repair with raw.replace(b"\r\n", b"\n").
  - A QUOTED PATH INSIDE AN `sh -c` STRING IS MANGLED BY MSYS, but only when the
    path contains NO SPACE - a space suppresses the conversion. That is why it
    passed at `C:\Resin Compute` and would fail at `C:\dev\ResinCompute`. Pass
    the path as argv and run `exec "$0"`. Same root cause as the taskkill rule.
  - `taskkill /F /PID` DOES NOT WORK in the Bash tool - MSYS rewrites the lone
    /F into F:/. Write `taskkill //F //PID <pid>`. It fails SILENTLY when
    redirected to /dev/null, so a process you believe you killed is still alive.
  - A SINGLE-LINE GREP MISSES A WRAPPED SENTENCE. Any prose sweep must be
    multiline-aware; normalise whitespace before matching.
  - A LITERAL WORD-PROBE IS ONLY AS GOOD AS ITS MORPHOLOGY. A probe for
    \bscrape\b returned 0 on a document containing "scraped" twice, and a whole
    licence finding was built on that zero. Search the STEM, not the lemma - and
    a probe returning a CONVENIENT NEGATIVE deserves exactly the scrutiny a
    summary returning a convenient positive gets.
  - A SUMMARISED RETRIEVAL IS NOT A RETRIEVAL. Two separate summarising fetches
    invented clauses this tree acted on. Re-probe the raw bytes.
  - AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE, and neither is disagreement.
    Find the SHARED INPUT and test THAT against the upstream artifact.
  - A SWEEP NEEDS TWO GUARDS: one that the bad thing is gone, one that the
    LEGITIMATE NEIGHBOURS SURVIVED. "Legion" names both the machine AND a
    sibling project in ADR-004's port registry.
  - FREEZE READ-ONLY PASSES AGAINST A COMMITTED SHA. Both adversaries this
    session reported the tree moving under them because the orchestrator kept
    merging. Dispatch them against a SHA and tell them to clone or git archive
    it. A verdict rendered against a moving tree is about no state at all.
  - A heredoc plus a non-raw Python string mangles backslashes. Use Write/Edit.
  - `python3` here is the Microsoft Store shim with no pytest, and
    `command -v python3` SUCCEEDS. Probe CAPABILITY: `python3 -c "import pytest"`.
  - `git check-attr --stdin -z` changes the INPUT separator too. Join on NUL.
  - AN EMPTY DIRECTORY IS NOT IN THE REPOSITORY. `git ls-files <dir>` returning
    nothing while `ls` shows it is the tell.
  - Ports are owned by core/ports.py and nowhere else. This project holds
    8790-8809. 8870 is Daemon Slayer's. Verify a band against the owning
    project's registry IN SOURCE, never against netstat.
  - computer-use minimizes all windows when it initialises.

OPERATOR DECISIONS ALREADY TAKEN, do not re-open without cause:
  - Repository NAME: description and README H1 only, no rename.
  - Commit identity: publish as-is. No second history rewrite. The two commits
    carrying an agent as author/committer stay, and the author email on most
    commits becomes public on the flip. Considered and declined 2026-09-06.
  - Publication rests on the VENDORING argument alone - zero vendored assets,
    zero vendored data, no game-client contact, one outbound host - NOT on any
    fan-content permission. ADR-008 records the COGNOSPHERE ToS section 7(c)
    scraping clause and the HoYoverse -> enka.network -> this-repo data chain
    honestly, as an open question it does NOT resolve.

WORKING RULES: TDD, failing test first. Atomic writes only via core/atomic_io.py.
py_compile before any restart. 7-bit ASCII everywhere, no em-dashes, no
en-dashes, no smart quotes. Never add a Co-Authored-By or Claude-Session trailer.
Verify against ground truth before asserting anything is done, fixed, broken or
missing, and report the exact result observed with counts. Never trust a
subagent's claim about test counts, green CI or file existence without an
independent probe - that rule earned itself repeatedly this session, including
against the main thread's own accepted findings.

First action in a FRESH clone: python scripts/install_hooks.py
core.hooksPath is local config and is not cloned, so a fresh clone runs zero
hooks. Never treat a hook's presence as proof it fires - stage a banned glyph,
attempt a real commit, assert HEAD is unchanged.
```
