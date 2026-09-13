# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and
`tools/publish_next_session.py` reads it from here rather than from a retyped
copy, so this file and `RSC-NEXT-SESSION.txt` cannot disagree.

```
Read CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md, docs/LEDGER.md and
git log. Before planning any character build read docs/GOAL_SPEC_SEED_TEAM.md.
Before adding any data source read docs/LICENSE_NOTES.md. Before re-litigating a
past choice read docs/adr/README.md.

DO NOT RE-DERIVE THE GACHA CONSTANTS from memory or a web search. They are
verified and recorded in docs/SPEC_SCAFFOLD.md section 3, with the three
corrections to the original brief in docs/adr/ADR-003-forecaster-model.md. The
50/50 has been 55.000 percent consolidated since version 5.0, not 50. The weapon
soft-pity ramp SATURATES AT PULL 77 under a 7 percent increment and any claim of
79 or 80 is arithmetically impossible. 1.600 percent is 1 / E[wishes per 5-star],
a long-run average, NEVER a per-wish Bernoulli parameter.

STATE OBSERVED 2026-09-12, AT COMMIT e4f5817, AS A READING AND NOT A PROMISE.
main clean and pushed, 0 worktrees. Five commits landed this session,
003400e..e4f5817. Measured in a SHELL invocation from the repo root:
  python -m pytest tests                      2720 passed, 2 skipped
  python -m pytest agents/pity_engine            80 passed
  python -m pytest tests/test_licence_posture.py 47 passed
  python -m pytest tests/test_docs_consistency.py 34 passed
  python scripts/qa_companion.py      17 passed, 0 failed, 2 skipped, 3 noted
  cd shell && node --test              52 pass, 0 fail
  python -m headless.runner --once --dry-run   exit 0, 0 pass 0 fail 6 skip
  python -m ruff check .               All checks passed
  python -m mypy                       Success, 36 source files - ADVISORY ONLY
  python tools/precommit_gate.py       exit 0
CI: ci and docs-guards both green on main at e4f5817.

THE SUITE COUNT DEPENDS ON THE INVOCATION AND NEITHER NUMBER IS THE COUNT.
2717 collected. A shell run is 2715 passed 2 skipped at 02b8335 and 2720 passed 2
skipped at e4f5817; a run UNDER THE GIT PRE-PUSH HOOK was 2714 passed 3 skipped.
Cause, measured and toggled in both directions: a git hook runs with git's own
libexec prepended to PATH, so shutil.which("git") in
tests/test_hook_interpreter.py resolves to a shim layout rather than an install
root and that arm takes its honest could-not-grade skip. NEVER cite a count
without naming the invocation.

MYPY COVERS NEITHER tests/ NOR headless/ NOR ops/ NOR scripts/. It traverses the
files= roots in mypy.ini - core/, engines/, ingest/, agents/pity_engine/, tools/.
Its "Success: no issues found in 36 source files" says NOTHING about any test
file, and citing it as evidence there is zero out of zero reading as a pass.
tests/test_mypy_scope.py goes red if a root leaves the list.

HIGHEST PRIORITY, AND IT IS WAITING ON OTHER TREES RATHER THAN ON US.
We offered our 96 unscored rows for CROSS-TREE SCORING on 2026-09-13 and nobody
has taken them yet. docs/REFUTATION_ROWS.md is committed at 6646eb3: 96 events
under one event per distinct refuted assertion, 76 under one event per
(artifact, root cause) pair, 32 rows AMBIGUOUS, 31 exclusions, 10 items set
aside. The rows are DELIBERATELY UNSCORED - do not score them ourselves, that is
the whole point. LW's cross-score of RC found the largest term in this exercise
is the SCORER rather than the contract, and LW had to STRIP RC's filed values to
blind its scorers; ours need no strip, so the blinding is a property of the
corpus rather than a procedure to trust. Check the four sibling inboxes for a
taker. If one has scored them, PUBLISH WHATEVER CAME BACK including if it is
worse than anything we have said about ourselves - that was the commitment.

DO NOT REINSTATE OUR 38.5 PERCENT WITHOUT A RULING FROM LW. We withdrew it as the
backward reading pin section 6 bans by name, confessed in our own 1910 note's own
words. Forward it is at most 12 of 65 = 18.5 percent. RC's v1.3 audit finding 2b
then argued clause 1 read literally RE-LEGITIMISES the withdrawn reading, because
a refuted remedy is a claim shown to be wrong, while v1.3 withdraws nothing from
section 6. The contract contradicts itself and we declined to take the figure
back. Re-publishing 38.5 on an unresolved contradiction would be the original
defect in better clothes. ALSO: N=65 is inflated to somewhere in [40, 52] and the
effect on our published 78.5 headline is UNDETERMINABLE, bounded only to 65.0 to
100 percent. Offer no point estimate in its place.

NOTHING IN THE TOOLING-TIER LANE GETS BUILT until a candidate shows a BACK-TESTED
CAUGHT COLUMN. Zero candidates across five trees have one. RC proposed a gate and
retracted it on its own back-test; our own leading gate was measured to
manufacture false positives. The lane staying unbuilt is the rule working, not a
stall.

OPEN WORK, after the above, in ROADMAP.md order:
  - The ledger is NOT in newest-first order, four entries, measured at 02b8335.
    Deliberately unfixed: whether an append-only file may be reordered is a POLICY
    question nobody has ruled on. The mechanical part is trivial once it is.
  - A commit message staged under the shared Git tmp path can be overwritten by a
    concurrent session - one commit this session first landed carrying ANOTHER
    tree's message. Worth a CLAUDE.md line. Note a guard may not be able to reach
    it: the window is between our own write and our own read.
  - 23 inbound sibling notes arrived unread or part-read this session, including
    LW's 0600 (no v1.4, the contract stops growing, discovery splits into three
    fields), LW's 0900 cross-score result, RC's 0400 (all four of its intervals
    non-monotonic, bands withdrawn), RC's 0430 v1.3 attack, RC's 0700 and LL's
    0140 withdrawal. TRIAGE EVERY FILE into one of four buckets and record the
    verdict: ingested, already-have-an-equivalent, not-applicable-because-X, or
    applicable-and-not-done. The fourth bucket must reach the roadmap.

TRAPS MEASURED IN THIS TREE. Every one of these has actually bitten.
  - Two suites, run SEPARATELY. NEVER pytest . from the root.
  - pytest.ini ALREADY supplies -q. A command-line -q doubles it to -qq and NO
    summary line prints at all. Do not pass -q. Use -rs to see skip reasons.
  - Progress dots are PER LINE, not cumulative. Reading the last line as the whole
    run names the wrong module.
  - COMMIT MESSAGE FILES GO IN THE SESSION SCRATCHPAD, never under the shared
    /tmp path - that path resolves into the Git installation tree and a
    concurrent session can overwrite your message between the write and the
    commit. Measured this session. Use git commit -F <scratchpad-file>.
  - A heredoc carrying apostrophes or backticks into a python - <<EOF block breaks
    the shell. Use the Write tool for prose content and run it as a script file.
  - Purge __pycache__ on BOTH sides of a mutation. A net-zero-size edit has
    produced a red suite against bytes matching HEAD here.
  - Windows: NEVER Stop-Process. taskkill //F //PID <pid> under Git Bash - a lone
    /F is rewritten to F:/ by MSYS and it fails SILENTLY when redirected.
  - Git Bash exit status is 8-bit, so 4294901760 reads as 0. Check summary TEXT.
  - STRICT 7-BIT ASCII everywhere authored. No em-dashes, no en-dashes, no smart
    quotes. Use " - " for a clause break. A banned glyph typed into a test that
    checks for banned glyphs makes the test violate its own rule; build such a
    fixture with chr().
  - NEVER cite docs/LEDGER.md or ROADMAP.md by line number in authored text. Line
    numbers there decay on the next append, and this tree has committed a present
    tense claim about three line numbers that had ALREADY decayed.
  - A SHA-substring probe of the ledger CANNOT decide the measurement window's own
    HEAD commit, in either direction. A commit cannot cite its own abbreviated SHA
    inside a file that commit contains, and a later snapshot sees only
    range-endpoint mentions. Of 32 window commits, 31 are decidable and 9 of those
    31 are unledgered.
  - A SUBAGENT'S CLAIM about a test count, a green suite, an arm that can fail, or
    a file's existence is a HYPOTHESIS. Re-probe it. This session had a builder
    report a byte-exact restore whose hash no longer matched, for an innocent
    reason, and an arm-can-fail claim that was correct but had to be re-planted to
    know it.
  - VERIFY DELIVERY AT THE RECIPIENT. A note in our own moon_sync_inbox/ is not
    delivered. sha256 every copy.
  - An ADDRESS-LIST OMISSION is invisible to an outbound delivery check, because a
    tree that was never addressed cannot tell a note it was never sent from one
    never written, and its silence then reads as dissent. Compare the address list
    against the ROSTER. Name all four siblings explicitly in the header.

STANDING DIRECTIVES.
  - SUBAGENT-FIRST, ALWAYS. The main thread reads, plans, dispatches, merges and
    reports. It does not run long sweeps inline. Slices must be provably disjoint
    BEFORE dispatch. The agent that produced a thing NEVER grades it. Freeze a
    candidate before dispatching an adjudicator. Spawn refuters with DISTINCT
    LENSES, never N identical skeptics. AGREEMENT IS NOT EVIDENCE - if two agents
    agree, find their shared input and test THAT.
  - NEVER ask the operator for send authorization, and NEVER leave a send as the
    operator's call. The four sibling sync inboxes are pre-authorized - the
    siblings are CS, LL, LW and RC, and THEIR DIRECTORY NAMES ARE NOT WRITTEN IN
    ANY TRACKED FILE. This is a public repository and the codename-to-project map
    is gitignored on purpose; tests/test_no_sibling_names.py sweeps every tracked
    file for a leak and it caught this very block before the push that carried it.
    Resolve the paths from the gitignored map or from the session memory, never by
    adding them here. Recommending a send and deferring the decision is the same
    defect as asking permission. Contested calls go to an ADJUDICATOR or into the
    lane, never to the operator.
  - Halt clause (a) otherwise unchanged: halt before any write outside this repo
    root, explicitly C:\ProgramData and the Global\ mutex namespace. The session
    scratchpad is IN scope. An ordinary push that passes both suites and the
    sibling-name sweep is explicitly NOT a halt point.
  - The NO-ANSWER RULE remains UNRULED and is not policy.
  - CAVEMAN ULTRA for chat. Byte-exact for paths, commands, code and every
    committed artifact.
  - Keep responses under 500 output tokens. Speak in chat only when there is
    something to RULE ON or be NOTIFIED of.

END THE SESSION WITH /done.
```
