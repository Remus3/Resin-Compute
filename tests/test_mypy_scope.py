"""mypy's scope is a PROPER SUBSET of this tree, and that must stay visible.

Every other gate here sweeps the whole tracked corpus and carries a meta-test
against its own scope developing a hole. `ruff check .` traverses exactly the 92
tracked `.py` files. `precommit_gate.py` partitions every tracked path on the
`.md` suffix and its docstring records the historical case where 14 files
matched neither selector. `tests/test_line_endings.py` parametrizes over every
suffix the tree actually uses.

mypy is the exception. `mypy.ini` restricts `files=` to four roots, so
`python -m mypy` reports success over roughly a quarter of the tracked Python
and says nothing about the rest. That is a defensible design and an indefensible
silence: the command prints `Success: no issues found in N source files` with no
hint that N is a subset, and two files in `.claude/agents/` used to instruct an
agent to run it as a done-gate over slices it cannot see. A builder working in
`headless/` ran it, read Success, and reported done on a module mypy had never
opened. Zero out of zero reads as a pass.

So this module pins the scope. The dark set is declared here as a literal with a
reason per entry, NOT derived from `mypy.ini`, because a test that recomputes
its expectation from the file it is checking can never fail. A directory that
falls out of coverage shows up as a new dark entry and this goes red.
"""

from __future__ import annotations

import configparser
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Directories holding tracked `.py` that `python -m mypy` does NOT check, with
#: the reason each one is out. Measured 2026-09-07 by widening `files=` one
#: directory at a time against an unmodified tree; the error counts are what a
#: future session would have to fix to bring each one in.
#:
#: This is a LITERAL, deliberately. Deriving it from `mypy.ini` would make the
#: assertion a tautology - the config would always agree with itself.
DARK_BY_DESIGN = {
    "tests": "39 files. Test bodies are untyped by convention here.",
    "scripts": (
        "7 files. BLOCKED rather than chosen: mypy refuses the tree with "
        "'Source file found twice under different module names' for "
        "scripts/make_shortcut.py, which needs an __init__.py or "
        "--explicit-package-bases before the directory can be added at all."
    ),
    "surface": "5 files, 1 error when added.",
    "ops": "5 files, 8 errors when added.",
    "headless": "3 files, 3 errors when added.",
    "agents": "agents/__init__.py only; the pity_engine package itself IS checked.",
    ".": "conftest.py at the repository root.",
}

#: Roots that `mypy.ini` must keep in `files=`. `tools/` is here because it
#: holds the guards - the gates, the hand-off writer, the claim gate - and
#: because adding it cost nothing: it was measured clean at 0 errors.
REQUIRED_ROOTS = ("core/", "engines/", "ingest/", "agents/pity_engine/", "tools/")


def _git_python_files(*args: str) -> tuple[str, ...]:
    """`.py` paths from GIT rather than from a filesystem walk.

    A walk behind an ad-hoc denylist is the shape that went red in this tree for
    any contributor who created a `.venv/`.
    """
    require_git_repository()
    out = subprocess.run(
        ["git", "ls-files", "-z", *args, "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tuple(sorted(p for p in out.split("\0") if p))


def _tracked_python_files() -> tuple[str, ...]:
    return _git_python_files()


def _untracked_python_files() -> tuple[str, ...]:
    """`.py` present but not yet staged, ignored files excluded.

    mypy WALKS THE FILESYSTEM and git does not, so a builder part-way through a
    slice - a new module written and not yet staged - makes the two disagree
    legitimately. The count arm went red for exactly that on 2026-09-07, on a
    worktree holding a new `tools/` module, and a guard that reddens for honest
    work in progress is one a contributor learns to ignore.
    """
    return _git_python_files("--others", "--exclude-standard")


def _configured_roots() -> tuple[str, ...]:
    parser = configparser.ConfigParser()
    parser.read(REPO_ROOT / "mypy.ini", encoding="utf-8")
    raw = parser.get("mypy", "files")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _top_level(rel: str) -> str:
    head, sep, _ = rel.partition("/")
    return head if sep else "."


def _partition() -> tuple[list[str], list[str]]:
    """`(covered, dark)` over the tracked corpus, by the configured roots."""
    roots = _configured_roots()
    covered: list[str] = []
    dark: list[str] = []
    for rel in _tracked_python_files():
        if any(rel.startswith(root) for root in roots):
            covered.append(rel)
        else:
            dark.append(rel)
    return covered, dark


def test_the_corpus_is_real_and_the_partition_is_armed():
    """Non-vacuity first. A partition of nothing agrees with any expectation."""
    tracked = _tracked_python_files()
    assert len(tracked) > 50, (
        f"only {len(tracked)} tracked .py files found; the corpus query is "
        "broken and every assertion below would be vacuous"
    )
    covered, dark = _partition()
    assert covered, "no file is covered, so the configured roots match nothing"
    assert dark, (
        "nothing is dark, which would mean mypy now sweeps the whole tree - "
        "good news, but this module's premise is gone and it should be rewritten"
    )
    assert len(covered) + len(dark) == len(tracked)


def test_the_dark_set_is_exactly_what_is_declared_here():
    """A directory falling out of mypy coverage must go RED, not go quiet."""
    _, dark = _partition()
    got = {_top_level(rel) for rel in dark}
    assert got == set(DARK_BY_DESIGN), (
        "mypy's dark set moved.\n"
        f"  newly dark: {sorted(got - set(DARK_BY_DESIGN))}\n"
        f"  no longer dark: {sorted(set(DARK_BY_DESIGN) - got)}\n"
        "Update DARK_BY_DESIGN with a measured reason, or restore the root to "
        "mypy.ini. Do not update it to make this pass without measuring."
    )


@pytest.mark.parametrize("root", REQUIRED_ROOTS)
def test_a_required_root_is_still_configured(root):
    """Named roots cannot be dropped from `files=` without this going red."""
    assert root in _configured_roots(), (
        f"{root} left mypy.ini's files= list. Everything under it is now "
        "unchecked while the command still prints Success."
    )


def test_mypy_reports_the_number_of_files_the_partition_predicts():
    """The load-bearing arm: the config's own arithmetic against mypy's output.

    Without this the module only proves that `mypy.ini` says what it says. An
    `exclude=` line, a stub-only module or a resolution failure can all make the
    real number differ from the configured one, and the number in the hand-off
    block is the one a reader trusts.
    """
    covered, _ = _partition()
    parser = configparser.ConfigParser()
    parser.read(REPO_ROOT / "mypy.ini", encoding="utf-8")
    excluded_prefix = parser.get("mypy", "exclude", fallback="").lstrip("^")
    if excluded_prefix:
        covered = [rel for rel in covered if not rel.startswith(excluded_prefix)]
    assert covered, "the covered set emptied out, so the comparison is vacuous"

    run = subprocess.run(
        ["python", "-m", "mypy"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tail = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
    assert "source files" in tail, (
        "mypy did not print a source-file count, so this arm cannot compare "
        f"anything. Last line was: {tail!r}"
    )
    # Read the count that precedes "source files", NOT the first digit on the
    # line. When mypy is clean the tail is "Success: no issues found in N source
    # files" and the two agree. When mypy has errors it is "Found 3 errors in 3
    # files (checked 31 source files)" and the first digit is the ERROR count.
    # Measured 2026-09-07: this arm reported "mypy checked 3 files but the
    # configured roots select 31" on a CI run whose real problem was three
    # platform errors, and the message sent the reader to look at the scope
    # rather than at the errors. A guard that reports the wrong number is worse
    # than one that stays quiet.
    words = tail.split()
    reported = None
    for index in range(len(words) - 1):
        if words[index] == "source" and words[index + 1].startswith("files"):
            candidate = words[index - 1]
            if candidate.isdigit():
                reported = int(candidate)
                break
    assert reported is not None, (
        "could not find the file count before 'source files'. Last line was: "
        + repr(tail)
    )

    roots = _configured_roots()
    pending = [
        rel
        for rel in _untracked_python_files()
        if any(rel.startswith(root) for root in roots)
        and not (excluded_prefix and rel.startswith(excluded_prefix))
    ]
    expected = len(covered) + len(pending)
    assert reported == expected, (
        f"mypy checked {reported} files but the configured roots select "
        f"{len(covered)} tracked plus {len(pending)} unstaged. The two have "
        "drifted, so the count in any hand-off block is describing something "
        "other than the tree."
        + (f" Unstaged under the roots: {pending}" if pending else "")
    )
