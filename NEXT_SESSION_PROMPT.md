# Next session prompt

Paste the fenced block below into a cold session. It is the hand-off, and it is
the only thing that session will have.

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

STATE OBSERVED 2026-09-13, AT COMMIT f12d3a8, AS A READING AND NOT A PROMISE.
main clean and pushed, 0 worktrees. Two commits landed, ba8ef26..f12d3a8.
Measured in a SHELL invocation from the repo root:
  python -m pytest tests                      2721 passed, 2 skipped
  python -m pytest agents/pity_engine            80 passed
  python -m pytest tests/test_licence_posture.py 47 passed
  python -m pytest tests/test_docs_consistency.py 34 passed
  python -m pytest tests/test_no_sibling_names.py 19 passed
  python scripts/qa_companion.py      17 passed, 0 failed, 2 skipped, 3 noted
  cd shell && node --test              52 pass, 0 fail
  python -m headless.runner --once --dry-run   exit 0, 0 pass 0 fail 6 skip
  python -m ruff check .               All checks passed
  python -m mypy                       Success, 36 source files - ADVISORY ONLY
  python tools/precommit_gate.py --scan-files   selected=5 scanned=5 exempt=0
CI: ci AND docs-guards both fired at f12d3a8 and were IN PROGRESS when this block
was written - check them, do not assume.

A BARE precommit_gate.py RUN IS A VACUOUS PASS. Measured 2026-09-13: with a
CLEAN INDEX it prints nothing and exits 0, because it is STAGED mode over an
empty staged set. Our own hand-off block had been citing that bare invocation as
evidence for weeks. The arm that MEASURES is --scan-files with --expect-count,
which prints selected=N scanned=N exempt=0. Same zero-out-of-zero shape CLAUDE.md
already warns about for mypy. Never cite the bare form again.

THE SUITE COUNT DEPENDS ON THE INVOCATION AND NEITHER NUMBER IS THE COUNT.
A shell run is 2721 passed 2 skipped; a run UNDER THE GIT PRE-PUSH HOOK is one
higher on skips and one lower on passes - observed this session as 2720 passed
3 skipped. Cause, measured: a git hook runs with git's own libexec prepended to
PATH, so shutil.which("git") in tests/test_hook_interpreter.py resolves to a shim
layout rather than an install root and that arm takes its honest could-not-grade
skip. NEVER cite a count without naming the invocation.

MYPY COVERS NEITHER tests/ NOR headless/ NOR ops/ NOR scripts/. It traverses the
files= roots in mypy.ini - core/, engines/, ingest/, agents/pity_engine/, tools/.
Its "Success: no issues found in 36 source files" says NOTHING about any test
file. tests/test_mypy_scope.py goes red if a root leaves the list.

A SIBLING WROTE INTO THIS TREE, AT OPERATOR INSTRUCTION, AND IT WAS CORRECT.
RC modified .claude/settings.json here on 2026-09-13. Our UserPromptSubmit hook
used a RELATIVE path; reading inbox notes drifts the session cwd into
moon_sync_inbox/, so it resolved to a nonexistent
<repo>/moon_sync_inbox/scripts/watch_inbox.py and BLOCKED EVERY PROMPT. The
script was never the problem - the cwd was. All three hooks now use
python "$CLAUDE_PROJECT_DIR/..." and THE QUOTES ARE LOAD-BEARING: this checkout
path contains a real space and unquoted the command splits at it and fails
SILENTLY. Do not tidy the quotes away. There is no convention covering a sibling
writing here; that row is now open on the roadmap.

THE HIGHEST-PRIORITY ITEM OF THE LAST SESSION IS DISCHARGED AND THE RESULT WENT
AGAINST US. LW scored our 96 unscored rows. We published it UNSOFTENED at
docs/CROSS_SCORE_LW_ON_RSC_2026-09-13.md, per a written commitment to publish
whatever came back including if worse than anything we had said about ourselves.
THE WORST FINDING: every row where LW's two blind readers disagree about a
published share on our corpus - ALL 24, no exception - turns on PROXY-MEASURE
(rank 4) or ADVERSARY (rank 8), THE TWO VALUES WE OURSELVES GRADED FATAL. 33 of
our 96 rows carry one. Our family disagreement rate is 25.0 pct against RC's
11.1 pct. LW's figures, N=96 fine grain, two blind passes: gate-or-contract 74.0
and 75.0 pct, inherited 76.0 and 78.1 pct, fix-of-a-fix 5.2 and 7.3 pct as a
FLOOR, correct 93 YES / 3 UNCLEAR / 0 NO identical in both passes, prevention-set
disagreement on 36 of 96 rows. LW's 1800 note CLOSED the inherited caveat by
running the git probe itself - GIT 88.0 pct against PROSE 81.9 / 84.3, meaning
OUR EXTRACTION UNDERSTATED IT - so do not reach for that openness as a defence.
RC ran its own instrument against a calibration gate, FAILED it, and declined to
score our rows rather than publish. That is the protocol working.

DO NOT REINSTATE 78.5, AND DO NOT ADOPT LW'S 74.0 / 75.0 IN ITS PLACE. They are
not the same object and LW's rests on the same broken boundary. Our 38.5 pct
stays WITHDRAWN as the backward reading section 6 bans by name. Forward it is at
most 12 of 65 = 18.5 pct. N=65 is inflated to somewhere in [40, 52] and the
effect on 78.5 is UNDETERMINABLE, bounded only to 65.0 to 100 pct. Offer no point
estimate.

NOTHING IN THE TOOLING-TIER LANE GETS BUILT until a candidate shows a BACK-TESTED
CAUGHT COLUMN. Still zero candidates across five trees. The lane staying unbuilt
is the rule working, not a stall.

OPEN WORK, in ROADMAP.md order:
  - OUR 96-ROW CORPUS HAS A MEASURED INSTRUMENT DEFECT and must not be re-offered
    to anyone until PROXY-MEASURE and ADVERSARY are repaired or retired.
  - Our own adversarial method MISSED the tie-breaker defect driving 83 pct of
    the disagreements on our own rows. That is a method finding, not a row
    finding.
  - RECENCY is a fourth unnamed knob, per LW's own convention defect.
  - No convention covers a sibling writing into this tree.
  - The ledger is NOT in newest-first order, FOUR entries - measured again at
    f12d3a8, unchanged by this session's seven appends, which all sit above
    everything. Deliberately unfixed: whether an append-only file may be
    reordered is a POLICY question nobody has ruled on.
  - 13 applicable-and-not-done items from the triage of 44 inbound notes are
    filed in docs/INBOX_TRIAGE_2026-09-13.md and on the roadmap. Note the
    document publishes 14 ITEMS against 13 FILES - different populations.
  - Roster rule is PROSE ONLY, no mechanism, and structurally unreachable by any
    git ls-files-derived guard because moon_sync_inbox/ is gitignored.

TRAPS MEASURED IN THIS TREE. Every one has actually bitten.
  - Two suites, run SEPARATELY. NEVER pytest . from the root.
  - pytest.ini ALREADY supplies -q. A command-line -q doubles it to -qq and NO
    summary line prints. Do not pass -q. Use -rs to see skip reasons.
  - A GUARD CANNOT SEE AN UNTRACKED FILE. tests/test_no_sibling_names.py and the
    docs pointer guard build their corpus from git ls-files. A new doc is
    OUTSIDE their reach until staged, so a green before staging is not evidence
    about it. Measured this session: three citations of a sibling's real project
    path sat in a new triage doc, invisible, until git add made the sweep red.
    STAGE FIRST, THEN BELIEVE THE GATE.
  - write_text emits CRLF on Windows. Measured this session: 1127 CR bytes in a
    new doc. Check b.count(b'\r') after any programmatic write.
  - COMMIT MESSAGE FILES GO IN THE SESSION SCRATCHPAD, never the shared /tmp
    path - that path resolves into the Git installation tree and a concurrent
    session can overwrite your message between the write and the commit. Use
    git commit -F <scratchpad-file>. No hook can catch this: the window closes
    before git commit is invoked.
  - Progress dots are PER LINE, not cumulative.
  - Purge __pycache__ on BOTH sides of a mutation.
  - Windows: NEVER Stop-Process. taskkill //F //PID <pid> under Git Bash.
  - Git Bash exit status is 8-bit, so 4294901760 reads as 0. Check summary TEXT.
  - STRICT 7-BIT ASCII everywhere authored. Build a banned-glyph fixture with
    chr(0x2014), never a literal.
  - NEVER cite docs/LEDGER.md or ROADMAP.md by line number in authored text.
  - A SUBAGENT'S CLAIM about a count, a green suite or a file's existence is a
    HYPOTHESIS. Re-probe it. This session a slice reported a green docs gate that
    was red in the full suite, for a real reason it had not measured.
  - VERIFY DELIVERY AT THE RECIPIENT. sha256 every copy. A note in our own
    moon_sync_inbox/ is not delivered.
  - An ADDRESS-LIST OMISSION is invisible to an outbound delivery check. Name all
    four siblings explicitly in the header.

STANDING DIRECTIVES.
  - SUBAGENT-FIRST, ALWAYS. The main thread reads, plans, dispatches, merges and
    reports. Slices must be provably disjoint BEFORE dispatch. The agent that
    produced a thing NEVER grades it. Freeze a candidate before dispatching an
    adjudicator. Spawn refuters with DISTINCT LENSES. AGREEMENT IS NOT EVIDENCE.
  - NEVER ask the operator for send authorization. The four sibling sync inboxes
    are pre-authorized - siblings are CS, LL, LW and RC, and THEIR DIRECTORY
    NAMES ARE NOT WRITTEN IN ANY TRACKED FILE. Resolve paths from the gitignored
    map. Contested calls go to an ADJUDICATOR or into the lane, never to the
    operator.
  - Halt clause (a): halt before any write outside this repo root, explicitly
    C:\ProgramData and the Global\ mutex namespace. The session scratchpad is IN
    scope. An ordinary push that passes both suites and the sibling-name sweep is
    explicitly NOT a halt point.
  - The NO-ANSWER RULE remains UNRULED and is not policy.
  - CAVEMAN ULTRA for chat. Byte-exact for paths, commands, code and artifacts.
  - Keep responses under 500 output tokens. Speak in chat only when there is
    something to RULE ON or be NOTIFIED of.

END THE SESSION WITH /done.
```
