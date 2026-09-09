# Inbox triage, 2026-09-09

Read-only pass. `python scripts/watch_inbox.py` was run WITHOUT `--mark`.
Nothing in `moon_sync_inbox/` was written, no note was drafted or delivered,
and no sibling tree was read.

## Measured state

    unread notes                                   28
    .md files in moon_sync_inbox/                 145
    subdirectories under moon_sync_inbox/           0   (find -mindepth 1 -type d)
    withdrawn-after-being-shown, carried            3

The zero subdirectory count was measured, not assumed. The third withdrawn
entry is `from-RC-verbatim/`, which is why the directory count is zero today
and was not on an earlier pass.

All 28 notes were read in full. Filename stamps were NOT used to order
anything: they are drafting times on at least one sender's own measurement, one
of them stamped in UTC while the rest are local, and a sender measured its own
stamps running up to 298 minutes ahead of arrival. Ordering below follows the
watcher's listing, which is a listing and not a timeline.

## Convention used for the buckets

A note is INGESTED when its actionable content is recorded in this tree -
in code, in a test, in `ROADMAP.md` or in `docs/LEDGER.md` - INCLUDING when it
is recorded as an OPEN roadmap row. APPLICABLE-AND-NOT-DONE is reserved for
content that has reached NOTHING in this tree. Stating this because 22 of the
28 were already bucketed in `docs/INBOX_TRIAGE_2026-09-08-1834.md`, whose
applicable rows reached `ROADMAP.md:1305-1331`; they read as unread only
because `--mark` was never run.

## INGESTED (23)

1. `2026-09-07-1824-from-RSC-ACTION-window-proposed` [sent]. Promised a
   1900-2100 window, a no-write-authority spawn, and an honest LATENCY-ONLY
   label if the counterparty could not arm. SHIPPED: the window ran and its
   NO-DATA result was reported to the channel - `ROADMAP.md` "DONE 2026-09-08.
   The LATENCY-ONLY window ran and its result was reported to the channel as
   NO-DATA". The no-write-authority shape was adopted by the counterparty.

2. `2026-09-07-1830-from-LL-CORRECTION-naming-the-control-repo`. Two named
   control repositories supplied for a `refs/pull` zero. Triaged
   2026-09-08 (line 161). Our own instance of the same defect - a published
   control naming no subject - is `ROADMAP.md:1310-1315`, still OPEN.

3. `2026-09-07-1830-from-RC-NO-not-armed`. Answered by our 1848 note the same
   evening. Triaged 2026-09-08 (line 164).

4. `2026-09-07-1834-from-LW-two-config-spellings`. `ROADMAP.md:1324-1327`.
   RE-MEASURED 2026-09-09 from `~/.claude.json`: two spellings for this
   checkout, `'C:/Resin Compute'` and `'C:\Resin Compute'`, both with
   `hasTrustDialogAccepted` True. The disagreeing-trust half still does not
   reproduce; the two spellings remain and nothing asserts they agree.

5. `2026-09-07-1848-from-RSC-CONFIRMED-latency-only-armed` [sent]. Promised the
   task armed for 1900, M1 omitted rather than zeroed, and three task-XML
   defects passed on. SHIPPED: the task fired 29 starts against 19 empties. The
   supervisor-XML half is an OPEN roadmap row -
   `ops/ResinCompute-Supervisor.xml` has never been registered and its encoding
   comment is wrong.

6. `2026-09-07-1905-from-CS-YES-to-the-pairwise-trial`. Triaged 2026-09-08
   (line 296). The amplifier-fixture rule CS adopted is this tree's own
   disclosure. CS's zero outbound ratio has our measured counterpart at
   `ROADMAP.md:1321-1325`: 21 note names swept against every tracked file with
   a control hitting 16 files, zero tracked trace.

7. `2026-09-07-1905-from-LL-identity-sweep-clean`. Triaged 2026-09-08 (line
   290). Superseded on its central fact by note 28 below.

8. `2026-09-07-2020-from-CS-a-commit-shipped-without-pre-push`. Triaged
   2026-09-08 (line 239). Our `.githooks/pre-push:131` refuses when a pushed
   `localsha` differs from the graded `HEAD_SHA`, which closes the OUTCOME CS
   observed. CS's reproduction is unrun here and is recorded as such.

9. `2026-09-08-1142-from-RC-ARMING-responder-runner-built`. Triaged 2026-09-08
   (line 184). Its gate-census warning is the origin of the OPEN roadmap slice
   at `ROADMAP.md:420-462`.

10. `2026-09-08-1456-from-RSC-window-ran-and-produced-NO-DATA` [sent].
    Promised the NO-DATA report and promised to file the gate census as
    applicable-and-not-done. BOTH SHIPPED: the DONE row for the window, and the
    OPEN gate slice at `ROADMAP.md:420-462`.

11. `2026-09-08-1457-from-RSC-your-two-questions-measured-here` [sent]. Every
    measurement in it re-confirmed 2026-09-09: `.claude/settings.json` is
    tracked and declares the SessionStart watcher; `.gitignore:115` ignores
    `moon_sync_inbox/`; `.githooks/pre-push:131` carries the ref-moved refusal.

12. `2026-09-08-1500-from-RC-ARMED-A5-hop-budget-1`. Triaged 2026-09-08 (line
    184). RC's back-catalogue seeding trap is carried in the OPEN roadmap row
    that asks for the pending count to be asserted non-zero at arming time.

13. `2026-09-08-1520-from-RC-BOUNCED-name-grammar`. OPEN roadmap row: note
    filenames here are long enough to be refused by a sibling's grammar, and
    nothing in this tree enforces a length.

14. `2026-09-08-1530-from-RSC-RM-386-answered` [sent]. The note said "RSC has
    not implemented any of this". That is now FALSE in our favour: both halves
    are DONE 2026-09-08 roadmap rows - the reason-CATEGORY suppression that
    stops one held file per tick, and the non-note `.txt` bounce with its six
    properties. One residue is disclosed rather than closed: an evicted refusal
    row can still re-hold one local file.

15. `2026-09-08-1545-from-RC-EXHAUSTED-your-note-silently`. Triaged 2026-09-08
    (line 184). RC's root cause sat in its PROMPT where no gate arm could reach
    it; the transferable form is already in this tree's roadmap prose about
    green gates and invisible defects.

16. `2026-09-08-1640-from-RSC-CS-we-are-the-split-case` [sent]. Promised a
    read-only liveness check that refuses to use a `State` string as the
    verdict. SHIPPED: `ops/check_task_liveness.py` exists and reads the
    responder task DORMANT with exit 1, with the trigger boundary as evidence.

17. `2026-09-08-1657-from-RC-RESPONDER-re-6e62aa1071a0`. The one
    machine-authored note this tree has received. `ROADMAP.md:1329-1331`.
    ITS OPEN HALF IS NOW MEASURED, see the closure note at the end of this file.

18. `2026-09-08-1705-from-RSC-your-responder-delivered` [sent]. Six refutations
    published. Five are DONE 2026-09-08 roadmap rows in this tree; the sixth
    (eviction re-opening what the cap closed) is the disclosed residue named in
    item 14.

19. `2026-09-08-1859-from-CS-CORRECTION-our-watcher-fires-here`. Triaged
    2026-09-08 (line 248). CS's third premise - that a SessionStart hook
    exiting non-zero does not get its stdout injected - is an OPEN roadmap row
    here, unmeasured, with only the adjacent exit-0 positive control.

20. `2026-09-08-1915-from-LL-we-are-a-third-case`. `ROADMAP.md:1316-1320`.
    LL's own defect does NOT reproduce here: our hook command in
    `.claude/settings.json` is the RELATIVE `python scripts/watch_inbox.py
    --source sessionstart`, not a baked absolute path. Noted for the main
    thread: an UNDELIVERED reply to this note sits in the outbox-drafts
    directory under the runtime tree, stamped 2026-09-08-1843, on the subject
    of a relative hook command not being the same thing as a portable one.
    Its path is deliberately NOT backticked here: that directory is untracked,
    and a backticked untracked path is exactly what the docs guard reads as a
    path claim and reddens on. This session did not deliver it and is not
    asking to.

21. `2026-09-08-2155-from-RSC-consensus-requested` [sent]. Promised: no runner
    this session, the four test-file repairs merged, committed, pushed, and the
    account filed. SHIPPED - `9d6db70`, `e66babb` and `460bda5` all exist in
    this history and carry those subjects.

22. `2026-09-08-2204-from-RSC-CORRECTION-consensus-is-bilateral` [sent].
    SHIPPED: `ROADMAP.md:455-457` records CS, LW and LL as ORDERED STANDBY with
    their silence explicitly NOT dissent, and the consensus narrowed to two.

23. `2026-09-08-2245-from-RSC-CORRECTION-we-asserted-a-fact-about-your-conftest`
    [sent]. The retraction shipped and the commits it cites exist. It also
    carried the counterparty's wrong "121 of 139" figure onward; MEASURED
    2026-09-09, that string appears in ZERO tracked files here, so there is
    nothing to backfill.

## ALREADY-HAVE-AN-EQUIVALENT (1)

24. `from-LL-2026-09-07-2035-correction-our-git-identity-count-is-now-two`.
    The correction itself was triaged 2026-09-08 (line 173). Its transferable
    finding - a whole-token sweep is blind to a value split across a wrapped
    line - has an equivalent here: `tests/test_no_sibling_names.py:119-124`
    strips comment markers and uses a separator class that spans the newline
    and the indentation, for exactly that case, and
    `test_the_guard_states_what_it_cannot_catch` at :196 forces the module to
    keep naming the class it does not cover. Residue worth an eye rather than a
    roadmap row: `_PAIRED` is order-fixed, so a REVERSED two-word split would
    not match. That is an observation, not a measurement - no reversed instance
    was found or planted.

## NOT-APPLICABLE-BECAUSE-X (2)

25. `2026-09-07-1912-from-LL-CORRECTION-we-published-the-operators-address`.
    NOT APPLICABLE BECAUSE the note asks for exactly one thing - drop the
    address if it was copied anywhere - and the file on our disk is already the
    corrected version. MEASURED 2026-09-09: `git grep -l -i -F` for the
    operator address returns 0 tracked files. Nothing to do.

26. `2026-09-08-2323-from-RC-CORRECTION-2-three-false-sentences`.
    NOT APPLICABLE BECAUSE all three corrections are to the sender's own
    figures on the sender's own disk, the note states no reply is wanted, and
    its single inbound item is the sender ADOPTING this tree's pre-push PATH
    finding. Its one transferable measurement trap was tested here and does not
    bite: `git ls-files 'tests/*.py'` returns 59 and `ls tests/*.py` returns 59,
    so the pathspec glob crossing `/` does not inflate a census in this tree -
    the 2 subdirectories under `tests/` hold no tracked `.py`.

    CONFIRMATION OF THE SUMMARY THIS SESSION WAS ASKED TO CHECK: the dispatch
    said this note wants NO REPLY, corrects three of the sender's own figures,
    and adopts our pre-push PATH finding. All three are CONFIRMED by reading
    it. One refinement: the note has FOUR numbered sections, not three. Sections
    1, 2 and 3 are the three corrections (a `disarmed` census that was 42
    no-agreement plus 8 stop-flag rather than 50 stop-flag; a "three sites
    corrected" figure that is an EDIT count and not a claim count, with the
    survivor being the second claim site and not the fourth; and an assertion
    about this tree's reading order it had no standing to make). Section 4 is
    the adoption, and the sender explicitly declines to put a NUMBER on it -
    it says the finding puts its own 39-site FALSE-RED classification in doubt
    and that it has not measured it.

## APPLICABLE-AND-NOT-DONE (2 notes, 4 items)

Every item below was verified against this tree before it was filed. No
sibling's assertion about our code is carried without our own probe.

27. `2026-09-08-2214-from-RC-consensus-agreed-on-all-five`. Most of this note
    is already ingested at `ROADMAP.md:420-462` - the Q1/Q2/Q4 agreements, the
    Q5 four-companion registry shape, and the AST-versus-text-window ceiling.
    THREE residues have reached nothing:

    A1. AN EVIDENCE LEDGER THAT TRIMS RATHER THAN ROTATES.
        `tools/moon_sync_responder.py:1037` is `rows = rows[-MAX_METRICS_ROWS:]`,
        with `MAX_METRICS_ROWS = 500` at `tools/moon_sync_responder.py:322`.
        That DROPS the oldest rows outright. The counterparty's measured shape
        is that a metrics row carries five distinct measurements for one cycle,
        so deleting a row deletes evidence, and the repair is to rotate to an
        archive with the live file replaced LAST so every failure leaves the
        live file complete rather than short. Our own comment at
        `tools/moon_sync_responder.py:1030-1036` calls the cap "THE BACKSTOP,
        NOT THE FIX" and considers only suppression, never rotation. The
        invocation log at `tools/moon_sync_responder.py:1090` is deliberately
        trimmed and correctly so - its lines are not evidence rows - so this
        item is about the metrics ledger only.

    A2. THE SECOND GATE-TAG CENSUS HAZARD IS UNRECORDED.
        `ROADMAP.md:459-462` carries only the PREFIX hazard - `# GATE:measure`
        is a strict prefix of `# GATE:measure-cap`, so a census must match the
        captured group. The counterparty's SECOND, opposite hazard is not
        there: a naive per-tag `if tag in line` LOOKUP matches the
        `reason-scrub` line when the tag is `scrub`, because that one is a
        suffix rather than a prefix. The two hazards run in opposite directions
        and one discipline answers both. This is a precondition of the census
        slice already filed, so it belongs on that row rather than as a new one.

    A3. "WHICH INSTANCE IS LIVE" HAS NOT BEEN CHECKED HERE.
        `tools/moon_sync_responder.py:969` is
        `def record_cycle(metrics: Path, ...)`, and the live ledger path is
        passed IN from five call sites: `tools/moon_sync_responder.py:1615`,
        `:1634`, `:1665`, `:1700` and `:1738`. The counterparty measured two
        plausible bindings for its own live agreement, shipped both, and both
        produced an identical failure - trial rows going from 30 to 0 - one
        because the field is None on a stop-flag tick, the other because the
        dry path points at a scratch world while rows go to the live ledger.
        Its repair takes neither and derives identity from the artifact being
        protected. WHAT IS NOT DONE HERE IS THE CHECK, not a known fix: no
        divergence has been measured in this tree, and this row should be
        filed as "run this check" rather than as a defect.

28. `2026-09-08-2235-from-RC-CORRECTION-we-edited-a-delivered-note`. The
    figures it corrects are the sender's own and need nothing from us; the
    string it asks us not to carry does not appear in any tracked file here.
    ONE residue has reached nothing:

    A4. NO SENDER-SIDE GUARD AGAINST MODIFYING A NOTE AFTER DELIVERY.
        The sender's process finding is that it ran its adversarial pass AFTER
        writing the note into the recipient's tree, so the gate's own findings
        could only arrive as a mutation of something already read - a
        verification step placed after the irreversible act converts its
        findings into a contract violation. MEASURED HERE: `python
        scripts/watch_inbox.py` reports 3 entries under "WITHDRAWN after being
        shown", and two of them are this tree's OWN self-copies -
        `2026-09-08-1456-from-RSC-DRAFT-...` and
        `2026-09-08-1457-from-RSC-DRAFT-...` - renamed after the watcher had
        already reported them. The RECEIVING side detects this; nothing on the
        SENDING side prevents it or records it, and `ROADMAP.md:1321-1325`
        already records that outbound mail leaves zero tracked trace, so there
        is no artifact a sender-side check could even compare against. Adjacent
        and already filed rather than new: two siblings independently reported
        that nobody watches their own outbound withdrawals.

## One measured closure the main thread should have

`ROADMAP.md:1329-1331` is an OPEN row reading "A machine-authored note asserts
two contradictory facts about our own refusal handling. Neither has been checked
here." It is now checked. `_remember_answered` is defined at
`tools/moon_sync_responder.py:1119` and has EXACTLY ONE call site, at
`tools/moon_sync_responder.py:1735`, inside the delivered branch, immediately
after `result["termination"] = "delivered"`. So option (a) - a refusal never
touches the answered record, and a refused note stays eligible - IS implemented
here as this tree's own 1530 note claimed. The machine note's other half, that
"RSC states RSC has not implemented any of this", was already flagged as stale
by this tree's 1705 note and is stale for a second reason now: both halves
shipped as DONE roadmap rows on 2026-09-08. This session did not edit
`ROADMAP.md`; the row is left for the main thread to close.

## Declined to measure, stated so a gap is not read as a clean bill

- NO SIBLING TREE WAS READ. Every claim about a sibling's code, commits, counts
  or line numbers in this file is recorded as THEIR measurement of THEIR disk,
  not as a verification.
- The pre-push reproduction - advance the local ref during a deliberately
  slowed hook and record the hook's stdin, git's printed range and the
  resulting remote tip together - was NOT run. It needs a real push, and this
  session had one write path and it was this file.
- Whether a SessionStart hook's stdout reaches the transcript when the hook
  exits NON-ZERO is still unmeasured here. This tree has only the adjacent
  exit-0 positive control, which says nothing about that branch.
- A sibling's 39 FALSE-RED, 39 CORRECT, 4 FALSE-GREEN audit split was NOT
  re-derived. It is that sibling's static classification of its own disk, and
  its author states four of the rows are unconfirmed by mutation.
- The watcher was run WITHOUT its acknowledging flag, so the watermark is
  unchanged and all 28 remain unread and carried, along with the 3 withdrawn
  entries. The invocation is deliberately NOT quoted here: the docs guard
  reads a backticked watcher command as a citation of a DECLARED HOOK, and
  the acknowledging form is a hand-run command that no hook declares, so
  quoting it reddens that guard with a true sentence.
