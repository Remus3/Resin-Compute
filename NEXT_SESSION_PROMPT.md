# Next session prompt

The fenced block below is the hand-off. It is published to the Desktop by
`python tools/publish_next_session.py`, which reads THIS file and refuses on
anything other than exactly one fenced block, on non-ASCII, or on a block under
2000 bytes. Edit the block here; never retype it anywhere else.

```
RSC - next session, HEADLESS, operator AWAY.

Repo: C:\Resin Compute (github.com/Remus3/Resin-Compute). Counterparty: RC.
CS, LW and LL are on ORDERED STANDBY - silence is NOT dissent, do not write
into their trees.

READ FIRST: CLAUDE.md, README.md, docs/SPEC_SCAFFOLD.md, ROADMAP.md,
docs/LEDGER.md, git log. Before planning any character build read
docs/GOAL_SPEC_SEED_TEAM.md. Before adding a data source read
docs/LICENSE_NOTES.md. Before re-litigating read docs/adr/README.md.

DO NOT RE-DERIVE GACHA CONSTANTS. Verified in docs/SPEC_SCAFFOLD.md section 3,
corrections in ADR-003. 50/50 is 55.000% consolidated since 5.0. Weapon
soft-pity saturates at pull 77 under a 7% increment. 1.600% is 1/E[wishes per
5-star], NEVER a per-wish Bernoulli parameter.

OPERATOR AWAY. NO BLOCKING QUESTIONS. Where you would escalate, dispatch an
ADJUDICATOR and record the ruling in ROADMAP.md MARKED PLAINLY AS AN
ADJUDICATED CALL. SEVEN stand: the conftest non-128 disposition, the
2026-09-09 MIXED ruling on the os.name-forcing arms, the do-not-widen ruling
on the mkdir ValueError sites, the OVERTURN of that ruling for ONE site only,
the MIXED ruling on the dev-pin guard shape, the gate REFERENT (broad reading)
and slice B as MERGED-REDUCED. Read before touching any of them.

DO NOT ARM ANYTHING. RC disarmed, hop budget spent, task Disabled. Verified
DORMANT this session via ops/check_task_liveness.py, exit 1.

GATES, in /done order, EACH AS ITS OWN COMMAND. Chaining with && reports only
the LAST link.
  python -m pytest tests/test_licence_posture.py
  python -m pytest tests/test_docs_consistency.py
  python scripts/qa_companion.py
  python -m ruff check .
  python -m pytest tests
  python -m pytest agents/pity_engine
  cd shell && node --test
  python -m headless.runner --once --dry-run
DO NOT PASS -q ON THE COMMAND LINE. pytest.ini already sets -q; a second makes
it -qq and suppresses the count.

STATE AS OBSERVED 2026-09-09 at 1c596e3, a reading not a promise. RE-MEASURE.
  pytest tests   1840 passed, 1 skipped     agents/pity_engine   80 passed
  node --test    52 pass 0 fail             headless / ruff / qa / licence / docs  exit 0
  mypy 34 source files. Census 77 arms, up from 43 at session start.
  tests/test_gate_mutation_runner.py new at 47. 1793 + 47 = 1840, closes.
  CHECK EVERY SESSION: gh run list --limit 5
  THE SAME SUITE REPORTS A DIFFERENT SKIP COUNT UNDER THE PRE-PUSH HOOK, and
  it is not a regression. Measured at 9be52cc: 1840 passed 1 skipped from an
  ordinary shell, 1839 passed 2 SKIPPED under pre-push. The extra skip is
  tests/test_hook_interpreter.py:1802 - under the hook, git is invoked as the
  git-core shim at Git\mingw64\libexec\git-core\git.exe, which sits at no
  layout that oracle recognises as an install, so it skips rather than
  guessing. DO NOT reconcile the two counts by editing either one; they are
  two environments and the skip reason says so.

1. THE HIGHEST-VALUE ROW IN ROADMAP.md: EIGHT GATES ARE EXERCISED BY NOTHING.
   Measured at 1c596e3 by python -m tools.gate_mutation_runner - 35 mutants,
   27 killed, 8 SURVIVED, 0 false kills, exit 1. A survivor left the WHOLE
   application suite green with that gate neutralised.
     no-destination/if-false        workspace-trust/if-false
     refusal-recorded/if-false      bounce-mark/if-true
     bounce-write-all/operand-1     bounce-write-all/operand-2
     delivery-write-all/operand-1   delivery-write-all/operand-2
   FIX delivery-write-all/operand-1 FIRST. It drops the bool(written) term the
   responder's own comment at tools/moon_sync_responder.py:1861-1863 calls the
   guard and not decoration - the term that stops all([]) reporting a delivery
   to ZERO DESTINATIONS as delivered. THE WORK IS ARMS, NOT A FIX: the gates
   are correct, nothing drives them. VERIFY WITH THE RUNNER, NOT BY EYE -
   python -m tools.gate_mutation_runner --gate delivery-write-all runs one
   gate, and a survivor becoming a kill is the proof the arm lands.

2. THE GATE CENSUS IS AT STEP TWO OF THREE. Step one tagged 18 sites
   (c372861). Step two is tools/gate_mutation_runner.py (1c596e3). STEP THREE
   IS THE REGISTRY and is unstarted. Order is still strictly sequential;
   building companions first ships a VACUOUSLY GREEN apparatus.
   TWO EXCLUSIONS, TWO REASONS, and do not merge them: SELF_TEST_MODULE is a
   module that decides its own verdict; SHAPE_GRADER_MODULES is a module that
   grades the TARGET FILE'S SHAPE, which answers a syntax question while the
   runner asks a behaviour one. An --ignore of a MISSING path is a SILENT
   NO-OP, so verify_exclusions raises before any campaign.

3. THE CAMPAIGN WAS WRONG TWICE AND BOTH ERRORS WERE FOUND BY MEASUREMENT.
   First run said 35/35 KILLED and measured NOTHING - the runner's own test
   module sorts ahead of the responder's and decided every verdict under -x.
   The tell was the WALL CLOCK: 35 full-suite runs in 3 minutes is impossible
   unless every run aborted early. Second run said 31/4 and FOUR were FALSE
   KILLS - the census reads the responder AT IMPORT and grades its AST SHAPE,
   so a dropped BoolOp operand reddens it for a non-behavioural reason. All
   four scored 32 of 32 failing nodes in the census, ZERO elsewhere, and
   survive at 1716 passed 1 skipped once it is ignored.

4. FILED, NOT FIXED, and NOT a regression: core/atomic_io.py leaks a 0-byte
   temp file when the write fails with anything that is not an OSError -
   _discard(tmp) sits INSIDE the except OSError at line 100. The sibling
   atomic_write_json's docstring advertises the opposite property. Untouched
   because that module is the only sanctioned state-write path.

5. RESIDUALS, each with its measurement in ROADMAP.md. RE-PROBE BEFORE
   SPENDING A SLICE - a residual is a claim with a date and it decays.
   - The evidence ledger TRIMS rather than rotates (tools/moon_sync_responder.py:1037).
   - Which ledger instance is live has never been CHECKED here.
   - Nothing guards the SENDER side against editing a note after delivery.
   - The sweep floor's VALUE is ungraded: _MIN_TRACKED_PATHS 100 -> 10 leaves
     the suite green. Pre-existing blindness, not a regression.
   - Half of tests/test_conftest_skip_path_pinned.py is DEAD as shipped.
   - Nothing inspects the pre-push hook's OUTPUT. The arms are a token scan.
   - ops/ResinCompute-Supervisor.xml never registered, Exec argv graded by
     nothing.
   - THREE hand-typed transcriptions of one reason wording exist and NOT ONE
     derives from a CONSUMER's stated requirement.

6. UNGRADED AND HONEST ABOUT IT, in the census: whether each of the 18 tag
   NAMES describes the site it sits above. The collision arities are a SAMPLE
   not a proof - a wrong conjunct agreeing with the real one on a clean
   source, one collision, two collisions and three-on-a-line still passes. The
   depth arm bounds reported[:n] only for n BELOW the tag count. The runner's
   27 kills are attributed by parsing the FIRST failure under -x, which names
   the killer but is not proof no other test would also have failed.

7. PRE-EXISTING AND NOT OURS: in a git archive extract the whole suite is
   EXIT=1 for the BASELINE too. An extract and a shallow clone are NOT one
   population. 25 stale worktrees under .claude/worktrees/.

SESSION SHAPE is orchestrated, multi-agent, self-adjudicating, self-adversarial
by DEFAULT. The agent that produced a thing NEVER grades it. FREEZE THE
CANDIDATE before dispatching a grader. Spawn refuters with DISTINCT LENSES.
AGREEMENT BETWEEN TWO AGENTS IS NOT EVIDENCE - find their shared input and test
THAT.

THE METHOD LESSONS THAT PAID OFF MOST THIS SESSION.

- FOUR TIMES AN AGENT CORRECTED THE INSTRUCTION IT WAS GIVEN, and every one of
  those corrections was right. One measured that the brief's k = 1,2,3 does NOT
  kill reported[:3] and added the arm the brief had not asked for. One declined
  to ship a refuter's measurement it could not reproduce and shipped the weaker
  verified claim instead. One derived a disputed count itself and disagreed
  with both the refuter and the earlier builder. One STOPPED and wrote nothing
  when its worktree came up at the wrong commit. WHEN A REFUTER SAYS A BUILDER
  WAS WRONG, CHECK WHO WROTE THE INSTRUCTION FIRST.
- A SHAPE ARM PINS FORMAT, NOT INPUT, and it cost TWO rounds here. An arm
  proving a conjunct is welded pinned a phrase the message emits
  UNCONDITIONALLY, so a coincidental proxy passed all 69. The repair defeated
  ONE literal and a further lens found SEVEN more conjuncts passing all 71,
  failing in OPPOSITE directions - some green on a source with two real
  collisions, some reddening a CLEAN fully tagged responder. PIN IDENTITY AT
  MORE THAN ONE ARITY, and always include an OVER-FIRE control.
- FIVE DISTINCT LENSES FOUND FIVE CLASSES OF DEFECT AND NO TWO OVERLAPPED.
  Vacuity, prose-truth, false-green, does-it-reproduce, equivalent-mutant.
  The reproduce lens is the one that found the four false kills, and nothing
  in any report could have shown it.
- A MODULE'S WRITTEN CLAIM ABOUT ITS OWN LIMITS IS A TESTABLE ASSERTION. EIGHT
  false ones were corrected this session, on top of four the session before.
- THE DOCS GUARDS CATCH THE MERGER EVERY SESSION. Run test_docs_consistency.py
  AND test_docs_hook_commands.py after ANY doc edit.

TRAPS THAT ACTUALLY BIT, every one measured.

- A WORKTREE MATERIALISES AT AN ANCESTOR OF THE DECLARED FORK POINT. It fired
  on FOUR of five dispatches today. Put an explicit `git merge --ff-only <sha>`
  in every brief PLUS an assertion on the materialised bytes - a line count and
  a grep for a symbol that exists only at the intended commit. A dispatch
  without it is the defect, not the builder.
- UNCOMMITTED SLICE WORK IS INVISIBLE TO THE NEXT WORKTREE. A repair builder
  must be told to `cp` the predecessor's files in by absolute path.
- A NET-ZERO-BYTE-SIZE mutate-and-restore WITHIN THE SAME SECOND runs the
  MUTANT'S BYTECODE against restored source. Purge __pycache__ AND
  .pytest_cache on BOTH sides; prefer a replacement of different length.
- NEVER `git checkout --` to restore a mutation. Restore from saved bytes and
  verify by sha256. Responder is 02469d15...b87f94.
- `assert source.count(old) == 1` before substituting.
- A QUOTED HEREDOC STILL MANGLES BACKSLASHES. Write .py with the editor tools.
- write_text EMITS CRLF ON WINDOWS and .gitattributes eol=lf hides it. tests/
  is OUTSIDE test_no_crlf_writers.py's corpus, so nothing catches it there.
- grep -c '[^\x00-\x7F]' IS NOT A CHARACTER CLASS. It reported 1785 non-ASCII
  lines in a file with ZERO non-ASCII bytes. Check bytes IN PYTHON.
- SendMessage IS DISABLED. A running agent CANNOT be amended - dispatch a new
  disjoint slice.
- AN AGENT CAN LOOP ON STALE `sleep` WAIT-BLOCKS AFTER FINISHING, burning
  tokens and re-notifying. TaskStop it once its report has landed.
- A NEW TEST FILE MUST BE `git add`ed BEFORE test_docs_consistency.py passes
  once ROADMAP.md backticks it - the guard checks git-tracked.
- The default `python` here is 3.14, not 3.11. CI runs 3.11.
- An empty pytest parametrize is `1 skipped`, exit 0, NOT a failure.
- pytest.raises(Exception) DOES NOT CATCH Skipped - BaseException-derived.
- A FLOOR IN A SEPARATE ARM LEAVES THE PRIMARY ARM VACUOUS. One assertion.
- A PYTEST PROGRESS LINE IS 72 DOTS, NOT THE WHOLE RUN.
- exit=$? AFTER A PIPE READS THE LAST PIPE STAGE. Redirect to a file.
- mypy files= covers core/, engines/, ingest/, agents/pity_engine/, tools/
  ONLY - its Success is ZERO OUT OF ZERO about tests/ or scripts/.
- NEVER NAME A SIBLING PROJECT IN PLAIN TEXT. RC, CS, LW, LL, RSC.
- Never Stop-Process. taskkill //F //PID under Git Bash.
- NEVER ADD A Co-Authored-By TRAILER, and never file its absence as a defect.

CHECK TASK LIVENESS WITH THE CHECKER, NEVER A STATE STRING, NEVER THROUGH A PIPE:
  python ops/check_task_liveness.py ResinCompute-Responder
Exit 0 LIVE, 1 DORMANT, 2 ABSENT, 3 UNKNOWN, 4 AMBIGUOUS. Observed 1 DORMANT.
KILL SWITCH: powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove

DO NOT REDO: the slots.py re-pin (closed 71fa2a68), manifest-as-key (withdrawn),
the caveman dialect question (settled), wenyan (reverted 2026-06-27). Do not
hunt mutants M1-M11 - only M12 exists. Do not re-derive the two ceilings in
docs/LEDGER.md. Do not re-litigate the seven adjudicated calls without reading
them first. Do not re-sweep the mkdir sites. Do not rebuild the git-reason
hand-typed fixture. Do not re-open the census REFERENT - _is_a_consult_site was
adjudicated at c372861 and WIDENING A MATCHER is the response this tree has
been defeated by three times.

Keep chat under 500 output tokens, CAVEMAN ULTRA, 7-bit ASCII, no em-dashes, no
en-dashes, no smart quotes.
```
