# Next session prompt

Paste the block below into a cold session. It is the hand-off, and
`tools/publish_next_session.py` reads it from this file rather than from a
retyped copy, so the printed block and the Desktop backup cannot disagree.

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

STATE OBSERVED 2026-09-14, AS A READING AND NOT A PROMISE. main clean and pushed,
0 worktrees. Measured in a SHELL invocation from the repo root:
  python -m pytest tests                      2721 passed, 2 skipped
  python -m pytest agents/pity_engine            80 passed
  python -m pytest tests/test_licence_posture.py 47 passed
  python -m pytest tests/test_docs_consistency.py 34 passed
  python scripts/qa_companion.py      17 passed, 0 failed, 2 skipped, 3 noted
  cd shell && node --test              52 pass, 0 fail
  python -m headless.runner --once --dry-run   exit 0, 0 pass 0 fail 6 skip
  python -m ruff check .               All checks passed
  python -m mypy                       Success, 36 source files - ADVISORY ONLY
  python tools/precommit_gate.py --scan-files README.md  selected=1 scanned=1
README.md is 561 lines, 0 non-ASCII bytes, 0 CR bytes.

THIS SESSION REWROTE THE PUBLIC README AND REFRESHED THE REPOSITORY METADATA.
README.md went 657 lines to 561: it now leads with a forecast captured from a
live engine run, carries a scannable SHIPPED / PARTIAL / PLANNED table, and puts
the forward-looking section directly under that table. The About description and
the topic list were changed through the GitHub API.

THE LESSON IS NOT THE README, IT IS THAT NO GUARD COULD SEE THE WORST DEFECT.
The draft was frozen and attacked by THREE passes with DISTINCT LENSES - rendered
visual, correctness, scope-and-loss - none run by the agent that wrote it. The
visual pass alone would have shipped it. The scope pass returned TEN LOSS
rulings. tests/test_readme_tree.py asserts every path NAMED in the tree exists
and is tracked, which is ONE-DIRECTIONAL, so five tracked files DELETED from the
block were invisible and both suites stayed green. Three of the five were the
only public disclosure of their own behaviour anywhere in the tree: a SECOND
scheduled task whose definition survives its window, a full-screen screenshot
cadence, and an out-of-repo desktop write. All restored by hand.

ONE ROADMAP ROW WAS FALSE AT BIRTH, not stale by decay. The Chronicled HTTP route
row said the engine models it and the route does not expose it. Measured: POST
{"banner":"chronicled"} returns HTTP 200 with a forecast identical to the direct
library call, and a bogus banner returns 400, because __main__.py builds its
banner map from every BannerKind. The row is closed. A rewrite that copies a
roadmap row forward inherits that row's defect.

A COUNT READ OFF SOURCE IS NOT A COUNT OBSERVED FROM THE FUNCTION. The merging
thread passed down 2 READY / 2 PARTIAL / 2 NOT_WIRED for the dashboard, taken
from an adversary reading surface/model.py. The fix slice MEASURED it through
build_dashboard(AccountState(uid=''), now) and a fresh clone renders 2 READY,
0 PARTIAL, 4 NOT_WIRED. The subagent corrected the merger; take that seriously.

AN AUDIT BRIEF CAN CARRY ITS OWN INSTRUMENT DEFECT. The visual audit was
dispatched with mode=gfm, which is GitHub's COMMENT renderer: it injected 151
spurious line breaks and stripped every heading id, manufacturing three confident
false findings. mode=markdown is correct, and its heading ids carry a
user-content- prefix that GitHub's frontend strips - a checker blind to the
prefix reads a false zero. State which renderer any future rendered check used.

DO NOT REINSTATE 78.5, AND DO NOT ADOPT LW'S 74.0 / 75.0 IN ITS PLACE. They are
not the same object and LW's rests on the same broken boundary. Our 38.5 pct
stays WITHDRAWN as the backward reading section 6 bans by name. Forward it is at
most 12 of 65 = 18.5 pct. N=65 is inflated to somewhere in [40, 52]. Offer no
point estimate.

NOTHING IN THE TOOLING-TIER LANE GETS BUILT until a candidate shows a BACK-TESTED
CAUGHT COLUMN. Still zero candidates across five trees. The lane staying unbuilt
is the rule working, not a stall.

OPEN WORK, in ROADMAP.md order:
  - A TRACKED FILE DELETED FROM THE README TREE BLOCK IS INVISIBLE TO EVERY
    GUARD. A naive reverse arm is WRONG - the block is a curated public summary,
    so demanding every tracked file appear would be deleted within a session. The
    candidate is a NAMED WATCHLIST of load-bearing disclosures. Closes only when
    a planted deletion is observed RED.
  - THE ABOUT DESCRIPTION AND TOPIC LIST ARE PUBLIC SURFACE NO GUARD CAN SEE.
    Same shape as the gitignored inbox - the guards derive their corpus from
    git ls-files. Undecided whether to mirror them into a tracked file.
  - OUR 96-ROW CORPUS HAS A MEASURED INSTRUMENT DEFECT and must not be re-offered
    to anyone until PROXY-MEASURE and ADVERSARY are repaired or retired.
  - Our own adversarial method MISSED the tie-breaker defect driving 83 pct of
    the disagreements on our own rows. A method finding, not a row finding.
  - RECENCY is a fourth unnamed knob, per LW's own convention defect.
  - No convention covers a sibling writing into this tree.
  - The ledger is NOT in newest-first order, FOUR entries. Deliberately unfixed:
    whether an append-only file may be reordered is a POLICY question nobody has
    ruled on.
  - 13 applicable-and-not-done items from the triage of 44 inbound notes are in
    docs/INBOX_TRIAGE_2026-09-13.md. That document publishes 14 ITEMS against 13
    FILES - different populations.
  - Roster rule is PROSE ONLY, no mechanism, and structurally unreachable by any
    git ls-files-derived guard because moon_sync_inbox/ is gitignored.
  - The largest product unlock is unglamorous: first-hand observed cost tables.
    data/costs/ holds a contract README and ZERO data rows, so the objective DAG,
    the scheduler and the plan panel emit zeros until those rows exist.

TRAPS MEASURED IN THIS TREE. Every one has actually bitten.
  - Two suites, run SEPARATELY. NEVER pytest . from the root.
  - pytest.ini ALREADY supplies -q. A command-line -q doubles it to -qq and NO
    summary line prints. Do not pass -q. Use -rs to see skip reasons.
  - NEVER pipe a suite through tail or head - that consumes the exit status.
    Redirect to a file and read the file.
  - A GUARD CANNOT SEE AN UNTRACKED FILE, and the README tree guard cannot see a
    DELETION. Stage first, then believe the gate, and do not read a green suite
    as evidence about something nothing asserts.
  - A BARE precommit_gate.py run is a VACUOUS PASS - clean index, zero files
    scanned, exit 0. The arm that MEASURES is --scan-files with --expect-count.
  - README.md must stay at 318 lines or more. docs/LEDGER.md carries the
    citation README.md:317-318 and a guard requires it to resolve in range. That
    citation is already historically decayed; only the FLOOR matters.
  - write_text emits CRLF on Windows and .gitattributes declares eol=lf, so git
    diff looks CLEAN while the line-endings test stays red. Check b.count(b'\r').
  - grep -c 'C:\Resin Compute' README.md returns 0 under Git Bash while the
    literal IS present. Count it in Python.
  - COMMIT MESSAGE FILES GO IN THE SESSION SCRATCHPAD, never a shared /tmp path -
    that path resolves into the Git installation tree and a concurrent session
    can overwrite your message between the write and the commit. No hook can
    catch this: the window closes before git commit is invoked.
  - Progress dots are PER LINE, not cumulative.
  - Purge __pycache__ on BOTH sides of a mutation.
  - Windows: NEVER Stop-Process. taskkill //F //PID <pid> under Git Bash.
  - Git Bash exit status is 8-bit, so 4294901760 reads as 0. Check summary TEXT.
  - STRICT 7-BIT ASCII everywhere authored. Build a banned-glyph fixture with
    chr(0x2014), never a literal. No emoji in any .md, including the README.
  - NEVER cite docs/LEDGER.md or ROADMAP.md by line number.
  - A SUBAGENT'S CLAIM about a count, a green suite or a file's existence is a
    HYPOTHESIS. Re-probe it. This session a subagent corrected the MERGER.
  - VERIFY DELIVERY AT THE RECIPIENT. sha256 every copy. A note in our own
    moon_sync_inbox/ is not delivered.
  - An ADDRESS-LIST OMISSION is invisible to an outbound delivery check. Name all
    four siblings explicitly in the header.

STANDING DIRECTIVES.
  - SUBAGENT-FIRST, ALWAYS. The main thread reads, plans, dispatches, merges and
    reports. Slices must be provably disjoint BEFORE dispatch. The agent that
    produced a thing NEVER grades it. Freeze a candidate before dispatching an
    adjudicator. Spawn refuters with DISTINCT LENSES. AGREEMENT IS NOT EVIDENCE.
  - FULL AUTHORITY, reconfirmed by the operator 2026-09-14: adjudicate, do not
    ask. Contested calls go to an ADJUDICATOR or into the lane, never upward.
  - NEVER ask the operator for send authorization. The four sibling sync inboxes
    are pre-authorized - siblings are CS, LL, LW and RC, and THEIR DIRECTORY
    NAMES ARE NOT WRITTEN IN ANY TRACKED FILE. Resolve paths from the gitignored
    map on disk.
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
