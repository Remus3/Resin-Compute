"""Atomic state IO - the ONLY sanctioned write path for state files.

The rule, inherited verbatim from Sibling-C (docs/SPEC_SCAFFOLD.md section
2):

    Atomic writes only: `tmp.write_text(...); tmp.replace(target)`. Never write
    a state file in place.

WHY it exists, which is the part that keeps getting forgotten: readers poll
mid-write. In the parent project an overlay reads the JSON on a timer with no
lock, so a plain `open(path, "w")` truncates the file to zero bytes and the very
next poll parses an empty or half-serialized document. The consumer then either
crashes or, worse, silently treats a truncated document as the real state.

`Path.replace` is a single rename on the same filesystem, so a reader sees
either the whole old file or the whole new file and never a partial one. The
temp file is created as a SIBLING of the target for exactly that reason: a temp
in the system temp dir is usually on a different filesystem, where replace
degrades to a copy and stops being atomic.

Everything here is fail-soft. A write returns a bool and logs the raw error;
`read_json` returns the caller's default and never raises. Per the hard rule, a
raw exception string is never handed back to a caller.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.log_setup import get_logger

_log = get_logger(__name__)

_ENCODING = "utf-8"

# Newline policy on the temp write. `Path.write_text` defaults to
# `newline=None`, which is NOT "leave the text alone" - it translates every
# "\n" the caller passed into `os.linesep`, so on Windows this module used to
# emit CRLF for text the caller wrote with LF. Measured in this tree:
# `atomic_write_text(p, "a\nb\n")` produced `b'a\r\nb\r\n'`, and a caller who
# deliberately passed CRLF got `b'a\r\r\nb\r\r\n'` - the CR kept, the LF
# expanded underneath it.
#
# That matters here rather than being a style point. `.gitattributes` declares
# `* text=auto eol=lf` and `tests/test_line_endings.py` fails any tracked file
# that declares eol=lf and carries CRLF on disk. This module is named by
# CLAUDE.md as the ONLY sanctioned state-write path, so the first TRACKED file
# anything wrote through it would have turned the suite red - and `git diff`
# would have shown nothing at all, because the index normalises the ending
# away on the way in.
#
# `newline="\n"` disables the translation layer outright: what the caller
# handed in is what lands on disk. It is deliberately NOT a normalisation - a
# caller who passes CRLF still gets CRLF, because rewriting a caller's bytes is
# the defect being fixed, not the fix. `os.linesep` would reintroduce exactly
# the platform dependence this removes.
_NEWLINE = "\n"


def _temp_path(target: Path) -> Path:
    """Return a unique sibling temp path.

    Sibling, so `replace` stays a same-filesystem rename. Unique per process and
    per call, so two writers racing on one target cannot corrupt each other's
    temp file - the rename is still last-writer-wins, but neither ever observes
    a mixed one.
    """
    return target.with_name(f".{target.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp")


def _discard(tmp: Path) -> None:
    """Delete a temp file, swallowing any failure to remove it."""
    try:
        tmp.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("could not remove temp file %s: %s", tmp, exc)


def atomic_write_text(path: str | os.PathLike[str], text: str) -> bool:
    """Write `text` to `path` atomically. Returns True on success.

    Creates parent directories as needed. On any OS-level failure the target is
    left exactly as it was, the temp file is removed, and False is returned.

    The bytes on disk are the caller's bytes. `newline=_NEWLINE` is what makes
    that true, and it is load-bearing rather than cosmetic - see `_NEWLINE`.
    """
    target = Path(path)
    tmp = _temp_path(target)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding=_ENCODING, newline=_NEWLINE)
        tmp.replace(target)
        return True
    except OSError as exc:
        _log.error("atomic_write_text failed for %s: %s: %s", target, exc.__class__.__name__, exc)
        _discard(tmp)
        return False


def atomic_write_json(path: str | os.PathLike[str], obj: Any) -> bool:
    """Serialize `obj` as JSON and write it atomically. Returns True on success.

    Serialization happens BEFORE the temp file is opened, so an unserializable
    object cannot leave a stray temp behind. `ensure_ascii=True` is deliberate:
    this tree is 7-bit ASCII by rule, and it also keeps a non-ASCII game name in
    a data value from becoming an encoding question at read time.
    """
    target = Path(path)
    try:
        payload = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        _log.error("atomic_write_json could not serialize payload for %s: %s: %s",
                   target, exc.__class__.__name__, exc)
        return False
    return atomic_write_text(target, payload + "\n")


def read_json(path: str | os.PathLike[str], default: Any = None) -> Any:
    """Read JSON from `path`, returning `default` instead of ever raising.

    A missing file is NOT an error: absent state is the default state, and that
    case is not logged. A corrupt or undecodable file IS logged, at error, with
    the raw parse failure - and the caller still gets `default`, so a poisoned
    state file degrades the run instead of ending it.
    """
    target = Path(path)
    try:
        raw = target.read_text(encoding=_ENCODING)
    except FileNotFoundError:
        return default
    except (OSError, UnicodeDecodeError) as exc:
        _log.error("read_json could not read %s: %s: %s", target, exc.__class__.__name__, exc)
        return default

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _log.error("read_json found corrupt JSON in %s: %s: %s", target, exc.__class__.__name__, exc)
        return default
