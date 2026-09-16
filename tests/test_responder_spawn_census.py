"""A SOURCE CENSUS of spawn sites, with its claim narrowed to what it can support.

SPLIT OUT OF `tests/test_responder_no_console_window.py` ON 2026-09-16, and the
split is the point rather than a tidy-up. That module mixed two kinds of arm and
the mixture had a measured consequence.

  - THE BEHAVIOUR ARMS drive `_spawn_headless` through a fixture and grade the
    kwargs it really passes. When a mutation lands inside that function they
    redden, and a reddening there is a LEGITIMATE KILL.
  - THE CENSUS ARMS, the ones in this file, read the target's SOURCE. A reader of
    source can redden over syntax and shape, which is the thing
    `SHAPE_GRADER_MODULES` exists to keep out of a mutation campaign.

`tools/gate_mutation_runner.SHAPE_GRADER_MODULES` excludes PER MODULE, via
`--ignore` in `suite_argv`. So while both kinds sat in one file, declaring that
file deleted the legitimate kills along with the shape grading. THIS file is the
declared one; the behaviour arms stay in the campaign where they can kill.

THIS FILE IS DELIBERATELY WRITTEN IN THE DETECTOR-VISIBLE FORM. It binds
`RESPONDER` at module level and calls `RESPONDER.read_text(...)` directly, rather
than routing the read through a `pytest.mark.parametrize` argument or a local
variable. `gate_mutation_runner._binds_and_reads_responder` matches a read
attribute on a module-level `Name`, and the previous arrangement slipped past it
by accident - which meant a declared shape grader that the detector could not
see, and an arm elsewhere that could no longer witness that every declared entry
is a detected reader. Keeping this file visible restores that witness. Do not
"simplify" the reads below into a parametrized helper; the direct form is load
bearing.

THE RULE BEING ENFORCED. RC's `CHANNEL.md` v1 section 5: every console-subsystem
CHILD of a windowless parent needs `creationflags=CREATE_NO_WINDOW` on the spawn,
or it flashes a console window. The interpreter token removes no flash, and
creationflags are NOT INHERITED, so the fix lands on each spawn individually -
which is why a census of SITES is the instrument.

WHY THIS FILE STOPPED WIDENING ITS MATCHER. The census has been defeated twice by
inputs wider than it models: first an aliased import and `os.system` against a
regex, then an assignment rebinding and two unenumerated callables against the
ast walk that replaced it. This tree's rule after a second defeat is to stop
widening and ask what claim the mechanism can actually support. A third widening
loses to the fourth input. So `unflagged_spawn_sites` now states a NARROW claim it
can keep, and the things it cannot see are enumerated below as measured fact
instead of being implied away.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESPONDER = ROOT / "tools" / "moon_sync_responder.py"
CAPTURE = ROOT / "tools" / "first_run_capture.py"

#: `subprocess` entry points that create a process AND accept `creationflags`.
_SUBPROCESS_SPAWNS = frozenset({"run", "Popen", "call", "check_output", "check_call"})

#: `subprocess` entry points that create a process and CANNOT carry
#: `creationflags`. Both run their argument through `check_output(shell=True)`, so
#: each one spawns a `cmd.exe`, and neither exposes a flags parameter to suppress
#: its console. They were MISSING from the enumeration above until 2026-09-16 -
#: an omission from a declared list, not a limit of the mechanism, which is why
#: closing it is a completion rather than another widening.
_SUBPROCESS_FORBIDDEN = frozenset({"getoutput", "getstatusoutput"})

#: `os` routes that create a process and CANNOT carry `creationflags`. Matched by
#: exact name plus the `spawn` prefix, which covers spawnl, spawnle, spawnlp,
#: spawnlpe, spawnv, spawnve, spawnvp and spawnvpe without listing all eight.
_OS_SPAWNS = frozenset({"system", "popen", "startfile"})
_OS_SPAWN_PREFIX = "spawn"

#: EVERY INPUT THIS CENSUS IS MEASURED BLIND TO. Each was run against the live
#: module on 2026-09-16 and left it at 14 passed / 1 skipped / exit 0, so each is
#: an observation and not a worry. They are recorded rather than modelled: the
#: first and third would require the census to become a dataflow analysis, and a
#: partial dataflow analysis is the fourth input waiting to happen.
#:
#:   ASSIGNMENT REBINDING. `_sp = subprocess` and then `_sp.Popen([...])`.
#:   Measured invisible both on a cold path and inline in `_spawn_headless`.
#:   `unflagged_spawn_sites` resolves names bound by IMPORT STATEMENTS only; a
#:   name bound by an assignment is not an import binding and is not followed.
#:
#:   ATTRIBUTE-PATH IMPORTS. `import os.path` binds the name `os`, but
#:   `_module_aliases` compares `alias.name` to the module name exactly, so
#:   `import os.path` followed by `os.system(...)` is invisible in a file with no
#:   plain `import os`. Same shape for `import subprocess.something`.
#:
#:   ANY INDIRECTION THAT IS NOT AN IMPORT BINDING. A callable fetched with
#:   `getattr`, stored in a dict, passed as a parameter, or produced by a factory.
#:
#: WHAT FOLLOWS FROM THAT. A clean result from this census means "no spawn of the
#: enumerated shapes, reached through an import binding, is unflagged". It does
#: NOT mean "this file cannot flash a console window". The behaviour arms in
#: `tests/test_responder_no_console_window.py` are what grade the spawn that
#: actually runs, and they are the arms a campaign keeps.
_BLIND_TO = (
    "assignment rebinding: _sp = subprocess; _sp.Popen([...])",
    "attribute-path imports: import os.path; os.system(...)",
    "non-import indirection: getattr, dict lookup, parameter, factory",
)


def _is_os_spawn(attr: str) -> bool:
    return attr in _OS_SPAWNS or attr.startswith(_OS_SPAWN_PREFIX)


def _module_aliases(tree: ast.AST, module: str) -> set[str]:
    """Local names bound to `module` itself - `import os`, `import os as _o`.

    EXACT MATCH ON `alias.name`, which is why `import os.path` is in `_BLIND_TO`.
    """
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
    """Every process-creating call in `source` that is reached through a name an
    IMPORT STATEMENT in `source` binds, drawn from the enumerated callables in
    `_SUBPROCESS_SPAWNS`, `_SUBPROCESS_FORBIDDEN` and `_OS_SPAWNS`, and that
    cannot be made windowless as written.

    THAT SENTENCE IS THE WHOLE CLAIM AND IT IS DELIBERATELY NARROW. It is not
    "every process-creating call": an earlier wording said that, and the wording
    was refuted twice - by an aliased import and `os.system` against a regex, then
    by an assignment rebinding and two unenumerated callables against this walk.
    `_BLIND_TO` above lists what is outside the claim, each entry measured rather
    than supposed. An empty result is a statement about the enumerated,
    import-bound population and about nothing else.

    A site is reported when it cannot be windowless as written:

      - a `subprocess` spawn with no `creationflags` keyword at all;
      - a `subprocess` spawn whose `creationflags` is the literal `0`, which is
        the parameter's own default and therefore not a flag. This is the one
        value check here, and it exists because a literal zero is INVISIBLE to
        the behaviour arms on POSIX - where the guard legitimately resolves to 0 -
        and was invisible for the capture daemon on every platform, since no
        behaviour arm drove that spawn until 2026-09-16;
      - a `**kwargs` splat on a `subprocess` spawn. The flag may be inside it, but
        a census that accepted a splat could be silenced by writing one, and an
        instrument that the watched code can silence is not an instrument;
      - any call to `_SUBPROCESS_FORBIDDEN` or `_OS_SPAWNS`, which take no
        `creationflags` parameter and so have no flagged form to ask for.
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
            elif func.value.id in sp_mods and func.attr in _SUBPROCESS_FORBIDDEN:
                family, attr = "forbidden", f"subprocess.{func.attr}"
            elif func.value.id in os_mods and _is_os_spawn(func.attr):
                family, attr = "forbidden", f"os.{func.attr}"
        elif isinstance(func, ast.Name):
            if func.id in sp_members and sp_members[func.id] in _SUBPROCESS_SPAWNS:
                family, attr = "subprocess", sp_members[func.id]
            elif func.id in sp_members and sp_members[func.id] in _SUBPROCESS_FORBIDDEN:
                family, attr = "forbidden", f"subprocess.{sp_members[func.id]}"
            elif func.id in os_members and _is_os_spawn(os_members[func.id]):
                family, attr = "forbidden", f"os.{os_members[func.id]}"

        if family is None or attr is None:
            continue

        if family == "forbidden":
            offenders.append(
                f"line {node.lineno}: {attr} takes no creationflags, so it has no "
                "windowless form - use a subprocess call that can carry the flag"
            )
            continue

        named = {kw.arg for kw in node.keywords}
        if None in named and "creationflags" not in named:
            offenders.append(
                f"line {node.lineno}: subprocess.{attr} passes a **kwargs splat, "
                "which this census does not accept as a flag"
            )
            continue
        if "creationflags" not in named:
            offenders.append(f"line {node.lineno}: subprocess.{attr} has no creationflags")
            continue
        for keyword in node.keywords:
            if keyword.arg != "creationflags":
                continue
            value = keyword.value
            if isinstance(value, ast.Constant) and value.value == 0:
                offenders.append(
                    f"line {node.lineno}: subprocess.{attr} passes creationflags=0, "
                    "which is the parameter's default and not a flag - pass the "
                    "module's CREATE_NO_WINDOW guard instead"
                )
    return offenders


# ---------------------------------------------------------------------------
# The census over each real file. Read DIRECTLY off the module-level names, so
# `_binds_and_reads_responder` can see this module. See the header.
# ---------------------------------------------------------------------------


def test_the_responder_has_no_unflagged_spawn():
    offenders = unflagged_spawn_sites(RESPONDER.read_text(encoding="utf-8"))
    assert offenders == [], (
        "tools/moon_sync_responder.py spawns a console child without the "
        f"no-window flag, so it flashes under a windowless parent: {offenders}"
    )


def test_the_capture_daemon_has_no_unflagged_spawn():
    offenders = unflagged_spawn_sites(CAPTURE.read_text(encoding="utf-8"))
    assert offenders == [], (
        "tools/first_run_capture.py spawns a console child without the no-window "
        f"flag, and its parent holds no console at all: {offenders}"
    )


def test_the_census_population_is_not_empty():
    """The floor. A census finding no spawn would pass both arms above by
    looking at nothing at all."""
    for target in (RESPONDER, CAPTURE):
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
# Non-vacuity. Every route below is one that DEFEATED a previous version of this
# census, or a value that defeated the behaviour arms. Hand-typed, because a
# fixture derived the way the census derives its input cannot show that
# derivation being wrong.
# ---------------------------------------------------------------------------

_ALIASED_POPEN = (
    "from subprocess import Popen as _P\n\n\ndef go():\n    return _P(['reg', 'query'])\n"
)
_OS_SYSTEM = "import os\n\n\ndef go():\n    return os.system('reg query')\n"
_RENAMED_MODULE = "import subprocess as sp\n\n\ndef go():\n    return sp.run(['reg'])\n"
_SPLAT_ONLY = "import subprocess\n\n\ndef go(kw):\n    return subprocess.run(['reg'], **kw)\n"
_GETOUTPUT = "import subprocess\n\n\ndef go():\n    return subprocess.getoutput('reg query')\n"
_GETSTATUSOUTPUT = (
    "import subprocess\n\n\ndef go():\n    return subprocess.getstatusoutput('reg query')\n"
)
_ALIASED_GETOUTPUT = (
    "from subprocess import getoutput as _g\n\n\ndef go():\n    return _g('reg query')\n"
)
_LITERAL_ZERO = (
    "import subprocess\n\n\ndef go():\n    return subprocess.run(['reg'], creationflags=0)\n"
)


@pytest.mark.parametrize(
    "label,source",
    [
        ("aliased Popen", _ALIASED_POPEN),
        ("os.system", _OS_SYSTEM),
        ("renamed subprocess module", _RENAMED_MODULE),
        ("kwargs splat", _SPLAT_ONLY),
        ("subprocess.getoutput", _GETOUTPUT),
        ("subprocess.getstatusoutput", _GETSTATUSOUTPUT),
        ("aliased getoutput", _ALIASED_GETOUTPUT),
        ("creationflags=0 literal", _LITERAL_ZERO),
    ],
)
def test_the_census_fires_on_each_route_that_defeated_an_earlier_version(label, source):
    assert unflagged_spawn_sites(source) != [], (
        f"the census cannot see an unflagged spawn reached through {label}, so a "
        "clean report from it says nothing about that route"
    )


#: The CONTROL. Correctly flagged, through both an alias and the module, so a
#: census that condemned aliases indiscriminately fails here rather than passing
#: every arm above.
_FLAGGED_ALIAS = (
    "import subprocess\n"
    "from subprocess import Popen as _P\n"
    "\n"
    "_N = getattr(subprocess, 'CREATE_NO_WINDOW', 0)\n"
    "\n\ndef go():\n"
    "    _P(['reg'], creationflags=_N)\n"
    "    return subprocess.run(['reg'], check=False, creationflags=_N)\n"
)


def test_the_census_does_not_fire_on_a_correctly_flagged_alias():
    """THE SURVIVAL GUARD. A detector that flagged every aliased call would score
    full marks on every arm above by condemning correct code too."""
    assert unflagged_spawn_sites(_FLAGGED_ALIAS) == []


# ---------------------------------------------------------------------------
# The blind list is itself graded, so it cannot rot into a comforting fiction.
# ---------------------------------------------------------------------------

_BLIND_REBIND = (
    "import subprocess\n_sp = subprocess\n\n\ndef go():\n    return _sp.Popen(['reg'])\n"
)
_BLIND_ATTR_PATH = "import os.path\n\n\ndef go():\n    return os.system('reg query')\n"


@pytest.mark.parametrize(
    "label,source",
    [
        ("assignment rebinding", _BLIND_REBIND),
        ("attribute-path import", _BLIND_ATTR_PATH),
    ],
)
def test_the_declared_blind_spots_really_are_blind(label, source):
    """THE HONESTY ARM, and it asserts the UNCOMFORTABLE direction on purpose.

    `_BLIND_TO` claims this census cannot see two specific shapes. A claim of
    incapacity is exactly the kind that rots silently: if someone later widens the
    walk to follow assignments, the entry becomes false and every reader of
    `_BLIND_TO` is then misled about what a clean result means. This arm goes red
    on that day and says so. It is NOT an instruction to keep the blind spot - the
    repair is to delete the `_BLIND_TO` entry and this parameter case together, in
    the same commit that widens the walk.
    """
    assert unflagged_spawn_sites(source) == [], (
        f"{label} is now VISIBLE to the census, so the _BLIND_TO entry describing "
        "it is false - delete that entry and this case together"
    )


def test_the_blind_list_is_not_empty_and_is_prose():
    """A floor on the disclosure itself. An empty `_BLIND_TO` beside a narrowed
    claim would read as "nothing is outside the claim", which is the
    overstatement this file was refuted twice for."""
    assert len(_BLIND_TO) >= 3, _BLIND_TO
    assert all(isinstance(entry, str) and len(entry) > 20 for entry in _BLIND_TO), _BLIND_TO
