#!/usr/bin/env python
"""Report which `moon_sync_inbox/` notes and drops this repo has not read yet.

WHY A SCRIPT AND NOT A LIVE WATCHER. A session-scoped watcher dies with its
session. `moon_sync_inbox/` is gitignored on purpose - a note is correspondence,
not source - so a cold session inherits no record of what it already answered,
and an overnight note looks exactly like one dealt with hours ago. The failure
that costs real time is not a missed note; it is a note answered TWICE, or a
sibling's question left sitting while every agent assumes another took it.
Sibling-C's charter states the rule: silence is not agreement.

So the durable half is a WATERMARK on disk, and this script is how a session
reads and advances it.

  python scripts/watch_inbox.py                    # what is new since the mark
  python scripts/watch_inbox.py --all              # everything, new or not
  python scripts/watch_inbox.py --mark             # record the current set read
  python scripts/watch_inbox.py --quiet-when-empty # for a per-prompt hook

READING IS NOT ACKNOWLEDGING. Listing never advances the watermark; `--mark` is
a separate, deliberate act, because "I saw it scroll past" and "I answered it"
are different states and only the second one is safe to forget. That separation
is also what stops a subagent's session start from marking the operator's queue
as read.

WHAT IS AN ENTRY, AND WHY THE KEY IS A PAIR
===========================================

Every top-level `.md` file is a NOTE and every top-level directory is a DROP,
and both are first-class entries. The watermark keys each one on the PAIR
(key, digest) rather than on its name:

  note   key `<filename>`      digest sha256 of the file's bytes
  drop   key `<dirname>/`      digest of a manifest computed over WHAT IS ON DISK

THIS FIXED FOUR MEASURED HOLES. All five repos on this cross-repo channel
independently built the same watcher and each printed a confident "nothing new"
over a real payload. Measured in a fixture inbox, 2026-09-07:

  PASS  a brand new note is unread
  PASS  marking clears it
  FAIL  a note corrected IN PLACE, same filename, does not resurface
  FAIL  a 2-file subdirectory drop does not surface at all
  FAIL  an edited subdirectory payload does not surface
  FAIL  a file swapped inside a drop, count equal, does not surface

The root cause was two lines. The walker globbed `*.md` at the top level only,
and a DIRECTORY has no `.md` suffix, so `from-RC-verbatim/` - 48 real files:
hooks, guards, tools, tests - was invisible while the notes beside it merely
described them. And the watermark keyed on the filename alone, so a note edited
under a CORRECTION heading read as already answered.

THE DROP MANIFEST, and it is computed here rather than read from the sender:

  one line per contained file: the drop-relative POSIX path, a NUL byte, then
  that file's sha256; sorted; joined with newlines; hashed once.

The relative path inside each line is what makes two files SWAPPING CONTENTS
move the digest - the multiset of hashes is unchanged but the pairing is not.
An unreadable file contributes its exception CLASS in place of a hash, so it
moves the digest rather than vanishing from the manifest; a file that silently
drops out is a payload reported as unchanged while it is not.

TWO OTHER KEY SHAPES WERE PROPOSED ACROSS THE FLEET AND BOTH ARE REFUTED. Do
not re-derive them:

  FILE COUNT is refuted. A sender who REPLACES a file leaves the count equal,
  so the drop reads as already acknowledged. `test_two_files_swapping_contents_
  inside_a_drop_re_surfaces_it` pins it, and asserts the count did NOT move so
  the arm cannot pass under a count-keyed watcher.

  A DIGEST OF THE SENDER'S `MANIFEST.sha256` is refuted. Sibling-C
  measured a payload edited without regenerating its manifest: same manifest,
  completely different contents, same key, silently unread. Keying on a
  sender's manifest means trusting the sender remembered to rebuild it, which
  is precisely the assumption a watcher exists to remove. It is SHIPPED as
  human context when present and is never the key.

AN EMPTY DROP IS STILL REPORTED. A drop is an entry because of its NAME, never
because it has content to hash. That is the fleet's standing one-line test: put
an empty directory in the inbox and see whether the next report mentions it.

A RENAME STILL RESURFACES, and that is the accepted cost, unchanged.
Sibling-C measured it 2026-09-07: Sibling-A re-dated four notes and every
seen-name watcher on the box reported four unread notes already answered. A
false "new mail" costs one glance; a missed correction costs whatever the
correction was for.

BACKWARD COMPATIBILITY WITH THE SHIPPED NAME-ONLY WATERMARK
===========================================================

The watermark that shipped held `{"seen": [<name string>, ...]}` - names only,
80-odd of them on this machine. Discarding that on a version bump would dump
the entire inbox back on the operator as unread, which is worse than the bug it
fixes, so a legacy entry GRANDFATHERS its note: a name in the old list counts
as read whatever the file now hashes to, until the next `--mark` rewrites the
state in the keyed shape.

A legacy watermark never held a DIRECTORY, because the old walker could not see
one, so every drop surfaces on the first run after this change. That is the fix
arriving, not a regression.

The reader dispatches on the TYPE of `seen` - a list is legacy, an object is
current - rather than on the `version` field. A version integer is a claim a
writer makes about a payload; the shape is the payload. `version` is written
for a human reading the file.

DEGRADES TOWARD RE-REPORTING. A missing inbox is normal in a fresh clone and is
reported as a plain line, not a traceback. A corrupt watermark is treated as if
nothing had been read, which re-reports notes rather than dropping them: a
duplicate read costs a minute, a dropped note costs a sibling waiting on an
answer nobody knows they owe. No raw exception string ever reaches the report.

The watermark lives under `ops/runtime/`, which is gitignored, and is written
through `core/atomic_io.py` - the only sanctioned state-write path in this tree,
because readers poll mid-write.

EVERY INVOCATION IS LOGGED, and that is a requirement rather than an
improvement. See `log_invocation`.

TWO ENVIRONMENT VARIABLES, AND BOTH EXIST FOR THE SAME REASON
=============================================================

A SUBPROCESS CANNOT BE ISOLATED BY MONKEYPATCHING A MODULE ATTRIBUTE. The
fixture in `tests/test_watch_inbox.py` redirects every `DEFAULT_` Path by
enumeration - complete, and confined to one interpreter. Anything that
LAUNCHES `python scripts/watch_inbox.py` gets a fresh import with the real
defaults. Measured 2026-09-08: `python -m pytest tests/test_session_hooks.py`
passed 33 arms and left six real lines in `ops/runtime/inbox_invocations.log`
plus two planted fixture keys in `ops/runtime/inbox_reported.json`. So:

  RESINCOMPUTE_RUNTIME_DIR       moves every runtime record. NOT this tool's
                                 own knob - `ops/health.py` defines it and
                                 `headless/runner.py` already honours it.
                                 `DEFAULT_INBOX` deliberately does NOT follow
                                 it; the inbox is an input, and moving it would
                                 isolate a caller by blinding it.
  RESINCOMPUTE_INVOCATION_SOURCE names the entry point. See `resolve_source`.

Neither is required and neither is a test-only door: a scheduled task or an
operator probe can name itself the same way. What matters is the direction of
the default - absent, the label stays the honest one a real hook writes.

THE ENTRY-POINT LABEL HAS THREE SOURCES, IN THIS ORDER
======================================================

  1. RESINCOMPUTE_INVOCATION_SOURCE, the environment.
  2. `--source LABEL`, the flag. See `source_from_argv`.
  3. `cli`, the fallback a bare run writes.

THE ENVIRONMENT OUTRANKS THE FLAG, and the direction is load-bearing.
`tests/test_session_hooks.py` proves a hook fires by launching THE DECLARED
COMMAND out of `.claude/settings.json`, argv and all - it cannot edit that argv
without no longer testing the declared command. The environment is then the
only channel left that can mark a suite-launched child as suite noise, so it
has to win. Inverted, every arm that fires the real hook command would write
lines labelled `sessionstart` into whatever log it could reach, and the
instrument would be measuring its own suite again.

THE FLAG IS A FLAG AND NOT A SECOND VARIABLE because a hook command is handed
to a shell this tree has not measured. `RESINCOMPUTE_INVOCATION_SOURCE=x python
...` is POSIX syntax and this is Windows; `cmd.exe` reads it as a program name
and the hook then fails AT THE HOOK, where nothing in this suite would see it.
Argv is argv on every shell there is.

WHY THIS EXISTS AT ALL. `.claude/settings.json` wires BOTH `SessionStart` AND
`UserPromptSubmit` to this one script, and a manual terminal run is a third
caller, so all three wrote `cli`. Measured 2026-09-08 at HEAD 0e9491a: the
complete log carried ONE label, `cli`, on every fire, three of them stamped
within two seconds of one cold boot while only TWO watch_inbox hook events were
visible in that session. The question the log exists to answer - did
SessionStart fire, and does it survive /clear - is about ONE of those events.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import re
import stat
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

#: Present on Windows only. Named here so the walk reads the same on every
#: platform and the Windows-only bit is a lookup rather than a branch.
_FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.atomic_io import atomic_write_json, atomic_write_text, read_json  # noqa: E402
# `ENV_RUNTIME_DIR` IS RE-EXPORTED ON PURPOSE and is not dead. It is this
# module's statement of which variable isolates a CHILD of this script, and a
# caller that spelled the literal itself would go stale silently the day the
# name moved. F401 is switched ON in this tree by choice - see `ruff.toml` - so
# the suppression is stated here with its reason rather than inherited.
from ops.health import ENV_RUNTIME_DIR, runtime_dir  # noqa: E402, F401

#: Correspondence lives here. Gitignored: see `moon_sync_inbox/README.md`.
#:
#: NOT re-rooted by `RUNTIME_DIR`. The inbox is an INPUT, and a redirect that
#: moved it would isolate a caller by handing this tool an empty channel -
#: green, and blind. `test_every_runtime_record_follows_the_override_and_the_
#: inbox_does_not` asserts that in both directions.
DEFAULT_INBOX = REPO_ROOT / "moon_sync_inbox"

#: Where every runtime record below lives, resolved from the environment at
#: IMPORT so a child process inherits it. See `resolve_source` for why the
#: environment is the only channel that can carry this.
#:
#: `RESINCOMPUTE_RUNTIME_DIR` IS NOT A NEW KNOB. `ops/health.py` defines it and
#: `headless/runner.py` already honours it, so this tool joins one contract
#: rather than standing a second one beside it - and the variable an operator
#: forgets to set is always the one that writes into live state.
RUNTIME_DIR = runtime_dir()

#: Runtime state, gitignored, never source.
DEFAULT_STATE = RUNTIME_DIR / "inbox_seen.json"

#: What has been SHOWN, which is a different fact from what has been READ. Kept
#: in its own file so a plain reporting run leaves the WATERMARK byte-unchanged
#: and mtime-unmoved - the property that stops a subagent's session start from
#: consuming the operator's queue.
DEFAULT_REPORTED = RUNTIME_DIR / "inbox_reported.json"

#: One line per fire. See `log_invocation` for why this is a requirement of the
#: hook rather than an improvement filed against it.
DEFAULT_INVOCATIONS = RUNTIME_DIR / "inbox_invocations.log"

#: WHAT THIS SESSION HAS ALREADY BEEN TOLD. A CACHE, not a record, and the
#: distinction is the whole reason it is a THIRD file rather than a field in one
#: of the two above.
#:
#: NOT `DEFAULT_REPORTED`, and that is not tidiness. `withdrawn` unions
#: `read_reported()` into its baseline by design - Sibling-D's correction,
#: because a note LISTED at session start and pulled before anyone acknowledged
#: lives in the report record and nowhere else. Writing per-session keys into
#: that file would inject them straight into the WITHDRAWAL baseline, and every
#: one of them would re-derive as a withdrawn note on the next fire. Scoping
#: them per session inside that file cannot help either: the baseline reads the
#: whole list.
#:
#: NOT `DEFAULT_STATE` for the reason clause 5 of the fleet contract states
#: flatly - SHOWING NEVER ACKNOWLEDGES. The watermark is what `--mark`
#: advances deliberately, and a per-prompt hook must never reach it.
#:
#: NEVER UNDER `%LOCALAPPDATA%` OR `%APPDATA%`, AND THAT IS MEASURED. RC found
#: this on 2026-09-15 on its own poller state: a hook or tool carrying the
#: Claude desktop app's MSIX package identity has its writes under those roots
#: redirected into the package's LocalCache TWIN, and every later read from that
#: harness returns the twin - silently, with no error and no permission failure.
#: A months-old shadow was being read by every harness shell while the live task
#: rewrote the real file on every poll. Repo roots are NOT virtualised, so this
#: joins `RUNTIME_DIR` like every other runtime record here rather than standing
#: a second contract beside it.
DEFAULT_SESSIONS = RUNTIME_DIR / "inbox_sessions.json"

#: Ceiling on the session rows kept, newest retained. Bounded for the same
#: reason `MAX_INVOCATION_LINES` is: this is rewritten on EVERY prompt, and a
#: record nobody prunes on a path nobody stops is a file that grows for as long
#: as the tree is used. The only session whose suppression can matter is the one
#: now running, so the oldest rows are the ones that go.
MAX_TRACKED_SESSIONS = 64

#: THE OVERFLOW LISTING, and it is the only file here a human is meant to open.
#:
#: Clause 3 of the fleet contract caps the transcript at N names and then wants a
#: POINTER to "the project's gitignored report file". `DEFAULT_REPORTED` could
#: not be that file: it is a machine key-set that answers "has this ever been
#: shown", it holds no drop counts and no anomaly reasons, and pointing an
#: operator at a JSON array of bare keys is pointing them at less than the
#: transcript already gave them.
#:
#: Under `RUNTIME_DIR` with everything else, so it is gitignored and outside the
#: MSIX LocalCache shadow - see `DEFAULT_SESSIONS`.
DEFAULT_REPORT = RUNTIME_DIR / "inbox_report.txt"

#: Ceiling on the names put in the transcript, from clause 3: "at most N full
#: names, newest first, where N is the project's existing list cap or 10 where
#: none exists". MEASURED AT BASE e9b4542: this tree had no cap at all - `_render`
#: printed every entry - so the fleet default of 10 applies.
#:
#: NAMES ARE NEVER TRUNCATED to make them fit, which clause 6 forbids outright.
#: The list is shortened; a name that appears appears whole.
MAX_LISTED_NAMES = 10

#: The token a could-not-measure line must carry, from clause 2. A blind watcher
#: must never read as clean, and silence on a per-prompt hook reads as clean
#: because silence is exactly what a clean inbox produces.
UNMEASURED = "UNMEASURED"

#: Ceiling on the lines kept. The `UserPromptSubmit` hook fires on EVERY prompt,
#: so an uncapped log is a file that grows for as long as the tree is used and
#: that nobody prunes. The oldest lines are dropped, never the newest: the
#: question the log answers - did this fire, just now - is about the recent end.
MAX_INVOCATION_LINES = 2000

#: U+FFFD, what `errors="replace"` substitutes for a byte the decoder cannot
#: take. WRITTEN AS `chr(0xFFFD)` BECAUSE THIS TREE IS 7-BIT ASCII BY RULE and
#: the pre-commit glyph gate rejects the literal. `_log_tail` folds it down to
#: an ASCII `?` before anything is written back - see that docstring for why
#: retaining it would grow the file threefold per fire.
_REPLACEMENT = chr(0xFFFD)

#: The ENTRY POINT column. `cli` is what a hook produces, because a hook runs
#: `python scripts/watch_inbox.py` and reaches `main` through the `__main__`
#: guard. `main` is an in-process call - a test, or another tool importing this
#: one. Without the column the log answers "something ran" and the question is
#: whether the HOOK ran.
SOURCE_MAIN = "main"
SOURCE_CLI = "cli"

#: What a TEST-SPAWNED child calls itself. Named here rather than in the suite
#: so the tree carries one spelling: a label the tests invent privately is a
#: label an operator reading the log has nothing to look it up against.
SOURCE_SUITE = "suite"

#: The HOOK EVENT labels. `cli` said "not an in-process call" and stopped there,
#: and `.claude/settings.json` wires TWO events to this one script, so both of
#: them plus a manual terminal run wrote the same word. Measured 2026-09-08 at
#: HEAD 0e9491a: the complete log carried ONE label, `cli`, on every fire,
#: three of them stamped within two seconds of one cold boot while only TWO
#: watch_inbox hook events were visible in that session. The log's entire
#: purpose is to answer "did SessionStart fire, and does it survive /clear",
#: and it could not separate a SessionStart fire from a per-prompt fire.
#:
#: SPELLED AS THE EVENT NAME LOWERCASED, with nothing else changed. A reader
#: holding a log line and the settings file maps one to the other by eye,
#: without a table to look anything up in; a prettier `session-start` would be
#: a second spelling of a name Claude Code already owns.
SOURCE_SESSION_START = "sessionstart"
SOURCE_USER_PROMPT_SUBMIT = "userpromptsubmit"

#: Claude Code hook event -> the label a hook on that event must declare.
#:
#: DECLARED HERE RATHER THAN IN THE SUITE. `tests/test_session_hooks.py` reads
#: this mapping and grades the REAL `.claude/settings.json` against it, so a
#: wiring that forgets the flag is red, and an event added tomorrow inherits
#: the guard rather than needing somebody to remember it.
HOOK_EVENT_SOURCES = {
    "SessionStart": SOURCE_SESSION_START,
    "UserPromptSubmit": SOURCE_USER_PROMPT_SUBMIT,
}

#: How a caller names itself on ARGV. See `source_from_argv` for why the label
#: arrives this way rather than through the environment.
SOURCE_FLAG = "--source"

#: Names WHO invoked this process, for the case a module attribute cannot
#: reach. See `resolve_source`.
ENV_INVOCATION_SOURCE = "RESINCOMPUTE_INVOCATION_SOURCE"

#: Ceiling on a label, as a literal. The log line is written on a hook path and
#: the label is the one field this module does not choose.
MAX_SOURCE_LABEL_CHARS = 32

#: `\A` and `\Z`, NEVER `^` and `$`. In Python `$` also matches immediately
#: before a trailing newline, so `^[a-z]+$` accepts `cli` followed by a newline
#: - which is precisely the forgery this shape exists to refuse, since a
#: newline in the label writes a second line into a line-oriented log.
_SOURCE_LABEL_SHAPE = re.compile(
    r"\A[a-z0-9][a-z0-9._-]{0," + str(MAX_SOURCE_LABEL_CHARS - 1) + r"}\Z"
)

#: CEILING ON WHAT THIS PROCESS READS FROM STDIN, AS A LITERAL, AND IT IS THE
#: MOST DANGEROUS NUMBER IN THIS FILE.
#:
#: `.claude/settings.json` wires this script as a `UserPromptSubmit` hook with a
#: FIVE SECOND timeout, on every prompt. A read that blocks does not fail loudly:
#: the hook is killed, its stdout is DROPPED by the harness, and nothing anywhere
#: records that it had mail to announce. So the read is bounded on two
#: independent axes, and the budget is only the second of them.
#:
#: THE FIRST AXIS IS THAT IT IS ONE `os.read` AND IS NEVER LOOPED - see
#: `_read_stdin_budget`. A single `os.read` returns as soon as ANY bytes are
#: available, so it waits on one syscall rather than on a full buffer. A loop
#: that drained to the budget or to EOF would reintroduce the unbounded wait
#: that this constant cannot save anyone from.
#:
#: 65536 IS CHOSEN AGAINST THE PAYLOAD RATHER THAN AT RANDOM. A Claude Code hook
#: payload is a small JSON object - the session id, the event name, a transcript
#: path, a working directory - except that a `UserPromptSubmit` payload also
#: carries the operator's PROMPT, which has no small bound at all. A prompt past
#: the budget truncates the JSON, which fails to parse, which yields no session
#: id, which FAILS OPEN and prints. That is the accepted cost and it is armed:
#: the worst outcome is a duplicate line on screen, never a swallowed note.
MAX_STDIN_BYTES = 65536

#: CEILING ON HOW LONG THIS PROCESS WILL WAIT FOR THAT PAYLOAD, IN SECONDS, AND
#: IT IS THE BOUND THAT ACTUALLY MATTERS. THE BYTE BUDGET ABOVE DOES NOT BOUND
#: TIME AT ALL.
#:
#: MEASURED, AND IT WAS SHIPPED BROKEN ONCE. The first version of this reader
#: was a single un-timed `os.read`, defended in prose as bounded because it did
#: not loop. An adversary reproduced the hole and so did this file's own probe:
#: with stdin a pipe that a parent holds OPEN and never writes, that one read
#: blocked past 25 seconds and had to be killed with `taskkill`. Under the
#: `UserPromptSubmit` hook's declared five second timeout the hook is killed,
#: its stdout is DROPPED by the harness, and nothing anywhere records that it
#: had mail to announce. The BASELINE READ NO STDIN AT ALL, so that failure mode
#: was introduced by adding the reader - a watcher that silently dies on every
#: prompt is worse than one that says nothing, and calling it a known residual
#: did not make it safe.
#:
#: SO THE BOUND IS A WAIT AND NOT A PEEK, and the three candidates were measured
#: rather than reasoned about:
#:
#:   os.set_blocking(fd, False)  REFUSED. It works on 3.14 on this box and does
#:                              NOT EXIST on Windows on 3.11, which is the
#:                              version this tree pins - `AttributeError: module
#:                              'os' has no attribute 'set_blocking'`. It also
#:                              mutates an inherited descriptor this process does
#:                              not own, and it cannot wait, so it loses to a
#:                              parent that writes a few milliseconds late.
#:   PeekNamedPipe via ctypes    REFUSED. Works on both interpreters, but it is
#:                              Windows-only, needs a non-pipe fallback for a
#:                              file redirect, and has the same startup race: it
#:                              reports zero bytes available when the parent has
#:                              simply not written yet.
#:   a thread with a bounded join  CHOSEN. One code path on every platform and
#:                              every version, no ctypes, no descriptor
#:                              mutation, and it WAITS - so a parent that writes
#:                              late is still read. Measured identically on 3.11
#:                              and 3.14: 0.03s when the payload is there, and
#:                              it returns and the process exits 0 in ~0.53s
#:                              when it never arrives.
#:
#: 0.5 SECONDS AGAINST A FIVE SECOND CEILING is a tenfold margin, and the cost is
#: paid ONLY on a pathological stdin. A closed or absent stdin gives immediate
#: EOF, a terminal is short-circuited before any read, and a real payload returns
#: as soon as it lands.
STDIN_WAIT_SECONDS = 0.5

#: The field a Claude Code hook payload carries the session id in.
SESSION_ID_FIELD = "session_id"

#: What the session column holds when no validated id reached this process - a
#: manual run, a hook whose stdin was closed, or a payload this module refused.
#:
#: A PLACEHOLDER RATHER THAN AN EMPTY COLUMN. The log is TAB separated and a
#: blank field collapses the record for a naive splitter, so a fire with no
#: session id must still leave a well-formed four-column line.
SESSION_ABSENT = "-"

#: Ceiling on a session id, as a literal, for the same reason
#: `MAX_SOURCE_LABEL_CHARS` is one: the id is written into a capped,
#: line-oriented log and an unbounded id is an unbounded line. A Claude Code
#: session id is a 36-character UUID today; the ceiling is set above that rather
#: than at it, because the shape is a validator and not a format claim.
MAX_SESSION_ID_CHARS = 64

#: `\A` and `\Z`, NEVER `^` and `$`, for exactly the reason recorded above
#: `_SOURCE_LABEL_SHAPE`: in Python `$` also matches immediately before a
#: trailing newline, so `^[a-z]+$` accepts an id followed by a newline - which is
#: the forgery this shape exists to refuse, since a newline in the id writes a
#: second line into a line-oriented log.
#:
#: MIXED CASE IS ALLOWED HERE AND IS NOT ALLOWED FOR THE SOURCE LABEL, and the
#: difference is deliberate. A source label is a name THIS TREE chooses, so two
#: spellings of one entry point are a defect and the shape refuses them. A
#: session id is an OPAQUE IDENTIFIER some other process chose; folding its case
#: would merge two genuinely different sessions, and refusing its case would
#: throw away a real id and fail open on every fire of a harness that happens to
#: emit one. Neither is a repair worth making to an identifier.
_SESSION_ID_SHAPE = re.compile(
    r"\A[A-Za-z0-9][A-Za-z0-9._-]{0," + str(MAX_SESSION_ID_CHARS - 1) + r"}\Z"
)


@contextlib.contextmanager
def _console_logging_muted() -> Iterator[None]:
    """Keep `core/atomic_io.py`'s raw error text off this process's stderr.

    THE RULE THIS ENFORCES IS ABSOLUTE IN THIS TREE: never surface a raw API or
    error string on a user-facing surface - catch it, render a friendly degraded
    state, and LOG the raw error. Every rendering path in this module already
    obeyed it. The WRITE paths did not, and nothing here was the thing printing.

    MEASURED. `core/atomic_io.py` catches its own `OSError` and returns False,
    exactly as documented, and then logs the failure through `core/log_setup.py`,
    whose console handler is a `StreamHandler` on stderr. So a refused write on
    the overflow-report path put a raw `PermissionError: [WinError 5]` in front
    of the operator, carrying the FULL FILESYSTEM PATH - which is also a
    machine-identity leak of the kind this tree has closed before - and ANSI
    colour codes with it. The friendly degraded state was rendered correctly on
    stdout at the same moment, so the operator got both.

    THE FIX IS HERE AND NOT IN `core/atomic_io.py`. That module is the sanctioned
    state-write path for the entire tree and its logging is correct FOR A
    LIBRARY: it must not decide that some caller's console is too precious for an
    error. What is wrong is this module running a hook surface without saying so.
    A caller that knows it is a hook is the right place to say it.

    THE RAW ERROR IS STILL LOGGED, which is the half that must not be lost.
    `core/log_setup.py` attaches a `FileHandler` beside the console handler, and
    only the console one is muted - so the error still reaches the day's log file
    where an operator can grep it. Muting by RAISING THE HANDLER'S LEVEL rather
    than by detaching it keeps that true even if the handler is shared
    process-wide, which `core/log_setup.py` says it is.

    `FileHandler` IS A SUBCLASS OF `StreamHandler`, which is the trap in writing
    this and the reason the check excludes it explicitly. Selecting on
    `StreamHandler` alone would mute the file handler too and turn "do not
    surface it" into "do not record it", which is the opposite instruction.
    """
    muted: list[tuple[logging.Handler, int]] = []
    for logger in (logging.getLogger("core.atomic_io"), logging.getLogger()):
        for handler in list(logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                muted.append((handler, handler.level))
                handler.setLevel(logging.CRITICAL + 1)
    try:
        yield
    finally:
        for handler, level in muted:
            handler.setLevel(level)


def _read_stdin_budget(wait: float | None = None) -> bytes:
    """At most `MAX_STDIN_BYTES` from stdin, waiting at most `STDIN_WAIT_SECONDS`.

    Never raises, and never blocks the caller past that wait.

    THIS IS THE RISKIEST FUNCTION IN THIS FILE and it is written to be boring.
    It runs on a `UserPromptSubmit` hook with a five second ceiling, on every
    prompt, and every failure mode it has is silent: a killed hook has its stdout
    dropped, so a blocked read does not report a blocked read - it reports
    nothing at all, on the one path whose entire job is to speak up.

    THE BOUND IS A WAIT, NOT A BUDGET, AND THE EARLIER VERSION OF THIS FUNCTION
    GOT THAT WRONG. It issued a single un-timed `os.read` and argued in its own
    docstring that not looping made it bounded. It does not: `os.read` on a pipe
    blocks until bytes arrive or every write handle closes, and a parent that
    holds the pipe open without writing satisfies neither. Reproduced here at
    over 25 seconds, killed with `taskkill`. See `STDIN_WAIT_SECONDS` for the
    three candidate fixes and why the thread won on measurement - notably that
    `os.set_blocking` does not exist on Windows on the 3.11 this tree pins.

    THE THREAD IS A DAEMON AND IS DELIBERATELY NEVER JOINED TO COMPLETION. If
    the payload never arrives the worker stays parked in `os.read` forever, and
    that is ACCEPTED: a daemon thread does not hold the interpreter open, so the
    process still exits, measured at ~0.53s and rc 0 on both 3.11 and 3.14. The
    alternative - waiting for a thread that by construction may never return -
    is the hang this function exists to remove.

    THE TERMINAL IS STILL CHECKED FIRST, AND IT IS A DIFFERENT CASE FROM THE
    HANG ABOVE. `python scripts/watch_inbox.py` typed at a prompt has stdin on
    the TERMINAL, where a read blocks until somebody types. The wait would now
    bound that too, but at the cost of half a second on every manual run for a
    payload a terminal is never going to send. `test_a_terminal_stdin_is_not_
    read_at_all` asserts the ORDER by counting descriptor requests, because a
    fake that is never asked for its fd is the only proof the terminal is untouched.

    ONE `os.read` INSIDE THE THREAD, NEVER LOOPED. That still matters: a loop
    draining to the budget or to EOF would keep the worker running past the
    point the caller stopped caring, and could return a payload nobody reads.
    The stated cost is unchanged - a payload split across two writes comes back
    partial, fails to parse, and the fire falls back to printing.

    `sys.stdin.buffer.read(n)` IS NOT USED, deliberately: it loops internally
    until it has `n` bytes or EOF, which is that same drain.

    WHAT IT RETURNS `b""` FOR, all of them normal: no stdin at all; a terminal;
    an object with no file descriptor, which is what pytest's own capture
    installs and therefore what every in-process arm in this suite runs under;
    a payload that did not arrive inside the wait; and any OS-level failure on
    the read. There is no exception path, because an exception here escapes
    before a single line has been written and reads afterwards exactly like a
    hook that is not wired.
    """
    stream = sys.stdin
    if stream is None:
        return b""
    try:
        if stream.isatty():
            return b""
        fd = stream.fileno()
    except (OSError, ValueError, AttributeError):
        # `io.UnsupportedOperation` - what pytest's captured stdin raises out of
        # `fileno` - subclasses both OSError and ValueError, so it is already in
        # this tuple and importing `io` to name it would say nothing extra.
        return b""

    box: list[bytes] = []

    def _worker() -> None:
        try:
            box.append(os.read(fd, MAX_STDIN_BYTES))
        except (OSError, ValueError):
            # Swallowed on purpose. Nothing reads a return value from here, and
            # an exception escaping a thread prints a traceback to stderr - which
            # on a hook path is noise in the operator's session for a condition
            # the empty box already reports.
            pass

    worker = threading.Thread(target=_worker, name="watch-inbox-stdin", daemon=True)
    worker.start()
    worker.join(STDIN_WAIT_SECONDS if wait is None else wait)
    # `box` is read WITHOUT a lock, and that is safe rather than lucky: a single
    # `list.append` is atomic under the GIL, and the only two states this can
    # observe are empty and one-element.
    return box[0] if box else b""


def session_id_from_payload(raw: bytes) -> str | None:
    """The validated session id in a hook's stdin payload, or `None`.

    PURE, AND SEPARATED FROM THE READ ON PURPOSE. The read has to reach a real
    descriptor and a real clock - see `_read_stdin_budget` - and the validation
    has to reach neither, so keeping them apart lets every hostile-payload arm
    below run against plain bytes, with no pipe, no thread and no wait.

    THE ID IS THE SECOND FIELD THIS MODULE DOES NOT CHOOSE, after the source
    label, and it is validated for the same measured reason: the invocation
    record is TAB separated and LINE oriented and capped at
    `MAX_INVOCATION_LINES`, so a tab forges the disposition column and a newline
    forges a whole row - timestamp, entry point, disposition and all. A forged
    row is a fabricated answer to the one question the log exists to answer.

    REFUSED RATHER THAN TRIMMED INTO SHAPE, following `resolve_source` rather
    than inventing a second convention beside it. A silently repaired id is an
    id nobody can trace back to a session, and it would also merge two sessions
    whose ids differed only in the part that got trimmed - which turns a
    suppression cache into a cross-session gag.

    EVERY REFUSAL FAILS OPEN. `None` means the caller prints and writes nothing.
    Absent, closed, empty, truncated, non-UTF-8, non-JSON, JSON that is not an
    object, an object with no id, an id that is not a string and an id the shape
    refuses all arrive here as the same answer, because the caller's correct
    response to all nine is identical.
    """
    if not raw:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        # `json.JSONDecodeError` is a `ValueError`. A truncated payload - the
        # normal consequence of the byte budget - lands here.
        return None
    if not isinstance(payload, dict):
        return None
    candidate = payload.get(SESSION_ID_FIELD)
    if not isinstance(candidate, str) or not _SESSION_ID_SHAPE.match(candidate):
        return None
    return candidate


def validated_session_id() -> str | None:
    """This fire's session id, read from stdin under budget. `None` fails open.

    RESOLVED AT THE PROCESS ENTRY POINT and handed to `main`, for the same
    reason `source_from_argv` is: `main` writes its `start` line BEFORE the body
    runs, and both lines of one fire must name the same session. A fire killed
    at the hook's five second ceiling leaves only that `start` line, so it is
    precisely the line that must carry the id.

    IT IS ALSO WHY THIS IS A PARAMETER RATHER THAN AN AMBIENT READ. Stdin can be
    consumed exactly once. A second call would return `b""` and the two lines of
    one fire would disagree - one attributed, one not - which is the same defect
    `source_from_argv` was written to close for the entry-point label.
    """
    return session_id_from_payload(_read_stdin_budget())


def resolve_source(fallback: str) -> str:
    """The entry-point label this PROCESS writes, from the environment.

    A SUBPROCESS CANNOT BE ISOLATED BY MONKEYPATCHING A MODULE ATTRIBUTE, and
    that is the whole reason this reads the environment. `tests/test_watch_
    inbox.py` redirects every `DEFAULT_` Path by enumeration - complete, and
    confined to one interpreter. A test that launches `python
    scripts/watch_inbox.py` gets a fresh import with the real defaults.
    Measured 2026-09-08: `python -m pytest tests/test_session_hooks.py` passed
    33 arms and left six real lines in the live invocation log, every one of
    them labelled `cli`, which is exactly what a genuine SessionStart hook
    writes. An instrument its own suite writes to indistinguishably is not
    evidence about the world, and the log's entire purpose is to answer
    "does the hook fire, and does it survive /clear".

    THE FALLBACK IS THE HONEST ONE. A hook fires with nothing set, so an absent
    variable must produce the label a hook produces. Inverting that - defaulting
    to a test label - would report every real session start as suite noise.

    THE LABEL IS VALIDATED BECAUSE IT IS THE ONE FIELD THIS MODULE DOES NOT
    CHOOSE. The record is TAB separated and line oriented, so a tab forges the
    disposition column and a newline forges a whole line, timestamp and all.
    Anything that is not a plain lowercase label falls back rather than being
    trimmed into one: a silently repaired label is a label nobody can trace.
    """
    raw = os.environ.get(ENV_INVOCATION_SOURCE, "")
    if _SOURCE_LABEL_SHAPE.match(raw):
        return raw
    return fallback


def source_from_argv(argv: list[str] | None) -> str | None:
    """The `--source` label on this argv, or `None` if there is not a valid one.

    WHY ARGV RATHER THAN THE ENVIRONMENT. The label has to reach the process
    from `.claude/settings.json`, and a hook command there is handed to a shell
    this tree has not measured. `RESINCOMPUTE_INVOCATION_SOURCE=x python ...`
    is POSIX syntax; `cmd.exe` reads it as a program name and the hook fails at
    the hook, where no test in this tree would ever see it. A flag is argv on
    every shell there is.

    PRECEDENCE: ENVIRONMENT, THEN THIS FLAG, THEN THE `cli` FALLBACK. The
    caller composes it as `resolve_source(source_from_argv(argv) or
    SOURCE_CLI)`, so this value is only ever the FALLBACK the environment gets
    to override. That direction is load-bearing rather than arbitrary:
    `tests/test_session_hooks.py` proves a hook fires by launching THE DECLARED
    COMMAND, argv and all, and cannot edit that argv without no longer testing
    the declared command. The environment is the one channel left that can tell
    a suite-launched child from a real fire, so it has to win. Inverted, every
    arm that fires the real hook command would write `sessionstart` lines.

    WHY A HAND SCAN RATHER THAN THE PARSER. `main` writes its `start` line
    BEFORE it calls `_main`, which is where `parse_args` runs - see `main`. A
    plain argparse flag could therefore only label the terminal line, and the
    two lines of one fire would name two different callers. Worse, the `start`
    line is the ONLY evidence left by a fire killed at the hook's five second
    ceiling, so it is precisely the line that must carry the label. This runs
    at the process entry point instead, before `main`.

    IT NEVER RAISES AND NEVER EXITS. A malformed flag returns `None` and the
    fire falls back to `cli`, exactly as a malformed variable does: this runs
    before a single line has been written, so an exception here would leave a
    fire with NO record at all - which reads afterwards like a hook that is not
    wired. `_build_parser` still declares `--source`, so `_main` reports a
    genuinely bad argv through the normal `argv-rejected` disposition.

    THE LAST OCCURRENCE WINS, matching argparse, for the form this scan
    accepts. The two readers do NOT agree everywhere, and claiming they did
    was an overclaim found by an adversary: argparse honours the abbreviation
    `--sour x`, accepts `--source=` as the empty string, and raises
    `SystemExit(2)` for a trailing `--source` with no value, while this scan
    returns None for all three. Every divergence falls on the conservative
    side - None means the label falls back to `cli` - and `_main` never reads
    `args.source`, so no divergence can reach the log. Measured 2026-09-08.
    """
    if not argv:
        return None

    inline = SOURCE_FLAG + "="
    found: str | None = None
    for index, item in enumerate(argv):
        if item == SOURCE_FLAG:
            found = argv[index + 1] if index + 1 < len(argv) else ""
        elif item.startswith(inline):
            found = item[len(inline):]

    if found is None or not _SOURCE_LABEL_SHAPE.match(found):
        return None
    return found

#: The OPENING line of a fire, and NOT a termination. It is written before the
#: body runs, so a fire killed part way through - this hook is declared with a
#: five second timeout and `MAX_DROP_ENTRIES` exists because a walk can run past
#: it - still leaves evidence that it happened.
PHASE_START = "start"

#: The terminal dispositions. Exactly one is written per fire.
#:
#: `no-inbox` IS DELIBERATELY NOT `nothing-unread`. `moon_sync_inbox/` is
#: gitignored (`.gitignore:115`), so a fresh clone receives no channel at all
#: and this tool prints its no-inbox line and exits 0. Recording that as a quiet
#: channel would claim the inbox was checked and was empty, which is a different
#: fact and sends a reader somewhere else entirely.
TERMINAL_NO_INBOX = "no-inbox"

#: `inbox-unlistable` IS DELIBERATELY NOT `no-inbox` AND NOT `nothing-unread`.
#: It used to be the third of those, which made the invocation log agree with
#: the false line on screen: a fire that could not read the channel filed itself
#: as a fire that read it and found it quiet. Those are opposite facts and the
#: log is the only place either is recorded, so an operator reconstructing a
#: blind window from the log would have found nothing to notice. It is not
#: `no-inbox` either - that state is normal and permanent in a fresh clone and
#: in every worktree, while this one is a fault somebody has to go and fix.
TERMINAL_UNLISTABLE_INBOX = "inbox-unlistable"
TERMINAL_NOTHING_UNREAD = "nothing-unread"
TERMINAL_REPORTED = "reported"
TERMINAL_WITHDRAWN_ONLY = "withdrawn-only"
TERMINAL_MARKED = "marked"
TERMINAL_MARK_FAILED = "mark-failed"
TERMINAL_USAGE = "usage-printed"
TERMINAL_ARGV_REJECTED = "argv-rejected"
TERMINAL_CRASHED = "crashed"

#: `suppressed` IS DELIBERATELY NOT `nothing-unread`, for exactly the reason
#: `no-inbox` is not. A quiet fire that found unread mail and stayed silent
#: because THIS SESSION had already been told is a different fact from a fire
#: that found a quiet channel, and the log is the only place either one is
#: recorded. Collapsing the two would make the per-session suppression
#: invisible - and an invisible suppression is indistinguishable from the
#: swallowed-mail defect it is one refactor away from becoming.
TERMINAL_SUPPRESSED = "suppressed"

#: Cross-checked against the module's own `TERMINAL_` constants by
#: `test_the_declared_dispositions_are_discovered_rather_than_listed`, because
#: this tuple is itself a hand-maintained list and those go stale silently.
TERMINAL_DISPOSITIONS = (
    TERMINAL_NO_INBOX,
    TERMINAL_UNLISTABLE_INBOX,
    TERMINAL_NOTHING_UNREAD,
    TERMINAL_REPORTED,
    TERMINAL_WITHDRAWN_ONLY,
    TERMINAL_MARKED,
    TERMINAL_MARK_FAILED,
    TERMINAL_USAGE,
    TERMINAL_ARGV_REJECTED,
    TERMINAL_CRASHED,
    TERMINAL_SUPPRESSED,
)

#: This repo's own code in the `from-<CODE>-` naming convention. A note we sent
#: sits in the same directory as one we received, so direction is read off the
#: filename rather than guessed from mtime.
SELF_CODE = "RSC"

#: Written into the watermark for a human. The READER dispatches on the shape
#: of `seen`, not on this number - see the module docstring.
STATE_VERSION = 2

#: A sender's own checksum listing. Surfaced as human context; never the key.
MANIFEST_NAME = "MANIFEST.sha256"

#: Streamed rather than slurped: a drop can carry an arbitrary payload and this
#: runs on a hook with a five second ceiling.
_CHUNK_BYTES = 1 << 20

#: Prefix for the stand-in a file contributes when it cannot be read. It is a
#: digest INPUT, never printed on a user-facing surface.
_UNREADABLE = "unreadable:"

#: Ceiling on entries visited while walking ONE drop. The count is the harmless
#: half of the junction defect; the walk running past the hook's timeout is the
#: outage, because a killed hook surfaces nothing at all. A drop that blows this
#: stops walking and says so rather than reporting a partial payload as whole.
MAX_DROP_ENTRIES = 2000

#: Why an entry could not be digested. These are digest INPUTS and they are also
#: printed - an anomaly is the one thing that must reach the report every run,
#: so its reason is written to be read. They carry no bytes of any payload.
REASON_REPARSE = "reparse-point-not-followed"
REASON_UNCLASSIFIABLE = "neither-file-nor-directory"
REASON_UNWALKABLE = "directory-could-not-be-listed"
REASON_BUDGET = "entry-budget-exhausted"


class InboxUnlistable(Exception):
    """The inbox directory is THERE and its listing failed.

    A FOURTH COULD-NOT-MEASURE STATE, and the one that used to print the
    affirmative clean line. CS published it as a fleet-wide review finding on
    2026-09-16 and asked to be checked rather than agreed with; it REPRODUCED
    here, through a REAL permission denial rather than only an injected one -
    which is the limit CS stated on its own reproduction. Measured on this host
    2026-09-16 against `icacls <dir> /deny <user>:(RD)` on a directory holding
    one real note: `is_dir()` answered True, `os.listdir` raised
    `PermissionError` WinError 5, and the real script printed `unread: none`
    with exit 0 - silence on the quiet path - and filed `nothing-unread` as its
    terminal disposition.

    THE ROOT CAUSE WAS ONE `except OSError` DOING TWO JOBS. `_entries` guarded
    its listing against a MISSING directory, which is normal in a fresh clone,
    and the same clause caught PRESENT-BUT-UNLISTABLE and answered both with an
    empty list. Every caller of `_entries` was then handed "the inbox is empty"
    as the answer to "the inbox could not be read", and there were THREE of
    them, not one:

      the report        printed the affirmative clean line over real mail
      `withdrawn`       derived every held key as RETRACTED, announcing a
                        retraction of mail sitting in the directory - and a
                        withdrawal is the one inbox event with no artifact left
                        on disk, so a fabricated one is uncheckable
      `--mark`          rewrote the watermark from the empty listing and ERASED
                        it, and pruned the report record to nothing. Measured:
                        `{"seen": {"NOTE-live.md": "41bc9432..."}}` became
                        `{"seen": {}}`, printing `marked read:` while it did it

    SO THE SIGNAL IS AN EXCEPTION RATHER THAN A GUARD AT ONE CALL SITE. A guard
    added where the report reads would have left the acknowledge destroying
    state, because `mark_seen` does not go through the report. Raising makes the
    blind state impossible to receive as an empty listing, which fixes all three
    by construction rather than by remembering three times.

    NOT AN `OSError` SUBCLASS, deliberately. Half this module's readers catch
    `OSError` to degrade gracefully around one unreadable child, and every one
    of them would swallow this - reinstating the exact conflation it exists to
    end.
    """


#: The label the exception above carries, spelled beside its siblings so the
#: vocabulary stays in one place. Distinct from `REASON_UNWALKABLE`, which is a
#: directory INSIDE a drop: that one is an anomaly within a payload that was
#: otherwise measured, and this one means the channel was not examined at all.
REASON_INBOX_UNLISTABLE = "inbox-could-not-be-listed"


class Entry(NamedTuple):
    """One thing in the inbox, note or drop, with what it currently hashes to.

    `files` and `manifest` are appended at the END with defaults, per the
    convention in `CLAUDE.md`: a mid-tuple required field breaks every existing
    positional construction and its tests.
    """

    key: str
    digest: str
    path: Path
    kind: str
    files: int = 0
    manifest: bool = False
    anomalies: tuple[str, ...] = ()


def direction(name: str) -> str:
    """`sent` if this repo wrote the note, `recv` otherwise.

    Outbound notes are LABELLED rather than hidden. A cold session wants to know
    what this repo said as well as what arrived - half a conversation reads as
    an unanswered question.
    """
    return "sent" if f"-from-{SELF_CODE}-" in name else "recv"


def _file_digest(path: Path) -> str:
    """sha256 of a file's bytes, or a marker naming why it could not be read.

    The marker is deliberate. A file that failed to open must MOVE the digest
    it contributes to, not disappear from it - a payload half of which vanished
    from the manifest would otherwise report as unchanged.
    """
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        return f"{_UNREADABLE}{exc.__class__.__name__}"
    return digest.hexdigest()


def _classify(child) -> tuple[str, str]:  # noqa: ANN001 - duck-typed on purpose
    """(`dir` | `file` | `anomaly`, reason). The reason is empty unless anomalous.

    THIS EXISTS BECAUSE OF THE MISSING `else`. An `if is_dir() / elif is_file()`
    ladder drops any entry BOTH calls answer False for off the end of the loop,
    under a confident exit 0. Sibling-C reached that state with a trailing dot
    or space in a filename; Sibling-D could not create such a name on its box at
    all, so the class is handled here rather than tested through a trick that
    does not port. An unstattable entry lands here too, by the same argument: it
    must be reported, never assumed away.
    """
    try:
        if child.is_dir():
            return "dir", ""
        if child.is_file():
            return "file", ""
    except OSError:
        return "anomaly", REASON_UNCLASSIFIABLE
    return "anomaly", REASON_UNCLASSIFIABLE


def _is_reparse_point(path: Path) -> bool:
    """Whether `path` is a link, junction or any other reparse point.

    `Path.is_symlink()` IS NOT ENOUGH ON WINDOWS. It returns False for an NTFS
    junction, which is why `rglob` descends one: Sibling-D measured a one-file
    drop reported as 32 files, Sibling-A measured the same shape at 6, and a
    junction over a large tree runs the walk past the hook's timeout. The
    attribute bit is the check that actually answers the question; the
    `is_symlink` half is the portable fallback for everything else.
    """
    try:
        if path.is_symlink():
            return True
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except (OSError, ValueError):
        # Unstattable is not "ordinary". Treating it as a reparse point prunes
        # the walk, and the caller records it as an anomaly either way.
        return True
    return bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT)


def _walk_drop(drop: Path) -> tuple[list[Path], list[tuple[str, str]]]:
    """(files under `drop` in a stable order, (relative path, reason) anomalies).

    ITERATIVE AND PRUNED, because `rglob` cannot be told not to follow a
    junction. Every entry the walk refuses to digest - a reparse point, an
    unlistable directory, something that is neither a file nor a directory, or
    the point at which the budget ran out - comes back as an anomaly rather
    than as silence. That is Sibling-C's rule: WHAT CANNOT BE DIGESTED IS
    FORCED INTO EVERY REPORT WITH ITS REASON, never keyed silently and never
    dropped.
    """
    files: list[Path] = []
    anomalies: list[tuple[str, str]] = []
    pending = [drop]
    visited = 0

    def rel_of(path: Path) -> str:
        try:
            return path.relative_to(drop).as_posix()
        except ValueError:
            return path.name

    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            anomalies.append((rel_of(current), REASON_UNWALKABLE))
            continue
        for child in children:
            visited += 1
            if visited > MAX_DROP_ENTRIES:
                anomalies.append((rel_of(child), REASON_BUDGET))
                pending.clear()
                break
            if _is_reparse_point(child):
                # NOT descended and NOT ignored. Both halves are the fix.
                anomalies.append((rel_of(child), REASON_REPARSE))
                continue
            kind, reason = _classify(child)
            if kind == "dir":
                pending.append(child)
            elif kind == "file":
                files.append(child)
            else:
                anomalies.append((rel_of(child), reason))

    files.sort(key=lambda p: p.as_posix())
    anomalies.sort()
    return files, anomalies


def _drop_manifest(drop: Path) -> tuple[str, int, bool, tuple[str, ...]]:
    """(manifest digest, file count, sender manifest present, anomaly reasons).

    Computed over WHAT IS ON DISK. See the module docstring for why a sender's
    own `MANIFEST.sha256` is refuted as the key and shipped as context instead.

    THE FORMAT DOES NOT MOVE FOR A DROP OF ORDINARY FILES. An anomaly
    contributes a line of exactly the same shape - relative path, NUL, then its
    reason where a hash would be - so a drop with no anomalies hashes to the
    byte-identical value it hashed to before this walk existed. Sibling-D named
    the constraint and this repo measured the cost of breaking it at 88 notes:
    a watcher that re-reports the whole inbox because its digest format moved
    is a worse artifact than the silence it fixes.
    """
    files, anomalies = _walk_drop(drop)
    lines = []
    manifest = False
    for path in files:
        try:
            rel = path.relative_to(drop).as_posix()
        except ValueError:
            rel = path.name
        if rel == MANIFEST_NAME:
            manifest = True
        lines.append(f"{rel}\0{_file_digest(path)}")
    for rel, reason in anomalies:
        lines.append(f"{rel}\0{reason}")
    body = "\n".join(sorted(lines))
    reasons = tuple(f"{rel}: {reason}" for rel, reason in anomalies)
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), len(files), manifest, reasons


def _entries(inbox: Path) -> list[Entry]:
    """Every note and drop in the inbox, oldest name first.

    An ABSENT inbox is empty rather than an error: a fresh clone has no
    `moon_sync_inbox/` at all, and so does every worktree, because the directory
    is gitignored.

    AN INBOX THAT IS THERE AND CANNOT BE LISTED RAISES `InboxUnlistable`, and
    the two states are split apart here on purpose - see that exception for the
    three defects one shared `except OSError` produced. Empty and unreadable are
    the same VALUE and they are opposite FACTS, so the difference cannot be
    carried in the return value.

    THE `is_dir()` PROBE KEEPS ITS OWN TOLERANT GUARD. A path whose PARENT is
    unreadable makes `is_dir()` itself raise, and that is the absent case as far
    as this tool can tell: there is nothing at `inbox` that it can name.
    """
    try:
        if not inbox.is_dir():
            return []
    except OSError:
        return []

    try:
        children = sorted(inbox.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        # THE RAW ERROR REACHES THE LOG AND NEVER THE SURFACE, which is this
        # tree's absolute rule and the same split `_console_logging_muted`
        # exists to keep. The exception carries a LABEL, not the error text: it
        # is rendered into a user-facing line by `_main`, and an error string
        # there would carry a full filesystem path in front of the operator.
        logging.getLogger(__name__).warning("inbox listing failed at %s: %r", inbox, exc)
        raise InboxUnlistable(REASON_INBOX_UNLISTABLE) from exc

    entries: list[Entry] = []
    for child in children:
        try:
            if _is_reparse_point(child):
                # A link at the TOP level is a deliverable nobody can digest.
                entries.append(
                    Entry(child.name, REASON_REPARSE, child, "anomaly", 0, False, (REASON_REPARSE,))
                )
                continue
            kind, reason = _classify(child)
            if kind == "dir":
                digest, count, manifest, reasons = _drop_manifest(child)
                entries.append(
                    Entry(child.name + "/", digest, child, "drop", count, manifest, reasons)
                )
            elif kind == "file" and child.name.lower().endswith(".md"):
                entries.append(Entry(child.name, _file_digest(child), child, "note"))
            elif kind == "file":
                # A LOOSE TOP-LEVEL FILE IS A DELIVERABLE IN ITS OWN RIGHT.
                # Measured on this channel 2026-09-07: Sibling-A delivered
                # `REFERENCE-moon_sync_poller.py.txt` beside a note, and every
                # watcher globbing `*.md` was silent about it - not a note, not
                # a directory, so it matched nothing. It is keyed on its content
                # like everything else and NONE of its bytes reach the report.
                entries.append(Entry(child.name, _file_digest(child), child, "file"))
            else:
                entries.append(Entry(child.name, reason, child, "anomaly", 0, False, (reason,)))
        except OSError:
            # One unreadable child must not take the whole report down, but it
            # must not vanish either - it is reported with its reason.
            entries.append(
                Entry(
                    child.name,
                    REASON_UNCLASSIFIABLE,
                    child,
                    "anomaly",
                    0,
                    False,
                    (REASON_UNCLASSIFIABLE,),
                )
            )
    return entries


def _seen(state: Path) -> tuple[dict[str, str], set[str]]:
    """(current key -> digest map, legacy name set). Corrupt state means neither.

    Exactly one of the two is ever populated, because `seen` is either an
    object or a list. Both are returned so the caller does not have to know
    which shape it got.
    """
    payload = read_json(state, default=None)
    if not isinstance(payload, dict):
        return {}, set()
    seen = payload.get("seen")
    if isinstance(seen, dict):
        return {k: v for k, v in seen.items() if isinstance(k, str) and isinstance(v, str)}, set()
    if isinstance(seen, list):
        # The shipped name-only shape. A name here grandfathers its note
        # whatever the file now hashes to - see the module docstring.
        return {}, {n for n in seen if isinstance(n, str)}
    return {}, set()


def _is_seen(entry: Entry, digests: dict[str, str], legacy: set[str]) -> bool:
    if entry.key in digests:
        return digests[entry.key] == entry.digest
    return entry.key in legacy


def survey(inbox: Path, state: Path) -> tuple[int, list[Entry]]:
    """(entries examined, entries unread). Pure read - never marks.

    RETURNS THE PAIR ON PURPOSE. A watcher that matches nothing reports
    "unread: none" and looks exactly like a clean one: zero out of zero
    rendered as a clean bill of health. The examined count is what lets a
    caller - and every arm of `tests/test_watch_inbox.py` - tell the two apart.

    RAISES `InboxUnlistable` RATHER THAN ANSWERING `(0, [])`, which is the same
    property one step further on. An examined count of zero at least says "I
    matched nothing"; a blind read has not examined anything and must not be
    able to say it did. `_main` renders it; see that exception for what the
    silent version cost.
    """
    entries = _entries(inbox)
    digests, legacy = _seen(state)
    return len(entries), [e for e in entries if not _is_seen(e, digests, legacy)]


def unseen_entries(inbox: Path, state: Path) -> list[Entry]:
    """Notes and drops the watermark does not already hold at this digest."""
    return survey(inbox, state)[1]


def unseen_notes(inbox: Path, state: Path) -> list[Path]:
    """The unread NOTES only, as paths. Kept for callers that predate drops."""
    return [e.path for e in unseen_entries(inbox, state) if e.kind == "note"]


def mark_seen(inbox: Path, state: Path) -> bool:
    """Record every note and drop currently in `inbox` as read, at its digest.

    Returns whether the write landed.

    THE SET IS REWRITTEN FROM THE CURRENT LISTING, NOT MERGED INTO. That is
    deliberate rather than incidental: a key that no longer exists drops out,
    so a re-dated batch cannot accumulate two entries per note forever.
    Sibling-C found the same property in its own implementation by accident and
    asked that it be kept on purpose. `test_the_seen_set_does_not_accumulate_
    renamed_notes` pins it.

    Rewriting is also the migration: one `--mark` carries a legacy name-only
    watermark over to the keyed shape.

    AND AN UNLISTABLE INBOX IS REFUSED RATHER THAN REWRITTEN FROM NOTHING. The
    rewrite-rather-than-merge property above is exactly what makes this
    destructive: handed an empty listing for an inbox it could not read, it
    writes `{"seen": {}}` over a real watermark. Measured against a real ACL
    denial on this host 2026-09-16 - one `--mark` erased a watermark holding a
    real note and printed `marked read:` while doing it, on the one command an
    operator runs deliberately.

    FALSE COMES BACK AND THE BYTES ARE LEFT ALONE, following `prune_records`,
    which already refuses for the mirror-image reason on the other record rather
    than inventing a second convention beside it.
    """
    try:
        seen = {entry.key: entry.digest for entry in _entries(inbox)}
    except InboxUnlistable:
        return False
    state.parent.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(state, {"version": STATE_VERSION, "seen": seen})


def _reported_record(reported: Path) -> tuple[set[str], str | None]:
    """The keys shown, and the REASON the record is unusable if it is.

    Returns `(keys, None)` when the record is ABSENT or READABLE, and
    `(set(), reason)` when a file exists at `reported` whose contents this
    module cannot use.

    ABSENT AND UNREADABLE ARE NOT THE SAME STATE, and this is the only place
    that says so. `read_json` returns its default for a missing file, for an
    undecodable one and for corrupt JSON alike, so every caller here used to
    see one empty set for three different facts. Absent is legitimately empty
    history; unreadable is history that is on disk and cannot be seen. A caller
    that splices the second with new data and writes it back deletes it.

    FAIL CLOSED IS THE POINT, taken from `tools/moon_sync_responder.py`'s
    `refusals_usable`, which was written for exactly this fail-open hazard. A
    caller holding a reason must REFUSE ITS WRITE and leave the bytes where
    they are, so the record can be repaired rather than replaced.

    `reason` IS A SHORT MODULE-CHOSEN LABEL, NEVER A RAW PARSE STRING. It
    reaches a user-facing surface, and this tree does not surface raw error
    text. The raw failure is already logged by `read_json` at error level,
    which is where it belongs.
    """
    if not reported.exists():
        return set(), None
    payload = read_json(reported, default=None)
    if not isinstance(payload, dict):
        return set(), "the record is present but could not be parsed"
    shown = payload.get("reported")
    if not isinstance(shown, list):
        return set(), "the record is present but carries no list of keys"
    return {k for k in shown if isinstance(k, str)}, None


def read_reported(reported: Path) -> set[str]:
    """The keys this repo has ever SHOWN the operator. Corrupt means empty.

    THIS RECORD NEVER FEEDS THE UNREAD DECISION. It is written by a plain
    reporting run, so if it ever reached `_is_seen` a session start would
    silently consume the operator's queue - which is exactly the defect `--mark`
    is separated out to prevent, re-entering behind it. Its only reader is
    `withdrawn`. `test_the_report_record_is_never_a_second_acknowledgement_path`
    pins that, and it is the arm nobody asks for.

    UNREADABLE STILL DEGRADES TO EMPTY HERE, DELIBERATELY. This function is a
    READER for readers: its only caller is `withdrawn`, which prints. A degraded
    read there under-reports withdrawals and can never invent one, so it fails
    in the safe direction, and making it raise instead would take the
    session-start hook down with it. Every WRITER goes through
    `_reported_record` and refuses. `test_read_reported_still_degrades_to_empty_
    for_its_reading_callers` pins the split so a later reader cannot "finish the
    fix" by tightening the wrong half.
    """
    return _reported_record(reported)[0]


def record_reported(reported: Path, keys: list[str]) -> bool:
    """Add `keys` to the record of what has been shown. Union, never a rewrite.

    THE DOCSTRING ABOVE USED TO BE FALSE, which is how this was found. The
    union started from `read_reported`, and an unreadable record read as the
    empty set - so the "union" was a total rewrite from nothing wearing a
    union's name, and one stray byte in the record turned the next report into
    an erasure of everything ever shown.

    AN UNUSABLE RECORD IS NOW REFUSED RATHER THAN REPLACED: False comes back,
    nothing is written, and the bytes stay on disk to be repaired. False is
    surfaced by `_main` as a degraded line; it is not an exception, because
    this runs inside a session-start hook.
    """
    known, unusable = _reported_record(reported)
    if unusable is not None:
        return False
    merged = known | set(keys)
    reported.parent.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(reported, {"version": 1, "reported": sorted(merged)})


def withdrawn(inbox: Path, state: Path, reported: Path) -> list[str]:
    """Keys this repo has seen or shown that are no longer in the inbox.

    THE BASELINE IS `reported | seen`, NOT `seen` ALONE. Sibling-D's correction,
    and the case that motivated the whole feature is the one a seen-only
    baseline scores as a non-event: notes LISTED at session start and pulled
    before anyone ran the acknowledge live in the REPORT record only.

    THE COMPARISON IS ON THE STABLE NAME. Once keys carry a content digest an
    EDIT and a RETRACTION both move the key, so comparing digests would file an
    edited note in two contradictory sections of the same report. This tool's
    key already IS the bare name, with the digest held beside it as the value,
    so the name comparison is the natural one rather than a stripping step.

    WHY IT IS CARRIED RATHER THAN REPORTED ONCE. Reporting a withdrawal exactly
    once puts it straight back into the watermark's own failure class - a
    session cleared before anyone reads the output loses it - and unlike every
    other inbox event there is no artifact left on disk to notice later. It is
    carried until an explicit `--mark` prunes it.

    AN UNLISTABLE INBOX IS NOT A MASS RETRACTION. The subtraction below reads an
    empty listing as "none of it is there any more", so an inbox this tool
    cannot read used to derive EVERY held key as withdrawn - the watcher
    announcing that a sibling pulled mail that is sitting in the directory.
    Nothing is returned instead, and the caller says it was blind; that is the
    only honest answer, because a withdrawal is the one inbox event with no
    artifact left on disk to check a claim against.
    """
    try:
        present = {entry.key for entry in _entries(inbox)}
    except InboxUnlistable:
        return []
    digests, legacy = _seen(state)
    baseline = set(digests) | legacy | read_reported(reported)
    return sorted(baseline - present)


def prune_records(inbox: Path, reported: Path) -> bool:
    """Drop every reported key that is no longer in the inbox.

    THE ACKNOWLEDGE HAS TO PRUNE BOTH RECORDS. Sibling-D shipped this half
    broken and found it twenty minutes later by running its own command against
    live mail: the acknowledge pruned the SEEN record and never touched the
    REPORT record, so a withdrawn name re-derived itself on every run and could
    never be cleared by anything. Every arm passed, because every arm asserted
    that a withdrawal REPORTS and none asserted that it STOPS. A report the
    reader cannot clear is a defect even when every line in it is true.

    AND AN UNREADABLE RECORD IS REFUSED RATHER THAN PRUNED TO NOTHING. The
    intersection used to start from a degraded read, so a record this module
    could not parse was answered with `"reported": []` - the acknowledge
    destroying the exact history it exists to maintain, and doing it on the one
    command the operator runs deliberately. False comes back and the bytes are
    left alone; `_main` refuses the whole acknowledge on it.

    AND AN UNLISTABLE INBOX IS REFUSED FOR THE SAME REASON FROM THE OTHER SIDE.
    The intersection has two inputs and the refusal above covered only one of
    them: an inbox this tool could not READ arrived as an empty `present` set
    and pruned the record to `[]` just as surely as a degraded read of the
    record itself. Measured against a real ACL denial on this host 2026-09-16.
    """
    known, unusable = _reported_record(reported)
    if unusable is not None:
        return False
    try:
        present = {entry.key for entry in _entries(inbox)}
    except InboxUnlistable:
        return False
    reported.parent.mkdir(parents=True, exist_ok=True)
    keep = sorted(known & present)
    return atomic_write_json(reported, {"version": 1, "reported": keep})


#: How a suppression key names the EVENT rather than the entry. A note shown as
#: unread and the same note's later WITHDRAWAL are two different events about one
#: bare name, so a flat key set would score the withdrawal as already shown and
#: stay silent about it - losing the one inbox event that leaves no artifact on
#: disk for anybody to notice later.
SHOWN_UNREAD = "unread:"
SHOWN_GONE = "gone:"

#: The ABSENT-INBOX line's own event key. Clause 4 makes this the one
#: could-not-measure state that MAY be shown once per session id rather than
#: re-printed on every fire while it persists - and it needs that allowance more
#: than any other, because an absent inbox is not transient. It is the normal
#: permanent state of a fresh clone and of every worktree, so re-printing it
#: would put a line in front of the operator on every single prompt, forever.
SHOWN_NO_INBOX = "no-inbox:"

#: The UNLISTABLE-INBOX line's own event key, namespaced away from the one above
#: for the reason `SHOWN_UNREAD` and `SHOWN_GONE` are namespaced away from each
#: other: two different events about one bare path, and a flat key set would
#: score the second as already shown.
#:
#: IT TAKES THE SAME ONCE-PER-SESSION ALLOWANCE AS ITS SIBLING, and for the same
#: clause 4 reason: an ACL does not clear itself between prompts, so a per-prompt
#: hook would otherwise put this line in front of the operator on every single
#: prompt for as long as the fault lasts. The SessionStart command declares no
#: `--quiet-when-empty`, so a session still always BEGINS by being told - which
#: is the fire that matters - and with no session id it re-prints, which is fail
#: open.
SHOWN_UNLISTABLE_INBOX = "unlistable-inbox:"


def read_shown(sessions: Path, session: str | None) -> set[str]:
    """Event keys this SESSION has already been shown. Absent or unusable is empty.

    DEGRADES TO EMPTY, WHICH IS FAIL OPEN, AND THAT IS THE OPPOSITE POLARITY TO
    `_reported_record`. The difference is the point and not an inconsistency.

    `_reported_record` fails CLOSED because a caller that spliced an unreadable
    report record with new data and wrote it back would DELETE history that is on
    disk and irreplaceable. This file holds no history. It is a CACHE whose
    entire content is reconstructed by the next fire, and the worst consequence
    of losing all of it is one duplicate line on screen. Failing closed here
    would invert that: a single stray byte in a cache file would suppress real
    mail, which is the failure the watcher exists to prevent.

    `test_an_unreadable_cache_re_prints_rather_than_suppressing` pins this half
    so a later reader cannot "finish the fix" by tightening the wrong one.

    NO SESSION MEANS THE EMPTY SET, so a fire with no validated id suppresses
    nothing at all.
    """
    if session is None:
        return set()
    payload = read_json(sessions, default=None)
    if not isinstance(payload, dict):
        return set()
    rows = payload.get("sessions")
    if not isinstance(rows, list):
        return set()
    for row in rows:
        if isinstance(row, dict) and row.get("id") == session:
            shown = row.get("shown")
            if isinstance(shown, list):
                return {k for k in shown if isinstance(k, str)}
            return set()
    return set()


def record_shown(sessions: Path, session: str | None, keys: list[str]) -> bool:
    """Add `keys` to this session's shown set. Returns whether a write landed.

    CALLED ONLY AFTER STDOUT HAS BEEN FLUSHED, and the caller is where that
    ordering lives. It matters because this hook is declared with a five second
    ceiling: recorded first and then killed, an entry would be filed as SHOWN
    having never reached a human - a note silently swallowed, which is the one
    outcome worse than a duplicate. Written after the flush, a killed fire
    RE-PRINTS instead. `test_the_cache_is_written_only_after_stdout_is_flushed`
    asserts the order rather than an outcome, because both orderings look
    identical on any fire that is not killed.

    IT NEVER TOUCHES THE WATERMARK AND NEVER TOUCHES THE REPORT RECORD. That is
    clause 5 of the fleet contract - SHOWING NEVER ACKNOWLEDGES - and it is why
    this is a third file. See `DEFAULT_SESSIONS` for why neither existing record
    could carry it.

    THE CURRENT SESSION IS MOVED TO THE END, which is what makes the cap an LRU
    rather than a guillotine. Rows are ordered oldest first and the tail is kept,
    so the session now running can never be the row that gets dropped.

    A CORRUPT CACHE IS REPLACED RATHER THAN REFUSED, which is the direction
    `record_reported` deliberately does NOT take. Again: there is no history here
    to lose. Refusing the write would leave a bad byte suppressing nothing
    forever and growing nothing, but it would also leave the file unrepairable by
    the only thing that writes it.
    """
    if session is None or not keys:
        return False
    payload = read_json(sessions, default=None)
    rows: list[dict] = []
    if isinstance(payload, dict) and isinstance(payload.get("sessions"), list):
        rows = [
            row
            for row in payload["sessions"]
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        ]
    kept = [row for row in rows if row.get("id") != session]
    kept.append({"id": session, "shown": sorted(read_shown(sessions, session) | set(keys))})
    sessions.parent.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(
        sessions, {"version": 1, "sessions": kept[-MAX_TRACKED_SESSIONS:]}
    )


def _log_tail() -> list[str]:
    """The lines already in the invocation log, oldest first. Unreadable is MANGLED.

    THIS USED TO RETURN THE EMPTY LIST ON A DECODE FAILURE, and the docstring
    that defended it argued that rewriting "loses history it could not see
    anyway". That sentence is true about the corrupt BYTES and false about the
    FILE. `log_invocation` does not append: it rebuilds the file from this tail
    plus one new line and writes the result over the target. So one undecodable
    byte anywhere - newest line or oldest - made the very next fire replace the
    entire log with a single line, and `MAX_INVOCATION_LINES` was never the
    only discard path. Reproduced 2026-09-10 on a COPY of the live record,
    which held 664 lines at the time: two bytes took all 664. The live log
    itself has never been truncated - the consequence is demonstrated, not
    suffered. Degrading a READ to empty is defensive; splicing that empty with
    new data and writing it BACK converts unreadable history into DELETED
    history, which is a different act.

    THE PRECEDENT IS `tools/moon_sync_responder.py`, which reads its own
    invocation log with `errors="replace"` and is immune to this by
    construction. Preserving mangled bytes beats deleting readable ones.

    FOLDING THE REPLACEMENT CHARACTER DOWN TO ASCII `?` IS A DEPARTURE FROM
    THAT PRECEDENT AND IS DELIBERATE. The responder only ever TRIMS, and rarely;
    this module rewrites the whole file on EVERY fire, and `atomic_write_text`
    encodes UTF-8. A retained U+FFFD would therefore be written back as three
    bytes, read back on the next fire as three replacement characters and
    written back as nine - one bad character growing threefold per fire, past a
    billion bytes inside twenty. `?` is ASCII, so the rewrite is stable and the
    mangled line stops changing. `test_a_second_fire_does_not_grow_the_mangled_
    line` pins that, and it is the arm nobody asks for.

    STILL NEVER RAISES. A hook that dies on a corrupt runtime file surfaces
    nothing at all, so an OSError or a ValueError out of the read is still the
    empty list - which is now the ABSENT case and only the absent case.
    `UnicodeDecodeError` has left the tuple because `errors="replace"` cannot
    raise it; it is a `ValueError` subclass in any event, so nothing narrowed.
    """
    try:
        raw = DEFAULT_INVOCATIONS.read_text(encoding="ascii", errors="replace")
    except (OSError, ValueError):
        return []
    return [line.replace(_REPLACEMENT, "?") for line in raw.splitlines() if line.strip()]


def log_invocation(
    source: str,
    disposition: str,
    now: float | None = None,
    session: str | None = None,
) -> bool:
    """One line per fire: when, from which entry point, in which session, and what came of it.

    THIS IS A REQUIREMENT, NOT AN IMPROVEMENT. This tool's only output is a
    report to a human, and a report to a human leaves nothing behind that says
    it ran. The `SessionStart` hook declared in `.claude/settings.json` - `python
    scripts/watch_inbox.py`, timeout 5 - could therefore fire on every cold
    session or on none at all, and this tree would read exactly the same
    afterwards either way. The honest status of "does the hook fire, and does it
    survive /clear" was never UNVERIFIED. It was UNMEASURABLE AS BUILT, which is
    worse, because no amount of care could have measured it.

    Four repositories on this channel reported the same thing as unverified and
    argued it by construction. `tools/moon_sync_responder.py` has the fix;
    this did not, so the same argument that condemned the responder condemned
    this tool and nobody had said so.

    NEVER A PAYLOAD BYTE. The columns are a timestamp, an entry point, a session
    and a disposition. Three of the four are values this module chose. A note is
    untrusted data and none of it reaches the log, for the same reason none of it
    reaches the report.

    THE SESSION COLUMN GOES THIRD, NOT LAST, AND THE POSITION IS LOAD-BEARING.
    `tests/test_session_hooks.py` reads the disposition as the LAST tab-separated
    field and the entry point as the second. Appending the session would silently
    redefine both readings, and the arms would go red describing a disposition
    defect that is not there. Third, every existing reader keeps its meaning and
    the line still ends with what came of the fire - which is also the natural
    reading order, since the outcome is the thing a reader scans for.

    THE SESSION IS VALIDATED HERE AND NOT ONLY AT THE PARSE. It is the one column
    whose value originates outside this process, and the log line is where a tab
    or a newline in it would do its damage: a tab forges the disposition column,
    a newline fabricates an entire row. `session_id_from_payload` is the gate on
    the stdin path, but it is not the only way a value can reach this function -
    a later caller could hand one straight in - so the refusal is enforced at the
    write as well. Anything the shape refuses becomes `SESSION_ABSENT` rather
    than being trimmed into something plausible.

    ATOMIC, DESPITE BEING AN APPEND. `core/atomic_io.py` is the only sanctioned
    state-write path in this tree because readers poll mid-write, and a bare
    `open(path, "a")` leaves a real window in which a reader sees a line without
    its newline. The cap needs a rewrite rather than an append in any case.
    """
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() if now is None else now))
    column = session if session is not None and _SESSION_ID_SHAPE.match(session) else SESSION_ABSENT
    kept = [*_log_tail(), f"{stamp}\t{source}\t{column}\t{disposition}"][-MAX_INVOCATION_LINES:]
    try:
        return atomic_write_text(DEFAULT_INVOCATIONS, "\n".join(kept) + "\n")
    except (OSError, ValueError):
        # A log that cannot be written must not take the watcher down with it:
        # an exception escaping a session-start hook crashes it, and a crashed
        # hook surfaces NOTHING at all.
        #
        # `ValueError` IS IN THIS TUPLE BECAUSE OF A MEASUREMENT. A path
        # carrying a NUL byte raises `ValueError` out of `mkdir`, not `OSError`,
        # and `core/atomic_io.py` catches `OSError` alone - so the escape is
        # real rather than hypothetical. The exception a guard names is a claim
        # about the failure, and the claim needs testing.
        return False


def write_overflow_report(report: Path, entries: list[Entry], heading: str) -> bool:
    """Write the full listing to `report`. Returns whether the write landed.

    WRITTEN BEFORE STDOUT, WHICH IS THE OPPOSITE ORDERING TO `record_shown`, AND
    BOTH ARE RIGHT. Clause 3 says the report file is written atomically BEFORE
    stdout so the pointer never names an absent file; clause 4 says the reported
    record is written only AFTER stdout is flushed so a killed hook re-prints.
    The two clauses order two different writes because they are protecting
    against opposite mistakes - a pointer to nothing, and a suppression of
    something nobody saw.

    ATOMIC, through `core/atomic_io.py`, which is the only sanctioned state-write
    path in this tree. It matters more here than usual: the pointer printed a
    moment later invites a human to open this file, so a reader can arrive
    mid-write.

    NAMES, COUNTS AND DIGESTS ONLY - NEVER A PAYLOAD BYTE. This file is not
    stdout and is not injected into a session's context, but it is read by the
    same operator moments later and the rule does not get to relax because the
    surface changed.
    """
    ordered = _newest_first(entries)
    lines = [
        f"{heading}: {len(ordered)}",
        "the full listing the transcript capped; newest first",
        f"written by scripts/watch_inbox.py, cap {MAX_LISTED_NAMES}",
        "",
    ]
    lines.extend(f"  [{direction(e.key)}] {e.key}{_describe(e)}" for e in ordered)
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        return atomic_write_text(report, "\n".join(lines) + "\n")
    except (OSError, ValueError):
        # Same guard and the same reason as `log_invocation`: a path carrying a
        # NUL byte raises `ValueError` out of `mkdir`, which `core/atomic_io.py`
        # does not catch, and a hook that dies writing a convenience file
        # surfaces nothing at all.
        return False


def _describe(entry: Entry) -> str:
    """The human-context suffix on a drop's line. Empty for a note."""
    bits: list[str] = []
    if entry.kind == "drop":
        bits.append(f"{entry.files} file" + ("" if entry.files == 1 else "s"))
        if entry.manifest:
            bits.append(f"{MANIFEST_NAME} present, not used as the key")
    elif entry.kind == "file":
        bits.append("loose file, not a note")
    # AN ANOMALY IS FORCED INTO EVERY REPORT WITH ITS REASON. It is the one
    # thing that must never be summarised away: the entry the walk could not
    # digest is precisely the one the old walker was silent about.
    bits.extend(entry.anomalies)
    if not bits:
        return ""
    return "  (" + ", ".join(bits) + ")"


def _newest_first(entries: list[Entry]) -> list[Entry]:
    """`entries` in newest-name-first order, which is clause 3's wording.

    ON THE NAME, DESCENDING, AND NOT ON AN MTIME. Every filename on this channel
    is `YYYY-MM-DD-HHMM-from-<CODE>-<topic>`, so a descending name sort IS
    newest-first for the entries that follow the grammar, and it is stable and
    cheap for the ones that do not. An mtime sort would be a different and worse
    answer: a `--mark` run, a checkout or a virus scanner moves mtimes, and
    clause 2 of section 5 is specifically that mtime is not to be trusted here.

    `_entries` DELIBERATELY STAYS ASCENDING - its docstring says "oldest name
    first" and the watermark and `withdrawn` both depend on its order not being
    a display decision. This reverses for DISPLAY only.
    """
    return sorted(entries, key=lambda entry: entry.key, reverse=True)


def _render(entries: list[Entry], heading: str, pointer: str = "") -> list[Entry]:
    """Print the counts line and at most `MAX_LISTED_NAMES` names, newest first.

    Returns THE ENTRIES ACTUALLY LISTED, which is the load-bearing half of the
    signature. Clause 3 ends "the entries beyond the cap are NOT treated as
    shown", so the caller has to be told what went on screen rather than
    assuming its whole input did. A version that returned nothing would leave
    every caller recording the full list as shown, which is the swallowed-mail
    direction.

    THE COUNTS LINE CARRIES THE FULL COUNT, not the listed count. "unread: 25"
    followed by ten names and a pointer is the honest rendering; "unread: 10"
    would be a lie that happens to match the list under it.
    """
    if not entries:
        print(f"{heading}: none")
        return []
    print(f"{heading}: {len(entries)}")
    ordered = _newest_first(entries)
    listed = ordered[:MAX_LISTED_NAMES]
    for entry in listed:
        print(f"  [{direction(entry.key)}] {entry.key}{_describe(entry)}")
    held = len(ordered) - len(listed)
    if held:
        print(f"  (+{held} more{pointer})")
    return listed


def _build_parser() -> argparse.ArgumentParser:
    """The declaration of what `main` accepts, built where a test can read it.

    Extracted so the flag matrix in `tests/test_watch_inbox.py` is DISCOVERED
    from the parser rather than listed by hand. A hand-maintained list of exit
    paths to check is the failure this whole section exists to remove, and it
    would be a poor joke to guard it with one.
    """
    parser = argparse.ArgumentParser(
        description="Report unread moon_sync_inbox notes and advance the watermark.",
    )
    parser.add_argument("--dir", default=str(DEFAULT_INBOX), help="inbox directory")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="watermark file")
    parser.add_argument("--all", action="store_true", help="list every note, read or not")
    parser.add_argument("--reported", default=str(DEFAULT_REPORTED), help="report record")
    parser.add_argument("--mark", action="store_true", help="record the current set as read")
    parser.add_argument(
        "--quiet-when-empty",
        action="store_true",
        help="print nothing at all when there is nothing to report",
    )
    # DECLARED HERE, CONSUMED AT THE `__main__` GUARD. `_main` never reads it:
    # by the time this parser runs the `start` line is already on disk, which
    # is why `source_from_argv` scans argv at the process entry point instead.
    #
    # It is declared all the same, and that is not decoration. Without it every
    # hook wired with `--source` would leave through argparse as `argv-rejected`
    # with exit code 2, printing a usage block into the session context on every
    # single session start.
    parser.add_argument(
        SOURCE_FLAG,
        default=None,
        help=(
            "name this entry point in the invocation log; overridden by "
            f"{ENV_INVOCATION_SOURCE}, and ignored unless it is a plain "
            "lowercase label"
        ),
    )
    return parser


def main(
    argv: list[str] | None = None,
    source: str = SOURCE_MAIN,
    session: str | None = None,
) -> int:
    """Run one report, with its outcome guaranteed to reach the invocation log.

    EVERY EXIT IS LOGGED HERE, not on the path that takes it. The responder
    logged per exit path first and four terminations - `window`, `budget`,
    `empty` and `disarmed` - simply did not, each having a passing arm asserting
    its termination as a RETURN VALUE. A gate tested as a pure predicate is not
    an enforced gate. Measured against the live scheduled task 2026-09-07 at
    19:16: four fires, four bare `start` lines, no record of what any of them
    decided.

    So the body cannot forget. It returns its disposition, and this wrapper
    writes the terminal line whatever the body did - including when the body
    raised, and including when it left through `SystemExit`, which is what
    argparse throws and which is not an `Exception`.

    Two lines per fire, a `start` and exactly one terminal. The `start` is not
    redundant: a fire killed at the hook's five second ceiling writes no
    terminal line, and the `start` is then the only evidence it happened.

    `session` IS A PARAMETER AND IS NOT READ HERE, for the reason
    `validated_session_id` records: stdin can be consumed exactly once, and both
    lines of one fire must name the same session. It arrives already validated or
    already `None`, and `log_invocation` re-validates it anyway because it is the
    one column whose value came from outside this process.
    """
    # APPLIED AT THE SURFACE, ONCE, RATHER THAN AT EACH WRITE. `main` IS the
    # user-facing surface - it is what `.claude/settings.json` invokes - so this
    # is the frame that knows a raw error string must not escape. Wrapping it
    # covers every write and every degraded read inside it, including the ones a
    # later edit adds, rather than depending on each new call site remembering.
    # The raw error still reaches the day's log file; see `_console_logging_muted`.
    with _console_logging_muted():
        return _main_logged(argv, source, session)


def _main_logged(argv: list[str] | None, source: str, session: str | None) -> int:
    """`main`'s body, so the logging guard above stays one unindented `with`."""
    log_invocation(source, PHASE_START, session=session)
    try:
        code, disposition = _main(argv, session)
    except SystemExit as exc:
        # argparse, and only argparse. A usage print and a rejected flag are
        # different events: the second means something invoked this tool with a
        # flag it does not have, which for a hook is a wiring defect that would
        # otherwise leave no trace at all.
        log_invocation(
            source,
            TERMINAL_USAGE if not exc.code else TERMINAL_ARGV_REJECTED,
            session=session,
        )
        raise
    except BaseException:
        # NOT swallowed. A watcher that hides its own failure is the defect one
        # layer down; the log says the fire died before the exception goes on.
        log_invocation(source, TERMINAL_CRASHED, session=session)
        raise
    log_invocation(source, disposition, session=session)
    return code


def _main(argv: list[str] | None, session: str | None = None) -> tuple[int, str]:
    """The report itself. Returns (exit code, terminal disposition).

    It does not log. That is the whole point of the wrapper above: a path that
    returns early here cannot forget to say what it decided, because saying so
    is the return value rather than a call it has to remember to make.
    """
    args = _build_parser().parse_args(argv)

    inbox = Path(args.dir)
    state = Path(args.state)
    reported = Path(args.reported)

    if not inbox.is_dir():
        # A COULD-NOT-MEASURE STATE, AND IT NOW SAYS SO ON EVERY PATH INCLUDING
        # THE QUIET ONE. Clause 2: a could-not-measure state prints ONE line
        # carrying the token UNMEASURED and never the affirmative clean line.
        #
        # THE QUIET PATH USED TO BE SILENT HERE, and that was the last
        # return-0-plus-UNMEASURED gap in the fleet. Silence is not neutral on
        # this hook: silence is EXACTLY what a clean inbox produces, so a
        # watcher that cannot see the channel at all read as a watcher reporting
        # good news. A blind watcher must never read as clean. It is also the
        # normal state of a fresh clone and of EVERY WORKTREE, because the
        # directory is gitignored - which is precisely when somebody most needs
        # telling that no channel is being watched.
        #
        # AN ABSENT SEEN STORE IS NOT THIS. Clause 2 is explicit that an absent
        # watermark is an EMPTY SET rather than a failure, and `_seen` treats it
        # that way; nothing here prints UNMEASURED for that.
        #
        # SHOWN ONCE PER VALIDATED SESSION, which clause 4 allows for this one
        # state specifically and which it needs more than any other: an absent
        # inbox is not a transient fault that clears, so re-printing it on every
        # fire would put this line in front of the operator on every prompt
        # forever. With no session id it re-prints, which is fail open.
        line = f"{UNMEASURED} - no inbox at {inbox}, so the channel was not examined"
        quiet_session = args.quiet_when_empty and session is not None
        key = SHOWN_NO_INBOX + str(inbox)
        if not quiet_session or key not in read_shown(DEFAULT_SESSIONS, session):
            print(line)
            if quiet_session:
                # Flushed before the cache write, for the reason `record_shown`
                # records: a fire killed between the two would file this as
                # shown having never emitted it.
                sys.stdout.flush()
                record_shown(DEFAULT_SESSIONS, session, [key])
        return 0, TERMINAL_NO_INBOX

    try:
        if args.all:
            entries, heading = _entries(inbox), "all notes"
        else:
            entries, heading = unseen_entries(inbox, state), "unread"
    except InboxUnlistable:
        # THE FOURTH COULD-NOT-MEASURE STATE, and the one that was printing the
        # affirmative clean line. See `InboxUnlistable` for the measurement and
        # for the two further defects that shared its root cause.
        #
        # THE RETURN IS THE OTHER HALF OF THE FIX. Everything below this point -
        # `withdrawn`, the suppression cache, the overflow report, and `--mark`
        # itself - derives from a listing that does not exist. Leaving through
        # here is what stops the acknowledge reaching `mark_seen` at all; the
        # refusal inside `mark_seen` covers the OTHER callers, and neither one
        # is redundant.
        #
        # NO RAW ERROR STRING, per this tree's absolute rule. The label went to
        # the day's log inside `_entries`; this is the friendly degraded state.
        line = (
            f"{UNMEASURED} - the inbox at {inbox} exists but could not be listed, "
            "so the channel was not examined"
        )
        quiet_session = args.quiet_when_empty and session is not None
        key = SHOWN_UNLISTABLE_INBOX + str(inbox)
        if not quiet_session or key not in read_shown(DEFAULT_SESSIONS, session):
            print(line)
            if quiet_session:
                # Flushed before the cache write, for the reason `record_shown`
                # records: a fire killed between the two would file this as
                # shown having never emitted it.
                sys.stdout.flush()
                record_shown(DEFAULT_SESSIONS, session, [key])
        return 0, TERMINAL_UNLISTABLE_INBOX

    # QUIET IS FOR THE PER-PROMPT HOOK. It runs on every single prompt, and a
    # hook that speaks when it has nothing to say trains the reader to skip it -
    # at which point it is worse than absent, because it looks wired.
    gone = withdrawn(inbox, state, reported)

    # RESOLVED ONCE, HERE, AND USED THREE TIMES BELOW. An unreadable report
    # record degrades `withdrawn` as well as the two writers - the baseline
    # unions in `read_reported`, so an unreadable record silently UNDER-reports
    # withdrawals. That read is not itself a fourth defect: it cannot invent a
    # withdrawal and it destroys nothing, so it fails in the safe direction.
    # What it cannot do is stay quiet about it, because a short withdrawal
    # section and a correct one look identical on screen. So the condition is
    # surfaced once, in words, rather than fixed in a reader that must not
    # raise.
    _, unusable = _reported_record(reported)

    # ONCE PER VALIDATED SESSION, AND ONLY ON THE PER-PROMPT PATH.
    #
    # The quiet hook fires on EVERY prompt, and acknowledging is a separate
    # deliberate act, so an unread note re-printed into the session context on
    # every single prompt for as long as it stayed unread - which is potentially
    # forever. The fleet contract states the corollary senders have to budget
    # for: anything that adds notes adds PERMANENT session-start text in every
    # recipient until somebody acknowledges.
    #
    # THE QUIET PATH AND NOTHING ELSE. `SessionStart` fires once per session, so
    # there is nothing for suppression to save there - and a suppressed
    # session-start report is a session that begins blind, which is the exact
    # failure this whole tool was built for. A deliberate manual run and `--all`
    # are the operator asking, and an answer that has been withheld because some
    # earlier prompt already got it is not an answer.
    #
    # NO SESSION ID MEANS FAIL OPEN - print, and write nothing. Without an id
    # there is nothing to scope suppression to, and a global scope would be an
    # acknowledgement wearing a cache's name.
    #
    # THE KEY IS THE EVENT, NOT THE ENTRY. An unread note and that same note's
    # later withdrawal are two events about one bare name, so they are
    # namespaced - see `SHOWN_UNREAD`. The unread key carries the DIGEST as well,
    # because an in-place CORRECTION is the case this channel keys on content
    # for: RULING then ADDENDUM then CORRECTION is routine here, and suppressing
    # on the name alone would swallow the correction inside the very session that
    # had been told about the version it corrects.
    suppress = args.quiet_when_empty and session is not None
    already = read_shown(DEFAULT_SESSIONS, session) if suppress else set()
    held_back = 0
    if suppress:
        fresh = [e for e in entries if SHOWN_UNREAD + e.key + ":" + e.digest not in already]
        fresh_gone = [k for k in gone if SHOWN_GONE + k not in already]
        held_back = (len(entries) - len(fresh)) + (len(gone) - len(fresh_gone))
        entries, gone = fresh, fresh_gone

    # THE OVERFLOW REPORT IS WRITTEN BEFORE STDOUT, so the pointer printed below
    # can never name a file that is not there yet. Clause 3, and the ordering is
    # the clause's whole point.
    #
    # ONLY WITH A VALIDATED SESSION ID. Without one the pointer is the plain
    # "+k more" and NO file is written - a fire that cannot attribute itself does
    # not get to leave state behind, which is the same fail-open rule the
    # suppression cache follows.
    pointer = ""
    overflow_written = False
    overflow = [e for e in _newest_first(entries)[MAX_LISTED_NAMES:]]
    if overflow and session is not None:
        overflow_written = write_overflow_report(DEFAULT_REPORT, entries, heading)
        if overflow_written:
            pointer = f", listed in full in {DEFAULT_REPORT}"
        else:
            # THE POINTER SAYS SO WITH `UNMEASURED` RATHER THAN NAMING A FILE
            # THAT IS NOT THERE, and the entries beyond the cap are NOT recorded
            # as shown below - both halves of clause 3's last sentence. A pointer
            # to an absent file is worse than no pointer: it sends a reader
            # somewhere empty and they conclude there was nothing to see.
            pointer = f" - {UNMEASURED}, the full listing could not be written"

    # RENDER ONLY WHEN THERE IS SOMETHING TO LIST, ON THE QUIET PATH.
    #
    # THIS FIXES A BUG THAT PREDATES THE SESSION WORK. `gone` used to be in this
    # condition, so a withdrawal-only QUIET fire printed `unread: none` and then
    # the withdrawal block. Two things wrong with that: `unread: none` is the
    # affirmative clean line, which clause 2 forbids beside a report of anything,
    # and `QUIET_SHAPE` in `tests/test_session_hooks.py` rejects it - so shipped
    # behaviour at base e9b4542 could redden that arm, measured. A withdrawal-only
    # quiet fire now prints the withdrawal block and nothing else.
    listed: list[Entry] = []
    if entries or not args.quiet_when_empty:
        listed = _render(entries, heading, pointer)

    # A WITHDRAWAL IS FILED AS AN ANOMALY, NOT AS AN INFORMATIONAL LINE.
    # Sibling-A pulled 50 files from four inboxes in one night and every
    # arrival-keyed watcher on this box reported silence while an entire payload
    # left the channel; two senders then spent a night reasoning about bytes the
    # receiver did not have. It is the only inbox event with no artifact left on
    # disk, so the watcher is the only thing that can say it happened.
    if gone:
        print(f"WITHDRAWN after being shown: {len(gone)}")
        for key in gone:
            print(f"  [gone] {key}")
        print("  (run --mark to acknowledge; they are carried until you do)")

    if unusable is not None:
        # A DEGRADED STATE IN WORDS, NOT A RAW ERROR STRING. `unusable` is one
        # of two labels this module chose; the parse failure itself went to the
        # log inside `read_json`, which is where a reader who wants it can find
        # it. The second line is the actionable half: nothing here repairs the
        # file, and nothing here overwrites it either.
        print(f"the record of what has been shown is unusable - {unusable}")
        print(f"  (it will NOT be rewritten; repair or remove {reported})")
        print("  (withdrawal reporting is incomplete until you do)")

    # EVERYTHING BELOW HAPPENS AFTER STDOUT IS FLUSHED, AND THAT NOW INCLUDES
    # THE REPORT RECORD.
    #
    # Clause 4's exact words are "the reported record is written only AFTER
    # stdout is flushed, so a killed hook re-prints rather than suppresses", and
    # `record_reported` used to run before the flush. The failure direction was
    # benign - that record only feeds `withdrawn`, so an early write can
    # OVER-report a withdrawal and can never swallow mail - but this tree is the
    # one claiming compliance with the clause, and a benign deviation left
    # unstated is still a false claim. Both writes are on the far side of the
    # flush now, so neither can record as shown a line that never left the
    # process.
    #
    # `print` writes into a buffer, which is why the flush is a separate act from
    # having called `print`.
    #
    # WHAT COUNTS AS SHOWN IS `listed`, NOT `entries`, plus the overflow only if
    # its file actually landed - clause 3's "the entries beyond the cap are NOT
    # treated as shown". Recording the full list would suppress on the next fire
    # names this fire never put anywhere a human could read them.
    shown_now = list(listed)
    if overflow_written:
        shown_now.extend(overflow)

    if shown_now or gone:
        sys.stdout.flush()
    if shown_now:
        # Never touches the watermark and never feeds the unread decision.
        record_reported(reported, [entry.key for entry in shown_now])
    # `record_shown` refuses a `None` session on its own, so the fail-open
    # "print and write nothing" rule is enforced there rather than depending on
    # this call site remembering it.
    if suppress and (shown_now or gone):
        record_shown(
            DEFAULT_SESSIONS,
            session,
            [SHOWN_UNREAD + e.key + ":" + e.digest for e in shown_now]
            + [SHOWN_GONE + key for key in gone],
        )

    if args.mark:
        # REFUSED BEFORE EITHER WRITE, NOT BETWEEN THEM. `mark_seen(...) and
        # prune_records(...)` runs the watermark write FIRST, so a prune that
        # failed printed "it stays where it was" about a watermark that had
        # already moved - a true-sounding line about a state that no longer
        # held. Checking here keeps that line honest: on a refusal neither
        # record is touched, and the acknowledge can be retried once the
        # report record is repaired.
        if unusable is not None:
            print("could not read the record of what has been shown - the acknowledge is refused")
            print("  (the watermark stays where it was; nothing was rewritten)")
            return 0, TERMINAL_MARK_FAILED
        # The acknowledge is the deliberate act, so it is what the line says
        # happened. Whether it LANDED is the fact worth keeping: a mark that
        # failed leaves the watermark where it was, and the next session then
        # re-reads a queue somebody believes they cleared.
        if mark_seen(inbox, state) and prune_records(inbox, reported):
            print(f"marked read: {state}")
            return 0, TERMINAL_MARKED
        print("could not update the watermark - it stays where it was")
        return 0, TERMINAL_MARK_FAILED

    if entries:
        return 0, TERMINAL_REPORTED
    if gone:
        return 0, TERMINAL_WITHDRAWN_ONLY
    if held_back:
        # There WAS unread mail and this session had already been told. Saying
        # `nothing-unread` here would be a false line in the one record that
        # exists to say what a fire decided. See `TERMINAL_SUPPRESSED`.
        return 0, TERMINAL_SUPPRESSED
    return 0, TERMINAL_NOTHING_UNREAD


if __name__ == "__main__":
    # `SOURCE_CLI` is what makes a HOOK fire distinguishable in the log from an
    # in-process call, and the hook is the whole question. It is the FALLBACK
    # rather than the value, so a caller that can say who it is - a test
    # harness spawning this script - says so, and a caller that says nothing
    # still records the honest `cli`. Resolved HERE, at the process entry
    # point, rather than inside `log_invocation`: the variable describes how
    # this PROCESS was invoked, and an in-process call already carries an
    # explicit label from its caller that ambient environment must not override.
    #
    # THE THREE-WAY PRECEDENCE IS SPELLED OUT BY THIS ONE LINE, and it reads
    # right to left: `SOURCE_CLI` is what a bare `python scripts/watch_inbox.py`
    # writes, `--source` lets the WIRING say which hook event this is, and
    # `resolve_source` lets the ENVIRONMENT outrank both - which is how the
    # suite tells its own launches of the declared command from a real fire.
    # See `source_from_argv` for why that direction and not the other one.
    #
    # Resolved BEFORE `main` is entered, because `main` writes its `start` line
    # before argv is ever parsed and both lines of one fire must agree.
    # THE SESSION ID IS READ HERE, ONCE, AND FOR THE SAME REASON THE SOURCE
    # LABEL IS. `main` writes its `start` line before the body runs, so both
    # lines of one fire must be handed the same value; and stdin can be consumed
    # exactly once, so a second read anywhere would return nothing and leave the
    # two lines disagreeing - one attributed, one not.
    #
    # READ BEFORE ANYTHING ELSE HAPPENS, and bounded in TIME as well as in bytes.
    # See `STDIN_WAIT_SECONDS` for why an unbounded read on this path kills mail
    # announcements silently - it was shipped that way once and measured hanging
    # past 25 seconds under a hook declared with a five second ceiling.
    raise SystemExit(
        main(
            source=resolve_source(source_from_argv(sys.argv[1:]) or SOURCE_CLI),
            session=validated_session_id(),
        )
    )
