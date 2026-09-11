"""An in-process write tracer that states its own coverage, and its own holes.

WHY THIS EXISTS, AND WHAT IT IS AN ANSWER TO. Two ad-hoc in-process tracers were
used on 2026-09-11 to take "0 bytes written" readings. Both of them missed the
same two things, and both readings were therefore statements about the shapes
those tracers happened to patch rather than about the disk:

  1. The `os.open` plus `os.write` / `os.fdopen` route was invisible, because
     `os.write` is handed an INT and no path ever matched a path filter. That
     shape is live in this tree at `ops/loop/slots.py:189` and `:195`, in the
     code that writes the machine-wide bucket the halt ruling names by name.
  2. Neither patched DELETION or TRUNCATION at all, while this tree calls
     `shutil.rmtree` at session finish and `unlink` in nine files.

So the defect being closed is a defect OF AN INSTRUMENT: it overstated its
coverage by saying nothing about it. This module therefore publishes both
`COVERED_ROUTES` and `UNCOVERED_ROUTES`, and `tests/test_write_tracer.py`
asserts that every covered route is really patched and really restored, that
every patched route is really listed, and that neither list is silent about a
route family the other one also omits.

THE FOUR OP VALUES. `write`, `truncate`, `delete` and `create`. `create` is the
answer to a measured silent gap: `os.open(p, O_CREAT | O_EXCL)`, `Path.touch()`
and `open(p, "x")` each brought a file into existence and produced NO event at
all, so a "0 bytes written" reading over the lock-file creation at
`ops/loop/slots.py:189` would have read CLEAN while the files appeared. An
EMPTY file that was not there before is a filesystem mutation, and an instrument
that reports zero bytes for it is reporting the wrong question's answer.

WHEN AN EVENT IS RECORDED, relative to the call it describes. `write` and
`truncate` are recorded BEFORE the wrapped call runs, because bytes that may
have reached disk must never be silent - a failed call that wrote a partial
buffer is still a mutation. `create` is recorded AFTER the call SUCCEEDS,
because a create that did not happen is a positively wrong reading, and a wrong
path is worse than no path.

HOW ATTRIBUTION WORKS FOR A DESCRIPTOR. `os.open` is wrapped, and the path it
was given is recorded in a `fd -> path` map keyed on the descriptor it returns.
`os.write`, `os.fdopen`, `os.truncate` and `os.ftruncate` consult that map;
`os.close` and a traced file object's `close` evict from it. `os.dup` copies the
entry onto the new descriptor, and `os.dup2` either copies the source entry onto
the target or EVICTS the target's entry when the source has none - without that
eviction `dup2`'s implicit close leaves a stale entry behind and the next write
is reported against a path the bytes never reached. A descriptor with no entry
is NOT dropped - it is recorded as `<unattributed fd N>`, because silence is
never an answer and a dropped event is indistinguishable from a quiet disk.

WHAT IT CANNOT SEE. Stated here as well as in `UNCOVERED_ROUTES`, because an
instrument that overstates its coverage is the exact defect this module closes:

  - Writes performed by a CHILD PROCESS - `subprocess`, `os.system`, any exec.
    Only this interpreter's own calls are wrapped.
  - Writes from a C EXTENSION that reaches the filesystem without going through
    the `os` module or Python-level file objects.
  - `mmap` stores. A store into a mapping is a memory write that the kernel
    flushes later; no wrapped call is involved.
  - PATH ATTRIBUTION for a descriptor opened BEFORE the context was entered and
    written with the raw `os.write(fd, data)` form. The BYTES are recorded, as
    `<unattributed fd N>`; the path is not.
  - ALL OF IT - bytes included - for a FILE OBJECT opened before entry.
    A file object opened before entry is a plain builtin object whose `write`
    reaches the C-level writer directly without passing through any wrapped
    name, so nothing at all is recorded. MEASURED 2026-09-11 on CPython 3.14.4
    and 3.11.9: `open(p, "wb", buffering=0)` before the context, one 9-byte
    write inside it, 9 bytes on disk and ZERO events. This is a SEPARATE
    sub-case from the raw-`os.write` one above and must not be folded into it -
    the earlier wording claimed the bytes were recorded for both, and that
    claim was false for this half.
  - `io.FileIO` constructed directly. It is a C type whose `write` cannot be
    replaced, so `io.FileIO(path, "w").write(...)` is invisible. `open` and
    `Path.open` are covered because the wrapper sits on the OPENER, not on the
    type it returns.
  - METADATA-ONLY operations. `os.utime`, `os.chmod`, `os.chown` and
    `Path.touch` on a file that already exists change no bytes and are not
    reported.
  - DIRECTORY-level operations. `os.mkdir`, `os.makedirs`, `os.rmdir`,
    `Path.mkdir` and `Path.rmdir` are not wrapped, so creating or removing an
    EMPTY directory produces no event. `shutil.rmtree` and the shutil copy
    family ARE covered, and each records ONE aggregate event on the tree root.
  - Anything at all after the context manager exits. Every name is restored on
    the way out, including on an exception.

MEASURED HERE, 2026-09-11, under CPython 3.14.4 and 3.11.9: `Path.rename` and
`Path.replace` are NOT patched by name and do not need to be - they delegate to
`os.rename` / `os.replace`, which are, so a `Path.rename` inside the context
yields one `write` event on the destination. That is an observation about these
interpreters rather than a language guarantee; if a future version stops
delegating, the route arms for `os.rename` and `os.replace` still hold and this
sentence is the thing that has gone stale.

ALSO MEASURED 2026-09-11, and the reason the shutil copy family is patched by
name rather than left to fall through `builtins.open`: on CPython 3.14.4 for
Windows, `shutil.copy2` produced ZERO events through the unpatched module,
because `shutil.copyfile` takes a native fast path that never calls `open`.
Relying on transitive coverage there would have been an overstatement on one
platform and correct on another.

DOUBLE COUNTING, and why a re-entrancy guard is correct rather than convenient.
`Path.write_text` calls `Path.open`, which calls `io.open`; `shutil.rmtree`
calls `os.unlink`; `shutil.copytree` calls `shutil.copy2`. Recording each layer
would report one logical write three times. Only the OUTERMOST wrapped call on a
thread records, so `p.write_text("abcd")` yields exactly one `write` of 4 bytes
and no nested `truncate`. Byte counts are therefore per logical call, not per
syscall, and `shutil.copytree` reports one `write` carrying the total size of
the source tree.

NOTHING HERE RAISES THROUGH A WRAPPED CALL. Size measurement and path
stringification are guarded, the original callable is always invoked, and its
own exception propagates untouched - `open` on a missing directory still raises
its own `OSError` and never a tracer error.
"""
from __future__ import annotations

import builtins
import io
import os
import shutil
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Routes that are actually patched. An entry beginning with "<" is mediated by
# the wrapper this module puts around a file object returned by one of the
# patched openers, or is a MODE of a patched opener rather than a name of its
# own, so it has no dotted name to resolve; `tests/test_write_tracer.py` maps
# each of those to a dedicated arm by name and resolves every other entry by
# attribute. The dotted entries must equal `PATCH_TARGETS` in BOTH directions,
# which is what stops a route being patched without ever being listed.
COVERED_ROUTES: tuple[str, ...] = (
    "builtins.open",
    "io.open",
    "pathlib.Path.open",
    "pathlib.Path.write_text",
    "pathlib.Path.write_bytes",
    "pathlib.Path.unlink",
    "pathlib.Path.touch",
    "os.open",
    "os.write",
    "os.close",
    "os.dup",
    "os.dup2",
    "os.fdopen",
    "os.replace",
    "os.rename",
    "os.remove",
    "os.unlink",
    "os.truncate",
    "os.ftruncate",
    "os.link",
    "os.symlink",
    "shutil.rmtree",
    "shutil.copyfile",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copytree",
    "<file object>.write",
    "<file object>.writelines",
    "<file object>.truncate",
    '<open(mode="x")>',
)

# Shapes this tracer deliberately does NOT see. Kept in the same order as the
# docstring paragraph above, which carries the reasoning for each. A route that
# is in NEITHER list is the silent class, and silence is the failure that
# conservation arithmetic cannot catch, so a route family belongs in exactly
# one of these two tuples.
UNCOVERED_ROUTES: tuple[str, ...] = (
    "child-process writes - subprocess, os.system, any exec",
    "writes from a C extension that bypasses the os module and Python file objects",
    "mmap stores - a memory write the kernel flushes with no wrapped call involved",
    "path attribution for a descriptor opened before the tracer was entered and written "
    "with the raw os.write(fd, data) form - the BYTES are recorded as <unattributed fd N>, "
    "the path is not",
    "everything, bytes included, for a file object opened before the tracer was entered "
    "- a file object opened before entry is a plain builtin object whose write reaches the "
    "C-level writer with no wrapped name in the path, so NOTHING is recorded; measured "
    "2026-09-11 on CPython 3.14.4 and 3.11.9 as 9 bytes on disk and 0 events",
    "io.FileIO constructed directly - a C type whose write cannot be replaced; open and "
    "Path.open are covered because the wrapper sits on the OPENER, not on the type",
    "metadata-only operations - os.utime, os.chmod, os.chown, and a touch of a file that "
    "ALREADY EXISTS, change no bytes and produce no event",
    "directory-level operations - os.mkdir, os.makedirs, os.rmdir, Path.mkdir, Path.rmdir "
    "- creating or removing an EMPTY directory produces no event; rmtree and the shutil "
    "copy family are covered and each record ONE aggregate event on the tree root",
    "anything after the context manager exits - every name is restored on the way out",
)

# The implementation's own patch table, published so a test can compare it
# against COVERED_ROUTES in both directions. A test that derived the claim from
# this would be circular, so the test derives the NAME from the owner object
# here and compares it to the hand-written tuple above.
PATCH_TARGETS: tuple[tuple[Any, str], ...] = (
    (builtins, "open"),
    (io, "open"),
    (Path, "open"),
    (Path, "write_text"),
    (Path, "write_bytes"),
    (Path, "unlink"),
    (Path, "touch"),
    (os, "open"),
    (os, "write"),
    (os, "close"),
    (os, "dup"),
    (os, "dup2"),
    (os, "fdopen"),
    (os, "replace"),
    (os, "rename"),
    (os, "remove"),
    (os, "unlink"),
    (os, "truncate"),
    (os, "ftruncate"),
    (os, "link"),
    (os, "symlink"),
    (shutil, "rmtree"),
    (shutil, "copyfile"),
    (shutil, "copy"),
    (shutil, "copy2"),
    (shutil, "copytree"),
)

_WRITE_MODE_CHARS = frozenset("wax+")


@dataclass(frozen=True)
class WriteEvent:
    """One recorded filesystem mutation.

    `op` is one of write, delete, truncate or create. `create` means a path that
    did not exist before the call exists after it; its `nbytes` is 0, because an
    empty file that was not there before is a mutation with no bytes in it.
    """

    op: str
    path: str
    nbytes: int


def _as_text(path: Any) -> str:
    """Never raises. A path this cannot render is still recorded, as its repr."""
    try:
        return os.fspath(path) if not isinstance(path, str) else path
    except (TypeError, ValueError):
        return repr(path)


def _nbytes_of(data: Any) -> int:
    """Best-effort byte count. Never raises - an unmeasurable payload is 0."""
    try:
        if isinstance(data, str):
            return len(data.encode("utf-8", "surrogateescape"))
        if isinstance(data, memoryview):
            return int(data.nbytes)
        return len(data)
    except (TypeError, ValueError, UnicodeError, AttributeError):
        return 0


def _mode_of(args: tuple[Any, ...], kwargs: dict[str, Any], index: int, default: str) -> str:
    mode = kwargs.get("mode", args[index] if len(args) > index else default)
    return mode if isinstance(mode, str) else default


def _is_write_mode(mode: str) -> bool:
    return bool(_WRITE_MODE_CHARS & set(mode))


def _exists(target: Any) -> bool:
    """Never raises. `os.stat` is not a patched route, so this cannot recurse."""
    try:
        os.stat(target)
    except (OSError, TypeError, ValueError):
        return False
    return True


class _TracedFile:
    """Thin pass-through that records `write`, `writelines` and `truncate`.

    Only wraps a file object opened in a WRITE mode, so a read stays an
    untouched builtin object and the negative control in the test module has
    something real to be negative about.
    """

    def __init__(self, fh: Any, path: str, sink: Any, fd: int | None = None) -> None:
        self._rc_fh = fh
        self._rc_path = path
        self._rc_sink = sink
        self._rc_fd = fd

    def write(self, data: Any) -> Any:
        self._rc_sink("write", self._rc_path, _nbytes_of(data))
        return self._rc_fh.write(data)

    def writelines(self, lines: Any) -> Any:
        chunks = list(lines)
        self._rc_sink("write", self._rc_path, sum(_nbytes_of(c) for c in chunks))
        return self._rc_fh.writelines(chunks)

    def truncate(self, size: Any = None) -> Any:
        recorded = size
        if recorded is None:
            try:
                recorded = self._rc_fh.tell()
            except (OSError, ValueError, AttributeError):
                recorded = 0
        self._rc_sink("truncate", self._rc_path, _nbytes_of(b"") + int(recorded or 0))
        if size is None:
            return self._rc_fh.truncate()
        return self._rc_fh.truncate(size)

    def close(self) -> Any:
        try:
            return self._rc_fh.close()
        finally:
            if self._rc_fd is not None:
                self._rc_sink("__evict__", str(self._rc_fd), 0)

    def __enter__(self) -> _TracedFile:
        self._rc_fh.__enter__()
        return self

    def __exit__(self, *exc: Any) -> Any:
        try:
            return self._rc_fh.__exit__(*exc)
        finally:
            if self._rc_fd is not None:
                self._rc_sink("__evict__", str(self._rc_fd), 0)

    def __iter__(self) -> Any:
        return iter(self._rc_fh)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._rc_fh, name)


@contextmanager
def trace_writes() -> Iterator[list[WriteEvent]]:
    """Patch every route in `COVERED_ROUTES` and yield the list events land in.

    The list is live: it fills as calls happen inside the block. Every patched
    name is restored on the way out, including when an exception leaves the
    block.
    """
    events: list[WriteEvent] = []
    fd_paths: dict[int, str] = {}
    state = threading.local()

    def _depth() -> int:
        return int(getattr(state, "depth", 0))

    def _enter() -> None:
        state.depth = _depth() + 1

    def _leave() -> None:
        state.depth = max(0, _depth() - 1)

    def _sink(op: str, path: str, nbytes: int) -> None:
        # The eviction pseudo-op is how a traced file object tells the fd map it
        # is done, without the map itself being part of the public surface.
        if op == "__evict__":
            try:
                fd_paths.pop(int(path), None)
            except (TypeError, ValueError):
                pass
            return
        events.append(WriteEvent(op, path, int(nbytes)))

    def _path_for_fd(fd: Any) -> str:
        try:
            key = int(fd)
        except (TypeError, ValueError):
            return repr(fd)
        return fd_paths.get(key, f"<unattributed fd {key}>")

    def _size_of(path: Any) -> int:
        try:
            return int(os.stat(path).st_size)
        except (OSError, TypeError, ValueError):
            return 0

    def _tree_size(root: Any) -> int:
        total = 0
        try:
            for where, _dirs, files in os.walk(root):
                for name in files:
                    total += _size_of(os.path.join(where, name))
        except (OSError, TypeError, ValueError):
            return total
        return total

    def _copy_dest(src: Any, dst: Any) -> str:
        """shutil.copy accepts a DIRECTORY as dst. Naming it would be a wrong path."""
        try:
            if os.path.isdir(dst):
                return os.path.join(_as_text(dst), os.path.basename(_as_text(src)))
        except (OSError, TypeError, ValueError):
            pass
        return _as_text(dst)

    originals: list[tuple[Any, str, Any]] = []

    def _orig(owner: Any, attr: str) -> Any:
        for o, a, fn in originals:
            if o is owner and a == attr:
                return fn
        raise AssertionError(f"no original recorded for {attr}")

    # ---- wrappers ---------------------------------------------------------

    def _wrap_open(owner: Any, attr: str, mode_index: int) -> Any:
        def _opened(*args: Any, **kwargs: Any) -> Any:
            original = _orig(owner, attr)
            if _depth() > 0:
                return original(*args, **kwargs)
            target = args[0] if args else kwargs.get("file", kwargs.get("self"))
            mode = _mode_of(args, kwargs, mode_index, "r")
            path = _as_text(target)
            writing = _is_write_mode(mode)
            existed = True if not writing else _exists(target)
            if writing and "w" in mode:
                _sink("truncate", path, 0)
            _enter()
            try:
                fh = original(*args, **kwargs)
            finally:
                _leave()
            if writing and not existed:
                _sink("create", path, 0)
            if not writing:
                return fh
            return _TracedFile(fh, path, _sink)

        return _opened

    def _wrap_path_open() -> Any:
        def _opened(self: Path, *args: Any, **kwargs: Any) -> Any:
            original = _orig(Path, "open")
            if _depth() > 0:
                return original(self, *args, **kwargs)
            mode = _mode_of(args, kwargs, 0, "r")
            path = _as_text(self)
            writing = _is_write_mode(mode)
            existed = True if not writing else _exists(self)
            if writing and "w" in mode:
                _sink("truncate", path, 0)
            _enter()
            try:
                fh = original(self, *args, **kwargs)
            finally:
                _leave()
            if writing and not existed:
                _sink("create", path, 0)
            if not writing:
                return fh
            return _TracedFile(fh, path, _sink)

        return _opened

    def _wrap_write_text() -> Any:
        def _written(self: Path, data: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(Path, "write_text")
            if _depth() > 0:
                return original(self, data, *args, **kwargs)
            existed = _exists(self)
            _sink("write", _as_text(self), _nbytes_of(data))
            _enter()
            try:
                result = original(self, data, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(self), 0)
            return result

        return _written

    def _wrap_write_bytes() -> Any:
        def _written(self: Path, data: Any) -> Any:
            original = _orig(Path, "write_bytes")
            if _depth() > 0:
                return original(self, data)
            existed = _exists(self)
            _sink("write", _as_text(self), _nbytes_of(data))
            _enter()
            try:
                result = original(self, data)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(self), 0)
            return result

        return _written

    def _wrap_path_touch() -> Any:
        def _touched(self: Path, *args: Any, **kwargs: Any) -> Any:
            original = _orig(Path, "touch")
            if _depth() > 0:
                return original(self, *args, **kwargs)
            existed = _exists(self)
            _enter()
            try:
                result = original(self, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(self), 0)
            return result

        return _touched

    def _wrap_path_unlink() -> Any:
        def _unlinked(self: Path, *args: Any, **kwargs: Any) -> Any:
            original = _orig(Path, "unlink")
            if _depth() > 0:
                return original(self, *args, **kwargs)
            _sink("delete", _as_text(self), 0)
            _enter()
            try:
                return original(self, *args, **kwargs)
            finally:
                _leave()

        return _unlinked

    def _wrap_os_open() -> Any:
        def _opened(*args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "open")
            if _depth() > 0:
                return original(*args, **kwargs)
            target = args[0] if args else kwargs.get("path")
            flags = args[1] if len(args) > 1 else kwargs.get("flags", 0)
            path = _as_text(target)
            existed = _exists(target)
            _enter()
            try:
                fd = original(*args, **kwargs)
            finally:
                _leave()
            try:
                fd_paths[int(fd)] = path
            except (TypeError, ValueError):
                pass
            if not existed:
                _sink("create", path, 0)
            try:
                if int(flags) & os.O_TRUNC:
                    _sink("truncate", path, 0)
            except (TypeError, ValueError):
                pass
            return fd

        return _opened

    def _wrap_os_write() -> Any:
        def _written(fd: Any, data: Any) -> Any:
            original = _orig(os, "write")
            if _depth() > 0:
                return original(fd, data)
            _sink("write", _path_for_fd(fd), _nbytes_of(data))
            _enter()
            try:
                return original(fd, data)
            finally:
                _leave()

        return _written

    def _wrap_os_close() -> Any:
        def _closed(fd: Any) -> Any:
            original = _orig(os, "close")
            try:
                return original(fd)
            finally:
                try:
                    fd_paths.pop(int(fd), None)
                except (TypeError, ValueError):
                    pass

        return _closed

    def _wrap_os_dup() -> Any:
        def _duped(fd: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "dup")
            new_fd = original(fd, *args, **kwargs)
            try:
                known = fd_paths.get(int(fd))
                if known is not None:
                    fd_paths[int(new_fd)] = known
                else:
                    fd_paths.pop(int(new_fd), None)
            except (TypeError, ValueError):
                pass
            return new_fd

        return _duped

    def _wrap_os_dup2() -> Any:
        def _duped(fd: Any, fd2: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "dup2")
            result = original(fd, fd2, *args, **kwargs)
            # dup2 implicitly CLOSES fd2 and rebinds it to whatever fd points
            # at. Leaving fd2's old entry in place makes the next write on it
            # report a path the bytes never reached, which is worse than
            # silence - so an unknown source EVICTS rather than keeps.
            try:
                known = fd_paths.get(int(fd))
                if known is not None:
                    fd_paths[int(fd2)] = known
                else:
                    fd_paths.pop(int(fd2), None)
            except (TypeError, ValueError):
                pass
            return result

        return _duped

    def _wrap_os_fdopen() -> Any:
        def _opened(*args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "fdopen")
            if _depth() > 0:
                return original(*args, **kwargs)
            fd = args[0] if args else kwargs.get("fd")
            mode = _mode_of(args, kwargs, 1, "r")
            path = _path_for_fd(fd)
            _enter()
            try:
                fh = original(*args, **kwargs)
            finally:
                _leave()
            if not _is_write_mode(mode):
                return fh
            key: int | None
            try:
                key = int(fd) if fd is not None else None
            except (TypeError, ValueError):
                key = None
            return _TracedFile(fh, path, _sink, key)

        return _opened

    def _wrap_moved(attr: str) -> Any:
        def _moved(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, attr)
            if _depth() > 0:
                return original(src, dst, *args, **kwargs)
            existed = _exists(dst)
            _sink("write", _as_text(dst), _size_of(src))
            _enter()
            try:
                result = original(src, dst, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(dst), 0)
            return result

        return _moved

    def _wrap_linked(attr: str) -> Any:
        def _linked(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, attr)
            if _depth() > 0:
                return original(src, dst, *args, **kwargs)
            existed = _exists(dst)
            _enter()
            try:
                result = original(src, dst, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(dst), 0)
            return result

        return _linked

    def _wrap_removed(attr: str) -> Any:
        def _removed(path: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, attr)
            if _depth() > 0:
                return original(path, *args, **kwargs)
            _sink("delete", _as_text(path), 0)
            _enter()
            try:
                return original(path, *args, **kwargs)
            finally:
                _leave()

        return _removed

    def _wrap_os_truncate() -> Any:
        def _truncated(path: Any, length: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "truncate")
            if _depth() > 0:
                return original(path, length, *args, **kwargs)
            name = _path_for_fd(path) if isinstance(path, int) else _as_text(path)
            _sink("truncate", name, _nbytes_of(b"") + int(length or 0))
            _enter()
            try:
                return original(path, length, *args, **kwargs)
            finally:
                _leave()

        return _truncated

    def _wrap_os_ftruncate() -> Any:
        def _truncated(fd: Any, length: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(os, "ftruncate")
            if _depth() > 0:
                return original(fd, length, *args, **kwargs)
            _sink("truncate", _path_for_fd(fd), int(length or 0))
            _enter()
            try:
                return original(fd, length, *args, **kwargs)
            finally:
                _leave()

        return _truncated

    def _wrap_rmtree() -> Any:
        def _removed(path: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(shutil, "rmtree")
            if _depth() > 0:
                return original(path, *args, **kwargs)
            _sink("delete", _as_text(path), 0)
            _enter()
            try:
                return original(path, *args, **kwargs)
            finally:
                _leave()

        return _removed

    def _wrap_copied(attr: str) -> Any:
        def _copied(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(shutil, attr)
            if _depth() > 0:
                return original(src, dst, *args, **kwargs)
            landing = _copy_dest(src, dst)
            existed = _exists(landing)
            _sink("write", landing, _size_of(src))
            _enter()
            try:
                result = original(src, dst, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", landing, 0)
            return result

        return _copied

    def _wrap_copytree() -> Any:
        def _copied(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
            original = _orig(shutil, "copytree")
            if _depth() > 0:
                return original(src, dst, *args, **kwargs)
            existed = _exists(dst)
            _sink("write", _as_text(dst), _tree_size(src))
            _enter()
            try:
                result = original(src, dst, *args, **kwargs)
            finally:
                _leave()
            if not existed:
                _sink("create", _as_text(dst), 0)
            return result

        return _copied

    # ---- install ----------------------------------------------------------

    for owner, attr in PATCH_TARGETS:
        originals.append((owner, attr, getattr(owner, attr)))

    replacements: dict[tuple[int, str], Any] = {
        (id(builtins), "open"): _wrap_open(builtins, "open", 1),
        (id(io), "open"): _wrap_open(io, "open", 1),
        (id(Path), "open"): _wrap_path_open(),
        (id(Path), "write_text"): _wrap_write_text(),
        (id(Path), "write_bytes"): _wrap_write_bytes(),
        (id(Path), "unlink"): _wrap_path_unlink(),
        (id(Path), "touch"): _wrap_path_touch(),
        (id(os), "open"): _wrap_os_open(),
        (id(os), "write"): _wrap_os_write(),
        (id(os), "close"): _wrap_os_close(),
        (id(os), "dup"): _wrap_os_dup(),
        (id(os), "dup2"): _wrap_os_dup2(),
        (id(os), "fdopen"): _wrap_os_fdopen(),
        (id(os), "replace"): _wrap_moved("replace"),
        (id(os), "rename"): _wrap_moved("rename"),
        (id(os), "remove"): _wrap_removed("remove"),
        (id(os), "unlink"): _wrap_removed("unlink"),
        (id(os), "truncate"): _wrap_os_truncate(),
        (id(os), "ftruncate"): _wrap_os_ftruncate(),
        (id(os), "link"): _wrap_linked("link"),
        (id(os), "symlink"): _wrap_linked("symlink"),
        (id(shutil), "rmtree"): _wrap_rmtree(),
        (id(shutil), "copyfile"): _wrap_copied("copyfile"),
        (id(shutil), "copy"): _wrap_copied("copy"),
        (id(shutil), "copy2"): _wrap_copied("copy2"),
        (id(shutil), "copytree"): _wrap_copytree(),
    }

    try:
        for owner, attr in PATCH_TARGETS:
            setattr(owner, attr, replacements[(id(owner), attr)])
        yield events
    finally:
        for owner, attr, original in originals:
            setattr(owner, attr, original)
