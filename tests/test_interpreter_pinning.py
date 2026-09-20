"""A guard that shells out to Python must shell out to THE RUNNING Python.

The defect this module exists for, measured 2026-09-20 in this tree.
`tests/test_mypy_scope.py` launched `["python", "-m", "mypy"]`. That argv asks
"does SOME python agree with my arithmetic", when the question the arm means to
ask is "does THIS python agree". The two are the same interpreter often enough
that the arm looks healthy, and they come apart exactly where it matters.

THE RESOLUTION IS NOT A PATH LOOKUP, and that is the part worth writing down.
On Windows `CreateProcess` resolves a bare image name against the directory of
the CALLING image first, then the current directory, then `PATH`. Measured here
against a real venv, three names a reader would expect to coincide did not:

    sys.executable              <venv>\\Scripts\\python.exe
    shutil.which("python")      ...\\Programs\\Python\\Python314\\python.EXE
    subprocess.run(["python"])  ...\\Python\\pythoncore-3.11-64\\python.exe

Three different interpreters from one process. The one actually launched was
NOT the one `shutil.which` names, so a reader who reasons about `PATH` - or who
probes with `which` and believes the answer - reaches the wrong conclusion
about what ran. Prepending a directory to `PATH` did not move it either; four
levers were tried (inherited environment, `cwd` holding a foreign
`python.exe`, `env=` with the foreign directory first, and both together) and
none changed the resolution outside a venv.

The consequence for a guard is silent and total: `-m mypy` under the wrong
interpreter loads a different `site-packages`, so the arm either reports
`No module named mypy` or, worse, type-checks against a different set of
installed stubs and passes for the wrong reason.

WHY THIS DETECTOR FOLLOWS NAMES AND NOT CALL SITES. The first version of this
module matched a string literal sitting in argv[0] at the call site. An
adversarial pass defeated it in one line by reinstating the original defect in
the shape THIS MODULE'S OWN FIX had introduced:

    MYPY_ARGV = ("python", "-m", "mypy")
    subprocess.run(list(MYPY_ARGV), cwd="x")

argv[0] at that call site is a `Call`, not a literal, so the detector returned
no findings and every arm passed with the guarded defect present. Re-measured
here, the first version was blind to five of six defect shapes: a module-level
tuple splatted, `list()`-ed, or passed by name, and a head built by
`os.path.join` or an f-string. Only the bare literal was caught.

So the detector now RESOLVES argv[0] through module-level bindings before
judging it, and - this is the other half - it reports a head it cannot resolve
as UNRESOLVED rather than as clean. A detector that answers "no findings" when
it means "I could not tell" is the silent-empty shape, and this tree has
shipped it before. `tools/git_subprocess_census.py` already reached that
conclusion for git call sites and emits an UNRESOLVED row; this module borrows
its launcher resolution outright rather than shipping a weaker copy.

THE ARMS, AND WHICH KIND EACH ONE IS. Stated plainly because this tree has been
defeated twice by a shape arm sold as a behavioural one:

  * `test_no_launch_site_reaches_a_bare_interpreter` is a SHAPE ARM. It reads
    source through the AST and pins FORMAT. Resolving names makes it much
    harder to defeat than a literal match, but it is still defeated by a head
    that only exists at runtime - read from a file, computed in a branch,
    passed in as a parameter. Those are not silently blessed: they land in the
    UNRESOLVED census below, which is pinned, so a NEW one goes red and must be
    triaged by hand.
  * `test_the_detector_catches_every_known_defect_shape` is the load-bearing
    NON-VACUITY arm. It reinstates the real defect in each shape and requires
    each to be caught. It replaced the behavioural arm as the arm that proves
    this module works.
  * `test_the_pinned_argv_launches_the_running_interpreter` is a BEHAVIOURAL
    arm and it SKIPS LOUDLY where it cannot discriminate. On a host where a
    bare name already resolves to `sys.executable` it would pass with the
    defect present, which is an assertion about nothing; it says so and skips
    rather than reporting a green it has not earned.

THE NON-PYTHON LANE IS ENUMERATED TOO. An earlier version of this module
declared a corpus of `.py`, `.githooks/`, `.ps1` and `.yml` and missed `.js`
entirely, while `shell/` holds a live Node process that spawns Python by bare
name. See `DELIBERATE_JS_INTERPRETERS` for the triage.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tools.git_subprocess_census import _import_aliases, _launcher_for

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Spellings that name a Python interpreter rather than some other program.
INTERPRETER_NAMES = frozenset(
    {
        "python",
        "python3",
        "pythonw",
        "python.exe",
        "python3.exe",
        "pythonw.exe",
        "py",
    }
)

#: Dotted heads that ARE the running interpreter and are therefore the fix, not
#: the defect. Mirrors `NEVER_GIT_DOTTED` in the census module.
PINNED_DOTTED = frozenset({"sys.executable", "sys._base_executable"})

BARE = "BARE"
PINNED = "PINNED"
OTHER = "OTHER"
UNRESOLVED = "UNRESOLVED"

#: Python launch sites that reach a bare interpreter ON PURPOSE, with the
#: reason. Keyed by path and literal so a SECOND bare name in an already-listed
#: file still turns this red.
#:
#: Empty today. The one deliberate ladder in this tree - the ruff candidate
#: list in `tools/precommit_gate.py` - reaches its launcher through a splat of
#: a local, so it surfaces as an UNRESOLVED row rather than a BARE one. That is
#: the honest answer: this detector cannot see through it, and says so.
DELIBERATE_BARE_INTERPRETERS: dict[tuple[str, str], tuple[int, str]] = {}

#: Launch sites whose argv[0] cannot be resolved at parse time, pinned PER FILE
#: with the count. Line numbers are deliberately not pinned - they decay on the
#: next edit. A new unresolvable head anywhere bumps a count or adds a file and
#: turns this red, which forces a triage instead of allowing a silent addition.
#:
#: Measured 2026-09-20: 22 rows over 15 files, out of 94 launch sites in 158
#: tracked `.py` (51 other literals such as `git`, 21 already pinned to
#: `sys.executable`).
UNRESOLVED_CENSUS: dict[str, tuple[int, str]] = {
    "ops/check_task_liveness.py": (1, "PowerShell, resolved by a helper at call time."),
    "ops/supervisor.py": (
        1,
        "config.command, and the config default is built from sys.executable by "
        "default_child_python() in that same file.",
    ),
    "scripts/make_shortcut.py": (1, "PowerShell argv built by a helper."),
    "tests/test_commit_trailers.py": (1, "shutil.which of a shell, not a Python."),
    "tests/test_git_env_scrub.py": (2, "argv is a test-local fixture value."),
    "tests/test_hook_interpreter.py": (1, "_sh() resolves the POSIX shell under test."),
    "tests/test_interpreter_pinning.py": (
        2,
        "this module's own probes - one takes argv0 as a parameter, one "
        "stringifies a venv path it just created.",
    ),
    "tests/test_line_endings.py": (1, "args is a test-local fixture value."),
    "tests/test_session_hooks.py": (3, "argv rebound per parametrized case."),
    "tests/test_task_liveness.py": (3, "exe is the PowerShell under test."),
    "tools/capture_supervisor.py": (
        1,
        "spawn_detached takes argv from its caller; both call sites in that "
        "file pass sys.executable.",
    ),
    "tools/gate_mutation_runner.py": (
        1,
        "suite_argv() builds [sys.executable, -m, pytest, ...] in that file.",
    ),
    "tools/moon_sync_responder.py": (1, "shutil.which of the session command, not a Python."),
    "tools/precommit_gate.py": (
        2,
        "The ruff candidate ladder, and DELIBERATE. This gate runs on channels "
        "that do NOT share an interpreter - a git hook launched by whatever "
        "`sh` picked, a developer shell, CI - so it PROBES rather than guesses. "
        "sys.executable is already first in the ladder; the bare names are "
        "fallbacks for channels where it has no ruff, and ruff's verdict does "
        "not depend on site-packages the way mypy's file count does. See "
        "_ruff_candidates() in that file.",
    ),
    "tools/publish_next_session.py": (1, "PowerShell argv built by a helper."),
}

#: The `.js` lane, triaged 2026-09-20 rather than fixed, with the measurement.
#:
#: `shell/` is an Electron app that spawns the Python surface:
#:     shell/lib/supervisor.js:31   const DEFAULT_PYTHON = "pythonw.exe";
#:     shell/lib/supervisor.js:68   const python = input.python.trim() || DEFAULT_PYTHON;
#:     shell/lib/supervisor.js:69   const argv = [python, "-m", "surface"];
#:     shell/main.js:148            spawn(argv[0], argv.slice(1), {cwd: <repo root>, shell: false})
#:     shell/main.js:142            passes process.env.RESIN_PYTHON, normally UNSET
#: `shell:false` on Windows is `CreateProcess`, so the resolution order measured
#: at the top of this module applies here too, with the repo root in the search
#: path. This is the hiding-behind-a-parameter-default shape.
#:
#: TRIAGED DELIBERATE, on four measured grounds:
#:  1. There is no `sys.executable` to pin to. The running interpreter is Node,
#:     not Python, so the fix applied on the Python side has no analogue here.
#:  2. `pythonw.exe` rather than `python.exe` is a REQUIREMENT, not a drifted
#:     default - the windowless interpreter is what keeps a console from
#:     flashing. `ops/supervisor.py:default_child_python()` makes the same
#:     choice on the Python side, where it CAN derive it from sys.executable.
#:  3. An override exists and is wired: `RESIN_PYTHON` reaches `spawnArgv`.
#:  4. The value is actively pinned by `shell/test/lib.test.js`, so it is a
#:     stated contract rather than an accident.
#: IF a future session rules it a defect, the fix is not a literal swap: the
#: Python side would have to record its own `sys.executable` somewhere the
#: shell reads (the config `core/` already owns), and `shell/test/lib.test.js`
#: pins the current value so it would have to move in the same change.
DELIBERATE_JS_INTERPRETERS: dict[str, tuple[int, str]] = {
    "shell/lib/supervisor.js": (1, "DEFAULT_PYTHON - see the triage above."),
    "shell/test/lib.test.js": (
        4,
        "Test inputs and the assertion that PINS the default. Three supply an "
        "explicit interpreter as the argument under test; one asserts the "
        "default at line 252. None launches anything - spawnArgv only BUILDS "
        "an argv, and the spawn lives in shell/main.js.",
    ),
}


@dataclass(frozen=True)
class Head:
    """One launch site's argv[0], resolved as far as parse time allows."""

    lineno: int
    status: str
    detail: str


def _tracked(*patterns: str) -> tuple[str, ...]:
    """Tracked paths from GIT, the corpus every other sweep here uses."""
    require_git_repository()
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *patterns],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tuple(sorted(p for p in out.split("\0") if p))


def _dotted(node: ast.expr) -> str:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _module_bindings(tree: ast.AST) -> tuple[dict[str, ast.expr], set[str]]:
    """Module-level name bindings, plus the names bound more than once.

    A name bound twice cannot be resolved to one value, so it is reported
    rather than resolved to whichever assignment happened to be walked last.
    """
    bindings: dict[str, ast.expr] = {}
    rebound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            pairs = [(target, node.value) for target in node.targets]
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            pairs = [(node.target, node.value)]
        else:
            continue
        for target, value in pairs:
            if isinstance(target, ast.Name):
                if target.id in bindings:
                    rebound.add(target.id)
                bindings[target.id] = value
    return bindings, rebound


def _resolve_head(
    expr: ast.expr,
    bindings: dict[str, ast.expr],
    rebound: set[str],
    depth: int = 0,
) -> tuple[str, str]:
    """`(status, detail)` for an argv[0] expression, following names.

    Every branch returns SOMETHING. There is deliberately no fall-through that
    yields "clean" for an expression this function did not understand.
    """
    if depth > 5:
        return (UNRESOLVED, "binding chain deeper than five hops")
    if isinstance(expr, ast.Constant):
        if not isinstance(expr.value, str):
            return (UNRESOLVED, f"non-string argv[0] constant {expr.value!r}")
        if expr.value.lower() in INTERPRETER_NAMES:
            return (BARE, expr.value)
        return (OTHER, expr.value)
    if isinstance(expr, (ast.List, ast.Tuple)):
        if not expr.elts:
            return (UNRESOLVED, "empty argv display")
        first = expr.elts[0]
        if isinstance(first, ast.Starred):
            return _resolve_head(first.value, bindings, rebound, depth + 1)
        return _resolve_head(first, bindings, rebound, depth + 1)
    if isinstance(expr, ast.Name):
        if expr.id in rebound:
            return (UNRESOLVED, f"name {expr.id} is bound more than once")
        if expr.id not in bindings:
            return (UNRESOLVED, f"name {expr.id} has no module-level binding")
        return _resolve_head(bindings[expr.id], bindings, rebound, depth + 1)
    if isinstance(expr, ast.Attribute):
        dotted = _dotted(expr)
        if dotted in PINNED_DOTTED:
            return (PINNED, dotted)
        return (UNRESOLVED, f"attribute head {dotted or '<complex>'}")
    if isinstance(expr, ast.Call):
        callee = _dotted(expr.func)
        if callee in ("list", "tuple") and len(expr.args) == 1:
            return _resolve_head(expr.args[0], bindings, rebound, depth + 1)
        return (UNRESOLVED, f"head comes from a {callee or '<complex>'} call")
    if isinstance(expr, ast.JoinedStr):
        return (UNRESOLVED, "head is an f-string, so it exists only at runtime")
    if isinstance(expr, ast.BinOp):
        return (UNRESOLVED, "head is a concatenation")
    return (UNRESOLVED, f"head is a {type(expr).__name__} expression")


def _launch_heads(source: str) -> list[Head]:
    """Every subprocess launch in `source`, with argv[0] resolved or reported.

    Launcher resolution is BORROWED from `tools/git_subprocess_census.py`,
    which already handles `import subprocess as sp` and
    `from subprocess import run as grab`. A first draft re-derived it and
    missed `sp.Popen([...])` outright.
    """
    tree = ast.parse(source)
    imports = _import_aliases(tree)
    bindings, rebound = _module_bindings(tree)
    heads: list[Head] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        launch = _launcher_for(node, imports)
        if launch is None or launch.kind != "subprocess":
            continue
        status, detail = _resolve_head(node.args[0], bindings, rebound)
        heads.append(Head(lineno=node.lineno, status=status, detail=detail))
    return heads


def _bare(source: str) -> list[tuple[int, str]]:
    return [(h.lineno, h.detail) for h in _launch_heads(source) if h.status == BARE]


def test_the_corpus_is_real_so_the_sweep_is_not_vacuous():
    """A sweep over nothing agrees with every expectation."""
    tracked = _tracked("*.py")
    assert len(tracked) > 50, (
        f"only {len(tracked)} tracked .py found; the corpus query is broken and "
        "every sweep below would pass by finding nothing"
    )
    assert "tests/test_interpreter_pinning.py" in tracked, (
        "this module is not in its own corpus, so it could hold the very defect "
        "it guards against. Stage it."
    )
    assert _tracked("*.js"), "no tracked .js found, so the shell lane sweep is vacuous"


def test_the_detector_catches_every_known_defect_shape():
    """THE LOAD-BEARING NON-VACUITY ARM.

    Reinstates the real defect in every shape it is known to take, including
    the indirection this module's own fix introduced, which defeated the first
    version of this detector completely.
    """
    defect_shapes = {
        "bare literal at the call site": (
            "import subprocess\nsubprocess.run(['python', '-m', 'mypy'])\n"
        ),
        "module-level tuple, list()-ed": (
            "import subprocess\n"
            "MYPY_ARGV = ('python', '-m', 'mypy')\n"
            "subprocess.run(list(MYPY_ARGV), cwd='x')\n"
        ),
        "module-level tuple, splatted": (
            "import subprocess\n"
            "MYPY_ARGV = ('python', '-m', 'mypy')\n"
            "subprocess.run([*MYPY_ARGV], cwd='x')\n"
        ),
        "module-level list, passed by name": (
            "import subprocess\n"
            "MYPY_ARGV = ['python', '-m', 'mypy']\n"
            "subprocess.run(MYPY_ARGV, cwd='x')\n"
        ),
        "aliased launcher": (
            "import subprocess as sp\nsp.Popen(['pythonw.exe', '-m', 'surface'])\n"
        ),
        "launcher imported directly": (
            "from subprocess import check_output\ncheck_output(['py', '-c', 'pass'])\n"
        ),
    }
    missed = [label for label, src in defect_shapes.items() if not _bare(src)]
    assert not missed, (
        "the detector did NOT catch these defect shapes, so the guard below is "
        "blind to them:\n  " + "\n  ".join(missed)
    )


def test_the_detector_refuses_to_certify_a_head_it_cannot_read():
    """A head that only exists at runtime is REPORTED, never called clean.

    "No findings" must not be the answer to "I could not tell". That silent
    empty is the shape this tree keeps re-shipping.
    """
    opaque = {
        "join": "import subprocess, os\nsubprocess.run([os.path.join(d, 'python')])\n",
        "f-string": "import subprocess\nsubprocess.run([f'{d}/python', '-m', 'x'])\n",
        "parameter": "import subprocess\ndef go(argv):\n    subprocess.run(argv)\n",
        "concatenation": "import subprocess\nsubprocess.run([d + '/python'])\n",
        "conditional": "import subprocess\nsubprocess.run([a if b else 'python'])\n",
    }
    for label, src in opaque.items():
        heads = _launch_heads(src)
        assert heads, f"{label}: no launch site was seen at all"
        assert all(h.status == UNRESOLVED for h in heads), (
            f"{label}: head was certified as {[h.status for h in heads]} rather "
            "than reported UNRESOLVED"
        )


def test_the_detector_leaves_its_legitimate_neighbours_alone():
    """SURVIVORS arm. A sweep that scores full marks by deleting its
    neighbours has failed.

    The four shapes below are the real ones an earlier draft over-fired on in
    `tests/test_hook_interpreter.py`. None starts a process. A guard that flags
    them teaches contributors to switch it off.
    """
    survivors = {
        "candidate name tuple": 'CANDIDATES = ("python3", "python", "py")\n',
        "tuple of pairs": "for n, c in (('python3', a), ('python', b)):\n    pass\n",
        "assertion about output": "assert out.split() == ['python3', 'python', 'py']\n",
        "assertion about a ladder": "assert ['python', '-m', 'ruff'] in candidates\n",
        "a non-interpreter launch": "import subprocess\nsubprocess.run(['git', 'ls-files'])\n",
        "the fix itself": (
            "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'mypy'])\n"
        ),
        "the fix, indirected": (
            "import subprocess, sys\n"
            "MYPY_ARGV = (sys.executable, '-m', 'mypy')\n"
            "subprocess.run(list(MYPY_ARGV))\n"
        ),
    }
    for label, src in survivors.items():
        assert not _bare(src), f"the detector fired on a legitimate shape: {label}"


def test_no_launch_site_reaches_a_bare_interpreter():
    """SHAPE ARM - see the module docstring for exactly what defeats it."""
    offenders: list[str] = []
    counted: dict[tuple[str, str], int] = {}

    for rel in _tracked("*.py"):
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for head in _launch_heads(source):
            if head.status != BARE:
                continue
            key = (rel, head.detail)
            counted[key] = counted.get(key, 0) + 1
            if key not in DELIBERATE_BARE_INTERPRETERS:
                offenders.append(f"{rel}:{head.lineno} reaches {head.detail!r}")

    assert not offenders, (
        "a launch site reaches an interpreter by bare name, so it runs whatever "
        "the platform resolves that name to rather than the interpreter running "
        "this suite:\n  "
        + "\n  ".join(offenders)
        + "\n\nUse sys.executable. If a foreign interpreter is the POINT of the "
        "call site, add it to DELIBERATE_BARE_INTERPRETERS with a reason - an "
        "unexplained bare name is indistinguishable from the defect."
    )

    drifted = [
        f"{rel}: {counted.get((rel, literal), 0)} occurrences of {literal!r}, "
        f"expected {expected}"
        for (rel, literal), (expected, _r) in DELIBERATE_BARE_INTERPRETERS.items()
        if counted.get((rel, literal), 0) != expected
    ]
    assert not drifted, (
        "the deliberate-bare-interpreter budget moved:\n  " + "\n  ".join(drifted)
    )


def test_the_unresolvable_heads_are_the_ones_already_triaged():
    """Pins the census of heads the shape arm CANNOT read.

    This is what stops an unreadable head being a free pass. A new one bumps a
    count or adds a file and this goes red, so it gets looked at by a human
    instead of joining a silent majority.
    """
    tally: dict[str, int] = {}
    where: dict[str, list[str]] = {}
    for rel in _tracked("*.py"):
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for head in _launch_heads(source):
            if head.status != UNRESOLVED:
                continue
            tally[rel] = tally.get(rel, 0) + 1
            where.setdefault(rel, []).append(f"{rel}:{head.lineno} {head.detail}")

    expected = {rel: count for rel, (count, _r) in UNRESOLVED_CENSUS.items()}
    if tally != expected:
        new = sorted(set(tally) - set(expected))
        gone = sorted(set(expected) - set(tally))
        moved = sorted(
            f"{rel}: {tally[rel]} now, {expected[rel]} pinned"
            for rel in set(tally) & set(expected)
            if tally[rel] != expected[rel]
        )
        detail = "\n  ".join(line for rel in new for line in where[rel])
        raise AssertionError(
            "the census of unresolvable launch heads moved.\n"
            f"  files newly unresolvable: {new}\n"
            f"  files no longer present : {gone}\n"
            f"  counts that moved       : {moved}\n"
            + (f"  new rows:\n  {detail}\n" if detail else "")
            + "Triage each one: if its argv[0] can reach a bare interpreter, "
            "pin it to sys.executable. If it cannot, add it to "
            "UNRESOLVED_CENSUS with the measured reason."
        )


def test_the_shell_lane_holds_only_triaged_interpreters():
    """The `.js` lane, which an earlier version of this module never swept.

    `shell/` spawns Python from Node with `shell:false`, which on Windows is
    `CreateProcess` - the same resolution this module exists for. There is no
    `sys.executable` to pin to from a Node process, so the entries here are
    triaged rather than fixed; the reasoning is on DELIBERATE_JS_INTERPRETERS.
    """
    import re

    pattern = re.compile(
        r"""["'](python|python3|pythonw|py|python\.exe|python3\.exe|pythonw\.exe)["']"""
    )
    counted: dict[str, int] = {}
    sightings: dict[str, list[str]] = {}
    for rel in _tracked("*.js", "*.mjs", "*.cjs"):
        for lineno, line in enumerate(
            (REPO_ROOT / rel).read_text(encoding="utf-8").splitlines(), 1
        ):
            for _ in pattern.finditer(line):
                counted[rel] = counted.get(rel, 0) + 1
                sightings.setdefault(rel, []).append(f"{rel}:{lineno} {line.strip()}")

    expected = {rel: count for rel, (count, _r) in DELIBERATE_JS_INTERPRETERS.items()}
    assert counted == expected, (
        "the shell lane's interpreter names moved.\n"
        f"  found  : {counted}\n"
        f"  pinned : {expected}\n"
        "Every bare interpreter in a spawned argv must be triaged. Add it to "
        "DELIBERATE_JS_INTERPRETERS with a measured reason, or fix it - and note "
        "that shell/test/lib.test.js pins the current default, so a fix has to "
        "move both in one change.\n  "
        + "\n  ".join(line for rows in sightings.values() for line in rows)
    )


def test_every_recorded_entry_carries_a_reason():
    """An allowlist whose entries need no justification is a disabled guard."""
    tables = (
        ("DELIBERATE_BARE_INTERPRETERS", DELIBERATE_BARE_INTERPRETERS),
        ("UNRESOLVED_CENSUS", UNRESOLVED_CENSUS),
        ("DELIBERATE_JS_INTERPRETERS", DELIBERATE_JS_INTERPRETERS),
    )
    for table_name, table in tables:
        for key, (expected, reason) in table.items():
            assert expected >= 1, f"{table_name}[{key}] allows zero, so it is dead weight"
            assert len(reason) > 30, (
                f"{table_name}[{key}] has no real reason recorded: {reason!r}"
            )


def _resolved_interpreter(argv0: str) -> tuple[str, int, str]:
    """Ask the interpreter `argv0` names to report its own path."""
    done = subprocess.run(
        [argv0, "-c", "import sys; print(sys.executable)"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return done.stdout.strip(), done.returncode, done.stderr.strip()


def test_the_pinned_argv_launches_the_running_interpreter():
    """BEHAVIOURAL arm - and it SKIPS LOUDLY where it cannot discriminate.

    It takes the argv `tests/test_mypy_scope.py` ACTUALLY shells out with and
    reads back the path that interpreter reports for ITSELF. Importing the real
    constant is load-bearing: a copy of the argv spelled out here would pass
    while the guard next door launched something else.

    The skip matters as much as the assertion. On a host where a bare name
    already resolves to `sys.executable` - which is the case on the machine
    this was written on, outside a venv - this arm passes WITH THE DEFECT
    PRESENT. Reporting that as green would be a false negative dressed as
    evidence, so it declines to answer instead.
    """
    from tests.test_mypy_scope import MYPY_ARGV

    bare_reported, bare_rc, _bare_err = _resolved_interpreter("python")
    if bare_rc == 0 and bare_reported and Path(bare_reported) == Path(sys.executable):
        pytest.skip(
            "cannot discriminate on this host: a bare 'python' already resolves "
            f"to {sys.executable}, so this assertion would hold with the defect "
            "present. test_the_detector_catches_every_known_defect_shape is the "
            "arm carrying this property here."
        )

    reported, rc, err = _resolved_interpreter(MYPY_ARGV[0])
    assert rc == 0, f"the guard's interpreter would not start: rc={rc} {err!r}"
    assert Path(reported) == Path(sys.executable), (
        "the mypy scope guard launches a DIFFERENT interpreter than the one "
        "running this suite, so its file count describes another environment:\n"
        f"  this suite runs on : {sys.executable}\n"
        f"  the guard launched : {reported}\n"
        f"  its argv[0] was    : {MYPY_ARGV[0]!r}"
    )


def test_a_bare_name_and_sys_executable_really_can_diverge(tmp_path):
    """The measurement behind the fix, kept executable.

    Builds a throwaway venv and asks it the same question the guards ask. If a
    bare name and `sys.executable` could never come apart, this whole module
    would be ceremony. `--without-pip` keeps it to about a second, and the venv
    is built FROM the running interpreter so no second Python is needed.

    Note this proves a property of VENVS, not a property of MYPY_ARGV - it is
    the justification for the fix, not a test of it.
    """
    venv_root = tmp_path / "pin_probe"
    made = subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv_root)],
        capture_output=True,
        text=True,
    )
    if made.returncode != 0:
        pytest.skip(f"venv creation unavailable here: {made.stderr.strip()[:200]}")

    scripts = "Scripts" if sysconfig.get_platform().startswith("win") else "bin"
    exe_name = "python.exe" if scripts == "Scripts" else "python"
    venv_python = venv_root / scripts / exe_name
    if not venv_python.exists():
        pytest.skip(f"venv layout not as expected: no {venv_python}")

    script = (
        "import subprocess, sys\n"
        "print('SELF', sys.executable)\n"
        "pinned = subprocess.run([sys.executable, '-c',"
        " 'import sys; print(sys.executable)'], capture_output=True, text=True)\n"
        "print('PINNED', pinned.stdout.strip(), pinned.returncode)\n"
    )
    probe = subprocess.run(
        [str(venv_python), "-c", script], capture_output=True, text=True
    )
    if probe.returncode != 0:
        pytest.skip(f"venv interpreter would not run the probe: {probe.stderr[:200]}")

    lines = dict(
        (part[0], part[1] if len(part) > 1 else "")
        for part in (line.split(None, 1) for line in probe.stdout.splitlines())
    )
    inside = lines.get("SELF", "")
    pinned = lines.get("PINNED", "").rsplit(" ", 1)[0]

    assert Path(pinned) == Path(inside), (
        "even sys.executable did not round-trip inside the venv:\n"
        f"  venv interpreter : {inside}\n"
        f"  pinned came back : {pinned}\n"
        f"  raw probe output : {probe.stdout!r}"
    )
