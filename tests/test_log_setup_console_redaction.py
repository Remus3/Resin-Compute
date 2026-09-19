"""Console-only path redaction: the repo root never reaches stderr.

THE DEFECT THESE ARMS PIN. `core/atomic_io.py` has five log sites - lines 87,
126, 145, 165 and 171 - and every one of them interpolates a `Path`. Callers
hand that module absolute paths, so every one of those five lines puts a FULL
FILESYSTEM PATH on stderr, and four of them put the raw exception beside it.
An operator watching a console therefore reads the machine's directory layout
out of an ordinary degraded-write report.

THE RULING THESE ARMS ENCODE, and it is deliberately NOT the obvious one. The
repair does not go in `core/atomic_io.py`: that module's logging is correct for
a library, and mechanically it could not address "the file handler" anyway
because `core.log_setup` caches ONE console handler and ONE file handler in
module globals and shares both process-wide across every logger. Nor does it go
at the call site, which would need the same edit in five places and again in the
sixth site somebody adds later. It goes in `core/log_setup.py`, which already
owns a console-only rendering decision in `_ColorFormatter` - redaction is that
same decision one notch further out.

WHAT EACH ARM MEASURES, and what makes it move.

- `test_the_console_handler_does_not_render_the_repo_root` fails BEFORE the fix
  because the console formatter renders the message verbatim, repo root and
  all. It passes AFTER because the console formatter rewrites the repo-root
  prefix to `<repo>` on the formatted STRING.
- `test_the_file_handler_still_renders_the_raw_path` passes BEFORE and must
  keep passing AFTER. It goes red if the repair over-reaches onto the file
  handler, and it goes red if the repair is implemented DESTRUCTIVELY - as a
  `logging.Filter` or anything else that edits the LogRecord in place - because
  `core/log_setup.py` attaches the console handler FIRST and the file handler
  SECOND, so both see the same record object and the second one would inherit
  whatever the first did to it.
- `test_the_console_still_emits_the_record_at_all` is the ARMING CONTROL. It
  does not move with the fix, and that is the point: without it, the two arms
  above would both be satisfied by a console handler that emitted nothing, which
  turns "do not surface" into "do not record".
- `test_the_redaction_covers_every_atomic_io_site` drives all five sites rather
  than the one, so a repair that happened to cover `atomic_write_text` alone
  still fails.
- `test_the_file_handler_receives_no_ansi_colour_code` pins the existing
  `finally` restoration in `_ColorFormatter`. A colour escape in the day log
  breaks `grep` and `less`, and it is exactly what a redaction implemented by
  record mutation would drag in with it.

These are BEHAVIOURAL arms. They build the real console handler out of
`core.log_setup`, swap its stream for a `StringIO`, attach it and a real
`logging.FileHandler` to `core.atomic_io`'s own logger in the production order,
and then drive REAL failures through `core.atomic_io`. Nothing here greps the
source text of a module: a source-text arm pins the shape of a repair rather
than its behaviour, and survives the defect untouched.

NO FILESYSTEM SIDE EFFECT INSIDE THE REPOSITORY. The failure driver patches
`Path.mkdir` and `Path.unlink` to raise, which reaches the SAME `except OSError`
at `core/atomic_io.py:126` and the same `_discard` warning at line 87 that the
`Path.replace` pattern in `tests/test_core_atomic_io.py` reaches, while creating
no byte at all under the repo root. That matters here and not there: these arms
need a target whose path is PREFIXED BY THE REPO ROOT, and the `replace` variant
would have to create a real temp file inside the tree to get one.

`caplog` is no use for any of this. `core.log_setup.get_logger` sets
`logger.propagate = False`, so nothing reaches the root handler pytest installs,
and a caplog assertion here would measure the harness instead of the module.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import pytest

import core.atomic_io
import core.log_setup
from core.config import REPO_ROOT

# The ANSI escape introducer, spelled with `chr` rather than as a literal. A
# literal escape byte in an ASCII-only tree is a glyph argument nobody needs.
_ESC = chr(0x1B)

#: Errno 28 has no dedicated `OSError` subclass, so the raised class name stays
#: exactly "OSError". This mirrors the value already used by
#: `tests/test_core_atomic_io.py` so the two files fail the same way.
_ENOSPC = 28
_ENOSPC_TEXT = "No space left on device"


class _Wiring:
    """Handles on the two streams an emitted record lands in."""

    def __init__(self, console_buffer: io.StringIO, day_log: Path) -> None:
        self._console_buffer = console_buffer
        self._day_log = day_log

    @property
    def console_text(self) -> str:
        return self._console_buffer.getvalue()

    @property
    def day_log_text(self) -> str:
        return self._day_log.read_text(encoding="utf-8")


@pytest.fixture
def wiring(tmp_path):
    """Attach the REAL console handler plus a real FileHandler, in production order.

    Production order is load-bearing rather than incidental:
    `core/log_setup.py` adds the console handler first and the file handler
    second, so a record-mutating repair on the console side would reach the file
    side. Reproducing the order here is what lets
    `test_the_file_handler_still_renders_the_raw_path` detect that.

    The console handler is the process-wide singleton from
    `core.log_setup._ensure_console()`, not a fresh one, so these arms measure
    the formatter the running process actually installs. Its stream and level
    are restored on teardown.
    """
    console = core.log_setup._ensure_console()
    original_stream = console.stream
    original_console_level = console.level
    buffer = io.StringIO()
    console.stream = buffer
    console.setLevel(logging.DEBUG)

    day_log = tmp_path / "day.log"
    file_handler = logging.FileHandler(day_log, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter(core.log_setup._LINE_FORMAT, datefmt=core.log_setup._TIME_FORMAT)
    )
    file_handler.setLevel(logging.DEBUG)

    logger = core.atomic_io._log
    original_handlers = list(logger.handlers)
    original_logger_level = logger.level
    logger.handlers = [console, file_handler]
    logger.setLevel(logging.DEBUG)
    try:
        yield _Wiring(buffer, day_log)
    finally:
        logger.handlers = original_handlers
        logger.setLevel(original_logger_level)
        file_handler.close()
        console.stream = original_stream
        console.setLevel(original_console_level)


def _repo_root_forms() -> tuple[str, ...]:
    """Both separator renderings of the repo root, lowercased.

    `Path` renders one separator and a string literal in this tree carries the
    other, and Windows compares paths case-insensitively, so an absence
    assertion that checks a single exact rendering is weaker than it looks.
    """
    text = str(REPO_ROOT)
    return (text.lower(), text.replace("\\", "/").lower())


def _assert_repo_root_absent(console_text: str, label: str) -> None:
    lowered = console_text.lower()
    for form in _repo_root_forms():
        assert form not in lowered, (
            f"{label}: the console rendered the repo root prefix {form!r}.\n"
            f"console text was:\n{console_text}"
        )


def _fail_a_write(monkeypatch: pytest.MonkeyPatch, target: Path) -> bool:
    """Drive a REAL failed `atomic_write_text` against `target`.

    Reaches two of the five log sites in one call: `core/atomic_io.py:126` for
    the refused write and `core/atomic_io.py:87` for the temp file the `finally`
    then cannot discard. Creates nothing on disk, because the first thing the
    function does is the `mkdir` that is patched to refuse.
    """

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError(_ENOSPC, _ENOSPC_TEXT)

    monkeypatch.setattr(Path, "mkdir", boom)
    monkeypatch.setattr(Path, "unlink", boom)
    return core.atomic_io.atomic_write_text(target, "NEW")


def test_the_console_handler_does_not_render_the_repo_root(wiring, monkeypatch):
    """RED before the fix: the console formatter renders the absolute path verbatim.

    GREEN after: the console formatter rewrites the repo-root prefix to
    `<repo>`. The basename assertion is the other half of the claim - an
    operator has to be able to tell WHICH file failed, so a repair that reduced
    the message to a bare `<repo>` would fail here even though the absence half
    would be satisfied.
    """
    target = REPO_ROOT / "no_such_probe_dir" / "state.json"
    assert _fail_a_write(monkeypatch, target) is False

    console_text = wiring.console_text
    _assert_repo_root_absent(console_text, "atomic_write_text")
    assert "state.json" in console_text, (
        "the basename must survive redaction, or the operator cannot tell which "
        f"file failed. console text was:\n{console_text}"
    )
    assert "<repo>" in console_text, (
        f"expected the repo root to be replaced by a marker. console text was:\n{console_text}"
    )


def test_the_file_handler_still_renders_the_raw_path(wiring, monkeypatch):
    """GREEN before AND after: the day log keeps the full absolute path.

    This is the opposite direction from the arm above. It goes red if the
    repair over-reaches onto the file handler's formatter, and it goes red if
    the repair mutates the LogRecord rather than the formatted string - the
    console handler is attached FIRST, so a mutated record would arrive here
    already redacted.
    """
    target = REPO_ROOT / "no_such_probe_dir" / "state.json"
    assert _fail_a_write(monkeypatch, target) is False

    day_log_text = wiring.day_log_text
    assert str(target) in day_log_text, (
        "the day log must keep the raw absolute path - redaction is a console "
        f"decision only. day log was:\n{day_log_text}"
    )
    assert _ENOSPC_TEXT in day_log_text, f"day log lost the raw OSError text:\n{day_log_text}"
    assert "OSError" in day_log_text, f"day log lost the exception class name:\n{day_log_text}"


def test_the_console_still_emits_the_record_at_all(wiring, monkeypatch):
    """THE ARMING CONTROL. Does not move with the fix, and that is the point.

    GREEN before AND after. Without it, the two arms above are both satisfied by
    a console handler that emits nothing at all, which would turn "do not
    surface the path" into "do not report the failure" - the opposite
    instruction.
    """
    target = REPO_ROOT / "no_such_probe_dir" / "state.json"
    assert _fail_a_write(monkeypatch, target) is False

    console_text = wiring.console_text
    assert console_text.strip(), "the console handler emitted nothing at all"
    assert "atomic_write_text failed" in console_text, (
        f"the console lost the failure report itself. console text was:\n{console_text}"
    )
    assert "could not remove temp file" in console_text, (
        f"the console lost the temp-discard warning. console text was:\n{console_text}"
    )


def test_the_redaction_covers_every_atomic_io_site(wiring, monkeypatch):
    """RED before the fix at each of the five sites, GREEN after.

    Pins that the repair is PER-HANDLER rather than per-call-site. A change that
    covered `atomic_write_text` alone leaves `atomic_write_json`, both
    `read_json` branches and the temp-discard warning still printing the repo
    root, and this arm names which one survived.
    """
    unserializable = REPO_ROOT / "no_such_probe_dir" / "payload.json"
    corrupt = REPO_ROOT / "no_such_probe_dir" / "corrupt.json"
    unreadable = REPO_ROOT / "no_such_probe_dir" / "unreadable.json"

    # Sites 126 and 87 - the refused write and the temp it cannot discard.
    with monkeypatch.context() as patch:
        assert _fail_a_write(patch, REPO_ROOT / "no_such_probe_dir" / "state.json") is False
    _assert_repo_root_absent(wiring.console_text, "atomic_write_text and _discard")

    # Site 145 - a payload the JSON encoder refuses. Touches no disk at all.
    assert core.atomic_io.atomic_write_json(unserializable, {"k": object()}) is False
    _assert_repo_root_absent(wiring.console_text, "atomic_write_json")

    # Site 171 - a file that reads cleanly but is not JSON.
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", lambda self, *a, **k: "{ this is not json")
        assert core.atomic_io.read_json(corrupt, default="fallback") == "fallback"
    _assert_repo_root_absent(wiring.console_text, "read_json corrupt")

    # Site 165 - a file the operating system refuses to hand over.
    def boom_read(self: Path, *args: object, **kwargs: object) -> str:
        raise OSError(_ENOSPC, _ENOSPC_TEXT)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", boom_read)
        assert core.atomic_io.read_json(unreadable, default="fallback") == "fallback"
    _assert_repo_root_absent(wiring.console_text, "read_json unreadable")

    console_text = wiring.console_text
    for basename in ("state.json", "payload.json", "corrupt.json", "unreadable.json"):
        assert basename in console_text, (
            f"the basename {basename} did not survive redaction. console text was:\n{console_text}"
        )


def test_the_file_handler_receives_no_ansi_colour_code(wiring, monkeypatch):
    """GREEN before AND after: colour is a console decision, same as redaction.

    `_ColorFormatter` wraps `record.levelname` in an ANSI escape and restores it
    in a `finally`, because the file handler formats the SAME record object
    afterwards. A redaction bolted on in a way that loses that restoration would
    put escape bytes in the day log, which breaks `grep` and `less` for the
    operator. The console half of this arm is the non-vacuity control: it proves
    the escape really is being produced, so the day-log assertion is measuring
    an absence that had something to be absent from.
    """
    target = REPO_ROOT / "no_such_probe_dir" / "state.json"
    assert _fail_a_write(monkeypatch, target) is False

    assert _ESC + "[" in wiring.console_text, (
        "the console stopped emitting colour, so the day-log assertion below "
        f"would be vacuous. console text was:\n{wiring.console_text}"
    )
    day_log_text = wiring.day_log_text
    assert _ESC not in day_log_text, (
        f"an ANSI escape reached the day log:\n{day_log_text!r}"
    )
