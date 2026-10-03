r"""An abandoned job's half-written temp is swept on a later pass - only ours.

THE MECHANISM, measured in section 1 rather than asserted.

`core/atomic_io.atomic_write_text` writes a SIBLING temp named
`.<target>.<pid>.<8 hex>.tmp` and then renames it over the target. Its
cleanup sits in a `finally`, so every exception - OSError, an encode error, a
KeyboardInterrupt - removes the temp. What a `finally` cannot survive is the
interpreter ending under it: `headless/runner._die_holding_slot` ends the
process with `os._exit` while an abandoned job is still running, by design
(no slot is released while a job of this process runs). A job that was
between the temp write and the rename at that instant leaves the temp behind.
A `taskkill /F` of the runner does the same. The target is never torn - only
the rename makes a temp the target.

THE REPAIR. Prevention is impossible at the source - the dying process cannot
know which temp its abandoned thread is holding - so the next LIVE pass
sweeps, before it takes a slot, the runtime directory and the data directory
(the two directories a runner-path write lands in). A temp is removed ONLY
when all of these hold:

  1. its name matches the exact shape `core/atomic_io._temp_path` produces;
  2. it is a regular file, not a directory or link;
  3. the pid in its name is NOT this process and is NOT a live process
     (`ops/loop/slots.pid_alive`, the reaper's own predicate, which treats an
     unqueryable pid as alive);
  4. it is older than `ORPHAN_TEMP_MIN_AGE_SECONDS`.

A concurrent writer is always a live pid, so (3) alone protects it; (4)
protects against a pid that was reused between the probe and the unlink. A
dry run sweeps nothing, because a dry run writes nothing.

Every live arm passes `slot_root` and `runtime_dir` under `tmp_path`. The
child-process arm runs the runner in a CHILD interpreter, because the
behaviour that orphans the temp is `os._exit`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core import atomic_io as atomic_io_mod
from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops.loop import slots as slots_mod

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_JOB = "orphan_probe"
OLD = 10 * 24 * 3600.0


@pytest.fixture(autouse=True)
def never_exit_this_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_die_holding_slot` would `os._exit` the pytest process; refuse instead."""

    def _refuse(*args, **kwargs) -> None:
        raise AssertionError("the runner tried to os._exit the pytest process")

    monkeypatch.setattr(runner_mod, "_die_holding_slot", _refuse)


@pytest.fixture()
def clean_registry():
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture()
def tmp_counts_as_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let a tmp root pass the halt-clause (a) check, for wiring arms only.

    The check itself is measured, unpatched, in section 5.
    """
    monkeypatch.setattr(runner_mod, "_inside_repo_root", lambda path: True)


@pytest.fixture()
def dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_counts_as_repo
) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    data = tmp_path / "data"
    slots = tmp_path / "slots"
    for path in (runtime, data, slots):
        path.mkdir()
    assert slots != slots_mod.DEFAULT_ROOT
    monkeypatch.setenv("RESINCOMPUTE_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("RC_DATA_DIR", str(data))
    return {"runtime": runtime, "data": data, "slots": slots}


def _dead_pid() -> int:
    """A pid that WAS a process and is not one now."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(30)
    if slots_mod.pid_alive(proc.pid):
        pytest.skip("the finished child's pid read as alive - reused already")
    return proc.pid


def _temp_name(target: str, pid: int, suffix: str = "0123abcd") -> str:
    return f".{target}.{pid}.{suffix}.tmp"


def _plant(directory: Path, name: str, age: float = OLD) -> Path:
    path = directory / name
    path.write_bytes(b"{\"half\": ")
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


def _register_probe() -> None:
    jobs_mod.register(
        jobs_mod.JobSpec(
            name=PROBE_JOB,
            description="orphan sweep probe",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=lambda context: jobs_mod.passed(PROBE_JOB, "ok"),
        )
    )


def _run_live(dirs: dict[str, Path], dry_run: bool = False) -> int:
    return runner_mod.run_once(
        uid=None,
        dry_run=dry_run,
        job_names=[PROBE_JOB],
        runtime_dir=str(dirs["runtime"]),
        slot_root=str(dirs["slots"]),
        slot_timeout=5,
    )


# ---------------------------------------------------------------------------
# 1. The mechanism: os._exit mid-write orphans a temp beside an untorn target
# ---------------------------------------------------------------------------

_CHILD = r"""
import pathlib, sys, time
from pathlib import Path
repo, work = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, repo)
from core import atomic_io
from headless import jobs as jobs_mod
from headless import runner as runner_mod

target = work / "runtime" / "victim.json"
started = work / "started"
_real_replace = pathlib.Path.replace

def _stalled_replace(self, dest):
    # The job is now between the temp write and the rename, which is exactly
    # where os._exit catches an abandoned writer.
    if Path(dest).name == "victim.json":
        started.write_text("1", encoding="utf-8")
        time.sleep(30)
    return _real_replace(self, dest)

pathlib.Path.replace = _stalled_replace

def _writer(context):
    atomic_io.atomic_write_text(target, "NEW CONTENT\n")
    return jobs_mod.passed("writer", "late")

jobs_mod.register(jobs_mod.JobSpec(
    name="writer", description="stalls mid atomic write",
    cadence=jobs_mod.CADENCE_ON_DEMAND, func=_writer))
runner_mod.JOB_DEADLINE_SECONDS = 0.5
runner_mod.JOB_CANCEL_GRACE_SECONDS = 0.1
code = runner_mod.run_once(
    uid=None, dry_run=False, job_names=["writer"],
    runtime_dir=str(work / "runtime"), slot_root=str(work / "slots"), slot_timeout=5)
sys.exit(90 + code)
"""


def _orphan_from_a_killed_child(work: Path) -> tuple[int, Path, list[Path]]:
    (work / "runtime").mkdir(parents=True)
    (work / "slots").mkdir()
    target = work / "runtime" / "victim.json"
    target.write_bytes(b"OLD CONTENT\n")
    env = dict(os.environ)
    env["RESINCOMPUTE_RUNTIME_DIR"] = str(work / "runtime")
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD, str(REPO_ROOT), str(work)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        child.wait(60)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(30)
    assert (work / "started").exists(), "the writer never reached the rename"
    assert child.returncode == runner_mod.EXIT_JOB_ABANDONED
    orphans = sorted((work / "runtime").glob(".victim.json.*.tmp"))
    return child.pid, target, orphans


def test_os_exit_mid_write_orphans_a_temp_beside_an_untorn_target(tmp_path: Path) -> None:
    """Characterization: the gap is real and this is its exact shape."""
    pid, target, orphans = _orphan_from_a_killed_child(tmp_path / "work")
    assert target.read_bytes() == b"OLD CONTENT\n", "the target was torn"
    assert len(orphans) == 1, f"expected one orphan, found {orphans}"
    assert f".victim.json.{pid}." in orphans[0].name
    assert runner_mod.parse_orphan_temp_name(orphans[0].name) == ("victim.json", pid)


def test_the_next_live_pass_sweeps_the_real_orphan(
    tmp_path: Path, clean_registry, monkeypatch: pytest.MonkeyPatch, tmp_counts_as_repo
) -> None:
    """End to end: the orphan the child left is gone after the next live pass."""
    work = tmp_path / "work"
    _pid, target, orphans = _orphan_from_a_killed_child(work)
    assert orphans, "non-vacuity: the child must have left an orphan"
    stamp = time.time() - OLD
    for orphan in orphans:
        os.utime(orphan, (stamp, stamp))
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("RC_DATA_DIR", str(data))
    _register_probe()
    code = _run_live(
        {"runtime": work / "runtime", "data": data, "slots": work / "slots"}
    )
    assert code == runner_mod.EXIT_OK
    assert [p for p in orphans if p.exists()] == [], "the orphan survived a live pass"
    assert target.read_bytes() == b"OLD CONTENT\n", "the untorn target was touched"


# ---------------------------------------------------------------------------
# 2. The naming contract is coupled to core/atomic_io, not copied from it
# ---------------------------------------------------------------------------


def test_the_pattern_matches_what_atomic_io_actually_names(tmp_path: Path) -> None:
    for name in ("health.json", "account_state.json", "a.b.c", "x"):
        produced = atomic_io_mod._temp_path(tmp_path / name).name
        assert runner_mod.parse_orphan_temp_name(produced) == (name, os.getpid()), produced


@pytest.mark.parametrize(
    "name",
    [
        "health.json",
        "health.json.tmp",  # ops/health.py fallback - fixed name, not ours
        "123456.json.tmp",  # ingest enka cache - fixed name, not ours
        ".health.json.123.zzzzzzzz.tmp",  # not hex
        ".health.json.123.0123abc.tmp",  # 7 hex
        ".health.json.123.0123ABCD.tmp",  # uppercase is not what uuid4().hex emits
        ".health.json.abc.0123abcd.tmp",  # pid not numeric
        "health.json.123.0123abcd.tmp",  # no leading dot
        ".health.json.123.0123abcd.tmp.bak",
        "..123.0123abcd.tmp",  # empty target name
        ".health.json.4294967296.deadbeef.tmp",  # pid past 32 bits
        ".health.json.0.deadbeef.tmp",  # pid 0 is never a writer
        ".health.json.99999999999999999999.deadbeef.tmp",
    ],
)
def test_names_that_are_not_ours_do_not_parse(name: str) -> None:
    assert runner_mod.parse_orphan_temp_name(name) is None


# ---------------------------------------------------------------------------
# 3. The sweep: removes provable orphans, and the neighbours SURVIVE
# ---------------------------------------------------------------------------


def test_sweep_removes_an_old_dead_pid_temp(tmp_path: Path) -> None:
    orphan = _plant(tmp_path, _temp_name("health.json", _dead_pid()))
    removed = runner_mod.sweep_orphan_temps([tmp_path])
    assert removed == [orphan]
    assert not orphan.exists()


def test_sweep_spares_every_legitimate_neighbour(tmp_path: Path) -> None:
    dead = _dead_pid()
    live_child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"]
    )
    try:
        assert slots_mod.pid_alive(live_child.pid)
        orphan = _plant(tmp_path, _temp_name("state.json", dead))
        survivors = [
            # young, even with a dead pid: a pid reuse window, not provable
            _plant(tmp_path, _temp_name("health.json", dead, "aaaaaaaa"), age=1.0),
            # our own pid: may be a write in flight in this very process
            _plant(tmp_path, _temp_name("health.json", os.getpid(), "bbbbbbbb")),
            # a live process: a concurrent writer, never ours to take
            _plant(tmp_path, _temp_name("health.json", live_child.pid, "cccccccc")),
            # fixed-name temps of other writers, and the target itself
            _plant(tmp_path, "health.json.tmp"),
            _plant(tmp_path, "health.json"),
            _plant(tmp_path, "notes.txt"),
        ]
        as_dir = tmp_path / _temp_name("dir.json", dead, "dddddddd")
        as_dir.mkdir()
        nested = tmp_path / "sub"
        nested.mkdir()
        deep = _plant(nested, _temp_name("deep.json", dead, "eeeeeeee"))

        removed = runner_mod.sweep_orphan_temps([tmp_path])
    finally:
        live_child.kill()
        live_child.wait(30)

    assert removed == [orphan], "non-vacuity: the one provable orphan must go"
    assert not orphan.exists()
    for path in survivors:
        assert path.exists(), f"a legitimate neighbour was swept: {path.name}"
    assert as_dir.is_dir(), "a directory is never swept"
    assert deep.exists(), "the sweep is not recursive"


def test_sweep_survives_a_missing_directory_and_an_unlink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dead = _dead_pid()
    stuck = _plant(tmp_path, _temp_name("stuck.json", dead, "aaaaaaaa"))
    free = _plant(tmp_path, _temp_name("free.json", dead, "bbbbbbbb"))
    real_unlink = Path.unlink

    def _unlink(self: Path, *args, **kwargs) -> None:
        if self.name == stuck.name:
            raise PermissionError(32, "in use by another process")
        real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _unlink)
    removed = runner_mod.sweep_orphan_temps([tmp_path / "absent", tmp_path])
    assert removed == [free]
    assert stuck.exists()


def test_the_age_floor_outlasts_any_runner_job() -> None:
    floor = runner_mod.ORPHAN_TEMP_MIN_AGE_SECONDS
    assert floor >= runner_mod.JOB_DEADLINE_SECONDS + runner_mod.JOB_CANCEL_GRACE_SECONDS


# ---------------------------------------------------------------------------
# 4. Wiring: a live pass sweeps runtime and data dirs; a dry run sweeps nothing
# ---------------------------------------------------------------------------


def test_a_live_pass_sweeps_the_runtime_and_data_dirs(
    dirs: dict[str, Path], clean_registry
) -> None:
    dead = _dead_pid()
    in_runtime = _plant(dirs["runtime"], _temp_name("health.json", dead))
    in_data = _plant(dirs["data"], _temp_name("account_state.json", dead))
    _register_probe()
    assert _run_live(dirs) == runner_mod.EXIT_OK
    assert not in_runtime.exists(), "the runtime-dir orphan survived"
    assert not in_data.exists(), "the data-dir orphan survived"


def test_a_dry_run_sweeps_nothing(dirs: dict[str, Path], clean_registry) -> None:
    dead = _dead_pid()
    in_runtime = _plant(dirs["runtime"], _temp_name("health.json", dead))
    in_data = _plant(dirs["data"], _temp_name("account_state.json", dead))
    _register_probe()
    assert _run_live(dirs, dry_run=True) == runner_mod.EXIT_OK
    assert in_runtime.exists() and in_data.exists(), "a dry run deleted a file"


def test_a_halted_pass_sweeps_nothing(dirs: dict[str, Path], clean_registry) -> None:
    dead = _dead_pid()
    in_runtime = _plant(dirs["runtime"], _temp_name("health.json", dead))
    runner_mod.halt_sentinel_path(str(dirs["runtime"])).write_bytes(b"")
    _register_probe()
    assert _run_live(dirs) == runner_mod.EXIT_JOB_FAILED
    assert in_runtime.exists(), "a halted pass deleted a file"


# ---------------------------------------------------------------------------
# 5. Refuted at b982c90: an unprobeable pid, and roots outside the repo
# ---------------------------------------------------------------------------


def test_a_pid_past_32_bits_is_skipped_and_the_sweep_carries_on(tmp_path: Path) -> None:
    """The adversary's reproducer. `slots.pid_alive` raises ctypes.ArgumentError
    on Windows for a pid >= 2**32, which used to end the whole sweep - and the
    pass, and the daemon - at the first such name."""
    huge = _plant(tmp_path, ".health.json.4294967296.deadbeef.tmp", age=7200.0)
    if slots_mod.pid_alive(999999):
        pytest.skip("pid 999999 is in use on this host")
    plain = _plant(tmp_path, ".health.json.999999.deadbeef.tmp", age=7200.0)
    removed = runner_mod.sweep_orphan_temps([tmp_path])
    assert huge.exists(), "a pid that cannot be probed is never ours to delete"
    assert removed == [plain] and not plain.exists()


def test_one_entry_that_raises_does_not_stop_the_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dead = _dead_pid()
    first = _plant(tmp_path, _temp_name("a.json", dead, "aaaaaaaa"))
    second = _plant(tmp_path, _temp_name("b.json", dead, "bbbbbbbb"))
    real = slots_mod.pid_alive
    calls: list[int] = []

    def _flaky(pid: int) -> bool:
        calls.append(pid)
        if len(calls) == 1:
            raise RuntimeError("probe exploded")
        return real(pid)

    monkeypatch.setattr(slots_mod, "pid_alive", _flaky)
    removed = runner_mod.sweep_orphan_temps([tmp_path])
    assert len(calls) == 2, "non-vacuity: both entries were probed"
    assert first.exists(), "the entry whose probe raised was kept"
    assert removed == [second]


def test_a_sweep_that_raises_never_fails_the_live_pass(
    dirs: dict[str, Path], clean_registry, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    def _boom(directories) -> list[Path]:
        calls.append(directories)
        raise RuntimeError("sweep exploded")

    monkeypatch.setattr(runner_mod, "sweep_orphan_temps", _boom)
    _register_probe()
    assert _run_live(dirs) == runner_mod.EXIT_OK
    assert calls, "non-vacuity: the sweep was reached"


def test_the_repo_root_check_measures_real_paths(tmp_path: Path) -> None:
    repo = runner_mod.health_mod.REPO_ROOT
    assert runner_mod._inside_repo_root(repo / "ops" / "runtime")
    assert runner_mod._inside_repo_root(repo / "data")
    assert not runner_mod._inside_repo_root(tmp_path)
    assert not runner_mod._inside_repo_root(repo.parent)
    assert not runner_mod._inside_repo_root(repo / ".." / "elsewhere")


def test_a_root_outside_the_repo_is_not_swept_by_a_pass(
    tmp_path: Path, clean_registry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Halt clause (a): no delete outside the repo root. A runtime or data dir
    pointed outside it by env var is skipped by the pass, not swept."""
    runtime = tmp_path / "runtime"
    data = tmp_path / "data"
    slots = tmp_path / "slots"
    for path in (runtime, data, slots):
        path.mkdir()
    monkeypatch.setenv("RESINCOMPUTE_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("RC_DATA_DIR", str(data))
    assert not runner_mod._inside_repo_root(runtime)
    dead = _dead_pid()
    outside = [
        _plant(runtime, _temp_name("health.json", dead)),
        _plant(data, _temp_name("account_state.json", dead)),
    ]
    _register_probe()
    code = _run_live({"runtime": runtime, "data": data, "slots": slots})
    assert code == runner_mod.EXIT_OK
    for path in outside:
        assert path.exists(), f"a file outside the repo root was deleted: {path.name}"
    # Control: the same files ARE removable once the root counts as inside.
    monkeypatch.setattr(runner_mod, "_inside_repo_root", lambda path: True)
    assert _run_live({"runtime": runtime, "data": data, "slots": slots}) == runner_mod.EXIT_OK
    assert not any(path.exists() for path in outside)
