"""Logging setup - one log file per day, no rotation.

Operator preference inherited verbatim from Sibling-C:

    Logs live at logs/YYYY-MM-DD.log. One file per calendar day. NO rotation,
    no size cap, no RotatingFileHandler. A day is the unit an operator greps.

Console output is colour-coded per level so a warning is visible in a scrolling
terminal; the file handler is deliberately PLAIN, because ANSI escape bytes in
a log file break `grep`, `less` and every downstream reader.

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
import sys
from datetime import date
from pathlib import Path

from core.config import load_config

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
        handler.setFormatter(_ColorFormatter(_LINE_FORMAT, datefmt=_TIME_FORMAT))
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
