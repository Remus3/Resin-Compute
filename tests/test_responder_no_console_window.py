"""The responder's one spawn is graded for CREATE_NO_WINDOW, by behaviour.

THE RULE. RC's `CHANNEL.md` v1 section 5, adopted fleet-wide: every
console-subsystem CHILD of a windowless parent - a `pythonw` process, or any
hook running under the desktop harness - needs `creationflags=CREATE_NO_WINDOW`
on the spawn, or it flashes a console window. THE INTERPRETER TOKEN REMOVES NO
FLASH: swapping `python` for `pythonw` at a hook command is measured INERT for
this, so the fix has to land on the spawn and cannot land on the command line.

WHAT IS CONFIRMED AND WHAT IS NOT, because the difference is the whole reason
this docstring is longer than the test. RC ran a positive control on
2026-09-15 and it PASSED on all three arms: both unflagged spawns under a
windowless `pythonw` parent produced a `ConsoleWindowClass` event, the
`CREATE_NO_WINDOW` spawn produced NONE, and a heartbeat landed after the last
spawn with no liveness gap. That CONFIRMS THE DETECTOR AND THE FLAG. It does
NOT confirm that the residual flash an operator observed came from this spawn -
that attribution stays PROBABLE at n=1 and is not claimed here.

WHY THE SPAWN IN `tools/moon_sync_responder.py` IS IN SCOPE AT ALL. It launches
the headless `claude` shim, which on this box is a console `cmd.exe` entry
point - `_spawn_headless` resolves it through `shutil.which` precisely because
`subprocess` will not launch a bare `claude` on Windows. A console child is
exactly the population section 5 names.

WHY THIS IS NOT A SOURCE-TEXT ARM. "the module's source contains
CREATE_NO_WINDOW" pins FORMAT, not behaviour: it survives a mutant that passes
the flag to the wrong call, to a second spawn added later, or into a dead
constant nobody reads. So the arms below monkeypatch `subprocess.run` and grade
THE KWARGS THE RESPONDER ACTUALLY PASSES. `test_the_spawn_site_census_is_one`
is the only shape arm here and it is deliberately scoped to COUNTING spawn
sites, so a future second spawn cannot be added without a decision.

THE POSIX HALF. `CREATE_NO_WINDOW` does not exist as a `subprocess` attribute
off Windows, and this tree's CI has a Linux lane. The tree already has one
idiom for this - `tools/precommit_gate.py:93` resolves
`getattr(subprocess, "CREATE_NO_WINDOW", 0)` once at module level and passes
the result unconditionally - and the responder now follows it. So the kwarg is
present on BOTH platforms and only its VALUE differs: the real flag on Windows,
and `0` on POSIX, which is `subprocess.run`'s own default for `creationflags`
and therefore inert rather than wrong. `test_the_resolved_flag_is_not_zero_here`
is the non-vacuity arm that keeps the value assertion from reading `0 == 0` on
the host where the flag is native.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"

#: What the flag must resolve to on the host the test is running on. Derived
#: from `subprocess` itself rather than retyped as `0x08000000`, because a
#: literal here would agree with itself and with nothing else.
EXPECTED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@pytest.fixture()
def rsp():
    """The responder, loaded by path under its own module name.

    RE-DEFINED rather than imported from a sibling test module, matching
    `tests/test_responder_delivery_gates.py` - two files sharing one loaded
    module share one set of monkeypatches too, and this file patches
    `subprocess.run`.

    No `DEFAULT_` redirection is needed here: every arm intercepts the spawn
    before it runs and none of them reaches a write path.
    """
    spec = importlib.util.spec_from_file_location("responder_no_console_window_under_test", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Captured:
    """A stand-in for `CompletedProcess` that records what it was called with."""

    def __init__(self) -> None:
        self.args: tuple = ()
        self.kwargs: dict = {}
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls += 1
        return subprocess.CompletedProcess(args=args[0] if args else [], returncode=0, stdout="ok")


@pytest.fixture()
def spawned(rsp, monkeypatch):
    """Run `_spawn_headless` with the real spawn intercepted, return the record.

    `shutil.which` is stubbed because the arm must hold on a host where the
    `claude` shim is absent - a CI runner, for instance - and `_spawn_headless`
    raises `SpawnFailed` before reaching `subprocess.run` when it resolves to
    None. A test that passes only where the shim happens to be installed is a
    statement about the installation.
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
    expected value is `0` - so a value-only comparison against a missing key
    would read `None == 0`... and `0 == 0` if the test defaulted the lookup.
    Presence is the property that distinguishes flagged from unflagged there.
    """
    assert "creationflags" in spawned.kwargs, (
        "the responder's spawn passes no creationflags, so a console child of a "
        "windowless parent flashes a window - CHANNEL.md v1 section 5. The "
        "interpreter token does not fix this; the flag on the spawn does."
    )


def test_the_creationflags_value_is_the_no_window_flag(spawned):
    """And it is the RIGHT flag, resolved the way the tree already resolves it."""
    assert spawned.kwargs["creationflags"] == EXPECTED_FLAG, (
        f"creationflags is {spawned.kwargs['creationflags']!r}, expected "
        f"{EXPECTED_FLAG!r} - on Windows that is subprocess.CREATE_NO_WINDOW, "
        "and off Windows it is 0, which is subprocess.run's own default"
    )


@pytest.mark.skipif(sys.platform != "win32", reason="CREATE_NO_WINDOW is a Windows-only attribute")
def test_the_resolved_flag_is_not_zero_here():
    """NON-VACUITY for the value arm on the platform where it can bite.

    Without this, `test_the_creationflags_value_is_the_no_window_flag` could
    pass on Windows against a responder that resolved the flag to `0` - through
    a typo in the `getattr` name, say - and the assertion would read `0 == 0`
    while every spawn kept flashing.
    """
    assert EXPECTED_FLAG != 0, (
        "subprocess.CREATE_NO_WINDOW resolved to 0 on win32, so the value arm "
        "above is comparing nothing to nothing"
    )
    assert EXPECTED_FLAG == 0x08000000, (
        f"CREATE_NO_WINDOW is {EXPECTED_FLAG!r}, not the documented 0x08000000"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="the POSIX half of the platform guard")
def test_the_module_imports_and_spawns_on_posix(spawned):
    """The POSIX arm: the flag is inert, not absent, and nothing raised.

    `subprocess` rejects a non-zero `creationflags` off Windows, so the guard
    has to resolve to `0` there rather than be omitted - and the `rsp` fixture
    importing the module at all is the other half of this arm.
    """
    assert spawned.kwargs["creationflags"] == 0, (
        "a non-zero creationflags off Windows is a ValueError from subprocess"
    )


def test_the_guard_resolves_to_zero_when_the_attribute_is_absent(monkeypatch):
    """THE POSIX BRANCH, MEASURED ON THIS HOST rather than skipped off it.

    `test_the_module_imports_and_spawns_on_posix` above only ever runs on the
    lane it describes, so on Windows the Linux behaviour would be asserted by
    nothing at all - and a Linux-only type or import error has been reproduced
    in this tree before. This arm deletes `subprocess.CREATE_NO_WINDOW`, reloads
    the module, and checks the guard degrades to `0`: the value `subprocess.run`
    already uses when `creationflags` is not given, which is why the kwarg can
    stay unconditional instead of sitting behind a platform branch.

    It is a simulation of the ATTRIBUTE's absence and nothing more. It does not
    claim to run POSIX process creation.
    """
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)
    assert not hasattr(subprocess, "CREATE_NO_WINDOW"), "the simulation did not take"

    spec = importlib.util.spec_from_file_location("responder_posix_simulated", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._NO_WINDOW == 0, (
        f"the guard resolved to {module._NO_WINDOW!r} with the attribute absent - "
        "a non-zero creationflags off Windows is a ValueError from subprocess"
    )


def test_the_other_spawn_kwargs_survived(spawned):
    """THE SURVIVAL GUARD for the edit that added the flag.

    An arm that only checks the new kwarg scores full marks against a diff that
    added `creationflags` and dropped `timeout` - and a spawn with no ceiling is
    the exact failure `_spawn_headless`'s own docstring says the timeout exists
    to prevent. So the kwargs the spawn had BEFORE this slice are named here.
    """
    for name in ("input", "capture_output", "text", "timeout", "cwd", "check"):
        assert name in spawned.kwargs, (
            f"{name} vanished from the spawn - adding the flag must not cost a "
            "pre-existing kwarg"
        )
    assert spawned.kwargs["timeout"] == pytest.approx(rsp_bounds_timeout()), (
        "the spawn's timeout no longer comes from Bounds"
    )
    assert spawned.kwargs["check"] is False, "check=False is load-bearing for the failure path"


def rsp_bounds_timeout() -> float:
    """`Bounds().spawn_timeout_seconds`, read rather than retyped."""
    spec = importlib.util.spec_from_file_location("responder_bounds_probe", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return float(module.Bounds().spawn_timeout_seconds)


def test_the_spawn_site_census_is_one():
    """SCOPE ARM, and the only text-shaped one here.

    It does not grade the flag - the arms above do that. It grades the
    POPULATION, so that a second `subprocess.run` added to this module later
    cannot slip in unflagged behind arms that only ever exercise the first one.
    If this goes red, the answer is to flag the new spawn and raise the count,
    never to loosen the pattern.
    """
    text = MODULE.read_text(encoding="utf-8")
    sites = re.findall(r"subprocess\.(?:run|Popen|call|check_output|check_call)\s*\(", text)
    assert len(sites) == 1, (
        f"this module now has {len(sites)} spawn sites {sites} and this file's "
        "behaviour arms only exercise _spawn_headless. Flag the new one and "
        "raise this count."
    )
    flagged = re.findall(r"creationflags\s*=", text)
    assert len(flagged) == len(sites), (
        f"{len(sites)} spawn sites but {len(flagged)} creationflags kwargs - "
        "one of them flashes a console window"
    )
