"""Console-subsystem children of windowless parents are graded for the no-window flag.

THE RULE. RC's `CHANNEL.md` v1 section 5, adopted fleet-wide: every
console-subsystem CHILD of a windowless parent - a `pythonw` process, or any
hook running under the desktop harness - needs `creationflags=CREATE_NO_WINDOW`
on the spawn, or it flashes a console window. THE INTERPRETER TOKEN REMOVES NO
FLASH: swapping `python` for `pythonw` at a hook command is measured INERT for
this, so the fix has to land on the spawn and cannot land on the command line.
CREATIONFLAGS ARE ALSO NOT INHERITED, so the fix cannot land on a parent either
- it lands on each spawn, one at a time, which is why this file grades sites
rather than processes.

WHAT IS CONFIRMED AND WHAT IS NOT, because the difference is the whole reason
this docstring is longer than the tests. RC ran a positive control on
2026-09-15 and it PASSED on all three arms: both unflagged spawns under a
windowless `pythonw` parent produced a `ConsoleWindowClass` event, the
`CREATE_NO_WINDOW` spawn produced NONE, and a heartbeat landed after the last
spawn with no liveness gap. That CONFIRMS THE DETECTOR AND THE FLAG. It does
NOT confirm that the residual flash an operator observed came from any
particular spawn - that attribution stays PROBABLE at n=1 and is not claimed
here.

THE TWO SITES GRADED, and both are in the windowless-parent population:

  tools/moon_sync_responder.py   `_spawn_headless` launches the headless
                                 `claude` shim, a console `cmd.exe` entry point
                                 on this box - which is why that function has to
                                 resolve it through `shutil.which` at all.
  tools/first_run_capture.py     `poll_registry` spawns `reg query`. Its parent
                                 is MORE windowless than `pythonw`, not less:
                                 `tools/capture_supervisor.py` starts this
                                 daemon through `spawn_detached`, whose flags are
                                 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`,
                                 and DETACHED_PROCESS means the daemon owns no
                                 console at all. It is also a LOOP - three
                                 registry keys, `registry_every` defaulting to
                                 15 ticks, launched at `--interval 2`, so the
                                 unflagged form allocated three consoles every
                                 thirty seconds for the life of the daemon.

WHY THE BEHAVIOUR ARMS ARE NOT SOURCE-TEXT ARMS. "the module's source contains
CREATE_NO_WINDOW" pins FORMAT, not behaviour: it survives a mutant that passes
the flag to the wrong call or into a dead constant nobody reads. So the arms on
the responder monkeypatch `subprocess.run` and grade THE KWARGS THE RESPONDER
ACTUALLY PASSES.

WHY A CENSUS IS NEEDED ANYWAY, AND WHY IT IS AN AST WALK RATHER THAN A REGEX.
Behaviour cannot see a spawn it does not reach, so a second unflagged spawn
added on a cold path is invisible to every monkeypatch arm. Only a census over
the source can see one. AN EARLIER VERSION OF THIS FILE COUNTED
`subprocess\\.(run|Popen|...)\\(` WITH A REGEX AND AN ADVERSARY DEFEATED IT
TWICE, with mutants that passed green at exit 0:

    from subprocess import Popen as _P   ...   _P([...])
    os.system(...)

Neither is an exotic construction; the first is ordinary Python and the second
is the shortest way to spawn anything. The regex census's wording claimed to
grade "the POPULATION", and against those two it did not. The repair is the
WIDER INSTRUMENT rather than the narrower claim: `unflagged_spawn_sites` below
resolves import bindings - `import subprocess as sp`, `from subprocess import
Popen as _P`, `from os import system as _s` - and walks every `Call` node, so an
alias is followed rather than missed.

THE `os` FAMILY IS FORBIDDEN OUTRIGHT, not merely required to be flagged.
`os.system`, `os.popen`, `os.spawn*` and `os.startfile` take no `creationflags`
parameter at all, so there is no flagged form of them to ask for. In the
windowless-parent population the only correct answer is a `subprocess` call that
can carry the flag.

WHAT THE ARMS HERE CANNOT SEE, stated rather than implied:

  - A `creationflags=0` LITERAL IS INDISTINGUISHABLE ON THE LINUX LANE. On
    Windows `test_the_creationflags_value_is_the_no_window_flag` kills it,
    because `EXPECTED_FLAG` is `0x08000000` there. On Linux `EXPECTED_FLAG` is
    legitimately `0`, so the mutant's value matches, and the non-vacuity arm
    that would notice is `skipif sys.platform != "win32"`. That mutant is
    therefore killed by this file ONLY on Windows.
  - THE CENSUS GRADES CALL SITES, NOT REACHABILITY. It cannot say whether a
    flagged spawn is ever executed, and it does not try to.
  - NO ARM HERE OBSERVES A CONSOLE WINDOW. The flag's effect on real process
    creation rests on RC's control, cited above as theirs and not re-run here.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"
CAPTURE = ROOT / "tools" / "first_run_capture.py"

#: What the flag must resolve to on the host the test is running on. Derived
#: from `subprocess` itself rather than retyped as `0x08000000`, because a
#: literal here would agree with itself and with nothing else.
EXPECTED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)

#: `subprocess` entry points that create a process AND accept `creationflags`.
_SUBPROCESS_SPAWNS = frozenset({"run", "Popen", "call", "check_output", "check_call"})

#: `os` routes that create a process and CANNOT carry `creationflags`. Matched by
#: exact name plus the `spawn` prefix, which covers spawnl, spawnle, spawnlp,
#: spawnlpe, spawnv, spawnve, spawnvp and spawnvpe without listing all eight.
_OS_SPAWNS = frozenset({"system", "popen", "startfile"})
_OS_SPAWN_PREFIX = "spawn"


def _is_os_spawn(attr: str) -> bool:
    return attr in _OS_SPAWNS or attr.startswith(_OS_SPAWN_PREFIX)


def _module_aliases(tree: ast.AST, module: str) -> set[str]:
    """Local names bound to `module` itself - `import os`, `import os as _o`."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    found.add(alias.asname or alias.name)
    return found


def _member_aliases(tree: ast.AST, module: str) -> dict[str, str]:
    """Local name -> member name for `from <module> import x, y as z`."""
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            for alias in node.names:
                found[alias.asname or alias.name] = alias.name
    return found


def unflagged_spawn_sites(source: str) -> list[str]:
    """Every process-creating call in `source` that cannot be windowless.

    Returns a human-readable line per offending site, empty when clean. Import
    bindings are RESOLVED rather than assumed, because the two mutants that
    defeated this file's predecessor were both alias-shaped.

    A `**kwargs` splat on a subprocess spawn counts as UNFLAGGED. The flag may
    well be inside it, but a census that accepted a splat could be silenced by
    writing one, and an instrument that can be silenced by the thing it watches
    for is not an instrument.
    """
    tree = ast.parse(source)
    sp_mods = _module_aliases(tree, "subprocess")
    os_mods = _module_aliases(tree, "os")
    sp_members = _member_aliases(tree, "subprocess")
    os_members = _member_aliases(tree, "os")

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        family = attr = None
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id in sp_mods and func.attr in _SUBPROCESS_SPAWNS:
                family, attr = "subprocess", func.attr
            elif func.value.id in os_mods and _is_os_spawn(func.attr):
                family, attr = "os", func.attr
        elif isinstance(func, ast.Name):
            if func.id in sp_members and sp_members[func.id] in _SUBPROCESS_SPAWNS:
                family, attr = "subprocess", sp_members[func.id]
            elif func.id in os_members and _is_os_spawn(os_members[func.id]):
                family, attr = "os", os_members[func.id]

        if family is None or attr is None:
            continue

        if family == "os":
            offenders.append(
                f"line {node.lineno}: os.{attr} takes no creationflags, so it "
                "has no windowless form - use subprocess with creationflags"
            )
            continue

        named = {kw.arg for kw in node.keywords}
        if "creationflags" not in named:
            reason = "a **kwargs splat, which this census does not accept" if None in named else "no creationflags"
            offenders.append(f"line {node.lineno}: subprocess.{attr} has {reason}")
    return offenders


# ---------------------------------------------------------------------------
# The census, over both real files, plus the arms proving it can fire.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", [MODULE, CAPTURE], ids=["responder", "capture_daemon"])
def test_no_spawn_in_a_windowless_parent_is_unflagged(target: Path):
    """THE CENSUS over each real file in the population."""
    offenders = unflagged_spawn_sites(target.read_text(encoding="utf-8"))
    assert offenders == [], (
        f"{target.name} spawns a console child without the no-window flag, so it "
        f"flashes a console window under a windowless parent: {offenders}"
    )


#: The two mutants that defeated the regex census, hand-typed. HAND-TYPED IS THE
#: POINT: a fixture derived from the real file the same way the census derives
#: its input cannot show that derivation being wrong.
_ALIASED_POPEN = (
    "from subprocess import Popen as _P\n"
    "\n"
    "\n"
    "def go():\n"
    '    return _P(["reg", "query", "HKCU"])\n'
)

_OS_SYSTEM = (
    "import os\n"
    "\n"
    "\n"
    "def go():\n"
    '    return os.system("reg query HKCU")\n'
)

_RENAMED_MODULE = (
    "import subprocess as sp\n"
    "\n"
    "\n"
    "def go():\n"
    '    return sp.run(["reg"], check=False)\n'
)

_SPLAT_ONLY = (
    "import subprocess\n"
    "\n"
    "\n"
    "def go(kw):\n"
    '    return subprocess.run(["reg"], **kw)\n'
)

#: The CONTROL. Properly flagged, and through an alias, so a census that fired
#: on aliases indiscriminately fails here instead of passing the arms above.
_FLAGGED_ALIAS = (
    "import subprocess\n"
    "from subprocess import Popen as _P\n"
    "\n"
    "_N = getattr(subprocess, 'CREATE_NO_WINDOW', 0)\n"
    "\n"
    "\n"
    "def go():\n"
    '    _P(["reg"], creationflags=_N)\n'
    '    return subprocess.run(["reg"], check=False, creationflags=_N)\n'
)


@pytest.mark.parametrize(
    "label,source",
    [
        ("aliased Popen", _ALIASED_POPEN),
        ("os.system", _OS_SYSTEM),
        ("renamed subprocess module", _RENAMED_MODULE),
        ("kwargs splat", _SPLAT_ONLY),
    ],
)
def test_the_census_fires_on_each_route_that_defeated_its_predecessor(label, source):
    """NON-VACUITY. The first two are the adversary's actual passing mutants.

    Without this arm the census above is indistinguishable from a function that
    returns `[]` unconditionally - which is exactly what the regex version
    effectively was for these four shapes.
    """
    assert unflagged_spawn_sites(source) != [], (
        f"the census cannot see an unflagged spawn reached through {label}, so a "
        "clean report from it says nothing"
    )


def test_the_census_does_not_fire_on_a_correctly_flagged_alias():
    """THE SURVIVAL GUARD for the census itself.

    A detector that flagged every aliased call would score full marks on all
    four arms above by condemning correct code too, and would then have to be
    loosened the first time someone wrote a legitimate alias.
    """
    assert unflagged_spawn_sites(_FLAGGED_ALIAS) == []


def test_the_census_population_is_not_empty():
    """The floor. A census that found no spawn at all in either file would pass
    `test_no_spawn_in_a_windowless_parent_is_unflagged` by looking at nothing."""
    for target in (MODULE, CAPTURE):
        tree = ast.parse(target.read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _SUBPROCESS_SPAWNS
        ]
        assert calls, f"{target.name} has no subprocess spawn, so the census graded nothing"


# ---------------------------------------------------------------------------
# The behaviour arms, on the responder's one spawn.
# ---------------------------------------------------------------------------


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

    ON WINDOWS ONLY does this kill a `creationflags=0` literal. Off Windows
    `EXPECTED_FLAG` is legitimately 0 and that mutant is indistinguishable here;
    the module docstring records the limit.
    """
    assert spawned.kwargs["creationflags"] == EXPECTED_FLAG, (
        f"creationflags is {spawned.kwargs['creationflags']!r}, expected "
        f"{EXPECTED_FLAG!r} - on Windows that is subprocess.CREATE_NO_WINDOW, "
        "and off Windows it is 0, which is subprocess.run's own default"
    )


@pytest.mark.skipif(sys.platform != "win32", reason="CREATE_NO_WINDOW is a Windows-only attribute")
def test_the_resolved_flag_is_not_zero_here():
    """NON-VACUITY for the value arm on the platform where it can bite.

    Without it, the value arm could pass on Windows against a responder that
    resolved the flag to `0` - through a typo in the `getattr` name, say - and
    the assertion would read `0 == 0` while every spawn kept flashing.
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


@pytest.mark.parametrize("target", [MODULE, CAPTURE], ids=["responder", "capture_daemon"])
def test_the_guard_resolves_to_zero_when_the_attribute_is_absent(monkeypatch, target):
    """THE POSIX BRANCH, MEASURED ON THIS HOST rather than skipped off it.

    `test_the_module_imports_and_spawns_on_posix` only ever runs on the lane it
    describes, so on Windows the Linux behaviour would be asserted by nothing at
    all - and a Linux-only failure has been reproduced in this tree before. This
    arm deletes `subprocess.CREATE_NO_WINDOW`, reloads each module, and checks
    the guard degrades to `0`: the value `subprocess.run` already uses when
    `creationflags` is not given, which is why the kwarg can stay unconditional
    instead of sitting behind a platform branch.

    It is a simulation of the ATTRIBUTE's absence and nothing more. It does not
    claim to run POSIX process creation.
    """
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)
    assert not hasattr(subprocess, "CREATE_NO_WINDOW"), "the simulation did not take"

    spec = importlib.util.spec_from_file_location(f"posix_simulated_{target.stem}", target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._NO_WINDOW == 0, (
        f"{target.name} resolved the guard to {module._NO_WINDOW!r} with the "
        "attribute absent - a non-zero creationflags off Windows is a ValueError"
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
