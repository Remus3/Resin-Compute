"""The staged half's CORPUS read must fail CLOSED.

`_git` returned `out.stdout` and never consulted `out.returncode`, so an
unanswerable `git diff --cached` (exit 129 outside a repo, 128 with a bad root)
arrived at `_staged_added` as `""`, became `{}`, and `_check_staged` read `{}`
as data: no banned-glyph scan, no py_compile, no net-new ruff, return 0, EMPTY
stderr. A clean tree with nothing staged and an UNREADABLE corpus were
byte-identical to the caller.

The distinction these arms pin, and it is the whole fix:

- `None` means the corpus could not be read. Block, and say so.
- `{}` means the corpus was read and is empty. A genuine no-op commit passes.

The FAIL-OPEN RULE in the module docstring is not in tension with this. It
enumerates its own class in its parenthesis - ruff missing, message file
unreadable - which is TOOL PROVISIONING, a half the gate needs to run itself.
A staged diff is not a tool the gate needs; it is the staged half's SUBJECT.
`_check_scan_files` already carves that class out, on the same reasoning: a
gate that scanned zero files must not report zero findings as a pass.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"


@pytest.fixture(scope="module")
def gate():
    sys.path.insert(0, str(TOOLS))
    try:
        import precommit_gate
    finally:
        sys.path.pop(0)
    return precommit_gate


def _init_repo(path: pathlib.Path) -> None:
    """A real repo with a real commit, so `git diff --cached` is answerable."""
    subprocess.run(
        ["git", "init", "-q", "."], cwd=str(path), capture_output=True, timeout=60,
    )
    (path / "seed.txt").write_bytes(b"seed\n")
    subprocess.run(
        ["git", "add", "seed.txt"], cwd=str(path), capture_output=True, timeout=60,
    )
    subprocess.run(
        [
            "git",
            "-c", "user.name=t",
            "-c", "user.email=t@example.invalid",
            "-c", "commit.gpgsign=false",
            "-c", "core.hooksPath=",
            "commit", "-q", "-m", "seed",
        ],
        cwd=str(path),
        capture_output=True,
        timeout=60,
    )


def test_git_returns_none_on_nonzero_returncode(tmp_path, gate):
    """The return-type contract, pinned directly at the choke point.

    `git rev-parse --show-toplevel` outside a repo exits 128. Today's bytes
    hand back `out.stdout`, which is `""` - a str that every caller treats as
    a successful empty answer.
    """
    assert not (tmp_path / ".git").exists()
    assert gate._git(["rev-parse", "--show-toplevel"], str(tmp_path)) is None


def test_git_returns_str_on_success(gate):
    """The arm that says the None is about FAILURE and not about everything."""
    out = gate._git(["rev-parse", "--show-toplevel"], str(REPO_ROOT))
    assert isinstance(out, str)
    assert out.strip()


def test_staged_added_returns_none_when_diff_unanswerable(tmp_path, gate):
    """`None`, not `{}`. Conflating them IS the defect."""
    assert not (tmp_path / ".git").exists()
    assert gate._staged_added(str(tmp_path)) is None


def test_check_staged_blocks_and_speaks_when_corpus_unreadable(
    tmp_path, gate, capsys,
):
    """Both clauses are live on today's bytes: rc 0 and empty stderr.

    No monkeypatch of the function under test - the input is a real directory
    that is not a repo, so the real `git diff --cached` really exits 129.
    """
    assert not (tmp_path / ".git").exists()
    rc = gate._check_staged(f'git -C "{tmp_path}" commit -m x')
    err = capsys.readouterr().err
    assert rc == 1, f"unreadable corpus returned {rc}, so the commit passed unscanned"
    assert err.strip(), "blocked in SILENCE - the caller cannot tell why"
    assert str(tmp_path) in err, f"stderr does not name the root consulted: {err!r}"


def test_check_staged_passes_a_clean_repo_with_nothing_staged(
    tmp_path, gate, capsys,
):
    """The case that must NOT change.

    Without this arm the fix could wedge every clean commit in the tree and no
    arm would say so. `{}` here is a read corpus that is empty, which is a
    genuine no-op commit, and it is not the same fact as an unread one.
    """
    _init_repo(tmp_path)
    assert (tmp_path / ".git").exists()
    assert gate._staged_added(str(tmp_path)) == {}
    rc = gate._check_staged(f'git -C "{tmp_path}" commit -m x')
    err = capsys.readouterr().err
    assert rc == 0, f"a clean repo with nothing staged was blocked: {err!r}"
