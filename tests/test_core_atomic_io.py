"""Tests for core.atomic_io.

The claim under test is not "the file gets written" - it is that a CONCURRENT
READER can never observe a partial file, and that a failed write leaves the
previous state intact. Those are the two properties the atomic-write rule
exists for, so they are asserted directly rather than assumed.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

import core.atomic_io
from core.atomic_io import atomic_write_json, atomic_write_text, read_json


def _sibling_temps(directory: Path) -> list[Path]:
    """Every temp file atomic_io could have left in `directory`."""
    return sorted(p for p in directory.iterdir() if p.name.endswith(".tmp"))


def test_atomic_write_text_creates_file_and_parents(tmp_path):
    target = tmp_path / "nested" / "deeper" / "state.txt"
    assert atomic_write_text(target, "hello") is True
    assert target.read_text(encoding="utf-8") == "hello"


def test_target_is_never_observed_in_a_partial_state(tmp_path, monkeypatch):
    """The target holds the OLD bytes right up to the rename, then the NEW ones.

    Path.replace is spied on so the moment just before the swap is observable.
    That instant is exactly when a polling reader would be at risk.
    """
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    payload = "NEW-" + ("x" * 8192)
    observed: dict[str, str] = {}
    real_replace = Path.replace

    def spy(self: Path, other):
        observed["target_before_swap"] = Path(other).read_text(encoding="utf-8")
        observed["temp_before_swap"] = self.read_text(encoding="utf-8")
        return real_replace(self, other)

    monkeypatch.setattr(Path, "replace", spy)
    assert atomic_write_text(target, payload) is True

    # The target still held the complete previous document at swap time.
    assert observed["target_before_swap"] == "OLD"
    # The temp already held the complete new document at swap time.
    assert observed["temp_before_swap"] == payload
    # And the swap published it whole.
    assert target.read_text(encoding="utf-8") == payload


def test_no_temp_file_is_left_behind_after_a_successful_write(tmp_path):
    target = tmp_path / "state.json"
    assert atomic_write_json(target, {"a": 1}) is True
    assert atomic_write_json(target, {"a": 2}) is True
    assert _sibling_temps(tmp_path) == []
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_unserializable_payload_leaves_the_previous_file_intact(tmp_path):
    target = tmp_path / "state.json"
    assert atomic_write_json(target, {"kept": True}) is True

    assert atomic_write_json(target, {"bad": object()}) is False
    # Previous document survives byte for byte, and no temp is orphaned.
    assert json.loads(target.read_text(encoding="utf-8")) == {"kept": True}
    assert _sibling_temps(tmp_path) == []


def test_failed_rename_leaves_previous_content_and_removes_the_temp(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    def boom(self: Path, other):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "replace", boom)
    assert atomic_write_text(target, "NEW") is False
    assert target.read_text(encoding="utf-8") == "OLD"
    assert _sibling_temps(tmp_path) == []


def test_read_json_returns_default_for_a_missing_file(tmp_path):
    sentinel = {"default": True}
    assert read_json(tmp_path / "absent.json", sentinel) is sentinel
    assert read_json(tmp_path / "absent.json") is None


def test_read_json_returns_default_on_corruption_and_does_not_raise(tmp_path):
    target = tmp_path / "corrupt.json"
    target.write_text('{"half": ', encoding="utf-8")
    try:
        result = read_json(target, {"fallback": 1})
    except Exception as exc:  # noqa: BLE001 - the whole point is that none escapes
        pytest.fail(f"read_json raised {exc.__class__.__name__} instead of degrading")
    assert result == {"fallback": 1}


def test_read_json_returns_default_on_undecodable_bytes(tmp_path):
    target = tmp_path / "binary.json"
    target.write_bytes(b"\xff\xfe\x00\x01not utf-8")
    assert read_json(target, []) == []


def test_json_roundtrip_preserves_the_document(tmp_path):
    target = tmp_path / "state.json"
    payload = {"uid": "700000000", "pity": {"character_event": 42}, "list": [1, 2, 3]}
    assert atomic_write_json(target, payload) is True
    assert read_json(target, None) == payload


def test_write_to_an_unwritable_path_degrades_to_false(tmp_path):
    # A directory occupies the target name, so the rename cannot succeed.
    target = tmp_path / "occupied"
    target.mkdir()
    assert atomic_write_text(target, "nope") is False
    assert target.is_dir()
    assert _sibling_temps(tmp_path) == []


# ---------------------------------------------------------------------------
# Line endings
#
# `Path.write_text` opens with `newline=None`, which translates every newline
# the caller passed into `os.linesep`. On Windows that is CRLF, so the
# sanctioned write path silently rewrote the caller's bytes. `.gitattributes`
# declares `* text=auto eol=lf` and `tests/test_line_endings.py` fails a
# tracked file that carries CRLF, so the first TRACKED file written through
# this module would have turned the suite red - and `git diff` would have
# shown nothing, because the index normalises the ending away.
#
# Every assertion below reads RAW BYTES. `Path.read_text` translates CRLF back
# to a newline on the way in, so a text-level assertion cannot see the defect
# at all and would have passed against the broken writer.
# ---------------------------------------------------------------------------

_CRLF = b"\r\n"


def _crlf_offenders(path: Path, label: str) -> list[str]:
    """Return one offender string when `path` carries a CRLF pair, else none.

    Separated from the tests that use it so the detector itself can be armed
    against a planted control. A checker never observed to fire and a clean
    tree look identical.
    """
    raw = path.read_bytes()
    if _CRLF in raw:
        return [f"{label}: {raw.count(_CRLF)} CRLF pair(s) in {path.name}"]
    return []


# Every public writer in the module, with a call that produces a newline.
# `test_every_public_writer_is_covered_by_the_sweep` fails if the module grows
# a writer this registry does not name, so the sweep cannot silently narrow.
_PUBLIC_WRITERS = {
    "atomic_write_text": lambda p: atomic_write_text(p, "a\nb\n"),
    "atomic_write_json": lambda p: atomic_write_json(p, {"a": 1, "b": [2, 3]}),
}


def test_atomic_write_text_does_not_translate_a_newline(tmp_path):
    """The writer transports bytes; it does not rewrite them."""
    target = tmp_path / "state.txt"
    assert atomic_write_text(target, "a\nb\n") is True
    assert target.read_bytes() == b"a\nb\n"


def test_atomic_write_json_writes_lf_only(tmp_path):
    """`atomic_write_json` funnels through `atomic_write_text`, indent and all."""
    target = tmp_path / "state.json"
    assert atomic_write_json(target, {"a": 1}) is True
    raw = target.read_bytes()
    assert _CRLF not in raw
    assert raw == b'{\n  "a": 1\n}\n'


def test_a_caller_supplied_crlf_survives_verbatim(tmp_path):
    """The contract is NO TRANSLATION, not "normalise everything to LF".

    This is the surviving-neighbour arm. A writer that replaced CRLF with LF
    would score full marks on the two tests above while silently corrupting a
    caller who deliberately wants CRLF - a `.ps1` or a fixture, say. Both arms
    are needed; either one alone is passable by a wrong implementation.
    """
    target = tmp_path / "crlf.txt"
    assert atomic_write_text(target, "a\r\nb\r\n") is True
    assert target.read_bytes() == b"a\r\nb\r\n"


def test_a_lone_cr_survives_verbatim(tmp_path):
    """A bare carriage return is a newline to `newline=None` too."""
    target = tmp_path / "cr.txt"
    assert atomic_write_text(target, "a\rb") is True
    assert target.read_bytes() == b"a\rb"


def test_every_public_writer_is_covered_by_the_sweep():
    """The sweep's registry must name every `atomic_write_*` the module exports."""
    exported = {name for name in dir(core.atomic_io) if name.startswith("atomic_write")}
    assert exported == set(_PUBLIC_WRITERS), (
        "core.atomic_io exports a writer the CRLF sweep does not exercise: "
        f"exported={sorted(exported)} swept={sorted(_PUBLIC_WRITERS)}"
    )


def test_no_public_writer_emits_crlf(tmp_path):
    """The sweep. Checked count is asserted BEFORE the offender list."""
    checked = 0
    offenders: list[str] = []
    for name, invoke in sorted(_PUBLIC_WRITERS.items()):
        target = tmp_path / f"{name}.out"
        assert invoke(target) is True
        checked += 1
        offenders.extend(_crlf_offenders(target, name))

    assert checked == len(_PUBLIC_WRITERS)
    assert checked > 0, "zero out of zero is not a pass"
    assert offenders == [], f"writers emitted CRLF: {offenders}"


def test_the_crlf_detector_fires_on_a_planted_offender(tmp_path):
    """Non-vacuity. An unarmed detector and a clean tree look identical."""
    planted = tmp_path / "planted.txt"
    planted.write_bytes(b"a\r\nb\r\n")
    assert _crlf_offenders(planted, "planted") == [
        "planted: 2 CRLF pair(s) in planted.txt"
    ]

    clean = tmp_path / "clean.txt"
    clean.write_bytes(b"a\nb\n")
    assert _crlf_offenders(clean, "clean") == []


# ---------------------------------------------------------------------------
# The temp file must not survive ANY failure
#
# `Path.write_text` opens the file BEFORE it encodes the payload, so a payload
# that cannot be encoded leaves a zero-byte temp on disk. The handler caught
# only OSError, and a UnicodeEncodeError is a ValueError, so `_discard` was
# skipped outright. Measured in this tree at 3533965 before the fix:
#
#     RAISED UnicodeEncodeError 'utf-8' codec can't encode character
#     '\\ud800' in position 0: surrogates not allowed
#     residue ['.state.json.27536.5013851f.tmp']  size 0
#
# The leak is not specific to encoding. Anything raised between the open and
# the rename orphans the temp, including a BaseException such as a
# KeyboardInterrupt landing mid-write. The repair therefore has to be reached
# without catching anything, and it must NOT fire on the success path, where
# the temp has already been renamed onto the target.
#
# Every arm below carries a positive floor IN THE SAME ARM - the exception type
# raised, a counted injection, or the target's exact bytes. An arm that asserts
# only "no temp remains" passes just as happily when the write never ran at
# all, which is a test about nothing.
# ---------------------------------------------------------------------------

_LONE_SURROGATE = chr(0xD800)


class _InjectedFailure(Exception):
    """A failure that is neither an OSError nor an encoding error."""


def _residue(directory: Path) -> list[str]:
    """Every name left in `directory`, derived rather than hand-counted."""
    return sorted(p.name for p in directory.iterdir())


def _spy_write_text_then_raise(monkeypatch, exc: BaseException) -> dict[str, int]:
    """Make `Path.write_text` do the real write and THEN raise `exc`.

    Writing for real before raising is what makes these arms bite. An injected
    failure that raises before the open never creates a temp, so "no residue"
    would hold against the unfixed module too and the arm would prove nothing.
    This reproduces the real shape: the temp exists on disk, then the call
    dies.
    """
    calls = {"n": 0}
    real_write_text = Path.write_text

    def spy(self: Path, *args, **kwargs):
        calls["n"] += 1
        real_write_text(self, *args, **kwargs)
        raise exc

    monkeypatch.setattr(Path, "write_text", spy)
    return calls


def test_an_unencodable_payload_leaves_no_temp_behind(tmp_path):
    """A1. The measured leak: a lone surrogate cannot be UTF-8 encoded.

    The raise is the floor. It proves the write path ran and failed for the
    encoding reason rather than the target simply never being touched. Whether
    this case raises or returns False is a separate contract question; this arm
    pins only that the temp is gone either way.
    """
    target = tmp_path / "state.json"
    with pytest.raises(UnicodeEncodeError):
        atomic_write_text(target, _LONE_SURROGATE)
    assert not target.exists()
    assert _residue(tmp_path) == []


def test_an_unencodable_payload_leaves_the_previous_document_intact(tmp_path):
    """A1, surviving-neighbour arm. The old state must outlive the bad write."""
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    with pytest.raises(UnicodeEncodeError):
        atomic_write_text(target, _LONE_SURROGATE)

    assert target.read_bytes() == b"OLD"
    assert _residue(tmp_path) == ["state.json"]


def test_a_non_oserror_failure_mid_write_leaves_no_temp_behind(tmp_path, monkeypatch):
    """A2. An arbitrary Exception raised after the temp exists on disk."""
    target = tmp_path / "state.json"
    calls = _spy_write_text_then_raise(monkeypatch, _InjectedFailure("disk gremlin"))

    with pytest.raises(_InjectedFailure):
        atomic_write_text(target, "NEW")

    assert calls["n"] == 1
    assert not target.exists()
    assert _residue(tmp_path) == []


def test_a_baseexception_mid_write_leaves_no_temp_behind(tmp_path, monkeypatch):
    """A3. A KeyboardInterrupt is not an Exception, and it orphans the temp too.

    `pytest.raises(Exception)` does NOT catch a BaseException subclass, so this
    arm names KeyboardInterrupt explicitly. A repair built on a wider `except`
    clause would not cover this case at all.
    """
    target = tmp_path / "state.json"
    calls = _spy_write_text_then_raise(monkeypatch, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        atomic_write_text(target, "NEW")

    assert calls["n"] == 1
    assert not target.exists()
    assert _residue(tmp_path) == []


def test_a_successful_write_publishes_the_bytes_and_leaves_no_residue(tmp_path):
    """A4. Control. The cleanup must not touch the success path.

    A repair that unlinks the temp unconditionally is harmless only by luck -
    the temp name no longer exists after the rename. This arm pins the intent:
    the caller's exact bytes land on the target and the directory holds that
    one file and nothing else.
    """
    target = tmp_path / "state.txt"
    assert atomic_write_text(target, "a\nb\n") is True
    assert target.read_bytes() == b"a\nb\n"
    assert _residue(tmp_path) == ["state.txt"]


class _Recorder(logging.Handler):
    """Collects formatted records off a single logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_an_oserror_still_returns_false_and_logs_and_leaves_no_residue(tmp_path, monkeypatch):
    """A5. Control. The OSError contract is unchanged by the cleanup repair.

    The existing rename-failure arm pins the return value and the residue; this
    one adds the log record, so a repair that quietly stopped reporting the
    failure would be caught.

    `caplog` cannot see this record. `core.log_setup.get_logger` sets
    `logger.propagate = False`, so nothing reaches the root handler pytest
    installs, and a caplog-based assertion here would measure the harness
    rather than the module. The handler is attached to the module's own logger
    instead.
    """
    target = tmp_path / "state.json"
    assert atomic_write_text(target, "OLD") is True

    def boom(self: Path, other):
        raise OSError(28, "No space left on device")

    recorder = _Recorder()
    core.atomic_io._log.addHandler(recorder)
    try:
        monkeypatch.setattr(Path, "replace", boom)
        assert atomic_write_text(target, "NEW") is False
    finally:
        core.atomic_io._log.removeHandler(recorder)

    assert len(recorder.messages) == 1, f"expected one error log, got {recorder.messages}"
    assert "atomic_write_text failed" in recorder.messages[0]
    assert "OSError" in recorder.messages[0]
    assert target.read_bytes() == b"OLD"
    assert _residue(tmp_path) == ["state.json"]


def test_an_unencodable_payload_raises_rather_than_returning_false(tmp_path):
    """A6. THE ADJUDICATED CONTRACT, held as a checked claim rather than prose.

    NOT a mutant-coverage claim, and measured before it was written. Widening
    the guard to `except (OSError, UnicodeEncodeError)` on a scratch copy turns
    THREE arms red, two of them slice A's. So the absorb is already caught.
    What it is not already is STATED: both of those arms use the raise only as
    a floor proving the write path ran, and
    `test_an_unencodable_payload_leaves_no_temp_behind` says in as many words
    that whether this raises or returns False is a separate contract question
    it does not pin. A maintainer who decided to absorb would read their red as
    two arms needing an update, which is exactly what an unstated contract buys
    you. This arm makes that red mean "you changed the contract".

    THE RULING IS KEEP RAISING, and two measured facts decided it. A payload
    the encoder rejects is a programmer error, not a state of the disk, and
    `tools/moon_sync_responder.py` re-raises `UnicodeError` out of its widened
    guard precisely so it cannot be mistaken for an ordinary `(False, target)`
    row - "loud-to-quiet is strictly worse than the silent abort". And
    `tests/test_responder_broadcast_refusal.py` asserts that escape end to end
    in `test_an_unencodable_draft_still_escapes_the_delivery_loop`, so an
    absorb here would redden a suite two modules away rather than fail locally.

    THE CONTROL IS IN THIS ARM ON PURPOSE. Without it the arm cannot tell
    "raises on a surrogate" from "raises on everything" - a module that lost
    its ability to write at all would satisfy every negative above.
    """
    refused = tmp_path / "refused"
    refused.mkdir()
    target = refused / "state.json"

    with pytest.raises(UnicodeEncodeError):
        atomic_write_text(target, _LONE_SURROGATE)

    assert not target.exists(), (
        "the encoder refused the payload but the target was published anyway"
    )
    assert _residue(refused) == [], (
        "the refused write left something behind in the target's directory"
    )

    # CONTROL. The same call, the same directory shape, a payload utf-8 accepts.
    accepted = tmp_path / "accepted"
    ok_target = accepted / "state.json"
    assert atomic_write_text(ok_target, "state.json\n") is True, (
        "an encodable payload failed too, so the arm above measured a module "
        "that cannot write rather than one that refuses a surrogate"
    )
    assert ok_target.read_bytes() == b"state.json\n"
    assert _residue(accepted) == ["state.json"]
