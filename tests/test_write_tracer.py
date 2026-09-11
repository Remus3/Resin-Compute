"""Arms for `tools/write_tracer.py`.

WHY EVERY FIXTURE HERE IS HAND-WRITTEN. The row this module closes is about an
INSTRUMENT that overstated its own coverage, so a test that builds its fixture
out of the value it pins would reproduce the exact defect one layer up: a shape
arm generated from `COVERED_ROUTES` passes for any `COVERED_ROUTES`, including
an empty one and including one naming a route nobody patched. Nothing below
iterates `COVERED_ROUTES` to decide WHAT to call. Each route arm spells the
literal call shape out, and the `os.open` plus `os.fdopen` arm copies the shape
at `ops/loop/slots.py:189` and `:195` by hand.

The coverage-honesty arm DOES iterate `COVERED_ROUTES` - that is a different
question. It asks whether every route the module CLAIMS is patched and restored,
which is a statement about the claim rather than about the syscalls, and it
cannot stand in for the per-route arms above it.
"""
from __future__ import annotations

import builtins
import importlib
import io
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import write_tracer  # noqa: E402
from tools.write_tracer import COVERED_ROUTES, UNCOVERED_ROUTES, WriteEvent, trace_writes  # noqa: E402


def _ops(events, op):
    return [e for e in events if e.op == op]


def _paths(events, op=None):
    return [e.path for e in events if op is None or e.op == op]


# --------------------------------------------------------------------------
# One arm per route. Each drives the REAL call, hand-written.
# --------------------------------------------------------------------------


def test_os_open_plus_os_fdopen_is_attributed_to_the_path(tmp_path):
    """THE PRIMARY HOLE. Shape copied by hand from ops/loop/slots.py:189,195."""
    p = tmp_path / "0.lock"
    with trace_writes() as events:
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("x")
    writes = _ops(events, "write")
    assert writes, f"the os.open plus os.fdopen route produced no write event: {events}"
    assert [e.path for e in writes] == [str(p)], (
        "the descriptor was not attributed back to the path recorded at "
        f"os.open time: {writes}"
    )
    assert sum(e.nbytes for e in writes) == 1
    assert p.read_text(encoding="utf-8") == "x", "the tracer changed the real effect of the call"


def test_os_open_plus_os_write_is_attributed_to_the_path(tmp_path):
    p = tmp_path / "raw.bin"
    with trace_writes() as events:
        fd = os.open(str(p), os.O_CREAT | os.O_WRONLY)
        try:
            os.write(fd, b"hello")
        finally:
            os.close(fd)
    assert WriteEvent("write", str(p), 5) in events, events


def test_builtins_open_w_records_a_truncate_distinct_from_the_bytes(tmp_path):
    p = tmp_path / "b.txt"
    p.write_bytes(b"old content")
    with trace_writes() as events:
        with builtins.open(p, "w", encoding="utf-8") as fh:
            fh.write("new")
    truncates = _ops(events, "truncate")
    writes = _ops(events, "write")
    assert truncates, f'open(mode="w") recorded no truncate event: {events}'
    assert [e.path for e in truncates] == [str(p)]
    assert writes, f"the bytes written after the truncate were not recorded: {events}"
    assert sum(e.nbytes for e in writes) == 3


def test_io_open_is_seen(tmp_path):
    p = tmp_path / "io.txt"
    with trace_writes() as events:
        with io.open(p, "a", encoding="utf-8") as fh:  # noqa: UP020
            fh.write("ab")
    assert WriteEvent("write", str(p), 2) in events, events


def test_path_open_is_seen(tmp_path):
    p = tmp_path / "po.txt"
    with trace_writes() as events:
        with p.open("a", encoding="utf-8") as fh:
            fh.write("abc")
    assert WriteEvent("write", str(p), 3) in events, events


def test_path_write_text_is_seen(tmp_path):
    p = tmp_path / "wt.txt"
    with trace_writes() as events:
        p.write_text("abcd", encoding="utf-8")
    assert WriteEvent("write", str(p), 4) in events, events


def test_path_write_bytes_is_seen(tmp_path):
    p = tmp_path / "wb.bin"
    with trace_writes() as events:
        p.write_bytes(b"abcde")
    assert WriteEvent("write", str(p), 5) in events, events


def test_os_replace_is_seen(tmp_path):
    src = tmp_path / "src.tmp"
    dst = tmp_path / "dst.json"
    src.write_bytes(b"abcd")
    with trace_writes() as events:
        os.replace(src, dst)
    assert WriteEvent("write", str(dst), 4) in events, events


def test_os_rename_is_seen(tmp_path):
    src = tmp_path / "r_src.tmp"
    dst = tmp_path / "r_dst.json"
    src.write_bytes(b"abc")
    with trace_writes() as events:
        os.rename(src, dst)
    assert WriteEvent("write", str(dst), 3) in events, events


def test_os_remove_is_a_delete(tmp_path):
    p = tmp_path / "gone1.txt"
    p.write_bytes(b"x")
    with trace_writes() as events:
        os.remove(p)
    assert WriteEvent("delete", str(p), 0) in events, events


def test_os_unlink_is_a_delete(tmp_path):
    p = tmp_path / "gone2.txt"
    p.write_bytes(b"x")
    with trace_writes() as events:
        os.unlink(p)
    assert WriteEvent("delete", str(p), 0) in events, events


def test_path_unlink_is_a_delete(tmp_path):
    p = tmp_path / "gone3.txt"
    p.write_bytes(b"x")
    with trace_writes() as events:
        p.unlink()
    assert _ops(events, "delete"), f"Path.unlink produced no delete event: {events}"
    assert str(p) in _paths(events, "delete")


def test_shutil_rmtree_is_a_delete(tmp_path):
    d = tmp_path / "tree"
    d.mkdir()
    (d / "a.txt").write_bytes(b"x")
    with trace_writes() as events:
        shutil.rmtree(d)
    assert _ops(events, "delete"), f"shutil.rmtree produced no delete event: {events}"
    assert str(d) in _paths(events, "delete")
    assert not d.exists()


def test_os_truncate_is_a_truncate(tmp_path):
    p = tmp_path / "t.bin"
    p.write_bytes(b"abcdef")
    with trace_writes() as events:
        os.truncate(str(p), 2)
    assert WriteEvent("truncate", str(p), 2) in events, events


def test_a_file_object_truncate_is_a_truncate(tmp_path):
    p = tmp_path / "ft.bin"
    p.write_bytes(b"abcdef")
    with trace_writes() as events:
        with builtins.open(p, "r+b") as fh:
            fh.truncate(3)
    assert WriteEvent("truncate", str(p), 3) in events, events
    assert p.read_bytes() == b"abc"


# --------------------------------------------------------------------------
# Coverage honesty, restoration, attribution, and the negative control.
# --------------------------------------------------------------------------


def _resolve(route):
    """`(owner, attr)` for a dotted route name such as `pathlib.Path.open`."""
    parts = route.split(".")
    for i in range(len(parts) - 1, 0, -1):
        try:
            mod = importlib.import_module(".".join(parts[:i]))
        except ImportError:
            continue
        obj = mod
        for name in parts[i:-1]:
            obj = getattr(obj, name)
        return obj, parts[-1]
    raise AssertionError(f"COVERED_ROUTES names {route!r}, which does not resolve to anything")


def test_covered_routes_is_not_empty_and_names_the_primary_hole():
    """Non-vacuity. An empty tuple satisfies every iteration arm below it."""
    assert len(COVERED_ROUTES) >= 10, COVERED_ROUTES
    assert "os.open" in COVERED_ROUTES
    assert "os.fdopen" in COVERED_ROUTES
    assert "os.write" in COVERED_ROUTES


def test_every_covered_route_is_patched_during_and_restored_after():
    dotted = [r for r in COVERED_ROUTES if not r.startswith("<")]
    assert dotted, "every covered route is wrapper-mediated, so nothing is checkable here"
    before = {r: getattr(*_resolve(r)) for r in dotted}
    with trace_writes():
        for route in dotted:
            owner, attr = _resolve(route)
            assert getattr(owner, attr) is not before[route], (
                f"{route} is listed in COVERED_ROUTES but was never patched"
            )
    for route in dotted:
        owner, attr = _resolve(route)
        assert getattr(owner, attr) is before[route], f"{route} was not restored on exit"


def test_covered_and_uncovered_routes_are_disjoint():
    overlap = set(COVERED_ROUTES) & set(UNCOVERED_ROUTES)
    assert not overlap, f"a route is claimed as both covered and uncovered: {sorted(overlap)}"


def test_uncovered_routes_declares_the_shapes_that_are_not_seen():
    blob = " ".join(UNCOVERED_ROUTES).lower()
    for token in ("subprocess", "c extension", "mmap", "before the tracer", "after the"):
        assert token in blob, f"UNCOVERED_ROUTES does not declare {token!r}: {UNCOVERED_ROUTES}"


def test_an_exception_inside_the_context_still_restores_every_name():
    dotted = [r for r in COVERED_ROUTES if not r.startswith("<")]
    before = {r: getattr(*_resolve(r)) for r in dotted}
    with pytest.raises(RuntimeError, match="boom"):
        with trace_writes():
            raise RuntimeError("boom")
    for route in dotted:
        owner, attr = _resolve(route)
        assert getattr(owner, attr) is before[route], (
            f"{route} stayed patched after an exception left the context"
        )


def test_an_fd_opened_before_the_context_is_unattributed_and_not_dropped(tmp_path):
    p = tmp_path / "pre.bin"
    fd = os.open(str(p), os.O_CREAT | os.O_WRONLY)
    try:
        with trace_writes() as events:
            os.write(fd, b"zz")
    finally:
        os.close(fd)
    assert events, "the write on a pre-opened fd was DROPPED; silence is never an answer"
    assert events == [WriteEvent("write", f"<unattributed fd {fd}>", 2)], events


def test_reading_a_file_produces_no_events(tmp_path):
    """The legitimate neighbour must SURVIVE the sweep."""
    p = tmp_path / "read.txt"
    p.write_text("payload", encoding="utf-8")
    with trace_writes() as events:
        assert p.read_text(encoding="utf-8") == "payload"
        assert p.read_bytes() == b"payload"
        with builtins.open(p, encoding="utf-8") as fh:
            assert fh.read() == "payload"
        with p.open("rb") as fh2:
            assert fh2.read() == b"payload"
        fd = os.open(str(p), os.O_RDONLY)
        try:
            assert os.read(fd, 16) == b"payload"
        finally:
            os.close(fd)
        assert sorted(x.name for x in tmp_path.iterdir()) == ["read.txt"]
    assert events == [], f"reading produced write events: {events}"


def test_a_failing_open_propagates_its_own_error_not_a_tracer_error(tmp_path):
    missing = tmp_path / "nope" / "deeper.txt"
    with trace_writes() as events:
        with pytest.raises((FileNotFoundError, NotADirectoryError, OSError)):
            builtins.open(missing, "w", encoding="utf-8")
        with pytest.raises(OSError):
            os.open(str(missing), os.O_CREAT | os.O_WRONLY)
    assert isinstance(events, list)


def test_the_module_docstring_declares_what_it_cannot_see():
    doc = (write_tracer.__doc__ or "").lower()
    for token in ("subprocess", "mmap", "c extension"):
        assert token in doc, f"the module docstring does not declare {token!r}"


# --------------------------------------------------------------------------
# D1. The pre-context descriptor claim, split into its two real sub-cases.
# --------------------------------------------------------------------------


def test_a_raw_os_write_on_a_pre_context_fd_is_recorded_unattributed(tmp_path):
    """Sub-case ONE, the one the original claim was true for."""
    p = tmp_path / "pre_raw.bin"
    fd = os.open(str(p), os.O_CREAT | os.O_WRONLY)
    try:
        with trace_writes() as events:
            os.write(fd, b"zz")
    finally:
        os.close(fd)
    assert p.stat().st_size == 2, "the bytes never reached disk, so this arm measures nothing"
    assert events == [WriteEvent("write", f"<unattributed fd {fd}>", 2)], events


def test_a_buffered_handle_opened_before_the_context_records_nothing(tmp_path):
    """Sub-case TWO. MEASURED FALSE against the original claim: 9 bytes, 0 events."""
    p = tmp_path / "pre_buffered.bin"
    fh = open(p, "wb", buffering=0)  # noqa: SIM115
    try:
        with trace_writes() as events:
            fh.write(b"ONDISKNOW")
    finally:
        fh.close()
    assert p.stat().st_size == 9, "the bytes never reached disk, so this arm measures nothing"
    assert events == [], (
        "the tracer now sees this shape; the UNCOVERED_ROUTES entry that declares it "
        f"blind is understating and must be corrected: {events}"
    )


def test_the_pre_context_declaration_names_both_sub_cases_separately():
    """D1. A declaration that covers only the raw form must not speak for both."""
    blob = " ".join(UNCOVERED_ROUTES).lower()
    doc = (write_tracer.__doc__ or "").lower()
    for token in ("os.write(fd", "file object opened before"):
        assert token in blob, f"UNCOVERED_ROUTES does not separate the sub-case {token!r}"
        assert token in doc, f"the module docstring does not separate the sub-case {token!r}"


# --------------------------------------------------------------------------
# D2. A positively wrong path must never be emitted.
# --------------------------------------------------------------------------


def test_os_dup2_never_names_the_wrong_path(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    with trace_writes() as events:
        fa = os.open(str(a), os.O_CREAT | os.O_WRONLY)
        fb = os.open(str(b), os.O_CREAT | os.O_WRONLY)
        os.dup2(fa, fb)
        try:
            os.write(fb, b"123456789")
        finally:
            os.close(fb)
            os.close(fa)
    assert a.stat().st_size == 9, "disk says the bytes did not land in a.txt"
    assert b.stat().st_size == 0, "disk says b.txt is not empty"
    assert str(b) not in _paths(events, "write"), (
        f"a POSITIVELY WRONG path was emitted for a write that landed in a.txt: {events}"
    )
    assert [e.path for e in _ops(events, "write")] == [str(a)], events


def test_os_dup_attributes_the_duplicate_to_the_same_path(tmp_path):
    c = tmp_path / "c.txt"
    with trace_writes() as events:
        fc = os.open(str(c), os.O_CREAT | os.O_WRONLY)
        dup_fd = os.dup(fc)
        try:
            os.write(dup_fd, b"xy")
        finally:
            os.close(dup_fd)
            os.close(fc)
    assert c.stat().st_size == 2
    assert [e.path for e in _ops(events, "write")] == [str(c)], (
        "a descriptor duplicated INSIDE the context was reported unattributed, which "
        f"falls outside the declared pre-context limit: {events}"
    )


def test_os_dup2_from_an_unknown_source_evicts_rather_than_keeping_a_stale_name(tmp_path):
    """D2 root cause. dup2 implicitly CLOSES the target, so its old entry is stale.

    Keeping that entry is worse than losing it: the next write on the descriptor
    is then reported against a path the bytes never reached.
    """
    a = tmp_path / "pre_a.txt"
    b = tmp_path / "known_b.txt"
    pre = os.open(str(a), os.O_CREAT | os.O_WRONLY)  # opened BEFORE the context
    try:
        with trace_writes() as events:
            fb = os.open(str(b), os.O_CREAT | os.O_WRONLY)
            os.dup2(pre, fb)
            try:
                os.write(fb, b"123456789")
            finally:
                os.close(fb)
    finally:
        os.close(pre)
    assert a.stat().st_size == 9, "disk says the bytes did not land in pre_a.txt"
    assert b.stat().st_size == 0, "disk says known_b.txt is not empty"
    assert str(b) not in _paths(events, "write"), (
        f"a STALE fd entry named known_b.txt for bytes that landed in pre_a.txt: {events}"
    )
    assert [e.path for e in _ops(events, "write")] == [f"<unattributed fd {fb}>"], events


# --------------------------------------------------------------------------
# D3. File creation is an observable event. This is the ops/loop/slots.py shape.
# --------------------------------------------------------------------------


def test_os_open_o_creat_o_excl_on_a_new_path_is_an_observable_create(tmp_path):
    """Shape copied by hand from ops/loop/slots.py:189 - lock file creation."""
    p = tmp_path / "0.lock"
    with trace_writes() as events:
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    assert p.exists(), "the file was not created, so this arm measures nothing"
    assert WriteEvent("create", str(p), 0) in events, events


def test_path_touch_on_a_new_path_is_an_observable_create(tmp_path):
    p = tmp_path / "touched.txt"
    with trace_writes() as events:
        p.touch()
    assert p.exists()
    assert WriteEvent("create", str(p), 0) in events, events


def test_open_mode_x_on_a_new_path_is_an_observable_create(tmp_path):
    p = tmp_path / "excl.txt"
    with trace_writes() as events:
        with builtins.open(p, "x", encoding="utf-8") as fh:
            fh.write("q")
    assert p.read_text(encoding="utf-8") == "q"
    assert WriteEvent("create", str(p), 0) in events, events


def test_path_write_bytes_on_a_new_path_is_an_observable_create(tmp_path):
    p = tmp_path / "fresh.bin"
    with trace_writes() as events:
        p.write_bytes(b"abcde")
    assert WriteEvent("create", str(p), 0) in events, events
    assert WriteEvent("write", str(p), 5) in events, events


def test_writing_an_existing_file_is_not_a_create(tmp_path):
    """The legitimate neighbour must SURVIVE. A create everywhere is a create nowhere."""
    p = tmp_path / "already.txt"
    p.write_bytes(b"old")
    with trace_writes() as events:
        with builtins.open(p, "w", encoding="utf-8") as fh:
            fh.write("new")
        p.write_bytes(b"newer")
        p.touch()
        fd = os.open(str(p), os.O_WRONLY)
        os.close(fd)
    assert _ops(events, "create") == [], (
        f"an existing file was reported as created: {_ops(events, 'create')}"
    )


# --------------------------------------------------------------------------
# D4. No route may sit in NEITHER list. Silence is the class conservation misses.
# --------------------------------------------------------------------------


def test_os_ftruncate_is_a_truncate(tmp_path):
    p = tmp_path / "ft2.bin"
    p.write_bytes(b"abcdef")
    with trace_writes() as events:
        fd = os.open(str(p), os.O_RDWR)
        try:
            os.ftruncate(fd, 2)
        finally:
            os.close(fd)
    assert p.stat().st_size == 2, "disk says nothing was truncated"
    assert WriteEvent("truncate", str(p), 2) in events, events


def test_os_link_is_a_create(tmp_path):
    src = tmp_path / "link_src.txt"
    src.write_bytes(b"hello")
    dst = tmp_path / "link_dst.txt"
    with trace_writes() as events:
        try:
            os.link(str(src), str(dst))
        except (OSError, NotImplementedError, AttributeError) as exc:
            pytest.skip(f"os.link unavailable on this host: {exc}")
    assert dst.exists()
    assert WriteEvent("create", str(dst), 0) in events, events


def test_os_symlink_is_a_create(tmp_path):
    src = tmp_path / "sym_src.txt"
    src.write_bytes(b"hello")
    dst = tmp_path / "sym_dst.txt"
    with trace_writes() as events:
        try:
            os.symlink(str(src), str(dst))
        except (OSError, NotImplementedError, AttributeError) as exc:
            pytest.skip(f"os.symlink unavailable on this host: {exc}")
    assert WriteEvent("create", str(dst), 0) in events, events


def test_shutil_copy2_is_seen(tmp_path):
    src = tmp_path / "cp_src.txt"
    src.write_bytes(b"hello")
    dst = tmp_path / "cp_dst.txt"
    with trace_writes() as events:
        shutil.copy2(str(src), str(dst))
    assert dst.read_bytes() == b"hello", "disk says nothing was copied"
    assert WriteEvent("write", str(dst), 5) in events, events
    assert WriteEvent("create", str(dst), 0) in events, events


def test_shutil_copytree_is_seen(tmp_path):
    src = tmp_path / "ct_src"
    src.mkdir()
    (src / "one.txt").write_bytes(b"abc")
    (src / "two.txt").write_bytes(b"de")
    dst = tmp_path / "ct_dst"
    with trace_writes() as events:
        shutil.copytree(str(src), str(dst))
    assert (dst / "one.txt").read_bytes() == b"abc", "disk says nothing was copied"
    assert WriteEvent("write", str(dst), 5) in events, events


_ROUTE_FAMILIES_THAT_MUST_BE_DECLARED = (
    "io.FileIO",
    "os.ftruncate",
    "os.link",
    "os.symlink",
    "pathlib.Path.touch",
    'open(mode="x")',
    "os.utime",
    "shutil.copy2",
    "shutil.copytree",
    "os.dup",
    "os.dup2",
)


def test_no_named_route_family_sits_in_neither_list():
    """D4. A route in neither list is the silent class, and silence never fails."""
    covered = " ".join(COVERED_ROUTES)
    uncovered = " ".join(UNCOVERED_ROUTES)
    missing = [
        name
        for name in _ROUTE_FAMILIES_THAT_MUST_BE_DECLARED
        if name not in covered and name not in uncovered
    ]
    assert not missing, f"these routes are in NEITHER list: {missing}"
    both = [
        name
        for name in _ROUTE_FAMILIES_THAT_MUST_BE_DECLARED
        if name in covered and name in uncovered
    ]
    assert not both, f"these routes are in BOTH lists: {both}"


# --------------------------------------------------------------------------
# D5. The honesty arm, in BOTH directions.
# --------------------------------------------------------------------------


def _derived_route_name(owner, attr):
    """Derived from the OWNER OBJECT, never from a hand-typed label beside it."""
    if isinstance(owner, type):
        return f"{owner.__module__}.{owner.__qualname__}.{attr}"
    return f"{owner.__name__}.{attr}"


def test_covered_routes_equals_the_patch_table_in_both_directions():
    """A route that IS patched but is NOT listed was invisible to every other arm."""
    patched = {_derived_route_name(owner, attr) for owner, attr in write_tracer.PATCH_TARGETS}
    assert len(patched) >= 10, f"non-vacuity: the patch table is near empty: {patched}"
    listed = {r for r in COVERED_ROUTES if not r.startswith("<")}
    assert patched - listed == set(), (
        f"PATCHED BUT NOT LISTED - invisible to every arm: {sorted(patched - listed)}"
    )
    assert listed - patched == set(), (
        f"LISTED BUT NOT PATCHED - the module claims more than it does: {sorted(listed - patched)}"
    )


def test_the_patch_table_really_replaces_every_name_it_holds():
    """Non-vacuity for the arm above: the table is not a decorative list."""
    before = {_derived_route_name(o, a): getattr(o, a) for o, a in write_tracer.PATCH_TARGETS}
    with trace_writes():
        for owner, attr in write_tracer.PATCH_TARGETS:
            name = _derived_route_name(owner, attr)
            assert getattr(owner, attr) is not before[name], f"{name} is in the table, unpatched"
    for owner, attr in write_tracer.PATCH_TARGETS:
        name = _derived_route_name(owner, attr)
        assert getattr(owner, attr) is before[name], f"{name} was not restored"


# --------------------------------------------------------------------------
# D6. The wrapper-mediated entries, each with the dedicated arm claimed for it.
# --------------------------------------------------------------------------


def test_a_file_object_writelines_is_recorded_once_with_the_total(tmp_path):
    p = tmp_path / "wl.txt"
    with trace_writes() as events:
        with builtins.open(p, "w", encoding="utf-8") as fh:
            fh.writelines(["ab", "cde"])
    assert p.read_text(encoding="utf-8") == "abcde", "disk says the lines were not written"
    assert WriteEvent("write", str(p), 5) in events, events
    assert len(_ops(events, "write")) == 1, f"writelines was counted more than once: {events}"


_WRAPPER_ROUTE_ARMS = {
    "<file object>.write": "test_builtins_open_w_records_a_truncate_distinct_from_the_bytes",
    "<file object>.writelines": "test_a_file_object_writelines_is_recorded_once_with_the_total",
    "<file object>.truncate": "test_a_file_object_truncate_is_a_truncate",
    '<open(mode="x")>': "test_open_mode_x_on_a_new_path_is_an_observable_create",
}


def test_every_wrapper_mediated_covered_route_names_a_dedicated_arm():
    """The module docstring claims these have dedicated arms. This checks the claim."""
    wrapper = {r for r in COVERED_ROUTES if r.startswith("<")}
    assert wrapper == set(_WRAPPER_ROUTE_ARMS), (
        f"the wrapper-mediated routes and their arm map disagree: "
        f"{sorted(wrapper ^ set(_WRAPPER_ROUTE_ARMS))}"
    )
    for route, arm in _WRAPPER_ROUTE_ARMS.items():
        assert callable(globals().get(arm)), f"{route} claims arm {arm}, which does not exist"


def test_the_create_op_is_declared_on_the_event_type():
    """A new op value is a seam change. It must be stated where the type is defined."""
    doc = (WriteEvent.__doc__ or "").lower()
    assert "create" in doc, f"WriteEvent does not declare the create op: {WriteEvent.__doc__!r}"
