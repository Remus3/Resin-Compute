# Completion ledger

Append-only, **newest first**, following the parent project's convention. One
entry per landed unit of work, with what was actually measured rather than what
was intended.

`ROADMAP.md` holds OPEN work. This holds CLOSED work. Neither belongs in
`CLAUDE.md`, and a test count belongs in neither: counts are not guarded and a
document is not a source of truth. Where a count appears below it is stamped with
the date it was measured, as a historical reading rather than as a claim about
now.

---

## 2026-09-08 - The invocation log could not name which hook fired, and the proof took a real fire

Commit `3964544`. `scripts/watch_inbox.py`, `.claude/settings.json`,
`tests/test_watch_inbox.py`, `tests/test_session_hooks.py`. Measured 2026-09-08:
1421 passed and 1 skipped in the application suite, 80 in PityEngine, licence 41,
docs 23, qa_companion 17 passed 0 failed 1 skipped, ruff clean, headless exit 0.
Baseline 1408 was re-derived by an adversary from a fresh clone at `0e9491a`
rather than taken on the builder's word; 13 arms added, 0 removed, and the
arithmetic closes against a collected count of 1422.

**The defect.** The runtime invocation log under `ops/runtime/`, named here in
prose because it is gitignored, existed to answer whether the `SessionStart`
hook fires on a cold session and survives `/clear`. It could not answer either.
`.claude/settings.json` wired BOTH `SessionStart` AND `UserPromptSubmit` to the
same command, `resolve_source` falls back to `cli` for both, and a manual
terminal run writes `cli` as well. Every fire in the complete log was `cli`.
An instrument that cannot separate its callers is not evidence about any of them.

**The trap the shape of the module set.** `main` writes its `start` line BEFORE
`_main` parses argv, so a label resolved by argparse would tag the terminal line
only and the two lines of one fire would disagree. The label is resolved by a
hand scan at the `__main__` guard instead. A flag rather than an env prefix,
because `VAR=x python ...` is POSIX syntax and the shell that runs a hook command
on this machine was never established.

**What actually settled it was a real fire, and an adversary was right to
demand one.** The builder's probe spawned the declared command as a subprocess,
which proves tokenisation by the test, not by the harness. A second adversary
refused that as evidence and was correct to: it further showed that
`--quiet-when-empty`, the flag already live in a hook command at `0e9491a`, is
NOT a positive control, because that flag changes stdout only and `_main` returns
its disposition unconditionally, so no log line could ever record it arriving.
The candidate was merged into the live checkout uncommitted against a pinned
baseline of 18 lines all `cli`, and the next real `UserPromptSubmit` fire
appended `userpromptsubmit` on BOTH of its lines, three columns, exit 0. That is
the first end-to-end measurement in this tree that a Claude Code hook delivers
argv to the process it names.

**Still unmeasured, deliberately.** `SessionStart` carried no flag at `0e9491a`,
so this change makes it argv-dependent for the first time, on the exact event the
log exists to prove. Its label cannot be read until a cold boot. A next session
reading `sessionstart` there closes it; reading nothing new means the hook died
and the recovery is a hand edit of plain JSON that needs no working hook.

**Two adversaries, distinct lenses, and they disagreed.** Does-it-reproduce
returned NOT REFUTED on six claims, having re-run the mutant itself, mutated the
settings file two ways - collapsing both hooks onto one label fails 6 arms,
collapsing both onto `cli` fails 8 - and fuzzed the argv scan with 12 real spawns
without producing a forged column or a forged line. Scope-and-siblings returned
REFUTED on the argv hole above, on an unfixed sibling, and on stale prose. Both
were right about different things, which is the case the two-lens rule exists for.

**A count baked into a comment was false within the hour.** The committed prose
cited ten lines and five fires from the live log. The log stood at 20 by the time
the slice merged. The comments name the property now and not the number, which is
the same rule the suite counts already live under.

**Corrected before merge:** an overclaim in `source_from_argv` that two readers of
one argv reaching two answers is its own defect. False for `--sour x`, for
`--source=`, and for a trailing `--source` with no value. Every divergence is
conservative and `_main` never reads `args.source`, so none can reach the log.

**A sibling repository's defect does not apply here, and was checked rather than
assumed.** Sibling-L reported the same day that its tracked hook command carries
an ABSOLUTE path, so in any clone or worktree it runs the ORIGINAL tree's script
and reports the ORIGINAL tree's inbox. This tree's commands are relative, verified
byte-wise, and the builder's own worktree run left no runtime log in the worktree
at all.

## 2026-09-08 - A task State string is not liveness, and every slice was refuted before it merged

One commit, `e7ab266`, four slices, ten files. THE PROCESS RESULT IS THE
HEADLINE: every one of the four slices was reported COMPLETE by its own builder,
with passing arms, clean ruff and honest counts, and every one was then refuted
or defect-found by an agent that did not write it. Three by independent
adversaries, one by the merger. Nothing in this entry rests on a self-report.

**The root finding. `ops/check_task_liveness.py`, proven by
`tests/test_task_liveness.py`.** ResinCompute-Responder reported `State: Ready`
and `LastTaskResult: 0` while its only trigger had expired at
2026-09-07T21:00:00, `NextRunTime` was empty, and the invocation log carried no
line dated 2026-09-08. It had not fired in 24 hours and never would again. The
previous hand-off read that string and claimed a 5-minute tick. **A task State
string names a state, not a capability.** The checker verdicts on positive
evidence of a future firing; State may VETO and never vouch.

The mirror error was measured too and is why the first cut was refuted: an
ABSENT EndBoundary is absence of evidence, not evidence, and a fired one-shot
carries none. An adversary found SEVEN surviving mutants and a false LIVE on a
real task on this box. All seven are killed.

**M12 survived the repair as well, and that is the entry worth remembering.**
The arm named as its killer,
`test_the_real_probe_emits_every_key_the_parser_reads`, pinned KEY PRESENCE and
not VALUE POPULATION - a probe emitting an `end_boundary` of null keeps the key
and all 56 arms stayed green. An adjudicator ruled MERGE with the gap recorded,
but attached a condition: if the installer slice landed and taught a script to
read exit 0 as "will fire", the gap was promoted to a blocker. IT LANDED IN THE
SAME SESSION. `test_the_real_probe_reports_the_end_boundary_value_and_not_just_the_key`
now kills it - verified by the merger applying the mutant and observing
`1 failed, 57 passed`, then restoring.

**Fixed at its three sources, not only at the new tool.** Both installers
printed the task's State property as the final word after registering, and
`NEXT_SESSION_PROMPT.md` instructed a bare state read. That is the lineage that
taught the false claim. Both installers now report LIVENESS and exit with the
checker's verdict; absent the checker or a console interpreter they say
UNVERIFIED rather than falling back to a state string.
`tests/test_task_state_claims.py` goes red if any tracked file presents a State
string as evidence of firing, with a planted positive control proving it
discriminates. A FOURTH site was found unprompted - the removal recipe in
`README.md` - and correctly ruled a false positive by narrowing the rule at
source rather than allowlisting the path.

The installer-to-checker seam was exercised without registering anything, by
extracting the real bytes of the console-interpreter resolver and the liveness
block: dormant task exit 1 NOT ESTABLISHED, live task exit 0 ESTABLISHED.

**`tools/moon_sync_responder.py` - refuse without answering, and a bounce that
is not a note.** Six refutations, all measured, all repaired but one. The
sharpest: the refusal fingerprint hashed the RENDERED REASON TEXT, and one
reason interpolated a byte count, so a draft oversize by a different amount each
cycle minted a fresh fingerprint every tick. Ten cycles, ten held files - the
288-a-day defect alive with ONE note and no cap involved. The arm that should
have caught it fed a BYTE-IDENTICAL draft both cycles and could not fail. Keyed
on category now; 10 cycles produce 1 held file and 1 fingerprint.

Also measured and fixed: an unwritable refusals record failed OPEN and delivered
five bounces INTO A SIBLING'S REPOSITORY with no error surfaced, which at a
five-minute tick is 288 files a day in someone else's tree - it now records
before delivering, so an unrecordable refusal stops the outbound; an unguarded
directory creation raised WinError 183 when the parent existed as a file, AFTER
the held file and bounce were already written, at four sites; a metrics row
appended unconditionally every cycle with no cap, 100 cycles giving 100 rows and
54150 bytes with the whole file rewritten each tick, O(n^2), now 1 row and 579
bytes; and head-of-line starvation, where one un-passable note blocked the
entire channel forever because the pending queue sorted by name and a refusal
never touched the answered record - reachable DELIBERATELY by a sibling with a
name that sorts first. NOT fixed, and disclosed rather than hidden: an evicted
refusal row can still re-hold one local file.

**`scripts/watch_inbox.py` gains an invocation log**, so whether the SessionStart
hook fires and survives a clear is measurable here for the first time rather
than merely unverified. The first cut wrote that log FROM THE TEST SUITE under
the same source label a real firing uses, so the instrument forged its own
evidence - running `tests/test_session_hooks.py` alone wrote six
indistinguishable lines. **Root cause, and it generalises: an isolation fixture
that monkeypatches module attributes cannot isolate a SUBPROCESS**, which
re-imports the module with the real defaults. Both records now re-root through
the runtime-directory environment variable that `ops/health.py` and
`headless/runner.py` already honoured, so no new knob was invented. Verified
independently: a full `pytest tests` leaves the log byte-identical by sha256.

**A data fix, not just a prevention.** The watcher's reported-notes record,
which lives under the gitignored runtime directory and is deliberately named in
prose here rather than as a path, carried
a fixture filename written by `tests/test_session_hooks.py`, and the watcher had
been reporting it as withdrawn mail in every session banner. Removed via
`core/atomic_io.py`; withdrawals 4 to 3. The other three were checked
individually and are genuine - the withdrawn verbatim directory is a real
withdrawal, not fixture pollution, correcting a subagent's claim.

**Two instrument errors by the merger, both self-caught, both the same class as
the tree's own waiter trap.** Reading a shell exit status after a pipeline
measured the last filter's status, not the tool's. Listing a dict-shaped JSON
record counted its two top-level keys and reported no pollution where there was
some. Both were statements about the probe rather than the world. Re-measured
correctly before anything was claimed.

**Channel.** Sibling-D's two questions answered by measurement: this tree is the
SPLIT case - wiring TRACKED in `.claude/settings.json`, inbox IGNORED in
`.gitignore` - so a fresh clone FIRES the watcher with no channel, the
combination that sibling declined to ship. But its third clause does not
transfer: our tool exits 0 and its stdout is on the normal injection path,
measured in a real clone. That sibling's own refutation leans on the claim that
a hook's stdout does not inject on a non-zero exit, which the same note lists
under what it is NOT claiming - load-bearing and disclaimed in one document.

**Sibling-A's responder DELIVERED at 17:00**, cycle
`20260908T165744-28336-aba821`. First machine-authored note this repository has
ever received; M2 and M3 are no longer NO-DATA on the receiving side after three
attempts. Its one stale claim is instructive rather than defective: it reports
that sibling's refusal handling as the opposite of ours, accurate about their
code at `origin/main` and stale about their own already-accepted ruling. **A
responder that measures HEAD reports the code, and a repository's intent can be
newer than its code.** Their bounce and ours converged independently on the same
six properties.

Counts measured 2026-09-08 at `e7ab266`: `pytest tests` 1408 passed 1 skipped;
`pytest agents/pity_engine` 80 passed; `shell node --test` 52 pass 0 fail;
licence 41; docs 23; qa_companion 17 passed 0 failed 1 skipped; ruff clean;
headless smoke exit 0; mypy advisory Success over 33 files, which says nothing
about `ops/`, `scripts/`, `headless/` or `tests/`.

---

## 2026-09-08 - The trial window measured nothing, and the fix that made NO-DATA reportable at all

One commit, `fe53f31`. The 1900-2100 LATENCY-ONLY window agreed with Sibling-A
ran on 2026-09-07 and produced no reply and no metrics file.

**The result, and why it is NO-DATA rather than zero.** Measured after the
window closed: the responder metrics JSON under the runtime directory was
never created, and the
invocation log held 29 `start` lines against 19 `empty` terminations, first fire
18:45:34, last 20:55:00, scheduled task afterwards Ready with LastTaskResult 0.
M1 INAPPLICABLE under the agreed grammar, M2 and M3 NO-DATA.

The cause was RSC's own eligibility rule, not the counterparty. `pending()`
takes `since=bounds.window_opens`, so only mail ARRIVING after 19:00 was
eligible, and the counterparty's most recent note predated the window. Nothing
could match on any tick. The rule was left alone mid-window on the reasoning
that widening eligibility while the experiment ran would edit the experiment,
and a latency measured under a rule changed halfway measures neither rule.

No metrics row was written for a no-op cycle, deliberately. A row carries
`reply_seconds` as `replied - arrival`, so a row for a cycle that sent nothing
would put an invented latency into M2 - the number the trial exists to measure.
The absent file is the honest report.

**The defect found by checking, mid-window, at 19:16.** Four fires inside the
agreed window had each terminated `empty` while the log carried four bare
`start` lines. `window`, `budget`, `empty` and `disarmed` each returned from
`run_once` before reaching `log_invocation`, so a cycle that ran and declined to
act was byte-identical on disk to a cycle that never fired. That is the exact
condition `log_invocation`'s own docstring says it exists to prevent, and the
same class already fixed on the `no-destination` path, which carries a comment
saying so.

All four had a passing test. Each asserted the termination as a RETURN VALUE.
This is the trap this tree published to the channel on 2026-09-07 - a gate
tested but not enforced - reappearing in the same file with the assertion
pointed at the wrong thing.

**The fix is structural rather than four more call sites.** `run_once` is now a
wrapper that logs `start`, delegates to `_run_once`, and writes the terminal
line whatever the body returned, plus `crashed` if it raised. The five scattered
per-path calls are gone. A hand-maintained list of paths that remember to log is
the failure mode this suite already met when its isolation fixture named three
`DEFAULT_` paths by hand and a fourth arrived an hour later.

Verified against the live scheduled task rather than by reading: the 19:25 fire
was the first to run the patched file and wrote `start` then `empty` at the same
second, LastTaskResult 0. The 19 `empty` lines above exist only because of this
fix - without it the window would have closed leaving 24 bare `start` lines, and
the honest report would have been UNMEASURABLE rather than NO-DATA.

Proof: `tests/test_moon_sync_responder.py`, five arms red before and green
after. Four name the terminations; the fifth asserts `lines[-1]` equals
`result["termination"]` without naming a path, so a NEW early return fails there
instead of silently reopening the hole.

One existing arm changed contract deliberately.
`test_the_invocation_log_records_one_line_per_fire` asserted one line per fire,
which held only because the quiet terminations skipped their second. It is now
`test_the_invocation_log_records_a_start_and_a_terminal_line_per_fire` and
asserts the pairing. The `start` line is not redundant: it is the only evidence
that a fire which dies mid-cycle happened at all.

**A second delivery attempt, also NO-DATA.** Sibling-A rebuilt its end, armed
under `hop_budget 1`, and two notes were hand-delivered to it. The first was
refused 72 seconds later at the input stage on name grammar - RSC's filename was
130 characters with a 102-character topic against a `{1,80}` topic group. The
counterparty's own correction is the more useful half: it first blamed a length
cap, then measured all 207 names across the five inboxes and found 33 failures,
ALL on the topic group and only 11 on the length cap, so raising the number it
had blamed would have fixed none of them. RSC accepts the correction as a defect
in its own naming convention and now keeps topics under 80 characters.

No responder-authored reply had arrived 15 minutes after the bounce, polled
against the counterparty's exact reply grammar. Three candidate explanations
exist and none were measured, so none is recorded here. The responder has still
never answered real mail.

**A prediction of RSC's was refuted by the counterparty.** RSC measured that its
own watcher reports an underscore-prefixed `.md` as a NOTE and only demotes the
`.tmp` suffix, and predicted a transient phantom note during the counterparty's
hard-link window. The counterparty measured what it actually writes - the tmp
name carries `.tmp` - so the window is unobservable here. RSC's reader-side
defect is real and unreached by that delivery scheme.

**Answered to the channel, unimplemented here.** A counterparty defect - an
input-stage refusal that holds the note, marks it answered and delivers nothing,
leaving the sender unable to distinguish refusal from being ignored - was
answered with a shape RSC does not yet implement: refuse WITHOUT answering,
which `_remember_answered`'s single call site in the delivered branch already
does here, plus a bounce written as a file that is NOT a note. Measured basis:
`pending()` requires `.md` plus a parseable sender, and the watcher lists a
non-note as a loose file, so such a bounce is visible to a human, ineligible as
responder input, and incapable of a bounce war by construction rather than by
policy.

The cost of refusing-without-answering was disclosed rather than hidden: a
permanently-refused note re-refuses every tick forever, and `_hold` writes
`held/<epoch>-<name>` with a fresh epoch each time, so one unpassable note
produces 288 held files a day at a five-minute tick. Not fixed, no date claimed.

---

## 2026-09-07 - The responder was armed for a trial, and every defect that mattered was found by running it

Six commits, `1d80f8c` through `159f4ac`. The cross-repo responder trial: RSC
volunteered as Sibling-A's pairwise partner, built its end, and armed it.

**The watcher first.** Two holes closed in `scripts/watch_inbox.py`. `rglob`
descended NTFS junctions, because `Path.is_symlink()` is False for one - a
one-file drop reported 6 files on one sibling's tree and 32 on another. Replaced
with an iterative pruned walk plus a per-drop entry budget. And the walker had no
withdrawal reporting at all: the report was `entries - seen`, so a deletion
simply stopped appearing, and Sibling-A's 50-file pull from four inboxes would
have been reported here as silence. Both proven by `tests/test_watch_inbox.py`,
9 of 9 mutants killed against the shipped functions.

The digest FORMAT deliberately did not move for a drop of ordinary files, so no
seen key went stale and the live inbox did not re-report. That constraint came
from a sibling and this tree had already measured the cost of breaking it at 88
notes.

A third hole in the same walker was a LIVE MISS rather than a latent class: the
top level globbed `*.md`, so a sibling's loose `REFERENCE-moon_sync_poller.py.txt`
had been invisible here for thirteen hours. It surfaced on the first run after
the fix.

**The responder.** `tools/moon_sync_responder.py`, 55 arms in
`tests/test_moon_sync_responder.py`, 21 of 21 mutants killed. The design decision
worth not re-litigating: THE SPAWNED SESSION NEVER WRITES INTO A SIBLING TREE. It
is handed a note and a staging directory here and its only output is a draft;
this module validates and delivers. Every rule is enforced on OUTPUT, after the
session exits, by code the session did not run. A sibling's allowlist reads as
though the responder decides by parsing the request, which it cannot - a note is
prose written by another agent, and keying an EXECUTOR on sender-supplied text is
strictly worse than keying a detector on it.

Consequence adopted channel-wide: the session needs NO write authority at all,
so the trial does not require anyone to grant an unattended agent write access.
`--dangerously-skip-permissions` is absent and the prompt goes in on STDIN.

**FOUR DEFECTS FOUND BY RUNNING, NONE VISIBLE IN 53 GREEN ARMS.**

1. A FAILED SPAWN WAS RECORDED AS `exhausted`. The first live spawn raised
   FileNotFoundError - on Windows the entry point is a `.CMD` shim subprocess
   will not launch by bare name - and the spawn returned EMPTY. An empty draft is
   refused by the gate and recorded as `exhausted`, which is precisely the label
   meaning "the bound worked as predicted". A subprocess that never ran would
   have published the reassuring result every cycle. `spawn-failed` is now its
   own value.
2. THE BACKLOG WAS ELIGIBLE. With an empty answered-record the first armed cycle
   selected a note from the PREVIOUS DAY. It would have answered a stale question
   and spent the hop budget before any new mail arrived.
3. THE ROOTS LOOKUP COULD NEVER RESOLVE ANYONE. The per-host roster keys by
   codename by design; notes are addressed by channel code. It looked up "RC",
   found nothing, and returned no destination - silently, every cycle.
4. A no-destination exit left `termination` as `unknown`, indistinguishable from
   a cycle that never ran.

**Three gates were tested and never enforced.** `within_budget`, `window_open`
and the self-sender check were each correct, each had a passing arm, and each was
IGNORED by `run_once`. Mutants disabled them inside the cycle and the suite
stayed green, because every arm tested the PREDICATE as a pure function. A
predicate can be right, tested, and ignored - the same class as configuration
read as behaviour.

**The counterparty's agreement is a precondition the code checks**, not a promise
someone remembers. A gitignored record under `ops/runtime/` names the counterparty, the
note it rests on, and an expiry; absent, malformed or expired all mean no.
Registering the task does not start the trial.

**Task registration cost two measured defects.** Trigger element order is not
free - `Repetition` must precede `StartBoundary` and needs a `Duration`, failing
as 0x8004131a naming no element. And the XML declaration must say UTF-16, because
`Register-ScheduledTask` takes a .NET string: a UTF-8 declaration fails with
"(1,40)::ERROR: unable to switch". `ops/ResinCompute-Supervisor.xml` carries a
comment arguing the opposite, and THAT TASK IS NOT REGISTERED ON THIS MACHINE,
which is how the wrong claim survived - nothing ever exercised it. Bisected
across five variants rather than reasoned about.

**The pre-push hook drained the only statement of what it was gating.** It sent
its stdin to `/dev/null` under a comment calling the ref list "unused", and the
suites grade the WORKING TREE rather than the pushed commit - so a dirty tree
mis-grades on every push, with no concurrency required. Measured window: 28s. It
now reads the refs, REFUSES when a pushed sha is not HEAD, and on a dirty tree
names the commit actually shipping instead of printing a bare OK. Verified by
feeding synthetic ref lists: incident exits 1, HEAD exits 0.

**A workspace-trust divergence that would have silently degraded every headless
run.** Reported by a sibling and reproduced here: `~/.claude.json` held two path
spellings of this checkout with disagreeing trust, and an untrusted workspace
makes a headless run DISCARD its permissions without erroring. `workspace_trust`
now refuses the spawn loudly and checks EVERY equivalent spelling, because
`str(Path("C:/x"))` normalises to a backslash on Windows and a Path-keyed lookup
cannot see the forward-slash entry at all. Operator flipped the stale key to
True; the whole config was diffed field by field afterwards and exactly one key
moved.

**Trial state at close, a reading and not a promise.** `ResinCompute-Responder`
registered and firing on cadence, LastResult 0. Sibling-A answered NO to arming -
its end is unbuilt - and endorsed LATENCY-ONLY tonight: M2 and M3 only, M1
recorded INAPPLICABLE rather than zero, because with a human at the far end
hops-to-quiescence is undefined and a zero would be the most misleading value
available. Zero auto-replies delivered anywhere as of 19:10.

**OPEN AND NOT ACTED ON: 89 of 91 commits in this PUBLIC repository carry the
operator's personal email in the author field.** Measured this session against
`origin/main`. A sibling redacted a single occurrence of the same string from a
note hours earlier and called it the operator's identity. No action taken - a
history rewrite on a public remote is an operator decision, and a sibling spent
the evening measuring how expensive and trap-laden one is.

## 2026-09-07 - The corpus was a snapshot and the session moved the tree under it

Both scrub halves reported complete and both were telling the truth. A tree-wide
sweep after the merge still found 11 full-name hits across three files that were
on NEITHER write-list: `tests/test_guard_worktree_exclusion.py`,
`tests/test_watch_inbox.py` and one line of `tests/test_loop_concurrency.py`.

None was an oversight. The corpus was computed by `git grep` at `4781de1` and
dispatched against; all three files were created or rewritten by this session's
own merges AFTER that point. The third is a comment the merger itself authored
in the slots re-pin, on a line the code slice's fork point predates, so that
slice could not have seen it even in principle.

**A CORPUS IS A SNAPSHOT, AND A LONG SESSION MOVES THE TREE UNDER IT.** A sweep
dispatched against a file list is correct about the tree that existed when the
list was built and says nothing about the tree at merge time. Re-derive after
the merges. Fixed in `3323481`; the checker asserts a NON-EMPTY corpus before
asserting zero survivors, because zero out of zero reads as a pass.

A second residual was caught by the code slice and ruled on by the merger rather
than by the producer: after every name was codenamed, `core/ports.py` still
explained a sibling's 2999 reservation by naming a third-party API whose vendor
name is the first word of that project's name. The mechanism is kept, the vendor
is not named, and the reason is recorded at the site so nobody restores it.
**A residual inference channel is not less of one for being a fact about a port.**

---

## 2026-09-07 - The only sanctioned write path in this repo emitted CRLF

`core/atomic_io.py` called `tmp.write_text` with no `newline=` argument, so
Python translated every LF to `os.linesep`. `CLAUDE.md` names this module as the
only sanctioned state-write path, which means it was the write path everything
else is told to use.

Measured before the fix: `atomic_write_text(p, "a" + LF + "b" + LF)` returned
CR-LF-separated bytes, and `atomic_write_json` produced 7 CRLF pairs on a
two-key object. Worse, and the reason the contract is "no translation" rather
than "normalise to LF": a caller who supplied CRLF got back CR-CR-LF, the CR
kept and the LF expanded underneath it. Fixed in `e1b20e6`, verified by
main-thread probe after merge rather than by the producer's own report.

`.gitattributes` carries `eol=lf` and `tests/test_line_endings.py` fails a
tracked file holding CRLF, so the first TRACKED file written through this
function would have gone red with nothing in `git diff` to explain it.

Then the sibling sweep, `b739f02`. Seven candidate sites, and **two were false
positives**: two `tools/` modules already passed `newline=` on the CONTINUATION
LINE of a wrapped call, which the line-based grep that built the corpus could
not see. The guard added in `tests/test_no_crlf_writers.py` parses with `ast`
rather than scanning lines, takes its corpus from `git ls-files` so a leftover
worktree cannot poison it, asserts the checked count before the offender list,
and plants a real offender as a positive control. It needs no self-exemption:
it never calls the function it searches for, and `ast` cannot see a literal
inside a string.

Live corruption measured, not hypothesised: the inbox seen-state file under the
gitignored runtime directory - not backticked here, because a backticked path
under a tree root must be tracked and that one must never be - held 98 CRLF
pairs, and a capture-store artefact outside the tree held 5. The first
self-heals on the next `--mark`; the second was renormalised only after
measuring that no manifest pinned its digest and it was not in the
content-addressed blob store.

**Verification pointer:** `tests/test_core_atomic_io.py`,
`tests/test_no_crlf_writers.py`.

---

## 2026-09-07 - Four root-walking guards could not tell a nested checkout from this tree

Fixed in `ffce5a9`, and the verification is the part worth recording. The
builder proved its fix against a hand-planted `gitdir:` marker file and said so.
A marker file is not a worktree, so an independent verifier planted REAL linked
worktrees under `data/` and `docs/` with `git worktree add --detach`:

```
builder branch, real worktrees planted   1106 passed, 1 skipped, exit 0
main 353e3c1, identical worktrees        6 failed, 1089 passed, exit 1
```

Downstream output changed, so the fix acts on the real thing. **A linked
worktree's `.git` entry is a FILE of 53 bytes beginning with a gitdir pointer**,
measured on this machine - the predicate uses `.exists()` for that reason and
`.is_dir()` would have failed silently.

Two corrections the verifier made to the slice as claimed, both kept in the
merge message rather than smoothed away: `tests/test_line_endings.py` was NOT
nested-checkout-blind as shipped, because its `iterdir()` plus `is_file()`
skipped a directory outright - making it recursive is a genuine coverage
widening but fixed no live defect and belonged in its own slice. And "asserts
the checked count" is really `len(checked) > 0`, which is non-emptiness rather
than a pinned number; the anti-vacuity intent holds and the wording overstated
it.

The misclassification was INHERITED: `tests/test_guard_worktree_blindness.py`
already listed that module among the four despite its own criterion requiring a
recursive loop.

**The transferable half, sent to the fleet:** 34 of 39 test modules here were
structurally immune because their corpus is `git ls-files`, and git does not
descend into a nested checkout. That single question triages a whole suite
before anything is measured.

---

## 2026-09-07 - The digest-key arms were green against an mtime key and a size key

A sibling measured two mutants surviving their whole watcher suite and asked
every repo on the channel to check its own. Checked here by applying each
mutation to `scripts/watch_inbox.py` in an isolated worktree, running the suite
against each, and recording survived-or-killed before and after. Three survived,
all now killed, `35a8565`.

**The refinement is sharper than the report.** The LITERAL substitutions were
killed here, but only by SHAPE arms - one asserting a readable file's digest is
a plain sha256, and a length assertion. Hashing the metadata restores the shape
and walks straight past both. Moving the substitution to the entry-key site or
to the manifest line needs even less. **A shape arm reads as coverage and is
not: it pins the FORMAT of the key, never its INPUT.**

`scripts/watch_inbox.py` was CORRECT and is untouched. Every survivor survived
because the arm was weak.

A later note from the same sibling reported a second layer - that `os.utime`
with float seconds does not restore `st_mtime_ns`, so an arm can assert it
restored the timestamp, read as armed to a reviewer, and still leave a
nanosecond-reading key moved. **Re-measured here rather than re-read, and the
arms were already sound**: one restore site, already using `ns=`, already
asserting in nanoseconds, written that way an hour before the note arrived. All
four mutants killed against a green pristine floor. Nothing was changed and
nothing was committed - an arm that is already sound does not get hardened to
have shipped something.

**The finding from that measurement is in the harness, not the arms.** The first
mutation harness used a quoted heredoc, a NUL escape collapsed inside it, and
the drop-site search matched ZERO times. The mutation was a silent no-op and the
harness would have reported SURVIVED on both drop mutants - a confident false
confirmation of the sibling's own finding. An `assert source.count(old) == 1`
uniqueness guard caught it. **Assert the mutation site matched before trusting
the verdict, or a broken harness is indistinguishable from a weak arm.**

**Verification pointer:** `tests/test_watch_inbox.py`, 43 arms.

---

## 2026-09-07 - Noelle was found, and the recorded search window was wrong

`observations.jsonl` line 9 recorded her acquisition as NOT-FOUND and attributed
the failure to a 1 fps sampling rate over the window 09:20:44Z to 09:42:59Z.

Re-swept at 15.000 fps - every frame of all 29 readable segments, 129180 frames
against the prior sweep's 1384. She was acquired at 09:07:38.533Z to
09:07:39.667Z as card 1 of the first Beginners' Wish 10-pull, a 4-star Geo
character card tagged New, bracketed on both sides by the banner counter reading
20/20 at 09:07:24.000Z and 10/20 at 09:07:46.000Z.

**The correction matters more than the find. The recorded bound was FALSE.** At
09:12:09Z the banner reads 10/20, not 20/20; the last 20/20 frame is before
09:07:26Z. The 20/20 reading was correct at 09:07:24Z and stale by the time it
was attributed to 09:12:09Z. That wrong bound placed the search window about
thirteen minutes AFTER the event, so no sampling rate applied to that window
could ever have found her - re-sweeping the SAME window at 15 fps returns
nothing but Miliastra Wonderland.

So "not found at 1 fps" was never mainly a sampling problem. The sampling rate
was the explanation that came to hand, and it was true and irrelevant at once.
**A caveat that is correct can still be the wrong explanation, and a plausible
one stops the search.**

Detection was non-OCR, with two positive controls: the Dehya splash known to be
present in the same corpus, and a transfer control on a different character over
a different background. Both fire.

The record was corrected without rewriting it: all eight original fields are
preserved byte-identical and four supersession fields were added, with the
resolving observation appended as a new record carrying read method, sampling
rate, both controls, five evidence digests and the one unswept interval. A
record of what was believed is worth keeping; a record readable as current truth
when it is false is not.

---

## 2026-09-07 - A row-scoped provenance schema, before the first row lands in data/

`core/provenance.py` and `docs/PROVENANCE_SCHEMA.md`, merged as `62ee019`,
authored while `data/` still holds nothing but hand-authored fixtures. The
ordering is the point: a schema written after the first row is a schema fitted
to whatever the first row happened to have.

Every value entering `data/` carries what it was read FROM, that source's
sha256, and HOW it was read - by eye, by OCR, or from the game's own bytes. Each
of those exists because of a measured failure this session or the last:
independence is COMPUTABLE through `parent_sha256` so two crops of one frame
collapse to one witness; a NOT_FOUND row without a sampling rate is refused; a
row carrying a forbidden key is refused, because the capture store holds an
account UID and a login token deliberately outside this tree and the schema is
what decides which values may cross that line.

**Built against a null skeleton first** - real types, degenerate functions -
which gave 43 failed and 16 passed with each arm failing for its own reason
rather than the whole file failing on one import error. That is the difference
between a suite that is red and a suite that is armed.

`core/types.py` was not touched. It is the shared contract and a merge surface,
and a contract with no consumers has no business in it.

Documented limitation rather than a papered-over one: whether a row came from an
OCR SWEEP is not decidable from the record, so the sampling requirement is
enforced only on the two decidable cases. No field was invented to pretend
otherwise.

**Verification pointer:** `tests/test_provenance.py`.

---

## 2026-09-07 - The shared governor docstring named two siblings one line above forbidding it

`ops/loop/slots.py` opened by naming three projects in plain text and closed the
same paragraph with "Nothing here may reference ANY of them". All carriers are
published repositories, so the contradiction was also an exposure.

A sibling proposed the replacement wording and this repo authored the bytes,
which meant this repo carried the red window. Committed as `02d5d93`; all three
carriers subsequently converged on `71fa2a68`, measured on three disks by three
parties plus a fourth that vendors none of them.

Only the docstring's opening paragraph moved. An adversary proved it by
reconstructing the HEAD blob with lines 4-8 swapped in from disk: the
reconstruction matched exactly, and the differing 1-based line indices across
all 247 lines were [4, 5, 6, 7, 8] and nothing else.

**Two corrections went back up the channel and both were accepted.** The
proposal's claim that the new wording matched `winmutex.py` exactly was false in
three places, and the claim that `winmutex.py` was clean of every sibling name
was false at one line - confirmed independently from a third disk, and in the
SHARED bytes rather than in one tree's drift, so it is everyone's or nobody's
and cannot be scrubbed unilaterally.

**What this round did NOT close, disclosed rather than fixed:** `SHARED_SHA256`
hashes only this repo's own disk. There is no cross-carrier arm, so the suite
reads green while the byte-identity contract is divergent. A guard that can only
see its own disk cannot detect divergence.

**Verification pointer:** `tests/test_loop_concurrency.py`, 22 arms.

---

## 2026-09-07 - Sibling project names replaced by codenames across the tracked tree

This repository is public. Before this pass its tracked files named six sibling
projects of the same operator's in plain text, which published a roster of a
private fleet as a side effect of documenting this tree's own inheritance.
Each sibling now appears as an opaque codename, Sibling-A through Sibling-F,
and nothing tracked resolves a codename to a project. The resolution map is a
single gitignored per-host file, ops/moon_sync_repos.json, deliberately not
backticked here because a backticked path under a tree root must be tracked and
that one must never be.

**Stated at its real size, because an over-claimed rationale outlives a wrong
line of code.** The operator's ruling was that these names are not secrets and
that the tree only needs to be ambiguous about them. This removes a plain-text
roster from a public repository. It does NOT make the fleet unlearnable to
anyone who already knows it, and no entry in this file should be read as
claiming otherwise. Prior commit messages and prior blobs are untouched by this
pass.

**Only proper nouns moved in the historical entries below.** No date, digest,
count, causal claim or verdict was altered, softened or reordered, and nothing
was deleted. Append-only governs ENTRIES, not BYTES: this is a vocabulary
substitution of the same kind as an ASCII normalisation pass, and it is
recorded here rather than done silently precisely so a reader who meets
"Sibling-E" inside a 2026-09-06 entry can see from the top of the file that the
word was substituted afterwards. Line wrapping was reflowed only in the
paragraphs a substitution touched.

**What deliberately did NOT move, each for a stated reason.** The five
hand-off filename prefixes on the shared Desktop are real basenames observed on
disk, and a guard that compares against invented filenames is vacuous, so they
stay byte-exact. The shared ProgramData slot-bucket path is a live OS location
three repositories coordinate through; renaming it from one side points this
repository at a different bucket and silently un-serialises the governor, so
closing it is a fleet migration rather than a scrub. This repository's own
`RC_` environment prefix means Resin Compute and is not a sibling. A third-party
vendor name that once appeared in `core/ports.py` was judged a company rather
than a sibling; that judgement was WRONG and the line is gone - see the
2026-09-07 entry on residual inference channels. The vendor name is deliberately
not repeated here, because repeating it in the ledger hands back exactly the
token the module removed. One machine-name
token survives in `README.md` and `docs/adr/ADR-004-port-block.md`; the
operator ruled on project names and that is a separate question, left open
rather than assumed.

---

## 2026-09-07 (second session) - The account was created once, and the capture lane was built in front of it

Three commits, `2fd8aef` through `f930263`. The operator installed and launched
Genshin Impact for the first time on this machine during the session, so the
work was done against a clock: every artefact a first run produces is either
overwritten later or never produced again. The chat surface was kept for
instructions to the operator and for verdicts, per their instruction.

### What was standing before the game launched

Four processes, built and positive-controlled first, then started:

- `tools/first_run_capture.py` - polls the filesystem and registry write
  surfaces every two seconds and content-addresses every distinct generation,
  so an overwrite ADDS a blob rather than replacing one. Reads through
  `CreateFileW` with `FILE_SHARE_DELETE` when a plain read fails, because a
  rotation is both the moment worth capturing and the moment the handle is
  contended.
- `tools/screen_capture.py` - screenshot daemon with a 64-bit mean-hash dedupe
  that still writes an index line on a deduped tick. "No new PNG" is the
  daemon's steady state AND what a dead daemon looks like; those two must not
  be indistinguishable.
- `tools/wish_authkey.py` - recovers the wish-history authkey URL and pulls the
  gacha log. Refuses to write anywhere inside this git tree.
- `tools/capture_supervisor.py` - keeps the lane alive and reports to a file,
  not to chat. Measures CONTENT and not only liveness, because ffmpeg keeps
  writing frames when a Direct3D title has handed it a blank surface.

Plus an ffmpeg screen recorder at 15fps, 2560x1440, nvenc, 300-second segments.

**Measured at the end of the run:** 6062 file events over 5971 distinct blobs,
1542 screenshots kept out of 2036 index lines, 29 video segments, 2 webCaches
snapshots, 10 wish-pull attempts, 7 recorded observations, 15 GB.
`output_log.txt` alone was captured at 47 distinct generations, so the whole
first-run log history survives rather than only its final state.

### The capture store is not in this tree, and the absence was proven

`C:/rsc-first-run/` holds the bytes. Genshin's logs carry the account UID and
the miHoYo registry subtree carries a login token. A sweep over all 164 tracked
files for any nine-digit run hashing to the account UID found 0, and the checker
was proven to fire on a planted control first, because a clean result and an
unarmed check look identical.

### Four facts recovered, and the one that needed the second lane

The account UID was read four ways that do NOT share one input: two pixel reads
off one crop, which is one fact rather than two, plus the game's own
`UidInfo.txt` bytes and the directory it created under `BeyondLocal/`. The
region was stamped UNVERIFIED as an inference from the UID prefix, then
promoted to VERIFIED when the game wrote
`security_server_default_iplist_os_usa.txt` itself.

**The traveller nickname was missed entirely by the 4-second screenshot lane and
recovered from the 15fps video** at `seg_20260907_025348.mkv +108s`. That is the
only point in the session where the two lanes were not redundant, and it is the
justification for carrying both.

### A recorded inference was refuted by the operator's next action

Dehya was recorded as a TRIAL character on the strength of Level 17 with
Friendship 1. The operator then levelled her with EXP books, which a trial
character cannot be. The inference was retracted in `observations.jsonl` with
what replaced it: her card is GOLD, the owned 5-star colour, and the genuinely
anomalous slot was a different one whose card is RED. **Two numbers consistent
with a hypothesis are not evidence for it, and the card colour was on screen the
whole time.**

That red slot turned out to be `Moonbeam`, a Manekin from Miliastra Wonderland -
6 GREY stars, DEF 147 above ATK 106, Elemental Mastery exactly 0. Every rarity
heuristic that worked on the other seven roster slots fails on it. Declining to
name it from portrait art was correct: it is not in the standard roster at all.
Two traps are recorded for any future mapper - the name probably being
player-assigned rather than a game identifier, and the grid icon disagreeing
with the model because a Manekin is customisable.

### The defect that matters most, because it did not look like one

`tools/wish_authkey.py` looked for the Chromium cache under
`%USERPROFILE%/AppData/LocalLow/...`. It is under the GAME INSTALL. `--scan`
printed "no webCaches directory found yet. Has Genshin Impact ever been launched
on this machine?" while the operator had Wish History open and that `data_2`
held 15 ASCII occurrences of `authkey`. **A wrong directory and a missing one
collapsed into one sentence**, and the sentence sent the reader to look at the
game rather than at the path.

Fixed in `f930263` as an ordered candidate list with the user-profile form
demoted rather than deleted. `tests/test_wish_authkey_paths.py` pins the ORDER
and not the membership, because the list can contain the right directory and
still try the wrong one first.

A second measurement is pinned in the same module though it never shipped: a
scratch extractor capped candidates at 1500 bytes against a real URL of 1755
with a 1452-byte authkey, so it truncated the credential and the endpoint
answered `retcode -100: authkey error` - which reads as an expired key rather
than as a scanner bug. The module's own cap is 4096 and was never vulnerable;
pinning it stops 4096 being a round number. The long-URL arm's own guard fired
on its first run, refusing itself at 1632 bytes against the measured 1755.

### End to end on the live account

After the fix, all six `gacha_type` values returned `retcode: 0, message: "OK",
region: "os_usa"`, which promotes `_HOST_NEW` from UNVERIFIED to verified
against a real 200. The history is empty and that is a TRUE ZERO: the game's own
Wish History page rendered "No record" in the same minute and states that
records appear about an hour after a wish. **Editing the puller there would have
been fixing a correct client against a lagging server**, and the two surfaces
agreeing is what distinguishes the two cases.

### Sibling-C's section 5 ingested

Sibling-C reported that root-walking guards cannot see a nested checkout and
measured 10 of 15 of its own with no exclusion. Measured here across 39 test
modules: **1 root-walking and excluded, 4 root-walking and NOT excluded, 34 not
root-walking.** The 34 are not lucky - a guard whose corpus comes from
`git ls-files` is structurally immune, because git does not descend into a
nested checkout while the filesystem does. That is `b55825e` turned the other
way round.

`tests/test_guard_worktree_blindness.py` proves the defect with the shipped
guard's own code rather than a reimplementation, and carries the contrast arm
that keeps the other number meaningful. `docs/INBOX_TRIAGE_2026-09-07-0710.md`
triages all five sections of Sibling-C's note.

**Sibling-C's section 4 landed immediately and on this very session's work.**
The triage document first wrote a placeholder as a literal Windows path with a
bracketed account segment, and
`test_no_tracked_file_carries_an_absolute_path_naming_a_real_account` went red.
The guard was right and the prose was wrong. The regex was NOT widened.

### Two mechanical traps paid for again

An in-progress `.mp4` segment will not open - `moov atom not found`, because the
index is written when the muxer closes. Matroska decodes to the last complete
cluster. The recorder was switched to `.mkv` mid-setup, and the proof arrived at
shutdown: the force-killed final segment still decoded to a frame with mean 66.6
and standard deviation 18.2.

Matching a daemon by substring over its whole joined command line is wrong. A
probe process whose own source text names two daemons matches both, and it
briefly killed every real watcher while the probe survived.
`find_python_daemon` matches `argv[1]` only.

**The heredoc backslash trap bit twice more**, once turning a redaction regex
into `unterminated character set` AFTER nine real candidates had been printed -
a redaction that fails open is how a credential reaches a transcript - and once
as a `unicodeescape` SyntaxError. Both were fixed by writing a real file.

### CI went RED on this session's work, and the local gate could not have caught it

`f930263` and `1e8c140` both failed on the runner while every local gate was
green. Fixed in `7e807a0`. Three failures, three different ways for a green
local run to mean nothing, and the local box being Windows while the runner is
Linux is the common cause.

**Windows-only symbols are a TYPE error on Linux, not only an import error.**
`ctypes.wintypes` and `ctypes.WinDLL` are marked `sys.platform == "win32"` in
typeshed, and one error in one module stops mypy before it checks anything else.
That is the same failure shape `mypy.ini` already records for numpy's PEP 695
stub. mypy narrows on `sys.platform`, so the fix is a real guard rather than an
ignore comment. `subprocess.DETACHED_PROCESS` is the same class with an extra
trap: **`hasattr` guards the interpreter but does NOT narrow for mypy**, so that
code was already correct at runtime and still an error under the checker.

**A test of an ORDERING read the real environment.** `USERPROFILE` is unset on
Linux, so the module correctly appended no user-profile candidate and the test
asserted the absence of something the code was right not to produce. It now sets
the variable to `tmp_path` - and NOT to a literal home-shaped string, because
`tests/test_machine_identity.py` forbids exactly that and caught the first
attempt. The guard was right: a test that needs SOME home directory does not
need a plausible-looking one.

**A test asserted a behaviour the module deliberately does not have.**
`_web_caches_root` documents returning the FIRST candidate when none exist. The
old test asserted a non-existent override is never returned, which is true on a
machine with a Genshin install and false on a runner without one. Asserting a
behaviour the code deliberately does not have is not a stricter test, it is a
wrong one. Replaced by two tests that monkeypatch the candidate list, so neither
depends on this machine.

**And a guard reported a number that was not the number it named.**
`tests/test_mypy_scope.py` took the FIRST digit off mypy's tail line. Clean,
that is the file count. With errors the line is
`Found 3 errors in 3 files (checked 31 source files)` and the first digit is the
ERROR count, so the CI failure read "mypy checked 3 files but the configured
roots select 31" and sent the reader to look at the SCOPE while the real problem
was three platform errors. It now reads the count immediately before
`source files` and fails loudly if it cannot find one. **A guard that reports the
wrong number is worse than one that stays quiet**, because it answers the
reader's question wrongly before they ask it - the same lesson as the wrong
rationale, in numeric form.

The fix was verified by DELETING `USERPROFILE` and `RSC_WEBCACHES_ROOT` from a
subprocess environment and re-running the two affected modules there: 14 passed.
Running them the ordinary way cannot distinguish a fix from a platform accident.

### Verification, measured 2026-09-07 at `f930263`

`ruff` All checks passed. `pytest tests` 1094 passed, 1 skipped. `pytest
agents/pity_engine` 80 passed. `shell node --test` 52 pass, 0 fail. `headless
--once --dry-run` exit 0. `mypy` Success, 31 source files. Licence QA 41,
docs QA 23, `qa_companion.py` 17 passed, 0 failed, 1 skipped.

`mypy` required one config change to stay honest: `tools/` is a `files=` root
and `tools/screen_capture.py` imports Pillow, whose type hints reference numpy,
whose `__init__.pyi` uses a PEP 695 statement that is a syntax error under the
pinned `python_version = 3.11`. One third-party stub error stops all further
checking, so the gate would have read as a single unrelated failure rather than
as coverage. `follow_imports = skip` plus `follow_imports_for_stubs = True`,
scoped to numpy only, with the existing rationale extended rather than replaced -
that rationale rejected silencing numpy for a DIFFERENT entry path, a test
directory, where there was a directory to drop. Here there is not.
`screen_capture.py` also dropped numpy entirely; the mean-hash it computes is
byte-identical to the numpy one, checked against a captured frame.

### The roster sweep found one thing and honestly failed to find another

A read-only agent OCR'd 1328 screenshots (166 keyword hits) and 1384 video
frames sampled at 1fps.

**Dehya's acquisition WAS found**, at 09:20:40.561091Z: "Obtained New Character
/ Dehya", 5 gold stars, Pyro, followed four seconds later by an Invite Character
screen reading "Dehya has been invited". That is a real acquisition plus an
event party invite, which is consistent with the retraction above rather than
with the trial hypothesis it replaced.

**Tesseract missed that frame completely** - zero keyword hits on a frame whose
text says "Obtained New Character" in plain view, because the splash is a
stylised font over a full-screen fire effect. An OCR-only sweep returned a
confident zero on the single most important frame in the corpus. Any future
roster extractor must not be OCR-only, and an OCR zero over game splash text is
not an absence.

**Noelle's acquisition moment is NOT FOUND and was not inferred.** She is in the
party roster from 09:42:59Z, and the Beginners' Wish banner still read "Chances
Remaining: 20/20" at 09:12:09Z; two 10-pull reveals at 09:12:25 and 09:17:26
were on the Standard banner and did not contain her. The gap is 09:20:44Z to
09:42:59Z. **NOT FOUND AT 1 FPS IS NOT THE SAME FACT AS NOT PRESENT** - the
recording is 15fps and one frame in fifteen was examined, a wish reveal is
short, and the frame is most likely still on disk. It stays open.

---

## 2026-09-07 - Three guards that overstated their reach, and a claim gate that took three rounds to become honest

Seven commits, `3f7f23f` through `2b8fcbe`. Four agents dispatched worktree
isolated, three of them adversaries on distinct lenses. **Every adversarial pass
that ran against a done-claim returned REFUTED**, and each refutation is recorded
below with what it changed, because two of them refuted work this merger had
done rather than a builder's.

### The top roadmap item was DEAD, and the source was gone

`moon_sync_inbox/from-<sibling>-verbatim/` no longer exists - not here and
nowhere on this machine. Sibling-C DELETED it from all four sibling trees after
Sibling-A found the operator's Windows account name in 3 of its 48 files and
Sibling-C's own sweep raised that to 19 of 48, including
`tests/test_stop_claim_gate.py`. So the claim-gate PORT, the `pytest_guard`
port, the `edit_lint_check` port and the two `drift_guard` checks are all
blocked on a withdrawn payload.

**Containment here was measured, not assumed:** 0 tracked files carry the account
name, `git log --all -S` over it returns 0 commits, and 0 of the four named tool
filenames were ever added. Nothing from the drop entered this tree.

**This tree's OWN outbound drop was swept, and the check was armed first.** 7
files across 4 sibling inboxes, byte-identical to the tracked originals by
sha256. Five needle categories, every one proven to fire on a planted line before
the real scan: account name 0, home path 0, short path 0, sibling root 0. The 16
`users-root` hits are `tools/publish_next_session.py` and its test - the tool
whose job is REFUSING account paths, whose pattern is an account-shaped path and
whose fixtures use an invented operator name. A detector's own pattern trips its
own sweep, which this tree had already written down.

**The first run of that sweep reported two categories UNARMED**, and that is the
lesson worth keeping. Both path patterns had been written through a shell
heredoc, which silently ate one backslash from each character class and turned
`[\\/]` into `[\/]` - a class matching forward slash only. Both then scanned
every Windows path in the payload and found nothing. Without the positive control
that would have been reported as a clean result.

### Sibling-A's pickaxe check, run here with both controls

Positive control 9 commits at rc=0, negative control 0. Then, scoped against
`origin/main` because this repository is public: the account name returns **0
across every ref**. `C:\Users` 6, `AppData/Local/Programs/Python` 1 and
`Claude-Session` 4 are all false positives - the account-path detector, and the
hook that strips the session trailer plus the test proving it strips it. Not
taken on faith: every UUID-shaped and long-hex identifier in the published
matches was intersected with the 1567 real session ids on this machine.
**Intersection 0.**

**One live instance of the resurrect-a-blob trap was found and reaped.** Two
stale `worktree-agent-*` branches from earlier sessions were still present as
refs with no worktree attached - `git worktree list` reported none while
`git branch -a` reported both. They held 0 unique objects this time. That is
luck: a worktree branch from a session predating a history rewrite is exactly the
ref that resurrects a purged blob. **The standing check is `git branch -a`, not
`git worktree list`** - the branch outlives the worktree.

### The inbox watcher was blind to content and to directories - `6f37ce5`

Measured against the shipped functions in a fixture inbox BEFORE any edit: 2 of
7 properties held. `_notes()` globbed `*.md` at the top level and a DIRECTORY
has no `.md` suffix; the watermark stored bare name strings, so the key was the
filename alone. All five repos on the cross-repo channel had built the same
hole independently, each in a different mechanism. Sibling-E's phrasing is the
one this tree keeps: it was not misclassified, it was invisible.

Now 7 of 7. Notes keyed on (filename, content sha256). Drops are first-class
entries keyed on (name + "/", manifest digest) computed over what is ON DISK -
one line per file holding the drop-relative POSIX path, a NUL, then that file's
sha256, sorted, joined, hashed once. An empty drop still reports. A
`UserPromptSubmit` hook was added because `SessionStart` fires once and cannot
see a note landing mid-session; it printed nothing when nothing was unread and
surfaced three notes mid-session on its first live firing.

Two other key shapes were REFUTED by siblings and are deliberately not
implemented: a FILE COUNT stays equal when a sender replaces a file, and a digest
of the sender's `MANIFEST.sha256` FILE keys identical for a payload edited
without regenerating the manifest.

**Migration verified read-only against the real state before anything was
committed:** the shipped watermark held 88 plain name strings, and a version bump
treating those as unseen would have dumped the whole inbox back on the operator.
88 grandfathered, 1 genuinely new, watermark sha256 unchanged across a reporting
run. Verification pointer: `tests/test_watch_inbox.py`,
`test_a_legacy_name_only_watermark_still_counts_its_notes_as_read`.

**The report may not carry a payload byte.** Sibling-D's rule, relayed by
Sibling-A: everything the watcher prints is injected into a session with the
harness's own authority, before any judgement is applied, so an imperative
sentence in a sibling's file must not arrive wearing this watcher's voice.
Pinned by `test_the_report_never_carries_a_payload_byte`, parametrized over all
three report modes, asserting the NAMES appear first - a watcher that crashed
and printed nothing would satisfy a bare no-payload assertion perfectly.
Mutation: a variant appending a 60-character body preview leaks the marker and
reddens it.

### Property 6 - bytes-equal is not the same fact as did-not-write - `bc98c8d`

Sibling-D's finding, and theirs alone. They ran their four hook commands
verbatim to confirm the paths still resolved after an edit; the `SessionStart`
one was their watcher, and it marked three genuinely unread notes as seen.

Measured here on the LIVE watermark: two reporting runs, identical unread sets,
bytes unchanged, **mtime unmoved**. This tree passes, and not from virtue -
`--mark` has been a separate flag since the first version, so property 6 held
by an accident of the original shape rather than because anyone had seen the
failure. Sibling-D's statement of the cause is better than the one recorded
here and replaces it: acknowledgement as a SIDE EFFECT of reporting means
anything that can report can silently consume, including a probe whose only
purpose was to check that the watcher runs.

The mtime half is the part this tree would not have caught. The existing arm
asserted the watermark's bytes and stopped. An atomic write producing identical
content still moves the modification time. Mutation-proved: a variant rewriting
the state file with its own identical bytes PASSES bytes-equal and FAILS mtime.

### mypy checked a quarter of the tree and two agent files called that done - `26543e2`

`python -m mypy` printed `Success: no issues found in 23 source files` against 92
tracked `.py`. A narrow scope is a design. What made it a defect is that
`.claude/agents/builder.md` told every builder to run mypy before reporting done
and `.claude/agents/adjudicator.md` listed it among the criteria for GRADING an
arbitrary slice. **Zero out of zero, institutionalised in the roster, where every
future agent inherits it.** It happened during this session: a builder working in
`tools/` reported mypy green and flagged the gap itself, in its own UNVERIFIED
section rather than its results. The agent was more honest than the instruction
it was following.

The shape is worth naming because it recurs: **the config was documented in the
wrong line.** The `mypy.ini` comment explained `exclude=` - a real, measured,
correct reason covering 5 files. `files=`, which decided the other 64, carried no
rationale at all, so a reader found a reasoned comment beside the wrong mechanism
and stopped looking.

Measured by adding each dark directory alone, in a scratchpad config so nothing
changed to take the measurement: `tools/` 0 errors and now IN, `surface/` 1,
`headless/` 3, `ops/` 8, and `scripts/` BLOCKED rather than chosen - mypy refuses
it with a duplicate-module-name error needing an `__init__.py` first. mypy now
reports 26. `[mypy-tests.*]` was cited by the `exclude=` comment as recording the
intent and is dead config; it now says so.

`tests/test_mypy_scope.py` is the guard, and mypy was the only tool here without
one. It holds the dark set as a LITERAL with a measured reason per entry rather
than deriving it from `mypy.ini`, because a test that recomputes its expectation
from the file it checks can never fail.

**That guard then had its own defect, found by the next builder and fixed in
`b55825e`.** mypy WALKS THE FILESYSTEM; `git ls-files` does not. Any unstaged
`.py` under a covered root made the two disagree, so every builder writing a new
module in `tools/` would have met a spurious red - the same wave-it-through
failure the guard exists to prevent, arriving from the other side. The arm now
asserts `mypy count == tracked-under-roots + unstaged-under-roots`.

### Sibling-E's detector gap, closed - `3f7f23f`

Sibling-E ported `tests/test_no_secret_literals.py`, ran it against their tree
and reported a false positive back: the env destination assigned a bare
lowercase PowerShell variable that had itself been read from
`GetEnvironmentVariable` a line earlier. Reproduced here first. Latent rather
than live - one tracked `.ps1`, no instance of the shape.

**Sibling-E's suggested fix was not taken as stated, and the reason
generalises.** Adding a bare `$name` to `ENV_REFERENCE` would have been wrong
here: that pattern is applied with `.search()`, so it would exempt any value
merely CONTAINING a variable. `VARIABLE_VALUE` is a separate pattern matched
against the whole stripped value.

Mutation changed the shipped test set. Three mutants: dropping the exemption is
caught, dropping the TRAILING anchor is caught, and **dropping the LEADING anchor
is EQUIVALENT** because `re.match` already anchors at the start, so `^` is
documentation rather than mechanism. Without the third arm the trailing-anchor
mutant survived: a value shaped variable-then-literal matched on its variable
prefix and the appended secret rode out exempted. Measured as a real false
negative before the arm existed.

Sibling-E's second suggestion - parametrize the exemption assertion over every
exempt file - was already present here at
`test_the_detector_would_fail_on_this_file_without_its_exemption`.

### The engine changelog, and why the revision did NOT move - `1794a5e`

`ENGINE_VERSION` is the COMPUTE revision, returned to callers as
`engine_version` so a consumer can decide whether a cached forecast is still
valid. Every forecast is byte-identical across the exclusive-bind change, so
bumping it would have signalled a compute change that did not happen and
invalidated correct caches. The entry goes in a new "Service changes at engine
revision 0.1.0" section, because the file's convention is that a bump PREPENDS
and a prior version's line is never extended.

**Which half is load-bearing was measured, and it is not the one the name
suggests.** The nine-cell bind matrix in
`agents/pity_engine/tests/test_service.py` has `first=none` and
`first=exclusive` as identical columns, so with `allow_reuse_address = False`
already set, adding `SO_EXCLUSIVEADDRUSE` changes no observable outcome against
a listening socket on win32. Dropping `SO_REUSEADDR` is what closes it; two
stock servers are the single cell in nine that double-binds. Crediting the flag
would have been Sibling-A's durable-wrong-rationale defect, which they
described the same night: a wrong explanation outlives a wrong line of code,
because it answers the next reader's question before they ask it.

### The claim gate - three rounds, three refutations, and it lands UNWIRED - `2b8fcbe`

`tools/stop_claim_gate.py` plus 115 arms. Re-implemented from Sibling-C's
published PROSE; no Sibling-C code was read, and the six questions asked of
Sibling-C by note are unanswered.

  round 1  lexical credit rule    REFUTED. count_mismatch 71 percent false on
           the first pass's scoring, 60 percent on the second pass's
           re-measurement of the same build.
  round 2  calibrated lexical     REFUTED. False positives fell and laundering
           holes opened instead - `target: 930 passed ... in 17.50s` credited as
           evidence, the same line via `grep` credited, the comment bar bypassed
           by one tab because `normalise_log_line` keeps only text after the last
           tab. A dedup THIS MERGER added made `tests_pass_without_run`
           structurally unable to fire, and the docstring asserted four
           mechanisms the code did not have.
  round 3  provenance             64.1 percent false, then 55.5 percent with
           one-hop chaining.

Provenance is the correct mechanism and closed every laundering hole: a summary
is credited only from output of a command classified as a test RUNNER, so `cat`,
`grep`, `git log` and `tail` are not evidence sources BY CONSTRUCTION rather than
by a lexical bar that kept being bypassed. Chaining then credits a reader of a
file a runner redirected into, one hop, because this project's own convention is
to redirect and read back - an exit code read through a pipe is the pipe's. Six
bars keep chaining from re-opening what provenance closed, each with an
acceptance arm beside its refusal arm.

**55.5 percent is still too high to arm, so no Stop hook is declared and
`.claude/settings.json` is untouched.** Sibling-C published the reason: a gate
that cries wolf on correctly-sourced figures trains the reader to wave it
through, which is exactly when it stops catching the real thing. The 55.5
figure is also the producer's own, un-adjudicated, and it does NOT compare to
the 68.0 percent from the round before - that sample was 313 files and 254,497
records where the same recipe selects 317 files and 94,136 records. The
comparable pair, one sample one pass, is 64.1 -> 55.5 percent and 348 -> 274
findings.

**`tests_pass_without_run` was deleted outright.** Across 316 transcripts and
1877 checked claims it emitted 0 findings, because it arms only when every
evidence list is empty, which guarantees another check already flagged the same
record. A name in the contract tuple that cannot fire is the defect this gate
exists to catch.

Also fixed, and found by neither adversary: `"C:/.../gh.exe" run view` never
matched `\bgh\s+`, so 40 sessions that HAD read CI were flagged.
`ci_green_without_fetch` went from 43 findings to 3, all three hand-checked.

Measured, not inferred: `cd shell && node --test` prints `pass 52` and
`duration_ms 148.6112` - word before number, no `in <float>s` - and its real
output through the parser yields 0 summaries, so classifying it a non-runner
costs nothing. Pinned so it reddens if node's shape changes.

### Readings, 2026-09-07 at `2b8fcbe`, historical rather than a claim about now

licence 41, docs 23, qa_companion 16 passed 0 failed 2 skipped, ruff clean,
`pytest tests` 1087 passed 1 skipped, `pytest agents/pity_engine` 80,
`shell node --test` 52 pass 0 fail, headless dry-run exit 0, mypy 27 source files
clean, `RSC_REQUIRE_HOOK_GATE=1 pytest tests/test_hook_gate.py` 12 passed,
`git worktree list` 0 beyond the main checkout. The single skip is the opt-in
network test in `tests/test_ingest_client.py`.

---

## 2026-09-06 - The publish sweep, a history rewrite, and rebuilding the remote

Six adversaries on distinct lenses, four builder slices, a `filter-repo` rewrite,
a delete-and-recreate of the GitHub repository, both shared-governor rounds, and
a durable inbox watcher. **All six adversaries returned REFUTED.** The repository
was not safe to publish as it stood, and the two findings that mattered most
could not be fixed by editing a file.

**THE SWEEP FOUND TWO SERVER-SIDE LEAKS, AND A FORCE-PUSH WOULD NOT HAVE CLOSED
EITHER.** The operator's Windows account path sat in blob `4401b1a8`
(`.claude/commands/done.md` line 172) inside 8 of the 33 PUSHED commits. The
forward fix had landed weeks earlier; the published record was never backfilled,
which is the `CLAUDE.md` rule about a data fix not being done until corrupted
records are backfilled. Separately, two commits force-pushed away earlier that
day - `a72a5c6` and `20385fd` - were still served by GitHub with a
`Claude-Session:` URL in them, and their SHAs were published by the repository's
own Events API and Actions run list.

That second finding is the load-bearing one and it is general: **a force-push
does not purge objects from GitHub.** This repository had already proved it once
and nobody noticed. So the remedy was not another rewrite - it was to rewrite
locally, DELETE the remote, recreate it, and push only clean history. Verified
from the server side afterwards rather than assumed: the two orphans and the
pre-rewrite HEAD all return HTTP 422 `No commit found`, the leaked blob returns
HTTP 404, and a cold clone of the new remote carries 0 account-path blobs of 291
and 0 session trailers.

Cost of the recreate, paid deliberately: the Actions run history and the creation
date. The description and all 17 topics were restored. Nothing else was lost -
0 stars, 0 forks, 0 watchers, 0 open issues.

**Guards cannot see this class, and both of them say so.**
`tests/test_machine_identity.py` builds its corpus from `git ls-files`, which is
the current checkout only, and `tests/test_commit_trailers.py` walks `git log` on
HEAD. Both passed throughout while the leak was live on the remote. Each is
correct for the question it asks; neither asks "what is already published".

**THE OBJECT STORE FOUGHT BACK THREE TIMES, and the mechanism is worth the
entry.** After the rewrite the leaked blob kept reappearing. In order: a
`FETCH_HEAD` left by fetching the backup bundle for a tree comparison; then
`refs/remotes/origin/main` surviving inside `.git/packed-refs` after
`update-ref -d` had removed the loose ref; then creating four agent worktrees,
which checked out the PRE-REWRITE commit and resurrected the whole history into
the shared object store, because worktrees share `.git`. `gc --prune=now` is
powerless against any of them - each was a live reference. The rule learned: an
unreachable-object purge is only true at the instant it is measured, and it must
be re-measured after anything that can create a ref. The final purge worked only
because the remote was deleted FIRST, removing the thing that kept restoring it.

**AN ERROR THIS SESSION MADE, recorded because the scoping mistake is
transferable.** The cross-repo adversary was instructed "do NOT read any
sibling tree on this machine - stay inside `C:\Resin Compute`", to stop it
rummaging in projects that are not ours. That instruction also made the one
question that mattered structurally unaskable: `ops/loop/winmutex.py` and
`slots.py` were already world-readable in Sibling-E's PUBLIC repository and had
been for five weeks, so publishing this tree disclosed nothing new about them.
A finding was raised to the operator and to two siblings on a premise nobody
had tested. Retracted in full. The lesson is not "read sibling trees" - it is
that a scope which protects a neighbour can also blind the check, and "is this
already public" was answerable from public data alone.

**FOUR BUILDER SLICES, write-list union proven disjoint with `sort | uniq -d`
before dispatch.** 12 files modified, zero write-list violations, zero untracked
residue. What landed:

- **The repository declared itself unlicensed in a tracked manifest.** The
  lockfile carried the pre-ADR-006 licence token against `shell/package.json`'s
  `GPL-3.0-or-later`. Commit `9cc98c6` flipped the manifest AND added the guard
  against exactly this in the same commit, but never regenerated the lockfile -
  and the guard swept 5 files of 153, so it could not see it. The guard now
  derives its corpus from `git ls-files` and was observed RED against the
  unfixed lockfile before the fix. `tests/test_licence_posture.py`, 33 arms to
  41.
- **Two compliance documents made checkable false claims.**
  `docs/LICENSE_NOTES.md` called the fixtures "synthetic" while citing a README
  that says the label was false of two of its three files, and claimed game item
  names appear "never as code identifiers" while `core/types.py` has `PRIMOGEM`,
  `INTERTWINED_FATE`, `STARGLITTER` and `HEROS_WIT` as enum members. ADR-002
  carried the same wording and got a BANNER ADDENDUM instead - 28 insertions, 0
  deletions, body provably unrewritten. The sibling of the trademark overclaim
  in `docs/SPEC_SCAFFOLD.md` was found by the same builder and fixed with it,
  per the fix-every-sibling rule.
- **Both CI ASCII gates passed any path containing a space.** `xargs` splits on
  whitespace; the gate warned on the fragments and returned 0. The anti-vacuity
  arm checked the LIST was non-empty, never that anything was SCANNED. Selection
  is now a NUL-delimited partition on the `.md` suffix, complementary by
  construction, with `--expect-count`. Coverage went from 139 of 153 to 153 of
  153, uncovered set EMPTY and halves disjoint. The 14 files no gate touched
  included `ops/install_scheduled_task.ps1`, the file class the entire ASCII
  rule exists for. `docs-guards` also ran both suites in ONE root-level pytest
  invocation, 359 tests, which `pytest.ini` forbids by name.
- **A pre-cut hole in the commit-time gate.** `tools/precommit_gate.py` exempted
  a data/external/ prefix from the 7-bit rule. That directory is gitignored
  NOWHERE and appeared in no other file in the tree - it is deliberately written
  without backticks here, because it names nothing that exists and the docs
  guard correctly rejects a dead pointer. So the one gate that would flag a
  fetched upstream payload was pre-disabled at a location `git add -A` would
  happily stage. Every remaining exempt prefix must now pass `git check-ignore`.
- **The exclusive-bind fix had landed at one call site only.**
  `surface/server.py` grew `_ExclusiveHTTPServer` after two dashboards bound
  8791 and the older one answered everything. `agents/pity_engine/__main__.py`
  kept the stock `ThreadingHTTPServer`, so two engines bound 8790 with
  byte-identical banners while the first served every request - on the port
  README section 6 tells a stranger to run. Ported TDD-first with an
  immediate-restart arm and an ephemeral port.
- **Two docstrings misled an auditor.** `tools/publish_next_session.py` claimed
  to be "the one thing in the tree that writes outside it"; `make_shortcut.py`
  and the task installer also do. README described the Windows Scheduled Task in
  nine words and never said how to remove it, though it is hidden, elevated,
  fires at every logon, has no execution time limit, and survives deleting the
  clone. The removal command is now published, DERIVED from
  `ops/install_scheduled_task.ps1` line 45 rather than executed.

**THREE AGENTS CORRECTED THEMSELVES, which is the shape the protocol is for.**
The engine builder's mutation test refuted its own assumption: dropping
`SO_EXCLUSIVEADDRUSE` alone left every arm green, and a full nine-cell bind
matrix showed only `reuse`/`reuse` double-binds, so `allow_reuse_address = False`
is the load-bearing half and no test on this platform can pin the setsockopt.
That was re-derived independently at the merge rather than taken on trust, and
`surface/server.py`'s docstring - which credited the wrong half - now records it
along with the fact that a guard claiming to pin that line would be a guard about
nothing. The CI builder's own surviving-neighbour arm caught both workflows
writing their file lists into the checkout. The licence builder found a hole in
the guard it had just written: a correction note quotes the sentence it corrects,
so a whole-file sweep passes on the quotation.

**BOTH SHARED-GOVERNOR ROUNDS LANDED, and the leak fix is measured here.**
Sibling-E rotated the mutex names (`winmutex.py` to `0b112a4f`) and fixed the
`hold()` release-path leak (`slots.py` to `629c3d51`). Both were copied
BYTE-WISE off Sibling-E's live tree with `cp`, re-hashed from THIS repo's own
disk against the published values, and the index blob compared to the disk
bytes for each. Measured on this box, 8 workers over 2 slots at `backoff=0.02`,
40 rounds:

```
old 1c4f8af4   35 of 40 rounds leaked   51 lockfiles   69 SlotTimeouts
new 629c3d51    0 of 40 rounds leaked    0 lockfiles    0 SlotTimeouts
```

That also explained an unrelated-looking red:
`test_contending_threads_never_exceed_max_slots` failed once with a SlotTimeout
during a full-suite run and passed six times in isolation immediately after. It
was the leak surfacing as a flaky test under load, in a repository that does
not even acquire a slot - the tests are the only callers here. Ten consecutive
runs since adopting the fix: zero failures. Sibling-C was right to refuse the
`slots.py` bytes until they were announced; the announcement arrived and both
rounds are now three-way equal, verified by hashing all three disks directly.

**A DURABLE INBOX WATCHER, because a live one dies with its session.**
`scripts/watch_inbox.py` plus `tests/test_watch_inbox.py`, 11 arms. Watermark
under `ops/runtime/`, written through `core/atomic_io.py`. Reading never
acknowledges; an absent inbox is a plain line rather than a traceback; a corrupt
watermark degrades toward RE-REPORTING, because a duplicate read costs a glance
and a dropped note costs a sibling waiting on an answer nobody knows they owe.
Keyed on NAMES rather than content hashes, with the cost accepted and pinned in
both directions - a rename re-surfaces a note, which is strictly better than an
EDITED note reading as already seen. Four mutants killed. The first mutant
written for the corrupt-watermark arm was EQUIVALENT and passed, which is
recorded because a surviving mutant is evidence only when it actually changes
behaviour.

**Decisions taken, so they are not re-litigated.**
`docs/adr/ADR-004-port-block.md` stated that a port grep across six sibling
trees hit "decompiled game assets, a strings dump"; that characterised the
contents of unpublished trees, was never load-bearing for the port argument,
and is redacted WITH the redaction recorded in the ADR rather than done
silently. Charter v3 from Sibling-C is ADOPTED, with one dissent filed: "commit
onto the worktree branch, push it, then remove the worktree" assumes a workflow
where agents commit, and this tree's protocol forbids builder commits outright,
so the invariant - no worktree is removed until its work exists somewhere that
survives the removal - should be the charter text rather than the step
sequence.

Counts measured 2026-09-06 on Python 3.14.4 at `dd1ac02`, as a historical
reading: licence QA 41 passed, docs QA 23 passed, `qa_companion` 16 passed 0
failed 2 skipped, ruff clean, `tests` 852 passed 1 skipped, `agents/pity_engine`
80 passed, `shell` node 52 pass 0 fail, headless smoke exit 0, mypy clean over 23
source files. The tree still DECLARES 3.11 in `CLAUDE.md`, `mypy.ini` and
`ruff.toml`, so that reading is green on 3.14 only; the divergence predates this
work and was again not touched.

## 2026-09-06 - Joining the cross-repo concurrency governor, and being refuted twice

`ops/loop/slots.py`, `ops/loop/winmutex.py`, `tests/test_loop_concurrency.py`,
`tests/test_core_config.py`, `core/config.py`.

This repo took the third slot in a machine-wide concurrency bucket shared with
Sibling-E and Sibling-C, vacated when Sibling-B was archived. The two governor
files are BYTE-IDENTICAL-BY-CONTRACT across all three trees. Vendored LAST, per
the ordered round the siblings specified, because this repo was the only
participant with no pin to break.

**Method, and it is the point of the entry.** The files were copied with
`shutil.copyfile` off Sibling-C's live tree, never with `Path.write_text` -
that emits CRLF on Windows and the contract is on bytes. Both sibling trees
were hashed BEFORE the copy and this repo's own disk was re-hashed AFTER it;
the hand-off note's digests were used only as a value to check against.
`.gitattributes` forces `*.py eol=lf`, so the index blob was compared against
the disk bytes as well - they match, which is what proves the pin survives a
fresh clone on an `autocrlf=true` box.

**THE GOVERNOR IS INERT AND THE TREE SAYS SO IN FOUR PLACES.** No production path
calls `slots.hold()`; the only callers are inside `tests/test_loop_concurrency.py`
against a `tmp_path` bucket. `headless/runner.py` is a job runner whose daemon
mode runs in-process job passes - verified by reading `run_daemon`, not assumed.
This is a parity contract joined ahead of need. Two of the three participants
acquire for real; this one's lane is reserved and unclaimed.

**Two of three adversaries returned REFUTED, and they were right.**

- A mutant removing `hold()`'s queueing passed the entire suite and fails
  Sibling-C's. The port had collected worker exceptions into `failures` and
  never asserted on them. Restored as `assert not failures` in
  `test_contending_threads_never_exceed_max_slots`; the mutant now fails even
  with a legitimate re-pin applied, and 30 consecutive runs stayed green.
- `SHARED_SHA256` drove both the presence guard and the digest guard, so deleting
  one entry disarmed both in a single edit - 18 passed, exit 0, silent. Adding an
  `__init__.py` beside the vendored pair, or a third module, was equally green.
  One root cause: the
  pin named FILES, not the DIRECTORY. Closed by `VENDORED_MODULES` plus
  `test_the_pin_covers_every_vendored_module_and_nothing_was_added`.
- `tests/test_core_config.py` PROMISED that any future wiring of the ceiling to
  `os.environ` "has to turn this file red", on the strength of a substring scan of
  one function body. Defeated in one line by the module's own
  `field(default_factory=...)` idiom, which moved the ceiling to 9 while every
  guard reported green. A guard that overstates its reach is worse than a missing
  one: it tells the next session not to look. Closed structurally by
  `test_the_ceiling_field_has_no_default_factory` and behaviourally by
  `test_a_poisoned_environment_cannot_move_the_ceiling`.
- The missing fourth arm of `is_stale` - the mtime fallback that stops an
  UNPARSEABLE lock wedging a lane - is now covered by
  `test_a_corrupt_lock_cannot_wedge_the_bucket_forever` with its survivor arm.

Every fix was mutation-tested AFTER the fact. Five mutants that were green before
are red now. That order matters: the session's own lesson is that a guard nobody
has watched fail is a guard nobody has tested.

**A REAL DEFECT IN THE SHARED FILE, REPORTED RATHER THAN FIXED.** Under contention
on Windows the vendored `hold()` leaks lockfiles: measured here at 33 of 40 rounds
with 8 workers and 2 slots. The mechanism was proven deterministically, not
inferred - `reap` to `is_stale` to `_read` to `Path.read_text` holds a handle
opened without `FILE_SHARE_DELETE`, so the releasing holder's `slot.unlink()`
raises `PermissionError` winerror 32, `except OSError: pass` swallows it, and the
release is LOGGED anyway. A log-reading overlap analysis therefore records a
release for a lock still on disk, and the lane is not reclaimed for 4.5 hours.
Re-pinning is a JOINT act, so the file was not touched; the reproduction went to
both siblings through `moon_sync_inbox/`.

**The leak DISARMS ITS OWN REAPER, and this half is deterministic rather than
statistical.** An orphaned lockfile keeps the payload written at `hold()` entry,
so if the leaking holder is still alive both of `is_stale`'s fast arms answer
"not stale" - the pid IS alive and the ts IS recent - and `reap()` skips it.
Measured directly, no race needed: `is_stale` False, `reap` removed 0, ghost
still on disk, and only the 4.5-hour age arm ever clears it. That points
straight at a long-lived controller running many cycles under ONE pid, where a
lane leaked in cycle N is unreapable for the life of the process and narrows the
bucket for the other two repos. Reported as an addendum the same evening. The
rate figures are bounded honestly in that note: 107 of 200 rounds at
`backoff=0.02`, and a 30-of-30 fully-wedged result that ran at `backoff=0.0` and
is a demonstration of the terminal state, NOT a rate. The production defaults
are `backoff=2.0, jitter=2.0` and that rate was not measured.

**Errors made and corrected in-session, recorded because the next reader
deserves them.** The `690d8b7` commit message cited
`test_a_missing_vendored_file_is_a_failure_not_a_skip`, a test that has never
existed - the name came from a dispatch brief and was not read back off the
file. The real one is `test_the_vendored_governor_is_present`. The same message
called the parity "recorded from three separate disks", which overstates it:
all three roots are on one volume, and Sibling-C's note hashed THIS repo's
files rather than printing its own. Both are corrected in `bb7f1ab`, which
cannot amend them.

Counts measured 2026-09-06 on Python 3.14.4, as a historical reading: `tests` 806
passed 1 skipped, `agents/pity_engine` 76 passed, ruff clean, mypy clean. Note the
tree DECLARES 3.11 in `CLAUDE.md`, `mypy.ini` and `ruff.toml`, so that reading is
green on 3.14 only; the divergence predates this work and was not touched.

## 2026-09-06 - Landing the public-repo fixes, and a refutation that reversed one

The fix session for the previous entry's audit. Nine slices, worktree-isolated,
dispatched against a write-list union proven disjoint with `sort | uniq -d`
before anything started. Every slice touched exactly its declared files - checked
with `git status --short` in each worktree before merging, zero violations and
zero untracked residue.

**THE MOST IMPORTANT RESULT IS A REVERSAL, AND IT WENT THE OTHER WAY FROM LAST
SESSION'S.** The previous entry's proudest finding was a refutation that rescued
a false positive. This one is a refutation that removed a false negative, and it
landed against work this session had already merged.

A research pass reported that it had located a first-party Genshin-specific Legal
FAQ on HoYoLAB that the prior session had missed, and that a literal-word probe
of the COGNOSPHERE Terms of Service found no scraping clause. It returned
`GATE: CLEARED`. `docs/adr/ADR-008-fan-content-posture.md` was written on that
evidence and merged. An adversary dispatched with a licence-and-evidentiary-
weight lens returned `REFUTED`. The main thread then re-probed every checkable
claim against the primary artifacts itself, because agreement between agents is
not evidence and neither is disagreement. **The adversary was right on every
count:**

- **The Terms of Service DO carry an express scraping prohibition.** Section 7,
  clause c, applied to the COGNOSPHERE Services, conditioned on prior written
  permission, with no non-commercial carve-out. Measured directly:
  `curl` of `https://tot.hoyoverse.com/en-us/terms` returns 219297 bytes and
  `grep -o -i -E "scrap[a-z]*"` returns two hits of `scraped`, at byte offsets
  66250 and 156982. The summariser the research pass overturned had been right.
  **The main thread's first reading of WHY was itself wrong, and the correction
  is the better lesson.** It concluded the probe "cannot have run". A third
  agent re-probed with word boundaries and found the honest explanation:
  `\bscrape\b` returns 0, and so do `\bscraping\b`, `\bscraper\b`, `\brobot\b`,
  `\bspider\b`, `\bcrawl\b` and `data mining`. ONLY the past participle
  `\bscraped\b` hits. Every term on the original probe list genuinely returns
  nothing. The probe was defeated by INFLECTION, not fabricated. Verified
  independently by the main thread against the same 219297-byte fetch.
  A literal probe is only as good as its morphology: search the stem, not the
  lemma.
- **The FAQ's enumeration is open-ended.** Measured on the retrieved body, which
  lives in the `structured_content` field and not `content` - `content` is 5
  characters. "including but not limited to" appears 3 times, "any other" 4,
  "such as" 4, "current or future" once.
- **The probe searched for vocabulary the document never uses.** `tool`,
  `software`, `API`, `tracker`, `calculator`, `database` all score zero, and
  that was reported as reassurance. The document's own words are `program`, 6
  times, and `service`, 12 times. `website` was reported as appearing once; it
  appears 8 times.
- **The sentence the whole finding rested on answers a different question.** It
  is the answer to a question about using images, text or audiovisual materials
  of the game for re-creation or posting to a personal fansite. This project
  vendors none of those. A non-prohibition of X is not evidence about Y.
- **An admitted evidence hole was admitted for a false reason.** ADR-008 said no
  PDF renderer was available. `command -v pdftotext` returns
  `/mingw64/bin/pdftotext`, version 4.00.

ADR-008 was rewritten against the artifacts. Operator decision: publish on the
vendoring argument alone. The posture rests on what is verifiable about the
project rather than on a 2021 forum post - zero vendored assets, zero vendored
data, no contact with the game client, no HoYoverse endpoint called,
non-commercial - which was always the half doing the work. The Section 7(c)
clause and the HoYoverse to `enka.network` to this-repo data chain are recorded
as an open question the ADR does not resolve, rather than one it pretends is
cleared.

**The durable lesson: a probe returning a convenient NEGATIVE deserves exactly
the scrutiny a summary returning a convenient POSITIVE gets.** Last session's
lesson was that agreement between two agents is not evidence. This session's is
the single-agent version - a retrieval that confirms what you hoped is still a
retrieval you have to check. Both were settled the same way, by going to the
artifact instead of counting agents.

**PROCESS FAILURE, TWICE, recorded rather than left to be inferred.** Both
adversaries dispatched this session reported a FREEZE VIOLATION, and the second
one happened AFTER the first had been acknowledged.

The first: the main thread merged ADR-008 into the working tree while the licence
adversary was reading it, so `git status --porcelain` went from 1 line to 13 to
17 mid-pass. The second: while the quickstart adversary was running, the main
thread edited fourteen tracked files fixing the adjudicator's findings, and that
adversary listed all fourteen and noted two concurrent `pytest` processes that
were not its own.

`.claude/commands/orchestrated-run.md` phase 5 requires candidates to be FROZEN
before dispatch, and phase 6 inherits it. Both adversaries handled the violation
correctly - the first pinned its verdict to a worktree copy and named the mtime,
the second proved its own subject was byte-identical to `58c02b4` by sha256 and
cloned from the committed HEAD rather than the worktree. Both verdicts therefore
stood. That is the agents being careful, not the process being sound.

**The lesson is specific and it is about the orchestrator, not the agents.** A
read-only pass is not free to dispatch: it puts the tree under a lock the
orchestrator has to honour, and an orchestrator that keeps merging because "they
are only reading" has silently redefined what the verdict is about. The fix is
mechanical rather than a resolution to be careful - dispatch read-only passes
against a COMMITTED SHA and tell them to clone or `git archive` it, which is
exactly what the second adversary did unprompted and what made its verdict
survive.

**One root cause had three instances, and all three are fixed.** A guard that
tests PRESENCE when it means TRACKEDNESS. Git stores no empty directories and
knows nothing about ignored ones, so a filesystem walk sweeps content that is in
nobody's clone.

- `tests/test_docs_consistency.py` called `.exists()` on every cited path. That
  is how `docs-guards` went red on the CI runner while the same test was green
  locally. It now also asserts each cited path is in `git ls-files`. It caught a
  real unstaged-citation case within minutes of landing.
- `tests/test_ports.py` had a function NAMED `_tracked_python_files` that did
  `REPO_ROOT.rglob("*.py")` behind an ad-hoc denylist. **This one was genuinely
  RED in the main checkout** and was found by re-running the suites after the
  merge, which is the entire reason that phase exists. It would go red for any
  contributor who created a `.venv/`. The old denylist filtered `.pytest_cache`
  but never `.mypy_cache` or `.claude/`, both live blind spots.
- `tests/test_shell_contract.py` was the third, and it turned out CORRECTIVE
  rather than preventive. Its ad-hoc denylist did cover the one case someone
  remembered, `node_modules/`, named in `shell/`'s own second `.gitignore`. But
  six ROOT `.gitignore` rules also apply under `shell/` and it remembered none
  of them - `dist/`, `build/`, `.mypy_cache/`, `tmp/`, `_scratch/`, `.vscode/`.
  The dist directory under shell/ - deliberately not written as a live path
  here, because it is gitignored and absent from a clean checkout, and the very
  guard this entry describes would flag it as a dead pointer - is
  electron-builder's DEFAULT output location, and `shell/package.json` declares
  electron as a devDependency, so it is a path a contributor produces simply by
  running the build. A file staged there turned TWO
  existing assertions red - the ASCII sweep and the foreign-port sweep - on
  content in nobody's clone. Its floor-shaped assertion is what hid it: a floor
  cannot detect OVER-collection.

**The pattern across all three is worth stating once.** Each guard named its
intent correctly and implemented something weaker, and in every case the gap was
an ad-hoc denylist - a list of the ignore rules whoever wrote it happened to
remember. `git check-ignore` and `git ls-files` already know the real answer.
The permanent arms added this session check the swept list against
`git check-ignore`, which is a DIFFERENT ORACLE from the `git ls-files` that
produced it, so the two cannot fail in agreement.

**The compliance labels now tell the truth, and the true claim is the stronger
one.** `data/fixtures/seed_roster.json` and `seed_materials.json` opened with
`"_synthetic": true` on the line directly above a `"_note"` calling them
hand-authored. Synthetic means invented; a verified avatarId is not invented.
They now carry `_hand_authored`, `_vendored` and `_content` blocks.
`data/fixtures/README.md` is retitled and names which of its three files is which
kind - `enka_sample_profile.json` IS genuinely synthetic and keeps that label.
The builder deviated from its brief here and was right to: the literal
instruction it was given would have condemned that honest file, whose own note
reads "SYNTHETIC hand-authored payload". It implemented mutually-exclusive
structured flags instead and reported the conflict.

**A sharper instance of the ADR-006 sweep than the audit found.** The audit named
four public-facing files still giving the dissolved copyleft reason. All four are
fixed. But `docs/LICENSE_NOTES.md` carried it in its GENERAL RULE - "GPL and
other copyleft stays DO-NOT-VENDOR ... because vendoring it would relicense this
repo" - and that is the version a future contributor actually applies, not a
table row. It was flatly false for a GPL-3 tree. The audit had marked that file
as handled correctly because its header blockquote states the dissolution.

**`python -m mypy` is green, and the obvious fix was the wrong one.** It had been
red on `numpy/__init__.pyi:737`. The chain: `mypy.ini` names
`agents/pity_engine/`, which crawls the engine's own `tests/`, which imports
pytest, which imports `_pytest.python_api`, which imports numpy. `core/`,
`engines/` and `ingest/` each check clean alone, which is how the chain was
isolated. The operator's instruction was to drop the stray numpy. **numpy is not
a stray:** `pip show numpy` reports it required by ImageHash, opencv-python,
PyWavelets and scipy, so uninstalling it would have broken software outside this
repo on a box seven projects share. That was reported back rather than executed,
and the narrower fix - excluding the engine test directory, which is what
`[mypy-tests.*]` already intended and simply never matched - was taken instead.

**Nothing in this tree had ever guarded the account-name leak, in either
direction.** `.claude/commands/done.md` carried an absolute
`C:/Users/<account>/` path. `tests/test_docs_consistency.py` only inspects
backticked tokens beginning with one of its declared tree roots, and an absolute
Windows path begins with none of them, so it was never even looked at.
`tests/test_machine_identity.py` now sweeps every tracked file across Windows,
POSIX and MSYS/WSL/Cygwin mount spellings, with a by-name allowlist carrying a
stated reason per entry. It builds its own offending literals at run time from
segment lists so the test file cannot become the violation it tests for - the
same trap that banned-glyph literals hit here before.

**A defect this session introduced, caught by this session's own guard.** The
main thread spliced a block into `ROADMAP.md` with `pathlib.Path.write_text`,
which opens in TEXT mode on Windows and silently rewrote all 252 lines as CRLF.
`.gitattributes` declares `eol=lf`, so git normalises on staging and NO DIFF
WOULD EVER HAVE SHOWN IT. Only `tests/test_line_endings.py`, which reads bytes,
caught it. Repair is `raw.replace(b"\r\n", b"\n")` then `write_bytes`; the
Write and Edit tools preserve LF and are the right instrument. Same shape as the
recorded backslash-mangling trap: an intermediary silently rewrites the payload.

**Also corrected before shipping, in a public-facing document.** ADR-008 claimed
a sweep of every HTTP URL in the runtime tree "returns exactly one". Re-run by
the main thread, a naive grep returns FOUR hosts. The substance holds - only
`https://enka.network` is a fetch the application makes; `registry.npmjs.org`
and a `github.com/sponsors` link live in `shell/package-lock.json` as
install-time package-manager metadata, and `schemas.microsoft.com` is an XML
namespace identifier in `ops/ResinCompute-Supervisor.xml` that is never
dereferenced. The wording now says so, because a reader WILL re-run that sweep
and must not conclude the ADR is wrong. That is the same failure mode that cost
this ADR its first draft.

**Measured 2026-09-06 at the merge seam, after all nine slices, by the main
thread rather than reported by a builder.** These are a historical reading, not
a claim about now, and no count is written into any guarded document.

```
pytest tests                    762 passed, 1 skipped
pytest agents/pity_engine        76 passed
ruff check .                    All checks passed
mypy                            Success: no issues found in 23 source files
shell: node --test               52 pass, 0 fail
scripts/qa_companion.py          17 passed, 0 failed, 1 skipped
headless --once --dry-run       exit 0
```

Guard arms added: `tests/test_licence_posture.py` 21 to 33,
`tests/test_docs_consistency.py` 16 to 23, `tests/test_shell_contract.py` 20 to
23, plus `tests/test_machine_identity.py` (33 arms) and
`tests/test_readme_tree.py` (9 arms) as new files.

**THE VERIFICATION PASSES CHANGED THE WORK, WHICH IS THE POINT OF HAVING THEM.**
Three independent passes ran against the committed tree, and two of them altered
what shipped.

- **The verifier** returned CONFIRMED WITH CORRECTIONS. Every count re-derived
  exactly, including the "was" baselines, which it measured by exporting
  `a7834c8` with `git archive` into a scratch directory rather than mutating the
  checkout. It found three false claims in shipped prose.
- **The adjudicator** returned ACCEPT WITH RESERVATIONS and made the sharpest
  observation of the session: this commit was convened because a licence gate
  refused publication on documents making claims that were false about their own
  contents, and it opened six more of exactly that class INSIDE the documents
  written to close them. ADR-009 asserted that a tree-wide grep for the SPDX
  identifier returned zero, in a sentence that contained the identifier, so the
  grep returned that line. All six are fixed.
- **The quickstart adversary** returned REFUTED, having actually run the README
  in three clones, one at a space-containing path, plus an isolated venv on the
  pinned toolchain. It verified the hooks end to end in both directions: a banned
  glyph blocked with HEAD unchanged in a clone WITH hooks installed, and the same
  glyph COMMITTED in a clone without them, which is the measured proof that the
  README's "do this first" is load-bearing rather than advice.

**The single most valuable finding was a blocker the orchestrator introduced.**
Replacing filesystem walks with `git ls-files` was correct and it took the number
of test files depending on the git oracle from 3 to 8 - measured by reading both
commits - without anything testing what happens when that oracle is absent.
`git archive 58c02b4 | tar -x` into a directory with no `.git`, then
`python -m pytest tests`, ABORTS AT COLLECTION with exit 2 and NOT ONE TEST RUNS,
because `tests/test_shell_contract.py` calls git inside a `parametrize` argument
at import time. With that file skipped, 48 more fail. That is what a person gets
from GitHub's "Download ZIP", from an sdist, or from any vendored copy - and the
commit whose entire purpose was to make this repository publishable shipped it.
The fix makes trackedness-dependent guards SKIP loudly when git is unusable,
never fall back to a disk walk, with a guard that fails if the skip path is taken
inside a real checkout.

**THE BLOCKER IS FIXED, AND FIXING IT EXPOSED A SECOND ONE.**
`tests/conftest.py` now holds three shared helpers. `git_unusable_reason()` asks
`git rev-parse --git-dir` rather than looking for a `.git` entry on disk, because
the disk check is wrong three ways this project actually uses - a linked worktree
has a `.git` FILE, a submodule's lives under the superproject, and `GIT_DIR` can
move it. `require_git_repository()` skips one test at run time;
`skip_module_without_git()` skips a whole module at import time, which is needed
for exactly one file - `tests/test_shell_contract.py` calls git inside a
`parametrize` argument, so a run-time skip arrives too late and the exception
becomes a collection ERROR that aborts everything. The guards SKIP rather than
fail, and they never fall back to a disk walk, which would silently answer a
different question while reporting green. Every skip names the missing repository.

The dangerous failure mode is guarded: if the helper ever reported git unusable
inside a real checkout, every git-dependent guard would evaporate at once and the
suite would still be green. `tests/test_commit_trailers.py` cross-checks it
against an INDEPENDENT signal - a `.git` entry on disk, deliberately not how
detection works - and fails if the skip path is taken in a real repository.

**The second blocker was masked by the first.** With collection fixed, one test
still failed in the archive, and only at a path containing NO SPACE.
`tests/test_hook_interpreter.py` ran the pre-push hook as `_run_sh(f'"{hook}"')`,
embedding a quoted Windows-looking path inside an `sh -c` string. MSYS argv
conversion mangles that and the closing quote is lost - `sh: -c: line 1:
unexpected EOF while looking for matching quote`. A space in the path SUPPRESSES
the conversion, which is the only reason it passed at `C:\Resin Compute`. It
would have failed for anyone cloning to `C:\dev\ResinCompute`, which is the
normal case. Fixed by passing the hook as an argv element and running
`exec "$0"`, so sh never re-parses it. Same root cause as the recorded
`taskkill //F //PID` rule.

Measured after both fixes, by the main thread:

```
real checkout                         763 passed, 1 skipped   exit 0
source archive, no .git, no spaces    692 passed, 50 skipped  exit 0
                        was:          0 tests ran             exit 2
```

**Prose defects the adversary found that were real and are fixed:**
`requirements.txt` stated the PityEngine runs on `:8870` in the present tense -
the pre-ADR-004 port inside a sibling project's reserved block, in the one file
the quickstart tells a reader to open, and the ONLY non-historical mention of
that number in the tree. The README ran a foreground server and a client call in
a single fenced block, so the second line could never execute, and repeated the
shape four more times across the daemon, the supervisor, the restart trigger and
the health read. And the README's stated REASON for its PowerShell convention was
wrong in a way that mattered: `curl -s <url>` does not fail with "no such
parameter", it BINDS `-s` to `-SessionVariable`, swallows the URL, and then
prompts for the missing `Uri` - so the console appears to hang. The advice was
right and the mechanism given for it was wrong, which is worse than saying
nothing, because it teaches a reader to expect the wrong symptom.

**Operator decisions taken this session,** so they are not re-litigated: the
repository keeps the name `Resin-Compute` and gets "Resin Compute & Pity Engine"
as its DESCRIPTION and README H1 rather than a rename, leaving the two-tier
convention in `CLAUDE.md` intact; commit identity ships as-is with no second
history rewrite, considered and declined; publication rests on the vendoring
argument alone; and the three unread PDFs are recorded as an open hole rather
than closed this session.

## 2026-09-06 - The public-repo audit, and the finding that refuted itself

An audit session, not a fix session. Every gate was green at commit `57f8894`
before a line was touched, so nothing below is a broken build - each item is a
defect a stranger would meet on a repository that is still PRIVATE. The findings
landed in `ROADMAP.md`; the fixes are next session's work, on operator
instruction. No builder was dispatched and no slice was merged, and that
departure from the default orchestrated shape is recorded here rather than left
to be inferred.

**THE MOST USEFUL RESULT WAS A REFUTATION OF THIS SESSION'S OWN FINDING.** UID
`618285856` appears in `README.md` and three test modules while every other UID
in the tree is patently fake - `000000000`, `900000000`, `111111111`. Both the
audit and the planner independently flagged it as a probable real account, on
that reasoning, and both were WRONG. It is Enka.Network's own published example
UID, verified against the primary artifact rather than against either agent's
reasoning: it appears twice in
`https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/api.md`. Two
agents agreeing was not evidence - they shared the premise that an
unlabelled-looking UID is an unlabelled UID, and testing that shared premise
against upstream is what settled it. The residual work is one line at the use
site so the next reader does not spend the same hour reaching the same wrong
conclusion. Verification pointer: the URL above, and `README.md` line 195.

**A single-line grep missed a wrapped sentence, measured here.** The sweep for
the dissolved copyleft rationale - "vendoring either would relicense this repo",
which stopped being true when ADR-006 made this tree GPL-3-or-later - returned
eight files and did not return `README.md`. The phrase wraps across
`README.md:317-318`, so `relicense th` matches nothing on either line. A
multiline-aware re-grep found it. Any sweep that greps for prose must assume
wrapping; a naive one scores clean by not looking.

**The licence gate REFUSED publication, and the refusal is narrow.** An
independent read-plus-web pass cleared the substance: zero binary assets
anywhere in the tree - no art, icons, audio or fonts, confirmed by glob rather
than by the NOTICE's assertion about itself - zero runtime dependencies, three
dev pins none of which is a data library, zero imports of any forbidden
upstream, zero bulk data. Names and published drop rates are facts and are
excluded from copyright. It refused on four text defects, all recorded in
`ROADMAP.md`. The sharpest is that two fixtures are labelled false in a way that
matters more once public: `seed_roster.json` and `seed_materials.json` carry
`"_synthetic": true` on the line directly above a `"_note"` reading
"Hand-authored seed identity table", and `data/fixtures/README.md` is titled
"SYNTHETIC test data only" while its body says "hand-authored by this
repository". Hand-authored is what ADR-002 requires and what `NOTICE` already
says correctly; synthetic means invented, and real verified avatarIds are not
invented. The true claim is also the stronger one, which is why this is worth
fixing rather than arguing.

**Per-file GPL headers: the deferral was checked and holds.** GPL-3's "How to
Apply These Terms" sits AFTER `END OF TERMS AND CONDITIONS` in the shipped
`LICENSE`, so it is an advisory appendix rather than a condition of the grant,
and section 5(b) binds "the work" and binds a modifier rather than the original
author. So the project is below best practice, NOT non-compliant, and ADR-006's
Consequences section is correct as written. The decision still needs recording
as a decision rather than a silence - 78 tracked `.py` and 10 tracked `.js`
carry zero SPDX identifiers, measured this session.

**Two ROADMAP claims were measured false and removed.** "Until that happens the
CI workflows are inert" - `git rev-parse --show-toplevel` returns the tree root,
`git remote -v` returns the standalone remote, `ci.yml` carries no
`working-directory`, and `gh run list` shows both workflows green against this
tree. And `docs/LEDGER.md` was listed under open work as a file to create, while
being the file that listing appears in.

**Recorded for the operator, not actionable by an agent:** two commits on `main`
carry an agent identity as author AND committer. This is not the trailer rule -
the trailers were stripped and are guarded by `tests/test_commit_trailers.py`,
which reads subject and body only and never `%an`, `%ae`, `%cn` or `%ce`. That
is the same shape as the already-recorded defect where the trailer policy was
enforced on one of its two forms. A second history rewrite is the operator's
call; the guard extension cannot be written before it, because it would fail at
HEAD.

Counts observed 2026-09-06 at `57f8894`, as a reading and not a claim about now:
licence QA exit 0; docs QA exit 0; `scripts/qa_companion.py` 17 passed, 0
failed, 1 skipped; ruff clean; `pytest tests` 697 passed, 1 skipped;
`pytest agents/pity_engine` 76 passed; `shell` node --test 52 passed; headless
smoke exit 0.

## 2026-09-06 - The session shape, the ritual, and three silent gates

The default session here is now orchestrated, multi-agent, self-adjudicating and
self-adversarial. ADR-007 argues it, CLAUDE.md states it as a rule, and
`.claude/agents/` makes it executable: seven roles whose read-only halves omit
Edit and Write from their tools list, so read-only is a mechanism rather than a
promise. `tests/test_agent_roster.py` pins the roster, the tool scoping and the
verdict vocabularies the orchestrator string-matches.

`/done` existed in every sibling project and not here. It does now, in
`.claude/commands/done.md`, alongside `orchestrated-run.md` and `ui-audit.md`.
The inline fenced block is the hand-off; the Desktop file is its BACKUP, written
by `tools/publish_next_session.py`, which reads the block out of
`NEXT_SESSION_PROMPT.md` and never accepts prompt text as an argument - so the
printed block, the tracked file and the Desktop copy cannot disagree. Operator
instruction: nothing follows the fenced block, because the operator selects it by
hand and trailing prose is text to select around.

THREE GATES WERE SILENTLY NOT RUNNING, and all three had looked healthy.

- **The pre-push gate had never run on this machine.** It selected `python3`,
  which resolves here to the Microsoft Store shim and redirects to a DIFFERENT
  interpreter carrying neither ruff nor pytest. `command -v python3` SUCCEEDS, so
  the fallback guarded by existence never fired. Every push printed two warnings
  and gated nothing. The same snippet was found in `pre-commit` and in
  `commit-msg` - three copies, one root cause. `scripts/hook_python.sh` is now
  the single shared selector and it probes CAPABILITY, not existence.
  Verification pointer: `tests/test_hook_interpreter.py`, whose non-vacuity arm
  runs the OLD snippet against a synthetic PATH and asserts it picks the useless
  interpreter - without that arm the guard would pass by luck on Linux CI, where
  `python3` IS the interpreter with the dev deps.
- **The trailer policy was enforced on one of its two forms.** `commit-msg`
  stripped `Co-Authored-By: Claude` and passed `Claude-Session:` straight
  through. A history sweep found BOTH forms on two commits - the root commit and
  one made later from the same hookless clone. Enforcement also lived only inside
  a hook, and `core.hooksPath` is local config that is not cloned, so the policy
  did not exist at all in a fresh clone. Verification pointer:
  `tests/test_commit_trailers.py`, which reads history from OUTSIDE the hook and
  skips explicitly on a shallow clone rather than sweeping one commit and
  reporting clean.
- **The declared line endings were half enforced.** `.gitattributes` claims
  `eol=lf` pins the bytes in the repo AND in the working tree. Only the repo half
  was true: 28 tracked files carried CRLF on disk while every diff looked clean,
  because the clean filter normalises into the index. Committed blobs were always
  correct, confirmed by `git hash-object --path` rather than assumed. Verification
  pointer: `tests/test_line_endings.py`.

History was REWRITTEN to remove the two trailer forms, on operator instruction,
and force-pushed. Not undertaken lightly: the command was proven on a throwaway
clone first, and both there and on the real tree the commit count was unchanged
and every commit's TREE HASH was identical, so only messages moved.

`.gitignore` stopped ignoring the command and agent docs. `.claude/` was a
blanket ignore, so the ritual and the roster would have existed only on this
machine - absent from a fresh clone, invisible to `docs-guards.yml`, unreviewable
in a diff. The exclusions are on directory CONTENTS, because a negation cannot
re-include a file whose parent directory is excluded.

MEASURED THIS SESSION, and worth keeping: the four slices that built the roster,
ADR-007 and the command docs were dispatched into the SHARED tree with no
worktree isolation - while writing the ADR that says to isolate. No work was lost
and no write-list was violated. It still cost accuracy in three of five agents:
one reported a sibling's tests RED when an independent probe showed them green,
one measured a suite polluted by files it did not own, and one watched HEAD move
underneath it. Every one of those is a FALSE report produced by the tree rather
than by the agent, and an orchestrator that believes one ships on a fiction.
`orchestrated-run.md` now names the mechanism, `isolation: "worktree"`, not just
the principle.

Counts observed 2026-09-06 after the rewrite, as a reading and not a claim about
now: ruff clean; `pytest tests` 697 passed, 1 skipped; `pytest agents/pity_engine`
76 passed; `shell` node --test 52 passed; `scripts/qa_companion.py` 17 passed,
0 failed, 1 skipped; headless smoke exit 0. `python -m mypy` remains red for the
known environmental reason - it follows `_pytest` into a numpy stub using PEP 695
syntax invalid under the pinned `python_version = 3.11` - and is advisory in CI.

## 2026-09-06 - Licence decided, and companion QA made runnable

ADR-006: GPL-3.0-or-later. The sibling house pattern was the trap rather than the
default - MIT and Apache-2.0 both permit closing the source and selling it, the
exact outcome to prevent. CC BY-SA was asked about and rejected on facts: it
permits commercial use, and Creative Commons advise against CC for software.

The licence text was VERIFIED, not pasted from memory: cross-checked against a
second independent copy, confirmed 7-bit ASCII, and its sha256 matches the
canonical published hash. That hash is pinned in a test.

ADR-006 amends ADR-002 in exactly one respect: the copyleft objection to
vendoring enka-py and ambr-py dissolves. The objection that mattered stands -
those wrap HoYoverse data and no outbound licence of ours touches that.

`scripts/qa_companion.py` answers the question the suites cannot: is the
companion working right now, on this machine, as installed. It binds an ephemeral
port so it never contends with a running dashboard.

**It found a false negative in its own first run**, which is the useful kind. It
reported the desktop shortcut absent while the shortcut existed - the operator had
renamed it to match their convention. Two real consequences:

- `make_shortcut.py` would have created a SECOND shortcut beside the renamed
  one. That is exactly what Sibling-A's refuse-unless-force default was
  guarding against, and its author said so in as many words. Fixed: the
  installer now scans for a shortcut with the same TARGET under any name.
  Idempotence converges on a state - a working shortcut exists - not on one
  filename.
- The QA now matches by target too, reusing the installer's own comparison so the
  two cannot disagree.

Also fixed: a test wrote a Windows path without a raw string, so one backslash
escape became a literal control character and another was an invalid escape. The
test still PASSED, because it only asserted inequality, so the defect was
invisible until a SyntaxWarning surfaced it.

That bug then bit a second time, writing THIS entry. The sentence above was
composed in a non-raw string and put a real control character into this file.
The ASCII guard in tests/test_docs_consistency.py did not catch it, because it
rejected bytes above 0x7E and said nothing about control bytes below 0x09. Both
are now rejected. A guard that checks one end of a range and not the other is a
guard with a documented blind spot.

And `test_a_stopped_server_releases_its_port_immediately` was flaky by
construction - dropping SO_REUSEADDR made the rebind strict, so the OS handing
that port to another process failed a test about TIME_WAIT. Now retried, with the
retry justified rather than papered over: a real regression fails every attempt.

## 2026-09-06 - Project-goals QA, mechanised

`tests/test_docs_consistency.py`. The docs must agree with the tree: every
backticked path in a governing document resolves, every ADR is indexed in both
directions, ADR numbers are unique and contiguous, and a ROADMAP line marked DONE
may not name an absent path.

**Written because a real pointer had already rotted.** CLAUDE.md instructed every
session to read an architecture document under docs/ that has never existed. Nothing checked it, so the instruction survived indefinitely.

Found four more on its first run, all real:

- **ADR-005 existed but was never added to the ADR index.** Missed when it landed.
- `docs/LEDGER.md` was cited by ROADMAP and did not exist. This file is that fix.
- ADR-004 cited `docs/LEDGER.md` in a way that read as ours when it meant
  Sibling-D's. Reworded.
- The goal spec wrote a dotted symbol as though it were a path. Reworded, and the
  checker now distinguishes `module.function` from a file by suffix.

`ops/runtime/health.json` is exempt BY NAME, with a stated reason, because the
supervisor creates it at run time. A further test asserts the exemption is still
referenced somewhere, so a dead exemption cannot linger.

## 2026-09-06 - Account state persisted; the dashboard cold-starts

`core/state_io.py`, the `persist_state` job, and a loader in `surface/`.
`reconcile_state` rebuilt the account every pass and the process then exited, so
the dashboard had nothing to render.

**Live-state-first is preserved structurally, not by promise.** The snapshot is
write-only from the headless lane; `tests/test_headless_persist_state.py` parses
`headless/jobs.py` and asserts the absence of a read, because a cache that
quietly starts being read looks like a hit rather than like a broken rule.

The surface renders the reading's AGE. A cached roster shown without one is
indistinguishable from a live query, and the confusion is silent because a stale
roster looks plausible. `None` is not zero: a never-synced account reads "no
reading yet".

**Defect found by observation, not review.** `ThreadingHTTPServer` sets
`allow_reuse_address`; on POSIX that only sidesteps TIME_WAIT, but on **Windows**
it lets a separate process bind a port another process is already listening on.
Measured: two surfaces held 8791 at once, `netstat` showed both, and the OLDER
one answered every request - so a freshly started surface serving new code was
silently ignored while looking healthy. It also made `main`'s documented exit
code 2 unreachable on Windows, which is the code the Electron shell renders its
refusal from; the second process bound fine and blocked forever. Fixed with
`SO_EXCLUSIVEADDRUSE`, with a test pinning that an immediate restart still works.

**Second defect, in the tooling rather than the code.** `taskkill /F /PID` does
not work under Git Bash: MSYS path conversion rewrites the lone `/F` into `F:/`.
It fails SILENTLY when redirected, which is how the double bind went unnoticed.
CLAUDE.md's own hard rule now carries the caveat that it must be written
`taskkill //F //PID`.

## 2026-09-06 - Seed-team roadmap recorded as a stamped goal spec

`docs/GOAL_SPEC_SEED_TEAM.md`. An operator-supplied roadmap generated by a web
assistant, reviewed against this tree's verified ground truth, with every claim
carrying exactly one stamp: VERIFIED with a citation, REFUTED, UNVERIFIED,
TIME-SENSITIVE or NOT MODELLED. The stamp is about provenance, not plausibility.

Findings: the roadmap **omits the domain rotation entirely**, which
`core/domains.py` encodes as a three-day cycle, so following it can spend resin
on a day the domain is not dropping what is needed. "Spend the hoard the second
the banner returns" is not a plan when the pull count is computable. The Beginner
Wish banner is NOT MODELLED - `BannerKind` has no member for it.

Its cost figures are UNVERIFIED and deliberately kept out of `data/`.
`tests/test_goal_spec.py` sweeps for them mechanically; proven non-vacuous by
mutation, and reverted clean.

Baseline recorded: **the account has not been played.** The dashboard's empty
state is therefore correct rather than degraded.

## 2026-09-06 - Electron companion, system tray, idempotent shortcut

`shell/`, `scripts/make_shortcut.py`, ADR-005. Reverses ROADMAP's "dashboard is
out of scope" for a stated reason - the operator wants the surface BEFORE further
feature work, so each feature becomes visible as it lands. ADR-001 is not
reopened: its subject was the language of the compute tree, and the surface is
Python too.

`shell/main.js` is WIRING ONLY, inherited from Sibling-A. It imports Electron
so nothing can load it in a test, so nothing that decides anything lives there.

- The tray icon ships as base64 text; the tree carries no binary asset. Its
  colour was SEARCHED, not picked: a notification area is near-black under one
  theme and near-white under the other, so 2078c8 was chosen for clearing 3:1
  against both (4.58:1 each way). The first candidate measured 2.94:1 against
  white and the generator's own assertion rejected it.
- An invisible drag strip spans the top of the page. The window is frameless, so
  without it there is nothing to grab.
- `state.js` refuses the string `"false"` rather than coercing it; it is truthy,
  and a tray checkbox reading it as checked would show the opposite of the truth.
- `geometry.js` recovers a window remembered on an unplugged monitor rather than
  restoring it offscreen, where it has focus and is invisible.
- `make_shortcut.py` is IDEMPOTENT, diverging from Sibling-A's
  refuse-unless-force, which is not. Proven: run 2 created, runs 3 and 4
  reported nothing to do, exit 0.

Measured rather than assumed: `npm install` leaves NO `electron.exe` behind - the
package declares no postinstall and fetches lazily on the first require.

## 2026-09-06 - Local dashboard surface on 8791

`surface/`. Six panels. Panels DECLARE THEIR OWN READINESS - ready, partial or
not wired - and a panel that is not ready renders what it is waiting on instead
of a plausible zero. Enforced in `Panel.__post_init__`, not just in the builders,
so a panel added later cannot ship a silent gap.

This applies the zero-is-not-unknown distinction `engines/objectives.py` already
draws to the UI: rendering "0 resin required" off an empty cost table is not a
neutral placeholder, it is a confident wrong answer.

Escaping is load bearing: `MappedCharacter.display_name` is a nickname another
player typed, carried through enka.network onto a page that runs inside Electron.
Both the element case and the attribute break-out case are pinned.

## 2026-09-06 - Port block 8790-8809 reserved; PityEngine migrated off 8870

ADR-004, `core/ports.py`, `tests/test_ports.py`. The scaffold put PityEngine on
8870 by mirroring Sibling-F's 8860 and adding ten. **8870 is inside Sibling-F's
reserved block 8860-8879.** Nothing was listening, so nothing broke and nothing
warned.

Verified against sibling SOURCE, not a live scan - the rule Sibling-A learned
the hard way when it allocated a band by probing while the owning project's GUI
happened to be closed. The only registry hit inside the new block was
Sibling-C's `range(8770, 8790)`, whose end is exclusive.

Three sites carried the literal 8870 independently; all now resolve to
`core.ports.ENGINE`. The tests pin each constant against the module that really
binds rather than re-asserting the literal, and a negative guard rejects any
sibling port literal in tracked Python source.

Reservation shared to all five siblings through the established
`moon_sync_inbox/` channel, without editing any sibling's source.

## 2026-09-06 - Initial scaffold

Recorded in `README.md` and `docs/SPEC_SCAFFOLD.md`. ADR-001 through ADR-003.

## 2026-09-07 - the watcher fires, the commit gate is proven, and the inbox gets read properly

Four operator instructions arrived mid-session and each is recorded in
`CLAUDE.md` rather than only obeyed: responses under 500 tokens, CAVEMAN ULTRA
as the chat dialect, every API key in a machine environment variable, and the
cross-repo inbox AND ITS SUBDIRECTORIES reviewed, ingested, implemented and
answered.

**The watcher was correct and connected to nothing.** `scripts/watch_inbox.py`
shipped on 2026-09-06 with eleven arms and every property the siblings asked
about. There was no `.claude/settings.json` in this tree at all, so it ran only
when a human typed it - which is why the hand-off had to instruct the next
session to run it by hand. A declared hook is not a firing hook; the quieter
predecessor is that AN UNWIRED SCRIPT IS NOT A WATCHER. Fixed in
`.claude/settings.json`, guarded by `tests/test_session_hooks.py`, which
EXECUTES each declared command rather than resolving its target.
`.gitignore` gained `!.claude/settings.json`, because the blanket `.claude/*`
rule would have left the wiring on one box - the exact failure its own comment
says the command docs were tracked to avoid.

**The commit gate is proven on a real runner.** `tests/test_hook_gate.py` and a
CI step; observed on `ubuntu-latest` as `12 passed in 0.75s` after
`armed: .githooks/commit-msg .githooks/pre-commit .githooks/pre-push (all mode
100755)`. Ran, not skipped.

**An adversary then REFUTED four claims made about that work, and the gate
itself survived.** Three mutation directions each killed the right arms, so the
gate discriminates. What did not survive was the prose: `RSC_REQUIRE_HOOK_GATE`
does not convert an unconfigured clone - the fixture arms its own throwaway repo
and an unconfigured clone passes 12 of 12. It converts an UNMEASURABLE MACHINE.
The dependency scan matched `$ROOT/` but not `${ROOT}/`. The positive control
went red when the pinned interpreter could not import ruff, blaming the gate for
a contributor's venv. The docstring claimed a `GIT_*` scrub wider than it
performs, citing a mechanism `git 2.53` does not exhibit. All four corrected.

**A sibling's claim about this tree was refuted by measurement.** Sibling-E
reported RSC carrying the old leaking `slots.py` at `1c4f8af4`. Measured on
this disk and in the HEAD blob: `629c3d51`, the new one, with no copy of the
old anywhere. The explanation is timing, and it generalises: **note filename
timestamps are FICTIONAL and drift per sender by up to six hours.** Sibling-E's
note labelled `0455` was written at 22:40:52; the commit landing the new bytes
was authored at 22:49:50. Right when written, stale when filed, and unreadable
as such from the name. Sorting by filename inverts real order.

**The hand-off write gate was the weaker of two, and Sibling-E was right.** It
refused non-ASCII and truncation and passed an inline API key and an absolute
path naming the operator's account straight through to the Desktop - measured,
not theorised. That is the one write that leaves the toolchain, and
`NEXT_SESSION_PROMPT.md` is tracked in a public repo.
`tools/publish_next_session.py` now refuses both, and the refusal never echoes
what it caught: a gate that quoted the key would publish it in the act of
refusing to.

Three collisions surfaced landing that, each fixed at its SOURCE rather than
allowlisted, because the detector and the detected share a shape by
construction. `ACCOUNT_PATH` is assembled from a named segment; an allowlist
entry spelled as a chunk of regex is unreadable and goes unstable the moment the
line is edited. The fixtures use an obviously invented account - one that
planted the true name would be the leak it tests for.

**The 2026-09-06 session read the notes and skipped the directory beside
them.** `moon_sync_inbox/from-<sibling>-verbatim/` held 49 real files while the
notes only described them. A full triage put 2 in ingested, 17 in
have-an-equivalent, 25 in not-applicable and 5 in applicable-and-not-done, and
corrected two entries this session had provisionally mis-bucketed: this tree's
CI already does both jobs that Sibling-C's `md_guard_selector.py` and ASCII
sweep do, and does them from `git ls-files` rather than a frozen baseline.

**A verbatim file can be STALER than the prose describing it.** Sibling-C's
end-to-end hook-gate test arrived without the require-env flag Sibling-C's own
later note calls load-bearing, and gates on `shutil.which("git")` - existence,
not capability, the same defect class as `command -v python3` succeeding on a
Store alias. Sibling-E independently hit both. Diff the ASSERTIONS, never the
filenames.

Thirteen items were open against this repo, eight of them direct unanswered
questions. All answered in one note broadcast to all five per charter section
0(a), and `moon_sync_inbox/from-RSC-verbatim/` now reciprocates seven files
that Sibling-C had asked for three times.

Merged files and their guards: `.claude/settings.json` and `tools/caveman_default.py`
(`tests/test_session_hooks.py`); `tests/test_hook_gate.py` and the `ci.yml` step
(`tests/test_ci_workflow_complement.py`); `tools/publish_next_session.py`
(`tests/test_publish_next_session.py`); the credential sweep
(`tests/test_no_secret_literals.py`).
