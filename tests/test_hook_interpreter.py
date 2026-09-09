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

THE SECOND DEFECT, IN THIS FILE'S OWN HARNESS, MEASURED 2026-09-08.

A CONDITION THAT CANNOT DISTINGUISH "CHECKED AND FOUND NOTHING" FROM "COULD NOT
CHECK" is the same root cause tests/test_task_liveness.py has now been refuted
for several times, and it lived here twice.

SITE 1, the search for a POSIX `sh`. It ran `git --exec-path` with
`check=False` and then did

    root = Path(proc.stdout.strip() or ".")

so a git that was absent, exited non-zero, or printed nothing collapsed into a
scan of the current directory, which finds no `sh.exe`, and `_sh()` took

    pytest.skip("no POSIX sh on this machine - the .githooks/ shims cannot run here")

Measured: making that query exit 3 turned the file into 11 passed, 15 skipped
at exit 0, with all fifteen skips asserting something about the machine that
was FALSE in that run - the machine had `sh` at
`C:\\Program Files\\Git\\usr\\bin\\sh.EXE` the whole time. A broken git read as
an absent shell.

SITE 2, the interpreter pick. It ran `resin_pick_python` and read the EXIT CODE
alone:

    if picked.returncode != 0:
        pytest.skip(f"no interpreter on this PATH can import {module}")

`resin_pick_python` returns 1 when it probed every candidate and none carried
the module. `sh` ALSO exits 1 when it cannot source the helper at all, and 127
when the helper defines no such function. A SHARED EXIT CODE IS NOT A
FINGERPRINT. Measured: pointing HELPER at a helper whose `resin_pick_python`
returns 1 unconditionally produced those same two skips, blaming a machine that
carries both pytest and ruff.

So both discovery helpers now return a STATUS. FAILED means the tool did not
run and MUST fail the calling arm, naming the tool failure. Only NONE - probed,
and nothing qualified - may skip, which is the legitimate case: a clone without
dev deps, or a box with no POSIX shell. The classification is split into pure
functions, `_classify_exec_path` and `_classify_pick`, so every FAILED branch is
gradeable on any platform with neither git nor `sh` present, and
`test_non_vacuity_neither_discovery_helper_can_report_a_tool_failure_as_an_absent_capability`
drives them through every failure shape AND through positive controls, then
grades the two CALLERS - a gate tested as a pure predicate is not an enforced
gate.

The pick's fingerprint is a MARKER on stdout, not an exit code. Measured on the
operator's box, 2026-09-08: `sh -c '. "/no/such/file"; printf MARKER'` exits 1
having printed NOTHING, because `.` is a special builtin whose failure aborts a
non-interactive shell. So marker-absent and marker-present are two different
facts where exit-1 and exit-1 were one.

AND THE MARKER ALONE WAS REFUTED THE SAME DAY. A SHARED FINGERPRINT IS NOT A
FINGERPRINT, and a bare marker turned out to be shared in exactly the way the
exit code had been:

  - The marker was printed on the `else` branch of the selector's exit status,
    so for the failure mode that matters it WAS the exit status. A helper whose
    `resin_pick_python` did `return 1` unconditionally - probing nothing at all
    - produced the same skip as an exhausted search, blaming a machine that
    carries both pytest and ruff.
  - The marker is printed by a wrapper this harness writes, and the helper is
    sourced FIRST, so any fixed string the wrapper can print the helper can
    print earlier. A helper that was one source-time echo and an `exit 0`
    classified NONE and skipped, and the NOFUNC branch written for exactly
    "helper defines no resin_pick_python" was never reached, because the marker
    arrived before the function would have been called. A SHAPE ARM PINS
    FORMAT, NOT VALUE - the presence of a token was pinned, the occurrence of a
    search was not.

So the marker now carries a PER-RUN NONCE and a PROBE COUNT, both on the one
line. The nonce cannot be in a file authored earlier. The count is written by
shell-function shadows over the candidate names, which log the invocation and
delegate through `command` - POSIX defines `command` as suppressing the shell
function lookup - so it records work the selector actually did rather than a
token it printed. A NONE carrying a count of ZERO is FAILED: A SKIP MUST BE
EARNED BY EVIDENCE THAT A SEARCH HAPPENED. The detail text names the number, so
"the selector probed N candidates" is arithmetic the classifier holds rather
than a claim it merely makes.

THREE SKIP DOORS, NOT ONE, AND THIS FILE OWNS TWO OF THEM.

The two above are `_sh()` and the real-PATH pick arm. THE THIRD IS
`require_git_repository()`, called by the tracked-helper arm and by
`_run_prepush` for every `needs_git=True` caller. Measured 2026-09-08 in this
tree: injecting `git rev-parse --git-dir` exit 7 - a TOOL FAILURE, not an
absent repository - gave 29 passed, 4 SKIPPED, exit 0 against the arms as
they now stand. Four evaporate green on a broken git: the tracked-helper arm
and the three pre-push arms.
The root cause is the final `return` of `git_unusable_reason` at
`tests/conftest.py:109`, which routes every non-128 non-zero exit to a skip
reason; the skip itself is raised at `tests/conftest.py:128`.

That file is not this slice's to change, and the door is a DECLARED
could-not-check rather than a disguised one - its reason reads "git is present
but did not answer ... exited 7" and asserts nothing about the machine's
capabilities. It is recorded here so the next reader is not told there is one
door when there are three.

THE FOURTH DISPOSITION THAT WAS BEING MERGED INTO THE SECOND, 2026-09-08.

`_msys_tool_pick` caught `(OSError, subprocess.SubprocessError)` around the
`git --exec-path` query and called every one of them FAILED. But a
FileNotFoundError there does not mean git failed - it means GIT IS NOT
INSTALLED, which is disposition 3, the same "probed, nothing to consult" state
the non-Windows branch already returned NONE for. The file contradicted itself
on it: identical epistemic state, two dispositions, differing only by platform.
`tests/conftest.py:90` splits exactly this case out, routing OSError to "git is
not runnable on this machine" and a SKIP.

Measured on Windows with git absent and no `sh` on PATH - the real population
being Windows / Download-ZIP / Python installed / no Git for Windows - the file
gave 17 FAILED, exit 1, every one reading "the search for a POSIX sh did not
run ... `git --exec-path` could not be launched: FileNotFoundError". The
pre-slice baseline was red there too, at 12 FAILED, so this was an
AMPLIFICATION of an existing false red rather than a skip-to-fail conversion.
Split now, and CORROBORATED rather than inferred from the exception class: a
FileNotFoundError raised while `git` still resolves on PATH is a tool failure
and stays FAILED.

THE DISCOVERY HAD NO POSITIVE CONTROL, 2026-09-08.

Everything above proves a FABRICATED skip cannot happen. Nothing proved the
LEGITIMATE search still fires. Measured in the operator's real shape - git on
PATH, `sh` not - DELETING the whole git-install search gave 13 passed, 20
SKIPPED, exit 0: THE MUTANT SURVIVED, because in the mutant's world every one
of those twenty skip reasons was true. A guard against a false skip, over a
capability nobody graded. The mutant-killer is
`test_the_git_install_discovery_still_fires_where_an_sh_demonstrably_sits`,
and its oracle differs from the matcher in ROUTE (resolve `git` on PATH and
walk up, rather than asking git for its exec-path) and in BREADTH (a
depth-bounded case-insensitive walk, rather than two hardcoded relative names),
so it can catch a matcher that went NARROW and not only one that was deleted.
The oracle is itself graded against planted trees by
`test_the_oracle_that_grades_the_discovery_is_itself_wider_than_the_discovery`,
because an oracle stuck at NONE would make its arm skip forever.

THE PORTABILITY CEILING, STATED RATHER THAN PAPERED OVER.

THE MUTANT-KILLER IS WINDOWS-ONLY, and skips elsewhere. Production reaches the
searching branch only on Windows, and an ancestor walk over a POSIX `/usr` or
`/` is unbounded, so an oracle there would have to give up early and answer
NONE for "I could not look" - the conflation this file exists to refuse. The
oracle's own mechanism arm plants directories and does grade everywhere.

SITE 1 IS CLOSED ON THE `os.name == "nt"` BRANCH ONLY. `_msys_tool_pick`
returns NONE, having performed NO SEARCH AT ALL, when `sh` is absent from PATH
and the box is not Windows - no filesystem probe, no `git --exec-path` - while
its detail asserts "there is no git install to search", a fact about a git
install it never consulted. Measured 2026-09-08 by forcing that branch
against the arms as they now stand: 13 passed, 20 SKIPPED, exit 0. Every arm
that needs a shell goes through that one door, the four end-to-end forgery
arms added below included.

And production cannot reach the closed half there. `_sh()` calls
`_msys_tool_pick("sh")` with `search_git_install=None`, which resolves to False
on any non-Windows host, so the two end-to-end site-1 FAILED arms below reach
the searching branch only because they pass `search_git_install=True`
themselves: on a Linux runner they grade a path production never takes. The
PURE classifier arms are unaffected and do grade everywhere. Faking a Linux
host to manufacture coverage would make the arm a statement about no machine at
all, so the ceiling is stated instead of closed.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

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


class _ExecPathPick(typing.NamedTuple):
    """Did `git --exec-path` ANSWER. Says nothing about whether a tool was found."""

    status: str  # "OK" or "FAILED"
    root: Path | None
    detail: str


class _ToolPick(typing.NamedTuple):
    """FOUND / NONE / FAILED. NONE is the only one a caller may skip on."""

    status: str
    path: str | None
    detail: str


def _query_exec_path() -> subprocess.CompletedProcess:
    """The impure seam, so the arms below can make it fail without a broken git."""
    return subprocess.run(
        ["git", "--exec-path"], capture_output=True, text=True, check=False, timeout=60
    )


def _classify_exec_path(returncode: int, stdout: str) -> _ExecPathPick:
    """Pure half of the git query, so its FAILED arms are gradeable anywhere.

    The old code's `or "."` is the whole defect: every one of these branches
    collapsed into a scan of the working directory, which finds nothing, which
    the caller then reported as a machine with no shell.
    """
    if returncode != 0:
        return _ExecPathPick("FAILED", None, f"`git --exec-path` exited {returncode}")
    text = stdout.strip()
    if not text:
        return _ExecPathPick(
            "FAILED", None, "`git --exec-path` exited 0 but printed nothing"
        )
    root = Path(text)
    # git prints an absolute path. Anything else is not an answer to the
    # question asked, and must not be scanned as though it were - a RELATIVE
    # path that happens to name a real directory would otherwise be scanned
    # silently and report NONE.
    if not root.is_absolute():
        return _ExecPathPick(
            "FAILED", None, f"`git --exec-path` printed {text!r}, which is not an absolute path"
        )
    if not root.is_dir():
        return _ExecPathPick(
            "FAILED", None, f"`git --exec-path` printed {text!r}, which is not a directory"
        )
    return _ExecPathPick("OK", root, f"`git --exec-path` answered {text!r}")


# Suffixes `shutil.which` will resolve off PATHEXT but CreateProcess will not
# launch directly, so the two probes below can disagree with nothing wrong.
# `.exe` and `.com` are deliberately absent: those two ARE launchable, so a
# FileNotFoundError against one of them stays the contradiction it always was.
_CREATEPROCESS_CANNOT_LAUNCH = frozenset({".bat", ".cmd"})


def _msys_tool_pick(name: str, *, search_git_install: bool | None = None) -> _ToolPick:
    """Locate an MSYS tool, reporting WHY when it cannot be located.

    `search_git_install` exists so the Windows-only branch is reachable from a
    Linux runner. Passing it does not fake the branch's answer - it only lets
    the arm ask the question the operator's box asks.
    """
    direct = shutil.which(name)
    if direct:
        return _ToolPick("FOUND", direct, f"{name} is on PATH at {direct}")
    if search_git_install is None:
        search_git_install = os.name == "nt"
    if not search_git_install:
        return _ToolPick(
            "NONE",
            None,
            f"no {name} on PATH, and this is not Windows, so there is no git "
            "install to search",
        )
    try:
        proc = _query_exec_path()
    except FileNotFoundError:
        # DISPOSITION 3, NOT DISPOSITION 2, and the distinction is the whole
        # point of this file. git is not FAILING here - git is NOT INSTALLED.
        # That is the identical epistemic state the `not search_git_install`
        # branch above already returns NONE for: no `name` on PATH, and no git
        # install to consult. Reporting it FAILED made this file red on
        # Windows / Download-ZIP / Python-installed / no-Git-for-Windows, which
        # is a real population - `tests/conftest.py:90` splits exactly that
        # case out of its own tool-failure branch for exactly that reason.
        #
        # CORROBORATED, not inferred from the exception class alone: a
        # FileNotFoundError raised while `git` still resolves on PATH is not an
        # absent git, and stays FAILED below.
        resolved = shutil.which("git")
        if resolved is None:
            return _ToolPick(
                "NONE",
                None,
                f"no {name} on PATH; `git --exec-path` raised FileNotFoundError and "
                "git does not resolve on PATH either, so git is not installed and "
                "there is no git install to search",
            )
        # THE CORROBORATION'S TWO SIGNALS ASK DIFFERENT QUESTIONS OF PATH, and
        # on exactly one Windows shape they disagree without anything being
        # broken. `shutil.which` is PATHEXT-aware and resolves `git.bat`;
        # `subprocess.run(["git", ...])` goes through CreateProcess, which
        # appends only `.exe`. Measured 2026-09-08 with a `git.bat` as the only
        # git on PATH: the whole file went 17 failed / 13 passed / exit 1, every
        # red reading "raised FileNotFoundError even though git resolves on
        # PATH". A shim like that is an ordinary install shape, and the
        # disagreement is about PATHEXT rather than about git working, so it is
        # NOT the contradictory state the branch below exists to catch. Nothing
        # is broken and no install can be consulted through this route - the
        # same epistemic state as the absent-git branch above, and NONE for the
        # same reason. The door is opened only for a positively named
        # shell-script suffix, never for a resolution this route could launch.
        if os.name == "nt" and Path(resolved).suffix.lower() in _CREATEPROCESS_CANNOT_LAUNCH:
            return _ToolPick(
                "NONE",
                None,
                f"no {name} on PATH; the git on PATH is {resolved!r}, a shell-script "
                "shim that CreateProcess cannot launch directly, so `git --exec-path` "
                "raised FileNotFoundError because of PATHEXT and not because git is "
                "broken, and no git install could be consulted through it",
            )
        return _ToolPick(
            "FAILED",
            None,
            "`git --exec-path` raised FileNotFoundError even though git resolves "
            f"on PATH at {resolved!r}, so this is a tool failure and not an "
            "absent git",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _ToolPick(
            "FAILED", None, f"`git --exec-path` could not be launched: {type(exc).__name__}"
        )
    answered = _classify_exec_path(proc.returncode, proc.stdout)
    if answered.status == "FAILED" or answered.root is None:
        return _ToolPick("FAILED", None, answered.detail)
    for base in [answered.root, *answered.root.parents]:
        for rel in ("usr/bin", "bin"):
            candidate = base / rel / f"{name}.exe"
            if candidate.is_file():
                return _ToolPick(
                    "FOUND", str(candidate), f"{answered.detail}, and {name}.exe sits under it"
                )
    return _ToolPick(
        "NONE",
        None,
        f"{answered.detail}, and no {name}.exe sits under it or any of its parents",
    )


def _sh() -> str:
    """The gate. FAILED fails; only NONE skips, and it says what it searched."""
    pick = _msys_tool_pick("sh")
    if pick.status == "FAILED":
        pytest.fail(
            "the search for a POSIX sh did not run, so a skip here would blame the "
            f"machine for a tool failure: {pick.detail}"
        )
    if pick.status == "NONE" or pick.path is None:
        pytest.skip(
            "no POSIX sh on this machine - the .githooks/ shims cannot run here "
            f"({pick.detail})"
        )
    return pick.path


def _run_sh(
    script: str, *, path_prefix: Path | None = None, env: dict[str, str] | None = None,
    stdin: str = "", argv: tuple[str, ...] = (),
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
        [_sh(), "-c", script, *argv],
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


# The pick's fingerprint. An exit code cannot serve: `resin_pick_python`
# returns 1 for "probed everything, nothing qualified", and `sh` returns 1 when
# it could not source the helper at all. Measured 2026-09-08, a missing source
# aborts the shell BEFORE any marker is printed, so marker-absent and
# marker-present separate the two facts that exit-1 conflated.
PICK_MARKER = "RESIN_PICK"


class _PickResult(typing.NamedTuple):
    """FOUND / NONE / FAILED, plus the raw process for the stderr assertions."""

    status: str
    chosen: str | None
    proc: subprocess.CompletedProcess | None
    detail: str


# The candidate names the shared helper iterates over. The wrapper shadows each
# with a shell function that LOGS the invocation and then delegates through
# `command`, which POSIX defines as suppressing the shell function lookup. That
# is how the harness counts probes the selector actually made, without editing
# the helper and without changing which interpreter wins - the helper prints the
# candidate NAME, and the shadow carries the same name.
TRACED_CANDIDATES = ("python3", "python", "py")


def _pick_script(modules: tuple[str, ...], nonce: str, probe_log: Path) -> str:
    """Wrap the helper's selector in a PROBE COUNTER and a PER-RUN NONCE.

    THE NONCE, and why a bare marker was not a fingerprint. The marker is
    printed by this wrapper, and the helper is sourced BEFORE the wrapper runs,
    so any fixed string this wrapper can print, a helper can print first.
    Measured 2026-09-08: a helper that was only a source-time echo of
    "RESIN_PICK NONE" followed by `exit 0` - defining no selector at all - was
    classified NONE and skipped the calling arm with a detail claiming a search
    had happened. The nonce is generated per run, so a file authored earlier
    cannot carry it.

    THE COUNT, and why a status verb was not enough. `resin_pick_python`
    returns 1 both when it probed every candidate and found nothing and when it
    did no work at all. Measured 2026-09-08: a helper whose selector was
    `return 1` unconditionally produced the same NONE, and the same skip, as a
    real exhausted search. A SHARED FINGERPRINT IS NOT A FINGERPRINT, and
    replacing a shared exit code with a token shared in the same way changed
    nothing. The count is the evidence the detail text was already claiming and
    did not hold.

    `command -v` on a FUNCTION name is the one thing it answers exactly: the
    function is either defined in this shell or it is not. Nothing about an
    interpreter is decided there.

    ONE MEASURED SIDE EFFECT OF THE SHADOWS. With a shadow defined, the
    helper's own `command -v "$_rp_py"` existence check passes for a candidate
    that has no executable on PATH at all, so that candidate is attempted and
    counted where production would have passed over it unprobed. It still
    cannot be CHOSEN - `command python3 ...` exits 127 and the helper moves on -
    so the pick is unchanged and the count is, if anything, generous. A
    generous count can only make a skip easier to earn, never a FOUND easier to
    fake, and every FOUND arm proves its answer by importing the module.

    The emitted shell carries NO backslash escapes anywhere: `echo` supplies the
    newline instead of `printf`. A backslash here has to survive this file, a
    heredoc, MSYS argv conversion and `sh` word splitting, and it does not
    reliably survive all four.
    """
    trace = "".join(
        name + '() { echo ' + name + ' >> "$RESIN_PROBE_LOG"; command '
        + name + ' "$@"; }\n'
        for name in TRACED_CANDIDATES
    )
    return (
        'RESIN_PROBE_LOG="' + probe_log.as_posix() + '"\n'
        + ': > "$RESIN_PROBE_LOG"\n'
        + trace
        + _source_helper()
        + "if ! command -v resin_pick_python >/dev/null 2>&1; then\n"
        + f'    echo "{PICK_MARKER} {nonce} NOFUNC"\n'
        + "    exit 0\n"
        + "fi\n"
        + 'if _rp_chosen="$(resin_pick_python ' + " ".join(modules) + ')"; then\n'
        + "    _rp_verb=FOUND\n"
        + "else\n"
        + "    _rp_verb=NONE\n"
        + "    _rp_chosen=\n"
        + "fi\n"
        # Counted in the shell and printed on the SAME line as the nonce. A
        # count delivered on a second channel is a channel a forged marker can
        # simply decline to write.
        + "_rp_probes=0\n"
        + "while IFS= read -r _rp_line; do _rp_probes=$((_rp_probes + 1)); done"
        + ' < "$RESIN_PROBE_LOG"\n'
        + f'echo "{PICK_MARKER} {nonce}'
        + ' $_rp_verb $_rp_probes $_rp_chosen"\n'
    )


def _classify_pick(returncode: int, stdout: str, stderr: str, nonce: str) -> _PickResult:
    """Pure half of _pick, so its FAILED arms are gradeable without a shell.

    Three facts decide the verdict, and the first two were added 2026-09-08
    after this classifier was refuted for treating a token's PRESENCE as
    evidence that a search had occurred.

    1. THE NONCE MUST MATCH. A marker without this run's nonce is a string some
       earlier-authored file printed, not an answer from the wrapper.
    2. A NONE MUST CARRY A NON-ZERO PROBE COUNT. "Probed zero candidates" is
       FAILED, never NONE - the only status a caller is allowed to skip on.
    3. The verb still has to be one of the three the wrapper can emit.

    The detail text is held to the same standard as the status: it names the
    NUMBER of candidates probed, because "the selector probed every candidate"
    is a claim, and the classifier now holds the arithmetic behind it.
    """
    prefix = f"{PICK_MARKER} {nonce} "
    marked = [line for line in stdout.splitlines() if line.startswith(prefix)]
    if not marked:
        forged = [
            line for line in stdout.splitlines()
            if line.startswith(PICK_MARKER + " ") and not line.startswith(prefix)
        ]
        why = (
            f"it printed {len(forged)} {PICK_MARKER} line(s) carrying no nonce or "
            f"another run's, which is what a source-time echo can forge: {forged}"
            if forged
            else "it never reached the wrapper that answers the question"
        )
        return _PickResult(
            "FAILED", None, None,
            f"the selection script exited {returncode} without printing a "
            f"{PICK_MARKER} marker for this run - {why}: {stderr.strip()[:200]!r}",
        )
    if len(marked) > 1:
        return _PickResult(
            "FAILED", None, None,
            f"the selection script printed {len(marked)} markers, so which one "
            f"answers the question is undecidable: {marked}",
        )
    verb, _, rest = marked[0][len(prefix):].partition(" ")
    if verb == "NOFUNC":
        return _PickResult(
            "FAILED", None, None,
            "the shared helper was sourced but defines no resin_pick_python, so "
            "nothing probed any interpreter",
        )
    if verb not in ("NONE", "FOUND"):
        return _PickResult(
            "FAILED", None, None,
            f"the selection script printed an unknown marker: {marked[0]!r}",
        )
    count_text, _, chosen = rest.partition(" ")
    if not re.fullmatch(r"[0-9]+", count_text):
        return _PickResult(
            "FAILED", None, None,
            f"the {verb} marker carried {count_text!r} where a probe count "
            "belongs, so how many candidates were tried is undecidable",
        )
    probed = int(count_text)
    if verb == "NONE":
        if probed == 0:
            return _PickResult(
                "FAILED", None, None,
                "the selector reported that nothing qualified having probed 0 "
                "candidates, so no search ran and a skip here would fabricate one",
            )
        return _PickResult(
            "NONE", None, None,
            f"the selector probed {probed} candidate(s) and none of them qualified",
        )
    chosen = chosen.strip()
    if not chosen:
        return _PickResult(
            "FAILED", None, None,
            "the selector reported success and named no interpreter, which "
            "contradicts itself",
        )
    return _PickResult(
        "FOUND", chosen, None,
        f"the selector chose {chosen!r} after probing {probed} candidate(s)",
    )


def _pick(*modules: str, path_prefix: Path | None = None,
          env: dict[str, str] | None = None) -> _PickResult:
    """Run the selector once, under a fresh nonce and a fresh probe log.

    The nonce is per CALL, not per session: a stale marker left on stdout by an
    earlier run of anything would otherwise authenticate a later one.
    """
    nonce = secrets.token_hex(8)
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run_sh(
            _pick_script(modules, nonce, Path(tmp) / "probes.log"),
            path_prefix=path_prefix,
            env=env,
        )
    return _classify_pick(
        proc.returncode, proc.stdout, proc.stderr, nonce
    )._replace(proc=proc)


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
    require_git_repository()

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
    Skipped ONLY for that, though - a selector that could not run at all is a
    tool failure and fails here rather than blaming the machine's dev deps.
    """
    picked = _pick(module)
    assert picked.status != "FAILED", (
        "the selector this arm grades did not run, so a skip here would blame "
        f"the machine for a tool failure: {picked.detail}"
    )
    if picked.status == "NONE":
        pytest.skip(f"no interpreter on this PATH can import {module} - {picked.detail}")
    chosen = picked.chosen
    assert chosen, "the selector returned success with no interpreter"
    proof = _run_sh(f'"{chosen}" -c "import {module}"')
    assert proof.returncode == 0, (
        f"the selector chose {chosen!r}, which cannot import {module}: "
        f"{proof.stderr.strip()[:300]}"
    )


def test_a_shim_that_exists_but_imports_nothing_is_passed_over(shimmed_path: Path):
    """The measured defect, reproduced deterministically on any platform."""
    picked = _pick("pytest", path_prefix=shimmed_path)
    assert picked.status == "FOUND", picked.detail
    assert picked.chosen == "python", (
        "the selector stopped at the first name that resolved instead of the "
        f"first that worked: chose {picked.chosen!r}"
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
        assert picked.status == "FOUND", f"{module}: {picked.detail}"
        assert picked.chosen == "python", module


def test_an_explicit_PYTHON_is_probed_first(shimmed_path: Path):
    """The override still leads, it just no longer wins on existence alone.

    Graded on EQUALITY with the override path rather than on a suffix. `python`
    is also a plain candidate and it also ends in "python", so a suffix match
    here would pass whether the override was honoured or ignored.
    """
    override = (shimmed_path / "python").as_posix()
    picked = _pick("pytest", path_prefix=shimmed_path, env={"PYTHON": override})
    assert picked.status == "FOUND", picked.detail
    assert picked.chosen == override
    assert picked.proc is not None
    assert picked.proc.stderr.strip() == "", "an honoured override needs no warning"


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
    assert picked.status == "FOUND", picked.detail
    assert picked.chosen == "python"
    assert picked.proc is not None
    assert override in picked.proc.stderr, (
        "the selector overrode an explicit PYTHON without a word about it"
    )


def test_the_selector_reports_failure_when_no_candidate_qualifies(barren_path: Path):
    """The trigger for the fail-open branch: it RAN, and nothing qualified.

    Graded as NONE rather than as a non-zero exit. Exit 1 is also what `sh`
    returns when it cannot source the helper at all, and this arm must not pass
    for that reason - it is the arm that certifies the fail-open trigger.
    """
    picked = _pick("pytest", path_prefix=barren_path)
    assert picked.status == "NONE", picked.detail
    assert picked.chosen is None
    assert picked.proc is not None
    assert picked.proc.returncode == 0, (
        "the wrapper reports through its marker, so a non-zero exit here means "
        "the shell died on the way rather than the selector answering"
    )


def test_a_bare_pick_still_finds_a_working_interpreter(barren_path: Path):
    """With no module named, any interpreter that RUNS qualifies.

    pre-commit and commit-msg need this: the scripts they drive are stdlib-only,
    so a box without dev deps must still get its glyph gate. That gate is
    fail-CLOSED and must not be turned into a fail-open one by this change.
    """
    picked = _pick(path_prefix=barren_path)
    assert picked.status == "FOUND", picked.detail
    assert picked.chosen == "python3"


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
# The harness's own discovery helpers, graded for the root cause they used to
# carry. This section needs neither git nor sh nor a Windows box - the pure
# classifiers are the point, and the two callers are monkeypatched at the seam.
# ---------------------------------------------------------------------------

_ABSENT_TOOL = "no_such_msys_tool_xyz"


def _raise_and_catch(fn: typing.Callable[[], object]) -> BaseException:
    """Return whatever a zero-arg callable raises, so its SHAPE can be asserted."""
    try:
        fn()
    except BaseException as exc:  # noqa: BLE001
        return exc
    raise AssertionError("the callable did not raise")


def test_non_vacuity_neither_discovery_helper_can_report_a_tool_failure_as_an_absent_capability(
    monkeypatch, tmp_path: Path,
):
    """Both sites, every failure shape, then the POSITIVE CONTROLS, then the CALLERS.

    Measured 2026-09-08 against the version this replaces: making the
    `git --exec-path` query exit 3 gave 11 passed, 15 skipped, exit 0, every
    skip reading "no POSIX sh on this machine" on a box that had sh; and
    pointing HELPER at a helper whose resin_pick_python returns 1 gave two
    skips reading "no interpreter on this PATH can import pytest" on a box
    carrying both pytest and ruff.

    A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES CANNOT DISCOVER
    THAT THE MATCHER IS NARROW, so the injected failures vary in shape: a
    non-zero exit, exit 0 printing nothing, exit 0 printing junk, exit 0
    printing a relative path, exit 0 naming a path that does not exist, and a
    launch that raises.
    """
    # --- SITE 1, the pure classifier -------------------------------------
    for returncode, stdout, why in (
        (3, "/usr/libexec/git-core", "a non-zero exit"),
        (128, "", "a non-zero exit with no output"),
        (0, "", "exit 0 with no output"),
        (0, "   \n", "exit 0 with only whitespace"),
        (0, "not a path at all", "exit 0 with junk"),
        (0, "libexec/git-core", "exit 0 with a relative path"),
        (0, str(tmp_path / "nope" / "libexec"), "exit 0 naming a path that does not exist"),
    ):
        got = _classify_exec_path(returncode, stdout)
        assert got.status == "FAILED", (
            f"the exec-path classifier reported {why} as something other than a failure"
        )
        assert got.root is None

    # POSITIVE CONTROL. A query that really answered must not read FAILED, or
    # the classifier could return FAILED unconditionally and pass the above.
    answered = _classify_exec_path(0, str(tmp_path) + "\n")
    assert answered.status == "OK"
    assert answered.root == tmp_path
    assert len({answered.status, _classify_exec_path(3, "").status}) == 2

    # --- SITE 2, the pure classifier -------------------------------------
    # A nonce fixed here rather than generated: these are unit inputs, and the
    # arm has to be able to hand the classifier a marker carrying the WRONG
    # nonce, which is only expressible when the right one is known.
    nonce = "0123456789abcdef"

    def mk(body: str) -> str:
        return f"{PICK_MARKER} {nonce} {body}"

    for returncode, stdout, why in (
        (1, "", "the shell dying before the marker, which is exit 1 exactly like a real NONE"),
        (127, "", "a missing function, which exits 127"),
        (0, "", "exit 0 with no marker"),
        (0, "python\n", "the bare selector output with no marker"),
        (0, mk("NOFUNC"), "a helper defining no resin_pick_python"),
        (0, mk("FOUND 2   "), "a success naming no interpreter"),
        (0, mk("WAT 1 python"), "an unknown marker"),
        (0, mk("NONE 1") + "\n" + mk("FOUND 1 python"), "two contradicting markers"),
        # The 2026-09-08 defeats. Each of these SKIPPED the calling arm, with a
        # detail claiming the selector had probed every candidate, against the
        # version this replaces.
        (0, f"{PICK_MARKER} NONE 3", "a marker carrying no nonce, which any source-time echo can print"),
        (0, f"{PICK_MARKER} deadbeefdeadbeef NONE 3", "a marker carrying ANOTHER run's nonce"),
        (0, mk("NONE 0"), "a NONE that probed zero candidates, so no search happened"),
        (0, mk("NONE"), "a NONE carrying no probe count at all"),
        (0, mk("NONE many"), "a NONE whose probe count is not a number"),
        (0, mk("FOUND x python"), "a FOUND whose probe count is not a number"),
    ):
        got = _classify_pick(returncode, stdout, "", nonce)
        assert got.status == "FAILED", (
            f"the pick classifier reported {why} as something other than a failure"
        )
        assert got.chosen is None

    # POSITIVE CONTROLS. RAN-AND-FOUND-NOTHING is NONE, not FAILED, and it is
    # the only status a caller may skip on. A real find is FOUND.
    none = _classify_pick(0, mk("NONE 3") + "\n", "", nonce)
    assert none.status == "NONE" and none.chosen is None
    assert "3" in none.detail, (
        "a NONE must carry the number of candidates it probed into its own "
        f"detail, or the text is a claim nothing backs: {none.detail}"
    )
    found = _classify_pick(0, mk("FOUND 2 python") + "\n", "", nonce)
    assert found.status == "FOUND" and found.chosen == "python"
    spaced = _classify_pick(0, mk("FOUND 2 /c/Program Files/py/python") + "\n", "", nonce)
    assert spaced.chosen == "/c/Program Files/py/python", "an override path may contain spaces"
    # An override that wins on the FIRST candidate is probed by PATH, not by a
    # traced name, so a FOUND may legitimately carry a zero count. FOUND never
    # skips and every FOUND arm proves its answer by importing the module, so
    # the count is not load-bearing there - only on the branch that skips.
    override = _classify_pick(0, mk("FOUND 0 /opt/pyX") + "\n", "", nonce)
    assert override.status == "FOUND" and override.chosen == "/opt/pyX"
    assert len({_classify_pick(1, "", "", nonce).status, none.status, found.status}) == 3

    # --- SITE 1, end to end, with no git and no Windows required ----------
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)

    monkeypatch.setattr(
        sys.modules[__name__], "_query_exec_path",
        lambda: subprocess.CompletedProcess(["git", "--exec-path"], 3, "", "fatal\n"),
    )
    broken = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert broken.status == "FAILED", "a broken exec-path query read as an absent tool"
    assert "exited 3" in broken.detail

    def _raise():
        raise OSError(2, "No such file or directory")

    # A LAUNCH THAT RAISES IS NOT ONE FACT, IT IS TWO, and merging them is the
    # 2026-09-08 defeat this block was rewritten for. FileNotFoundError with no
    # git on PATH is an ABSENT git - disposition 3, the same state the
    # non-Windows branch reports NONE for. Every other launch error is a git
    # that is there and did not work - disposition 2, FAILED.
    #
    # OSError(2, ...) is constructed as a FileNotFoundError by Python's errno
    # mapping, which is why the absent-git shape is written this way and the
    # tool-failure shapes below must carry other errnos.
    assert isinstance(_raise_and_catch(_raise), FileNotFoundError), (
        "the absent-git shape must really be a FileNotFoundError, or this block "
        "grades a branch it never reaches"
    )
    monkeypatch.setattr(sys.modules[__name__], "_query_exec_path", _raise)
    absent = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert absent.status == "NONE", (
        "an absent git was reported as a tool failure, which fails the arm on a "
        f"box that simply has no git installed: {absent.detail}"
    )
    assert "not installed" in absent.detail, absent.detail

    for exc, why in (
        (OSError(13, "Permission denied"), "a git that exists and cannot be executed"),
        (subprocess.TimeoutExpired(["git"], 60), "a git that hung"),
        (subprocess.SubprocessError("spawn failed"), "a spawn that failed"),
    ):
        def _boom(_exc=exc):
            raise _exc

        monkeypatch.setattr(sys.modules[__name__], "_query_exec_path", _boom)
        unlaunchable = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
        assert unlaunchable.status == "FAILED", (
            f"{why} read as an absent tool: {unlaunchable.detail}"
        )
        assert "could not be launched" in unlaunchable.detail

    # And the corroboration itself: FileNotFoundError while git DOES resolve on
    # PATH is not an absent git, so it must stay FAILED. Without this arm the
    # split above could be "any FileNotFoundError is a skip", which is a wider
    # door than the defect asked for.
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: "/usr/bin/git" if name == "git" else None)
    monkeypatch.setattr(sys.modules[__name__], "_query_exec_path", _raise)
    contradictory = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert contradictory.status == "FAILED", (
        "a FileNotFoundError from a git that resolves on PATH is a tool failure, "
        f"not an absent install: {contradictory.detail}"
    )
    assert "not an absent git" in contradictory.detail
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)

    # POSITIVE CONTROL for the search itself: a query that answered, over a
    # real directory, holding no such tool. That is NONE, and it is the state
    # a skip is allowed to describe.
    monkeypatch.setattr(
        sys.modules[__name__], "_query_exec_path",
        lambda: subprocess.CompletedProcess(["git", "--exec-path"], 0, str(tmp_path), ""),
    )
    searched = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert searched.status == "NONE", searched.detail
    # repr, not str: the detail quotes the path through !r, and on Windows that
    # doubles every backslash. A raw str() substring silently never matches.
    assert repr(str(tmp_path)) in searched.detail, "a NONE must say what it searched"

    # And a tool that IS on PATH is FOUND without consulting git at all.
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: "/usr/bin/" + str(name))
    monkeypatch.setattr(sys.modules[__name__], "_query_exec_path", _raise)
    on_path = _msys_tool_pick("sh", search_git_install=True)
    assert on_path.status == "FOUND" and on_path.path == "/usr/bin/sh"


def test_non_vacuity_the_two_callers_enforce_the_status_rather_than_only_reading_it(
    monkeypatch,
):
    """A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE.

    It is not enough that the classifiers return FAILED. `_sh` and the
    real-PATH pick arm are where a FAILED used to become a skip, so they are
    driven here directly through all three statuses.
    """
    this = sys.modules[__name__]

    # --- _sh -------------------------------------------------------------
    monkeypatch.setattr(
        this, "_msys_tool_pick",
        lambda name, **kw: _ToolPick("FAILED", None, "`git --exec-path` exited 3"),
    )
    # NOT `pytest.raises`, and the difference is a MEASURED HOLE, 2026-09-08.
    # `Skipped` derives from BaseException, so `pytest.raises(fail.Exception)`
    # lets it through and the arm ends SKIPPED at exit 0. Regressing `_sh` to
    # the old shape - skip whenever `pick.path is None`, which is both FAILED
    # and NONE - left this file at exit 0 with zero failures: the arm written
    # to grade the gate was itself GREEN-BY-SKIP. Every outcome is captured and
    # its TYPE asserted instead.
    failed = _raise_and_catch(_sh)
    assert isinstance(failed, pytest.fail.Exception), (
        "a FAILED pick must FAIL the caller; this arm saw "
        f"{type(failed).__name__} instead, and a Skipped here would end the arm "
        f"green: {failed}"
    )
    assert "exited 3" in str(failed), "the failure must name the tool failure"
    assert "no POSIX sh on this machine" not in str(failed), (
        "a tool failure must not be reported as a statement about the machine"
    )

    monkeypatch.setattr(
        this, "_msys_tool_pick",
        lambda name, **kw: _ToolPick("NONE", None, "searched /opt/git and found no sh.exe"),
    )
    skipped = _raise_and_catch(_sh)
    assert isinstance(skipped, pytest.skip.Exception), (
        f"a NONE pick must SKIP the caller, not {type(skipped).__name__}: {skipped}"
    )
    assert "no POSIX sh on this machine" in str(skipped)
    assert "searched /opt/git" in str(skipped), "the skip must say what it searched"

    monkeypatch.setattr(
        this, "_msys_tool_pick",
        lambda name, **kw: _ToolPick("FOUND", "/usr/bin/sh", "on PATH"),
    )
    assert _sh() == "/usr/bin/sh", "a FOUND must be returned, not skipped"

    # --- the real-PATH pick arm ------------------------------------------
    arm = test_the_pick_lands_on_an_interpreter_that_can_import_the_module

    monkeypatch.setattr(
        this, "_pick",
        lambda *m, **kw: _PickResult("FAILED", None, None, "the selection script exited 1"),
    )
    busted = _raise_and_catch(lambda: arm("pytest"))
    assert isinstance(busted, AssertionError), (
        "a FAILED pick must FAIL the real-PATH arm; it raised "
        f"{type(busted).__name__} instead: {busted}"
    )
    assert "did not run" in str(busted)

    monkeypatch.setattr(
        this, "_pick",
        lambda *m, **kw: _PickResult("NONE", None, None, "probed every candidate"),
    )
    none_skip = _raise_and_catch(lambda: arm("pytest"))
    assert isinstance(none_skip, pytest.skip.Exception), (
        f"a NONE pick must SKIP the real-PATH arm, not {type(none_skip).__name__}: "
        f"{none_skip}"
    )
    assert "no interpreter on this PATH can import pytest" in str(none_skip)


# ---------------------------------------------------------------------------
# The 2026-09-08 defeats, driven END TO END through a real `sh` against fake
# helpers. The classifier arms above grade a pure function; these grade the
# WRAPPER that feeds it, which is where both defeats actually lived - a marker
# any sourced file could print first, and a count nothing was keeping.
# ---------------------------------------------------------------------------

FAKE_HELPERS = {
    # DEFEAT 1. The selector returns 1 having probed nothing. Exit 1 is also
    # what a real exhausted search returns, and the marker was printed on the
    # `else` branch of exactly that exit status, so the marker WAS the exit
    # code. Measured against the version this replaces: SKIPPED, reading "no
    # interpreter on this PATH can import pytest - the selector probed every
    # candidate", on a box carrying both pytest and ruff.
    "selector_returns_one_without_probing": (
        "#!/bin/sh\n"
        "resin_python_candidates() { echo python3 python py; }\n"
        "resin_pick_python() { return 1; }\n"
    ),
    # DEFEAT 1, second shape. The selector writes a plausible-looking marker,
    # but to stderr, and probes nothing. Same skip, same fabricated detail.
    "selector_lies_on_stderr_and_probes_nothing": (
        "#!/bin/sh\n"
        "resin_pick_python() { echo " + PICK_MARKER + " FOUND 3 /bin/liar >&2; return 1; }\n"
    ),
    # DEFEAT 2. The marker is echoed at SOURCE time by a helper that defines no
    # selector at all, then the file exits. A SHAPE ARM PINS FORMAT, NOT VALUE:
    # the old classifier pinned the presence of a token and this forged it.
    "marker_echoed_at_source_time_then_exits": (
        "#!/bin/sh\n"
        "echo " + PICK_MARKER + " NONE 3\n"
        "exit 0\n"
    ),
    # DEFEAT 2, and the branch that never fired. Same forgery, but the file
    # returns instead of exiting, so control reaches the wrapper's NOFUNC
    # branch - the branch written for "helper defines no resin_pick_python"
    # which the exiting shape above could never reach.
    "no_selector_defined_at_all": (
        "#!/bin/sh\n"
        "echo " + PICK_MARKER + " NONE 3\n"
        "resin_python_candidates() { echo python3 python py; }\n"
    ),
}


@pytest.mark.parametrize("shape", sorted(FAKE_HELPERS))
def test_a_helper_that_never_searched_cannot_buy_a_skip(
    monkeypatch, tmp_path: Path, barren_path: Path, shape: str,
):
    """Every measured forgery must reach FAILED, and must FAIL the caller.

    The second half is not a formality. `Skipped` derives from BaseException,
    so `pytest.raises(Exception)` does not catch it: a regression here would
    surface as a SKIPPED arm rather than a red one, which is the exact failure
    mode this whole section exists to refuse. The caller is therefore driven
    directly and every non-AssertionError outcome is turned into a failure.
    """
    fake = tmp_path / (shape + ".sh")
    fake.write_bytes(FAKE_HELPERS[shape].encode("ascii"))
    monkeypatch.setattr(sys.modules[__name__], "HELPER", fake)

    picked = _pick("pytest", path_prefix=barren_path)
    assert picked.status == "FAILED", (
        f"{shape} was classified {picked.status}, so a caller would act on it "
        f"as an answer: {picked.detail}"
    )
    assert picked.chosen is None

    arm = test_the_pick_lands_on_an_interpreter_that_can_import_the_module
    try:
        arm("pytest")
    except AssertionError as exc:
        assert "did not run" in str(exc), (
            f"{shape} failed the caller for the wrong reason: {exc}"
        )
    except BaseException as exc:  # noqa: BLE001
        pytest.fail(
            f"{shape} reached the caller as {type(exc).__name__} rather than a "
            f"failure: {exc}"
        )
    else:
        pytest.fail(f"{shape} passed the caller silently")


def test_the_real_helper_still_earns_both_answers_on_the_synthetic_paths(
    shimmed_path: Path, barren_path: Path,
):
    """POSITIVE CONTROL. HARDWIRING FAILED WOULD PASS THE ARM ABOVE.

    The real helper, driven over the same wrapper, must still produce a FOUND
    and a NONE - and the COUNTS are asserted exactly, because a count that was
    always zero would condemn every NONE and a count that was never read would
    condemn none of them. `shimmed_path` probes python3 then python, so 2;
    `barren_path` probes all three and rejects all three, so 3.
    """
    found = _pick("pytest", path_prefix=shimmed_path)
    assert found.status == "FOUND", found.detail
    assert "after probing 2 candidate" in found.detail, (
        f"the probe count is not being counted: {found.detail}"
    )

    exhausted = _pick("pytest", path_prefix=barren_path)
    assert exhausted.status == "NONE", exhausted.detail
    assert "probed 3 candidate" in exhausted.detail, (
        "a NONE must hold the number of candidates it actually tried, or its "
        f"detail text is a claim nothing backs: {exhausted.detail}"
    )


# ---------------------------------------------------------------------------
# THE DISCOVERY ITSELF, GRADED. Everything above proves a FABRICATED skip
# cannot happen; nothing above proved the LEGITIMATE search still fires.
#
# Measured 2026-09-08 in the operator's real shape - git on PATH, `sh` not on
# PATH: DELETING the entire git-install search out of `_msys_tool_pick` gave
# 13 passed, 20 SKIPPED, exit 0. THE MUTANT SURVIVED. Twenty arms converted
# into skips whose reason was TRUE in the mutant's world ("no sh.exe sits
# under it or any of its parents"), so no assertion could catch it. That is
# this file's own defect class pointing the other way: a guard against a false
# skip, over a capability nobody graded.
#
# The control needs an oracle that does not go through the code under test, or
# it re-derives the answer it is checking. Its route is independent:
#
#   ROUTE. `_msys_tool_pick` asks git where its exec-path is. The oracle
#   resolves `git` on PATH instead and identifies the install root from the
#   executable's OWN position. Deleting the search under test does not touch it.
#
# WHAT THE ORACLE IS NOT. Corrected 2026-09-08 after both directions were driven
# against planted trees. The version this replaces bounded the walk to three
# ancestors of the git executable and called itself wider than the discovery on
# every axis. Both halves were false, and an arm that claims more than it checks
# is worse than no arm:
#
#   THE ANCESTOR COUNT WAS NOT A CONTAINMENT. On the operator's box `git`
#   resolves to `C:\Program Files\Git\mingw64\bin\git.EXE`, whose third
#   ancestor IS the install root. On the equally ordinary `<install>/cmd/git.exe`
#   layout the third ancestor is `C:\Program Files` - THE CONTAINER, holding
#   every unrelated package beside git. Planted and measured: git at
#   `Program Files/Git/cmd/git.exe` carrying no sh, with an unrelated
#   `Program Files/msys64/usr/bin/sh.exe` beside it. The three-ancestor oracle
#   answered FOUND naming the msys64 sh while the discovery correctly answered
#   NONE - A FALSE RED AGAINST A CORRECT DISCOVERY. NO SINGLE COUNT FIXES IT:
#   `cmd/git.exe` puts the root two up and `mingw64/bin/git.exe` puts it three
#   up, so the count that reaches one overshoots the other into the container.
#   The count is therefore replaced by a POSITIVE MARKER - an ancestor is the
#   install root only when the git executable sits at a known install-relative
#   path under it, which no container satisfies.
#
#   CASE-INSENSITIVITY IS NOT A WIDENING ON NTFS. Measured 2026-09-08: with only
#   `sh.EXE` on disk, `Path("sh.exe").is_file()` is True, so the matcher's own
#   `candidate.is_file()` already matches it. The oracle's lower-cased compare
#   buys correct behaviour on a case-sensitive filesystem and an accurate
#   on-disk name in the detail, and nothing at all against this matcher here.
#
#   THE ORACLE IS NARROWER ON THE ANCESTOR AXIS, not wider. The discovery walks
#   `[root, *root.parents]` - every parent, unbounded. The oracle walks ONE
#   identified root to a bounded depth. Its only real widening is on the
#   SUBDIRECTORY NAME axis: the matcher probes two hardcoded relative names,
#   `usr/bin` and `bin`, while the oracle matches the filename anywhere under
#   the root, so a git that puts `sh.exe` outside those two names goes red here
#   rather than silently skipping.
#
# WHAT THIS THEREFORE DOES NOT GUARANTEE, stated rather than left implied:
#
#   * IT DOES NOT GRADE A GIT REACHED THROUGH A SHIM. Planted and measured: a
#     scoop layout, `.../scoop/shims/git.exe` with the real install at
#     `.../scoop/apps/git/current/`. No ancestor of the shim carries the marker,
#     so the oracle reports could-not-identify and the arm SKIPS - and the
#     delete-the-discovery mutant SURVIVES on such a box. That is an honest
#     exclusion, not a covered case. The old three-ancestor oracle was no better
#     there: it answered a silent NONE, which read as "the install carries none"
#     and hid the same hole behind a wrong reason.
#
#   * IT DOES NOT PROVE THE DISCOVERY'S FOUND IS THE INSTALL'S OWN SH. The
#     discovery's unbounded parent walk can land on a sibling package's
#     `usr/bin/sh.exe`. This arm only requires it to find SOMETHING where the
#     oracle proved something is there.
#
# FOUR DISPOSITIONS, applied to the control itself. Not Windows, git absent, a
# git whose install root cannot be identified, and an identified install
# carrying no `sh.exe` are all COULD-NOT-CHECK and skip with the oracle's own
# reason - each worded differently, because they mean different things. Only
# "the oracle demonstrably found one under the install root it named, and the
# discovery did not" is red.
# ---------------------------------------------------------------------------

# Deep enough for `<git>/usr/bin/sh.exe`, which sits two levels under the
# install root; the extra level is slack for a layout that nests one deeper.
_ORACLE_MAX_DEPTH = 3
# THE POSITIVE MARKER THAT REPLACES THE ANCESTOR COUNT. An ancestor is this
# box's git install root only when the resolved git executable sits at one of
# these paths under it. Compared lower-cased and posix-slashed because the
# operator's box carries `git.EXE` at `mingw64/bin/`. Every entry is a measured
# Git-for-Windows layout; a shim directory satisfies none of them, which is the
# whole point.
_ORACLE_GIT_EXE_RELATIVE = frozenset({
    "cmd/git.exe",
    "bin/git.exe",
    "mingw64/bin/git.exe",
    "mingw32/bin/git.exe",
    "usr/bin/git.exe",
})
# How far up to look for that marker. Four clears the deepest marker above with
# a level to spare, and unlike the count it replaces OVERSHOOTING IS HARMLESS:
# an ancestor without the marker is rejected, never searched.
_ORACLE_ANCESTOR_SEARCH = 4

# WHY THE THREE ORACLE-WRAPPER ARMS BELOW SKIP OFF WINDOWS.
#
# The order of the two clauses is the point. The PRIMARY reason is that the arm
# grades a branch production reaches only on Windows, so off Windows it was
# never exercising real behaviour - it was grading a path nothing takes, with
# install markers that are measured Git-for-Windows layouts. The pathlib
# dispatch is the SECOND reason and would be a false-implying reason on its
# own: it makes the arm ERROR rather than makes the arm meaningful, and a skip
# whose stated reason names the wrong cause is worse than a failure.
#
# The pathlib half, measured: in Python 3.11 `pathlib.Path.__new__` selects
# `WindowsPath` when `os.name == "nt"` and raises
# `NotImplementedError: cannot instantiate 'WindowsPath' on your system` on a
# POSIX host. `_oracle_sh_under_git_install` constructs a bare `Path` at
# `Path(git_exe).resolve()` and again inside `_find_under`, both INSIDE the
# forced window, so on the Linux CI runner these three arms exploded rather
# than failed.
_ORACLE_WINDOWS_ONLY_SKIP = (
    "this arm grades a Windows-only branch - _sh() passes search_git_install=None, "
    "which resolves to os.name == 'nt', and the install markers planted here are "
    "measured Git-for-Windows layouts - so off Windows it never exercised real "
    "behaviour, and forcing os.name to 'nt' on a POSIX host would additionally make "
    "pathlib.Path dispatch to WindowsPath and raise NotImplementedError."
)


def _find_under(root: Path, filename: str, *, max_depth: int = _ORACLE_MAX_DEPTH) -> str | None:
    """Depth-bounded, case-insensitive walk. The oracle's search, not the matcher's."""
    root = Path(root)
    if not root.is_dir():
        return None
    base = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root, onerror=None):
        here = Path(dirpath)
        if len(here.parts) - base >= max_depth:
            dirnames[:] = []
        for candidate in filenames:
            if candidate.lower() == filename.lower():
                return str(here / candidate)
    return None


def _git_install_root(git_exe: Path) -> Path | None:
    """The install root that OWNS this executable, or None when it cannot be told.

    POSITIVE IDENTIFICATION, NOT A COUNT. An ancestor qualifies only when the
    executable sits at a known install-relative path under it, so the container
    directory an install happens to live in never qualifies. A shim - scoop's
    `shims/git.exe`, chocolatey's shim directory - satisfies no entry at all,
    and None is the honest answer there rather than whatever directory happens
    to sit a fixed number of levels up.

    The LONGEST marker wins, which is why the loop keeps going after a hit:
    `<install>/usr/bin/git.exe` also matches the shorter `bin/git.exe` one level
    in, and stopping at the nearest match would name `<install>/usr` as the root
    and never look outside it.
    """
    git_exe = Path(git_exe)
    best: Path | None = None
    for root in list(git_exe.parents)[:_ORACLE_ANCESTOR_SEARCH]:
        if git_exe.relative_to(root).as_posix().lower() in _ORACLE_GIT_EXE_RELATIVE:
            best = root
    return best


def _oracle_sh_under_git_install() -> _ToolPick:
    """Where does an `sh.exe` REALLY sit on this box, established without the matcher.

    Windows only, and for two independent reasons rather than convenience.
    Production reaches the searching branch at all only on Windows - `_sh()`
    passes `search_git_install=None`, which resolves to `os.name == "nt"` - so
    off Windows this arm would grade a path nothing takes. And the install-root
    markers are measured Git-for-Windows layouts: on POSIX the same walk would
    root itself at `/usr` and scan a whole filesystem to answer a question
    production never asks.

    Every non-FOUND answer here is a COULD-NOT-CHECK carrying its own reason.
    None of them is evidence the discovery works, and the caller must skip on
    them rather than pass.
    """
    if os.name != "nt":
        return _ToolPick(
            "NONE", None,
            "this is not Windows, so there is no git-install discovery to grade - "
            "production never reaches that branch here",
        )
    git_exe = shutil.which("git")
    if git_exe is None:
        return _ToolPick(
            "NONE", None,
            "git does not resolve on PATH, so there is no install to search",
        )
    resolved = Path(git_exe).resolve()
    root = _git_install_root(resolved)
    if root is None:
        return _ToolPick(
            "NONE", None,
            f"the git at {str(resolved)!r} sits at no layout this oracle recognises as "
            "an install - a shim directory looks exactly like this - so the install "
            "root cannot be identified and the discovery cannot be graded here",
        )
    hit = _find_under(root, "sh.exe")
    if hit is not None:
        return _ToolPick(
            "FOUND", hit,
            f"a depth-{_ORACLE_MAX_DEPTH} walk under the git install root "
            f"{str(root)!r} found {hit!r}",
        )
    return _ToolPick(
        "NONE", None,
        f"no sh.exe within {_ORACLE_MAX_DEPTH} levels of the git install root "
        f"{str(root)!r}, so this git install carries none and the discovery "
        "cannot be graded here",
    )


@pytest.mark.skipif(os.name != "nt", reason=_ORACLE_WINDOWS_ONLY_SKIP)
def test_the_oracle_that_grades_the_discovery_is_wider_on_names_and_bounded_on_ancestors(
    monkeypatch, tmp_path: Path,
):
    """POSITIVE CONTROL FOR THE CONTROL. An oracle that always answered NONE
    would make the arm below skip forever, which is the exact failure this
    section exists to refuse.

    Plants only, no machine consulted: the canonical layout both searches know,
    a layout only the oracle reaches, an install carrying nothing, and the
    install-root marker driven over every layout it claims.
    """
    canonical = tmp_path / "canonical"
    (canonical / "usr" / "bin").mkdir(parents=True)
    (canonical / "usr" / "bin" / "sh.EXE").write_bytes(b"")
    hit = _find_under(canonical, "sh.exe")
    # NOT A WIDENING OVER THE MATCHER, and the docstring above no longer says it
    # is: measured 2026-09-08, `Path("sh.exe").is_file()` is already True on
    # NTFS with only `sh.EXE` on disk. What this pins is that the walk behaves
    # the same way on a case-sensitive filesystem, and that the detail names the
    # file as it is actually spelled on disk.
    assert hit is not None and Path(hit).name == "sh.EXE", (
        "the oracle must match case-insensitively and report the on-disk name - "
        f"the operator's box carries sh.EXE, not sh.exe: {hit!r}"
    )

    # THE INSTALL-ROOT MARKER, driven over every layout it claims to know. A
    # marker set nothing exercises is a claim nothing backs.
    for rel in sorted(_ORACLE_GIT_EXE_RELATIVE):
        planted = tmp_path / "roots" / rel.replace("/", "_")
        exe = planted.joinpath(*rel.split("/"))
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        # `usr/bin/git.exe` also matches the shorter `bin/git.exe` one level in,
        # so this is the longest-match rule as well as the marker itself.
        assert _git_install_root(exe) == planted, (
            f"the marker {rel!r} did not identify the root it was planted under"
        )
    assert _git_install_root(tmp_path / "nowhere" / "git.exe") is None, (
        "a git at no recognised layout must be UNIDENTIFIABLE, not defaulted to "
        "some ancestor, or the container-directory defeat returns"
    )

    # WIDER THAN THE MATCHER ON THE NAME AXIS, demonstrated rather than asserted
    # in prose. If `_msys_tool_pick`'s two hardcoded names are ever widened to cover sbin,
    # this line goes red; the right response is to move the plant to another
    # path the matcher still does not know, never to delete the arm.
    odd = tmp_path / "odd"
    (odd / "mingw64" / "sbin").mkdir(parents=True)
    (odd / "mingw64" / "sbin" / "sh.exe").write_bytes(b"")
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    monkeypatch.setattr(
        sys.modules[__name__], "_query_exec_path",
        lambda: subprocess.CompletedProcess(["git", "--exec-path"], 0, str(odd), ""),
    )
    narrow = _msys_tool_pick("sh", search_git_install=True)
    assert _find_under(odd, "sh.exe") is not None, "the oracle missed a planted sh.exe"
    assert narrow.status == "NONE", (
        "the matcher was expected to miss a layout outside usr/bin and bin, which "
        "is what makes the oracle able to catch a narrow matcher rather than only "
        f"a deleted one: {narrow.detail}"
    )

    # NEGATIVE CONTROL. An install with no sh.exe must read NONE, or the oracle
    # could return FOUND unconditionally and pass everything above.
    empty = tmp_path / "empty"
    (empty / "usr" / "bin").mkdir(parents=True)
    assert _find_under(empty, "sh.exe") is None
    # And the depth bound is real, not decorative.
    deep = tmp_path / "deep"
    (deep / "a" / "b" / "c" / "d").mkdir(parents=True)
    (deep / "a" / "b" / "c" / "d" / "sh.exe").write_bytes(b"")
    assert _find_under(deep, "sh.exe") is None, "the walk ignored its depth bound"
    assert _find_under(deep, "sh.exe", max_depth=6) is not None

    # AND THE WRAPPER, not only the walk. An oracle stuck at NONE would make
    # the mutant-killer skip forever and nothing would be red, so the ancestor
    # loop is driven end to end against a planted install. `os.name` is forced
    # only to reach the wrapper's own branch - the same reason
    # `search_git_install=True` exists - not to fake its answer.
    install = tmp_path / "planted_git"
    (install / "cmd").mkdir(parents=True)
    (install / "cmd" / "git.exe").write_bytes(b"")
    (install / "usr" / "bin").mkdir(parents=True)
    (install / "usr" / "bin" / "sh.exe").write_bytes(b"")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        shutil, "which",
        lambda name, *a, **k: str(install / "cmd" / "git.exe") if name == "git" else None,
    )
    wrapped = _oracle_sh_under_git_install()
    assert wrapped.status == "FOUND", (
        f"the oracle wrapper missed a planted install: {wrapped.detail}"
    )
    assert wrapped.path is not None and Path(wrapped.path).name.lower() == "sh.exe"

    # NEGATIVE CONTROL for the wrapper: git resolves, install carries no sh.
    # Kept nested one level deeper than the plants above, which was load-bearing
    # against the three-ancestor wrapper this replaces - it would otherwise have
    # found THEIR sh.exe and passed for the wrong reason. Under the marker it is
    # belt and braces; the arm that actually proves a sibling package is out of
    # reach is `test_the_oracle_does_not_wander_into_a_package_beside_the_git_install`.
    bare = tmp_path / "isolated" / "bare_git"
    (bare / "cmd").mkdir(parents=True)
    (bare / "cmd" / "git.exe").write_bytes(b"")
    monkeypatch.setattr(
        shutil, "which",
        lambda name, *a, **k: str(bare / "cmd" / "git.exe") if name == "git" else None,
    )
    assert _oracle_sh_under_git_install().status == "NONE"
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    assert _oracle_sh_under_git_install().status == "NONE", "no git is not gradeable"


@pytest.mark.skipif(os.name != "nt", reason=_ORACLE_WINDOWS_ONLY_SKIP)
def test_the_oracle_does_not_wander_into_a_package_beside_the_git_install(
    monkeypatch, tmp_path: Path,
):
    """DEFEAT REPRODUCED AND CLOSED, 2026-09-08. The oracle over-fired.

    Shape: Git for Windows at `<container>/Git/cmd/git.exe` carrying NO sh, and
    an unrelated msys64 sitting beside it in the same container. The oracle this
    replaces walked three ancestors, reached the container, found the STRANGER'S
    sh.exe and answered FOUND - a false red against a discovery that correctly
    answered NONE, on an ordinary Windows install shape.
    """
    container = tmp_path / "Program Files"
    install = container / "Git"
    git_exe = install / "cmd" / "git.exe"
    git_exe.parent.mkdir(parents=True)
    git_exe.write_bytes(b"")
    (install / "mingw64" / "libexec" / "git-core").mkdir(parents=True)
    stranger = container / "msys64" / "usr" / "bin"
    stranger.mkdir(parents=True)
    (stranger / "sh.exe").write_bytes(b"")

    # NON-VACUITY, both halves. The stranger's sh IS reachable by the walk from
    # the container, and the container IS the third ancestor - so this arm is
    # about the BOUND, not about a plant that was never findable.
    assert _find_under(container, "sh.exe") is not None, "the planted stranger is unreachable"
    assert list(git_exe.parents)[2] == container, (
        "this shape no longer reproduces the defeat: the container is not the "
        "third ancestor any more, so the arm would pass without proving anything"
    )
    assert _find_under(install, "sh.exe") is None, "the install was meant to carry no sh"

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **k: str(git_exe) if name == "git" else None,
    )
    graded = _oracle_sh_under_git_install()
    assert graded.status == "NONE", (
        "the oracle answered for an sh sitting in a package BESIDE the git "
        f"install, which is a false red against a correct discovery: {graded.detail}"
    )
    assert "carries none" in graded.detail, (
        f"the install root was identified, so the reason must say so: {graded.detail}"
    )
    assert "msys64" not in graded.detail, (
        f"the detail names the stranger package, so the walk still reached it: {graded.detail}"
    )


@pytest.mark.skipif(os.name != "nt", reason=_ORACLE_WINDOWS_ONLY_SKIP)
def test_the_oracle_admits_it_cannot_identify_the_install_behind_a_shim(
    monkeypatch, tmp_path: Path,
):
    """THE HOLE, NAMED. A scoop or chocolatey shim is not under the install.

    `.../scoop/shims/git.exe` with the real install at `.../scoop/apps/git/current/`:
    no ancestor of the shim carries an install marker, so the oracle CANNOT SEE
    and the mutant-killer below skips. The delete-the-discovery mutant survives
    on such a box - stated here so the exclusion is disclosed rather than
    discovered. What this arm does enforce is that the skip says the right
    thing: could-not-identify, never "the install carries none".
    """
    scoop = tmp_path / "scoop"
    shim = scoop / "shims" / "git.exe"
    shim.parent.mkdir(parents=True)
    shim.write_bytes(b"")
    real = scoop / "apps" / "git" / "current"
    (real / "usr" / "bin").mkdir(parents=True)
    (real / "usr" / "bin" / "sh.exe").write_bytes(b"")

    # NON-VACUITY: the install behind the shim really does carry an sh, so a
    # NONE here is the oracle admitting it cannot see, not an empty tree.
    assert _find_under(real, "sh.exe") is not None, "the planted install carries no sh"
    assert _git_install_root(shim) is None, "a shim must not be mistaken for an install"

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **k: str(shim) if name == "git" else None,
    )
    graded = _oracle_sh_under_git_install()
    assert graded.status == "NONE", graded.detail
    assert "cannot be identified" in graded.detail, (
        "a shim must be reported as UNIDENTIFIABLE, not as an install carrying "
        f"no sh - the two skips mean different things: {graded.detail}"
    )
    assert "carries none" not in graded.detail, graded.detail


def test_a_bat_shim_git_is_a_shim_shape_and_not_a_broken_git(monkeypatch, tmp_path: Path):
    """DEFEAT REPRODUCED AND CLOSED, 2026-09-08. The corroboration over-fired.

    `shutil.which` is PATHEXT-aware; CreateProcess appends only `.exe`. With a
    `git.bat` as the only git on PATH the two probes disagree with nothing
    broken, and the file went 17 failed / 13 passed / exit 1 blaming a tool
    failure. Everything here is measured against a real launch rather than
    asserted from the exception class.
    """
    if os.name != "nt":
        pytest.skip(
            "PATHEXT and CreateProcess are Windows behaviours - there is no such "
            "disagreement to reproduce off Windows"
        )
    (tmp_path / "git.bat").write_text("@echo off\necho nothing\n", encoding="ascii")
    monkeypatch.setenv("PATH", str(tmp_path))

    # NON-VACUITY 1: `which` really does resolve the .bat off PATHEXT.
    resolved = shutil.which("git")
    assert resolved is not None and Path(resolved).suffix.lower() == ".bat", (
        f"the .bat shim was not resolved by shutil.which, so nothing below is "
        f"reproducing the defeat: {resolved!r}"
    )
    # NON-VACUITY 2: the launch really does raise FileNotFoundError - the real
    # `_query_exec_path`, not a stub, so this is the box's own CreateProcess.
    try:
        _query_exec_path()
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - would mean CreateProcess grew PATHEXT support
        pytest.fail(
            "`git --exec-path` launched a .bat shim, so the disagreement this "
            "branch exists for does not happen on this box"
        )

    shimmed = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert shimmed.status == "NONE", (
        "a PATHEXT-only git shim was reported as a tool failure, which fails the "
        f"whole file on an ordinary Windows install shape: {shimmed.detail}"
    )
    assert "shim" in shimmed.detail and "PATHEXT" in shimmed.detail, shimmed.detail

    # AND THE DOOR IS NARROW. `.exe` and `.com` are launchable, so the same
    # FileNotFoundError against one of them stays the contradiction it was.
    assert ".exe" not in _CREATEPROCESS_CANNOT_LAUNCH, (
        "a .exe git that raises FileNotFoundError is a real tool failure and "
        "must never buy a skip"
    )
    assert _CREATEPROCESS_CANNOT_LAUNCH == frozenset({".bat", ".cmd"}), (
        "the shim door was widened beyond the two shell-script suffixes that "
        f"actually explain the disagreement: {sorted(_CREATEPROCESS_CANNOT_LAUNCH)}"
    )

    def _raise():
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **k: "C:\\fake\\git.exe" if name == "git" else None,
    )
    monkeypatch.setattr(sys.modules[__name__], "_query_exec_path", _raise)
    launchable = _msys_tool_pick(_ABSENT_TOOL, search_git_install=True)
    assert launchable.status == "FAILED", (
        "a .exe git that resolves on PATH and cannot be launched is a tool "
        f"failure, and the shim branch must not swallow it: {launchable.detail}"
    )
    assert "not an absent git" in launchable.detail, launchable.detail


def test_the_git_install_discovery_still_fires_where_an_sh_demonstrably_sits(monkeypatch):
    """THE MUTANT-KILLER. Deleting the git-install search must go RED here.

    Measured 2026-09-08, git on PATH and `sh` not: with the search present this
    arm passes; with the search deleted the file went 13 passed / 20 skipped /
    exit 0 and nothing was red. This arm is the only thing in the file that
    turns that mutation into a failure.

    The PATH lookup is knocked out for `sh` ALONE - every other name stays
    real, so the discovery runs against this box's actual git install and the
    oracle keeps its own independent route.
    """
    oracle = _oracle_sh_under_git_install()
    if oracle.status != "FOUND" or oracle.path is None:
        # COULD-NOT-CHECK, stated as such. This is not evidence the discovery
        # works; it is evidence this box cannot say either way.
        pytest.skip(f"the git-install discovery cannot be graded here: {oracle.detail}")

    real_which = shutil.which
    monkeypatch.setattr(
        shutil, "which",
        lambda name, *a, **k: None if name == "sh" else real_which(name, *a, **k),
    )
    pick = _msys_tool_pick("sh", search_git_install=True)
    assert pick.status == "FOUND", (
        f"an sh.exe demonstrably sits under this box's git install ({oracle.detail}), "
        f"so the git-install discovery must find one; it returned {pick.status} "
        f"instead: {pick.detail}"
    )
    assert pick.path is not None and Path(pick.path).is_file(), (
        f"the discovery named {pick.path!r}, which is not a file"
    )



# ---------------------------------------------------------------------------
# pre-push, end to end. The stubs stand in for ruff and pytest so the arms
# cost milliseconds and do not recursively run the suites they are part of.
# ---------------------------------------------------------------------------


def _run_prepush(path_prefix: Path, env: dict[str, str] | None = None, *,
                 needs_git: bool = True):
    """Run the real pre-push hook under `sh`.

    `needs_git` defaults True because the hook is a GIT hook: it shells out to
    git and exits 128 outside a repository, long before reaching the
    interpreter selection these arms actually grade. Measured in a `git
    archive` extract, the arms then failed with git's "not a git repository"
    in stderr, which names the wrong cause.

    The escape-hatch arm is the one genuine exception - it returns before any
    git call - so it passes `needs_git=False` and stays enforceable in a
    Download-ZIP copy. Skipping it too would be over-skipping: a working guard
    thrown away for no reason.
    """
    if needs_git:
        require_git_repository()

    hook = (HOOKS_DIR / "pre-push").as_posix()
    # PASS THE PATH AS ARGV, NEVER INSIDE THE SCRIPT STRING.
    # `_run_sh(f'"{hook}"')` embeds a quoted Windows-looking path in the `sh -c`
    # argument, and MSYS argv conversion mangles it - the closing quote is lost
    # and sh dies with "unexpected EOF while looking for matching quote".
    # Measured 2026-09-06: it only bites when the repository path contains NO
    # space, because a space suppresses the conversion. So it passed here, at
    # `C:\Resin Compute`, and would fail for a contributor who cloned to
    # `C:\dev\ResinCompute` - the normal case. Same root cause as the
    # `taskkill //F //PID` rule in CLAUDE.md.
    # As `$0`, the path is a separate argv element that sh never re-parses.
    return _run_sh('exec "$0"', path_prefix=path_prefix, env=env, argv=(hook,))


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
    result = _run_prepush(shimmed_path, env={"RESIN_SKIP_PREPUSH": "1"}, needs_git=False)
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
