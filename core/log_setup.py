"""Logging setup - one log file per day, no rotation.

Operator preference inherited verbatim from Sibling-C:

    Logs live at logs/YYYY-MM-DD.log. One file per calendar day. NO rotation,
    no size cap, no RotatingFileHandler. A day is the unit an operator greps.

Console output is colour-coded per level so a warning is visible in a scrolling
terminal; the file handler is deliberately PLAIN, because ANSI escape bytes in
a log file break `grep`, `less` and every downstream reader.

The console handler ALSO redacts two machine-identifying path prefixes - the
repository root and the user profile - down to `<repo>` and `<user>`. Only the
prefix goes: the rest of the path, basename included, is left alone, so a report
still names the file it is about. The file handler is untouched by this and
keeps the raw absolute path, which is what an operator needs in order to act on
the failure. Both decisions are console-only rendering, and both live in this
module for the same reason: the handlers are cached here and shared
process-wide, so no library module could express "console but not file" even if
it wanted to. See `_RedactingColorFormatter`.

`get_logger(name)` is idempotent. Calling it twice for the same name attaches no
second handler, so a module-level `_log = get_logger(__name__)` plus a call from
a test never duplicates a line. Handlers are shared process-wide, and the file
handler is swapped when the calendar day rolls over so a long-lived daemon does
not keep writing yesterday's file.

File logging is best-effort. If the log directory cannot be created (read-only
volume, permission denied) the console handler still works and the failure is
reported once, at WARNING, rather than raising into a caller.
"""
from __future__ import annotations

import logging
import re
import sys
from datetime import date
from pathlib import Path

from core.config import REPO_ROOT, load_config

# ANSI SGR codes. 7-bit ASCII, applied to the console handler only.
_RESET = "\033[0m"
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[1;31m",  # bold red
}

_LINE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Process-wide handler state. Shared instances, not one pair per logger, so a
# day rollover is a single swap rather than a walk of every logger's handlers.
_configured_names: set[str] = set()
_console_handler: logging.Handler | None = None
_file_handler: logging.Handler | None = None
_file_handler_day: str = ""
_file_handler_failed = False


# Console-only redaction markers. Chosen to be obviously not a path segment, so
# a reader can see that something was replaced rather than guess at a truncation.
_REPO_MARKER = "<repo>"
_USER_MARKER = "<user>"

#: Built once on first use and cached, because the two prefixes it derives from
#: cannot change within a process: `REPO_ROOT` is resolved from `__file__` at
#: import and `Path.home()` from the account running the interpreter. Lazy
#: rather than eager so that an unresolvable home directory cannot turn this
#: module's IMPORT into a failure - it only ever costs the redaction itself.
_redaction_rules: tuple[tuple[re.Pattern[str], str], ...] | None = None


def _prefix_pattern(prefix: str) -> re.Pattern[str] | None:
    """Compile a tolerant matcher for one absolute path prefix.

    Two tolerances, both measured rather than defensive:

    - CASE. Windows compares paths case-insensitively, so `C:\\Resin Compute`
      and `c:\\resin compute` name the same directory and an exact-case matcher
      would leak the second one.
    - SEPARATOR. `Path` renders one separator and a string literal in this tree
      carries the other, and the same path can reach a log line either way. Each
      separator run is therefore matched as `[\\\\/]+` rather than literally.

    The trailing `(?![\\w.])` is what keeps this a PREFIX match rather than a
    substring match: without it a repo root at `.../agent-a1` would also redact
    an unrelated `.../agent-a1b`. Returns None when the prefix is too short to
    anchor on - a bare drive letter or a single segment - in which case the
    caller simply does not redact it.
    """
    text = prefix.rstrip("\\/")
    if not text:
        return None
    lead = r"[\\/]" if text[0] in "\\/" else ""
    parts = [re.escape(part) for part in re.split(r"[\\/]+", text) if part]
    if not parts or (len(parts) < 2 and not lead):
        return None
    return re.compile(lead + r"[\\/]+".join(parts) + r"(?![\w.])", re.IGNORECASE)


def _build_redaction_rules() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Assemble the console redaction table, longest prefix first.

    Order matters and is not cosmetic. If the repository happens to live INSIDE
    the user profile, both prefixes match the same line, and applying the
    shorter one first would leave a half-redacted `<user>\\...\\repo\\state`
    that still discloses the layout. Sorting by length descending applies the
    more specific prefix first in every arrangement, without this function
    having to know which arrangement it is in.

    A prefix that cannot be resolved is dropped rather than raised on, per the
    degrade-do-not-raise rule in `_RedactingColorFormatter`.
    """
    candidates: list[tuple[str, str]] = [(str(REPO_ROOT), _REPO_MARKER)]
    try:
        candidates.append((str(Path.home()), _USER_MARKER))
    except (OSError, RuntimeError):
        # No resolvable home on this host. Redact what can be resolved.
        pass

    rules: list[tuple[re.Pattern[str], str]] = []
    for text, marker in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        pattern = _prefix_pattern(text)
        if pattern is not None:
            rules.append((pattern, marker))
    return tuple(rules)


def _console_redaction_rules() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Return the cached redaction table, building it on first use."""
    global _redaction_rules
    if _redaction_rules is None:
        _redaction_rules = _build_redaction_rules()
    return _redaction_rules


class _ColorFormatter(logging.Formatter):
    """Console formatter that wraps the level name in an ANSI colour."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        if not color:
            return super().format(record)
        original = record.levelname
        record.levelname = f"{color}{original}{_RESET}"
        try:
            return super().format(record)
        finally:
            # Restore, or the file handler inherits the escape codes: handlers
            # share one LogRecord instance.
            record.levelname = original


class _RedactingColorFormatter(_ColorFormatter):
    """Console formatter that also rewrites two machine-identifying prefixes.

    WHY THIS LIVES HERE AND NOT AT THE LOG SITE. `core/atomic_io.py` has five
    log sites - lines 87, 126, 145, 165 and 171 - and every one of them
    interpolates a `Path` that its callers supply absolute, so every one of them
    puts a full filesystem path on stderr. Repairing that at the five call sites
    would leave the sixth site somebody adds later, and repairing it inside
    `core/atomic_io.py` could not express "console but not file" at all: this
    module caches ONE console handler and ONE file handler in module globals and
    shares both process-wide, so a library module has no handle on either. This
    module already owns a console-only rendering decision in `_ColorFormatter`.
    Redaction is that same decision one notch further out.

    WHY A FORMATTER AND NOT A `logging.Filter`. `get_logger` attaches the
    console handler FIRST and the file handler SECOND, and both receive the SAME
    `LogRecord` object. A filter - or anything else that edited `record.msg` or
    `record.args` in place - would therefore redact the day log as well, turning
    "do not surface this" into "do not record this", which is the opposite
    instruction. This class touches only the string `super().format()` returns,
    so the record it was handed is unchanged when the file handler formats it
    next. `_ColorFormatter` already relies on exactly that discipline for its
    `levelname` restoration.

    WHAT IS REDACTED, AND WHAT DELIBERATELY IS NOT. Only the repo-root prefix
    and the user-profile prefix, and only the prefix - everything after it,
    including the basename, survives untouched. That is not a small point. The
    "file logging disabled" warning in `_ensure_file` below carries a path as
    its only useful content on a console-only degraded run, and an operator
    reading any of the five `core/atomic_io.py` reports has to be able to tell
    WHICH file failed. A blanket path scrubber would gut both. `<repo>\\state`
    still names the file; `<redacted>` would not.

    DEGRADES RATHER THAN RAISES. If a prefix cannot be resolved, it simply is
    not redacted. A formatter that raises converts a logged error into a logging
    error and loses both of them.
    """

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        try:
            for pattern, marker in _console_redaction_rules():
                rendered = pattern.sub(marker, rendered)
        except (OSError, RuntimeError, re.error):
            # Unresolvable prefix or a pathological pattern. Emitting the
            # unredacted line is strictly better than emitting nothing.
            return rendered
        return rendered


def log_path_for(day: date | None = None) -> Path:
    """Absolute path of the log file for `day`, defaulting to today."""
    cfg = load_config()
    stamp = (day or date.today()).strftime("%Y-%m-%d")
    return cfg.log_dir / f"{stamp}.log"


def _resolve_level(name: str) -> int:
    level = logging.getLevelName(name.upper())
    return level if isinstance(level, int) else logging.INFO


def _ensure_console() -> logging.Handler:
    global _console_handler
    if _console_handler is None:
        handler = logging.StreamHandler(stream=sys.stderr)
        # The redacting subclass, on the CONSOLE handler only. `_ensure_file`
        # below keeps the plain `logging.Formatter`, so the day log still
        # records the raw absolute path that an operator needs in order to act
        # on the failure.
        handler.setFormatter(_RedactingColorFormatter(_LINE_FORMAT, datefmt=_TIME_FORMAT))
        _console_handler = handler
    return _console_handler


def _ensure_file() -> logging.Handler | None:
    """Return today's file handler, creating or swapping it as needed.

    Returns None when file logging is unavailable. That is a degraded mode, not
    an error: the console handler still carries every line.
    """
    global _file_handler, _file_handler_day, _file_handler_failed
    today = date.today().strftime("%Y-%m-%d")
    if _file_handler is not None and _file_handler_day == today:
        return _file_handler
    if _file_handler_failed and _file_handler is None and _file_handler_day == today:
        return None

    target = log_path_for()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(target, encoding="utf-8")
    except OSError as exc:
        _file_handler_failed = True
        _file_handler_day = today
        # Console-only from here. Reported through the raw stdlib logger so this
        # does not recurse back into get_logger.
        logging.getLogger(__name__).warning(
            "file logging disabled, %s writing to %s", exc.__class__.__name__, target
        )
        return None

    handler.setFormatter(logging.Formatter(_LINE_FORMAT, datefmt=_TIME_FORMAT))
    previous = _file_handler
    _file_handler = handler
    _file_handler_day = today
    _file_handler_failed = False

    if previous is not None:
        # Day rolled over. Move every already-configured logger onto the new
        # file before closing the old one, so no line is dropped.
        for name in _configured_names:
            logger = logging.getLogger(name)
            if previous in logger.handlers:
                logger.removeHandler(previous)
            logger.addHandler(handler)
        previous.close()
    return handler


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Safe to call any number of times.

    Idempotent on two axes: the same name never gains a second copy of a
    handler, and repeated calls across a midnight boundary swap the file handler
    rather than stacking one per day.
    """
    logger = logging.getLogger(name)
    level = _resolve_level(load_config().log_level)
    logger.setLevel(level)
    # Own handlers only. Propagating as well would double every line whenever a
    # host process has also configured the root logger.
    logger.propagate = False

    console = _ensure_console()
    console.setLevel(level)
    if console not in logger.handlers:
        logger.addHandler(console)

    file_handler = _ensure_file()
    if file_handler is not None:
        file_handler.setLevel(level)
        if file_handler not in logger.handlers:
            logger.addHandler(file_handler)

    _configured_names.add(name)
    return logger
