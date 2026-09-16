"""BEHAVIOUR arms: the kwargs two windowless-parent spawns actually pass.

THE RULE. RC's `CHANNEL.md` v1 section 5, adopted fleet-wide: every
console-subsystem CHILD of a windowless parent - a `pythonw` process, or any hook
running under the desktop harness - needs `creationflags=CREATE_NO_WINDOW` on the
spawn, or it flashes a console window. THE INTERPRETER TOKEN REMOVES NO FLASH:
swapping `python` for `pythonw` at a hook command is measured INERT. CREATIONFLAGS
ARE ALSO NOT INHERITED, so the fix cannot land on a parent either.

THIS FILE HOLDS ONLY THE ARMS THAT RUN CODE. The source census that used to live
here moved to `tests/test_responder_spawn_census.py` on 2026-09-16, and the split
is load bearing rather than cosmetic:

  `tools/gate_mutation_runner.SHAPE_GRADER_MODULES` excludes PER MODULE, by
  emitting `--ignore` in `suite_argv`. A module that reads the target's SOURCE
  belongs in that list, because it reddens over syntax and shape and would record
  a mutant as KILLED without any test having driven the gate. The arms BELOW are
  the opposite case: they drive `_spawn_headless` and `poll_registry` through a
  patched `subprocess`, so when a mutation lands in one of those functions their
  reddening is a LEGITIMATE KILL. While both kinds shared one file, declaring that
  file deleted the legitimate kills too. This file is therefore NOT declared, and
  stays in the campaign.

Do not add a `read_text` of either target to this file. That would put it back in
the shape-grader population and it would have to be excluded again, taking these
arms out of every campaign with it.

THE TWO SITES, both genuinely in the windowless-parent population:

  tools/moon_sync_responder.py   `_spawn_headless` launches the headless `claude`
                                 shim, a console `cmd.exe` entry point on this
                                 box - which is why it resolves the executable
                                 through `shutil.which` at all.
  tools/first_run_capture.py     `poll_registry` spawns `reg query`. Its parent is
                                 MORE windowless than `pythonw`: the daemon is
                                 started by `tools/capture_supervisor.py`
                                 `spawn_detached`, whose flags are
                                 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`, and
                                 DETACHED_PROCESS means it owns no console at all.
                                 It is a loop - three registry keys, an interval of
                                 2 seconds and `registry_every` of 15 - so the
                                 unflagged form allocated three consoles every
                                 thirty seconds for the life of the daemon.

WHAT IS CONFIRMED AND WHAT IS NOT. RC ran a positive control on 2026-09-15 and it
PASSED on all three arms: both unflagged spawns under a windowless `pythonw`
parent produced a `ConsoleWindowClass` event, the `CREATE_NO_WINDOW` spawn
produced NONE, and a heartbeat landed after the last spawn with no liveness gap.
That CONFIRMS THE DETECTOR AND THE FLAG. It does NOT confirm that any residual
flash an operator observed came from either of these spawns - that attribution
stays PROBABLE at n=1 and is claimed nowhere here. NO ARM IN THIS FILE OBSERVES A
CONSOLE WINDOW.

THE ONE THING THESE ARMS CANNOT SEE, stated rather than implied. A
`creationflags=0` LITERAL is indistinguishable from the guard ON POSIX, because
`_NO_WINDOW` legitimately resolves to 0 there, so the value comparison matches and
the non-vacuity arm that would notice is `skipif sys.platform != "win32"`. On
POSIX that mutant is not merely undetected, it is EQUIVALENT - there is no
behavioural difference to detect. On Windows these arms kill it for BOTH sites.
It is also killed on every platform by
`tests/test_responder_spawn_census.py`, which rejects a literal zero at the
source, and that arm is why the gap is closed rather than merely disclosed.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"
CAPTURE = ROOT / "tools" / "first_run_capture.py"

#: What the flag must resolve to on the host the test is running on. Derived from
#: `subprocess` itself rather than retyped as `0x08000000`, because a literal here
#: would agree with itself and with nothing else.
EXPECTED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _load(name: str, path: Path):
    """Load a target module by path. `importlib`, never `read_text` - see header."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Captured:
    """A stand-in for `CompletedProcess` that records what it was called with."""

    def __init__(self, stdout: object = "ok") -> None:
        self.args: tuple = ()
        self.kwargs: dict = {}
        self.calls = 0
        self._stdout = stdout

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls += 1
        return subprocess.CompletedProcess(
            args=args[0] if args else [], returncode=0, stdout=self._stdout
        )


# ---------------------------------------------------------------------------
# The responder's one spawn.
# ---------------------------------------------------------------------------


@pytest.fixture()
def rsp():
    """The responder, loaded under its own module name.

    RE-DEFINED rather than imported from a sibling test module, matching
    `tests/test_responder_delivery_gates.py` - two files sharing one loaded module
    share one set of monkeypatches too, and this file patches `subprocess.run`.

    No `DEFAULT_` redirection is needed: every arm intercepts the spawn before it
    runs and none reaches a write path.
    """
    return _load("responder_no_console_window_under_test", MODULE)


@pytest.fixture()
def spawned(rsp, monkeypatch):
    """Run `_spawn_headless` with the real spawn intercepted, return the record.

    `shutil.which` is stubbed because the arm must hold where the `claude` shim is
    absent - a CI runner - since `_spawn_headless` raises `SpawnFailed` before
    reaching `subprocess.run` when it resolves to None. A test that passes only
    where the shim happens to be installed is a statement about the installation.
    """
    import shutil

    record = _Captured()
    monkeypatch.setattr(shutil, "which", lambda _name: str(ROOT / "fake-claude-shim.cmd"))
    monkeypatch.setattr(subprocess, "run", record)

    out = rsp._spawn_headless("a prompt", rsp.Bounds())
    assert out == "ok", "the fixture's own stub did not reach the return path"
    assert record.calls == 1, f"expected exactly one spawn, saw {record.calls}"
    return record


def test_the_spawn_passes_creationflags_at_all(spawned):
    """THE MUTANT-KILLING ARM. Drop the kwarg and this is the failure.

    Key PRESENCE is asserted separately from the value, because on POSIX the
    expected value is `0` - so a value comparison alone cannot tell a flagged
    spawn from an unflagged one there. Presence is the property that can.
    """
    assert "creationflags" in spawned.kwargs, (
        "the responder's spawn passes no creationflags, so a console child of a "
        "windowless parent flashes a window - CHANNEL.md v1 section 5. The "
        "interpreter token does not fix this; the flag on the spawn does."
    )


def test_the_creationflags_value_is_the_no_window_flag(spawned):
    """And it is the RIGHT flag, resolved the way the tree already resolves it.

    ON WINDOWS ONLY does this kill a `creationflags=0` literal. On POSIX that
    mutant is EQUIVALENT rather than undetected, and the source census kills it on
    every platform. See the module header.
    """
    assert spawned.kwargs["creationflags"] == EXPECTED_FLAG, (
        f"creationflags is {spawned.kwargs['creationflags']!r}, expected "
        f"{EXPECTED_FLAG!r} - on Windows that is subprocess.CREATE_NO_WINDOW, and "
        "off Windows it is 0, which is subprocess.run's own default"
    )


def test_the_other_spawn_kwargs_survived(spawned, rsp):
    """THE SURVIVAL GUARD for the edit that added the flag.

    An arm that only checks the new kwarg scores full marks against a diff that
    added `creationflags` and dropped `timeout` - and a spawn with no ceiling is
    the exact failure `_spawn_headless`'s own docstring says the timeout exists to
    prevent. So the kwargs the spawn had BEFORE the flag landed are named here.
    """
    for name in ("input", "capture_output", "text", "timeout", "cwd", "check"):
        assert name in spawned.kwargs, (
            f"{name} vanished from the spawn - adding the flag must not cost a "
            "pre-existing kwarg"
        )
    assert spawned.kwargs["timeout"] == pytest.approx(rsp.Bounds().spawn_timeout_seconds), (
        "the spawn's timeout no longer comes from Bounds"
    )
    assert spawned.kwargs["check"] is False, "check=False is load-bearing for the failure path"


# ---------------------------------------------------------------------------
# The capture daemon's registry spawn. ADDED 2026-09-16: until this arm existed,
# a `creationflags=0` literal at that site was invisible on EVERY platform, since
# no behaviour arm drove it and the census accepted any value.
# ---------------------------------------------------------------------------


@pytest.fixture()
def polled(monkeypatch, tmp_path):
    """Drive `poll_registry` with `subprocess.run` intercepted.

    The daemon's real `CaptureStore` writes outside the repo by design, so a
    minimal stand-in is used instead: `poll_registry` only ever calls `offer`, and
    returning False keeps the arm off every write path while still exercising the
    spawn. `tmp_path` is requested so that if this ever does touch disk it lands
    somewhere disposable rather than in the operator's capture root.
    """
    capture = _load("capture_daemon_under_test", CAPTURE)

    class _Store:
        def __init__(self) -> None:
            self.offers = 0

        def offer(self, *_args, **_kwargs) -> bool:
            self.offers += 1
            return False

    record = _Captured(stdout=b"")
    monkeypatch.setattr(subprocess, "run", record)
    monkeypatch.setattr(capture, "DEFAULT_CAPTURE_ROOT", tmp_path / "unused")

    capture.poll_registry(_Store())
    assert record.calls >= 1, (
        f"poll_registry spawned nothing, so this arm graded no spawn: {record.calls}"
    )
    return record


def test_the_registry_spawn_passes_creationflags_at_all(polled):
    """The daemon's parent holds NO console, so an unflagged child allocates one."""
    assert "creationflags" in polled.kwargs, (
        "poll_registry spawns reg query with no creationflags. Its parent is "
        "started DETACHED_PROCESS and owns no console, so every one of these "
        "allocates a fresh one - three keys every thirty seconds, on a loop."
    )


def test_the_registry_spawn_uses_the_no_window_flag(polled):
    """And the value is the guard, not a hardcoded zero - on Windows.

    On POSIX the guard is legitimately 0 and there is nothing here to distinguish;
    `tests/test_responder_spawn_census.py` rejects a literal zero at the source on
    every platform, which is what closes that gap.
    """
    assert polled.kwargs["creationflags"] == EXPECTED_FLAG, (
        f"the registry spawn passes creationflags={polled.kwargs['creationflags']!r}, "
        f"expected {EXPECTED_FLAG!r}"
    )


def test_the_registry_spawn_kept_its_timeout(polled):
    """SURVIVAL GUARD. `reg query /s` on a large subtree is not instant, and the
    daemon polls on a loop, so losing the ceiling would hang the loop rather than
    fail it."""
    assert polled.kwargs.get("timeout"), (
        "the registry spawn lost its timeout - on a polling loop that hangs the "
        "loop instead of failing it"
    )


# ---------------------------------------------------------------------------
# The platform guard, on both modules.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="CREATE_NO_WINDOW is a Windows-only attribute")
def test_the_resolved_flag_is_not_zero_here():
    """NON-VACUITY for the value arms on the platform where they can bite.

    Without it, a value arm could pass on Windows against a module that resolved
    the flag to `0` - through a typo in the `getattr` name, say - and the assertion
    would read `0 == 0` while every spawn kept flashing.
    """
    assert EXPECTED_FLAG != 0, (
        "subprocess.CREATE_NO_WINDOW resolved to 0 on win32, so the value arms are "
        "comparing nothing to nothing"
    )
    assert EXPECTED_FLAG == 0x08000000, (
        f"CREATE_NO_WINDOW is {EXPECTED_FLAG!r}, not the documented 0x08000000"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX half of the platform guard")
def test_the_spawns_are_inert_not_absent_on_posix(spawned, polled):
    """`subprocess` rejects a non-zero `creationflags` off Windows, so the guard
    has to resolve to `0` there rather than the kwarg being omitted."""
    assert spawned.kwargs["creationflags"] == 0
    assert polled.kwargs["creationflags"] == 0


@pytest.mark.parametrize("target", [MODULE, CAPTURE], ids=["responder", "capture_daemon"])
def test_the_guard_resolves_to_zero_when_the_attribute_is_absent(monkeypatch, target):
    """THE POSIX BRANCH, MEASURED ON THIS HOST rather than skipped off it.

    The arm above only runs on the lane it describes, so on Windows the Linux
    behaviour would be asserted by nothing at all - and a Linux-only failure has
    been reproduced in this tree before. This deletes
    `subprocess.CREATE_NO_WINDOW`, reloads each module, and checks the guard
    degrades to `0`: the value `subprocess.run` already uses when `creationflags`
    is not given, which is why the kwarg can stay unconditional instead of sitting
    behind a platform branch.

    It simulates the ATTRIBUTE's absence and nothing more. It does not claim to run
    POSIX process creation.
    """
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)
    assert not hasattr(subprocess, "CREATE_NO_WINDOW"), "the simulation did not take"

    module = _load(f"posix_simulated_{target.stem}", target)
    assert module._NO_WINDOW == 0, (
        f"{target.name} resolved the guard to {module._NO_WINDOW!r} with the "
        "attribute absent - a non-zero creationflags off Windows is a ValueError"
    )
