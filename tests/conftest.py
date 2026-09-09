"""Shared collection-time guards for the `tests/` suite.

WHY THIS FILE EXISTS.

Several guards in this directory ask git what the repository actually TRACKS -
`ls-files`, `check-attr`, `check-ignore` - rather than walking the filesystem.
That is the right question. A disk walk answers "what is on this machine",
which is not the same as "what a fresh clone receives", and the gap between
those two is exactly the class of defect those guards exist to catch.

It also makes them depend on a git repository, and a published repository is
routinely received WITHOUT one: GitHub's "Download ZIP" button, an sdist, a
`git archive` tarball, or any vendored copy. Measured 2026-09-06 against a
147-file `git archive` extract, the suite did not merely fail there. `git
ls-files` raised inside a `@pytest.mark.parametrize` argument, so COLLECTION
ABORTED and not one test in the whole suite ran - exit 2, zero tests, for the
public that receives the repository.

WHAT THE HONEST BEHAVIOUR IS.

With no git repository, TRACKEDNESS IS UNKNOWABLE, so these guards SKIP.

They must not FAIL: nothing is wrong with the code under test, and a red suite
a reader cannot act on trains them to ignore red.

They must equally not FALL BACK TO A DISK WALK. That would silently answer a
different question, reintroducing the precise defect the `ls-files` conversion
removed, while reporting green. A guard that quietly changes what it measures
is worse than one that says it cannot measure.

Every skip names the missing repository as its reason. A silent skip is how a
guard stops guarding.

THE DANGEROUS FAILURE MODE, AND WHERE IT IS GUARDED.

If `git_unusable_reason()` ever returned a reason inside a REAL checkout, every
git-dependent guard in this directory would evaporate at once and the suite
would still report green. That is worse than deleting them, because it reads as
coverage. `tests/test_commit_trailers.py` therefore cross-checks this helper
against an independent signal and FAILS if the skip path is ever taken in a
tree that is a git repository.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Category tokens for `classify_git_probe`. They exist so a caller - in
#: practice `tests/test_conftest_git_gate.py` - can tell the four outcomes apart
#: STRUCTURALLY rather than by matching English prose. Rewording a reason string
#: is then a readability change; merging two branches is a token change and
#: reddens.
GIT_PROBE_USABLE = "usable"
GIT_PROBE_NOT_RUNNABLE = "not-runnable"
GIT_PROBE_NOT_A_REPOSITORY = "not-a-repository"
GIT_PROBE_DID_NOT_ANSWER = "did-not-answer"


def classify_git_probe(
    returncode: int | None,
    stdout: str,
    stderr: str,
    exec_error: str | None,
) -> tuple[str, str | None]:
    """Turn one `git rev-parse --git-dir` outcome into (category, reason), PURELY.

    Extracted from `git_unusable_reason()` so each of the four outcomes is
    reachable without a subprocess. Before the extraction the non-128 non-zero
    branch was separated from the 128 branch by NO TEST AT ALL - nothing under
    `tests/` stubbed the probe - so it could have been deleted into its
    neighbour with the whole suite still green.

    `exec_error` carries the already-formatted `"OSError: message"` text when the
    exec itself failed; `returncode` is then None. Every parameter is required:
    a constant bound as a DEFAULT ARGUMENT cannot be replaced by patching the
    constant, which would make this function untestable in exactly the way the
    extraction exists to fix.

    THE REASON STRINGS ARE A CONTRACT. `tests/test_commit_trailers.py`,
    `tests/test_hook_gate.py` and `tests/test_line_endings.py` all consume
    `git_unusable_reason()`'s return value, and `tests/test_hook_interpreter.py`
    quotes this wording in prose. They are reproduced here byte-identically to
    what this file emitted before the extraction.
    """
    if exec_error is not None:
        return GIT_PROBE_NOT_RUNNABLE, (
            f"git is not runnable on this machine ({exec_error}), so "
            f"trackedness cannot be established for {REPO_ROOT} and this guard is "
            "SKIPPED rather than passed"
        )

    if returncode == 0:
        return GIT_PROBE_USABLE, None

    detail = stderr.strip() or stdout.strip() or "no output"
    if returncode == 128:
        return GIT_PROBE_NOT_A_REPOSITORY, (
            "this tree is not a git repository, so trackedness cannot be established "
            "and this guard is SKIPPED rather than passed: `git rev-parse --git-dir` "
            f"in {REPO_ROOT} exited 128 ({detail}). That is the normal state of a "
            "Download-ZIP, sdist or `git archive` copy - clone the repository to "
            "enforce this guard"
        )
    return GIT_PROBE_DID_NOT_ANSWER, (
        f"git is present but did not answer for {REPO_ROOT}, so trackedness cannot be "
        "established and this guard is SKIPPED rather than passed: `git rev-parse "
        f"--git-dir` exited {returncode} ({detail})"
    )


@lru_cache(maxsize=1)
def git_unusable_reason() -> str | None:
    """Why git cannot answer questions about this tree, or None when it can.

    ASKED OF GIT, NOT INFERRED FROM DISK. The obvious check - does `.git` exist
    as a directory - is wrong three ways, and each way is a shape this project
    actually uses:

      - a linked worktree has a `.git` FILE, not a directory;
      - a submodule's git directory lives under the superproject;
      - `GIT_DIR` can move it anywhere at all.

    `git rev-parse --git-dir` is git's own answer to the same question and is
    correct in all three. Disk presence is used in exactly one place - the
    cross-check in `tests/test_commit_trailers.py` - and there its independence
    from this function is the entire point.

    The three unusable states are distinguished in the reason text, because
    "git is not installed" and "this is not a repository" send a reader to
    completely different next steps:

      - git missing or not runnable -> OSError from the exec itself
      - not a repository            -> exit 128, git's own code for it
      - git present but broken      -> any other non-zero exit

    Cached: the answer cannot change during a run, and every guard in the
    directory asks.

    THE SIGNATURE AND RETURN TYPE ARE A MERGE SURFACE and did not change when
    the classification moved into `classify_git_probe()`. Four modules under
    `tests/` consume this `str | None` directly, and returning the classifier's
    tuple here would break them - or worse, pass a truthiness check while the
    reason was None.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return classify_git_probe(None, "", "", f"{type(exc).__name__}: {exc}")[1]

    return classify_git_probe(completed.returncode, completed.stdout, completed.stderr, None)[1]


def require_git_repository() -> None:
    """Skip the CURRENT test when git cannot answer for this tree.

    For use at RUN time - inside a test body, a fixture, or a helper that a
    test calls. Raising `Skipped` from the helper that actually invokes git is
    deliberate: it puts the guard at the single point where the dependency is
    real, so a test in the same module that never reaches git keeps running and
    keeps its coverage. Skipping a whole module when only two of its tests need
    a repository would throw away working guards.
    """
    reason = git_unusable_reason()
    if reason is not None:
        pytest.skip(reason)


def skip_module_without_git() -> None:
    """Skip the WHOLE module at IMPORT time when git cannot answer.

    For the one case `require_git_repository()` cannot serve: a module that
    calls git while it is being imported, typically to build a
    `@pytest.mark.parametrize` argument list.

    A plain `pytest.skip()` is too late there. At import time the exception
    escapes collection, and pytest reports a collection ERROR - which aborts
    the entire run rather than skipping one module. That is the exact failure
    this file exists to remove, so reaching for the wrong one of these two
    helpers reproduces it. `allow_module_level=True` is the supported way to
    say "this whole file cannot run here", and it is reported as an ordinary
    skip with the reason attached.

    Call it at module scope, AFTER the imports and BEFORE the first line that
    touches git.
    """
    reason = git_unusable_reason()
    if reason is not None:
        pytest.skip(reason, allow_module_level=True)
