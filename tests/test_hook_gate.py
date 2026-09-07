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

    AND THE CITED MECHANISM IS NOT THE REAL ONE. On `git 2.53.0.windows.3`,
    `pre-push` exports only `GIT_EDITOR`, `GIT_EXEC_PATH` and `GIT_PREFIX` - no
    `GIT_DIR`, no `GIT_INDEX_FILE`. `pre-commit` exports `GIT_INDEX_FILE` but
    still no `GIT_DIR`. The scrub is correct defensive practice and cheap; it
    is not preventing the specific leak this comment used to claim.
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
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import git_unusable_reason

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".githooks"

# MEASURED against this tree, not copied from a sibling. Riot Commander's
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


def _msys_tool(name: str) -> str | None:
    """Locate a POSIX tool, falling back to the one git ships on Windows.

    PowerShell has no `sh` on PATH and the operator runs the suite from there,
    so it is located from git's own install rather than assumed reachable.
    Same approach as tests/test_hook_interpreter.py, for the same reason.
    """
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


class _ThrowawayRepo:
    """A `git init` under tmp_path wired exactly the way the installer wires
    this one, and isolated from everything about the machine it runs on."""

    def __init__(self, root: Path, env: dict[str, str], message_file: Path) -> None:
        self.root = root
        self.env = env
        self.message_file = message_file

    def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
        if check and proc.returncode != 0:
            raise AssertionError(
                f"fixture setup failed: `git {' '.join(args)}` exited "
                f"{proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        return proc

    def head(self) -> str:
        """The current commit, or '' on an unborn HEAD."""
        return self.git("rev-parse", "HEAD").stdout.strip()

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


def _throwaway_env(root: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # Non-existent paths. Git reads them as empty config, which is the point:
    # an inherited hooksPath, autocrlf or LFS filter would make every arm below
    # a statement about the wrong repository.
    env["GIT_CONFIG_GLOBAL"] = str(root / "no-global-gitconfig")
    env["GIT_CONFIG_SYSTEM"] = str(root / "no-system-gitconfig")
    env["PYTHON"] = sys.executable.replace("\\", "/")
    sh_path = _msys_tool("sh")
    if sh_path is not None:
        # APPENDED. Launched from PowerShell, `sh.exe` inherits a PATH with no
        # /usr/bin on it and the hooks die on `grep: command not found` - a
        # harness artefact with nothing to do with what is being graded.
        env["PATH"] = env.get("PATH", "") + os.pathsep + str(Path(sh_path).parent)
    return env


@pytest.fixture
def gate_repo(tmp_path: Path) -> _ThrowawayRepo:
    if shutil.which("git") is None:
        _unavailable("git is not on PATH, so no repository can be created")
    if _msys_tool("sh") is None:
        _unavailable("no POSIX sh on this machine - the .githooks/ shims cannot run")
    for name in EXPECTED_HOOKS:
        if not (HOOKS_DIR / name).is_file():
            _unavailable(f"missing {HOOKS_DIR / name}, so the real hook cannot be copied")

    root = tmp_path / "throwaway"
    root.mkdir()
    repo = _ThrowawayRepo(root, _throwaway_env(root), tmp_path / "commit-message.txt")

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
    recurse - this module runs inside those suites."""
    remotes = gate_repo.git("remote").stdout.strip()
    assert remotes == "", (
        f"the throwaway repo has remotes {remotes!r}; a push from here would run "
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
    """Staged content carrying an em-dash must not become a commit."""
    gate_repo.stage("bad.txt", GLYPH_CONTENT)
    before = gate_repo.head()

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
    """A clean tree with a dirty MESSAGE must not become a commit."""
    gate_repo.stage("note.txt", CLEAN_CONTENT)
    before = gate_repo.head()

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
    assert gate_repo.git("config", "--get", "core.hooksPath").stdout.strip() == "", (
        "core.hooksPath survived the unset; this arm would measure an armed repo"
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
