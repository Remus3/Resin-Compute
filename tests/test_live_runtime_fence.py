"""The two conftest audit-hook fences resolve a path the way the KERNEL will.

REGRESSION, measured on CI run 37131711357 (ubuntu-latest, Python 3.11.16) at
9061eb4: 141 failures and errors, every one downstream of a single event. On
POSIX `shutil.rmtree` takes the fd-based route (`_rmtree_safe_fd`) and removes
each entry by NAME relative to an open directory fd:

    os.rmdir(entry.name, dir_fd=topfd)   ->  audit ('os.rmdir', ('moon_sync_inbox', 13))

pytest's own `tmp_path` teardown (`tmp_path_retention_policy = failed`) ran
that over a tmp tree holding a `moon_sync_inbox` directory. The live-runtime
fence joined the bare name onto `os.getcwd()` - the repo root - instead of onto
fd 13, concluded the LIVE inbox was being removed, and raised a BaseException
inside pytest's teardown. pytest's finalizer loop catches `Exception` only, so
the remaining finalizers never ran, the function-scoped ledgers stayed cached,
and every later fence arm read a stale window (the "125 landed" and "4 == 2"
failures). The slot-bucket fence had the identical defect.

Windows never sees it: `dir_fd=` raises NotImplementedError there BEFORE any
audit event is raised, so the host suite was green on the same commit.

The arms below drive the fences with SYNTHETIC events through a seam -
`conftest._dir_fd_path` - so the POSIX case is reproducible on Windows, plus one
arm that runs the real mechanism (it discriminates on POSIX only, and says so).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest


def _conftest():
    import conftest

    return conftest


REPO_ROOT = Path(_conftest().__file__).resolve().parent
#: Any int that is not -1. The fences never dereference it except through the
#: `_dir_fd_path` seam, which every synthetic arm here patches.
FAKE_FD = 4242


def _fd_resolves_to(monkeypatch: pytest.MonkeyPatch, mapping: dict[int, Path | None]) -> None:
    def fake(fd: int) -> str | None:
        target = mapping.get(fd)
        return None if target is None else str(target)

    # raising=False: before the fix the seam does not exist, and the arm must
    # then fail on the FENCE, not on the patch.
    monkeypatch.setattr(_conftest(), "_dir_fd_path", fake, raising=False)


# --- live-runtime fence -----------------------------------------------------


def test_a_name_relative_to_a_tmp_dir_fd_is_not_the_live_inbox(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE CI DEFECT. cwd is the repo root, but the name is relative to a tmp fd."""
    monkeypatch.chdir(REPO_ROOT)
    _fd_resolves_to(monkeypatch, {FAKE_FD: tmp_path})
    sys.audit("os.rmdir", "moon_sync_inbox", FAKE_FD)
    sys.audit("os.remove", "moon_sync_inbox", FAKE_FD)
    sys.audit("os.mkdir", "moon_sync_inbox", 0o777, FAKE_FD)
    sys.audit("shutil.rmtree", "moon_sync_inbox", FAKE_FD)
    assert runtime_fence_ledger.hits() == []


def test_the_destination_dir_fd_is_honoured_per_argument(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """os.rename carries src_dir_fd AND dst_dir_fd; each path takes its own."""
    monkeypatch.chdir(REPO_ROOT)
    _fd_resolves_to(monkeypatch, {FAKE_FD: tmp_path, FAKE_FD + 1: REPO_ROOT})
    sys.audit("os.rename", "moon_sync_inbox", "elsewhere", FAKE_FD, -1)
    assert runtime_fence_ledger.hits() == []
    conftest = _conftest()
    with pytest.raises(conftest.LiveRuntimeFenceError):
        sys.audit("os.rename", str(tmp_path / "x"), "moon_sync_inbox", -1, FAKE_FD + 1)
    assert runtime_fence_ledger.acknowledge(1) == 1


def test_a_name_relative_to_a_dir_fd_on_the_repo_root_still_trips(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fence keeps its teeth: the fd, not the cwd, decides - in both directions."""
    monkeypatch.chdir(tmp_path)
    _fd_resolves_to(monkeypatch, {FAKE_FD: REPO_ROOT})
    with pytest.raises(_conftest().LiveRuntimeFenceError):
        sys.audit("os.rmdir", "moon_sync_inbox", FAKE_FD)
    assert runtime_fence_ledger.acknowledge(1) == 1


def test_an_absolute_live_path_trips_whatever_the_dir_fd(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POSIX ignores dir_fd for an absolute path, and so must the fence."""
    monkeypatch.chdir(tmp_path)
    _fd_resolves_to(monkeypatch, {FAKE_FD: tmp_path})
    live = str(REPO_ROOT / "moon_sync_inbox")
    conftest = _conftest()
    for dir_fd in (-1, FAKE_FD, None):
        with pytest.raises(conftest.LiveRuntimeFenceError):
            sys.audit("os.rmdir", live, dir_fd)
    assert runtime_fence_ledger.acknowledge(3) == 3


def test_a_relative_name_without_a_dir_fd_still_resolves_against_cwd(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The neighbours: dir_fd -1 means cwd, which is right both at the repo and in tmp."""
    monkeypatch.chdir(tmp_path)
    sys.audit("os.rmdir", "moon_sync_inbox", -1)
    assert runtime_fence_ledger.hits() == []
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(_conftest().LiveRuntimeFenceError):
        sys.audit("os.rmdir", "moon_sync_inbox", -1)
    assert runtime_fence_ledger.acknowledge(1) == 1


def test_an_unresolvable_dir_fd_is_not_called_live(
    runtime_fence_ledger, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stated policy: a name whose directory cannot be named is not a live record.

    Guessing the cwd instead is exactly the defect. The live runtime is on the
    Windows host, where dir_fd is never reachable, so this costs nothing there.
    """
    monkeypatch.chdir(REPO_ROOT)
    _fd_resolves_to(monkeypatch, {})
    sys.audit("os.rmdir", "moon_sync_inbox", FAKE_FD)
    assert runtime_fence_ledger.hits() == []


def test_the_real_fd_based_rmtree_of_a_tmp_inbox_passes(
    runtime_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CI mechanism itself, unpatched. Discriminates on POSIX only.

    On Windows `shutil.rmtree` takes the path-based route and this arm is green
    before and after the fix; on Linux it is the exact teardown that went red.
    """
    monkeypatch.chdir(REPO_ROOT)
    tree = tmp_path / "t"
    (tree / "moon_sync_inbox" / "held").mkdir(parents=True)
    (tree / "moon_sync_inbox" / "held" / "n.md").write_bytes(b"x\n")
    shutil.rmtree(tree)
    assert not tree.exists()
    assert runtime_fence_ledger.hits() == []


def test_the_dir_fd_seam_names_a_real_directory_or_nothing(tmp_path: Path) -> None:
    resolve = _conftest()._dir_fd_path
    if os.name == "nt":
        # No dir_fd on Windows, and no /proc: the seam must answer None, never a guess.
        fd = os.open(str(tmp_path / "f"), os.O_WRONLY | os.O_CREAT)
        try:
            assert resolve(fd) is None
        finally:
            os.close(fd)
        return
    fd = os.open(str(tmp_path), os.O_RDONLY)
    try:
        got = resolve(fd)
    finally:
        os.close(fd)
    if got is None:
        assert not os.path.isdir("/proc/self/fd"), "a /proc host resolved nothing"
    else:
        assert os.path.samefile(got, tmp_path)


# --- slot-bucket fence: the same rule ---------------------------------------


def _relative_bucket(monkeypatch: pytest.MonkeyPatch) -> str:
    """A RELATIVE spelling of the bucket that the cwd turns into the real bucket."""
    conftest = _conftest()
    raw = conftest._SLOT_BUCKET_RAW
    if not conftest._SLOT_BUCKET_IS_ABS:
        return raw  # POSIX: the Windows-shaped default is already relative to cwd
    anchor = Path(raw).anchor
    monkeypatch.chdir(anchor)
    return os.path.relpath(raw, anchor)


def test_the_slot_fence_resolves_a_relative_name_against_its_dir_fd(
    slot_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = _relative_bucket(monkeypatch)
    _fd_resolves_to(monkeypatch, {FAKE_FD: tmp_path})
    sys.audit("os.mkdir", rel, 0o777, FAKE_FD)
    sys.audit("os.rmdir", rel, FAKE_FD)
    assert slot_fence_ledger.hits() == []


def test_the_slot_fence_still_trips_relative_to_cwd_and_to_a_bucket_fd(
    slot_fence_ledger, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conftest = _conftest()
    rel = _relative_bucket(monkeypatch)
    with pytest.raises(conftest.SlotBucketFenceError):
        sys.audit("os.mkdir", rel, 0o777, -1)
    bucket = Path(conftest._bucket_norm())
    _fd_resolves_to(monkeypatch, {FAKE_FD: bucket.parent})
    with pytest.raises(conftest.SlotBucketFenceError):
        sys.audit("os.rmdir", bucket.name, FAKE_FD)
    assert slot_fence_ledger.acknowledge(2) == 2
