"""tests/test_hook_gate.py - the commit-time gate FIRES, end to end.

WHY PRESENCE IS NOT PROOF
------------------------
CLAUDE.md states it directly: never treat a hook's PRESENCE as proof it fires.
`.githooks/` being tracked, `core.hooksPath` reading back correctly, and the
three shims being on disk are all satisfiable by a gate that does nothing. The
only valid test is end to end - stage a banned glyph, attempt a REAL commit,
and assert HEAD IS UNCHANGED. Every arm below asserts on HEAD before and after,
because a refusal is a commit that did not happen, not a command that printed
something.

WHY THIS MATTERS MORE ONCE THE REPO IS PUBLIC
---------------------------------------------
`core.hooksPath` is LOCAL config and is not cloned. A fork has never run
`scripts/install_hooks.py`, so for every contributor the commit-time gate is
STRUCTURALLY ABSENT and CI is the only gate there is. That is not a worry, it
is measured here: `test_an_unconfigured_clone_commits_*_straight_through`
unsets `core.hooksPath` in the throwaway repo and watches the same em-dash that
was refused a moment earlier land in history with exit 0.

THE POSITIVE CONTROL IS THE ONE PEOPLE LEAVE OUT
------------------------------------------------
A gate that refuses EVERYTHING passes both refusal arms below. The
catastrophically broken version is the one that looks safest, and it is also
the shape a broken FIXTURE produces: copy the shims without
`scripts/hook_python.sh` and every hook dies sourcing a missing file, every
commit fails, and both negatives go green while measuring nothing.
`test_clean_ascii_change_commits` is the arm that fails in that world, so it is
load-bearing rather than decorative. The negatives additionally require the
gate's OWN marker on stderr, so a refusal is attributed to the gate rather than
to any other reason a commit can fail.

THE TWO NEGATIVES ARE SEPARATE ON PURPOSE. Staged CONTENT goes through
`pre-commit`; the MESSAGE goes through `commit-msg`. Git's order is
pre-commit -> prepare the message -> commit-msg, so `.git/COMMIT_EDITMSG` does
not exist yet when pre-commit runs and the message half CANNOT live there.
One arm passing says nothing about the other.

FIXTURE TRAPS, each already paid for elsewhere in this tree:

  * GLOBAL AND SYSTEM GIT CONFIG ARE CUT OFF. An inherited `core.hooksPath`,
    `autocrlf` or LFS filter would make the fixture measure the wrong repo and
    it would still look green.
  * EVERY INHERITED `GIT_*` VARIABLE IS DROPPED **FROM THE THROWAWAY REPO'S
    ENVIRONMENT**. `.githooks/pre-push` runs `pytest tests`, so this module can
    run from inside a git hook, and an inherited `GIT_INDEX_FILE` would point
    the fixture's `git` calls at the outer repository. Measured in this
    worktree: the agent harness already exports `GIT_EDITOR`.

    TWO CORRECTIONS, both measured 2026-09-06 by an adversarial pass, because
    the first version of this paragraph overstated its own reach:

    THE SCRUB IS NOT GLOBAL TO THIS MODULE. It lives in `_throwaway_env` and
    covers the fixture only. `test_the_tracked_hook_set_is_exactly_the_three_
    this_probe_copies` and `test_every_tracked_hook_is_mode_100755_in_the_index`
    run `git ls-files` against `REPO_ROOT` with the INHERITED environment, and
    they are supposed to: they ask about THIS repository. Under a planted
    `GIT_DIR`/`GIT_INDEX_FILE` they go RED rather than wrong, which is the
    acceptable failure - but "every `git` call below" was false.

    AND THE CITED MECHANISM IS CONFIGURATION-SCOPED, which the correction above
    it did not say and which made it read as a claim about git rather than about
    one checkout. On `git 2.53.0.windows.3` the answer depends on WHERE the push
    is made from. Measured 2026-09-11 in a throwaway repository with a main
    checkout, one linked worktree and a `pre-push` that dumps its own
    environment, every returncode read in Python:

      MAIN CHECKOUT    `pre-push` sees `GIT_EXEC_PATH` and `GIT_PREFIX`, and no
                       `GIT_DIR` and no `GIT_INDEX_FILE`.
      LINKED WORKTREE  `pre-push` sees those two AND
                       `GIT_DIR=<main>/.git/worktrees/<name>`.

    `git hook run --ignore-missing pre-push` splits exactly the same way, so a
    reading taken through that command inherits the same scope and is not a
    third configuration. The `pre-commit` half - `GIT_INDEX_FILE` exported, no
    `GIT_DIR` - is the 2026-09-06 reading carried forward and was NOT re-measured
    on 2026-09-11.

    THIS TREE IS WORKED IN LINKED WORKTREES under `.claude/worktrees/`, so the
    worktree row is the live configuration and not the hypothetical one. What it
    used to mean is the paragraph above: the two arms here that run `git
    ls-files` against `REPO_ROOT` under the inherited environment went RED there.
    They no longer do. `conftest.py` at the repository root now removes `GIT_DIR`
    and eight siblings at IMPORT, before any test module is loaded, and
    `tests/test_git_env_scrub.py` feeds each of them in as a real exported value
    and measures the corpus that comes back. `_throwaway_env` still drops every
    inherited `GIT_*` from the fixture's child environment, and that is still
    load-bearing: a process-wide scrub at conftest import cannot defend against a
    variable set DURING the run.

    `GIT_EDITOR` IS NOT GIT'S DOING, and naming it alongside the other two read
    as though it were. It is in this module's environment because the agent
    harness exports it; a probe that clears `GIT_*` before pushing does not see
    git put it back.
  * THE INTERPRETER IS PINNED via `PYTHON`, with backslashes as forward
    slashes, so the probe depends on the gate rather than on whatever PATH
    happens to resolve. `scripts/hook_python.sh` warns on stderr when it passes
    over an explicit `PYTHON`; the positive control asserts that warning is
    absent, which is how the pin is confirmed rather than assumed.
  * `commit.gpgsign false`, because an unsigned-commit prompt hangs CI.
  * THE REAL HOOK BODIES ARE COPIED, not stubs. A stub tests the fixture. They
    are copied as BYTES - `Path.write_text` converts LF to CRLF on Windows and
    a CRLF shebang makes the kernel look for an interpreter named `/bin/sh`
    with a trailing CR, so the hook is skipped and every arm here passes for
    the wrong reason.
  * THE HOOKS ARE NOT SELF-CONTAINED. All three source
    `"$ROOT/scripts/hook_python.sh"`, where ROOT is the THROWAWAY repo, so the
    dependency set has to be copied too.
    `test_the_hooks_reference_nothing_outside_the_copied_dependency_set`
    re-derives that set from the shipped hook bodies and fails when it drifts,
    so the fixture cannot quietly stop being faithful.
  * THE INDEX MODE IS SET EXPLICITLY. 100644 is the difference between a gate
    and nothing on Linux, and git REPORTS NOTHING when it declines to run a
    non-executable hook.
  * THE BASELINE COMMIT USES `--no-verify`. The fixture's own scaffolding is
    not what is under test. This is the one sanctioned use of that flag: a
    throwaway repo under tmp_path, never this repository's history.
  * COMMITS GO THROUGH `-F <file>`, NEVER `-m`. A non-ASCII message handed over
    in argv can be mangled before the hook ever sees it, which would test the
    shell rather than the gate. The message file is written OUTSIDE the
    throwaway worktree so it can never be staged by accident.
  * THE BANNED GLYPH IS AN ESCAPE, NEVER A LITERAL. `chr(0x2014)` concatenated
    in, so this file does not become a banned-glyph hit that trips the very
    gate it tests - and so an editor cannot normalise the escape back into one.
  * NO REMOTE IS EVER CONFIGURED. `.githooks/pre-push` runs both suites; a
    probe that fired it would recurse.

RSC_REQUIRE_HOOK_GATE
---------------------
Set it to 1 and every SKIP below becomes a FAILURE. CI sets it. Without it the
whole module skips on a runner that cannot reach a POSIX `sh`, and A SKIPPED
TEST IS A GREEN TICK - which is exactly how a sibling repo's five hooks sat at
mode 100644 for weeks while CI stayed green.

The flag governs a REAL ABSENCE and nothing else. A TOOL FAILURE does not reach
it: see below.

"COULD NOT CHECK" IS NOT "CHECKED AND FOUND NOTHING"
---------------------------------------------------
Two helpers here used to collapse those two facts into one value, and the flag
above could not repair either of them, because a flag decides how LOUD an answer
is and not whether the answer is TRUE.

  * THE SHELL LOCATOR fell back to `Path(".")` whenever `git --exec-path` did
    not answer, found no `sh.exe` under it, and returned a bare None. The
    fixture then skipped with "no POSIX sh on this machine". Measured
    2026-09-08 with only that one probe broken: 6 passed, 6 skipped at exit 0,
    on a machine holding C:\\Program Files\\Git\\usr\\bin\\sh.EXE the whole
    time. It now returns a STATUS: FAILED fails outright and names the tool,
    and only a true NONE may skip.
  * `head()` returned `''` both for an unborn HEAD and for a git that could not
    read the repository. `after == before` is satisfied by two empty strings,
    so a probe that never ran would have reported that a banned glyph was
    refused. It now raises on a tool failure, and the unborn case is asserted
    against in the arms that depend on HEAD having moved.
  * `git remote` was read as a bare `.stdout.strip() == ""`. THE SAME SHAPE
    AGAIN: an empty string is the legitimate "no remotes configured" answer AND
    what a failed git leaves behind. Measured 2026-09-08 with a REAL `origin`
    planted and only the one-argument `git remote` call made to return
    (128, '', 'fatal: ...'): 1 passed, exit 0. That assertion IS the whole arm,
    so a broken git retired it in silence.
  * `git config --get core.hooksPath` was read the same way, and this was the
    worst of the four because the arm holding it NAMES the check it was not
    doing - "this arm would measure an armed repo". Measured 2026-09-08 with
    `core.hooksPath` left SET and only that one call broken: 1 passed, exit 0.
    An arm whose name claims more than it checks is worse than no arm.

THE TWO NEW SITES DO NOT SHARE ONE FIX, and their exit-code contracts were
established by RUNNING git 2.53.0.windows.3 rather than by recall:

    git remote      -> 0 with empty stdout is the LEGITIMATE no-remotes answer,
                       128 on a fatal. The exit code is the whole fingerprint.
    git config --get-> 0 with a value, 0 with empty stdout when the key is set
                       to the empty string, 1 when the key is absent, 1 ALSO
                       when run outside a repository, 128 on a fatal. Exit 1 is
                       shared, so the caller asks a second question - can git
                       read this repository - exactly as the HEAD reader does.

A RESIDUAL THIS ROUND DID NOT CLOSE, AND IT IS ABOUT HOW A GREEN RUN RENDERS
---------------------------------------------------------------------------
With RSC_REQUIRE_HOOK_GATE unset and a GENUINE absence - no POSIX sh, no git,
no `.githooks/` to copy - every fixture-dependent arm here SKIPS and the run
exits 0. Measured 2026-09-08 in this worktree by making `shutil.which('git')`
answer None, which is the fixture's own real third-disposition branch (the tool
is not present on this platform): 16 passed, 6 skipped, EXIT 0, rendered as

    ................ssssss

and nothing else. `pytest.ini` sets `addopts = -q` and does NOT set `-rs`, so
the six skip REASONS - each of which names the flag - are never printed. A
GREEN LINE FOR THIS FILE CAN THEREFORE MEAN THE GATE WAS NEVER EXERCISED.

The counts above are this machine on this day and are not a contract; what is
stable is the shape - dots and `s` at exit 0, with no reason text.

WHERE THIS BITES, precisely. `.github/workflows/ci.yml` runs this file TWICE.
Its dedicated hook-gate step sets `RSC_REQUIRE_HOOK_GATE=1`, so that step is
sound and the residual does not reach it. The later `python -m pytest tests`
step does NOT set the flag, and it is the one whose green tick can be six
silent skips. Closing that means changing CI, which is outside this file.

A reader running the file by hand should pass `-rs`, or set
RSC_REQUIRE_HOOK_GATE=1, before believing a green run measured anything.

Every arm that grades those four lives above the fixture section, is pure, and
runs on every machine.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import typing
from pathlib import Path

import pytest

from tests.conftest import git_unusable_reason

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".githooks"

# MEASURED against this tree, not copied from a sibling. Sibling-C's
# equivalent step asserts five hooks; asserting five here would be red on
# arrival. Named rather than counted, because a bare count drifts silently in
# either direction.
EXPECTED_HOOKS = ("commit-msg", "pre-commit", "pre-push")

# Everything the three shims reach for through "$ROOT/". All four are
# stdlib-only, which is what makes a bare `git init` enough to run them.
# Re-derived from the hook bodies below rather than trusted.
HOOK_DEPENDENCIES = (
    "scripts/hook_python.sh",
    "scripts/precommit_msg_check.py",
    "scripts/precommit_pycompile.py",
    "tools/precommit_gate.py",
)

# Never a literal. See the module docstring.
EM_DASH = chr(0x2014)

# The gate's own headline. Asserting on it attributes a refusal to the GATE
# rather than to any other reason a commit can fail - a missing dependency, a
# rejected subject line, an unwritable index.
GATE_MARKER = "precommit_gate BLOCKED"

# Both negatives and both unconfigured-clone arms share these bytes on purpose.
# The unconfigured arm proves the message is otherwise LEGAL - a valid
# Conventional Commits subject that `scripts/precommit_msg_check.py` accepts -
# so the refusal in the armed arm is attributable to the glyph and nothing else.
CLEAN_CONTENT = b"a clean ascii line - nothing banned here\n"
CLEAN_MESSAGE = b"docs(gate-probe): a clean ascii commit\n"
GLYPH_CONTENT = ("clause" + EM_DASH + "break\n").encode("utf-8")
GLYPH_MESSAGE = (
    "docs(gate-probe): subject" + EM_DASH + "carrying a banned glyph\n"
).encode("utf-8")

REQUIRE_FLAG = "RSC_REQUIRE_HOOK_GATE"

# Generous: each commit spawns sh, then python, then git again from inside the
# gate. The gate carries its own 20s/60s inner ceilings.
_TIMEOUT = 180


# ---------------------------------------------------------------------------
# Availability, and the flag that turns a skip into a failure
# ---------------------------------------------------------------------------


def _unavailable(reason: str) -> None:
    """Skip - or FAIL, when CI has demanded the gate actually be measured.

    A skip is the honest answer on a machine with no POSIX `sh` or no git:
    nothing is wrong with the gate, it simply cannot be exercised here. On a CI
    runner that is not honest, it is a hole - the run goes green having proved
    nothing. RSC_REQUIRE_HOOK_GATE closes it.
    """
    if os.environ.get(REQUIRE_FLAG) == "1":
        pytest.fail(
            f"{REQUIRE_FLAG}=1 demands the hook gate be measured, and it could "
            f"not be: {reason}"
        )
    pytest.skip(f"{reason} (set {REQUIRE_FLAG}=1 to make this a failure)")


class _ToolPick(typing.NamedTuple):
    """The answer to "where is this POSIX tool", as a STATUS and never a bare None.

    FOUND  - a path was located, and `path` carries it.
    NONE   - the machine was successfully asked and genuinely holds no such tool.
    FAILED - the question could not be put. This is NOT the same fact as NONE
             and must never be reported as one.
    """

    status: str
    path: str | None
    detail: str


class _ExecPathPick(typing.NamedTuple):
    """The pure reading of one `git --exec-path` outcome. READ or FAILED."""

    status: str
    root: Path | None
    detail: str


def _classify_exec_path(
    returncode: int,
    stdout: str,
    is_dir: typing.Callable[[Path], bool] | None = None,
) -> _ExecPathPick:
    """The PURE half of the locator, so its FAILED arms are testable anywhere.

    THE DEFECT THIS REPLACES, and it is the seventh site of one root cause
    closed in this tree: the caller did

        proc = subprocess.run(["git", "--exec-path"], check=False)
        root = Path(proc.stdout.strip() or ".")

    so a git that exited non-zero, printed nothing, or printed junk collapsed
    into `Path(".")`, the scan under it found no `sh.exe`, the locator returned
    None, and the fixture took a skip reading "no POSIX sh on this machine".
    That sentence is a claim ABOUT THE MACHINE, and it was measured FALSE:
    2026-09-08, with only the exec-path call broken, this file reported
    6 passed, 6 skipped at exit 0 on a machine carrying
    C:\\Program Files\\Git\\usr\\bin\\sh.EXE the whole time.

    `is_dir` is injectable because "the directory git named is not there" is a
    fifth failure shape, and an arm that could not reach it would be grading
    only the shapes the matcher already handles.
    """
    probe = Path.is_dir if is_dir is None else is_dir
    if returncode != 0:
        return _ExecPathPick(
            "FAILED", None, f"the exec-path probe exited {returncode}"
        )
    text = stdout.strip()
    if not text:
        return _ExecPathPick(
            "FAILED", None, "the exec-path probe exited 0 and printed nothing"
        )
    root = Path(text)
    # ABSOLUTE, and this is the assertion that kills the `or "."` fallback: `.`
    # is a perfectly good directory, so an is_dir check alone would pass it.
    if not root.is_absolute():
        return _ExecPathPick(
            "FAILED",
            None,
            f"the exec-path probe exited 0 and printed {text!r}, which is not an absolute path",
        )
    if not probe(root):
        return _ExecPathPick(
            "FAILED",
            None,
            f"the exec-path probe named {text!r}, which is not a directory on this machine",
        )
    return _ExecPathPick("READ", root, f"the exec-path probe named {text}")


def _tool_under(root: Path, name: str) -> str | None:
    """The scan itself. Separate, so a miss here is a MISS and not a failure."""
    for base in [root, *root.parents]:
        for rel in ("usr/bin", "bin"):
            candidate = base / rel / f"{name}.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def _locate_msys_tool(name: str) -> _ToolPick:
    """Locate a POSIX tool, falling back to the one git ships on Windows.

    PowerShell has no `sh` on PATH and the operator runs the suite from there,
    so it is located from git's own install rather than assumed reachable.
    Same shape as tests/test_hook_interpreter.py, for the same reason.

    Returns a STATUS. See _classify_exec_path for what the bare `str | None`
    this replaces could not say.
    """
    direct = shutil.which(name)
    if direct:
        return _ToolPick("FOUND", direct, f"{name} is on PATH at {direct}")
    if os.name != "nt":
        return _ToolPick(
            "NONE",
            None,
            f"PATH carries no {name}, and this is not Windows, so there is no "
            "git-shipped copy to fall back to",
        )
    try:
        proc = subprocess.run(
            ["git", "--exec-path"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # THE FOURTH SHAPE. Before this, an OSError here escaped as a raw
        # traceback out of a fixture - loud, but attributed to nothing.
        return _ToolPick(
            "FAILED",
            None,
            f"the exec-path probe could not be launched: {type(exc).__name__}: {exc}",
        )
    read = _classify_exec_path(proc.returncode, proc.stdout)
    if read.status == "FAILED" or read.root is None:
        return _ToolPick("FAILED", None, read.detail)
    found = _tool_under(read.root, name)
    if found is not None:
        return _ToolPick(
            "FOUND", found, f"{read.detail}, and {name} sits beside it at {found}"
        )
    return _ToolPick(
        "NONE",
        None,
        f"PATH carries no {name}, {read.detail}, and no {name}.exe sits under it",
    )


def _require_posix_sh() -> str:
    """The sh this probe needs, or the RIGHT kind of stop.

    FAILED FAILS, and RSC_REQUIRE_HOOK_GATE is deliberately NOT consulted on
    that branch: a tool that could not be run is a failure on every runner, and
    routing it through the flag would let the default configuration keep
    reporting a tool failure as a fact about the machine. Only a true NONE
    reaches `_unavailable`, where the flag still decides skip against fail.
    """
    pick = _locate_msys_tool("sh")
    if pick.status == "FAILED":
        pytest.fail(
            "the POSIX sh this probe needs could not be LOOKED FOR, which is not "
            f"the same fact as this machine not having one: {pick.detail}. "
            "Reporting it as an absent shell would be a claim about the machine "
            "that this run cannot support."
        )
    if pick.status == "NONE":
        _unavailable(
            f"no POSIX sh on this machine - {pick.detail} - so the .githooks/ "
            "shims cannot run"
        )
    assert pick.path is not None
    return pick.path


def _require_real_repo() -> None:
    """The arms that ask git about THIS tree, routed through the flag.

    `tests/conftest.py` already decides when trackedness is unknowable (a
    Download-ZIP or `git archive` copy). Its reason text is reused; only the
    verdict differs, so that RSC_REQUIRE_HOOK_GATE reaches these arms too.
    """
    reason = git_unusable_reason()
    if reason is not None:
        _unavailable(reason)


# ---------------------------------------------------------------------------
# The throwaway repository
# ---------------------------------------------------------------------------


# A commit id, sha1 or sha256. The shape is asserted so that an exit 0 which
# printed something OTHER than a commit id cannot be stored as "the HEAD".
_COMMIT_ID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class _HeadRead(typing.NamedTuple):
    """FOUND / UNBORN / FAILED. The second site of the same root cause."""

    status: str
    sha: str | None
    detail: str


def _classify_head_read(returncode: int, stdout: str, repo_is_readable: bool) -> _HeadRead:
    """Read one `rev-parse HEAD` outcome, PURELY.

    THE SIBLING SITE. `head()` used to be

        return self.git("rev-parse", "HEAD").stdout.strip()

    which returns '' for an unborn HEAD AND '' for a git that could not read the
    repository at all. Both negative arms below then assert `after == before`,
    and '' == '' is a pass. A probe that could not run would have reported that
    a banned glyph was refused.

    A SHARED EXIT CODE IS NOT A FINGERPRINT: git exits 128 both for an unborn
    HEAD and for "not a repository", so the exit code cannot separate them. The
    caller therefore asks a SECOND question - can git read this repository at
    all - and that answer is what `repo_is_readable` carries.
    """
    text = stdout.strip()
    if returncode == 0:
        if _COMMIT_ID_RE.match(text):
            return _HeadRead("FOUND", text, f"HEAD is {text}")
        if not text:
            return _HeadRead(
                "FAILED", None, "`rev-parse HEAD` exited 0 and printed nothing"
            )
        return _HeadRead(
            "FAILED",
            None,
            f"`rev-parse HEAD` exited 0 and printed {text!r}, which is not a commit id",
        )
    if repo_is_readable:
        return _HeadRead(
            "UNBORN",
            None,
            f"`rev-parse HEAD` exited {returncode} in a repository git can otherwise "
            "read, so HEAD is unborn",
        )
    return _HeadRead(
        "FAILED",
        None,
        f"`rev-parse HEAD` exited {returncode} and git could not read the throwaway "
        "repository at all",
    )


class _RemoteRead(typing.NamedTuple):
    """NONE / PRESENT / FAILED. The THIRD site of the same root cause."""

    status: str
    names: tuple[str, ...]
    detail: str


def _classify_remote_list(returncode: int, stdout: str) -> _RemoteRead:
    """Read one `git remote` outcome, PURELY.

    THE DEFECT THIS REPLACES. The guard used to be a single line:

        remotes = gate_repo.git("remote").stdout.strip()
        assert remotes == ""

    and that assertion IS the whole arm, so a git that could not answer retired
    it in silence. Measured 2026-09-08 in this worktree with a REAL `origin`
    planted and only the one-argument `git remote` call made to return
    (128, '', 'fatal: ...'): 1 passed, exit 0. The arm reported that no remote
    existed while one did.

    MEASURED EXIT-CODE CONTRACT, git 2.53.0.windows.3, run rather than recalled:

        no remotes configured      -> exit 0, empty stdout
        one remote configured      -> exit 0, "origin"
        corrupt config / not a repo-> exit 128, empty stdout, fatal on stderr

    So exit 0 with nothing printed is the LEGITIMATE "nothing configured"
    answer here, and the empty string alone cannot be trusted. The exit code is
    the whole fingerprint, which is why this site does NOT get the second
    readability question `_classify_config_get` needs.
    """
    if returncode != 0:
        return _RemoteRead(
            "FAILED",
            (),
            f"`git remote` exited {returncode}, so whether this repository has a "
            "remote was never established",
        )
    names = tuple(line.strip() for line in stdout.splitlines() if line.strip())
    if names:
        return _RemoteRead("PRESENT", names, f"`git remote` named {list(names)}")
    return _RemoteRead(
        "NONE", (), "`git remote` exited 0 and named nothing, so there is no remote"
    )


class _ConfigRead(typing.NamedTuple):
    """SET / UNSET / FAILED. The FOURTH site of the same root cause."""

    status: str
    value: str | None
    detail: str


def _classify_config_get(
    returncode: int, stdout: str, repo_is_readable: bool
) -> _ConfigRead:
    """Read one `git config --get <key>` outcome, PURELY.

    THE DEFECT THIS REPLACES, and it was the worst of the four because the arm
    holding it NAMES the thing it failed to check - "this arm would measure an
    armed repo":

        assert gate_repo.git("config", "--get", "core.hooksPath").stdout.strip() == ""

    Measured 2026-09-08 in this worktree with `core.hooksPath` left SET and
    only that one `config --get` call made to return (128, '', 'fatal: ...'):
    1 passed, exit 0. The guard passed while core.hooksPath was still
    configured. An arm whose name claims more than it checks is worse than no
    arm.

    MEASURED EXIT-CODE CONTRACT, git 2.53.0.windows.3, run rather than recalled:

        key set                    -> exit 0, the value on stdout
        key set to the EMPTY string-> exit 0, empty stdout (still SET)
        key not set                -> exit 1, empty stdout
        run outside any repository -> exit 1, empty stdout
        corrupt config file        -> exit 128, empty stdout

    A SHARED EXIT CODE IS NOT A FINGERPRINT, the same lesson as
    `_classify_head_read`: exit 1 is BOTH "not set" and "git could not read a
    repository here". So the caller asks a second question - can git read this
    repository at all - and that answer arrives as `repo_is_readable`.

    Exit 0 with empty stdout is deliberately SET rather than UNSET. `git config
    core.hooksPath ""` produces exactly that, and a key present in the config
    file with an empty value is not an unconfigured clone.
    """
    text = stdout.strip()
    if returncode == 0:
        return _ConfigRead(
            "SET",
            text,
            f"`config --get` exited 0 and the key holds {text!r}"
            if text
            else "`config --get` exited 0 with no value, so the key is present and "
            "set to the empty string",
        )
    if returncode == 1:
        if repo_is_readable:
            return _ConfigRead(
                "UNSET",
                None,
                "`config --get` exited 1 in a repository git can otherwise read, so "
                "the key is genuinely not set",
            )
        return _ConfigRead(
            "FAILED",
            None,
            "`config --get` exited 1 and git could not read the throwaway repository "
            "at all, so 'not set' would be a claim about a repository that was never "
            "reached",
        )
    return _ConfigRead(
        "FAILED",
        None,
        f"`config --get` exited {returncode}, which is neither git's 0 for a value "
        "nor its 1 for an absent key",
    )


class _ThrowawayRepo:
    """A `git init` under tmp_path wired exactly the way the installer wires
    this one, and isolated from everything about the machine it runs on."""

    def __init__(self, root: Path, env: dict[str, str], message_file: Path) -> None:
        self.root = root
        self.env = env
        self.message_file = message_file

    def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        """Every git exec in this fixture, and a DESIGNED failure when the exec
        itself is refused.

        GIT PRESENT BUT NOT RUNNABLE is a fourth state, and before this guard
        it escaped as a raw traceback out of a fixture - loud, but attributed
        to nothing, exactly as the fourth shape in `_locate_msys_tool` used to.
        It is routed to a FAILURE and not to a skip: `shutil.which` answered a
        path, so any skip claiming git is absent would be FALSE, and a false
        reason is the whole defect the four readers above exist to close. It is
        also not consulted against RSC_REQUIRE_HOOK_GATE, for the same reason
        `_require_posix_sh` does not consult it on FAILED - a tool that could
        not be RUN is a failure on every runner, and this one is actionable: a
        reader can repair a permission, where a skip would bury it under a
        green tick.
        """
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(self.root),
                env=self.env,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AssertionError(
                "the throwaway repository's git could not be RUN, which is not the "
                f"same fact as this machine not having git: `git {' '.join(args)}` "
                f"raised {type(exc).__name__}: {exc}, while PATH answers "
                f"{shutil.which('git')!r} for it. Nothing about the repository was "
                "measured, so no arm here may report on the gate - and a skip "
                "claiming an absent git would be a statement PATH contradicts."
            ) from exc
        if check and proc.returncode != 0:
            raise AssertionError(
                f"fixture setup failed: `git {' '.join(args)}` exited "
                f"{proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        return proc

    def read_head(self) -> _HeadRead:
        """The status-carrying read. The second git call happens ONLY on a
        failure, because that is the only time the two 128s need separating."""
        proc = self.git("rev-parse", "HEAD")
        if proc.returncode == 0:
            return _classify_head_read(proc.returncode, proc.stdout, True)
        readable = self.git("rev-parse", "--git-dir").returncode == 0
        return _classify_head_read(proc.returncode, proc.stdout, readable)

    def head(self) -> str:
        """The current commit, or '' on an unborn HEAD - and a RAISE when git
        could not answer, because 'HEAD did not move' would then be a statement
        about nothing."""
        read = self.read_head()
        if read.status == "FAILED":
            raise AssertionError(
                "the throwaway repository could not be read, so no arm here may "
                f"report on whether HEAD moved: {read.detail}"
            )
        return read.sha or ""

    def read_remotes(self) -> _RemoteRead:
        """The status-carrying `git remote`. One call is enough: the exit code
        alone separates all three outcomes at this site."""
        proc = self.git("remote")
        return _classify_remote_list(proc.returncode, proc.stdout)

    def remotes(self) -> tuple[str, ...]:
        """Every configured remote, and a RAISE when git could not answer -
        because 'this repo has no remote' would then be a statement about
        nothing at all. Same contract as head()."""
        read = self.read_remotes()
        if read.status == "FAILED":
            raise AssertionError(
                "the throwaway repository's remotes could not be read, so no arm "
                f"here may report that it has none: {read.detail}"
            )
        return read.names

    def read_config(self, key: str) -> _ConfigRead:
        """The status-carrying `git config --get`. The SECOND git call happens
        ONLY on exit 1, because that is the only code git shares between 'not
        set' and 'this is not a repository'."""
        proc = self.git("config", "--get", key)
        if proc.returncode != 1:
            return _classify_config_get(proc.returncode, proc.stdout, True)
        readable = self.git("rev-parse", "--git-dir").returncode == 0
        return _classify_config_get(proc.returncode, proc.stdout, readable)

    def config_is_unset(self, key: str) -> bool:
        """True when git positively answered that `key` holds nothing, and a
        RAISE when git could not answer. The bare `.stdout.strip() == ''` this
        replaces returned True in both worlds."""
        read = self.read_config(key)
        if read.status == "FAILED":
            raise AssertionError(
                f"the throwaway repository's {key} could not be read, so no arm here "
                f"may report that it is unset: {read.detail}"
            )
        return read.status == "UNSET"

    def stage(self, relpath: str, content: bytes) -> None:
        """write_BYTES, never write_text - the latter would rewrite LF to CRLF
        on Windows and change what is being staged."""
        target = self.root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        self.git("add", "--", relpath, check=True)

    def commit(self, message: bytes, *, no_verify: bool = False) -> subprocess.CompletedProcess:
        """`-F`, never `-m`. See the module docstring."""
        self.message_file.write_bytes(message)
        args = ["commit", "-F", str(self.message_file)]
        if no_verify:
            args.insert(1, "--no-verify")
        return self.git(*args)

    def disarm(self) -> None:
        """Become an ordinary fresh clone: tracked hooks present, none active."""
        self.git("config", "--unset", "core.hooksPath", check=True)


def _throwaway_env(root: Path, sh_path: str) -> dict[str, str]:
    """The environment for the throwaway repo. `sh_path` is PASSED IN rather
    than looked up again: a second lookup would be a second chance to conflate a
    tool failure with an absent shell, and this one is silent - it would simply
    not append to PATH and the hooks would die on `grep: command not found`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # Non-existent paths. Git reads them as empty config, which is the point:
    # an inherited hooksPath, autocrlf or LFS filter would make every arm below
    # a statement about the wrong repository.
    env["GIT_CONFIG_GLOBAL"] = str(root / "no-global-gitconfig")
    env["GIT_CONFIG_SYSTEM"] = str(root / "no-system-gitconfig")
    env["PYTHON"] = sys.executable.replace("\\", "/")
    # APPENDED. Launched from PowerShell, `sh.exe` inherits a PATH with no
    # /usr/bin on it and the hooks die on `grep: command not found` - a
    # harness artefact with nothing to do with what is being graded.
    env["PATH"] = env.get("PATH", "") + os.pathsep + str(Path(sh_path).parent)
    return env


@pytest.fixture
def gate_repo(tmp_path: Path) -> _ThrowawayRepo:
    if shutil.which("git") is None:
        _unavailable("git is not on PATH, so no repository can be created")
    # FAILS on a tool failure, SKIPS only on a real absence. See
    # _require_posix_sh - this line is the enforced caller, and
    # test_the_fixture_itself_fails_rather_than_skipping_on_a_tool_failure
    # drives THIS function rather than the predicate.
    sh_path = _require_posix_sh()
    for name in EXPECTED_HOOKS:
        if not (HOOKS_DIR / name).is_file():
            _unavailable(f"missing {HOOKS_DIR / name}, so the real hook cannot be copied")

    root = tmp_path / "throwaway"
    root.mkdir()
    repo = _ThrowawayRepo(root, _throwaway_env(root, sh_path), tmp_path / "commit-message.txt")

    repo.git("init", check=True)
    for key, value in (
        ("user.name", "Hook Gate Probe"),
        ("user.email", "hook-gate-probe@example.invalid"),
        # An unsigned-commit prompt HANGS CI.
        ("commit.gpgsign", "false"),
        # RELATIVE, the same wiring scripts/install_hooks.py performs. An
        # absolute path would not survive the repo moving.
        ("core.hooksPath", ".githooks"),
    ):
        repo.git("config", key, value, check=True)

    # shutil.copy preserves BYTES. hook_python.sh in particular must keep LF.
    (root / ".githooks").mkdir()
    for name in EXPECTED_HOOKS:
        shutil.copy(HOOKS_DIR / name, root / ".githooks" / name)
    for rel in HOOK_DEPENDENCIES:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, destination)

    repo.git("add", "-A", check=True)
    for name in EXPECTED_HOOKS:
        repo.git("update-index", "--chmod=+x", f".githooks/{name}", check=True)

    baseline = repo.commit(b"chore(gate-probe): baseline scaffolding\n", no_verify=True)
    if baseline.returncode != 0:
        raise AssertionError(
            f"fixture baseline commit failed: {baseline.returncode}\n"
            f"stdout: {baseline.stdout}\nstderr: {baseline.stderr}"
        )
    if not repo.head():
        raise AssertionError("fixture baseline commit left HEAD unborn")
    return repo


# ---------------------------------------------------------------------------
# The flag itself, in both directions
#
# RSC_REQUIRE_HOOK_GATE is the whole reason the CI step is worth having, so it
# cannot be the one thing here taken on faith. If `_unavailable` silently kept
# skipping under the flag, CI would go green having measured nothing - which is
# precisely the failure this module exists to make impossible.
# ---------------------------------------------------------------------------


def test_the_require_flag_turns_an_unmeasurable_gate_into_a_failure(monkeypatch):
    monkeypatch.setenv(REQUIRE_FLAG, "1")
    with pytest.raises(pytest.fail.Exception) as excinfo:
        _unavailable("synthetic reason")
    assert "synthetic reason" in str(excinfo.value)
    assert REQUIRE_FLAG in str(excinfo.value)


def test_without_the_flag_an_unmeasurable_gate_is_an_honest_skip(monkeypatch):
    """NON-VACUITY, the other direction. A skip is the right answer on a
    machine with no POSIX sh - nothing is wrong with the gate, it simply cannot
    be exercised. If this arm also failed, the flag would be doing nothing and
    the arm above would pass for free."""
    monkeypatch.delenv(REQUIRE_FLAG, raising=False)
    with pytest.raises(pytest.skip.Exception) as excinfo:
        _unavailable("synthetic reason")
    assert "synthetic reason" in str(excinfo.value)
    assert REQUIRE_FLAG in str(excinfo.value), (
        "the skip reason must name the flag, or a reader has no way to learn "
        "that the skip can be made fatal"
    )


# ---------------------------------------------------------------------------
# "COULD NOT CHECK" IS NOT "CHECKED AND FOUND NOTHING"
#
# The whole reason the flag above exists is that a skip reads as a green tick.
# A skip whose TEXT IS FALSE is worse: it sends the reader to a machine that is
# fine. Measured 2026-09-08 against the version of this file that shipped
# before these arms, with nothing broken but the exec-path probe:
#
#     6 passed, 6 skipped, exit 0
#     SKIPPED tests/test_hook_gate.py:497: no POSIX sh on this machine - the
#     .githooks/ shims cannot run (set RSC_REQUIRE_HOOK_GATE=1 to make this a
#     failure)
#
# while `shutil.which('sh')` on that same machine answered
# C:\Program Files\Git\usr\bin\sh.EXE. Exit 0 with junk and exit 0 with no
# output produced the identical six skips; an OSError escaped as a raw
# traceback instead. Under RSC_REQUIRE_HOOK_GATE=1 the run went red - but with
# the same false sentence, so the flag bought loudness and not attribution.
#
# The arms below grade the CLASSIFIER, which is pure and runs on every machine,
# and then the CALLERS, because a gate tested only as a pure predicate is not
# an enforced gate.
# ---------------------------------------------------------------------------


# Absolute on the platform the arm is running on. `/usr/lib/git-core` is
# absolute to POSIX and RELATIVE to Windows (no drive), so a single hardcoded
# string would make the positive controls below pass on one platform and fail
# on the other for a reason that has nothing to do with the subject.
_AN_ABSOLUTE_DIR = (
    "C:/Program Files/Git/mingw64/libexec/git-core"
    if os.name == "nt"
    else "/usr/lib/git-core"
)


def test_non_vacuity_every_shape_of_a_broken_exec_path_probe_reads_as_a_tool_failure():
    """A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES cannot discover
    that the matcher is narrow, so the shapes are varied: a non-zero exit, a
    non-zero exit that still printed a usable path, silence, whitespace, the
    relative `.` the old fallback substituted, junk, and an error message
    delivered on stdout."""
    always_a_dir: typing.Callable[[Path], bool] = lambda _p: True  # noqa: E731
    for returncode, stdout, why in (
        (3, "", "a non-zero exit"),
        (1, _AN_ABSOLUTE_DIR, "a non-zero exit that still printed a usable path"),
        (0, "", "exit 0 with no output"),
        (0, "   \n", "exit 0 with whitespace only"),
        (0, ".", "exit 0 printing the relative path the old fallback substituted"),
        (0, "not a path at all\n", "exit 0 with junk"),
        (0, "libexec/git-core\n", "exit 0 with a RELATIVE path"),
        (0, "fatal: not a repository\n", "exit 0 with an error message on stdout"),
    ):
        got = _classify_exec_path(returncode, stdout, is_dir=always_a_dir)
        assert got.status == "FAILED", (
            f"the locator read {why} as {got.status} rather than a tool failure, so a "
            f"caller could report it as a fact about the machine"
        )
        assert got.root is None

    # THE FIFTH SHAPE, and the reason is_dir is injectable: git named a
    # directory that is not there.
    never_a_dir: typing.Callable[[Path], bool] = lambda _p: False  # noqa: E731
    absent = _classify_exec_path(0, _AN_ABSOLUTE_DIR, is_dir=never_a_dir)
    assert absent.status == "FAILED"
    assert "not a directory" in absent.detail

    # POSITIVE CONTROLS. Without these a classifier hardwired to FAILED passes
    # everything above.
    read = _classify_exec_path(0, _AN_ABSOLUTE_DIR + "\n", is_dir=always_a_dir)
    assert read.status == "READ", "a probe that really answered must not read as a failure"
    assert read.root == Path(_AN_ABSOLUTE_DIR)
    # THE STATUS, not the tuple's arity - a shape arm pins format, not value.
    assert len({read.status, _classify_exec_path(3, "", is_dir=always_a_dir).status}) == 2


def test_non_vacuity_a_tool_failure_and_an_absent_shell_are_different_answers():
    """The locator's three outcomes, driven end to end through the real
    function with only the two tools it calls replaced."""
    real_which = shutil.which

    def _no_sh(cmd, *a, **k):
        return None if str(cmd) in ("sh", "sh.exe") else real_which(cmd, *a, **k)

    # FAILED: Windows, nothing on PATH, and the exec-path probe broken.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "name", "nt")
        patch.setattr(shutil, "which", _no_sh)
        patch.setattr(
            subprocess,
            "run",
            lambda *a, **k: subprocess.CompletedProcess(["probe"], 3, "", "fatal: broken"),
        )
        failed = _locate_msys_tool("sh")
    assert failed.status == "FAILED"
    assert "exited 3" in failed.detail

    # FAILED, the launch shape. An OSError used to escape as a raw traceback.
    def _explode(*a, **k):
        raise OSError("simulated launch failure")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "name", "nt")
        patch.setattr(shutil, "which", _no_sh)
        patch.setattr(subprocess, "run", _explode)
        exploded = _locate_msys_tool("sh")
    assert exploded.status == "FAILED"
    assert "OSError" in exploded.detail

    # NONE: the machine was successfully asked and holds no sh.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "name", "posix")
        patch.setattr(shutil, "which", _no_sh)
        none = _locate_msys_tool("sh")
    assert none.status == "NONE"
    assert none.path is None

    # FOUND: PATH answered, and no probe was needed at all.
    def _forbidden(*a, **k):
        raise AssertionError("PATH already answered; the probe must not be run")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(shutil, "which", lambda cmd, *a, **k: "/somewhere/sh")
        patch.setattr(subprocess, "run", _forbidden)
        found = _locate_msys_tool("sh")
    assert found.status == "FOUND"
    assert found.path == "/somewhere/sh"

    # And the three are genuinely distinct, so none of the above is satisfied
    # by a locator that answers the same word every time.
    assert len({failed.status, none.status, found.status}) == 3


def test_the_caller_fails_rather_than_skipping_when_the_shell_could_not_be_looked_for(
    monkeypatch,
):
    """FAILED must FAIL, and it must do so WHETHER OR NOT the flag is set.

    pytest.raises(Exception) DOES NOT CATCH pytest's Skipped - it derives from
    BaseException, so a guard written that way would let the skip through and
    report `s` rather than red. This catches BaseException and then asserts on
    the TYPE, which is the only way to tell a fail from a skip here.
    """
    real_which = shutil.which
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda cmd, *a, **k: None if str(cmd) in ("sh", "sh.exe") else real_which(cmd, *a, **k),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(["probe"], 3, "", "fatal: broken"),
    )

    for flag in (None, "1"):
        if flag is None:
            monkeypatch.delenv(REQUIRE_FLAG, raising=False)
        else:
            monkeypatch.setenv(REQUIRE_FLAG, flag)
        with pytest.raises(BaseException) as excinfo:  # noqa: B017 - see docstring
            _require_posix_sh()
        assert isinstance(excinfo.value, pytest.fail.Exception), (
            f"with {REQUIRE_FLAG}={flag!r} a tool failure came out as "
            f"{type(excinfo.value).__name__}, not a failure"
        )
        message = str(excinfo.value)
        assert "exited 3" in message, "the failure must name the TOOL failure"
        assert "no POSIX sh on this machine" not in message, (
            "the failure must not repeat the false claim about the machine that "
            "this whole section exists to remove"
        )


def test_positive_control_a_genuinely_absent_shell_still_takes_an_honest_skip(monkeypatch):
    """The other direction, and it is what keeps the arm above from being
    satisfied by a `_require_posix_sh` that fails unconditionally. A machine
    with no sh is not a broken run - and RSC_REQUIRE_HOOK_GATE still governs
    THIS branch, so the flag mechanism is intact rather than bypassed."""
    real_which = shutil.which
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda cmd, *a, **k: None if str(cmd) in ("sh", "sh.exe") else real_which(cmd, *a, **k),
    )

    monkeypatch.delenv(REQUIRE_FLAG, raising=False)
    with pytest.raises(BaseException) as skipped:  # noqa: B017 - Skipped is not an Exception
        _require_posix_sh()
    assert isinstance(skipped.value, pytest.skip.Exception), (
        f"a genuinely absent sh came out as {type(skipped.value).__name__}, so the "
        "honest skip has been turned into noise"
    )
    assert REQUIRE_FLAG in str(skipped.value)

    monkeypatch.setenv(REQUIRE_FLAG, "1")
    with pytest.raises(BaseException) as failed:  # noqa: B017
        _require_posix_sh()
    assert isinstance(failed.value, pytest.fail.Exception), (
        f"{REQUIRE_FLAG}=1 must still turn the honest skip into a failure"
    )


def test_positive_control_the_caller_returns_the_shell_when_one_is_found(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: "/somewhere/sh")
    assert _require_posix_sh() == "/somewhere/sh"


# THREE DISPOSITIONS, NOT TWO.
#
# `gate_repo` asks `shutil.which("git")` BEFORE it asks for sh. So a machine
# with no git binary at all - a Download-ZIP or sdist user, the population
# tests/conftest.py exists to serve - takes the git skip first, and an arm that
# patched only the sh locator would grade the tree's own CORRECT answer as a
# defect. Measured 2026-09-08 with `shutil.which("git")` returning None and
# subprocess raising FileNotFoundError for argv[0] == "git":
#
#     1 failed, 14 passed, 8 skipped, exit 1
#     AssertionError: the FIXTURE turned a broken exec-path probe into Skipped.
#
# with nothing wrong but the absence of git. The FOUR answers are - three of
# them named here from the start, and the fourth added 2026-09-08 after it was
# found escaping as six raw tracebacks:
#
#     tool ran, machine genuinely holds none  -> SKIP, reason TRUE
#     tool ran, something went wrong          -> FAIL
#     tool is NOT PRESENT AT ALL              -> SKIP, reason TRUE
#     tool is PRESENT but cannot be EXECUTED  -> FAIL. Not a skip: PATH
#         answered a path, so "git is not on PATH" would be FALSE. Graded by
#         test_a_git_that_is_present_but_cannot_be_executed_fails_and_never_skips
#         and enforced in `_ThrowawayRepo.git`.
#
# This does NOT redden ubuntu-latest CI - actions/checkout@v6 hands the runner
# a real repository with git and /bin/sh, so the git guard never fires there.
# It is exactly and only the git-less population that it broke.
_PINNED_GIT = "/pinned/git-need-not-exist"


def _sh_absent_git_pinned(real_which):
    """A `shutil.which` substitute: sh ABSENT, git PINNED PRESENT.

    One named object, so the arm below and the guard below it grade the SAME
    callable rather than two hand-copied lambdas that can drift apart. Pinning
    git present is what lets the arm grade the sh branch IN ISOLATION instead
    of being pre-empted by the fixture's first guard.
    """

    def _which(cmd, *a, **k):
        name = str(cmd)
        if name in ("sh", "sh.exe"):
            return None
        if name in ("git", "git.exe"):
            return real_which(name, *a, **k) or _PINNED_GIT
        return real_which(cmd, *a, **k)

    return _which


def test_the_fixture_itself_fails_rather_than_skipping_on_a_tool_failure(monkeypatch, tmp_path):
    """A GATE TESTED AS A PURE PREDICATE IS NOT AN ENFORCED GATE.

    Everything above grades `_require_posix_sh`. This arm drives the FIXTURE -
    the only caller that matters - through `gate_repo.__wrapped__`, which is
    the undecorated function pytest keeps for exactly this. Delete the call in
    the fixture and the predicate arms all stay green while this one goes red.
    """
    real_which = shutil.which
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(shutil, "which", _sh_absent_git_pinned(real_which))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(["probe"], 3, "", "fatal: broken"),
    )
    monkeypatch.delenv(REQUIRE_FLAG, raising=False)

    with pytest.raises(BaseException) as excinfo:  # noqa: B017 - Skipped is not an Exception
        gate_repo.__wrapped__(tmp_path)
    assert isinstance(excinfo.value, pytest.fail.Exception), (
        f"the FIXTURE turned a broken exec-path probe into "
        f"{type(excinfo.value).__name__}. The predicate can be perfect and this "
        "still be a hole."
    )
    assert "exited 3" in str(excinfo.value)


def test_the_fixture_arm_grades_the_sh_branch_and_not_the_absence_of_git(monkeypatch, tmp_path):
    """THE PERMANENT ARM for the three dispositions above.

    Two guards on the substitute, because a sweep proved only by "the bad thing
    is gone" is satisfied by deleting the subject; then the third disposition
    driven end to end, because pinning git present inside ONE arm must not have
    taught the fixture to fail on a machine that genuinely has no git.
    """
    # GUARD ONE - the substitute reports git PRESENT even when the machine
    # underneath holds none. Revert it to a partial patch that passes git
    # straight through to real_which and this line goes red.
    nothing_on_this_machine: typing.Callable[..., str | None] = lambda _cmd, *a, **k: None  # noqa: E731
    which = _sh_absent_git_pinned(nothing_on_this_machine)
    for name in ("git", "git.exe"):
        assert which(name) is not None, (
            f"the substitute let {name} read as absent, so the arm above grades "
            "the fixture's git guard rather than the sh branch it means to"
        )

    # GUARD TWO - the LEGITIMATE NEIGHBOUR SURVIVES. sh is still reported
    # absent, so the arm above still reaches the branch it exists to grade. A
    # substitute that answered a path for everything would satisfy guard one
    # and measure nothing.
    for name in ("sh", "sh.exe"):
        assert which(name) is None, (
            f"the substitute answered a path for {name}, so the sh branch is "
            "never entered and the arm above passes for free"
        )

    # GUARD THREE - disposition 3, driven through the real fixture on a fully
    # git-less world. An honest SKIP naming git, not a failure.
    #
    # WHAT PROVES THE GUARD SHORT-CIRCUITS, STATED PER PLATFORM. An earlier
    # version of this comment credited one mechanism - "reach it and this comes
    # out as FileNotFoundError rather than Skipped" - and that mechanism holds
    # on NEITHER platform, because `_locate_msys_tool` CATCHES OSError; that is
    # its documented fourth shape. Measured 2026-09-08 in this worktree with
    # the fixture's git guard moved below `_require_posix_sh()`:
    #
    #   os.name == "nt"    -> Failed, from the FAILED branch of
    #                         `_require_posix_sh` (the exec-path probe could not
    #                         be launched). The isinstance line below kills it.
    #   os.name == "posix" -> Skipped, reason "no POSIX sh on this machine".
    #                         The isinstance line PASSES; only the message
    #                         assertion below kills it.
    #
    # CI runs this file on ubuntu-latest, so the posix row is the one that
    # matters, and `assert "git is not on PATH"` is load-bearing rather than
    # decorative. That row's own behaviour - forced os.name, absent sh, honest
    # skip - is graded on every machine by
    # test_positive_control_a_genuinely_absent_shell_still_takes_an_honest_skip.
    def _no_git_binary(args, *a, **k):
        raise FileNotFoundError(2, "No such file or directory: 'git'")

    monkeypatch.setattr(shutil, "which", nothing_on_this_machine)
    monkeypatch.setattr(subprocess, "run", _no_git_binary)
    monkeypatch.delenv(REQUIRE_FLAG, raising=False)
    with pytest.raises(BaseException) as excinfo:  # noqa: B017 - Skipped is not an Exception
        gate_repo.__wrapped__(tmp_path)
    assert isinstance(excinfo.value, pytest.skip.Exception), (
        f"a machine with NO GIT AT ALL came out as {type(excinfo.value).__name__}. "
        "Tool-not-present is disposition 3 - an honest skip, not a defect."
    )
    assert "git is not on PATH" in str(excinfo.value)
    assert REQUIRE_FLAG in str(excinfo.value)


# Pinned present so this arm cannot be pre-empted by the fixture's OTHER two
# guards. Never opened, exactly like _PINNED_GIT above: substituting any value
# at all leaves the arm's verdict unchanged, because nothing here executes it.
_PINNED_SH = "/pinned/sh-need-not-exist"


def test_a_git_that_is_present_but_cannot_be_executed_fails_and_never_skips(
    monkeypatch, tmp_path
):
    """THE FOURTH DISPOSITION, which used to leave the fixture as a raw traceback.

    `shutil.which` answers a path, so git IS present on this machine; the exec
    itself is refused. Measured 2026-09-08 in this worktree, before
    `_ThrowawayRepo.git` guarded it, by raising PermissionError for
    argv[0] == "git" while leaving git on PATH:

        16 passed, 2 skipped, 6 errors, exit 1
        PermissionError: [Errno 13] Permission denied: 'git'

    six of them, one per fixture-dependent arm, attributed to nothing. Every
    other error path in this file is a designed sentence; that one was an
    uncaught exception, which is the shape CLAUDE.md forbids surfacing raw.

    WHICH DISPOSITION IT BELONGS TO, and why the other three are wrong. Not
    disposition 1 or 3: PATH answered a path, so a skip reading "git is not on
    PATH" would be FALSE, and a false skip reason is precisely the "could not
    check reported as checked and found nothing" defect the four readers above
    exist to close. It is disposition 2 - the question could not be PUT.
    Nothing about the repository was measured and nothing is wrong with the
    gate, but that is equally true of a broken exec-path probe, and
    `_require_posix_sh` already rules that a tool which could not be RUN fails
    on every runner. RSC_REQUIRE_HOOK_GATE is deliberately not consulted, for
    that same reason: an exec denial is a fact about this process rather than
    about the machine's inventory, and it is actionable - a reader can repair a
    permission, where a skip would bury it under a green tick.
    """
    real_which = shutil.which

    def _both_tools_present(cmd, *a, **k):
        name = str(cmd)
        if name in ("git", "git.exe"):
            return real_which(name, *a, **k) or _PINNED_GIT
        if name in ("sh", "sh.exe"):
            return real_which(name, *a, **k) or _PINNED_SH
        return real_which(cmd, *a, **k)

    # GUARD ONE - the substitute reports git PRESENT even on a machine holding
    # none. Without it, a git-less runner would take the fixture's FIRST guard
    # and this arm would grade disposition 3 all over again, passing for free.
    nothing_on_this_machine: typing.Callable[..., str | None] = lambda _cmd, *a, **k: None  # noqa: E731
    which = _both_tools_present
    monkeypatch.setattr(shutil, "which", nothing_on_this_machine)
    for name in ("git", "git.exe"):
        assert which(name) is not None, (
            f"the substitute let {name} read as absent, so this arm grades the "
            "fixture's git guard rather than the exec denial it means to"
        )

    # GUARD TWO - and sh reports PRESENT too, so `_require_posix_sh` returns
    # without executing anything and the FIRST exec reached is the fixture's
    # own `git init`. A substitute that left sh absent would satisfy guard one
    # and still measure the sh branch instead.
    for name in ("sh", "sh.exe"):
        assert which(name) is not None, (
            f"the substitute let {name} read as absent, so the sh branch fires "
            "first and the exec denial is never reached"
        )

    def _exec_denied(args, *a, **k):
        raise PermissionError(13, "Permission denied: 'git'")

    monkeypatch.setattr(shutil, "which", _both_tools_present)
    monkeypatch.setattr(subprocess, "run", _exec_denied)
    monkeypatch.delenv(REQUIRE_FLAG, raising=False)

    with pytest.raises(BaseException) as excinfo:  # noqa: B017 - Skipped is not an Exception
        gate_repo.__wrapped__(tmp_path)
    assert not isinstance(excinfo.value, pytest.skip.Exception), (
        "a git that PATH answers for, but that this process may not execute, "
        "came out as a SKIP. Every reason available to that skip claims an "
        f"absence: {excinfo.value}"
    )
    assert isinstance(excinfo.value, AssertionError), (
        "a refused git exec came out as "
        f"{type(excinfo.value).__name__} rather than a designed failure. A raw "
        "PermissionError out of the fixture is attributed to nothing, which is "
        "the state this arm exists to keep closed."
    )
    message = str(excinfo.value)
    assert "could not be RUN" in message
    assert "PermissionError" in message


def test_non_vacuity_an_unreadable_head_is_never_reported_as_a_head_that_did_not_move():
    """THE SIBLING SITE, and it is the one that would have made a REFUSAL ARM
    lie: `after == before` is satisfied by two empty strings."""
    for returncode, stdout, readable, why in (
        (128, "", False, "not a repository"),
        (1, "", False, "git failed and could not read the repo"),
        (0, "", True, "exit 0 with no output"),
        (0, "HEAD\n", True, "exit 0 printing something that is not a commit id"),
        (0, "fatal: bad revision\n", True, "exit 0 with an error message on stdout"),
        (0, "0123456789abcdef\n", True, "exit 0 with a truncated id"),
    ):
        got = _classify_head_read(returncode, stdout, readable)
        assert got.status == "FAILED", f"an unreadable HEAD read as {got.status}: {why}"
        assert got.sha is None

    # UNBORN is a real, different answer: git read the repository fine and
    # there simply is no commit yet.
    unborn = _classify_head_read(128, "", True)
    assert unborn.status == "UNBORN"
    assert unborn.sha is None

    # POSITIVE CONTROLS, both id lengths this tree could ever see.
    sha1 = "0" * 40
    sha256 = "a" * 64
    assert _classify_head_read(0, sha1 + "\n", True) == _HeadRead(
        "FOUND", sha1, f"HEAD is {sha1}"
    )
    assert _classify_head_read(0, sha256, True).status == "FOUND"

    # Three distinct answers, so none of the above is met by one constant.
    assert len({
        _classify_head_read(128, "", False).status,
        unborn.status,
        _classify_head_read(0, sha1, True).status,
    }) == 3


def test_the_head_reader_raises_rather_than_returning_an_empty_string_it_cannot_defend():
    """The CALLER of that classifier. `head()` returns '' for an unborn HEAD,
    which is legitimate, and must RAISE when git could not answer - otherwise
    the two are the same string and the negative arms cannot tell them apart."""

    class _Broken(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(args), 128, "", "fatal: not a repo")

    class _Unborn(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            if args[:2] == ("rev-parse", "--git-dir"):
                return subprocess.CompletedProcess(list(args), 0, ".git\n", "")
            return subprocess.CompletedProcess(list(args), 128, "", "fatal: bad revision")

    class _Born(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(args), 0, "b" * 40 + "\n", "")

    broken = _Broken(Path("."), {}, Path("unused.txt"))
    with pytest.raises(AssertionError) as excinfo:
        broken.head()
    assert "could not be read" in str(excinfo.value)

    # POSITIVE CONTROLS through the same method.
    assert _Unborn(Path("."), {}, Path("unused.txt")).head() == ""
    assert _Born(Path("."), {}, Path("unused.txt")).head() == "b" * 40


def test_non_vacuity_an_unreadable_remote_list_is_never_reported_as_having_no_remote():
    """THE THIRD SITE. `git remote` legitimately exits 0 printing nothing when
    a repo has no remotes, so the empty string is the RIGHT answer and the
    WRONG answer at the same time - the exit code is the only separator."""
    for returncode, stdout, why in (
        (128, "", "not a repository"),
        (128, "", "a corrupt config file, which git also reports as 128"),
        (1, "", "a generic non-zero exit"),
        (129, "usage: git remote\n", "a usage error that still printed to stdout"),
    ):
        got = _classify_remote_list(returncode, stdout)
        assert got.status == "FAILED", (
            f"an unanswerable remote list read as {got.status}: {why}"
        )
        assert got.names == ()

    # NONE is a real, different answer: git answered, and there is no remote.
    none = _classify_remote_list(0, "")
    assert none.status == "NONE"
    assert none.names == ()
    assert _classify_remote_list(0, "  \n \n").status == "NONE", (
        "whitespace-only output is still git answering that there are no remotes"
    )

    # POSITIVE CONTROLS - the arm must be able to SEE a remote, or it would
    # pass in the world it exists to refuse.
    one = _classify_remote_list(0, "origin\n")
    assert one.status == "PRESENT"
    assert one.names == ("origin",)
    assert _classify_remote_list(0, "origin\nupstream\n").names == ("origin", "upstream")

    # Three distinct answers, so none of the above is met by one constant.
    assert len({
        _classify_remote_list(128, "").status,
        none.status,
        one.status,
    }) == 3


def test_non_vacuity_an_unreadable_config_key_is_never_reported_as_unset():
    """THE FOURTH SITE, and the one whose arm NAMES the check it was not doing.

    Exit 1 is git's code for BOTH "the key is not set" and "there is no
    repository here", so the readability answer is what separates them - the
    same shape `_classify_head_read` needs for its two 128s.
    """
    for returncode, stdout, readable, why in (
        (128, "", True, "a corrupt config file"),
        (128, "", False, "not a repository"),
        (1, "", False, "exit 1 where git could not read the repo at all"),
        (5, "", True, "an unset of a key that does not exist"),
        (2, "", True, "no section or name provided"),
    ):
        got = _classify_config_get(returncode, stdout, readable)
        assert got.status == "FAILED", (
            f"an unanswerable config read reported {got.status}: {why}"
        )
        assert got.value is None

    # UNSET is a real, different answer: git read the repository and the key
    # genuinely is not there.
    unset = _classify_config_get(1, "", True)
    assert unset.status == "UNSET"
    assert unset.value is None

    # POSITIVE CONTROLS. The empty-value case is the trap: `git config
    # core.hooksPath ""` exits 0 printing nothing, and that key IS set.
    assert _classify_config_get(0, ".githooks\n", True) == _ConfigRead(
        "SET", ".githooks", "`config --get` exited 0 and the key holds '.githooks'"
    )
    empty = _classify_config_get(0, "", True)
    assert empty.status == "SET", (
        "a key set to the empty string is present in the config file and must not "
        "read as an unconfigured clone"
    )
    assert empty.value == ""

    # Three distinct answers, so none of the above is met by one constant.
    assert len({
        _classify_config_get(128, "", True).status,
        unset.status,
        empty.status,
    }) == 3


def test_the_remote_and_config_readers_raise_rather_than_answering_for_a_broken_git():
    """The CALLERS of those two classifiers, because a gate tested only as a
    pure predicate is not an enforced gate.

    Both of these used to be a bare `.stdout.strip()`, and both of the arms
    that hold them assert on an EMPTY STRING - which is what a failed git
    leaves behind. Measured 2026-09-08 in this worktree, each with only its own
    subcommand broken and everything else really running: 1 passed, exit 0,
    once with a real `origin` configured and once with `core.hooksPath` still
    set.
    """

    class _Broken(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(args), 128, "", "fatal: not a repo")

    class _NotSet(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            if args[:2] == ("rev-parse", "--git-dir"):
                return subprocess.CompletedProcess(list(args), 0, ".git\n", "")
            return subprocess.CompletedProcess(list(args), 1, "", "")

    class _Armed(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(args), 0, ".githooks\n", "")

    class _NoRemote(_ThrowawayRepo):
        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(list(args), 0, "", "")

    class _Exit1Unreadable(_ThrowawayRepo):
        """Git's exit 1 for `config --get` OUTSIDE a repository - measured
        2026-09-08, and byte-identical to its exit 1 for an absent key. This
        drives the SECOND question `read_config` asks; without it a caller that
        never asked would pass every arm above."""

        def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
            if args[:2] == ("rev-parse", "--git-dir"):
                return subprocess.CompletedProcess(list(args), 128, "", "fatal: not a repo")
            return subprocess.CompletedProcess(list(args), 1, "", "")

    broken = _Broken(Path("."), {}, Path("unused.txt"))
    with pytest.raises(AssertionError) as remote_failure:
        broken.remotes()
    assert "may report that it has none" in str(remote_failure.value)
    with pytest.raises(AssertionError) as config_failure:
        broken.config_is_unset("core.hooksPath")
    assert "may report that it is unset" in str(config_failure.value)

    # THE SHARED EXIT CODE, through the caller. A `config --get` that exits 1
    # is 'not set' ONLY when git could read the repository; here it could not,
    # so this must raise rather than answer.
    with pytest.raises(AssertionError) as shared_code:
        _Exit1Unreadable(Path("."), {}, Path("unused.txt")).config_is_unset("core.hooksPath")
    assert "could not read the throwaway repository at all" in str(shared_code.value)

    # POSITIVE CONTROLS through the same methods, both directions each.
    assert _NoRemote(Path("."), {}, Path("unused.txt")).remotes() == ()
    assert _Armed(Path("."), {}, Path("unused.txt")).remotes() == (".githooks",)
    assert _NotSet(Path("."), {}, Path("unused.txt")).config_is_unset("core.hooksPath")
    assert not _Armed(Path("."), {}, Path("unused.txt")).config_is_unset("core.hooksPath"), (
        "a repo whose core.hooksPath still reads back must not report as unset, or "
        "the unconfigured-clone arms would measure an armed repo"
    )


# ---------------------------------------------------------------------------
# The fixture is faithful to the hooks it claims to be exercising
# ---------------------------------------------------------------------------


def test_the_tracked_hook_set_is_exactly_the_three_this_probe_copies():
    """Names, not a count. A bare count drifts in both directions.

    If a fourth hook is added, this arm fails and the author has to decide
    whether the probe should copy it - rather than the probe silently
    exercising a subset of the gate while reporting on all of it.
    """
    _require_real_repo()
    listing = subprocess.run(
        ["git", "ls-files", ".githooks/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=True,
    )
    tracked = sorted(line.strip() for line in listing.stdout.splitlines() if line.strip())
    assert tracked == sorted(f".githooks/{name}" for name in EXPECTED_HOOKS), (
        f"tracked hooks are {tracked}; this probe copies {list(EXPECTED_HOOKS)}. A hook "
        f"the probe does not copy is a hook nothing here measures."
    )


def test_every_tracked_hook_is_mode_100755_in_the_index():
    """100644 is the difference between a gate and nothing on Linux.

    Git says NOTHING when it declines to run a non-executable hook, so this
    cannot be noticed by watching a commit succeed. This tree's three hooks
    were measured at 100755 while this guard was written; the guard stays
    because a sibling repo sat at 100644 for weeks with green CI.
    """
    _require_real_repo()
    listing = subprocess.run(
        ["git", "ls-files", "-s", ".githooks/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=True,
    )
    rows = [line for line in listing.stdout.splitlines() if line.strip()]
    assert rows, "git ls-files -s reported no tracked hooks at all"
    offenders = [row for row in rows if not row.startswith("100755 ")]
    assert not offenders, (
        "these tracked hooks are not mode 100755, so git will silently decline to "
        f"run them for every other clone: {offenders}. "
        "Fix with: git update-index --chmod=+x .githooks/<hook>"
    )


def _root_references(hook: str) -> set[str]:
    """Repo-relative paths a hook reaches for through "$ROOT/".

    Comment lines are dropped first. All three hooks DISCUSS their dependencies
    in prose, and a scan that read the prose would report paths nothing
    executes.
    """
    # BOTH SPELLINGS. `$ROOT/` and `${ROOT}/` are the same reference to sh, and
    # a scan that saw only the bare form was measured GREEN on 2026-09-06 while
    # a `. "${ROOT}/scripts/newdep.sh"` went uncopied - the rot guard this
    # function serves reported nothing missing while the fixture was already
    # broken. The downstream arms caught it, so it was a latent hole rather
    # than a false pass, but a guard whose job is to notice a new dependency
    # must notice it in the spelling somebody will actually use.
    pattern = re.compile(r"\$\{?ROOT\}?/([^\"'\s]+)")
    found: set[str] = set()
    for raw in (HOOKS_DIR / hook).read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        found.update(pattern.findall(stripped))
    return found


def test_the_hooks_reference_nothing_outside_the_copied_dependency_set():
    """THE FIXTURE-ROT GUARD.

    The shims are not self-contained: all three source
    `"$ROOT/scripts/hook_python.sh"` where ROOT is the THROWAWAY repo. Add a
    new `"$ROOT/scripts/whatever.py"` call to a hook and, without this arm, the
    probe would keep passing while running a hook that dies on a missing file -
    which reads as a refusal, so both negatives would stay green.
    """
    referenced: set[str] = set()
    for name in EXPECTED_HOOKS:
        referenced |= _root_references(name)
    assert referenced, (
        "no $ROOT/ reference was recovered from any hook, so this guard is "
        "measuring nothing - re-read the hook bodies before trusting it"
    )
    missing = sorted(referenced - set(HOOK_DEPENDENCIES))
    assert not missing, (
        f"the hooks reach for {missing}, which the fixture does not copy into the "
        f"throwaway repo. Add them to HOOK_DEPENDENCIES (they must be stdlib-only) "
        f"or the probe is exercising a hook that cannot run."
    )


def test_every_copied_dependency_exists_and_is_stdlib_reachable():
    """NON-VACUITY for the constant itself: an entry naming a missing file
    would make the fixture raise rather than measure, and an unused entry would
    let the guard above pass while the real dependency went uncopied."""
    for rel in HOOK_DEPENDENCIES:
        assert (REPO_ROOT / rel).is_file(), f"HOOK_DEPENDENCIES names a missing file: {rel}"
    referenced: set[str] = set()
    for name in EXPECTED_HOOKS:
        referenced |= _root_references(name)
    unused = sorted(set(HOOK_DEPENDENCIES) - referenced)
    assert not unused, (
        f"HOOK_DEPENDENCIES carries {unused}, which no hook actually references. "
        f"Either a hook stopped using it, or the entry was a guess."
    )


def test_the_probe_repo_has_no_remote_so_pre_push_can_never_fire(gate_repo: _ThrowawayRepo):
    """`.githooks/pre-push` runs BOTH suites. A probe that fired it would
    recurse - this module runs inside those suites.

    THIS ONE ASSERTION IS THE WHOLE ARM, which is why it goes through
    `remotes()` rather than reading stdout. A git that could not answer used to
    leave the same empty string a remote-less repo leaves, and the arm retired
    itself at exit 0 - measured, see `_classify_remote_list`.
    """
    remotes = gate_repo.remotes()
    assert remotes == (), (
        f"the throwaway repo has remotes {list(remotes)}; a push from here would run "
        f"pre-push, which runs the suites this test is part of"
    )


# ---------------------------------------------------------------------------
# THE POSITIVE CONTROL - without it, a gate that refuses everything passes
# both refusal arms below and looks like the safest tree in the world
# ---------------------------------------------------------------------------


def test_clean_ascii_change_commits(gate_repo: _ThrowawayRepo):
    """A clean change must LAND. HEAD before != HEAD after.

    This is the arm that fails when the fixture is broken rather than the gate:
    a missing dependency, a CRLF shebang, or a hook that refuses unconditionally
    all show up here and nowhere else.
    """
    gate_repo.stage("note.txt", CLEAN_CONTENT)
    before = gate_repo.head()
    assert before, "the fixture left HEAD unborn"

    proc = gate_repo.commit(CLEAN_MESSAGE)
    after = gate_repo.head()

    assert proc.returncode == 0, (
        f"a clean ASCII commit was REFUSED (exit {proc.returncode}). The gate is "
        f"refusing everything, which would make both negative arms below pass "
        f"while measuring nothing.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert after != before, (
        f"the commit reported success but HEAD did not move: {before} -> {after}"
    )
    assert GATE_MARKER not in proc.stderr, (
        f"the gate blocked a clean commit: {proc.stderr}"
    )
    # Confirms the PYTHON pin was honoured rather than assumed. hook_python.sh
    # prints this only when it passes OVER an explicit PYTHON, so its absence
    # means the interpreter this probe pinned is the one the hooks ran.
    #
    # THE `ruff` PASS-OVER IS EXEMPT, AND THIS IS A REAL CONTRIBUTOR CASE
    # rather than a hypothetical. `.githooks/pre-commit` asks for an
    # interpreter that can `import ruff`; this probe pins PYTHON to
    # `sys.executable`, the interpreter running pytest. Anyone with pytest in a
    # venv and ruff only on the global interpreter makes those two DIFFERENT
    # interpreters, `resin_pick_python ruff` correctly passes over the pin, and
    # a bare assertion here turned that into a RED positive control blamed on
    # the gate. Measured 2026-09-06 by pinning PYTHON at a ruff-less
    # interpreter: 1 failed, 11 passed, and the gate was perfect.
    #
    # Passing over for ruff is hook_python.sh working as designed and it is
    # announced on stderr, which is the behaviour that file exists to provide.
    # Passing over for anything else still fails: that would mean the pinned
    # interpreter could not even RUN, and this probe would be measuring
    # whatever PATH resolved instead of the interpreter it chose.
    passovers = [
        line
        for line in proc.stderr.splitlines()
        if "hooks: PYTHON=" in line and "import ruff" not in line
    ]
    assert not passovers, (
        "the hooks passed over the pinned interpreter for something other than "
        f"ruff, so this probe measured whatever PATH resolved instead: {passovers}"
    )


# ---------------------------------------------------------------------------
# NEGATIVE 1 - staged CONTENT, refused by pre-commit
# ---------------------------------------------------------------------------


def test_banned_glyph_in_staged_content_is_refused(gate_repo: _ThrowawayRepo):
    """Staged content carrying an em-dash must not become a commit.

    WHICH OF THE FOUR ASSERTIONS BELOW ACTUALLY CARRIES THIS ARM, stated
    because an ungraded assertion that LOOKS load-bearing is how a reader comes
    to trust the wrong thing. Measured 2026-09-08 by mutating `head()` to
    return a constant: four arms in this module went red and THIS ONE DID NOT.

      LOAD-BEARING: `proc.returncode != 0` and `GATE_MARKER in proc.stderr`.
                    Together they say a commit was refused AND that the gate is
                    what refused it. `tools/precommit_gate.py` emits that
                    headline from five sites; the one a staged glyph reaches is
                    its general block message, measured on this run.
      CORROBORATION: `after == before`. A HEAD that cannot move cannot fail it,
                    so no mutation of the HEAD reader is capable of turning
                    this arm red. It is kept because it is the sentence CLAUDE.md
                    demands - a refusal is a commit that did not happen - and
                    because it is the assertion whose MESSAGE a reader sees
                    first. It is not what grades the gate.

    `head()` still raises on an unreadable repository, so the corroboration is
    at least never a statement about nothing. See _classify_head_read.
    """
    gate_repo.stage("bad.txt", GLYPH_CONTENT)
    before = gate_repo.head()
    # `after == before` below is satisfied by two empty strings, so an unborn or
    # unreadable HEAD would read as a refusal. head() now RAISES on unreadable;
    # this closes the unborn half.
    assert before, "the fixture left HEAD unborn, so 'HEAD did not move' proves nothing"

    proc = gate_repo.commit(CLEAN_MESSAGE)
    after = gate_repo.head()

    assert after == before, (
        f"A BANNED GLYPH COMMITTED. HEAD moved {before} -> {after} with a U+2014 in "
        f"staged content.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert proc.returncode != 0, (
        f"git commit exited 0 while HEAD stayed at {before}; the refusal is not "
        f"attributable to the gate"
    )
    assert GATE_MARKER in proc.stderr, (
        f"the commit was refused, but not by the gate - so this arm would also pass "
        f"if the hook were merely broken.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "bad.txt" in proc.stderr, (
        f"the gate blocked without naming the offending file: {proc.stderr}"
    )


# ---------------------------------------------------------------------------
# NEGATIVE 2 - the MESSAGE, refused by commit-msg
#
# A separate hook, at a separate point in git's order. Negative 1 passing says
# nothing whatsoever about this one.
# ---------------------------------------------------------------------------


def test_banned_glyph_in_commit_message_is_refused(gate_repo: _ThrowawayRepo):
    """A clean tree with a dirty MESSAGE must not become a commit.

    THE SAME DIVISION AS THE ARM ABOVE, and measured the same way: with `head()`
    mutated to a constant this arm stayed green. `proc.returncode != 0` and
    `GATE_MARKER in proc.stderr` are load-bearing; `after == before` is
    corroboration a HEAD mutation cannot reach.
    """
    gate_repo.stage("note.txt", CLEAN_CONTENT)
    before = gate_repo.head()
    assert before, "the fixture left HEAD unborn, so 'HEAD did not move' proves nothing"

    proc = gate_repo.commit(GLYPH_MESSAGE)
    after = gate_repo.head()

    assert after == before, (
        f"A BANNED GLYPH COMMITTED IN THE SUBJECT LINE. HEAD moved {before} -> "
        f"{after}.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert proc.returncode != 0, (
        f"git commit exited 0 while HEAD stayed at {before}; the refusal is not "
        f"attributable to the gate"
    )
    assert GATE_MARKER in proc.stderr, (
        f"the commit was refused, but not by the gate. `precommit_msg_check.py` "
        f"rejecting the SUBJECT SHAPE would also refuse it, and that is a different "
        f"guard.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "commit message" in proc.stderr, (
        f"the gate blocked without naming the message as the source: {proc.stderr}"
    )


# ---------------------------------------------------------------------------
# NON-VACUITY - the same bytes, through an unconfigured clone, land clean
#
# These are the paired arms the tree's conventions require: a guard is not
# finished until something proves the detector actually fires. They also
# measure the hole itself. `core.hooksPath` is local config and is not cloned,
# so this IS the state of every fork - and CI is the only gate those
# contributors ever meet.
# ---------------------------------------------------------------------------


def test_an_unconfigured_clone_commits_banned_staged_content_straight_through(
    gate_repo: _ThrowawayRepo,
):
    gate_repo.disarm()
    assert gate_repo.config_is_unset("core.hooksPath"), (
        "core.hooksPath survived the unset; this arm would measure an armed repo. "
        f"{gate_repo.read_config('core.hooksPath').detail}"
    )

    gate_repo.stage("bad.txt", GLYPH_CONTENT)
    before = gate_repo.head()
    proc = gate_repo.commit(CLEAN_MESSAGE)
    after = gate_repo.head()

    assert proc.returncode == 0 and after != before, (
        "an unconfigured clone REFUSED a banned glyph, which means something other "
        "than core.hooksPath is doing the refusing and the two armed negatives above "
        f"may be passing for that reason instead.\nstdout: {proc.stdout}\n"
        f"stderr: {proc.stderr}"
    )


def test_an_unconfigured_clone_commits_a_banned_message_straight_through(
    gate_repo: _ThrowawayRepo,
):
    """Also proves GLYPH_MESSAGE is otherwise LEGAL.

    The subject is a valid Conventional Commits line, so
    `scripts/precommit_msg_check.py` has no quarrel with it. That is what makes
    the armed arm's refusal attributable to the glyph and to nothing else.
    """
    gate_repo.disarm()
    gate_repo.stage("note.txt", CLEAN_CONTENT)
    before = gate_repo.head()
    proc = gate_repo.commit(GLYPH_MESSAGE)
    after = gate_repo.head()

    assert proc.returncode == 0 and after != before, (
        "an unconfigured clone refused the message, so the armed arm above may be "
        f"measuring the subject-shape validator rather than the glyph gate.\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    subject = gate_repo.git("log", "-1", "--pretty=%s").stdout
    assert EM_DASH in subject, (
        "the glyph did not survive into the committed subject, so this arm did not "
        "demonstrate the hole it claims to measure"
    )
