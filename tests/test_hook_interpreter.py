"""The git hooks must pick an interpreter that can IMPORT their tools.

THE DEFECT THIS PINS, MEASURED 2026-09-06 ON THE OPERATOR'S WINDOWS BOX.

All three shims in `.githooks/` carried the identical interpreter-selection
snippet:

    PY="${PYTHON:-python3}"
    if ! command -v "$PY" >/dev/null 2>&1; then
        PY=python
    fi

`command -v` answers "does a file by that name exist on PATH". On Windows,
`python3` resolves to the Microsoft Store app-execution alias at
`AppData/Local/Microsoft/WindowsApps/python3`, which redirects to a DIFFERENT
interpreter (`AppData/Local/Python/pythoncore-3.14-64/python.exe`) carrying
neither ruff nor pytest. So `command -v python3` SUCCEEDS, the fallback to
`python` never fires, and the interpreter chosen is the one that cannot run any
of the tools the hooks exist to run. Meanwhile the plain `python` on the same
PATH resolves to `AppData/Local/Programs/Python/Python314/python.exe`, where
both `-m ruff` and `-m pytest` work.

Net effect: every push printed

    pre-push WARNING: ruff not importable - the lint half did NOT run.
    pre-push WARNING: pytest not importable - the suites did NOT run.
    pre-push: OK

The hook fails OPEN by design and it did say so, so nothing was silent - but
the gate had never once actually run on that machine. EXISTENCE IS NOT
CAPABILITY, and that is the whole content of the fix: probe candidates in
order and take the first that can IMPORT the module, not the first that
resolves to a filename.

WHY THE ARMS ARE SHAPED THE WAY THEY ARE.

A test that ran the selection logic against the REAL PATH and stopped there
would be worthless on the Linux CI runner, where `python3` IS the interpreter
with the dev deps and the broken probe therefore gives the right answer by
luck. So the load-bearing arms build a synthetic PATH: a `python3` that exists
and runs but can import nothing, and a `python` that can import everything.
That is the Store-shim shape, reproduced deterministically on any platform.
The old snippet is then run against that same PATH and asserted to pick the
useless interpreter, which is what makes the new arm non-vacuous - it proves
the harness would catch a regression to existence-only probing rather than
merely agreeing with whatever is installed.

The stubs model INTERPRETER SELECTION, not Python. The only two properties the
selection logic can observe about a candidate are "does the name resolve" and
"does `-c 'import X'` exit 0", and the stubs reproduce exactly those.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".githooks"
HELPER = REPO_ROOT / "scripts" / "hook_python.sh"

# Every shim that selects an interpreter. All three carried the same snippet,
# so all three are graded together - fixing only the one that showed symptoms
# is how the sibling repo left two live copies of a defect behind.
HOOKS = ("pre-commit", "pre-push", "commit-msg")

# The historical snippet, verbatim. It is the input to every non-vacuity arm:
# a guard that does not flag THIS text is not guarding anything.
OLD_SELECTION = (
    'PY="${PYTHON:-python3}"\n'
    "\n"
    'if ! command -v "$PY" >/dev/null 2>&1; then\n'
    "    PY=python\n"
    "fi\n"
)

# An interpreter that RESOLVES and RUNS but carries no third-party module -
# the Store shim's observable shape. `-c pass` succeeds, `-c "import pytest"`
# does not.
STUB_WITHOUT_MODULES = (
    "#!/bin/sh\n"
    "# Stub: a working interpreter with no third-party modules.\n"
    'case "$*" in *import*) exit 1;; esac\n'
    "exit 0\n"
)

# An interpreter that can import anything asked of it.
STUB_WITH_MODULES = (
    "#!/bin/sh\n"
    "# Stub: an interpreter carrying the dev dependencies.\n"
    "exit 0\n"
)


# ---------------------------------------------------------------------------
# Harness. PowerShell has neither `sh` nor `cygpath` on PATH, and the operator
# runs the suite from PowerShell, so both are located from git's own install
# rather than assumed to be reachable.
# ---------------------------------------------------------------------------


def _msys_tool(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    if os.name != "nt":
        return None
    proc = subprocess.run(
        ["git", "--exec-path"], capture_output=True, text=True, check=False
    )
    root = Path(proc.stdout.strip() or ".")
    for base in [root, *root.parents]:
        for rel in ("usr/bin", "bin"):
            candidate = base / rel / f"{name}.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def _sh() -> str:
    found = _msys_tool("sh")
    if found is None:
        pytest.skip("no POSIX sh on this machine - the .githooks/ shims cannot run here")
    return found


def _run_sh(
    script: str, *, path_prefix: Path | None = None, env: dict[str, str] | None = None,
    stdin: str = "",
) -> subprocess.CompletedProcess:
    """Run a snippet under the same `sh` git uses to run the hooks.

    PATH is PREPENDED rather than replaced, in the native form this process
    already holds. MSYS converts the whole variable to its own form at startup,
    and mixing a POSIX-form entry into a Windows-form PATH is how that
    conversion silently drops the entry.

    The directory holding `sh` is APPENDED. Launched from PowerShell rather
    than from Git Bash, `sh.exe` inherits a PATH with no `/usr/bin` on it and
    the hook dies on `cat: command not found` - a harness artefact that has
    nothing to do with what is being graded. Appending rather than prepending
    keeps the stub interpreters winning the name lookup.
    """
    environ = dict(os.environ)
    if env:
        environ.update(env)
    if path_prefix is not None:
        environ["PATH"] = str(path_prefix) + os.pathsep + environ["PATH"]
    environ["PATH"] = environ["PATH"] + os.pathsep + str(Path(_sh()).parent)
    return subprocess.run(
        [_sh(), "-c", script],
        cwd=str(REPO_ROOT),
        input=stdin,
        capture_output=True,
        text=True,
        env=environ,
    )


def _source_helper() -> str:
    # as_posix() keeps the drive letter but drops the backslashes; MSYS resolves
    # `C:/...` for a file operation, while `C:\...` it does not.
    return f'. "{HELPER.as_posix()}"\n'


def _pick(*modules: str, path_prefix: Path | None = None,
          env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    script = _source_helper() + "resin_pick_python " + " ".join(modules)
    return _run_sh(script, path_prefix=path_prefix, env=env)


@pytest.fixture
def shimmed_path(tmp_path: Path) -> Path:
    """The measured Windows shape: `python3` and `py` are dead ends, `python` works."""
    return _make_stubs(tmp_path / "shimmed", python3=False, python=True, py=False)


@pytest.fixture
def barren_path(tmp_path: Path) -> Path:
    """No candidate carries the dev deps. The fail-open contract must hold."""
    return _make_stubs(tmp_path / "barren", python3=False, python=False, py=False)


def _make_stubs(directory: Path, *, python3: bool, python: bool, py: bool) -> Path:
    directory.mkdir(parents=True)
    for name, capable in (("python3", python3), ("python", python), ("py", py)):
        body = STUB_WITH_MODULES if capable else STUB_WITHOUT_MODULES
        # newline="\n" is not cosmetic: a CRLF shebang makes the kernel look for
        # an interpreter named "/bin/sh\r" and the stub becomes unrunnable, which
        # would make every arm below pass for the wrong reason.
        (directory / name).write_text(body, encoding="ascii", newline="\n")
        (directory / name).chmod(0o755)
    return directory


# ---------------------------------------------------------------------------
# The shared helper exists, is tracked, and is what all three hooks use
# ---------------------------------------------------------------------------


def test_the_shared_helper_exists():
    assert HELPER.is_file(), f"missing {HELPER}"


def test_the_shared_helper_is_tracked_so_a_fresh_clone_gets_it():
    """The hooks SOURCE it. An untracked helper is three broken hooks, not one."""
    listed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "scripts/hook_python.sh"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0, "scripts/hook_python.sh is not tracked by git"


@pytest.mark.parametrize("hook", HOOKS)
def test_every_hook_sources_the_shared_helper(hook: str):
    body = (HOOKS_DIR / hook).read_text(encoding="utf-8")
    assert "scripts/hook_python.sh" in body, (
        f".githooks/{hook} does not source the shared selector; a private copy "
        "is how three sites drift apart"
    )


@pytest.mark.parametrize("hook", HOOKS)
def test_no_hook_selects_an_interpreter_by_existence_alone(hook: str):
    body = (HOOKS_DIR / hook).read_text(encoding="utf-8")
    assert not _existence_only_hits(body), (
        f".githooks/{hook} still picks an interpreter with `command -v`, which "
        "answers existence and not capability"
    )


def _existence_only_hits(text: str) -> list[str]:
    """Lines that decide an interpreter from a name lookup alone."""
    hits = []
    for line in text.splitlines():
        if re.search(r'command -v\s+"?\$PY"?', line):
            hits.append(line.strip())
        if re.search(r'PY="\$\{PYTHON:-python3\}"', line):
            hits.append(line.strip())
    return hits


def test_the_existence_only_guard_is_not_vacuous():
    """Fed the historical snippet, the guard above must flag it."""
    hits = _existence_only_hits(OLD_SELECTION)
    assert len(hits) == 2, f"the guard would not have caught the old snippet: {hits}"


# ---------------------------------------------------------------------------
# The selection logic itself, run under `sh`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", ["pytest", "ruff"])
def test_the_pick_lands_on_an_interpreter_that_can_import_the_module(module: str):
    """The real machine, the real PATH. This is the arm the operator cares about.

    Skipped rather than failed when nothing on the box carries the module: a
    clone without dev deps is a legitimate state and the hooks fail open for it.
    """
    picked = _pick(module)
    if picked.returncode != 0:
        pytest.skip(f"no interpreter on this PATH can import {module}")
    chosen = picked.stdout.strip()
    assert chosen, "the selector returned success with no interpreter"
    proof = _run_sh(f'"{chosen}" -c "import {module}"')
    assert proof.returncode == 0, (
        f"the selector chose {chosen!r}, which cannot import {module}: "
        f"{proof.stderr.strip()[:300]}"
    )


def test_a_shim_that_exists_but_imports_nothing_is_passed_over(shimmed_path: Path):
    """The measured defect, reproduced deterministically on any platform."""
    picked = _pick("pytest", path_prefix=shimmed_path)
    assert picked.returncode == 0, picked.stderr
    assert picked.stdout.strip() == "python", (
        "the selector stopped at the first name that resolved instead of the "
        f"first that worked: chose {picked.stdout.strip()!r}"
    )


def test_the_old_probe_would_have_chosen_the_useless_shim(shimmed_path: Path):
    """NON-VACUITY. Without this the arm above could pass on a healthy PATH.

    The historical snippet is run against the SAME synthetic PATH. It must pick
    `python3` - and that pick must be unable to import pytest. Together those
    two facts prove the harness distinguishes a fixed selector from the broken
    one, so a regression to existence-only probing fails the arm above rather
    than sliding through.
    """
    old = _run_sh(
        OLD_SELECTION + "printf '%s' \"$PY\"", path_prefix=shimmed_path
    )
    assert old.returncode == 0, old.stderr
    assert old.stdout.strip() == "python3"

    proof = _run_sh('python3 -c "import pytest"', path_prefix=shimmed_path)
    assert proof.returncode != 0, (
        "the stub PATH does not actually reproduce the defect, so the arm above "
        "proves nothing"
    )


def test_ruff_and_pytest_are_resolved_separately(tmp_path: Path):
    """They are two different capabilities and may live on two interpreters.

    `python3` here carries neither, `python` carries both; the point of the arm
    is that each query is answered on its own rather than one answer being
    reused for the other half of the hook.
    """
    stubs = _make_stubs(tmp_path / "split", python3=False, python=True, py=False)
    for module in ("ruff", "pytest"):
        picked = _pick(module, path_prefix=stubs)
        assert picked.returncode == 0, picked.stderr
        assert picked.stdout.strip() == "python", module


def test_an_explicit_PYTHON_is_probed_first(shimmed_path: Path):
    """The override still leads, it just no longer wins on existence alone.

    Graded on EQUALITY with the override path rather than on a suffix. `python`
    is also a plain candidate and it also ends in "python", so a suffix match
    here would pass whether the override was honoured or ignored.
    """
    override = (shimmed_path / "python").as_posix()
    picked = _pick("pytest", path_prefix=shimmed_path, env={"PYTHON": override})
    assert picked.returncode == 0, picked.stderr
    assert picked.stdout.strip() == override
    assert picked.stderr.strip() == "", "an honoured override needs no warning"


def test_an_explicit_PYTHON_that_cannot_import_is_not_silently_obeyed(
    shimmed_path: Path,
):
    """Falling through is right; doing it in silence is not.

    The A side of this pair is the arm above: the SAME shape of override, an
    absolute path in the same directory, differing only in whether the stub it
    names can import. One is honoured and one is passed over, so importability
    is demonstrably the discriminator rather than resolvability.
    """
    override = (shimmed_path / "python3").as_posix()
    picked = _pick("pytest", path_prefix=shimmed_path, env={"PYTHON": override})
    assert picked.returncode == 0, picked.stderr
    assert picked.stdout.strip() == "python"
    assert override in picked.stderr, (
        "the selector overrode an explicit PYTHON without a word about it"
    )


def test_the_selector_reports_failure_when_no_candidate_qualifies(barren_path: Path):
    """The trigger for the fail-open branch. Empty stdout, non-zero status."""
    picked = _pick("pytest", path_prefix=barren_path)
    assert picked.returncode != 0
    assert picked.stdout.strip() == ""


def test_a_bare_pick_still_finds_a_working_interpreter(barren_path: Path):
    """With no module named, any interpreter that RUNS qualifies.

    pre-commit and commit-msg need this: the scripts they drive are stdlib-only,
    so a box without dev deps must still get its glyph gate. That gate is
    fail-CLOSED and must not be turned into a fail-open one by this change.
    """
    picked = _pick(path_prefix=barren_path)
    assert picked.returncode == 0, picked.stderr
    assert picked.stdout.strip() == "python3"


def test_the_candidate_list_is_the_documented_one():
    listing = _run_sh(_source_helper() + "resin_python_candidates")
    assert listing.returncode == 0, listing.stderr
    assert listing.stdout.split() == ["python3", "python", "py"]


def test_the_candidate_list_names_an_explicit_PYTHON_first():
    listing = _run_sh(
        _source_helper() + "resin_python_candidates", env={"PYTHON": "/opt/pyX"}
    )
    assert listing.stdout.split() == ["/opt/pyX", "python3", "python", "py"]


# ---------------------------------------------------------------------------
# pre-push, end to end. The stubs stand in for ruff and pytest so the arms
# cost milliseconds and do not recursively run the suites they are part of.
# ---------------------------------------------------------------------------


def _run_prepush(path_prefix: Path, env: dict[str, str] | None = None):
    hook = (HOOKS_DIR / "pre-push").as_posix()
    return _run_sh(f'"{hook}"', path_prefix=path_prefix, env=env)


def test_pre_push_runs_both_halves_when_an_interpreter_carries_the_tools(
    shimmed_path: Path,
):
    """The whole point. On the measured PATH shape this printed two WARNINGs."""
    result = _run_prepush(shimmed_path)
    assert result.returncode == 0, result.stderr
    assert "did NOT run" not in result.stderr, (
        "pre-push skipped a half although a capable interpreter was on PATH:\n"
        + result.stderr
    )
    assert "pre-push: OK" in result.stdout


def test_pre_push_still_fails_open_when_nothing_carries_the_tools(barren_path: Path):
    """The inherited contract, unchanged: let the push through, but say so."""
    result = _run_prepush(barren_path)
    assert result.returncode == 0, result.stderr
    assert "ruff not importable" in result.stderr
    assert "pytest not importable" in result.stderr
    assert "did NOT run" in result.stderr
    assert "pre-push: OK" in result.stdout


def test_pre_push_names_what_it_tried_when_it_fails_open(barren_path: Path):
    """Fail OPEN, never fail SILENT - a warning that does not say what was tried
    leaves the reader with no next step, which is how this defect survived."""
    result = _run_prepush(barren_path)
    assert "python3" in result.stderr and "python" in result.stderr
    assert "requirements-dev.txt" in result.stderr


def test_the_escape_hatch_still_skips_the_whole_gate(shimmed_path: Path):
    result = _run_prepush(shimmed_path, env={"RESIN_SKIP_PREPUSH": "1"})
    assert result.returncode == 0, result.stderr
    assert "SKIPPED" in result.stdout
    assert "pre-push: OK" not in result.stdout


# ---------------------------------------------------------------------------
# tools/precommit_gate.py - audited for the same root cause and found CLEAN.
# Pinned so it stays that way.
# ---------------------------------------------------------------------------


def test_the_gate_probes_ruff_by_running_it_not_by_finding_it():
    """`_resolve_ruff` already demanded a working `--version`, so the gate never
    carried the existence-only defect. It is graded here because its FIRST
    candidate is `sys.executable`, which under a hook launched by the Store shim
    is precisely the ruff-less interpreter - the probe is the only thing that
    saved it, and it must not be relaxed into a `shutil.which`.
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        import precommit_gate
    finally:
        sys.path.pop(0)

    source = (REPO_ROOT / "tools" / "precommit_gate.py").read_text(encoding="utf-8")
    assert "--version" in source
    assert "shutil.which" not in source

    candidates = precommit_gate._ruff_candidates()
    assert candidates[0] == [sys.executable, "-m", "ruff"]
    assert ["python", "-m", "ruff"] in candidates


def test_the_gate_rejects_an_interpreter_that_cannot_import_ruff(monkeypatch):
    """Non-vacuity for the arm above: the probe must actually reject a bad one."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        import precommit_gate
    finally:
        sys.path.pop(0)

    monkeypatch.setattr(
        precommit_gate, "_ruff_candidates", lambda: [[sys.executable, "-m", "no_such_module_xyz"]]
    )
    assert precommit_gate._resolve_ruff() is None
