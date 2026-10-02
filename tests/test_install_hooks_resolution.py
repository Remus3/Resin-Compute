"""`scripts/install_hooks.py` exit path 4: a PATH, compared as a PATH.

WHAT WAS WRONG. `main()` writes `core.hooksPath` and then READS IT BACK, which
is the right instinct - a --system, --global, --worktree or include-supplied
value can outrank the --local one just written, so the write is not the fact
and the readback is. The comparison was `active != HOOKS_DIRNAME`: two
STRINGS, where the subject is a PATH. One directory has many spellings, and
all but one of them made the installer announce `hooks are NOT installed`
about a clone whose hooks were installed and firing.

ENUMERATED EXIT PATHS OF `main()`, in source order, because "path 4" has to
name something rather than gesture at it. `test_main_has_exactly_six_exit_paths_and_the_fourth_is_the_readback`
below derives this list from the AST rather than from this docstring, so the
two cannot drift apart silently:

    1  return 1   REPO_ROOT has no .git entry
    2  return 1   the tracked .githooks/ directory is missing
    3  return 1   `git config core.hooksPath <name>` itself failed
    4  return 1   THE READBACK did not name the hooks directory   <-- this one
    5  return 1   a tracked hook is not mode 100755 in the index
    6  return 0   success

Six, not seven. A sibling's enumeration of this script reported seven; this
run counted the `ast.Return` nodes inside `main` and got six, and the
module-level `raise SystemExit(main())` is the obvious seventh thing a reader
may or may not have been counting. Say which population was counted: this one
is RETURN STATEMENTS IN `main`, and the arm below counts exactly that.

HOW THE DEFECT WAS MEASURED, end to end, rather than reasoned about. A
throwaway repo was wired exactly as a fresh clone - real `.githooks/`, real
`tools/precommit_gate.py`, hooks at index mode 100755 - and then given

    git config extensions.worktreeConfig true
    git config --worktree core.hooksPath '.githooks/'

one trailing separator, at the WORKTREE scope, which outranks the --local
scope the installer writes. That is not an exotic configuration here: this
repository runs its agents in linked worktrees. The installer exited 1 with

    core.hooksPath reads back as '.githooks/', expected '.githooks' -
    hooks are NOT installed.

while a real `git commit` of a line carrying U+2014 under that same
configuration was REFUSED, HEAD did not move, and `precommit_gate BLOCKED`
was on stderr. The hooks were installed. The string said otherwise.
`'./.githooks'` reproduces it identically. After the fix the same repo exits
0 and still refuses the glyph.

THE RULE THIS SCRIPT SITS UNDER, restated because it is what makes a false
"NOT installed" expensive rather than cosmetic: git hooks are the
AUTHORITATIVE gate, `core.hooksPath` is LOCAL config and is not cloned, so a
fresh clone runs ZERO hooks until this script runs. An installer that cries
wolf is an installer whose output people stop reading. NEVER treat a hook's
PRESENCE as proof it fires - every arm here that claims hooks are or are not
active proves it by attempting a REAL COMMIT and reading HEAD.

THE WINDOWS SPELLING SPACE, and which members of it are portable enough to
assert. A case difference, a trailing separator, a backslash separator, an
8.3 short name, a junction and an absolute spelling all name one directory
and all compare unequal as strings. Only the trailing separator, the `./`
prefix and the absolute spelling behave identically on Linux, so those three
are the committed arms; the case arm is guarded on `os.name == "nt"` and
states in its skip why.

NON-VACUITY, the paired arm this tree requires of every sweep. A readback
naming a DIFFERENT directory must still be refused, and
`test_a_hooks_path_naming_a_different_directory_is_refused_and_the_hooks_really_are_dead`
proves both halves of that in one run: the installer says no, AND the same
banned glyph commits straight through, so the installer's no was true.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import git_unusable_reason

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install_hooks.py"
HOOKS_DIR = REPO_ROOT / ".githooks"

#: Mirrors tests/test_hook_gate.py's EXPECTED_HOOKS. Named rather than
#: counted - a bare count drifts silently in either direction.
EXPECTED_HOOKS = ("commit-msg", "pre-commit", "pre-push")

#: Everything the three shims reach for through "$ROOT/", plus the installer
#: itself, which is the subject here.
COPIED = (
    "scripts/hook_python.sh",
    "scripts/install_hooks.py",
    "scripts/precommit_msg_check.py",
    "scripts/precommit_pycompile.py",
    "tools/precommit_gate.py",
)

#: Never a literal - typing one would make this module violate the rule the
#: gate it drives exists to enforce.
EM_DASH = chr(0x2014)
GLYPH_CONTENT = ("clause" + EM_DASH + "break\n").encode("utf-8")
CLEAN_MESSAGE = b"docs(installer-probe): a clean ascii commit\n"
GATE_MARKER = "precommit_gate BLOCKED"

_TIMEOUT = 180


def _load_installer():
    """`scripts/install_hooks.py` loaded FRESH from disk, under a private name.

    `scripts/` is not a package and is not on `sys.path`, so this is the only
    way to reach `_names_hooks_dir` as a function rather than as text. A
    private module name keeps it out of anything else's import cache.
    """
    spec = importlib.util.spec_from_file_location(
        "_install_hooks_probe", INSTALLER
    )
    assert spec is not None and spec.loader is not None, (
        f"{INSTALLER} could not be loaded, so nothing here measures it"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The enumeration - which return IS path 4
# ---------------------------------------------------------------------------


def _main_ast() -> tuple[ast.FunctionDef, list[ast.Return], dict[ast.AST, ast.AST]]:
    """`main`, its returns IN SOURCE ORDER, and a child -> parent map.

    ONE parse, returning all three, and that is a measurement rather than
    tidiness. Two parses produce two independent object graphs, and an
    identity lookup of a node from parse A in a parent map from parse B
    silently answers None - which this arm first reported as "path 4 is not
    inside an `if`" about a function where it plainly is.

    SORTED BY POSITION for the same class of reason: `ast.walk` is
    BREADTH-FIRST, so taken raw its index 3 was the final `return 0`. "Path 4"
    is a claim about SOURCE ORDER, so the list has to be in it.
    """
    tree = ast.parse(INSTALLER.read_text(encoding="utf-8"))
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(main):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    found = [n for n in ast.walk(main) if isinstance(n, ast.Return)]
    return main, sorted(found, key=lambda n: (n.lineno, n.col_offset)), parents


def test_main_has_exactly_six_exit_paths_and_the_fourth_is_the_readback():
    """Derives the enumeration in the module docstring from the AST.

    Counting RETURN STATEMENTS IN `main`, which is the population being
    counted and is stated as such. The module-level `raise SystemExit(main())`
    is not one of them and is the likeliest source of a seventh in anyone
    else's count.

    This arm is what stops the fix below being attached to the wrong path. If
    someone inserts a new guard above the readback, path 4 becomes something
    else and this goes red with a reason rather than letting the docstring rot.
    """
    _main, returns, parents = _main_ast()
    assert len(returns) == 6, (
        f"main() has {len(returns)} return statements, not the six the module "
        f"docstring enumerates, at lines {[n.lineno for n in returns]}"
    )

    source = INSTALLER.read_text(encoding="utf-8").splitlines()
    fourth = returns[3]
    guard: ast.AST | None = parents.get(fourth)
    while guard is not None and not isinstance(guard, ast.If):
        guard = parents.get(guard)
    assert isinstance(guard, ast.If), (
        f"exit path 4 (line {fourth.lineno}: {source[fourth.lineno - 1].strip()!r}) "
        f"is not inside an `if`, so the enumeration above describes a different "
        f"function than the one on disk"
    )
    assert ast.unparse(guard.test) == "not _names_hooks_dir(active, hooks_dir)", (
        f"exit path 4 is guarded by {ast.unparse(guard.test)!r}, not by the "
        f"RESOLVED-path predicate. If this reads like a string comparison of "
        f"`active` against a name, the defect is back: a path has many spellings "
        f"and all but one of them make the installer report a working "
        f"installation as broken."
    )


# ---------------------------------------------------------------------------
# The predicate, as a unit - every spelling of one directory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spelling",
    [
        ".githooks",
        ".githooks/",
        "./.githooks",
        "./.githooks/",
    ],
    ids=["bare", "trailing-separator", "dot-prefix", "both"],
)
def test_every_relative_spelling_of_the_hooks_directory_is_accepted(spelling: str):
    """All four name one directory. Only the first survives a string compare."""
    module = _load_installer()
    assert module._names_hooks_dir(spelling, HOOKS_DIR), (
        f"{spelling!r} names {HOOKS_DIR} and was rejected, so the installer would "
        f"report a working clone as unhooked"
    )


def test_the_absolute_spelling_of_the_hooks_directory_is_accepted():
    """`core.hooksPath` is documented as absolute OR relative, so both arrive."""
    module = _load_installer()
    assert module._names_hooks_dir(str(HOOKS_DIR), HOOKS_DIR)
    assert str(HOOKS_DIR) != ".githooks", (
        "the absolute and relative spellings are the same string here, so this "
        "arm is not measuring the absolute case at all"
    )


@pytest.mark.skipif(
    os.name != "nt",
    reason="a case difference names a DIFFERENT directory on a case-sensitive "
    "filesystem, so accepting it on Linux would be a defect rather than a fix",
)
def test_a_case_difference_is_accepted_on_windows_only():
    module = _load_installer()
    assert module._names_hooks_dir(".GITHOOKS", HOOKS_DIR), (
        "Windows resolves .GITHOOKS and .githooks to one directory and git runs "
        "the hooks under either, so the installer must not call one of them absent"
    )


@pytest.mark.parametrize(
    "spelling",
    ["", "somewhere-else", ".githooks-old", "scripts"],
    ids=["empty", "sibling-name", "near-miss", "a-real-but-wrong-directory"],
)
def test_a_hooks_path_naming_anything_else_is_still_refused(spelling: str):
    """NON-VACUITY for every arm above.

    A predicate that returned True unconditionally would pass all five
    acceptance arms perfectly. `scripts` is in the list on purpose: it is a
    directory that EXISTS, so a resolver that quietly accepted any resolvable
    path would be caught here rather than only by the non-existent names.
    """
    module = _load_installer()
    assert not module._names_hooks_dir(spelling, HOOKS_DIR), (
        f"{spelling!r} does not name {HOOKS_DIR} and was accepted, so the "
        f"installer would report hooks installed when they are not"
    )


# ---------------------------------------------------------------------------
# End to end - the only valid test of a hook is a real commit
# ---------------------------------------------------------------------------


class _Clone:
    """A `git init` wired the way a fresh clone is, isolated from this machine."""

    def __init__(self, root: Path, env: dict[str, str], message_file: Path) -> None:
        self.root = root
        self.env = env
        self.message_file = message_file

    def git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            ["git", "-C", str(self.root), *args],
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
        proc = self.git("rev-parse", "HEAD")
        if proc.returncode != 0:
            raise AssertionError(
                "the throwaway clone could not be read, so no arm here may report "
                f"on whether HEAD moved: {proc.stderr.strip()}"
            )
        return proc.stdout.strip()

    def install_hooks(self) -> subprocess.CompletedProcess:
        """Run the SHIPPED installer, by `sys.executable`, never a bare name.

        Windows `CreateProcess` resolves a bare name against the calling
        image's directory first, then cwd, then PATH, so a bare `python` can
        be three different interpreters from one process.
        """
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "install_hooks.py")],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )

    def attempt_banned_commit(self) -> tuple[bool, subprocess.CompletedProcess]:
        """Stage a U+2014 and really try to commit it. Returns (landed, proc).

        THIS is the only valid test of whether a hook fires. A hook's presence
        on disk, and `core.hooksPath` reading back a plausible value, are both
        things that stay true while the gate is absent.
        """
        (self.root / "bad.txt").write_bytes(GLYPH_CONTENT)
        self.git("add", "--", "bad.txt", check=True)
        before = self.head()
        self.message_file.write_bytes(CLEAN_MESSAGE)
        proc = self.git("commit", "-F", str(self.message_file))
        landed = self.head() != before
        return landed, proc


@pytest.fixture
def clone(tmp_path: Path) -> _Clone:
    reason = git_unusable_reason()
    if reason:
        pytest.skip(reason)
    if shutil.which("sh") is None:
        pytest.skip(
            "no POSIX sh on PATH, so the /bin/sh hook bodies cannot run and no "
            "arm here could tell a disarmed gate from an unrunnable one"
        )
    for name in EXPECTED_HOOKS:
        if not (HOOKS_DIR / name).is_file():
            pytest.skip(f"missing {HOOKS_DIR / name}, so the real hook cannot be copied")

    root = tmp_path / "clone"
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # Non-existent paths. Git reads them as empty config, which is the point:
    # an inherited hooksPath would make every arm a statement about this
    # machine rather than about a fresh clone.
    env["GIT_CONFIG_GLOBAL"] = str(root / "no-global-gitconfig")
    env["GIT_CONFIG_SYSTEM"] = str(root / "no-system-gitconfig")
    env["PYTHON"] = sys.executable.replace("\\", "/")
    sh_dir = str(Path(shutil.which("sh")).parent)
    # APPENDED. Launched from PowerShell, sh.exe inherits a PATH with no
    # /usr/bin on it and the hooks die on `grep: command not found`.
    env["PATH"] = env.get("PATH", "") + os.pathsep + sh_dir

    repo = _Clone(root, env, tmp_path / "commit-message.txt")
    repo.git("init", check=True)
    for key, value in (
        ("user.name", "Installer Probe"),
        ("user.email", "installer-probe@example.invalid"),
        # An unsigned-commit prompt HANGS CI.
        ("commit.gpgsign", "false"),
    ):
        repo.git("config", key, value, check=True)

    # shutil.copy preserves BYTES. hook_python.sh in particular must keep LF.
    (root / ".githooks").mkdir()
    for name in EXPECTED_HOOKS:
        shutil.copy(HOOKS_DIR / name, root / ".githooks" / name)
    for rel in COPIED:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, destination)

    repo.git("add", "-A", check=True)
    for name in EXPECTED_HOOKS:
        repo.git("update-index", "--chmod=+x", f".githooks/{name}", check=True)
    repo.message_file.write_bytes(b"chore(installer-probe): baseline\n")
    repo.git("commit", "--no-verify", "-F", str(repo.message_file), check=True)
    if not repo.head():
        raise AssertionError("the fixture baseline commit left HEAD unborn")
    return repo


def _pin_at_worktree_scope(repo: _Clone, value: str) -> None:
    """Put `value` in the one scope that outranks the --local one the
    installer writes. This is the mechanism a linked worktree uses, which is
    why it is the realistic reproduction here rather than a contrivance."""
    repo.git("config", "extensions.worktreeConfig", "true", check=True)
    repo.git("config", "--worktree", "core.hooksPath", value, check=True)
    readback = repo.git("config", "core.hooksPath").stdout.strip()
    assert readback == value, (
        f"the --worktree pin did not take: git reads back {readback!r}, not "
        f"{value!r}, so this arm would measure an ordinary installation"
    )


@pytest.mark.parametrize(
    "spelling", [".githooks/", "./.githooks"], ids=["trailing-separator", "dot-prefix"]
)
def test_a_differently_spelled_hooks_path_installs_and_the_hooks_really_fire(
    clone: _Clone, spelling: str
):
    """THE REGRESSION. Both halves, because either alone is unfalsifiable.

    The installer must exit 0 - and the hooks must actually REFUSE a banned
    glyph under that same configuration, proving the exit 0 was true rather
    than merely cheerful. Before the fix this arm's first assertion failed
    with `hooks are NOT installed` while the second one passed, which is the
    defect stated as two measurements.
    """
    _pin_at_worktree_scope(clone, spelling)

    installed = clone.install_hooks()
    assert installed.returncode == 0, (
        f"the installer rejected core.hooksPath={spelling!r}, which names the "
        f"same directory as '.githooks'. A path was compared as a string.\n"
        f"stdout: {installed.stdout}\nstderr: {installed.stderr}"
    )

    landed, proc = clone.attempt_banned_commit()
    assert not landed, (
        f"the installer reported success but a U+2014 COMMITTED under "
        f"core.hooksPath={spelling!r}, so its exit 0 was false.\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert GATE_MARKER in proc.stderr, (
        f"the commit was refused, but not by the gate, so this arm would also pass "
        f"on a merely broken hook.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


def test_a_hooks_path_naming_a_different_directory_is_refused_and_the_hooks_really_are_dead(
    clone: _Clone,
):
    """NON-VACUITY for the arm above, and it carries its own proof.

    An installer that simply stopped checking would pass the arm above
    perfectly. Here the readback names a directory that is NOT the hooks
    directory, so the installer must say so - and the banned glyph must
    COMMIT, which is what makes the refusal a true statement rather than a
    reflex.
    """
    _pin_at_worktree_scope(clone, "somewhere-else")

    installed = clone.install_hooks()
    assert installed.returncode != 0, (
        f"the installer accepted core.hooksPath='somewhere-else'. A resolver that "
        f"accepts anything is not a check.\nstdout: {installed.stdout}\n"
        f"stderr: {installed.stderr}"
    )
    assert "NOT installed" in installed.stderr, (
        f"the installer failed without saying the hooks are absent, so a reader "
        f"gets an exit code and no reason: {installed.stderr}"
    )

    landed, proc = clone.attempt_banned_commit()
    assert landed, (
        f"the installer said the hooks are NOT installed, but something refused a "
        f"banned glyph anyway - so the arm above may be passing for a reason "
        f"other than core.hooksPath.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert GATE_MARKER not in proc.stderr, (
        f"the gate spoke in a clone it is not installed in: {proc.stderr}"
    )


def test_the_installer_says_out_loud_when_another_scope_supplied_the_path(
    clone: _Clone,
):
    """A different SPELLING is not a failure, but it is not nothing either.

    Something outranked the --local value the installer just wrote. That is
    the one fact a reader would otherwise have to go hunting for, so the
    installer prints it. This arm exists so a later tidy-up does not delete
    the line as noise.
    """
    _pin_at_worktree_scope(clone, ".githooks/")
    installed = clone.install_hooks()
    assert installed.returncode == 0, installed.stderr
    assert "higher-precedence scope" in installed.stdout, (
        f"the installer accepted a value another scope supplied and said nothing "
        f"about it: {installed.stdout}"
    )


def test_the_ordinary_case_prints_no_such_note(clone: _Clone):
    """NON-VACUITY for the arm above: the note must not be unconditional."""
    installed = clone.install_hooks()
    assert installed.returncode == 0, installed.stderr
    assert "higher-precedence scope" not in installed.stdout, (
        f"the note fires on a plain installation too, so it tells a reader "
        f"nothing: {installed.stdout}"
    )
