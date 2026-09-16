"""Guards for the WATCHER CONTRACT clauses `scripts/watch_inbox.py` adopted.

WHERE THE CONTRACT CAME FROM. RC shipped `docs/CHANNEL.md` v1 on 2026-09-15,
whose section 5 carries a six-clause fleet contract that all five watchers on
this channel are graded against. RC's covering note named four changes for this
tree by role, and the three this module guards are:

  a BOUNDED stdin reader, because this watcher reads no stdin at all today and
  the payload carrying the session id arrives on it;

  per-session suppression of already-shown entries on the `--quiet-when-empty`
  path, because that hook fires on EVERY prompt and re-printed the same unread
  note on every one of them;

  a session id COLUMN in the invocation log, sanitised exactly the way the
  entry-point label already is.

WHY THE STDIN READER IS THE RISKIEST EDIT IN THE SET, and it is RC's word
rather than this module's. `.claude/settings.json` wires this script as a
`UserPromptSubmit` hook with a five second timeout on every prompt. A read that
blocks kills mail announcements SILENTLY - the hook is simply killed, its stdout
is dropped, and nothing anywhere records that it had something to say. So the
reader is bounded on two independent axes and both are armed below: a byte
budget, and a SINGLE `os.read` that is never looped.

THE INTERACTIVE CASE IS THE ONE THAT BITES FIRST, and it is not the hook at all.
`python scripts/watch_inbox.py` typed at a terminal has stdin attached to the
TERMINAL, where a read blocks until the operator types something and presses
return. The documented CLI usage would hang. `test_a_terminal_stdin_is_not_read_
at_all` is that arm, and it is the reason the reader tests `isatty` before it
tests anything else.

FAIL OPEN IS THE DIRECTION EVERYWHERE IN HERE. No session id means print and
write nothing; an unreadable suppression cache means print; a truncated or
undecodable payload means print. Every degraded path costs one duplicate line
on screen and none of them can lose a note. That polarity is the OPPOSITE of
`_reported_record`'s deliberate fail-CLOSED, and the difference is not an
inconsistency - see `test_the_session_cache_is_not_a_second_reported_record`.
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "watch_inbox.py"


@pytest.fixture()
def watch(tmp_path):
    """The module under test, with every `DEFAULT_` Path redirected.

    DISCOVERED RATHER THAN LISTED, for the reason `tests/test_watch_inbox.py`
    records at length: a hand-maintained list of things to isolate goes stale
    the moment somebody adds the next one, and it fails silently because the arm
    that would catch it IS the list. This module adds a fifth such path, and it
    inherits the isolation by shape rather than by anybody remembering.
    """
    spec = importlib.util.spec_from_file_location("watch_inbox_session_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _note(inbox: Path, name: str, body: str = "body\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def _log_lines(watch) -> list[str]:
    target = Path(watch.DEFAULT_INVOCATIONS)
    if not target.is_file():
        return []
    return [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]


class _FakeStdin:
    """A stdin that is not a terminal and hands out ONE chunk, then EOF.

    `fileno` RAISES, DELIBERATELY. The reader must reach a real file descriptor
    or give up, and a fake that supplied a plausible integer would be testing
    `os.read` against some other process's fd. Every arm that needs a real
    descriptor uses a real file instead - see `_fd_stdin`.
    """

    def __init__(self, tty: bool) -> None:
        self._tty = tty
        self.read_calls = 0

    def isatty(self) -> bool:
        return self._tty

    def fileno(self) -> int:
        self.read_calls += 1
        raise OSError("no descriptor")


class _FakeStdinWithFd:
    """A non-terminal stdin handing out a fixed descriptor number.

    Paired with a monkeypatched `os.read`, so the number is never dereferenced.
    That is what lets the wait arms measure the WAIT rather than some platform's
    pipe semantics - and it is why they cannot hang the suite the way an
    undrained real pipe already did once here.
    """

    def __init__(self, fd: int) -> None:
        self._fd = fd

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return self._fd


# ---------------------------------------------------------------------------
# ITEM 1 - THE BOUNDED STDIN READER
# ---------------------------------------------------------------------------


def test_the_budget_is_a_named_constant_and_is_actually_small(watch):
    """A budget nobody can find is a budget the next reader raises by accident.

    Asserted against LITERAL bounds rather than against itself, so a mutation
    that sets the constant to a megabyte goes red here. The upper bound is the
    load-bearing half: the point of the constant is that it is SMALL.
    """
    assert isinstance(watch.MAX_STDIN_BYTES, int)
    assert 1024 <= watch.MAX_STDIN_BYTES <= 1 << 18, (
        f"the stdin budget is {watch.MAX_STDIN_BYTES}, which is not a small "
        "bounded read on a hook that fires before every prompt"
    )


def test_a_terminal_stdin_is_not_read_at_all(watch, monkeypatch):
    """THE HANG ARM, and the first thing that would have broken in practice.

    A documented CLI usage - `python scripts/watch_inbox.py` at a prompt - has
    stdin attached to the terminal. A read there blocks until somebody types.
    So `isatty` is consulted BEFORE a descriptor is ever asked for, and this arm
    proves the order rather than the outcome: the fake counts how many times
    anything asked it for a descriptor, and the answer must be zero.
    """
    fake = _FakeStdin(tty=True)
    monkeypatch.setattr(watch.sys, "stdin", fake)

    assert watch._read_stdin_budget() == b""
    assert fake.read_calls == 0, (
        "a terminal stdin was read from. That blocks until the operator types, "
        "and the blocked process is the documented CLI usage"
    )


def test_an_absent_stdin_is_not_a_traceback(watch, monkeypatch):
    monkeypatch.setattr(watch.sys, "stdin", None)
    assert watch._read_stdin_budget() == b""
    assert watch.validated_session_id() is None


def test_a_stdin_without_a_descriptor_is_not_a_traceback(watch, monkeypatch):
    """pytest's own capture replaces stdin with an object that has no fd.

    So this is the case EVERY in-process arm in this suite already runs under,
    and it must be silent rather than an exception.
    """
    monkeypatch.setattr(watch.sys, "stdin", _FakeStdin(tty=False))
    assert watch._read_stdin_budget() == b""


def _fd_stdin(monkeypatch, watch, tmp_path: Path, payload: bytes):
    """Give the module a REAL file descriptor as stdin, pre-loaded with `payload`.

    A real descriptor is the only thing that exercises the `os.read` call at all.

    A FILE AND NOT AN `os.pipe`, AND THAT IS A MEASURED CORRECTION. The first
    version of this helper wrote the payload into a pipe and closed the write
    end, which reads naturally and DEADLOCKS: an OS pipe buffer is finite - tens
    of kilobytes on this box - and `os.write` blocks once it is full until a
    reader drains it. There is no reader yet, so the over-budget payload in
    `test_the_read_is_capped_at_the_budget` hung the whole suite with no output
    at all, and it had to be killed with `taskkill`. A regular file has no such
    buffer, returns EOF at its end exactly as a closed pipe does, and gives the
    same single-`os.read` semantics this reader depends on.

    The file is left in `tmp_path` and the descriptor is left open for pytest to
    tear down with the directory: closing it here would race the reader.
    """
    import os

    target = tmp_path / f"stdin-{len(payload)}.json"
    target.write_bytes(payload)
    fd = os.open(str(target), os.O_RDONLY | getattr(os, "O_BINARY", 0))

    class _Real:
        def isatty(self) -> bool:
            return False

        def fileno(self) -> int:
            return fd

    monkeypatch.setattr(watch.sys, "stdin", _Real())
    return fd


def test_a_real_descriptor_is_read_and_its_session_id_validated(watch, monkeypatch, tmp_path):
    """THE POSITIVE CONTROL. Every refusal arm below is vacuous without it."""
    payload = json.dumps(
        {"session_id": "ab12cd34-5678-90ef-ab12-cd345678", "hook_event_name": "UserPromptSubmit"}
    ).encode("ascii")
    _fd_stdin(monkeypatch, watch, tmp_path, payload)

    assert watch.validated_session_id() == "ab12cd34-5678-90ef-ab12-cd345678"


def test_the_read_is_capped_at_the_budget(watch, monkeypatch, tmp_path):
    """A payload past the budget comes back TRUNCATED, not whole.

    The truncated bytes are not valid JSON, so the session id is None and the
    fire falls back to printing. That is the accepted cost of a bounded read and
    it is asserted rather than assumed.
    """
    payload = b'{"session_id": "s1", "prompt": "' + b"x" * (watch.MAX_STDIN_BYTES * 2) + b'"}'
    _fd_stdin(monkeypatch, watch, tmp_path, payload)

    raw = watch._read_stdin_budget()
    assert len(raw) <= watch.MAX_STDIN_BYTES, (
        f"read {len(raw)} bytes against a declared budget of {watch.MAX_STDIN_BYTES}"
    )
    assert watch.session_id_from_payload(raw) is None, (
        "a truncated payload parsed anyway, so the JSON reader is not strict"
    )


def test_the_wait_is_a_named_constant_well_under_the_hook_ceiling(watch):
    """The bound that actually matters, asserted against literals.

    The hook is declared with a five second timeout. A wait anywhere near that
    is not a bound, it is the same silent death with extra steps.
    """
    assert isinstance(watch.STDIN_WAIT_SECONDS, (int, float))
    assert 0 < watch.STDIN_WAIT_SECONDS <= 1.0, (
        f"the stdin wait is {watch.STDIN_WAIT_SECONDS}s against a declared hook "
        "ceiling of 5s; that is not a tenfold margin"
    )


def test_a_stdin_that_never_arrives_returns_inside_the_wait(watch, monkeypatch):
    """THE HANG ARM, AND THE HANG WAS REAL AND WAS SHIPPED ONCE.

    The first version of this reader was one un-timed `os.read`, argued bounded
    on the grounds that it did not loop. It is not: `os.read` on a pipe blocks
    until bytes arrive or every write handle closes, and a parent holding the
    pipe open satisfies neither. Reproduced at over 25 seconds and killed with
    `taskkill`. Under the hook's five second timeout that is a hook killed on
    every prompt, with its stdout dropped by the harness - a watcher that dies
    silently rather than one that says nothing.

    ASSERTED ON ELAPSED TIME, which is the only thing that distinguishes the
    broken version from the fixed one: both return `b""` eventually.

    A DESCRIPTOR THAT NEVER YIELDS, WITHOUT NEEDING A PIPE. `os.read` is replaced
    with a sleep longer than the wait, so the arm measures the WAIT rather than
    any platform's pipe semantics - and it cannot itself hang the suite the way
    an undrained real pipe already did once in this module's history.
    """
    import time as _time

    slept: list[float] = []

    def never(fd: int, size: int) -> bytes:
        slept.append(size)
        _time.sleep(30.0)
        return b"too late"

    monkeypatch.setattr(watch.os, "read", never)
    monkeypatch.setattr(watch.sys, "stdin", _FakeStdinWithFd(0))

    started = _time.monotonic()
    got = watch._read_stdin_budget()
    elapsed = _time.monotonic() - started

    assert slept, "os.read was never called, so nothing was being waited on"
    assert got == b"", f"a payload that never arrived was returned anyway: {got!r}"
    assert elapsed < watch.STDIN_WAIT_SECONDS + 1.5, (
        f"the reader took {elapsed:.2f}s against a declared wait of "
        f"{watch.STDIN_WAIT_SECONDS}s. An unbounded read here kills the hook at "
        "its five second ceiling and the harness DROPS the stdout, so the "
        "failure is silent"
    )


def test_a_payload_that_arrives_late_but_inside_the_wait_is_still_read(watch, monkeypatch):
    """THE SURVIVING-NEIGHBOUR HALF OF THE ARM ABOVE.

    The arm above passes for a reader that always returns `b""` immediately. This
    one fails for that reader, so between them they pin "waits, but not forever".

    WHAT THIS ARM DOES NOT PROVE, corrected after it was over-cited once. It was
    described as discriminating this design from the rejected `os.set_blocking`
    and `PeekNamedPipe` variants, on the grounds that both peek and so lose to a
    parent that writes late. That reasoning is sound about the DESIGNS and this
    arm does not test it: the arm patches `os.read` itself, so a peek-based
    reader that called the patched `os.read` after a successful readiness check
    would pass here too. Discriminating those variants needs a real descriptor
    and a real writer, which is what the probe in the commit message measured and
    what no in-process arm here does.

    The hang itself is killed by `test_a_stdin_that_never_arrives_returns_inside_
    the_wait`, not by this.
    """
    import time as _time

    def late(fd: int, size: int) -> bytes:
        _time.sleep(0.05)
        return b'{"session_id": "late1"}'

    monkeypatch.setattr(watch.os, "read", late)
    monkeypatch.setattr(watch.sys, "stdin", _FakeStdinWithFd(0))

    assert watch.validated_session_id() == "late1", (
        "a payload that arrived 50ms after the read began was lost, so this is a "
        "peek and not a wait"
    )


def test_the_reader_issues_exactly_one_os_read(watch, monkeypatch, tmp_path):
    """THE UNBOUNDED-WAIT ARM, and it is about the LOOP rather than the budget.

    `os.read` returns as soon as ANY bytes are available. A loop that drained
    until the budget was full - or until EOF - would wait on a writer that has
    not written yet, which is the unbounded read this whole design exists to
    refuse. The byte budget does not prevent that; only not looping does.

    So the count is asserted, not the bytes.
    """
    import os

    calls: list[int] = []
    real_read = os.read

    def counted(fd: int, size: int) -> bytes:
        calls.append(size)
        return real_read(fd, size)

    _fd_stdin(monkeypatch, watch, tmp_path, b'{"session_id": "s1"}')
    monkeypatch.setattr(watch.os, "read", counted)

    watch._read_stdin_budget()

    assert len(calls) == 1, (
        f"the reader issued {len(calls)} reads. More than one means it is "
        "draining, and a drain waits on a writer that may never write - which "
        "is exactly the blocked hook this budget cannot save"
    )
    assert calls == [watch.MAX_STDIN_BYTES]


#: Payloads that must yield NO session id, each with the reason it is here.
#: Control bytes are built with `chr()` rather than typed, because this tree is
#: 7-bit ASCII by rule and a literal tab or newline in a source string is
#: exactly the forgery these arms exist to refuse.
_REFUSED_PAYLOADS = (
    (b"", "an empty payload - a closed or absent stdin"),
    (b"   ", "whitespace only"),
    (b"not json at all", "a non-JSON body"),
    (b"[1, 2, 3]", "valid JSON that is not an object"),
    (b'"a string"', "valid JSON that is not an object"),
    (b"{}", "an object with no session id at all"),
    (b'{"session_id": null}', "a null session id"),
    (b'{"session_id": 17}', "a session id that is not a string"),
    (b'{"session_id": ""}', "an empty session id leaves the column blank"),
    (b'{"session_id": "   "}', "whitespace leaves the column blank"),
    (b'{"session_id": "-leading"}', "a session id must start with something nameable"),
    (b'{"session_id": "' + b"x" * 500 + b'"}', "an unbounded id is an unbounded line"),
    (b"\xff\xfe\x00bad", "bytes the UTF-8 decoder cannot take"),
)


@pytest.mark.parametrize("raw,why", _REFUSED_PAYLOADS)
def test_a_payload_that_carries_no_usable_session_id_is_refused(watch, raw, why):
    assert watch.session_id_from_payload(raw) is None, why


#: The two control bytes that would FORGE a record in a tab-separated,
#: line-oriented log. Assembled with `chr()` for the reason above.
_FORGED_SESSION_IDS = (
    ("s1" + chr(9) + "reported", "a tab forges the disposition column"),
    (
        "s1" + chr(10) + "2026-01-01T00:00:00" + chr(9) + "cli" + chr(9) + "s2",
        "a newline forges a whole line, timestamp and all",
    ),
    ("s1" + chr(13) + "x", "a carriage return is a line break to some readers"),
)


@pytest.mark.parametrize("forged,why", _FORGED_SESSION_IDS)
def test_a_hostile_session_id_cannot_forge_a_log_record(watch, forged, why):
    """The session id is the SECOND field this module does not choose.

    It arrives on stdin from a harness this tree does not control, and it is
    written into a record that is TAB separated and LINE oriented and capped at
    `MAX_INVOCATION_LINES`. A newline in it fabricates a whole row - timestamp,
    entry point, disposition - which is a forged answer to the one question the
    log exists to answer.

    REFUSED RATHER THAN TRIMMED INTO SHAPE, following `resolve_source`: a
    silently repaired id is an id nobody can trace back to a session.
    """
    raw = json.dumps({"session_id": forged}).encode("utf-8")
    assert watch.session_id_from_payload(raw) is None, why


@pytest.mark.parametrize(
    "legitimate",
    (
        "ab12cd34-5678-90ef-ab12-cd345678",
        "s1",
        "A1",
        "session.2",
        "run_once",
        "0",
    ),
)
def test_a_legitimate_session_id_survives(watch, legitimate):
    """THE SURVIVING-NEIGHBOUR HALF.

    A validator that refused everything would satisfy every refusal arm above
    perfectly, and the whole feature would silently degrade to fail-open on
    every fire - which looks exactly like the defect it was built to fix.
    """
    raw = json.dumps({"session_id": legitimate}).encode("ascii")
    assert watch.session_id_from_payload(raw) == legitimate


# ---------------------------------------------------------------------------
# ITEM 4 - THE SESSION COLUMN IN THE INVOCATION LOG
# ---------------------------------------------------------------------------


def test_every_logged_line_carries_four_columns_with_the_session_third(watch, tmp_path):
    """THE COLUMN ORDER IS LOAD-BEARING AND THE SESSION GOES IN THE MIDDLE.

    `tests/test_session_hooks.py` reads the disposition as `split(chr(9))[-1]`
    and the entry point as `[1]`. Appending the session at the END would make
    `[-1]` the session id, so two arms in a module this slice does not own
    would go red - and they would go red while reporting something that reads
    like a disposition defect. Inserted third, both readers keep their meaning
    and the line still ends with what came of the fire.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    watch.main(
        ["--dir", str(inbox), "--state", str(tmp_path / "seen.json")],
        session="ab12cd34",
    )

    lines = _log_lines(watch)
    assert len(lines) == 2, f"expected a start and one terminal, got {lines}"
    for line in lines:
        fields = line.split(chr(9))
        assert len(fields) == 4, f"expected stamp, source, session, disposition: {line!r}"
        time.strptime(fields[0], "%Y-%m-%dT%H:%M:%S")
        assert fields[1], f"the entry point column is empty: {line!r}"
        assert fields[2] == "ab12cd34", f"the session column is wrong: {line!r}"
        assert fields[3], f"the disposition column is empty: {line!r}"
    assert lines[0].split(chr(9))[-1] == watch.PHASE_START, (
        "the last column is no longer the disposition, which is what the "
        "session-hooks module parses it as"
    )


def test_an_absent_session_leaves_a_placeholder_not_an_empty_column(watch, tmp_path):
    """An empty column collapses the record for a naive splitter.

    A fire with no session id is the NORMAL case for a manual run and for every
    end-to-end arm that launches this script with stdin closed, so it must
    produce a well-formed four-column line rather than a ragged one.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json")])

    lines = _log_lines(watch)
    assert lines, "nothing was logged, so this arm is vacuous"
    for line in lines:
        fields = line.split(chr(9))
        assert len(fields) == 4, f"a fire with no session id left a ragged line: {line!r}"
        assert fields[2] == watch.SESSION_ABSENT
        assert fields[2].strip(), "the session column is blank rather than a placeholder"


def test_a_hostile_session_id_reaching_the_logger_directly_is_still_refused(watch, tmp_path):
    """DEFENCE AT THE WRITE, not only at the parse.

    `session_id_from_payload` is the gate today, but it is not the only way a
    value can reach `log_invocation` - a later caller could pass one straight
    in. The log line is where the damage happens, so the refusal is asserted
    where the bytes are written and the ARM does not depend on the parser.
    """
    watch.log_invocation("cli", "reported", session="s1" + chr(10) + "forged\tline\there")

    lines = _log_lines(watch)
    assert len(lines) == 1, (
        f"a newline in the session id fabricated {len(lines)} lines out of one "
        f"fire: {lines}"
    )
    assert lines[0].split(chr(9))[2] == watch.SESSION_ABSENT


# ---------------------------------------------------------------------------
# ITEM 5 - THE RENDER-EVERY-FIRE ARM, RE-ARMED
#
# RC's note says a test arm pins render-every-fire and that WHICH one is
# unverified from RC's side. Measured in this tree instead, at
# e9b454218253f205a2d050ab8e2561656b790f20: NO arm pinned it. The closest two
# are `test_reporting_never_advances_the_watermark`, which fires `main` three
# times and asserts only on the WATERMARK's bytes, and
# `test_reporting_is_idempotent_and_does_not_even_touch_the_state_file`, which
# calls `survey` twice and never goes near stdout. Both stay true under
# per-session suppression, because neither says anything about what is printed.
#
# So there was nothing to re-arm and the property was simply UNGUARDED - which
# is worse than a wrong arm, because it means the old behaviour was never a
# decision. The two arms below state it in both directions now.
# ---------------------------------------------------------------------------


def test_without_a_session_id_the_quiet_path_re_prints_on_every_fire(watch, tmp_path, capsys):
    """FAIL OPEN, and this is the arm the contract names explicitly.

    No session id means print and write nothing. It is also the behaviour every
    end-to-end arm in `tests/test_session_hooks.py` runs under, because those
    launch the declared command with stdin closed.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv)
    first = capsys.readouterr().out
    watch.main(argv)
    second = capsys.readouterr().out

    assert "a.md" in first, "the first fire said nothing, so this arm is vacuous"
    assert "a.md" in second, (
        "a second fire with NO session id suppressed the note. Fail open is the "
        "contract: without an id there is nothing to scope suppression to, and "
        "silently swallowing mail is the failure the watcher exists to prevent"
    )
    assert not Path(watch.DEFAULT_SESSIONS).exists(), (
        "a fire with no session id wrote the suppression cache anyway, so the "
        "next fire would suppress against a key nobody can attribute"
    )


def test_the_same_entry_is_shown_once_per_validated_session(watch, tmp_path, capsys):
    """CLAUSE 4. The per-prompt hook fires on EVERY prompt.

    Before this, an unread note re-printed into the session context on every
    single prompt for as long as it stayed unread - and since acknowledging is a
    separate deliberate act, that is potentially forever. The contract's own
    corollary says it plainly: anything that adds notes adds PERMANENT text in
    every recipient.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    first = capsys.readouterr().out
    watch.main(argv, session="sess1")
    second = capsys.readouterr().out

    assert "a.md" in first, "the first fire said nothing, so the silence below proves nothing"
    assert second == "", f"the second fire in the same session re-printed: {second!r}"


def test_a_different_session_sees_the_note_again(watch, tmp_path, capsys):
    """The suppression is SCOPED, and a new session is a new reader.

    A cache that suppressed globally would be an acknowledgement wearing a
    cache's name, and it would silence the operator's next session over a note
    a subagent's session happened to print once.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    capsys.readouterr()
    watch.main(argv, session="sess2")

    assert "a.md" in capsys.readouterr().out, (
        "a second session was suppressed by the first one's cache, which makes "
        "the cache a global acknowledgement"
    )


def test_a_changed_digest_shows_once_more_in_the_same_session(watch, tmp_path, capsys):
    """CLAUSE 4's second sentence: a new name or a CHANGED DIGEST shows once.

    This is the case the whole channel keys on content for. RULING then ADDENDUM
    then CORRECTION is routine here, and a correction lands as an in-place edit
    of the same filename. Suppressing on the NAME would swallow exactly the
    message that most needed reading, inside the session that had already been
    told about the earlier version.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", "first\n")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    assert "a.md" in capsys.readouterr().out, "the first version never printed"

    watch.main(argv, session="sess1")
    assert capsys.readouterr().out == "", "the unchanged note re-printed, so the arm below is moot"

    _note(inbox, "a.md", "CORRECTION\n")
    watch.main(argv, session="sess1")

    assert "a.md" in capsys.readouterr().out, (
        "an in-place CORRECTION was suppressed inside the session that had seen "
        "the earlier version. The channel sends corrections as a matter of "
        "course and this is the one entry that must not be swallowed"
    )


def test_a_withdrawal_is_a_separate_event_from_the_note_it_is_about(watch, tmp_path, capsys):
    """THE NAMESPACE ARM, and it is the bug a single flat key set would have.

    A note is shown as UNREAD, then the sender pulls it. Both events are about
    the same bare name, so a suppression cache keyed on the name alone would
    score the withdrawal as already shown and stay silent - losing the one inbox
    event that leaves NO artifact on disk to notice later.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    reported = tmp_path / "reported.json"
    argv = [
        "--dir", str(inbox), "--state", str(state), "--reported", str(reported),
        "--quiet-when-empty",
    ]

    watch.main(argv, session="sess1")
    assert "a.md" in capsys.readouterr().out, "the note never printed as unread"

    (inbox / "a.md").unlink()
    watch.main(argv, session="sess1")
    out = capsys.readouterr().out

    assert "WITHDRAWN" in out, (
        "the withdrawal of a note already shown as unread was suppressed. The "
        "two are different events about one name, so the cache must namespace "
        "them rather than hold bare keys"
    )
    assert "a.md" in out


def test_a_withdrawal_is_itself_shown_only_once_per_session(watch, tmp_path, capsys):
    """The other half of clause 4. A withdrawal is CARRIED until `--mark`.

    Carried means it re-derives on every fire forever, which on a per-prompt
    hook is the same permanent-text problem as an unread note.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    reported = tmp_path / "reported.json"
    watch.mark_seen(inbox, state)
    (inbox / "a.md").unlink()
    argv = [
        "--dir", str(inbox), "--state", str(state), "--reported", str(reported),
        "--quiet-when-empty",
    ]

    watch.main(argv, session="sess1")
    assert "WITHDRAWN" in capsys.readouterr().out, "no withdrawal was reported at all"

    watch.main(argv, session="sess1")
    assert capsys.readouterr().out == "", "the withdrawal re-printed in the same session"


def test_suppression_does_not_reach_the_session_start_path(watch, tmp_path, capsys):
    """SUPPRESSION IS FOR THE PER-PROMPT HOOK AND FOR NOTHING ELSE.

    `SessionStart` fires once per session, so there is nothing for suppression
    to save there - and a suppressed session-start report is a session that
    begins blind, which is the exact failure the whole tool was built for. The
    same goes for a deliberate manual run and for `--all`.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"

    quiet = ["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"]
    watch.main(quiet, session="sess1")
    assert "a.md" in capsys.readouterr().out, "the quiet fire printed nothing to suppress"

    for mode in ([], ["--all"]):
        watch.main(["--dir", str(inbox), "--state", str(state), *mode], session="sess1")
        assert "a.md" in capsys.readouterr().out, (
            f"the {mode or ['(bare)']} path was suppressed by the quiet path's cache. A "
            "session start that says nothing is a session that begins blind"
        )


# ---------------------------------------------------------------------------
# WHERE THE PER-SESSION STATE LIVES, AND WHY IT IS NOT THE REPORTED FILE
# ---------------------------------------------------------------------------


def test_the_session_cache_lives_under_the_runtime_directory(watch, monkeypatch):
    """NEVER UNDER AppData, and this is a MEASURED machine-level trap.

    RC measured it on 2026-09-15 on its own poller state: anything a hook or
    tool writes under `%LOCALAPPDATA%` or `%APPDATA%` while carrying the Claude
    desktop app's MSIX package identity lands in the package's LocalCache TWIN,
    and every later read from that harness returns the twin - silently, with no
    error and no permission failure. A months-old shadow was being read by every
    harness shell while the live task rewrote the real file on every poll. REPO
    ROOTS ARE NOT VIRTUALISED.

    So the cache joins the one contract this module already has for runtime
    records rather than standing a second one beside it. Asserted on the
    UNREDIRECTED module, because the fixture rewrites every `DEFAULT_` path and
    would make this arm a statement about `tmp_path`.
    """
    spec = importlib.util.spec_from_file_location("watch_inbox_live_paths", SCRIPT)
    assert spec is not None and spec.loader is not None
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)

    target = live.DEFAULT_SESSIONS
    assert target.parent == live.RUNTIME_DIR, (
        f"{target} is not under the runtime directory {live.RUNTIME_DIR}"
    )
    lowered = str(target).lower()
    for banned in ("appdata", "localcache", "packages"):
        assert banned not in lowered, (
            f"the suppression cache resolves inside {banned!r} ({target}). Under "
            "the desktop harness that path is shadowed by an MSIX LocalCache "
            "twin and every later read returns the twin, silently"
        )


def test_the_session_cache_is_not_a_second_reported_record(watch, tmp_path, capsys):
    """THREE RECORDS, THREE JOBS, AND THE BASELINE MUST NOT MOVE.

    `withdrawn` unions `read_reported()` into its baseline by design - Sibling-D's
    correction, because a note LISTED at session start and pulled before anyone
    acknowledged lives in the report record only. So writing per-session keys
    into that file would inject them into the WITHDRAWAL baseline, and every
    namespaced cache key would re-derive as a withdrawn note on the next fire.

    This arm asserts the separation on the BYTES of both other records.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    reported = tmp_path / "reported.json"
    watch.mark_seen(inbox, state)
    _note(inbox, "b.md")
    argv = [
        "--dir", str(inbox), "--state", str(state), "--reported", str(reported),
        "--quiet-when-empty",
    ]

    watch.main(argv, session="sess1")
    capsys.readouterr()

    watermark = state.read_bytes()
    shown = json.loads(reported.read_text(encoding="utf-8"))
    cache = json.loads(Path(watch.DEFAULT_SESSIONS).read_text(encoding="utf-8"))

    assert "b.md" in shown["reported"], "the report record did not record what was shown"
    assert cache != shown, "the two records are the same payload under two names"
    for key in cache["sessions"][0]["shown"]:
        assert key not in shown["reported"], (
            f"the namespaced cache key {key!r} leaked into the report record, "
            "which is the withdrawal baseline"
        )

    watch.main(argv, session="sess2")
    assert state.read_bytes() == watermark, (
        "SHOWING NEVER ACKNOWLEDGES. The per-session layer moved the watermark"
    )


def test_the_cache_never_writes_the_seen_store_even_when_it_is_the_only_write(
    watch, tmp_path, capsys
):
    """CLAUSE 5, asserted on the state file's MTIME as well as its bytes.

    An atomic write producing identical content still moves the modification
    time, so bytes-equal is a weaker claim than did-not-write and this tree has
    already been bitten by the difference once.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    watch.mark_seen(inbox, state)
    _note(inbox, "b.md")
    argv = ["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"]

    before_bytes = state.read_bytes()
    before_mtime = state.stat().st_mtime_ns

    for session in ("sess1", "sess1", "sess2"):
        watch.main(argv, session=session)
        capsys.readouterr()

    assert Path(watch.DEFAULT_SESSIONS).is_file(), "the cache was never written, so this is vacuous"
    assert state.read_bytes() == before_bytes
    assert state.stat().st_mtime_ns == before_mtime, (
        "the watermark's bytes are unchanged but it was written again"
    )


def test_the_cache_is_written_only_after_stdout_is_flushed(watch, tmp_path, capsys):
    """CLAUSE 4's last sentence, and it is about a KILLED hook.

    This hook is declared with a five second ceiling. If the cache were written
    first and the process were then killed before its output reached the
    session, the entry would be recorded as shown having never been seen by
    anybody - a note silently swallowed, which is the one outcome worse than a
    duplicate. Writing after the flush makes a killed fire RE-PRINT instead.

    Asserted on the ORDER of the two operations rather than on an outcome,
    because the outcome of the safe ordering and of the unsafe one are identical
    on any fire that is not killed.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    order: list[str] = []

    real_write = watch.atomic_write_json

    def traced(path, payload):
        order.append(f"write:{Path(path).name}")
        return real_write(path, payload)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(watch, "atomic_write_json", traced)
    monkey.setattr(
        watch.sys.stdout, "flush", lambda: order.append("flush"), raising=False
    )
    try:
        watch.main(
            ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"],
            session="sess1",
        )
    finally:
        monkey.undo()
    capsys.readouterr()

    cache = f"write:{Path(watch.DEFAULT_SESSIONS).name}"
    assert cache in order, f"the cache was never written: {order}"
    assert "flush" in order, f"stdout was never flushed: {order}"
    assert order.index("flush") < order.index(cache), (
        f"the cache was written before stdout was flushed: {order}. A hook "
        "killed at its five second ceiling would then have recorded as SHOWN "
        "something no human ever saw"
    )


def test_the_reported_record_is_also_written_only_after_stdout_is_flushed(
    watch, tmp_path, capsys
):
    """CLAUSE 4'S LITERAL SUBJECT, AND IT IS THE `reported` FILE IT NAMES.

    The clause says "the reported record is written only AFTER stdout is flushed,
    so a killed hook re-prints rather than suppresses". The arm above pins the
    per-session CACHE, which is this tree's own addition; the record the clause
    actually names is `inbox_reported.json`, and moving it after the flush was
    claimed in a commit message with NO GUARD BEHIND IT. An adversary swapped it
    back to its pre-fix position and the whole suite was byte-identical in its
    results - the mutant survived completely, because `inbox_reported.json`
    appeared in no ordering assertion anywhere in `tests/`.

    That is the same class of defect as a constant shipping without an arm, in
    the same commit as the fix for one.

    WHY THE ORDER MATTERS HERE TOO, even though this record is gentler than the
    cache. `record_reported` feeds `withdrawn`'s baseline, so an early write can
    only OVER-report a withdrawal and can never swallow mail - the failure
    direction is safe. It is still a fleet contract this tree claims compliance
    with, and a benign deviation left unguarded is how a later refactor makes it
    non-benign without anybody noticing.

    ASSERTED ON THE CALL ORDER, because both orderings produce identical state on
    any fire that is not killed.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    reported = tmp_path / "isolated-reported.json"
    order: list[str] = []
    real_json = watch.atomic_write_json

    def traced(path, payload):
        order.append(f"write:{Path(path).name}")
        return real_json(path, payload)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(watch, "atomic_write_json", traced)
    monkey.setattr(watch.sys.stdout, "flush", lambda: order.append("flush"), raising=False)
    try:
        watch.main(
            ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"),
             "--reported", str(reported), "--quiet-when-empty"],
            session="sess1",
        )
    finally:
        monkey.undo()
    capsys.readouterr()

    assert reported.is_file(), f"the reported record was never written: {order}"
    written = f"write:{reported.name}"
    assert written in order, (
        f"the reported-record write was not observed at all, so this arm is "
        f"vacuous: {order}"
    )
    assert "flush" in order, f"stdout was never flushed: {order}"
    assert order.index("flush") < order.index(written), (
        f"the reported record was written BEFORE stdout was flushed: {order}. A "
        "hook killed at its five second ceiling would then have recorded as shown "
        "something no human ever saw, which is exactly what clause 4 orders these "
        "two writes to prevent"
    )


def test_an_unreadable_cache_re_prints_rather_than_suppressing(watch, tmp_path, capsys):
    """FAIL OPEN HERE, WHICH IS THE OPPOSITE POLARITY TO `_reported_record`.

    That helper fails CLOSED on purpose: a caller that spliced an unreadable
    report record with new data and wrote it back would DELETE history. This
    file holds no history. It is a suppression CACHE whose entire content is
    reconstructible from the next fire, and the worst consequence of losing it
    is one duplicate line on screen. Failing closed here would instead mean a
    stray byte in a cache file could silence real mail, which is the inversion
    that matters.

    Both polarities are correct and they are not the same rule. This arm exists
    so a later reader cannot "finish the fix" by tightening the wrong half.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    assert "a.md" in capsys.readouterr().out, "nothing printed, so the corruption below is moot"

    cache = Path(watch.DEFAULT_SESSIONS)
    assert cache.is_file(), "no cache to corrupt"
    cache.write_bytes(b"{ this is not json")

    watch.main(argv, session="sess1")
    assert "a.md" in capsys.readouterr().out, (
        "an unreadable suppression cache silenced real mail. A cache that cannot "
        "be read must not suppress"
    )


def test_the_cache_does_not_grow_without_a_bound(watch, tmp_path, capsys):
    """One row per session, on a file rewritten by a hook that fires constantly.

    Bounded for the same reason `MAX_INVOCATION_LINES` is: a record nobody
    prunes, written on every prompt, is a file that grows for as long as the
    tree is used. The NEWEST sessions are kept, because the only session whose
    suppression matters is the one now running.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    assert 1 <= watch.MAX_TRACKED_SESSIONS <= 512, (
        f"the session cap is {watch.MAX_TRACKED_SESSIONS}, which is not a bound"
    )
    for i in range(watch.MAX_TRACKED_SESSIONS + 5):
        watch.main(argv, session=f"s{i}")
        capsys.readouterr()

    rows = json.loads(Path(watch.DEFAULT_SESSIONS).read_text(encoding="utf-8"))["sessions"]
    assert len(rows) == watch.MAX_TRACKED_SESSIONS, (
        f"{len(rows)} rows against a cap of {watch.MAX_TRACKED_SESSIONS}"
    )
    assert rows[-1]["id"] == f"s{watch.MAX_TRACKED_SESSIONS + 4}", (
        "the newest session is not the one retained, so the running session is "
        "the one whose suppression gets dropped"
    )


# ---------------------------------------------------------------------------
# THE SUPPRESSED DISPOSITION - A CONSTANT THAT SHIPPED WITH NO ARM
#
# `TERMINAL_SUPPRESSED` was added with a docstring arguing that an invisible
# suppression is indistinguishable from swallowed mail, and then no test
# anywhere emitted it - zero grep hits across tests/. An adversary mutated
# `return 0, TERMINAL_SUPPRESSED` to `TERMINAL_NOTHING_UNREAD` and the mutant
# SURVIVED the whole suite. The exact property the constant was added for was
# the one left unguarded, which is the sharpest version of this mistake.
# ---------------------------------------------------------------------------


def test_a_suppressed_fire_says_suppressed_and_not_nothing_unread(watch, tmp_path, capsys):
    """KILLS THE `TERMINAL_SUPPRESSED` -> `TERMINAL_NOTHING_UNREAD` MUTANT.

    The two are different facts. `nothing-unread` claims the channel was checked
    and was quiet; `suppressed` says there IS unread mail and this session had
    already been told about it. The invocation log is the only place either is
    recorded, so collapsing them makes per-session suppression invisible - and an
    invisible suppression is indistinguishable from the swallowed-mail defect it
    is one refactor away from becoming.

    BOTH POLARITIES ARE ASSERTED. Requiring `suppressed` to be present is what
    kills the mutant; requiring `nothing-unread` to be ABSENT is what stops a
    later version emitting both and passing.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    assert "a.md" in capsys.readouterr().out, "the first fire printed nothing to suppress"
    first_terminals = [ln.split(chr(9))[-1] for ln in _log_lines(watch)]
    assert watch.TERMINAL_REPORTED in first_terminals, (
        f"the first fire did not report, so the second proves nothing: {first_terminals}"
    )

    watch.main(argv, session="sess1")
    assert capsys.readouterr().out == "", "the second fire was not suppressed at all"

    terminals = [ln.split(chr(9))[-1] for ln in _log_lines(watch)]
    assert terminals[-1] == watch.TERMINAL_SUPPRESSED, (
        f"a suppressed fire logged {terminals[-1]!r}. If that is "
        f"{watch.TERMINAL_NOTHING_UNREAD!r} the log now claims a quiet channel "
        "over real unread mail, and the suppression is invisible"
    )
    assert watch.TERMINAL_NOTHING_UNREAD not in terminals, (
        f"a fire over unread mail recorded {watch.TERMINAL_NOTHING_UNREAD!r}: {terminals}"
    )


def test_a_genuinely_quiet_fire_still_says_nothing_unread(watch, tmp_path, capsys):
    """THE SURVIVING-NEIGHBOUR HALF. The arm above must not be satisfiable by a
    watcher that simply always writes `suppressed`, which would erase the
    distinction in the other direction.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    watch.mark_seen(inbox, state)
    argv = ["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    assert capsys.readouterr().out == ""

    terminals = [ln.split(chr(9))[-1] for ln in _log_lines(watch)]
    assert terminals[-1] == watch.TERMINAL_NOTHING_UNREAD, (
        f"a genuinely quiet channel logged {terminals[-1]!r}, so the disposition "
        "no longer separates a quiet inbox from a suppressed one"
    )


# ---------------------------------------------------------------------------
# CLAUSE 2 - THE UNMEASURED LINE FOR A CHANNEL THAT WAS NOT LOOKED AT
# ---------------------------------------------------------------------------


def test_the_quiet_no_inbox_path_prints_one_unmeasured_line(watch, tmp_path, capsys):
    """A BLIND WATCHER MUST NEVER READ AS CLEAN, and this path used to be silent.

    Silence is not neutral on a hook that fires before every prompt: silence is
    EXACTLY what a clean inbox produces, so a watcher that could not see the
    channel at all read as one reporting good news. It is also the normal state
    of a fresh clone and of every worktree, because `moon_sync_inbox/` is
    gitignored - so this was the quiet failure in the copies that most need the
    warning.
    """
    rc = watch.main(
        ["--dir", str(tmp_path / "absent"), "--state", str(tmp_path / "s.json"),
         "--quiet-when-empty"]
    )
    out = capsys.readouterr().out

    assert rc == 0, "a could-not-measure state must still exit 0; clause 1"
    assert watch.UNMEASURED in out, f"no UNMEASURED token on a blind fire: {out!r}"
    assert len([ln for ln in out.splitlines() if ln.strip()]) == 1, (
        f"clause 2 says ONE line, got: {out!r}"
    )
    assert "unread: none" not in out and "unread: 0" not in out, (
        f"the affirmative clean line was printed for a channel nobody looked at: {out!r}"
    )
    assert "nothing to report" not in out, (
        "the retired affirmative wording is back; that phrase is what clause 2 forbids"
    )


def test_an_absent_seen_store_is_an_empty_set_and_never_unmeasured(watch, tmp_path, capsys):
    """CLAUSE 2'S OWN EXCEPTION, spelled out because it is easy to over-apply.

    "An absent SEEN STORE is an empty set, not a failure." A fresh clone has no
    watermark and every note in the inbox is legitimately unread; printing
    UNMEASURED for that would cry blind over a state the tool measured perfectly.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "definitely" / "absent.json"
    assert not state.exists()

    watch.main(["--dir", str(inbox), "--state", str(state), "--quiet-when-empty"])
    out = capsys.readouterr().out

    assert "a.md" in out, "the note did not surface, so this arm is vacuous"
    assert watch.UNMEASURED not in out, (
        f"an absent watermark was reported as a measurement failure: {out!r}"
    )


def test_the_absent_inbox_line_is_shown_once_per_session_but_always_without_one(
    watch, tmp_path, capsys
):
    """Clause 4 allows this ONE could-not-measure state to be shown once per
    session id, and it needs the allowance more than any other: an absent inbox
    is not a transient fault that clears. It is permanent in a worktree, so
    re-printing it would put the line in front of the operator on every prompt
    forever.
    """
    argv = [
        "--dir", str(tmp_path / "absent"), "--state", str(tmp_path / "s.json"),
        "--quiet-when-empty",
    ]

    watch.main(argv, session="sess1")
    assert watch.UNMEASURED in capsys.readouterr().out, "the first fire said nothing"
    watch.main(argv, session="sess1")
    assert capsys.readouterr().out == "", "the blind line re-printed inside one session"
    watch.main(argv, session="sess2")
    assert watch.UNMEASURED in capsys.readouterr().out, "a new session was not told"

    # FAIL OPEN with no id, and nothing written.
    cache = Path(watch.DEFAULT_SESSIONS)
    before = cache.read_bytes()
    watch.main(argv)
    assert watch.UNMEASURED in capsys.readouterr().out, "fail open did not print"
    watch.main(argv)
    assert watch.UNMEASURED in capsys.readouterr().out, "fail open suppressed on a second fire"
    assert cache.read_bytes() == before, "a fire with no session id wrote the cache"


def test_the_non_quiet_no_inbox_line_also_carries_the_token(watch, tmp_path, capsys):
    """Clause 2 is about the STATE, not about which hook observed it."""
    watch.main(["--dir", str(tmp_path / "absent"), "--state", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert watch.UNMEASURED in out, f"the session-start rendering stayed affirmative: {out!r}"
    assert "nothing to report" not in out


# ---------------------------------------------------------------------------
# CLAUSE 3 - THE LIST CAP, NEWEST FIRST, AND THE OVERFLOW REPORT FILE
# ---------------------------------------------------------------------------


def _many(inbox: Path, count: int) -> list[str]:
    """`count` date-stamped notes, returned OLDEST name first."""
    names = []
    for i in range(count):
        name = f"2026-09-{i + 1:02d}-1200-from-RC-note-{i:02d}.md"
        _note(inbox, name, f"body {i}\n")
        names.append(name)
    return names


def test_the_cap_is_the_contract_value_of_ten(watch):
    """PINS THE NUMBER ITSELF, because every other arm is parametric in it.

    The cap arm below derives its expectations from `MAX_LISTED_NAMES`, so it
    follows the constant wherever it goes and cannot pin it. An adversary found
    the value was held only by ACCIDENT - a hardcoded "+5 more" literal in
    `test_without_a_session_id_...`, which pins the arithmetic of one fixture and
    would still pass at a different cap with a different fixture.

    Clause 3 names the number: "at most N full names ... where N is the project's
    existing list cap or 10 where none exists". MEASURED AT BASE e9b4542 this
    tree had no cap - `_render` printed every entry - so N is the fleet default of
    10 and it is a CONTRACT VALUE rather than a tuning knob. Changing it is a
    change to what this tree tells four other repositories it does.
    """
    assert watch.MAX_LISTED_NAMES == 10, (
        f"the transcript cap is {watch.MAX_LISTED_NAMES}, not the 10 that clause 3 "
        "of the fleet watcher contract specifies for a project with no prior cap. "
        "This is a cross-repo commitment, not a local preference"
    )


def test_the_transcript_is_capped_at_ten_names_newest_first(watch, tmp_path, capsys):
    """CLAUSE 3, and the ORDER is the half this tree got wrong first.

    `_entries` sorts ascending and its docstring says "oldest name first", so the
    uncapped render listed oldest first - which under a cap is the worst possible
    choice: it shows the ten notes you are least likely to still need and hides
    today's. The names on this channel are date-prefixed, so a descending name
    sort IS newest-first.

    THE COUNTS LINE CARRIES THE FULL COUNT. "unread: 25" over ten names plus a
    pointer is honest; "unread: 10" would be a lie that matches its own list.
    """
    inbox = tmp_path / "inbox"
    names = _many(inbox, 25)
    watch.main(
        ["--dir", str(inbox), "--state", str(tmp_path / "seen.json")], session="sess1"
    )
    out = capsys.readouterr().out

    assert f"unread: {len(names)}" in out, f"the counts line is not the full count: {out!r}"
    listed = [ln for ln in out.splitlines() if ln.startswith("  [")]
    assert len(listed) == watch.MAX_LISTED_NAMES, (
        f"{len(listed)} names listed against a cap of {watch.MAX_LISTED_NAMES}"
    )
    assert names[-1] in out, "the NEWEST note is not in the transcript"
    assert names[0] not in out, (
        "the OLDEST note is in the transcript, so the cap kept the wrong end"
    )
    expected = list(reversed(names))[: watch.MAX_LISTED_NAMES]
    assert [ln.split("] ")[1].split("  (")[0] for ln in listed] == expected, (
        f"the ten names are not the newest ten in newest-first order: {listed}"
    )
    assert f"+{len(names) - watch.MAX_LISTED_NAMES} more" in out, "no overflow pointer"
    assert "..." not in out, "a name was truncated, which clause 6 forbids outright"


def test_the_overflow_report_is_written_before_stdout_and_named_by_the_pointer(
    watch, tmp_path, capsys
):
    """CLAUSE 3's ordering, and it is the OPPOSITE of the cache's on purpose.

    The report file is written BEFORE stdout so the pointer never names a file
    that is not there; the per-session cache is written AFTER the flush so a
    killed hook re-prints. Two writes, two clauses, two opposite mistakes being
    guarded against.

    Asserted on the ORDER of the calls, because on any fire that is not killed
    both orderings look identical.
    """
    inbox = tmp_path / "inbox"
    names = _many(inbox, 15)
    order: list[str] = []
    real_text = watch.atomic_write_text

    def traced_text(path, payload):
        order.append(f"write:{Path(path).name}")
        return real_text(path, payload)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(watch, "atomic_write_text", traced_text)
    monkey.setattr(watch.sys.stdout, "flush", lambda: order.append("flush"), raising=False)
    try:
        watch.main(
            ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"],
            session="sess1",
        )
    finally:
        monkey.undo()
    out = capsys.readouterr().out

    report = Path(watch.DEFAULT_REPORT)
    assert report.is_file(), f"no overflow report was written: {order}"
    assert str(report) in out, (
        f"the pointer does not name this project's report file: {out!r}"
    )
    written = f"write:{report.name}"
    assert written in order, f"the report write was not observed: {order}"
    assert "flush" in order, f"stdout was never flushed: {order}"
    assert order.index(written) < order.index("flush"), (
        f"the report was written after stdout was flushed: {order}. The pointer "
        "would then name a file that did not exist when the reader saw it"
    )

    body = report.read_text(encoding="utf-8")
    for name in names:
        assert name in body, f"{name} is missing from the full listing"
    assert body.index(names[-1]) < body.index(names[0]), (
        "the report file is not newest-first"
    )


def test_without_a_session_id_the_pointer_is_plain_and_no_file_is_written(
    watch, tmp_path, capsys
):
    """CLAUSE 3, and it is the same fail-open rule the cache follows: a fire that
    cannot attribute itself does not get to leave state behind.
    """
    inbox = tmp_path / "inbox"
    _many(inbox, 15)
    watch.main(["--dir", str(inbox), "--state", str(tmp_path / "seen.json")])
    out = capsys.readouterr().out

    assert "+5 more" in out, f"no overflow pointer at all: {out!r}"
    assert str(Path(watch.DEFAULT_REPORT)) not in out, (
        f"the pointer named a report file on a fire that writes none: {out!r}"
    )
    assert not Path(watch.DEFAULT_REPORT).exists(), (
        "a fire with no validated session id wrote the report file anyway"
    )


def test_a_failed_report_write_says_unmeasured_and_does_not_treat_the_rest_as_shown(
    watch, tmp_path, capsys
):
    """CLAUSE 3's LAST SENTENCE, both halves.

    A pointer to an absent file is worse than no pointer: it sends the reader
    somewhere empty and they conclude there was nothing to see. And the entries
    beyond the cap must NOT be recorded as shown, or the next fire in this
    session suppresses names that reached no human and no file.
    """
    inbox = tmp_path / "inbox"
    names = _many(inbox, 15)
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    monkey = pytest.MonkeyPatch()
    monkey.setattr(watch, "atomic_write_text", lambda path, payload: False)
    try:
        watch.main(argv, session="sess1")
    finally:
        monkey.undo()
    out = capsys.readouterr().out

    assert watch.UNMEASURED in out, f"a failed report write was not disclosed: {out!r}"
    assert str(Path(watch.DEFAULT_REPORT)) not in out, (
        f"the pointer named a file whose write failed: {out!r}"
    )

    cache = json.loads(Path(watch.DEFAULT_SESSIONS).read_text(encoding="utf-8"))
    shown = cache["sessions"][0]["shown"]
    assert len(shown) == watch.MAX_LISTED_NAMES, (
        f"{len(shown)} entries recorded as shown when only "
        f"{watch.MAX_LISTED_NAMES} reached the transcript and the file failed"
    )
    assert names[0] not in "".join(shown), (
        "an entry beyond the cap was recorded as shown after the report write failed"
    )

    # AND THE PROOF THAT MATTERS: the held-back entries come back on the next
    # fire. Recording them as shown would have swallowed them for the rest of the
    # session, which is the whole reason clause 3 says not to.
    watch.main(argv, session="sess1")
    second = capsys.readouterr().out
    assert names[0] in second, (
        "an entry beyond the cap never reached the transcript OR the report file "
        f"and was still suppressed on the next fire: {second!r}"
    )
    assert names[-1] not in second, (
        "an entry that WAS listed on the first fire printed again, so suppression "
        "stopped working while fixing the overflow case"
    )


def test_a_refused_report_write_leaks_no_raw_error_to_stderr(watch, tmp_path, capsys):
    """NEVER A RAW API OR ERROR STRING ON A USER-FACING SURFACE - a hard rule here.

    MEASURED, and the leak was real. `core/atomic_io.py` catches its own OSError
    and returns False exactly as documented, then LOGS the failure through
    `core/log_setup.py`, whose console handler is a `StreamHandler` on stderr. So
    a refused write on the overflow-report path put a raw
    `PermissionError: [WinError 5]` in front of the operator, carrying the full
    filesystem path - a machine-identity leak of the kind this tree has closed
    before - and ANSI colour codes with it. The friendly degraded state was
    rendered correctly on stdout at the same instant, so the operator got both.

    THE STDOUT HALF IS ASSERTED TOO, and it is the arming half: a watcher that
    crashed, or one that silently skipped the whole path, would satisfy the
    no-leak assertion perfectly.

    THE RAW ERROR IS NOT SUPPRESSED, ONLY KEPT OFF THIS SURFACE. `core/log_setup.py`
    attaches a `FileHandler` beside the console handler and only the console one
    is muted, so the error still reaches the day's log file. That is the third
    clause of the rule - catch it, render a friendly state, LOG the raw error -
    and dropping it would trade one violation for another.

    CAPTURED THROUGH AN OWN STREAM HANDLER, NOT THROUGH `capsys`, AND THAT IS A
    MEASURED CORRECTION. The first version of this arm asserted on
    `capsys.readouterr().err` and was VACUOUS: `capsys` swaps `sys.stderr`, but
    `core/log_setup.py` builds its console handler with `stream=sys.stderr`
    resolved at import, so the handler holds the ORIGINAL stream and writes past
    the capture entirely. The arm passed whether or not the mute was there -
    removing the mute from `main` left it green. A handler this arm attaches
    itself is the thing actually being muted, so it cannot miss.
    """
    import io as _io
    import logging as _logging

    inbox = tmp_path / "inbox"
    _many(inbox, 15)

    sink = _io.StringIO()
    probe = _logging.StreamHandler(stream=sink)
    probe.setLevel(_logging.DEBUG)
    atomic_log = _logging.getLogger("core.atomic_io")
    atomic_log.addHandler(probe)

    boom = PermissionError(5, "Access is denied", str(tmp_path / "inbox_report.txt"))

    def refuse(path, payload):
        # Routed through the real module's logger so this arm exercises the same
        # path `core/atomic_io.py` takes, rather than a quieter imitation of it.
        atomic_log.error(
            "atomic_write_text failed for %s: %s: %s", path, type(boom).__name__, boom
        )
        return False

    monkey = pytest.MonkeyPatch()
    monkey.setattr(watch, "atomic_write_text", refuse)
    try:
        watch.main(
            ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"),
             "--quiet-when-empty"],
            session="sess1",
        )
    finally:
        monkey.undo()
        atomic_log.removeHandler(probe)
    captured = capsys.readouterr()
    on_console = sink.getvalue()

    assert watch.UNMEASURED in captured.out, (
        f"the degraded pointer never rendered, so this arm is vacuous: {captured.out!r}"
    )
    for leak in ("PermissionError", "WinError", "Access is denied", "Traceback"):
        assert leak not in on_console, (
            f"a raw error string reached a console stream: {leak!r} in "
            f"{on_console[:400]!r}. This tree forbids a raw API or error string on "
            "any user-facing surface - catch it, render a friendly degraded state, "
            "log the raw error"
        )
    assert str(tmp_path) not in on_console, (
        f"a full filesystem path reached a console stream: {on_console[:400]!r}. "
        "That is a machine-identity leak as well as a raw-error one"
    )

    # THE ARMING HALF. The probe handler must be capable of receiving that exact
    # record, or the silence above says nothing about the mute. Emitted OUTSIDE
    # `main`, where nothing is muted.
    atomic_log.addHandler(probe)
    try:
        atomic_log.error("atomic_write_text failed for %s: %s: %s", tmp_path, "PermissionError", boom)
    finally:
        atomic_log.removeHandler(probe)
    assert "PermissionError" in sink.getvalue(), (
        "the probe handler never receives this record at all, so the no-leak "
        "assertions above would pass against a broken instrument"
    )


def test_the_console_mute_leaves_the_file_handler_alone(watch):
    """THE SURVIVING-NEIGHBOUR HALF, and it guards the trap in writing the mute.

    `logging.FileHandler` IS A SUBCLASS of `logging.StreamHandler`. A mute that
    selected on `StreamHandler` alone would silence the file handler too, turning
    "do not surface the raw error" into "do not record it" - which is the
    opposite of what the rule says and would be undetectable from the console,
    because the console is the thing being muted.
    """
    import logging as _logging

    console = _logging.StreamHandler()
    console.setLevel(_logging.INFO)
    to_file = _logging.FileHandler(
        str(Path(watch.DEFAULT_SESSIONS).parent / "probe.log"), delay=True
    )
    to_file.setLevel(_logging.INFO)
    target = _logging.getLogger("core.atomic_io")
    target.addHandler(console)
    target.addHandler(to_file)
    try:
        with watch._console_logging_muted():
            assert console.level > _logging.CRITICAL, (
                "the console handler was not muted, so the leak is still open"
            )
            assert to_file.level == _logging.INFO, (
                "the FILE handler was muted too. FileHandler subclasses "
                "StreamHandler, so a mute that does not exclude it stops the raw "
                "error being RECORDED - the rule says log it, not lose it"
            )
        assert console.level == _logging.INFO, "the console level was not restored"
    finally:
        target.removeHandler(console)
        target.removeHandler(to_file)
        to_file.close()


def test_a_withdrawal_only_quiet_fire_does_not_print_the_affirmative_clean_line(
    watch, tmp_path, capsys
):
    """A PRE-EXISTING BUG, FIXED HERE, AND IT PREDATES THE SESSION WORK.

    At base e9b454218253f205a2d050ab8e2561656b790f20 a withdrawal-only quiet fire
    printed `unread: none` and then the withdrawal block. Two faults: `unread:
    none` is the affirmative clean line, which clause 2 keeps off this hook; and
    `QUIET_SHAPE` in `tests/test_session_hooks.py` rejects that body, so shipped
    behaviour could redden an arm nobody had run with a withdrawal pending.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    reported = tmp_path / "reported.json"
    watch.mark_seen(inbox, state)
    (inbox / "a.md").unlink()

    watch.main([
        "--dir", str(inbox), "--state", str(state), "--reported", str(reported),
        "--quiet-when-empty",
    ])
    out = capsys.readouterr().out

    assert "WITHDRAWN" in out, "no withdrawal was reported, so this arm is vacuous"
    assert "unread: none" not in out, (
        f"the affirmative clean line was printed beside a withdrawal: {out!r}"
    )


def test_a_withdrawal_only_session_start_fire_still_renders_the_heading(watch, tmp_path, capsys):
    """THE SURVIVING-NEIGHBOUR HALF of the fix above.

    Dropping `unread: none` from the QUIET path must not drop it from the
    deliberate one. `SessionStart` and a manual run are somebody asking, and
    "unread: none" is the answer - it is the affirmative clean line doing its
    actual job, on a surface that fires once rather than on every prompt.
    """
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md")
    state = tmp_path / "seen.json"
    reported = tmp_path / "reported.json"
    watch.mark_seen(inbox, state)
    (inbox / "a.md").unlink()

    watch.main([
        "--dir", str(inbox), "--state", str(state), "--reported", str(reported),
    ])
    out = capsys.readouterr().out

    assert "unread: none" in out, (
        f"the session-start rendering lost its counts line: {out!r}"
    )
    assert "WITHDRAWN" in out


def test_the_report_never_carries_a_payload_byte_on_the_suppressed_path(watch, tmp_path, capsys):
    """The privileged-surface property, restated across the new code path.

    Everything this prints at `UserPromptSubmit` is injected into a session's
    context with the harness's authority before any judgement is applied to it.
    The suppression layer is new code between the walk and that surface, so the
    no-payload property is re-asserted through it rather than assumed to have
    survived.
    """
    marker = "ZQ" + chr(45) + "SESSIONBODY" + chr(45) + "MARKER"
    inbox = tmp_path / "inbox"
    _note(inbox, "a.md", f"# heading\n\n{marker}\n")
    argv = ["--dir", str(inbox), "--state", str(tmp_path / "seen.json"), "--quiet-when-empty"]

    watch.main(argv, session="sess1")
    first = capsys.readouterr().out
    _note(inbox, "a.md", f"# corrected\n\n{marker}\n")
    watch.main(argv, session="sess1")
    second = capsys.readouterr().out

    assert "a.md" in first and "a.md" in second, "one of the two fires said nothing"
    assert marker not in first + second
    cache = Path(watch.DEFAULT_SESSIONS).read_text(encoding="utf-8")
    assert marker not in cache, (
        "a payload byte reached the suppression cache. Nothing a sender wrote "
        "belongs in a record this tree writes"
    )
